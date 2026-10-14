"""Movidesk (base) - lógica (conexão com o banco do Movidesk e acesso à API pública (URL, token, perfis e equipes)).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import re
import logging
import os
from typing import Optional

from dotenv import dotenv_values

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_config_hibrido
from nucleo.config import _obter_secao_central

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _config_indicadores_movidesk() -> dict:
    """CREDENCIAIS_CENTRALIZADAS.env primeiro (seção
    [infra_indicadores_movidesk]), cai pro .env.indicadores_movidesk
    tradicional se essa seção não existir (ver core/config_central.py)."""
    valores = _obter_config_hibrido(
        "infra_indicadores_movidesk", ".env.indicadores_movidesk",
        ["db_server", "db_name", "db_user", "db_password"],
    )
    return {
        "server": valores["db_server"],
        "database": valores["db_name"],
        "username": valores["db_user"],
        "password": _obter_valor_config("indicadores_movidesk::db_password", valores["db_password"]),
    }


def _conectar_indicadores_movidesk():
    cfg = _config_indicadores_movidesk()
    if not all(cfg.values()):
        return None, "Credenciais do banco de Indicadores Movidesk não configuradas (.env.indicadores_movidesk)."
    try:
        conn = conectar_banco(cfg["server"], cfg["database"], cfg["username"], cfg["password"])
    except Exception as e:
        logger.exception("Erro inesperado ao conectar no banco de Indicadores Movidesk")
        return None, f"Erro inesperado ao conectar: {e}"
    if not conn:
        return None, "Não foi possível conectar ao banco de Indicadores Movidesk."
    return conn, None


class ManutencaoUsuariosConfigError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Movidesk - cadastro/desativação da PESSOA em si via API pública (perfil de
# acesso/equipe no Movidesk), separado dos bancos de cada produto acima.
# IMPORTANTE: essa integração eu não consegui testar contra a API de
# verdade (meu ambiente não alcança api.movidesk.com) - montei tudo
# seguindo exatamente os exemplos de request/response que você me passou,
# mas o primeiro cadastro/desativação real precisa ser conferido por você.
# ---------------------------------------------------------------------------
MOVIDESK_API_BASE = "https://api.movidesk.com/public/v1/persons"
# mapeamento Área (do formulário) -> perfil de acesso/equipe no Movidesk -
# ASSUNÇÃO minha pros nomes de perfil/equipe (bati com o único exemplo que
# você me passou, "MONITORAMENTO"); pra área "todos" não tem um perfil
# único óbvio, então uso MONITORAMENTO como principal e entro nas duas
# equipes - me corrija se não for isso.
MOVIDESK_AREA_PARA_ACCESS_PROFILE = {
    "suporte": "SUPORTE", "monitoramento": "MONITORAMENTO", "todos": "MONITORAMENTO",
}
MOVIDESK_AREA_PARA_TEAMS = {
    "suporte": ["SUPORTE"], "monitoramento": ["MONITORAMENTO"], "todos": ["SUPORTE", "MONITORAMENTO"],
}

_movidesk_api_token_cache: Optional[str] = None

_RE_TOKEN_URL = re.compile(r"(token=)[^&\s'\"]+", re.IGNORECASE)


def ocultar_token(texto: object) -> str:
    """Tira o token da API do Movidesk de qualquer texto (3.2.7.1): o erro do requests traz a URL inteira, com
    `?token=...`, e isso ia parar na tela da Manutenção de Usuários e nos logs de auditoria."""
    return _RE_TOKEN_URL.sub(lambda m: m.group(1) + "<oculto>", str(texto))


def _movidesk_api_token() -> str:
    global _movidesk_api_token_cache
    if _movidesk_api_token_cache is not None:
        return _movidesk_api_token_cache
    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seção
    # [manutencao_usuarios_movidesk]), cai pro .env.manutencao_usuarios.movidesk
    # tradicional se essa seção não existir.
    token = (_obter_secao_central("manutencao_usuarios_movidesk").get("MOVIDESK_TOKEN") or "").strip()
    if not token:
        caminho = os.path.join(_base_path_app(), ".env.manutencao_usuarios.movidesk")
        if not os.path.exists(caminho):
            raise ManutencaoUsuariosConfigError("Arquivo de configuração não encontrado: .env.manutencao_usuarios.movidesk")
        valores = dotenv_values(caminho)
        token = (valores.get("MOVIDESK_TOKEN") or "").strip()
    if not token:
        raise ManutencaoUsuariosConfigError("MOVIDESK_TOKEN não configurado (nem no arquivo central, nem em .env.manutencao_usuarios.movidesk)")
    _movidesk_api_token_cache = token
    return token
