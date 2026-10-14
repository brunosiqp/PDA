"""Dashboards por Cliente - lógica (mapa cliente -> produtos e o dashboard nativo ClienteB/NFAg).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import json
import logging
import os
from datetime import datetime
from datetime import timedelta
from typing import Dict
from typing import Optional

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco
from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_config_hibrido

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _caminho_dashboards_clientes_json() -> str:
    return os.path.join(_base_path_app(), "dashboards_clientes.json")


def _carregar_dashboards_clientes() -> dict:
    """Cliente -> lista de produtos - dados semente (ClienteB/ClienteG) só pra
    ter uma base visual enquanto o dashboard de verdade não é construído
    (card em Beta). Devolve {} se o arquivo não existir/estiver
    corrompido, em vez de quebrar a página."""
    caminho = _caminho_dashboards_clientes_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, dict):
                return dados
        except Exception:
            logger.exception("Não foi possível ler dashboards_clientes.json.")
    return {}


# ---------------------------------------------------------------------------
# Dashboard ClienteB > NFAg - transcrito do Power BI (Indicadores_NFAg_ClienteB
# .pbix) em 08/09/2026, a pedido do Igor. Mesma lógica de negócio das
# medidas DAX originais (ver 02_medidas_dax.txt que ele mandou), só que
# calculada em Python a partir da mesma query SQL nativa do PBIX.
# ---------------------------------------------------------------------------
NFAG_CLIENTE_B_CNPJ = "90213482855909"

# Mesmo SWITCH(TRUE(), ...) da coluna calculada "Status Descricao" do PBIX -
# tradução direta, IND_STATUS -> rótulo (ordem importa: 1 e 2 caem no
# primeiro IN, exatamente como no DAX original).
NFAG_STATUS_MAPA = {
    1: "Validada", 2: "Validada",
    3: "Criticada",
    6: "Autorizada",
    8: "Rejeitada",
    9: "Cancelada",
    10: "Autorizada Contingência",
    12: "Rejeitada Contingência",
    15: "Validada Contingência",
}
NFAG_STATUS_AUTORIZADA = {"Autorizada", "Autorizada Contingência"}
NFAG_STATUS_REJEITADA = {"Rejeitada", "Rejeitada Contingência"}


def _status_descricao_nfag(ind_status) -> str:
    try:
        return NFAG_STATUS_MAPA.get(int(ind_status), "Outros / Não mapeado")
    except (TypeError, ValueError):
        return "Outros / Não mapeado"


def _config_dashboard_cliente_b_nfag() -> dict:
    """CREDENCIAIS_CENTRALIZADAS.env primeiro (seção
    [dashboard_cliente_b_nfag]), cai pro .env.dashboard_cliente_b_nfag
    tradicional se essa seção não existir (ver core/config_central.py)."""
    valores = _obter_config_hibrido(
        "dashboard_cliente_b_nfag", ".env.dashboard_cliente_b_nfag",
        ["db_server", "db_name", "db_user", "db_password"],
    )
    return {
        "server": valores["db_server"],
        "database": valores["db_name"],
        "username": valores["db_user"],
        "password": _obter_valor_config("dashboard_cliente_b_nfag::db_password", valores["db_password"]),
    }


def _consultar_dashboard_cliente_b_nfag(data_inicio: Optional[str], data_fim: Optional[str]) -> dict:
    """Mesma query nativa do PBIX (mesmo WHERE por CNPJ), com filtro de
    data OPCIONAL por cima (equivalente ao slicer "Entre" do relatório
    original) - devolve {"ok": True, ...} com tudo que os visuais do
    PBIX precisam, ou {"ok": False, "erro": str}."""
    cfg = _config_dashboard_cliente_b_nfag()
    if not cfg["password"] or cfg["password"] == "PREENCHER_SENHA_AQUI":
        return {"ok": False, "erro": "Credencial do banco nfagpack_homol ainda não configurada (db_password em branco)."}

    query = (
        "SELECT ID, CHAVE_NF, IND_STATUS, DATA_INTEGRATION, EMPRESA_CNPJ, SERIE, NNF, DEMI, "
        "PROT_C_STAT, PROT_X_MOTIVO FROM documento_fiscal WHERE empresa_cnpj = ?"
    )
    params = [NFAG_CLIENTE_B_CNPJ]
    if data_inicio:
        query += " AND DATA_INTEGRATION >= ?"
        params.append(data_inicio)
    if data_fim:
        query += " AND DATA_INTEGRATION <= ?"
        params.append(data_fim)

    conn = conectar_banco(cfg["server"], cfg["database"], cfg["username"], cfg["password"], raise_on_error=False)
    if not conn:
        return {"ok": False, "erro": f"Falha ao conectar no banco {cfg['database']}."}
    try:
        linhas, colunas = executar_query(conn, query, params=tuple(params), fetch=True, raise_on_error=True)
    except Exception as exc:
        logger.exception("Erro ao consultar dashboard ClienteB/NFAg")
        return {"ok": False, "erro": f"Erro na consulta: {exc}"}
    finally:
        fechar_conexao(conn)

    colunas_lower = [c.lower() for c in colunas]
    registros = [dict(zip(colunas_lower, linha)) for linha in linhas]

    agora = datetime.now()
    contagem_status: Dict[str, int] = {}
    contagem_hora: Dict[str, Dict[str, int]] = {}
    qtd_ultima_hora = 0
    qtd_autorizadas = 0
    qtd_rejeitadas = 0

    for r in registros:
        status = _status_descricao_nfag(r.get("ind_status"))
        contagem_status[status] = contagem_status.get(status, 0) + 1
        if status in NFAG_STATUS_AUTORIZADA:
            qtd_autorizadas += 1
        if status in NFAG_STATUS_REJEITADA:
            qtd_rejeitadas += 1

        data_integracao = r.get("data_integration")
        if isinstance(data_integracao, str):
            try:
                data_integracao = datetime.fromisoformat(data_integracao)
            except ValueError:
                data_integracao = None
        if isinstance(data_integracao, datetime):
            # "Qtd Última Hora" é sempre relativa a AGORA (mesma semântica
            # de NOW() - TIME(1,0,0) do DAX) - independente do filtro de
            # data escolhido, pra ser um indicador de saúde em tempo real
            if data_integracao >= agora - timedelta(hours=1):
                qtd_ultima_hora += 1
            rotulo_hora = data_integracao.strftime("%d/%m %H:00")
            bucket = contagem_hora.setdefault(rotulo_hora, {"integradas": 0, "autorizadas": 0})
            bucket["integradas"] += 1
            if status in NFAG_STATUS_AUTORIZADA:
                bucket["autorizadas"] += 1

    por_status = [{"status": k, "qtd": v} for k, v in contagem_status.items()]
    por_status.sort(key=lambda x: x["qtd"], reverse=True)

    por_hora = [{"hora": k, **v} for k, v in contagem_hora.items()]
    # ordena pela data/hora de verdade (o rótulo "dd/mm HH:00" sozinho não
    # ordena certo entre meses diferentes, então reconstrói pra ordenar)
    por_hora.sort(key=lambda x: datetime.strptime(x["hora"], "%d/%m %H:00"))

    return {
        "ok": True,
        "kpis": {
            "qtd_integradas": len(registros),
            "qtd_ultima_hora": qtd_ultima_hora,
            "qtd_autorizadas": qtd_autorizadas,
            "qtd_rejeitadas": qtd_rejeitadas,
        },
        "por_status": por_status,
        "por_hora": por_hora,
    }
