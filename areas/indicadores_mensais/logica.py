"""Indicadores Mensais - lógica (Avaliação de Efetividade e NOC Pendente, direto no banco do Movidesk).

Criado na 2.33.7.0. Mesmo banco dos Indicadores Movidesk/Horas Trabalhadas
(`_conectar_indicadores_movidesk`, tabelas Tickets e NOC). As consultas são as
que o Igor passou, só com o mês trocado por parâmetro; os updates mexem em uma
coluna de um registro por vez (sempre parametrizado, valor validado contra a
lista de opções aqui).
"""
import logging
import re
from datetime import date, datetime, timedelta
from typing import Optional

from core.db_utils import executar_query, fechar_conexao
from nucleo.movidesk import _conectar_indicadores_movidesk

logger = logging.getLogger("alertas.indicadores_mensais")  # log próprio, configurado no alertas_gui.py

# clientes que entram na Avaliação de Efetividade (Tickets.clientOrganizationBusinessName)
ORGANIZACOES_EFETIVIDADE = (
    "CLIENTE_L SA", "CLIENTE_J", "CLIENTE_J_", "HOTEL RENAISSANCE", "HOTELARIA ALBA (Geral Suporte)",
    "LOJAS CLIENTE_H", "LOUIS VUITTON BRASIL", "CLIENTE_R", "CLIENTE_Q", "SKECHERS DO BRASIL CALCADOS LTDA",
    "CLIENTE_G - Telefonia",
)
OPCOES_EFETIVIDADE = ("Sim", "Não")
OPCOES_JUSTIFICATIVA_NOC = (
    "Call com outro cliente do Suporte",
    "Chamado atendido dentro do prazo",
    "Não possui ninguém no horário",
    "Outros",
    "Sem justificativa",
)
# NOC: passou desse tempo de primeira resposta sem justificativa = pendente
LIMITE_PRIMEIRA_RESPOSTA_NOC_MIN = 30
# Avaliação de Efetividade (3.3.9.2, pedido do Igor): sempre os tickets resolvidos nos últimos N dias, não pelo mês da tela
DIAS_EFETIVIDADE = 30
# Considerar/Desconsiderar pesquisa de satisfação (Satisfacao2.considerar, VARCHAR(2))
TIMES_SATISFACAO = ("SUPORTE", "MONITORAMENTO", "SERVIÇOS")
SATISFACAO_AVALIADA = "Insatisfeito"
OPCOES_CONSIDERAR = {"S": "Considerar", "N": "Não considerar"}
# coluna da NOC com o número do ticket, se existir (minúsculas); senão vale o ID
COLUNAS_TICKET_NOC = ("ticketid", "ticket_id", "idticket", "id_ticket", "numero_ticket", "ticket")
# link do ticket no Movidesk (padrão do Movidesk; trocar aqui se o subdomínio for outro)
LINK_TICKET_MOVIDESK = "https://example.movidesk.com/Ticket/Edit/{id}"


def link_ticket(ticket_id) -> str:
    try:
        return LINK_TICKET_MOVIDESK.format(id=int(ticket_id))
    except (TypeError, ValueError):
        return ""


def periodo_do_mes(mes: Optional[str]) -> tuple:
    """'AAAA-MM' -> (primeiro dia do mês, primeiro dia do mês seguinte), como no
    BETWEEN '2026-09-01' AND '2026-10-01' das consultas. Sem mês (ou inválido):
    o mês atual (3.4.8.1, igual à tela; antes era o anterior)."""
    hoje = date.today()
    if mes and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", mes):
        ano, m = int(mes[:4]), int(mes[5:])
    else:
        ano, m = hoje.year, hoje.month
    inicio = date(ano, m, 1)
    fim = date(ano + 1, 1, 1) if m == 12 else date(ano, m + 1, 1)
    return inicio, fim


def _valor_json(valor):
    if isinstance(valor, (datetime, date)):
        return valor.strftime("%d/%m/%Y %H:%M") if isinstance(valor, datetime) else valor.strftime("%d/%m/%Y")
    if valor is None or isinstance(valor, (str, int, float, bool)):
        return valor
    return str(valor)


def _consultar(sql: str, params: tuple) -> tuple:
    """Devolve (linhas como dict com as colunas no nome original, erro)."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return [], erro
    try:
        linhas, colunas = executar_query(conn, sql, params=params, fetch=True, raise_on_error=True)
        vistos, nomes = set(), []
        for c in colunas:  # "SELECT x, *" repete a coluna x: fica só a primeira
            nomes.append(None if c.lower() in vistos else c)
            vistos.add(c.lower())
        return [{n: _valor_json(v) for n, v in zip(nomes, linha) if n} for linha in linhas], None
    except Exception as e:
        logger.exception("Erro na consulta dos Indicadores Mensais")
        return [], f"Erro ao consultar o banco: {e}"
    finally:
        fechar_conexao(conn)


def _campo(registro: dict, nome: str):
    """Coluna sem diferenciar maiúscula (o banco pode devolver ID, Id ou id)."""
    for chave, valor in registro.items():
        if chave.lower() == nome.lower():
            return valor
    return None


def listar_efetividade_pendente(mes: Optional[str] = None) -> dict:
    """Tickets do Monitoramento resolvidos nos últimos DIAS_EFETIVIDADE dias, dos clientes da avaliação, sem efetividade.
    3.3.9.2: o `mes` da tela não vale mais aqui (antes era o BETWEEN do mês escolhido); fica na assinatura pela rota."""
    desde = datetime.now() - timedelta(days=DIAS_EFETIVIDADE)
    marcadores = ", ".join("?" for _ in ORGANIZACOES_EFETIVIDADE)
    sql = (
        "SELECT clientOrganizationBusinessName, * FROM Tickets "
        "WHERE ownerTeam = 'MONITORAMENTO' "
        "AND resolvedIn >= ? "
        f"AND clientOrganizationBusinessName IN ({marcadores}) "
        "AND clientBusinessName NOT LIKE 'OA%' "
        "AND efetividadeOA IS NULL "
        # 3.3.1.0: saiu o "closedIn IS NOT NULL": o ticket só aparecia depois de fechado (dias depois de resolvido);
        # agora vem tudo o que foi resolvido no mês e ainda está sem avaliação
        "ORDER BY resolvedIn"
    )
    linhas, erro = _consultar(sql, (desde,) + ORGANIZACOES_EFETIVIDADE)
    if erro:
        return {"ok": False, "erro": erro}
    tickets = [{
        "id": _campo(r, "id"),
        "link": link_ticket(_campo(r, "id")),
        "organizacao": _campo(r, "clientOrganizationBusinessName") or "",
        "cliente": _campo(r, "clientBusinessName") or "",
        "assunto": _campo(r, "subject") or "",
        "responsavel": _campo(r, "ownerBusinessName") or _campo(r, "owner") or "",
        "categoria": _campo(r, "category") or "",
        "resolvido_em": _campo(r, "resolvedIn") or "",
        "fechado_em": _campo(r, "closedIn") or "",
    } for r in linhas]
    return {"ok": True, "dias": DIAS_EFETIVIDADE, "desde": desde.strftime("%d/%m/%Y %H:%M"), "tickets": tickets,
            "opcoes": list(OPCOES_EFETIVIDADE)}


def listar_noc_pendente(mes: Optional[str]) -> dict:
    inicio, fim = periodo_do_mes(mes)
    sql = (
        "SELECT * FROM NOC "
        "WHERE createdDate BETWEEN ? AND ? "
        "AND tempo_primeira_resposta_minutos > ? "
        "AND justificativa_noc IS NULL "
        "ORDER BY createdDate"
    )
    linhas, erro = _consultar(sql, (inicio, fim, LIMITE_PRIMEIRA_RESPOSTA_NOC_MIN))
    if erro:
        return {"ok": False, "erro": erro}
    registros = []
    # link do Movidesk (2.34.3.0): coluna de ticket se a NOC tiver uma; senão o ID,
    # que é o número do ticket do NOC
    colunas = {k.lower(): k for k in (linhas[0] if linhas else {})}
    coluna_ticket = next((colunas[c] for c in COLUNAS_TICKET_NOC if c in colunas), None)
    for r in linhas:
        # as colunas da NOC além dessas variam: vão todas em "detalhes" pra tela mostrar
        detalhes = {k: v for k, v in r.items()
                    if k.lower() not in ("id", "createddate", "tempo_primeira_resposta_minutos", "justificativa_noc")}
        ticket = r.get(coluna_ticket) if coluna_ticket else _campo(r, "id")
        registros.append({
            "id": _campo(r, "id"),
            "ticket": ticket,
            "link": link_ticket(ticket),
            "criado_em": _campo(r, "createdDate") or "",
            "tempo_minutos": _campo(r, "tempo_primeira_resposta_minutos"),
            "detalhes": detalhes,
        })
    return {"ok": True, "mes": inicio.strftime("%Y-%m"), "registros": registros,
            "opcoes": list(OPCOES_JUSTIFICATIVA_NOC), "limite_minutos": LIMITE_PRIMEIRA_RESPOSTA_NOC_MIN}


def listar_satisfacao(mes: Optional[str]) -> dict:
    """Pesquisas 'Insatisfeito' de tickets fechados no mês (Suporte, Monitoramento e
    Serviços), com o que já está marcado em considerar. Diferente das outras abas,
    a consulta não filtra só os pendentes: a tela mostra todos e filtra por status.
    Uma linha por ticket (o UPDATE é por ticketId, então mexe em todas as respostas
    dele de uma vez); `respostas` diz quantas linhas a Satisfacao2 tem pro ticket e
    `comentarios` junta a descrição da insatisfação (A.commentary) de cada uma.
    Colunas = as da consulta do Igor (2.34.1.0) + A.considerar, pro status."""
    inicio, fim = periodo_do_mes(mes)
    marcadores = ", ".join("?" for _ in TIMES_SATISFACAO)
    sql = (
        "SELECT B.id, B.ownerTeam, B.clientOrganizationBusinessName, B.subject, A.commentary, A.considerar "
        "FROM Satisfacao2 A "
        "LEFT JOIN Tickets B ON (A.ticketId = B.id) "
        "WHERE B.closedIn BETWEEN ? AND ? "
        f"AND ownerTeam IN ({marcadores}) "
        "AND satisfacao = ? "
        "ORDER BY B.closedIn"
    )
    linhas, erro = _consultar(sql, (inicio, fim) + TIMES_SATISFACAO + (SATISFACAO_AVALIADA,))
    if erro:
        return {"ok": False, "erro": erro}
    por_ticket = {}
    for r in linhas:
        ticket_id = _campo(r, "id")
        comentario = str(_campo(r, "commentary") or "").strip()
        if ticket_id in por_ticket:
            registro = por_ticket[ticket_id]
            registro["respostas"] += 1
            if comentario and comentario not in registro["comentarios"]:
                registro["comentarios"].append(comentario)
            continue
        considerar = (_campo(r, "considerar") or "").strip().upper()
        por_ticket[ticket_id] = {
            "id": ticket_id,
            "link": link_ticket(ticket_id),
            "considerar": considerar if considerar in OPCOES_CONSIDERAR else "",
            "organizacao": _campo(r, "clientOrganizationBusinessName") or "",
            "assunto": _campo(r, "subject") or "",
            "time": _campo(r, "ownerTeam") or "",
            "respostas": 1,
            "comentarios": [comentario] if comentario else [],
        }
    return {"ok": True, "mes": inicio.strftime("%Y-%m"), "tickets": list(por_ticket.values()),
            "opcoes": OPCOES_CONSIDERAR}


def _atualizar(tabela_coluna: str, valor: str, registro_id) -> dict:
    """UPDATE <tabela> SET <coluna> = ? WHERE <chave> = ? (tabela/coluna fixas no código).
    Efetividade e NOC mexem em exatamente 1 linha (ID único); a satisfação é por
    ticketId e pode ter mais de uma resposta pro mesmo ticket, então aceita várias."""
    try:
        registro_id = int(str(registro_id).strip())
    except (TypeError, ValueError):
        return {"ok": False, "erro": "ID inválido."}
    sql, varias_linhas = {
        "Tickets.efetividadeOA": ("UPDATE Tickets SET efetividadeOA = ? WHERE ID = ?", False),
        "NOC.justificativa_noc": ("UPDATE NOC SET justificativa_noc = ? WHERE ID = ?", False),
        "Satisfacao2.considerar": ("UPDATE Satisfacao2 SET considerar = ? WHERE ticketId = ?", True),
    }[tabela_coluna]
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (valor, registro_id))
        alteradas = cursor.rowcount
        if alteradas != 1 and not (varias_linhas and alteradas > 1):
            # 0 = ID não existe; mais de 1 nunca deveria acontecer (ID é único): desfaz por segurança
            conn.rollback()
            return {"ok": False, "erro": "Registro não encontrado." if alteradas == 0
                    else f"O update mexeria em {alteradas} registros; nada foi alterado."}
        conn.commit()
        return {"ok": True, "alteradas": alteradas}
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        logger.exception("Erro no update %s do ID %s", tabela_coluna, registro_id)
        return {"ok": False, "erro": f"Erro ao gravar no banco: {e}"}
    finally:
        fechar_conexao(conn)


def definir_efetividade(ticket_id, valor: str, quem: str) -> dict:
    if valor not in OPCOES_EFETIVIDADE:
        return {"ok": False, "erro": "Efetividade tem que ser Sim ou Não."}
    resultado = _atualizar("Tickets.efetividadeOA", valor, ticket_id)
    if resultado["ok"]:
        logger.info("Efetividade do ticket %s definida como '%s' por '%s'.", ticket_id, valor, quem)
    return resultado


def definir_considerar_satisfacao(ticket_id, valor: str, quem: str) -> dict:
    """S = considerar, N = não considerar (coluna VARCHAR(2))."""
    if valor not in OPCOES_CONSIDERAR:
        return {"ok": False, "erro": "Considerar tem que ser S ou N."}
    resultado = _atualizar("Satisfacao2.considerar", valor, ticket_id)
    if resultado["ok"]:
        logger.info("Pesquisa de satisfação do ticket %s marcada como '%s' (%s, %s linha(s)) por '%s'.",
                    ticket_id, valor, OPCOES_CONSIDERAR[valor], resultado["alteradas"], quem)
    return resultado


def definir_justificativa_noc(noc_id, valor: str, quem: str) -> dict:
    if valor not in OPCOES_JUSTIFICATIVA_NOC:
        return {"ok": False, "erro": "Justificativa fora da lista de opções."}
    resultado = _atualizar("NOC.justificativa_noc", valor, noc_id)
    if resultado["ok"]:
        logger.info("Justificativa do NOC %s definida como '%s' por '%s'.", noc_id, valor, quem)
    return resultado
