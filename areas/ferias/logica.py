"""Calendário de Férias - lógica (períodos de férias, day-off e atestados da equipe (ferias.json)).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import json
import logging
import os
import threading

from nucleo.caminhos import base_path_app as _base_path_app

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _caminho_ferias_json() -> str:
    return os.path.join(_base_path_app(), "ferias.json")


def _carregar_ferias() -> list:
    caminho = _caminho_ferias_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
        except Exception:
            logger.exception("Não foi possível ler ferias.json, começando vazio.")
    return []


def _salvar_ferias(dados: list) -> None:
    caminho = _caminho_ferias_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar ferias.json.")


FERIAS: list = _carregar_ferias()


_lock_ferias = threading.Lock()


def _periodos_se_sobrepoem(inicio1: str, fim1: str, inicio2: str, fim2: str) -> bool:
    return inicio1 <= fim2 and inicio2 <= fim1
