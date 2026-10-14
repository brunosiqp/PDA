"""String Connections - lógica (strings de conexão reutilizáveis por cliente e produto (string_connections.json)).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import json
import logging
import os

from nucleo.caminhos import base_path_app as _base_path_app

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _caminho_string_connections_json() -> str:
    return os.path.join(_base_path_app(), "string_connections.json")


def _carregar_string_connections() -> dict:
    caminho = _caminho_string_connections_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.exception("Não foi possível ler string_connections.json.")
    return {}


def _salvar_string_connections(dados: dict) -> None:
    caminho = _caminho_string_connections_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar string_connections.json.")


def _chave_string_connection(cliente: str, produto: str) -> tuple:
    """Cliente + produto sem diferença de maiúscula/minúscula nem de espaços
    ("ClienteX " e "CLIENTE_X" são o mesmo cliente)."""
    normalizar = lambda texto: " ".join(str(texto or "").split()).casefold()
    return normalizar(cliente), normalizar(produto)


def _buscar_string_connection_igual(cliente: str, produto: str, ignorar_id: str = None):
    """ID da string que já existe pro mesmo cliente + produto (ou None). Só
    pode existir uma por par: ao criar ou editar, a tela pergunta se deve
    substituir a que já existe. `ignorar_id` = a própria string sendo editada."""
    chave = _chave_string_connection(cliente, produto)
    for id_conexao, info in STRING_CONNECTIONS.items():
        if id_conexao != ignorar_id and _chave_string_connection(info.get("cliente"), info.get("produto")) == chave:
            return id_conexao
    return None


STRING_CONNECTIONS: dict = _carregar_string_connections()
