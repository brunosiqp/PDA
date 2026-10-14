"""Banco de monitoramento - lógica (conexão com o banco de monitoramento usada pelas Manutenções de Alertas, Rejeições e Relatórios).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import logging

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco
from nucleo.config import _obter_config_hibrido

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


TIPOS_BANCO_VALIDOS = ["ORACLE", "SQL"]

# E-mail padrão do monitoramento - todo alerta criado/editado por aqui usa
# esse endereço, travado (não é um campo livre no formulário).
EMAIL_MONITORAMENTO_PADRAO = "contato66@example.com"


def _config_monitoramento() -> dict:
    """Lê as credenciais do banco de monitoramento - CREDENCIAIS_CENTRALIZADAS.env
    primeiro (seção [infra_monitoramento]), cai pro .env.monitoramento
    tradicional se essa seção não existir (ver core/config_central.py)."""
    valores = _obter_config_hibrido(
        "infra_monitoramento", ".env.monitoramento",
        ["MONITORAMENTO_DB_SERVER", "MONITORAMENTO_DB_DATABASE",
         "MONITORAMENTO_DB_USER", "MONITORAMENTO_DB_PASSWORD"],
    )
    return {
        "server": valores["MONITORAMENTO_DB_SERVER"],
        "database": valores["MONITORAMENTO_DB_DATABASE"],
        "username": valores["MONITORAMENTO_DB_USER"],
        "password": _obter_valor_config("monitoramento::MONITORAMENTO_DB_PASSWORD", valores["MONITORAMENTO_DB_PASSWORD"]),
    }


def _conectar_monitoramento():
    cfg = _config_monitoramento()
    if not all(cfg.values()):
        return None, "Credenciais do banco de monitoramento não configuradas (.env.monitoramento)."
    try:
        conn = conectar_banco(cfg["server"], cfg["database"], cfg["username"], cfg["password"])
    except Exception as e:
        # blindagem extra: core.db_utils já trata pyodbc.Error/ValueError
        # internamente, mas um driver ODBC real pode levantar outros tipos
        # de exceção (timeout de rede, falha de DNS, etc.) - isso NUNCA pode
        # derrubar a thread do servidor web.
        logger.exception("Erro inesperado ao conectar no banco de monitoramento")
        return None, f"Erro inesperado ao conectar: {e}"
    if not conn:
        return None, "Não foi possível conectar ao banco de monitoramento."
    return conn, None
