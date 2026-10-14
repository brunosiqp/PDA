"""Configuração: leitura híbrida (CREDENCIAIS_CENTRALIZADAS.env primeiro, .env legado depois).

Movido do alertas_gui.py em 26/09/2026 pra as áreas usarem o mesmo leitor (com o mesmo
plano B se core/config_central.py faltar na instalação).
"""
import logging
import os

from nucleo.caminhos import base_path_app as _base_path_app

# CREDENCIAIS_CENTRALIZADAS.env - arquivo único que substitui os ~40 .env
# espalhados (ver conversa de 05/09/2026). Mesma ideia de import separado
# do config_seguro acima: evita import circular com alerta_core.
#
# TOLERANTE A FALTA DO ARQUIVO: core/config_central.py é um módulo NOVO -
# se alguém esquecer de copiar ele pra pasta core/ (aconteceu uma vez,
# derrubou o programa inteiro com ModuleNotFoundError), o PDA não pode
# travar por causa disso. Cai pro comportamento de ANTES da consolidação
# (cada coisa lendo direto do seu .env de sempre) em vez de crashar.
try:
    from core.config_central import (
        obter_secao as _obter_secao_central,
        obter_config_hibrido as _obter_config_hibrido,
    )
except ImportError:
    logging.getLogger("alertas").warning(
        "core/config_central.py não encontrado nesta instalação - "
        "CREDENCIAIS_CENTRALIZADAS.env não vai ser usado nesta execução, "
        "tudo cai pro .env tradicional de cada coisa (comportamento de antes "
        "da consolidação). Copie core/config_central.py pra pasta core/ "
        "pra voltar a usar o arquivo único."
    )

    def _obter_secao_central(nome_secao: str) -> dict:
        return {}

    def _obter_config_hibrido(secao_central: str, nome_arquivo_env: str, chaves: list) -> dict:
        env_path = os.path.join(_base_path_app(), nome_arquivo_env)
        if os.path.exists(env_path):
            from dotenv import load_dotenv
            load_dotenv(dotenv_path=env_path, override=True)
        return {chave: os.getenv(chave, "") for chave in chaves}
