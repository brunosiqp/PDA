"""Horas Trabalhadas - lógica (apontamentos do Movidesk x meta, escala, feriados, férias e exportação em Excel).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import io
import json
import logging
import os
import unicodedata
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Optional

import pandas as pd

from areas.ferias.logica import FERIAS
from areas.ferias.logica import _lock_ferias
from areas.manutencao_usuarios.movidesk import _listar_usuarios_movidesk
from areas.manutencao_usuarios.movidesk import _nome_movidesk_vinculado
from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.equipes import _pertence_a_equipe, ATRIBUICAO_SERVICOS
from nucleo.movidesk import _conectar_indicadores_movidesk
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _carregar_escala_horas() -> dict:
    """Fonte da escala de cada pessoa pro cálculo de meta em Horas
    Trabalhadas. Prioridade: tabela 'usuarios' do banco movidesk (fonte
    principal agora - onde cargo, escala, horário e dias trabalhados
    ficam vinculados ao cadastro do PDA) e, pra quem não tiver escala
    preenchida lá (campo em branco/nulo), cai pro escala.json como
    reserva (mantém funcionando quem já estava configurado lá antes
    dessa mudança, sem precisar re-cadastrar tudo de novo na tabela).
    Se nem a consulta ao banco funcionar, usa só o escala.json mesmo -
    nunca quebra o resto da tela por causa disso."""
    escala_arquivo = {}
    caminho = os.path.join(_base_path_app(), "escala.json")
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                escala_arquivo = json.load(f)
        except Exception:
            logger.exception("Não foi possível ler escala.json")

    resultado_banco = _listar_usuarios_movidesk()
    if not resultado_banco.get("ok"):
        logger.warning("Não foi possível ler a tabela usuarios (banco movidesk) pra escala: %s. Usando só escala.json.", resultado_banco.get("erro"))
        return escala_arquivo

    escala_combinada = dict(escala_arquivo)
    for registro in resultado_banco["registros"]:
        nome = str(registro.get("nome") or "").strip().upper()
        escala_valor = registro.get("escala")
        if not nome or not escala_valor:
            continue
        escala_combinada[nome] = {"escala": escala_valor, "email": registro.get("email", "")}
    return escala_combinada


# Feriados nacionais fixos do Brasil (só os 10 federais, sem os pontos
# facultativos/estaduais/municipais tipo Carnaval e Corpus Christi, que
# variam por cidade/ano) - pesquisado em portarias oficiais/ANBIMA em
# 03/09/2026. Cobre só 2026 e 2027 por enquanto; precisa ser atualizado
# a cada virada de ano (datas móveis como Sexta-feira Santa mudam).
_FERIADOS_NACIONAIS_BR: dict = {
    date(2026, 1, 1): "Confraternização Universal",
    date(2026, 4, 3): "Paixão de Cristo",
    date(2026, 4, 21): "Tiradentes",
    date(2026, 5, 1): "Dia do Trabalho",
    date(2026, 9, 7): "Independência do Brasil",
    date(2026, 10, 12): "Nossa Senhora Aparecida",
    date(2026, 11, 2): "Finados",
    date(2026, 11, 15): "Proclamação da República",
    date(2026, 11, 20): "Consciência Negra",
    date(2026, 12, 25): "Natal",

    date(2027, 1, 1): "Confraternização Universal",
    date(2027, 3, 26): "Paixão de Cristo",
    date(2027, 4, 21): "Tiradentes",
    date(2027, 5, 1): "Dia do Trabalho",
    date(2027, 9, 7): "Independência do Brasil",
    date(2027, 10, 12): "Nossa Senhora Aparecida",
    date(2027, 11, 2): "Finados",
    date(2027, 11, 15): "Proclamação da República",
    date(2027, 11, 20): "Consciência Negra",
    date(2027, 12, 25): "Natal",
}


def _dias_excluidos_e_ausencias_periodo(dt_inicio: date, dt_fim: date) -> "tuple[set, dict, list]":
    """Pra excluir da META de horas trabalhadas os dias em que a pessoa
    não deveria ter trabalhado mesmo (feriado nacional, férias ou day
    off aprovado) - sem isso a meta calculada pelo calendário cheio
    penaliza injustamente quem tirou férias no período.

    Devolve (feriados_no_periodo, dias_ferias_por_analista, ausencias_periodo):
      - feriados_no_periodo: {date, date, ...} - vale pra TODO MUNDO,
        somado por fora ao calcular a meta de cada analista (ver
        _consultar_horas_trabalhadas).
      - dias_ferias_por_analista: {nome_movidesk: {date, date, ...}} -
        só férias/day off aprovados, só de quem tirou.
      - ausencias_periodo: lista pronta pra tarja de aviso na tela de
        Horas Trabalhadas - cada item já vem com nome de exibição e tipo
        ("feriado", "ferias" ou "day_off"), cortada pro período pedido.
    """
    feriados_no_periodo = {
        dia: nome for dia, nome in _FERIADOS_NACIONAIS_BR.items()
        if dt_inicio <= dia <= dt_fim
    }

    dias_ferias_por_analista: dict = {}
    ausencias_periodo: list = []

    for dia, nome_feriado in feriados_no_periodo.items():
        ausencias_periodo.append({
            "tipo": "feriado", "nome": nome_feriado,
            "inicio": dia.strftime("%d/%m/%Y"), "fim": dia.strftime("%d/%m/%Y"),
        })

    with _lock_ferias:
        registros_ferias = list(FERIAS)

    cache_nome_movidesk: dict = {}
    for registro in registros_ferias:
        try:
            ini_registro = datetime.strptime(registro["inicio"], "%Y-%m-%d").date()
            fim_registro = datetime.strptime(registro["fim"], "%Y-%m-%d").date()
        except (KeyError, ValueError, TypeError):
            continue
        # interseção entre o período do afastamento e o período pedido -
        # sem sobreposição, não afeta esse cálculo
        inicio_efetivo = max(ini_registro, dt_inicio)
        fim_efetivo = min(fim_registro, dt_fim)
        if inicio_efetivo > fim_efetivo:
            continue

        usuario_login = registro.get("usuario")
        tipo = registro.get("tipo") or "ferias"
        info_usuario = USUARIOS_WEB.get(usuario_login, {})
        nome_exibicao = info_usuario.get("nome") or usuario_login
        ausencias_periodo.append({
            "tipo": tipo, "nome": nome_exibicao,
            "inicio": inicio_efetivo.strftime("%d/%m/%Y"), "fim": fim_efetivo.strftime("%d/%m/%Y"),
        })

        if usuario_login not in cache_nome_movidesk:
            nome_movidesk, _erro = _nome_movidesk_vinculado(usuario_login)
            cache_nome_movidesk[usuario_login] = nome_movidesk
        nome_movidesk = cache_nome_movidesk[usuario_login]
        if not nome_movidesk:
            # sem vínculo com o Movidesk - não tem meta calculada mesmo,
            # não tem o que excluir
            continue

        dias_pessoa = dias_ferias_por_analista.setdefault(nome_movidesk, set())
        dia_atual = inicio_efetivo
        while dia_atual <= fim_efetivo:
            dias_pessoa.add(dia_atual)
            dia_atual += timedelta(days=1)

    ausencias_periodo.sort(key=lambda a: (a["inicio"], a["nome"]))
    return set(feriados_no_periodo.keys()), dias_ferias_por_analista, ausencias_periodo


def _minutos_para_horas_str(minutos: float) -> str:
    minutos = int(minutos)
    if minutos <= 0:
        return "00:00"
    h, m = divmod(minutos, 60)
    return f"{h:02d}:{m:02d}"


def _calcular_meta_dia_especifico(tipo_escala: str, data_analise: date) -> float:
    """Meta de minutos trabalhados nesse dia, de acordo com o tipo de
    escala - mesma lógica do relatorio_horas.py original pro 6x1,
    ESTAGIO e ESCALA_ARA. O 5x2 conta todo dia útil (segunda a sexta)
    como meta cheia - fim de semana sem meta.

    O 12x36 é diferente dos outros: como esse turno é noturno (18h às
    06h), a meta é uma quantidade FIXA de 6h em qualquer dia que teve
    algum chamado respondido - não varia por dia da semana nem alterna
    entre dias (isso foi corrigido a pedido do Igor - a versão anterior
    tentava simular uma alternância 12h/0h por dia, que não representa
    como esse turno funciona de verdade)."""
    dia_semana = data_analise.weekday()  # 0=segunda ... 6=domingo
    if tipo_escala == "6x1":
        if dia_semana == 5:
            return 7.5 * 60
        elif dia_semana == 6:
            return 0
        else:
            return 6.5 * 60
    elif tipo_escala == "ESTAGIO":
        return 0 if dia_semana >= 5 else 6 * 60
    elif tipo_escala == "ESCALA_ARA":
        return 0 if dia_semana in (0, 1) else 7 * 60
    elif tipo_escala == "12x36":
        return 6 * 60
    else:  # 5x2 (padrão, inclusive pra quem não está cadastrado no escala.json)
        return 0 if dia_semana >= 5 else 8 * 60


def _calcular_meta_periodo(tipo_escala: str, dt_inicio: date, dt_fim: date, dias_com_atividade: set, dias_excluidos: Optional[set] = None) -> float:
    """Soma a meta do PERÍODO INTEIRO (todo dia do calendário dentro do
    intervalo pedido, não só os dias em que a pessoa tem apontamento) -
    pedido explícito do Igor: usar como métrica só os dias com registro
    faz a meta encolher artificialmente pra quem trabalhou menos dias no
    período (a meta precisa refletir o que a pessoa DEVERIA ter
    trabalhado segundo a escala dela, não só os dias em que ela mexeu
    em algo).

    `dias_excluidos` (opcional): dias que não entram na meta mesmo sendo
    dia útil pela escala - feriado nacional, férias ou day off aprovado
    (ver _dias_excluidos_e_ausencias_periodo). Sem isso, tirar férias
    reduziria as horas trabalhadas SEM reduzir a meta, punindo a pessoa
    duas vezes.

    EXCEÇÃO: 12x36 continua diferente - esse turno alterna trabalho/folga
    de um jeito que não segue um padrão fixo de dia da semana (não tem
    como o sistema prever quais dias são de trabalho ou folga sem uma
    escala de turno cadastrada), então pra essa escala a meta continua
    sendo calculada só nos dias em que a pessoa teve QUALQUER
    apontamento (6h fixo por dia ativo) - comportamento já era assim
    antes dessa correção e continua sendo o certo pra esse caso (e não
    faz sentido excluir dia de férias/feriado dela tampouco, já que a
    meta nem olha o calendário nesse caso)."""
    if tipo_escala == "12x36":
        return len(dias_com_atividade) * 6 * 60
    dias_excluidos = dias_excluidos or set()
    total = 0.0
    dia_atual = dt_inicio
    while dia_atual <= dt_fim:
        if dia_atual not in dias_excluidos:
            total += _calcular_meta_dia_especifico(tipo_escala, dia_atual)
        dia_atual += timedelta(days=1)
    return total


def _buscar_apontamentos_movidesk(conn, dt_inicio: date, dt_fim: date) -> list:
    """Busca os apontamentos direto da tabela 'apontamentos' (banco
    'movidesk', mesma conexão/servidor já usados por Indicadores
    Movidesk - confirmado com o Igor que é a mesma instância
    192.0.2.201\\INSTANCIA_HML, mesmo usuário serve pras duas bases) - troca
    a antiga busca via API do Movidesk por uma consulta direta ao banco.

    Só traz linhas com periodStart/periodEnd preenchidos: sem isso não
    dá pra saber QUANDO o apontamento aconteceu, então não tem como
    contar - mesmo comportamento de antes (a busca via API também
    pulava apontamentos sem período, mesmo que tivessem workTime
    preenchido)."""
    str_ini = dt_inicio.strftime("%Y-%m-%d 00:00:00")
    str_fim = (dt_fim + timedelta(days=1)).strftime("%Y-%m-%d 00:00:00")
    linhas, colunas = executar_query(
        conn,
        "SELECT id, createdByName, periodStart, periodEnd FROM apontamentos "
        "WHERE periodStart IS NOT NULL AND periodEnd IS NOT NULL "
        "AND periodStart >= ? AND periodStart < ?",
        params=(str_ini, str_fim),
        fetch=True,
        raise_on_error=True,
    )
    colunas_lower = [c.lower() for c in colunas]
    return [dict(zip(colunas_lower, linha)) for linha in linhas]


def _contar_tickets_acao_total(nome_movidesk: str) -> dict:
    """Conta quantos tickets DISTINTOS a pessoa já teve algum apontamento
    (ação) - DESDE SEMPRE, sem filtro de período, diferente do card de
    Horas Trabalhadas (que sempre olha só um período. Também traz a
    data do primeiro apontamento registrado, e o TOTAL DE HORAS
    trabalhadas desde sempre (soma bruta de todos os apontamentos, SEM
    a deduplicação por minuto que o resumo mensal faz - pedido explícito
    do Igor: quando 1 hora foi registrada em 2 chamados ao mesmo tempo,
    aqui conta as duas vezes mesmo, porque senão precisaria buscar e
    processar TODOS os apontamentos de todo o histórico da pessoa em vez
    de só somar direto no banco, o que ficaria bem mais pesado). Usado
    nos indicadores gerais do Perfil. Devolve {"ok": True,
    "total_tickets": int, "primeira_atividade": str|None,
    "total_horas": str|None} ou {"ok": False, "erro": str}."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT COUNT(DISTINCT id) AS total, MIN(periodStart) AS primeira, "
            "SUM(DATEDIFF(minute, periodStart, periodEnd)) AS total_minutos "
            "FROM apontamentos WHERE createdByName = ? "
            "AND periodStart IS NOT NULL AND periodEnd IS NOT NULL",
            params=(nome_movidesk,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": True, "total_tickets": 0, "primeira_atividade": None, "total_horas": None}
        colunas_lower = [c.lower() for c in colunas]
        linha = dict(zip(colunas_lower, linhas[0]))
        primeira = linha.get("primeira")
        if isinstance(primeira, str):
            try:
                primeira = datetime.fromisoformat(primeira)
            except ValueError:
                primeira = None
        total_minutos = linha.get("total_minutos")
        return {
            "ok": True,
            "total_tickets": int(linha.get("total") or 0),
            "primeira_atividade": primeira.strftime("%d/%m/%Y") if primeira else None,
            "total_horas": _minutos_para_horas_str(total_minutos) if total_minutos else None,
        }
    except Exception as e:
        logger.exception("Erro ao contar tickets com ação (desde sempre) pra %s", nome_movidesk)
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _processar_apontamentos_movidesk(apontamentos: list, dt_inicio: date, dt_fim: date, escala_dict: dict) -> list:
    """Mesma lógica de deduplicação por minuto que a versão antiga (via
    API) já fazia - evita contar 2x um apontamento sobreposto pro mesmo
    analista no mesmo dia. periodStart/periodEnd agora vêm como
    datetime completo (data + hora) direto da tabela, em vez de só
    "HH:MM" vindo da API - a data de cada linha é extraída do próprio
    periodStart."""
    minutos_marcados: dict = {}   # {(analista, data_str): set(minutos)}
    por_analista_dia: dict = {}   # {(analista, data_str): {"minutos": int, "tickets": set()}}

    for row in apontamentos:
        analista = str(row.get("createdbyname") or "").strip().upper()
        if not analista:
            continue

        periodo_ini = row.get("periodstart")
        periodo_fim = row.get("periodend")
        if periodo_ini is None or periodo_fim is None:
            continue

        # periodStart/periodEnd podem vir como datetime (pyodbc lê coluna
        # DATETIME assim nativamente) ou como string ISO, dependendo do
        # driver/tipo exato da coluna - normaliza os dois casos
        if isinstance(periodo_ini, str):
            try:
                periodo_ini = datetime.fromisoformat(periodo_ini)
            except ValueError:
                continue
        if isinstance(periodo_fim, str):
            try:
                periodo_fim = datetime.fromisoformat(periodo_fim)
            except ValueError:
                continue

        data_app = periodo_ini.date()
        if not (dt_inicio <= data_app <= dt_fim):
            continue

        ini_minuto = periodo_ini.hour * 60 + periodo_ini.minute
        fim_minuto = periodo_fim.hour * 60 + periodo_fim.minute
        if fim_minuto <= ini_minuto:
            # atravessou a meia-noite, ou dado inconsistente no banco -
            # ignora esse caso raro em vez de arriscar contar minutos
            # errados (negativos ou de outro dia)
            continue

        data_str = data_app.strftime("%Y-%m-%d")
        chave = (analista, data_str)
        minutos_marcados.setdefault(chave, set())
        por_analista_dia.setdefault(chave, {"minutos": 0, "tickets": set()})

        for m in range(ini_minuto, fim_minuto):
            if m not in minutos_marcados[chave]:
                minutos_marcados[chave].add(m)
                por_analista_dia[chave]["minutos"] += 1
        if row.get("id") is not None:
            por_analista_dia[chave]["tickets"].add(row.get("id"))

    linhas = []
    for (analista, data_str), info in por_analista_dia.items():
        dados_escala = escala_dict.get(analista)
        tipo_escala = dados_escala.get("escala") if isinstance(dados_escala, dict) else None
        if not tipo_escala:
            tipo_escala = "5x2"
        data_obj = datetime.strptime(data_str, "%Y-%m-%d").date()
        meta_minutos = _calcular_meta_dia_especifico(tipo_escala, data_obj)
        linhas.append({
            "analista": analista,
            "data": data_obj.strftime("%d/%m/%Y"),
            "data_iso": data_str,
            "escala": tipo_escala,
            "cadastrado_na_escala": isinstance(dados_escala, dict),
            "minutos_trabalhados": info["minutos"],
            "horas_trabalhadas": _minutos_para_horas_str(info["minutos"]),
            "meta_horas": _minutos_para_horas_str(meta_minutos),
            "percentual": round(info["minutos"] / meta_minutos * 100, 1) if meta_minutos > 0 else None,
            "qtd_tickets": len(info["tickets"]),
        })
    linhas.sort(key=lambda r: (r["analista"], r["data_iso"]))
    return linhas


def _mapa_atribuicao_por_nome_movidesk() -> dict:
    """{NOME_MOVIDESK_MAIÚSCULO: atribuicao} - pra filtrar Horas
    Trabalhadas por equipe (Suporte/Monitoramento). Só cobre quem tem
    vínculo com o Movidesk (usuario_movidesk_id) - sem vínculo não tem
    como saber qual nome do apontamento corresponde a qual login, então
    essa pessoa simplesmente não entra no filtro por equipe (mas
    continua aparecendo normalmente quando o filtro é "Todos")."""
    vinculos = {
        info.get("usuario_movidesk_id"): info.get("atribuicao") or "Suporte"
        for info in USUARIOS_WEB.values()
        if info.get("usuario_movidesk_id")
    }
    if not vinculos:
        return {}
    resultado = _listar_usuarios_movidesk()
    if not resultado.get("ok"):
        return {}
    return {
        str(r.get("nome") or "").strip().upper(): vinculos[r["id"]]
        for r in resultado["registros"]
        if r.get("id") in vinculos
    }


def _nomes_bloqueados_por_desativacao() -> set:
    """Nomes (em maiúsculo) que devem ficar de fora do cálculo de Horas
    Trabalhadas por terem o login do PDA desativado. Só bloqueia quem
    está DESATIVADO *e* vinculado a um registro da tabela usuarios
    (banco movidesk) - sem vínculo não tem como saber qual nome
    corresponde a esse login, então não tem o que bloquear."""
    ids_bloqueados = {
        info.get("usuario_movidesk_id")
        for info in USUARIOS_WEB.values()
        if not info.get("ativo", True) and info.get("usuario_movidesk_id")
    }
    if not ids_bloqueados:
        return set()
    resultado = _listar_usuarios_movidesk()
    if not resultado.get("ok"):
        # não consegue confirmar quem bloquear - mais seguro não bloquear
        # ninguém do que arriscar esconder gente que na verdade está ativa
        return set()
    return {
        str(r.get("nome") or "").strip().upper()
        for r in resultado["registros"]
        if r.get("id") in ids_bloqueados
    }


# Gerência (3.1.3.1, pedido do Igor): nunca entra no cálculo de horas (Horas Trabalhadas, perfil e números
# da equipe no início). (login no PDA, nome): o nome do apontamento bate pelo vínculo do Movidesk do login
# ou, sem vínculo, por ter todas as palavras do nome (sem acento, em qualquer ordem).
FORA_DO_CALCULO_DE_HORAS = (
    ("eduardo", "Eduardo Yamada"),
    ("toledo", "Sabrina Barros"),
    ("sergio.henriques", "Sergio Henriques"),
)


def _palavras_nome(nome: str) -> set:
    sem_acento = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode()
    return set(sem_acento.upper().split())


def _fora_do_calculo_de_horas() -> list:
    """(login, nome) de quem não entra no cálculo de horas: a gerência fixa e, desde a 3.2.5.0, todo mundo da
    equipe Serviços (atribuicao no usuarios.json), que não tem meta nem escala no PDA."""
    lista = list(FORA_DO_CALCULO_DE_HORAS)
    for login, info in USUARIOS_WEB.items():
        if (info.get("atribuicao") or "") == ATRIBUICAO_SERVICOS:
            # sem vínculo, o nome só serve se for completo (nome e sobrenome): só o primeiro nome pegaria outras pessoas
            nome = info.get("nome") or ""
            lista.append((login, nome if len(_palavras_nome(nome)) >= 2 else ""))
    return lista


def _filtro_fora_do_calculo_de_horas():
    """Função que diz se um nome de apontamento (createdbyname) é de alguém de _fora_do_calculo_de_horas()."""
    return filtro_por_pessoas(_fora_do_calculo_de_horas())


def filtro_por_pessoas(fora_lista) -> "callable":
    """Função que diz se um nome de apontamento (createdbyname) é de alguém de `fora_lista` [(login, nome)]: pelo nome
    do vínculo do Movidesk do login ou, sem vínculo, por ter todas as palavras do nome (3.2.6.1: usada também pra
    tirar pessoas só do percentual da equipe na Comunidade)."""
    nomes_vinculados = set()
    ids = {(USUARIOS_WEB.get(login) or {}).get("usuario_movidesk_id") for login, _ in fora_lista} - {None, ""}
    if ids:
        resultado = _listar_usuarios_movidesk()
        if resultado.get("ok"):
            nomes_vinculados = {str(r.get("nome") or "").strip().upper() for r in resultado["registros"] if r.get("id") in ids}
    palavras = [_palavras_nome(nome) for _, nome in fora_lista]

    def fora(nome_apontamento: str) -> bool:
        nome = str(nome_apontamento or "").strip()
        if nome.upper() in nomes_vinculados:
            return True
        do_apontamento = _palavras_nome(nome)
        return any(p and p <= do_apontamento for p in palavras)
    return fora


def _buscar_dados_tickets(ticket_ids: list) -> dict:
    """Busca título (`subject`) e as colunas de COLUNAS_OPCIONAIS_TICKETS
    (organização, cliente, categoria) de uma lista de tickets na tabela
    Tickets, pra enriquecer a exportação em Excel. Conexão PRÓPRIA e só sob
    demanda (só quando alguém exporta) - o resumo da tela não precisa disso.
    Devolve {ticket_id: {"titulo", "organizacao", "cliente", "categoria"}};
    ticket não encontrado não entra no dict (fica em branco na planilha). Se
    alguma coluna opcional der erro no banco, descobre qual testando uma por
    uma e consulta sem ela: a exportação sempre sai, só com aquela em branco."""
    ids_validos = sorted({int(i) for i in ticket_ids if i is not None})
    if not ids_validos:
        return {}
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        logger.warning("Não foi possível buscar os dados dos tickets pra exportação: %s", erro)
        return {}
    montar_sql = lambda colunas: ", ".join(["id", "subject"] + colunas)
    todas = [coluna for coluna, _ in COLUNAS_OPCIONAIS_TICKETS]
    try:
        try:
            return _consultar_tickets_em_lotes(conn, ids_validos, montar_sql(todas))
        except Exception:
            logger.warning("Consulta em Tickets com todas as colunas deu erro - conferindo uma por uma")
        validas = []
        for coluna in todas:
            try:  # 1 ticket só: só pra saber se a coluna existe
                _consultar_tickets_em_lotes(conn, ids_validos[:1], montar_sql([coluna]))
                validas.append(coluna)
            except Exception:
                logger.warning("Tickets.%s deu erro - exportando com essa coluna em branco", coluna)
        return _consultar_tickets_em_lotes(conn, ids_validos, montar_sql(validas))
    except Exception:
        logger.exception("Erro ao buscar os dados dos tickets (Tickets) pra exportação")
        return {}
    finally:
        fechar_conexao(conn)


# colunas da tabela Tickets que entram no Detalhe por Ticket além do título: (coluna no banco, chave no detalhe)
COLUNAS_OPCIONAIS_TICKETS = (
    ("clientOrganizationBusinessName", "organizacao"), ("clientBusinessName", "cliente"), ("category", "categoria"),
)


def _consultar_tickets_em_lotes(conn, ids_validos: list, colunas_sql: str) -> dict:
    """Em lotes de 1000 IDs - evita estourar o limite de parâmetros de uma
    query parametrizada (um mês inteiro pode ter milhares de tickets)."""
    dados = {}
    TAMANHO_LOTE = 1000
    for inicio in range(0, len(ids_validos), TAMANHO_LOTE):
        lote = ids_validos[inicio:inicio + TAMANHO_LOTE]
        placeholders = ",".join("?" for _ in lote)
        linhas, colunas = executar_query(
            conn, f"SELECT {colunas_sql} FROM Tickets WHERE id IN ({placeholders})",
            params=tuple(lote), fetch=True, raise_on_error=True,
        )
        colunas_lower = [c.lower() for c in colunas]
        for linha in linhas:
            registro = dict(zip(colunas_lower, linha))
            dados[int(registro["id"])] = {
                "titulo": registro.get("subject") or "",
                **{chave: registro.get(coluna.lower()) or "" for coluna, chave in COLUNAS_OPCIONAIS_TICKETS},
            }
    return dados


def _montar_detalhe_apontamentos(apontamentos: list) -> list:
    """Um apontamento por linha (sem o agrupamento/deduplicação por minuto
    do resumo), com título e organização do ticket - usado pelas exportações
    em Excel (Perfil, Horas Trabalhadas e Indicadores)."""
    detalhe = []
    for row in apontamentos:
        analista = str(row.get("createdbyname") or "").strip().upper()
        periodo_ini = row.get("periodstart")
        periodo_fim = row.get("periodend")
        if not analista or periodo_ini is None or periodo_fim is None:
            continue
        if isinstance(periodo_ini, str):
            try:
                periodo_ini = datetime.fromisoformat(periodo_ini)
            except ValueError:
                continue
        if isinstance(periodo_fim, str):
            try:
                periodo_fim = datetime.fromisoformat(periodo_fim)
            except ValueError:
                continue
        duracao_minutos = int((periodo_fim - periodo_ini).total_seconds() // 60)
        detalhe.append({
            "analista": analista,
            "ticket_id": row.get("id"),
            "data": periodo_ini.strftime("%d/%m/%Y"),
            "data_iso": periodo_ini.strftime("%Y-%m-%d"),
            "inicio": periodo_ini.strftime("%H:%M"),
            "fim": periodo_fim.strftime("%H:%M"),
            "duracao_minutos": duracao_minutos,
            "duracao": _minutos_para_horas_str(max(duracao_minutos, 0)),
        })
    detalhe.sort(key=lambda d: (d["analista"], d["data_iso"], d["inicio"]))

    # título e organização - busca em lote, uma vez pra todos os IDs
    # distintos do período, em vez de uma query por linha
    dados_por_ticket = _buscar_dados_tickets([d["ticket_id"] for d in detalhe])
    for d in detalhe:
        dados_ticket = dados_por_ticket.get(d["ticket_id"], {})
        d["titulo"] = dados_ticket.get("titulo", "")
        d["organizacao"] = dados_ticket.get("organizacao", "")
        d["cliente"] = dados_ticket.get("cliente", "")
        d["categoria"] = dados_ticket.get("categoria", "")
    return detalhe


def _consultar_horas_trabalhadas(
    data_inicio_str: str, data_fim_str: str, incluir_detalhe: bool = False, equipe_filtro: Optional[str] = None,
) -> dict:
    try:
        dt_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        dt_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"ok": False, "erro": "Data inválida."}
    if dt_fim < dt_inicio:
        return {"ok": False, "erro": "Data final não pode ser antes da data inicial."}

    escala_dict = _carregar_escala_horas()

    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        apontamentos = _buscar_apontamentos_movidesk(conn, dt_inicio, dt_fim)
    except Exception as e:
        logger.exception("Erro ao buscar apontamentos no banco pra horas trabalhadas")
        return {"ok": False, "erro": f"Erro ao consultar a tabela apontamentos: {e}"}
    finally:
        fechar_conexao(conn)

    nomes_bloqueados = _nomes_bloqueados_por_desativacao()
    if nomes_bloqueados:
        apontamentos = [
            a for a in apontamentos
            if str(a.get("createdbyname") or "").strip().upper() not in nomes_bloqueados
        ]
    fora_do_calculo = _filtro_fora_do_calculo_de_horas()  # gerência (3.1.3.1) e equipe Serviços (3.2.5.0)
    apontamentos = [a for a in apontamentos if not fora_do_calculo(a.get("createdbyname"))]

    # Filtro por equipe (Suporte/Monitoramento) - OPCIONAL. Quem tem
    # atribuição "Suporte e Monitoramento" (ex.: escala 12x36) aparece
    # nos dois filtros. Sem vínculo Movidesk conhecido, a pessoa só
    # aparece quando o filtro é "Todos" (equipe_filtro vazio/None).
    if equipe_filtro:
        mapa_equipe = _mapa_atribuicao_por_nome_movidesk()
        def _pertence_apontamento(a):
            nome = str(a.get("createdbyname") or "").strip().upper()
            return nome in mapa_equipe and _pertence_a_equipe(mapa_equipe[nome], equipe_filtro)
        apontamentos = [a for a in apontamentos if _pertence_apontamento(a)]

    try:
        linhas = _processar_apontamentos_movidesk(apontamentos, dt_inicio, dt_fim, escala_dict)
    except Exception as e:
        logger.exception("Erro ao processar horas trabalhadas")
        return {"ok": False, "erro": f"Erro ao processar os dados: {e}"}

    # detalhe por ticket individual (um apontamento por linha, sem o
    # agrupamento/deduplicação por minuto que "linhas" faz) - só monta se
    # pedido, usado pela exportação em Excel pra validação linha a linha.
    # Reaproveita a mesma lista "apontamentos" já buscada acima, sem
    # round-trip extra no banco.
    detalhe = _montar_detalhe_apontamentos(apontamentos) if incluir_detalhe else None

    # meta calculada pelo CALENDÁRIO do período pedido, não só pelos dias
    # em que cada pessoa tem apontamento (ver _calcular_meta_periodo pro
    # motivo) - MAS nunca além de HOJE: se o período pedido inclui dias
    # futuros (ex.: "mês inteiro" de um mês que ainda não terminou), esses
    # dias que ainda não aconteceram não podem entrar na meta - ninguém
    # pode ter "trabalhado" um dia que ainda não chegou. Sem esse limite,
    # pedir o mês de agosto inteiro no dia 13 contava a meta até dia 31,
    # inflando a meta muito além do que faz sentido nesse ponto do mês.
    dt_fim_para_meta = min(dt_fim, datetime.now().date())

    dias_com_atividade_por_analista: dict = {}
    for linha in linhas:
        dias_com_atividade_por_analista.setdefault(linha["analista"], set()).add(linha["data_iso"])

    # feriados nacionais + férias/day off aprovados no período não contam
    # pra meta de ninguém (feriado é geral, férias/day off só de quem
    # tirou) - ver _dias_excluidos_e_ausencias_periodo. "ausencias" vai
    # junto na resposta pra alimentar a tarja de aviso na tela.
    feriados_periodo, dias_ferias_por_analista, ausencias_periodo = _dias_excluidos_e_ausencias_periodo(
        dt_inicio, dt_fim_para_meta
    )

    meta_periodo_por_analista = {}
    for analista, dias_ativos in dias_com_atividade_por_analista.items():
        dados_escala = escala_dict.get(analista)
        tipo_escala = dados_escala.get("escala") if isinstance(dados_escala, dict) else None
        if not tipo_escala:
            tipo_escala = "5x2"
        dias_excluidos_analista = feriados_periodo | dias_ferias_por_analista.get(analista, set())
        meta_periodo_por_analista[analista] = _calcular_meta_periodo(
            tipo_escala, dt_inicio, dt_fim_para_meta, dias_ativos, dias_excluidos_analista
        )

    return {
        "ok": True, "linhas": linhas, "total_tickets_periodo": len(apontamentos),
        "meta_periodo_por_analista": meta_periodo_por_analista,
        "ausencias_periodo": ausencias_periodo,
        **({"detalhe": detalhe} if incluir_detalhe else {}),
    }


COLUNAS_DETALHE_TICKET = (  # (cabeçalho, chave no detalhe, largura) - mesma aba nas 3 exportações
    ("Analista", "analista", 22), ("Data", "data", 12), ("Ticket ID", "ticket_id", 12),
    ("Organização", "organizacao", 32), ("Cliente", "cliente", 32), ("Categoria", "categoria", 22),
    ("Início", "inicio", 10), ("Fim", "fim", 10),
    ("Duração", "duracao", 12), ("Título do Ticket", "titulo", 60),
)


def _df_detalhe_ticket(detalhe: list):
    """Aba 'Detalhe por Ticket' (Perfil, Horas Trabalhadas e Indicadores)."""
    return pd.DataFrame([{cab: d.get(chave, "") for cab, chave, _ in COLUNAS_DETALHE_TICKET} for d in detalhe]), \
        [largura for _, _, largura in COLUNAS_DETALHE_TICKET]


def _gerar_xlsx(abas: list) -> bytes:
    """Monta um .xlsx com as abas (dataframe, nome, larguras) na formatação
    padrão das exportações do PDA (cabeçalho colorido, largura de coluna,
    topo congelado, autofiltro). Aba vazia vira um aviso."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book
        formato_cabecalho = workbook.add_format({
            "bold": True, "font_color": "#ffffff", "bg_color": "#2db8cf",
            "align": "left", "valign": "vcenter", "font_size": 10, "border": 0,
        })
        for df, nome_aba, larguras in abas:
            if df.empty:
                df = pd.DataFrame([{"Aviso": "Nenhum registro encontrado no período selecionado."}])
                df.to_excel(writer, sheet_name=nome_aba, index=False)
                ws = writer.sheets[nome_aba]
                ws.write(0, 0, "Aviso", formato_cabecalho)
                ws.set_column(0, 0, 50)
                continue
            df.to_excel(writer, sheet_name=nome_aba, index=False)
            ws = writer.sheets[nome_aba]
            for col_num, nome_coluna in enumerate(df.columns):
                ws.write(0, col_num, nome_coluna, formato_cabecalho)
            for col_num, largura in enumerate(larguras[:len(df.columns)]):
                ws.set_column(col_num, col_num, largura)
            ws.freeze_panes(1, 0)
            ws.autofilter(0, 0, len(df), len(df.columns) - 1)
    return buffer.getvalue()


def _gerar_excel_export_horas(linhas_resumo: list, detalhe: list) -> bytes:
    """Gera o .xlsx de exportação de Horas Trabalhadas - usado tanto pela
    página Horas Trabalhadas (período com todo mundo) quanto pelo Perfil
    (uma pessoa só). Duas abas: 'Resumo Diário' (mesmo agregado por dia das
    telas) e 'Detalhe por Ticket' (cada apontamento, sem a deduplicação por
    minuto do resumo, pra validar linha a linha), com a organização
    (Tickets.clientOrganizationBusinessName), o cliente (Tickets.clientBusinessName)
    e o título do ticket (Tickets.subject)."""
    df_resumo = pd.DataFrame([{
        "Analista": l["analista"], "Data": l["data"], "Escala": l["escala"],
        "Horas Trabalhadas": l["horas_trabalhadas"], "Meta": l["meta_horas"],
        "%": l["percentual"], "Qtd. Tickets": l["qtd_tickets"],
    } for l in linhas_resumo])
    df_detalhe, larguras_detalhe = _df_detalhe_ticket(detalhe)
    return _gerar_xlsx([
        (df_resumo, "Resumo Diário", [22, 12, 10, 16, 12, 8, 12]),
        (df_detalhe, "Detalhe por Ticket", larguras_detalhe),
    ])
