"""Indicadores Movidesk - lógica (escalonamentos, dúvidas e demais métricas direto do banco do Movidesk).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import logging
import re
from datetime import datetime
from datetime import timedelta
from typing import Optional

import pandas as pd

from areas.horas_trabalhadas.logica import _buscar_apontamentos_movidesk
from areas.horas_trabalhadas.logica import _df_detalhe_ticket
from areas.horas_trabalhadas.logica import _gerar_xlsx
from areas.horas_trabalhadas.logica import _mapa_atribuicao_por_nome_movidesk
from areas.horas_trabalhadas.logica import _montar_detalhe_apontamentos
from core.db_utils import fechar_conexao
from nucleo.equipes import _pertence_a_equipe
from nucleo.movidesk import _conectar_indicadores_movidesk

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _buscar_tabelas_parecidas(conn, termo_busca: str) -> list:
    """Procura tabelas cujo nome contenha um pedaço do termo de busca (sem
    diferenciar maiúsculas/minúsculas), em qualquer schema do banco - ajuda
    a encontrar o nome/schema corretos quando uma consulta falha com
    "Invalid object name", sem precisar abrir o SSMS pra procurar na mão."""
    try:
        pedaco = re.sub(r"[_\W]+", "", termo_busca)[:8]  # pedaço reconhecível, sem underscore/símbolos
        df = pd.read_sql(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE ?",
            conn, params=(f"%{pedaco}%",),
        )
        return [f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}" for r in df.to_dict("records")]
    except Exception:
        return []  # diagnóstico é só um extra - se ele mesmo falhar, não deve mascarar o erro original


def _buscar_colunas_tabela(conn, nome_tabela: str) -> list:
    """Lista as colunas REAIS de uma tabela (via INFORMATION_SCHEMA.COLUMNS)
    - usado quando o erro é de COLUNA errada (não de tabela), pra mostrar
    de cara quais colunas existem de verdade, sem precisar abrir o SSMS."""
    try:
        df = pd.read_sql(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            conn, params=(nome_tabela,),
        )
        return df["COLUMN_NAME"].tolist()
    except Exception:
        return []


def _executar_consulta_indicador(conn, nome_amigavel: str, termo_busca: str, query: str, params: tuple = ()):
    """Roda uma consulta isolada pro dashboard de indicadores - se
    falhar, NÃO derruba as outras 3 seções (cada uma é independente).
    O diagnóstico é esperto sobre o TIPO de erro: se for tabela que não
    existe (42S02 / "Invalid object name"), sugere tabelas parecidas; se
    for coluna que não existe (42S22 / "Invalid column name"), lista as
    colunas REAIS da tabela - bem mais direto ao ponto do que ficar
    adivinhando nome de coluna às cegas. Retorna
    (dataframe_ou_None, mensagem_de_erro_ou_None)."""
    try:
        return pd.read_sql(query, conn, params=params), None
    except Exception as e:
        texto_erro = str(e)
        msg = texto_erro
        eh_erro_de_coluna = "42S22" in texto_erro or "Invalid column name" in texto_erro
        if eh_erro_de_coluna:
            colunas_reais = _buscar_colunas_tabela(conn, termo_busca)
            if colunas_reais:
                msg += f" — colunas que realmente existem em '{termo_busca}': {', '.join(colunas_reais)}"
            else:
                msg += f" — não consegui listar as colunas de '{termo_busca}' (a tabela em si existe?)."
        else:
            sugestoes = _buscar_tabelas_parecidas(conn, termo_busca)
            if sugestoes:
                msg += f" — tabelas parecidas encontradas neste banco: {', '.join(sugestoes[:8])}"
            else:
                msg += " — não encontrei nenhuma tabela parecida neste banco; confirme se é o banco certo."
        return None, msg


def _montar_secao_indicador(df, erro_query: Optional[str], construtor) -> dict:
    """Empacota o resultado de uma consulta no formato {ok, erro, ...}
    que o front-end espera - isola erros que aconteçam até na hora de
    PROCESSAR o resultado (não só na query em si, ex.: coluna com nome
    diferente do esperado), pra um problema aqui também ficar restrito a
    essa seção específica, sem derrubar as outras 3."""
    if erro_query:
        return {"ok": False, "erro": erro_query}
    try:
        return {"ok": True, **construtor(df)}
    except Exception as e:
        return {"ok": False, "erro": f"A consulta funcionou, mas não consegui processar o resultado: {e}"}


def _apontamentos_da_equipe(conn, dt_inicio, dt_fim, equipe_filtro: Optional[str]) -> list:
    """Apontamentos do período, filtrados pela equipe (se pedida) - o mesmo
    critério do card "Chamados por analista" e do Excel do mês."""
    apontamentos = _buscar_apontamentos_movidesk(conn, dt_inicio, dt_fim)
    if equipe_filtro:
        mapa_equipe = _mapa_atribuicao_por_nome_movidesk()

        def _pertence_apontamento_im(a):
            nome = str(a.get("createdbyname") or "").strip().upper()
            return nome in mapa_equipe and _pertence_a_equipe(mapa_equipe[nome], equipe_filtro)
        apontamentos = [a for a in apontamentos if _pertence_apontamento_im(a)]
    return apontamentos


def _contar_chamados_por_analista(apontamentos: list) -> list:
    """Tickets DISTINTOS por pessoa, do maior pro menor. Uma função só pra
    tela e pro Excel: o número da planilha é sempre o mesmo da tela."""
    contagem: dict = {}
    for row in apontamentos:
        analista = str(row.get("createdbyname") or "").strip().upper()
        ticket_id = row.get("id")
        if not analista or ticket_id is None:
            continue
        contagem.setdefault(analista, set()).add(ticket_id)
    return sorted(
        [{"analista": nome, "qtd": len(tickets)} for nome, tickets in contagem.items()],
        key=lambda x: (-x["qtd"], x["analista"]),
    )


def _gerar_excel_indicadores(data_inicio_str: Optional[str] = None, data_fim_str: Optional[str] = None,
                             equipe_filtro: Optional[str] = None) -> tuple:
    """Excel do PERÍODO da tela ("A partir de" / "Até") de todos os
    analistas dos Indicadores, com o filtro de equipe. Sem data, usa o mês
    atual (dia 1 até hoje), que era o único período até a 2.33.4.0. Três abas:
    'Tickets por Analista' (mesmo número do card Chamados por analista),
    'Tickets por Organização' (tickets distintos por organização e quem
    atendeu) e 'Detalhe por Ticket' (mesma aba da exportação do Perfil, com
    a Organização). Devolve (conteudo, nome_arquivo, erro)."""
    hoje = datetime.now().date()
    try:
        dt_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date() if data_inicio_str else hoje.replace(day=1)
        dt_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date() if data_fim_str else hoje
    except ValueError:
        return None, None, "Data inválida (use o formato AAAA-MM-DD)."
    if dt_fim < dt_inicio:
        return None, None, "Data final não pode ser antes da data inicial."
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return None, None, erro
    try:
        apontamentos = _apontamentos_da_equipe(conn, dt_inicio, dt_fim, equipe_filtro)
    except Exception as e:
        logger.exception("Erro ao buscar apontamentos pro Excel dos Indicadores")
        return None, None, f"Erro ao consultar a tabela apontamentos: {e}"
    finally:
        fechar_conexao(conn)

    por_analista = _contar_chamados_por_analista(apontamentos)
    detalhe = _montar_detalhe_apontamentos(apontamentos)

    organizacoes: dict = {}
    for d in detalhe:
        org = d.get("organizacao") or "(sem organização)"
        info = organizacoes.setdefault(org, {"tickets": set(), "analistas": set()})
        info["tickets"].add(d["ticket_id"])
        info["analistas"].add(d["analista"])
    df_org = pd.DataFrame(sorted(
        [{"Organização": org, "Qtd. Tickets": len(i["tickets"]), "Analistas": ", ".join(sorted(i["analistas"]))}
         for org, i in organizacoes.items()],
        key=lambda x: (-x["Qtd. Tickets"], x["Organização"]),
    ))
    df_analistas = pd.DataFrame([{"Analista": a["analista"], "Qtd. Tickets": a["qtd"]} for a in por_analista])
    df_detalhe, larguras_detalhe = _df_detalhe_ticket(detalhe)
    conteudo = _gerar_xlsx([
        (df_analistas, "Tickets por Analista", [30, 14]),
        (df_org, "Tickets por Organização", [40, 14, 80]),
        (df_detalhe, "Detalhe por Ticket", larguras_detalhe),
    ])
    sufixo_equipe = f"_{equipe_filtro.lower()}" if equipe_filtro else ""
    nome = f"indicadores_tickets{sufixo_equipe}_{dt_inicio:%Y-%m-%d}_a_{dt_fim:%Y-%m-%d}.xlsx"
    return conteudo, nome, None


def _consultar_indicadores_movidesk(data_inicio_str: str, data_fim_str: str = None, equipe_filtro: Optional[str] = None) -> dict:
    """Roda as 4 consultas de indicadores (sincronização, dúvidas abertas,
    dúvidas processadas, escalonamentos por marcador), todas filtradas
    entre `data_inicio_str` e `data_fim_str` (formato YYYY-MM-DD, vindo
    do filtro de data da página) - `data_fim_str` é opcional, se não
    vier assume "agora" (mantém compatível com quem só manda a data de
    início). Cada uma é INDEPENDENTE - se uma tabela tiver nome errado
    ou não existir (ou o resultado vier num formato inesperado), só
    aquela seção fica com erro, as outras continuam mostrando dado
    normal. Retorna um dict já pronto pra virar JSON, com "ok" geral (só
    False se nem conseguiu conectar) e um "ok" por seção.

    Também traz "chamados_por_analista" - contagem de tickets distintos
    por pessoa no período, a partir da MESMA tabela apontamentos que o
    card de Horas Trabalhadas usa (reaproveita a mesma conexão, sem
    precisar abrir uma segunda)."""
    try:
        dt_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"ok": False, "erro": "Data inválida (use o formato AAAA-MM-DD)."}

    if data_fim_str:
        try:
            dt_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return {"ok": False, "erro": "Data final inválida (use o formato AAAA-MM-DD)."}
    else:
        dt_fim = datetime.now().date()
    if dt_fim < dt_inicio:
        return {"ok": False, "erro": "Data final não pode ser antes da data inicial."}

    data_fim_exclusiva = (dt_fim + timedelta(days=1)).strftime("%Y-%m-%d")

    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}

    try:
        df_sinc, erro_sinc = _executar_consulta_indicador(
            conn, "Controle de Sincronização", "ControleSincronizacao",
            "SELECT nomeProcesso AS [Processo], ultimaExecucao AS [Última Execução], "
            "statusUltimaExecucao AS [Status], registrosAtualizados AS [Registros Atualizados], "
            "mensagemUltimaExecucao AS [Mensagem] FROM ControleSincronizacao",
        )

        df_duv_qtd, erro_duv_qtd = _executar_consulta_indicador(
            conn, "Dúvidas abertas", "Tickets",
            "SELECT COUNT(*) AS qtd FROM Tickets WHERE tags LIKE '%Dúvida%' "
            "AND createdDate >= ? AND createdDate < ?",
            (data_inicio_str, data_fim_exclusiva),
        )

        df_duv_proc, erro_duv_proc = _executar_consulta_indicador(
            conn, "Dúvidas processadas", "Movidesk_Duvidas_Processadas",
            "SELECT ticket_id AS [Ticket ID], cliente AS [Cliente], ticket_subject AS [Título], "
            "solicitado_por_nome AS [Solicitado Por], data_acao AS [Data Ação] "
            "FROM Movidesk_Duvidas_Processadas WHERE data_detectado >= ? AND data_detectado < ?",
            (data_inicio_str, data_fim_exclusiva),
        )

        # 3.3.1.0: o filtro de equipe valia só pros chamados por analista; as dúvidas processadas (e o "Top
        # solicitantes", montado delas na tela) vinham sempre de todo mundo. Agora fica só quem solicitou e é da equipe
        # (pelo vínculo do Movidesk, o mesmo critério das outras seções)
        if equipe_filtro and df_duv_proc is not None and not erro_duv_proc and not df_duv_proc.empty:
            mapa_equipe_duv = _mapa_atribuicao_por_nome_movidesk()
            df_duv_proc = df_duv_proc[df_duv_proc["Solicitado Por"].map(
                lambda nome: _pertence_a_equipe(mapa_equipe_duv.get(str(nome or "").strip().upper(), ""), equipe_filtro)
                if str(nome or "").strip().upper() in mapa_equipe_duv else False)]

        df_escal, erro_escal = _executar_consulta_indicador(
            conn, "Escalonamentos", "Movidesk_Escalonamentos_Processados",
            "SELECT COUNT(*) AS qtd, marcador_macro FROM Movidesk_Escalonamentos_Processados "
            "WHERE data_acao >= ? AND data_acao < ? GROUP BY marcador_macro ORDER BY COUNT(*) DESC",
            (data_inicio_str, data_fim_exclusiva),
        )

        chamados_por_analista = {"ok": True, "dados": []}
        try:
            apontamentos = _apontamentos_da_equipe(conn, dt_inicio, dt_fim, equipe_filtro)
            chamados_por_analista["dados"] = _contar_chamados_por_analista(apontamentos)
        except Exception as e:
            logger.exception("Erro ao calcular chamados por analista (apontamentos)")
            chamados_por_analista = {"ok": False, "erro": str(e)}

        return {
            "ok": True,
            "sincronizacao": _montar_secao_indicador(
                df_sinc, erro_sinc,
                lambda df: {"dados": df.fillna("").astype(str).to_dict("records")},
            ),
            "duvidas_abertas": _montar_secao_indicador(
                df_duv_qtd, erro_duv_qtd,
                lambda df: {"valor": int(df.iloc[0]["qtd"]) if not df.empty else 0},
            ),
            "duvidas_processadas": _montar_secao_indicador(
                df_duv_proc, erro_duv_proc,
                lambda df: {"dados": df.fillna("").astype(str).to_dict("records")},
            ),
            "escalonamentos": _montar_secao_indicador(
                df_escal, erro_escal,
                lambda df: {
                    "dados": [
                        {"marcador": r["marcador_macro"], "qtd": int(r["qtd"])}
                        for r in df.fillna("Sem marcador").to_dict("records")
                    ],
                },
            ),
            "chamados_por_analista": chamados_por_analista,
        }
    except Exception as e:
        logger.exception("Erro inesperado ao consultar indicadores Movidesk")
        return {"ok": False, "erro": f"Erro inesperado ao consultar o banco: {e}"}
    finally:
        fechar_conexao(conn)
