"""Serviços (3.3.1.0) - lógica do Calendário de GMUD's.

Desde a 3.3.4.0 as GMUDs vêm do banco do Movidesk (o mesmo dos Indicadores Movidesk), tabela `gmud`, sempre com
`ownerTeam = 'SERVIÇOS'`. O agendamento sai de `dataHoraInicioGmud` e `dataHoraFimGmud` (datetime, ex.
2026-10-07 14:00:00.000; o fim pode ser em outro dia e a tela desenha a GMUD em todos os dias que ela atravessa).

As outras colunas da tabela não foram passadas, então a consulta é `SELECT *` e cada campo da tela é procurado por
uma lista de nomes prováveis (`CANDIDATAS`, sem diferenciar maiúscula): o que não existir fica em branco, sem erro.
As colunas que a tabela tem vão pro log principal uma vez por partida, pra ajustar a lista se algum campo vier
vazio (a resposta também diz quais campos não acharam coluna, em `faltando`). Cada GMUD devolvida:
{id, titulo, cliente, agendada_para: "AAAA-MM-DD HH:MM", termina_em: "AAAA-MM-DD HH:MM", prazo_sla (slaSolutionDate),
 fim_demanda (dataFimDemanda, 3.3.7.1), status
 (agendada|aprovacao|execucao|concluida|cancelada), responsaveis: [login do PDA], responsavel_nome, link}.
"""
import logging
import re
import unicodedata
from datetime import date, datetime, timedelta

from nucleo.equipes import ATRIBUICAO_SERVICOS
from nucleo.fotos import _caminho_foto_usuario
from nucleo.movidesk import _conectar_indicadores_movidesk
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

EQUIPE_GMUD = "SERVIÇOS"
LINK_TICKET_MOVIDESK = "https://example.movidesk.com/Ticket/Edit/{id}"
MESES_ANTES, MESES_DEPOIS = 6, 6  # janela consultada em volta de hoje (o calendário navega por mês)
LIMITE_LINHAS = 3000
DIAS_SLA_PRA_TRAS = 365  # 3.3.8.4: GMUD com SLA (mesmo sem agendamento) entra se o SLA for do último ano pra frente
STATUS_FORA_DO_SLA = ("resolvido", "fechado")  # pedido do Igor: só esses saem de "vencidas e próximas a vencer"
# campo da tela -> nomes de coluna prováveis na tabela gmud (o primeiro que existir vale)
CANDIDATAS = {
    "id": ("ticketId", "ticket_id", "idTicket", "id", "ID"),
    "titulo": ("subject", "titulo", "assunto", "nomeGmud", "tituloGmud", "descricaoGmud", "descricao"),
    "cliente": ("clientOrganizationBusinessName", "organizacao", "clientBusinessName", "cliente", "empresa"),
    "status": ("statusGmud", "status", "baseStatus", "situacao"),
    "responsavel": ("ownerName", "owner", "responsavel", "responsavelGmud", "executor", "agente", "createdByName"),
    "prazo_sla": ("slaSolutionDate", "prazoSla", "prazo_sla", "slaSolucao", "slaResponseDate", "prazo"),
    "fim_demanda": ("dataFimDemanda", "fimDemanda", "data_fim_demanda"),  # 3.3.7.1: coluna nova, passada pelo Igor
}
_colunas_logadas = {"feito": False}


def _sem_acento(texto) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", str(texto or "")) if unicodedata.category(c) != "Mn").lower().strip()


def _pessoas() -> list:
    """Ativos, a equipe Serviços primeiro (são eles que tocam as GMUDs)."""
    lista = []
    for login, info in USUARIOS_WEB.items():
        if not info.get("ativo", True) or login.lower().startswith("teste"):
            continue
        lista.append({"login": login, "nome": info.get("nome") or login, "tem_foto": _caminho_foto_usuario(login) is not None,
                      "servicos": (info.get("atribuicao") or "") == ATRIBUICAO_SERVICOS})
    lista.sort(key=lambda p: (not p["servicos"], not p["tem_foto"], p["nome"].lower()))
    return lista


def _login_do_nome(nome: str) -> str:
    """Login do PDA de quem tem todas as palavras do nome que veio do Movidesk (nome de uma palavra só não serve)."""
    palavras = set(re.findall(r"[a-z]+", _sem_acento(nome)))
    if len(palavras) < 2:
        return ""
    achados = [login for login, info in USUARIOS_WEB.items()
               if (pal := set(re.findall(r"[a-z]+", _sem_acento(info.get("nome"))))) and len(pal) >= 2 and pal <= palavras]
    return achados[0] if len(achados) == 1 else ""


def _data_hora(valor) -> str:
    """datetime (ou texto "2026-10-07 14:00:00.000") -> "AAAA-MM-DD HH:MM"; vazio se não der."""
    if valor is None or valor == "":
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%Y-%m-%d %H:%M")
    if isinstance(valor, date):
        return valor.strftime("%Y-%m-%d") + " 00:00"
    m = re.match(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})", str(valor).strip())
    return f"{m.group(1)} {m.group(2)}" if m else ""


def _status(texto: str, inicio: str, fim: str, agora: datetime) -> str:
    """Status do Movidesk/da GMUD -> as 5 situações da tela; sem coluna de status, deduz pelo horário."""
    t = _sem_acento(texto)
    if t:
        if "cancel" in t:
            return "cancelada"
        if any(p in t for p in ("conclu", "fechad", "resolvid", "finaliz", "closed", "resolved")):
            return "concluida"
        if "aprova" in t:
            return "aprovacao"
        if any(p in t for p in ("execu", "andamento", "atendimento", "progress")):
            return "execucao"
        if any(p in t for p in ("agend", "novo", "new", "aberto", "aguard", "pendente")):
            return "agendada"
    agora_txt = agora.strftime("%Y-%m-%d %H:%M")
    if fim and fim < agora_txt:
        return "concluida"
    if inicio and inicio <= agora_txt and (not fim or agora_txt <= fim):
        return "execucao"
    return "agendada"


def _coluna(nomes: list, campo: str):
    minusculas = {n.lower(): n for n in nomes}
    for candidata in CANDIDATAS[campo]:
        if candidata.lower() in minusculas:
            return minusculas[candidata.lower()]
    return None


def _montar(linha: dict, cols: dict, agora: datetime) -> dict:
    inicio = _data_hora(linha.get(cols["inicio"]))
    fim = _data_hora(linha.get(cols["fim"]))
    pega = lambda campo: linha.get(cols[campo]) if cols.get(campo) else None
    ident = pega("id")
    nome_resp = str(pega("responsavel") or "").strip()
    login = _login_do_nome(nome_resp) if nome_resp else ""
    titulo = str(pega("titulo") or "").strip() or (f"GMUD {ident}" if ident not in (None, "") else "GMUD")
    return {
        "id": str(ident) if ident not in (None, "") else "",
        "titulo": titulo[:200],
        "cliente": str(pega("cliente") or "").strip(),
        "agendada_para": inicio,
        "termina_em": fim if fim and fim != inicio else "",
        "prazo_sla": _data_hora(pega("prazo_sla")),
        "fim_demanda": _data_hora(pega("fim_demanda")),
        "status": _status(pega("status"), inicio, fim, agora),
        "status_movidesk": str(pega("status") or "").strip(),
        "responsaveis": [login] if login else [],
        "responsavel_nome": nome_resp,
        "link": LINK_TICKET_MOVIDESK.format(id=ident) if cols.get("id") and str(ident or "").isdigit() else "",
    }


def listar_gmuds(hoje: date = None) -> dict:
    """GMUDs de Serviços dos últimos/próximos meses. Banco fora do ar -> ok False (a rota responde 503)."""
    hoje = hoje or date.today()
    agora = datetime.now()
    desde = (hoje.replace(day=1) - timedelta(days=31 * MESES_ANTES)).replace(day=1)
    ate = (hoje.replace(day=1) + timedelta(days=31 * (MESES_DEPOIS + 1))).replace(day=1)
    conn, erro = _conectar_indicadores_movidesk()
    if not conn:
        return {"ok": False, "integrado": True, "erro": erro or "banco do Movidesk indisponível", "gmuds": [], "pessoas": _pessoas()}
    try:
        cursor = conn.cursor()
        # GMUD que começa ou termina dentro da janela (ou atravessa ela inteira) e, desde a 3.3.8.4, as que têm SLA
        # (slaSolutionDate) do último ano pra frente, mesmo sem agendamento (entram só na caixa do SLA)
        desde_sla = hoje - timedelta(days=DIAS_SLA_PRA_TRAS)
        try:
            cursor.execute(
                f"SELECT TOP {LIMITE_LINHAS} * FROM gmud WHERE ownerTeam = ? AND ("
                "(dataHoraInicioGmud IS NOT NULL AND dataHoraInicioGmud < ? AND COALESCE(dataHoraFimGmud, dataHoraInicioGmud) >= ?) "
                "OR (slaSolutionDate IS NOT NULL AND slaSolutionDate >= ?)) ORDER BY COALESCE(dataHoraInicioGmud, slaSolutionDate)",
                (EQUIPE_GMUD, ate, desde, desde_sla),
            )
        except Exception:
            # base sem a coluna slaSolutionDate: volta pra consulta só pelo agendamento
            logger.warning("Calendário de GMUD's: consulta com slaSolutionDate falhou; usando só o agendamento.", exc_info=True)
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT TOP {LIMITE_LINHAS} * FROM gmud WHERE ownerTeam = ? "
                "AND dataHoraInicioGmud IS NOT NULL AND dataHoraInicioGmud < ? "
                "AND COALESCE(dataHoraFimGmud, dataHoraInicioGmud) >= ? ORDER BY dataHoraInicioGmud",
                (EQUIPE_GMUD, ate, desde),
            )
        nomes = [d[0] for d in cursor.description]
        linhas = [dict(zip(nomes, r)) for r in cursor.fetchall()]
    except Exception as e:
        logger.exception("Calendário de GMUD's: erro ao consultar a tabela gmud")
        return {"ok": False, "integrado": True, "erro": f"erro ao consultar as GMUDs: {e}", "gmuds": [], "pessoas": _pessoas()}
    finally:
        try:
            conn.close()
        except Exception:
            pass
    cols = {campo: _coluna(nomes, campo) for campo in CANDIDATAS}
    cols["inicio"] = next((n for n in nomes if n.lower() == "datahorainiciogmud"), "dataHoraInicioGmud")
    cols["fim"] = next((n for n in nomes if n.lower() == "datahorafimgmud"), "dataHoraFimGmud")
    if not _colunas_logadas["feito"]:
        _colunas_logadas["feito"] = True
        logger.info("Calendário de GMUD's: colunas da tabela gmud = %s; usadas = %s", ", ".join(nomes),
                    {k: v for k, v in cols.items() if v})
    # sem agendamento, só vale a pena se tem prazo e não está Resolvido/Fechado (aparece na caixa do SLA, não no calendário)
    gmuds = [g for g in (_montar(l, cols, agora) for l in linhas)
             if g["agendada_para"] or ((g["prazo_sla"] or g["fim_demanda"]) and g["status_movidesk"].lower() not in STATUS_FORA_DO_SLA)]
    return {"ok": True, "integrado": True, "gmuds": gmuds, "pessoas": _pessoas(),
            "faltando": [campo for campo in ("titulo", "cliente", "responsavel", "prazo_sla", "fim_demanda", "status") if not cols.get(campo)]}
