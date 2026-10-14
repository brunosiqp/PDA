# encoding: utf-8
"""
Carregador do CREDENCIAIS_CENTRALIZADAS.env - arquivo único que substitui
os ~40 .env espalhados pela pasta do PDA (ver conversa de 05/09/2026).

Formato: INI (seções [nome] com chave = valor), lido com configparser e
interpolation=None (queries SQL têm '%' de LIKE, que o configparser trataria
como caractere especial de interpolação se não desligar isso).

FALLBACK DE PROPÓSITO: se uma seção não existir no arquivo central (porque
ele ainda não foi copiado pra essa máquina, ou porque alguém criou um alerta
novo e esqueceu de migrar), quem usa `obter_config_hibrido` cai de volta pro
.env antigo automaticamente - mesma filosofia de migração gradual que
core/config_seguro.py já usa pra senha cifrada (nada quebra de uma hora pra
outra, mesmo em máquina que ainda não tem o arquivo novo).
"""
import os
import sys
import configparser
from typing import Optional

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None


def _base_path_app() -> str:
    """Mesma lógica duplicada em alertas_gui.py e core/config_seguro.py -
    de propósito, pra evitar import circular entre esses módulos."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


NOME_ARQUIVO_CENTRAL = "CREDENCIAIS_CENTRALIZADAS.env"
_config_central_cache: Optional[configparser.ConfigParser] = None


def _carregar_config_central() -> configparser.ConfigParser:
    global _config_central_cache
    if _config_central_cache is not None:
        return _config_central_cache
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str  # preserva maiúsculas/minúsculas das chaves (ex.: SHAREPOINT_LOGIN)
    caminho = os.path.join(_base_path_app(), NOME_ARQUIVO_CENTRAL)
    if os.path.exists(caminho):
        cp.read(caminho, encoding="utf-8")
    _config_central_cache = cp
    return cp


def recarregar_config_central() -> None:
    """Força reler o arquivo do disco na próxima chamada - útil se ele foi
    editado manualmente com o programa já rodando (não precisa reiniciar
    o PDA inteiro pra pegar uma senha nova, só chamar isso - hoje só
    usado internamente, mas fica exposto caso vire um botão no futuro)."""
    global _config_central_cache
    _config_central_cache = None


def obter_secao(nome_secao: str) -> dict:
    """Devolve um dict com todas as chaves da seção [nome_secao] do
    CREDENCIAIS_CENTRALIZADAS.env, ou {} se a seção não existir (arquivo
    não copiado ainda, ou nome de seção errado/novo)."""
    cp = _carregar_config_central()
    if nome_secao not in cp:
        return {}
    return dict(cp[nome_secao])


def obter_config_hibrido(secao_central: str, nome_arquivo_env: str, chaves: list) -> dict:
    """Devolve {chave: valor} pras `chaves` pedidas - tenta a seção
    `secao_central` do arquivo centralizado primeiro; qualquer chave que
    não esteja lá cai pro .env tradicional `nome_arquivo_env` (mesmo
    comportamento de sempre: load_dotenv + os.getenv), pra quem ainda não
    copiou o arquivo central pra essa máquina não perder nada."""
    valores_centrais = obter_secao(secao_central)
    precisa_fallback = any(c not in valores_centrais for c in chaves)
    if precisa_fallback and load_dotenv:
        env_path = os.path.join(_base_path_app(), nome_arquivo_env)
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=True)
    resultado = {}
    for chave in chaves:
        resultado[chave] = valores_centrais.get(chave) or os.getenv(chave, "")
    return resultado
