# -*- coding: utf-8 -*-
"""
Painel consolidado de alertas (dark theme).

Junta todos os alertas num único processo, cada um rodando em sua própria
thread quando disparado, com acompanhamento visual de status e log com
timestamp de tudo que acontece.

Nem todo alerta segue o mesmo padrão de execução/agendamento, então cada
item de JOBS é um `Job` genérico com:
    - executar: a função que efetivamente faz o trabalho
    - registrar_horarios: a função que registra os horários dele na lib
      `schedule` (pode ser "toda hora, :00, todo dia", "de 30 em 30 min
      em horário comercial, dias úteis", etc.)

Como adicionar um novo alerta:
    - Se ele seguir o padrão padrão do `Alerta(nome, descricao, clientes)`
      rodando de hora em hora todo dia: use `job_alerta(...)`.
    - Se tiver um horário diferente (ex.: só dias úteis, meia em meia
      hora, horário comercial): use `job_alerta(..., registrar_horarios=...)`
      com uma das funções de agenda já prontas, ou crie uma nova.
    - Se a lógica não usar `Alerta` (como o ValidacaoFTP): monte um `Job`
      na mão, com sua própria função `executar`.

ATENÇÃO — módulos locais de projeto (ex.: `features/operations.py` do
ValidacaoFTP): esse arquivo precisa estar numa pasta `features/` ao lado
deste script. Se no futuro outro alerta também tiver uma pasta local
`features/` ou `core/` com conteúdo diferente, vai dar colisão de nome de
import — nesse caso, ou renomeia o pacote local pra algo mais específico
(ex.: `validacao_ftp/operations.py`) ou isola esse alerta em outro processo.
"""

import base64
import html as html_utils
import json
import logging
import os
import io
import zipfile
import re
import hashlib
import secrets
import socket
import sys
import threading
import time
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
import tkinter as tk
import urllib.parse
import webbrowser
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date, time as time_cls
from pathlib import Path
import decimal
import calendar
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from logging.handlers import RotatingFileHandler
from tkinter import ttk
from typing import Callable, Dict, List, Optional, Union


def _falha_fatal_na_importacao(nome_modulo: str, dica: str, erro: Exception) -> None:
    """Se um import essencial falhar, isso acontece ANTES de qualquer
    janela abrir — por padrão o processo simplesmente morre e some
    ("abre e fecha"). Aqui a gente imprime o erro real e segura o
    console aberto, pra dar pra ler o que quebrou."""
    print(f"\n[ERRO FATAL] Não foi possível importar '{nome_modulo}': {erro}\n")
    print(dica)
    input("\nPressione ENTER para sair...")
    sys.exit(1)


# Bibliotecas externas (não vêm com o Python "puro" - precisam de
# "py -m pip install -r requirements.txt"). Cada uma protegida
# separadamente, pra dizer exatamente qual está faltando em vez de só
# fechar a janela sem explicação.
try:
    import pyodbc
except Exception as _e:
    _falha_fatal_na_importacao(
        "pyodbc",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install pyodbc)",
        _e,
    )

try:
    import requests
except Exception as _e:
    _falha_fatal_na_importacao(
        "requests",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install requests)\n"
        "Essa biblioteca é usada pelo monitoramento de Contingências SEFAZ.",
        _e,
    )

try:
    import schedule
except Exception as _e:
    _falha_fatal_na_importacao(
        "schedule",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install schedule)",
        _e,
    )

try:
    from dotenv import load_dotenv, dotenv_values
except Exception as _e:
    _falha_fatal_na_importacao(
        "python-dotenv",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install python-dotenv)",
        _e,
    )


try:
    from alerta_core import Alerta
except Exception as _e:
    _falha_fatal_na_importacao(
        "alerta_core",
        "Verifique se o módulo/pacote 'alerta_core' está instalado e acessível "
        "no Python que está rodando este script (o mesmo usado pelos scripts antigos).",
        _e,
    )

try:
    from features.operations import execute as ftp_execute, getEnv as ftp_getEnv
except Exception as _e:
    _falha_fatal_na_importacao(
        "features.operations",
        "Verifique se:\n"
        "  1) a pasta 'features/' (com operations.py) do projeto ValidacaoFTP\n"
        "     está copiada para o lado deste alertas_gui.py;\n"
        "  2) o pacote 'core' (email_utils / utils) está acessível no ambiente;\n"
        "  3) a lib 'pandas' está instalada (pip install pandas).",
        _e,
    )

try:
    from core.db_utils import conectar_banco, executar_query, fechar_conexao, _rollback_if_possible
except Exception as _e:
    _falha_fatal_na_importacao(
        "core.db_utils",
        "Verifique se a pasta 'core/' (com db_utils.py) está copiada para o "
        "lado deste alertas_gui.py - é usada pela Manutenção de Alertas em Banco.",
        _e,
    )

try:
    from core.email_utils import enviar_email
except Exception as _e:
    _falha_fatal_na_importacao(
        "core.email_utils",
        "Verifique se a pasta 'core/' (com email_utils.py) está copiada para o "
        "lado deste alertas_gui.py - é usada pelos alertas por e-mail e pelo "
        "e-mail de boas-vindas da Manutenção de Usuários.",
        _e,
    )

try:
    import pandas as pd
except Exception as _e:
    _falha_fatal_na_importacao(
        "pandas",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install pandas xlsxwriter)\n"
        "Usado pelos Relatórios Shein.",
        _e,
    )

try:
    import xlsxwriter  # noqa: F401 - não é usado direto no código, só precisa
    # estar instalado porque o pandas usa ele por baixo dos panos (engine=
    # "xlsxwriter") pra gerar os arquivos .xlsx dos Relatórios Shein. Sem
    # essa checagem aqui, o erro só aparecia na hora de gerar o relatório
    # de verdade, com uma mensagem meio críptica.
except Exception as _e:
    _falha_fatal_na_importacao(
        "xlsxwriter",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install xlsxwriter)\n"
        "Usado pelos Relatórios Shein pra gerar os arquivos .xlsx.",
        _e,
    )

try:
    from cryptography.fernet import Fernet, InvalidToken
except Exception as _e:
    _falha_fatal_na_importacao(
        "cryptography",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install cryptography)\n"
        "Usado pra cifrar configurações sensíveis (config.dat).",
        _e,
    )

try:
    from dateutil.relativedelta import relativedelta
except Exception as _e:
    _falha_fatal_na_importacao(
        "python-dateutil",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install python-dateutil)\n"
        "Usado pra calcular o período do mês anterior na Atualização "
        "Dash Financeiro.",
        _e,
    )


DIAS_UTEIS = ["monday", "tuesday", "wednesday", "thursday", "friday"]


# ---------------------------------------------------------------------------
# Funções de agendamento (cada uma registra 1+ horários na lib `schedule`
# e retorna a lista de `schedule.Job` criados, pra dar pra calcular a
# "próxima execução" na GUI)
# ---------------------------------------------------------------------------
def agenda_todo_dia_hora_cheia(runner: Callable[[], None]) -> List["schedule.Job"]:
    """Todo dia, de hora em hora, na marca (:00). Padrão da maioria dos alertas."""
    return [schedule.every().hour.at(":00").do(runner)]


def agenda_dias_uteis_meia_hora_06_22(runner: Callable[[], None]) -> List["schedule.Job"]:
    """Dias úteis, de 30 em 30 min, das 06:00 até 22:00 (última só em :00)."""
    horarios = [
        f"{hora:02d}:{minuto:02d}"
        for hora in range(6, 23)
        for minuto in (0, 30)
        if hora < 22 or minuto == 0
    ]
    jobs = []
    for dia in DIAS_UTEIS:
        for horario in horarios:
            jobs.append(getattr(schedule.every(), dia).at(horario).do(runner))
    return jobs


def agenda_dias_uteis_hora_cheia_08_17(runner: Callable[[], None]) -> List["schedule.Job"]:
    """Dias úteis, de hora em hora, das 08:00 às 17:00."""
    horarios = [f"{hora:02d}:00" for hora in range(8, 18)]
    jobs = []
    for dia in DIAS_UTEIS:
        for horario in horarios:
            jobs.append(getattr(schedule.every(), dia).at(horario).do(runner))
    return jobs


def agenda_a_cada_4_horas(runner: Callable[[], None]) -> List["schedule.Job"]:
    """A cada 4 horas a partir de agora. A primeira execução (na abertura do
    painel) já acontece via Agendador.iniciar() - esta função só cuida das
    repetições seguintes."""
    return [schedule.every(4).hours.do(runner)]


def agenda_todo_dia_as_09(runner: Callable[[], None]) -> List["schedule.Job"]:
    """Todo dia, uma vez só, às 09:00 - pra jobs que não precisam (e não
    devem) rodar de hora em hora, tipo o alerta de tempo de empresa."""
    return [schedule.every().day.at("09:00").do(runner)]


# ---------------------------------------------------------------------------
# Definição genérica de um alerta/job
# ---------------------------------------------------------------------------
@dataclass
class Job:
    nome: str
    executar: Callable[[], None]
    registrar_horarios: Callable[[Callable[[], None]], List["schedule.Job"]] = agenda_todo_dia_hora_cheia


# Cada item de `clientes` pode ser uma string simples ("accor") ou uma
# tupla (nome_exibicao, chave_env) - usada quando o mesmo cliente aparece
# em mais de um alerta, pra cada um ler seu próprio .env (ver Cliente em
# alerta_core/cliente.py pro motivo completo).
ClienteOuTupla = Union[str, tuple]

# Registro de todos os (alerta, cliente_exibicao, chave_env) esperados,
# preenchido conforme os jobs vão sendo montados via job_alerta() logo
# abaixo - usado só pro diagnóstico de inicialização (_diagnosticar_envs_
# faltantes), pra avisar de uma vez só quais .env estão faltando, em vez
# de descobrir aos poucos conforme cada alerta dispara no seu próprio
# horário.
REGISTRO_CLIENTES_ALERTAS: List[dict] = []


def _fazer_executar_alerta(nome: str, descricao: str, clientes: List[ClienteOuTupla]) -> Callable[[], None]:
    """Fábrica: monta a função `executar` padrão pros alertas baseados em Alerta()."""
    def _run() -> None:
        alerta = Alerta(nome=nome, descricao=descricao, clientes=clientes)
        alerta.processar_clientes()
        alerta.ativar_alerta()
    return _run


def job_alerta(
    nome: str,
    descricao: str,
    clientes: List[ClienteOuTupla],
    registrar_horarios: Callable[[Callable[[], None]], List["schedule.Job"]] = agenda_todo_dia_hora_cheia,
) -> Job:
    for c in clientes:
        nome_exibicao, chave_env = c if isinstance(c, tuple) else (c, c)
        REGISTRO_CLIENTES_ALERTAS.append(
            {"alerta": nome, "cliente": nome_exibicao, "chave_env": chave_env}
        )
    return Job(
        nome=nome,
        executar=_fazer_executar_alerta(nome, descricao, clientes),
        registrar_horarios=registrar_horarios,
    )


def _diagnosticar_envs_faltantes() -> List[dict]:
    """Confere, de uma vez só, quais arquivos .env.<chave> esperados pelos
    alertas não existem na pasta do programa. Não impede o programa de
    abrir - só avisa cedo, tudo junto, em vez do solicitante descobrir aos
    poucos conforme cada alerta dispara no seu próprio horário (alguns só
    rodam 1x por dia)."""
    faltando = []
    for item in REGISTRO_CLIENTES_ALERTAS:
        caminho = os.path.join(_base_path_app(), f".env.{item['chave_env'].lower()}")
        if not os.path.exists(caminho):
            faltando.append(item)
    return faltando


def _executar_alertas_tempo_de_empresa_job() -> None:
    """Wrapper fino só pra poder registrar isso aqui em cima, perto do
    resto dos jobs - a implementação de verdade (_executar_alertas_tempo_
    de_empresa) fica lá embaixo, perto do resto do módulo de e-mail (mais
    fácil de manter junto). Resolvido em tempo de EXECUÇÃO (não de
    definição), então funciona mesmo a função real vindo bem depois no
    arquivo - só não pode ser chamada direto na lista JOBS aqui embaixo,
    porque essa lista é montada na carga do módulo, e nesse momento a
    função de verdade ainda não existiria como nome."""
    _executar_alertas_tempo_de_empresa()


def _executar_validacao_ftp() -> None:
    """Lógica original do ValidacaoFTP: conta arquivos parados por cliente
    numa pasta de rede e dispara e-mail se algum cliente passar do limite."""
    ftp_getEnv("email")

    dir_base = os.path.join(
        os.environ.get("PDA_FTP_UNC", r"\\servidor-ftp\FTP"), "integracao"
    )
    dic_clientes = {
        cliente: os.path.join(dir_base, cliente) for cliente in os.listdir(dir_base)
    }

    clientes_acima = {}
    for cliente, caminho in dic_clientes.items():
        dir_datalog = os.path.join(caminho, "Datalog")
        if not os.path.isdir(dir_datalog):
            continue
        total_arq = sum(1 for entry in os.scandir(dir_datalog) if entry.is_file())
        if total_arq >= 100:
            clientes_acima[cliente] = total_arq

    if clientes_acima:
        ftp_execute(clientes_acima)
    else:
        logger.info("Validação FTP: nenhuma pasta acima do limite.")


def _base_path_app() -> str:
    """Resolve a pasta onde o programa está (funciona tanto rodando como
    .py quanto como .exe empacotado). Usado pra achar o .env, o
    usuarios.json, etc. - tudo sempre ao lado do executável/script."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------
# Criptografia de configurações sensíveis (Fernet + config.dat)
# ---------------------------------------------------------------------------
# A lógica de verdade mora em core/config_seguro.py (módulo compartilhado,
# sem dependência de alertas_gui.py) - importante porque o Cliente()
# também usa essa criptografia (pras 30+ credenciais de clientes que
# passam por ali), e alertas_gui.py -> alerta_core -> importaria de volta
# alertas_gui.py se essa lógica estivesse só aqui (import circular). Ver
# core/config_seguro.py pra explicação completa de como funciona e o que
# isso protege de verdade.

from core.config_seguro import (
    carregar_config_dat as _carregar_config_dat,
    definir_valor_config_dat as _definir_valor_config_dat,
    listar_chaves_config_dat as _listar_chaves_config_dat,
    obter_valor_config as _obter_valor_config,
    remover_valor_config_dat as _remover_valor_config_dat,
    salvar_config_dat as _salvar_config_dat,
)

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
            load_dotenv(dotenv_path=env_path, override=True)
        return {chave: os.getenv(chave, "") for chave in chaves}

# ---------------------------------------------------------------------------
# Atualização Dash Financeiro - adaptado do notebook
# Atualizacao_Dash_Financeiro.ipynb que o solicitante mandou. Pra cada produto
# (NFe, CTe, NFCe, CFe, NFSe Out, NFSe In, MDFe, LASA, SaaS), gera um CSV
# mensal com a contagem de documentos por cliente/CNPJ, salvando em
# <PDA_DASH_FINANCEIRO_PASTA>/<Produto>/. Idempotente por mês - se o
# CSV do mês já existir, não faz nada (mesmo comportamento do notebook
# original). As credenciais de banco (23 combinações distintas de
# servidor+banco) são cifradas no config.dat - ver Configurações
# Seguras/CRIPTOGRAFIA.md - não tem fallback pra texto puro porque essa
# automação nasce já protegida, não veio de um .env antigo.
# ---------------------------------------------------------------------------


PASTA_BASE_DASH_FINANCEIRO = os.environ.get("PDA_DASH_FINANCEIRO_PASTA", r"C:\PDA\PowerBI\Financeiro")

# nome da pasta de saída de cada produto - a maioria bate com a chave do
# JSON, só NFSeOut/NFSeIn que têm espaço no nome da pasta de verdade
# (confirmado no print que o solicitante mandou: "NFSe In", "NFSe Out")
NOME_PASTA_POR_PRODUTO = {
    "NFe": "NFe", "CTe": "CTe", "NFCe": "NFCe", "CFe": "CFe",
    "NFSeOut": "NFSe Out", "NFSeIn": "NFSe In", "MDFe": "MDFe",
    "LASA": "LASA", "SaaS": "SaaS",
}


def _carregar_conexoes_dash_financeiro() -> dict:
    caminho = os.path.join(_base_path_app(), "dash_financeiro_conexoes.json")
    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def _obter_senha_dash_financeiro(database: str) -> str:
    """Toda credencial do Dash Financeiro é cifrada no config.dat (não
    tem fallback pra .env em texto puro, porque essa automação é nova -
    nasce já protegida). Chave: dash_financeiro::<nome do banco>."""
    return _obter_valor_config(f"dash_financeiro::{database}", "")


def _conectar_dash_financeiro(server: str, database: str, uid: str):
    senha = _obter_senha_dash_financeiro(database)
    if not senha:
        raise RuntimeError(
            f"Sem senha cadastrada pra '{database}' - cadastre em "
            f"Criptografia de Dados Sensíveis com a chave 'dash_financeiro::{database}'."
        )
    return pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={uid};"
        f"PWD={senha}"
    )


def _periodo_mes_anterior():
    """Mesmo cálculo do notebook: mês anterior completo (do dia 1 ao
    último dia)."""
    hoje = datetime.today()
    data_ini = (hoje.replace(day=1) - relativedelta(months=1)).replace(day=1)
    data_fim = hoje.replace(day=1) - relativedelta(days=1)
    return {
        "arquivo": data_ini.strftime("%Y-%m"),
        "ini": data_ini.strftime("%Y-%m-%d"),
        "fim": data_fim.strftime("%Y-%m-%d"),
        "ini_compacto": data_ini.strftime("%Y%m%d"),  # usado só pelo CFe (formato diferente na query)
        "fim_compacto": data_fim.strftime("%Y%m%d"),
    }


# ---------------------------------------------------------------------------
# Queries por produto - adaptadas 1:1 da lógica do notebook, só trocando
# a leitura de config.dat em vez de senha em texto puro no dicionário.
# ---------------------------------------------------------------------------

def _query_nfe(cliente: str, cnpj_filtro: str, tipo: str, proces: str, periodo: dict, produto="NFe") -> str:
    return f"""
    SELECT
        A.NUM_CNPJ_ESTAB_GERDOR as CNPJ,
        COUNT(A.NUM_SEQ_NFE) as QTD,
        FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
        '{cliente}' as Cliente,
        '{tipo}' as Tipo,
        '{produto}' as Produto,
        B.DSC_SIGLA_FILIAL as Sigla,
        GETDATE() as Atualizacao
    FROM INTERF_NFE A WITH (NOLOCK)
    JOIN ESTAB_GERDOR B WITH (NOLOCK) ON A.NUM_CNPJ_ESTAB_GERDOR = B.NUM_CNPJ_ESTAB_GERDOR
    WHERE A.DAT_REG_NFE > '{periodo["ini"]} 00:00:00' AND A.DAT_REG_NFE < '{periodo["fim"]} 23:59:59'
    AND A.NUM_CNPJ_ESTAB_GERDOR {cnpj_filtro}
    AND A.ind_tipo_proces = '{proces}'
    GROUP BY A.NUM_CNPJ_ESTAB_GERDOR, B.DSC_SIGLA_FILIAL
    ORDER BY QTD DESC
    """


def _query_cte(cliente: str, cnpj_filtro: str, tipo: str, proces: str, periodo: dict) -> str:
    return f"""
    SELECT e.cnpj as CNPJ,
    COUNT(*) QTD,
    FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
    '{cliente}' as Cliente,
    '{tipo}' as Tipo,
    'CTe' as Produto,
    '' as Sigla,
    getdate() as Atualizacao
    FROM INTERF_CTE_XML X WITH (NOLOCK)
    INNER JOIN interf_cte C WITH (NOLOCK) ON C.ID = X.INTERF_CTE_FK
    INNER JOIN empresas E WITH (NOLOCK) ON C.EMPRESA_FK = e.id
    WHERE B_DHEMI > '{periodo["ini"]} 00:00:00' AND B_DHEMI < '{periodo["fim"]} 23:59:59'
    AND e.CNPJ {cnpj_filtro}
    AND c.ind_tipo_proces = '{proces}'
    GROUP BY e.cnpj
    ORDER BY qtd DESC
    """


def _query_nfce(cliente: str, cnpj_filtro: str, periodo: dict) -> str:
    return f"""
    SELECT A.NUM_CNPJ_ESTAB_GERDOR as CNPJ,
    COUNT (A.NUM_SEQ_NFE) as QTD,
    FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
    '{cliente}' as Cliente,
    'Emissao' as Tipo,
    'NFCe' as Produto,
    B.DSC_SIGLA_FILIAL as Sigla,
    getdate() as Atualizacao
    FROM INTERF_NFE A WITH (NOLOCK)
    JOIN ESTAB_GERDOR B WITH (NOLOCK) ON A.NUM_CNPJ_ESTAB_GERDOR = B.NUM_CNPJ_ESTAB_GERDOR
    WHERE A.DAT_REG_NFE > '{periodo["ini"]} 00:00:00' AND A.DAT_REG_NFE < '{periodo["fim"]} 23:59:59'
    AND A.NUM_CNPJ_ESTAB_GERDOR {cnpj_filtro}
    GROUP BY A.NUM_CNPJ_ESTAB_GERDOR, B.DSC_SIGLA_FILIAL
    ORDER BY qtd DESC
    """


def _query_cfe(cliente: str, cnpj_filtro: str, periodo: dict) -> str:
    return f"""
    SELECT
    A.C_CNPJ as CNPJ,
    COUNT(A.NUM_SEQ_CFE) as QTD,
    FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
    '{cliente}' as Cliente,
    'Emissao' as Tipo,
    'CFe' as Produto,
    B.DSC_SIGLA_FILIAL as Sigla,
    getdate() as Atualizacao
    FROM INTERF_CFE A WITH (NOLOCK)
    JOIN ESTAB_GERDOR B WITH (NOLOCK) ON A.C_CNPJ = B.NUM_CNPJ_ESTAB_GERDOR
    WHERE A.B_DATA_HORA_EMISSAO > '{periodo["ini_compacto"]}000000' AND A.B_DATA_HORA_EMISSAO < '{periodo["fim_compacto"]}235959'
    AND A.C_CNPJ {cnpj_filtro}
    GROUP BY A.C_CNPJ, B.DSC_SIGLA_FILIAL
    ORDER BY qtd DESC
    """


def _query_nfse_out(cliente: str, cnpj_filtro: str, periodo: dict) -> str:
    return f"""
    SELECT PRE_CPF_CNPJ AS CNPJ,
    COUNT(*) AS QTD,
    FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
    '{cliente}' as Cliente,
    'Emissao' as Tipo,
    'NFSe Out' as Produto,
    '' as Sigla,
    getdate() as Atualizacao
    FROM INTERF_NFSE_XML WITH (NOLOCK)
    WHERE DAT_HOR_EMIS_RPS > '{periodo["ini"]} 00:00:00' AND DAT_HOR_EMIS_RPS < '{periodo["fim"]} 23:59:59'
    AND PRE_CPF_CNPJ {cnpj_filtro}
    GROUP BY PRE_CPF_CNPJ
    ORDER BY qtd DESC
    """


def _query_nfse_in(cliente: str, cnpj_filtro: str, periodo: dict) -> str:
    return f"""
    SELECT
    c.cnpj as CNPJ,
    COUNT(*) as QTD,
    FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
    '{cliente}' as Cliente,
    'Recebimento' as Tipo,
    'NFSe In' as Produto,
    '' as Sigla,
    getdate() as Atualizacao
    FROM DOCUMENTO_RECEBIDO a,
    TOMADOR c WITH (NOLOCK)
    WHERE a.TOMADOR_FK = c.id
    AND a.dt_emissao > '{periodo["ini"]} 00:00:00' AND a.dt_emissao < '{periodo["fim"]} 23:59:59'
    AND c.cnpj {cnpj_filtro}
    GROUP BY c.cnpj
    ORDER BY qtd DESC
    """


def _query_mdfe(cliente: str, cnpj_filtro: str, periodo: dict) -> str:
    return f"""
    SELECT EMIT_CNPJ as CNPJ,
    COUNT(*) as QTD,
    FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data,
    '{cliente}' as Cliente,
    'Emissao' as Tipo,
    'MDFe' as Produto,
    '' as Sigla,
    getdate() as Atualizacao
    FROM INTERF_MDFE_XML WITH (NOLOCK)
    WHERE dhEmi > '{periodo["ini"]} 00:00:00' AND dhEmi < '{periodo["fim"]} 23:59:59'
    AND EMIT_CNPJ {cnpj_filtro}
    GROUP BY EMIT_CNPJ
    ORDER BY qtd DESC
    """


def _query_lasa(periodo: dict) -> str:
    data_sql = datetime.strptime(periodo["ini"], "%Y-%m-%d").strftime("%m/%Y")
    return f"""
    SELECT
      'LASA' as Cliente,
      CASE
        WHEN IND_TIPO_PROCES = 0 THEN 'Recebimento'
        WHEN IND_TIPO_PROCES = 1 THEN 'Emissao'
        ELSE CAST(IND_TIPO_PROCES as varchar)
      END as Tipo,
      '{data_sql}' as Data,
      COUNT(*) as Eventos
    FROM
      INTERF_EVENTO_FISCAL WITH (NOLOCK)
    WHERE
      IND_STATUS_EVENTO_FISCAL IN (4, 5, 7)
      AND DAT_HOR_EVENTO > '{periodo["ini"]} 00:00:00' AND DAT_HOR_EVENTO < '{periodo["fim"]} 23:59:59'
    GROUP BY
      CASE
        WHEN IND_TIPO_PROCES = 0 THEN 'Recebimento'
        WHEN IND_TIPO_PROCES = 1 THEN 'Emissao'
        ELSE CAST(IND_TIPO_PROCES as varchar)
      END
    """


# ---------------------------------------------------------------------------
# Orquestração - um "motor" genérico pros 7 produtos que seguem o padrão
# "lista de conexões + tipo/proces variando" (NFe, CTe, NFCe, CFe, NFSe
# Out, NFSe In, MDFe), e um tratamento especial pro LASA (conexão única,
# sem variação de tipo) e pro SaaS (query fixa por banco, não por
# "cliente").
# ---------------------------------------------------------------------------

# produtos que variam por (tipo, proces) - NFe e CTe
PRODUTOS_COM_TIPO_PROCES = {
    "NFe": {"tipos": ["Emissao", "Recebimento"], "proces": ["E", "R"], "query_fn": _query_nfe},
    "CTe": {"tipos": ["Emissao", "Recebimento"], "proces": ["1", "2"], "query_fn": _query_cte},
}

# produtos com 1 query só por conexão (sem variar tipo/proces)
PRODUTOS_QUERY_UNICA = {
    "NFCe": _query_nfce,
    "CFe": _query_cfe,
    "NFSeOut": _query_nfse_out,
    "NFSeIn": _query_nfse_in,
    "MDFe": _query_mdfe,
}


def _caminho_saida_produto(produto: str) -> str:
    nome_pasta = NOME_PASTA_POR_PRODUTO.get(produto, produto)
    return os.path.join(PASTA_BASE_DASH_FINANCEIRO, nome_pasta)


def _verificar_permissao_escrita(pasta: str) -> Optional[str]:
    """Confirma que dá pra escrever nessa pasta ANTES de gastar minutos
    consultando 20+ bancos - sem essa checagem, um problema de permissão
    só aparecia no final (na hora de salvar o CSV), depois de já ter
    rodado todas as queries à toa. Tenta criar e apagar um arquivo
    temporário; se falhar, devolve uma mensagem de erro clara (ou None
    se está tudo certo)."""
    caminho_teste = os.path.join(pasta, f".teste_permissao_{os.getpid()}.tmp")
    try:
        with open(caminho_teste, "w") as f:
            f.write("teste")
        os.remove(caminho_teste)
        return None
    except PermissionError as e:
        return (
            f"Sem permissão de escrita em '{pasta}'. Isso costuma ser uma "
            f"questão de ACL da pasta no Windows (comum quando ela está num "
            f"disco diferente do resto do programa) - confirme se a conta "
            f"que roda o serviço tem permissão de Gravação nessa pasta "
            f"específica (clique direito → Propriedades → Segurança), ou se "
            f"algum arquivo lá dentro está aberto em outro programa "
            f"(Excel, por exemplo). Erro original: {e}"
        )
    except Exception as e:
        return f"Não foi possível confirmar permissão de escrita em '{pasta}': {e}"


def _salvar_csv_com_retentativa(df: "pd.DataFrame", caminho: str, tentativas: int = 3) -> Optional[str]:
    """Salva o CSV com algumas tentativas curtas antes de desistir - cobre
    o caso comum de um bloqueio BREVE (antivírus escaneando o arquivo
    recém-criado, um sync de OneDrive/backup passando por cima, etc.).
    Não resolve uma permissão de verdade negada (ACL), só o bloqueio
    passageiro. Devolve a mensagem de erro final, ou None se salvou."""
    ultimo_erro = None
    for tentativa in range(1, tentativas + 1):
        try:
            df.to_csv(caminho, index=False)
            return None
        except PermissionError as e:
            ultimo_erro = e
            if tentativa < tentativas:
                time.sleep(1.5)
    return (
        f"Sem permissão pra gravar '{caminho}' mesmo após {tentativas} tentativas. "
        f"Confirme a permissão de escrita da pasta pra conta que roda o serviço, "
        f"ou se o arquivo está aberto em outro programa. Erro original: {ultimo_erro}"
    )


def _executar_produto_padrao(produto: str, conexoes: list) -> dict:
    """Produtos com lista de conexões (NFe, CTe, NFCe, CFe, NFSe Out,
    NFSe In, MDFe). Uma conexão com erro não derruba as outras - só é
    pulada e reportada no resumo (mesma robustez que o notebook original
    já tinha pro NFSe Out, aplicada em todos aqui)."""
    periodo = _periodo_mes_anterior()
    pasta_saida = _caminho_saida_produto(produto)
    arquivo_mes = os.path.join(pasta_saida, f"{periodo['arquivo']}.csv")
    arquivo_consolidado = os.path.join(pasta_saida, "df_consolidado.csv")

    if os.path.exists(arquivo_mes):
        return {"ok": True, "pulado": True, "motivo": f"{periodo['arquivo']}.csv já existe"}

    os.makedirs(pasta_saida, exist_ok=True)

    erro_permissao = _verificar_permissao_escrita(pasta_saida)
    if erro_permissao:
        return {"ok": False, "erro": erro_permissao}

    todos_dados = []
    erros = []

    variacoes = []
    if produto in PRODUTOS_COM_TIPO_PROCES:
        info = PRODUTOS_COM_TIPO_PROCES[produto]
        for tipo, proces in zip(info["tipos"], info["proces"]):
            variacoes.append((tipo, proces))
    else:
        variacoes = [(None, None)]

    for conexao_cfg in conexoes:
        for tipo, proces in variacoes:
            try:
                conn = _conectar_dash_financeiro(
                    conexao_cfg["server"], conexao_cfg["database"], conexao_cfg["uid"]
                )
                try:
                    if produto in PRODUTOS_COM_TIPO_PROCES:
                        query_fn = PRODUTOS_COM_TIPO_PROCES[produto]["query_fn"]
                        sql = query_fn(conexao_cfg["cliente"], conexao_cfg["cnpj"], tipo, proces, periodo)
                    else:
                        query_fn = PRODUTOS_QUERY_UNICA[produto]
                        sql = query_fn(conexao_cfg["cliente"], conexao_cfg["cnpj"], periodo)
                    df = pd.read_sql(sql, conn)
                    todos_dados.append(df)
                finally:
                    conn.close()
            except Exception as e:
                erros.append(f"{conexao_cfg['cliente']} ({conexao_cfg['database']}): {e}")
                logger_dash_financeiro.warning(
                    "Dash Financeiro (%s): erro ao consultar %s: %s",
                    produto, conexao_cfg["cliente"], e,
                )

    if not todos_dados:
        return {"ok": False, "erro": "Nenhuma consulta retornou dados.", "erros_individuais": erros}

    df_mensal = pd.concat(todos_dados, ignore_index=True)
    erro_gravacao = _salvar_csv_com_retentativa(df_mensal, arquivo_mes)
    if erro_gravacao:
        return {"ok": False, "erro": erro_gravacao, "erros_individuais": erros}

    if os.path.exists(arquivo_consolidado):
        df_consolidado = pd.read_csv(arquivo_consolidado)
        df_final = pd.concat([df_consolidado, df_mensal], ignore_index=True)
    else:
        df_final = df_mensal
    erro_gravacao_consolidado = _salvar_csv_com_retentativa(df_final, arquivo_consolidado)
    if erro_gravacao_consolidado:
        return {"ok": False, "erro": erro_gravacao_consolidado, "erros_individuais": erros}

    return {
        "ok": True, "pulado": False, "linhas": len(df_mensal),
        "conexoes_com_erro": len(erros), "erros_individuais": erros,
    }


def _executar_lasa(conexoes: list) -> dict:
    periodo = _periodo_mes_anterior()
    pasta_saida = _caminho_saida_produto("LASA")
    arquivo_mes = os.path.join(pasta_saida, f"{periodo['arquivo']}.csv")
    arquivo_consolidado = os.path.join(pasta_saida, "df_consolidado.csv")

    if os.path.exists(arquivo_mes):
        return {"ok": True, "pulado": True, "motivo": f"{periodo['arquivo']}.csv já existe"}

    os.makedirs(pasta_saida, exist_ok=True)

    erro_permissao = _verificar_permissao_escrita(pasta_saida)
    if erro_permissao:
        return {"ok": False, "erro": erro_permissao}

    cfg = conexoes[0]
    conn = _conectar_dash_financeiro(cfg["server"], cfg["database"], cfg["uid"])
    try:
        df_mensal = pd.read_sql(_query_lasa(periodo), conn)
    finally:
        conn.close()

    erro_gravacao = _salvar_csv_com_retentativa(df_mensal, arquivo_mes)
    if erro_gravacao:
        return {"ok": False, "erro": erro_gravacao}

    if os.path.exists(arquivo_consolidado):
        df_consolidado = pd.read_csv(arquivo_consolidado)
        df_final = pd.concat([df_consolidado, df_mensal], ignore_index=True)
    else:
        df_final = df_mensal
    erro_gravacao_consolidado = _salvar_csv_com_retentativa(df_final, arquivo_consolidado)
    if erro_gravacao_consolidado:
        return {"ok": False, "erro": erro_gravacao_consolidado}

    return {"ok": True, "pulado": False, "linhas": len(df_mensal)}


def _queries_saas(periodo: dict) -> list:
    """As 7 queries fixas do SaaS - uma por banco, na MESMA ordem da
    lista de bancos em dash_financeiro_conexoes.json (SaaS.bancos).
    Cada uma já embute o nome do produto correspondente na própria
    query (igual o notebook original fazia)."""
    return [
        f"""
        SELECT
        	inf.num_cnpj_estab_gerdor as CNPJ,
        	eg.nom_estab_gerdor as 'RazaoSocial',
        	ga.NOM_GRUPO_ACESSO as Cliente,
        	COUNT(inf.NUM_SEQ_NFE) as QTD,
        	'NFe' as Produto,
        	CASE
        		WHEN inf.IND_TIPO_PROCES = 'E' THEN 'Emissao'
        		WHEN inf.IND_TIPO_PROCES = 'R' THEN 'Recebimento'
        	END as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM INTERF_NFE inf WITH (NOLOCK)
        	JOIN estab_gerdor eg WITH (NOLOCK)
        		ON inf.num_cnpj_estab_gerdor = eg.num_cnpj_estab_gerdor
        		JOIN PERMSS_ACESSO_EMIS pae WITH (NOLOCK)
        			ON eg.num_cnpj_estab_gerdor = pae.NUM_CNPJ_EMIS
        			JOIN GRUPO_ACESSO ga WITH (NOLOCK)
        				ON pae.NUM_SEQ_GRUPO_ACESSO = ga.NUM_SEQ_GRUPO_ACESSO
        WHERE inf.DAT_REG_NFE BETWEEN '{periodo["ini"]} 00:00:00' AND '{periodo["fim"]} 23:59:59'
        	AND inf.num_cnpj_estab_gerdor IS NOT NULL
        	AND inf.IND_TIPO_PROCES in ('E', 'R')
        GROUP BY inf.num_cnpj_estab_gerdor, inf.IND_TIPO_PROCES, eg.nom_estab_gerdor, ga.NOM_GRUPO_ACESSO
        ORDER BY QTD DESC
        """,
        f"""
        SELECT
        	emp.CNPJ as CNPJ,
        	emp.RAZAO_SOCIAL as 'RazaoSocial',
        	CASE
        		WHEN gp.NOME_GRUPO IS NULL THEN 'Nao Especificado'
        		ELSE gp.NOME_GRUPO
        	END as Cliente,
        	COUNT(*) as QTD,
        	'CTe' as Produto,
        	CASE
        		WHEN IND_TIPO_PROCES = '1' THEN 'Emissao'
        		WHEN IND_TIPO_PROCES = '2' THEN 'Recebimento'
        	END as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM INTERF_CTE_XML incx WITH (NOLOCK)
        	INNER JOIN INTERF_CTE inc with (NOLOCK)
        		ON incx.INTERF_CTE_FK = inc.ID
        		INNER JOIN EMPRESAS emp WITH(NOLOCK)
        			ON inc.EMPRESA_FK = emp.ID
        			INNER JOIN GRUPO_EMPRESA gp
        				ON emp.GRUPO_EMPRESA_FK = gp.ID
        WHERE B_DHEMI BETWEEN '{periodo["ini"]} 00:00:00' AND '{periodo["fim"]} 23:59:59'
        	AND emp.CNPJ IS NOT NULL
        	AND inc.IND_TIPO_PROCES IN ('1', '2')
        GROUP BY emp.CNPJ, inc.IND_TIPO_PROCES, emp.RAZAO_SOCIAL, gp.NOME_GRUPO
        ORDER BY QTD DESC
        """,
        f"""
        SELECT top 10
        	inf.num_cnpj_estab_gerdor as CNPJ,
        	eg.nom_estab_gerdor as 'RazaoSocial',
        	CASE
        		WHEN ga.NOM_GRUPO_ACESSO IS NULL THEN 'Nao Especificado'
        		ELSE ga.NOM_GRUPO_ACESSO
        	END as Cliente,
        	COUNT(inf.NUM_SEQ_NFE) as QTD,
        	'NFCe' as Produto,
        	'Emissao' as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM interf_nfe as inf WITH (NOLOCK)
        	JOIN ESTAB_GERDOR eg WITH (NOLOCK)
        		ON inf.num_cnpj_estab_gerdor = eg.num_cnpj_estab_gerdor
        		JOIN PERMSS_ACESSO_EMIS pae WITH (NOLOCK)
        			ON eg.num_cnpj_estab_gerdor = pae.NUM_CNPJ_EMIS
        			JOIN GRUPO_ACESSO ga WITH (NOLOCK)
        				ON pae.NUM_SEQ_GRUPO_ACESSO = ga.NUM_SEQ_GRUPO_ACESSO
        WHERE inf.DAT_REG_NFE BETWEEN '{periodo["ini"]} 00:00:00' AND '{periodo["fim"]} 23:59:59'
        	AND inf.num_cnpj_estab_gerdor IS NOT NULL
        GROUP BY inf.num_cnpj_estab_gerdor, eg.nom_estab_gerdor, ga.NOM_GRUPO_ACESSO
        ORDER BY QTD DESC
        """,
        f"""
        SELECT
        	inc.C_CNPJ as CNPJ,
        	eg.nom_estab_gerdor as 'RazaoSocial',
        	ga.NOM_GRUPO_ACESSO as Cliente,
        	COUNT(inc.NUM_SEQ_CFE) as QTD,
        	'CFe' as Produto,
        	'Emissao' as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM INTERF_CFE inc WITH (NOLOCK)
        	JOIN estab_gerdor eg WITH (NOLOCK)
        	 ON inc.C_CNPJ = eg.num_cnpj_estab_gerdor
        	 JOIN PERMSS_ACESSO_EMIS pae WITH (NOLOCK)
        		ON eg.num_cnpj_estab_gerdor = pae.NUM_CNPJ_EMIS
        		JOIN GRUPO_ACESSO ga WITH (NOLOCK)
        			ON pae.NUM_SEQ_GRUPO_ACESSO = ga.NUM_SEQ_GRUPO_ACESSO
        WHERE inc.B_DATA_HORA_EMISSAO BETWEEN '{periodo["ini_compacto"]}000000' AND '{periodo["fim_compacto"]}235959'
        	AND inc.C_CNPJ IS NOT NULL
        GROUP BY inc.C_CNPJ, eg.nom_estab_gerdor, ga.NOM_GRUPO_ACESSO
        ORDER BY QTD DESC
        """,
        f"""
        SELECT
        	PRE_CPF_CNPJ as CNPJ,
        	PRE_RAZSOC as 'RazaoSocial',
        	'Nao Especificado' as Cliente,
        	COUNT(*) as QTD,
        	'NFSeOut' as Produto,
        	'Emissao' as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM INTERF_NFSE_XML WITH (NOLOCK)
        WHERE DAT_HOR_EMIS_RPS BETWEEN '{periodo["ini"]} 00:00:00' AND '{periodo["fim"]} 23:59:59'
        	AND PRE_CPF_CNPJ IS NOT NULL
            AND NOT PRE_CPF_CNPJ = '61031928000128'
        GROUP BY PRE_CPF_CNPJ, PRE_RAZSOC
        ORDER BY QTD DESC
        """,
        f"""
        SELECT
        	tom.CNPJ as CNPJ,
        	tom.RAZAO_SOCIAL as 'RazaoSocial',
        	CASE
        		WHEN ge.NOME IS NULL THEN 'Nao Especificado'
        		ELSE ge.NOME
        	END as Cliente,
        	COUNT(*) as QTD,
        	'NFSeIn' as Produto,
        	'Recebimento' as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM DOCUMENTO_RECEBIDO dr
        	JOIN TOMADOR tom WITH (NOLOCK)
        		ON dr.TOMADOR_FK = tom.ID
        		JOIN GRUPO_EMPRESA ge WITH (NOLOCK)
        			ON tom.GRUPO_EMPRESA_FK = ge.ID
        WHERE dr.DT_EMISSAO BETWEEN '{periodo["ini"]} 00:00:00' AND '{periodo["fim"]} 23:59:59'
        	AND tom.CNPJ IS NOT NULL
        GROUP BY tom.CNPJ, tom.RAZAO_SOCIAL, ge.NOME
        ORDER BY QTD DESC
        """,
        f"""
        SELECT
        	imd.EMIT_CNPJ as CNPJ,
        	emp.RAZAO_SOCIAL as 'RazaoSocial',
        	CASE
        		WHEN ge.NOME_GRUPO IS NULL THEN 'Nao Especificado'
        		ELSE ge.NOME_GRUPO
        	END as Cliente,
        	COUNT(*) as QTD,
        	'MDFe' as Produto,
        	'Emissao' as Tipo,
        	FORMAT(DATEADD(MONTH, -1, GETDATE()), 'MM/yyyy') as Data
        FROM INTERF_MDFE_XML imd WITH (NOLOCK)
        	JOIN EMPRESAS emp WITH (NOLOCK)
        		ON imd.EMIT_CNPJ = emp.CNPJ
        		JOIN GRUPO_EMPRESA ge WITH (NOLOCK)
        			ON emp.GRUPO_EMPRESA_FK = ge.ID
        WHERE dhEmi > '{periodo["ini"]} 00:00:00' AND dhEmi < '{periodo["fim"]} 23:59:59'
        	AND imd.EMIT_CNPJ IS NOT NULL
        GROUP BY imd.EMIT_CNPJ, emp.RAZAO_SOCIAL, ge.NOME_GRUPO
        ORDER BY QTD DESC
        """,
    ]


def _executar_saas(conexao_base: dict) -> dict:
    """Caso especial: 1 servidor/usuário, 7 bancos diferentes (um por
    produto), 7 queries fixas (não filtra por 'cliente' como os outros -
    já vem com o Grupo de Acesso certo direto da query). Reaproveita as
    MESMAS chaves de senha em config.dat que os outros produtos já usam
    pra esses bancos (dash_financeiro::<banco>), não precisa cadastrar
    de novo."""
    periodo = _periodo_mes_anterior()
    pasta_saida = _caminho_saida_produto("SaaS")
    arquivo_mes = os.path.join(pasta_saida, f"{periodo['arquivo']}.csv")
    arquivo_consolidado = os.path.join(pasta_saida, "df_consolidado.csv")

    if os.path.exists(arquivo_mes):
        return {"ok": True, "pulado": True, "motivo": f"{periodo['arquivo']}.csv já existe"}

    os.makedirs(pasta_saida, exist_ok=True)

    erro_permissao = _verificar_permissao_escrita(pasta_saida)
    if erro_permissao:
        return {"ok": False, "erro": erro_permissao}

    bancos = conexao_base["bancos"]
    queries = _queries_saas(periodo)
    todos_produtos = []
    erros = []

    for banco, sql in zip(bancos, queries):
        try:
            conn = _conectar_dash_financeiro(conexao_base["server"], banco, conexao_base["uid"])
            try:
                df = pd.read_sql(sql, conn)
                todos_produtos.append(df)
            finally:
                conn.close()
        except Exception as e:
            erros.append(f"{banco}: {e}")
            logger_dash_financeiro.warning("Dash Financeiro (SaaS): erro ao consultar %s: %s", banco, e)

    if not todos_produtos:
        return {"ok": False, "erro": "Nenhuma consulta retornou dados.", "erros_individuais": erros}

    df_produtos = pd.concat(todos_produtos, ignore_index=True)
    df_produtos["Cliente"] = df_produtos["Cliente"].apply(
        lambda cliente: str(cliente).split("_")[0].split("/")[0].split("-")[0].strip()
    )
    df_produtos = df_produtos.drop_duplicates()

    erro_gravacao = _salvar_csv_com_retentativa(df_produtos, arquivo_mes)
    if erro_gravacao:
        return {"ok": False, "erro": erro_gravacao, "erros_individuais": erros}

    if os.path.exists(arquivo_consolidado):
        df_consolidado = pd.read_csv(arquivo_consolidado)
        df_final = pd.concat([df_consolidado, df_produtos], ignore_index=True)
    else:
        df_final = df_produtos
    erro_gravacao_consolidado = _salvar_csv_com_retentativa(df_final, arquivo_consolidado)
    if erro_gravacao_consolidado:
        return {"ok": False, "erro": erro_gravacao_consolidado, "erros_individuais": erros}

    return {
        "ok": True, "pulado": False, "linhas": len(df_produtos),
        "conexoes_com_erro": len(erros), "erros_individuais": erros,
    }


def executar_produto_dash_financeiro(produto: str, conexoes_json: dict) -> dict:
    """Ponto de entrada único - roteia pro tratamento certo de acordo com
    o produto."""
    try:
        if produto == "LASA":
            return _executar_lasa(conexoes_json["LASA"])
        elif produto == "SaaS":
            return _executar_saas(conexoes_json["SaaS"])
        elif produto in conexoes_json:
            return _executar_produto_padrao(produto, conexoes_json[produto])
        else:
            return {"ok": False, "erro": f"Produto '{produto}' não reconhecido."}
    except Exception as e:
        logger_dash_financeiro.exception("Erro inesperado no Dash Financeiro (%s)", produto)
        return {"ok": False, "erro": str(e)}


ORDEM_PRODUTOS_DASH_FINANCEIRO = [
    "NFe", "CTe", "NFCe", "CFe", "NFSeOut", "NFSeIn", "MDFe", "LASA", "SaaS",
]

# status da última execução de cada produto NESSA SESSÃO (reseta ao
# reiniciar o programa) - lido pela tela web, sem precisar reprocessar
# nada só pra mostrar o que já rodou. Quando isso está vazio (None), a
# tela cai pro status real do arquivo em disco (ver _status_disco_produto)
# - assim, depois de reiniciar o programa, a tela não mostra "nunca
# rodou" pra produtos que na verdade já têm o CSV do mês salvo.
estado_dash_financeiro: dict = {produto: None for produto in ORDEM_PRODUTOS_DASH_FINANCEIRO}
_lock_dash_financeiro = threading.Lock()

# produtos que estão sendo processados NESTE EXATO MOMENTO - a tela usa
# isso pra mostrar "Rodando"/"Gerando arquivo" em vez de um status parado
_produtos_em_execucao: set = set()

# true enquanto uma rodada completa (os 9 produtos) estiver em andamento -
# usado pra IMPEDIR que cliques repetidos em "Executar agora" disparem
# várias rodadas ao mesmo tempo, cada uma reconsultando os mesmos bancos
_dash_financeiro_execucao_ativa = False


def _status_disco_produto(produto: str) -> Optional[dict]:
    """Monta um status "sintético" a partir do que já está salvo em
    disco, pra quando a sessão atual ainda não processou esse produto
    (por exemplo, logo depois de reiniciar o programa). Sem isso, a tela
    mostraria "nunca rodou" pra produtos que, na verdade, já têm o CSV do
    mês certinho - só que salvo numa execução de uma sessão anterior.
    Devolve None só se REALMENTE nunca gerou nada pra esse produto."""
    pasta = _caminho_saida_produto(produto)
    if not os.path.isdir(pasta):
        return None

    periodo_atual = _periodo_mes_anterior()
    arquivo_mes_atual = os.path.join(pasta, f"{periodo_atual['arquivo']}.csv")
    if os.path.isfile(arquivo_mes_atual):
        mtime = datetime.fromtimestamp(os.path.getmtime(arquivo_mes_atual))
        return {
            "ok": True, "pulado": True,
            "motivo": f"{periodo_atual['arquivo']}.csv já existe",
            "executado_em": mtime.strftime("%d/%m/%Y %H:%M:%S"),
            "atualizado_no_mes": True,
        }

    # não tem o arquivo do mês atual - procura o mais recente que existir,
    # pra pelo menos avisar "a última vez que rodou foi em tal data",
    # em vez de simplesmente dizer que nunca rodou
    try:
        candidatos = [
            f for f in os.listdir(pasta)
            if re.fullmatch(r"\d{4}-\d{2}\.csv", f)
        ]
    except OSError:
        return None
    if not candidatos:
        return None

    mais_recente = max(candidatos, key=lambda f: os.path.getmtime(os.path.join(pasta, f)))
    mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(pasta, mais_recente)))
    return {
        "ok": True, "pulado": True,
        "motivo": f"último arquivo salvo foi {mais_recente}",
        "executado_em": mtime.strftime("%d/%m/%Y %H:%M:%S"),
        "atualizado_no_mes": False,
    }


def _executar_todos_dash_financeiro() -> dict:
    """Roda os 9 produtos em sequência, atualizando o status de cada um
    conforme vai processando (a tela web consulta esse status a
    qualquer momento, mesmo com a execução ainda em andamento)."""
    global _dash_financeiro_execucao_ativa
    conexoes_json = _carregar_conexoes_dash_financeiro()
    resumo = {}
    try:
        _dash_financeiro_execucao_ativa = True
        for produto in ORDEM_PRODUTOS_DASH_FINANCEIRO:
            with _lock_dash_financeiro:
                _produtos_em_execucao.add(produto)
            try:
                logger_dash_financeiro.info("Dash Financeiro: iniciando %s...", produto)
                resultado = executar_produto_dash_financeiro(produto, conexoes_json)
                resumo[produto] = resultado
                with _lock_dash_financeiro:
                    estado_dash_financeiro[produto] = {
                        **resultado,
                        "executado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                    }
                if resultado.get("ok"):
                    if resultado.get("pulado"):
                        logger_dash_financeiro.info("Dash Financeiro: %s pulado (%s).", produto, resultado.get("motivo"))
                    else:
                        logger_dash_financeiro.info(
                            "Dash Financeiro: %s concluído (%s linha(s), %s erro(s) de conexão).",
                            produto, resultado.get("linhas"), resultado.get("conexoes_com_erro", 0),
                        )
                else:
                    logger_dash_financeiro.error("Dash Financeiro: %s falhou - %s", produto, resultado.get("erro"))
            finally:
                with _lock_dash_financeiro:
                    _produtos_em_execucao.discard(produto)
    finally:
        _dash_financeiro_execucao_ativa = False
    return resumo


HORARIO_DASH_FINANCEIRO_AUTOMATICO = "07:00"


def _executar_dash_financeiro_mensal_se_dia_1() -> None:
    """A lib 'schedule' não tem agendamento nativo por dia do mês - só dá
    pra agendar por dia da semana/hora/intervalo. Então agenda essa
    função pra rodar TODO DIA nesse horário, e ela mesma decide se é
    dia 1 antes de fazer alguma coisa de verdade. Seguro mesmo se
    rodar mais de uma vez no dia 1 (reinício do programa, por exemplo)
    porque cada produto já é idempotente por mês por conta própria."""
    global _dash_financeiro_execucao_ativa
    if datetime.now().day != 1:
        return
    with _lock_dash_financeiro:
        if _dash_financeiro_execucao_ativa:
            logger_dash_financeiro.info(
                "Dash Financeiro: já tem uma execução em andamento (provavelmente manual) - "
                "pulando o disparo automático do dia 1 dessa vez."
            )
            return
        _dash_financeiro_execucao_ativa = True
    logger_dash_financeiro.info("Dash Financeiro: dia 1 do mês - iniciando execução automática mensal.")
    _executar_todos_dash_financeiro()



def _executar_valor_zerado_bmw() -> None:
    """Zera o status de documentos rejeitados por 'valor de serviço 0' pra
    reprocessamento, para os tomadores BMW. Lógica SQL identica ao script
    original valor_zerado_BMW.py - só a leitura do .env e o logging que
    foram adaptados pra entrar no padrão do painel."""
    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seção [infra_bmw_valor_zerado]),
    # cai pro .env tradicional (bare, sem sufixo) se essa seção não existir.
    valores = _obter_config_hibrido(
        "infra_bmw_valor_zerado", ".env",
        ["DB_SERVER", "DB_DATABASE", "DB_USER", "DB_PASSWORD"],
    )
    servidor = valores["DB_SERVER"]
    banco = valores["DB_DATABASE"]
    usuario = valores["DB_USER"]
    senha = _obter_valor_config("bmw::DB_PASSWORD", valores["DB_PASSWORD"])

    conn = None
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={servidor};"
            f"DATABASE={banco};"
            f"UID={usuario};"
            f"PWD={senha};"
        )
        cursor = conn.cursor()

        sql = """
        update documento_recebido
        set ind_status = 1
        from documento_recebido DR INNER JOIN EVENTOS_DOC_RECEBIDO ES ON DR.ID = ES.DOCUMENTO_RECEBIDO_FK
        where DR.val_servico = 0.0000
            and DR.tomador_fk in (68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 79)
            and DR.ind_status = 3
            AND ES.MENSAGEM LIKE '%Valor total do serviço não pode ser 0%'
            AND dt_emissao >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
            AND DT_EMISSAO >= DATEADD(DAY, -1, GETDATE())
        """
        cursor.execute(sql)
        conn.commit()
        logger.info("Valor Zerado BMW: %d registro(s) atualizado(s).", cursor.rowcount)
        cursor.close()
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Lista de jobs
# ---------------------------------------------------------------------------
JOBS: List[Job] = [
    job_alerta(
        nome="Pendências Datalog NFSe",
        descricao="Documentos não processados pela Datalog.",
        clientes=[("saas", "saas__pendencias_datalog")],
    ),
    job_alerta(
        nome="NFSe Status Transitório",
        descricao=(
            "Documentos fiscais da Accor com status 'Transitório' por "
            "mais de 15 minutos."
        ),
        clientes=["accor"],
    ),
    job_alerta(
        nome="Manifestações",
        descricao=(
            "Documentos fiscais no qual deveriam ter sido manifestados "
            "automaticamente pela aplicação e não foram."
        ),
        clientes=[
            ("acom", "acom__manifestacoes"),
            ("nissei", "nissei__manifestacoes"),
            ("saas2", "saas2__manifestacoes"),
        ],
    ),
    job_alerta(
        nome="Retorno Personalizado Nissei",
        descricao=(
            "Documentos no qual possuem retorno personalizado configurado "
            "porém não obtiveram retorno."
        ),
        clientes=[
            ("nissei", "nissei__retorno_personalizado"),
            ("acom", "acom__retorno_personalizado"),
        ],
    ),
    job_alerta(
        nome="Fila de E-mail",
        descricao="E-mails não processados na fila de envio.",
        clientes=[("saas", "saas__fila_email")],
    ),
    job_alerta(
        nome="Fila de Processamento",
        descricao=(
            "Documentos travados na fila de processamento em status "
            "transitório."
        ),
        clientes=[
            "Accor-NFSe1",
            "Accor-NFSe2",
            "MyrpEnterprise",
            "MyrpStandart",
            "Nissei-NFe",
            "Nissei-CTe",
            "SaaS-NFe",
            "SaaS-CTe",
            "SaaS-NFSe1",
            "SaaS-NFSe2",
        ],
    ),
    job_alerta(
        nome="CTe2 SaaS Status Inicial",
        descricao=(
            "Documentos CTe2 do SaaS de notas parados em status 0, 1 ou 2 "
            "por mais de 15 minutos."
        ),
        clientes=[("saas", "saas__cte2_status_inicial")],
        registrar_horarios=agenda_dias_uteis_meia_hora_06_22,
    ),
    Job(
        nome="Validação FTP",
        executar=_executar_validacao_ftp,
        registrar_horarios=agenda_dias_uteis_hora_cheia_08_17,
    ),
    job_alerta(
        nome="NFe Status Transitório",
        descricao=(
            "Documentos fiscais NFe com status 'Transitório' (1, 2, 14) "
            "por mais de 30 minutos."
        ),
        clientes=[
            "myrpenterprise",
            "myrpstandart",
            ("nissei", "nissei__nfe_status_transitorio"),
            ("saas", "saas__nfe_status_transitorio"),
            ("saas2", "saas2__nfe_status_transitorio"),
        ],
    ),
    job_alerta(
        nome="CTe em Status 30",
        descricao="CTe travados em status 30 (Recebido Fornecedor)",
        clientes=[("saas", "saas__cte_status_30")],
    ),
    job_alerta(
        nome="CTe Incompleto Tramontina",
        descricao="CTe travados em status 0 (Incompleto) na Tramontina",
        clientes=[("saas", "saas__cte_incompleto_tramontina")],
    ),
    # "Valor Zerado BMW" desativado a pedido do solicitante (04/09/2026) - a
    # função _executar_valor_zerado_bmw() continua no código, só não é
    # mais registrada/agendada. Pra reativar, é só descomentar o Job
    # abaixo.
    # Job(
    #     nome="Valor Zerado BMW",
    #     executar=_executar_valor_zerado_bmw,
    #     registrar_horarios=agenda_a_cada_4_horas,
    # ),
    Job(
        nome="Alertas de Tempo de Empresa (45/90 dias)",
        executar=_executar_alertas_tempo_de_empresa_job,
        registrar_horarios=agenda_todo_dia_as_09,
    ),
    # --- Adicione os próximos alertas aqui ---
]


# ---------------------------------------------------------------------------
# Estado de execução (só é mexido pela thread da GUI, nunca pelas workers)
# ---------------------------------------------------------------------------
@dataclass
class JobState:
    job: Job
    scheduled: List["schedule.Job"] = field(default_factory=list)
    running: bool = False
    status: str = "Aguardando"
    last_run: Optional[str] = None
    last_error: Optional[str] = None
    row_id: Optional[str] = None  # id da linha no Treeview
    _proxima_cache: Optional[datetime] = field(default=None, repr=False, compare=False)


def _proxima_execucao(state: JobState) -> Optional[datetime]:
    """Calcula a próxima execução agendada de um job, com cache - evita
    varrer centenas de horários (ex.: o CTe2 tem 165) a cada poll de 2s
    da página web. Só recalcula quando o horário em cache já passou."""
    agora = datetime.now()
    if state._proxima_cache is not None and state._proxima_cache > agora:
        return state._proxima_cache
    proximos = [j.next_run for j in state.scheduled if j.next_run]
    state._proxima_cache = min(proximos) if proximos else None
    return state._proxima_cache


# ---------------------------------------------------------------------------
# Logging: arquivo rotativo + histórico compartilhado, com número de
# sequência em cada linha - dá pra web pedir só "o que é novo desde X" em
# vez de reenviar tudo a cada poll (economiza banda e trabalho de DOM)
# ---------------------------------------------------------------------------
log_history: "deque" = deque(maxlen=500)
_log_seq_lock = threading.Lock()
_log_seq_contador = 0

logger = logging.getLogger("alertas")
logger.setLevel(logging.INFO)

_formatter = logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# Todos os logs ficam dentro de uma pasta "logs" ao lado do programa - um
# arquivo por card/automação, em vez de tudo misturado (como o Alertas
# Suporte fazia antes, juntando registro de todos os outros cards
# também). Cada logger abaixo é FILHO de "alertas" (nome com ponto tipo
# "alertas.dash_financeiro") - herda o nível e continua aparecendo no
# painel/histórico compartilhado normalmente, só GANHA um arquivo
# próprio além disso.
_PASTA_LOGS = os.path.join(_base_path_app(), "logs")
os.makedirs(_PASTA_LOGS, exist_ok=True)


def _criar_handler_arquivo(nome_arquivo: str, max_mb: int = 5, backups: int = 5) -> RotatingFileHandler:
    """Cria o handler de log rotativo pro arquivo dentro de `_PASTA_LOGS`.
    Se não conseguir escrever lá (ex.: log criado por OUTRO usuário do
    Windows numa sessão anterior, com ACL que não dá permissão de
    gravação pro usuário atual - Errno 13), cai pra um arquivo equivalente
    dentro da pasta temporária do sistema em vez de derrubar a aplicação
    inteira, avisando no console. Mesmo padrão já usado no
    monitor_emailpack_gui_corrigido_30min.py, só que aqui com
    RotatingFileHandler (em vez de FileHandler simples) já que essa função
    também controla tamanho/backup, e com nome de fallback por arquivo
    (em vez de um nome fixo) porque essa função é chamada várias vezes,
    uma por card/automação.
    """
    caminho = os.path.join(_PASTA_LOGS, nome_arquivo)
    try:
        handler = RotatingFileHandler(
            caminho,
            maxBytes=max_mb * 1024 * 1024, backupCount=backups, encoding="utf-8",
        )
    except (PermissionError, OSError) as e:
        caminho_fallback = os.path.join(tempfile.gettempdir(), f"painelalertas_fallback_{nome_arquivo}")
        print(
            f"[AVISO] Sem permissão de escrita em '{caminho}' ({e}). "
            f"Gravando esse log em '{caminho_fallback}' até a permissão da pasta ser corrigida."
        )
        handler = RotatingFileHandler(
            caminho_fallback,
            maxBytes=max_mb * 1024 * 1024, backupCount=backups, encoding="utf-8",
        )
    handler.setFormatter(_formatter)
    return handler


logger.addHandler(_criar_handler_arquivo("alertas_suporte.log"))

# Log isolado dos Relatórios Shein (geração + envio ao SharePoint) -
# facilita achar e mandar exatamente o que aconteceu numa falha, sem
# precisar filtrar no meio do log dos outros 12 alertas.
logger_shein = logging.getLogger("alertas.shein")
logger_shein.setLevel(logging.INFO)
logger_shein.propagate = False  # NÃO escreve em alertas_suporte.log - só no arquivo próprio
logger_shein.addHandler(_criar_handler_arquivo("relatorios_shein.log", max_mb=2, backups=3))

# Log isolado da Atualização Dash Financeiro (os 9 produtos).
logger_dash_financeiro = logging.getLogger("alertas.dash_financeiro")
logger_dash_financeiro.setLevel(logging.INFO)
logger_dash_financeiro.propagate = False
logger_dash_financeiro.addHandler(_criar_handler_arquivo("dash_financeiro.log", max_mb=2, backups=3))

# Log isolado de ações administrativas (usuários, permissões, Manutenção
# de Alertas em Banco, String Connections, Configurações Seguras, login)
# - tudo que é "alguém mexendo em alguma configuração", separado do
# "alerta rodou/não rodou" do Alertas Suporte.
logger_administracao = logging.getLogger("alertas.administracao")
logger_administracao.setLevel(logging.INFO)
logger_administracao.propagate = False
logger_administracao.addHandler(_criar_handler_arquivo("administracao.log", max_mb=2, backups=3))

# Log isolado do Controle de Sincronização / Automação Movidesk.
logger_automacao_movidesk = logging.getLogger("alertas.automacao_movidesk")
logger_automacao_movidesk.setLevel(logging.INFO)
logger_automacao_movidesk.propagate = False
logger_automacao_movidesk.addHandler(_criar_handler_arquivo("automacao_movidesk.log", max_mb=2, backups=3))

# Log isolado do Monitoramento EmailPack (varredura dos logs dos
# serviços EmailPack, agrupamento por e-mail, erros).
logger_emailpack = logging.getLogger("alertas.emailpack")
logger_emailpack.setLevel(logging.INFO)
logger_emailpack.propagate = False
logger_emailpack.addHandler(_criar_handler_arquivo("monitoramento_emailpack.log", max_mb=2, backups=3))

# Nomes exibidos na tela de Logs, na ordem em que devem aparecer -
# mapeando pra (pasta, arquivo) do log físico correspondente. Os do PDA
# em si ficam em logs/ (pasta do programa); os da Aplicação Monitoramento
# são um programa externo separado, cujos logs vivem numa pasta fixa
# própria (PDA_LOGS_MONITORAMENTO) - só leitura, o PDA não escreve
# nada lá, só mostra.
CAMINHO_LOGS_MONITORAMENTO = os.environ.get("PDA_LOGS_MONITORAMENTO", r"C:\PDA\Monitoramento\log")

LOGS_DISPONIVEIS = {
    "Alertas Suporte": (_PASTA_LOGS, "alertas_suporte.log"),
    "Relatórios Shein": (_PASTA_LOGS, "relatorios_shein.log"),
    "Atualização Dash Financeiro": (_PASTA_LOGS, "dash_financeiro.log"),
    "Automação Movidesk": (_PASTA_LOGS, "automacao_movidesk.log"),
    "Monitoramento EmailPack": (_PASTA_LOGS, "monitoramento_emailpack.log"),
    "Administração (usuários, permissões, configurações)": (_PASTA_LOGS, "administracao.log"),
    "Monitoramento - Alertas": (CAMINHO_LOGS_MONITORAMENTO, "Alertas.log"),
    "Monitoramento - Processamentos": (CAMINHO_LOGS_MONITORAMENTO, "Processamentos.log"),
    "Monitoramento - Relatórios": (CAMINHO_LOGS_MONITORAMENTO, "Relatorios.log"),
    "Monitoramento - Service": (CAMINHO_LOGS_MONITORAMENTO, "Service.log"),
}


def _ler_ultimas_linhas_arquivo(caminho: str, n_linhas: int = 1000, bloco_bytes: int = 65536) -> list:
    """Lê as últimas n_linhas de um arquivo de texto SEM carregar o
    arquivo inteiro na memória - importante pros logs da Aplicação
    Monitoramento, que passam de 30-50 MB (os do próprio PDA já são
    pequenos por causa do RotatingFileHandler, mas essa função funciona
    bem pros dois casos). Lê de trás pra frente, em blocos, até juntar
    linhas suficientes."""
    with open(caminho, "rb") as f:
        f.seek(0, os.SEEK_END)
        tamanho_arquivo = f.tell()
        blocos = []
        linhas_encontradas = 0
        posicao = tamanho_arquivo
        while posicao > 0 and linhas_encontradas <= n_linhas:
            ler = min(bloco_bytes, posicao)
            posicao -= ler
            f.seek(posicao)
            bloco = f.read(ler)
            blocos.append(bloco)
            linhas_encontradas += bloco.count(b"\n")
        conteudo = b"".join(reversed(blocos))
    texto = conteudo.decode("utf-8", errors="replace")
    linhas = texto.splitlines()
    return linhas[-n_linhas:]


class QueueLogHandler(logging.Handler):
    """Handler que só empilha o log formatado num histórico compartilhado
    (log_history) - lido tanto pela GUI (Tkinter) quanto pelo servidor web,
    de forma independente uma da outra."""

    def emit(self, record: logging.LogRecord) -> None:
        global _log_seq_contador
        try:
            msg = self.format(record)
            with _log_seq_lock:
                _log_seq_contador += 1
                seq = _log_seq_contador
            log_history.append((seq, record.levelname, msg))
        except Exception:
            pass


_queue_handler = QueueLogHandler()
_queue_handler.setFormatter(_formatter)
logger.addHandler(_queue_handler)

# Como os loggers isolados (shein, dash financeiro, administração,
# automação movidesk) não propagam mais pro "alertas" pai (ver acima -
# propagate = False, pra não misturar nos arquivos), precisam do MESMO
# handler da tela ao vivo adicionado neles direto também, senão
# sumiriam da tela ao vivo do painel - só ficariam nos arquivos.
for _logger_isolado in (logger_shein, logger_dash_financeiro, logger_administracao, logger_automacao_movidesk):
    _logger_isolado.addHandler(_queue_handler)


# ---------------------------------------------------------------------------
# Execução dos jobs
# ---------------------------------------------------------------------------
running_jobs_lock = threading.Lock()
running_jobs: set = set()


def _executar_job_thread(state: JobState) -> None:
    nome = state.job.nome

    with running_jobs_lock:
        if nome in running_jobs:
            logger.warning("Pulando '%s': já está em execução.", nome)
            return
        running_jobs.add(nome)

    # Atualiza o JobState diretamente (é a fonte única de verdade, lida
    # tanto pela GUI quanto pelo servidor web - nenhum dos dois precisa
    # estar "escutando" nada pra isso funcionar).
    state.status = "Executando"
    logger.info("Iniciando alerta: %s", nome)
    try:
        state.job.executar()
        state.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.status = "OK"
        state.last_error = None
        logger.info("Alerta concluído com sucesso: %s", nome)
    except Exception as e:
        state.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.status = "Erro"
        state.last_error = str(e)
        logger.exception("Erro ao executar alerta '%s': %s", nome, e)
    finally:
        with running_jobs_lock:
            running_jobs.discard(nome)


def disparar_job(state: JobState) -> None:
    """Dispara a execução do job numa thread própria (não bloqueia
    quem chamou, seja o agendador ou o botão da GUI)."""
    threading.Thread(target=_executar_job_thread, args=(state,), daemon=True).start()


# ---------------------------------------------------------------------------
# Agendador (roda em background, thread separada da GUI)
# ---------------------------------------------------------------------------
class Agendador:
    def __init__(self, job_states: List[JobState]):
        self.job_states = job_states
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def iniciar(self) -> None:
        for state in self.job_states:
            def runner(st=state) -> None:
                disparar_job(st)
            state.scheduled = state.job.registrar_horarios(runner)

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

        # roda uma vez logo na abertura, igual os scripts originais faziam
        for state in self.job_states:
            disparar_job(state)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                schedule.run_pending()
            except Exception as e:
                logger.exception("Erro inesperado no loop do agendador: %s", e)
            self._stop.wait(30)

    def parar(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


# ---------------------------------------------------------------------------
# Monitoramento de Contingências SEFAZ (SVC-AN / SVC-RS)
# ---------------------------------------------------------------------------
# ATENÇÃO - leia antes de confiar nisso pra uma decisão real:
#   Isso faz web scraping de duas páginas públicas do governo, sem API
#   oficial:
#     - SVC-RS: sefaz.rs.gov.br/NFE/NFE-SVC.aspx - tabela simples com a
#       situação (ativada/desativada, com datas) dos 8 estados que usam a
#       SVC-RS. NÃO exige captcha.
#     - SVC-AN: nfe.fazenda.gov.br/portal/principal.aspx - aviso na home
#       do Portal Nacional ("Serviços em Contingência"), mostra se há
#       algo ativado ou agendado pros estados que usam a SVC-AN. NÃO
#       exige captcha (correção: eu tinha dito antes que exigia - errado,
#       captcha só é usado numa página diferente, de consulta de NF-e
#       individual por chave de acesso, não nessa consulta agregada).
#   Como não tenho acesso à internet daqui, não consegui validar o
#   parsing abaixo contra o HTML real de nenhuma das duas páginas -
#   escrevi com base nas capturas de tela que você mandou. Teste na
#   prática antes de confiar pra decisão real - se der erro, me manda o
#   HTML atual (Ctrl+U) de qualquer uma das duas que eu ajusto.
#   O intervalo de consulta é de 10 em 10 min por padrão (INTERVALO_CONTINGENCIA_MINUTOS).
#   Qualquer falha ao consultar mostra "não verificado" na tela, NUNCA
#   inventa um status - e as duas fontes são tratadas de forma
#   independente (se uma falhar, a outra ainda atualiza normalmente).
# ---------------------------------------------------------------------------

# Mapeamento estático: qual contingência cada UF usa quando o serviço
# próprio dela fica indisponível (não muda com frequência, mas vale
# reconferir de tempos em tempos).
SVC_POR_UF = {
    "AC": "SVC-AN", "AL": "SVC-AN", "AP": "SVC-AN", "CE": "SVC-AN", "DF": "SVC-AN",
    "ES": "SVC-AN", "MG": "SVC-AN", "PA": "SVC-AN", "PB": "SVC-AN", "PI": "SVC-AN",
    "RJ": "SVC-AN", "RN": "SVC-AN", "RO": "SVC-AN", "RR": "SVC-AN", "RS": "SVC-AN",
    "SC": "SVC-AN", "SE": "SVC-AN", "SP": "SVC-AN", "TO": "SVC-AN",
    "AM": "SVC-RS", "BA": "SVC-RS", "GO": "SVC-RS", "MA": "SVC-RS", "MS": "SVC-RS",
    "MT": "SVC-RS", "PE": "SVC-RS", "PR": "SVC-RS",
}

TODOS_UFS = [
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
    "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO",
]

NOME_UF = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais", "PA": "Pará", "PB": "Paraíba", "PR": "Paraná",
    "PE": "Pernambuco", "PI": "Piauí", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul", "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina",
    "SP": "São Paulo", "SE": "Sergipe", "TO": "Tocantins",
}

# Posição de cada UF numa grade estilizada, calibrada a partir de um
# contorno REAL do Brasil (extraído por processamento de imagem de uma
# referência que o usuário mandou - ver comentário na seção do
# Monitoramento de Contingências) - as posições foram recalculadas com
# as mesmas coordenadas geográficas de sempre, mas re-calibradas pra
# bater com esse contorno específico.
# (coluna, linha) - coluna cresce pra leste, linha cresce pra sul.
GRADE_UF = {
    "RR": (2, 0),
    "AP": (5, 0),
    "AM": (2, 1), "PA": (4, 1), "MA": (5, 1), "CE": (6, 1),
    "PI": (5, 2), "RN": (8, 2),
    "AC": (0, 3), "RO": (1, 3), "TO": (5, 3), "PE": (7, 3), "PB": (8, 3),
    "SE": (6, 4), "AL": (7, 4),
    "MT": (2, 5), "GO": (3, 5), "DF": (4, 5), "BA": (6, 5),
    "MS": (4, 6), "MG": (5, 6), "ES": (6, 6),
    "SP": (4, 7), "RJ": (5, 7),
    "PR": (4, 8),
    "SC": (4, 9), "RS": (5, 9),
}

INTERVALO_CONTINGENCIA_MINUTOS = 10  # a cada 10 min, conforme pedido

estado_contingencias: dict = {
    # normal | contingencia | agendada | desconhecido
    "ufs": {uf: "desconhecido" for uf in TODOS_UFS},
    "detalhes": {},  # uf -> {"inicio": ..., "fim": ...} pras que estao ativas (SVC-RS tem datas)
    "ultima_verificacao": None,
    "ultimo_erro": None,
}
_lock_contingencias = threading.Lock()

_CABECALHOS_HTTP_SEFAZ = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


def _buscar_pagina_sefaz(url: str, url_aquecimento: Optional[str] = None):
    """Busca uma página de um site de SEFAZ/governo de um jeito bem mais
    parecido com um navegador de verdade do que um requests.get() simples:
      - usa uma sessão (cookies persistem entre requisições, igual um
        navegador faria);
      - se `url_aquecimento` for informado, visita essa página ANTES (uma
        "entrada" natural no site, pra ganhar cookie de sessão do jeito
        que uma pessoa navegando ganharia, em vez de cair direto numa
        página interna - alguns sites de governo bloqueiam/erroram
        justamente esse padrão de "bateu direto na página X sem vir de
        lugar nenhum");
      - tenta de novo 1x se vier erro 5xx (esses servidores às vezes
        engasgam ou bloqueiam só a primeira tentativa).
    Levanta exceção se não conseguir depois de tentar - nunca finge que
    deu certo."""
    sessao_http = requests.Session()
    sessao_http.headers.update(_CABECALHOS_HTTP_SEFAZ)

    if url_aquecimento:
        try:
            sessao_http.get(url_aquecimento, timeout=15)
        except requests.exceptions.RequestException:
            pass  # se a pagina de "entrada" falhar, tenta a principal mesmo assim

    ultima_excecao = None
    for tentativa in range(2):
        try:
            resposta = sessao_http.get(url, timeout=20)
            if resposta.status_code >= 500 and tentativa == 0:
                time.sleep(2)
                continue
            resposta.raise_for_status()
            return resposta
        except requests.exceptions.RequestException as e:
            ultima_excecao = e
            if tentativa == 0:
                time.sleep(2)
                continue
    raise ultima_excecao


def _texto_limpo_da_pagina(resposta) -> str:
    """Extrai o texto de uma resposta HTTP de forma robusta: corrige
    problemas comuns de encoding (comum em sites .aspx antigos que não
    declaram o charset direito, fazendo o requests advinhar errado),
    decodifica entidades HTML (&nbsp;, &aacute; etc.) e remove as tags."""
    corpo = resposta.text
    if not resposta.encoding or resposta.encoding.lower() in ("iso-8859-1", "ascii"):
        try:
            corpo_alternativo = resposta.content.decode(
                resposta.apparent_encoding or "utf-8", errors="ignore"
            )
            if corpo_alternativo:
                corpo = corpo_alternativo
        except Exception:
            pass
    texto = re.sub(r"<[^>]+>", " ", corpo)
    texto = html_utils.unescape(texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto


def _consultar_svc_rs() -> dict:
    """Consulta a situação real da SVC-RS direto na SEFAZ-RS (tabela
    simples, sem captcha). Retorna {uf: {"status": "ativa"/"desativada",
    "inicio": str|None, "fim": str|None}} pros 8 estados que usam SVC-RS.
    Levanta exceção se não conseguir - nunca inventa status.

    Parsing tolerante de propósito: em vez de exigir uma estrutura exata
    de tags entre o nome da UF e o status (a primeira versão fazia isso
    e não bateu com o HTML real da página), aqui a gente só acha "XX -
    NOME" em qualquer lugar do texto e procura "Ativada em ... até ..."
    ou "Desativada" numa janela generosa de texto logo depois - bem mais
    resistente a pequenas diferenças de marcação que eu não consigo
    prever sem acesso à página de verdade."""
    resposta = _buscar_pagina_sefaz(
        "https://www.sefaz.rs.gov.br/NFE/NFE-SVC.aspx",
        url_aquecimento="https://www.sefaz.rs.gov.br/",
    )
    texto = _texto_limpo_da_pagina(resposta)

    resultados = {}
    for uf, svc in SVC_POR_UF.items():
        if svc != "SVC-RS":
            continue
        m_inicio = re.search(
            r"\b" + re.escape(uf) + r"\s*-\s*(?:(?!Ativada|Desativada|Agendada)[A-Za-zÀ-ÿ\s\(\)]){2,45}", texto
        )
        if not m_inicio:
            continue
        janela = texto[m_inicio.end(): m_inicio.end() + 250]
        m_status = re.search(
            r"(Ativada\s+em\s*([\d/]+\s+[\d:]+)\s*at[ée]\s*([\d/]+\s+[\d:]+)"
            r"|Agendada\s+para\s*([\d/]+\s+[\d:]+)\s*at[ée]\s*([\d/]+\s+[\d:]+)"
            r"|Desativada)",
            janela,
            re.IGNORECASE,
        )
        if not m_status:
            continue
        texto_status = m_status.group(1).lower()
        if texto_status.startswith("ativada"):
            resultados[uf] = {"status": "ativa", "inicio": m_status.group(2), "fim": m_status.group(3)}
        elif texto_status.startswith("agendada"):
            resultados[uf] = {"status": "agendada", "inicio": m_status.group(4), "fim": m_status.group(5)}
        else:
            resultados[uf] = {"status": "desativada", "inicio": None, "fim": None}

    if not resultados:
        raise RuntimeError(
            "Não encontrei nenhuma UF reconhecível na página da SVC-RS "
            "(sefaz.rs.gov.br) - a estrutura do HTML provavelmente mudou."
        )
    return resultados


def _consultar_svc_an() -> dict:
    """Consulta o aviso 'Serviços em Contingência' na home do Portal
    Nacional da NF-e (sem captcha - isso é só a home, não uma consulta
    individual por chave). Retorna {"ativas": [...], "agendadas": [...]}
    com os códigos de UF mencionados em cada seção. Levanta exceção se
    não conseguir encontrar as seções esperadas."""
    resposta = _buscar_pagina_sefaz(
        "https://www.nfe.fazenda.gov.br/portal/principal.aspx",
        url_aquecimento="https://www.nfe.fazenda.gov.br/portal/",
    )
    texto = _texto_limpo_da_pagina(resposta)

    def _fatiar(rotulo, proximo_rotulo):
        m = re.search(re.escape(rotulo), texto, re.IGNORECASE)
        if not m:
            return None
        inicio = m.end()
        fim = -1
        if proximo_rotulo:
            m_fim = re.search(re.escape(proximo_rotulo), texto[inicio:], re.IGNORECASE)
            if m_fim:
                fim = inicio + m_fim.start()
        if fim == -1:
            fim = inicio + 500
        return texto[inicio:fim]

    secao_ativa = _fatiar("Contingência Ativada na SVC-AN", "Contingência Agendada na SVC-AN")
    secao_agendada = _fatiar("Contingência Agendada na SVC-AN", "Denegação")

    if secao_ativa is None or secao_agendada is None:
        raise RuntimeError(
            "Não encontrei as seções de contingência da SVC-AN na página "
            "principal do Portal Nacional - a estrutura do HTML provavelmente mudou."
        )

    ufs_svc_an = [uf for uf, svc in SVC_POR_UF.items() if svc == "SVC-AN"]

    def _ufs_citadas(secao: str) -> list:
        if re.search(r"n[ãa]o\s*h[áa]", secao, re.IGNORECASE):
            return []
        return [uf for uf in ufs_svc_an if re.search(r"\b" + uf + r"\b", secao)]

    return {"ativas": _ufs_citadas(secao_ativa), "agendadas": _ufs_citadas(secao_agendada)}


# ---------------------------------------------------------------------------
# Notificações no Teams (Workflow) - Contingências SEFAZ
# ---------------------------------------------------------------------------
# Avisa num canal do Teams quando uma UF muda de estado no monitoramento de
# contingências: agendada pela primeira vez, entrada de contingência
# (iniciada) e saída de contingência (encerrada). A URL do Workflow fica
# cifrada no config.dat (mesmo sistema Fernet das outras credenciais
# sensíveis) - webhook do Teams é sensível igual senha: quem tiver a URL
# consegue postar mensagem no canal.
# ---------------------------------------------------------------------------

CORES_EVENTO_TEAMS_CONTINGENCIA = {
    "agendada": "Warning",       # amarelo
    "iniciada": "Attention",     # vermelho
    "encerrada": "Good",         # verde
    "cancelada": "Accent",       # azul neutro - nem alerta nem alivio, so um aviso informativo
}

TITULOS_EVENTO_TEAMS_CONTINGENCIA = {
    "agendada": "🟡 Contingência Agendada",
    "iniciada": "🔴 Entrada de Contingência",
    "encerrada": "🟢 Saída de Contingência",
    "cancelada": "🔵 Agendamento de Contingência Cancelado",
}


def _obter_webhook_teams_contingencias() -> str:
    return _obter_valor_config("teams::contingencias_webhook", "")


def _montar_cartao_teams_contingencia(uf: str, evento: str, detalhes: Optional[dict] = None) -> dict:
    """Monta o payload no formato Adaptive Card que o Workflow do Teams
    espera (o gatilho 'quando um webhook for recebido' só aceita esse
    formato - não é o webhook antigo de texto simples)."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    corpo = [
        {
            "type": "TextBlock",
            "text": TITULOS_EVENTO_TEAMS_CONTINGENCIA[evento],
            "weight": "Bolder",
            "size": "Medium",
            "color": CORES_EVENTO_TEAMS_CONTINGENCIA[evento],
        },
        {
            "type": "FactSet",
            "facts": [
                {"title": "UF", "value": uf},
                {"title": "Detectado em", "value": agora},
            ],
        },
    ]
    if evento == "iniciada" and detalhes and detalhes.get("inicio"):
        corpo[1]["facts"].append({"title": "Ativada desde", "value": detalhes["inicio"]})
        if detalhes.get("fim"):
            corpo[1]["facts"].append({"title": "Prevista até", "value": detalhes["fim"]})
    elif evento == "cancelada" and detalhes and detalhes.get("inicio"):
        corpo[1]["facts"].append({"title": "Estava agendada pra", "value": detalhes["inicio"]})
        if detalhes.get("fim"):
            corpo[1]["facts"].append({"title": "Até", "value": detalhes["fim"]})

    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": corpo,
                },
            }
        ],
    }


def _enviar_notificacao_teams_contingencia(uf: str, evento: str, detalhes: Optional[dict] = None) -> None:
    """Dispara o webhook do Teams pra um evento de contingência. Nunca
    levanta exceção pra fora - uma falha de notificação (Teams fora do ar,
    URL errada, etc.) não pode derrubar o monitoramento de contingências
    em si, só fica registrada no log."""
    webhook_url = _obter_webhook_teams_contingencias()
    if not webhook_url:
        logger.warning(
            "Contingências: evento %s em %s não notificado - webhook do Teams não configurado "
            "(cadastre em Criptografia de Dados Sensíveis: teams::contingencias_webhook).",
            evento, uf,
        )
        return
    try:
        payload = _montar_cartao_teams_contingencia(uf, evento, detalhes)
        resposta = requests.post(webhook_url, json=payload, timeout=15)
        resposta.raise_for_status()
        logger.info("Contingências: notificação do Teams enviada (%s - %s).", uf, evento)
    except Exception as e:
        logger.warning("Contingências: falha ao notificar o Teams (%s - %s): %s", uf, evento, e)


def _atualizar_estado_contingencias() -> None:
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    estado_anterior = dict(estado_contingencias["ufs"])
    detalhes_anteriores = dict(estado_contingencias["detalhes"])
    primeira_verificacao = estado_contingencias["ultima_verificacao"] is None
    novos = dict(estado_contingencias["ufs"])
    detalhes = {}
    erros = []

    try:
        rs_dados = _consultar_svc_rs()
        for uf, info in rs_dados.items():
            if info["status"] == "ativa":
                novos[uf] = "contingencia"
                detalhes[uf] = {"inicio": info["inicio"], "fim": info["fim"]}
            elif info["status"] == "agendada":
                novos[uf] = "agendada"
                detalhes[uf] = {"inicio": info["inicio"], "fim": info["fim"]}
            else:
                novos[uf] = "normal"
    except Exception as e:
        erros.append(f"SVC-RS: {e}")
        logger.warning("Não foi possível verificar SVC-RS: %s", e)

    try:
        an_dados = _consultar_svc_an()
        for uf, svc in SVC_POR_UF.items():
            if svc != "SVC-AN":
                continue
            if uf in an_dados["ativas"]:
                novos[uf] = "contingencia"
            elif uf in an_dados["agendadas"]:
                novos[uf] = "agendada"
            else:
                novos[uf] = "normal"
    except Exception as e:
        erros.append(f"SVC-AN: {e}")
        logger.warning("Não foi possível verificar SVC-AN: %s", e)

    with _lock_contingencias:
        estado_contingencias["ufs"] = novos
        estado_contingencias["detalhes"] = detalhes
        estado_contingencias["ultima_verificacao"] = agora
        estado_contingencias["ultimo_erro"] = "; ".join(erros) if erros else None

    # Avisos no Teams por TRANSIÇÃO de estado - nunca na primeira
    # verificação depois de o programa ligar (senão avisaria "encerrada"
    # pra toda UF só porque o estado anterior era "desconhecido", o que
    # não é um evento real de contingência).
    if not primeira_verificacao:
        for uf, status_novo in novos.items():
            status_antigo = estado_anterior.get(uf, "desconhecido")
            if status_novo == status_antigo:
                continue
            try:
                if status_novo == "agendada":
                    _enviar_notificacao_teams_contingencia(uf, "agendada")
                elif status_novo == "contingencia":
                    _enviar_notificacao_teams_contingencia(uf, "iniciada", detalhes.get(uf))
                elif status_antigo == "contingencia" and status_novo == "normal":
                    _enviar_notificacao_teams_contingencia(uf, "encerrada")
                elif status_antigo == "agendada" and status_novo == "normal":
                    # o agendamento sumiu da SEFAZ numa consulta seguinte
                    # sem nunca ter virado contingência de verdade - ou
                    # seja, foi cancelado antes de comecar. Manda os
                    # detalhes de quando ESTAVA agendado (capturados
                    # antes de serem sobrescritos nesta mesma rodada),
                    # já que a rodada atual não tem mais essa informação
                    # (a UF já voltou pra "normal", sem data nenhuma).
                    _enviar_notificacao_teams_contingencia(uf, "cancelada", detalhes_anteriores.get(uf))
            except Exception:
                # a notificação em si já se protege contra erro de rede,
                # mas essa camada extra garante que NENHUM bug imprevisto
                # aqui consiga derrubar o monitoramento de contingências -
                # o painel em si é o que importa de verdade, o aviso no
                # Teams é um extra.
                logger.exception("Erro inesperado ao processar notificação do Teams pra %s", uf)

    qtd_contingencia = sum(1 for v in novos.values() if v == "contingencia")
    qtd_agendada = sum(1 for v in novos.values() if v == "agendada")
    logger.info(
        "Contingências atualizadas: %d ativa(s), %d agendada(s).", qtd_contingencia, qtd_agendada
    )


class MonitorContingencias:
    """Thread própria, separada do Agendador de alertas - checagem
    periódica (padrão: 10 em 10 min) da disponibilidade
    dos autorizadores de NF-e."""

    def __init__(self, intervalo_minutos: int = INTERVALO_CONTINGENCIA_MINUTOS):
        self.intervalo_minutos = intervalo_minutos
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock_execucao = threading.Lock()
        self._executando = False

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _rodar_com_trava(self) -> None:
        """Roda _atualizar_estado_contingencias, mas só se não tiver
        outra rodada (manual ou periódica) já em andamento - sem isso,
        cliques repetidos em "Atualizar agora" (ou um clique batendo
        com a verificação periódica) disparavam várias consultas à
        SEFAZ em paralelo ao mesmo tempo, à toa (era exatamente o que
        os logs duplicados do solicitante mostravam - o mesmo disparo
        registrado 5-6 vezes no mesmo segundo)."""
        with self._lock_execucao:
            if self._executando:
                return
            self._executando = True
        try:
            _atualizar_estado_contingencias()
        finally:
            with self._lock_execucao:
                self._executando = False

    def _loop(self) -> None:
        self._rodar_com_trava()  # roda uma vez já na abertura
        while not self._stop.is_set():
            if self._stop.wait(self.intervalo_minutos * 60):
                break
            self._rodar_com_trava()

    def forcar_atualizacao(self) -> bool:
        """Dispara uma atualização manual numa thread separada (não
        bloqueia quem chamou). Devolve False sem fazer nada se já tiver
        uma rodada em andamento (manual ou periódica) - True se
        realmente disparou uma nova."""
        with self._lock_execucao:
            if self._executando:
                return False
        threading.Thread(target=self._rodar_com_trava, daemon=True).start()
        return True

    def parar(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


# Referência global pro monitor em execução, pra dar pro handler HTTP
# conseguir chamar "forçar atualização agora" (setada em AlertasApp.__init__).
_monitor_contingencias_ref: Optional["MonitorContingencias"] = None


# ---------------------------------------------------------------------------
# Monitoramento EmailPack
# ---------------------------------------------------------------------------
# Varre os logs dos serviços EmailPack (via caminho de rede UNC) procurando
# erros por e-mail processado, e avisa no Teams quando encontra algo (ou,
# opcionalmente, um "heartbeat" de sucesso quando não encontra nada). Portado
# do script standalone monitor_emailpack_gui.py (versão com contexto por
# thread persistente entre ciclos) - a lógica central é a mesma; só a
# interface mudou (GUI Tkinter -> card + página web do PDA).
#
# IMPORTANTE sobre o motivo do contexto por thread: como a leitura é por
# OFFSET (só linhas novas desde a última vez), é bem comum a linha
# "Verificando caixa de entrada do endereço 'X'" cair num ciclo e o
# ERROR/FATAL correspondente só aparecer no ciclo seguinte, na mesma
# thread do log. Uma versão anterior que associava o e-mail só dentro do
# mesmo lote de linhas lidas de uma vez perdia essa associação nesse caso
# (o erro ficava "órfão", sem e-mail, e podia nem ser notificado) - por
# isso agora o "último e-mail visto por thread" é salvo em disco e
# carregado de novo no próximo ciclo, junto com os offsets.

_UNC_EMAILPACK_PADRAO = os.environ.get("EMAILPACK_UNC_SERVIDOR", r"\\servidor-emailpack\EmailPack")


def _diretorios_padrao_emailpack() -> List[str]:
    return [
        os.path.join(_UNC_EMAILPACK_PADRAO, "EmailPackServiceGeral", "log"),
        os.path.join(_UNC_EMAILPACK_PADRAO, "EmailPackServiceGeral2", "log"),
        os.path.join(_UNC_EMAILPACK_PADRAO, "EmailPackServiceEmpresa", "log"),
        os.path.join(_UNC_EMAILPACK_PADRAO, "EmailPackServiceEmpresa2", "log"),
        os.path.join(_UNC_EMAILPACK_PADRAO, "EmailPackServiceEmpresa3", "log"),
        os.path.join(_UNC_EMAILPACK_PADRAO, "EmailPackSemAutenticacao", "log"),
    ]


CONFIG_EMAILPACK = {
    "diretorios_log": (
        os.environ["EMAILPACK_DIRS"].split(";")
        if os.environ.get("EMAILPACK_DIRS")
        else _diretorios_padrao_emailpack()
    ),
    "extensoes_log": (".log",),
    "pasta_monitoramento": os.environ.get(
        "EMAILPACK_PASTA_MON", os.path.join(_base_path_app(), "logs", "emailpack")
    ),
    "niveis_erro": {"ERROR", "FATAL"},
    "dedup_minutos": int(os.environ.get("EMAILPACK_DEDUP_MIN", "9")),
    "heartbeat_sucesso": os.environ.get("EMAILPACK_HEARTBEAT", "1") == "1",
    "encoding_log": os.environ.get("EMAILPACK_LOG_ENCODING", "cp1252"),
    "linhas_stack_no_alerta": 3,
    "limite_caracteres_card": 4000,
    "intervalo_execucao_segundos": int(os.environ.get("EMAILPACK_INTERVALO_SEG", "600")),  # 10 min
    "timeout_diretorio_segundos": float(os.environ.get("EMAILPACK_TIMEOUT_DIR", "5")),
    "identificacao_alerta": os.environ.get("EMAILPACK_IDENTIFICACAO", "PDA"),
    "unc_servidor": _UNC_EMAILPACK_PADRAO,
    "unc_usuario": os.environ.get("EMAILPACK_UNC_USUARIO", ""),
}
# a senha do compartilhamento UNC e o webhook do Teams seguem o mesmo
# padrão de credencial cifrada (Configurações Seguras) que o resto do
# PDA usa - nada de senha/URL assinada em texto puro no código. Sem
# nenhum dos dois configurados, o alerta é só registrado no log.
_WEBHOOK_EMAILPACK_PADRAO = ""


def _senha_unc_emailpack() -> str:
    return _obter_valor_config("emailpack::UNC_SENHA", os.getenv("EMAILPACK_UNC_SENHA", ""))


def _webhook_teams_emailpack() -> str:
    return _obter_valor_config(
        "teams::emailpack_webhook", os.getenv("EMAILPACK_TEAMS_WEBHOOK", _WEBHOOK_EMAILPACK_PADRAO)
    )


RE_LINHA_EMAILPACK = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+"
    r"\[(?P<thread>\d+)\]\s+(?P<nivel>\w+)\s+(?P<logger>\S+)\s+-\s+(?P<msg>.*)$"
)
RE_ENDERECO_EMAILPACK = re.compile(r"Verificando caixa de entrada do endere[cç]o '([^']+)'")
RE_EMAIL_SOLTO_EMAILPACK = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


@dataclass
class _LogEntryEmailPack:
    timestamp: datetime
    thread: str
    nivel: str
    logger: str
    mensagem: str


@dataclass
class _ResumoErroEmailPack:
    quantidade: int = 0
    primeira: Optional[datetime] = None
    ultima: Optional[datetime] = None
    mensagem: str = ""
    mensagens: List[str] = field(default_factory=list)


_executor_rede_emailpack = ThreadPoolExecutor(max_workers=8, thread_name_prefix="checagem_unc_emailpack")
_autenticacao_tentada_emailpack = False


def _dir_existe_com_timeout_emailpack(dir_path: Path, timeout_seg: float) -> bool:
    future = _executor_rede_emailpack.submit(dir_path.is_dir)
    try:
        return future.result(timeout=timeout_seg)
    except Exception:
        return False


def _autenticar_compartilhamento_emailpack() -> None:
    global _autenticacao_tentada_emailpack
    if _autenticacao_tentada_emailpack:
        return
    _autenticacao_tentada_emailpack = True

    servidor = CONFIG_EMAILPACK.get("unc_servidor")
    usuario = CONFIG_EMAILPACK.get("unc_usuario")
    senha = _senha_unc_emailpack()
    if not (servidor and usuario and senha):
        return

    try:
        resultado = subprocess.run(
            ["net", "use", servidor, senha, f"/user:{usuario}"],
            capture_output=True, text=True, timeout=15,
        )
        if resultado.returncode == 0:
            logger_emailpack.info("Autenticado no compartilhamento %s", servidor)
        else:
            logger_emailpack.warning(
                "Falha ao autenticar no compartilhamento %s (código %s): %s",
                servidor, resultado.returncode, resultado.stderr.strip(),
            )
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger_emailpack.warning("Erro ao tentar autenticar no compartilhamento %s: %s", servidor, exc)


def _listar_arquivos_log_emailpack() -> Dict[str, list]:
    arquivos_por_dir: Dict[str, list] = {}
    timeout = CONFIG_EMAILPACK["timeout_diretorio_segundos"]
    for dir_str in CONFIG_EMAILPACK["diretorios_log"]:
        dir_path = Path(dir_str)
        if not _dir_existe_com_timeout_emailpack(dir_path, timeout):
            logger_emailpack.warning(
                "Diretório configurado não encontrado/acessível (ou sem resposta em %.0fs): %s",
                timeout, dir_str,
            )
            continue
        try:
            encontrados = [
                p for p in dir_path.iterdir()
                if p.is_file() and p.suffix.lower() in CONFIG_EMAILPACK["extensoes_log"]
            ]
        except Exception as exc:
            logger_emailpack.warning("Falha ao listar arquivos em '%s': %s", dir_str, exc)
            continue
        arquivos_por_dir[dir_str] = sorted(encontrados)
    return arquivos_por_dir


def _nome_servico_emailpack(caminho_arquivo: Path) -> str:
    partes = caminho_arquivo.parts
    try:
        idx = len(partes) - 1 - partes[::-1].index("log")
        return partes[idx - 1]
    except ValueError:
        return caminho_arquivo.parent.name


def _carregar_estado_monitoramento_emailpack(arquivo_estado: Path):
    """Devolve (offsets, thread_context, thread_inicio). thread_context
    guarda, por arquivo e por thread do log, qual foi o último e-mail
    visto ("Verificando caixa de entrada de X") - e thread_inicio, o
    horário em que essa associação começou. Os dois persistem entre
    ciclos (por isso um erro que aparece num ciclo seguinte ao da linha
    de início continua sendo associado ao e-mail certo).

    Compatibilidade: se o JSON salvo for do formato antigo (só
    {arquivo: offset}, sem contexto de thread), migra automaticamente."""
    if not arquivo_estado.exists():
        return {}, {}, {}
    try:
        estado = json.loads(arquivo_estado.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}, {}

    if isinstance(estado, dict) and "offsets" in estado:
        offsets = estado.get("offsets") if isinstance(estado.get("offsets"), dict) else {}
        thread_context = estado.get("thread_context") if isinstance(estado.get("thread_context"), dict) else {}
        thread_inicio = estado.get("thread_inicio") if isinstance(estado.get("thread_inicio"), dict) else {}
        offsets_validos = {}
        for k, v in offsets.items():
            try:
                offsets_validos[str(k)] = int(v)
            except Exception:
                pass
        return offsets_validos, thread_context, thread_inicio

    if isinstance(estado, dict):
        # formato antigo (so offset simples) - migra sem contexto de thread
        offsets_validos = {}
        for k, v in estado.items():
            try:
                offsets_validos[str(k)] = int(v)
            except Exception:
                pass
        return offsets_validos, {}, {}

    return {}, {}, {}


def _salvar_estado_monitoramento_emailpack(arquivo_estado: Path, offsets: dict, thread_context: dict, thread_inicio: dict) -> None:
    arquivo_estado.parent.mkdir(parents=True, exist_ok=True)
    estado = {
        "versao": 2,
        "atualizado_em": datetime.now().isoformat(),
        "offsets": offsets,
        "thread_context": thread_context,
        "thread_inicio": thread_inicio,
    }
    arquivo_estado.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")


_lock_emails_emailpack = threading.Lock()


def _caminho_emails_conhecidos_emailpack() -> Path:
    return Path(CONFIG_EMAILPACK["pasta_monitoramento"]) / "emails_conhecidos.json"


def _caminho_emails_ignorados_emailpack() -> Path:
    return Path(CONFIG_EMAILPACK["pasta_monitoramento"]) / "emails_ignorados.json"


def _carregar_emails_conhecidos_emailpack() -> set:
    caminho = _caminho_emails_conhecidos_emailpack()
    if not caminho.exists():
        return set()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dados, list):
            return set(dados)
    except Exception:
        logger_emailpack.exception("Não foi possível ler emails_conhecidos.json.")
    return set()


def _salvar_emails_conhecidos_emailpack(emails: set) -> None:
    caminho = _caminho_emails_conhecidos_emailpack()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(sorted(emails), indent=2, ensure_ascii=False), encoding="utf-8")


def _carregar_emails_ignorados_emailpack() -> set:
    caminho = _caminho_emails_ignorados_emailpack()
    if not caminho.exists():
        return set()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dados, list):
            return set(dados)
    except Exception:
        logger_emailpack.exception("Não foi possível ler emails_ignorados.json.")
    return set()


def _salvar_emails_ignorados_emailpack(emails: set) -> None:
    caminho = _caminho_emails_ignorados_emailpack()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(sorted(emails), indent=2, ensure_ascii=False), encoding="utf-8")


def _ler_novas_linhas_emailpack(caminho_arquivo: Path, offsets: dict) -> list:
    chave = str(caminho_arquivo)
    tamanho_atual = caminho_arquivo.stat().st_size
    primeira_vez = chave not in offsets
    offset = int(offsets.get(chave, 0))

    if offset > tamanho_atual:
        offset = 0  # log rotacionou/truncou - recomeça do início

    if primeira_vez:
        # não apita histórico antigo na primeira vez que vê o arquivo -
        # só marca a posição atual e passa a ler dali em diante
        offsets[chave] = tamanho_atual
        return []

    with open(caminho_arquivo, "r", encoding=CONFIG_EMAILPACK["encoding_log"], errors="replace") as f:
        f.seek(offset)
        linhas = f.readlines()
        novo_offset = f.tell()

    offsets[chave] = novo_offset
    return linhas


def _parse_linhas_emailpack(linhas: list) -> List[_LogEntryEmailPack]:
    entradas: List[_LogEntryEmailPack] = []
    for linha_bruta in linhas:
        linha = linha_bruta.rstrip("\n").rstrip("\r")
        if not linha.strip():
            continue
        m = RE_LINHA_EMAILPACK.match(linha)
        if m:
            try:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S,%f")
            except Exception:
                continue
            entradas.append(
                _LogEntryEmailPack(
                    timestamp=ts,
                    thread=m.group("thread"),
                    nivel=m.group("nivel").strip(),
                    logger=m.group("logger"),
                    mensagem=m.group("msg"),
                )
            )
        elif entradas:
            entradas[-1].mensagem += "\n" + linha.strip()
    return entradas


def _limpar_mensagem_para_alerta_emailpack(msg: str) -> str:
    msg = msg.strip()
    if not msg:
        return "(sem detalhe)"
    linhas = msg.splitlines()
    principal = linhas[0].strip()
    extras = [l.strip() for l in linhas[1: 1 + CONFIG_EMAILPACK["linhas_stack_no_alerta"]] if l.strip()]
    if extras:
        return principal + "\n" + "\n".join(extras)
    return principal


def _descobrir_email_fallback_emailpack(texto: str) -> Optional[str]:
    m = RE_EMAIL_SOLTO_EMAILPACK.search(texto or "")
    return m.group(0) if m else None


def _parse_iso_data_emailpack(valor: Optional[str]) -> Optional[datetime]:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except Exception:
        return None


def _registrar_erros_por_ordem_thread_emailpack(
    erros_por_servico: Dict[str, Dict[str, _ResumoErroEmailPack]],
    servico: str,
    caminho_arquivo: Path,
    entradas: List[_LogEntryEmailPack],
    thread_context: dict,
    thread_inicio: dict,
    emails_conhecidos: Optional[set] = None,
) -> None:
    """Associa cada ERROR/FATAL ao último e-mail visto na MESMA thread
    (persistindo isso em thread_context/thread_inicio pros próximos
    ciclos) - em vez de só agrupar dentro do lote de linhas lido agora,
    o que perdia a associação quando a linha "verificando caixa de
    entrada" e o erro correspondente caíam em ciclos diferentes.
    Se emails_conhecidos for passado, todo endereço visto (mesmo sem
    erro nenhum) é acumulado ali - vira o "cache" de endereços já
    processados alguma vez, usado pra montar a lista de quem dá pra
    marcar como ignorado."""
    bucket = erros_por_servico.setdefault(servico, {})
    chave_arquivo = str(caminho_arquivo)
    contexto_arquivo = thread_context.setdefault(chave_arquivo, {})
    inicio_arquivo = thread_inicio.setdefault(chave_arquivo, {})

    for e in entradas:
        m_email = RE_ENDERECO_EMAILPACK.search(e.mensagem)
        if m_email:
            contexto_arquivo[e.thread] = m_email.group(1)
            inicio_arquivo[e.thread] = e.timestamp.isoformat()
            if emails_conhecidos is not None:
                emails_conhecidos.add(m_email.group(1))

        if e.nivel not in CONFIG_EMAILPACK["niveis_erro"]:
            continue

        email = contexto_arquivo.get(e.thread)
        if not email:
            email = _descobrir_email_fallback_emailpack(e.mensagem) or f"(sem_email_thread_{e.thread})"

        mensagem_alerta = _limpar_mensagem_para_alerta_emailpack(e.mensagem)
        resumo = bucket.setdefault(email, _ResumoErroEmailPack())
        resumo.quantidade += 1
        resumo.mensagem = mensagem_alerta
        resumo.mensagens.append(mensagem_alerta)

        inicio_email = _parse_iso_data_emailpack(inicio_arquivo.get(e.thread)) or e.timestamp
        if resumo.primeira is None or inicio_email < resumo.primeira:
            resumo.primeira = inicio_email
        if resumo.ultima is None or e.timestamp >= resumo.ultima:
            resumo.ultima = e.timestamp


def _enviar_teams_alerta_emailpack(titulo: str, mensagem: str, nivel: str = "erro") -> None:
    webhook_url = _webhook_teams_emailpack()
    if not webhook_url:
        logger_emailpack.warning("Webhook do Teams não configurado. Alerta NÃO enviado: %s", titulo)
        return

    estilo = {"sucesso": "good", "aviso": "warning"}.get(nivel, "attention")
    prefixo = {"sucesso": "[OK]", "aviso": "[ATENÇÃO]"}.get(nivel, "[ERRO]")

    limite = CONFIG_EMAILPACK["limite_caracteres_card"]
    mensagem_cortada = mensagem if len(mensagem) < limite else mensagem[:limite] + "\n... (cortado, ver log de execução)"

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "Container",
                            "style": estilo,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{prefixo} {titulo}",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "wrap": True,
                                }
                            ],
                        },
                        {"type": "TextBlock", "text": mensagem_cortada, "wrap": True},
                        {
                            "type": "TextBlock",
                            "text": f"{CONFIG_EMAILPACK['identificacao_alerta']} | {datetime.now():%Y-%m-%d %H:%M:%S}",
                            "isSubtle": True,
                            "size": "Small",
                            "wrap": True,
                        },
                    ],
                },
            }
        ],
    }

    try:
        resp = requests.post(webhook_url, json=card, timeout=15)
        resp.raise_for_status()
        logger_emailpack.info("Notificação Teams enviada [%s]: %s", nivel, titulo)
    except requests.RequestException as exc:
        logger_emailpack.error("Falha ao enviar notificação Teams: %s", exc)


def _calcular_hash_emailpack(texto: str) -> str:
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def _caminho_dedup_fallback_emailpack(arquivo_estado: Path) -> Path:
    """Caminho de fallback (em %TEMP%, gravável por qualquer usuário) pro
    estado de dedup - mesmo caso de ACL entre usuários do Windows já
    visto nos logs/relatórios (ver _criar_handler_arquivo). Usa o mesmo
    nome de arquivo, só numa pasta alternativa."""
    pasta_fallback = Path(tempfile.gettempdir()) / "painelalertas_fallback_dedup_erros_email"
    return pasta_fallback / arquivo_estado.name


def _deve_reenviar_emailpack(hash_atual: str, arquivo_estado: Path, dedup_minutos: int) -> bool:
    if dedup_minutos <= 0:
        return True
    caminho_real = arquivo_estado
    if not caminho_real.exists():
        # se o estado principal não existe (nunca foi gravado, ou foi
        # parar no fallback numa rodada anterior por causa da ACL),
        # confere o fallback antes de assumir que é a primeira vez
        caminho_fallback = _caminho_dedup_fallback_emailpack(arquivo_estado)
        caminho_real = caminho_fallback if caminho_fallback.exists() else caminho_real
    if not caminho_real.exists():
        return True
    try:
        estado = json.loads(caminho_real.read_text(encoding="utf-8"))
        hash_anterior = estado.get("hash")
        data_anterior = datetime.fromisoformat(estado.get("data"))
    except Exception:
        return True
    dentro_da_janela = (datetime.now() - data_anterior) < timedelta(minutes=dedup_minutos)
    return not (hash_anterior == hash_atual and dentro_da_janela)


def _gravar_estado_dedup_emailpack(hash_atual: str, arquivo_estado: Path) -> None:
    conteudo = json.dumps({"hash": hash_atual, "data": datetime.now().isoformat()})
    try:
        arquivo_estado.parent.mkdir(parents=True, exist_ok=True)
        arquivo_estado.write_text(conteudo, encoding="utf-8")
    except (PermissionError, OSError) as e:
        # mesmo caso de ACL entre usuários do Windows já visto antes nos
        # logs (Errno 13) - cai pro fallback em vez de derrubar o ciclo
        # de monitoramento inteiro por causa de UM arquivo de dedup
        caminho_fallback = _caminho_dedup_fallback_emailpack(arquivo_estado)
        logger_emailpack.warning(
            "Sem permissão de escrita em '%s' (%s). Gravando o estado de dedup em '%s' até a "
            "permissão da pasta ser corrigida.", arquivo_estado, e, caminho_fallback,
        )
        caminho_fallback.parent.mkdir(parents=True, exist_ok=True)
        caminho_fallback.write_text(conteudo, encoding="utf-8")


def _nome_arquivo_seguro_emailpack(texto: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9_.@-]+", "_", texto or "sem_nome")
    return seguro[:150].strip("._") or "sem_nome"


def _formatar_texto_alerta_email_emailpack(servico: str, email: str, resumo: _ResumoErroEmailPack) -> str:
    primeira = resumo.primeira.strftime("%H:%M:%S") if resumo.primeira else "?"
    ultima = resumo.ultima.strftime("%H:%M:%S") if resumo.ultima else "?"

    mensagens_distintas: List[str] = []
    for msg in resumo.mensagens:
        if msg not in mensagens_distintas:
            mensagens_distintas.append(msg)
        if len(mensagens_distintas) >= 3:
            break

    partes = [
        f"**Serviço:** {servico}",
        f"**E-mail:** {email}",
        f"**Ocorrências:** {resumo.quantidade}",
        f"**Primeiro erro:** {primeira}",
        f"**Último erro:** {ultima}",
        "",
        "**Mensagem:**",
    ]
    if mensagens_distintas:
        for msg in mensagens_distintas:
            partes.append(msg)
            partes.append("")
    else:
        partes.append("(sem detalhe)")
    return "\n".join(partes).strip()


def _enviar_alertas_por_email_emailpack(
    pasta_estado: Path,
    erros_por_servico: Dict[str, Dict[str, _ResumoErroEmailPack]],
    emails_ignorados: Optional[set] = None,
) -> None:
    """Manda um card separado no Teams pra cada (serviço, e-mail) com
    erro - com dedup granular por par serviço+e-mail (não um hash
    combinado de tudo), pra um e-mail com erro novo não ficar esperando
    a janela de dedup de outro e-mail que já tinha sido avisado.
    E-mails na lista de ignorados continuam registrados/visíveis na tela
    do PDA (pra não esconder informação), só não geram card no Teams."""
    pasta_dedup_email = pasta_estado / "dedup_erros_email"
    try:
        pasta_dedup_email.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        # mesmo problema de ACL, só que na CRIAÇÃO da pasta - sem isso,
        # nenhum alerta desse ciclo seria enviado. _gravar_estado_dedup_emailpack
        # já cai pro fallback em %TEMP% sozinho quando grava cada arquivo,
        # então só logamos aqui e seguimos (a pasta pode nem ser
        # necessária se _deve_reenviar_emailpack achar tudo no fallback).
        logger_emailpack.warning(
            "Sem permissão pra criar '%s' (%s). O dedup vai cair pro fallback "
            "em %%TEMP%% conforme necessário.", pasta_dedup_email, e,
        )
    emails_ignorados = emails_ignorados or set()

    total_enviados = 0
    total_suprimidos = 0
    total_ignorados = 0

    for servico, emails in erros_por_servico.items():
        for email, resumo in sorted(emails.items()):
            if email in emails_ignorados:
                total_ignorados += 1
                continue

            try:
                texto_email = _formatar_texto_alerta_email_emailpack(servico, email, resumo)
                hash_email = _calcular_hash_emailpack(f"{servico}|{email}|{texto_email}")
                arquivo_estado_email = pasta_dedup_email / f"{_nome_arquivo_seguro_emailpack(servico)}__{_nome_arquivo_seguro_emailpack(email)}.json"

                if _deve_reenviar_emailpack(hash_email, arquivo_estado_email, CONFIG_EMAILPACK["dedup_minutos"]):
                    _enviar_teams_alerta_emailpack(f"Monitoramento EmailPack - Erro em {email}", texto_email, "erro")
                    _gravar_estado_dedup_emailpack(hash_email, arquivo_estado_email)
                    total_enviados += 1
                else:
                    logger_emailpack.info(
                        "Erro de %s/%s já notificado há menos de %d min. Card não reenviado.",
                        servico, email, CONFIG_EMAILPACK["dedup_minutos"],
                    )
                    total_suprimidos += 1
            except Exception:
                # UM e-mail/serviço com problema (dedup, envio ao Teams,
                # etc.) não pode travar o ciclo inteiro - os outros
                # serviços/e-mails que TAMBÉM têm erro real pra avisar
                # continuam sendo processados normalmente.
                logger_emailpack.exception(
                    "Falha ao processar o alerta de %s/%s - seguindo pros próximos.", servico, email,
                )

    if total_ignorados:
        logger_emailpack.info("%d card(s) não enviado(s) por estarem na lista de e-mails ignorados.", total_ignorados)

    logger_emailpack.info("Cards por e-mail enviados: %d; suprimidos por dedup: %d", total_enviados, total_suprimidos)


# Estado do último ciclo, pra tela web mostrar sem precisar reprocessar
# nada - atualizado no final de cada _executar_ciclo_emailpack.
estado_emailpack: dict = {
    "ultima_execucao": None, "executando": False,
    "total_linhas_novas": 0, "servicos_verificados": 0, "arquivos_verificados": 0,
    "dirs_ausentes": [], "erros_por_servico": {}, "ultimo_erro_execucao": None,
}
_lock_estado_emailpack = threading.Lock()


def _executar_ciclo_emailpack() -> None:
    """Um ciclo completo de monitoramento - mesma lógica do script
    original (executar_ciclo), só que gravando o resumo em
    estado_emailpack no final, pra tela web mostrar."""
    pasta = Path(CONFIG_EMAILPACK["pasta_monitoramento"])
    arquivo_estado_monitoramento = pasta / "ultimo_offset.json"
    arquivo_estado_dirs = pasta / "ultimo_aviso_dirs.json"

    logger_emailpack.info("===== Iniciando ciclo de monitoramento (%d diretórios) =====", len(CONFIG_EMAILPACK["diretorios_log"]))

    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    _autenticar_compartilhamento_emailpack()
    arquivos_por_dir = _listar_arquivos_log_emailpack()
    dirs_ausentes = [d for d in CONFIG_EMAILPACK["diretorios_log"] if d not in arquivos_por_dir]

    offsets, thread_context, thread_inicio = _carregar_estado_monitoramento_emailpack(arquivo_estado_monitoramento)
    emails_conhecidos = _carregar_emails_conhecidos_emailpack()
    qtd_emails_conhecidos_antes = len(emails_conhecidos)
    erros_por_servico: Dict[str, Dict[str, _ResumoErroEmailPack]] = {}
    total_linhas_novas = 0
    total_entradas_parseadas = 0
    arquivos_com_falha_leitura = []

    for dir_str, arquivos in arquivos_por_dir.items():
        for caminho in arquivos:
            servico = _nome_servico_emailpack(caminho)
            try:
                linhas_novas = _ler_novas_linhas_emailpack(caminho, offsets)
            except Exception as exc:
                logger_emailpack.error("Falha ao ler '%s': %s", caminho, exc)
                arquivos_com_falha_leitura.append(f"{servico}/{caminho.name}: {exc}")
                continue

            if not linhas_novas:
                continue

            total_linhas_novas += len(linhas_novas)
            entradas = _parse_linhas_emailpack(linhas_novas)
            total_entradas_parseadas += len(entradas)
            _registrar_erros_por_ordem_thread_emailpack(
                erros_por_servico, servico, caminho, entradas, thread_context, thread_inicio, emails_conhecidos,
            )

    try:
        _salvar_estado_monitoramento_emailpack(arquivo_estado_monitoramento, offsets, thread_context, thread_inicio)
    except Exception as exc:
        logger_emailpack.warning("Não foi possível salvar o estado de monitoramento: %s", exc)
    if len(emails_conhecidos) != qtd_emails_conhecidos_antes:
        try:
            _salvar_emails_conhecidos_emailpack(emails_conhecidos)
            logger_emailpack.info(
                "Cache de e-mails conhecidos atualizado: %d novo(s), %d no total.",
                len(emails_conhecidos) - qtd_emails_conhecidos_antes, len(emails_conhecidos),
            )
        except Exception:
            logger_emailpack.exception("Não foi possível salvar o cache de e-mails conhecidos.")
    logger_emailpack.info("Total de linhas novas lidas: %d", total_linhas_novas)
    logger_emailpack.info("Total de entradas de log parseadas: %d", total_entradas_parseadas)

    if dirs_ausentes:
        texto = "\n".join(f"- {d}" for d in dirs_ausentes)
        hash_dirs = _calcular_hash_emailpack(texto)
        if _deve_reenviar_emailpack(hash_dirs, arquivo_estado_dirs, CONFIG_EMAILPACK["dedup_minutos"]):
            _enviar_teams_alerta_emailpack(
                f"Monitoramento EmailPack - {len(dirs_ausentes)} diretório(s) inacessível(is)", texto, "aviso",
            )
            _gravar_estado_dedup_emailpack(hash_dirs, arquivo_estado_dirs)
        else:
            logger_emailpack.info("Aviso de diretórios ausentes já notificado recentemente. Não reenviado.")

    if erros_por_servico:
        total_emails = sum(len(v) for v in erros_por_servico.values())
        total_ocorrencias = sum(r.quantidade for emails in erros_por_servico.values() for r in emails.values())

        for servico, emails in erros_por_servico.items():
            for email, resumo in sorted(emails.items()):
                primeira_linha = resumo.mensagem.splitlines()[0] if resumo.mensagem else "(sem detalhe)"
                logger_emailpack.error("[%s] %s -> %dx | %s", servico, email, resumo.quantidade, primeira_linha)

        logger_emailpack.info(
            "Enviando cards separados por e-mail: %d e-mail(s), %d ocorrência(s).", total_emails, total_ocorrencias,
        )
        emails_ignorados = _carregar_emails_ignorados_emailpack()
        _enviar_alertas_por_email_emailpack(pasta, erros_por_servico, emails_ignorados)
    elif not dirs_ausentes:
        logger_emailpack.info("Nenhum ERROR/FATAL encontrado nas linhas novas.")
        if CONFIG_EMAILPACK["heartbeat_sucesso"]:
            _enviar_teams_alerta_emailpack(
                "Monitoramento EmailPack - OK",
                f"Nenhum ERROR/FATAL encontrado nas linhas novas. {total_linhas_novas} linha(s) nova(s), "
                f"{total_entradas_parseadas} entrada(s) parseada(s), "
                f"{sum(len(v) for v in arquivos_por_dir.values())} arquivo(s), "
                f"{len(arquivos_por_dir)} diretório(s) verificado(s).",
                "sucesso",
            )

    if arquivos_com_falha_leitura:
        logger_emailpack.warning("Arquivos com falha de leitura: %s", "; ".join(arquivos_com_falha_leitura))

    logger_emailpack.info("===== Ciclo finalizado =====")

    with _lock_estado_emailpack:
        estado_emailpack["ultima_execucao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        estado_emailpack["total_linhas_novas"] = total_linhas_novas
        estado_emailpack["servicos_verificados"] = len(arquivos_por_dir)
        estado_emailpack["arquivos_verificados"] = sum(len(v) for v in arquivos_por_dir.values())
        estado_emailpack["dirs_ausentes"] = dirs_ausentes
        estado_emailpack["erros_por_servico"] = {
            servico: {
                email: {
                    "quantidade": r.quantidade,
                    "primeira": r.primeira.strftime("%H:%M:%S") if r.primeira else None,
                    "ultima": r.ultima.strftime("%H:%M:%S") if r.ultima else None,
                    "mensagem": r.mensagem.splitlines()[0] if r.mensagem else "",
                }
                for email, r in emails.items()
            }
            for servico, emails in erros_por_servico.items()
        }
        estado_emailpack["ultimo_erro_execucao"] = None


class MonitorEmailPack:
    """Mesma ideia de MonitorContingencias - thread própria, roda de
    tempos em tempos (padrão: 10 em 10 min, igual o script original),
    com trava contra rodadas sobrepostas (manual batendo com a
    periódica, ou clique duplo no botão)."""

    def __init__(self, intervalo_segundos: int = None):
        self.intervalo_segundos = intervalo_segundos or CONFIG_EMAILPACK["intervalo_execucao_segundos"]
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock_execucao = threading.Lock()
        self._executando = False

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _rodar_com_trava(self) -> None:
        with self._lock_execucao:
            if self._executando:
                return
            self._executando = True
        with _lock_estado_emailpack:
            estado_emailpack["executando"] = True
        try:
            _executar_ciclo_emailpack()
        except Exception as e:
            logger_emailpack.exception("Erro fatal no ciclo de monitoramento EmailPack")
            with _lock_estado_emailpack:
                estado_emailpack["ultimo_erro_execucao"] = str(e)
            try:
                _enviar_teams_alerta_emailpack(
                    "Monitoramento EmailPack - FALHA NO SCRIPT", f"Erro fatal: {e}", "erro"
                )
            except Exception:
                pass
        finally:
            with self._lock_execucao:
                self._executando = False
            with _lock_estado_emailpack:
                estado_emailpack["executando"] = False

    def _loop(self) -> None:
        self._rodar_com_trava()
        while not self._stop.is_set():
            if self._stop.wait(self.intervalo_segundos):
                break
            self._rodar_com_trava()

    def forcar_atualizacao(self) -> bool:
        with self._lock_execucao:
            if self._executando:
                return False
        threading.Thread(target=self._rodar_com_trava, daemon=True).start()
        return True

    def parar(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)


_monitor_emailpack_ref: Optional["MonitorEmailPack"] = None



# ---------------------------------------------------------------------------
# Manutenção de Alertas em Banco
# ---------------------------------------------------------------------------
# Cria/lista/ativa-desativa registros na tabela CONFIGURACOES_ALERTA do banco
# de monitoramento (instância de homologação do banco de
# monitoramento). Segue exatamente o schema e as regras descritas na
# documentação interna (Script sempre em base64, Título sempre iniciando com
# "[ALERTA]", Tipo Banco ORACLE/SQL, Disponibilidade 1/0).
#
# ATENÇÃO: eu não tenho como testar a conexão de verdade com esse servidor
# a partir daqui (mesma limitação de rede das outras integrações externas
# deste projeto) - toda a lógica de consulta/insert/update foi escrita e
# testada com uma conexão "de mentira" (mock), reaproveitando exatamente as
# mesmas funções `core.db_utils.conectar_banco` / `executar_query` que o
# resto do projeto já usa em produção. Teste na prática antes de confiar
# pra criar alertas reais.
# ---------------------------------------------------------------------------

TIPOS_BANCO_VALIDOS = ["ORACLE", "SQL"]

# E-mail padrão do monitoramento - todo alerta criado/editado por aqui usa
# esse endereço, travado (não é um campo livre no formulário).
EMAIL_MONITORAMENTO_PADRAO = os.environ.get("PDA_EMAIL_MONITORAMENTO", "monitoramento@example.com")


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


def _listar_alertas_banco() -> dict:
    """Lista os registros de CONFIGURACOES_ALERTA (sem trazer SCRIPT nem
    CONEXAO na listagem - ficam guardados, mas não expostos na tabela por
    serem sensíveis/extensos)."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        resultado = executar_query(
            conn,
            "SELECT ID, CLIENTE, TITULO, TIPO_BANCO, TETO_ALERTA, INTERVALO_MINUTOS, "
            "EMAILS, DISPONIBILIDADE FROM CONFIGURACOES_ALERTA ORDER BY ID DESC",
            fetch=True,
            raise_on_error=True,
        )
        linhas, colunas = resultado
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _criar_alerta_banco(dados: dict, usuario_executor: str) -> dict:
    """Insere um novo registro em CONFIGURACOES_ALERTA. O SCRIPT chega em
    texto puro (SQL normal) e é convertido pra base64 aqui dentro - quem usa
    o formulário não precisa se preocupar em codificar nada na mão. O e-mail
    é sempre o padrão do monitoramento, mesmo que outra coisa tenha vindo
    do formulário (o campo é travado no front, e reforçado aqui também)."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "INSERT INTO CONFIGURACOES_ALERTA "
            "(CONEXAO, SCRIPT, CLIENTE, EMAILS, TIPO_BANCO, TETO_ALERTA, TITULO, "
            "DESCRICAO, INTERVALO_MINUTOS, DISPONIBILIDADE) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=(
                dados["conexao"], script_base64, dados["cliente"], EMAIL_MONITORAMENTO_PADRAO,
                dados["tipo_banco"], dados["teto_alerta"], dados["titulo"],
                dados["descricao"], dados["intervalo_minutos"], dados["disponibilidade"],
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Novo alerta criado em CONFIGURACOES_ALERTA: cliente=%s, titulo=%s, por='%s'", dados["cliente"], dados["titulo"], usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao inserir em CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_alerta_banco(id_alerta: int) -> dict:
    """Busca um registro completo de CONFIGURACOES_ALERTA por ID, incluindo
    CONEXAO/SCRIPT/DESCRICAO (não trazidos na listagem) - usado pra abrir o
    formulário de edição já preenchido. O SCRIPT volta decodificado de
    base64 pra texto puro, pra edição ficar natural."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT ID, CLIENTE, TITULO, TIPO_BANCO, TETO_ALERTA, INTERVALO_MINUTOS, "
            "EMAILS, DISPONIBILIDADE, CONEXAO, SCRIPT, DESCRICAO "
            "FROM CONFIGURACOES_ALERTA WHERE ID = ?",
            params=(id_alerta,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "alerta não encontrado"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        if registro.get("script"):
            try:
                registro["script"] = base64.b64decode(registro["script"]).decode("utf-8")
            except Exception:
                pass  # se não vier em base64 válido por algum motivo, devolve como veio
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar alerta em CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_alerta_banco(id_alerta: int, dados: dict, usuario_executor: str) -> dict:
    """Atualiza TODOS os campos editáveis de um registro existente em
    CONFIGURACOES_ALERTA. Mesma regra do e-mail travado da criação."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_ALERTA SET "
            "CONEXAO=?, SCRIPT=?, CLIENTE=?, EMAILS=?, TIPO_BANCO=?, TETO_ALERTA=?, "
            "TITULO=?, DESCRICAO=?, INTERVALO_MINUTOS=?, DISPONIBILIDADE=? "
            "WHERE ID=?",
            params=(
                dados["conexao"], script_base64, dados["cliente"], EMAIL_MONITORAMENTO_PADRAO,
                dados["tipo_banco"], dados["teto_alerta"], dados["titulo"],
                dados["descricao"], dados["intervalo_minutos"], dados["disponibilidade"],
                id_alerta,
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Alerta ID=%s atualizado em CONFIGURACOES_ALERTA por '%s'.", id_alerta, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _alternar_disponibilidade_banco(id_alerta: int, novo_valor: int, usuario_executor: str) -> dict:
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_ALERTA SET DISPONIBILIDADE = ? WHERE ID = ?",
            params=(novo_valor, id_alerta),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Disponibilidade do alerta ID=%s alterada para %s por '%s'", id_alerta, novo_valor, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar disponibilidade em CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _validar_dados_alerta_banco(dados: dict) -> Optional[str]:
    """Valida os campos do formulário contra as regras documentadas.
    Retorna a mensagem de erro, ou None se está tudo certo.

    'emails' não entra na validação: esse campo é travado no e-mail padrão
    do monitoramento (EMAIL_MONITORAMENTO_PADRAO) e sempre sobrescrito no
    backend, então validar o que veio do formulário pra esse campo
    especificamente não faz sentido - o valor final nunca é o que foi
    enviado."""
    obrigatorios = ["conexao", "script", "cliente", "tipo_banco", "titulo", "descricao"]
    for campo in obrigatorios:
        if not dados.get(campo, "").strip():
            return f"O campo '{campo}' é obrigatório."
    if dados["tipo_banco"].upper() not in TIPOS_BANCO_VALIDOS:
        return "Tipo de banco precisa ser ORACLE ou SQL."
    if not dados["titulo"].strip().startswith("[ALERTA]"):
        return "O título precisa começar com '[ALERTA]'."
    try:
        float(dados["teto_alerta"])
    except (ValueError, TypeError):
        return "Teto do alerta precisa ser um número."
    try:
        intervalo = int(dados["intervalo_minutos"])
        if intervalo <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return "Intervalo (minutos) precisa ser um número inteiro positivo."
    return None


def _montar_texto_gatilho(cliente: str, titulo: str) -> dict:
    """Monta o texto pronto pra colar na abertura do gatilho no Movidesk,
    seguindo o padrão documentado (Nome / Solicitante / Serviço)."""
    titulo_sem_prefixo = titulo.strip()
    if titulo_sem_prefixo.upper().startswith("[ALERTA]"):
        titulo_sem_prefixo = titulo_sem_prefixo[len("[ALERTA]"):].strip()
    return {
        "nome": f"{cliente} - [ALERTA] - {titulo_sem_prefixo}",
        "solicitante": f"OA {cliente}",
        "servico": f"Monitoramento > Alertas > {cliente} > {titulo_sem_prefixo}",
    }


# ---------------------------------------------------------------------------
# Manutenção Rejeições em Banco
# ---------------------------------------------------------------------------
# Mesma ideia da Manutenção de Alertas em Banco (mesmo banco de
# monitoramento, mesmo jeito de guardar o SCRIPT em base64), mas numa
# tabela mais simples - CONFIGURACOES_REJEICAO não tem TITULO, TETO_ALERTA,
# INTERVALO_MINUTOS, DESCRICAO nem DISPONIBILIDADE (não existem colunas
# assim nessa tabela, conforme a documentação que o solicitante passou). O
# script aqui precisa retornar o código da rejeição E a quantidade (não
# só uma contagem, como no alerta). EMAILS é um campo de verdade editável
# aqui (client-specific) - diferente do alerta, onde é sempre travado no
# e-mail padrão do monitoramento; aqui o e-mail do monitoramento já é
# adicionado automaticamente por fora, então não precisa (nem deve)
# entrar nesse campo.
# ---------------------------------------------------------------------------


def _listar_rejeicoes_banco() -> dict:
    """Lista os registros de CONFIGURACOES_REJEICAO (sem trazer SCRIPT nem
    CONEXAO na listagem - mesmo motivo do alerta: sensível/extenso demais
    pra tabela)."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        resultado = executar_query(
            conn,
            "SELECT ID, CLIENTE, TIPO_BANCO, TIPO_AGENDAMENTO, EMAILS FROM CONFIGURACOES_REJEICAO ORDER BY ID DESC",
            fetch=True,
            raise_on_error=True,
        )
        linhas, colunas = resultado
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _criar_rejeicao_banco(dados: dict, usuario_executor: str) -> dict:
    """Insere um novo registro em CONFIGURACOES_REJEICAO. Mesma conversão
    de SCRIPT pra base64 do alerta."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "INSERT INTO CONFIGURACOES_REJEICAO (CONEXAO, SCRIPT, CLIENTE, EMAILS, TIPO_BANCO, TIPO_AGENDAMENTO) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            params=(
                dados["conexao"], script_base64, dados["cliente"],
                dados.get("emails", "").strip(), dados["tipo_banco"], dados["tipo_agendamento"],
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Nova rejeição criada em CONFIGURACOES_REJEICAO: cliente=%s, por='%s'", dados["cliente"], usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao inserir em CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_rejeicao_banco(id_rejeicao: int) -> dict:
    """Busca um registro completo de CONFIGURACOES_REJEICAO por ID,
    incluindo CONEXAO/SCRIPT (não trazidos na listagem) - usado pra abrir
    o formulário de edição já preenchido. O SCRIPT volta decodificado de
    base64 pra texto puro."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT ID, CLIENTE, TIPO_BANCO, TIPO_AGENDAMENTO, EMAILS, CONEXAO, SCRIPT "
            "FROM CONFIGURACOES_REJEICAO WHERE ID = ?",
            params=(id_rejeicao,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "rejeição não encontrada"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        if registro.get("script"):
            try:
                registro["script"] = base64.b64decode(registro["script"]).decode("utf-8")
            except Exception:
                pass
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar rejeição em CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_rejeicao_banco(id_rejeicao: int, dados: dict, usuario_executor: str) -> dict:
    """Atualiza todos os campos editáveis de um registro existente em
    CONFIGURACOES_REJEICAO."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_REJEICAO SET "
            "CONEXAO=?, SCRIPT=?, CLIENTE=?, EMAILS=?, TIPO_BANCO=?, TIPO_AGENDAMENTO=? "
            "WHERE ID=?",
            params=(
                dados["conexao"], script_base64, dados["cliente"],
                dados.get("emails", "").strip(), dados["tipo_banco"], dados["tipo_agendamento"],
                id_rejeicao,
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Rejeição ID=%s atualizada em CONFIGURACOES_REJEICAO por '%s'.", id_rejeicao, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _excluir_rejeicao_banco(id_rejeicao: int, usuario_executor: str) -> dict:
    """Exclui um registro de CONFIGURACOES_REJEICAO. Diferente do alerta
    (que só ativa/desativa via DISPONIBILIDADE), a rejeição não tem essa
    coluna - excluir é a única forma de tirar uma regra de circulação."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "DELETE FROM CONFIGURACOES_REJEICAO WHERE ID = ?",
            params=(id_rejeicao,),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Rejeição ID=%s excluída de CONFIGURACOES_REJEICAO por '%s'.", id_rejeicao, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao excluir de CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _validar_dados_rejeicao_banco(dados: dict) -> Optional[str]:
    """'emails' é OPCIONAL aqui (ao contrário do alerta) - a documentação
    mostra até um INSERT de exemplo sem esse campo. O e-mail do
    monitoramento já é adicionado por fora, automaticamente.
    'tipo_agendamento' é obrigatório (VARCHAR livre - a documentação não
    especificou uma lista fechada de valores válidos, diferente de
    tipo_banco)."""
    obrigatorios = ["conexao", "script", "cliente", "tipo_banco", "tipo_agendamento"]
    for campo in obrigatorios:
        if not dados.get(campo, "").strip():
            return f"O campo '{campo}' é obrigatório."
    if dados["tipo_banco"].upper() not in TIPOS_BANCO_VALIDOS:
        return "Tipo de banco precisa ser ORACLE ou SQL."
    return None


def _montar_texto_gatilho_rejeicao(cliente: str) -> dict:
    """Mesma ideia do gatilho de alerta, adaptado pra rejeição (que não
    tem título)."""
    return {
        "nome": f"{cliente} - [REJEIÇÃO]",
        "solicitante": f"OA {cliente}",
        "servico": f"Monitoramento > Rejeições > {cliente}",
    }


# ---------------------------------------------------------------------------
# Manutenção de Relatórios em Banco
# ---------------------------------------------------------------------------
# Mesma ideia da Manutenção de Alertas/Rejeições (mesmo banco de
# monitoramento, mesmo jeito de guardar o SCRIPT em base64), mas na
# tabela CONFIGURACOES_RELATORIO, que é bem mais rica que as outras duas
# - controla relatórios automáticos (planilha/csv/txt) enviados por
# e-mail pro cliente ou pro Movidesk, com frequência configurável
# (diário/semanal/mensal) e agrupamento opcional de vários relatórios
# num e-mail só.
#
# DISPONIBILIDADE: 1=ativo / 0=inativo - igual CONFIGURACOES_ALERTA. A
# documentação inicial dizia 1=ativo/2=inativo, mas a tabela real usa
# 1/0 - corrigido depois de confirmar com o solicitante (o "Failed to fetch"
# reportado era outra coisa - um valor de HORA_EXECUCAO vindo do banco
# como objeto time, que quebrava o json.dumps antes de mandar qualquer
# resposta - ver _normalizar_hora_execucao e _json_serializar_padrao).
# ---------------------------------------------------------------------------

MODELOS_ARQUIVO_VALIDOS = {"P", "C", "T"}
REINCIDENCIAS_VALIDAS = {"DIARIO", "SEMANAL", "MENSAL"}
DIAS_SEMANA_VALIDOS = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}


def _normalizar_hora_execucao(valor) -> str:
    """HORA_EXECUCAO pode vir do banco como string ('08:00'), como objeto
    datetime.time (comum com pyodbc em colunas TIME), ou até como
    datetime completo em alguns drivers - normaliza tudo pra uma string
    limpa 'HH:MM' (sem segundos), que é o formato que o campo <input
    type="time"> do formulário e a validação (_validar_dados_relatorio_
    banco) esperam. Sem isso, um objeto time chegava intacto até o
    json.dumps e quebrava a resposta inteira (era a causa do "Failed to
    fetch" reportado)."""
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor[:5]  # corta eventuais segundos tipo '08:00:00' -> '08:00'
    if isinstance(valor, (time_cls, datetime)):
        return valor.strftime("%H:%M")
    return str(valor)[:5]


def _listar_relatorios_banco() -> dict:
    """Lista os registros de CONFIGURACOES_RELATORIO (sem CONEXAO/SCRIPT -
    mesmo motivo das outras duas manutenções: sensível/extenso demais pra
    tabela)."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        resultado = executar_query(
            conn,
            "SELECT ID, CLIENTE, TITULO_EMAIL, TIPO_BANCO, MODELO_ARQUIVO, REINCIDENCIA, "
            "HORA_EXECUCAO, DISPONIBILIDADE FROM CONFIGURACOES_RELATORIO ORDER BY ID DESC",
            fetch=True,
            raise_on_error=True,
        )
        linhas, colunas = resultado
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        for registro in registros:
            registro["hora_execucao"] = _normalizar_hora_execucao(registro.get("hora_execucao"))
            if registro.get("disponibilidade") is not None:
                registro["disponibilidade"] = int(registro["disponibilidade"])
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_relatorio_banco(id_relatorio: int) -> dict:
    """Busca um registro completo de CONFIGURACOES_RELATORIO por ID,
    incluindo CONEXAO/SCRIPT - usado pra abrir o formulário de edição já
    preenchido. O SCRIPT volta decodificado de base64 pra texto puro."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT ID, CONEXAO, SCRIPT, EMAILS, TIPO_BANCO, CLIENTE, TITULO_EMAIL, "
            "CORPO_EMAIL, NOME_ARQUIVO, MODELO_ARQUIVO, REINCIDENCIA, DIA_SEMANA, "
            "DIA_MENSAL, HORA_EXECUCAO, DISPONIBILIDADE, AGRUPADOR_RELATORIO "
            "FROM CONFIGURACOES_RELATORIO WHERE ID = ?",
            params=(id_relatorio,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "relatório não encontrado"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        if registro.get("script"):
            try:
                registro["script"] = base64.b64decode(registro["script"]).decode("utf-8")
            except Exception:
                pass
        registro["hora_execucao"] = _normalizar_hora_execucao(registro.get("hora_execucao"))
        if registro.get("disponibilidade") is not None:
            registro["disponibilidade"] = int(registro["disponibilidade"])
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar relatório em CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _campos_relatorio_para_query(dados: dict) -> tuple:
    """Monta a tupla de valores na mesma ordem usada pelo INSERT/UPDATE -
    função única pra não duplicar essa lista comprida em dois lugares e
    arriscar desalinhar a ordem em algum dos dois."""
    return (
        dados["conexao"], dados["script_base64"], dados["emails"], dados["tipo_banco"],
        dados["cliente"], dados["titulo_email"], dados["corpo_email"], dados["nome_arquivo"],
        dados["modelo_arquivo"], dados["reincidencia"], dados.get("dia_semana") or None,
        dados.get("dia_mensal") or None, dados["hora_execucao"], dados["disponibilidade"],
        dados.get("agrupador_relatorio") or None,
    )


def _criar_relatorio_banco(dados: dict, usuario_executor: str) -> dict:
    dados = dict(dados)
    dados["script_base64"] = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "INSERT INTO CONFIGURACOES_RELATORIO "
            "(CONEXAO, SCRIPT, EMAILS, TIPO_BANCO, CLIENTE, TITULO_EMAIL, CORPO_EMAIL, "
            "NOME_ARQUIVO, MODELO_ARQUIVO, REINCIDENCIA, DIA_SEMANA, DIA_MENSAL, "
            "HORA_EXECUCAO, DISPONIBILIDADE, AGRUPADOR_RELATORIO) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=_campos_relatorio_para_query(dados),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info(
            "Novo relatório criado em CONFIGURACOES_RELATORIO: cliente=%s, titulo_email=%s, por='%s'",
            dados["cliente"], dados["titulo_email"], usuario_executor,
        )
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao inserir em CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_relatorio_banco(id_relatorio: int, dados: dict, usuario_executor: str) -> dict:
    dados = dict(dados)
    dados["script_base64"] = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_RELATORIO SET "
            "CONEXAO=?, SCRIPT=?, EMAILS=?, TIPO_BANCO=?, CLIENTE=?, TITULO_EMAIL=?, "
            "CORPO_EMAIL=?, NOME_ARQUIVO=?, MODELO_ARQUIVO=?, REINCIDENCIA=?, DIA_SEMANA=?, "
            "DIA_MENSAL=?, HORA_EXECUCAO=?, DISPONIBILIDADE=?, AGRUPADOR_RELATORIO=? "
            "WHERE ID=?",
            params=_campos_relatorio_para_query(dados) + (id_relatorio,),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Relatório ID=%s atualizado em CONFIGURACOES_RELATORIO por '%s'.", id_relatorio, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _alterar_disponibilidade_relatorio(id_relatorio: int, ativo: bool, usuario_executor: str) -> dict:
    """Ativa/desativa um relatório. Convenção 1=ativo, 0=inativo - igual
    CONFIGURACOES_ALERTA (a documentação inicial dizia 1/2, mas a tabela
    real usa 1/0 - corrigido depois de confirmar com o solicitante)."""
    novo_valor = 1 if ativo else 0
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_RELATORIO SET DISPONIBILIDADE = ? WHERE ID = ?",
            params=(novo_valor, id_relatorio),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info(
            "Relatório ID=%s teve disponibilidade alterada pra %s por '%s'.", id_relatorio, novo_valor, usuario_executor
        )
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao alterar disponibilidade em CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _validar_dados_relatorio_banco(dados: dict) -> Optional[str]:
    obrigatorios = [
        "conexao", "script", "emails", "tipo_banco", "cliente", "titulo_email",
        "corpo_email", "nome_arquivo", "modelo_arquivo", "reincidencia", "hora_execucao",
    ]
    for campo in obrigatorios:
        if not dados.get(campo, "").strip():
            return f"O campo '{campo}' é obrigatório."

    if dados["tipo_banco"].upper() not in TIPOS_BANCO_VALIDOS:
        return "Tipo de banco precisa ser ORACLE ou SQL."

    if dados["modelo_arquivo"].upper() not in MODELOS_ARQUIVO_VALIDOS:
        return "Modelo do arquivo precisa ser P (planilha), C (csv) ou T (txt)."

    reincidencia = dados["reincidencia"].upper()
    if reincidencia not in REINCIDENCIAS_VALIDAS:
        return "Reincidência precisa ser DIARIO, SEMANAL ou MENSAL."

    # dia_semana só é validado/obrigatório pra reincidência SEMANAL - se
    # não informado nesse caso, a documentação diz pra assumir Terça-Feira
    dia_semana = (dados.get("dia_semana") or "").strip()
    if reincidencia == "SEMANAL":
        if not dia_semana:
            dados["dia_semana"] = "Tuesday"
        elif dia_semana not in DIAS_SEMANA_VALIDOS:
            return "Dia da semana precisa ser um dia em inglês (ex.: Monday, Tuesday...)."
    else:
        dados["dia_semana"] = ""

    # dia_mensal só é validado/obrigatório pra reincidência MENSAL
    dia_mensal = (dados.get("dia_mensal") or "").strip()
    if reincidencia == "MENSAL":
        try:
            dia_mensal_num = int(dia_mensal)
            if not (1 <= dia_mensal_num <= 31):
                raise ValueError
        except (ValueError, TypeError):
            return "Dia do mês precisa ser um número de 1 a 31 (obrigatório pra reincidência MENSAL)."
    else:
        dados["dia_mensal"] = ""

    hora = dados["hora_execucao"].strip()
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
        return "Hora de execução precisa estar no formato HH:MM (00:00 a 23:59)."

    return None


# ---------------------------------------------------------------------------
# Relatórios Shein
# ---------------------------------------------------------------------------
# Porta pro painel web o processo que hoje roda manualmente num notebook
# Jupyter: consulta CTe/CTe-canceladas do banco de produção do Shein
# (shein_cte_prd) pra uma data específica, e gera os dois arquivos Excel
# (Notas e Canceladas) exatamente como o notebook fazia - incluindo o
# split em "Parte 1"/"Parte 2" quando passa de ~1 milhão de linhas.
#
# Igual às outras integrações externas deste projeto: eu não tenho acesso
# de rede ao servidor de banco daqui, então não consigo testar a
# conexão de verdade - toda a lógica (consulta, geração do Excel, split de
# planilha) foi testada com dados e conexão simulados. Teste na prática
# antes de confiar pra decisão real.
# ---------------------------------------------------------------------------

MAX_LINHAS_POR_ABA_EXCEL = 1_048_576 - 1


def _config_shein() -> dict:
    """Lê as credenciais do banco Shein - CREDENCIAIS_CENTRALIZADAS.env
    primeiro (seção [infra_shein]), cai pro .env.shein tradicional se
    essa seção não existir (ver core/config_central.py)."""
    valores = _obter_config_hibrido(
        "infra_shein", ".env.shein",
        ["SHEIN_DB_SERVER", "SHEIN_DB_DATABASE", "SHEIN_DB_USER", "SHEIN_DB_PASSWORD"],
    )
    return {
        "server": valores["SHEIN_DB_SERVER"],
        "database": valores["SHEIN_DB_DATABASE"],
        "username": valores["SHEIN_DB_USER"],
        "password": _obter_valor_config("shein::SHEIN_DB_PASSWORD", valores["SHEIN_DB_PASSWORD"]),
    }


def _conectar_shein():
    cfg = _config_shein()
    if not all(cfg.values()):
        return None, "Credenciais do banco Shein não configuradas (.env.shein)."
    try:
        conn = conectar_banco(cfg["server"], cfg["database"], cfg["username"], cfg["password"])
    except Exception as e:
        logger.exception("Erro inesperado ao conectar no banco Shein")
        return None, f"Erro inesperado ao conectar: {e}"
    if not conn:
        return None, "Não foi possível conectar ao banco Shein."
    return conn, None


# ---------------------------------------------------------------------------
# Indicadores Movidesk - dashboard admin com métricas de escalonamentos,
# dúvidas e sincronização, puxadas direto do banco (Movidesk). Conexão
# própria (.env.indicadores_movidesk), separada das outras.
# ---------------------------------------------------------------------------


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


def _buscar_tabelas_parecidas(conn, termo_busca: str) -> list:
    """Procura tabelas cujo nome contenha um pedaço do termo de busca (sem
    diferenciar maiúsculas/minúsculas), em qualquer schema do banco - ajuda
    a encontrar o nome/schema corretos quando uma consulta falha com
    "Invalid object name", sem precisar abrir o SSMS pra procurar na mão."""
    try:
        pedaco = re.sub(r"[_\W]+", "", termo_busca)[:8]  # pedaço reconhecível, sem underscore/símbolos
        df = pd.read_sql(
            "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE ?",
            conn, params=(f"%{pedaco}%",),
        )
        return [f"{r['TABLE_SCHEMA']}.{r['TABLE_NAME']}" for r in df.to_dict("records")]
    except Exception:
        return []  # diagnóstico é só um extra - se ele mesmo falhar, não deve mascarar o erro original


def _buscar_colunas_tabela(conn, nome_tabela: str) -> list:
    """Lista as colunas REAIS de uma tabela (via INFORMATION_SCHEMA.COLUMNS)
    - usado quando o erro é de COLUNA errada (não de tabela), pra mostrar
    de cara quais colunas existem de verdade, sem precisar abrir o SSMS."""
    try:
        df = pd.read_sql(
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ? ORDER BY ORDINAL_POSITION",
            conn, params=(nome_tabela,),
        )
        return df["COLUMN_NAME"].tolist()
    except Exception:
        return []


def _executar_consulta_indicador(conn, nome_amigavel: str, termo_busca: str, query: str, params: tuple = ()):
    """Roda uma consulta isolada pro dashboard de indicadores - se
    falhar, NÃO derruba as outras 3 seções (cada uma é independente).
    O diagnóstico é esperto sobre o TIPO de erro: se for tabela que não
    existe (42S02 / "Invalid object name"), sugere tabelas parecidas; se
    for coluna que não existe (42S22 / "Invalid column name"), lista as
    colunas REAIS da tabela - bem mais direto ao ponto do que ficar
    adivinhando nome de coluna às cegas. Retorna
    (dataframe_ou_None, mensagem_de_erro_ou_None)."""
    try:
        return pd.read_sql(query, conn, params=params), None
    except Exception as e:
        texto_erro = str(e)
        msg = texto_erro
        eh_erro_de_coluna = "42S22" in texto_erro or "Invalid column name" in texto_erro
        if eh_erro_de_coluna:
            colunas_reais = _buscar_colunas_tabela(conn, termo_busca)
            if colunas_reais:
                msg += f" — colunas que realmente existem em '{termo_busca}': {', '.join(colunas_reais)}"
            else:
                msg += f" — não consegui listar as colunas de '{termo_busca}' (a tabela em si existe?)."
        else:
            sugestoes = _buscar_tabelas_parecidas(conn, termo_busca)
            if sugestoes:
                msg += f" — tabelas parecidas encontradas neste banco: {', '.join(sugestoes[:8])}"
            else:
                msg += " — não encontrei nenhuma tabela parecida neste banco; confirme se é o banco certo."
        return None, msg


def _montar_secao_indicador(df, erro_query: Optional[str], construtor) -> dict:
    """Empacota o resultado de uma consulta no formato {ok, erro, ...}
    que o front-end espera - isola erros que aconteçam até na hora de
    PROCESSAR o resultado (não só na query em si, ex.: coluna com nome
    diferente do esperado), pra um problema aqui também ficar restrito a
    essa seção específica, sem derrubar as outras 3."""
    if erro_query:
        return {"ok": False, "erro": erro_query}
    try:
        return {"ok": True, **construtor(df)}
    except Exception as e:
        return {"ok": False, "erro": f"A consulta funcionou, mas não consegui processar o resultado: {e}"}


def _consultar_indicadores_movidesk(data_inicio_str: str, data_fim_str: str = None) -> dict:
    """Roda as 4 consultas de indicadores (sincronização, dúvidas abertas,
    dúvidas processadas, escalonamentos por marcador), todas filtradas
    entre `data_inicio_str` e `data_fim_str` (formato YYYY-MM-DD, vindo
    do filtro de data da página) - `data_fim_str` é opcional, se não
    vier assume "agora" (mantém compatível com quem só manda a data de
    início). Cada uma é INDEPENDENTE - se uma tabela tiver nome errado
    ou não existir (ou o resultado vier num formato inesperado), só
    aquela seção fica com erro, as outras continuam mostrando dado
    normal. Retorna um dict já pronto pra virar JSON, com "ok" geral (só
    False se nem conseguiu conectar) e um "ok" por seção.

    Também traz "chamados_por_analista" - contagem de tickets distintos
    por pessoa no período, a partir da MESMA tabela apontamentos que o
    card de Horas Trabalhadas usa (reaproveita a mesma conexão, sem
    precisar abrir uma segunda)."""
    try:
        dt_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return {"ok": False, "erro": "Data inválida (use o formato AAAA-MM-DD)."}

    if data_fim_str:
        try:
            dt_fim = datetime.strptime(data_fim_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return {"ok": False, "erro": "Data final inválida (use o formato AAAA-MM-DD)."}
    else:
        dt_fim = datetime.now().date()
    if dt_fim < dt_inicio:
        return {"ok": False, "erro": "Data final não pode ser antes da data inicial."}

    data_fim_exclusiva = (dt_fim + timedelta(days=1)).strftime("%Y-%m-%d")

    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}

    try:
        df_sinc, erro_sinc = _executar_consulta_indicador(
            conn, "Controle de Sincronização", "ControleSincronizacao",
            "SELECT nomeProcesso AS [Processo], ultimaExecucao AS [Última Execução], "
            "statusUltimaExecucao AS [Status], registrosAtualizados AS [Registros Atualizados], "
            "mensagemUltimaExecucao AS [Mensagem] FROM ControleSincronizacao",
        )

        df_duv_qtd, erro_duv_qtd = _executar_consulta_indicador(
            conn, "Dúvidas abertas", "Tickets",
            "SELECT COUNT(*) AS qtd FROM Tickets WHERE tags LIKE '%Dúvida%' "
            "AND createdDate >= ? AND createdDate < ?",
            (data_inicio_str, data_fim_exclusiva),
        )

        df_duv_proc, erro_duv_proc = _executar_consulta_indicador(
            conn, "Dúvidas processadas", "Movidesk_Duvidas_Processadas",
            "SELECT ticket_id AS [Ticket ID], cliente AS [Cliente], ticket_subject AS [Título], "
            "solicitado_por_nome AS [Solicitado Por], data_acao AS [Data Ação] "
            "FROM Movidesk_Duvidas_Processadas WHERE data_detectado >= ? AND data_detectado < ?",
            (data_inicio_str, data_fim_exclusiva),
        )

        df_escal, erro_escal = _executar_consulta_indicador(
            conn, "Escalonamentos", "Movidesk_Escalonamentos_Processados",
            "SELECT COUNT(*) AS qtd, marcador_macro FROM Movidesk_Escalonamentos_Processados "
            "WHERE data_acao >= ? AND data_acao < ? GROUP BY marcador_macro ORDER BY COUNT(*) DESC",
            (data_inicio_str, data_fim_exclusiva),
        )

        chamados_por_analista = {"ok": True, "dados": []}
        try:
            apontamentos = _buscar_apontamentos_movidesk(conn, dt_inicio, dt_fim)
            contagem: dict = {}
            for row in apontamentos:
                analista = str(row.get("createdbyname") or "").strip().upper()
                ticket_id = row.get("id")
                if not analista or ticket_id is None:
                    continue
                contagem.setdefault(analista, set()).add(ticket_id)
            chamados_por_analista["dados"] = sorted(
                [{"analista": nome, "qtd": len(tickets)} for nome, tickets in contagem.items()],
                key=lambda x: x["qtd"], reverse=True,
            )
        except Exception as e:
            logger.exception("Erro ao calcular chamados por analista (apontamentos)")
            chamados_por_analista = {"ok": False, "erro": str(e)}

        return {
            "ok": True,
            "sincronizacao": _montar_secao_indicador(
                df_sinc, erro_sinc,
                lambda df: {"dados": df.fillna("").astype(str).to_dict("records")},
            ),
            "duvidas_abertas": _montar_secao_indicador(
                df_duv_qtd, erro_duv_qtd,
                lambda df: {"valor": int(df.iloc[0]["qtd"]) if not df.empty else 0},
            ),
            "duvidas_processadas": _montar_secao_indicador(
                df_duv_proc, erro_duv_proc,
                lambda df: {"dados": df.fillna("").astype(str).to_dict("records")},
            ),
            "escalonamentos": _montar_secao_indicador(
                df_escal, erro_escal,
                lambda df: {
                    "dados": [
                        {"marcador": r["marcador_macro"], "qtd": int(r["qtd"])}
                        for r in df.fillna("Sem marcador").to_dict("records")
                    ],
                },
            ),
            "chamados_por_analista": chamados_por_analista,
        }
    except Exception as e:
        logger.exception("Erro inesperado ao consultar indicadores Movidesk")
        return {"ok": False, "erro": f"Erro inesperado ao consultar o banco: {e}"}
    finally:
        fechar_conexao(conn)


# ---------------------------------------------------------------------------
# Horas trabalhadas (Movidesk) - baseado no relatorio_horas.py que o solicitante
# já usa: busca os tickets com apontamento de tempo direto na API pública
# do Movidesk (não é banco SQL, é REST), soma os minutos únicos apontados
# por analista/dia (evitando contar duas vezes um mesmo minuto se houver
# apontamentos sobrepostos), e compara com uma "meta" de minutos calculada
# a partir do tipo de escala de cada pessoa (6x1, 5x2, 12x36, etc.).
#
# IMPORTANTE (conforme pedido): NÃO filtra só quem está no escala.json -
# busca todo mundo que tiver apontamento no período. O escala.json só é
# usado pra saber o TIPO DE ESCALA de quem está cadastrado nele; quem não
# está cadastrado cai no padrão 5x2 (mesmo comportamento do script
# original: "if not tipo: tipo = '5x2'").
# ---------------------------------------------------------------------------


def _listar_usuarios_movidesk() -> dict:
    """Lista os usuários da tabela 'usuarios' (banco movidesk, mesma
    conexão de Indicadores Movidesk/Apontamentos) - usado tanto pra
    popular o select de vínculo na aba Usuários do PDA quanto pra
    carregar a escala de todo mundo de uma vez só (_carregar_escala_
    horas), sem precisar de uma consulta por pessoa."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT id, nome, email, cargo, escala, ativo FROM usuarios ORDER BY nome",
            fetch=True,
            raise_on_error=True,
        )
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar usuarios (banco movidesk)")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_usuario_movidesk(id_usuario: str) -> dict:
    """Busca um registro completo da tabela usuarios por ID (o id nessa
    tabela é texto, não numérico - confirmado na amostra de dados: IDs
    tipo '1000530679', '399590887' etc.)."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT id, nome, email, cargo, escala, horainicio, horafim, diasTrabalhados, ativo "
            "FROM usuarios WHERE id = ?",
            params=(id_usuario,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "usuário não encontrado na tabela usuarios"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        registro["horainicio"] = _normalizar_hora_execucao(registro.get("horainicio"))
        registro["horafim"] = _normalizar_hora_execucao(registro.get("horafim"))
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar usuario (banco movidesk)")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_usuario_movidesk(id_usuario: str, dados: dict, usuario_executor: str) -> dict:
    """Atualiza cargo/email/escala/horário/dias trabalhados de um
    registro da tabela usuarios (banco movidesk). Não mexe no ID nem no
    nome - esses continuam vindo de onde quer que essa tabela seja
    alimentada (provavelmente sincronizada do Movidesk em si)."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE usuarios SET cargo=?, email=?, escala=?, horainicio=?, horafim=?, diasTrabalhados=? "
            "WHERE id=?",
            params=(
                dados.get("cargo") or None, dados.get("email") or None, dados.get("escala") or None,
                dados.get("horainicio") or None, dados.get("horafim") or None,
                dados.get("diasTrabalhados") or None, id_usuario,
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info(
            "Usuário Movidesk ID=%s (tabela usuarios) atualizado por '%s'.", id_usuario, usuario_executor
        )
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar usuario (banco movidesk)")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


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
    entre dias (isso foi corrigido a pedido do solicitante - a versão anterior
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
    pedido explícito do solicitante: usar como métrica só os dias com registro
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
    Movidesk - confirmado com o solicitante que é a mesma instância
    de banco, mesmo usuário serve pras duas bases) - troca
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
    do solicitante: quando 1 hora foi registrada em 2 chamados ao mesmo tempo,
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


def _buscar_titulos_tickets(ticket_ids: list) -> dict:
    """Busca o título/assunto (coluna `subject`) de uma lista de tickets
    na tabela Tickets, pra enriquecer a exportação em Excel. Conexão
    PRÓPRIA e feita só sob demanda (só quando alguém exporta) - o
    resumo/tela normal de Horas Trabalhadas não precisa disso, então não
    faz sentido pesar a consulta principal com esse JOIN toda vez.
    Devolve {ticket_id: titulo}; ticket sem título encontrado
    simplesmente não entra no dict (fica em branco na planilha)."""
    ids_validos = sorted({int(i) for i in ticket_ids if i is not None})
    if not ids_validos:
        return {}
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        logger.warning("Não foi possível buscar títulos de ticket pra exportação: %s", erro)
        return {}
    try:
        titulos = {}
        # em lotes de 1000 IDs por vez - evita estourar o limite de
        # parâmetros de uma query parametrizada em lotes muito grandes
        # (exportação de um mês inteiro pode ter centenas de tickets)
        TAMANHO_LOTE = 1000
        for inicio in range(0, len(ids_validos), TAMANHO_LOTE):
            lote = ids_validos[inicio:inicio + TAMANHO_LOTE]
            placeholders = ",".join("?" for _ in lote)
            linhas, colunas = executar_query(
                conn, f"SELECT id, subject FROM Tickets WHERE id IN ({placeholders})",
                params=tuple(lote), fetch=True, raise_on_error=True,
            )
            colunas_lower = [c.lower() for c in colunas]
            for linha in linhas:
                registro = dict(zip(colunas_lower, linha))
                titulos[int(registro["id"])] = registro.get("subject") or ""
        return titulos
    except Exception:
        logger.exception("Erro ao buscar títulos de ticket (Tickets.subject) pra exportação")
        return {}
    finally:
        fechar_conexao(conn)


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
    detalhe = None
    if incluir_detalhe:
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

        # título do ticket (Tickets.subject) - busca em lote só aqui, uma
        # vez pra todos os IDs distintos do período, em vez de uma query
        # por linha
        titulos_por_ticket = _buscar_titulos_tickets([d["ticket_id"] for d in detalhe])
        for d in detalhe:
            d["titulo"] = titulos_por_ticket.get(d["ticket_id"], "")

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


def _gerar_excel_export_horas(linhas_resumo: list, detalhe: list) -> bytes:
    """Gera o .xlsx de exportação de Horas Trabalhadas - usado tanto pela
    página Horas Trabalhadas (admin, período com todo mundo) quanto pelo
    Perfil (uma pessoa só, ela mesma ou vista por um admin). Duas abas:
    'Resumo Diário' (mesmo agregado por dia que já aparece nas duas
    telas) e 'Detalhe por Ticket' (cada apontamento individual, sem a
    deduplicação por minuto que o resumo faz - pra dar pra validar o
    resumo linha a linha), com o título do ticket (Tickets.subject) como
    última coluna, mais larga que as outras pra caber o texto.
    Formatação básica (cabeçalho colorido, largura de coluna, congelar
    topo, autofiltro) pra abrir bem no Excel."""
    df_resumo = pd.DataFrame([{
        "Analista": l["analista"], "Data": l["data"], "Escala": l["escala"],
        "Horas Trabalhadas": l["horas_trabalhadas"], "Meta": l["meta_horas"],
        "%": l["percentual"], "Qtd. Tickets": l["qtd_tickets"],
    } for l in linhas_resumo])
    df_detalhe = pd.DataFrame([{
        "Analista": d["analista"], "Data": d["data"], "Ticket ID": d["ticket_id"],
        "Início": d["inicio"], "Fim": d["fim"], "Duração": d["duracao"],
        "Título do Ticket": d.get("titulo", ""),
    } for d in detalhe])

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book
        formato_cabecalho = workbook.add_format({
            "bold": True, "font_color": "#ffffff", "bg_color": "#2db8cf",
            "align": "left", "valign": "vcenter", "font_size": 10, "border": 0,
        })

        abas = (
            (df_resumo, "Resumo Diário", [22, 12, 10, 16, 12, 8, 12]),
            (df_detalhe, "Detalhe por Ticket", [22, 12, 12, 10, 10, 12, 60]),
        )
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


def _pasta_saida_relatorios_shein(data: datetime) -> str:
    """Pasta local onde os relatórios de um dia específico ficam salvos -
    organizada em Mês (inglês) / DD-MM-YYYY, espelhando exatamente a
    mesma estrutura usada no SharePoint (ver _enviar_relatorio_shein_
    sharepoint) - pedido pra manter os dois arquivamentos consistentes a
    partir de agora. Cria a pasta se ainda não existir."""
    pasta = os.path.join(
        _base_path_app(), "relatorios_shein_saida",
        MESES_INGLES[data.month], data.strftime("%d-%m-%Y"),
    )
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _localizar_pasta_relatorio_shein_por_data_str(data_arquivo: str) -> str:
    """Reconstrói a pasta local (Mês/DD-MM-YYYY) a partir de uma data no
    formato 'DD-MM-YYYY' (o mesmo formato usado no nome dos arquivos) -
    usado pelas rotas que só recebem a data em texto, sem um objeto
    datetime já pronto."""
    data_obj = datetime.strptime(data_arquivo, "%d-%m-%Y")
    return _pasta_saida_relatorios_shein(data_obj)


def _construir_queries_shein(data: datetime) -> tuple:
    """Mesma consulta SQL usada hoje no notebook Jupyter (CTe + CTe
    canceladas), só parametrizada pela data. Mantida fiel ao original."""
    data_ini = data.strftime("%Y-%m-%d 00:00:00")
    data_fim = data.strftime("%Y-%m-%d 23:59:59")

    query_notas = f"""
SELECT
    ic.IND_STATUS               AS [STATUS],
    ic.B_SERIE                  AS [SERIE],
    icx.B_NCT                   AS [NUMERO],
    CONVERT(date, icx.B_DHEMI)  AS [DATA_EMISSAO],
    icx.D_CNPJ                  AS [CNPJ EMITENTE],
    ISNULL(icx.H_CNPJ, '-')     AS [CNPJ DESTINATARIO],
    icx.H_CPF                   AS [CPF DESTINATARIO],
    icx.H_XNOME                 AS [NOME DESTINATARIO],
    icx.E_CNPJ                  AS [CNPJ REMETENTE],
    icx.E_XNOME                 AS [NOME REMETENTE],
    icx.A_ID                    AS [CHAVE],
    icx.B_TPEMIS                AS [TIPO EMISSAO],
    icx.B_MODAL                 AS [MODAL],
    CASE
        WHEN B_TOMA IS NULL THEN icx.B_TOMA_CNPJ
        WHEN B_TOMA = 0 THEN icx.E_CNPJ
        WHEN B_TOMA = 1 THEN icx.F_CNPJ
        WHEN B_TOMA = 2 THEN icx.G_CNPJ
        WHEN B_TOMA = 3 THEN icx.H_CNPJ
        ELSE '-'
    END AS [CNPJ TOMADOR],
    icx.B_TOMA_XNOME                           AS [NOME TOMADOR],
    icx.B_CFOP                                 AS [CFOP],
    icx.J_CST                                  AS [CST],
    icx.B_XMUNINI                              AS [MUNICIPIO INICIAL],
    icx.B_CMUNINI                              AS [CODIGO MUNICIPIO INICIAL],
    icx.B_XMUNFIM                              AS [MUNICIPIO FIM],
    icx.B_CMUNFIM                              AS [CODIGO MUNICIPIO FIM],
    icx.B_UFINI                                AS [ESTADO INICIAL],
    icx.B_UFFIM                                AS [ESTADO FIM],
    REPLACE(ISNULL(icx.J_VICMS, 0), ',', '.')  AS [VALOR ICMS],
    REPLACE(ISNULL(icx.J_PICMS, 0), ',', '.')  AS [ALIQUOTA ICMS],
    REPLACE(icx.I_VTPREST, ',', '.')           AS [VALOR TOTAL],
    icn.E_CHAVE                                AS [CHAVE NFE],
    ISNULL(icx.J_VICMSOUTRAUF, 0)              AS [VALOR ICMS OUTRA UF],
    ISNULL(icx.J_PICMSOUTRAUF, 0)              AS [ALIQUOTA ICMS OUTRA UF]
FROM INTERF_CTE_XML icx
JOIN INTERF_CTE ic
  ON icx.INTERF_CTE_FK = ic.ID
RIGHT JOIN INTERF_CTE_NFE icn
  ON icx.ID = icn.INTERF_CTE_XML_FK
WHERE icx.B_DHEMI >= '{data_ini}'
  AND icx.B_DHEMI <= '{data_fim}'
ORDER BY icx.ID ASC;
"""

    query_canceladas = f"""
SELECT
    ic.IND_STATUS                       AS [STATUS],
    ic.B_SERIE                          AS [SERIE],
    icx.B_NCT                           AS [NUMERO],
    CONVERT(date, icx.B_DHEMI)          AS [DATA_EMISSAO],
    icx.D_CNPJ                          AS [CNPJ EMITENTE],
    ISNULL(icx.H_CNPJ, '-')             AS [CNPJ DESTINATARIO],
    icx.H_CPF                           AS [CPF DESTINATARIO],
    icx.H_XNOME                         AS [NOME DESTINATARIO],
    icx.E_CNPJ                          AS [CNPJ REMETENTE],
    icx.E_XNOME                         AS [NOME REMETENTE],
    icx.A_ID                            AS [CHAVE],
    icx.B_TPEMIS                        AS [TIPO EMISSAO],
    icx.B_MODAL                         AS [MODAL],
    CASE
        WHEN B_TOMA IS NULL THEN icx.B_TOMA_CNPJ
        WHEN B_TOMA = 0 THEN icx.E_CNPJ
        WHEN B_TOMA = 1 THEN icx.F_CNPJ
        WHEN B_TOMA = 2 THEN icx.G_CNPJ
        WHEN B_TOMA = 3 THEN icx.H_CNPJ
        ELSE '-'
    END AS [CNPJ TOMADOR],
    icx.B_TOMA_XNOME                           AS [NOME TOMADOR],
    icx.B_CFOP                                 AS [CFOP],
    icx.J_CST                                  AS [CST],
    icx.B_XMUNINI                              AS [MUNICIPIO INICIAL],
    icx.B_CMUNINI                              AS [CODIGO MUNICIPIO INICIAL],
    icx.B_XMUNFIM                              AS [MUNICIPIO FIM],
    icx.B_CMUNFIM                              AS [CODIGO MUNICIPIO FIM],
    icx.B_UFINI                                AS [ESTADO INICIAL],
    icx.B_UFFIM                                AS [ESTADO FIM],
    REPLACE(ISNULL(icx.J_VICMS, 0), ',', '.')  AS [VALOR ICMS],
    REPLACE(ISNULL(icx.J_PICMS, 0), ',', '.')  AS [ALIQUOTA ICMS],
    REPLACE(icx.I_VTPREST, ',', '.')           AS [VALOR TOTAL],
    icn.E_CHAVE                                AS [CHAVE NFE],
    ISNULL(icx.J_VICMSOUTRAUF, 0)              AS [VALOR ICMS OUTRA UF],
    ISNULL(icx.J_PICMSOUTRAUF, 0)              AS [ALIQUOTA ICMS OUTRA UF]
FROM INTERF_CTE_XML icx
JOIN INTERF_CTE ic
  ON icx.INTERF_CTE_FK = ic.ID
JOIN INTERF_CTE_NFE icn
  ON icx.ID = icn.INTERF_CTE_XML_FK
JOIN INTERF_EVENTO_FISCAL ief
  ON ic.ID = ief.EDOC_FK
WHERE ief.DATA_HORA_EVENTO >= '{data_ini}'
  AND ief.DATA_HORA_EVENTO <= '{data_fim}'
  AND ic.IND_STATUS = 21
ORDER BY icx.ID ASC;
"""
    return query_notas, query_canceladas


def _dataframe_shein(query: str, conn) -> "pd.DataFrame":
    """Mesma função `dataframe()` do notebook original - roda a query e
    normaliza as colunas de CNPJ pra string (evita notação científica /
    perda de zero à esquerda no Excel)."""
    df = pd.read_sql(query, conn)
    if df.empty:
        return df
    df = df.fillna("-")
    for coluna in ("CNPJ EMITENTE", "CNPJ REMETENTE", "CNPJ TOMADOR"):
        if coluna in df.columns:
            df[coluna] = df[coluna].astype(str)
    return df


def _gravar_excel_shein(df: "pd.DataFrame", caminho: str, nome_aba: str) -> None:
    """Grava um DataFrame em Excel, dividindo em 'Parte 1'/'Parte 2' se
    passar do limite de linhas de uma aba (igual o notebook original)."""
    with pd.ExcelWriter(caminho, engine="xlsxwriter") as writer:
        if len(df) > MAX_LINHAS_POR_ABA_EXCEL:
            df.iloc[:MAX_LINHAS_POR_ABA_EXCEL].to_excel(writer, sheet_name=f"{nome_aba} Parte 1", index=False)
            df.iloc[MAX_LINHAS_POR_ABA_EXCEL:].to_excel(writer, sheet_name=f"{nome_aba} Parte 2", index=False)
        else:
            df.to_excel(writer, sheet_name=nome_aba, index=False)


def _gerar_relatorio_shein(data_str: str) -> dict:
    """Gera os relatórios de Notas e Canceladas do Shein pra uma data
    (formato YYYY-MM-DD). Retorna os nomes dos arquivos gerados (prontos
    pra download) e a contagem de linhas de cada um."""
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        logger_shein.error("Data inválida recebida: %r", data_str)
        return {"ok": False, "erro": "Data inválida."}

    logger_shein.info("Iniciando geração do relatório Shein pra %s.", data.strftime("%d-%m-%Y"))

    conn, erro = _conectar_shein()
    if erro:
        logger_shein.error("Falha ao conectar no banco Shein: %s", erro)
        return {"ok": False, "erro": erro}

    pasta = None
    try:
        query_notas, query_canceladas = _construir_queries_shein(data)
        df_notas = _dataframe_shein(query_notas, conn)
        logger_shein.info("Query de Notas retornou %d linha(s).", len(df_notas))
        df_canceladas = _dataframe_shein(query_canceladas, conn)
        logger_shein.info("Query de Canceladas retornou %d linha(s).", len(df_canceladas))

        data_arquivo = data.strftime("%d-%m-%Y")
        pasta = _pasta_saida_relatorios_shein(data)
        # padrão de nomenclatura pedido pelo cliente (voltou a como era antes
        # de 07/08): Notas sem prefixo nenhum, Canceladas só com "Canceladas_"
        # na frente - sem "Shein_" em nenhum dos dois.
        nome_notas = f"{data_arquivo}.xlsx"
        nome_canceladas = f"Canceladas_{data_arquivo}.xlsx"
        _gravar_excel_shein(df_notas, os.path.join(pasta, nome_notas), "Notas")
        logger_shein.info("Arquivo '%s' gravado em %s.", nome_notas, pasta)
        _gravar_excel_shein(df_canceladas, os.path.join(pasta, nome_canceladas), "Canceladas")
        logger_shein.info("Arquivo '%s' gravado em %s.", nome_canceladas, pasta)

        logger.info(
            "Relatório Shein gerado pra %s: %d notas, %d canceladas.",
            data_arquivo, len(df_notas), len(df_canceladas),
        )
        return {
            "ok": True,
            "arquivo_notas": nome_notas,
            "arquivo_canceladas": nome_canceladas,
            "linhas_notas": len(df_notas),
            "linhas_canceladas": len(df_canceladas),
        }
    except PermissionError as e:
        # NÃO é erro de SharePoint (nem chegou perto disso ainda - a etapa
        # de upload só roda depois que esse retorno é bem-sucedido) - é
        # permissão de escrita NA PASTA LOCAL relatorios_shein_saida,
        # mesma causa raiz do Errno 13 já visto no log do EmailPack:
        # a pasta/arquivo foi criado por outra sessão do Windows e o
        # usuário atual não tem permissão de gravação nela. Mensagem
        # separada da genérica abaixo pra não confundir com falha de
        # conexão/autenticação no Graph.
        logger_shein.exception("Sem permissão pra gravar o relatório Shein localmente (pasta %s)", pasta)
        return {
            "ok": False,
            "erro": (
                f"Sem permissão pra gravar o arquivo localmente: {e}. "
                "Isso não é falha de conexão com o SharePoint - o problema é "
                "de permissão NTFS na pasta relatorios_shein_saida (provavelmente "
                "criada por outra sessão do Windows). Confira em Propriedades → "
                "Segurança da pasta se o usuário que roda essa automação tem "
                "permissão de Modificar."
            ),
        }
    except Exception as e:
        logger_shein.exception("Erro ao gerar relatório Shein pra %s", data_str)
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)
        logger_shein.info("Conexão com o banco Shein encerrada.")


# ---------------------------------------------------------------------------
# Envio automático dos Relatórios Shein pro SharePoint - todos os dias às
# 08:00, o relatório do dia anterior é gerado e enviado sozinho.
# ---------------------------------------------------------------------------
# ATENÇÃO - leia antes de confiar nisso:
#   A autenticação usa o fluxo "usuário e senha direto" do Microsoft Graph
#   (ROPC - Resource Owner Password Credentials), porque é o único jeito
#   de autenticar só com login/senha, sem precisar registrar um aplicativo
#   próprio no Azure AD da empresa (o que eu não tenho como fazer sozinho -
#   precisaria de acesso de administrador do Microsoft 365/Azure AD).
#
#   ISSO TEM UMA LIMITAÇÃO IMPORTANTE: ROPC **não funciona** se a conta
#   tiver autenticação multifator (MFA) obrigatória, nem se o Azure AD do
#   tenant tiver esse fluxo bloqueado por política de segurança (comum em
#   tenants configurados mais recentemente). Se der erro de autenticação,
#   é bem provável que seja por causa disso - nesse caso, a solução correta
#   é pedir pra alguém com acesso de administrador do Microsoft 365 criar
#   um "App Registration" no Azure AD com permissão de aplicação
#   (Sites.ReadWrite.All, com consentimento de administrador) e trocar esse
#   fluxo por "client credentials" (client_id + client_secret) - aí sim
#   funciona independente de MFA. Eu construí o código já isolado numa
#   função só (`_obter_token_sharepoint`) exatamente pra isso ser fácil de
#   trocar depois, se precisar.
#
#   Também não tenho como confirmar se a pasta "Relatorio_Shein" fica no
#   OneDrive pessoal da conta de suporte ou num site de
#   equipe do SharePoint - pela captura de tela que você mandou (o
#   círculo com o nome "Suporte" no canto), parece OneDrive pessoal,
#   e foi assim que implementei por padrão (usa o endpoint /me/drive, que
#   automaticamente aponta pro drive de quem autenticou). Se na prática for
#   um site de equipe, cola a URL completa (a que aparece na barra do
#   navegador com a pasta aberta) no campo SHAREPOINT_SITE_URL do
#   .env.sharepoint que o comportamento muda sozinho.
#
#   Por fim: não tenho acesso à internet daqui pra testar nada disso de
#   verdade contra o Microsoft Graph. Toda a lógica (autenticação, criação
#   de pastas, upload) foi testada com respostas HTTP simuladas.
# ---------------------------------------------------------------------------

CLIENT_ID_GRAPH_ROPC = "1950a258-227b-4e31-a9cf-717495945fc2"  # cliente público oficial da Microsoft (Azure PowerShell) - permite ROPC sem precisar de client secret

MESES_INGLES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

HORARIO_RELATORIO_SHEIN_AUTOMATICO = "08:00"

estado_relatorio_shein_automatico: dict = {
    "ultima_execucao": None,
    "ultimo_sucesso": None,
    "ultimo_erro": None,
}
_lock_relatorio_shein_auto = threading.Lock()


def _config_sharepoint() -> dict:
    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seção [infra_sharepoint]),
    # cai pro .env.sharepoint tradicional se essa seção não existir -
    # ver core/config_central.py.
    valores = _obter_config_hibrido(
        "infra_sharepoint", ".env.sharepoint",
        ["SHAREPOINT_LOGIN", "SHAREPOINT_PASSWORD", "SHAREPOINT_TENANT",
         "SHAREPOINT_SITE_URL", "SHAREPOINT_DRIVE_OWNER_EMAIL"],
    )
    # SHAREPOINT_PASSWORD é o primeiro campo migrado pro config.dat cifrado
    # (ver seção "Criptografia de configurações sensíveis" acima) - se
    # tiver lá, usa ele; senão, cai no valor que veio do híbrido acima
    # (compatibilidade com quem ainda não migrou).
    return {
        "login": valores["SHAREPOINT_LOGIN"],
        "senha": _obter_valor_config("SHAREPOINT_PASSWORD", valores["SHAREPOINT_PASSWORD"]),
        "tenant": valores["SHAREPOINT_TENANT"],
        "site_url": valores["SHAREPOINT_SITE_URL"].strip(),
        "drive_owner_email": valores["SHAREPOINT_DRIVE_OWNER_EMAIL"].strip(),
    }


def _obter_token_sharepoint(cfg: dict):
    """Autentica via ROPC (usuário+senha) contra o Microsoft Graph. Ver
    aviso no topo da seção sobre a limitação de MFA. Retorna (token, erro)."""
    if not cfg["login"] or not cfg["senha"] or not cfg["tenant"]:
        return None, "Credenciais do SharePoint não configuradas (.env.sharepoint)."
    try:
        resposta = requests.post(
            f"https://login.microsoftonline.com/{cfg['tenant']}/oauth2/v2.0/token",
            data={
                "grant_type": "password",
                "client_id": CLIENT_ID_GRAPH_ROPC,
                "username": cfg["login"],
                "password": cfg["senha"],
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=20,
        )
        try:
            corpo = resposta.json()
        except Exception:
            corpo = {}
        if resposta.status_code != 200:
            erro_desc = corpo.get("error_description", resposta.text)[:300]
            return None, f"Falha ao autenticar no Microsoft 365/SharePoint: {erro_desc}"
        return corpo.get("access_token"), None
    except Exception as e:
        return None, f"Erro inesperado ao autenticar no SharePoint: {e}"


def _extrair_site_do_link_sharepoint(url: str):
    """Tenta extrair (hostname, tipo, identificador) de uma URL do
    SharePoint/OneDrive, aceitando os formatos mais comuns que aparecem
    quando alguém copia o link direto da barra de endereço OU usa o botão
    "copiar link" da interface (que gera uma URL tipo
    /shared?id=%2Fpersonal%2F...%2FRelatorio_Shein%2F... com o caminho
    real codificado dentro do parâmetro "id", em vez de aparecer direto
    no caminho da URL).
    Retorna (hostname, "sites", nome_do_site) pra site de equipe,
    (hostname, "personal", conta_codificada) pra OneDrive pessoal, ou
    None se não conseguir reconhecer nenhum dos dois padrões."""
    partes = urllib.parse.urlsplit(url)
    hostname = partes.netloc
    if not hostname:
        return None

    # o caminho real pode estar direto na URL, ou codificado dentro do
    # parâmetro "id" (formato de link "compartilhar" do OneDrive/SharePoint)
    caminho = urllib.parse.unquote(partes.path)
    qs = urllib.parse.parse_qs(partes.query)
    if "id" in qs:
        caminho = urllib.parse.unquote(qs["id"][0])

    m_site = re.search(r"/sites/([^/]+)", caminho)
    if m_site:
        return hostname, "sites", m_site.group(1)

    m_pessoal = re.search(r"/personal/([^/]+)", caminho)
    if m_pessoal:
        return hostname, "personal", m_pessoal.group(1)

    return None


def _candidatos_graph_drive(cfg: dict) -> list:
    """Monta a lista de possíveis endereços do Graph pro drive certo, em
    ordem de prioridade - PLURAL de propósito, porque existe mais de um
    jeito de endereçar o mesmo OneDrive via Graph (por site ou por
    usuário), e na prática nem sempre o mesmo jeito funciona pra todo tipo
    de conta (ex.: contas de caixa compartilhada). Em vez de depender de
    adivinhar certo da primeira vez, a gente tenta cada candidato até um
    funcionar de verdade.
      1) SHAREPOINT_SITE_URL, endereçado por SITE (.../sites/{host}:/
         personal-ou-sites/{id}:/drive) - o jeito "oficial" de endereçar
         um site específico.
      2) Se a URL for de um OneDrive pessoal (".../personal/..."), TAMBÉM
         tenta o e-mail equivalente derivado da própria URL (ex.:
         "suporte_example_com" -> "suporte@example.com"), via
         endereçamento por USUÁRIO (/users/{email}/drive) - é uma rota
         totalmente diferente dentro do Graph, que pode funcionar mesmo
         quando a rota por site não funciona (ou vice-versa).
      3) SHAREPOINT_DRIVE_OWNER_EMAIL, se preenchido - mesmo endereçamento
         por usuário, mas com o e-mail informado direto (não derivado).
      4) OneDrive de quem autenticou (/me/drive) - último recurso."""
    candidatos = []
    if cfg["site_url"]:
        resolvido = _extrair_site_do_link_sharepoint(cfg["site_url"])
        if resolvido:
            hostname, tipo, identificador = resolvido
            candidatos.append(f"https://graph.microsoft.com/v1.0/sites/{hostname}:/{tipo}/{identificador}:/drive")
            if tipo == "personal":
                partes = identificador.split("_")
                if len(partes) >= 2:
                    email_derivado = partes[0] + "@" + ".".join(partes[1:])
                    candidatos.append(f"https://graph.microsoft.com/v1.0/users/{email_derivado}/drive")
    if cfg["drive_owner_email"]:
        candidatos.append(f"https://graph.microsoft.com/v1.0/users/{cfg['drive_owner_email']}/drive")
    candidatos.append("https://graph.microsoft.com/v1.0/me/drive")

    vistos, unicos = set(), []
    for c in candidatos:
        if c not in vistos:
            vistos.add(c)
            unicos.append(c)
    return unicos


def _base_graph_drive(cfg: dict) -> str:
    """Mantido só por compatibilidade (retorna o candidato de maior
    prioridade) - o fluxo de envio de verdade usa _resolver_base_graph_
    drive, que tenta vários candidatos até um funcionar."""
    return _candidatos_graph_drive(cfg)[0]


def _resolver_base_graph_drive(token: str, cfg: dict):
    """Tenta cada candidato de _candidatos_graph_drive até um responder
    200. Retorna (base_que_funcionou, None) em caso de sucesso, ou
    (None, mensagem_de_erro_juntando_todas_as_tentativas) se nenhum
    funcionar."""
    candidatos = _candidatos_graph_drive(cfg)
    tentativas_falhas = []
    for base in candidatos:
        try:
            resp = requests.get(base, headers={"Authorization": f"Bearer {token}"}, timeout=20)
        except requests.exceptions.RequestException as e:
            tentativas_falhas.append(f"{base}: erro de rede ({e})")
            continue
        if resp.status_code == 200:
            return base, None
        tentativas_falhas.append(f"{base}: {resp.status_code} {resp.text[:150]}")

    detalhes = "\n".join(f"  - {t}" for t in tentativas_falhas)

    # diagnóstico extra: se a URL configurada em SHAREPOINT_SITE_URL foi
    # reconhecida como um link de OneDrive PESSOAL (contém "/personal/"),
    # e não de um site de equipe, avisa isso explicitamente - é o motivo
    # mais comum desse erro (a conta configurada não ter OneDrive próprio,
    # tipicamente por ser uma caixa compartilhada), e economiza ter que
    # investigar o código toda vez que acontecer de novo.
    dica_tipo_url = ""
    if cfg["site_url"]:
        resolvido = _extrair_site_do_link_sharepoint(cfg["site_url"])
        if resolvido and resolvido[1] == "personal":
            dica_tipo_url = (
                "\n\nATENÇÃO: a URL configurada em SHAREPOINT_SITE_URL foi reconhecida como "
                "um link de OneDrive PESSOAL (contém '/personal/' na URL), não de um site de "
                "equipe do SharePoint. Se a pasta 'Relatorio_Shein' na verdade fica dentro de "
                "um site de equipe (ex: um site chamado 'Suporte'), copie a URL de dentro "
                "dessa pasta (que deve conter '/sites/' em vez de '/personal/', e o domínio "
                "SEM o '-my') e cole em SHAREPOINT_SITE_URL no .env.sharepoint."
            )

    return None, (
        f"Não consegui acessar nenhum dos {len(candidatos)} endereço(s) tentado(s) pro drive do "
        f"SharePoint/OneDrive:\n{detalhes}\n"
        "Isso costuma acontecer quando a conta de login é uma caixa de e-mail compartilhada "
        "(sem OneDrive próprio) e a URL/e-mail configurado em SHAREPOINT_SITE_URL ou "
        "SHAREPOINT_DRIVE_OWNER_EMAIL (.env.sharepoint) também não bateu. Confira se a URL "
        "está exatamente certa (copiada da barra de endereço, com a pasta Relatorio_Shein "
        "aberta), ou se a conta de login tem permissão de acessar esse local."
        + dica_tipo_url
    )


def _garantir_pasta_sharepoint(token: str, base: str, caminho_pastas: list):
    """Garante que a cadeia de pastas exista no SharePoint/OneDrive,
    criando as que faltarem. `base` é o endereço do Graph JÁ RESOLVIDO
    (ver _resolver_base_graph_drive) - não recalcula/adivinha de novo
    aqui, usa exatamente o que já foi confirmado que funciona. Retorna
    None se deu certo, ou a mensagem de erro."""
    cabecalhos = {"Authorization": f"Bearer {token}"}
    caminho_acumulado = ""
    for pasta in caminho_pastas:
        caminho_pai = caminho_acumulado
        caminho_acumulado = f"{caminho_acumulado}/{pasta}" if caminho_acumulado else pasta

        resp = requests.get(f"{base}/root:/{caminho_acumulado}", headers=cabecalhos, timeout=20)
        if resp.status_code == 200:
            continue  # já existe
        if resp.status_code != 404:
            return f"Erro ao verificar pasta '{caminho_acumulado}': {resp.status_code} {resp.text[:200]}"

        url_criar = f"{base}/root:/{caminho_pai}:/children" if caminho_pai else f"{base}/root/children"
        resp_criar = requests.post(
            url_criar,
            headers={**cabecalhos, "Content-Type": "application/json"},
            json={"name": pasta, "folder": {}, "@microsoft.graph.conflictBehavior": "replace"},
            timeout=20,
        )
        if resp_criar.status_code not in (200, 201):
            return f"Erro ao criar pasta '{caminho_acumulado}': {resp_criar.status_code} {resp_criar.text[:200]}"
    return None


def _enviar_arquivo_sharepoint(token: str, base: str, caminho_local: str, caminho_remoto: str):
    """Envia um arquivo local pro caminho remoto (upload simples - ok pra
    arquivos até uns 4MB, o esperado pra esses relatórios diários). `base`
    é o endereço do Graph já resolvido (mesma ideia de _garantir_pasta_
    sharepoint). Retorna None se deu certo, ou a mensagem de erro."""
    with open(caminho_local, "rb") as f:
        conteudo = f.read()
    resp = requests.put(
        f"{base}/root:/{caminho_remoto}:/content",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        data=conteudo,
        timeout=60,
    )
    if resp.status_code not in (200, 201):
        return f"Erro ao enviar '{caminho_remoto}': {resp.status_code} {resp.text[:300]}"
    return None


def _enviar_relatorio_shein_sharepoint(data: datetime, nome_notas: str, nome_canceladas: str) -> dict:
    """Sobe os dois arquivos do relatório do dia pro SharePoint, seguindo a
    estrutura Relatorio_Shein/<MêsEmInglês>/<DD-MM-YYYY>/ (mês sempre em
    inglês, igual você mostrou na captura de tela - não depende do idioma
    configurado na máquina que roda isso)."""
    logger_shein.info("Iniciando envio ao SharePoint pra %s.", data.strftime("%d-%m-%Y"))
    cfg = _config_sharepoint()

    token, erro = _obter_token_sharepoint(cfg)
    if erro:
        logger_shein.error("Falha ao autenticar no Microsoft Graph: %s", erro)
        return {"ok": False, "erro": erro}
    logger_shein.info("Autenticação no Microsoft Graph OK.")

    base, erro_drive = _resolver_base_graph_drive(token, cfg)
    if erro_drive:
        logger_shein.error("Não foi possível resolver o drive do SharePoint: %s", erro_drive)
        return {"ok": False, "erro": erro_drive}
    logger_shein.info("Drive resolvido: %s", base)

    pastas = ["Relatorio_Shein", MESES_INGLES[data.month], data.strftime("%d-%m-%Y")]
    erro_pasta = _garantir_pasta_sharepoint(token, base, pastas)
    if erro_pasta:
        logger_shein.error("Falha ao criar/conferir a pasta '%s': %s", "/".join(pastas), erro_pasta)
        return {"ok": False, "erro": erro_pasta}
    logger_shein.info("Pasta '%s' confirmada no SharePoint.", "/".join(pastas))

    caminho_pastas_str = "/".join(pastas)
    pasta_local = _pasta_saida_relatorios_shein(data)
    for nome_arquivo in (nome_notas, nome_canceladas):
        erro_envio = _enviar_arquivo_sharepoint(
            token, base, os.path.join(pasta_local, nome_arquivo), f"{caminho_pastas_str}/{nome_arquivo}"
        )
        if erro_envio:
            logger_shein.error("Falha ao enviar '%s': %s", nome_arquivo, erro_envio)
            return {"ok": False, "erro": erro_envio}
        logger_shein.info("Arquivo '%s' enviado com sucesso.", nome_arquivo)

    logger_shein.info("Envio ao SharePoint concluído com sucesso pra %s.", data.strftime("%d-%m-%Y"))
    return {"ok": True}


def _executar_relatorio_shein_diario() -> None:
    """Roda 1x por dia (agendado via `schedule`, junto com os outros
    alertas): gera o relatório de ONTEM e envia pro SharePoint."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ontem = datetime.now() - timedelta(days=1)
    logger_shein.info("=" * 60)
    logger_shein.info("Execução automática diária iniciada (relatório de %s).", ontem.strftime("%d-%m-%Y"))
    try:
        resultado = _gerar_relatorio_shein(ontem.strftime("%Y-%m-%d"))
        if not resultado.get("ok"):
            raise RuntimeError(resultado.get("erro", "erro desconhecido ao gerar o relatório"))

        resultado_envio = _enviar_relatorio_shein_sharepoint(
            ontem, resultado["arquivo_notas"], resultado["arquivo_canceladas"]
        )
        if not resultado_envio.get("ok"):
            raise RuntimeError(resultado_envio.get("erro", "erro desconhecido ao enviar pro SharePoint"))

        with _lock_relatorio_shein_auto:
            estado_relatorio_shein_automatico["ultima_execucao"] = agora
            estado_relatorio_shein_automatico["ultimo_sucesso"] = agora
            estado_relatorio_shein_automatico["ultimo_erro"] = None
        logger_shein.info("Relatório Shein automático de %s enviado ao SharePoint.", ontem.strftime("%d-%m-%Y"))
        logger_shein.info("Execução automática diária concluída com SUCESSO.")
    except Exception as e:
        with _lock_relatorio_shein_auto:
            estado_relatorio_shein_automatico["ultima_execucao"] = agora
            estado_relatorio_shein_automatico["ultimo_erro"] = str(e)
        logger.exception("Erro ao rodar o relatório Shein automático diário")
        logger_shein.exception("Execução automática diária FALHOU.")



# Logo genérico (placeholder - troque pelo logo da sua organização), embutido como base64 pra nao
# depender de nenhum arquivo externo - funciona igual dentro do .exe compilado.
_LOGO_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAJAAAACQCAYAAADnRuK4AAAIG0lEQVR42u3d53pVVRDG8fdGsHdFEVBpioIgUgUpIihIEaQkSAi9CxEElKogioUiRcFuejkJSc6xXdI4a9bZjzHmkLMniVLeD/87+H3Zz14zg/6Vf6J/5R/a73jU+g2PVf5qDajMWY9XZrV2DLTatFYMsq5icFWoBU9UNVtPVmW0JjxlNVpDqhq0egy16jCsqtYaXl0TkhHV1VqV9XR1pfVM9S/azzLS+kmerf7Req76h1jN9zKq5jtrdM232hV53rosY6xvZGzN1/kuyQs1F61xNRdkXO0FebH2vPaVjLfOyYTas/nOyETrtEyq/dKaXPuFNaX2c5lS95m8ZJ3SPpWp1icyzTopL9d9bE2vO6EdlxnWR9bM+g+1YzLLOiqv1B+xZtcftl6tP6QdtObUf6C9L3OtA/JaqGG/vN6wz5rX8F6+vZjfsMd6o+FdrQILrN1YaO3CooZ3sKgxtBOLG3dYbzZut5Y0btO2Yqm1BW81bs63CcusjVjetMFa0bReW4eV1lqUaP8FHlE8MtSqE4VjBTjE02M8onAsxaNVyAJrtyy0dklf4ilpKkdf4ZEQ8fzveETxaDtF4Uhv4ylpWoPexiPEc93iEYVj9Rae0gioV/AI8dwweLStstTqGZ7SpjL0FI8Qzw2LRxROPh+eVQkg4rml8cgyKz2eVU2r4cEjxHPT4RGFY6XB83bT2yAe4umIR1snxeIxQMRDPJ3waGulGDyrM6tAPMTTFR6tXLrDszpTCuIhnkJ4pNQqjKcsAiIe4imIR1ZZXeMpy5SAn+rE0x0eKYTHABEP8XSDx+oKz5rMShAP8RSDRyuVznjWZFaA/7aIp1g80hlPeQREPMRTFB6rI57yzHLwSQbxpMEjHfGszSwD8RBPGjxSbkU8BogvCYknJR5J8KzLvAXiIZ60eKyAxwB1eABPPMRTLB4DtD6zFJyeIB4PHgl41meWgHiIx4NHWyLrmxVQfuiPeIgnLR7Z0PwmkolR4iGetHi0xUjGjYmHeNLikY0RkM2qEw/xpMWjLUKy6IB4iCctHtmUACIe4nHg0RaCK1aIx4tHNjcvAPEQjxdPBEQ8xOPEI1ua3wiAiId4XHi0+REQ8RCPA08ERDzE48QjW5vnRUDEQzwOPBEQ8RCPE49sa349ACIe4nHhkW0trwHEQzxOPLI9AiIe4nHh0eYCxEM8TjyyIwFEPMTjwKPNAYiHeJx4ZGfLq3lAxEM86fHkAREP8fjwaLMB4iEeJx55p+WVCIh4iMeBJwIiHuJx4pFdLbMCIOIhHheeCIh4iMeJR3a3zAyAiId4XHi0GQDxEI8Tj1REQMRDPC482nSAeIjHiUfevfpyAoh4iCc1ngQQ8RCPC482DSAe4nHikT0JIOIhHgcebSpAPMTjxCN7r76kgIiHeHx4IiDiIR4nHnnv6pQAiHiIx4VHmwwQD/E48ci+CIh4iMeFR5sEEA/xOPHI/r8BEQ/xpMajTQyAiId4XHi0CQDxEI8TjxyIgIiHeFx45EDreIB4iMeJR95vfTECIh7iceCJgIiHeJx45IPWcREQ8RCPA08ERDzE48QjB1tfUEDEQzw+PNpYgHiIx4lHDkVAxEM8LjzamACIeIjHhScCIh7iceKRw63PB0DEQzwuPNpogHiIx4lHjkRAxEM8LjzaKIB4iMeJR462PhcBEQ/xOPDI0TYFRDzE48Qjx9qeDYCIh3hceCIg4iEeJx75sG1kAEQ8xOPCoz0TAREP8TjwREDEQzxOPPJR29MBEPEQjwuPNgIgHuJx4pHjERDxEI8LjzYcIB7iceKREwkg4iEeBx5tGEA8xOPEIx+3DY2AiId4HHgiIOIhHiceOdk2JAAiHuJx4ZGT7U9FQMRDPA48ERDxEI8Tj3zS/mQARDzE48ITAREP8TjxyKftTwRAxEM8LjzaYIB4iMeJR04ZIOIhHh8ebRBAPMTjxCOftQ+MgIiHeBx4IiDiIR4nHvm8/fEEEPEQT2o8CaC9IB7iceDRBiDgAfEQjwOPfNH+WAREPMTjwBMBKR4QD/E48MiX2UcDoAoQD/E48ERACwwQ8RBPajxyOts/ANoN4iEeBx7tEQQ8IB7iceCRMxHQLigeEA/xpMVzJvswEjwgHuJJgUcCnrPZh5DgAfEQTwo8EvDkARkei3iIJw2es9kH0REPiId4isAjCZ5zCaA8HigeEA/xFIvnXPYBdMYD4iGea+CRjni+yt6Pzni0LSAe4ikGjwHqAg+Ih3i6wCOd8ZzP3oeu8GibQDzE0x2e89l7UQiPthHEQzzXwnMhZ4AK4gHxEM85q2s8F3L34Fp4oHhAPMRTCM/FvwEVxIOVFvEQz7/xXMzdjWLwoMQiHuL5J56LubtQLB5tDYiHeDriuRQBFY1HKwPxEE+C51LuTqTFo62GwgHx3Dqf6oXwfJ27A148UDwgnlsbjwHqAR6UWSUgnpvn31YaPN/kbkdv4IHi0VaAeG7MJxlePAaoF/Foy6FwQDzX/0vC3sBzOXcb+gIPFI6leEA818f0RF/guZzrh77GA8UDxaMtxkZrETZZC6FwLMWjzbcUjqV4oHiw3ZqLHdYcKJx8s6FwLIVjKR5tBiqs6VA4+aZhjzUVCsdSPNpk7LMmYb81UZuAA6HW8VA4lsKxFI82FoesMZbi0UbjiDUKigeKB+Gmeiicxg7HaUPhxmg4E3ncGo4T1jCEoyWhcHsibH8PhR3MobBKN2xDPWUNQtgKFgq7eWIDEJYchMKocShMjJ42OH2L50quH/4CYV8j/Kn9r0AAAAAASUVORK5CYII="
_LOGO_DATA_URI = f"data:image/png;base64,{_LOGO_BASE64}"


# ---------------------------------------------------------------------------
# Servidor Web (visualização/controle via navegador, na mesma rede)
# ---------------------------------------------------------------------------
STATUS_COLORS_WEB = {
    "Aguardando": "#808080",
    "Executando": "#dcdcaa",
    "OK": "#4ec9b0",
    "Erro": "#f14c4c",
}

LOG_LEVEL_COLORS_WEB = {
    "INFO": "#d4d4d4",
    "WARNING": "#dcdcaa",
    "ERROR": "#f14c4c",
    "CRITICAL": "#f14c4c",
}

_HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .resumo { display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
  .cartao { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            padding: 12px 18px; min-width: 110px; }
  .cartao .num { font-size: 22px; font-weight: 700; }
  .cartao .rot { font-size: 11px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .04em; }
  .cabecalho-secao { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .cabecalho-secao h3 { margin: 0; }
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: #2a2a2b; }
  .status { font-weight: 600; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  h3 { color: var(--accent); margin: 22px 0 8px 0; font-size: 14px; }
</style>
</head>
<body>
__NAVBAR__

  <div class="conteudo">
    <div class="cabecalho-secao">
      <h3 style="margin-top:0" id="atualizado">carregando...</h3>
      <button class="btn-accent" onclick="executarTodos()">Executar todos agora</button>
    </div>

    <div class="resumo" id="resumo"></div>

    <div class="painel">
      <table>
        <thead>
          <tr>
            <th>Alerta</th><th>Status</th><th>Última execução</th>
            <th>Próxima execução</th><th>Último erro</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela"></tbody>
      </table>
    </div>
  </div>

<script>
const CORES_STATUS = {Aguardando: 'var(--wait)', Executando: 'var(--run)', OK: 'var(--ok)', Erro: 'var(--erro)'};
let linhasTabelaCriadas = false;
let ultimoResumoAssinatura = '';

function idLinha(nome) {
  return 'linha-' + nome.replace(/[^a-zA-Z0-9]/g, '_');
}

function montarLinhasTabela(jobs) {
  const corpo = document.getElementById('corpo-tabela');
  corpo.innerHTML = '';
  for (const job of jobs) {
    const tr = document.createElement('tr');
    tr.id = idLinha(job.nome);
    tr.innerHTML = `
      <td>${job.nome}</td>
      <td class="status" data-campo="status"></td>
      <td data-campo="ultima"></td>
      <td data-campo="proxima"></td>
      <td data-campo="erro"></td>
      <td><button class="btn-mini" onclick="executarUm('${job.nome.replace(/'/g, "\\\\'")}')">Executar</button></td>
    `;
    corpo.appendChild(tr);
  }
  linhasTabelaCriadas = true;
}

// Só escreve no DOM os campos que de fato mudaram desde o último poll -
// evita recriar a tabela inteira a cada 2s (menos flicker, menos trabalho
// de layout/reflow do navegador, preserva seleção de texto etc.)
function atualizarLinha(job) {
  const tr = document.getElementById(idLinha(job.nome));
  if (!tr) return;
  const campoStatus = tr.querySelector('[data-campo="status"]');
  if (campoStatus.dataset.valor !== job.status) {
    campoStatus.innerText = job.status;
    campoStatus.style.color = job.cor;
    campoStatus.dataset.valor = job.status;
  }
  const campos = {ultima: job.ultima || '-', proxima: job.proxima || '-', erro: job.erro || ''};
  for (const nomeCampo in campos) {
    const el = tr.querySelector(`[data-campo="${nomeCampo}"]`);
    if (el.dataset.valor !== campos[nomeCampo]) {
      el.innerText = campos[nomeCampo];
      el.dataset.valor = campos[nomeCampo];
    }
  }
}

async function carregarStatus() {
  try {
    const resp = await fetch('/api/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();

    document.getElementById('atualizado').innerText =
      'Atualizado às ' + new Date().toLocaleTimeString('pt-BR');

    const contagem = {Aguardando: 0, Executando: 0, OK: 0, Erro: 0};
    for (const job of dados.jobs) { contagem[job.status] = (contagem[job.status] || 0) + 1; }
    const assinaturaResumo = JSON.stringify(contagem);
    if (assinaturaResumo !== ultimoResumoAssinatura) {
      const resumo = document.getElementById('resumo');
      resumo.innerHTML = Object.entries(contagem).map(([status, n]) => `
        <div class="cartao">
          <div class="num" style="color:${CORES_STATUS[status]}">${n}</div>
          <div class="rot">${status}</div>
        </div>
      `).join('');
      ultimoResumoAssinatura = assinaturaResumo;
    }

    if (!linhasTabelaCriadas) montarLinhasTabela(dados.jobs);
    for (const job of dados.jobs) atualizarLinha(job);
  } catch (e) {
    document.getElementById('atualizado').innerText = 'Erro ao atualizar: ' + e;
  }
}

async function executarTodos() {
  await fetch('/api/run_all', { method: 'POST' });
  carregarStatus();
}

async function executarUm(nome) {
  await fetch('/api/run/' + encodeURIComponent(nome), { method: 'POST' });
  carregarStatus();
}

carregarStatus();
setInterval(carregarStatus, 2000);
</script>
__FOOTER__
</body>
</html>
"""


def _montar_alertas_html(sessao: dict) -> str:
    return (
        _HTML_PAGE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Status dos alertas"))
        .replace("__FOOTER__", _montar_footer())
    )


_LOGIN_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações - Entrar</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body {
    display: flex; flex-direction: column; min-height: 100vh; position: relative; overflow-x: hidden;
    --mx: 20%; --my: 30%;
  }
  body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; transition: background .3s ease;
    background:
      radial-gradient(ellipse 800px 560px at var(--mx) var(--my), rgba(45,184,207,.14), transparent 60%),
      radial-gradient(ellipse 900px 700px at 88% 84%, rgba(176,203,28,.08), transparent 60%);
  }
  body::after {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .5;
    background-image:
      linear-gradient(rgba(255,255,255,.012) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255,255,255,.012) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: radial-gradient(ellipse 1200px 900px at 50% 45%, black, transparent 75%);
  }

  @keyframes entrada { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes girar { to { transform: rotate(360deg); } }
  @keyframes pulsarPonto { 0%, 100% { box-shadow: 0 0 0 0 rgba(78,201,176,.55); } 70% { box-shadow: 0 0 0 6px rgba(78,201,176,0); } }
  @keyframes brilhoTagline { 0%, 100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }

  .centro { flex: 1; display: flex; align-items: stretch; justify-content: center; gap: 64px;
             padding: 56px 64px; flex-wrap: wrap; position: relative; z-index: 1; }

  .anim-entrada { opacity: 0; animation: entrada .65s cubic-bezier(.16,1,.3,1) forwards; }

  .coluna-login { display: flex; flex-direction: column; gap: 22px; width: 380px; flex-shrink: 0; }
  .fantasma-tagline { visibility: hidden; font-style: italic; font-size: 21px; font-weight: 600;
                       margin: 0; padding: 0 12px; line-height: normal; }

  .anim-entrada { opacity: 0; animation: entrada .65s cubic-bezier(.16,1,.3,1) forwards; }

  .cartao-login {
    background: var(--bg-panel); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 22px; padding: 44px 38px; width: 100%; flex: 1; min-height: 0; position: relative;
    box-shadow: 0 28px 70px rgba(0,0,0,.6), inset 0 1px 0 rgba(255,255,255,.05);
    border: 1px solid transparent;
    background-image: linear-gradient(var(--bg-panel), var(--bg-panel)),
                       linear-gradient(140deg, rgba(45,184,207,.5), rgba(255,255,255,.06) 40%, rgba(176,203,28,.35));
    background-origin: border-box; background-clip: padding-box, border-box;
    animation-delay: .05s;
    display: flex; flex-direction: column;
  }
  .corpo-login { flex: 1; display: flex; flex-direction: column; justify-content: center; min-height: 0; }
  .rodape-login { flex-shrink: 0; }
  .divisor-rodape-login { height: 1px; margin: 28px 0 18px 0;
                           background: linear-gradient(90deg, transparent, var(--border-forte), transparent); }
  .cartao-login::before {
    content: ""; position: absolute; top: 0; left: 10%; right: 10%; height: 2px; border-radius: 2px;
    background: var(--gradiente-marca); filter: blur(.5px);
    box-shadow: 0 0 16px 1px rgba(45,184,207,.5);
  }
  .cartao-login .logo-login { display: flex; justify-content: center; margin-bottom: 22px; position: relative; }
  .cartao-login .logo-login::before {
    content: ""; position: absolute; width: 90px; height: 90px; border-radius: 50%;
    background: radial-gradient(circle, rgba(45,184,207,.35), transparent 70%); filter: blur(6px);
  }
  .cartao-login .logo-login img { height: 60px; width: 60px; position: relative;
                                    filter: drop-shadow(0 8px 22px rgba(45,184,207,.4)); }
  .cartao-login h1 {
    background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent;
    font-size: 22px; margin: 0 0 6px 0; text-align: center; font-weight: 800; letter-spacing: -.01em;
  }
  .badge-status-login { display: flex; align-items: center; justify-content: center; gap: 6px;
                         color: var(--fg-dim); font-size: 11.5px; text-align: center; margin-bottom: 28px; }
  .ponto-online { width: 6px; height: 6px; border-radius: 50%; background: var(--ok);
                   animation: pulsarPonto 2s infinite; flex-shrink: 0; }

  label { display: block; font-size: 10.5px; color: var(--fg-dim); margin: 16px 0 6px 0;
          text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
  .campo-com-icone { position: relative; }
  .campo-com-icone svg.icone-campo { position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
                                       width: 15px; height: 15px; color: var(--fg-dim); pointer-events: none;
                                       transition: color .15s ease; z-index: 1; }
  .campo-com-icone:focus-within svg.icone-campo { color: var(--teal); }
  input {
    width: 100%; padding: 11px 13px 11px 36px; border-radius: 9px; border: 1px solid var(--border);
    background: rgba(0,0,0,.3); color: var(--fg); font-size: 14px; font-family: inherit;
    transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
    position: relative;
  }
  input:focus {
    outline: none; border-color: var(--teal); background: rgba(0,0,0,.4);
    box-shadow: 0 0 0 3px rgba(45,184,207,.16), 0 0 18px -4px rgba(45,184,207,.5);
  }
  .campo-senha { position: relative; }
  .campo-senha input { padding-left: 36px; padding-right: 40px; }
  .campo-senha .alternar-senha { position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
                                   background: none; border: none; padding: 4px; cursor: pointer;
                                   color: var(--fg-dim); display: flex; transition: color .15s ease; }
  .campo-senha .alternar-senha:hover { color: var(--teal); }
  .campo-senha .alternar-senha svg { width: 16px; height: 16px; }

  button.entrar {
    width: 100%; margin-top: 26px; padding: 12px; border-radius: 9px; font-size: 14.5px;
    font-family: inherit; font-weight: 700; letter-spacing: .01em; position: relative; overflow: hidden;
    box-shadow: 0 8px 24px rgba(45,184,207,.25); transition: transform .15s ease, box-shadow .15s ease;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  button.entrar:hover { transform: translateY(-1px); box-shadow: 0 12px 32px rgba(45,184,207,.4); }
  button.entrar:active { transform: translateY(0) scale(.98); }
  button.entrar .spinner-entrar {
    display: none; width: 15px; height: 15px; border-radius: 50%;
    border: 2px solid rgba(11,15,20,.35); border-top-color: #0b0f14; animation: girar .7s linear infinite;
  }
  button.entrar.carregando .texto-entrar { opacity: .001; }
  button.entrar.carregando .spinner-entrar { display: block; position: absolute; }

  .erro { color: var(--erro); font-size: 12px; text-align: center; margin-top: 14px; }
  .erro-desativado { background: rgba(241,76,76,.1); border: 1px solid rgba(241,76,76,.3);
                      border-radius: 10px; padding: 12px 14px; font-size: 12px; line-height: 1.6;
                      text-align: left; }
  .erro-desativado strong { color: var(--fg); }
  .msg-sucesso { color: var(--ok); font-size: 12px; text-align: center; margin-top: 14px; }

  .link-alterar-senha { display: inline-block; text-align: center; margin-top: 0; font-size: 11.5px;
                         color: var(--fg-dim); text-decoration: none; position: relative; width: 100%; }
  .link-alterar-senha::after {
    content: ""; position: absolute; left: 50%; bottom: -2px; width: 0; height: 1px;
    background: var(--teal); transition: width .25s ease, left .25s ease;
  }
  .link-alterar-senha:hover { color: var(--teal); }
  .link-alterar-senha:hover::after { width: 100px; left: calc(50% - 50px); }

  .coluna-showcase { flex: 1 1 600px; max-width: 1200px; display: flex; flex-direction: column; gap: 22px; }
  .tagline-showcase {
    font-style: italic; font-size: 21px; text-align: center; font-weight: 600; margin: 0; padding: 0 12px;
    letter-spacing: .01em; background: linear-gradient(100deg, var(--fg) 30%, var(--teal) 45%, var(--lime) 55%, var(--fg) 70%);
    background-size: 250% auto; -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .tagline-showcase.anim-entrada {
    /* combina a entrada em cascata com o brilho continuo numa unica
       declaracao de animation - se ficassem em regras separadas com a
       mesma especificidade, a que vem depois no CSS apaga a outra
       (as duas mexem na mesma propriedade "animation"), travando o
       elemento em opacity:0 pra sempre. */
    animation: entrada .65s cubic-bezier(.16,1,.3,1) .12s forwards,
               brilhoTagline 7s ease-in-out .8s infinite;
  }

  .painel-showcase {
    background: var(--bg-panel); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 22px; position: relative; overflow: hidden; padding: 48px 56px;
    box-shadow: 0 28px 70px rgba(0,0,0,.45), inset 0 1px 0 rgba(255,255,255,.04);
    border: 1px solid transparent;
    background-image: linear-gradient(var(--bg-panel), var(--bg-panel)),
                       linear-gradient(160deg, rgba(255,255,255,.09), rgba(255,255,255,.02) 30%, rgba(45,184,207,.18));
    background-origin: border-box; background-clip: padding-box, border-box;
    animation-delay: .16s;
    flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: center;
  }
  .painel-showcase::after {
    content: ""; position: absolute; top: -120px; right: -120px; width: 340px; height: 340px;
    border-radius: 50%; background: radial-gradient(circle, rgba(45,184,207,.13), transparent 70%);
    pointer-events: none;
  }
  .texto-showcase { position: relative; z-index: 1; }
  .texto-showcase p { color: var(--fg); font-size: 14.5px; line-height: 1.9; margin: 0 0 16px 0; }
  .texto-showcase p:last-of-type { margin-bottom: 0; }

  .grade-features-showcase { display: grid; grid-template-columns: repeat(5, 1fr);
                              gap: 14px; margin: 34px 0 28px 0; position: relative; z-index: 1; }
  .feature-showcase-card {
    background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 14px;
    padding: 18px 12px; text-align: center; cursor: default; position: relative;
    transition: transform .12s ease, border-color .25s ease, background .25s ease, box-shadow .25s ease;
    transform-style: preserve-3d; will-change: transform;
  }
  .feature-showcase-card:hover {
    border-color: var(--cor-tema, var(--teal)); background: rgba(255,255,255,.055);
    box-shadow: 0 12px 28px -8px var(--cor-tema-sombra, rgba(45,184,207,.4));
  }
  .feature-showcase-card .icone-feature { width: 38px; height: 38px; border-radius: 11px; margin: 0 auto 11px auto;
                                            display: flex; align-items: center; justify-content: center;
                                            transition: transform .25s ease; }
  .feature-showcase-card:hover .icone-feature { transform: scale(1.1); }
  .feature-showcase-card .icone-feature svg { width: 20px; height: 20px; }
  .feature-showcase-card h4 { margin: 0; font-size: 11.5px; color: var(--fg); font-weight: 700; line-height: 1.35; }

  .label-desenvolvido-por { text-align: center; font-size: 10.5px; color: var(--fg-dim);
                             text-transform: uppercase; letter-spacing: .08em; margin-bottom: 15px;
                             position: relative; z-index: 1; }
  .equipe-showcase { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; position: relative; z-index: 1; }
  .cartao-autor-showcase {
    display: flex; align-items: center; gap: 13px; background: rgba(255,255,255,.03);
    border-radius: 14px; padding: 15px 20px 15px 16px; flex: 1; min-width: 260px; position: relative;
    border: 1px solid var(--border-forte); overflow: hidden;
    transition: transform .12s ease, background .2s ease, box-shadow .2s ease;
    transform-style: preserve-3d; will-change: transform;
  }
  .cartao-autor-showcase::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--gradiente-marca);
  }
  .cartao-autor-showcase:hover { background: rgba(255,255,255,.06); box-shadow: 0 14px 30px -10px rgba(0,0,0,.5); }
  .avatar-autor-showcase { width: 44px; height: 44px; border-radius: 50%; object-fit: cover;
                            border: 2px solid var(--border-forte); flex-shrink: 0; }
  .cartao-autor-showcase .nome-autor-showcase { font-size: 13.5px; font-weight: 700; color: var(--fg); }
  .cartao-autor-showcase .cargo-autor-showcase { font-size: 10.5px; color: var(--fg-dim); line-height: 1.5; margin-top: 3px; }

  @media (max-width: 1000px) {
    .centro { justify-content: center; }
    .coluna-showcase { max-width: 620px; }
  }
  @media (max-width: 640px) {
    .painel-showcase { padding: 34px 26px; }
    .grade-features-showcase { grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); }
  }
  @media (prefers-reduced-motion: reduce) {
    .anim-entrada { animation: none; opacity: 1; }
    .tagline-showcase { animation: none; }
    .ponto-online { animation: none; }
  }
</style>
</head>
<body>
  <div class="centro">
    <div class="coluna-login">
      <div class="fantasma-tagline" aria-hidden="true">Um painel. Diversas operações.</div>
      <form class="cartao-login anim-entrada" method="POST" action="/login" id="form-login" style="animation-delay:.05s">
      <div class="corpo-login">
        <div class="logo-login"><img src="__LOGO__" alt="Logo"></div>
        <h1>Painel de Automações</h1>
        <div class="badge-status-login"><span class="ponto-online"></span>PDA · acesso restrito</div>
        <label>Usuário</label>
        <div class="campo-com-icone">
          <svg class="icone-campo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
          <input type="text" name="usuario" autofocus required autocomplete="username">
        </div>
        <label>Senha</label>
        <div class="campo-com-icone">
          <svg class="icone-campo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          __CAMPO_SENHA__
        </div>
        <button class="btn-accent entrar" type="submit">
          <span class="texto-entrar">Entrar</span>
          <span class="spinner-entrar"></span>
        </button>
        __ERRO__
        __SUCESSO__
      </div>
      <div class="rodape-login">
        <div class="divisor-rodape-login"></div>
        <a class="link-alterar-senha" href="/alterar-senha">Alterar minha senha</a>
      </div>
      </form>
    </div>

    <div class="coluna-showcase">
      <div class="tagline-showcase anim-entrada" style="animation-delay:.12s">Um painel. Diversas operações.</div>

      <div class="painel-showcase anim-entrada" style="animation-delay:.16s">
      <div class="texto-showcase">
        <p>
          O PDA — Painel de Automações foi criado para centralizar processos,
          automações, indicadores e ferramentas operacionais que antes estavam
          distribuídos entre diferentes aplicações, scripts e bancos de dados.
          Com isso, atividades do dia a dia se tornaram mais rápidas,
          organizadas e fáceis de acompanhar.
        </p>
        <p>
          Além de simplificar manutenções e reduzir processos manuais, o PDA
          permite monitorar execuções, identificar problemas e realizar ações
          diretamente pelo painel. A centralização também trouxe ganhos
          técnicos, reduzindo o uso de recursos por automações que antes
          funcionavam de forma isolada.
        </p>
        <p>
          Com dados sensíveis criptografados e controle de acesso por usuário,
          o PDA une praticidade e segurança em uma única plataforma. Em
          constante evolução, novas funcionalidades continuam sendo
          desenvolvidas para apoiar cada vez mais a operação, do Assistente à
          Gerência.
        </p>
      </div>

      <div class="grade-features-showcase">
        <div class="feature-showcase-card anim-entrada" style="--cor-tema:#2db8cf; --cor-tema-sombra:rgba(45,184,207,.4); animation-delay:.22s">
          <div class="icone-feature" style="background:rgba(45,184,207,.15)">
            <svg viewBox="0 0 24 24" fill="none" stroke="#2db8cf" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3a5 5 0 0 0-5 5v3.5c0 .7-.3 1.4-.8 1.9L5 15h14l-1.2-1.6c-.5-.5-.8-1.2-.8-1.9V8a5 5 0 0 0-5-5z"/>
              <path d="M9.5 18a2.5 2.5 0 0 0 5 0"/>
            </svg>
          </div>
          <h4>Monitoramento<br>Operacional</h4>
        </div>
        <div class="feature-showcase-card anim-entrada" style="--cor-tema:#f14c4c; --cor-tema-sombra:rgba(241,76,76,.4); animation-delay:.26s">
          <div class="icone-feature" style="background:rgba(241,76,76,.15)">
            <svg viewBox="0 0 24 24" fill="none" stroke="#f14c4c" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 3l7 3v6c0 4.5-3 8-7 9-4-1-7-4.5-7-9V6l7-3z"/>
              <path d="M12 8v5"/><path d="M12 16h.01"/>
            </svg>
          </div>
          <h4>Contingências<br>SEFAZ</h4>
        </div>
        <div class="feature-showcase-card anim-entrada" style="--cor-tema:#e8a33d; --cor-tema-sombra:rgba(232,163,61,.4); animation-delay:.30s">
          <div class="icone-feature" style="background:rgba(232,163,61,.15)">
            <svg viewBox="0 0 24 24" fill="none" stroke="#e8a33d" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 3v18h18"/>
              <path d="M7 15l4-5 3 3 5-7"/>
            </svg>
          </div>
          <h4>Indicadores<br>Movidesk</h4>
        </div>
        <div class="feature-showcase-card anim-entrada" style="--cor-tema:#b0cb1c; --cor-tema-sombra:rgba(176,203,28,.4); animation-delay:.34s">
          <div class="icone-feature" style="background:rgba(176,203,28,.15)">
            <svg viewBox="0 0 24 24" fill="none" stroke="#b0cb1c" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 13v-1a8 8 0 0 1 16 0v1"/>
              <rect x="2.5" y="13" width="4" height="6" rx="1.5"/>
              <rect x="17.5" y="13" width="4" height="6" rx="1.5"/>
              <path d="M19.5 19v1a3 3 0 0 1-3 3h-3"/>
            </svg>
          </div>
          <h4>Automações<br>Sustentação</h4>
        </div>
        <div class="feature-showcase-card anim-entrada" style="--cor-tema:#4ec9b0; --cor-tema-sombra:rgba(78,201,176,.4); animation-delay:.38s">
          <div class="icone-feature" style="background:rgba(78,201,176,.15)">
            <svg viewBox="0 0 24 24" fill="none" stroke="#4ec9b0" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="9"/>
              <path d="M12 7v5l3 3"/>
            </svg>
          </div>
          <h4>Horas<br>Trabalhadas</h4>
        </div>
      </div>

      <div class="label-desenvolvido-por">Desenvolvido por</div>
      <div class="equipe-showcase">
        <div class="cartao-autor-showcase anim-entrada" style="animation-delay:.42s">
          <div>
            <div class="nome-autor-showcase">Desenvolvimento</div>
            <div class="cargo-autor-showcase">Aplicação PDA · Frontend, Backend e QA</div>
          </div>
        </div>
        <div class="cartao-autor-showcase anim-entrada" style="animation-delay:.46s">
          <div>
            <div class="nome-autor-showcase">Supervisão</div>
            <div class="cargo-autor-showcase">Supervisão do projeto · Banco de Monitoramento &amp; Movidesk · UI/UX do PDA</div>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>

  __FOOTER__
<script>__JS_ALTERNAR_SENHA__</script>
<script>
(function () {
  // glow de fundo que segue o mouse suavemente (throttle via rAF)
  let ultimoX = 20, ultimoY = 30, pendente = false;
  document.addEventListener('mousemove', function (e) {
    ultimoX = (e.clientX / window.innerWidth) * 100;
    ultimoY = (e.clientY / window.innerHeight) * 100;
    if (!pendente) {
      pendente = true;
      requestAnimationFrame(function () {
        document.body.style.setProperty('--mx', ultimoX + '%');
        document.body.style.setProperty('--my', ultimoY + '%');
        pendente = false;
      });
    }
  });

  // tilt 3D leve nos cards de feature e nos cards de autor
  function aplicarTilt(seletor, intensidade) {
    document.querySelectorAll(seletor).forEach(function (card) {
      card.addEventListener('mousemove', function (e) {
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = 'perspective(600px) rotateY(' + (px * intensidade) + 'deg) rotateX(' + (-py * intensidade) + 'deg) translateY(-2px)';
      });
      card.addEventListener('mouseleave', function () {
        card.style.transform = '';
      });
    });
  }
  aplicarTilt('.feature-showcase-card', 10);
  aplicarTilt('.cartao-autor-showcase', 4);

  // spinner no botao ao enviar o formulario (o proprio submit continua normal)
  const form = document.getElementById('form-login');
  if (form) {
    form.addEventListener('submit', function () {
      const btn = form.querySelector('button.entrar');
      if (btn) btn.classList.add('carregando');
    });
  }
})();
</script>
</body>
</html>
"""


def _montar_login_html(com_erro: bool, com_sucesso: bool = False, desativado: bool = False) -> str:
    if desativado:
        bloco_erro = (
            '<div class="erro erro-desativado">'
            'Este usuário está desativado. Entre em contato com a '
            '<strong>administração do PDA</strong> pra reativar o acesso.'
            '</div>'
        )
    elif com_erro:
        bloco_erro = '<div class="erro">Usuário ou senha inválidos.</div>'
    else:
        bloco_erro = ""
    bloco_sucesso = '<div class="msg-sucesso">Senha alterada com sucesso. Entre com a nova senha.</div>' if com_sucesso else ""
    return (
_LOGIN_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__CAMPO_SENHA__", _campo_senha_html("senha", "current-password"))
        .replace("__ERRO__", bloco_erro)
        .replace("__SUCESSO__", bloco_sucesso)
        .replace("__JS_ALTERNAR_SENHA__", _JS_ALTERNAR_SENHA)
        .replace("__FOOTER__", _FOOTER_HTML)
    )


_ALTERAR_SENHA_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações - Alterar senha</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body { display: flex; flex-direction: column; min-height: 100vh; }
  .centro { flex: 1; display: flex; align-items: center; justify-content: center; padding: 24px; }
  .cartao-login {
    background: var(--bg-panel); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid var(--border-forte); border-radius: 20px;
    padding: 42px 36px; width: 360px;
    box-shadow: 0 24px 64px rgba(0,0,0,.55);
  }
  .cartao-login .logo-login { display: flex; justify-content: center; margin-bottom: 20px; }
  .cartao-login .logo-login img { height: 50px; width: 50px; filter: drop-shadow(0 6px 20px rgba(45,184,207,.35)); }
  .cartao-login h1 {
    background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent;
    font-size: 19px; margin: 0 0 4px 0; text-align: center; font-weight: 700;
  }
  .cartao-login .sub { color: var(--fg-dim); font-size: 12px; text-align: center; margin-bottom: 22px; line-height: 1.5; }
  label { display: block; font-size: 10.5px; color: var(--fg-dim); margin: 15px 0 5px 0;
          text-transform: uppercase; letter-spacing: .05em; }
  input {
    width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border);
    background: rgba(0,0,0,.28); color: var(--fg); font-size: 14px;
    transition: border-color .15s ease, box-shadow .15s ease;
  }
  input:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  button.entrar { width: 100%; margin-top: 24px; padding: 11px; border-radius: 8px; font-size: 14px; }
  .erro { color: var(--erro); font-size: 12px; text-align: center; margin-top: 14px; }
  .link-alterar-senha { display: block; text-align: center; margin-top: 18px; font-size: 11.5px;
                         color: var(--fg-dim); text-decoration: none; }
  .link-alterar-senha:hover { color: var(--teal); }
</style>
</head>
<body>
  <div class="centro">
    <form class="cartao-login" method="POST" action="/alterar-senha">
      <div class="logo-login"><img src="__LOGO__" alt="Logo"></div>
      <h1>Alterar senha</h1>
      <div class="sub">Informe seu usuário e a senha atual para definir uma nova senha.</div>
      <label>Usuário</label>
      <input type="text" name="usuario" autofocus required autocomplete="username">
      <label>Senha atual</label>
      __CAMPO_SENHA_ATUAL__
      <label>Nova senha</label>
      __CAMPO_NOVA_SENHA__
      <label>Confirmar nova senha</label>
      __CAMPO_CONFIRMA_SENHA__
      <button class="btn-accent entrar" type="submit">Salvar nova senha</button>
      __ERRO__
      <a class="link-alterar-senha" href="/login">Voltar para o login</a>
    </form>
  </div>
  __FOOTER__
<script>__JS_ALTERNAR_SENHA__</script>
</body>
</html>
"""

_MENSAGENS_ERRO_ALTERAR_SENHA = {
    "credenciais": "Usuário ou senha atual incorretos.",
    "confirmacao": "A nova senha e a confirmação não coincidem.",
    "tamanho": "A nova senha precisa ter ao menos 4 caracteres.",
    "campos": "Preencha todos os campos.",
}


def _montar_alterar_senha_html(erro: Optional[str] = None) -> str:
    bloco_erro = ""
    if erro:
        texto_erro = _MENSAGENS_ERRO_ALTERAR_SENHA.get(erro, "Não foi possível alterar a senha.")
        bloco_erro = f'<div class="erro">{texto_erro}</div>'
    return (
        _ALTERAR_SENHA_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__CAMPO_SENHA_ATUAL__", _campo_senha_html("senha_atual", "current-password"))
        .replace("__CAMPO_NOVA_SENHA__", _campo_senha_html("nova_senha", "new-password"))
        .replace("__CAMPO_CONFIRMA_SENHA__", _campo_senha_html("confirma_senha", "new-password"))
        .replace("__ERRO__", bloco_erro)
        .replace("__JS_ALTERNAR_SENHA__", _JS_ALTERNAR_SENHA)
        .replace("__FOOTER__", _FOOTER_HTML)
    )


# CSS/JS compartilhados entre hub, usuários e alertas (navbar + variáveis de
# cor + o pequeno "toast" usado pelo card de Relatórios).
_NAVBAR_CSS = """
  @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700;800&display=swap');
  :root {
    --bg: #0b0f14; --bg-panel: rgba(24,31,39,.66); --bg-panel-solid: #181f27;
    --fg: #e6edf3; --fg-dim: #8b98a5;
    --teal: #2db8cf; --lime: #b0cb1c; --grayblue: #97a2a8; --lightgray: #d4dee0;
    --accent: #2db8cf; --border: rgba(255,255,255,.09); --border-forte: rgba(255,255,255,.18);
    --ok: #4ec9b0; --erro: #f14c4c; --run: #dcdcaa; --wait: #808080;
    --gradiente-marca: linear-gradient(135deg, var(--teal), var(--lime));
    color-scheme: dark;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    background: var(--bg); color: var(--fg);
    font-family: 'Raleway', 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    margin: 0; min-height: 100vh; position: relative;
    display: flex; flex-direction: column;
  }
  /* Visual dos <select> em todo o site - fundo sólido (não translúcido) pra
     combinar com a lista de opções nativa do navegador, que também respeita
     o tema escuro graças ao color-scheme acima. Sem isso, o navegador abria
     o dropdown com fundo branco padrão do sistema, destoando do resto. */
  select {
    background-color: var(--bg-panel-solid); color: var(--fg);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 32px 8px 12px; font-size: 13px; font-family: inherit;
    appearance: none; -webkit-appearance: none; -moz-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238b98a5' stroke-width='1.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 12px center;
    cursor: pointer; transition: border-color .15s, box-shadow .15s;
  }
  select:hover { border-color: var(--border-forte); }
  select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  select option { background-color: var(--bg-panel-solid); color: var(--fg); }
  body::before {
    content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background:
      radial-gradient(ellipse 800px 550px at 10% -10%, rgba(45,184,207,.15), transparent 60%),
      radial-gradient(ellipse 650px 550px at 105% 8%, rgba(176,203,28,.10), transparent 60%),
      radial-gradient(ellipse 900px 650px at 50% 120%, rgba(45,184,207,.08), transparent 60%);
  }
  a { color: inherit; }
  .navbar { display: flex; justify-content: space-between; align-items: center;
            padding: 13px 28px; border-bottom: 1px solid var(--border);
            background: rgba(14,18,23,.72); backdrop-filter: blur(14px) saturate(140%);
            -webkit-backdrop-filter: blur(14px) saturate(140%);
            position: sticky; top: 0; z-index: 40; }
  .navbar .marca { display: flex; align-items: center; gap: 12px; }
  .navbar .marca img { height: 30px; width: 30px; display: block; }
  .navbar h1 { font-size: 17px; margin: 0; font-weight: 700;
               background: var(--gradiente-marca); -webkit-background-clip: text;
               background-clip: text; color: transparent; }
  .navbar h1 a { text-decoration: none; }
  .navbar .sub { color: var(--fg-dim); font-size: 11px; margin-top: 1px; }
  .navbar .acoes { display: flex; gap: 10px; align-items: center; }
  .navbar .usuario-info { font-size: 12px; color: var(--fg-dim); text-align: right; }
  .navbar .usuario-info b { color: var(--fg); }

  .usuario-area-navbar { position: relative; }
  .botao-usuario-navbar { display: flex; align-items: center; gap: 9px; background: transparent; border: none;
                            cursor: pointer; padding: 5px 8px 5px 5px; border-radius: 10px;
                            transition: background .15s ease; font-family: inherit; }
  .botao-usuario-navbar:hover { background: rgba(255,255,255,.05); }
  .avatar-navbar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; flex-shrink: 0;
                     border: 1px solid var(--border-forte); }
  .avatar-navbar-generico { background: rgba(255,255,255,.07); display: flex; align-items: center;
                              justify-content: center; color: var(--fg-dim); }
  .avatar-navbar-generico svg { width: 18px; height: 18px; }
  .seta-menu-navbar { width: 13px; height: 13px; color: var(--fg-dim); flex-shrink: 0;
                        transition: transform .15s ease; }
  .seta-menu-navbar.girada { transform: rotate(180deg); }
  .dropdown-usuario-navbar { display: none; position: absolute; top: calc(100% + 8px); right: 0; min-width: 190px;
                               background: var(--bg-panel-solid); border: 1px solid var(--border-forte);
                               border-radius: 10px; padding: 8px; box-shadow: 0 14px 32px rgba(0,0,0,.45); z-index: 80; }
  .dropdown-usuario-navbar.aberto { display: block; }
  .cargo-dropdown-navbar { font-size: 11.5px; color: var(--fg-dim); padding: 5px 9px 11px 9px;
                             border-bottom: 1px solid var(--border); margin-bottom: 6px; }
  .link-ver-perfil-navbar { display: block; padding: 7px 9px; border-radius: 7px; color: var(--fg);
                              text-decoration: none; font-size: 12.5px; font-weight: 600;
                              transition: background .15s ease, color .15s ease; }
  .link-ver-perfil-navbar:hover { background: rgba(45,184,207,.1); color: var(--teal); }
  .badge { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 10px;
           font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .badge-admin { background: rgba(45,184,207,.15); color: var(--teal); border: 1px solid rgba(45,184,207,.35); }
  .badge-view { background: rgba(139,152,165,.15); color: var(--fg-dim); border: 1px solid var(--border); }
  button, .btn-link { background: rgba(255,255,255,.06); color: var(--fg); border: 1px solid var(--border);
           padding: 9px 16px; border-radius: 8px; cursor: pointer; font-size: 13px;
           text-decoration: none; display: inline-block; transition: all .15s ease; }
  button:hover, .btn-link:hover { background: rgba(255,255,255,.11); border-color: var(--border-forte); }
  .btn-accent { background: var(--gradiente-marca); color: #0b0f14; font-weight: 700; border: none; }
  .btn-accent:hover { background: var(--gradiente-marca); filter: brightness(1.1); box-shadow: 0 6px 20px rgba(45,184,207,.25); }
  .conteudo { padding: 30px 28px; max-width: 1120px; margin: 0 auto; flex: 1 0 auto; width: 100%; }
  .rodape { margin-top: 44px; padding: 20px 28px; border-top: 1px solid var(--border);
            display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
            color: var(--fg-dim); font-size: 11px; }
  .rodape .marca-rodape { display: flex; align-items: center; gap: 8px; }
  .rodape .marca-rodape img { height: 15px; width: 15px; opacity: .75; }
  .toast { position: fixed; bottom: 26px; left: 50%; transform: translateX(-50%) translateY(20px);
           background: rgba(24,31,39,.96); backdrop-filter: blur(10px); border: 1px solid var(--border-forte); color: var(--fg);
           padding: 13px 22px; border-radius: 10px; font-size: 13px; box-shadow: 0 14px 34px rgba(0,0,0,.5);
           opacity: 0; pointer-events: none; transition: opacity .25s ease, transform .25s ease; z-index: 50; }
  .toast.mostrar { opacity: 1; transform: translateX(-50%) translateY(0); }

  /* campo de senha com botao de mostrar/ocultar ("olhinho") */
  .campo-senha { position: relative; }
  .campo-senha input { width: 100%; padding-right: 38px; }
  .alternar-senha { position: absolute; right: 4px; top: 50%; transform: translateY(-50%);
                     background: none; border: none; padding: 5px; margin: 0; cursor: pointer;
                     display: flex; align-items: center; justify-content: center; border-radius: 6px; }
  .alternar-senha:hover { background: rgba(255,255,255,.08); }
  .alternar-senha svg { width: 16px; height: 16px; stroke: var(--fg-dim); pointer-events: none; }

  .btn-perigo { background: rgba(241,76,76,.12); color: #ff8080; border: 1px solid rgba(241,76,76,.3); }
  .btn-perigo:hover { background: rgba(241,76,76,.2); border-color: #f14c4c; }

  /* mensagens de sucesso/erro em paginas de formulario (login, alterar senha) */
  .msg-sucesso { color: var(--ok); font-size: 12px; text-align: center; margin-top: 14px; }
"""

_JS_ALTERNAR_SENHA = """
function alternarSenha(inputId, botao) {
  const input = document.getElementById(inputId);
  const aberto = botao.querySelector('.olho-aberto');
  const fechado = botao.querySelector('.olho-fechado');
  if (input.type === 'password') {
    input.type = 'text';
    aberto.style.display = 'none';
    fechado.style.display = '';
  } else {
    input.type = 'password';
    aberto.style.display = '';
    fechado.style.display = 'none';
  }
}
"""

_NAVBAR_HTML = """
  <div class="navbar">
    <div class="marca">
      <img src="__LOGO__" alt="Logo">
      <div>
        <h1><a href="/">Painel de Automações</a></h1>
        <div class="sub">__SUBTITULO__</div>
      </div>
    </div>
    <div class="acoes">
      <div class="usuario-area-navbar">
        <button class="botao-usuario-navbar" onclick="alternarMenuUsuarioNavbar(event)" type="button">
          __AVATAR_NAVBAR__
          <div class="usuario-info">
            <b>__USUARIO__</b> <span class="badge __BADGE_CLASSE__">__BADGE_TEXTO__</span>
          </div>
          <svg class="seta-menu-navbar" id="seta-menu-navbar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <div class="dropdown-usuario-navbar" id="dropdown-usuario-navbar">
          <div class="cargo-dropdown-navbar" id="cargo-dropdown-navbar">Carregando...</div>
          <a href="/perfil/__LOGIN__" class="link-ver-perfil-navbar">Ver perfil</a>
        </div>
      </div>
      <a class="btn-link" href="/logout">Sair</a>
    </div>
  </div>
  <script>
    // Intercepta TODA chamada fetch() de QUALQUER página - se a sessão
    // expirou (90 min sem atividade) e a API responde 401, redireciona
    // pro login automaticamente, em vez de cada função JS precisar
    // lembrar de tratar isso na mão (o que já vinha esquecendo em vários
    // lugares, mostrando o JSON de erro cru pro usuário em vez de só
    // mandar logar de novo).
    (function () {
      const fetchOriginal = window.fetch;
      window.fetch = async function (...args) {
        const resposta = await fetchOriginal(...args);
        if (resposta.status === 401 && !window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
        return resposta;
      };
    })();

    // Menu dropdown do usuário na navbar (foto/ícone + nome + cargo +
    // link "Ver perfil") - o cargo só é buscado (via /api/perfil/) na
    // primeira vez que o menu abre, pra não pesar toda página com uma
    // consulta ao Movidesk sem necessidade.
    let _cargoNavbarJaCarregado = false;
    function alternarMenuUsuarioNavbar(ev) {
      ev.stopPropagation();
      const dropdown = document.getElementById('dropdown-usuario-navbar');
      const seta = document.getElementById('seta-menu-navbar');
      const vaiAbrir = !dropdown.classList.contains('aberto');
      dropdown.classList.toggle('aberto', vaiAbrir);
      if (seta) seta.classList.toggle('girada', vaiAbrir);
      if (vaiAbrir) carregarCargoNavbar();
    }
    document.addEventListener('click', function (ev) {
      const area = document.querySelector('.usuario-area-navbar');
      const dropdown = document.getElementById('dropdown-usuario-navbar');
      if (area && dropdown && !area.contains(ev.target)) {
        dropdown.classList.remove('aberto');
        const seta = document.getElementById('seta-menu-navbar');
        if (seta) seta.classList.remove('girada');
      }
    });
    async function carregarCargoNavbar() {
      if (_cargoNavbarJaCarregado) return;
      const el = document.getElementById('cargo-dropdown-navbar');
      try {
        const resp = await fetch('/api/perfil/__LOGIN__');
        const dados = await resp.json();
        if (dados.ok) {
          el.innerText = dados.cargo || 'Cargo não definido';
          _cargoNavbarJaCarregado = true;
        } else {
          el.style.display = 'none';
        }
      } catch (e) {
        el.style.display = 'none';
      }
    }
  </script>
"""

_FOOTER_HTML = """
  <div class="rodape">
    <div class="marca-rodape">
      <img src="__LOGO__" alt="Logo">
      <span>PDA</span>
    </div>
    <div>Painel de Automações</div>
  </div>
"""


def _saudacao_bem_vindo(genero: str) -> str:
    """Flexão de gênero pro "Bem-vindo" do hub - "" (não informado) usa
    uma forma neutra em vez de forçar masculino ou feminino."""
    if genero == "F":
        return "Bem-vinda"
    if genero == "M":
        return "Bem-vindo"
    return "Bem-vindo(a)"


def _texto_badge_admin(genero: str) -> str:
    """Flexão de gênero pro selo "Administrador"/"Administradora" na
    navbar - "Visualização" já é neutro, não precisa de flexão."""
    return "Administradora" if genero == "F" else "Administrador"


def _montar_navbar(sessao: dict, subtitulo: str) -> str:
    badge_classe = "badge-admin" if sessao["admin"] else "badge-view"
    badge_texto = _texto_badge_admin(sessao.get("genero", "")) if sessao["admin"] else "Visualização"
    login = sessao["usuario"]
    if _caminho_foto_usuario(login):
        avatar_navbar = f'<img class="avatar-navbar" src="/foto-usuario/{login}" alt="">'
    else:
        avatar_navbar = (
            '<div class="avatar-navbar avatar-navbar-generico">'
            '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'
            "</svg></div>"
        )
    return (
        _NAVBAR_HTML
        .replace("__SUBTITULO__", subtitulo)
        .replace("__USUARIO__", sessao.get("nome") or sessao["usuario"])
        .replace("__BADGE_CLASSE__", badge_classe)
        .replace("__BADGE_TEXTO__", badge_texto)
        .replace("__AVATAR_NAVBAR__", avatar_navbar)
        .replace("__LOGIN__", login)
    )


def _montar_footer() -> str:
    return _FOOTER_HTML  # já vem com o logo embutido (ver bloco de otimização)


_SVG_OLHO_ABERTO = (
    '<svg class="olho-aberto" viewBox="0 0 24 24" fill="none" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/>'
    "</svg>"
)
_SVG_OLHO_FECHADO = (
    '<svg class="olho-fechado" style="display:none" viewBox="0 0 24 24" fill="none" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4.24 4.24"/>'
    '<path d="M9.88 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-3.09 4.19'
    'M6.1 6.1C3.2 8 1 12 1 12a18.6 18.6 0 0 0 5.06 5.94A10.94 10.94 0 0 0 12 20c1.06 0 2.07-.17 3-.47"/>'
    "</svg>"
)


def _campo_senha_html(input_id: str, autocomplete: str, autofocus: bool = False) -> str:
    """Monta um <input type='password'> com botão de mostrar/ocultar
    ('olhinho') ao lado - reaproveitado em login, alterar senha e nos
    modais de admin. Precisa de _JS_ALTERNAR_SENHA presente na página."""
    autofocus_attr = " autofocus" if autofocus else ""
    return (
        f'<div class="campo-senha">'
        f'<input type="password" id="{input_id}" name="{input_id}" required '
        f'autocomplete="{autocomplete}"{autofocus_attr}>'
        f'<button type="button" class="alternar-senha" tabindex="-1" '
        f'onclick="alternarSenha(\'{input_id}\', this)">'
        f"{_SVG_OLHO_ABERTO}{_SVG_OLHO_FECHADO}"
        f"</button></div>"
    )


_HUB_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações - Início</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .hero { padding: 6px 0 30px 0; }
  .hero h1 { font-size: 27px; margin: 0 0 8px 0; font-weight: 700; letter-spacing: -.01em; }
  .hero .sub-hero { color: var(--fg-dim); font-size: 14px; }
  .hero .link-nome-hero { color: inherit; text-decoration: none; border-bottom: 2px solid transparent;
                            transition: border-color .15s ease; }
  .hero .link-nome-hero:hover { border-color: var(--teal); }

  .grid-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }

  .hub-paginado { overflow: hidden; position: relative; }
  .trilho-hub { display: flex; transition: transform .4s cubic-bezier(.4,0,.2,1); }
  .pagina-hub { flex: 0 0 100%; min-width: 100%; box-sizing: border-box; padding-right: 2px; }
  .grade-hub { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; }
  .navegacao-hub { display: flex; align-items: center; justify-content: center; gap: 18px; margin-top: 28px; }
  .seta-hub { background: rgba(255,255,255,.05); border: 1px solid var(--border); color: var(--fg);
              width: 36px; height: 36px; border-radius: 50%; cursor: pointer; font-size: 18px; line-height: 1;
              display: flex; align-items: center; justify-content: center; transition: background .15s, border-color .15s; }
  .seta-hub:hover:not(:disabled) { background: rgba(255,255,255,.1); border-color: var(--teal); }
  .seta-hub:disabled { opacity: .3; cursor: default; }
  .pontos-hub { display: flex; gap: 9px; }
  .ponto-hub { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,.15);
               cursor: pointer; transition: background .15s, transform .15s; border: none; padding: 0; }
  .ponto-hub:hover { background: rgba(255,255,255,.3); }
  .ponto-hub.ativo { background: var(--teal); transform: scale(1.35); }

  .card-hub {
    background: var(--bg-panel); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 26px 24px; cursor: pointer; text-decoration: none; color: inherit; display: block;
    position: relative;
    transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
    opacity: 0; transform: translateY(14px); animation: entrada-card .5s ease forwards;
  }
  .card-hub:nth-child(1) { animation-delay: .02s; }
  .card-hub:nth-child(2) { animation-delay: .08s; }
  .card-hub:nth-child(3) { animation-delay: .14s; }
  .card-hub:nth-child(4) { animation-delay: .20s; }
  .card-hub:nth-child(5) { animation-delay: .26s; }
  .card-hub:nth-child(6) { animation-delay: .32s; }
  .card-hub:nth-child(7) { animation-delay: .38s; }
  @keyframes entrada-card { to { opacity: 1; transform: translateY(0); } }

  .card-hub:hover {
    transform: translateY(-5px);
    border-color: var(--accent-card, var(--teal));
    box-shadow: 0 18px 40px rgba(0,0,0,.4), 0 0 26px -10px var(--accent-card, var(--teal));
  }
  .card-hub .icone { width: 54px; height: 54px; border-radius: 14px; display: flex; align-items: center;
                      justify-content: center; margin-bottom: 18px;
                      box-shadow: inset 0 0 0 1px rgba(255,255,255,.05); }
  .card-hub .icone svg { width: 26px; height: 26px; stroke: var(--accent-card, var(--accent)); }
  .card-hub h2 { font-size: 16px; margin: 0 0 6px 0; }
  .card-hub p { font-size: 12px; color: var(--fg-dim); margin: 0; line-height: 1.55; }
  .card-hub .tag-em-breve { display: inline-block; margin-top: 12px; font-size: 10px; font-weight: 700;
              letter-spacing: .04em; text-transform: uppercase; color: var(--run); }
  .card-hub.bloqueado { cursor: default; opacity: .55; filter: grayscale(.4); }
  .card-hub.bloqueado:hover { transform: none; border-color: var(--border); box-shadow: none; }
  .card-hub.bloqueado .icone svg { stroke: var(--fg-dim); }
  .card-hub .tag-live { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px;
              font-size: 10px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .tag-live .ponto { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
  .tag-live.ok { color: var(--ok); }
  .tag-live.ok .ponto { background: var(--ok); box-shadow: 0 0 6px var(--ok); }
  .tag-live.alerta { color: #ff8080; }
  .tag-live.alerta .ponto { background: #f14c4c; box-shadow: 0 0 8px #f14c4c; animation: pulso-ponto 1.4s infinite; }
  .tag-live.agendada { color: var(--run); }
  .tag-live.agendada .ponto { background: var(--run); box-shadow: 0 0 6px var(--run); }
  .tag-live.desconhecido { color: var(--fg-dim); }
  .tag-live.desconhecido .ponto { background: var(--fg-dim); }
  @keyframes pulso-ponto { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="hero">
      <h1>__SAUDACAO_HERO__, <a href="/perfil/__LOGIN_HERO__" class="link-nome-hero">__USUARIO_HERO__</a></h1>
      <div class="sub-hero">Central de automações e ferramentas internas.</div>
    </div>

    <div class="hub-paginado">
      <div class="trilho-hub" id="trilho-hub">
    <div class="pagina-hub" data-pagina="0">
      <div class="grade-hub">
      <a class="card-hub" href="/alertas" style="--accent-card:#2db8cf">
        <div class="icone" style="background:rgba(45,184,207,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3a5 5 0 0 0-5 5v3.5c0 .7-.3 1.4-.8 1.9L5 15h14l-1.2-1.6c-.5-.5-.8-1.2-.8-1.9V8a5 5 0 0 0-5-5z"/>
            <path d="M9.5 18a2.5 2.5 0 0 0 5 0"/>
          </svg>
        </div>
        <h2>Alertas Suporte</h2>
        <p>Status, agenda e log de execução de todos os alertas operacionais.</p>
      </a>
      <a class="card-hub" href="/contingencias" style="--accent-card:#f14c4c">
        <div class="icone" style="background:rgba(241,76,76,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3l7 3v6c0 4.5-3 8-7 9-4-1-7-4.5-7-9V6l7-3z"/>
            <path d="M12 8v5"/><path d="M12 16h.01"/>
          </svg>
        </div>
        <h2>Contingências SEFAZ</h2>
        <p>Monitoramento de ativação, agendamento e encerramento da SVC-AN e SVC-RS por estado.</p>
        <span class="tag-live __CLASSE_CONTING__"><span class="ponto"></span>__RESUMO_CONTING__</span>
      </a>
      __CARD_INDICADORES_MOVIDESK__
      __CARD_AUTOMACAO_MOVIDESK__
      __CARD_RELATORIOS_SHEIN__
      __CARD_DASH_FINANCEIRO__
      __CARD_MANUTENCAO_ALERTAS__
      __CARD_MANUTENCAO_REJEICOES__
      </div>
    </div>
    <div class="pagina-hub" data-pagina="1">
      <div class="grade-hub">
      __CARD_MANUTENCAO_RELATORIOS__
      __CARD_DASHBOARDS_CLIENTES__
      __CARD_MANUTENCAO_USUARIOS__
      __CARD_HORAS_TRABALHADAS__
      __CARD_LOGS__
      <a class="card-hub" href="/emailpack" style="--accent-card:#9b5de5">
        <div class="icone" style="background:rgba(155,93,229,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="5" width="18" height="14" rx="2"/>
            <path d="M3 7l9 6 9-6"/>
          </svg>
        </div>
        <h2>Monitoramento EmailPack</h2>
        <p>Varredura dos logs dos serviços EmailPack por e-mail processado, com aviso automático no Teams.</p>
      </a>
      <a class="card-hub" href="__URL_MEU_PLANTAO__" target="_blank" rel="noopener noreferrer" style="--accent-card:#6c63ff">
        <div class="icone" style="background:rgba(108,99,255,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>
          </svg>
        </div>
        <h2>Meu Plantão</h2>
        <p>Controle de horas trabalhadas em plantão e lançamento de horas.</p>
      </a>
      <a class="card-hub" href="/ferias" style="--accent-card:#4cc9f0">
        <div class="icone" style="background:rgba(76,201,240,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2"/>
            <path d="M3 9h18M8 2v4M16 2v4"/>
            <path d="M8 14l2 2 4-4"/>
          </svg>
        </div>
        <h2>Calendário de Férias</h2>
        <p>Visualização das férias já agendadas e aprovadas da equipe.</p>
      </a>
      </div>
    </div>
    __PAGINA_DADOS_SENSIVEIS__
      </div>
    </div>
    <div class="navegacao-hub">
      <button class="seta-hub" id="seta-esquerda-hub" onclick="mudarPaginaHub(-1)">‹</button>
      <div class="pontos-hub" id="pontos-hub"></div>
      <button class="seta-hub" id="seta-direita-hub" onclick="mudarPaginaHub(1)">›</button>
    </div>
  </div>

  __FOOTER__

<script>
let paginaAtualHub = 0;
const totalPaginasHub = document.querySelectorAll('.pagina-hub').length;

function atualizarNavegacaoHub() {
  document.getElementById('trilho-hub').style.transform = 'translateX(-' + (paginaAtualHub * 100) + '%)';
  document.querySelectorAll('.ponto-hub').forEach((p, i) => p.classList.toggle('ativo', i === paginaAtualHub));
  document.getElementById('seta-esquerda-hub').disabled = paginaAtualHub === 0;
  document.getElementById('seta-direita-hub').disabled = paginaAtualHub === totalPaginasHub - 1;
}

function mudarPaginaHub(direcao) {
  const nova = paginaAtualHub + direcao;
  if (nova < 0 || nova >= totalPaginasHub) return;
  paginaAtualHub = nova;
  atualizarNavegacaoHub();
}

function irParaPaginaHub(indice) {
  paginaAtualHub = indice;
  atualizarNavegacaoHub();
}

(function() {
  const pontosEl = document.getElementById('pontos-hub');
  for (let i = 0; i < totalPaginasHub; i++) {
    const botao = document.createElement('button');
    botao.className = 'ponto-hub' + (i === 0 ? ' ativo' : '');
    botao.setAttribute('aria-label', 'Página ' + (i + 1));
    botao.onclick = () => irParaPaginaHub(i);
    pontosEl.appendChild(botao);
  }
  atualizarNavegacaoHub();
})();

// deslizar lateralmente com o dedo (touch) ou mouse
let inicioXHub = null;
const trilhoHub = document.getElementById('trilho-hub');
trilhoHub.addEventListener('touchstart', e => { inicioXHub = e.touches[0].clientX; }, {passive: true});
trilhoHub.addEventListener('touchend', e => {
  if (inicioXHub === null) return;
  const diffX = e.changedTouches[0].clientX - inicioXHub;
  if (diffX > 50) mudarPaginaHub(-1);
  else if (diffX < -50) mudarPaginaHub(1);
  inicioXHub = null;
});
</script>

  <div class="toast" id="toast"></div>

<script>
function abrirEmConstrucao(ev, nome) {
  ev.preventDefault();
  const toast = document.getElementById('toast');
  toast.innerText = nome + ' está em construção e ainda não está disponível.';
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3500);
  return false;
}
</script>
</body>
</html>
"""


def _resumo_conting_hub() -> tuple:
    """Texto + classe CSS do selo do card de Contingências no hub, calculado
    a partir do estado atual (não faz nenhuma consulta nova, só lê o que já
    tem em memória)."""
    with _lock_contingencias:
        ufs = dict(estado_contingencias["ufs"])
        ultimo_erro = estado_contingencias["ultimo_erro"]
        ultima_verificacao = estado_contingencias["ultima_verificacao"]

    qtd_conting = sum(1 for v in ufs.values() if v == "contingencia")
    qtd_agendada = sum(1 for v in ufs.values() if v == "agendada")
    if ultima_verificacao is None:
        return "desconhecido", "Verificando..."
    if qtd_conting > 0:
        rotulo = "1 UF em contingência" if qtd_conting == 1 else f"{qtd_conting} UFs em contingência"
        return "alerta", rotulo
    if qtd_agendada > 0:
        rotulo = "1 UF com contingência agendada" if qtd_agendada == 1 else f"{qtd_agendada} UFs com contingência agendada"
        return "agendada", rotulo
    if ultimo_erro:
        return "desconhecido", "Não verificado"
    return "ok", "Tudo normal"


# Cards com acesso restrito - cada um só aparece no HTML pra quem tem a
# permissão correspondente (mesmo critério usado pelas rotas em
# do_GET, ver _tem_acesso_* e checagem de sessao["admin"]). Antes esses
# cards apareciam pra todo mundo e só bloqueavam o acesso no clique;
# agora ficam ocultos de quem não pode acessar, junto com os cards de
# Dados Sensíveis logo abaixo que já seguiam esse padrão.
_CARD_INDICADORES_MOVIDESK_HTML = """<a class="card-hub" href="/indicadores-movidesk" style="--accent-card:#e8a33d">
        <div class="icone" style="background:rgba(232,163,61,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v18h18"/>
            <path d="M7 15l4-5 3 3 5-7"/>
          </svg>
        </div>
        <h2>Indicadores Movidesk</h2>
        <p>Escalonamentos, dúvidas e sincronização - métricas direto do Movidesk.</p>
      </a>"""

_CARD_AUTOMACAO_MOVIDESK_HTML = """<a class="card-hub" href="/automacao-movidesk" style="--accent-card:#b0cb1c">
        <div class="icone" style="background:rgba(176,203,28,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 13v-1a8 8 0 0 1 16 0v1"/>
            <rect x="2.5" y="13" width="4" height="6" rx="1.5"/>
            <rect x="17.5" y="13" width="4" height="6" rx="1.5"/>
            <path d="M19.5 19v1a3 3 0 0 1-3 3h-3"/>
          </svg>
        </div>
        <h2>Automação Movidesk</h2>
        <p>Controle de sincronização - NOC, Satisfação, Uptime, GMUD, Jira e outras automações ainda em construção.</p>
      </a>"""

_CARD_RELATORIOS_SHEIN_HTML = """<a class="card-hub" href="/relatorios-shein" style="--accent-card:#dcdcaa">
        <div class="icone" style="background:rgba(220,220,170,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 20V10"/><path d="M12 20V4"/><path d="M20 20v-7"/><path d="M2 20h20"/>
          </svg>
        </div>
        <h2>Relatórios Shein</h2>
        <p>Extração de relatórios de notas e canceladas do cliente Shein.</p>
      </a>"""

_CARD_DASH_FINANCEIRO_HTML = """<a class="card-hub" href="/dash-financeiro" style="--accent-card:#dcdcaa">
        <div class="icone" style="background:rgba(220,220,170,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v18h18"/>
            <path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>
          </svg>
        </div>
        <h2>Atualização Dash Financeiro</h2>
        <p>Contagem mensal de documentos por cliente (NFe, CTe, NFCe, CFe, NFSe, MDFe, LASA, SaaS) pro Power BI.</p>
      </a>"""

_CARD_MANUTENCAO_ALERTAS_HTML = """<a class="card-hub" href="/manutencao-alertas" style="--accent-card:#97a2a8">
        <div class="icone" style="background:rgba(151,162,168,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <ellipse cx="12" cy="5" rx="8" ry="3"/>
            <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>
            <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>
          </svg>
        </div>
        <h2>Manutenção de Alertas em Banco</h2>
        <p>Criação e gerenciamento dos alertas automáticos configurados em CONFIGURACOES_ALERTA.</p>
      </a>"""

_CARD_MANUTENCAO_REJEICOES_HTML = """<a class="card-hub" href="/manutencao-rejeicoes" style="--accent-card:#ce9178">
        <div class="icone" style="background:rgba(206,145,120,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M9 9l6 6M15 9l-6 6"/>
          </svg>
        </div>
        <h2>Manutenção Rejeições em Banco</h2>
        <p>Criação e gerenciamento das rejeições automáticas configuradas em CONFIGURACOES_REJEICAO.</p>
      </a>"""

_CARD_MANUTENCAO_RELATORIOS_HTML = """<a class="card-hub" href="/manutencao-relatorios" style="--accent-card:#89b4d8">
        <div class="icone" style="background:rgba(137,180,216,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
            <path d="M14 3v6h6M9 13h6M9 17h6M9 9h1"/>
          </svg>
        </div>
        <h2>Manutenção de Relatórios em Banco</h2>
        <p>Criação e gerenciamento dos relatórios automáticos configurados em CONFIGURACOES_RELATORIO.</p>
      </a>"""

_CARD_DASHBOARDS_CLIENTES_HTML = """<a class="card-hub" href="/dashboards-clientes" style="--accent-card:#f5a3d0">
        <div class="icone" style="background:rgba(245,163,208,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="9" rx="1"/>
            <rect x="14" y="3" width="7" height="5" rx="1"/>
            <rect x="14" y="12" width="7" height="9" rx="1"/>
            <rect x="3" y="16" width="7" height="5" rx="1"/>
          </svg>
        </div>
        <h2>Dashboards por Cliente <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>Escolha um cliente e um produto pra ver os indicadores específicos dele.</p>
      </a>"""

_CARD_HORAS_TRABALHADAS_HTML = """<a class="card-hub" href="/horas-trabalhadas" style="--accent-card:#4ec9b0">
        <div class="icone" style="background:rgba(78,201,176,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M12 7v5l3 3"/>
          </svg>
        </div>
        <h2>Horas Trabalhadas</h2>
        <p>Apontamentos de horas por analista, direto do banco do Movidesk, filtrável por dia ou mês.</p>
      </a>"""

_CARD_LOGS_HTML = """<a class="card-hub" href="/logs" style="--accent-card:#9cdcfe">
        <div class="icone" style="background:rgba(156,220,254,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16v16H4z"/>
            <path d="M8 9h8M8 13h8M8 17h5"/>
          </svg>
        </div>
        <h2>Logs</h2>
        <p>Log de execução isolado por card - um arquivo por automação, salvos em logs/.</p>
      </a>"""


# Cards de Dados Sensíveis (String Connections + Criptografia de Dados
# Sensíveis) - mesmo padrão acima, só que continuam morando na página 2
# (montada à parte em _montar_hub_html) porque ficam sempre como os
# DOIS ÚLTIMOS cards, pedido explícito.
_CARD_CHECKLISTS_HTML = """<div class="card-hub bloqueado" style="--accent-card:#e0b354">
        <div class="icone" style="background:rgba(224,179,84,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="3" width="14" height="18" rx="2"/>
            <path d="M9 3v2a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1V3"/>
            <path d="M8.5 12l1.5 1.5 3-3M8.5 17l1.5 1.5"/>
          </svg>
        </div>
        <h2>Manutenção de Checklists</h2>
        <p>Criação e gerenciamento de checklists operacionais.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

# Card independente pra futura tela de "considerar/desconsiderar" tickets
# na pesquisa de satisfação do Movidesk - por enquanto só o card
# "bloqueado" (mesmo padrão do card de Checklists acima), sem rota nem
# lógica funcional ainda por trás.
_CARD_PESQUISA_SATISFACAO_HTML = """<div class="card-hub bloqueado" style="--accent-card:#ff8fa3">
        <div class="icone" style="background:rgba(255,143,163,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 17.3l-5.4 3.2 1.4-6.1L3 10.2l6.2-.5L12 4l2.8 5.7 6.2.5-4.9 4.2 1.4 6.1z"/>
          </svg>
        </div>
        <h2>Pesquisa de Satisfação</h2>
        <p>Considerar ou desconsiderar tickets específicos na pesquisa de satisfação do Movidesk.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

_CARD_NNU_ENCHANCED_HTML = """<div class="card-hub bloqueado" style="--accent-card:#7fd8a6">
        <div class="icone" style="background:rgba(127,216,166,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-3.5-7.1"/>
            <path d="M21 3v6h-6"/>
          </svg>
        </div>
        <h2>NNU Enchanced</h2>
        <p>Reprocessamento automático de NNUs pendentes, com ajuste de checklists e planilhas.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

_CARD_MANUTENCAO_USUARIOS_HTML = """<a class="card-hub" href="/manutencao-usuarios" style="--accent-card:#b389f9">
        <div class="icone" style="background:rgba(179,137,249,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="9" cy="8" r="3"/>
            <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
            <circle cx="17" cy="9" r="2.4"/>
            <path d="M15.5 14.2c2.4.4 4.3 2.3 4.5 4.8"/>
          </svg>
        </div>
        <h2>Usuários</h2>
        <p>Login no PDA, permissões, vínculo com o Movidesk e cadastro/desativação em produção - tudo num só lugar.</p>
      </a>
      """

_CARDS_DADOS_SENSIVEIS_HTML = """<a class="card-hub" href="/config-seguro" style="--accent-card:#569cd6">
        <div class="icone" style="background:rgba(86,156,214,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
          </svg>
        </div>
        <h2>Criptografia de Dados Sensíveis</h2>
        <p>Credenciais sensíveis cifradas com Fernet (config.dat), em vez de texto puro nos .env.</p>
      </a>
      <a class="card-hub" href="/string-connections" style="--accent-card:#c586c0">
        <div class="icone" style="background:rgba(197,134,192,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="7" width="18" height="10" rx="2"/>
            <path d="M7 12h.01M11 12h6"/>
          </svg>
        </div>
        <h2>String Connections</h2>
        <p>Conexões de banco reutilizáveis por cliente e produto, pra usar na Manutenção de Alertas.</p>
      </a>"""


def _montar_hub_html(sessao: dict) -> str:
    classe_conting, resumo_conting = _resumo_conting_hub()
    tem_dados_sensiveis = _tem_acesso_dados_sensiveis(sessao)
    cards_dados_sensiveis = _CARDS_DADOS_SENSIVEIS_HTML if tem_dados_sensiveis else ""
    pagina_dados_sensiveis = (
        '<div class="pagina-hub" data-pagina="2">\n'
        '      <div class="grade-hub">\n'
        + _CARD_CHECKLISTS_HTML
        + _CARD_PESQUISA_SATISFACAO_HTML
        + _CARD_NNU_ENCHANCED_HTML
        + cards_dados_sensiveis +
        '\n      </div>\n'
        '    </div>'
    )
    admin = bool(sessao.get("admin"))
    # Cada card com acesso restrito só entra no HTML se a pessoa logada
    # tiver a permissão correspondente - mesmo critério das rotas em
    # do_GET (ver _tem_acesso_* e sessao["admin"]). Quem não tem acesso
    # simplesmente não vê o card, em vez de ver e esbarrar num bloqueio.
    return (
        _HUB_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Escolha uma opção abaixo"))
        .replace("__USUARIO_HERO__", sessao.get("nome") or sessao["usuario"])
        .replace("__SAUDACAO_HERO__", _saudacao_bem_vindo(sessao.get("genero", "")))
        .replace("__LOGIN_HERO__", sessao["usuario"])
        .replace("__FOOTER__", _montar_footer())
        .replace("__CLASSE_CONTING__", classe_conting)
        .replace("__RESUMO_CONTING__", resumo_conting)
        .replace("__PAGINA_DADOS_SENSIVEIS__", pagina_dados_sensiveis)
        .replace("__CARD_INDICADORES_MOVIDESK__", _CARD_INDICADORES_MOVIDESK_HTML if admin else "")
        .replace("__CARD_AUTOMACAO_MOVIDESK__", _CARD_AUTOMACAO_MOVIDESK_HTML if admin else "")
        .replace("__CARD_RELATORIOS_SHEIN__", _CARD_RELATORIOS_SHEIN_HTML if _tem_acesso_relatorios_shein(sessao) else "")
        .replace("__CARD_DASH_FINANCEIRO__", _CARD_DASH_FINANCEIRO_HTML if _tem_acesso_dash_financeiro(sessao) else "")
        .replace("__CARD_MANUTENCAO_ALERTAS__", _CARD_MANUTENCAO_ALERTAS_HTML if _tem_acesso_manutencao_alertas(sessao) else "")
        .replace("__CARD_MANUTENCAO_REJEICOES__", _CARD_MANUTENCAO_REJEICOES_HTML if _tem_acesso_manutencao_rejeicoes(sessao) else "")
        .replace("__CARD_MANUTENCAO_RELATORIOS__", _CARD_MANUTENCAO_RELATORIOS_HTML if _tem_acesso_manutencao_relatorios(sessao) else "")
        .replace("__CARD_DASHBOARDS_CLIENTES__", _CARD_DASHBOARDS_CLIENTES_HTML if _tem_acesso_dashboards_clientes(sessao) else "")
        .replace("__CARD_MANUTENCAO_USUARIOS__", _CARD_MANUTENCAO_USUARIOS_HTML if _tem_acesso_manutencao_usuarios(sessao) else "")
        .replace("__CARD_HORAS_TRABALHADAS__", _CARD_HORAS_TRABALHADAS_HTML if admin else "")
        .replace("__CARD_LOGS__", _CARD_LOGS_HTML if admin else "")
    )


_USUARIOS_NEGADO_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Usuários - acesso restrito</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .aviso { max-width: 480px; margin: 60px auto; background: var(--bg-panel); backdrop-filter: blur(12px);
           -webkit-backdrop-filter: blur(12px); border: 1px solid var(--border-forte);
           border-radius: 16px; padding: 34px; text-align: center; }
  .aviso .icone { width: 56px; height: 56px; border-radius: 50%; background: rgba(241,76,76,.14);
                  display: flex; align-items: center; justify-content: center; margin: 0 auto 18px auto;
                  box-shadow: inset 0 0 0 1px rgba(241,76,76,.25); }
  .aviso .icone svg { width: 26px; height: 26px; stroke: var(--erro); }
  .aviso h2 { margin: 0 0 10px 0; font-size: 17px; }
  .aviso p { color: var(--fg-dim); font-size: 13px; line-height: 1.6; margin: 0 0 20px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="aviso">
      <div class="icone">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16h.01"/>
        </svg>
      </div>
      <h2>Acesso restrito</h2>
      <p>Para acessar esta página é preciso ter permissão de administrador.
         Fale com um administrador do painel se precisar de acesso.</p>
      <a class="btn-link" href="/">Voltar ao início</a>
    </div>
  </div>
  __FOOTER__
</body>
</html>
"""


def _montar_usuarios_negado_html(sessao: dict, contexto: str = "Usuários") -> str:
    return (
        _USUARIOS_NEGADO_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, contexto))
        .replace("__FOOTER__", _montar_footer())
    )


_USUARIOS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Usuários</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow-x: auto; max-width: 1120px; margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  .acoes-linha { display: flex; gap: 6px; }
  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; }
  .modal-fundo.aberto { display: flex; }
  .modal { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 28px 26px; width: 300px; box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal h3 { margin: 0 0 16px 0; font-size: 15px; color: var(--teal); }
  .modal label { display: block; font-size: 11px; color: var(--fg-dim); margin: 12px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal input { width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; }
  .modal select { width: 100%; }
  .modal input:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .modal .acoes-modal { display: flex; gap: 8px; margin-top: 20px; }
  .modal .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .modal p.aviso-exclusao { color: var(--fg-dim); font-size: 13px; line-height: 1.5; margin: 0 0 6px 0; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: 1120px; }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }

  .campo-checkbox { display: flex; align-items: center; gap: 9px; margin-top: 14px; }
  .campo-checkbox input[type="checkbox"] { width: auto; flex: 0 0 auto; padding: 0; }
  .campo-checkbox label { display: block; margin: 0; text-transform: none; letter-spacing: normal;
                           font-size: 13px; color: var(--fg); flex: 1; text-align: left; }
  .nota-admin-perm { font-size: 10px; color: var(--fg-dim); background: rgba(255,255,255,.06);
                      padding: 2px 8px; border-radius: 6px; white-space: nowrap; }
  .dica-campo { font-size: 11px; color: var(--fg-dim); margin-top: 14px; line-height: 1.5; }

  .badge-vinculo-ok { display: inline-block; padding: 3px 9px; border-radius: 6px; font-size: 11.5px;
                       background: rgba(78,201,176,.15); color: var(--ok); }
  .input-nome-usuario { width: 100%; min-width: 140px; padding: 6px 9px; border-radius: 6px;
                         border: 1px solid transparent; background: transparent; color: var(--fg);
                         font-size: 13px; font-family: inherit; transition: border-color .15s, background .15s; }
  .input-nome-usuario:hover:not(:disabled) { border-color: var(--border); background: rgba(255,255,255,.03); }
  .input-nome-usuario:focus { outline: none; border-color: var(--teal); background: rgba(0,0,0,.25); }
  .input-nome-usuario:disabled { color: var(--fg-dim); cursor: default; }
  .link-usuario-tabela { color: var(--teal); text-decoration: none; font-weight: 600; }
  .link-usuario-tabela:hover { text-decoration: underline; }
  .badge-vinculo-nao { display: inline-block; padding: 3px 9px; border-radius: 6px; font-size: 11.5px;
                        background: rgba(255,255,255,.06); color: var(--fg-dim); }

  .badge-status-usuario { display: inline-block; padding: 3px 10px; border-radius: 6px; font-size: 11.5px;
                           font-weight: 700; }
  .badge-ativo-usuario { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-inativo-usuario { background: rgba(241,76,76,.15); color: var(--erro); }
  .linha-usuario-desativado { opacity: .55; }
  .linha-usuario-desativado:hover { opacity: .85; }
  .btn-aviso { background: rgba(232,163,61,.15); border: 1px solid rgba(232,163,61,.4); color: #e8a33d; }
  .btn-aviso:hover { background: rgba(232,163,61,.25); }
  .btn-sucesso { background: rgba(78,201,176,.15); border: 1px solid rgba(78,201,176,.4); color: var(--ok); }
  .btn-sucesso:hover { background: rgba(78,201,176,.25); }

  .modal-largo-vinculo { background: var(--bg-panel-solid); border: 1px solid var(--border-forte);
                          border-radius: 14px; padding: 28px 30px; width: 100%; max-width: 520px;
                          max-height: 88vh; overflow-y: auto; box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal-largo-vinculo h3 { margin: 0 0 18px 0; font-size: 16px; color: var(--teal); }
  .modal-largo-vinculo label { display: block; font-size: 11px; color: var(--fg-dim); margin: 14px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal-largo-vinculo input, .modal-largo-vinculo select {
                 width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal-largo-vinculo input:focus, .modal-largo-vinculo select:focus {
                 outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .dica-campo-vinculo { font-size: 10.5px; color: var(--fg-dim); margin-top: 6px; line-height: 1.5; }
  .linha-dupla-vinculo { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
  .linha-tripla-vinculo { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0 14px; }
  .dias-semana-vinculo { display: flex; gap: 8px; flex-wrap: wrap; }
  .dia-check-vinculo { display: flex; align-items: center; gap: 5px; font-size: 12px; color: var(--fg-dim);
                        text-transform: none; letter-spacing: normal; background: rgba(255,255,255,.03);
                        border: 1px solid var(--border); border-radius: 8px; padding: 7px 10px; cursor: pointer; }
  .dia-check-vinculo input { width: auto; }
  .dia-check-vinculo:has(input:checked) { border-color: var(--teal); color: var(--fg); }
  .tabela-usuarios-rolagem { overflow-x: auto; border-radius: 10px; }
  .tabela-usuarios-rolagem table { white-space: nowrap; }

  .modal-editar-usuario-largura { max-width: 560px; }
  .divisor-secao-eu { height: 1px; background: linear-gradient(90deg, transparent, var(--border-forte), transparent);
                       margin: 22px 0; }
  .titulo-secao-eu { margin: 0 0 4px 0; font-size: 13px; color: var(--teal); text-transform: uppercase;
                      letter-spacing: .05em; font-weight: 700; }
  .info-status-eu { font-size: 12.5px; color: var(--fg-dim); margin: 8px 0 12px 0; }
  .modal-largo-vinculo button.btn-mini { width: auto; margin-top: 14px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Usuários cadastrados</h3>
      <button class="btn-accent" onclick="abrirModalNovo()">+ Novo usuário</button>
    </div>
    <div class="painel">
      <div class="tabela-usuarios-rolagem">
      <table>
        <thead><tr><th>Login</th><th>Nome</th><th>Papel</th><th>Status</th><th>Vínculo Movidesk</th><th></th></tr></thead>
        <tbody id="corpo-tabela"></tbody>
      </table>
      </div>
    </div>
  </div>

  <div class="modal-fundo" id="modal-novo">
    <div class="modal">
      <h3>Novo usuário</h3>
      <label>Login</label>
      <input type="text" id="novo-usuario" placeholder="login (sem espaços)">
      <label>Senha</label>
      <input type="password" id="novo_senha_criar" placeholder="mínimo 4 caracteres">
      <label>Papel</label>
      <select id="novo-papel">
        <option value="view">Visualização</option>
        <option value="admin">Administrador</option>
      </select>
      <div class="divisor-secao-eu"></div>
      <h4 class="titulo-secao-eu">Permissões</h4>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-manutencao">
        <label for="novo-pode-manutencao">Manutenção de Alertas em Banco</label>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-shein">
        <label for="novo-pode-shein">Relatórios Shein</label>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-dash">
        <label for="novo-pode-dash">Atualização Dash Financeiro</label>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-rejeicoes">
        <label for="novo-pode-rejeicoes">Manutenção Rejeições em Banco</label>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-relatorios">
        <label for="novo-pode-relatorios">Manutenção de Relatórios em Banco</label>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-string-conn">
        <label for="novo-pode-string-conn">Dados Sensíveis (String Connections + Criptografia)</label>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="novo-pode-manutencao-usuarios">
        <label for="novo-pode-manutencao-usuarios">Manutenção de Usuários (Beta) - cadastro/desativação em produção</label>
      </div>
      <div class="erro-modal" id="modal-novo-erro"></div>
      <div class="acoes-modal">
        <button class="btn-accent" onclick="criarUsuario()" style="flex:1">Criar</button>
        <button onclick="fecharModalNovo()" style="flex:1">Cancelar</button>
      </div>
    </div>
  </div>

  <div class="modal-fundo" id="modal-editar-usuario">
    <div class="modal-largo-vinculo modal-editar-usuario-largura">
      <h3 id="titulo-modal-editar-usuario">Editar usuário</h3>

      <label>Nome de exibição</label>
      <input type="text" id="eu-nome">

      <label>Papel</label>
      <select id="eu-papel">
        <option value="admin">Administrador</option>
        <option value="view">Visualização</option>
      </select>
      <label>Atribuição</label>
      <select id="eu-atribuicao">
        <option value="Suporte">Suporte</option>
        <option value="Monitoramento">Monitoramento</option>
      </select>
      <label>Gênero <span style="text-transform:none; font-weight:400;">(pra flexão de texto - "Bem-vindo/Bem-vinda")</span></label>
      <select id="eu-genero">
        <option value="">Não informado</option>
        <option value="M">Masculino</option>
        <option value="F">Feminino</option>
      </select>
      <div class="erro-modal" id="eu-erro-geral-topo"></div>
      <button class="btn-mini" onclick="salvarNomeEPapelModalEditar()">Salvar nome, papel, atribuição e gênero</button>

      <div class="divisor-secao-eu"></div>
      <h4 class="titulo-secao-eu">Status da conta</h4>
      <div class="info-status-eu" id="eu-status-info"></div>
      <div class="acoes-linha">
        <button class="btn-mini btn-aviso" id="eu-botao-desativar" onclick="statusModalEditar(false)">Desativar</button>
        <button class="btn-mini btn-sucesso" id="eu-botao-reativar" onclick="statusModalEditar(true)" style="display:none">Reativar</button>
      </div>
      <div class="erro-modal" id="eu-erro-status"></div>

      <div class="divisor-secao-eu"></div>
      <h4 class="titulo-secao-eu">Permissões</h4>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_manutencao_alertas">
        <label for="perm-pode_manutencao_alertas">Manutenção de Alertas em Banco</label>
        <span id="nota-admin-pode_manutencao_alertas" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_relatorios_shein">
        <label for="perm-pode_relatorios_shein">Relatórios Shein</label>
        <span id="nota-admin-pode_relatorios_shein" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_dash_financeiro">
        <label for="perm-pode_dash_financeiro">Atualização Dash Financeiro</label>
        <span id="nota-admin-pode_dash_financeiro" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_manutencao_rejeicoes">
        <label for="perm-pode_manutencao_rejeicoes">Manutenção Rejeições em Banco</label>
        <span id="nota-admin-pode_manutencao_rejeicoes" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_manutencao_relatorios">
        <label for="perm-pode_manutencao_relatorios">Manutenção de Relatórios em Banco</label>
        <span id="nota-admin-pode_manutencao_relatorios" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_dados_sensiveis">
        <label for="perm-pode_dados_sensiveis">Dados Sensíveis (String Connections + Criptografia)</label>
        <span id="nota-admin-pode_dados_sensiveis" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="campo-checkbox">
        <input type="checkbox" id="perm-pode_manutencao_usuarios">
        <label for="perm-pode_manutencao_usuarios">Manutenção de Usuários (Beta) - cadastro/desativação em produção</label>
        <span id="nota-admin-pode_manutencao_usuarios" class="nota-admin-perm" style="display:none">Sempre (admin)</span>
      </div>
      <div class="dica-campo">
        Dados Sensíveis e Manutenção de Usuários não são liberados automaticamente pra administradores - precisa marcar aqui, mesmo pra quem já é admin.
      </div>
      <div class="erro-modal" id="erro-permissoes"></div>
      <button class="btn-mini" onclick="salvarPermissoes()">Salvar permissões</button>

      <div class="divisor-secao-eu"></div>
      <h4 class="titulo-secao-eu">Horas / Vínculo Movidesk</h4>
      <label>Vincular a um usuário da tabela "usuarios" (banco movidesk)</label>
      <select id="vinculo-select-usuario" onchange="aoTrocarUsuarioVinculado()">
        <option value="">Selecione ou pesquise...</option>
      </select>
      <div class="dica-campo-vinculo">
        Ao vincular, os dados de horas trabalhadas (escala, horário, dias) ficam
        associados a esse login do PDA. Sem vínculo, a pessoa não tem meta de
        horas calculada corretamente.
      </div>

      <div id="campos-dados-movidesk" style="display:none">
        <div class="linha-dupla-vinculo">
          <div>
            <label>Cargo</label>
            <input type="text" id="vinculo-cargo">
          </div>
          <div>
            <label>E-mail</label>
            <input type="email" id="vinculo-email">
          </div>
        </div>

        <div class="linha-tripla-vinculo">
          <div>
            <label>Escala</label>
            <select id="vinculo-escala">
              <option value="">Sem escala definida</option>
              <option value="5x2">5x2</option>
              <option value="6x1">6x1</option>
              <option value="12x36">12x36</option>
              <option value="ESTAGIO">Estágio</option>
              <option value="ESCALA_ARA">Escala ARA</option>
            </select>
          </div>
          <div>
            <label>Hora início</label>
            <input type="time" id="vinculo-horainicio">
          </div>
          <div>
            <label>Hora fim</label>
            <input type="time" id="vinculo-horafim">
          </div>
        </div>

        <label>Dias trabalhados</label>
        <div class="dias-semana-vinculo">
          <label class="dia-check-vinculo"><input type="checkbox" value="Monday"> Seg</label>
          <label class="dia-check-vinculo"><input type="checkbox" value="Tuesday"> Ter</label>
          <label class="dia-check-vinculo"><input type="checkbox" value="Wednesday"> Qua</label>
          <label class="dia-check-vinculo"><input type="checkbox" value="Thursday"> Qui</label>
          <label class="dia-check-vinculo"><input type="checkbox" value="Friday"> Sex</label>
          <label class="dia-check-vinculo"><input type="checkbox" value="Saturday"> Sáb</label>
          <label class="dia-check-vinculo"><input type="checkbox" value="Sunday"> Dom</label>
        </div>
      </div>
      <div class="erro-modal" id="erro-vinculo-movidesk"></div>
      <button class="btn-mini" onclick="salvarVinculoMovidesk()">Salvar vínculo</button>

      <div class="divisor-secao-eu"></div>
      <h4 class="titulo-secao-eu">Alterar senha</h4>
      <label>Nova senha</label>
      __CAMPO_MODAL_NOVA_SENHA__
      <label>Confirmar nova senha</label>
      __CAMPO_MODAL_CONFIRMA_SENHA__
      <div class="erro-modal" id="modal-erro"></div>
      <button class="btn-mini" onclick="salvarSenha()">Salvar senha</button>

      <div class="divisor-secao-eu"></div>
      <div class="acoes-modal">
        <button onclick="fecharModalEditarUsuario()" style="flex:1">Fechar</button>
        <button class="btn-perigo" onclick="excluirModalEditar()" style="flex:1">Excluir usuário</button>
      </div>
      <div class="erro-modal" id="eu-erro-geral"></div>
    </div>
  </div>


  <div class="toast" id="toast"></div>

<script>__JS_ALTERNAR_SENHA__</script>
<script>
let usuarioModalAtual = null;
let usuarioParaExcluir = null;
let usuarioParaStatus = null;
let novoStatusPendente = null;

async function statusModalEditar(ativar) {
  const usuario = usuarioEmEdicaoModal;
  const mensagem = ativar
    ? `Reativar ${usuario}? A pessoa volta a conseguir logar normalmente, e os apontamentos dela voltam a ser contados em Horas Trabalhadas.`
    : `Desativar ${usuario}? A pessoa não vai mais conseguir logar (qualquer sessão aberta é encerrada agora), e - se estiver vinculada a alguém da tabela usuarios - os apontamentos dela deixam de ser contados em Horas Trabalhadas.`;
  if (!confirm(mensagem)) return;

  const resp = await fetch('/api/usuarios/alterar-status', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario) + '&ativo=' + (ativar ? 'true' : 'false'),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('eu-erro-status').innerText = dados.erro || 'Não foi possível alterar o status.';
    return;
  }
  document.getElementById('eu-erro-status').innerText = '';
  document.getElementById('eu-status-info').innerText = ativar ? 'Conta ativa.' : 'Conta desativada.';
  document.getElementById('eu-botao-desativar').style.display = ativar ? 'inline-flex' : 'none';
  document.getElementById('eu-botao-reativar').style.display = ativar ? 'none' : 'inline-flex';
  mostrarToast(usuario + (ativar ? ' reativado.' : ' desativado.'));
  carregarUsuarios();
}

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

let usuariosCarregados = [];
let usuariosMovideskCarregados = [];
let usuarioEmEdicaoVinculo = null;
let usuarioEmEdicaoModal = null;

function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function abrirModalEditarUsuario(usuario) {
  const u = usuariosCarregados.find(x => x.usuario === usuario);
  if (!u) return;
  usuarioEmEdicaoModal = usuario;
  document.getElementById('titulo-modal-editar-usuario').innerText = 'Editar usuário — ' + usuario;
  document.getElementById('eu-erro-geral').innerText = '';

  // Geral
  document.getElementById('eu-nome').value = u.nome || u.usuario;
  document.getElementById('eu-papel').value = u.admin ? 'admin' : 'view';
  document.getElementById('eu-atribuicao').value = u.atribuicao || 'Suporte';
  document.getElementById('eu-genero').value = u.genero || '';

  // Status
  const estaAtivo = u.ativo !== false;
  document.getElementById('eu-status-info').innerText = estaAtivo ? 'Conta ativa.' : 'Conta desativada.';
  document.getElementById('eu-botao-desativar').style.display = estaAtivo ? 'inline-flex' : 'none';
  document.getElementById('eu-botao-reativar').style.display = estaAtivo ? 'none' : 'inline-flex';
  document.getElementById('eu-erro-status').innerText = '';

  // Permissões e Vínculo Movidesk (reaproveita a mesma logica de sempre)
  popularSecaoPermissoes(u);
  popularSecaoVinculoMovidesk(u);

  // Senha
  popularSecaoSenha(usuario);

  document.getElementById('modal-editar-usuario').classList.add('aberto');
}

function fecharModalEditarUsuario() {
  document.getElementById('modal-editar-usuario').classList.remove('aberto');
  carregarUsuarios();
}

async function salvarNomeEPapelModalEditar() {
  const nomeInput = document.getElementById('eu-nome');
  await salvarNomeUsuario(usuarioEmEdicaoModal, nomeInput);
  await mudarPapel(usuarioEmEdicaoModal, document.getElementById('eu-papel').value);
  await fetch('/api/usuarios/alterar-atribuicao', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuarioEmEdicaoModal) + '&atribuicao=' + encodeURIComponent(document.getElementById('eu-atribuicao').value),
  });
  await fetch('/api/usuarios/alterar-genero', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuarioEmEdicaoModal) + '&genero=' + encodeURIComponent(document.getElementById('eu-genero').value),
  });
}

async function carregarUsuariosMovidesk() {
  try {
    const resp = await fetch('/api/usuarios-movidesk');
    const dados = await resp.json();
    if (!dados.ok) {
      console.warn('Não foi possível carregar usuarios-movidesk:', dados.erro);
      return;
    }
    usuariosMovideskCarregados = dados.registros;
  } catch (e) {
    console.warn('Erro ao carregar usuarios-movidesk:', e);
  }
}

function popularSecaoVinculoMovidesk(u) {
  usuarioEmEdicaoVinculo = u.usuario;
  document.getElementById('erro-vinculo-movidesk').innerText = '';
  document.getElementById('campos-dados-movidesk').style.display = 'none';

  const select = document.getElementById('vinculo-select-usuario');
  select.innerHTML = '<option value="">Selecione ou pesquise...</option>' +
    usuariosMovideskCarregados.map(m =>
      `<option value="${m.id}">${m.nome}${m.cargo ? ' · ' + m.cargo : ''}</option>`
    ).join('');
  select.value = u.usuario_movidesk_id || '';

  if (u.usuario_movidesk_id) {
    carregarDadosUsuarioMovidesk(u.usuario_movidesk_id);
  }
}

function fecharModalVinculoMovidesk() {
  carregarUsuarios();  // so atualiza os dados por baixo - o modal consolidado continua aberto
}

function aoTrocarUsuarioVinculado() {
  const id = document.getElementById('vinculo-select-usuario').value;
  if (id) {
    carregarDadosUsuarioMovidesk(id);
  } else {
    document.getElementById('campos-dados-movidesk').style.display = 'none';
  }
}

async function carregarDadosUsuarioMovidesk(id) {
  const erroEl = document.getElementById('erro-vinculo-movidesk');
  erroEl.innerText = '';
  try {
    const resp = await fetch('/api/usuarios-movidesk/' + encodeURIComponent(id));
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar os dados desse usuário.';
      document.getElementById('campos-dados-movidesk').style.display = 'none';
      return;
    }
    const r = dados.registro;
    document.getElementById('vinculo-cargo').value = r.cargo || '';
    document.getElementById('vinculo-email').value = r.email || '';
    document.getElementById('vinculo-escala').value = r.escala || '';
    document.getElementById('vinculo-horainicio').value = r.horainicio || '';
    document.getElementById('vinculo-horafim').value = r.horafim || '';

    const diasMarcados = (r.diastrabalhados || '').split(',').map(d => d.trim()).filter(Boolean);
    document.querySelectorAll('.dia-check-vinculo input').forEach(chk => {
      chk.checked = diasMarcados.includes(chk.value);
    });

    document.getElementById('campos-dados-movidesk').style.display = 'block';
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
  }
}

async function salvarVinculoMovidesk() {
  const erroEl = document.getElementById('erro-vinculo-movidesk');
  erroEl.innerText = '';
  const usuario = usuarioEmEdicaoVinculo;
  const idSelecionado = document.getElementById('vinculo-select-usuario').value;

  try {
    // 1) salva o vinculo (ou desvinculo) do login do PDA
    const respVinculo = await fetch('/api/usuarios/vincular-movidesk', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&id_movidesk=' + encodeURIComponent(idSelecionado),
    });
    const dadosVinculo = await respVinculo.json();
    if (!dadosVinculo.ok) {
      erroEl.innerText = dadosVinculo.erro || 'Não foi possível salvar o vínculo.';
      return;
    }

    // 2) se tiver um usuario selecionado, salva os dados dele tambem (cargo/email/escala/horario/dias)
    if (idSelecionado) {
      const diasMarcados = Array.from(document.querySelectorAll('.dia-check-vinculo input:checked')).map(c => c.value);
      const respDados = await fetch('/api/usuarios-movidesk/atualizar', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'id=' + encodeURIComponent(idSelecionado) +
              '&cargo=' + encodeURIComponent(document.getElementById('vinculo-cargo').value) +
              '&email=' + encodeURIComponent(document.getElementById('vinculo-email').value) +
              '&escala=' + encodeURIComponent(document.getElementById('vinculo-escala').value) +
              '&horainicio=' + encodeURIComponent(document.getElementById('vinculo-horainicio').value) +
              '&horafim=' + encodeURIComponent(document.getElementById('vinculo-horafim').value) +
              '&diasTrabalhados=' + encodeURIComponent(diasMarcados.join(',')),
      });
      const dadosSalvar = await respDados.json();
      if (!dadosSalvar.ok) {
        erroEl.innerText = dadosSalvar.erro || 'Vínculo salvo, mas não foi possível salvar os dados de horas.';
        return;
      }
    }

    mostrarToast('Vínculo e dados de ' + usuario + ' atualizados.');
    fecharModalVinculoMovidesk();
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  }
}


async function carregarUsuarios() {
  const resp = await fetch('/api/usuarios');
  if (resp.status === 401 || resp.status === 403) { window.location.href = '/'; return; }
  const dados = await resp.json();
  usuariosCarregados = dados.usuarios;
  const corpo = document.getElementById('corpo-tabela');
  corpo.innerHTML = '';
  for (const u of dados.usuarios) {
    const tr = document.createElement('tr');
    const nomeVinculado = u.usuario_movidesk_id
      ? (usuariosMovideskCarregados.find(m => m.id === u.usuario_movidesk_id)?.nome || 'ID ' + u.usuario_movidesk_id)
      : null;
    const estaAtivo = u.ativo !== false;
    if (!estaAtivo) tr.classList.add('linha-usuario-desativado');
    tr.innerHTML = `
      <td><a class="link-usuario-tabela" href="/perfil/${encodeURIComponent(u.usuario)}">${u.usuario}</a></td>
      <td>${escaparHtml(u.nome || u.usuario)}</td>
      <td>${u.admin ? 'Administrador' : 'Visualização'}</td>
      <td>
        ${estaAtivo
          ? '<span class="badge-status-usuario badge-ativo-usuario">Ativo</span>'
          : '<span class="badge-status-usuario badge-inativo-usuario">Desativado</span>'}
      </td>
      <td>
        ${nomeVinculado
          ? `<span class="badge-vinculo-ok" title="Vinculado a: ${nomeVinculado}">✓ ${nomeVinculado}</span>`
          : '<span class="badge-vinculo-nao">Não vinculado</span>'}
      </td>
      <td>
        <button class="btn-mini" onclick="abrirModalEditarUsuario('${u.usuario}')">Editar usuário</button>
      </td>
    `;
    corpo.appendChild(tr);
  }
}

const ENDPOINTS_PERMISSOES = {
  pode_manutencao_alertas: '/api/usuarios/permissao-manutencao',
  pode_relatorios_shein: '/api/usuarios/permissao-shein',
  pode_dash_financeiro: '/api/usuarios/permissao-dash-financeiro',
  pode_manutencao_rejeicoes: '/api/usuarios/permissao-manutencao-rejeicoes',
  pode_manutencao_relatorios: '/api/usuarios/permissao-manutencao-relatorios',
  pode_dados_sensiveis: '/api/usuarios/permissao-string-connections',
  pode_manutencao_usuarios: '/api/usuarios/permissao-manutencao-usuarios',
};

// Permissões que NÃO são automáticas pra admin (precisam ser marcadas à
// parte, mesmo pra quem já é administrador) - as outras, se a pessoa for
// admin, ficam travadas marcadas (sempre tem acesso de qualquer forma).
const PERMISSOES_NAO_AUTOMATICAS_PARA_ADMIN = new Set(['pode_dados_sensiveis', 'pode_manutencao_usuarios']);

let usuarioEmEdicaoPermissoes = null;

function popularSecaoPermissoes(u) {
  usuarioEmEdicaoPermissoes = u.usuario;
  document.getElementById('erro-permissoes').innerText = '';

  for (const chave of Object.keys(ENDPOINTS_PERMISSOES)) {
    const checkbox = document.getElementById('perm-' + chave);
    checkbox.checked = !!u[chave];
    const travarPorSerAdmin = u.admin && !PERMISSOES_NAO_AUTOMATICAS_PARA_ADMIN.has(chave);
    checkbox.disabled = travarPorSerAdmin;
    if (travarPorSerAdmin) checkbox.checked = true;
    const notaAdmin = document.getElementById('nota-admin-' + chave);
    notaAdmin.style.display = travarPorSerAdmin ? 'inline' : 'none';
  }
}

function fecharModalPermissoes() {
  carregarUsuarios();  // so atualiza os dados por baixo - o modal consolidado continua aberto
}

async function salvarPermissoes() {
  const erroEl = document.getElementById('erro-permissoes');
  erroEl.innerText = '';
  const usuario = usuarioEmEdicaoPermissoes;

  try {
    await Promise.all(Object.entries(ENDPOINTS_PERMISSOES).map(([chave, url]) => {
      const checkbox = document.getElementById('perm-' + chave);
      if (checkbox.disabled) return Promise.resolve(); // travado por ser admin - nada a enviar
      return fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'usuario=' + encodeURIComponent(usuario) + '&permitido=' + (checkbox.checked ? 'true' : 'false'),
      }).then(r => r.json());
    }));
    mostrarToast('Permissões de ' + usuario + ' atualizadas.');
    fecharModalPermissoes();
    carregarUsuarios();
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  }
}

async function mudarPapel(usuario, valor) {
  const resp = await fetch('/api/usuarios/admin', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario) + '&admin=' + (valor === 'admin' ? 'true' : 'false'),
  });
  const dados = await resp.json();
  if (!dados.ok) { mostrarToast(dados.erro || 'Não foi possível alterar.'); }
  carregarUsuarios();
}

async function salvarNomeUsuario(usuario, inputEl) {
  const novoNome = inputEl.value.trim();
  const nomeOriginal = inputEl.defaultValue;
  if (novoNome === nomeOriginal) return;  // nao mudou nada, nao faz requisicao a toa
  if (!novoNome) {
    inputEl.value = nomeOriginal;
    mostrarToast('O nome não pode ficar em branco.');
    return;
  }
  const resp = await fetch('/api/usuarios/alterar-nome', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario) + '&nome=' + encodeURIComponent(novoNome),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    inputEl.value = nomeOriginal;
    mostrarToast(dados.erro || 'Não foi possível alterar o nome.');
    return;
  }
  inputEl.defaultValue = novoNome;
  mostrarToast('Nome de ' + usuario + ' atualizado.');
}

function popularSecaoSenha(usuario) {
  usuarioModalAtual = usuario;
  document.getElementById('nova_senha').value = '';
  document.getElementById('confirma_senha').value = '';
  document.getElementById('modal-erro').innerText = '';
}

function fecharModal() {
  // senha - so avisa (o modal consolidado continua aberto pra outras edicoes)
}

async function salvarSenha() {
  const nova = document.getElementById('nova_senha').value;
  const confirma = document.getElementById('confirma_senha').value;
  const erroEl = document.getElementById('modal-erro');
  if (!nova || nova.length < 4) { erroEl.innerText = 'A senha precisa ter ao menos 4 caracteres.'; return; }
  if (nova !== confirma) { erroEl.innerText = 'As senhas não coincidem.'; return; }

  const resp = await fetch('/api/usuarios/senha', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuarioModalAtual) + '&nova_senha=' + encodeURIComponent(nova),
  });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModal();
    mostrarToast('Senha de ' + usuarioModalAtual + ' atualizada.');
  } else {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
  }
}

function abrirModalNovo() {
  document.getElementById('novo-usuario').value = '';
  document.getElementById('novo_senha_criar').value = '';
  document.getElementById('novo-papel').value = 'view';
  document.getElementById('novo-pode-manutencao').checked = false;
  document.getElementById('novo-pode-shein').checked = false;
  document.getElementById('novo-pode-dash').checked = false;
  document.getElementById('novo-pode-rejeicoes').checked = false;
  document.getElementById('novo-pode-relatorios').checked = false;
  document.getElementById('novo-pode-string-conn').checked = false;
  document.getElementById('novo-pode-manutencao-usuarios').checked = false;
  document.getElementById('modal-novo-erro').innerText = '';
  document.getElementById('modal-novo').classList.add('aberto');
}

function fecharModalNovo() {
  document.getElementById('modal-novo').classList.remove('aberto');
}

async function criarUsuario() {
  const usuario = document.getElementById('novo-usuario').value.trim();
  const senha = document.getElementById('novo_senha_criar').value;
  const papel = document.getElementById('novo-papel').value;
  const podeManutencao = document.getElementById('novo-pode-manutencao').checked;
  const podeShein = document.getElementById('novo-pode-shein').checked;
  const podeDash = document.getElementById('novo-pode-dash').checked;
  const podeRejeicoes = document.getElementById('novo-pode-rejeicoes').checked;
  const podeRelatorios = document.getElementById('novo-pode-relatorios').checked;
  const podeStringConn = document.getElementById('novo-pode-string-conn').checked;
  const podeManutencaoUsuarios = document.getElementById('novo-pode-manutencao-usuarios').checked;
  const erroEl = document.getElementById('modal-novo-erro');
  if (!usuario) { erroEl.innerText = 'Informe um nome de usuário.'; return; }
  if (!senha || senha.length < 4) { erroEl.innerText = 'A senha precisa ter ao menos 4 caracteres.'; return; }

  const resp = await fetch('/api/usuarios/criar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario) + '&senha=' + encodeURIComponent(senha) +
          '&admin=' + (papel === 'admin' ? 'true' : 'false') +
          '&pode_manutencao_alertas=' + (podeManutencao ? 'true' : 'false') +
          '&pode_relatorios_shein=' + (podeShein ? 'true' : 'false') +
          '&pode_dash_financeiro=' + (podeDash ? 'true' : 'false') +
          '&pode_manutencao_rejeicoes=' + (podeRejeicoes ? 'true' : 'false') +
          '&pode_manutencao_relatorios=' + (podeRelatorios ? 'true' : 'false') +
          '&pode_dados_sensiveis=' + (podeStringConn ? 'true' : 'false') +
          '&pode_manutencao_usuarios=' + (podeManutencaoUsuarios ? 'true' : 'false'),
  });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModalNovo();
    mostrarToast('Usuário ' + usuario + ' criado.');
    carregarUsuarios();
  } else {
    erroEl.innerText = dados.erro || 'Não foi possível criar.';
  }
}

async function excluirModalEditar() {
  const usuario = usuarioEmEdicaoModal;
  if (!confirm(`Tem certeza que quer excluir ${usuario}? Essa ação não pode ser desfeita.`)) return;

  const resp = await fetch('/api/usuarios/deletar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario),
  });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModalEditarUsuario();
    mostrarToast('Usuário ' + usuario + ' excluído.');
  } else {
    document.getElementById('eu-erro-geral').innerText = dados.erro || 'Não foi possível excluir.';
  }
}

(async function () {
  await carregarUsuariosMovidesk();
  carregarUsuarios();
})();
</script>
__FOOTER__
</body>
</html>
"""


def _montar_usuarios_html(sessao: dict) -> str:
    return (
        _USUARIOS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Usuários"))
        .replace("__CAMPO_MODAL_NOVA_SENHA__", _campo_senha_html("nova_senha", "new-password"))
        .replace("__CAMPO_MODAL_CONFIRMA_SENHA__", _campo_senha_html("confirma_senha", "new-password"))
        .replace("__CAMPO_MODAL_NOVA_SENHA_CRIAR__", _campo_senha_html("novo_senha_criar", "new-password"))
        .replace("__JS_ALTERNAR_SENHA__", _JS_ALTERNAR_SENHA)
        .replace("__FOOTER__", _montar_footer())
    )


_STRING_CONNECTIONS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>String Connections</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: 900px; margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  td.conexao-truncada { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                         color: var(--fg-dim); font-family: Consolas, monospace; font-size: 11.5px; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  .btn-perigo { color: var(--erro); border-color: rgba(241,76,76,.4); }
  .acoes-linha { display: flex; gap: 6px; }
  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; }
  .modal-fundo.aberto { display: flex; }
  .modal { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 28px 26px; width: 380px; box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal h3 { margin: 0 0 16px 0; font-size: 15px; color: var(--teal); }
  .modal label { display: block; font-size: 11px; color: var(--fg-dim); margin: 12px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal input, .modal textarea { width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal textarea { font-family: Consolas, monospace; font-size: 12px; min-height: 70px; resize: vertical; }
  .modal input:focus, .modal textarea:focus { outline: none; border-color: var(--teal);
                 box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .modal .acoes-modal { display: flex; gap: 8px; margin-top: 20px; }
  .modal .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .modal p.aviso-exclusao { color: var(--fg-dim); font-size: 13px; line-height: 1.5; margin: 0 0 6px 0; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: 900px; }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .sub-secao { color: var(--fg-dim); font-size: 12.5px; max-width: 900px; margin: 0 auto 16px auto; line-height: 1.5; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">String Connections</h3>
      <button class="btn-accent" onclick="abrirModalNovaConexao()">+ Nova conexão</button>
    </div>
    <div class="sub-secao">
      Strings de conexão reutilizáveis por cliente e produto (ex.: Vivo · NFCom, Nissei · NFe).
      Ficam disponíveis pra escolher na hora de criar ou editar um alerta em
      "Manutenção de Alertas em Banco", sem precisar digitar a conexão de novo toda vez.
    </div>
    <div class="painel">
      <table>
        <thead><tr><th>Cliente</th><th>Produto</th><th>Conexão</th><th></th></tr></thead>
        <tbody id="corpo-tabela-conexoes">
          <tr><td colspan="4" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-nova-conexao">
    <div class="modal">
      <h3 id="titulo-modal-conexao">Nova String Connection</h3>
      <label>Cliente</label>
      <input type="text" id="conexao-cliente" placeholder="Ex.: Vivo">
      <label>Produto</label>
      <input type="text" id="conexao-produto" placeholder="Ex.: NFCom">
      <label>String de conexão</label>
      <textarea id="conexao-valor" placeholder="Servidor, banco, usuário, senha..."></textarea>
      <div class="erro-modal" id="modal-conexao-erro"></div>
      <div class="acoes-modal">
        <button class="btn-secundario" onclick="fecharModalConexao()">Cancelar</button>
        <button class="btn-accent" id="botao-salvar-conexao" onclick="salvarConexao()">Criar</button>
      </div>
    </div>
  </div>

  <div class="modal-fundo" id="modal-excluir-conexao">
    <div class="modal">
      <h3>Excluir String Connection</h3>
      <p class="aviso-exclusao">
        Tem certeza que quer excluir a conexão de <strong id="nome-conexao-excluir"></strong>?
        Alertas que já usam essa conexão continuam funcionando (a string fica salva no alerta),
        só não vai mais aparecer como opção pronta pra novos alertas.
      </p>
      <div class="erro-modal" id="modal-excluir-conexao-erro"></div>
      <div class="acoes-modal">
        <button class="btn-secundario" onclick="fecharModalExcluirConexao()">Cancelar</button>
        <button class="btn-accent btn-perigo" onclick="confirmarExcluirConexao()">Excluir</button>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
let idEmEdicaoConexao = null;
let idParaExcluirConexao = null;

async function carregarStringConnections() {
  const resp = await fetch('/api/string-connections');
  if (resp.status === 401) { window.location.href = '/login'; return; }
  if (resp.status === 403) { window.location.href = '/'; return; }
  const dados = await resp.json();
  const corpo = document.getElementById('corpo-tabela-conexoes');
  if (!dados.ok) {
    corpo.innerHTML = '<tr><td colspan="4" style="color:var(--fg-dim)">Não foi possível carregar.</td></tr>';
    return;
  }
  if (dados.conexoes.length === 0) {
    corpo.innerHTML = '<tr><td colspan="4" style="color:var(--fg-dim)">Nenhuma String Connection cadastrada ainda.</td></tr>';
    return;
  }
  corpo.innerHTML = dados.conexoes.map(c => `
    <tr>
      <td>${c.cliente}</td>
      <td>${c.produto}</td>
      <td class="conexao-truncada" title="${c.conexao.replace(/"/g, '&quot;')}">${c.conexao}</td>
      <td>
        <div class="acoes-linha">
          <button class="btn-mini" onclick='abrirModalEditarConexao(${JSON.stringify(c)})'>Editar</button>
          <button class="btn-mini btn-perigo" onclick="abrirModalExcluirConexao('${c.id}', '${c.cliente} · ${c.produto}')">Excluir</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function abrirModalNovaConexao() {
  idEmEdicaoConexao = null;
  document.getElementById('titulo-modal-conexao').innerText = 'Nova String Connection';
  document.getElementById('botao-salvar-conexao').innerText = 'Criar';
  document.getElementById('conexao-cliente').value = '';
  document.getElementById('conexao-produto').value = '';
  document.getElementById('conexao-valor').value = '';
  document.getElementById('modal-conexao-erro').innerText = '';
  document.getElementById('modal-nova-conexao').classList.add('aberto');
}

function abrirModalEditarConexao(c) {
  idEmEdicaoConexao = c.id;
  document.getElementById('titulo-modal-conexao').innerText = 'Editar String Connection';
  document.getElementById('botao-salvar-conexao').innerText = 'Salvar';
  document.getElementById('conexao-cliente').value = c.cliente;
  document.getElementById('conexao-produto').value = c.produto;
  document.getElementById('conexao-valor').value = c.conexao;
  document.getElementById('modal-conexao-erro').innerText = '';
  document.getElementById('modal-nova-conexao').classList.add('aberto');
}

function fecharModalConexao() {
  document.getElementById('modal-nova-conexao').classList.remove('aberto');
}

async function salvarConexao() {
  const cliente = document.getElementById('conexao-cliente').value.trim();
  const produto = document.getElementById('conexao-produto').value.trim();
  const conexao = document.getElementById('conexao-valor').value.trim();
  const erroEl = document.getElementById('modal-conexao-erro');
  if (!cliente || !produto || !conexao) {
    erroEl.innerText = 'Preencha cliente, produto e a string de conexão.';
    return;
  }
  const corpo = 'cliente=' + encodeURIComponent(cliente) + '&produto=' + encodeURIComponent(produto) +
                '&conexao=' + encodeURIComponent(conexao) +
                (idEmEdicaoConexao ? '&id=' + encodeURIComponent(idEmEdicaoConexao) : '');
  const url = idEmEdicaoConexao ? '/api/string-connections/atualizar' : '/api/string-connections/criar';
  const resp = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: corpo });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModalConexao();
    mostrarToast('String Connection salva.');
    carregarStringConnections();
  } else {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
  }
}

function abrirModalExcluirConexao(id, nome) {
  idParaExcluirConexao = id;
  document.getElementById('nome-conexao-excluir').innerText = nome;
  document.getElementById('modal-excluir-conexao-erro').innerText = '';
  document.getElementById('modal-excluir-conexao').classList.add('aberto');
}

function fecharModalExcluirConexao() {
  document.getElementById('modal-excluir-conexao').classList.remove('aberto');
}

async function confirmarExcluirConexao() {
  const resp = await fetch('/api/string-connections/deletar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(idParaExcluirConexao),
  });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModalExcluirConexao();
    mostrarToast('String Connection excluída.');
    carregarStringConnections();
  } else {
    document.getElementById('modal-excluir-conexao-erro').innerText = dados.erro || 'Não foi possível excluir.';
  }
}

carregarStringConnections();
</script>
</body>
</html>
"""


def _montar_string_connections_html(sessao: dict) -> str:
    return (
        _STRING_CONNECTIONS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "String Connections"))
        .replace("__FOOTER__", _montar_footer())
    )


_CONFIG_SEGURO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Criptografia de Dados Sensíveis</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-cs { max-width: 900px; margin: 0 auto 20px auto; }
  .cabecalho-cs h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-cs .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; }

  .painel-cs { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 900px; margin: 0 auto 20px auto; }
  .painel-cs h2 { margin: 0 0 6px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .painel-cs .sub-painel { color: var(--fg-dim); font-size: 12px; margin-bottom: 16px; line-height: 1.5; }

  .linha-chave-cs { display: flex; align-items: center; justify-content: space-between; gap: 10px;
                     padding: 10px 0; border-bottom: 1px solid var(--border); }
  .linha-chave-cs:last-child { border-bottom: none; }
  .linha-chave-cs code { font-size: 12.5px; color: var(--teal); }
  .vazio-cs { color: var(--fg-dim); font-size: 12.5px; padding: 6px 0; }

  .grade-form-cs { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
  .grade-form-cs .campo-largo { grid-column: 1 / -1; }
  .dica-cs { color: var(--fg-dim); font-size: 11.5px; margin-top: -8px; margin-bottom: 14px; line-height: 1.5; }
  .erro-cs { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 6px 0; }
  .sucesso-cs { color: var(--ok); font-size: 12.5px; min-height: 16px; margin: 6px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-cs">
      <h1>Criptografia de Dados Sensíveis</h1>
      <div class="sub">
        Credenciais sensíveis (senhas de banco, tokens) cifradas com Fernet
        num arquivo só (config.dat), em vez de espalhadas em texto puro
        pelos .env. Ver o manual (CRIPTOGRAFIA.md) pra entender o que isso
        protege de verdade e como migrar o resto aos poucos.
      </div>
    </div>

    <div class="painel-cs">
      <h2>Chaves já migradas</h2>
      <div class="sub-painel">Só os nomes aparecem aqui - os valores nunca são exibidos de volta pela interface, nem pra admin.</div>
      <div id="lista-chaves-cs"><div class="vazio-cs">Carregando...</div></div>
    </div>

    <div class="painel-cs">
      <h2>Adicionar / atualizar uma chave</h2>
      <div class="sub-painel">Sobrescreve se a chave já existir.</div>
      <div class="grade-form-cs">
        <div>
          <label>Chave (formato origem::campo)</label>
          <input type="text" id="cs-chave" placeholder="ex.: saas::db_password">
        </div>
        <div>
          <label>Valor</label>
          <input type="password" id="cs-valor" placeholder="valor a cifrar" autocomplete="off">
        </div>
      </div>
      <div class="dica-cs">
        "origem" identifica de qual .env esse valor vem (ex.: "saas",
        "sharepoint", "nissei-cte" - use o nome do arquivo .env.&lt;origem&gt;
        sem o ".env." na frente). "campo" é o nome original da variável
        nesse arquivo (ex.: "db_password", "SHAREPOINT_PASSWORD").
      </div>
      <div class="erro-cs" id="cs-erro"></div>
      <div class="sucesso-cs" id="cs-sucesso"></div>
      <button class="btn-accent" onclick="salvarChaveConfigSeguro()">Salvar cifrado</button>
    </div>
  </div>

  __FOOTER__

<script>
async function carregarChavesConfigSeguro() {
  const el = document.getElementById('lista-chaves-cs');
  try {
    const resp = await fetch('/api/config-seguro');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      el.innerHTML = '<div class="vazio-cs">Não foi possível carregar.</div>';
      return;
    }
    if (dados.chaves.length === 0) {
      el.innerHTML = '<div class="vazio-cs">Nenhuma chave migrada ainda.</div>';
      return;
    }
    el.innerHTML = dados.chaves.map(c => `
      <div class="linha-chave-cs">
        <code>${c}</code>
        <button class="btn-mini btn-perigo" onclick="removerChaveConfigSeguro('${c}')">Remover</button>
      </div>
    `).join('');
  } catch (e) {
    el.innerHTML = '<div class="vazio-cs">Erro ao carregar: ' + e + '</div>';
  }
}

async function salvarChaveConfigSeguro() {
  const chave = document.getElementById('cs-chave').value.trim();
  const valor = document.getElementById('cs-valor').value;
  const erroEl = document.getElementById('cs-erro');
  const sucessoEl = document.getElementById('cs-sucesso');
  erroEl.innerText = '';
  sucessoEl.innerText = '';

  const resp = await fetch('/api/config-seguro/definir', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'chave=' + encodeURIComponent(chave) + '&valor=' + encodeURIComponent(valor),
  });
  const dados = await resp.json();
  if (dados.ok) {
    document.getElementById('cs-chave').value = '';
    document.getElementById('cs-valor').value = '';
    sucessoEl.innerText = 'Salvo e cifrado.';
    carregarChavesConfigSeguro();
  } else {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
  }
}

async function removerChaveConfigSeguro(chave) {
  if (!confirm('Remover "' + chave + '"? Volta a usar o valor do .env correspondente, se existir.')) return;
  const resp = await fetch('/api/config-seguro/remover', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'chave=' + encodeURIComponent(chave),
  });
  const dados = await resp.json();
  if (dados.ok) {
    carregarChavesConfigSeguro();
  } else {
    alert(dados.erro || 'Não foi possível remover.');
  }
}

carregarChavesConfigSeguro();
</script>
</body>
</html>
"""


def _montar_config_seguro_html(sessao: dict) -> str:
    return (
        _CONFIG_SEGURO_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Criptografia de Dados Sensíveis"))
        .replace("__FOOTER__", _montar_footer())
    )


_DASH_FINANCEIRO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Atualização Dash Financeiro</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-df { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1000px; margin: 0 auto 20px auto; }
  .cabecalho-df h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-df .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; }

  .painel-df { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1000px; margin: 0 auto 20px auto; }
  .painel-df h2 { margin: 0 0 6px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .painel-df .sub-painel { color: var(--fg-dim); font-size: 12px; margin-bottom: 16px; line-height: 1.5; }

  .grade-produtos-df { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 12px; }
  .cartao-produto-df { background: rgba(255,255,255,.03); border: 1px solid var(--border);
                        border-radius: 10px; padding: 14px 16px; }
  .cartao-produto-df .nome-produto { font-size: 13px; font-weight: 700; color: var(--fg); margin-bottom: 6px; }
  .cartao-produto-df .status-linha { font-size: 12px; margin-bottom: 3px; }
  .badge-status-df { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 10.5px;
                      font-weight: 700; text-transform: uppercase; letter-spacing: .03em; }
  .badge-ok { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-pulado { background: rgba(255,255,255,.08); color: var(--fg-dim); }
  .badge-pendente { background: rgba(232,163,61,.15); color: #e8a33d; }
  .badge-rodando { background: rgba(45,184,207,.15); color: var(--teal); }
  #df-botao-executar:disabled { opacity: .55; cursor: default; }
  .badge-erro { background: rgba(241,76,76,.15); color: var(--erro); }
  .badge-nunca { background: rgba(255,255,255,.05); color: var(--fg-dim); }
  .detalhe-produto-df { font-size: 11px; color: var(--fg-dim); margin-top: 6px; line-height: 1.5; }

  .erro-df { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 10px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-df">
      <div>
        <h1>Atualização Dash Financeiro</h1>
        <div class="sub">
          Gera a contagem mensal de documentos por cliente (NFe, CTe,
          NFCe, CFe, NFSe Out, NFSe In, MDFe, LASA, SaaS) e salva em
          a pasta configurada em PDA_DASH_FINANCEIRO_PASTA/&lt;Produto&gt;/ - a mesma pasta
          que o Power BI já lê. Idempotente por mês: se o CSV do mês já
          existir, não refaz a consulta.
        </div>
      </div>
      <button class="btn-accent" id="df-botao-executar" onclick="executarDashFinanceiro()">Executar agora</button>
    </div>

    <div class="erro-df" id="df-erro"></div>

    <div class="painel-df">
      <h2>Status por produto</h2>
      <div class="sub-painel">Atualiza sozinho a cada poucos segundos enquanto uma execução estiver rodando.</div>
      <div class="grade-produtos-df" id="df-grade-produtos">
        <div class="carregando-im">Carregando...</div>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
function formatarStatusProduto(info) {
  if (!info) {
    return { badge: '<span class="badge-status-df badge-nunca">Ainda não gerado</span>', detalhe: '' };
  }
  if (info.rodando) {
    return { badge: '<span class="badge-status-df badge-rodando">Gerando arquivo...</span>', detalhe: 'Consultando os bancos, aguarde.' };
  }
  if (!info.ok) {
    return {
      badge: '<span class="badge-status-df badge-erro">Erro</span>',
      detalhe: (info.erro || 'Erro desconhecido') + (info.executado_em ? ' · ' + info.executado_em : ''),
    };
  }
  if (info.pulado) {
    // "atualizado_no_mes" só vem quando o status foi reconstruído a
    // partir do disco (sessão atual ainda não processou esse produto) -
    // se for false, o CSV existente é de um mês anterior, não do atual
    const aindaNoMes = info.atualizado_no_mes !== false;
    const rotulo = aindaNoMes ? 'Atualizado' : 'Pendente este mês';
    const classe = aindaNoMes ? 'badge-pulado' : 'badge-pendente';
    return {
      badge: `<span class="badge-status-df ${classe}">${rotulo}</span>`,
      detalhe: 'Última atualização: ' + (info.executado_em || '?') + (aindaNoMes ? '' : ' (mês anterior)'),
    };
  }
  let detalhe = (info.linhas ?? 0) + ' linha(s)';
  if (info.conexoes_com_erro) detalhe += ' · ' + info.conexoes_com_erro + ' conexão(ões) com erro';
  if (info.executado_em) detalhe += ' · ' + info.executado_em;
  return { badge: '<span class="badge-status-df badge-ok">OK</span>', detalhe };
}

async function carregarStatusDashFinanceiro() {
  const erroEl = document.getElementById('df-erro');
  const botaoExecutar = document.getElementById('df-botao-executar');
  try {
    const resp = await fetch('/api/dash-financeiro/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar o status.';
      return;
    }
    erroEl.innerText = '';
    if (botaoExecutar) {
      botaoExecutar.disabled = !!dados.execucao_ativa;
      botaoExecutar.innerText = dados.execucao_ativa ? 'Executando...' : 'Executar agora';
    }
    const grade = document.getElementById('df-grade-produtos');
    grade.innerHTML = dados.ordem.map(produto => {
      const { badge, detalhe } = formatarStatusProduto(dados.status[produto]);
      return `
        <div class="cartao-produto-df">
          <div class="nome-produto">${produto}</div>
          <div class="status-linha">${badge}</div>
          <div class="detalhe-produto-df">${detalhe}</div>
        </div>
      `;
    }).join('');
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
  }
}

async function executarDashFinanceiro() {
  const resp = await fetch('/api/dash-financeiro/executar', { method: 'POST' });
  if (resp.status === 401) { window.location.href = '/login'; return; }
  if (resp.status === 403) { window.location.href = '/'; return; }
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('df-erro').innerText = dados.erro || 'Não foi possível iniciar.';
    carregarStatusDashFinanceiro();
    return;
  }
  carregarStatusDashFinanceiro();
}

carregarStatusDashFinanceiro();
setInterval(carregarStatusDashFinanceiro, 8000);
</script>
</body>
</html>
"""


def _montar_dash_financeiro_html(sessao: dict) -> str:
    return (
        _DASH_FINANCEIRO_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Atualização Dash Financeiro"))
        .replace("__FOOTER__", _montar_footer())
    )


_EMAILPACK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Monitoramento EmailPack</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-ep { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1080px; margin: 0 auto 20px auto; }
  .cabecalho-ep h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-ep .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; max-width: 640px; }
  #ep-botao-executar:disabled { opacity: .55; cursor: default; }

  .erro-ep { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 0 auto 10px auto; max-width: 1080px; }

  .painel-ep { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1080px; margin: 0 auto 20px auto; }
  .painel-ep h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }

  .grade-status-ep { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }
  .cartao-numero-ep { text-align: center; }
  .cartao-numero-ep .numero { font-size: 24px; font-weight: 800; color: var(--teal); }
  .cartao-numero-ep .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                               letter-spacing: .04em; margin-top: 4px; }

  .badge-ep { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 6px;
              font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; }
  .badge-ep.rodando { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-ep.parado { background: rgba(255,255,255,.06); color: var(--fg-dim); }
  .badge-ep .ponto { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
  .badge-ep.rodando .ponto { animation: pulso-ponto-ep 1.2s infinite; }
  @keyframes pulso-ponto-ep { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }

  .aviso-dirs-ep { background: rgba(232,163,61,.08); border: 1px solid rgba(232,163,61,.25);
                    border-radius: 10px; padding: 12px 16px; font-size: 12px; color: #e8a33d;
                    line-height: 1.6; margin-bottom: 16px; }
  .aviso-dirs-ep ul { margin: 6px 0 0 0; padding-left: 18px; }

  .vazio-ep { color: var(--fg-dim); font-size: 12.5px; padding: 8px 0; }
  .servico-ep { margin-bottom: 18px; }
  .servico-ep:last-child { margin-bottom: 0; }
  .servico-ep .nome-servico-ep { font-size: 12.5px; font-weight: 700; color: var(--fg); margin-bottom: 10px; }
  .barra-email-ep { margin-bottom: 12px; }
  .barra-email-ep:last-child { margin-bottom: 0; }
  .rotulo-barra-email-ep { font-size: 11.5px; color: var(--fg-dim); margin-bottom: 5px; overflow: hidden;
                             text-overflow: ellipsis; white-space: nowrap; }
  .trilho-barra-email-ep { position: relative; height: 24px; background: rgba(255,255,255,.04);
                             border-radius: 6px; overflow: hidden; display: flex; align-items: center; }
  .preenchimento-barra-email-ep { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 6px;
                                    background: linear-gradient(90deg, rgba(241,76,76,.5), rgba(241,76,76,.85));
                                    transition: width .5s ease; }
  .contagem-barra-email-ep { position: relative; z-index: 1; margin-left: auto; margin-right: 9px;
                               font-size: 11px; font-weight: 700; color: var(--fg); }
  .controle-ignorar-ep { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .controle-ignorar-ep select { flex: 1; min-width: 220px; padding: 8px 10px; border-radius: 7px;
                                  border: 1px solid var(--border); background: rgba(0,0,0,.28);
                                  color: var(--fg); font-size: 12.5px; font-family: inherit; }
  .controle-ignorar-ep select:focus { outline: none; border-color: var(--teal); }
  .linha-ignorado-ep { display: flex; justify-content: space-between; align-items: center;
                        background: rgba(255,255,255,.02); border: 1px solid var(--border);
                        border-radius: 8px; padding: 9px 14px; margin-bottom: 6px; font-size: 12.5px; }
  .linha-ignorado-ep:last-child { margin-bottom: 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-ep">
      <div>
        <h1>Monitoramento EmailPack</h1>
        <div class="sub">
          Varre os logs dos serviços EmailPack (NOC, Geral, Empresa, Sem
          Autenticação) procurando erros por e-mail processado, e avisa no
          Teams quando encontra algo.
        </div>
      </div>
      <button class="btn-accent" id="ep-botao-executar" onclick="executarEmailPack()">Executar agora</button>
    </div>

    <div class="erro-ep" id="ep-erro"></div>

    <div class="painel-ep">
      <h2>Status</h2>
      <div class="grade-status-ep">
        <div class="cartao-numero-ep">
          <div id="ep-badge-status"><span class="badge-ep parado"><span class="ponto"></span>Carregando...</span></div>
          <div class="rotulo">Situação</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-ultima-execucao">–</div>
          <div class="rotulo">Última execução</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-linhas">–</div>
          <div class="rotulo">Linhas novas processadas</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-servicos">–</div>
          <div class="rotulo">Serviços verificados</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-arquivos">–</div>
          <div class="rotulo">Arquivos verificados</div>
        </div>
      </div>
    </div>

    <div class="painel-ep">
      <h2>E-mails ignorados <span style="text-transform:none; font-weight:400; letter-spacing:normal;">(não geram aviso no Teams)</span></h2>
      __CONTROLE_IGNORAR_EP__
      <div id="ep-lista-ignorados"><div class="vazio-ep">Carregando...</div></div>
    </div>

    <div class="painel-ep">
      <h2>Erros encontrados na última execução</h2>
      <div id="ep-erros-servicos"><div class="vazio-ep">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

<script>
function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderizarErrosPorServico(errosPorServico) {
  const el = document.getElementById('ep-erros-servicos');
  const servicos = Object.keys(errosPorServico || {});
  if (servicos.length === 0) {
    el.innerHTML = '<div class="vazio-ep">Nenhum erro encontrado na última execução. ✓</div>';
    return;
  }

  // acha a maior contagem entre TODOS os servicos/emails, pra as barras
  // ficarem proporcionais entre si (nao so dentro do proprio servico)
  let maiorQuantidade = 1;
  for (const servico of servicos) {
    for (const email of Object.keys(errosPorServico[servico])) {
      maiorQuantidade = Math.max(maiorQuantidade, errosPorServico[servico][email].quantidade);
    }
  }

  el.innerHTML = servicos.map(servico => {
    const emails = errosPorServico[servico];
    const entradasOrdenadas = Object.keys(emails)
      .map(email => ({ email, quantidade: emails[email].quantidade }))
      .sort((a, b) => b.quantidade - a.quantidade);

    const barras = entradasOrdenadas.map(({ email, quantidade }) => {
      const largura = Math.max(6, Math.round((quantidade / maiorQuantidade) * 100));
      return `
        <div class="barra-email-ep">
          <div class="rotulo-barra-email-ep" title="${escaparHtml(email)}">${escaparHtml(email)}</div>
          <div class="trilho-barra-email-ep">
            <div class="preenchimento-barra-email-ep" style="width:${largura}%"></div>
            <span class="contagem-barra-email-ep">${quantidade}x</span>
          </div>
        </div>
      `;
    }).join('');

    return `<div class="servico-ep"><div class="nome-servico-ep">${escaparHtml(servico)}</div>${barras}</div>`;
  }).join('');
}

async function carregarStatusEmailPack() {
  try {
    const resp = await fetch('/api/emailpack/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível carregar o status.';
      return;
    }
    document.getElementById('ep-erro').innerText = '';

    const badgeEl = document.getElementById('ep-badge-status');
    const botao = document.getElementById('ep-botao-executar');
    if (dados.executando) {
      badgeEl.innerHTML = '<span class="badge-ep rodando"><span class="ponto"></span>Rodando</span>';
      botao.disabled = true;
      botao.innerText = 'Executando...';
    } else {
      badgeEl.innerHTML = '<span class="badge-ep parado"><span class="ponto"></span>Aguardando</span>';
      botao.disabled = false;
      botao.innerText = 'Executar agora';
    }

    document.getElementById('ep-ultima-execucao').innerText = dados.ultima_execucao || 'nunca rodou';
    document.getElementById('ep-linhas').innerText = dados.total_linhas_novas ?? '–';
    document.getElementById('ep-servicos').innerText = dados.servicos_verificados ?? '–';
    document.getElementById('ep-arquivos').innerText = dados.arquivos_verificados ?? '–';

    const painelErros = document.querySelectorAll('.painel-ep')[1];
    const avisoExistente = painelErros.querySelector('.aviso-dirs-ep');
    if (avisoExistente) avisoExistente.remove();
    if (dados.dirs_ausentes && dados.dirs_ausentes.length > 0) {
      const aviso = document.createElement('div');
      aviso.className = 'aviso-dirs-ep';
      aviso.innerHTML = `⚠ ${dados.dirs_ausentes.length} diretório(s) inacessível(is):<ul>` +
        dados.dirs_ausentes.map(d => `<li>${escaparHtml(d)}</li>`).join('') + '</ul>';
      painelErros.insertBefore(aviso, painelErros.querySelector('h2').nextSibling);
    }

    renderizarErrosPorServico(dados.erros_por_servico);
  } catch (e) {
    document.getElementById('ep-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

async function executarEmailPack() {
  const botao = document.getElementById('ep-botao-executar');
  if (botao.disabled) return;
  botao.disabled = true;
  botao.innerText = 'Executando...';
  try {
    const resp = await fetch('/api/emailpack/executar', { method: 'POST' });
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível executar.';
    }
  } catch (e) {
    document.getElementById('ep-erro').innerText = 'Erro ao executar: ' + e;
  } finally {
    setTimeout(carregarStatusEmailPack, 1000);
  }
}

const EH_ADMIN_EP = __EH_ADMIN_EP__;

function renderizarListaIgnorados(ignorados) {
  const el = document.getElementById('ep-lista-ignorados');
  if (ignorados.length === 0) {
    el.innerHTML = '<div class="vazio-ep">Nenhum e-mail ignorado.</div>';
    return;
  }
  el.innerHTML = ignorados.map(email => `
    <div class="linha-ignorado-ep">
      <span>${escaparHtml(email)}</span>
      ${EH_ADMIN_EP ? `<button class="btn-mini btn-perigo" onclick="removerIgnorado('${escaparHtml(email)}')">Remover</button>` : ''}
    </div>
  `).join('');
}

async function carregarEmailsEmailPack() {
  try {
    const resp = await fetch('/api/emailpack/emails');
    const dados = await resp.json();
    if (!dados.ok) return;

    renderizarListaIgnorados(dados.ignorados);

    if (EH_ADMIN_EP) {
      const select = document.getElementById('ep-select-ignorar');
      const disponiveis = dados.conhecidos.filter(e => !dados.ignorados.includes(e));
      select.innerHTML = '<option value="">Selecione um e-mail pra ignorar...</option>' +
        disponiveis.map(e => `<option value="${escaparHtml(e)}">${escaparHtml(e)}</option>`).join('');
    }
  } catch (e) {
    console.warn('Não foi possível carregar e-mails do EmailPack:', e);
  }
}

async function ignorarEmail() {
  const select = document.getElementById('ep-select-ignorar');
  const email = select.value;
  if (!email) return;
  const resp = await fetch('/api/emailpack/ignorar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'email=' + encodeURIComponent(email),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível ignorar.';
    return;
  }
  carregarEmailsEmailPack();
}

async function removerIgnorado(email) {
  const resp = await fetch('/api/emailpack/remover-ignorado', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'email=' + encodeURIComponent(email),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível remover.';
    return;
  }
  carregarEmailsEmailPack();
}

carregarStatusEmailPack();
setInterval(carregarStatusEmailPack, 8000);
carregarEmailsEmailPack();
setInterval(carregarEmailsEmailPack, 15000);
</script>
</body>
</html>
"""


def _montar_emailpack_html(sessao: dict) -> str:
    if sessao["admin"]:
        controle_ignorar = (
            '<div class="controle-ignorar-ep">'
            '<select id="ep-select-ignorar"><option value="">Selecione um e-mail pra ignorar...</option></select>'
            '<button class="btn-mini" onclick="ignorarEmail()">Ignorar</button>'
            '</div>'
        )
    else:
        controle_ignorar = ""
    return (
        _EMAILPACK_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Monitoramento EmailPack"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__CONTROLE_IGNORAR_EP__", controle_ignorar)
        .replace("__EH_ADMIN_EP__", "true" if sessao["admin"] else "false")
    )


_FERIAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Calendário de Férias</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body { position: relative; }
  body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: radial-gradient(ellipse 900px 500px at 15% 0%, rgba(76,201,240,.07), transparent 60%),
                radial-gradient(ellipse 800px 500px at 90% 100%, rgba(155,93,229,.06), transparent 60%);
  }
  .conteudo { position: relative; z-index: 1; }

  .cabecalho-fer { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                   gap: 14px; max-width: 1120px; margin: 0 auto 22px auto; }
  .cabecalho-fer h1 { font-size: 21px; margin: 0 0 4px 0; font-weight: 800;
                       background: var(--gradiente-marca); -webkit-background-clip: text;
                       background-clip: text; color: transparent; }
  .cabecalho-fer .sub { color: var(--fg-dim); font-size: 12.5px; }

  .painel-fer { background: var(--bg-panel); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
                border-radius: 16px; padding: 26px 28px; max-width: 1120px; margin: 0 auto 20px auto;
                border: 1px solid transparent;
                background-image: linear-gradient(var(--bg-panel), var(--bg-panel)),
                                   linear-gradient(150deg, rgba(255,255,255,.08), rgba(255,255,255,.01) 40%);
                background-origin: border-box; background-clip: padding-box, border-box;
                box-shadow: 0 20px 50px rgba(0,0,0,.35); }

  .nav-mes-fer { display: flex; align-items: center; justify-content: center; gap: 22px; margin-bottom: 22px; }
  .nav-mes-fer button { background: rgba(255,255,255,.04); border: 1px solid var(--border); color: var(--fg);
                          width: 34px; height: 34px; border-radius: 9px; cursor: pointer; font-size: 16px;
                          display: flex; align-items: center; justify-content: center;
                          transition: border-color .15s, color .15s, background .15s; }
  .nav-mes-fer button:hover { border-color: var(--teal); color: var(--teal); background: rgba(45,184,207,.08); }
  .nav-mes-fer h2 { margin: 0; font-size: 17px; font-weight: 700; color: var(--fg); min-width: 190px; text-align: center; }
  .nav-mes-fer .botao-hoje-fer { width: auto; padding: 0 12px; font-size: 11px; text-transform: uppercase;
                                   letter-spacing: .04em; font-weight: 700; color: var(--fg-dim); }
  .nav-mes-fer .botao-hoje-fer:hover { color: var(--teal); }

  .grade-cabecalho-fer { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; margin-bottom: 8px; }
  .grade-cabecalho-fer div { text-align: center; font-size: 10.5px; color: var(--fg-dim);
                              text-transform: uppercase; letter-spacing: .06em; padding: 4px 0; font-weight: 700; }
  .grade-dias-fer { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; }
  .dia-ferias { min-height: 92px; border-radius: 10px; padding: 8px; background: rgba(255,255,255,.02);
                border: 1px solid var(--border); transition: border-color .15s, background .15s; }
  .dia-ferias.fim-de-semana { background: rgba(255,255,255,.012); }
  .dia-ferias.vazio { background: transparent; border-color: transparent; }
  .dia-ferias.hoje { border-color: var(--teal); background: rgba(45,184,207,.08);
                      box-shadow: 0 0 0 1px rgba(45,184,207,.3), inset 0 0 20px rgba(45,184,207,.05); }
  .dia-ferias:not(.vazio):hover { border-color: var(--border-forte); background: rgba(255,255,255,.035); }
  .numero-dia-ferias { font-size: 12px; color: var(--fg-dim); margin-bottom: 6px; font-weight: 600; }
  .dia-ferias.hoje .numero-dia-ferias {
    color: #08090c; background: var(--gradiente-marca); width: 20px; height: 20px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; font-weight: 800; }
  .tags-dia-ferias { display: flex; flex-direction: column; gap: 3px; }
  .tag-pessoa-ferias { display: flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 600;
                        padding: 3px 6px 3px 4px; border-radius: 5px; cursor: default; color: #fff; }
  .tag-pessoa-ferias.day-off { border: 1px dashed rgba(255,255,255,.5); background: transparent !important;
                                 color: var(--fg) !important; }
  .tag-pessoa-ferias.atestado { border: 1px dotted rgba(232,163,61,.75); background: rgba(232,163,61,.08) !important;
                                  color: var(--fg) !important; }
  .avatar-mini-ferias { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; font-size: 7px;
                         font-weight: 800; display: flex; align-items: center; justify-content: center;
                         color: #08090c; background: rgba(255,255,255,.85); }
  .nome-na-tag-ferias { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .selo-tipo-ferias { flex-shrink: 0; font-size: 7.5px; font-weight: 800; letter-spacing: .02em;
                       padding: 1px 4px; border-radius: 3px; background: rgba(0,0,0,.28); }
  .tag-pessoa-ferias.day-off .selo-tipo-ferias { background: rgba(255,255,255,.14); }

  @media (max-width: 640px) {
    .dia-ferias { min-height: 54px; padding: 5px; }
    .tag-pessoa-ferias { font-size: 8px; }
    .avatar-mini-ferias { display: none; }
    .selo-tipo-ferias { font-size: 6.5px; padding: 1px 3px; }
  }

  .legenda-fer { display: flex; gap: 20px; justify-content: center; margin-top: 18px; flex-wrap: wrap; }
  .legenda-fer-item { display: flex; align-items: center; gap: 7px; font-size: 11px; color: var(--fg-dim); }
  .legenda-marca-ferias { width: 22px; height: 12px; border-radius: 4px; background: var(--teal); }
  .legenda-marca-dayoff { width: 22px; height: 12px; border-radius: 4px; border: 1px dashed var(--fg-dim); }
  .legenda-marca-atestado { width: 22px; height: 12px; border-radius: 4px; border: 1px dotted #e8a33d;
                              background: rgba(232,163,61,.1); }

  .lista-fer-titulo { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .lista-fer-titulo h2 { margin: 0; font-size: 12.5px; color: var(--fg-dim); text-transform: uppercase;
                          letter-spacing: .07em; font-weight: 700; }
  .linha-fer { display: flex; justify-content: space-between; align-items: center; gap: 12px;
               background: rgba(255,255,255,.02); border: 1px solid var(--border); border-radius: 10px;
               padding: 12px 16px; margin-bottom: 8px; font-size: 12.5px; transition: background .15s; }
  .linha-fer:hover { background: rgba(255,255,255,.035); }
  .linha-fer:last-child { margin-bottom: 0; }
  .linha-fer-esquerda { display: flex; align-items: center; gap: 12px; }
  .avatar-linha-ferias { width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0; font-size: 12.5px;
                          font-weight: 800; display: flex; align-items: center; justify-content: center; color: #08090c; }
  .linha-fer .nome-fer { font-weight: 700; color: var(--fg); display: flex; align-items: center; gap: 8px; }
  .linha-fer .periodo-fer { color: var(--fg-dim); font-size: 11.5px; margin-top: 2px; }
  .badge-tipo-fer { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em;
                     padding: 2px 7px; border-radius: 5px; }
  .badge-tipo-fer.ferias { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-tipo-fer.day-off { background: rgba(255,255,255,.06); color: var(--fg-dim); border: 1px dashed var(--border-forte); }
  .badge-tipo-fer.atestado { background: rgba(232,163,61,.12); color: #e8a33d; border: 1px dotted rgba(232,163,61,.6); }
  .link-nome-fer { color: var(--fg); text-decoration: none; }
  .link-nome-fer:hover { color: var(--teal); text-decoration: underline; }
  .vazio-fer { color: var(--fg-dim); font-size: 12.5px; padding: 8px 0; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  .erro-fer { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 0 auto 10px auto; max-width: 1120px; }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; }
  .modal-fundo.aberto { display: flex; }
  .modal { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 28px 26px; width: 340px; box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal h3 { margin: 0 0 16px 0; font-size: 15px; color: var(--teal); }
  .modal label { display: block; font-size: 11px; color: var(--fg-dim); margin: 12px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal input, .modal select { width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal input:focus, .modal select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .modal .acoes-modal { display: flex; gap: 8px; margin-top: 20px; }
  .modal .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .seletor-tipo-fer { display: flex; gap: 8px; margin-top: 6px; }
  .seletor-tipo-fer button { flex: 1; padding: 9px; border-radius: 7px; border: 1px solid var(--border);
                               background: rgba(0,0,0,.2); color: var(--fg-dim); font-size: 12.5px;
                               font-family: inherit; cursor: pointer; transition: all .15s; }
  .seletor-tipo-fer button.ativo { border-color: var(--teal); color: var(--teal); background: rgba(45,184,207,.1); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-fer">
      <div>
        <h1>Calendário de Férias</h1>
        <div class="sub">Visualização das férias e day offs já agendados e aprovados da equipe.</div>
      </div>
      __BOTAO_NOVA_FERIAS__
    </div>

    <div class="erro-fer" id="fer-erro"></div>

    <div class="painel-fer">
      <div class="nav-mes-fer">
        <button onclick="mudarMesFerias(-1)">‹</button>
        <h2 id="fer-mes-titulo">–</h2>
        <button onclick="mudarMesFerias(1)">›</button>
        <button class="botao-hoje-fer" onclick="irParaHojeFerias()">Hoje</button>
      </div>
      <div class="grade-cabecalho-fer">
        <div>Dom</div><div>Seg</div><div>Ter</div><div>Qua</div><div>Qui</div><div>Sex</div><div>Sáb</div>
      </div>
      <div class="grade-dias-fer" id="fer-grade-dias"></div>
      <div class="legenda-fer">
        <div class="legenda-fer-item"><div class="legenda-marca-ferias"></div>Férias</div>
        <div class="legenda-fer-item"><div class="legenda-marca-dayoff"></div>Day Off</div>
        <div class="legenda-fer-item"><div class="legenda-marca-atestado"></div>Atestado</div>
      </div>
    </div>

    <div class="painel-fer">
      <div class="lista-fer-titulo"><h2 id="fer-titulo-lista">Períodos cadastrados</h2></div>
      <div id="fer-lista-registros"><div class="vazio-fer">Carregando...</div></div>
    </div>
  </div>

  __MODAL_NOVA_FERIAS__

  __FOOTER__

<script>
function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const PALETA_CORES_FERIAS = ['#2db8cf','#f14c4c','#e8a33d','#b0cb1c','#4ec9b0','#9cdcfe','#b389f9','#f9c74f','#6c63ff','#4cc9f0','#9b5de5','#ff8fa3'];

function corDaPessoaFerias(nome) {
  let hash = 0;
  for (let i = 0; i < nome.length; i++) hash = (hash * 31 + nome.charCodeAt(i)) >>> 0;
  return PALETA_CORES_FERIAS[hash % PALETA_CORES_FERIAS.length];
}

function iniciaisDaPessoaFerias(nome) {
  const partes = nome.trim().split(/\\s+/).filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

const HOJE_FER = new Date();
let mesAtualFerias = HOJE_FER.getMonth();
let anoAtualFerias = HOJE_FER.getFullYear();
const NOMES_MESES_FERIAS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

let feriasCarregadas = [];
const EH_ADMIN_FERIAS = __EH_ADMIN_JS__;
let tipoSelecionadoModal = 'ferias';

function formatarDataISOFerias(ano, mes, dia) {
  return ano + '-' + String(mes + 1).padStart(2, '0') + '-' + String(dia).padStart(2, '0');
}

function pessoasDeFeriasNoDia(dataISO) {
  return feriasCarregadas.filter(f => f.inicio <= dataISO && dataISO <= f.fim);
}

const INFO_TIPO_FERIAS = {
  ferias: { rotulo: 'Férias', selo: 'FÉ', classe: '' },
  day_off: { rotulo: 'Day Off', selo: 'DO', classe: 'day-off' },
  atestado: { rotulo: 'Atestado', selo: 'AT', classe: 'atestado' },
};

function renderizarCalendarioFerias() {
  document.getElementById('fer-mes-titulo').innerText = NOMES_MESES_FERIAS[mesAtualFerias] + ' de ' + anoAtualFerias;

  const primeiroDiaSemana = new Date(anoAtualFerias, mesAtualFerias, 1).getDay();
  const diasNoMes = new Date(anoAtualFerias, mesAtualFerias + 1, 0).getDate();
  const hojeISO = formatarDataISOFerias(HOJE_FER.getFullYear(), HOJE_FER.getMonth(), HOJE_FER.getDate());

  let html = '';
  for (let i = 0; i < primeiroDiaSemana; i++) html += '<div class="dia-ferias vazio"></div>';

  for (let dia = 1; dia <= diasNoMes; dia++) {
    const dataISO = formatarDataISOFerias(anoAtualFerias, mesAtualFerias, dia);
    const pessoasNoDia = pessoasDeFeriasNoDia(dataISO);
    const ehHoje = dataISO === hojeISO;
    const diaSemana = new Date(anoAtualFerias, mesAtualFerias, dia).getDay();
    const ehFimDeSemana = diaSemana === 0 || diaSemana === 6;
    html += `
      <div class="dia-ferias ${ehHoje ? 'hoje' : ''} ${ehFimDeSemana ? 'fim-de-semana' : ''}">
        <div class="numero-dia-ferias">${dia}</div>
        <div class="tags-dia-ferias">
          ${pessoasNoDia.map(f => {
            const cor = corDaPessoaFerias(f.nome);
            const info = INFO_TIPO_FERIAS[f.tipo] || INFO_TIPO_FERIAS.ferias;
            const temFundoSolido = info.classe === '';
            const primeiroNome = f.nome.split(' ')[0];
            const estilo = temFundoSolido ? `background:${cor};` : '';
            return `<span class="tag-pessoa-ferias ${info.classe}" style="${estilo}" title="${escaparHtml(f.nome)} · ${info.rotulo} · ${f.inicio} até ${f.fim}">
              <span class="avatar-mini-ferias" style="${temFundoSolido ? '' : `background:${cor};color:#fff;`}">${iniciaisDaPessoaFerias(f.nome)}</span>
              <span class="nome-na-tag-ferias">${escaparHtml(primeiroNome)}</span>
              <span class="selo-tipo-ferias">${info.selo}</span>
            </span>`;
          }).join('')}
        </div>
      </div>
    `;
  }
  document.getElementById('fer-grade-dias').innerHTML = html;
}

function mudarMesFerias(direcao) {
  mesAtualFerias += direcao;
  if (mesAtualFerias < 0) { mesAtualFerias = 11; anoAtualFerias--; }
  if (mesAtualFerias > 11) { mesAtualFerias = 0; anoAtualFerias++; }
  renderizarCalendarioFerias();
  renderizarListaFerias();
}

function irParaHojeFerias() {
  mesAtualFerias = HOJE_FER.getMonth();
  anoAtualFerias = HOJE_FER.getFullYear();
  renderizarCalendarioFerias();
  renderizarListaFerias();
}

function periodoNoMesExibido(periodo) {
  // "overlap" entre o periodo (inicio/fim) e o mes/ano sendo exibido no
  // calendario agora - um periodo aparece na lista se qualquer parte
  // dele cair dentro do mes visivel, mesmo que comece ou termine fora
  const primeiroDiaMes = formatarDataISOFerias(anoAtualFerias, mesAtualFerias, 1);
  const ultimoDiaDoMes = new Date(anoAtualFerias, mesAtualFerias + 1, 0).getDate();
  const ultimoDiaMes = formatarDataISOFerias(anoAtualFerias, mesAtualFerias, ultimoDiaDoMes);
  return periodo.inicio <= ultimoDiaMes && periodo.fim >= primeiroDiaMes;
}

function renderizarListaFerias() {
  const el = document.getElementById('fer-lista-registros');
  const tituloEl = document.getElementById('fer-titulo-lista');
  if (tituloEl) tituloEl.innerText = 'Períodos de ' + NOMES_MESES_FERIAS[mesAtualFerias] + ' de ' + anoAtualFerias;

  const periodosDoMes = feriasCarregadas.filter(periodoNoMesExibido);
  if (periodosDoMes.length === 0) {
    el.innerHTML = '<div class="vazio-fer">Nenhum período cadastrado nesse mês.</div>';
    return;
  }
  el.innerHTML = periodosDoMes.map(f => {
    const cor = corDaPessoaFerias(f.nome);
    const info = INFO_TIPO_FERIAS[f.tipo] || INFO_TIPO_FERIAS.ferias;
    return `
    <div class="linha-fer">
      <div class="linha-fer-esquerda">
        <div class="avatar-linha-ferias" style="background:${cor}">${iniciaisDaPessoaFerias(f.nome)}</div>
        <div>
          <div class="nome-fer"><a class="link-nome-fer" href="/perfil/${encodeURIComponent(f.usuario)}">${escaparHtml(f.nome)}</a> <span class="badge-tipo-fer ${info.classe}">${info.rotulo}</span></div>
          <div class="periodo-fer">${f.inicio} até ${f.fim}</div>
        </div>
      </div>
      ${EH_ADMIN_FERIAS ? `<button class="btn-mini btn-perigo" onclick="excluirFerias(${f.id})">Excluir</button>` : ''}
    </div>
  `;
  }).join('');
}

async function carregarFerias() {
  try {
    const resp = await fetch('/api/ferias');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('fer-erro').innerText = dados.erro || 'Não foi possível carregar.';
      return;
    }
    document.getElementById('fer-erro').innerText = '';
    feriasCarregadas = dados.registros;
    renderizarCalendarioFerias();
    renderizarListaFerias();
  } catch (e) {
    document.getElementById('fer-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

async function excluirFerias(id) {
  if (!confirm('Remover esse período?')) return;
  const resp = await fetch('/api/ferias/excluir', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + id,
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('fer-erro').innerText = dados.erro || 'Não foi possível excluir.';
    return;
  }
  carregarFerias();
}

function selecionarTipoModal(tipo) {
  tipoSelecionadoModal = tipo;
  document.getElementById('fer-botao-tipo-ferias').classList.toggle('ativo', tipo === 'ferias');
  document.getElementById('fer-botao-tipo-dayoff').classList.toggle('ativo', tipo === 'day_off');
  document.getElementById('fer-botao-tipo-atestado').classList.toggle('ativo', tipo === 'atestado');
}

async function abrirModalNovaFerias() {
  document.getElementById('fer-modal-erro').innerText = '';
  selecionarTipoModal('ferias');
  document.getElementById('fer-input-inicio').value = '';
  document.getElementById('fer-input-fim').value = '';
  const select = document.getElementById('fer-select-usuario');
  if (select.options.length <= 1) {
    try {
      const resp = await fetch('/api/usuarios');
      const dados = await resp.json();
      select.innerHTML = '<option value="">Selecione...</option>' +
        dados.usuarios.map(u => `<option value="${escaparHtml(u.usuario)}">${escaparHtml(u.nome || u.usuario)}</option>`).join('');
    } catch (e) {
      document.getElementById('fer-modal-erro').innerText = 'Não foi possível carregar os usuários.';
    }
  }
  document.getElementById('modal-nova-ferias').classList.add('aberto');
}

function fecharModalNovaFerias() {
  document.getElementById('modal-nova-ferias').classList.remove('aberto');
}

async function salvarNovaFerias() {
  const usuario = document.getElementById('fer-select-usuario').value;
  const inicio = document.getElementById('fer-input-inicio').value;
  const fim = document.getElementById('fer-input-fim').value;
  const erroEl = document.getElementById('fer-modal-erro');

  if (!usuario || !inicio || !fim) {
    erroEl.innerText = 'Preencha a pessoa e as duas datas.';
    return;
  }

  const resp = await fetch('/api/ferias/criar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario) + '&inicio=' + encodeURIComponent(inicio) +
          '&fim=' + encodeURIComponent(fim) + '&tipo=' + encodeURIComponent(tipoSelecionadoModal),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
    return;
  }
  fecharModalNovaFerias();
  carregarFerias();
}

carregarFerias();
</script>
</body>
</html>
"""


_PERFIL_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Perfil</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body { position: relative; }
  body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: radial-gradient(ellipse 900px 500px at 20% 0%, rgba(45,184,207,.06), transparent 60%),
                radial-gradient(ellipse 800px 500px at 85% 100%, rgba(176,203,28,.05), transparent 60%);
  }
  .conteudo { position: relative; z-index: 1; max-width: 720px; }

  .cabecalho-perfil { display: flex; align-items: center; gap: 22px; margin-bottom: 24px; flex-wrap: wrap; }
  .foto-perfil-wrap { position: relative; width: 96px; height: 96px; flex-shrink: 0; }
  .foto-perfil { width: 96px; height: 96px; border-radius: 50%; object-fit: cover;
                  border: 3px solid var(--border-forte); background: rgba(255,255,255,.04);
                  display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 800;
                  color: #08090c; }
  .botao-trocar-foto { position: absolute; bottom: -2px; right: -2px; width: 30px; height: 30px; border-radius: 50%;
                        background: var(--gradiente-marca); border: 2px solid var(--bg); cursor: pointer;
                        display: flex; align-items: center; justify-content: center; }
  .botao-trocar-foto svg { width: 15px; height: 15px; color: #08090c; }
  .info-cabecalho-perfil h1 { margin: 0 0 6px 0; font-size: 22px; font-weight: 800;
                                background: var(--gradiente-marca); -webkit-background-clip: text;
                                background-clip: text; color: transparent; }
  .cargo-perfil { font-size: 13px; color: var(--fg-dim); margin-bottom: 10px; }
  .badges-perfil { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge-perfil { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 6px;
                   background: rgba(255,255,255,.06); color: var(--fg-dim); }
  .badge-perfil.atribuicao-suporte { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-perfil.atribuicao-monitoramento { background: rgba(176,203,28,.15); color: var(--lime); }
  .badge-perfil.atribuicao-ambas { background: linear-gradient(135deg, rgba(45,184,207,.18), rgba(176,203,28,.18)); color: var(--fg); }

  .painel-perfil { background: var(--bg-panel); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                    border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; margin-bottom: 18px; }
  .painel-perfil h2 { margin: 0 0 16px 0; font-size: 12.5px; color: var(--fg-dim); text-transform: uppercase;
                       letter-spacing: .06em; font-weight: 700; }
  .cabecalho-com-acao { display: flex; align-items: center; justify-content: space-between; }
  .btn-editar-historico { background: rgba(255,255,255,.05); border: 1px solid var(--border); border-radius: 7px;
      width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; cursor: pointer;
      color: var(--fg-dim); transition: all .15s; flex-shrink: 0; font-size: 12px; line-height: 1; }
  .btn-editar-historico:hover, .btn-editar-historico.ativo { color: var(--teal); border-color: var(--teal);
      background: rgba(45,184,207,.1); }
  /* fora do modo de edição, some com os botões de remover e o formulário
     de adicionar - fica só a timeline limpa (pedido: "bem bonito
     visualmente" quando não tá editando) */
  #painel-historico-carreira:not(.modo-edicao) .btn-remover-timeline,
  #painel-historico-carreira:not(.modo-edicao) .form-add-timeline { display: none; }

  /* Feedback interno - painel com destaque visual diferente (borda
     tracejada âmbar) pra deixar bem claro que é algo restrito/privado,
     que a própria pessoa nunca vê */
  .painel-feedback { border: 1px dashed rgba(220,220,170,.4) !important; background: rgba(220,220,170,.03) !important; }
  .aviso-feedback { font-size: 10.5px; color: var(--run); margin-bottom: 14px; display: flex; align-items: center; gap: 6px; }
  .item-feedback { background: rgba(255,255,255,.02); border: 1px solid var(--border); border-radius: 8px;
      padding: 12px 14px; margin-bottom: 10px; }
  .item-feedback:last-child { margin-bottom: 0; }
  .cabecalho-item-feedback { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
  .autor-feedback { font-size: 12px; font-weight: 700; color: var(--fg); }
  .data-feedback { font-size: 10.5px; color: var(--fg-dim); }
  .texto-feedback { font-size: 12.5px; color: var(--fg); line-height: 1.5; white-space: pre-wrap; }
  .form-add-feedback { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--border); }
  .form-add-feedback textarea { width: 100%; min-height: 70px; padding: 9px 10px; border-radius: 7px;
      border: 1px solid var(--border); background: rgba(0,0,0,.28); color: var(--fg); font-size: 12.5px;
      font-family: inherit; resize: vertical; }
  .form-add-feedback textarea:focus { outline: none; border-color: var(--teal); }
  .form-add-feedback input[type="text"] { width: 100%; padding: 9px 10px; border-radius: 7px;
      border: 1px solid var(--border); background: rgba(0,0,0,.28); color: var(--fg); font-size: 12.5px;
      font-family: inherit; }
  .badge-tipo-feedback { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .03em;
      padding: 2px 7px; border-radius: 5px; margin-right: 6px; }
  .badge-tipo-feedback.tipo-feedback { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-tipo-feedback.tipo-alinhamento { background: rgba(176,203,28,.15); color: var(--lime); }
  .seletor-tipo-feedback { display: flex; gap: 14px; margin: 4px 0 12px 0; }
  .opcao-tipo-feedback { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--fg-dim);
      text-transform: none; letter-spacing: normal; cursor: pointer; }
  .opcao-tipo-feedback input { margin: 0; }
  .link-canva-feedback { display: inline-block; margin-top: 8px; font-size: 11.5px; color: var(--teal);
      text-decoration: none; }
  .link-canva-feedback:hover { text-decoration: underline; }
  .acoes-item-feedback { display: flex; gap: 14px; margin-top: 6px; }
  .btn-remover-feedback { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 11px;
      margin-top: 0; padding: 0; opacity: .6; transition: opacity .15s, color .15s; }
  .btn-remover-feedback:hover { opacity: 1; color: var(--erro); }
  .btn-remover-feedback:first-child:hover { color: var(--teal); }
  .editado-feedback { font-style: italic; opacity: .7; }
  .nota-feedback { color: var(--run); font-size: 12px; margin-left: 6px; letter-spacing: 1px; }
  .rotulo-nota-feedback { display: block; font-size: 10px; color: var(--fg-dim); text-transform: uppercase;
      letter-spacing: .04em; margin-bottom: 6px; }
  .seletor-estrelas { display: flex; gap: 4px; margin-bottom: 12px; }
  .estrela-selecionavel { font-size: 20px; color: var(--fg-dim); cursor: pointer; transition: color .1s, transform .1s; user-select: none; }
  .estrela-selecionavel:hover { transform: scale(1.15); }
  .estrela-selecionavel.preenchida { color: var(--run); }

  .grade-metricas-perfil { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; }
  .metrica-perfil { text-align: center; }
  .metrica-perfil .valor-metrica { font-size: 24px; font-weight: 800; color: var(--teal); }
  .metrica-perfil .rotulo-metrica { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                                      letter-spacing: .04em; margin-top: 4px; }

  .barra-progresso-perfil { height: 8px; border-radius: 5px; background: rgba(255,255,255,.06); margin-top: 14px;
                              overflow: hidden; }
  .barra-progresso-perfil .preenchimento { height: 100%; background: var(--gradiente-marca); border-radius: 5px;
                                             transition: width .4s ease; }
  .comparacao-mes-anterior-perfil { margin-top: 16px; padding-top: 16px; border-top: 1px dashed var(--border); }
  .titulo-comparacao-perfil { font-size: 11.5px; color: var(--fg-dim); text-transform: uppercase;
                                letter-spacing: .05em; margin-bottom: 12px; font-weight: 700; }

  .linha-periodo-perfil { display: flex; justify-content: space-between; align-items: center; gap: 10px;
                            background: rgba(255,255,255,.02); border: 1px solid var(--border); border-radius: 8px;
                            padding: 10px 14px; margin-bottom: 8px; font-size: 12.5px; }
  .linha-periodo-perfil:last-child { margin-bottom: 0; }
  .badge-tipo-perfil { font-size: 9.5px; font-weight: 700; text-transform: uppercase; padding: 2px 7px;
                        border-radius: 5px; background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-tipo-perfil.day-off { background: rgba(255,255,255,.06); color: var(--fg-dim);
                                 border: 1px dashed var(--border-forte); }
  .vazio-perfil { color: var(--fg-dim); font-size: 12.5px; }

  .aviso-privado-perfil { background: rgba(255,255,255,.03); border: 1px solid var(--border); border-radius: 12px;
                            padding: 18px 20px; font-size: 12.5px; color: var(--fg-dim); text-align: center; }
  .erro-perfil { color: var(--erro); font-size: 12.5px; min-height: 16px; margin-bottom: 10px; }
  input[type="file"] { display: none; }

  /* Histórico de carreira - timeline estilo LinkedIn */
  .timeline-carreira { position: relative; padding-left: 28px; }
  .item-timeline-carreira { position: relative; padding-bottom: 22px; }
  .item-timeline-carreira:last-child { padding-bottom: 0; }
  .item-timeline-carreira::before {
    /* linha vertical conectando os pontos */
    content: ''; position: absolute; left: -20px; top: 20px; bottom: -2px; width: 2px;
    background: linear-gradient(to bottom, var(--border-forte), var(--border));
  }
  .item-timeline-carreira:last-child::before { display: none; }
  .ponto-timeline {
    position: absolute; left: -26px; top: 2px; width: 14px; height: 14px; border-radius: 50%;
    background: var(--bg); border: 2.5px solid var(--fg-dim); z-index: 1;
  }
  .ponto-timeline.area-suporte { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.15); }
  .ponto-timeline.area-monitoramento { border-color: var(--lime); box-shadow: 0 0 0 3px rgba(176,203,28,.15); }
  .ponto-timeline.atual {
    border-color: var(--teal); background: var(--gradiente-marca);
    box-shadow: 0 0 0 4px rgba(45,184,207,.22), 0 0 14px rgba(45,184,207,.5);
  }
  .cargo-timeline { font-size: 14.5px; font-weight: 700; color: var(--fg); display: flex; align-items: center;
                      gap: 8px; flex-wrap: wrap; }
  .badge-atual-timeline { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em;
                             padding: 2px 8px; border-radius: 20px; background: var(--gradiente-marca); color: #08090c; }
  .badge-area-timeline { font-size: 9.5px; font-weight: 700; text-transform: uppercase; padding: 2px 8px;
                           border-radius: 5px; margin-left: 2px; }
  .badge-area-timeline.suporte { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-area-timeline.monitoramento { background: rgba(176,203,28,.15); color: var(--lime); }
  .periodo-timeline { font-size: 11.5px; color: var(--fg-dim); margin-top: 3px; }
  .duracao-timeline { color: var(--fg-dim); opacity: .75; }
  .btn-remover-timeline { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 11px;
                             margin-left: 8px; opacity: .5; transition: opacity .15s, color .15s; }
  .btn-remover-timeline:hover { opacity: 1; color: var(--erro); }
  .form-add-timeline { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--border);
                          display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .form-add-timeline input, .form-add-timeline select { padding: 8px 10px; border-radius: 7px;
      border: 1px solid var(--border); background: rgba(0,0,0,.28); color: var(--fg); font-size: 12.5px;
      font-family: inherit; }
  .form-add-timeline label { font-size: 10px; color: var(--fg-dim); text-transform: uppercase;
      letter-spacing: .04em; display: block; margin-bottom: 4px; }
  .form-add-timeline .campo-largura-total { grid-column: 1 / -1; }
  .form-add-timeline .campo-checkbox-atual { display: flex; align-items: center; gap: 6px; font-size: 12px;
      color: var(--fg-dim); grid-column: 1 / -1; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="erro-perfil" id="perfil-erro"></div>
    <div id="perfil-corpo"><div class="vazio-perfil">Carregando...</div></div>
  </div>

  <input type="file" id="perfil-input-foto" accept="image/jpeg,image/png,image/webp">

  __FOOTER__

<script>
function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const USUARIO_PERFIL = "__USUARIO_PERFIL__";

function iniciaisPerfil(nome) {
  const partes = nome.trim().split(/\\s+/).filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function htmlFotoOuIniciais(dados) {
  if (dados.tem_foto) {
    return `<img class="foto-perfil" src="/foto-usuario/${encodeURIComponent(dados.usuario)}?t=${Date.now()}" alt="${escaparHtml(dados.nome)}">`;
  }
  return `<div class="foto-perfil">${iniciaisPerfil(dados.nome)}</div>`;
}

const MESES_ABREV_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

function formatarMesAnoTimeline(aaaaMm) {
  const [ano, mes] = aaaaMm.split('-').map(Number);
  return `${MESES_ABREV_PT[mes - 1]}/${ano}`;
}

function formatarDuracaoTimeline(inicio, fim) {
  const [anoIni, mesIni] = inicio.split('-').map(Number);
  const hoje = new Date();
  const [anoFim, mesFim] = fim ? fim.split('-').map(Number) : [hoje.getFullYear(), hoje.getMonth() + 1];
  let totalMeses = (anoFim - anoIni) * 12 + (mesFim - mesIni) + 1;
  if (totalMeses < 1) totalMeses = 1;
  const anos = Math.floor(totalMeses / 12);
  const meses = totalMeses % 12;
  const partes = [];
  if (anos > 0) partes.push(`${anos} ano${anos > 1 ? 's' : ''}`);
  if (meses > 0 || anos === 0) partes.push(`${meses} ${meses === 1 ? 'mês' : 'meses'}`);
  return partes.join(' e ');
}

function rotuloAreaTimeline(area) {
  if (area === 'suporte') return 'Suporte';
  if (area === 'monitoramento') return 'Monitoramento';
  return '';
}

function montarHtmlTimelineCarreira(historico, sessaoAdmin) {
  const itens = historico.length === 0
    ? '<div class="vazio-perfil">Nenhum histórico de carreira registrado ainda.</div>'
    : `<div class="timeline-carreira">${historico.map((h, i) => {
        const ehAtual = !h.fim;
        const classeArea = h.area ? `area-${h.area}` : '';
        const rotuloArea = rotuloAreaTimeline(h.area);
        const periodoTexto = ehAtual
          ? `${formatarMesAnoTimeline(h.inicio)} - o momento`
          : `${formatarMesAnoTimeline(h.inicio)} - ${formatarMesAnoTimeline(h.fim)}`;
        const botaoRemover = sessaoAdmin
          ? `<button class="btn-remover-timeline" onclick="removerHistoricoCarreira(${h.id})" title="Remover">✕</button>`
          : '';
        return `
          <div class="item-timeline-carreira">
            <div class="ponto-timeline ${classeArea} ${ehAtual ? 'atual' : ''}"></div>
            <div class="cargo-timeline">
              ${escaparHtml(h.cargo)}
              ${ehAtual ? '<span class="badge-atual-timeline">Atual</span>' : ''}
              ${rotuloArea ? `<span class="badge-area-timeline ${h.area}">${rotuloArea}</span>` : ''}
              ${botaoRemover}
            </div>
            <div class="periodo-timeline">${periodoTexto} <span class="duracao-timeline">· ${formatarDuracaoTimeline(h.inicio, h.fim)}</span></div>
          </div>
        `;
      }).join('')}</div>`;

  if (!sessaoAdmin) return itens;

  return itens + `
    <div class="form-add-timeline">
      <div class="campo-largura-total">
        <label>Cargo</label>
        <input type="text" id="th-cargo" maxlength="60" placeholder="Ex.: Analista Pleno">
      </div>
      <div>
        <label>Área</label>
        <select id="th-area">
          <option value="">Sem área</option>
          <option value="suporte">Suporte</option>
          <option value="monitoramento">Monitoramento</option>
        </select>
      </div>
      <div>
        <label>Início</label>
        <input type="month" id="th-inicio">
      </div>
      <div class="campo-checkbox-atual">
        <input type="checkbox" id="th-atual" checked onchange="document.getElementById('th-fim').disabled = this.checked; document.getElementById('th-fim').value = '';">
        <label for="th-atual" style="text-transform:none; font-size:12px; margin:0">Esse é o cargo atual (sem data de fim)</label>
      </div>
      <div class="campo-largura-total">
        <label>Fim</label>
        <input type="month" id="th-fim" disabled>
      </div>
      <div class="campo-largura-total erro-perfil" id="th-erro"></div>
      <div class="campo-largura-total">
        <button class="btn-mini" onclick="adicionarHistoricoCarreira()">+ Adicionar ao histórico</button>
      </div>
    </div>
  `;
}

function renderizarEstrelas(nota) {
  if (!nota) return '';
  let estrelas = '';
  for (let i = 1; i <= 5; i++) estrelas += i <= nota ? '★' : '☆';
  return `<span class="nota-feedback">${estrelas}</span>`;
}

let notaFeedbackSelecionada = 0;

function montarSeletorEstrelas() {
  let html = '<div class="seletor-estrelas" id="fb-seletor-estrelas">';
  for (let i = 1; i <= 5; i++) {
    html += `<span class="estrela-selecionavel" data-valor="${i}" onclick="selecionarNotaFeedback(${i})">☆</span>`;
  }
  html += '</div>';
  return html;
}

function selecionarNotaFeedback(valor) {
  notaFeedbackSelecionada = (notaFeedbackSelecionada === valor) ? 0 : valor;
  atualizarSeletorEstrelasVisual();
}

function atualizarSeletorEstrelasVisual() {
  document.querySelectorAll('#fb-seletor-estrelas .estrela-selecionavel').forEach(el => {
    const v = parseInt(el.dataset.valor, 10);
    el.textContent = v <= notaFeedbackSelecionada ? '★' : '☆';
    el.classList.toggle('preenchida', v <= notaFeedbackSelecionada);
  });
}

let feedbacksAtuaisPerfil = [];
let feedbackEmEdicaoId = null;

function montarHtmlFeedbackUsuario(feedbacks) {
  feedbacksAtuaisPerfil = feedbacks;
  const itens = feedbacks.length === 0
    ? '<div class="vazio-perfil">Nenhum feedback registrado ainda.</div>'
    : feedbacks.map(f => {
        const tipo = f.tipo || 'Feedback';
        const classeTipo = tipo === 'Alinhamento' ? 'tipo-alinhamento' : 'tipo-feedback';
        const linkCanva = f.link_canva
          ? `<a href="${escaparHtml(f.link_canva)}" target="_blank" rel="noopener" class="link-canva-feedback">🔗 Ver slide no Canva</a>`
          : '';
        const editado = f.editado_em ? `<span class="editado-feedback" title="Editado por ${escaparHtml(f.editado_por || '')}"> (editado)</span>` : '';
        return `
        <div class="item-feedback">
          <div class="cabecalho-item-feedback">
            <span class="autor-feedback">
              <span class="badge-tipo-feedback ${classeTipo}">${tipo}</span>
              ${escaparHtml(f.autor_nome)} ${renderizarEstrelas(f.nota)}
            </span>
            <span class="data-feedback">${escaparHtml(f.criado_em)}${editado}</span>
          </div>
          <div class="texto-feedback">${escaparHtml(f.texto)}</div>
          ${linkCanva}
          <div class="acoes-item-feedback">
            <button class="btn-remover-feedback" onclick="editarFeedbackUsuario(${f.id})" title="Editar">Editar</button>
            <button class="btn-remover-feedback" onclick="removerFeedbackUsuario(${f.id})" title="Remover">Remover</button>
          </div>
        </div>
      `;
      }).join('');

  notaFeedbackSelecionada = 0;
  feedbackEmEdicaoId = null;
  return itens + `
    <div class="form-add-feedback" id="form-feedback-perfil">
      <label class="rotulo-nota-feedback" id="fb-titulo-form">Novo registro</label>
      <div class="seletor-tipo-feedback">
        <label class="opcao-tipo-feedback"><input type="radio" name="fb-tipo" value="Feedback" checked> Feedback</label>
        <label class="opcao-tipo-feedback"><input type="radio" name="fb-tipo" value="Alinhamento"> Alinhamento</label>
      </div>
      <label class="rotulo-nota-feedback">Nota geral (opcional)</label>
      ${montarSeletorEstrelas()}
      <textarea id="fb-texto" maxlength="2000" placeholder="Escreva um feedback sobre essa pessoa - só admins conseguem ver isso, a própria pessoa nunca vê."></textarea>
      <label class="rotulo-nota-feedback" style="margin-top:10px">Link do Canva (opcional)</label>
      <input type="text" id="fb-link-canva" placeholder="https://www.canva.com/design/...">
      <div class="erro-perfil" id="fb-erro"></div>
      <div style="display:flex; gap:8px; margin-top:8px">
        <button class="btn-mini" id="fb-btn-salvar" onclick="adicionarFeedbackUsuario()">+ Adicionar</button>
        <button class="btn-mini" id="fb-btn-cancelar" onclick="cancelarEdicaoFeedbackUsuario()" style="display:none">Cancelar</button>
      </div>
    </div>
  `;
}

function editarFeedbackUsuario(id) {
  const item = feedbacksAtuaisPerfil.find(f => f.id === id);
  if (!item) return;
  feedbackEmEdicaoId = id;
  document.querySelector(`input[name="fb-tipo"][value="${item.tipo || 'Feedback'}"]`).checked = true;
  document.getElementById('fb-texto').value = item.texto || '';
  document.getElementById('fb-link-canva').value = item.link_canva || '';
  notaFeedbackSelecionada = item.nota || 0;
  atualizarSeletorEstrelasVisual();
  document.getElementById('fb-titulo-form').innerText = 'Editando registro';
  document.getElementById('fb-btn-salvar').innerText = 'Salvar edição';
  document.getElementById('fb-btn-cancelar').style.display = 'inline-block';
  document.getElementById('fb-erro').innerText = '';
  document.getElementById('form-feedback-perfil').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function cancelarEdicaoFeedbackUsuario() {
  feedbackEmEdicaoId = null;
  notaFeedbackSelecionada = 0;
  document.getElementById('fb-texto').value = '';
  document.getElementById('fb-link-canva').value = '';
  atualizarSeletorEstrelasVisual();
  document.getElementById('fb-titulo-form').innerText = 'Novo registro';
  document.getElementById('fb-btn-salvar').innerText = '+ Adicionar';
  document.getElementById('fb-btn-cancelar').style.display = 'none';
  document.getElementById('fb-erro').innerText = '';
}

async function adicionarFeedbackUsuario() {
  const texto = document.getElementById('fb-texto').value.trim();
  const linkCanva = document.getElementById('fb-link-canva').value.trim();
  const tipo = document.querySelector('input[name="fb-tipo"]:checked').value;
  const erroEl = document.getElementById('fb-erro');
  erroEl.innerText = '';
  if (!texto) { erroEl.innerText = 'Escreva algo antes de adicionar.'; return; }
  if (linkCanva && !(linkCanva.startsWith('http://') || linkCanva.startsWith('https://'))) { erroEl.innerText = 'Link do Canva precisa começar com http:// ou https://'; return; }

  const editando = feedbackEmEdicaoId !== null;
  const url = editando ? '/api/feedback-usuario/editar' : '/api/feedback-usuario/criar';
  const corpo = editando
    ? 'id=' + encodeURIComponent(feedbackEmEdicaoId) + '&texto=' + encodeURIComponent(texto) +
      '&nota=' + encodeURIComponent(notaFeedbackSelecionada || '') + '&tipo=' + encodeURIComponent(tipo) +
      '&link_canva=' + encodeURIComponent(linkCanva)
    : 'usuario=' + encodeURIComponent(USUARIO_PERFIL) + '&texto=' + encodeURIComponent(texto) +
      '&nota=' + encodeURIComponent(notaFeedbackSelecionada || '') + '&tipo=' + encodeURIComponent(tipo) +
      '&link_canva=' + encodeURIComponent(linkCanva);

  try {
    const resp = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: corpo,
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || (editando ? 'Não foi possível salvar a edição.' : 'Não foi possível adicionar.'); return; }
    feedbackEmEdicaoId = null;
    carregarPerfil();
  } catch (e) {
    erroEl.innerText = 'Erro: ' + e;
  }
}

async function removerFeedbackUsuario(id) {
  if (!confirm('Remover esse feedback?')) return;
  try {
    const resp = await fetch('/api/feedback-usuario/excluir', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(id),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { alert(dados.erro || 'Não foi possível remover.'); return; }
    carregarPerfil();
  } catch (e) {
    alert('Erro: ' + e);
  }
}

async function adicionarHistoricoCarreira() {
  const cargo = document.getElementById('th-cargo').value.trim();
  const area = document.getElementById('th-area').value;
  const inicio = document.getElementById('th-inicio').value;
  const ehAtual = document.getElementById('th-atual').checked;
  const fim = ehAtual ? '' : document.getElementById('th-fim').value;
  const erroEl = document.getElementById('th-erro');
  erroEl.innerText = '';

  if (!cargo) { erroEl.innerText = 'Informe o cargo.'; return; }
  if (!inicio) { erroEl.innerText = 'Informe o mês/ano de início.'; return; }
  if (!ehAtual && !fim) { erroEl.innerText = 'Informe o mês/ano de fim, ou marque "cargo atual".'; return; }

  try {
    const resp = await fetch('/api/historico-carreira/criar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(USUARIO_PERFIL) + '&cargo=' + encodeURIComponent(cargo) +
            '&area=' + encodeURIComponent(area) + '&inicio=' + encodeURIComponent(inicio) +
            '&fim=' + encodeURIComponent(fim),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível adicionar.'; return; }
    carregarPerfil();
  } catch (e) {
    erroEl.innerText = 'Erro: ' + e;
  }
}

async function removerHistoricoCarreira(id) {
  if (!confirm('Remover essa entrada do histórico de carreira?')) return;
  try {
    const resp = await fetch('/api/historico-carreira/excluir', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(id),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { alert(dados.erro || 'Não foi possível remover.'); return; }
    carregarPerfil();
  } catch (e) {
    alert('Erro: ' + e);
  }
}

function alternarEdicaoHistorico() {
  const painel = document.getElementById('painel-historico-carreira');
  const botao = painel.querySelector('.btn-editar-historico');
  painel.classList.toggle('modo-edicao');
  if (botao) botao.classList.toggle('ativo');
}

function renderizarPerfil(dados) {
  const corpo = document.getElementById('perfil-corpo');

  if (!dados.pode_ver_completo) {
    corpo.innerHTML = `
      <div class="cabecalho-perfil">
        <div class="foto-perfil-wrap">${htmlFotoOuIniciais(dados)}</div>
        <div class="info-cabecalho-perfil"><h1>${escaparHtml(dados.nome)}</h1></div>
      </div>
      <div class="aviso-privado-perfil">Esse perfil é privado - só a própria pessoa ou um administrador conseguem ver mais detalhes.</div>
    `;
    return;
  }

  const classeAtribuicao = dados.atribuicao === 'Monitoramento' ? 'atribuicao-monitoramento'
    : dados.atribuicao === 'Suporte e Monitoramento' ? 'atribuicao-ambas' : 'atribuicao-suporte';
  const percentual = dados.percentual_horas_mes;
  const larguraBarra = percentual === null ? 0 : Math.min(percentual, 100);

  let blocoHoras;
  if (!dados.vinculado_movidesk) {
    blocoHoras = '<div class="vazio-perfil">Ainda não vinculado a um usuário do Movidesk (fale com um admin em "Editar usuário" → Horas/Vínculo) - sem isso não dá pra calcular horas trabalhadas nem tickets.</div>';
  } else if (dados.erro_horas) {
    blocoHoras = `<div class="vazio-perfil">Não foi possível calcular agora: ${escaparHtml(dados.erro_horas)}</div>`;
  } else {
    blocoHoras = `
      <div class="grade-metricas-perfil">
        <div class="metrica-perfil">
          <div class="valor-metrica">${percentual === null ? '–' : percentual + '%'}</div>
          <div class="rotulo-metrica">Do mês concluído</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.horas_trabalhadas_mes || '–'}</div>
          <div class="rotulo-metrica">Horas trabalhadas</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.meta_horas_mes || '–'}</div>
          <div class="rotulo-metrica">Meta do mês</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.tickets_mes ?? '–'}</div>
          <div class="rotulo-metrica">Tickets com ação</div>
        </div>
      </div>
      <div class="barra-progresso-perfil"><div class="preenchimento" style="width:${larguraBarra}%"></div></div>
      <button class="btn-mini" id="btn-comparar-mes-anterior" onclick="compararMesAnterior()" style="margin-top:14px">Comparar com mês anterior</button>
      <button class="btn-mini" id="btn-exportar-horas-perfil" onclick="exportarHorasPerfil()" style="margin-top:14px">Exportar Excel (mês atual)</button>
      <div id="comparacao-mes-anterior"></div>
    `;
  }

  // Indicadores gerais - DIFERENTE do bloco acima (que é sempre só do mês
  // atual), esse aqui olha o histórico INTEIRO da pessoa, sem filtro de
  // período (pedido explícito do solicitante).
  let blocoIndicadoresGerais;
  if (!dados.vinculado_movidesk) {
    blocoIndicadoresGerais = '<div class="vazio-perfil">Ainda não vinculado a um usuário do Movidesk.</div>';
  } else if (dados.erro_indicadores_gerais) {
    blocoIndicadoresGerais = `<div class="vazio-perfil">Não foi possível calcular agora: ${escaparHtml(dados.erro_indicadores_gerais)}</div>`;
  } else {
    blocoIndicadoresGerais = `
      <div class="grade-metricas-perfil">
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.tickets_acao_total ?? '–'}</div>
          <div class="rotulo-metrica">Tickets com ação (desde sempre)</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.total_horas_trabalhadas || '–'}</div>
          <div class="rotulo-metrica">Horas totais trabalhadas</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.primeira_atividade || '–'}</div>
          <div class="rotulo-metrica">Primeira atividade registrada</div>
        </div>
      </div>
    `;
  }

  const listaPeriodos = dados.periodos_futuros.length === 0
    ? '<div class="vazio-perfil">Nenhuma férias ou day off agendado.</div>'
    : dados.periodos_futuros.map(p => {
        const ehDayOff = p.tipo === 'day_off';
        return `
          <div class="linha-periodo-perfil">
            <span>${p.inicio} até ${p.fim}</span>
            <span class="badge-tipo-perfil ${ehDayOff ? 'day-off' : ''}">${ehDayOff ? 'Day Off' : 'Férias'}</span>
          </div>
        `;
      }).join('');

  const blocoHistoricoCarreira = montarHtmlTimelineCarreira(dados.historico_carreira || [], !!dados.sessao_admin);
  const blocoFeedback = dados.pode_ver_feedback ? montarHtmlFeedbackUsuario(dados.feedbacks || []) : '';

  corpo.innerHTML = `
    <div class="cabecalho-perfil">
      <div class="foto-perfil-wrap">
        ${htmlFotoOuIniciais(dados)}
        <div class="botao-trocar-foto" onclick="document.getElementById('perfil-input-foto').click()" title="Trocar foto">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
        </div>
      </div>
      <div class="info-cabecalho-perfil">
        <h1>${escaparHtml(dados.nome)}</h1>
        ${dados.cargo ? `<div class="cargo-perfil">${escaparHtml(dados.cargo)}</div>` : ''}
        <div class="badges-perfil">
          <span class="badge-perfil ${classeAtribuicao}">${escaparHtml(dados.atribuicao)}</span>
          <span class="badge-perfil">${dados.admin ? 'Administrador' : 'Visualização'}</span>
          ${!dados.ativo ? '<span class="badge-perfil">Desativado</span>' : ''}
        </div>
      </div>
    </div>

    <div class="painel-perfil">
      <h2>Horas trabalhadas neste mês</h2>
      ${blocoHoras}
    </div>

    <div class="painel-perfil">
      <h2>Indicadores gerais</h2>
      ${blocoIndicadoresGerais}
    </div>

    <div class="painel-perfil">
      <h2>Férias &amp; Day Off agendados</h2>
      ${listaPeriodos}
    </div>

    <div class="painel-perfil" id="painel-historico-carreira">
      <h2 class="cabecalho-com-acao">
        <span>Histórico na Empresa</span>
        ${dados.sessao_admin ? '<button class="btn-editar-historico" onclick="alternarEdicaoHistorico()" title="Editar histórico">✏️</button>' : ''}
      </h2>
      ${blocoHistoricoCarreira}
    </div>

    ${dados.pode_ver_feedback ? `
    <div class="painel-perfil painel-feedback">
      <h2>Feedback (privado)</h2>
      <div class="aviso-feedback">🔒 Visível só pra admins da mesma equipe - a própria pessoa nunca vê isso.</div>
      ${blocoFeedback}
    </div>
    ` : ''}
  `;
}

async function carregarPerfil() {
  try {
    const resp = await fetch('/api/perfil/' + encodeURIComponent(USUARIO_PERFIL));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('perfil-erro').innerText = dados.erro || 'Não foi possível carregar o perfil.';
      return;
    }
    document.getElementById('perfil-erro').innerText = '';
    renderizarPerfil(dados);
  } catch (e) {
    document.getElementById('perfil-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

async function exportarHorasPerfil() {
  const botao = document.getElementById('btn-exportar-horas-perfil');
  const textoOriginal = botao.innerText;
  botao.disabled = true;
  botao.innerText = 'Gerando...';
  try {
    const resp = await fetch('/api/perfil/' + encodeURIComponent(USUARIO_PERFIL) + '/exportar-horas');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (!resp.ok) {
      let msg = 'Erro ao gerar a exportação.';
      try { msg = (await resp.json()).erro || msg; } catch (e) {}
      document.getElementById('perfil-erro').innerText = msg;
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `horas_${USUARIO_PERFIL}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    document.getElementById('perfil-erro').innerText = 'Erro ao exportar: ' + e;
  } finally {
    botao.disabled = false;
    botao.innerText = textoOriginal;
  }
}

async function compararMesAnterior() {
  const botao = document.getElementById('btn-comparar-mes-anterior');
  const container = document.getElementById('comparacao-mes-anterior');
  botao.disabled = true;
  botao.innerText = 'Carregando...';
  try {
    const resp = await fetch('/api/perfil/' + encodeURIComponent(USUARIO_PERFIL) + '/mes-anterior');
    const dados = await resp.json();
    if (!dados.ok) {
      container.innerHTML = `<div class="vazio-perfil">${escaparHtml(dados.erro || 'Não foi possível comparar.')}</div>`;
      botao.style.display = 'none';
      return;
    }
    if (!dados.vinculado_movidesk || dados.erro_horas || dados.percentual_horas_mes === null) {
      container.innerHTML = `<div class="vazio-perfil">Sem dados de ${escaparHtml(dados.nome_mes)} pra comparar.</div>`;
      botao.style.display = 'none';
      return;
    }
    container.innerHTML = `
      <div class="comparacao-mes-anterior-perfil">
        <div class="titulo-comparacao-perfil">${escaparHtml(dados.nome_mes)}</div>
        <div class="grade-metricas-perfil">
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.percentual_horas_mes}%</div>
            <div class="rotulo-metrica">Do mês concluído</div>
          </div>
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.horas_trabalhadas_mes || '–'}</div>
            <div class="rotulo-metrica">Horas trabalhadas</div>
          </div>
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.meta_horas_mes || '–'}</div>
            <div class="rotulo-metrica">Meta do mês</div>
          </div>
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.tickets_mes ?? '–'}</div>
            <div class="rotulo-metrica">Tickets com ação</div>
          </div>
        </div>
      </div>
    `;
    botao.style.display = 'none';
  } catch (e) {
    container.innerHTML = `<div class="vazio-perfil">Erro ao comparar: ${escaparHtml(String(e))}</div>`;
    botao.disabled = false;
    botao.innerText = 'Comparar com mês anterior';
  }
}

document.getElementById('perfil-input-foto').addEventListener('change', async (ev) => {
  const arquivo = ev.target.files[0];
  if (!arquivo) return;
  const leitor = new FileReader();
  leitor.onload = async () => {
    const resp = await fetch('/api/usuarios/upload-foto', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(USUARIO_PERFIL) + '&foto=' + encodeURIComponent(leitor.result),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('perfil-erro').innerText = dados.erro || 'Não foi possível trocar a foto.';
      return;
    }
    carregarPerfil();
  };
  leitor.readAsDataURL(arquivo);
});

carregarPerfil();
</script>
</body>
</html>
"""


def _montar_perfil_html(sessao: dict, usuario_perfil: str) -> str:
    return (
        _PERFIL_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Perfil"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__USUARIO_PERFIL__", usuario_perfil.replace("\\", "\\\\").replace('"', '\\"'))
    )


def _montar_ferias_html(sessao: dict) -> str:
    if sessao["admin"]:
        botao_nova = '<button class="btn-accent" onclick="abrirModalNovaFerias()">+ Novo período</button>'
        modal_nova = """
  <div class="modal-fundo" id="modal-nova-ferias">
    <div class="modal">
      <h3>Novo período</h3>
      <label>Tipo</label>
      <div class="seletor-tipo-fer">
        <button type="button" id="fer-botao-tipo-ferias" class="ativo" onclick="selecionarTipoModal('ferias')">Férias</button>
        <button type="button" id="fer-botao-tipo-dayoff" onclick="selecionarTipoModal('day_off')">Day Off</button>
        <button type="button" id="fer-botao-tipo-atestado" onclick="selecionarTipoModal('atestado')">Atestado</button>
      </div>
      <label>Pessoa</label>
      <select id="fer-select-usuario"><option value="">Selecione...</option></select>
      <label>Data início</label>
      <input type="date" id="fer-input-inicio">
      <label>Data fim</label>
      <input type="date" id="fer-input-fim">
      <div class="erro-modal" id="fer-modal-erro"></div>
      <div class="acoes-modal">
        <button class="btn-accent" onclick="salvarNovaFerias()" style="flex:1">Salvar</button>
        <button onclick="fecharModalNovaFerias()" style="flex:1">Cancelar</button>
      </div>
    </div>
  </div>
"""
    else:
        botao_nova = ""
        modal_nova = ""

    return (
        _FERIAS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Calendário de Férias"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__BOTAO_NOVA_FERIAS__", botao_nova)
        .replace("__MODAL_NOVA_FERIAS__", modal_nova)
        .replace("__EH_ADMIN_JS__", "true" if sessao["admin"] else "false")
    )

_LOGS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Logs</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-logs { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                     gap: 14px; max-width: 1000px; margin: 0 auto 20px auto; }
  .cabecalho-logs h1 { font-size: 20px; margin: 0 0 4px 0;
                        background: var(--gradiente-marca); -webkit-background-clip: text;
                        background-clip: text; color: transparent; }
  .cabecalho-logs .sub { color: var(--fg-dim); font-size: 12.5px; }
  .seletor-logs { display: flex; align-items: end; gap: 10px; }
  .seletor-logs label { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 5px;
                         text-transform: uppercase; letter-spacing: .04em; }
  .seletor-logs select { min-width: 320px; padding: 8px 30px 8px 12px; }

  .painel-logs { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                 border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
                 max-width: 1000px; margin: 0 auto 20px auto; }
  .conteudo-log { background: rgba(0,0,0,.35); border: 1px solid var(--border); border-radius: 10px;
                   padding: 14px 16px; font-family: 'Consolas', 'Courier New', monospace; font-size: 11.5px;
                   line-height: 1.6; white-space: pre-wrap; word-break: break-word; max-height: 65vh;
                   overflow-y: auto; color: var(--fg); }
  .erro-logs { color: var(--erro); font-size: 12.5px; margin: 10px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-logs">
      <div>
        <h1>Logs</h1>
        <div class="sub">Últimas 1000 linhas de cada log - os do PDA ficam em logs/ na pasta do programa; os da Aplicação Monitoramento vêm direto de a pasta configurada em PDA_LOGS_MONITORAMENTO.</div>
      </div>
      <div class="seletor-logs">
        <div>
          <label>Card</label>
          <select id="logs-seletor" onchange="carregarLogSelecionado()">
            __OPCOES_LOGS__
          </select>
        </div>
        <button class="btn-mini" onclick="carregarLogSelecionado()">Atualizar</button>
      </div>
    </div>

    <div class="erro-logs" id="logs-erro"></div>

    <div class="painel-logs">
      <div class="conteudo-log" id="logs-conteudo">Carregando...</div>
    </div>
  </div>

  __FOOTER__

<script>
async function carregarLogSelecionado() {
  const nomeCard = document.getElementById('logs-seletor').value;
  const conteudoEl = document.getElementById('logs-conteudo');
  const erroEl = document.getElementById('logs-erro');
  conteudoEl.innerText = 'Carregando...';
  erroEl.innerText = '';
  try {
    const resp = await fetch('/api/logs?card=' + encodeURIComponent(nomeCard));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar.';
      conteudoEl.innerText = '';
      return;
    }
    if (dados.linhas.length === 0) {
      conteudoEl.innerText = dados.aviso || 'Ainda não há nada registrado nesse log.';
      return;
    }
    conteudoEl.innerText = dados.linhas.join('\\n');
    conteudoEl.scrollTop = conteudoEl.scrollHeight;
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
    conteudoEl.innerText = '';
  }
}

carregarLogSelecionado();
</script>
</body>
</html>
"""


def _montar_logs_html(sessao: dict) -> str:
    opcoes = "".join(
        f'<option value="{nome}">{nome}</option>' for nome in LOGS_DISPONIVEIS
    )
    return (
        _LOGS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Logs"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__OPCOES_LOGS__", opcoes)
    )


_MANUTENCAO_USUARIOS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção de Usuários</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-mu { max-width: 1200px; margin: 0 auto 18px auto; }
  .cabecalho-mu h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-mu .sub { color: var(--fg-dim); font-size: 12.5px; }
  .aviso-beta-mu { max-width: 1200px; margin: 0 auto 22px auto; background: rgba(241,76,76,.08);
                   border: 1px solid rgba(241,76,76,.3); border-radius: 10px; padding: 12px 16px;
                   font-size: 12.5px; color: var(--fg); line-height: 1.6; }
  .aviso-beta-mu b { color: var(--erro); }

  /* Seletor de ação - pills grandes, uma tela central pra tudo que
     envolve identidade de usuário (PDA + Movidesk + banco), em vez de
     um formulariozinho apertado - pedido explícito do solicitante de repensar
     o visual dessa tela inteira. */
  .seletor-acao-mu { display: flex; gap: 10px; max-width: 1200px; margin: 0 auto 24px auto; flex-wrap: wrap; }
  .pill-acao-mu { flex: 1; min-width: 160px; text-align: center; padding: 14px 12px; border-radius: 12px;
                  border: 1px solid var(--border); background: var(--bg-panel); backdrop-filter: blur(10px);
                  cursor: pointer; transition: all .15s; }
  .pill-acao-mu:hover { border-color: var(--border-forte); }
  .pill-acao-mu .icone-pill-mu { display: block; font-size: 20px; margin-bottom: 6px; }
  .pill-acao-mu .rotulo-pill-mu { font-size: 12.5px; font-weight: 700; color: var(--fg-dim); }
  .pill-acao-mu.ativa { border-color: var(--teal); background: rgba(45,184,207,.1); }
  .pill-acao-mu.ativa .rotulo-pill-mu { color: var(--teal); }

  .secao-mu { display: none; }
  .secao-mu.ativa { display: block; }

  .grade-mu { display: grid; grid-template-columns: 380px 1fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
  @media (max-width: 900px) { .grade-mu { grid-template-columns: 1fr; } }

  .painel-mu { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; }
  .painel-mu h3 { margin: 0 0 14px 0; font-size: 13px; color: var(--teal); text-transform: uppercase; letter-spacing: .04em; }
  .painel-mu label { display: block; font-size: 11px; color: var(--fg-dim); margin: 14px 0 5px 0;
                      text-transform: uppercase; letter-spacing: .04em; }
  .painel-mu label:first-of-type { margin-top: 0; }
  .painel-mu input[type="text"], .painel-mu input[type="email"], .painel-mu input[type="time"],
  .painel-mu select { width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .painel-mu input:focus, .painel-mu select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .campo-radio { display: flex; align-items: center; gap: 8px; margin-top: 8px; font-size: 13px; }
  .campo-radio:first-of-type { margin-top: 0; }
  .campo-radio input { margin: 0; }
  .campo-checkbox { display: flex; align-items: center; gap: 8px; font-size: 13px; }
  .campo-checkbox input { margin: 0; }
  .dica-senha-padrao { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.5; }
  .acoes-mu { display: flex; flex-direction: column; gap: 8px; margin-top: 18px; }
  .erro-mu { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .status-mu { font-size: 12px; color: var(--fg-dim); margin-top: 6px; }

  table.tabela-mu { width: 100%; border-collapse: collapse; }
  table.tabela-mu th, table.tabela-mu td { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--border); font-size: 12.5px; }
  table.tabela-mu th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  table.tabela-mu tr:last-child td { border-bottom: none; }
  .badge-status-mu { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; }
  .badge-status-mu.success { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-status-mu.skipped { background: rgba(220,220,170,.15); color: var(--run); }
  .badge-status-mu.error { background: rgba(241,76,76,.15); color: var(--erro); }
  .vazio-mu { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .resumo-final-mu { margin-top: 14px; font-size: 12.5px; color: var(--fg-dim); }
  .resumo-final-mu b { color: var(--fg); }

  /* Permissões / Vínculo Movidesk */
  .grade-permissoes-mu { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 18px; margin-top: 10px; }
  .grade-permissoes-mu .campo-checkbox { font-size: 12.5px; }
  .nota-admin-mu { font-size: 10px; color: var(--fg-dim); margin-left: 6px; }
  .linha-dupla-mu, .linha-tripla-mu { display: grid; gap: 12px; }
  .linha-dupla-mu { grid-template-columns: 1fr 1fr; }
  .linha-tripla-mu { grid-template-columns: 1fr 1fr 1fr; }
  .dias-semana-mu { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 6px; }
  .dia-check-mu { display: flex; align-items: center; gap: 5px; font-size: 11.5px; color: var(--fg-dim);
                    border: 1px solid var(--border); border-radius: 7px; padding: 5px 9px; cursor: pointer; }
  .dia-check-mu input { width: auto; margin: 0; }
  .dia-check-mu:has(input:checked) { border-color: var(--teal); color: var(--fg); }
  .resumo-pessoa-mu { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid var(--border); margin-bottom: 14px; }
  .resumo-pessoa-mu .iniciais-mu { width: 40px; height: 40px; border-radius: 50%; background: var(--gradiente-marca);
       display: flex; align-items: center; justify-content: center; font-weight: 800; color: #08090c; font-size: 14px; flex-shrink: 0; }
  .resumo-pessoa-mu .foto-mu { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; flex-shrink: 0; }
  .resumo-pessoa-mu .nome-mu { font-size: 14px; font-weight: 700; }
  .resumo-pessoa-mu .login-mu { font-size: 11.5px; color: var(--fg-dim); }
  .linha-resumo-mu { display: flex; justify-content: space-between; padding: 6px 0; font-size: 12.5px; border-bottom: 1px dashed var(--border); }
  .linha-resumo-mu:last-child { border-bottom: none; }
  .linha-resumo-mu span:first-child { color: var(--fg-dim); }

  /* Aba Editar - lista clicável, perfil de edição, zona de risco */
  table.tabela-mu tbody tr[onclick]:hover { background: rgba(45,184,207,.06); }
  .zona-risco-mu { border-color: rgba(241,76,76,.3) !important; background: rgba(241,76,76,.04) !important; }
  .btn-perigo-mu { border-color: var(--erro) !important; color: var(--erro) !important; }
  .btn-perigo-mu:hover { background: rgba(241,76,76,.12) !important; }
  @media (max-width: 900px) {
    #editar-visao-perfil .grade-mu { grid-template-columns: 1fr !important; }
  }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-mu">
      <h1>Manutenção de Usuários</h1>
      <div class="sub">Central de identidade: login no PDA, vínculo com o Movidesk e acesso em banco de cada cliente - tudo num só lugar.</div>
    </div>

    <div class="aviso-beta-mu">
      <b>Atenção:</b> cadastrar/desativar roda direto em bancos de PRODUÇÃO de clientes reais (INSERT/UPDATE de
      verdade, sem ambiente de teste) e também chama a API do Movidesk de verdade (cria/desativa a pessoa). Gere a
      prévia primeiro, revise a lista de alvos, e só confirme a execução se estiver tudo certo. Toda execução
      fica registrada em log de auditoria (logs/manutencao_usuarios_*.jsonl).
    </div>

    <div class="seletor-acao-mu">
      <div class="pill-acao-mu ativa" data-acao="cad" onclick="selecionarAcaoMU('cad')">
        <span class="icone-pill-mu">➕</span><span class="rotulo-pill-mu">Cadastrar usuário</span>
      </div>
      <div class="pill-acao-mu" data-acao="exc" onclick="selecionarAcaoMU('exc')">
        <span class="icone-pill-mu">🚫</span><span class="rotulo-pill-mu">Desativar usuário</span>
      </div>
      <div class="pill-acao-mu" data-acao="editar" onclick="selecionarAcaoMU('editar')">
        <span class="icone-pill-mu">✏️</span><span class="rotulo-pill-mu">Editar usuários</span>
      </div>
    </div>

    <!-- Cadastrar / Desativar - mesmo fluxo de sempre (banco + Movidesk +
         login PDA opcional), só reorganizado visualmente -->
    <div id="secao-cad-exc" class="secao-mu ativa">
      <div class="grade-mu">
        <div class="painel-mu">
          <h3 id="titulo-form-cadexc">Cadastrar usuário</h3>
          <label>Área</label>
          <label class="campo-radio" style="margin-top:0">
            <input type="radio" name="mu-area" value="suporte" checked> Suporte
          </label>
          <label class="campo-radio">
            <input type="radio" name="mu-area" value="monitoramento"> Monitoramento
          </label>
          <label class="campo-radio">
            <input type="radio" name="mu-area" value="todos"> Todas
          </label>

          <label>Nome do usuário</label>
          <input type="text" id="mu-nome" maxlength="40" placeholder="Ex.: Maria Souza">

          <label>Login</label>
          <input type="text" id="mu-login" maxlength="255" placeholder="Ex.: maria.souza@example.com">

          <div class="dica-senha-padrao" id="mu-dica-senha">
            Senha inicial padrão continua sendo '__SENHA_PADRAO__' pros bancos E pro Movidesk (já vem fixa).
            Oriente a pessoa a trocar assim que possível. O cadastro/desativação da PESSOA no Movidesk
            (perfil de acesso conforme a Área escolhida acima) entra automaticamente, sem precisar marcar nada.
          </div>

          <div class="campo-checkbox" style="margin-top:16px">
            <input type="checkbox" id="mu-incluir-pda" onchange="atualizarCamposCondicionaisMU()">
            <label for="mu-incluir-pda" style="display:inline; margin:0; text-transform:none; font-size:13px; letter-spacing:normal">Também criar/desativar o login desse usuário no PDA</label>
          </div>
          <div id="mu-campos-pda" style="display:none">
            <label>Usuário do PDA</label>
            <input type="text" id="mu-usuario-pda" placeholder="Ex.: maria.souza">
            <label id="mu-label-senha-pda">Senha do login PDA</label>
            <input type="text" id="mu-senha-pda" placeholder="mínimo 4 caracteres">
            <div class="dica-senha-padrao">
              Login criado no PDA sem nenhuma permissão extra (nem admin) - ajuste depois na aba "Editar usuários" se precisar.
            </div>
          </div>

          <div class="campo-checkbox" id="mu-campo-boas-vindas" style="margin-top:10px">
            <input type="checkbox" id="mu-enviar-boas-vindas">
            <label for="mu-enviar-boas-vindas" style="display:inline; margin:0; text-transform:none; font-size:13px; letter-spacing:normal">Enviar e-mail de boas-vindas pro novo colaborador</label>
          </div>
          <div class="dica-senha-padrao" id="mu-dica-boas-vindas">
            Enviado pro endereço preenchido em "Login" acima, com o login/senha de acesso, o link do PDA e o
            aviso de que só funciona dentro da VPN da empresa.
          </div>

          <div class="acoes-mu">
            <button class="btn-accent" id="btn-mu-previa" onclick="gerarPreviaManutencaoUsuarios()">Gerar prévia</button>
            <button class="btn-mini" id="btn-mu-executar" onclick="confirmarExecucaoManutencaoUsuarios()" disabled>Confirmar e executar</button>
          </div>
          <div class="erro-mu" id="mu-erro"></div>
          <div class="status-mu" id="mu-status">Preencha os dados e gere a prévia.</div>
        </div>

        <div class="painel-mu">
          <h3 id="mu-titulo-workspace">Prévia de execução</h3>
          <div id="mu-workspace">
            <div class="vazio-mu">Gere a prévia pra ver os alvos que serão afetados.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Editar usuários - CENTRAL de identidade: lista + filtro, e a
         partir de cada pessoa dá pra editar TUDO (nome, senha, papel,
         equipe, permissões, vínculo Movidesk, status nos sistemas) e,
         se precisar, ir direto pra desativação completa (que reaproveita
         o mesmo fluxo de banco+Movidesk+PDA já usado na aba Desativar). -->
    <div id="secao-editar" class="secao-mu">

      <!-- VISÃO 1: lista + filtro -->
      <div id="editar-visao-lista">
        <div class="painel-mu" style="max-width:1200px; margin:0 auto 20px auto">
          <h3>Filtrar usuários</h3>
          <div class="linha-dupla-mu">
            <div>
              <label style="margin-top:0">Nome ou login</label>
              <input type="text" id="filtro-nome-mu" placeholder="Buscar por nome ou login..." oninput="filtrarListaEditarMU()">
            </div>
            <div>
              <label style="margin-top:0">Equipe</label>
              <select id="filtro-equipe-mu" onchange="filtrarListaEditarMU()">
                <option value="">Todas as equipes</option>
                <option value="Suporte">Suporte</option>
                <option value="Monitoramento">Monitoramento</option>
              </select>
            </div>
          </div>
        </div>

        <div class="painel-mu" style="max-width:1200px; margin:0 auto">
          <h3>Usuários (<span id="contagem-lista-mu">0</span>)</h3>
          <table class="tabela-mu">
            <thead>
              <tr><th>Login</th><th>Nome</th><th>Papel</th><th>Equipe</th><th>Status</th><th>Vínculo Movidesk</th></tr>
            </thead>
            <tbody id="corpo-lista-editar-mu"></tbody>
          </table>
          <div id="lista-editar-vazio-mu" class="vazio-mu" style="display:none">Nenhum usuário encontrado com esse filtro.</div>
        </div>
      </div>

      <!-- VISÃO 2: perfil de uma pessoa (some por padrão) -->
      <div id="editar-visao-perfil" style="display:none; max-width:1200px; margin:0 auto">
        <button class="btn-mini" onclick="voltarParaListaMU()" style="margin-bottom:18px">← Voltar pra lista</button>

        <div class="painel-mu" style="margin-bottom:20px">
          <div style="display:flex; align-items:center; justify-content:space-between; gap:12px; flex-wrap:wrap">
            <div class="resumo-pessoa-mu" id="perfil-cabecalho-mu" style="border-bottom:none; margin-bottom:0; padding-bottom:0; flex:1"></div>
            <a class="btn-mini" id="link-ver-perfil-mu" href="#" target="_blank" rel="noopener" style="text-decoration:none; white-space:nowrap">Ver perfil completo →</a>
          </div>
        </div>

        <div class="grade-mu" style="grid-template-columns: 1fr 1fr; max-width:none">
          <div>
            <!-- Dados gerais -->
            <div class="painel-mu" style="margin-bottom:20px">
              <h3>Dados gerais</h3>
              <label style="margin-top:0">Nome</label>
              <input type="text" id="ed-nome" maxlength="60">
              <label>E-mail pessoal</label>
              <input type="email" id="ed-email" placeholder="maria.souza@example.com">
              <label>Data de início na empresa (opcional)</label>
              <input type="date" id="ed-data-inicio">
              <div class="dica-senha-padrao">Usada pros alertas automáticos de 45 e 90 dias de empresa.</div>
              <label>Papel</label>
              <select id="ed-papel" onchange="atualizarTravasPermissoesMU()">
                <option value="view">Visualização</option>
                <option value="admin">Administrador</option>
              </select>
              <label>Equipe</label>
              <select id="ed-atribuicao">
                <option value="Suporte">Suporte</option>
                <option value="Monitoramento">Monitoramento</option>
                <option value="Suporte e Monitoramento">Suporte e Monitoramento (escala 12x36)</option>
              </select>
              <label>Status do login no PDA</label>
              <select id="ed-status">
                <option value="true">Ativo</option>
                <option value="false">Desativado</option>
              </select>
              <div class="acoes-mu">
                <button class="btn-accent" onclick="salvarDadosGeraisMU()">Salvar dados gerais</button>
              </div>
              <div class="erro-mu" id="ed-erro-geral-mu"></div>
              <div class="status-mu" id="ed-status-geral-mu"></div>

              <div style="margin-top:18px; padding-top:16px; border-top:1px dashed var(--border)">
                <button class="btn-mini" onclick="enviarBoasVindasTesteMU()">✉️ Enviar e-mail de boas-vindas</button>
                <div class="dica-senha-padrao">Envia pro e-mail cadastrado acima, com a senha ATUAL dessa pessoa no PDA. Salve o e-mail antes, se acabou de preencher.</div>
                <div class="erro-mu" id="ed-erro-boasvindas-mu"></div>
                <div class="status-mu" id="ed-status-boasvindas-mu"></div>
              </div>

              <div style="margin-top:18px; padding-top:16px; border-top:1px dashed rgba(241,76,76,.3)">
                <label style="margin-top:0; color:var(--erro)">Renomear usuário (login)</label>
                <input type="text" id="ed-usuario-novo" placeholder="Ex.: maria.souza">
                <div class="dica-senha-padrao">
                  Troca o login dessa pessoa em TUDO (permissões, feedbacks, histórico de carreira) - a sessão
                  ativa dela é encerrada e precisa logar de novo com o nome novo. Use pra igualar o usuário do
                  PDA com o dos webmonitors.
                </div>
                <div class="acoes-mu">
                  <button class="btn-mini btn-perigo-mu" onclick="renomearUsuarioMU()">Renomear</button>
                </div>
                <div class="erro-mu" id="ed-erro-renomear-mu"></div>
                <div class="status-mu" id="ed-status-renomear-mu"></div>
              </div>
            </div>

            <!-- Senha -->
            <div class="painel-mu" style="margin-bottom:20px">
              <h3>Senha</h3>
              <label style="margin-top:0">Nova senha</label>
              <input type="text" id="ed-nova-senha" placeholder="mínimo 4 caracteres">
              <label>Confirmar nova senha</label>
              <input type="text" id="ed-confirma-senha">
              <div class="acoes-mu">
                <button class="btn-mini" onclick="salvarSenhaEdicaoMU()">Trocar senha</button>
              </div>
              <div class="erro-mu" id="ed-erro-senha-mu"></div>
              <div class="status-mu" id="ed-status-senha-mu"></div>
            </div>

            <!-- Permissões especiais -->
            <div class="painel-mu">
              <h3>Permissões especiais</h3>
              <div class="grade-permissoes-mu">
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_manutencao_alertas"><label style="margin:0; text-transform:none; font-size:12.5px">Manutenção de Alertas</label></div>
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_relatorios_shein"><label style="margin:0; text-transform:none; font-size:12.5px">Relatórios Shein</label></div>
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_dash_financeiro"><label style="margin:0; text-transform:none; font-size:12.5px">Dash Financeiro</label></div>
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_manutencao_rejeicoes"><label style="margin:0; text-transform:none; font-size:12.5px">Manutenção de Rejeições</label></div>
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_manutencao_relatorios"><label style="margin:0; text-transform:none; font-size:12.5px">Manutenção de Relatórios</label></div>
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_dados_sensiveis"><label style="margin:0; text-transform:none; font-size:12.5px">Dados Sensíveis<span class="nota-admin-mu">(nunca automático)</span></label></div>
                <div class="campo-checkbox"><input type="checkbox" id="perm-pode_manutencao_usuarios"><label style="margin:0; text-transform:none; font-size:12.5px">Esta tela (Manutenção de Usuários)<span class="nota-admin-mu">(nunca automático)</span></label></div>
              </div>
              <div class="acoes-mu">
                <button class="btn-accent" onclick="salvarPermissoesMU()">Salvar permissões</button>
              </div>
              <div class="erro-mu" id="perm-erro-mu"></div>
              <div class="status-mu" id="perm-status-mu"></div>
            </div>
          </div>

          <div>
            <!-- Vínculo Movidesk -->
            <div class="painel-mu" style="margin-bottom:20px">
              <h3>Vínculo com o Movidesk</h3>
              <label style="margin-top:0">Vincular a um usuário da tabela "usuarios" (banco Movidesk)</label>
              <div style="display:flex; gap:8px; align-items:flex-start">
                <select id="vinc-select-movidesk" onchange="aoTrocarUsuarioVinculadoMU()" style="flex:1">
                  <option value="">Selecione ou pesquise...</option>
                </select>
                <button class="btn-mini" onclick="atualizarListaMovideskMU()" title="Reconsultar o banco - útil se uma pessoa nova ainda não aparece na lista" style="white-space:nowrap">🔄 Atualizar lista</button>
              </div>
              <div class="dica-senha-padrao" id="vinc-status-lista-mu">
                Ao vincular, os dados de horas trabalhadas (cargo, escala, horário, dias) ficam associados a esse
                login do PDA. Sem vínculo, a pessoa não tem meta de horas calculada corretamente.
              </div>

              <div id="vinc-campos-movidesk-mu" style="display:none">
                <div class="linha-dupla-mu" style="margin-top:14px">
                  <div>
                    <label>Cargo</label>
                    <input type="text" id="vinc-cargo">
                  </div>
                  <div>
                    <label>E-mail</label>
                    <input type="email" id="vinc-email">
                  </div>
                </div>
                <div class="linha-tripla-mu">
                  <div>
                    <label>Escala</label>
                    <select id="vinc-escala">
                      <option value="">Sem escala definida</option>
                      <option value="5x2">5x2</option>
                      <option value="6x1">6x1</option>
                      <option value="12x36">12x36</option>
                      <option value="ESTAGIO">Estágio</option>
                      <option value="ESCALA_ARA">Escala ARA</option>
                    </select>
                  </div>
                  <div>
                    <label>Hora início</label>
                    <input type="time" id="vinc-horainicio">
                  </div>
                  <div>
                    <label>Hora fim</label>
                    <input type="time" id="vinc-horafim">
                  </div>
                </div>
                <label>Dias trabalhados</label>
                <div class="dias-semana-mu">
                  <label class="dia-check-mu"><input type="checkbox" value="Monday"> Seg</label>
                  <label class="dia-check-mu"><input type="checkbox" value="Tuesday"> Ter</label>
                  <label class="dia-check-mu"><input type="checkbox" value="Wednesday"> Qua</label>
                  <label class="dia-check-mu"><input type="checkbox" value="Thursday"> Qui</label>
                  <label class="dia-check-mu"><input type="checkbox" value="Friday"> Sex</label>
                  <label class="dia-check-mu"><input type="checkbox" value="Saturday"> Sáb</label>
                  <label class="dia-check-mu"><input type="checkbox" value="Sunday"> Dom</label>
                </div>
              </div>

              <div class="acoes-mu">
                <button class="btn-accent" onclick="salvarVinculoMovideskMU()">Salvar vínculo</button>
              </div>
              <div class="erro-mu" id="vinc-erro-mu"></div>
              <div class="status-mu" id="vinc-status-mu"></div>
            </div>

            <!-- Diagnóstico / status nos sistemas -->
            <div class="painel-mu" style="margin-bottom:20px">
              <h3>Status nos sistemas</h3>
              <label style="margin-top:0">Login pra verificar (Movidesk/bancos)</label>
              <input type="text" id="diag-login" placeholder="Ex.: maria.souza@example.com">
              <div class="acoes-mu">
                <button class="btn-mini" id="btn-diag-verificar" onclick="verificarDiagnosticoMU()">Verificar status</button>
              </div>
              <div class="erro-mu" id="diag-erro-mu"></div>
              <div class="status-mu" id="diag-status-mu"></div>
              <div id="diag-resultado-mu" style="margin-top:14px">
                <div class="vazio-mu">Clique em "Verificar status" pra cruzar Movidesk + todos os bancos.</div>
              </div>
            </div>

            <!-- Zona de risco -->
            <div class="painel-mu zona-risco-mu">
              <h3 style="color:var(--erro)">Zona de risco</h3>
              <p style="font-size:12.5px; color:var(--fg-dim); margin:0 0 14px 0; line-height:1.5">
                Desativa essa pessoa em TODOS os sistemas de uma vez (banco de cada cliente + Movidesk + este
                login do PDA), usando o mesmo fluxo de prévia e confirmação de sempre - inclusive o
                acompanhamento do resultado alvo por alvo.
              </p>
              <button class="btn-mini btn-perigo-mu" onclick="irParaDesativarComDadosMU()">Desativar este usuário em todos os sistemas</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
let previaAlvosManutencaoUsuarios = [];
let usuariosCarregadosMU = [];
let usuariosMovideskCarregadosMU = [];
atualizarCamposCondicionaisMU();
carregarListasBaseMU();

async function carregarListasBaseMU() {
  try {
    const [respUsuarios, respMovidesk] = await Promise.all([
      fetch('/api/usuarios'),
      fetch('/api/usuarios-movidesk'),
    ]);
    if (respUsuarios.status === 401) { window.location.href = '/login'; return; }
    const dadosUsuarios = await respUsuarios.json();
    usuariosCarregadosMU = dadosUsuarios.usuarios || [];

    const dadosMovidesk = await respMovidesk.json();
    if (dadosMovidesk.ok) usuariosMovideskCarregadosMU = dadosMovidesk.registros;

    const opcoesMovidesk = '<option value="">Selecione ou pesquise...</option>' +
      usuariosMovideskCarregadosMU.map(m => `<option value="${m.id}">${escaparHtmlMU(m.nome)}${m.cargo ? ' · ' + escaparHtmlMU(m.cargo) : ''}</option>`).join('');
    document.getElementById('vinc-select-movidesk').innerHTML = opcoesMovidesk;

    filtrarListaEditarMU();
  } catch (e) {
    console.warn('Erro ao carregar listas base da Manutenção de Usuários:', e);
  }
}

// -- Atualizar a lista do Movidesk SEM recarregar a página inteira e SEM
// mexer em quem já está vinculado - reconsulta o banco na hora
// (/api/usuarios-movidesk já é sempre uma consulta ao vivo, nunca cache),
// só preserva a seleção atual depois de reconstruir as opções.
async function atualizarListaMovideskMU() {
  const statusEl = document.getElementById('vinc-status-lista-mu');
  const selecaoAtual = document.getElementById('vinc-select-movidesk').value;
  statusEl.innerText = 'Consultando o banco...';
  try {
    const resp = await fetch('/api/usuarios-movidesk');
    const dados = await resp.json();
    if (!dados.ok) { statusEl.innerText = dados.erro || 'Não foi possível atualizar a lista.'; return; }
    usuariosMovideskCarregadosMU = dados.registros;

    const opcoesMovidesk = '<option value="">Selecione ou pesquise...</option>' +
      usuariosMovideskCarregadosMU.map(m => `<option value="${m.id}">${escaparHtmlMU(m.nome)}${m.cargo ? ' · ' + escaparHtmlMU(m.cargo) : ''}</option>`).join('');
    document.getElementById('vinc-select-movidesk').innerHTML = opcoesMovidesk;
    // restaura a seleção de quem já estava sendo editado - a atualização
    // nunca deve mudar o vínculo de ninguém sozinha, só trazer gente nova
    document.getElementById('vinc-select-movidesk').value = selecaoAtual;

    statusEl.innerText = `Lista atualizada - ${usuariosMovideskCarregadosMU.length} pessoa(s) disponível(is) no Movidesk agora.`;
  } catch (e) {
    statusEl.innerText = 'Erro ao atualizar: ' + e;
  }
}

function escaparHtmlMU(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function iniciaisMU(nome) {
  const partes = (nome || '?').trim().split(/\\s+/).filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function avatarMU(u) {
  if (u.tem_foto) {
    return `<img class="foto-mu" src="/foto-usuario/${encodeURIComponent(u.usuario)}?t=${Date.now()}" alt="${escaparHtmlMU(u.nome || u.usuario)}">`;
  }
  return `<div class="iniciais-mu">${iniciaisMU(u.nome || u.usuario)}</div>`;
}

// -- Seletor de ação (pills) -------------------------------------------
function selecionarAcaoMU(acao) {
  document.querySelectorAll('.pill-acao-mu').forEach(p => p.classList.toggle('ativa', p.dataset.acao === acao));
  document.getElementById('secao-cad-exc').classList.toggle('ativa', acao === 'cad' || acao === 'exc');
  document.getElementById('secao-editar').classList.toggle('ativa', acao === 'editar');

  if (acao === 'cad' || acao === 'exc') {
    document.getElementById('titulo-form-cadexc').innerText = acao === 'cad' ? 'Cadastrar usuário' : 'Desativar usuário';
    window._muAcaoAtual = acao;
    atualizarCamposCondicionaisMU();
  }
}

// -- Cadastrar / Desativar (fluxo já existente, só lendo a ação do
// seletor de pills em vez de um radio) ----------------------------------
function lerFormularioManutencaoUsuarios() {
  const acao = window._muAcaoAtual || 'cad';
  const area = document.querySelector('input[name="mu-area"]:checked').value;
  const nome = document.getElementById('mu-nome').value.trim();
  const login = document.getElementById('mu-login').value.trim();
  const incluirPda = document.getElementById('mu-incluir-pda').checked;
  const usuarioPda = document.getElementById('mu-usuario-pda').value.trim();
  const senhaPda = document.getElementById('mu-senha-pda').value;
  const enviarBoasVindas = acao === 'cad' && document.getElementById('mu-enviar-boas-vindas').checked;
  return { acao, area, nome, login, incluirPda, usuarioPda, senhaPda, enviarBoasVindas };
}

function atualizarCamposCondicionaisMU() {
  const acao = window._muAcaoAtual || 'cad';
  const incluirPda = document.getElementById('mu-incluir-pda').checked;
  document.getElementById('mu-campos-pda').style.display = incluirPda ? 'block' : 'none';
  const campoSenha = document.getElementById('mu-senha-pda');
  const labelSenha = document.getElementById('mu-label-senha-pda');
  const mostrarSenha = acao === 'cad';
  campoSenha.style.display = mostrarSenha ? 'block' : 'none';
  labelSenha.style.display = mostrarSenha ? 'block' : 'none';

  // Boas-vindas só faz sentido no cadastro
  document.getElementById('mu-campo-boas-vindas').style.display = acao === 'cad' ? 'flex' : 'none';
  document.getElementById('mu-dica-boas-vindas').style.display = acao === 'cad' ? 'block' : 'none';
  if (acao !== 'cad') document.getElementById('mu-enviar-boas-vindas').checked = false;
}

function renderizarTabelaAlvosManutencaoUsuarios(alvos) {
  if (alvos.length === 0) {
    return '<div class="vazio-mu">Nenhum alvo encontrado pra essa área.</div>';
  }
  const linhas = alvos.map(a => `
    <tr>
      <td>${a.area}</td><td>${a.tenant}</td><td>${a.produto}</td><td>${a.database}</td>
    </tr>
  `).join('');
  return `
    <table class="tabela-mu">
      <thead><tr><th>Área</th><th>Tenant</th><th>Produto</th><th>Banco</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table>
  `;
}

async function gerarPreviaManutencaoUsuarios() {
  const { acao, area, nome, login, incluirPda, usuarioPda, enviarBoasVindas } = lerFormularioManutencaoUsuarios();
  const erroEl = document.getElementById('mu-erro');
  const statusEl = document.getElementById('mu-status');
  erroEl.innerText = '';
  document.getElementById('btn-mu-executar').disabled = true;
  previaAlvosManutencaoUsuarios = [];

  const botao = document.getElementById('btn-mu-previa');
  botao.disabled = true;
  try {
    const resp = await fetch('/api/manutencao-usuarios/previa', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'action=' + encodeURIComponent(acao) + '&area=' + encodeURIComponent(area) +
            '&nome=' + encodeURIComponent(nome) + '&login=' + encodeURIComponent(login) +
            '&incluir_pda=' + (incluirPda ? 'true' : 'false') + '&usuario_pda=' + encodeURIComponent(usuarioPda) +
            '&enviar_boas_vindas=' + (enviarBoasVindas ? 'true' : 'false'),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível gerar a prévia.';
      return;
    }
    previaAlvosManutencaoUsuarios = dados.targets;
    document.getElementById('mu-titulo-workspace').innerText = 'Prévia de execução';
    document.getElementById('mu-workspace').innerHTML = renderizarTabelaAlvosManutencaoUsuarios(dados.targets);
    document.getElementById('btn-mu-executar').disabled = dados.targets.length === 0;
    statusEl.innerText = `Prévia pronta: ${dados.targets.length} alvo(s) selecionado(s) (Movidesk incluso). Revise antes de confirmar.`;
  } catch (e) {
    erroEl.innerText = 'Erro ao gerar prévia: ' + e;
  } finally {
    botao.disabled = false;
  }
}

async function confirmarExecucaoManutencaoUsuarios() {
  if (previaAlvosManutencaoUsuarios.length === 0) {
    document.getElementById('mu-erro').innerText = 'Gere a prévia antes de executar.';
    return;
  }
  const { acao, area, nome, login, incluirPda, usuarioPda, senhaPda, enviarBoasVindas } = lerFormularioManutencaoUsuarios();
  const nomeAcao = acao === 'cad' ? 'cadastrar' : 'desativar';
  const confirmado = confirm(
    `Confirmar a ação de ${nomeAcao} o usuário '${login}' em ${previaAlvosManutencaoUsuarios.length} alvo(s)?\\n\\n` +
    'Essa ação grava de verdade nos bancos de produção e na API do Movidesk, e não pode ser desfeita automaticamente.'
  );
  if (!confirmado) {
    document.getElementById('mu-status').innerText = 'Execução cancelada pelo operador.';
    return;
  }

  const erroEl = document.getElementById('mu-erro');
  const statusEl = document.getElementById('mu-status');
  const botaoExecutar = document.getElementById('btn-mu-executar');
  const botaoPrevia = document.getElementById('btn-mu-previa');
  erroEl.innerText = '';
  botaoExecutar.disabled = true;
  botaoPrevia.disabled = true;
  statusEl.innerText = 'Executando... isso pode levar um tempo (uma conexão por alvo, em sequência).';
  document.getElementById('mu-titulo-workspace').innerText = 'Executando...';

  try {
    const resp = await fetch('/api/manutencao-usuarios/executar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'action=' + encodeURIComponent(acao) + '&area=' + encodeURIComponent(area) +
            '&nome=' + encodeURIComponent(nome) + '&login=' + encodeURIComponent(login) +
            '&incluir_pda=' + (incluirPda ? 'true' : 'false') +
            '&usuario_pda=' + encodeURIComponent(usuarioPda) + '&senha_pda=' + encodeURIComponent(senhaPda) +
            '&enviar_boas_vindas=' + (enviarBoasVindas ? 'true' : 'false'),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível executar.';
      statusEl.innerText = 'Falha na execução.';
      botaoPrevia.disabled = false;
      return;
    }
    renderizarResultadoManutencaoUsuarios(dados);
    statusEl.innerText = 'Execução finalizada.';
    previaAlvosManutencaoUsuarios = [];
  } catch (e) {
    erroEl.innerText = 'Erro ao executar: ' + e;
    statusEl.innerText = 'Falha na execução.';
  } finally {
    botaoPrevia.disabled = false;
  }
}

function renderizarResultadoManutencaoUsuarios(dados) {
  document.getElementById('mu-titulo-workspace').innerText = 'Resultado da execução';
  const rotulos = { success: 'OK', skipped: 'AVISO', error: 'ERRO' };
  const linhas = dados.resultados.map(r => `
    <tr>
      <td>${r.area}</td><td>${r.tenant}</td><td>${r.produto}</td><td>${r.database}</td>
      <td><span class="badge-status-mu ${r.status}">${rotulos[r.status] || r.status}</span></td>
      <td>${r.message}</td>
    </tr>
  `).join('');
  document.getElementById('mu-workspace').innerHTML = `
    <table class="tabela-mu">
      <thead><tr><th>Área</th><th>Tenant</th><th>Produto</th><th>Banco</th><th>Status</th><th>Mensagem</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table>
    <div class="resumo-final-mu">
      Finalizado: <b>${dados.sucesso}</b> sucesso(s), <b>${dados.ignorados}</b> ignorado(s), <b>${dados.erros}</b> erro(s).
      Log: <b>${dados.log}</b>
    </div>
  `;
}

// -- Editar permissões do PDA - reaproveita as MESMAS rotas /api/usuarios/*
// já usadas na tela Usuários (nada de lógica de permissão duplicada) -----
const ENDPOINTS_PERMISSOES_MU = {
  pode_manutencao_alertas: '/api/usuarios/permissao-manutencao',
  pode_relatorios_shein: '/api/usuarios/permissao-shein',
  pode_dash_financeiro: '/api/usuarios/permissao-dash-financeiro',
  pode_manutencao_rejeicoes: '/api/usuarios/permissao-manutencao-rejeicoes',
  pode_manutencao_relatorios: '/api/usuarios/permissao-manutencao-relatorios',
  pode_dados_sensiveis: '/api/usuarios/permissao-string-connections',
  pode_manutencao_usuarios: '/api/usuarios/permissao-manutencao-usuarios',
};
const PERMISSOES_NAO_AUTOMATICAS_MU = new Set(['pode_dados_sensiveis', 'pode_manutencao_usuarios']);
let usuarioAtualEditarMU = null;

// -- Lista + filtro ------------------------------------------------------
function pertenceAEquipeMU(atribuicao, equipeFiltro) {
  // Mesma lógica de _pertence_a_equipe() no backend - "Suporte e
  // Monitoramento" (escala 12x36, ex.: duas pessoas de exemplo) bate nos dois
  // filtros, não só no valor exato.
  if (!equipeFiltro) return true;
  const valor = atribuicao || 'Suporte';
  if (valor === 'Suporte e Monitoramento') return true;
  return valor === equipeFiltro;
}

function filtrarListaEditarMU() {
  const termo = (document.getElementById('filtro-nome-mu').value || '').trim().toLowerCase();
  const equipe = document.getElementById('filtro-equipe-mu').value;

  const filtrados = usuariosCarregadosMU.filter(u => {
    const bateNome = !termo || (u.nome || '').toLowerCase().includes(termo) || u.usuario.toLowerCase().includes(termo);
    const bateEquipe = pertenceAEquipeMU(u.atribuicao, equipe);
    return bateNome && bateEquipe;
  });
  filtrados.sort((a, b) => (a.nome || a.usuario).localeCompare(b.nome || b.usuario));

  document.getElementById('contagem-lista-mu').innerText = filtrados.length;
  const corpo = document.getElementById('corpo-lista-editar-mu');
  document.getElementById('lista-editar-vazio-mu').style.display = filtrados.length === 0 ? 'block' : 'none';

  corpo.innerHTML = filtrados.map(u => {
    const nomeVinculado = u.usuario_movidesk_id
      ? (usuariosMovideskCarregadosMU.find(m => m.id === u.usuario_movidesk_id)?.nome || ('ID ' + u.usuario_movidesk_id))
      : null;
    const estaAtivo = u.ativo !== false;
    return `
      <tr style="cursor:pointer" onclick="abrirPerfilEdicaoMU('${u.usuario}')">
        <td>${escaparHtmlMU(u.usuario)}</td>
        <td>${escaparHtmlMU(u.nome || u.usuario)}</td>
        <td>${u.admin ? 'Administrador' : 'Visualização'}</td>
        <td>${escaparHtmlMU(u.atribuicao || 'Suporte')}</td>
        <td><span class="badge-status-mu ${estaAtivo ? 'success' : 'error'}">${estaAtivo ? 'Ativo' : 'Desativado'}</span></td>
        <td>${nomeVinculado ? '✓ ' + escaparHtmlMU(nomeVinculado) : '<span style="color:var(--fg-dim)">Não vinculado</span>'}</td>
      </tr>
    `;
  }).join('');
}

function voltarParaListaMU() {
  document.getElementById('editar-visao-perfil').style.display = 'none';
  document.getElementById('editar-visao-lista').style.display = 'block';
  usuarioAtualEditarMU = null;
  carregarListasBaseMU();
}

// -- Abrir perfil de UMA pessoa - popula TUDO de uma vez (dados gerais,
// permissões, vínculo Movidesk, diagnóstico) --------------------------
async function abrirPerfilEdicaoMU(usuario) {
  const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
  if (!u) return;
  usuarioAtualEditarMU = usuario;

  document.getElementById('editar-visao-lista').style.display = 'none';
  document.getElementById('editar-visao-perfil').style.display = 'block';

  const estaAtivo = u.ativo !== false;
  document.getElementById('perfil-cabecalho-mu').innerHTML = `
    ${avatarMU(u)}
    <div>
      <div class="nome-mu">${escaparHtmlMU(u.nome || u.usuario)}</div>
      <div class="login-mu">${escaparHtmlMU(u.usuario)} · ${u.admin ? 'Administrador' : 'Visualização'} · ${escaparHtmlMU(u.atribuicao || 'Suporte')}
        · <span class="badge-status-mu ${estaAtivo ? 'success' : 'error'}">${estaAtivo ? 'Ativo' : 'Desativado'}</span>
      </div>
    </div>
  `;
  document.getElementById('link-ver-perfil-mu').href = '/perfil/' + encodeURIComponent(u.usuario);

  // Dados gerais
  document.getElementById('ed-nome').value = u.nome || u.usuario;
  document.getElementById('ed-email').value = u.email || '';
  document.getElementById('ed-data-inicio').value = u.data_inicio || '';
  document.getElementById('ed-papel').value = u.admin ? 'admin' : 'view';
  document.getElementById('ed-atribuicao').value = u.atribuicao || 'Suporte';
  document.getElementById('ed-status').value = estaAtivo ? 'true' : 'false';
  document.getElementById('ed-erro-geral-mu').innerText = '';
  document.getElementById('ed-status-geral-mu').innerText = '';
  document.getElementById('ed-erro-boasvindas-mu').innerText = '';
  document.getElementById('ed-status-boasvindas-mu').innerText = '';
  document.getElementById('ed-usuario-novo').value = '';
  document.getElementById('ed-erro-renomear-mu').innerText = '';
  document.getElementById('ed-status-renomear-mu').innerText = '';

  // Senha
  document.getElementById('ed-nova-senha').value = '';
  document.getElementById('ed-confirma-senha').value = '';
  document.getElementById('ed-erro-senha-mu').innerText = '';
  document.getElementById('ed-status-senha-mu').innerText = '';

  // Permissões
  for (const chave of Object.keys(ENDPOINTS_PERMISSOES_MU)) {
    document.getElementById('perm-' + chave).checked = !!u[chave];
  }
  atualizarTravasPermissoesMU();
  document.getElementById('perm-erro-mu').innerText = '';
  document.getElementById('perm-status-mu').innerText = '';

  // Vínculo Movidesk
  document.getElementById('vinc-select-movidesk').value = u.usuario_movidesk_id || '';
  document.getElementById('vinc-campos-movidesk-mu').style.display = 'none';
  document.getElementById('vinc-erro-mu').innerText = '';
  document.getElementById('vinc-status-mu').innerText = '';

  // Diagnóstico - login sugerido a partir do e-mail do Movidesk, se
  // vinculado (o login do PDA normalmente é diferente do login usado
  // nos bancos/Movidesk, que costuma ser o e-mail completo)
  const campoDiagLogin = document.getElementById('diag-login');
  campoDiagLogin.value = '';
  document.getElementById('diag-erro-mu').innerText = '';
  document.getElementById('diag-status-mu').innerText = '';
  document.getElementById('diag-resultado-mu').innerHTML = '<div class="vazio-mu">Clique em "Verificar status" pra cruzar Movidesk + todos os bancos.</div>';

  if (u.usuario_movidesk_id) {
    try {
      const resp = await fetch('/api/usuarios-movidesk/' + encodeURIComponent(u.usuario_movidesk_id));
      const dados = await resp.json();
      if (dados.ok) {
        const r = dados.registro;
        document.getElementById('vinc-cargo').value = r.cargo || '';
        document.getElementById('vinc-email').value = r.email || '';
        document.getElementById('vinc-escala').value = r.escala || '';
        document.getElementById('vinc-horainicio').value = r.horainicio || '';
        document.getElementById('vinc-horafim').value = r.horafim || '';
        const diasMarcados = (r.diastrabalhados || '').split(',').map(d => d.trim()).filter(Boolean);
        document.querySelectorAll('#vinc-campos-movidesk-mu .dia-check-mu input').forEach(chk => {
          chk.checked = diasMarcados.includes(chk.value);
        });
        document.getElementById('vinc-campos-movidesk-mu').style.display = 'block';
        if (r.email) campoDiagLogin.value = r.email;
      }
    } catch (e) { /* segue sem os dados do Movidesk, não trava a abertura do perfil */ }
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function atualizarTravasPermissoesMU() {
  const ehAdmin = document.getElementById('ed-papel').value === 'admin';
  for (const chave of Object.keys(ENDPOINTS_PERMISSOES_MU)) {
    const checkbox = document.getElementById('perm-' + chave);
    const travar = ehAdmin && !PERMISSOES_NAO_AUTOMATICAS_MU.has(chave);
    checkbox.disabled = travar;
    if (travar) checkbox.checked = true;
  }
}

// -- Dados gerais (nome, papel, equipe, status do login PDA) -----------
async function salvarDadosGeraisMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('ed-erro-geral-mu');
  const statusEl = document.getElementById('ed-status-geral-mu');
  erroEl.innerText = '';
  statusEl.innerText = 'Salvando...';

  const novoNome = document.getElementById('ed-nome').value.trim();
  if (!novoNome) { erroEl.innerText = 'O nome não pode ficar em branco.'; statusEl.innerText = ''; return; }
  const novoEmail = document.getElementById('ed-email').value.trim();
  const novaDataInicio = document.getElementById('ed-data-inicio').value;

  try {
    await fetch('/api/usuarios/alterar-nome', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&nome=' + encodeURIComponent(novoNome),
    });
    const respEmail = await fetch('/api/usuarios/alterar-email', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&email=' + encodeURIComponent(novoEmail),
    });
    const dadosEmail = await respEmail.json();
    if (!dadosEmail.ok) { erroEl.innerText = dadosEmail.erro || 'Não foi possível salvar o e-mail.'; statusEl.innerText = ''; return; }
    const respDataInicio = await fetch('/api/usuarios/alterar-data-inicio', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&data_inicio=' + encodeURIComponent(novaDataInicio),
    });
    const dadosDataInicio = await respDataInicio.json();
    if (!dadosDataInicio.ok) { erroEl.innerText = dadosDataInicio.erro || 'Não foi possível salvar a data de início.'; statusEl.innerText = ''; return; }
    await fetch('/api/usuarios/admin', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&admin=' + (document.getElementById('ed-papel').value === 'admin' ? 'true' : 'false'),
    });
    await fetch('/api/usuarios/alterar-atribuicao', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&atribuicao=' + encodeURIComponent(document.getElementById('ed-atribuicao').value),
    });
    const respStatus = await fetch('/api/usuarios/alterar-status', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&ativo=' + document.getElementById('ed-status').value,
    });
    const dadosStatus = await respStatus.json();
    if (!dadosStatus.ok) { erroEl.innerText = dadosStatus.erro || 'Não foi possível salvar o status.'; statusEl.innerText = ''; return; }

    statusEl.innerText = 'Dados gerais salvos.';
    const respUsuarios = await fetch('/api/usuarios');
    const dadosUsuarios = await respUsuarios.json();
    usuariosCarregadosMU = dadosUsuarios.usuarios || [];
    const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
    if (u) {
      const estaAtivo = u.ativo !== false;
      document.getElementById('perfil-cabecalho-mu').innerHTML = `
        ${avatarMU(u)}
        <div>
          <div class="nome-mu">${escaparHtmlMU(u.nome || u.usuario)}</div>
          <div class="login-mu">${escaparHtmlMU(u.usuario)} · ${u.admin ? 'Administrador' : 'Visualização'} · ${escaparHtmlMU(u.atribuicao || 'Suporte')}
            · <span class="badge-status-mu ${estaAtivo ? 'success' : 'error'}">${estaAtivo ? 'Ativo' : 'Desativado'}</span>
          </div>
        </div>
      `;
    }
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
    statusEl.innerText = '';
  }
}

// -- Senha ---------------------------------------------------------------
async function salvarSenhaEdicaoMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('ed-erro-senha-mu');
  const statusEl = document.getElementById('ed-status-senha-mu');
  erroEl.innerText = ''; statusEl.innerText = '';

  const nova = document.getElementById('ed-nova-senha').value;
  const confirma = document.getElementById('ed-confirma-senha').value;
  if (!nova || nova.length < 4) { erroEl.innerText = 'A senha precisa ter ao menos 4 caracteres.'; return; }
  if (nova !== confirma) { erroEl.innerText = 'As senhas não coincidem.'; return; }

  try {
    const resp = await fetch('/api/usuarios/senha', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&nova_senha=' + encodeURIComponent(nova),
    });
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível salvar.'; return; }
    statusEl.innerText = 'Senha atualizada.';
    document.getElementById('ed-nova-senha').value = '';
    document.getElementById('ed-confirma-senha').value = '';
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  }
}

// -- E-mail de boas-vindas - ferramenta oficial de envio manual, usando a
// senha REAL da pessoa (não uma senha padrão) - envia de verdade pro
// e-mail cadastrado dela.
async function enviarBoasVindasTesteMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('ed-erro-boasvindas-mu');
  const statusEl = document.getElementById('ed-status-boasvindas-mu');
  erroEl.innerText = '';
  statusEl.innerText = 'Enviando...';

  try {
    const resp = await fetch('/api/usuarios/enviar-boas-vindas', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario),
    });
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível enviar.'; statusEl.innerText = ''; return; }
    statusEl.innerText = `E-mail enviado pra ${dados.email}.`;
  } catch (e) {
    erroEl.innerText = 'Erro ao enviar: ' + e;
    statusEl.innerText = '';
  }
}

// -- Renomear usuário (login) - troca a chave primária em tudo (feedbacks,
// histórico de carreira, sessão ativa) - operação rara/delicada, por
// isso a confirmação explícita antes de mandar pro backend.
async function renomearUsuarioMU() {
  const usuarioAtual = usuarioAtualEditarMU;
  if (!usuarioAtual) return;
  const usuarioNovo = document.getElementById('ed-usuario-novo').value.trim();
  const erroEl = document.getElementById('ed-erro-renomear-mu');
  const statusEl = document.getElementById('ed-status-renomear-mu');
  erroEl.innerText = '';
  if (!usuarioNovo) { erroEl.innerText = 'Informe o novo usuário.'; return; }

  const confirmado = confirm(
    `Renomear o login de '${usuarioAtual}' pra '${usuarioNovo}'?\\n\\n` +
    'Isso troca o usuário em permissões, feedbacks e histórico de carreira, e encerra a sessão ativa dela.'
  );
  if (!confirmado) return;

  statusEl.innerText = 'Renomeando...';
  try {
    const resp = await fetch('/api/usuarios/renomear', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario_atual=' + encodeURIComponent(usuarioAtual) + '&usuario_novo=' + encodeURIComponent(usuarioNovo),
    });
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível renomear.'; statusEl.innerText = ''; return; }

    statusEl.innerText = `Renomeado pra '${dados.usuario_novo}'. Recarregando...`;
    const respUsuarios = await fetch('/api/usuarios');
    const dadosUsuarios = await respUsuarios.json();
    usuariosCarregadosMU = dadosUsuarios.usuarios || [];
    abrirPerfilEdicaoMU(dados.usuario_novo);
  } catch (e) {
    erroEl.innerText = 'Erro ao renomear: ' + e;
    statusEl.innerText = '';
  }
}

// -- Permissões especiais - reaproveita as MESMAS rotas /api/usuarios/*
// já usadas na tela Usuários (nada de lógica de permissão duplicada) ---
async function salvarPermissoesMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('perm-erro-mu');
  const statusEl = document.getElementById('perm-status-mu');
  erroEl.innerText = '';
  statusEl.innerText = 'Salvando...';

  try {
    await Promise.all(Object.entries(ENDPOINTS_PERMISSOES_MU).map(([chave, url]) => {
      const checkbox = document.getElementById('perm-' + chave);
      if (checkbox.disabled) return Promise.resolve();
      return fetch(url, {
        method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'usuario=' + encodeURIComponent(usuario) + '&permitido=' + (checkbox.checked ? 'true' : 'false'),
      });
    }));
    statusEl.innerText = 'Permissões salvas.';
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
    statusEl.innerText = '';
  }
}

// -- Vínculo Movidesk - reaproveita as MESMAS rotas /api/usuarios-movidesk*
// e /api/usuarios/vincular-movidesk já usadas na tela Usuários ----------

function aoTrocarUsuarioVinculadoMU() {
  const id = document.getElementById('vinc-select-movidesk').value;
  if (id) {
    carregarDadosMovideskParaVinculoMU(id);
  } else {
    document.getElementById('vinc-campos-movidesk-mu').style.display = 'none';
  }
}

async function carregarDadosMovideskParaVinculoMU(id) {
  const erroEl = document.getElementById('vinc-erro-mu');
  erroEl.innerText = '';
  try {
    const resp = await fetch('/api/usuarios-movidesk/' + encodeURIComponent(id));
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar os dados desse usuário.';
      document.getElementById('vinc-campos-movidesk-mu').style.display = 'none';
      return;
    }
    const r = dados.registro;
    document.getElementById('vinc-cargo').value = r.cargo || '';
    document.getElementById('vinc-email').value = r.email || '';
    document.getElementById('vinc-escala').value = r.escala || '';
    document.getElementById('vinc-horainicio').value = r.horainicio || '';
    document.getElementById('vinc-horafim').value = r.horafim || '';
    const diasMarcados = (r.diastrabalhados || '').split(',').map(d => d.trim()).filter(Boolean);
    document.querySelectorAll('#vinc-campos-movidesk-mu .dia-check-mu input').forEach(chk => {
      chk.checked = diasMarcados.includes(chk.value);
    });
    document.getElementById('vinc-campos-movidesk-mu').style.display = 'block';
    if (r.email) document.getElementById('diag-login').value = r.email;
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
  }
}

async function salvarVinculoMovideskMU() {
  const erroEl = document.getElementById('vinc-erro-mu');
  const statusEl = document.getElementById('vinc-status-mu');
  erroEl.innerText = ''; statusEl.innerText = '';
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const idSelecionado = document.getElementById('vinc-select-movidesk').value;

  try {
    const respVinculo = await fetch('/api/usuarios/vincular-movidesk', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(usuario) + '&id_movidesk=' + encodeURIComponent(idSelecionado),
    });
    const dadosVinculo = await respVinculo.json();
    if (!dadosVinculo.ok) { erroEl.innerText = dadosVinculo.erro || 'Não foi possível salvar o vínculo.'; return; }

    if (idSelecionado) {
      const diasMarcados = Array.from(document.querySelectorAll('#vinc-campos-movidesk-mu .dia-check-mu input:checked')).map(c => c.value);
      const respDados = await fetch('/api/usuarios-movidesk/atualizar', {
        method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'id=' + encodeURIComponent(idSelecionado) +
              '&cargo=' + encodeURIComponent(document.getElementById('vinc-cargo').value) +
              '&email=' + encodeURIComponent(document.getElementById('vinc-email').value) +
              '&escala=' + encodeURIComponent(document.getElementById('vinc-escala').value) +
              '&horainicio=' + encodeURIComponent(document.getElementById('vinc-horainicio').value) +
              '&horafim=' + encodeURIComponent(document.getElementById('vinc-horafim').value) +
              '&diasTrabalhados=' + encodeURIComponent(diasMarcados.join(',')),
      });
      const dadosSalvar = await respDados.json();
      if (!dadosSalvar.ok) { erroEl.innerText = dadosSalvar.erro || 'Vínculo salvo, mas não foi possível salvar os dados de horas.'; return; }
      const email = document.getElementById('vinc-email').value;
      if (email) document.getElementById('diag-login').value = email;
    }

    statusEl.innerText = 'Vínculo e dados atualizados.';
    const respUsuarios = await fetch('/api/usuarios');
    const dadosUsuarios = await respUsuarios.json();
    usuariosCarregadosMU = dadosUsuarios.usuarios || [];
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  }
}

// -- Ir pra Desativar, com os dados dessa pessoa já preenchidos - reaproveita
// o MESMO fluxo de prévia/confirmação/execução (banco+Movidesk+PDA) já
// usado na aba "Desativar usuário", só que já vem pronto pra conferir. --
function irParaDesativarComDadosMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
  if (!u) return;

  const loginSugerido = document.getElementById('vinc-email').value || document.getElementById('diag-login').value || '';
  selecionarAcaoMU('exc');
  document.getElementById('mu-nome').value = u.nome || u.usuario;
  document.getElementById('mu-login').value = loginSugerido;
  document.getElementById('mu-status').innerText = loginSugerido
    ? `Dados de "${u.nome || u.usuario}" pré-preenchidos a partir do perfil - confira Área e Login antes de gerar a prévia.`
    : `Nome pré-preenchido a partir do perfil de "${u.nome || u.usuario}" - preencha o Login manualmente (não achamos um e-mail vinculado) antes de gerar a prévia.`;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// -- Diagnóstico (cruzamento de usuários) - SÓ CONSULTA, nunca grava nada.
// Pra um login só, mostra de uma vez o vínculo Movidesk + presença em
// todos os bancos de cliente. ------------------------------------------
function renderizarResultadoDiagnosticoMU(dados, login) {
  const rotulos = { success: 'Encontrado', skipped: 'Não encontrado', error: 'Erro' };

  let blocoMovidesk;
  if (dados.erro_movidesk) {
    blocoMovidesk = `<div class="erro-mu" style="margin-top:0">Movidesk: ${escaparHtmlMU(dados.erro_movidesk)}</div>`;
  } else if (dados.movidesk) {
    const m = dados.movidesk;
    blocoMovidesk = `
      <div class="linha-resumo-mu"><span>Movidesk</span><span><span class="badge-status-mu success">Encontrado</span></span></div>
      <div class="linha-resumo-mu"><span>Nome</span><span>${escaparHtmlMU(m.businessName || '-')}</span></div>
      <div class="linha-resumo-mu"><span>Ativo</span><span>${m.isActive ? 'Sim' : 'Não'}</span></div>
      <div class="linha-resumo-mu"><span>Perfil de acesso</span><span>${escaparHtmlMU(m.accessProfile || '-')}</span></div>
    `;
  } else {
    blocoMovidesk = `<div class="linha-resumo-mu"><span>Movidesk</span><span><span class="badge-status-mu skipped">Não encontrado</span></span></div>`;
  }

  const linhasBancos = dados.resultados_bancos.map(r => `
    <tr>
      <td>${r.area}</td><td>${r.tenant}</td><td>${r.produto}</td><td>${r.database}</td>
      <td><span class="badge-status-mu ${r.status}">${rotulos[r.status] || r.status}</span></td>
      <td>${escaparHtmlMU(r.message)}</td>
    </tr>
  `).join('');
  const totalEncontrado = dados.resultados_bancos.filter(r => r.status === 'success').length;
  const totalErro = dados.resultados_bancos.filter(r => r.status === 'error').length;

  document.getElementById('diag-resultado-mu').innerHTML = `
    <div style="margin-bottom:16px">
      <div class="linha-resumo-mu"><span>Login diagnosticado</span><span>${escaparHtmlMU(login)}</span></div>
      ${blocoMovidesk}
    </div>
    <table class="tabela-mu">
      <thead><tr><th>Área</th><th>Tenant</th><th>Produto</th><th>Banco</th><th>Status</th><th>Detalhe</th></tr></thead>
      <tbody>${linhasBancos}</tbody>
    </table>
    <div class="resumo-final-mu">
      Encontrado em <b>${totalEncontrado}</b> de ${dados.resultados_bancos.length} banco(s) verificado(s)${totalErro ? ` (${totalErro} não puderam ser checados)` : ''}.
    </div>
  `;
}

async function verificarDiagnosticoMU() {
  const login = document.getElementById('diag-login').value.trim();
  const erroEl = document.getElementById('diag-erro-mu');
  const statusEl = document.getElementById('diag-status-mu');
  erroEl.innerText = '';
  if (!login) { erroEl.innerText = 'Informe o login pra diagnosticar.'; return; }

  const botao = document.getElementById('btn-diag-verificar');
  botao.disabled = true;
  statusEl.innerText = 'Verificando em todos os bancos... isso pode levar um tempo.';
  document.getElementById('diag-resultado-mu').innerHTML = '<div class="vazio-mu">Consultando...</div>';

  try {
    const resp = await fetch('/api/manutencao-usuarios/diagnostico', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'login=' + encodeURIComponent(login),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível diagnosticar.';
      statusEl.innerText = '';
      document.getElementById('diag-resultado-mu').innerHTML = '<div class="vazio-mu">Informe um login e clique em "Verificar status".</div>';
      return;
    }
    renderizarResultadoDiagnosticoMU(dados, login);
    statusEl.innerText = 'Diagnóstico concluído.';
  } catch (e) {
    erroEl.innerText = 'Erro ao diagnosticar: ' + e;
    statusEl.innerText = '';
  } finally {
    botao.disabled = false;
  }
}
</script>
</body>
</html>
"""


def _montar_manutencao_usuarios_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_USUARIOS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção de Usuários (Beta)"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__SENHA_PADRAO__", MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL)
    )


_INDICADORES_MOVIDESK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Indicadores Movidesk</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-im { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1120px; margin: 0 auto 22px auto; }
  .cabecalho-im h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-im .sub { color: var(--fg-dim); font-size: 12.5px; }
  .filtro-im { display: flex; align-items: end; gap: 10px; }
  .filtro-im label { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 5px;
                      text-transform: uppercase; letter-spacing: .04em; }
  .filtro-im input[type="date"] { padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border);
                                    background: var(--bg-panel-solid); color: var(--fg); font-size: 13px; }

  .grade-im { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px;
              max-width: 1120px; margin: 0 auto 20px auto; }
  .cartao-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 20px 22px; }
  .cartao-numero { font-size: 34px; font-weight: 800; background: var(--gradiente-marca);
                    -webkit-background-clip: text; background-clip: text; color: transparent; line-height: 1; }
  .cartao-numero.grande { font-size: 42px; }
  .cartao-rotulo { color: var(--fg-dim); font-size: 12px; margin-top: 8px; text-transform: uppercase;
                    letter-spacing: .04em; }

  .painel-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1120px; margin: 0 auto 20px auto; }
  .painel-im h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .cabecalho-painel-im { display: flex; justify-content: space-between; align-items: center;
                          flex-wrap: wrap; gap: 10px; margin-bottom: 4px; }
  .cabecalho-painel-im h2 { margin: 0; }
  .filtro-solicitante-im { display: flex; align-items: center; gap: 8px; }
  .filtro-solicitante-im label { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                                   letter-spacing: .04em; }
  .filtro-solicitante-im select { min-width: 180px; padding: 6px 30px 6px 10px; font-size: 12.5px; }

  .barra-escalonamento { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
  .barra-escalonamento .rotulo-marcador { width: 220px; flex-shrink: 0; font-size: 12px; color: var(--fg-dim);
                                            text-align: right; text-transform: capitalize;
                                            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .barra-escalonamento .trilha { flex: 1; background: rgba(255,255,255,.05); border-radius: 20px;
                                   height: 24px; overflow: hidden; position: relative; }
  .barra-escalonamento .preenchimento { height: 100%; border-radius: 20px;
                                          background: var(--gradiente-marca);
                                          box-shadow: 0 0 14px rgba(45,184,207,.35);
                                          display: flex; align-items: center; justify-content: flex-end;
                                          padding-right: 12px; transition: width .5s ease; min-width: 30px; }
  .barra-escalonamento .preenchimento span { font-size: 11.5px; font-weight: 700; color: #0b0f14; }

  .grade-niveis-escalonamento { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
  .cartao-nivel-escalonamento { background: rgba(255,255,255,.02); border: 1px solid var(--border);
                                  border-top: 3px solid var(--cor-nivel); border-radius: 12px;
                                  padding: 18px 20px; text-align: center; }
  .cartao-nivel-escalonamento .numero-nivel { font-size: 30px; font-weight: 800; color: var(--cor-nivel); line-height: 1; }
  .cartao-nivel-escalonamento .rotulo-nivel { font-size: 11px; color: var(--fg-dim); text-transform: uppercase;
                                                letter-spacing: .04em; margin-top: 8px; }

  .tabela-im-rolagem { overflow-x: auto; border-radius: 10px; }
  table.tabela-im { width: 100%; border-collapse: collapse; min-width: 100%; }
  table.tabela-im th, table.tabela-im td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border);
                                             font-size: 12.5px; white-space: nowrap; overflow: hidden;
                                             text-overflow: ellipsis; max-width: 220px; }
  table.tabela-im th { color: var(--teal); font-weight: 600; text-transform: uppercase; font-size: 10.5px;
                        letter-spacing: .03em; background: rgba(255,255,255,.03); position: sticky; top: 0; }
  table.tabela-im th.col-destaque, table.tabela-im td.col-destaque {
    max-width: 340px; white-space: normal; text-overflow: clip; line-height: 1.4;
  }
  table.tabela-im tbody tr { transition: background .12s; }
  table.tabela-im tbody tr:hover { background: rgba(255,255,255,.03); }
  table.tabela-im tbody tr:nth-child(even) { background: rgba(255,255,255,.015); }
  table.tabela-im tr:last-child td { border-bottom: none; }
  .vazio-im { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .erro-im { color: var(--erro); font-size: 12.5px; }
  .carregando-im { color: var(--fg-dim); font-size: 12.5px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-im">
      <div>
        <h1>Indicadores Movidesk</h1>
        <div class="sub">Escalonamentos, dúvidas e sincronização - direto do Movidesk.</div>
      </div>
      <div class="filtro-im">
        <div>
          <label>A partir de</label>
          <input type="date" id="im-data-inicio">
        </div>
        <div>
          <label>Até</label>
          <input type="date" id="im-data-fim">
        </div>
        <button class="btn-accent" onclick="carregarIndicadoresMovidesk()">Aplicar</button>
      </div>
    </div>

    <div class="grade-im">
      <div class="cartao-im">
        <div class="cartao-numero grande" id="im-numero-duvidas">–</div>
        <div class="cartao-rotulo">Dúvidas abertas no período</div>
      </div>
      <div class="cartao-im">
        <div class="cartao-numero" id="im-numero-escalonamentos">–</div>
        <div class="cartao-rotulo">Escalonamentos no período</div>
      </div>
      <div class="cartao-im">
        <div class="cartao-numero" id="im-numero-marcadores">–</div>
        <div class="cartao-rotulo">Marcadores distintos</div>
      </div>
    </div>

    <div class="painel-im">
      <h2>Top solicitantes (dúvidas processadas)</h2>
      <div id="im-barras-solicitantes"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <h2>Chamados por analista (apontamentos)</h2>
      <div id="im-barras-chamados"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <h2>Escalonamentos por marcador</h2>
      <div id="im-barras-escalonamento"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <div class="cabecalho-painel-im">
        <h2>Dúvidas processadas</h2>
        <div class="filtro-solicitante-im">
          <label for="im-filtro-solicitante">Solicitante</label>
          <select id="im-filtro-solicitante" onchange="aplicarFiltroSolicitante()">
            <option value="">Todos</option>
          </select>
        </div>
      </div>
      <div id="im-tabela-duvidas"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <h2>Escalonamentos processados por nível</h2>
      <div id="im-niveis-escalonamento"><div class="carregando-im">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

<script>
(function () {
  document.getElementById('im-data-inicio').value = new Date().toISOString().slice(0, 8) + '01';
  document.getElementById('im-data-fim').value = new Date().toISOString().slice(0, 10);
})();

function formatarNomeColuna(nomeCru) {
  // "TICKET_SUBJECT" / "solicitado_por_nome" -> "Ticket Subject"
  // Mas se já veio bem formatado direto do SQL (com "AS [Nome Bonito]" -
  // sem underscore e não tudo maiúsculo), deixa como está, senão sigla
  // tipo "ID" viraria "Id".
  if (!nomeCru.includes('_') && nomeCru !== nomeCru.toUpperCase()) {
    return nomeCru;
  }
  return nomeCru
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\\b\\w/g, c => c.toUpperCase());
}

function renderizarTabelaDinamica(linhas, elementoDestino) {
  if (!linhas || linhas.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum registro no período.</div>';
    return;
  }
  const colunas = Object.keys(linhas[0]);

  // colunas com texto tipicamente longo (ex.: assunto do ticket) merecem
  // mais espaço e podem quebrar linha - as demais ficam compactas, com
  // reticências e o valor completo disponível ao passar o mouse.
  const comprimentoMedio = {};
  colunas.forEach(c => {
    const total = linhas.slice(0, 30).reduce((soma, l) => soma + String(l[c] ?? '').length, 0);
    comprimentoMedio[c] = total / Math.min(30, linhas.length);
  });
  const colunaDestaque = colunas.reduce((maior, c) =>
    comprimentoMedio[c] > (comprimentoMedio[maior] || 0) ? c : maior, colunas[0]);
  const usaDestaque = comprimentoMedio[colunaDestaque] > 40;

  const cabecalho = colunas.map(c =>
    `<th class="${c === colunaDestaque && usaDestaque ? 'col-destaque' : ''}">${formatarNomeColuna(c)}</th>`
  ).join('');

  const linhasHtml = linhas.slice(0, 200).map(l => {
    const celulas = colunas.map(c => {
      const valor = String(l[c] ?? '');
      const ehDestaque = c === colunaDestaque && usaDestaque;
      const classe = ehDestaque ? 'col-destaque' : '';
      const titulo = valor.length > 24 ? ` title="${valor.replace(/"/g, '&quot;')}"` : '';
      return `<td class="${classe}"${titulo}>${valor}</td>`;
    }).join('');
    return `<tr>${celulas}</tr>`;
  }).join('');

  const avisoLimite = linhas.length > 200
    ? `<div class="vazio-im">Mostrando as primeiras 200 de ${linhas.length} linhas.</div>` : '';
  elementoDestino.innerHTML =
    `<div class="tabela-im-rolagem"><table class="tabela-im"><thead><tr>${cabecalho}</tr></thead><tbody>${linhasHtml}</tbody></table></div>${avisoLimite}`;
}

function renderizarBarrasEscalonamento(escalonamentos, elementoDestino) {
  if (!escalonamentos || escalonamentos.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum escalonamento no período.</div>';
    return;
  }
  const maiorQtd = Math.max(...escalonamentos.map(e => e.qtd));
  // rotulos tipo "[ESC_MONITORAMENTO_PLENO]" ficam mais legiveis sem
  // colchete/prefixo tecnico e com sublinhado virando espaço
  const limparRotulo = (texto) => texto.replace(/^\\[|\\]$/g, '').replace(/_/g, ' ');
  elementoDestino.innerHTML = escalonamentos.map(e => {
    const percentual = Math.max(6, (e.qtd / maiorQtd) * 100);
    const rotulo = limparRotulo(e.marcador);
    return `
      <div class="barra-escalonamento">
        <div class="rotulo-marcador" title="${rotulo.replace(/"/g, '&quot;')}">${rotulo}</div>
        <div class="trilha">
          <div class="preenchimento" style="width:${percentual}%"><span>${e.qtd}</span></div>
        </div>
      </div>
    `;
  }).join('');
}

// Agrupa os MESMOS dados de "escalonamentos por marcador" (ja vem do
// backend numa unica consulta) por nivel de senioridade - os marcadores
// brutos tipo "[ESC_MONITORAMENTO_JUNIOR]"/"[ESC_MONITORAMENTO_PLENO]"/
// "[ESC_MONITORAMENTO_SENIOR]" ja trazem o nivel embutido no proprio
// nome, entao nao precisa de nenhuma consulta nova ao banco - só juntar
// o que já veio, por nível, direto no navegador.
function renderizarNiveisEscalonamento(escalonamentos, elementoDestino) {
  if (!escalonamentos || escalonamentos.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum escalonamento no período.</div>';
    return;
  }

  const NIVEIS = [
    { chave: 'junior', rotulo: 'Júnior', padrao: /J[ÚU]NIOR/i, cor: '#2db8cf' },
    { chave: 'pleno', rotulo: 'Pleno', padrao: /PLENO/i, cor: '#b0cb1c' },
    { chave: 'senior', rotulo: 'Sênior', padrao: /S[ÊE]NIOR/i, cor: '#b389f9' },
  ];
  const totais = { junior: 0, pleno: 0, senior: 0, outros: 0 };

  for (const e of escalonamentos) {
    const nivelEncontrado = NIVEIS.find(n => n.padrao.test(e.marcador || ''));
    if (nivelEncontrado) {
      totais[nivelEncontrado.chave] += e.qtd;
    } else {
      totais.outros += e.qtd;
    }
  }

  let cartoes = NIVEIS.map(n => `
    <div class="cartao-nivel-escalonamento" style="--cor-nivel:${n.cor}">
      <div class="numero-nivel">${totais[n.chave]}</div>
      <div class="rotulo-nivel">${n.rotulo}</div>
    </div>
  `).join('');

  if (totais.outros > 0) {
    cartoes += `
      <div class="cartao-nivel-escalonamento" style="--cor-nivel:var(--fg-dim)">
        <div class="numero-nivel">${totais.outros}</div>
        <div class="rotulo-nivel">Outros marcadores</div>
      </div>
    `;
  }

  elementoDestino.innerHTML = `<div class="grade-niveis-escalonamento">${cartoes}</div>`;
}

// Conta quantas dúvidas processadas cada pessoa solicitou, a partir da
// lista completa (sem filtro) - o gráfico sempre mostra o ranking geral
// do período, independente do filtro de solicitante da tabela abaixo
// (filtrar pra 1 pessoa só deixaria o ranking sem sentido nenhum).
function contarPorSolicitante(linhas) {
  const contagem = {};
  for (const linha of linhas) {
    const nome = (linha['Solicitado Por'] || '').trim();
    if (!nome) continue;
    contagem[nome] = (contagem[nome] || 0) + 1;
  }
  return Object.entries(contagem)
    .map(([nome, qtd]) => ({ nome, qtd }))
    .sort((a, b) => b.qtd - a.qtd);
}

function renderizarBarrasSolicitantes(linhas, elementoDestino) {
  const ranking = contarPorSolicitante(linhas);
  if (ranking.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhuma dúvida processada com solicitante identificado no período.</div>';
    return;
  }
  // top 15, senão a barra fica ilegível de tao apertada com muita gente
  const topRanking = ranking.slice(0, 15);
  const maiorQtd = topRanking[0].qtd;
  elementoDestino.innerHTML = topRanking.map(r => {
    const percentual = Math.max(6, (r.qtd / maiorQtd) * 100);
    return `
      <div class="barra-escalonamento">
        <div class="rotulo-marcador" title="${r.nome.replace(/"/g, '&quot;')}">${r.nome}</div>
        <div class="trilha">
          <div class="preenchimento" style="width:${percentual}%"><span>${r.qtd}</span></div>
        </div>
      </div>
    `;
  }).join('');
}

// Guarda a lista completa de dúvidas processadas (sem filtro) - o
// filtro de solicitante é aplicado aqui no navegador mesmo, sem precisar
// consultar o banco de novo a cada troca.
let duvidasProcessadasCompletas = [];

function popularFiltroSolicitante(linhas) {
  const select = document.getElementById('im-filtro-solicitante');
  const valorAtual = select.value;
  const solicitantes = [...new Set(linhas.map(l => l['Solicitado Por']).filter(Boolean))].sort();
  select.innerHTML = '<option value="">Todos</option>' +
    solicitantes.map(s => `<option value="${s}">${s}</option>`).join('');
  // mantém a seleção anterior se o nome ainda existir na lista nova
  if (solicitantes.includes(valorAtual)) select.value = valorAtual;
}

function aplicarFiltroSolicitante() {
  const solicitante = document.getElementById('im-filtro-solicitante').value;
  const filtradas = solicitante
    ? duvidasProcessadasCompletas.filter(l => l['Solicitado Por'] === solicitante)
    : duvidasProcessadasCompletas;
  renderizarTabelaDinamica(filtradas, document.getElementById('im-tabela-duvidas'));
}

async function carregarIndicadoresMovidesk() {
  const dataInicio = document.getElementById('im-data-inicio').value;
  const dataFim = document.getElementById('im-data-fim').value;
  let params = '';
  if (dataInicio) params += (params ? '&' : '?') + 'data_inicio=' + encodeURIComponent(dataInicio);
  if (dataFim) params += (params ? '&' : '?') + 'data_fim=' + encodeURIComponent(dataFim);

  document.getElementById('im-barras-escalonamento').innerHTML = '<div class="carregando-im">Carregando...</div>';
  document.getElementById('im-barras-solicitantes').innerHTML = '<div class="carregando-im">Carregando...</div>';
  document.getElementById('im-barras-chamados').innerHTML = '<div class="carregando-im">Carregando...</div>';
  document.getElementById('im-tabela-duvidas').innerHTML = '<div class="carregando-im">Carregando...</div>';

  try {
    const resp = await fetch('/api/indicadores-movidesk' + params);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      // erro geral (nem conseguiu conectar) - aplica em tudo
      const msg = `<div class="erro-im">⚠ ${dados.erro || 'Não foi possível carregar os indicadores.'}</div>`;
      document.getElementById('im-barras-escalonamento').innerHTML = msg;
      document.getElementById('im-barras-chamados').innerHTML = msg;
      document.getElementById('im-tabela-duvidas').innerHTML = msg;
      document.getElementById('im-niveis-escalonamento').innerHTML = msg;
      document.getElementById('im-numero-duvidas').innerText = '–';
      document.getElementById('im-numero-escalonamentos').innerText = '–';
      document.getElementById('im-numero-marcadores').innerText = '–';
      return;
    }

    // cada seção é independente agora - uma tabela com nome errado não
    // impede as outras 3 de mostrarem dado normal
    const du = dados.duvidas_abertas;
    document.getElementById('im-numero-duvidas').innerText = du.ok ? du.valor : '–';

    const esc = dados.escalonamentos;
    if (esc.ok) {
      const totalEscalonamentos = esc.dados.reduce((soma, e) => soma + e.qtd, 0);
      document.getElementById('im-numero-escalonamentos').innerText = totalEscalonamentos;
      document.getElementById('im-numero-marcadores').innerText = esc.dados.length;
      renderizarBarrasEscalonamento(esc.dados, document.getElementById('im-barras-escalonamento'));
      renderizarNiveisEscalonamento(esc.dados, document.getElementById('im-niveis-escalonamento'));
    } else {
      document.getElementById('im-numero-escalonamentos').innerText = '–';
      document.getElementById('im-numero-marcadores').innerText = '–';
      document.getElementById('im-barras-escalonamento').innerHTML = `<div class="erro-im">⚠ ${esc.erro}</div>`;
      document.getElementById('im-niveis-escalonamento').innerHTML = `<div class="erro-im">⚠ ${esc.erro}</div>`;
    }

    const dp = dados.duvidas_processadas;
    if (dp.ok) {
      duvidasProcessadasCompletas = dp.dados;
      popularFiltroSolicitante(dp.dados);
      aplicarFiltroSolicitante();
      renderizarBarrasSolicitantes(dp.dados, document.getElementById('im-barras-solicitantes'));
    } else {
      duvidasProcessadasCompletas = [];
      document.getElementById('im-tabela-duvidas').innerHTML = `<div class="erro-im">⚠ ${dp.erro}</div>`;
      document.getElementById('im-barras-solicitantes').innerHTML = `<div class="erro-im">⚠ ${dp.erro}</div>`;
    }

    const cpa = dados.chamados_por_analista;
    const elChamados = document.getElementById('im-barras-chamados');
    if (cpa && cpa.ok) {
      if (cpa.dados.length === 0) {
        elChamados.innerHTML = '<div class="vazio-im">Nenhum chamado com apontamento no período.</div>';
      } else {
        const topChamados = cpa.dados.slice(0, 15);
        const maiorQtd = topChamados[0].qtd;
        elChamados.innerHTML = topChamados.map(c => {
          const percentual = Math.max(6, (c.qtd / maiorQtd) * 100);
          return `
            <div class="barra-escalonamento">
              <div class="rotulo-marcador" title="${c.analista.replace(/"/g, '&quot;')}">${c.analista}</div>
              <div class="trilha">
                <div class="preenchimento" style="width:${percentual}%"><span>${c.qtd}</span></div>
              </div>
            </div>
          `;
        }).join('');
      }
    } else if (cpa) {
      elChamados.innerHTML = `<div class="erro-im">⚠ ${cpa.erro}</div>`;
    }
  } catch (e) {
    const msg = '<div class="erro-im">⚠ Erro ao carregar: ' + e + '</div>';
    document.getElementById('im-barras-escalonamento').innerHTML = msg;
    document.getElementById('im-barras-solicitantes').innerHTML = msg;
    document.getElementById('im-barras-chamados').innerHTML = msg;
  }
}

carregarIndicadoresMovidesk();
</script>
</body>
</html>
"""


def _montar_indicadores_movidesk_html(sessao: dict) -> str:
    return (
        _INDICADORES_MOVIDESK_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Indicadores Movidesk"))
        .replace("__FOOTER__", _montar_footer())
    )


_HORAS_TRABALHADAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Horas Trabalhadas</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-ht { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1120px; margin: 0 auto 10px auto; }
  .cabecalho-ht h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-ht .sub { color: var(--fg-dim); font-size: 12.5px; }
  .aviso-ht { max-width: 1120px; margin: 0 auto 20px auto; color: var(--fg-dim); font-size: 12px;
              line-height: 1.5; background: rgba(255,255,255,.03); border: 1px solid var(--border);
              border-radius: 10px; padding: 10px 14px; }

  .filtro-horas-im { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .filtro-horas-im select, .filtro-horas-im input { padding: 6px 10px; font-size: 12.5px; }
  .filtro-horas-im select { min-width: 130px; padding-right: 30px; }

  .painel-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1120px; margin: 0 auto 20px auto; }
  .painel-im h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .cabecalho-painel-im { display: flex; justify-content: space-between; align-items: center;
                          flex-wrap: wrap; gap: 10px; margin-bottom: 4px; }
  .cabecalho-painel-im h2 { margin: 0; }

  .grade-resumo-horas { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
                         gap: 12px; margin-bottom: 20px; }
  .cartao-resumo-horas { background: rgba(255,255,255,.03); border: 1px solid var(--border);
                          border-radius: 10px; padding: 14px 16px; }
  .nome-analista-horas { font-size: 12.5px; font-weight: 700; color: var(--fg);
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .escala-analista-horas { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                            letter-spacing: .03em; margin: 2px 0 10px 0; }
  .horas-linha-resumo { font-size: 17px; font-weight: 700; color: var(--fg); margin-bottom: 4px; }
  .detalhe-resumo-horas { font-size: 11px; color: var(--fg-dim); margin-top: 6px; }

  .tabela-im-rolagem { overflow-x: auto; border-radius: 10px; }
  table.tabela-im { width: 100%; border-collapse: collapse; min-width: 100%; }
  table.tabela-im th, table.tabela-im td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border);
                                             font-size: 12.5px; white-space: nowrap; overflow: hidden;
                                             text-overflow: ellipsis; max-width: 220px; }
  table.tabela-im th { color: var(--teal); font-weight: 600; text-transform: uppercase; font-size: 10.5px;
                        letter-spacing: .03em; background: rgba(255,255,255,.03); position: sticky; top: 0; }
  table.tabela-im tbody tr { transition: background .12s; }
  table.tabela-im tbody tr:hover { background: rgba(255,255,255,.03); }
  table.tabela-im tbody tr:nth-child(even) { background: rgba(255,255,255,.015); }
  table.tabela-im tr:last-child td { border-bottom: none; }
  .vazio-im { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .erro-im { color: var(--erro); font-size: 12.5px; }
  .carregando-im { color: var(--fg-dim); font-size: 12.5px; }

  .tarja-ausencias-ht { max-width: 1120px; margin: 0 auto 16px auto; background: rgba(76,201,240,.08);
                          border: 1px solid rgba(76,201,240,.3); border-radius: 10px; padding: 12px 16px;
                          display: none; }
  .tarja-ausencias-ht .titulo-tarja-ht { font-size: 11px; font-weight: 700; text-transform: uppercase;
                                           letter-spacing: .04em; color: #4cc9f0; margin-bottom: 8px; }
  .tarja-ausencias-ht .itens-tarja-ht { display: flex; flex-wrap: wrap; gap: 8px; }
  .pilula-ausencia-ht { font-size: 11.5px; padding: 4px 10px; border-radius: 20px; background: rgba(255,255,255,.05);
                          border: 1px solid var(--border); white-space: nowrap; }
  .pilula-ausencia-ht.feriado { background: rgba(241,76,76,.1); border-color: rgba(241,76,76,.3); color: #ff9d9d; }
  .pilula-ausencia-ht.day_off { background: rgba(255,255,255,.06); border-color: var(--border-forte); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-ht">
      <div>
        <h1>Horas Trabalhadas</h1>
        <div class="sub">Apontamentos de horas por analista, direto do banco do Movidesk.</div>
      </div>
    </div>
    <div class="aviso-ht">
      Consulta direto na tabela de apontamentos do banco do Movidesk.
      Quem não tem escala configurada no escala.json é considerado 5x2
      por padrão.
    </div>
    <div class="tarja-ausencias-ht" id="tarja-ausencias-ht">
      <div class="titulo-tarja-ht">Feriados, férias e day offs no período (já excluídos da meta)</div>
      <div class="itens-tarja-ht" id="itens-tarja-ht"></div>
    </div>

    <div class="painel-im">
      <div class="cabecalho-painel-im">
        <h2>Horas trabalhadas</h2>
        <div class="filtro-horas-im">
          <select id="horas-modo-filtro" onchange="alternarModoFiltroHoras()">
            <option value="dia">Dia específico</option>
            <option value="mes">Mês inteiro</option>
            <option value="periodo">Período (de - até)</option>
          </select>
          <input type="date" id="horas-filtro-dia">
          <input type="month" id="horas-filtro-mes" style="display:none">
          <span id="horas-filtro-periodo-grupo" style="display:none; gap:8px; align-items:center">
            <input type="date" id="horas-filtro-periodo-inicio">
            <span style="color:var(--fg-dim); font-size:12px">até</span>
            <input type="date" id="horas-filtro-periodo-fim">
          </span>
          <select id="horas-filtro-equipe">
            <option value="">Todas as equipes</option>
            <option value="Suporte">Suporte</option>
            <option value="Monitoramento">Monitoramento</option>
          </select>
          <button class="btn-mini" onclick="carregarHorasTrabalhadas()">Aplicar</button>
          <button class="btn-mini" id="btn-exportar-horas" onclick="exportarHorasTrabalhadas()">Exportar Excel</button>
        </div>
      </div>
      <div id="horas-carregando" class="carregando-im" style="display:none">Consultando o banco do Movidesk...</div>
      <div id="horas-erro" class="erro-im"></div>
      <div id="horas-resumo-cards" class="grade-resumo-horas"></div>
      <div id="horas-tabela-detalhe"></div>
    </div>
  </div>

  __FOOTER__

<script>
(function () {
  document.getElementById('horas-filtro-dia').value = new Date().toISOString().slice(0, 10);
  document.getElementById('horas-filtro-mes').value = new Date().toISOString().slice(0, 7);
  document.getElementById('horas-filtro-periodo-inicio').value = new Date().toISOString().slice(0, 8) + '01';
  document.getElementById('horas-filtro-periodo-fim').value = new Date().toISOString().slice(0, 10);
})();

function alternarModoFiltroHoras() {
  const modo = document.getElementById('horas-modo-filtro').value;
  document.getElementById('horas-filtro-dia').style.display = modo === 'dia' ? '' : 'none';
  document.getElementById('horas-filtro-mes').style.display = modo === 'mes' ? '' : 'none';
  document.getElementById('horas-filtro-periodo-grupo').style.display = modo === 'periodo' ? 'inline-flex' : 'none';
}

function formatarPercentualHoras(p) {
  if (p === null || p === undefined) return '–';
  const cor = p >= 90 ? 'var(--ok)' : (p >= 50 ? 'var(--run)' : 'var(--erro)');
  return `<span style="color:${cor}; font-weight:700">${p.toFixed(1)}%</span>`;
}

function agruparHorasPorAnalista(linhas, metaPeriodoPorAnalista) {
  const grupos = {};
  for (const l of linhas) {
    if (!grupos[l.analista]) {
      grupos[l.analista] = {
        analista: l.analista, escala: l.escala, cadastrado_na_escala: l.cadastrado_na_escala,
        // a meta agora vem pronta do backend, calculada pelo calendário
        // inteiro do período (não soma mais linha por linha aqui) - ver
        // _calcular_meta_periodo no servidor pro motivo
        minutos_trabalhados: 0, minutos_meta: metaPeriodoPorAnalista[l.analista] || 0,
        dias_com_registro: 0, qtd_tickets: 0,
      };
    }
    const g = grupos[l.analista];
    g.minutos_trabalhados += l.minutos_trabalhados;
    g.dias_com_registro += 1;
    g.qtd_tickets += l.qtd_tickets;
  }
  return Object.values(grupos).sort((a, b) => a.analista.localeCompare(b.analista));
}

function minutosParaHoras(min) {
  min = Math.round(min);
  const h = Math.floor(min / 60), m = min % 60;
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
}

function obterPeriodoSelecionadoHoras() {
  const modo = document.getElementById('horas-modo-filtro').value;
  let dataInicio, dataFim;
  if (modo === 'dia') {
    const dia = document.getElementById('horas-filtro-dia').value;
    if (!dia) { document.getElementById('horas-erro').innerText = 'Selecione uma data.'; return null; }
    dataInicio = dia; dataFim = dia;
  } else if (modo === 'periodo') {
    dataInicio = document.getElementById('horas-filtro-periodo-inicio').value;
    dataFim = document.getElementById('horas-filtro-periodo-fim').value;
    if (!dataInicio || !dataFim) { document.getElementById('horas-erro').innerText = 'Selecione as duas datas do período.'; return null; }
    if (dataFim < dataInicio) { document.getElementById('horas-erro').innerText = 'A data final não pode ser antes da inicial.'; return null; }
  } else {
    const mes = document.getElementById('horas-filtro-mes').value;
    if (!mes) { document.getElementById('horas-erro').innerText = 'Selecione um mês.'; return null; }
    const [ano, mesNum] = mes.split('-').map(Number);
    dataInicio = mes + '-01';
    const ultimoDia = new Date(ano, mesNum, 0).getDate();
    dataFim = mes + '-' + String(ultimoDia).padStart(2, '0');
  }
  return { dataInicio, dataFim };
}

function renderizarTarjaAusencias(ausencias) {
  const tarja = document.getElementById('tarja-ausencias-ht');
  if (!ausencias.length) { tarja.style.display = 'none'; return; }
  const escapar = (txt) => String(txt).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rotulosTipo = { feriado: '📅', ferias: '🏖️', day_off: '☕' };
  document.getElementById('itens-tarja-ht').innerHTML = ausencias.map(a => {
    const periodo = a.inicio === a.fim ? a.inicio : `${a.inicio} a ${a.fim}`;
    const rotuloTipo = a.tipo === 'feriado' ? '' : (a.tipo === 'day_off' ? ' (Day Off)' : ' (Férias)');
    return `<span class="pilula-ausencia-ht ${a.tipo}">${rotulosTipo[a.tipo] || ''} ${escapar(a.nome)}${rotuloTipo} · ${periodo}</span>`;
  }).join('');
  tarja.style.display = 'block';
}

async function carregarHorasTrabalhadas() {
  const periodo = obterPeriodoSelecionadoHoras();
  if (!periodo) return;
  const { dataInicio, dataFim } = periodo;

  document.getElementById('horas-erro').innerText = '';
  document.getElementById('horas-resumo-cards').innerHTML = '';
  document.getElementById('horas-tabela-detalhe').innerHTML = '';
  document.getElementById('tarja-ausencias-ht').style.display = 'none';
  document.getElementById('horas-carregando').style.display = 'block';

  try {
    const equipeFiltro = document.getElementById('horas-filtro-equipe').value;
    let url = `/api/indicadores-movidesk/horas?data_inicio=${dataInicio}&data_fim=${dataFim}`;
    if (equipeFiltro) url += `&equipe=${encodeURIComponent(equipeFiltro)}`;
    const resp = await fetch(url);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    document.getElementById('horas-carregando').style.display = 'none';

    if (!dados.ok) {
      document.getElementById('horas-erro').innerText = '⚠ ' + dados.erro;
      return;
    }

    renderizarTarjaAusencias(dados.ausencias_periodo || []);

    if (dados.linhas.length === 0) {
      document.getElementById('horas-tabela-detalhe').innerHTML = '<div class="vazio-im">Nenhum apontamento de horas encontrado no período.</div>';
      return;
    }

    const resumos = agruparHorasPorAnalista(dados.linhas, dados.meta_periodo_por_analista || {});
    document.getElementById('horas-resumo-cards').innerHTML = resumos.map(r => {
      const percentual = r.minutos_meta > 0 ? (r.minutos_trabalhados / r.minutos_meta * 100) : null;
      const semEscala = !r.cadastrado_na_escala ? '<span title="Não cadastrado no escala.json - considerado 5x2 por padrão" style="color:var(--fg-dim); cursor:help"> ⓘ</span>' : '';
      return `
        <div class="cartao-resumo-horas">
          <div class="nome-analista-horas">${r.analista}${semEscala}</div>
          <div class="escala-analista-horas">${r.escala}</div>
          <div class="horas-linha-resumo">
            <span>${minutosParaHoras(r.minutos_trabalhados)}</span>
            <span style="color:var(--fg-dim)"> / ${minutosParaHoras(r.minutos_meta)}</span>
          </div>
          <div>${formatarPercentualHoras(percentual)}</div>
          <div class="detalhe-resumo-horas">${r.dias_com_registro} dia(s) · ${r.qtd_tickets} chamado(s)</div>
        </div>
      `;
    }).join('');

    const linhasOrdenadas = dados.linhas.slice().sort((a, b) => a.analista.localeCompare(b.analista) || a.data_iso.localeCompare(b.data_iso));
    const corpo = linhasOrdenadas.map(l => `
      <tr>
        <td>${l.analista}</td>
        <td>${l.data}</td>
        <td>${l.escala}</td>
        <td>${l.horas_trabalhadas}</td>
        <td>${l.meta_horas}</td>
        <td>${formatarPercentualHoras(l.percentual)}</td>
        <td>${l.qtd_tickets}</td>
      </tr>
    `).join('');
    document.getElementById('horas-tabela-detalhe').innerHTML = `
      <div class="tabela-im-rolagem">
        <table class="tabela-im">
          <thead><tr><th>Analista</th><th>Data</th><th>Escala</th><th>Horas</th><th>Meta</th><th>%</th><th>Chamados</th></tr></thead>
          <tbody>${corpo}</tbody>
        </table>
      </div>
    `;
  } catch (e) {
    document.getElementById('horas-carregando').style.display = 'none';
    document.getElementById('horas-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

carregarHorasTrabalhadas();

async function exportarHorasTrabalhadas() {
  const periodo = obterPeriodoSelecionadoHoras();
  if (!periodo) return;
  const { dataInicio, dataFim } = periodo;
  const botao = document.getElementById('btn-exportar-horas');
  const textoOriginal = botao.innerText;
  botao.disabled = true;
  botao.innerText = 'Gerando...';
  try {
    const equipeFiltro = document.getElementById('horas-filtro-equipe').value;
    let urlExportar = `/api/horas-trabalhadas/exportar?data_inicio=${dataInicio}&data_fim=${dataFim}`;
    if (equipeFiltro) urlExportar += `&equipe=${encodeURIComponent(equipeFiltro)}`;
    const resp = await fetch(urlExportar);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (!resp.ok) {
      let msg = 'Erro ao gerar a exportação.';
      try { msg = (await resp.json()).erro || msg; } catch (e) {}
      document.getElementById('horas-erro').innerText = '⚠ ' + msg;
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `horas_trabalhadas_${dataInicio}_a_${dataFim}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    document.getElementById('horas-erro').innerText = 'Erro ao exportar: ' + e;
  } finally {
    botao.disabled = false;
    botao.innerText = textoOriginal;
  }
}
</script>
</body>
</html>
"""


def _montar_horas_trabalhadas_html(sessao: dict) -> str:
    return (
        _HORAS_TRABALHADAS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Horas Trabalhadas"))
        .replace("__FOOTER__", _montar_footer())
    )


_AUTOMACAO_MOVIDESK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Automação Movidesk</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-am { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1120px; margin: 0 auto 22px auto; }
  .cabecalho-am h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-am .sub { color: var(--fg-dim); font-size: 12.5px; }
  .filtro-am { display: flex; align-items: end; gap: 10px; }
  .filtro-am label { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 5px;
                      text-transform: uppercase; letter-spacing: .04em; }

  .painel-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1120px; margin: 0 auto 20px auto; }
  .painel-im h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }

  .tabela-im-rolagem { overflow-x: auto; border-radius: 10px; }
  table.tabela-im { width: 100%; border-collapse: collapse; min-width: 100%; }
  table.tabela-im th, table.tabela-im td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border);
                                             font-size: 12.5px; white-space: nowrap; overflow: hidden;
                                             text-overflow: ellipsis; max-width: 220px; }
  table.tabela-im th { color: var(--teal); font-weight: 600; text-transform: uppercase; font-size: 10.5px;
                        letter-spacing: .03em; background: rgba(255,255,255,.03); position: sticky; top: 0; }
  table.tabela-im tbody tr { transition: background .12s; }
  table.tabela-im tbody tr:hover { background: rgba(255,255,255,.03); }
  table.tabela-im tbody tr:nth-child(even) { background: rgba(255,255,255,.015); }
  table.tabela-im tr:last-child td { border-bottom: none; }
  .vazio-im { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .erro-im { color: var(--erro); font-size: 12.5px; }
  .carregando-im { color: var(--fg-dim); font-size: 12.5px; }

  .aviso-em-breve-am { max-width: 1120px; margin: 0 auto 20px auto; color: var(--fg-dim); font-size: 12px;
                        line-height: 1.5; background: rgba(255,255,255,.03); border: 1px dashed var(--border-forte);
                        border-radius: 10px; padding: 12px 16px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-am">
      <div>
        <h1>Automação Movidesk</h1>
        <div class="sub">NOC, Satisfação, Uptime, Tickets, GMUD, Jira e outras automações de atendimento.</div>
      </div>
    </div>

    <div class="aviso-em-breve-am">
      As demais automações de NOC/Satisfação/Uptime/GMUD/Jira ainda estão
      em construção - por enquanto esse card já traz o Controle de
      Sincronização, que estava misturado no Indicadores Movidesk antes.
    </div>

    <div class="painel-im">
      <h2>Controle de sincronização</h2>
      <div id="am-tabela-sincronizacao"><div class="carregando-im">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

<script>
function formatarNomeColuna(nomeCru) {
  if (!nomeCru.includes('_') && nomeCru !== nomeCru.toUpperCase()) {
    return nomeCru;
  }
  return nomeCru
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\\b\\w/g, c => c.toUpperCase());
}

function renderizarTabelaDinamica(linhas, elementoDestino) {
  if (!linhas || linhas.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum registro no período.</div>';
    return;
  }
  const colunas = Object.keys(linhas[0]);
  const cabecalho = colunas.map(c => `<th>${formatarNomeColuna(c)}</th>`).join('');
  const linhasHtml = linhas.slice(0, 200).map(l =>
    '<tr>' + colunas.map(c => `<td title="${String(l[c] ?? '').replace(/"/g, '&quot;')}">${l[c]}</td>`).join('') + '</tr>'
  ).join('');
  const avisoLimite = linhas.length > 200
    ? `<div class="vazio-im">Mostrando as primeiras 200 de ${linhas.length} linhas.</div>` : '';
  elementoDestino.innerHTML = `<div class="tabela-im-rolagem"><table class="tabela-im"><thead><tr>${cabecalho}</tr></thead><tbody>${linhasHtml}</tbody></table></div>${avisoLimite}`;
}

async function carregarSincronizacao() {
  const primeiroDiaMes = new Date().toISOString().slice(0, 8) + '01';
  const el = document.getElementById('am-tabela-sincronizacao');
  el.innerHTML = '<div class="carregando-im">Carregando...</div>';
  try {
    const resp = await fetch('/api/indicadores-movidesk?data_inicio=' + primeiroDiaMes);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      el.innerHTML = `<div class="erro-im">⚠ ${dados.erro || 'Não foi possível carregar.'}</div>`;
      return;
    }
    const sinc = dados.sincronizacao;
    if (sinc.ok) {
      renderizarTabelaDinamica(sinc.dados, el);
    } else {
      el.innerHTML = `<div class="erro-im">⚠ ${sinc.erro}</div>`;
    }
  } catch (e) {
    el.innerHTML = '<div class="erro-im">⚠ Erro ao carregar: ' + e + '</div>';
  }
}

carregarSincronizacao();
</script>
</body>
</html>
"""


def _montar_automacao_movidesk_html(sessao: dict) -> str:
    return (
        _AUTOMACAO_MOVIDESK_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Automação Movidesk"))
        .replace("__FOOTER__", _montar_footer())
    )


_MANUTENCAO_ALERTAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção de Alertas em Banco</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: 900px; margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .barra-selecao-lote { display: flex; align-items: center; gap: 10px; padding: 10px 14px;
                         background: rgba(45,184,207,.08); border-bottom: 1px solid var(--border);
                         font-size: 12.5px; color: var(--fg-dim); }
  .barra-selecao-lote span { color: var(--teal); font-weight: 600; margin-right: 4px; }
  button.btn-mini:disabled { opacity: .35; cursor: not-allowed; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: 900px; }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .badge-status { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 10px;
                  font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .badge-status.ativo { background: rgba(78,201,176,.15); color: var(--ok); border: 1px solid rgba(78,201,176,.35); }
  .badge-status.inativo { background: rgba(139,152,165,.15); color: var(--fg-dim); border: 1px solid var(--border); }

  .filtros-alertas { display: flex; gap: 10px; margin: 0 auto 14px auto; max-width: 900px; flex-wrap: wrap; }
  .filtros-alertas input[type="text"] { flex: 1; min-width: 180px; padding: 8px 12px; border-radius: 8px;
                    border: 1px solid var(--border); background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; }
  .filtros-alertas input[type="text"]:focus { outline: none; border-color: var(--teal); }
  .filtros-alertas select { padding: 8px 12px; border-radius: 8px; font-size: 13px; }
  .acoes-linha { display: flex; gap: 6px; }
  input[readonly] { opacity: .65; cursor: not-allowed; }
  .dica-campo.dica-travado { color: var(--run); }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; padding: 24px; }
  .modal-fundo.aberto { display: flex; }
  .modal-largo { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 30px 32px; width: 100%; max-width: 560px; max-height: 88vh; overflow-y: auto;
           box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal-largo h3 { margin: 0 0 18px 0; font-size: 16px; color: var(--teal); }
  .modal-largo label { display: block; font-size: 11px; color: var(--fg-dim); margin: 14px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal-largo input, .modal-largo select, .modal-largo textarea {
                 width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal-largo textarea { font-family: Consolas, monospace; font-size: 12.5px; resize: vertical; min-height: 70px; }
  .modal-largo input:focus, .modal-largo select:focus, .modal-largo textarea:focus {
                 outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .linha-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
  .dica-campo { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.4; }
  .campo-checkbox { display: flex; align-items: center; gap: 8px; margin-top: 16px; }
  .campo-checkbox input { width: auto; }
  .campo-checkbox label { margin: 0; text-transform: none; font-size: 13px; color: var(--fg); letter-spacing: 0; }
  .acoes-modal { display: flex; gap: 8px; margin-top: 22px; }
  .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }

  .bloco-sucesso { text-align: center; }
  .bloco-sucesso .icone-ok { width: 52px; height: 52px; border-radius: 50%; background: rgba(78,201,176,.15);
                              display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; }
  .bloco-sucesso .icone-ok svg { width: 26px; height: 26px; stroke: var(--ok); }
  .bloco-sucesso h4 { margin: 0 0 8px 0; font-size: 15px; }
  .bloco-sucesso p { color: var(--fg-dim); font-size: 12.5px; line-height: 1.6; text-align: left; }
  .bloco-gatilho { background: rgba(0,0,0,.25); border: 1px solid var(--border); border-radius: 10px;
                   padding: 14px 16px; text-align: left; font-family: Consolas, monospace; font-size: 12px;
                   margin: 14px 0; line-height: 1.8; }
  .bloco-gatilho b { color: var(--teal); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Alertas cadastrados (CONFIGURACOES_ALERTA)</h3>
      <button class="btn-accent" onclick="abrirModalNovoAlerta()">+ Novo alerta</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro-banco" style="display:none; max-width:900px; margin:0 auto 16px auto;"></div>

    <div class="filtros-alertas">
      <input type="text" id="filtro-cliente" placeholder="Filtrar por cliente..." oninput="aplicarFiltrosAlertas()">
      <select id="filtro-status" onchange="aplicarFiltrosAlertas()">
        <option value="">Todos os status</option>
        <option value="1">Ativo</option>
        <option value="0">Inativo</option>
      </select>
    </div>

    <div class="painel">
      <div class="barra-selecao-lote" id="barra-selecao-lote" style="display:none">
        <span id="texto-selecao-lote"></span>
        <button class="btn-mini" onclick="alterarDisponibilidadeLote(true)">Ativar selecionados</button>
        <button class="btn-mini" onclick="alterarDisponibilidadeLote(false)">Desativar selecionados</button>
        <button class="btn-mini" onclick="limparSelecaoAlertas()">Limpar seleção</button>
      </div>
      <table>
        <thead>
          <tr>
            <th><input type="checkbox" id="checkbox-selecionar-todos" onchange="alternarSelecionarTodosAlertas(this.checked)"></th>
            <th>ID</th><th>Cliente</th><th>Título</th><th>Tipo</th><th>Teto</th><th>Intervalo</th><th>Status</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela-alertas">
          <tr><td colspan="9" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-novo-alerta">
    <div class="modal-largo">
      <h3 id="titulo-modal-alerta">Novo alerta em CONFIGURACOES_ALERTA</h3>

      <div id="form-novo-alerta">
        <div class="linha-dupla">
          <div>
            <label>Cliente</label>
            <input type="text" id="alerta-cliente" placeholder="Nome do cliente">
          </div>
          <div>
            <label>Tipo de banco</label>
            <select id="alerta-tipo-banco">
              <option value="SQL">SQL Server</option>
              <option value="ORACLE">Oracle</option>
            </select>
          </div>
        </div>

        <label>Título</label>
        <input type="text" id="alerta-titulo" value="[ALERTA] ">
        <div class="dica-campo">Precisa começar com "[ALERTA]" - já vem preenchido, só complete.</div>

        <label>Conexão</label>
        <select id="alerta-conexao-select" onchange="aplicarConexaoSelecionada()">
          <option value="">Selecione uma String Connection...</option>
        </select>
        <input type="hidden" id="alerta-conexao">
        <div class="dica-campo" id="dica-conexao-nao-cadastrada" style="display:none; color:var(--erro)">
          Este alerta usa uma conexão que não está cadastrada em String Connections - selecione uma da lista pra substituir.
        </div>

        <label>Script</label>
        <textarea id="alerta-script" placeholder="SELECT COUNT(*) FROM ..."></textarea>
        <div class="dica-campo">SQL puro - a conversão pra base64 é feita automaticamente. Precisa sempre trazer um número exato (via COUNT) pra comparar com o Teto do alerta.</div>

        <div class="linha-dupla">
          <div>
            <label>Teto do alerta</label>
            <input type="number" id="alerta-teto" placeholder="Ex.: 10" step="any">
          </div>
          <div>
            <label>Intervalo (minutos)</label>
            <input type="number" id="alerta-intervalo" placeholder="Ex.: 15" min="1" step="1">
          </div>
        </div>

        <label>E-mails</label>
        <input type="text" id="alerta-emails" value="__EMAIL_MONITORAMENTO__" readonly>
        <div class="dica-campo dica-travado">Sempre o e-mail padrão do monitoramento - não é editável.</div>

        <label>Descrição (corpo do e-mail)</label>
        <textarea id="alerta-descricao" placeholder="Texto que vai no corpo do e-mail enviado"></textarea>

        <div class="campo-checkbox">
          <input type="checkbox" id="alerta-disponibilidade" checked>
          <label for="alerta-disponibilidade">Ativar este alerta imediatamente</label>
        </div>

        <div class="erro-modal" id="erro-novo-alerta"></div>
        <div class="acoes-modal">
          <button class="btn-accent" id="botao-salvar-alerta" onclick="salvarAlertaBanco()" style="flex:1">Criar alerta</button>
          <button onclick="fecharModalNovoAlerta()" style="flex:1">Cancelar</button>
        </div>
      </div>

      <div id="sucesso-novo-alerta" style="display:none">
        <div class="bloco-sucesso">
          <div class="icone-ok">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
          </div>
          <h4>Alerta criado com sucesso</h4>
          <p>
            Falta um passo manual: solicitar a criação do gatilho no Movidesk
            (peça pra algum N2 ou N3). Use estes dados na
            abertura do serviço:
          </p>
          <div class="bloco-gatilho" id="texto-gatilho"></div>
          <div class="acoes-modal">
            <button class="btn-accent" onclick="copiarTextoGatilho()" style="flex:1">Copiar texto</button>
            <button onclick="fecharModalNovoAlerta()" style="flex:1">Fechar</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  __FOOTER__

<script>
let gatilhoAtual = null;
let idEmEdicao = null;  // null = criando um novo; numero = editando esse ID
let todosOsAlertas = [];

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

async function carregarAlertasBanco() {
  const avisoEl = document.getElementById('aviso-erro-banco');
  try {
    const resp = await fetch('/api/manutencao-alertas');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível carregar os alertas do banco de monitoramento: ' + (dados.erro || 'erro desconhecido.');
      document.getElementById('corpo-tabela-alertas').innerHTML =
        '<tr><td colspan="9" style="color:var(--fg-dim)">Sem dados no momento.</td></tr>';
      return;
    }
    avisoEl.style.display = 'none';
    todosOsAlertas = dados.registros;
    aplicarFiltrosAlertas();
  } catch (e) {
    avisoEl.style.display = 'block';
    avisoEl.innerText = '⚠ Erro ao carregar: ' + e;
  }
}

function aplicarFiltrosAlertas() {
  const filtroCliente = document.getElementById('filtro-cliente').value.trim().toLowerCase();
  const filtroStatus = document.getElementById('filtro-status').value;

  let filtrados = todosOsAlertas;
  if (filtroCliente) {
    filtrados = filtrados.filter(r => (r.cliente || '').toLowerCase().includes(filtroCliente));
  }
  if (filtroStatus !== '') {
    filtrados = filtrados.filter(r => String(Number(r.disponibilidade) === 1 ? 1 : 0) === filtroStatus);
  }

  const corpo = document.getElementById('corpo-tabela-alertas');
  if (todosOsAlertas.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum alerta cadastrado ainda.</td></tr>';
    return;
  }
  if (filtrados.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum alerta bate com o filtro.</td></tr>';
    return;
  }
  corpo.innerHTML = filtrados.map(r => `
    <tr>
      <td><input type="checkbox" class="checkbox-alerta" value="${r.id}" ${idsSelecionadosAlertas.has(String(r.id)) ? 'checked' : ''} onchange="atualizarSelecaoAlertas()"></td>
      <td>${r.id}</td>
      <td>${r.cliente || ''}</td>
      <td>${r.titulo || ''}</td>
      <td>${r.tipo_banco || ''}</td>
      <td>${r.teto_alerta ?? ''}</td>
      <td>${r.intervalo_minutos ?? ''} min</td>
      <td>
        <select onchange="alternarDisponibilidadeBanco(${r.id}, this.value)">
          <option value="true" ${Number(r.disponibilidade) === 1 ? 'selected' : ''}>Ativo</option>
          <option value="false" ${Number(r.disponibilidade) !== 1 ? 'selected' : ''}>Inativo</option>
        </select>
      </td>
      <td><button class="btn-mini btn-editar-alerta" onclick="abrirModalEditarAlerta(${r.id})">Editar</button></td>
    </tr>
  `).join('');
  atualizarSelecaoAlertas();
}

// --- Seleção em lote (ativar/desativar vários alertas de uma vez) ---
let idsSelecionadosAlertas = new Set();

function atualizarSelecaoAlertas() {
  const marcados = Array.from(document.querySelectorAll('.checkbox-alerta:checked')).map(c => c.value);
  idsSelecionadosAlertas = new Set(marcados);

  const barra = document.getElementById('barra-selecao-lote');
  const texto = document.getElementById('texto-selecao-lote');
  if (idsSelecionadosAlertas.size > 0) {
    barra.style.display = 'flex';
    texto.innerText = idsSelecionadosAlertas.size + ' selecionado(s)';
  } else {
    barra.style.display = 'none';
  }

  // com mais de um alerta marcado, editar não faz sentido (só dá pra
  // editar um de cada vez) - desabilita os botões de editar até a
  // seleção voltar pra 0 ou 1
  const desabilitarEdicao = idsSelecionadosAlertas.size > 1;
  document.querySelectorAll('.btn-editar-alerta').forEach(btn => {
    btn.disabled = desabilitarEdicao;
    btn.title = desabilitarEdicao ? 'Desmarque para editar apenas um alerta por vez' : '';
  });

  const todos = document.querySelectorAll('.checkbox-alerta');
  const checkboxTodos = document.getElementById('checkbox-selecionar-todos');
  if (checkboxTodos) {
    checkboxTodos.checked = todos.length > 0 && idsSelecionadosAlertas.size === todos.length;
    checkboxTodos.indeterminate = idsSelecionadosAlertas.size > 0 && idsSelecionadosAlertas.size < todos.length;
  }
}

function alternarSelecionarTodosAlertas(marcarTodos) {
  document.querySelectorAll('.checkbox-alerta').forEach(c => { c.checked = marcarTodos; });
  atualizarSelecaoAlertas();
}

function limparSelecaoAlertas() {
  document.querySelectorAll('.checkbox-alerta').forEach(c => { c.checked = false; });
  atualizarSelecaoAlertas();
}

async function alterarDisponibilidadeLote(ativar) {
  const ids = Array.from(idsSelecionadosAlertas);
  if (ids.length === 0) return;
  let sucesso = 0, falha = 0;
  for (const id of ids) {
    try {
      const resp = await fetch('/api/manutencao-alertas/disponibilidade', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'id=' + encodeURIComponent(id) + '&disponibilidade=' + (ativar ? 'true' : 'false'),
      });
      const dados = await resp.json();
      if (dados.ok) sucesso++; else falha++;
    } catch (e) {
      falha++;
    }
  }
  mostrarToast(
    `${sucesso} alerta(s) ${ativar ? 'ativado(s)' : 'desativado(s)'}` + (falha > 0 ? `, ${falha} falhou(aram)` : '')
  );
  idsSelecionadosAlertas.clear();
  carregarAlertasBanco();
}

async function alternarDisponibilidadeBanco(id, valor) {
  const resp = await fetch('/api/manutencao-alertas/disponibilidade', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(id) + '&disponibilidade=' + valor,
  });
  const dados = await resp.json();
  if (dados.ok) {
    mostrarToast('Disponibilidade do alerta #' + id + ' atualizada.');
  } else {
    mostrarToast(dados.erro || 'Não foi possível atualizar.');
  }
  carregarAlertasBanco();
}

function abrirModalNovoAlerta() {
  idEmEdicao = null;
  document.getElementById('titulo-modal-alerta').innerText = 'Novo alerta em CONFIGURACOES_ALERTA';
  document.getElementById('botao-salvar-alerta').innerText = 'Criar alerta';
  document.getElementById('form-novo-alerta').style.display = 'block';
  document.getElementById('sucesso-novo-alerta').style.display = 'none';
  document.getElementById('erro-novo-alerta').innerText = '';
  document.getElementById('alerta-cliente').value = '';
  document.getElementById('alerta-tipo-banco').value = 'SQL';
  document.getElementById('alerta-titulo').value = '[ALERTA] ';
  document.getElementById('alerta-conexao').value = '';
  document.getElementById('alerta-conexao-select').value = '';
  document.getElementById('dica-conexao-nao-cadastrada').style.display = 'none';
  document.getElementById('alerta-script').value = '';
  document.getElementById('alerta-teto').value = '';
  document.getElementById('alerta-intervalo').value = '';
  document.getElementById('alerta-descricao').value = '';
  document.getElementById('alerta-disponibilidade').checked = true;
  document.getElementById('modal-novo-alerta').classList.add('aberto');
}

async function abrirModalEditarAlerta(id) {
  const resp = await fetch('/api/manutencao-alertas/' + id);
  const dados = await resp.json();
  if (!dados.ok) {
    mostrarToast(dados.erro || 'Não foi possível carregar esse alerta.');
    return;
  }
  const r = dados.registro;
  idEmEdicao = id;
  document.getElementById('titulo-modal-alerta').innerText = 'Editar alerta #' + id + ' (CONFIGURACOES_ALERTA)';
  document.getElementById('botao-salvar-alerta').innerText = 'Salvar alterações';
  document.getElementById('form-novo-alerta').style.display = 'block';
  document.getElementById('sucesso-novo-alerta').style.display = 'none';
  document.getElementById('erro-novo-alerta').innerText = '';
  document.getElementById('alerta-cliente').value = r.cliente || '';
  document.getElementById('alerta-tipo-banco').value = r.tipo_banco || 'SQL';
  document.getElementById('alerta-titulo').value = r.titulo || '[ALERTA] ';
  document.getElementById('alerta-conexao').value = r.conexao || '';
  document.getElementById('alerta-script').value = r.script || '';
  document.getElementById('alerta-teto').value = r.teto_alerta ?? '';
  document.getElementById('alerta-intervalo').value = r.intervalo_minutos ?? '';
  document.getElementById('alerta-descricao').value = r.descricao || '';
  document.getElementById('alerta-disponibilidade').checked = Number(r.disponibilidade) === 1;

  // acha qual String Connection cadastrada corresponde à conexão já
  // salva nesse alerta, pra deixar selecionada no dropdown - sem
  // mostrar o valor bruto em campo nenhum. Se não achar nenhuma
  // correspondência (alerta criado antes dessa funcionalidade existir,
  // ou editado direto no banco), avisa sem revelar a string.
  const selectConexao = document.getElementById('alerta-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada');
  const encontrada = stringConnectionsDisponiveis.find(c => c.conexao === r.conexao);
  if (encontrada) {
    selectConexao.value = encontrada.id;
    avisoNaoCadastrada.style.display = 'none';
  } else if (r.conexao) {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'block';
  } else {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'none';
  }

  document.getElementById('modal-novo-alerta').classList.add('aberto');
}

function fecharModalNovoAlerta() {
  document.getElementById('modal-novo-alerta').classList.remove('aberto');
  carregarAlertasBanco();
}

function _corpoFormularioAlerta() {
  return 'cliente=' + encodeURIComponent(document.getElementById('alerta-cliente').value) +
    '&tipo_banco=' + encodeURIComponent(document.getElementById('alerta-tipo-banco').value) +
    '&titulo=' + encodeURIComponent(document.getElementById('alerta-titulo').value) +
    '&conexao=' + encodeURIComponent(document.getElementById('alerta-conexao').value) +
    '&script=' + encodeURIComponent(document.getElementById('alerta-script').value) +
    '&teto_alerta=' + encodeURIComponent(document.getElementById('alerta-teto').value) +
    '&intervalo_minutos=' + encodeURIComponent(document.getElementById('alerta-intervalo').value) +
    '&emails=' + encodeURIComponent(document.getElementById('alerta-emails').value) +
    '&descricao=' + encodeURIComponent(document.getElementById('alerta-descricao').value) +
    '&disponibilidade=' + (document.getElementById('alerta-disponibilidade').checked ? 'true' : 'false');
}

async function salvarAlertaBanco() {
  const erroEl = document.getElementById('erro-novo-alerta');

  if (!document.getElementById('alerta-conexao').value) {
    erroEl.innerText = 'Selecione uma String Connection pra esse alerta.';
    return;
  }

  if (idEmEdicao === null) {
    const resp = await fetch('/api/manutencao-alertas/criar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: _corpoFormularioAlerta(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível criar o alerta.';
      return;
    }
    gatilhoAtual = dados.gatilho;
    document.getElementById('texto-gatilho').innerHTML =
      '<b>Nome:</b> ' + gatilhoAtual.nome + '<br>' +
      '<b>Solicitante:</b> ' + gatilhoAtual.solicitante + '<br>' +
      '<b>Serviço:</b> ' + gatilhoAtual.servico;
    document.getElementById('form-novo-alerta').style.display = 'none';
    document.getElementById('sucesso-novo-alerta').style.display = 'block';
  } else {
    const resp = await fetch('/api/manutencao-alertas/atualizar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(idEmEdicao) + '&' + _corpoFormularioAlerta(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível salvar as alterações.';
      return;
    }
    mostrarToast('Alerta #' + idEmEdicao + ' atualizado.');
    fecharModalNovoAlerta();
  }
}

function copiarTextoGatilho() {
  if (!gatilhoAtual) return;
  const texto = 'Nome: ' + gatilhoAtual.nome + '\\nSolicitante: ' + gatilhoAtual.solicitante +
    '\\nServiço: ' + gatilhoAtual.servico;
  copiarTextoParaAreaDeTransferencia(texto);
}

// navigator.clipboard só funciona em "contexto seguro" (HTTPS ou
// localhost) - como o painel roda em HTTP puro na rede interna
// (http://pda.exemplo:8765/, não https), essa API fica indisponível
// no navegador e a chamada falhava sem erro visível nenhum. Esse
// fallback usa o método antigo (textarea invisível + document.execCommand)
// que funciona independente de HTTPS.
function copiarTextoParaAreaDeTransferencia(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(texto)
      .then(() => mostrarToast('Texto copiado.'))
      .catch(() => copiarViaTextareaFallback(texto));
  } else {
    copiarViaTextareaFallback(texto);
  }
}

function copiarViaTextareaFallback(texto) {
  const areaTemp = document.createElement('textarea');
  areaTemp.value = texto;
  areaTemp.style.position = 'fixed';
  areaTemp.style.left = '-9999px';
  areaTemp.style.top = '0';
  document.body.appendChild(areaTemp);
  areaTemp.focus();
  areaTemp.select();
  try {
    const sucesso = document.execCommand('copy');
    mostrarToast(sucesso ? 'Texto copiado.' : 'Não foi possível copiar automaticamente - selecione e copie manualmente.');
  } catch (e) {
    mostrarToast('Não foi possível copiar automaticamente - selecione e copie manualmente.');
  }
  document.body.removeChild(areaTemp);
}

// --- String Connections no formulário de alerta (preenchimento rápido) ---
let stringConnectionsDisponiveis = [];

async function carregarStringConnectionsParaSelect() {
  try {
    const resp = await fetch('/api/string-connections');
    const dados = await resp.json();
    if (!dados.ok) return;
    stringConnectionsDisponiveis = dados.conexoes;
    const select = document.getElementById('alerta-conexao-select');
    select.innerHTML = '<option value="">Selecione uma String Connection...</option>' +
      dados.conexoes.map(c => `<option value="${c.id}">${c.cliente} · ${c.produto}</option>`).join('');
  } catch (e) {
    // sem conexao pra rede/erro qualquer - falha silenciosa aqui esta ok,
    // o usuario so nao vai ter opcoes pra escolher ate a pagina recarregar
  }
}

function aplicarConexaoSelecionada() {
  const select = document.getElementById('alerta-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada');
  const encontrada = stringConnectionsDisponiveis.find(c => c.id === select.value);
  if (encontrada) {
    document.getElementById('alerta-conexao').value = encontrada.conexao;
    avisoNaoCadastrada.style.display = 'none';
  } else {
    document.getElementById('alerta-conexao').value = '';
  }
}

carregarAlertasBanco();
carregarStringConnectionsParaSelect();
</script>

</body>
</html>
"""


def _montar_manutencao_alertas_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_ALERTAS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção de Alertas em Banco"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__EMAIL_MONITORAMENTO__", EMAIL_MONITORAMENTO_PADRAO)
    )


_MANUTENCAO_REJEICOES_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção Rejeições em Banco</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: 900px; margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: 900px; }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .filtros-alertas { display: flex; gap: 10px; margin: 0 auto 14px auto; max-width: 900px; flex-wrap: wrap; }
  .filtros-alertas input[type="text"] { flex: 1; min-width: 180px; padding: 8px 12px; border-radius: 8px;
                    border: 1px solid var(--border); background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; }
  .filtros-alertas input[type="text"]:focus { outline: none; border-color: var(--teal); }
  .acoes-linha { display: flex; gap: 6px; }
  .dica-campo.dica-travado { color: var(--run); }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; padding: 24px; }
  .modal-fundo.aberto { display: flex; }
  .modal-largo { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 30px 32px; width: 100%; max-width: 560px; max-height: 88vh; overflow-y: auto;
           box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal-largo h3 { margin: 0 0 18px 0; font-size: 16px; color: var(--teal); }
  .modal-largo label { display: block; font-size: 11px; color: var(--fg-dim); margin: 14px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal-largo input, .modal-largo select, .modal-largo textarea {
                 width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal-largo textarea { font-family: Consolas, monospace; font-size: 12.5px; resize: vertical; min-height: 90px; }
  .modal-largo input:focus, .modal-largo select:focus, .modal-largo textarea:focus {
                 outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .linha-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
  .dica-campo { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.4; }
  .acoes-modal { display: flex; gap: 8px; margin-top: 22px; }
  .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }

  .bloco-sucesso { text-align: center; }
  .bloco-sucesso .icone-ok { width: 52px; height: 52px; border-radius: 50%; background: rgba(78,201,176,.15);
                              display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; }
  .bloco-sucesso .icone-ok svg { width: 26px; height: 26px; stroke: var(--ok); }
  .bloco-sucesso h4 { margin: 0 0 8px 0; font-size: 15px; }
  .bloco-sucesso p { color: var(--fg-dim); font-size: 12.5px; line-height: 1.6; text-align: left; }
  .bloco-gatilho { background: rgba(0,0,0,.25); border: 1px solid var(--border); border-radius: 10px;
                   padding: 14px 16px; text-align: left; font-family: Consolas, monospace; font-size: 12px;
                   margin: 14px 0; line-height: 1.8; }
  .bloco-gatilho b { color: var(--teal); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Rejeições cadastradas (CONFIGURACOES_REJEICAO)</h3>
      <button class="btn-accent" onclick="abrirModalNovaRejeicao()">+ Nova rejeição</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro-banco" style="display:none; max-width:900px; margin:0 auto 16px auto;"></div>

    <div class="filtros-alertas">
      <input type="text" id="filtro-cliente" placeholder="Filtrar por cliente..." oninput="aplicarFiltrosRejeicoes()">
    </div>

    <div class="painel">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Cliente</th><th>Tipo</th><th>Agendamento</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela-rejeicoes">
          <tr><td colspan="5" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-nova-rejeicao">
    <div class="modal-largo">
      <h3 id="titulo-modal-rejeicao">Nova rejeição em CONFIGURACOES_REJEICAO</h3>

      <div id="form-nova-rejeicao">
        <div class="linha-dupla">
          <div>
            <label>Cliente</label>
            <input type="text" id="rejeicao-cliente" placeholder="Nome do cliente">
          </div>
          <div>
            <label>Tipo de banco</label>
            <select id="rejeicao-tipo-banco">
              <option value="SQL">SQL Server</option>
              <option value="ORACLE">Oracle</option>
            </select>
          </div>
        </div>

        <label>Tipo de agendamento</label>
        <input type="text" id="rejeicao-tipo-agendamento" placeholder="Ex.: DIARIO">
        <div class="dica-campo">Campo obrigatório.</div>

        <label>Conexão</label>
        <select id="rejeicao-conexao-select" onchange="aplicarConexaoSelecionadaRejeicao()">
          <option value="">Selecione uma String Connection...</option>
        </select>
        <input type="hidden" id="rejeicao-conexao">
        <div class="dica-campo" id="dica-conexao-nao-cadastrada-rejeicao" style="display:none; color:var(--erro)">
          Esta rejeição usa uma conexão que não está cadastrada em String Connections - selecione uma da lista pra substituir.
        </div>

        <label>Script</label>
        <textarea id="rejeicao-script" placeholder="SELECT codigo_rejeicao, COUNT(*) FROM ..."></textarea>
        <div class="dica-campo">SQL puro - a conversão pra base64 é feita automaticamente. Precisa sempre retornar o código da rejeição E a quantidade, pra rejeição abrir corretamente.</div>

        <div class="erro-modal" id="erro-nova-rejeicao"></div>
        <div class="acoes-modal">
          <button class="btn-accent" id="botao-salvar-rejeicao" onclick="salvarRejeicaoBanco()" style="flex:1">Criar rejeição</button>
          <button onclick="fecharModalNovaRejeicao()" style="flex:1">Cancelar</button>
        </div>
      </div>

      <div id="sucesso-nova-rejeicao" style="display:none">
        <div class="bloco-sucesso">
          <div class="icone-ok">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
          </div>
          <h4>Rejeição criada com sucesso</h4>
          <p>
            Falta um passo manual: solicitar a criação do gatilho no Movidesk
            (peça pra algum N2 ou N3). Use estes dados na
            abertura do serviço:
          </p>
          <div class="bloco-gatilho" id="texto-gatilho-rejeicao"></div>
          <div class="acoes-modal">
            <button class="btn-accent" onclick="copiarTextoGatilhoRejeicao()" style="flex:1">Copiar texto</button>
            <button onclick="fecharModalNovaRejeicao()" style="flex:1">Fechar</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="modal-fundo" id="modal-excluir-rejeicao">
    <div class="modal-largo" style="max-width:420px">
      <h3>Excluir rejeição</h3>
      <p style="color:var(--fg-dim); font-size:13px; line-height:1.6">
        Tem certeza que quer excluir a rejeição <b id="nome-rejeicao-excluir"></b>?
        Essa ação não pode ser desfeita.
      </p>
      <div class="erro-modal" id="erro-excluir-rejeicao"></div>
      <div class="acoes-modal">
        <button class="btn-mini btn-perigo" onclick="confirmarExclusaoRejeicao()" style="flex:1">Excluir</button>
        <button onclick="fecharModalExcluirRejeicao()" style="flex:1">Cancelar</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  __FOOTER__

<script>
let gatilhoAtualRejeicao = null;
let idEmEdicaoRejeicao = null;
let idParaExcluirRejeicao = null;
let todasAsRejeicoes = [];

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

async function carregarRejeicoesBanco() {
  const avisoEl = document.getElementById('aviso-erro-banco');
  try {
    const resp = await fetch('/api/manutencao-rejeicoes');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível carregar as rejeições do banco de monitoramento: ' + (dados.erro || 'erro desconhecido.');
      document.getElementById('corpo-tabela-rejeicoes').innerHTML =
        '<tr><td colspan="5" style="color:var(--fg-dim)">Sem dados no momento.</td></tr>';
      return;
    }
    avisoEl.style.display = 'none';
    todasAsRejeicoes = dados.registros;
    aplicarFiltrosRejeicoes();
  } catch (e) {
    avisoEl.style.display = 'block';
    avisoEl.innerText = '⚠ Erro ao carregar: ' + e;
  }
}

function aplicarFiltrosRejeicoes() {
  const filtroCliente = document.getElementById('filtro-cliente').value.trim().toLowerCase();
  let filtrados = todasAsRejeicoes;
  if (filtroCliente) {
    filtrados = filtrados.filter(r => (r.cliente || '').toLowerCase().includes(filtroCliente));
  }

  const corpo = document.getElementById('corpo-tabela-rejeicoes');
  if (todasAsRejeicoes.length === 0) {
    corpo.innerHTML = '<tr><td colspan="5" style="color:var(--fg-dim)">Nenhuma rejeição cadastrada ainda.</td></tr>';
    return;
  }
  if (filtrados.length === 0) {
    corpo.innerHTML = '<tr><td colspan="5" style="color:var(--fg-dim)">Nenhuma rejeição bate com o filtro.</td></tr>';
    return;
  }
  corpo.innerHTML = filtrados.map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${r.cliente || ''}</td>
      <td>${r.tipo_banco || ''}</td>
      <td>${r.tipo_agendamento || ''}</td>
      <td>
        <div class="acoes-linha">
          <button class="btn-mini" onclick="abrirModalEditarRejeicao(${r.id})">Editar</button>
          <button class="btn-mini btn-perigo" onclick="abrirModalExcluirRejeicao(${r.id}, '${(r.cliente || '').replace(/'/g, "\\\\'")}')">Excluir</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function abrirModalNovaRejeicao() {
  idEmEdicaoRejeicao = null;
  document.getElementById('titulo-modal-rejeicao').innerText = 'Nova rejeição em CONFIGURACOES_REJEICAO';
  document.getElementById('botao-salvar-rejeicao').innerText = 'Criar rejeição';
  document.getElementById('form-nova-rejeicao').style.display = 'block';
  document.getElementById('sucesso-nova-rejeicao').style.display = 'none';
  document.getElementById('erro-nova-rejeicao').innerText = '';
  document.getElementById('rejeicao-cliente').value = '';
  document.getElementById('rejeicao-tipo-banco').value = 'SQL';
  document.getElementById('rejeicao-tipo-agendamento').value = '';
  document.getElementById('rejeicao-conexao').value = '';
  document.getElementById('rejeicao-conexao-select').value = '';
  document.getElementById('dica-conexao-nao-cadastrada-rejeicao').style.display = 'none';
  document.getElementById('rejeicao-script').value = '';
  document.getElementById('modal-nova-rejeicao').classList.add('aberto');
}

async function abrirModalEditarRejeicao(id) {
  const resp = await fetch('/api/manutencao-rejeicoes/' + id);
  const dados = await resp.json();
  if (!dados.ok) {
    mostrarToast(dados.erro || 'Não foi possível carregar essa rejeição.');
    return;
  }
  const r = dados.registro;
  idEmEdicaoRejeicao = id;
  document.getElementById('titulo-modal-rejeicao').innerText = 'Editar rejeição #' + id + ' (CONFIGURACOES_REJEICAO)';
  document.getElementById('botao-salvar-rejeicao').innerText = 'Salvar alterações';
  document.getElementById('form-nova-rejeicao').style.display = 'block';
  document.getElementById('sucesso-nova-rejeicao').style.display = 'none';
  document.getElementById('erro-nova-rejeicao').innerText = '';
  document.getElementById('rejeicao-cliente').value = r.cliente || '';
  document.getElementById('rejeicao-tipo-banco').value = r.tipo_banco || 'SQL';
  document.getElementById('rejeicao-tipo-agendamento').value = r.tipo_agendamento || '';
  document.getElementById('rejeicao-conexao').value = r.conexao || '';
  document.getElementById('rejeicao-script').value = r.script || '';

  const selectConexao = document.getElementById('rejeicao-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-rejeicao');
  const encontrada = stringConnectionsDisponiveis.find(c => c.conexao === r.conexao);
  if (encontrada) {
    selectConexao.value = encontrada.id;
    avisoNaoCadastrada.style.display = 'none';
  } else if (r.conexao) {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'block';
  } else {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'none';
  }

  document.getElementById('modal-nova-rejeicao').classList.add('aberto');
}

function fecharModalNovaRejeicao() {
  document.getElementById('modal-nova-rejeicao').classList.remove('aberto');
  carregarRejeicoesBanco();
}

function _corpoFormularioRejeicao() {
  return 'cliente=' + encodeURIComponent(document.getElementById('rejeicao-cliente').value) +
    '&tipo_banco=' + encodeURIComponent(document.getElementById('rejeicao-tipo-banco').value) +
    '&tipo_agendamento=' + encodeURIComponent(document.getElementById('rejeicao-tipo-agendamento').value) +
    '&conexao=' + encodeURIComponent(document.getElementById('rejeicao-conexao').value) +
    '&script=' + encodeURIComponent(document.getElementById('rejeicao-script').value);
}

async function salvarRejeicaoBanco() {
  const erroEl = document.getElementById('erro-nova-rejeicao');

  if (!document.getElementById('rejeicao-conexao').value) {
    erroEl.innerText = 'Selecione uma String Connection pra essa rejeição.';
    return;
  }

  if (idEmEdicaoRejeicao === null) {
    const resp = await fetch('/api/manutencao-rejeicoes/criar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: _corpoFormularioRejeicao(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível criar a rejeição.';
      return;
    }
    gatilhoAtualRejeicao = dados.gatilho;
    document.getElementById('texto-gatilho-rejeicao').innerHTML =
      '<b>Nome:</b> ' + gatilhoAtualRejeicao.nome + '<br>' +
      '<b>Solicitante:</b> ' + gatilhoAtualRejeicao.solicitante + '<br>' +
      '<b>Serviço:</b> ' + gatilhoAtualRejeicao.servico;
    document.getElementById('form-nova-rejeicao').style.display = 'none';
    document.getElementById('sucesso-nova-rejeicao').style.display = 'block';
  } else {
    const resp = await fetch('/api/manutencao-rejeicoes/atualizar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(idEmEdicaoRejeicao) + '&' + _corpoFormularioRejeicao(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível salvar as alterações.';
      return;
    }
    mostrarToast('Rejeição #' + idEmEdicaoRejeicao + ' atualizada.');
    fecharModalNovaRejeicao();
  }
}

function abrirModalExcluirRejeicao(id, cliente) {
  idParaExcluirRejeicao = id;
  document.getElementById('nome-rejeicao-excluir').innerText = '#' + id + ' (' + cliente + ')';
  document.getElementById('erro-excluir-rejeicao').innerText = '';
  document.getElementById('modal-excluir-rejeicao').classList.add('aberto');
}

function fecharModalExcluirRejeicao() {
  document.getElementById('modal-excluir-rejeicao').classList.remove('aberto');
}

async function confirmarExclusaoRejeicao() {
  const resp = await fetch('/api/manutencao-rejeicoes/excluir', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(idParaExcluirRejeicao),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('erro-excluir-rejeicao').innerText = dados.erro || 'Não foi possível excluir.';
    return;
  }
  mostrarToast('Rejeição #' + idParaExcluirRejeicao + ' excluída.');
  fecharModalExcluirRejeicao();
  carregarRejeicoesBanco();
}

function copiarTextoGatilhoRejeicao() {
  if (!gatilhoAtualRejeicao) return;
  const texto = 'Nome: ' + gatilhoAtualRejeicao.nome + '\\nSolicitante: ' + gatilhoAtualRejeicao.solicitante +
    '\\nServiço: ' + gatilhoAtualRejeicao.servico;
  copiarTextoParaAreaDeTransferencia(texto);
}

// navigator.clipboard só funciona em "contexto seguro" (HTTPS ou
// localhost) - como o painel roda em HTTP puro na rede interna, essa API
// fica indisponível no navegador. Mesmo fallback já usado em outras
// telas do painel.
function copiarTextoParaAreaDeTransferencia(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(texto)
      .then(() => mostrarToast('Texto copiado.'))
      .catch(() => copiarViaTextareaFallback(texto));
  } else {
    copiarViaTextareaFallback(texto);
  }
}

function copiarViaTextareaFallback(texto) {
  const areaTemp = document.createElement('textarea');
  areaTemp.value = texto;
  areaTemp.style.position = 'fixed';
  areaTemp.style.left = '-9999px';
  areaTemp.style.top = '0';
  document.body.appendChild(areaTemp);
  areaTemp.focus();
  areaTemp.select();
  try {
    const sucesso = document.execCommand('copy');
    mostrarToast(sucesso ? 'Texto copiado.' : 'Não foi possível copiar automaticamente - selecione e copie manualmente.');
  } catch (e) {
    mostrarToast('Não foi possível copiar automaticamente - selecione e copie manualmente.');
  }
  document.body.removeChild(areaTemp);
}

// --- String Connections no formulário (preenchimento rápido) ---
let stringConnectionsDisponiveis = [];

async function carregarStringConnectionsParaSelect() {
  try {
    const resp = await fetch('/api/string-connections');
    const dados = await resp.json();
    if (!dados.ok) return;
    stringConnectionsDisponiveis = dados.conexoes;
    const select = document.getElementById('rejeicao-conexao-select');
    select.innerHTML = '<option value="">Selecione uma String Connection...</option>' +
      dados.conexoes.map(c => `<option value="${c.id}">${c.cliente} · ${c.produto}</option>`).join('');
  } catch (e) {
    // sem conexao pra rede/erro qualquer - falha silenciosa aqui esta ok
  }
}

function aplicarConexaoSelecionadaRejeicao() {
  const select = document.getElementById('rejeicao-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-rejeicao');
  const encontrada = stringConnectionsDisponiveis.find(c => c.id === select.value);
  if (encontrada) {
    document.getElementById('rejeicao-conexao').value = encontrada.conexao;
    avisoNaoCadastrada.style.display = 'none';
  } else {
    document.getElementById('rejeicao-conexao').value = '';
  }
}

carregarRejeicoesBanco();
carregarStringConnectionsParaSelect();
</script>

</body>
</html>
"""


def _montar_manutencao_rejeicoes_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_REJEICOES_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção Rejeições em Banco"))
        .replace("__FOOTER__", _montar_footer())
    )


_MANUTENCAO_RELATORIOS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção de Relatórios em Banco</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: 980px; margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 12.5px;
           white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
  th { color: var(--teal); background: rgba(255,255,255,.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: 980px; }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .filtros-alertas { display: flex; gap: 10px; margin: 0 auto 14px auto; max-width: 980px; flex-wrap: wrap; }
  .filtros-alertas input[type="text"], .filtros-alertas select { flex: 1; min-width: 160px; padding: 8px 12px;
                    border-radius: 8px; border: 1px solid var(--border); background: rgba(0,0,0,.28);
                    color: var(--fg); font-size: 13px; }
  .filtros-alertas input[type="text"]:focus, .filtros-alertas select:focus { outline: none; border-color: var(--teal); }
  .acoes-linha { display: flex; gap: 6px; }
  .badge-status { display: inline-block; padding: 2px 9px; border-radius: 6px; font-size: 11px; font-weight: 700; }
  .badge-ativo { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-inativo { background: rgba(255,255,255,.08); color: var(--fg-dim); }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; padding: 24px; }
  .modal-fundo.aberto { display: flex; }
  .modal-largo { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 30px 32px; width: 100%; max-width: 620px; max-height: 88vh; overflow-y: auto;
           box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal-largo h3 { margin: 0 0 18px 0; font-size: 16px; color: var(--teal); }
  .modal-largo label { display: block; font-size: 11px; color: var(--fg-dim); margin: 14px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal-largo input, .modal-largo select, .modal-largo textarea {
                 width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(0,0,0,.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal-largo textarea { font-family: Consolas, monospace; font-size: 12.5px; resize: vertical; min-height: 90px; }
  .modal-largo input:focus, .modal-largo select:focus, .modal-largo textarea:focus {
                 outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .linha-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
  .linha-tripla { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0 14px; }
  .dica-campo { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.4; }
  .acoes-modal { display: flex; gap: 8px; margin-top: 22px; }
  .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .campo-checkbox { display: flex; align-items: center; gap: 9px; margin-top: 16px; }
  .campo-checkbox input[type="checkbox"] { width: auto; flex: 0 0 auto; padding: 0; }
  .campo-checkbox label { display: block; margin: 0; text-transform: none; letter-spacing: normal;
                           font-size: 13px; color: var(--fg); flex: 1; text-align: left; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Relatórios cadastrados (CONFIGURACOES_RELATORIO)</h3>
      <button class="btn-accent" onclick="abrirModalNovoRelatorio()">+ Novo relatório</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro-banco" style="display:none; max-width:980px; margin:0 auto 16px auto;"></div>

    <div class="filtros-alertas">
      <input type="text" id="filtro-cliente-rel" placeholder="Filtrar por cliente..." oninput="aplicarFiltrosRelatorios()">
      <select id="filtro-status-rel" onchange="aplicarFiltrosRelatorios()">
        <option value="">Todos os status</option>
        <option value="1">Ativos</option>
        <option value="0">Inativos</option>
      </select>
    </div>

    <div class="painel">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Cliente</th><th>Título e-mail</th><th>Tipo</th><th>Modelo</th>
            <th>Reincidência</th><th>Hora</th><th>Status</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela-relatorios">
          <tr><td colspan="9" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-novo-relatorio">
    <div class="modal-largo">
      <h3 id="titulo-modal-relatorio">Novo relatório em CONFIGURACOES_RELATORIO</h3>

      <div class="linha-dupla">
        <div>
          <label>Cliente</label>
          <input type="text" id="relatorio-cliente" placeholder="Nome do cliente">
        </div>
        <div>
          <label>Tipo de banco</label>
          <select id="relatorio-tipo-banco">
            <option value="SQL">SQL Server</option>
            <option value="ORACLE">Oracle</option>
          </select>
        </div>
      </div>

      <label>Conexão</label>
      <select id="relatorio-conexao-select" onchange="aplicarConexaoSelecionadaRelatorio()">
        <option value="">Selecione uma String Connection...</option>
      </select>
      <input type="hidden" id="relatorio-conexao">
      <div class="dica-campo" id="dica-conexao-nao-cadastrada-relatorio" style="display:none; color:var(--erro)">
        Este relatório usa uma conexão que não está cadastrada em String Connections - selecione uma da lista pra substituir.
      </div>

      <label>Script</label>
      <textarea id="relatorio-script" placeholder="SELECT ... (todos os dados desejados no relatório)"></textarea>
      <div class="dica-campo">SQL puro - a conversão pra base64 é feita automaticamente.</div>

      <label>E-mails</label>
      <input type="text" id="relatorio-emails" placeholder="email1@cliente.com, email2@cliente.com">
      <div class="dica-campo">Separados por vírgula.</div>

      <div class="linha-dupla">
        <div>
          <label>Título do e-mail</label>
          <input type="text" id="relatorio-titulo-email">
        </div>
        <div>
          <label>Nome do arquivo</label>
          <input type="text" id="relatorio-nome-arquivo">
        </div>
      </div>

      <label>Corpo do e-mail</label>
      <textarea id="relatorio-corpo-email" style="font-family:inherit; min-height:70px"></textarea>

      <div class="linha-tripla">
        <div>
          <label>Modelo do arquivo</label>
          <select id="relatorio-modelo-arquivo">
            <option value="P">Planilha</option>
            <option value="C">CSV</option>
            <option value="T">TXT</option>
          </select>
        </div>
        <div>
          <label>Reincidência</label>
          <select id="relatorio-reincidencia" onchange="atualizarCamposReincidencia()">
            <option value="DIARIO">Diário</option>
            <option value="SEMANAL">Semanal</option>
            <option value="MENSAL">Mensal</option>
          </select>
        </div>
        <div>
          <label>Hora de execução</label>
          <input type="time" id="relatorio-hora-execucao">
        </div>
      </div>

      <div id="campo-dia-semana" style="display:none">
        <label>Dia da semana</label>
        <select id="relatorio-dia-semana">
          <option value="Monday">Segunda-feira</option>
          <option value="Tuesday">Terça-feira</option>
          <option value="Wednesday">Quarta-feira</option>
          <option value="Thursday">Quinta-feira</option>
          <option value="Friday">Sexta-feira</option>
          <option value="Saturday">Sábado</option>
          <option value="Sunday">Domingo</option>
        </select>
        <div class="dica-campo">Se não escolher, assume Terça-feira.</div>
      </div>

      <div id="campo-dia-mensal" style="display:none">
        <label>Dia do mês</label>
        <input type="number" id="relatorio-dia-mensal" min="1" max="31" placeholder="1 a 31">
      </div>

      <label>Agrupador do relatório <span style="text-transform:none; color:var(--fg-dim)">(opcional)</span></label>
      <input type="text" id="relatorio-agrupador" placeholder="Só preencher se precisar juntar vários relatórios num e-mail só">
      <div class="dica-campo">Nome do agrupador cadastrado em AGRUPADOR_RELATORIO - deixe em branco na maioria dos casos.</div>

      <div class="campo-checkbox">
        <input type="checkbox" id="relatorio-disponibilidade" checked>
        <label for="relatorio-disponibilidade">Ativar este relatório imediatamente</label>
      </div>

      <div class="erro-modal" id="erro-novo-relatorio"></div>
      <div class="acoes-modal">
        <button class="btn-accent" id="botao-salvar-relatorio" onclick="salvarRelatorioBanco()" style="flex:1">Criar relatório</button>
        <button onclick="fecharModalNovoRelatorio()" style="flex:1">Cancelar</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  __FOOTER__

<script>
let idEmEdicaoRelatorio = null;
let todosOsRelatorios = [];
let stringConnectionsDisponiveis = [];

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

function atualizarCamposReincidencia() {
  const valor = document.getElementById('relatorio-reincidencia').value;
  document.getElementById('campo-dia-semana').style.display = valor === 'SEMANAL' ? 'block' : 'none';
  document.getElementById('campo-dia-mensal').style.display = valor === 'MENSAL' ? 'block' : 'none';
}

async function carregarRelatoriosBanco() {
  const avisoEl = document.getElementById('aviso-erro-banco');
  try {
    const resp = await fetch('/api/manutencao-relatorios');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível carregar os relatórios do banco de monitoramento: ' + (dados.erro || 'erro desconhecido.');
      document.getElementById('corpo-tabela-relatorios').innerHTML =
        '<tr><td colspan="9" style="color:var(--fg-dim)">Sem dados no momento.</td></tr>';
      return;
    }
    avisoEl.style.display = 'none';
    todosOsRelatorios = dados.registros;
    aplicarFiltrosRelatorios();
  } catch (e) {
    avisoEl.style.display = 'block';
    avisoEl.innerText = '⚠ Erro ao carregar: ' + e;
  }
}

function aplicarFiltrosRelatorios() {
  const filtroCliente = document.getElementById('filtro-cliente-rel').value.trim().toLowerCase();
  const filtroStatus = document.getElementById('filtro-status-rel').value;
  let filtrados = todosOsRelatorios;
  if (filtroCliente) {
    filtrados = filtrados.filter(r => (r.cliente || '').toLowerCase().includes(filtroCliente));
  }
  if (filtroStatus) {
    filtrados = filtrados.filter(r => String(Number(r.disponibilidade)) === filtroStatus);
  }

  const corpo = document.getElementById('corpo-tabela-relatorios');
  if (todosOsRelatorios.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum relatório cadastrado ainda.</td></tr>';
    return;
  }
  if (filtrados.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum relatório bate com o filtro.</td></tr>';
    return;
  }
  corpo.innerHTML = filtrados.map(r => {
    const ativo = Number(r.disponibilidade) === 1;
    const badge = ativo ? '<span class="badge-status badge-ativo">Ativo</span>' : '<span class="badge-status badge-inativo">Inativo</span>';
    return `
    <tr>
      <td>${r.id}</td>
      <td>${r.cliente || ''}</td>
      <td>${r.titulo_email || ''}</td>
      <td>${r.tipo_banco || ''}</td>
      <td>${r.modelo_arquivo || ''}</td>
      <td>${r.reincidencia || ''}</td>
      <td>${r.hora_execucao || ''}</td>
      <td>${badge}</td>
      <td>
        <div class="acoes-linha">
          <button class="btn-mini" onclick="abrirModalEditarRelatorio(${r.id})">Editar</button>
          <button class="btn-mini" onclick="alternarDisponibilidadeRelatorio(${r.id}, ${!ativo})">${ativo ? 'Desativar' : 'Ativar'}</button>
        </div>
      </td>
    </tr>
  `;
  }).join('');
}

function abrirModalNovoRelatorio() {
  idEmEdicaoRelatorio = null;
  document.getElementById('titulo-modal-relatorio').innerText = 'Novo relatório em CONFIGURACOES_RELATORIO';
  document.getElementById('botao-salvar-relatorio').innerText = 'Criar relatório';
  document.getElementById('erro-novo-relatorio').innerText = '';
  document.getElementById('relatorio-cliente').value = '';
  document.getElementById('relatorio-tipo-banco').value = 'SQL';
  document.getElementById('relatorio-conexao').value = '';
  document.getElementById('relatorio-conexao-select').value = '';
  document.getElementById('dica-conexao-nao-cadastrada-relatorio').style.display = 'none';
  document.getElementById('relatorio-script').value = '';
  document.getElementById('relatorio-emails').value = '';
  document.getElementById('relatorio-titulo-email').value = '';
  document.getElementById('relatorio-nome-arquivo').value = '';
  document.getElementById('relatorio-corpo-email').value = '';
  document.getElementById('relatorio-modelo-arquivo').value = 'P';
  document.getElementById('relatorio-reincidencia').value = 'DIARIO';
  document.getElementById('relatorio-dia-semana').value = 'Tuesday';
  document.getElementById('relatorio-dia-mensal').value = '';
  document.getElementById('relatorio-hora-execucao').value = '08:00';
  document.getElementById('relatorio-agrupador').value = '';
  document.getElementById('relatorio-disponibilidade').checked = true;
  atualizarCamposReincidencia();
  document.getElementById('modal-novo-relatorio').classList.add('aberto');
}

async function abrirModalEditarRelatorio(id) {
  const resp = await fetch('/api/manutencao-relatorios/' + id);
  const dados = await resp.json();
  if (!dados.ok) {
    mostrarToast(dados.erro || 'Não foi possível carregar esse relatório.');
    return;
  }
  const r = dados.registro;
  idEmEdicaoRelatorio = id;
  document.getElementById('titulo-modal-relatorio').innerText = 'Editar relatório #' + id + ' (CONFIGURACOES_RELATORIO)';
  document.getElementById('botao-salvar-relatorio').innerText = 'Salvar alterações';
  document.getElementById('erro-novo-relatorio').innerText = '';
  document.getElementById('relatorio-cliente').value = r.cliente || '';
  document.getElementById('relatorio-tipo-banco').value = r.tipo_banco || 'SQL';
  document.getElementById('relatorio-conexao').value = r.conexao || '';
  document.getElementById('relatorio-script').value = r.script || '';
  document.getElementById('relatorio-emails').value = r.emails || '';
  document.getElementById('relatorio-titulo-email').value = r.titulo_email || '';
  document.getElementById('relatorio-nome-arquivo').value = r.nome_arquivo || '';
  document.getElementById('relatorio-corpo-email').value = r.corpo_email || '';
  document.getElementById('relatorio-modelo-arquivo').value = r.modelo_arquivo || 'P';
  document.getElementById('relatorio-reincidencia').value = r.reincidencia || 'DIARIO';
  document.getElementById('relatorio-dia-semana').value = r.dia_semana || 'Tuesday';
  document.getElementById('relatorio-dia-mensal').value = r.dia_mensal || '';
  document.getElementById('relatorio-hora-execucao').value = r.hora_execucao || '08:00';
  document.getElementById('relatorio-agrupador').value = r.agrupador_relatorio || '';
  document.getElementById('relatorio-disponibilidade').checked = Number(r.disponibilidade) === 1;
  atualizarCamposReincidencia();

  const selectConexao = document.getElementById('relatorio-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-relatorio');
  const encontrada = stringConnectionsDisponiveis.find(c => c.conexao === r.conexao);
  if (encontrada) {
    selectConexao.value = encontrada.id;
    avisoNaoCadastrada.style.display = 'none';
  } else if (r.conexao) {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'block';
  } else {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'none';
  }

  document.getElementById('modal-novo-relatorio').classList.add('aberto');
}

function fecharModalNovoRelatorio() {
  document.getElementById('modal-novo-relatorio').classList.remove('aberto');
  carregarRelatoriosBanco();
}

function _corpoFormularioRelatorio() {
  return 'cliente=' + encodeURIComponent(document.getElementById('relatorio-cliente').value) +
    '&tipo_banco=' + encodeURIComponent(document.getElementById('relatorio-tipo-banco').value) +
    '&conexao=' + encodeURIComponent(document.getElementById('relatorio-conexao').value) +
    '&script=' + encodeURIComponent(document.getElementById('relatorio-script').value) +
    '&emails=' + encodeURIComponent(document.getElementById('relatorio-emails').value) +
    '&titulo_email=' + encodeURIComponent(document.getElementById('relatorio-titulo-email').value) +
    '&nome_arquivo=' + encodeURIComponent(document.getElementById('relatorio-nome-arquivo').value) +
    '&corpo_email=' + encodeURIComponent(document.getElementById('relatorio-corpo-email').value) +
    '&modelo_arquivo=' + encodeURIComponent(document.getElementById('relatorio-modelo-arquivo').value) +
    '&reincidencia=' + encodeURIComponent(document.getElementById('relatorio-reincidencia').value) +
    '&dia_semana=' + encodeURIComponent(document.getElementById('relatorio-dia-semana').value) +
    '&dia_mensal=' + encodeURIComponent(document.getElementById('relatorio-dia-mensal').value) +
    '&hora_execucao=' + encodeURIComponent(document.getElementById('relatorio-hora-execucao').value) +
    '&agrupador_relatorio=' + encodeURIComponent(document.getElementById('relatorio-agrupador').value) +
    '&disponibilidade=' + (document.getElementById('relatorio-disponibilidade').checked ? 'true' : 'false');
}

async function salvarRelatorioBanco() {
  const erroEl = document.getElementById('erro-novo-relatorio');

  if (!document.getElementById('relatorio-conexao').value) {
    erroEl.innerText = 'Selecione uma String Connection pra esse relatório.';
    return;
  }

  const url = idEmEdicaoRelatorio === null ? '/api/manutencao-relatorios/criar' : '/api/manutencao-relatorios/atualizar';
  const corpo = idEmEdicaoRelatorio === null
    ? _corpoFormularioRelatorio()
    : 'id=' + encodeURIComponent(idEmEdicaoRelatorio) + '&' + _corpoFormularioRelatorio();

  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: corpo,
  });
  const dados = await resp.json();
  if (!dados.ok) {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
    return;
  }
  mostrarToast(idEmEdicaoRelatorio === null ? 'Relatório criado.' : 'Relatório #' + idEmEdicaoRelatorio + ' atualizado.');
  fecharModalNovoRelatorio();
}

async function alternarDisponibilidadeRelatorio(id, ativar) {
  const resp = await fetch('/api/manutencao-relatorios/disponibilidade', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(id) + '&ativo=' + (ativar ? 'true' : 'false'),
  });
  const dados = await resp.json();
  if (dados.ok) {
    mostrarToast('Relatório #' + id + (ativar ? ' ativado.' : ' desativado.'));
    carregarRelatoriosBanco();
  } else {
    mostrarToast(dados.erro || 'Não foi possível alterar.');
  }
}

async function carregarStringConnectionsParaSelect() {
  try {
    const resp = await fetch('/api/string-connections');
    const dados = await resp.json();
    if (!dados.ok) return;
    stringConnectionsDisponiveis = dados.conexoes;
    const select = document.getElementById('relatorio-conexao-select');
    select.innerHTML = '<option value="">Selecione uma String Connection...</option>' +
      dados.conexoes.map(c => `<option value="${c.id}">${c.cliente} · ${c.produto}</option>`).join('');
  } catch (e) {
    // sem conexao pra rede/erro qualquer - falha silenciosa aqui esta ok
  }
}

function aplicarConexaoSelecionadaRelatorio() {
  const select = document.getElementById('relatorio-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-relatorio');
  const encontrada = stringConnectionsDisponiveis.find(c => c.id === select.value);
  if (encontrada) {
    document.getElementById('relatorio-conexao').value = encontrada.conexao;
    avisoNaoCadastrada.style.display = 'none';
  } else {
    document.getElementById('relatorio-conexao').value = '';
  }
}

carregarRelatoriosBanco();
carregarStringConnectionsParaSelect();
</script>

</body>
</html>
"""


def _montar_manutencao_relatorios_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_RELATORIOS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção de Relatórios em Banco"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_dashboards_clientes_html(sessao: dict) -> str:
    return (
        _DASHBOARDS_CLIENTES_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Dashboards por Cliente"))
        .replace("__FOOTER__", _montar_footer())
    )


_DASHBOARDS_CLIENTES_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Dashboards por Cliente</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
__NAVBAR_CSS__
  .cabecalho-dc { max-width: 900px; margin: 0 auto 24px auto; }
  .cabecalho-dc h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-dc .sub { color: var(--fg-dim); font-size: 12.5px; }
  .aviso-beta-dc { max-width: 900px; margin: 0 auto 24px auto; background: rgba(255,143,163,.08);
                   border: 1px solid rgba(255,143,163,.3); border-radius: 10px; padding: 12px 16px;
                   font-size: 12.5px; color: var(--fg); line-height: 1.6; }
  .aviso-beta-dc b { color: #f5a3d0; }

  .painel-dc { max-width: 900px; margin: 0 auto 20px auto; background: var(--bg-panel);
               backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 24px 26px; }
  .painel-dc h3 { margin: 0 0 16px 0; font-size: 13px; color: var(--teal); text-transform: uppercase; letter-spacing: .04em; }

  .grade-selecao-dc { display: flex; gap: 12px; flex-wrap: wrap; }
  .pill-dc { padding: 12px 22px; border-radius: 10px; border: 1px solid var(--border); background: rgba(255,255,255,.03);
             cursor: pointer; font-size: 13px; font-weight: 600; color: var(--fg-dim); transition: all .15s; }
  .pill-dc:hover { border-color: var(--border-forte); color: var(--fg); }
  .pill-dc.ativa { border-color: var(--teal); background: rgba(45,184,207,.1); color: var(--teal); }

  .trilha-dc { display: flex; align-items: center; gap: 8px; max-width: 900px; margin: 0 auto 20px auto;
               font-size: 12.5px; color: var(--fg-dim); }
  .trilha-dc .atual { color: var(--teal); font-weight: 700; }

  .placeholder-dc { text-align: center; padding: 50px 20px; color: var(--fg-dim); }
  .placeholder-dc .icone-placeholder-dc { font-size: 40px; margin-bottom: 14px; }
  .placeholder-dc .titulo-placeholder-dc { font-size: 15px; color: var(--fg); font-weight: 700; margin-bottom: 6px; }

  /* Dashboard Sanepar > NFAg - único já implementado de verdade */
  .cabecalho-nfag-dc { display: flex; align-items: center; justify-content: space-between;
      background: #1E2A38; border-radius: 12px; padding: 14px 24px; margin-bottom: 18px; }
  .cabecalho-nfag-dc .logo-nfag-dc { height: 34px; width: auto; }
  .cabecalho-nfag-dc .titulo-nfag-dc { color: #fff; font-size: 15px; font-weight: 700; letter-spacing: .02em; }
  .filtro-data-nfag-dc { display: flex; align-items: flex-end; gap: 14px; flex-wrap: wrap; }
  .filtro-data-nfag-dc div { display: flex; flex-direction: column; gap: 5px; }
  .filtro-data-nfag-dc label { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .04em; }
  .filtro-data-nfag-dc input[type="date"] { padding: 8px 10px; border-radius: 7px; border: 1px solid var(--border);
      background: rgba(0,0,0,.28); color: var(--fg); font-size: 12.5px; font-family: inherit; }
  .grade-kpis-nfag-dc { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin: 18px 0; }
  .kpi-nfag-dc { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px;
      padding: 18px; text-align: center; }
  .kpi-nfag-dc .valor-kpi-nfag-dc { font-size: 26px; font-weight: 800; color: var(--teal); }
  .kpi-nfag-dc .rotulo-kpi-nfag-dc { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
      letter-spacing: .04em; margin-top: 4px; }
  @media (max-width: 700px) { .grade-kpis-nfag-dc { grid-template-columns: repeat(2, 1fr); } }
  .container-grafico-nfag-dc { position: relative; height: 220px; width: 100%; }
  #painel-dashboard-nfag-dc { max-width: 1100px; margin: 0 auto; }
  #painel-dashboard-nfag-dc .painel-dc { max-width: none; margin: 0 0 18px 0; }
  .vazio-grafico-nfag-dc { display: flex; align-items: center; justify-content: center; height: 220px;
      color: var(--fg-dim); font-size: 12.5px; text-align: center; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-dc">
      <h1>Dashboards por Cliente</h1>
      <div class="sub">Indicadores específicos de cada cliente, por produto.</div>
    </div>

    <div class="aviso-beta-dc">
      <b>Beta:</b> por enquanto só a navegação entre cliente e produto está pronta - os dashboards de verdade
      (gráficos, indicadores) ainda vão ser construídos. Selecione um cliente e um produto pra ver o estado atual.
    </div>

    <div class="trilha-dc" id="trilha-dc">
      <span>Selecione um cliente</span>
    </div>

    <div class="painel-dc" id="painel-clientes-dc">
      <h3>Cliente</h3>
      <div class="grade-selecao-dc" id="grade-clientes-dc">
        <div class="vazio-mu">Carregando...</div>
      </div>
    </div>

    <div class="painel-dc" id="painel-produtos-dc" style="display:none">
      <h3>Produto</h3>
      <div class="grade-selecao-dc" id="grade-produtos-dc"></div>
    </div>

    <!-- Dashboard Sanepar > NFAg - transcrito do Power BI (08/09/2026),
         único já implementado de verdade por enquanto -->
    <div id="painel-dashboard-nfag-dc" style="display:none">
      <div class="cabecalho-nfag-dc">
        <div class="titulo-nfag-dc">Visualização por NFAg</div>
      </div>

      <div class="painel-dc filtro-data-nfag-dc">
        <div>
          <label>De</label>
          <input type="date" id="nfag-data-inicio">
        </div>
        <div>
          <label>Até</label>
          <input type="date" id="nfag-data-fim">
        </div>
        <button class="btn-accent" onclick="carregarDashboardNfag()">Aplicar</button>
      </div>

      <div class="grade-kpis-nfag-dc">
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-integradas">-</div><div class="rotulo-kpi-nfag-dc">Qtd Integradas</div></div>
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-ultima-hora">-</div><div class="rotulo-kpi-nfag-dc">Qtd Última Hora</div></div>
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-autorizadas">-</div><div class="rotulo-kpi-nfag-dc">Qtd Autorizadas</div></div>
        <div class="kpi-nfag-dc"><div class="valor-kpi-nfag-dc" id="kpi-nfag-rejeitadas">-</div><div class="rotulo-kpi-nfag-dc">Qtd Rejeitadas</div></div>
      </div>

      <div class="erro-mu" id="nfag-erro-dc"></div>

      <div class="painel-dc">
        <h3>Notas por Status</h3>
        <div class="container-grafico-nfag-dc" id="container-grafico-status-dc">
          <canvas id="grafico-status-nfag-dc"></canvas>
        </div>
      </div>

      <div class="painel-dc">
        <h3>Integrada x Autorizada por Hora</h3>
        <div class="container-grafico-nfag-dc" id="container-grafico-hora-dc">
          <canvas id="grafico-hora-nfag-dc"></canvas>
        </div>
      </div>
    </div>

    <!-- Painel genérico pra relatórios Power BI que já existem prontos e só
         precisam ser incorporados (iframe) - o navegador cuida da
         autenticação com a conta Microsoft/Power BI de quem estiver
         logado, igual abrir o link direto. -->
    <div class="painel-dc" id="painel-iframe-dc" style="display:none; max-width:1100px; margin:0 auto 20px auto">
      <div class="aviso-beta-dc" style="margin-bottom:16px">
        Relatório do Power BI incorporado direto - <b>precisa estar logado com uma conta Microsoft que tenha
        acesso a esse relatório</b> (mesma conta usada no navegador pra abrir o Power BI normalmente).
      </div>
      <iframe id="iframe-powerbi-dc" width="100%" height="620" frameborder="0" allowfullscreen="true"
              style="border-radius: 10px; background: #0b0f14;"></iframe>
    </div>

    <div class="painel-dc" id="painel-placeholder-dc" style="display:none">
      <div class="placeholder-dc">
        <div class="icone-placeholder-dc">🚧</div>
        <div class="titulo-placeholder-dc" id="placeholder-titulo-dc"></div>
        <div>Esse dashboard ainda está em construção - em breve vamos trabalhar nisso.</div>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
let clientesDC = {};
let clienteSelecionadoDC = null;

async function carregarClientesDC() {
  try {
    const resp = await fetch('/api/dashboards-clientes');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('grade-clientes-dc').innerHTML = '<div class="vazio-mu">' + (dados.erro || 'Erro ao carregar.') + '</div>';
      return;
    }
    clientesDC = dados.clientes;
    const nomes = Object.keys(clientesDC).sort();
    if (nomes.length === 0) {
      document.getElementById('grade-clientes-dc').innerHTML = '<div class="vazio-mu">Nenhum cliente cadastrado ainda.</div>';
      return;
    }
    document.getElementById('grade-clientes-dc').innerHTML = nomes.map(nome => `
      <div class="pill-dc" data-cliente="${nome}" onclick="selecionarClienteDC('${nome}')">${nome}</div>
    `).join('');
  } catch (e) {
    document.getElementById('grade-clientes-dc').innerHTML = '<div class="vazio-mu">Erro ao carregar: ' + e + '</div>';
  }
}

function selecionarClienteDC(nome) {
  clienteSelecionadoDC = nome;
  document.querySelectorAll('#grade-clientes-dc .pill-dc').forEach(p => p.classList.toggle('ativa', p.dataset.cliente === nome));

  document.getElementById('trilha-dc').innerHTML = `<span class="atual">${nome}</span><span>·</span><span>Selecione um produto</span>`;
  document.getElementById('painel-placeholder-dc').style.display = 'none';

  const produtos = clientesDC[nome] || [];
  document.getElementById('painel-produtos-dc').style.display = 'block';
  document.getElementById('grade-produtos-dc').innerHTML = produtos.map(produto => `
    <div class="pill-dc" data-produto="${produto}" onclick="selecionarProdutoDC('${produto}')">${produto}</div>
  `).join('');
}

// Relatórios Power BI já prontos, só incorporados via iframe - "Cliente|Produto" -> URL de embed
const IFRAMES_DASHBOARDS_DC = {
  // 'Cliente|Produto': 'https://app.powerbi.com/reportEmbed?reportId=...&autoAuth=true&ctid=...'
};

function selecionarProdutoDC(produto) {
  document.querySelectorAll('#grade-produtos-dc .pill-dc').forEach(p => p.classList.toggle('ativa', p.dataset.produto === produto));
  document.getElementById('trilha-dc').innerHTML = `<span class="atual">${clienteSelecionadoDC}</span><span>·</span><span class="atual">${produto}</span>`;

  // Sanepar > NFAg já tem dashboard de verdade (transcrito do Power BI) -
  // qualquer outra combinação cliente/produto ainda cai no placeholder.
  if (clienteSelecionadoDC === 'Sanepar' && produto === 'NFAg') {
    document.getElementById('painel-iframe-dc').style.display = 'none';
    document.getElementById('painel-placeholder-dc').style.display = 'none';
    document.getElementById('painel-dashboard-nfag-dc').style.display = 'block';
    document.getElementById('painel-dashboard-nfag-dc').scrollIntoView({ behavior: 'smooth', block: 'start' });
    carregarDashboardNfag();
    return;
  }

  // Relatório Power BI já pronto, incorporado direto via iframe
  const chaveIframe = clienteSelecionadoDC + '|' + produto;
  if (IFRAMES_DASHBOARDS_DC[chaveIframe]) {
    document.getElementById('painel-dashboard-nfag-dc').style.display = 'none';
    document.getElementById('painel-placeholder-dc').style.display = 'none';
    document.getElementById('iframe-powerbi-dc').src = IFRAMES_DASHBOARDS_DC[chaveIframe];
    document.getElementById('painel-iframe-dc').style.display = 'block';
    document.getElementById('painel-iframe-dc').scrollIntoView({ behavior: 'smooth', block: 'start' });
    return;
  }

  document.getElementById('painel-dashboard-nfag-dc').style.display = 'none';
  document.getElementById('painel-iframe-dc').style.display = 'none';
  document.getElementById('painel-placeholder-dc').style.display = 'block';
  document.getElementById('placeholder-titulo-dc').innerText = `${clienteSelecionadoDC} · ${produto}`;
  document.getElementById('painel-placeholder-dc').scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// -- Dashboard Sanepar > NFAg - transcrito do Power BI (Indicadores_NFAg
// _Sanepar.pbix) em 08/09/2026: mesma query nativa, mesmas medidas DAX
// (Status Descricao, Qtd Integradas/Última Hora/Autorizadas/Rejeitadas),
// calculadas em Python no backend (ver _consultar_dashboard_sanepar_nfag).
let graficoStatusNfagDC = null;
let graficoHoraNfagDC = null;

async function carregarDashboardNfag() {
  const dataInicio = document.getElementById('nfag-data-inicio').value;
  const dataFim = document.getElementById('nfag-data-fim').value;
  const erroEl = document.getElementById('nfag-erro-dc');
  erroEl.innerText = '';

  let url = '/api/dashboards-clientes/sanepar/nfag';
  const parametros = [];
  if (dataInicio) parametros.push('data_inicio=' + encodeURIComponent(dataInicio));
  if (dataFim) parametros.push('data_fim=' + encodeURIComponent(dataFim));
  if (parametros.length) url += '?' + parametros.join('&');

  try {
    const resp = await fetch(url);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar o dashboard.';
      mostrarErroNosGraficosNfagDC(dados.erro || 'Não foi possível carregar.');
      return;
    }
    renderizarDashboardNfagDC(dados);
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
    mostrarErroNosGraficosNfagDC('Erro ao carregar.');
  }
}

function mostrarErroNosGraficosNfagDC(mensagem) {
  // Em vez de deixar os dois gráficos como caixas grandes vazias quando
  // não tem dado nenhum (ex.: banco fora do ar), mostra um aviso
  // compacto no lugar - mesma altura do container (220px), só que com
  // uma mensagem centralizada em vez de nada.
  const html = `<div class="vazio-grafico-nfag-dc">⚠️ ${mensagem}</div>`;
  document.getElementById('container-grafico-status-dc').innerHTML = html;
  document.getElementById('container-grafico-hora-dc').innerHTML = html;
}

function restaurarCanvasGraficosNfagDC() {
  document.getElementById('container-grafico-status-dc').innerHTML = '<canvas id="grafico-status-nfag-dc"></canvas>';
  document.getElementById('container-grafico-hora-dc').innerHTML = '<canvas id="grafico-hora-nfag-dc"></canvas>';
}

function renderizarDashboardNfagDC(dados) {
  if (graficoStatusNfagDC) { graficoStatusNfagDC.destroy(); graficoStatusNfagDC = null; }
  if (graficoHoraNfagDC) { graficoHoraNfagDC.destroy(); graficoHoraNfagDC = null; }
  restaurarCanvasGraficosNfagDC();
  document.getElementById('kpi-nfag-integradas').innerText = dados.kpis.qtd_integradas;
  document.getElementById('kpi-nfag-ultima-hora').innerText = dados.kpis.qtd_ultima_hora;
  document.getElementById('kpi-nfag-autorizadas').innerText = dados.kpis.qtd_autorizadas;
  document.getElementById('kpi-nfag-rejeitadas').innerText = dados.kpis.qtd_rejeitadas;

  const corTexto = '#8b98a5';
  const corGrade = 'rgba(255,255,255,.08)';

  // "Notas por Status" - barras horizontais, ordenado decrescente (igual
  // ao Formatar visual > Eixo Y > Ordenar por valor do PBIX original)
  const ctxStatus = document.getElementById('grafico-status-nfag-dc').getContext('2d');
  graficoStatusNfagDC = new Chart(ctxStatus, {
    type: 'bar',
    data: {
      labels: dados.por_status.map(s => s.status),
      datasets: [{ label: 'Qtd Integradas', data: dados.por_status.map(s => s.qtd), backgroundColor: '#2db8cf' }],
    },
    options: {
      indexAxis: 'y',
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: corTexto }, grid: { color: corGrade }, beginAtZero: true },
        y: { ticks: { color: '#e6edf3' }, grid: { display: false } },
      },
    },
  });

  // "Integrada x Autorizada por Hora" - colunas agrupadas, escala
  // logarítmica no eixo Y (igual ao original)
  const ctxHora = document.getElementById('grafico-hora-nfag-dc').getContext('2d');
  graficoHoraNfagDC = new Chart(ctxHora, {
    type: 'bar',
    data: {
      labels: dados.por_hora.map(h => h.hora),
      datasets: [
        { label: 'Integradas', data: dados.por_hora.map(h => h.integradas), backgroundColor: '#2db8cf' },
        { label: 'Autorizadas', data: dados.por_hora.map(h => h.autorizadas), backgroundColor: '#b0cb1c' },
      ],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: '#e6edf3' } } },
      scales: {
        x: { ticks: { color: corTexto }, grid: { display: false } },
        y: { type: 'logarithmic', ticks: { color: corTexto }, grid: { color: corGrade } },
      },
    },
  });
}

carregarClientesDC();
</script>
</body>
</html>
"""


_SOBRE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Sobre o PDA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-sobre { text-align: center; max-width: 720px; margin: 10px auto 30px auto; }
  .cabecalho-sobre h1 { font-size: 26px; margin: 0 0 8px 0;
                         background: var(--gradiente-marca); -webkit-background-clip: text;
                         background-clip: text; color: transparent; }
  .cabecalho-sobre .sub { color: var(--fg-dim); font-size: 13.5px; line-height: 1.6; }

  .painel-sobre { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                  border: 1px solid var(--border); border-radius: 14px; padding: 26px 30px;
                  max-width: 720px; margin: 0 auto 20px auto; }
  .painel-sobre h2 { margin: 0 0 12px 0; font-size: 13px; color: var(--teal); text-transform: uppercase;
                      letter-spacing: .06em; }
  .painel-sobre p { color: var(--fg); font-size: 13.5px; line-height: 1.75; margin: 0 0 12px 0; }
  .painel-sobre p:last-child { margin-bottom: 0; }
  .painel-sobre ul { margin: 0; padding-left: 20px; color: var(--fg); font-size: 13.5px; line-height: 1.9; }

  .cartao-autor { display: flex; align-items: center; gap: 16px; flex: 1; min-width: 280px;
                  background: var(--bg-panel); border: 1px solid var(--border-forte); border-radius: 14px;
                  padding: 22px 26px; }
  .grade-autores { display: flex; flex-wrap: wrap; gap: 16px; max-width: 720px; margin: 0 auto 20px auto; }
  .avatar-autor { width: 54px; height: 54px; border-radius: 50%; flex-shrink: 0;
                   object-fit: cover; border: 2px solid var(--border-forte); }
  .info-autor .nome-autor { font-size: 15px; font-weight: 700; color: var(--fg); margin-bottom: 2px; }
  .info-autor .cargo-autor { font-size: 12px; color: var(--fg-dim); }

  .grade-numeros { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 14px;
                    max-width: 720px; margin: 0 auto 20px auto; }
  .cartao-numero { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px;
                    padding: 16px 18px; text-align: center; }
  .cartao-numero .valor { font-size: 24px; font-weight: 700; color: var(--teal); }
  .cartao-numero .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                            letter-spacing: .04em; margin-top: 4px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-sobre">
      <h1>PDA · Painel de Automações</h1>
      <div class="sub">Central de automações, indicadores e ferramentas internas.</div>
    </div>

    <div class="grade-numeros">
      <div class="cartao-numero"><div class="valor">12</div><div class="rotulo">Alertas automáticos</div></div>
      <div class="cartao-numero"><div class="valor">9</div><div class="rotulo">Produtos no Dash Financeiro</div></div>
      <div class="cartao-numero"><div class="valor">16</div><div class="rotulo">Cards no painel</div></div>
    </div>

    <div class="painel-sobre">
      <h2>O que é o PDA</h2>
      <p>
        O PDA é uma aplicação web desenvolvida para centralizar, executar
        e monitorar automações internas. A solução integra
        diferentes serviços e fontes de dados, utilizando Python, SQL
        Server, Microsoft Graph API e integrações com o Workflow e
        Sharepoint.
      </p>
      <p>
        A aplicação possui autenticação e controle granular de
        permissões, execução concorrente de automações, gerenciamento
        seguro de credenciais e registro das operações realizadas,
        proporcionando um ambiente centralizado para acompanhamento,
        controle e manutenção dos processos automatizados.
      </p>
      </p>
      <h2>O que o painel cobre hoje</h2>
      <ul>
        <li>Execução e acompanhamento dos alertas fiscais automáticos</li>
        <li>Monitoramento de contingências SEFAZ por estado, com aviso automático no Teams</li>
        <li>Indicadores, apontamentos e sincronização com o Movidesk</li>
        <li>Relatórios do cliente Shein (geração, download, envio automático)</li>
        <li>Atualização mensal do Dash Financeiro pro Power BI</li>
        <li>Manutenção de alertas, rejeições e relatórios direto no banco de monitoramento</li>
        <li>Monitoramento dos logs do EmailPack por e-mail processado, com aviso automático no Teams</li>
        <li>Gestão de usuários, permissões granulares e credenciais cifradas</li>
      </ul>
    </div>

    <div class="grade-autores">
      <div class="cartao-autor">
        <div class="info-autor">
          <div class="nome-autor">Desenvolvimento</div>
          <div class="cargo-autor">Aplicação PDA · Frontend, Backend e QA</div>
        </div>
      </div>
      <div class="cartao-autor">
        <div class="info-autor">
          <div class="nome-autor">Supervisão</div>
          <div class="cargo-autor">Supervisão do projeto · Banco de Monitoramento &amp; Movidesk · UI/UX do PDA</div>
        </div>
      </div>
    </div>
  </div>

  __FOOTER__
</body>
</html>
"""


def _montar_sobre_html(sessao: dict) -> str:
    return (
        _SOBRE_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Sobre o PDA"))
        .replace("__FOOTER__", _montar_footer())
    )


_RELATORIOS_SHEIN_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Relatórios Shein</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  .painel-shein { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                  border: 1px solid var(--border); border-radius: 16px; padding: 28px 30px;
                  max-width: 620px; margin: 0 auto; }
  .painel-shein h2 { margin: 0 0 6px 0; font-size: 16px; color: var(--teal); }
  .painel-shein .sub-shein { color: var(--fg-dim); font-size: 12.5px; line-height: 1.6; margin-bottom: 22px; }
  .painel-shein label { display: block; font-size: 11px; color: var(--fg-dim); margin: 0 0 6px 0;
                         text-transform: uppercase; letter-spacing: .04em; }
  .painel-shein input[type="date"] { width: 100%; padding: 10px 12px; border-radius: 8px;
                                       border: 1px solid var(--border); background: rgba(0,0,0,.28);
                                       color: var(--fg); font-size: 14px; }
  .painel-shein input[type="date"]:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .painel-shein button.btn-accent { width: 100%; margin-top: 18px; padding: 12px; font-size: 14px; }
  .erro-shein { color: var(--erro); font-size: 12.5px; margin-top: 14px; text-align: center; min-height: 14px; }
  .carregando-shein { display: none; text-align: center; color: var(--fg-dim); font-size: 12.5px; margin-top: 16px; }
  .btn-secundario { width: 100%; margin-top: 8px; padding: 11px; font-size: 13.5px; border-radius: 8px;
                     background: rgba(255,255,255,.04); color: var(--fg); border: 1px solid var(--border-forte);
                     cursor: pointer; transition: background .15s, border-color .15s; }
  .btn-secundario:hover { background: rgba(255,255,255,.08); border-color: var(--teal); }
  .carregando-shein.visivel { display: block; }
  .spinner-shein { width: 22px; height: 22px; border: 3px solid rgba(45,184,207,.2); border-top-color: var(--teal);
                    border-radius: 50%; margin: 0 auto 10px auto; animation: girar-spinner 0.8s linear infinite; }
  @keyframes girar-spinner { to { transform: rotate(360deg); } }

  .resultado-shein { display: none; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border); }
  .resultado-shein.visivel { display: block; }
  .resultado-shein .linha-resultado { display: flex; justify-content: space-between; align-items: center;
                    background: rgba(0,0,0,.2); border: 1px solid var(--border); border-radius: 10px;
                    padding: 12px 16px; margin-bottom: 10px; }
  .resultado-shein .linha-resultado .info-arquivo { font-size: 13px; }
  .resultado-shein .linha-resultado .info-arquivo .contagem { color: var(--fg-dim); font-size: 11.5px; margin-top: 2px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="painel-shein">
      <h2>Relatórios Shein</h2>
      <div class="sub-shein">
        Gera os relatórios de Notas e Canceladas (CTe) do cliente Shein pra
        uma data específica, direto do banco de produção. Pode demorar um
        pouco dependendo do volume do dia.
      </div>

      <label>Data</label>
      <input type="date" id="shein-data">

      <button class="btn-accent" onclick="gerarRelatorioShein()">Gerar relatório</button>

      <div class="carregando-shein" id="carregando-shein">
        <div class="spinner-shein"></div>
        Consultando o banco e montando as planilhas...
      </div>

      <div class="erro-shein" id="erro-shein"></div>

      <div class="resultado-shein" id="resultado-shein">
        <div class="linha-resultado">
          <div class="info-arquivo">
            Notas
            <div class="contagem" id="contagem-notas"></div>
          </div>
        </div>
        <div class="linha-resultado">
          <div class="info-arquivo">
            Canceladas
            <div class="contagem" id="contagem-canceladas"></div>
          </div>
        </div>
        <a class="btn-link" id="link-zip-gerado" href="#" style="display:block; text-align:center; margin-top:10px;">Baixar (.zip)</a>
      </div>
    </div>

    <div class="painel-shein" style="margin-top:20px">
      <h2>Baixar relatório já gerado</h2>
      <div class="sub-shein">
        Se o relatório de um dia já foi gerado antes (manualmente ou pelo
        envio automático das 08:00), baixa direto sem precisar consultar o
        banco de novo - vai pra pasta Downloads do navegador.
      </div>

      <label>Data</label>
      <input type="date" id="shein-data-baixar">

      <button class="btn-secundario" onclick="baixarRelatorioExistente()">Baixar relatório do dia</button>

      <div class="erro-shein" id="erro-shein-baixar"></div>
    </div>

    <div class="painel-shein" style="margin-top:20px">
      <h2>Envio automático diário</h2>
      <div class="sub-shein">
        Todos os dias às __HORARIO_AUTOMATICO__, o relatório do dia anterior é
        gerado e enviado sozinho pro SharePoint
        (Relatorio_Shein/&lt;Mês&gt;/&lt;DD-MM-AAAA&gt;).
      </div>
      <div id="status-automatico-shein" style="font-size:12.5px; color:var(--fg-dim); margin-bottom:14px;">Carregando status...</div>
      <button onclick="forcarRelatorioAutomatico()">Testar envio automático agora</button>
      <button onclick="alternarLogShein()" id="botao-log-shein" style="margin-left:8px">Ver log isolado</button>
      <div id="log-shein-container" style="display:none; margin-top:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="font-size:11px; color:var(--fg-dim); text-transform:uppercase; letter-spacing:.04em;">
            Últimas linhas de shein_relatorios.log
          </span>
          <button onclick="carregarLogShein()" class="btn-mini">Atualizar</button>
        </div>
        <pre id="log-shein-conteudo" style="background:rgba(0,0,0,.35); border:1px solid var(--border);
             border-radius:8px; padding:12px 14px; max-height:360px; overflow-y:auto; font-size:11px;
             font-family:Consolas,monospace; color:var(--fg-dim); white-space:pre-wrap; word-break:break-word;
             margin:0;">Carregando...</pre>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
(function () {
  const hoje = new Date();
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);
  document.getElementById('shein-data').value = ontem.toISOString().slice(0, 10);
})();

async function carregarStatusAutomaticoShein() {
  try {
    const resp = await fetch('/api/relatorios-shein/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    const el = document.getElementById('status-automatico-shein');
    if (!dados.ultima_execucao) {
      el.innerText = 'Ainda não rodou nesta execução do programa.';
    } else if (dados.ultimo_erro) {
      el.innerHTML = '<span style="color:var(--erro)">⚠ Última tentativa (' + dados.ultima_execucao + ') falhou: ' + dados.ultimo_erro + '</span>';
    } else {
      el.innerHTML = '<span style="color:var(--ok)">✓ Último envio bem-sucedido: ' + dados.ultimo_sucesso + '</span>';
    }
  } catch (e) {
    document.getElementById('status-automatico-shein').innerText = 'Erro ao consultar status: ' + e;
  }
}

async function forcarRelatorioAutomatico() {
  const resp = await fetch('/api/relatorios-shein/forcar-automatico', { method: 'POST' });
  if (resp.status === 401) { window.location.href = '/login'; return; }
  document.getElementById('status-automatico-shein').innerText = 'Disparado - rodando em segundo plano, atualize em alguns instantes...';
  setTimeout(carregarStatusAutomaticoShein, 4000);
  setTimeout(() => {
    if (document.getElementById('log-shein-container').style.display !== 'none') carregarLogShein();
  }, 4000);
}

let logSheinVisivel = false;
function alternarLogShein() {
  logSheinVisivel = !logSheinVisivel;
  document.getElementById('log-shein-container').style.display = logSheinVisivel ? 'block' : 'none';
  document.getElementById('botao-log-shein').innerText = logSheinVisivel ? 'Esconder log isolado' : 'Ver log isolado';
  if (logSheinVisivel) carregarLogShein();
}

async function carregarLogShein() {
  const el = document.getElementById('log-shein-conteudo');
  el.innerText = 'Carregando...';
  try {
    const resp = await fetch('/api/relatorios-shein/log');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { el.innerText = 'Erro: ' + dados.erro; return; }
    if (dados.linhas.length === 0) {
      el.innerText = dados.aviso || 'Ainda não há nada registrado.';
      return;
    }
    el.innerText = dados.linhas.join('\\n');
    el.scrollTop = el.scrollHeight;
  } catch (e) {
    el.innerText = 'Erro ao carregar: ' + e;
  }
}

carregarStatusAutomaticoShein();
async function gerarRelatorioShein() {
  const data = document.getElementById('shein-data').value;
  const erroEl = document.getElementById('erro-shein');
  const carregandoEl = document.getElementById('carregando-shein');
  const resultadoEl = document.getElementById('resultado-shein');
  erroEl.innerText = '';
  resultadoEl.classList.remove('visivel');

  if (!data) {
    erroEl.innerText = 'Selecione uma data.';
    return;
  }

  carregandoEl.classList.add('visivel');
  try {
    const resp = await fetch('/api/relatorios-shein/gerar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'data=' + encodeURIComponent(data),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    carregandoEl.classList.remove('visivel');

    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível gerar o relatório.';
      return;
    }

    document.getElementById('contagem-notas').innerText = dados.linhas_notas + ' linha(s)';
    document.getElementById('contagem-canceladas').innerText = dados.linhas_canceladas + ' linha(s)';
    const [ano, mes, dia] = data.split('-');
    const dataArquivo = dia + '-' + mes + '-' + ano;
    document.getElementById('link-zip-gerado').href = '/api/relatorios-shein/download-zip/' + encodeURIComponent(dataArquivo);
    resultadoEl.classList.add('visivel');
  } catch (e) {
    carregandoEl.classList.remove('visivel');
    erroEl.innerText = 'Erro ao gerar: ' + e;
  }
}

async function baixarRelatorioExistente() {
  const data = document.getElementById('shein-data-baixar').value;
  const erroEl = document.getElementById('erro-shein-baixar');
  erroEl.innerText = '';
  erroEl.style.color = '';
  if (!data) {
    erroEl.innerText = 'Selecione uma data.';
    return;
  }
  try {
    const resp = await fetch('/api/relatorios-shein/existe?data=' + encodeURIComponent(data));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível conferir.';
      return;
    }
    if (!dados.existe) {
      erroEl.innerText = 'Ainda não existe relatório gerado pra esse dia (gere na seção de cima primeiro).';
      return;
    }
    // baixa um zip só com os 2 arquivos, nomeado com a data - o navegador
    // salva na pasta Downloads dele, igual qualquer outro download normal
    const [ano, mes, dia] = data.split('-');
    const dataArquivo = dia + '-' + mes + '-' + ano;
    const link = document.createElement('a');
    link.href = '/api/relatorios-shein/download-zip/' + encodeURIComponent(dataArquivo);
    link.download = dataArquivo + '.zip';
    document.body.appendChild(link);
    link.click();
    link.remove();

    erroEl.style.color = 'var(--ok)';
    erroEl.innerText = 'Baixando ' + dataArquivo + '.zip...';
  } catch (e) {
    erroEl.style.color = '';
    erroEl.innerText = 'Erro ao baixar: ' + e;
  }
}
</script>
</body>
</html>
"""


def _montar_relatorios_shein_html(sessao: dict) -> str:
    return (
        _RELATORIOS_SHEIN_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Relatórios Shein"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__HORARIO_AUTOMATICO__", HORARIO_RELATORIO_SHEIN_AUTOMATICO)
    )


_CONTINGENCIAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Monitoramento de Contingências</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-conting {
    background: linear-gradient(135deg, rgba(241,76,76,.10), rgba(241,76,76,0) 60%);
    border: 1px solid rgba(241,76,76,.25); border-radius: 16px;
    padding: 22px 26px; margin-bottom: 22px;
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
  }
  .cabecalho-conting h1 { margin: 0 0 4px 0; font-size: 20px; color: #ff8080; }
  .cabecalho-conting .sub-conting { color: var(--fg-dim); font-size: 12px; max-width: 620px; line-height: 1.5; }
  .cabecalho-conting .ultima { color: var(--fg-dim); font-size: 11px; margin-top: 8px; font-family: Consolas, monospace; }
  .aviso-scraping { background: rgba(220,220,170,.08); border: 1px solid rgba(220,220,170,.25);
                     border-radius: 10px; padding: 12px 16px; font-size: 11.5px; color: var(--run);
                     margin-bottom: 22px; line-height: 1.6; }
  .resumo-conting { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
  .cartao-conting { background: var(--bg-panel); backdrop-filter: blur(10px); border: 1px solid var(--border);
                     border-radius: 12px; padding: 14px 20px; min-width: 130px; }
  .cartao-conting .num { font-size: 24px; font-weight: 700; font-family: Consolas, monospace; }
  .cartao-conting .rot { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em; }

  .area-mapa { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 22px; align-items: start; }
  @media (max-width: 860px) { .area-mapa { grid-template-columns: 1fr; } }

  .painel-mapa { background: var(--bg-panel); backdrop-filter: blur(10px); border: 1px solid var(--border);
                 border-radius: 16px; padding: 24px; overflow-x: auto; }
  .painel-mapa h2 { margin: 0 0 4px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                     letter-spacing: .05em; font-weight: 600; text-align: center; }
  .painel-mapa .legenda-inline { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center; }
  .painel-mapa .legenda-inline .item-legenda { display: flex; align-items: center; gap: 7px; font-size: 11.5px; color: var(--fg-dim); }
  .item-legenda .amostra { width: 13px; height: 13px; border-radius: 4px; flex-shrink: 0; }
  .amostra.normal { background: rgba(78,201,176,.25); border: 1px solid var(--ok); }
  .amostra.contingencia { background: rgba(241,76,76,.3); border: 1px solid #f14c4c; }
  .amostra.agendada { background: rgba(220,220,170,.3); border: 1px solid var(--run); }
  .amostra.desconhecido { background: rgba(255,255,255,.06); border: 1px solid var(--border-forte); }

  .mapa-escala-container { width: 100%; max-width: 680px; margin: 0 auto; position: relative;
                            overflow: hidden; }
  .mapa-wrapper { position: relative; width: 560px; height: 552px; transform-origin: top left; }
  .silhueta-brasil { position: absolute; inset: 0; width: 100%; height: 100%; }
  .silhueta-brasil path {
    fill: url(#gradiente-silhueta); stroke: rgba(45,184,207,.55); stroke-width: 2;
  }
  .mapa-brasil { display: grid; grid-template-columns: repeat(9, 40px); grid-auto-rows: 40px; gap: 6px;
                 position: absolute; left: 92px; top: 46px; }
  .uf-tile {
    border-radius: 9px; display: flex; align-items: center; justify-content: center;
    font-size: 11.5px; font-weight: 700; font-family: Consolas, monospace;
    background: rgba(20,26,32,.85); border: 1px solid var(--border-forte); color: var(--fg-dim);
    transition: transform .15s ease, box-shadow .15s ease; cursor: default;
  }
  .uf-tile:hover { transform: scale(1.18); z-index: 2; border-color: var(--teal); }
  .uf-tile.normal { background: rgba(78,201,176,.28); border-color: rgba(78,201,176,.6); color: #eafff9; }
  .uf-tile.desconhecido { background: rgba(20,26,32,.85); border-color: var(--border-forte); color: var(--fg-dim); }
  .uf-tile.agendada { background: rgba(220,220,170,.3); border-color: var(--run); color: #fff8e0; }
  .uf-tile.contingencia {
    background: rgba(241,76,76,.35); border-color: #f14c4c; color: #fff;
    animation: pulso-vermelho 1.6s ease-in-out infinite;
  }
  @keyframes pulso-vermelho {
    0%, 100% { box-shadow: 0 0 6px rgba(241,76,76,.35); }
    50% { box-shadow: 0 0 18px rgba(241,76,76,.85); }
  }

  .coluna-lateral { display: flex; flex-direction: column; gap: 18px; }
  .mini-painel { background: var(--bg-panel); backdrop-filter: blur(10px); border: 1px solid var(--border);
                 border-radius: 14px; padding: 18px 20px; }
  .mini-painel h3 { margin: 0 0 12px 0; font-size: 12.5px; color: #ff8080; text-transform: uppercase;
                     letter-spacing: .04em; font-weight: 700; }
  .mini-painel h3.neutro { color: var(--teal); }
  .lista-afetados .uf-linha { font-size: 12.5px; padding: 8px 10px; border-radius: 8px;
                               background: rgba(241,76,76,.08); border: 1px solid rgba(241,76,76,.2);
                               margin-bottom: 6px; }
  .uf-linha .uf-linha-topo { display: flex; justify-content: space-between; }
  .uf-linha .uf-linha-data { color: var(--fg-dim); font-size: 11px; margin-top: 3px; font-family: Consolas, monospace; }
  .uf-linha.agendada { background: rgba(220,220,170,.08); border-color: rgba(220,220,170,.25); }
  .sem-afetados { color: var(--fg-dim); font-size: 12.5px; }

  .mini-painel p { color: var(--fg-dim); font-size: 12px; line-height: 1.6; margin: 0 0 12px 0; }
  .links-oficiais { display: flex; flex-direction: column; gap: 8px; }
  .links-oficiais a { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--teal);
                       text-decoration: none; padding: 8px 10px; border-radius: 8px;
                       background: rgba(45,184,207,.08); border: 1px solid rgba(45,184,207,.2); }
  .links-oficiais a:hover { background: rgba(45,184,207,.15); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-conting">
      <div>
        <h1>Monitoramento de Contingências · SVC-AN / SVC-RS</h1>
        <div class="sub-conting">
          Acompanha a disponibilidade dos autorizadores de NF-e por UF e sinaliza
          quando um estado provavelmente está operando via contingência.
        </div>
        <div class="ultima" id="ultima-verificacao">carregando...</div>
      </div>
      <button class="btn-accent" id="botao-atualizar-contingencias" onclick="atualizarAgora()">Atualizar agora</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro" style="display:none"></div>

    <div class="resumo-conting" id="resumo-conting"></div>

    <div class="area-mapa">
      <div class="painel-mapa">
        <h2>Disponibilidade por UF</h2>
        <div class="legenda-inline">
          <div class="item-legenda"><div class="amostra normal"></div> Normal</div>
          <div class="item-legenda"><div class="amostra contingencia"></div> Contingência ativa</div>
          <div class="item-legenda"><div class="amostra agendada"></div> Contingência agendada</div>
          <div class="item-legenda"><div class="amostra desconhecido"></div> Não verificado</div>
        </div>
          <div class="mapa-escala-container" id="mapa-escala-container">
            <div class="mapa-wrapper" id="mapa-wrapper-escalavel">
              <svg class="silhueta-brasil" viewBox="0 0 560 552" preserveAspectRatio="xMidYMid meet">
                <defs>
                  <linearGradient id="gradiente-silhueta" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#2db8cf" stop-opacity="0.28"/>
                    <stop offset="100%" stop-color="#b0cb1c" stop-opacity="0.20"/>
                  </linearGradient>
                </defs>
                        <path d="M 193.7,20.0 L 186.4,29.0 L 146.3,36.4 L 151.4,59.5 L 158.2,61.7 L 134.5,74.7 L 123.2,74.7 L 108.0,58.4 L 78.7,65.1 L 71.9,88.8 L 78.1,104.6 L 74.7,127.7 L 42.6,143.0 L 20.0,184.7 L 29.0,210.6 L 41.4,219.7 L 56.7,220.2 L 65.1,232.1 L 89.4,233.2 L 122.1,219.1 L 134.5,243.9 L 189.2,265.9 L 196.5,280.6 L 192.6,281.1 L 196.0,297.5 L 218.0,302.6 L 219.1,311.0 L 227.5,312.1 L 223.0,315.0 L 227.5,325.1 L 221.9,337.0 L 224.2,370.8 L 250.1,382.6 L 254.1,378.1 L 253.5,395.6 L 267.0,400.7 L 267.0,415.9 L 274.4,426.6 L 272.7,437.9 L 258.0,445.2 L 229.2,480.2 L 271.5,510.7 L 279.4,532.1 L 315.5,498.8 L 343.7,459.3 L 347.7,425.5 L 356.7,415.9 L 400.7,395.1 L 434.0,393.4 L 453.7,371.4 L 472.9,326.2 L 479.1,284.5 L 497.1,271.5 L 509.5,252.4 L 507.9,245.0 L 534.9,217.4 L 540.0,197.1 L 537.2,173.4 L 528.7,156.5 L 496.6,147.5 L 470.6,124.3 L 415.4,115.3 L 403.5,103.5 L 342.0,83.2 L 343.2,66.2 L 330.2,52.1 L 324.6,34.7 L 310.5,42.0 L 298.6,62.9 L 271.0,52.7 L 218.0,69.6 L 210.6,53.3 L 212.3,30.7 L 207.2,22.3 Z"/>
              </svg>
              <div class="mapa-brasil" id="mapa-brasil"></div>
            </div>
          </div>
      </div>

      <div class="coluna-lateral">
        <div class="mini-painel lista-afetados">
          <h3>Contingência ativa agora</h3>
          <div id="lista-afetados"><div class="sem-afetados">Nenhuma no momento.</div></div>
        </div>

        <div class="mini-painel">
          <h3 class="neutro">Contingências agendadas</h3>
          <div id="lista-agendadas"><div class="sem-afetados">Nenhuma no momento.</div></div>
          <div class="links-oficiais" style="margin-top:14px">
            <a href="https://www.sefaz.rs.gov.br/NFE/NFE-SVC.aspx" target="_blank" rel="noopener">
              Fonte oficial: situação SVC-RS ↗
            </a>
            <a href="https://www.nfe.fazenda.gov.br/portal/principal.aspx" target="_blank" rel="noopener">
              Fonte oficial: Portal Nacional NF-e (SVC-AN) ↗
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
const GRADE_UF = __GRADE_UF_JSON__;
const NOME_UF = __NOME_UF_JSON__;
const SVC_POR_UF = __SVC_POR_UF_JSON__;

function montarMapa() {
  const mapa = document.getElementById('mapa-brasil');
  mapa.innerHTML = '';
  for (const uf in GRADE_UF) {
    const [col, lin] = GRADE_UF[uf];
    const tile = document.createElement('div');
    tile.className = 'uf-tile desconhecido';
    tile.id = 'uf-' + uf;
    tile.style.gridColumn = (col + 1);
    tile.style.gridRow = (lin + 1);
    tile.innerText = uf;
    tile.title = NOME_UF[uf] + ' (contingência: ' + SVC_POR_UF[uf] + ')';
    mapa.appendChild(tile);
  }
}

let ultimaAssinaturaConting = '';

async function carregarContingencias() {
  try {
    const resp = await fetch('/api/contingencias');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();

    const avisoEl = document.getElementById('aviso-erro');
    if (dados.ultimo_erro) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível confirmar a última consulta ao portal da NF-e: ' + dados.ultimo_erro;
    } else {
      avisoEl.style.display = 'none';
    }

    document.getElementById('ultima-verificacao').innerText =
      dados.ultima_verificacao ? ('Última verificação: ' + dados.ultima_verificacao) : 'Ainda não verificado';

    // Se nada mudou desde o ultimo poll, nao mexe em NADA no DOM - evita
    // reiniciar a animacao de pulso dos tiles em contingencia (senao ela
    // "piscaria" de novo a cada 5s mesmo sem mudanca real) e economiza
    // trabalho de layout do navegador.
    const assinaturaAtual = JSON.stringify(dados.ufs) + JSON.stringify(dados.detalhes || {});
    if (assinaturaAtual === ultimaAssinaturaConting) return;
    ultimaAssinaturaConting = assinaturaAtual;

    let normal = 0, contingencia = 0, agendada = 0, desconhecido = 0;
    const afetados = [];
    const agendadas = [];
    const detalhes = dados.detalhes || {};
    for (const uf in dados.ufs) {
      const status = dados.ufs[uf];
      const tile = document.getElementById('uf-' + uf);
      if (tile && tile.dataset.status !== status) {
        tile.className = 'uf-tile ' + status;
        tile.dataset.status = status;
      }
      if (status === 'normal') normal++;
      else if (status === 'contingencia') { contingencia++; afetados.push(uf); }
      else if (status === 'agendada') { agendada++; agendadas.push(uf); }
      else desconhecido++;
    }

    document.getElementById('resumo-conting').innerHTML = `
      <div class="cartao-conting"><div class="num" style="color:var(--ok)">${normal}</div><div class="rot">Normal</div></div>
      <div class="cartao-conting"><div class="num" style="color:#f14c4c">${contingencia}</div><div class="rot">Contingência</div></div>
      <div class="cartao-conting"><div class="num" style="color:var(--run)">${agendada}</div><div class="rot">Agendada</div></div>
      <div class="cartao-conting"><div class="num" style="color:var(--fg-dim)">${desconhecido}</div><div class="rot">Não verificado</div></div>
    `;

    const listaEl = document.getElementById('lista-afetados');
    if (afetados.length === 0) {
      listaEl.innerHTML = '<div class="sem-afetados">Nenhuma no momento.</div>';
    } else {
      listaEl.innerHTML = afetados.map(uf => {
        const d = detalhes[uf];
        const linhaData = d ? `<div class="uf-linha-data">Desde ${d.inicio}${d.fim ? ' até ' + d.fim : ''}</div>` : '';
        return `<div class="uf-linha">
          <div class="uf-linha-topo"><span>${NOME_UF[uf]} (${uf})</span><span>${SVC_POR_UF[uf]}</span></div>
          ${linhaData}
        </div>`;
      }).join('');
    }

    const listaAgendadasEl = document.getElementById('lista-agendadas');
    if (agendadas.length === 0) {
      listaAgendadasEl.innerHTML = '<div class="sem-afetados">Nenhuma no momento.</div>';
    } else {
      listaAgendadasEl.innerHTML = agendadas.map(uf => `
        <div class="uf-linha agendada">
          <div class="uf-linha-topo"><span>${NOME_UF[uf]} (${uf})</span><span>${SVC_POR_UF[uf]}</span></div>
        </div>
      `).join('');
    }
  } catch (e) {
    document.getElementById('ultima-verificacao').innerText = 'Erro ao atualizar: ' + e;
  }
}

async function atualizarAgora() {
  const botao = document.getElementById('botao-atualizar-contingencias');
  if (botao.disabled) return;  // trava no proprio clique - ignora cliques repetidos na hora, antes ate do fetch responder
  botao.disabled = true;
  const textoOriginal = botao.innerText;
  botao.innerText = 'Atualizando...';
  try {
    const resp = await fetch('/api/contingencias/atualizar', { method: 'POST' });
    const dados = await resp.json();
    if (!dados.ok) {
      const avisoEl = document.getElementById('aviso-erro');
      avisoEl.innerText = dados.erro || 'Não foi possível atualizar.';
      avisoEl.style.display = 'block';
      setTimeout(() => { avisoEl.style.display = 'none'; }, 4000);
    }
    setTimeout(carregarContingencias, 1500);
  } finally {
    setTimeout(() => { botao.disabled = false; botao.innerText = textoOriginal; }, 1500);
  }
}

// Escala o mapa (SVG + blocos, como uma unidade só) pra caber na largura
// disponível, mantendo mapa e blocos sempre alinhados entre si em
// qualquer tamanho de tela - sem isso, o SVG (que escala sozinho via
// viewBox) e os blocos (posicionados em pixel fixo) se descolavam um do
// outro em telas estreitas, cortando o mapa pela metade no celular.
function ajustarEscalaMapa() {
  const contêiner = document.getElementById('mapa-escala-container');
  const wrapper = document.getElementById('mapa-wrapper-escalavel');
  if (!contêiner || !wrapper) return;
  const larguraBase = 560, alturaBase = 552;
  const larguraDisponivel = contêiner.clientWidth || larguraBase;
  // permite crescer um pouco além do tamanho "natural" (até 1.25x, ~700px)
  // pra dar mais espaço de respiro aos blocos de status, mas continua
  // encolhendo normalmente em telas estreitas.
  const escala = Math.min(1.25, larguraDisponivel / larguraBase);
  wrapper.style.transform = `scale(${escala})`;
  contêiner.style.height = (alturaBase * escala) + 'px';
}
window.addEventListener('resize', ajustarEscalaMapa);
if (window.ResizeObserver) {
  const observador = new ResizeObserver(ajustarEscalaMapa);
  window.addEventListener('load', () => {
    const el = document.getElementById('mapa-escala-container');
    if (el) observador.observe(el);
  });
}

montarMapa();
ajustarEscalaMapa();
carregarContingencias();
setInterval(carregarContingencias, 5000);
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Otimização de performance: o logo/favicon (base64 de ~27KB) é idêntico em
# TODA página e NUNCA muda - antes, cada carregamento de página fazia até 3
# substituições desse texto de 27KB (__LOGO__ na navbar, __LOGO__ no rodapé,
# __FAVICON__ na própria página) via .replace(), toda vez, do zero. Isso
# significava escanear ~80KB de texto repetido a cada requisição, sem
# necessidade nenhuma - o resultado final é sempre o mesmo.
#
# Aqui a gente faz essa substituição UMA VEZ SÓ, na inicialização do
# programa, direto nos templates - o conteúdo final entregue ao navegador
# fica EXATAMENTE IGUAL (confirmado por hash byte a byte de cada página
# antes/depois desta mudança), só que sem repetir o trabalho a cada
# requisição. .replace() em uma substring que não existe no template não
# dá erro nenhum, só devolve o texto original - por isso é seguro aplicar
# nos dois placeholders (__FAVICON__/__LOGO__) em todos os templates, sem
# precisar saber exatamente qual template usa qual.
for _nome_template in (
    "_HTML_PAGE", "_LOGIN_HTML_TEMPLATE", "_ALTERAR_SENHA_HTML_TEMPLATE",
    "_HUB_HTML_TEMPLATE", "_USUARIOS_NEGADO_TEMPLATE", "_USUARIOS_HTML_TEMPLATE",
    "_MANUTENCAO_ALERTAS_HTML_TEMPLATE", "_MANUTENCAO_REJEICOES_HTML_TEMPLATE", "_MANUTENCAO_RELATORIOS_HTML_TEMPLATE", "_SOBRE_HTML_TEMPLATE", "_RELATORIOS_SHEIN_HTML_TEMPLATE",
    "_CONTINGENCIAS_HTML_TEMPLATE", "_STRING_CONNECTIONS_HTML_TEMPLATE", "_INDICADORES_MOVIDESK_HTML_TEMPLATE",
    "_HORAS_TRABALHADAS_HTML_TEMPLATE", "_AUTOMACAO_MOVIDESK_HTML_TEMPLATE", "_DASH_FINANCEIRO_HTML_TEMPLATE",
    "_LOGS_HTML_TEMPLATE", "_MANUTENCAO_USUARIOS_HTML_TEMPLATE",
    # os 4 abaixo tinham __FAVICON__ no HTML mas nunca entravam nessa lista
    # nem eram substituídos manualmente nos respectivos _montar_*_html -
    # favicon ficava literalmente mostrando o texto "__FAVICON__" quebrado
    # nessas 4 páginas (achado numa validação, pré-existente, não relacionado
    # a nenhuma mudança recente - corrigido de graça já que a lista tava aqui).
    "_CONFIG_SEGURO_HTML_TEMPLATE", "_EMAILPACK_HTML_TEMPLATE", "_FERIAS_HTML_TEMPLATE", "_PERFIL_HTML_TEMPLATE",
    "_NAVBAR_HTML", "_FOOTER_HTML",
):
    globals()[_nome_template] = (
        globals()[_nome_template]
        .replace("__FAVICON__", _LOGO_DATA_URI)
        .replace("__LOGO__", _LOGO_DATA_URI)
        .replace("__URL_MEU_PLANTAO__", os.environ.get("PDA_URL_MEU_PLANTAO", "#"))
    )


def _montar_contingencias_html(sessao: dict) -> str:
    return (
        _CONTINGENCIAS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Monitoramento de Contingências"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__GRADE_UF_JSON__", json.dumps(GRADE_UF))
        .replace("__NOME_UF_JSON__", json.dumps(NOME_UF, ensure_ascii=False))
        .replace("__SVC_POR_UF_JSON__", json.dumps(SVC_POR_UF))
    )


# ---------------------------------------------------------------------------
# Autenticação do servidor web (sessão simples via cookie, em memória) +
# usuários com papel (admin / visualização), persistidos em usuarios.json
# ---------------------------------------------------------------------------
# Usuários "de fábrica" - só valem na PRIMEIRA vez que o programa roda (pra
# criar o usuarios.json). Depois disso, qualquer alteração feita pela aba
# "Usuários" (senha, admin ou não) é lida/gravada em usuarios.json, do lado
# do alertas_gui.py/.exe - editar essa lista aqui não tem mais efeito depois
# que o arquivo já existir.
def _usuarios_web_padrao() -> dict:
    """Único usuário "de fábrica": um admin cuja senha inicial vem de
    PDA_ADMIN_SENHA_INICIAL ou, se não houver, é sorteada e registrada UMA
    vez no log. Nenhuma senha fica no código-fonte (repositório público)."""
    senha = os.environ.get("PDA_ADMIN_SENHA_INICIAL", "").strip()
    if not senha:
        senha = secrets.token_urlsafe(9)
        logger.warning("Primeira execução: usuário 'admin' criado com senha inicial sorteada: %s "
                       "(troque em Alterar senha; defina PDA_ADMIN_SENHA_INICIAL pra escolher a sua).", senha)
    return {
        "admin": {"senha": senha, "nome": "Administrador", "admin": True, "pode_manutencao_alertas": True,
                  "pode_relatorios_shein": True, "pode_dash_financeiro": True, "pode_manutencao_rejeicoes": True,
                  "pode_dados_sensiveis": True, "pode_manutencao_relatorios": True, "pode_manutencao_usuarios": True,
                  "ativo": True, "atribuicao": "Suporte", "genero": ""},
    }

DURACAO_INATIVIDADE_MINUTOS = 90  # desconecta depois de 90 min sem atividade real do usuário
SESSIONS: dict = {}  # token -> {"usuario": str, "admin": bool, "pode_manutencao_alertas": bool, "pode_relatorios_shein": bool, "pode_dash_financeiro": bool, "pode_manutencao_rejeicoes": bool, "pode_dados_sensiveis": bool, "pode_manutencao_relatorios": bool, "pode_manutencao_usuarios": bool, "expira": datetime}


def _caminho_usuarios_json() -> str:
    return os.path.join(_base_path_app(), "usuarios.json")


def _carregar_usuarios() -> dict:
    caminho = _caminho_usuarios_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            # compatibilidade com usuarios.json de versões anteriores, que
            # não tinham esses campos ainda - assume sem a permissão extra
            for login, info in dados.items():
                info.setdefault("pode_manutencao_alertas", False)
                info.setdefault("pode_relatorios_shein", False)
                info.setdefault("pode_dash_financeiro", False)
                info.setdefault("pode_manutencao_rejeicoes", False)
                info.setdefault("pode_manutencao_relatorios", False)
                info.setdefault("pode_manutencao_usuarios", False)
                info.setdefault("usuario_movidesk_id", None)
                info.setdefault("email", None)
                info.setdefault("data_inicio", None)
                info.setdefault("ativo", True)
                # nome de exibição (usado no "Bem-vindo, X" e em qualquer
                # lugar que mostre quem é a pessoa) é separado do login
                # (usado só pra entrar, nunca editável) - quem já existia
                # antes dessa separação recebe o próprio login como nome
                # inicial, editável dali em diante por um admin.
                info.setdefault("nome", login)
                # atribuicao da pessoa dentro da operacao - usado no perfil
                # dela; todo mundo comeca como "Suporte" por padrao, o admin
                # ajusta manualmente quem e "Monitoramento" via Editar usuario
                info.setdefault("atribuicao", "Suporte")
                # genero usado so pra flexao de texto (Bem-vindo/Bem-vinda,
                # Administrador/Administradora) - vazio = nao informado,
                # nesse caso usa uma forma neutra em vez de forcar
                # masculino ou feminino
                info.setdefault("genero", "")
                # "pode_string_connections" virou "pode_dados_sensiveis" (agora
                # cobre String Connections E Criptografia de Dados Sensíveis
                # juntos) - quem já tinha a permissão antiga marcada continua
                # com acesso, sem precisar marcar de novo manualmente.
                if "pode_dados_sensiveis" not in info:
                    info["pode_dados_sensiveis"] = info.pop("pode_string_connections", False)
                else:
                    info.pop("pode_string_connections", None)
            return dados
        except Exception:
            logger.exception("Não foi possível ler usuarios.json, usando padrão de fábrica.")
    # primeira execução (ou arquivo corrompido): parte do padrão de fábrica
    # e já grava em disco, pra próximas execuções lerem daqui em diante.
    dados = {u: dict(info) for u, info in _usuarios_web_padrao().items()}
    _salvar_usuarios(dados)
    return dados


def _salvar_usuarios(dados: dict) -> None:
    caminho = _caminho_usuarios_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar usuarios.json.")


USUARIOS_WEB: dict = _carregar_usuarios()


# ---------------------------------------------------------------------------
# Fotos de perfil
# ---------------------------------------------------------------------------
# Uma foto por login, salva como arquivo (não em base64 dentro do JSON, pra
# não inchar usuarios.json) - a própria pessoa ou um admin consegue trocar.

_EXTENSOES_FOTO_PERMITIDAS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_TAMANHO_MAXIMO_FOTO_BYTES = 3 * 1024 * 1024  # 3MB decodificado


def _pasta_fotos_usuarios() -> str:
    caminho = os.path.join(_base_path_app(), "fotos_usuarios")
    os.makedirs(caminho, exist_ok=True)
    return caminho


def _caminho_foto_usuario(usuario: str) -> Optional[str]:
    """Devolve o caminho da foto desse usuário se existir (tentando cada
    extensão suportada), ou None se a pessoa nunca subiu uma foto."""
    pasta = _pasta_fotos_usuarios()
    nome_seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", usuario)
    for ext in _EXTENSOES_FOTO_PERMITIDAS.values():
        candidato = os.path.join(pasta, nome_seguro + ext)
        if os.path.exists(candidato):
            return candidato
    return None


def _salvar_foto_usuario(usuario: str, data_url: str) -> Optional[str]:
    """Recebe uma data URL (ex: 'data:image/jpeg;base64,/9j/...'), valida
    tipo e tamanho, e salva em disco. Devolve uma mensagem de erro (str) se
    algo deu errado, ou None se salvou com sucesso."""
    m = re.match(r"^data:(image/[\w.+-]+);base64,(.+)$", data_url, re.DOTALL)
    if not m:
        return "formato de imagem inválido"
    tipo_mime, base64_dados = m.group(1), m.group(2)
    if tipo_mime not in _EXTENSOES_FOTO_PERMITIDAS:
        return f"tipo de imagem não suportado ({tipo_mime}) - use JPEG, PNG ou WEBP"

    try:
        bytes_imagem = base64.b64decode(base64_dados, validate=True)
    except Exception:
        return "não foi possível decodificar a imagem"

    if len(bytes_imagem) > _TAMANHO_MAXIMO_FOTO_BYTES:
        return f"imagem muito grande (máximo {_TAMANHO_MAXIMO_FOTO_BYTES // (1024*1024)}MB)"
    if len(bytes_imagem) == 0:
        return "imagem vazia"

    # remove qualquer foto anterior (pode ter sido salva com outra extensão)
    pasta = _pasta_fotos_usuarios()
    nome_seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", usuario)
    for ext in _EXTENSOES_FOTO_PERMITIDAS.values():
        antiga = os.path.join(pasta, nome_seguro + ext)
        if os.path.exists(antiga):
            try:
                os.remove(antiga)
            except Exception:
                pass

    extensao = _EXTENSOES_FOTO_PERMITIDAS[tipo_mime]
    caminho_novo = os.path.join(pasta, nome_seguro + extensao)
    try:
        with open(caminho_novo, "wb") as f:
            f.write(bytes_imagem)
    except Exception as e:
        logger.exception("Falha ao salvar foto de %s", usuario)
        return f"falha ao salvar: {e}"
    return None


def _calcular_resumo_horas_periodo(nome_movidesk: str, data_inicio: date, data_fim: date) -> dict:
    """Calcula horas trabalhadas, meta e tickets com ação de uma pessoa
    (pelo nome dela no Movidesk) num período específico - usado tanto
    pro mês atual quanto pra comparação com o mês anterior no perfil,
    evitando duplicar essa lógica nos dois lugares."""
    resultado = {"percentual": None, "horas": None, "meta": None, "tickets": None, "erro": None}
    resultado_horas = _consultar_horas_trabalhadas(data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d"))
    if not resultado_horas.get("ok"):
        resultado["erro"] = resultado_horas.get("erro")
        return resultado
    linhas_pessoa = [l for l in resultado_horas["linhas"] if l["analista"] == nome_movidesk]
    total_minutos = sum(l["minutos_trabalhados"] for l in linhas_pessoa)
    total_tickets = sum(l["qtd_tickets"] for l in linhas_pessoa)
    meta_minutos = resultado_horas["meta_periodo_por_analista"].get(nome_movidesk, 0)
    resultado["horas"] = _minutos_para_horas_str(total_minutos)
    resultado["meta"] = _minutos_para_horas_str(meta_minutos)
    resultado["percentual"] = round(total_minutos / meta_minutos * 100, 1) if meta_minutos > 0 else None
    resultado["tickets"] = total_tickets
    return resultado


def _nome_movidesk_vinculado(usuario_login: str) -> "tuple[Optional[str], Optional[str]]":
    """Devolve (nome_em_maiusculo, erro) da pessoa vinculada no Movidesk
    pra esse login do PDA - ou (None, None) se não tiver vínculo, ou
    (None, mensagem_erro) se o vínculo existir mas a consulta falhar."""
    info = USUARIOS_WEB.get(usuario_login, {})
    id_movidesk = info.get("usuario_movidesk_id")
    if not id_movidesk:
        return None, None
    detalhe = _buscar_usuario_movidesk(id_movidesk)
    if not detalhe.get("ok"):
        return None, detalhe.get("erro")
    nome_movidesk = str(detalhe["registro"].get("nome") or "").strip().upper()
    return (nome_movidesk or None), None


_NOMES_MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _montar_dados_perfil_mes_anterior(usuario_login: str) -> dict:
    """Mesmo resumo de horas/tickets que aparece no perfil, mas pro mês
    ANTERIOR ao atual (mês fechado por completo, sem o "corte até hoje"
    que o mês corrente tem) - usado na opção de comparação no perfil."""
    hoje = datetime.now().date()
    primeiro_dia_atual = hoje.replace(day=1)
    ultimo_dia_anterior = primeiro_dia_atual - timedelta(days=1)
    primeiro_dia_anterior = ultimo_dia_anterior.replace(day=1)

    resultado = {
        "nome_mes": f"{_NOMES_MESES_PT[primeiro_dia_anterior.month - 1]} de {primeiro_dia_anterior.year}",
        "vinculado_movidesk": bool(USUARIOS_WEB.get(usuario_login, {}).get("usuario_movidesk_id")),
        "percentual_horas_mes": None, "horas_trabalhadas_mes": None,
        "meta_horas_mes": None, "tickets_mes": None, "erro_horas": None,
    }

    nome_movidesk, erro_vinculo = _nome_movidesk_vinculado(usuario_login)
    if erro_vinculo:
        resultado["erro_horas"] = erro_vinculo
        return resultado
    if not nome_movidesk:
        return resultado

    resumo = _calcular_resumo_horas_periodo(nome_movidesk, primeiro_dia_anterior, ultimo_dia_anterior)
    resultado["percentual_horas_mes"] = resumo["percentual"]
    resultado["horas_trabalhadas_mes"] = resumo["horas"]
    resultado["meta_horas_mes"] = resumo["meta"]
    resultado["tickets_mes"] = resumo["tickets"]
    resultado["erro_horas"] = resumo["erro"]
    return resultado


def _montar_dados_perfil(usuario_login: str) -> Optional[dict]:
    """Junta as informações de perfil de uma pessoa: nome, atribuição,
    férias/day off futuros ou em andamento, % de horas trabalhadas no
    mês atual, e quantidade de tickets com ação no mês. Devolve None se
    o usuário não existir."""
    info = USUARIOS_WEB.get(usuario_login)
    if not info:
        return None

    hoje = datetime.now().date()
    primeiro_dia_mes = hoje.replace(day=1)

    dados = {
        "usuario": usuario_login,
        "nome": info.get("nome") or usuario_login,
        "atribuicao": info.get("atribuicao") or "Suporte",
        "admin": bool(info.get("admin")),
        "ativo": info.get("ativo", True),
        "tem_foto": _caminho_foto_usuario(usuario_login) is not None,
    }

    # Férias/Day Off futuros ou em andamento (a partir de hoje)
    hoje_iso = hoje.strftime("%Y-%m-%d")
    with _lock_ferias:
        periodos_pessoa = [
            dict(f) for f in FERIAS
            if f.get("usuario") == usuario_login and f.get("fim", "") >= hoje_iso
        ]
    for p in periodos_pessoa:
        p.setdefault("tipo", "ferias")
    periodos_pessoa.sort(key=lambda p: p["inicio"])
    dados["periodos_futuros"] = periodos_pessoa

    # Histórico de carreira (cargos/áreas ao longo do tempo) - do mais
    # RECENTE pro mais antigo (pedido explícito), pra ficar tipo LinkedIn
    with _lock_historico_carreira:
        historico_pessoa = [
            dict(h) for h in HISTORICO_CARREIRA if h.get("usuario") == usuario_login
        ]
    historico_pessoa.sort(key=lambda h: h["inicio"], reverse=True)
    dados["historico_carreira"] = historico_pessoa

    # % de horas trabalhadas no mês + tickets com ação - só dá pra
    # calcular se a pessoa estiver vinculada a um registro da tabela
    # usuarios (banco movidesk), já que é o "nome oficial" usado nos
    # apontamentos de horas
    id_movidesk = info.get("usuario_movidesk_id")
    dados["vinculado_movidesk"] = bool(id_movidesk)
    dados["cargo"] = None
    dados["percentual_horas_mes"] = None
    dados["horas_trabalhadas_mes"] = None
    dados["meta_horas_mes"] = None
    dados["tickets_mes"] = None
    dados["erro_horas"] = None
    dados["tickets_acao_total"] = None
    dados["primeira_atividade"] = None
    dados["total_horas_trabalhadas"] = None
    dados["erro_indicadores_gerais"] = None

    if id_movidesk:
        detalhe = _buscar_usuario_movidesk(id_movidesk)
        if detalhe.get("ok"):
            dados["cargo"] = detalhe["registro"].get("cargo") or None
            nome_movidesk = str(detalhe["registro"].get("nome") or "").strip().upper()
            if nome_movidesk:
                resumo = _calcular_resumo_horas_periodo(nome_movidesk, primeiro_dia_mes, hoje)
                dados["percentual_horas_mes"] = resumo["percentual"]
                dados["horas_trabalhadas_mes"] = resumo["horas"]
                dados["meta_horas_mes"] = resumo["meta"]
                dados["tickets_mes"] = resumo["tickets"]
                dados["erro_horas"] = resumo["erro"]

                # indicadores gerais (desde sempre, sem filtro de período) -
                # pedido explícito do solicitante: diferente do resumo acima
                # (sempre só do mês atual), esse total olha TODOS os
                # apontamentos já feitos por essa pessoa
                total_geral = _contar_tickets_acao_total(nome_movidesk)
                if total_geral.get("ok"):
                    dados["tickets_acao_total"] = total_geral["total_tickets"]
                    dados["primeira_atividade"] = total_geral["primeira_atividade"]
                    dados["total_horas_trabalhadas"] = total_geral["total_horas"]
                else:
                    dados["erro_indicadores_gerais"] = total_geral.get("erro")
        else:
            dados["erro_horas"] = detalhe.get("erro")

    return dados


# ---------------------------------------------------------------------------
# Calendário de Férias
# ---------------------------------------------------------------------------
# Registros simples de período de férias por usuário cadastrado no PDA -
# qualquer um logado pode ver, só admin pode cadastrar/remover.

def _caminho_ferias_json() -> str:
    return os.path.join(_base_path_app(), "ferias.json")


def _caminho_historico_carreira_json() -> str:
    return os.path.join(_base_path_app(), "historico_carreira.json")


def _caminho_feedbacks_usuarios_json() -> str:
    return os.path.join(_base_path_app(), "feedbacks_usuarios.json")


def _carregar_feedbacks_usuarios() -> list:
    caminho = _caminho_feedbacks_usuarios_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
        except Exception:
            logger.exception("Não foi possível ler feedbacks_usuarios.json, começando vazio.")
    return []


def _salvar_feedbacks_usuarios(dados: list) -> None:
    caminho = _caminho_feedbacks_usuarios_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar feedbacks_usuarios.json.")


def _carregar_historico_carreira() -> list:
    caminho = _caminho_historico_carreira_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
        except Exception:
            logger.exception("Não foi possível ler historico_carreira.json, começando vazio.")
    return []


def _salvar_historico_carreira(dados: list) -> None:
    caminho = _caminho_historico_carreira_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar historico_carreira.json.")


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
_proximo_id_ferias = max([f.get("id", 0) for f in FERIAS], default=0) + 1
_lock_ferias = threading.Lock()

# Histórico de carreira (cargos/áreas ao longo do tempo) exibido no
# Perfil - cada item: {id, usuario, cargo, area ("suporte"/"monitoramento"
# /""), inicio ("AAAA-MM"), fim ("AAAA-MM" ou None se for o cargo atual)}.
# lista inicial (vazia); depois disso quem manda é o historico_carreira.json.
_HISTORICO_CARREIRA_PILOTO: list = []  # sem dados de exemplo: cadastre pelo Perfil
HISTORICO_CARREIRA: list = _carregar_historico_carreira() or list(_HISTORICO_CARREIRA_PILOTO)
if not os.path.exists(_caminho_historico_carreira_json()):
    _salvar_historico_carreira(HISTORICO_CARREIRA)
_proximo_id_historico_carreira = max([h.get("id", 0) for h in HISTORICO_CARREIRA], default=0) + 1
_lock_historico_carreira = threading.Lock()

# Feedback interno sobre a pessoa - DIFERENTE de tudo mais no perfil: o
# PRÓPRIO USUÁRIO NUNCA VÊ isso, nem sendo admin vendo o próprio perfil.
# Só é visível/editável por admins da MESMA equipe (mesma "atribuicao":
# Suporte ou Monitoramento) da pessoa que está sendo vista - pedido
# explícito do solicitante (feedback de gestão, não é algo do funcionário ver).
FEEDBACKS_USUARIOS: list = _carregar_feedbacks_usuarios()
_proximo_id_feedback_usuario = max([f.get("id", 0) for f in FEEDBACKS_USUARIOS], default=0) + 1
_lock_feedbacks_usuarios = threading.Lock()


ATRIBUICAO_AMBAS = "Suporte e Monitoramento"


def _equipes_da_pessoa(atribuicao: str) -> set:
    """Devolve o conjunto de equipes que essa atribuição cobre - a
    maioria das pessoas cobre só uma, mas quem tem escala 12x36 pode
    cobrir as duas (ex.: duas pessoas de exemplo, pedido do solicitante em 08/09/2026).
    Usado em qualquer lugar que precisa comparar/filtrar por equipe, pra
    "Suporte e Monitoramento" sempre bater com as duas."""
    if atribuicao == ATRIBUICAO_AMBAS:
        return {"Suporte", "Monitoramento"}
    return {atribuicao or "Suporte"}


def _pertence_a_equipe(atribuicao: str, equipe_filtro: str) -> bool:
    """True se `atribuicao` cobre `equipe_filtro` - ou porque é
    exatamente igual, ou porque a pessoa está em "Suporte e
    Monitoramento" (cobre as duas)."""
    return equipe_filtro in _equipes_da_pessoa(atribuicao)


def _tem_acesso_feedback_usuario(sessao: dict, usuario_perfil: str) -> bool:
    """Qualquer admin vê/insere feedback de QUALQUER pessoa, de qualquer
    equipe (Suporte ou Monitoramento) - pedido do solicitante em 11/09/2026,
    removendo a restrição de "mesma equipe" que existia antes. Só
    continua vetado sobre si mesmo - feedback é sempre sobre OUTRA
    pessoa, a própria pessoa nunca vê/insere feedback dela mesma, nem
    sendo admin."""
    if sessao["usuario"] == usuario_perfil:
        return False
    return bool(sessao.get("admin"))


def _periodos_se_sobrepoem(inicio1: str, fim1: str, inicio2: str, fim2: str) -> bool:
    return inicio1 <= fim2 and inicio2 <= fim1


# ---------------------------------------------------------------------------
# String Connections - registro de strings de conexão reutilizáveis, por
# cliente + produto (ex.: "Vivo" + "NFCom", "Nissei" + "NFe"). Usado na
# Manutenção de Alertas em Banco pra não precisar digitar/colar a mesma
# string de conexão toda vez que um novo alerta é criado pro mesmo cliente -
# só admin mexe aqui, mas qualquer pessoa com acesso à Manutenção de Alertas
# (admin ou view com a permissão extra) pode ESCOLHER uma já cadastrada na
# hora de criar/editar um alerta.
# Guardado localmente (string_connections.json, mesmo padrão do
# usuarios.json) - não fica na tabela CONFIGURACOES_ALERTA do banco de
# monitoramento, só alimenta o campo CONEXAO na hora de criar/editar.
# ---------------------------------------------------------------------------


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


STRING_CONNECTIONS: dict = _carregar_string_connections()
_proximo_id_string_connection = max([int(k) for k in STRING_CONNECTIONS], default=0) + 1


# ---------------------------------------------------------------------------
# Manutenção de Usuários (Beta) - cadastro/desativação de usuário
# administrador em produção, nos bancos de cada cliente
# ---------------------------------------------------------------------------
# Porta pro PDA da ferramenta desktop "QG de Manutenção de Usuário"
# (Tkinter, standalone) que o solicitante já usava - mesma lógica de negócio
# (config.py + service.py + security.py de lá), só trocando a UI Tkinter
# pelas rotas web e reaproveitando os helpers de banco que o PDA já tem
# (core.db_utils) em vez da classe DatabaseRepository própria que o
# original tinha.
#
# Config trazida como arquivos PRÓPRIOS (pedido explícito - futuramente
# a ideia é unificar tudo num .env só, mas por enquanto fica separado):
#   - manutencao_usuarios_bases.json  (área -> tenant -> produto -> banco)
#   - .env.manutencao_usuarios.shared        (queries, comuns a todas as áreas)
#   - .env.manutencao_usuarios.suporte       (credenciais de conexão, área Suporte)
#   - .env.manutencao_usuarios.monitoramento (credenciais de conexão, área Monitoramento)
# Nomeados assim (em vez de ".env.suporte"/".env.monitoramento" como no
# projeto original) porque o PDA JÁ TINHA um ".env.monitoramento" próprio
# pra outra coisa (banco de monitoramento interno) - colidiria.
MANUTENCAO_USUARIOS_AREAS = ("suporte", "monitoramento")
# A senha padrão dos cadastros novos NÃO fica no código (repositório público):
# vem de PDA_SENHA_PADRAO_NOVOS_USUARIOS. O placeholder abaixo só aparece na
# tela; qualquer fluxo que ENVIA a senha pra fora exige a variável definida.
_SENHA_PADRAO_PLACEHOLDER = "<senha-padrao>"
MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL = os.environ.get("PDA_SENHA_PADRAO_NOVOS_USUARIOS", _SENHA_PADRAO_PLACEHOLDER)


def _exigir_senha_padrao_configurada() -> None:
    if MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL == _SENHA_PADRAO_PLACEHOLDER:
        raise RuntimeError("Defina a variável de ambiente PDA_SENHA_PADRAO_NOVOS_USUARIOS antes de cadastrar usuários.")

MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS = {
    "NFe": (
        "db_nfe_insert_emis1", "db_nfe_insert_emis2", "db_nfe_insert_dest1", "db_nfe_insert_dest2",
        "db_nfe_insert_trans1", "db_nfe_insert_trans2", "db_nfe_insert_oper",
    ),
    "NFe2": (
        "db_nfe2_insert_emis1", "db_nfe2_insert_emis2", "db_nfe2_insert_dest1", "db_nfe2_insert_dest2",
        "db_nfe2_insert_trans1", "db_nfe2_insert_trans2", "db_nfe2_insert_oper",
    ),
    "NFCe": (
        "db_nfce_insert_emis1", "db_nfce_insert_emis2", "db_nfce_insert_dest1", "db_nfce_insert_dest2",
        "db_nfce_insert_trans1", "db_nfce_insert_trans2", "db_nfce_insert_oper",
    ),
}
MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS = {"CTe", "CTe2", "NFSeOut"}
MANUTENCAO_USUARIOS_FIXED_MDFE_ROLES = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
MANUTENCAO_USUARIOS_SUPPORTED_PRODUCTS = (
    set(MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS) | MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS | {"MDFe", "NFSeIn"}
)

# mesmo padrão de caracteres proibidos do app original (evita quebrar as
# queries parametrizadas com caractere estranho no nome/login)
_MANUTENCAO_USUARIOS_CARACTERES_INVALIDOS = re.compile(r"[\[\]{}!#$%¨&*()+='\"\\|?/;,:]")

_manutencao_usuarios_bases_cache: Optional[dict] = None
_manutencao_usuarios_env_cache: dict = {}


class ManutencaoUsuariosConfigError(RuntimeError):
    pass


class ManutencaoUsuariosSkip(RuntimeError):
    """Motivo de SKIP visível pro operador (ex.: usuário já existe,
    usuário não encontrado) - diferente de um erro de banco de verdade."""
    pass


def _manutencao_usuarios_sanitize(mensagem: object) -> str:
    """Porta de security.sanitize_message do projeto original - nunca
    deixa senha/PWD vazar pra mensagem de resultado ou log de auditoria,
    mesmo que apareça dentro de uma exceção de conexão do pyodbc."""
    texto = str(mensagem)
    for padrao in (
        re.compile(r"(PWD|PASSWORD|SENHA)\s*=\s*[^;,\s]+", re.IGNORECASE),
        re.compile(r"(db_password_[A-Za-z0-9_]+)\s*=\s*[^\s]+", re.IGNORECASE),
    ):
        texto = padrao.sub(lambda m: f"{m.group(1)}=<oculto>", texto)
    return texto.replace("\r", " ").replace("\n", " ").strip()


def _carregar_manutencao_usuarios_bases() -> dict:
    global _manutencao_usuarios_bases_cache
    if _manutencao_usuarios_bases_cache is not None:
        return _manutencao_usuarios_bases_cache
    caminho = os.path.join(_base_path_app(), "manutencao_usuarios_bases.json")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as exc:
        raise ManutencaoUsuariosConfigError(f"Falha ao carregar manutencao_usuarios_bases.json: {exc}") from exc

    if not isinstance(dados, dict):
        raise ManutencaoUsuariosConfigError("manutencao_usuarios_bases.json precisa conter um objeto JSON.")
    for area in MANUTENCAO_USUARIOS_AREAS:
        if area not in dados or not isinstance(dados[area], dict):
            raise ManutencaoUsuariosConfigError(f"Área obrigatória ausente em manutencao_usuarios_bases.json: {area}")
        for tenant, produtos in dados[area].items():
            if not isinstance(tenant, str) or not isinstance(produtos, dict):
                raise ManutencaoUsuariosConfigError(f"Tenant inválido em manutencao_usuarios_bases.json: {tenant}")
            for produto, database in produtos.items():
                if not isinstance(produto, str) or not isinstance(database, str) or not database:
                    raise ManutencaoUsuariosConfigError(
                        f"Produto/banco inválido em manutencao_usuarios_bases.json: {tenant}/{produto}"
                    )
    _manutencao_usuarios_bases_cache = dados
    return dados


def _manutencao_usuarios_build_targets(areas: tuple) -> list:
    """Monta a lista de alvos (área, tenant, produto, banco) pras áreas
    pedidas - mesmo formato de "target" do projeto original, só que como
    dict em vez de dataclass Target (padrão já usado no resto do PDA)."""
    bases = _carregar_manutencao_usuarios_bases()
    targets = []
    for area in areas:
        for tenant, produtos in bases.get(area, {}).items():
            for produto, database in produtos.items():
                targets.append({"area": area, "tenant": tenant, "produto": produto, "database": database})
    return targets


def _manutencao_usuarios_load_env(area: str) -> dict:
    if area in _manutencao_usuarios_env_cache:
        return _manutencao_usuarios_env_cache[area]

    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seções
    # [manutencao_usuarios_shared] + [manutencao_usuarios_{area}]) - cai
    # pros dois .env.manutencao_usuarios.* tradicionais se QUALQUER uma
    # das duas seções não existir lá (arquivo ainda não migrado nessa
    # máquina, ver core/config_central.py).
    shared_central = _obter_secao_central("manutencao_usuarios_shared")
    area_central = _obter_secao_central(f"manutencao_usuarios_{area}")
    if shared_central and area_central:
        resultado = {**shared_central, **area_central}
        _manutencao_usuarios_env_cache[area] = resultado
        return resultado

    base = _base_path_app()
    caminho_shared = os.path.join(base, ".env.manutencao_usuarios.shared")
    caminho_area = os.path.join(base, f".env.manutencao_usuarios.{area}")
    if not os.path.exists(caminho_shared):
        raise ManutencaoUsuariosConfigError("Arquivo de configuração não encontrado: .env.manutencao_usuarios.shared")
    if not os.path.exists(caminho_area):
        raise ManutencaoUsuariosConfigError(f"Arquivo de configuração não encontrado: .env.manutencao_usuarios.{area}")
    shared = dotenv_values(caminho_shared)
    valores_area = dotenv_values(caminho_area)
    merged = {**shared, **valores_area}
    resultado = {k: v for k, v in merged.items() if v is not None}
    _manutencao_usuarios_env_cache[area] = resultado
    return resultado


def _manutencao_usuarios_credenciais(area: str, tenant: str) -> list:
    """Devolve uma LISTA de candidatos de conexão pro tenant - normalmente
    só 1 (o principal), mas pode ter um 2º candidato "_fallback" (ex.:
    tenant com 2 servidores válidos, caso do accor em 04/09/2026 - pedido
    do solicitante) que só é tentado se o principal falhar ao conectar."""
    env = _manutencao_usuarios_load_env(area)

    def montar(sufixo: str) -> Optional[dict]:
        server = (env.get(f"db_server_{tenant}{sufixo}") or "").strip()
        user = (env.get(f"db_user_{tenant}{sufixo}") or "").strip()
        password = (env.get(f"db_password_{tenant}{sufixo}") or "").strip()
        if not (server and user and password):
            return None
        return {"server": server, "user": user, "password": password}

    principal = montar("")
    if not principal:
        faltando = [
            chave for chave, valor in {
                f"db_server_{tenant}": env.get(f"db_server_{tenant}"),
                f"db_user_{tenant}": env.get(f"db_user_{tenant}"),
                f"db_password_{tenant}": env.get(f"db_password_{tenant}"),
            }.items() if not (valor or "").strip()
        ]
        raise ManutencaoUsuariosConfigError(f"Credenciais ausentes: {', '.join(faltando)}")

    candidatos = [principal]
    fallback = montar("_fallback")
    if fallback:
        candidatos.append(fallback)
    return candidatos


def _manutencao_usuarios_query(area: str, key: str) -> str:
    valor = (_manutencao_usuarios_load_env(area).get(key) or "").strip()
    if not valor:
        raise ManutencaoUsuariosConfigError(f"Query ausente: {key}")
    return valor


def _manutencao_usuarios_prefix(produto: str) -> str:
    return f"db_{produto.lower()}"


def _manutencao_usuarios_permission_query_keys(produto: str) -> list:
    if produto in MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS:
        return list(MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS[produto])
    if produto in MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS:
        prefix = _manutencao_usuarios_prefix(produto)
        return [f"{prefix}_select_max_role", f"{prefix}_insert_permis"]
    if produto == "MDFe":
        return ["db_mdfe_insert_permis"]
    return []


def _manutencao_usuarios_validate_required_queries(area: str, produto: str, action: str) -> None:
    prefix = _manutencao_usuarios_prefix(produto)
    required = [f"{prefix}_select_id"]
    if action == "cad":
        required.extend([f"{prefix}_select_login", f"{prefix}_insert_usuar"])
        required.extend(_manutencao_usuarios_permission_query_keys(produto))
    else:
        required.append(f"{prefix}_delete")
    for key in required:
        _manutencao_usuarios_query(area, key)


def _manutencao_usuarios_find_user_id(conn, area: str, produto: str, nome: str, login: str, missing_message: str) -> int:
    query = _manutencao_usuarios_query(area, f"{_manutencao_usuarios_prefix(produto)}_select_id")
    linhas, _colunas = executar_query(conn, query, params=(nome, login), fetch=True, raise_on_error=True)
    if not linhas:
        raise ManutencaoUsuariosSkip(missing_message)
    return int(linhas[0][0])


def _manutencao_usuarios_max_role(conn, area: str, produto: str) -> int:
    query = _manutencao_usuarios_query(area, f"{_manutencao_usuarios_prefix(produto)}_select_max_role")
    linhas, _colunas = executar_query(conn, query, fetch=True, raise_on_error=True)
    if not linhas:
        raise ManutencaoUsuariosSkip("Não foi possível coletar as permissões do produto.")
    return int(linhas[0][0])


def _manutencao_usuarios_grant_permissions(conn, area: str, produto: str, user_id: int) -> None:
    if produto in MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS:
        for key in MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS[produto]:
            executar_query(conn, _manutencao_usuarios_query(area, key), params=user_id, raise_on_error=True)
        return
    if produto in MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS:
        max_role = _manutencao_usuarios_max_role(conn, area, produto)
        query = _manutencao_usuarios_query(area, f"{_manutencao_usuarios_prefix(produto)}_insert_permis")
        for role in range(1, max_role + 1):
            executar_query(conn, query, params=(role, user_id), raise_on_error=True)
        return
    if produto == "MDFe":
        query = _manutencao_usuarios_query(area, "db_mdfe_insert_permis")
        for role in MANUTENCAO_USUARIOS_FIXED_MDFE_ROLES:
            executar_query(conn, query, params=(role, user_id), raise_on_error=True)


def _manutencao_usuarios_register(conn, area: str, produto: str, nome: str, login: str) -> str:
    prefix = _manutencao_usuarios_prefix(produto)
    select_login = _manutencao_usuarios_query(area, f"{prefix}_select_login")
    duplicadas, _colunas = executar_query(conn, select_login, params=login, fetch=True, raise_on_error=True)
    if duplicadas:
        raise ManutencaoUsuariosSkip("Usuário já existe neste produto.")

    executar_query(
        conn, _manutencao_usuarios_query(area, f"{prefix}_insert_usuar"),
        params=(nome, login), raise_on_error=True,
    )
    user_id = _manutencao_usuarios_find_user_id(
        conn, area, produto, nome, login, "Não foi possível localizar o ID do usuário."
    )
    _manutencao_usuarios_grant_permissions(conn, area, produto, user_id)
    return "Cadastro realizado."


def _manutencao_usuarios_deactivate(conn, area: str, produto: str, nome: str, login: str) -> str:
    prefix = _manutencao_usuarios_prefix(produto)
    user_id = _manutencao_usuarios_find_user_id(conn, area, produto, nome, login, "Usuário não encontrado.")
    executar_query(conn, _manutencao_usuarios_query(area, f"{prefix}_delete"), params=user_id, raise_on_error=True)
    return "Desativação realizada."


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


def _movidesk_api_buscar_pessoa_por_username(login: str) -> Optional[dict]:
    """Busca a pessoa no Movidesk pelo userName (login/e-mail) via API,
    pra achar o GUID dela - necessário pra DESATIVAR (a API pede o id,
    não o userName), já que a tabela SQL 'usuarios' que o PDA já usa não
    guarda esse GUID (só um id numérico próprio, diferente)."""
    token = _movidesk_api_token()
    resposta = requests.get(
        MOVIDESK_API_BASE,
        params={"token": token, "$filter": f"userName eq '{login}'"},
        timeout=20,
    )
    resposta.raise_for_status()
    resultado = resposta.json()
    if isinstance(resultado, list) and resultado:
        return resultado[0]
    return None


def _movidesk_api_criar_pessoa(nome: str, login: str, area_valor: str, operador: str) -> dict:
    """Cria a pessoa no Movidesk via API - senha inicial e demais valores
    fixos seguem o mesmo padrão dos cadastros em banco (mesma senha
    padrão exibida na tela, mesmo texto de 'oriente a trocar')."""
    _exigir_senha_padrao_configurada()
    token = _movidesk_api_token()
    access_profile = MOVIDESK_AREA_PARA_ACCESS_PROFILE.get(area_valor, "MONITORAMENTO")
    teams = MOVIDESK_AREA_PARA_TEAMS.get(area_valor, ["MONITORAMENTO"])
    corpo = {
        "isActive": True,
        "personType": 1,
        "profileType": 1,
        "accessProfile": access_profile,
        "businessName": nome,
        "userName": login,
        "password": MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL,
        "role": "Assistente",
        "cultureId": "pt-BR",
        "timeZoneId": "America/Sao_Paulo",
        "observations": f"Usuário criado via PDA (Manutenção de Usuários) por {operador} em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
        "emails": [{"emailType": "Profissional", "email": login, "isDefault": True}],
        "teams": teams,
    }
    resposta = requests.post(
        MOVIDESK_API_BASE, params={"token": token}, json=corpo, timeout=30,
    )
    resposta.raise_for_status()
    return resposta.json()


def _movidesk_api_desativar_pessoa(person_id: str) -> None:
    token = _movidesk_api_token()
    resposta = requests.patch(
        MOVIDESK_API_BASE, params={"token": token, "id": person_id},
        json={"isActive": False}, timeout=20,
    )
    resposta.raise_for_status()


def _manutencao_usuarios_execute_movidesk(action: str, nome: str, login: str, area_valor: str, operador: str) -> dict:
    """Roda o cadastro/desativação da PESSOA no Movidesk via API - formato
    de retorno igual ao de um "alvo" de banco (area/tenant/produto/
    database/status/message), pra entrar na mesma tabela de prévia e de
    resultado sem precisar de UI separada."""
    linha_base = {"area": area_valor, "tenant": "Movidesk", "produto": "Pessoa (API)", "database": "(via API pública)"}
    try:
        if action == "cad":
            resultado = _movidesk_api_criar_pessoa(nome, login, area_valor, operador)
            person_id = resultado.get("id", "?")
            return {**linha_base, "status": "success", "message": f"Pessoa criada no Movidesk (id {person_id})."}
        else:
            pessoa = _movidesk_api_buscar_pessoa_por_username(login)
            if not pessoa:
                return {**linha_base, "status": "skipped", "message": "Pessoa não encontrada no Movidesk pelo login informado."}
            if pessoa.get("isActive") is False:
                return {**linha_base, "status": "skipped", "message": "Pessoa já estava desativada no Movidesk."}
            _movidesk_api_desativar_pessoa(pessoa["id"])
            return {**linha_base, "status": "success", "message": f"Pessoa desativada no Movidesk (id {pessoa['id']})."}
    except ManutencaoUsuariosConfigError as exc:
        return {**linha_base, "status": "skipped", "message": _manutencao_usuarios_sanitize(exc)}
    except requests.exceptions.RequestException as exc:
        return {**linha_base, "status": "error", "message": f"Falha na API do Movidesk: {_manutencao_usuarios_sanitize(exc)}"}
    except Exception as exc:
        logger.exception("Erro inesperado na integração Movidesk (Manutenção de Usuários)")
        return {**linha_base, "status": "error", "message": _manutencao_usuarios_sanitize(exc)}


def _manutencao_usuarios_verificar_target(login: str, target: dict) -> dict:
    """SÓ CONSULTA (nunca insere/desativa nada) se `login` já existe no
    banco desse alvo - reaproveita a MESMA query de checagem de
    duplicidade (`{prefix}_select_login`) que o cadastro já usa pra
    evitar duplicar usuário, só que aqui é sempre somente-leitura. Usado
    pelo modo "Diagnóstico" (cruzamento de usuários) - pedido explícito
    do solicitante de ver, pra uma pessoa só, em quais bancos ela existe.
    status "success" = existe nesse banco, "skipped" = não existe (não é
    um erro, só informação), "error" = não deu pra nem checar."""
    produto = target["produto"]
    area = target["area"]
    linha_base = dict(target)
    if produto not in MANUTENCAO_USUARIOS_SUPPORTED_PRODUCTS:
        return {**linha_base, "status": "skipped", "message": "Produto ainda não suportado nesse diagnóstico."}

    try:
        prefix = _manutencao_usuarios_prefix(produto)
        query = _manutencao_usuarios_query(area, f"{prefix}_select_login")
        candidatos = _manutencao_usuarios_credenciais(area, target["tenant"])
    except ManutencaoUsuariosConfigError as exc:
        return {**linha_base, "status": "error", "message": _manutencao_usuarios_sanitize(exc)}

    conn = None
    for credenciais in candidatos:
        conn = conectar_banco(
            credenciais["server"], target["database"], credenciais["user"], credenciais["password"],
            raise_on_error=False,
        )
        if conn:
            break
    if not conn:
        return {**linha_base, "status": "error", "message": f"Falha ao conectar no banco {target['database']}"}
    try:
        linhas, _colunas = executar_query(conn, query, params=login, fetch=True, raise_on_error=True)
        if linhas:
            return {**linha_base, "status": "success", "message": "Encontrado nesse banco."}
        return {**linha_base, "status": "skipped", "message": "Não encontrado."}
    except Exception as exc:
        return {**linha_base, "status": "error", "message": _manutencao_usuarios_sanitize(exc)}
    finally:
        fechar_conexao(conn)


def _manutencao_usuarios_diagnostico(login: str) -> dict:
    """Cruza, pra UM login só: vínculo com o Movidesk (via API) e
    presença em TODOS os bancos de cliente (suporte + monitoramento de
    uma vez) - o "cruzamento de usuários" pedido pelo solicitante. Roda os
    ~33 bancos em paralelo (ThreadPoolExecutor) - em sequência (como o
    cadastro/desativação fazem, um por um, de propósito pra não
    sobrecarregar) ficaria bem mais lento pra uma consulta que é só
    diagnóstico, sem gravar nada."""
    targets = _manutencao_usuarios_build_targets(MANUTENCAO_USUARIOS_AREAS)
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados_bancos = list(executor.map(
            lambda t: _manutencao_usuarios_verificar_target(login, t), targets,
        ))
    resultados_bancos.sort(key=lambda r: (r["area"], r["tenant"], r["produto"]))

    pessoa_movidesk = None
    erro_movidesk = None
    try:
        pessoa_movidesk = _movidesk_api_buscar_pessoa_por_username(login)
    except ManutencaoUsuariosConfigError as exc:
        erro_movidesk = _manutencao_usuarios_sanitize(exc)
    except requests.exceptions.RequestException as exc:
        erro_movidesk = f"Falha na API do Movidesk: {_manutencao_usuarios_sanitize(exc)}"
    except Exception as exc:
        logger.exception("Erro inesperado ao consultar Movidesk no Diagnóstico")
        erro_movidesk = _manutencao_usuarios_sanitize(exc)

    return {
        "resultados_bancos": resultados_bancos,
        "movidesk": pessoa_movidesk,
        "erro_movidesk": erro_movidesk,
    }


# ---------------------------------------------------------------------------
# E-mail de boas-vindas - pedido do solicitante em 06/09/2026, com disparo
# opcional já embutido no Cadastro (checkbox) desde 07/09/2026.
# ---------------------------------------------------------------------------
LINK_PDA_WEB = os.environ.get("PDA_LINK_WEB", "http://localhost:8765/")


def _config_email_boas_vindas() -> dict:
    """Credenciais SMTP DEDICADAS ao e-mail de boas-vindas (conta própria
    suporte@example.com) - CREDENCIAIS_CENTRALIZADAS.env primeiro
    (seção [boas_vindas_email]), cai pro .env.boas_vindas tradicional se
    essa seção não existir. Propositalmente SEPARADA de
    _config_email_sistema() (usada pelos alertas legados, conta
    avisos@example.com...) - contas diferentes, credenciais diferentes."""
    valores = _obter_config_hibrido(
        "boas_vindas_email", ".env.boas_vindas",
        ["smtp_server", "smtp_port", "email_from", "email_password"],
    )
    return {
        "smtp_server": valores["smtp_server"],
        "smtp_port": valores["smtp_port"],
        "email_from": valores["email_from"],
        "email_password": _obter_valor_config("boas_vindas::email_password", valores["email_password"]),
    }


def _montar_email_boas_vindas_html(nome: str, login: str, senha: str) -> str:
    """E-mail de boas-vindas pro novo colaborador - avisa que esse é o
    acesso ao PDA, traz o link direto, os dados de acesso (login/senha)
    que o solicitante acabou de cadastrar, e avisa que só funciona dentro da
    VPN da empresa. UMA caixa de credenciais só - login e senha são o
    MESMO acesso (pedido explícito do solicitante em 07/09/2026, não dois
    acessos separados). Sem o parágrafo "qualquer dúvida, acione o solicitante
    e a supervisão" (removido em 07/09/2026) - o rodapé com "Desenvolvido
    por" já deixa claro quem procurar."""
    primeiro_nome = (nome or "").strip().split(" ")[0] or "tudo bem"

    caixa_credenciais = f"""
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 18px 0;">
              <p style="font-size:11px; color:#2db8cf; text-transform:uppercase; letter-spacing:.04em; font-weight:700; margin:0 0 10px 0;">Dados de acesso</p>
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Login: <b>{login}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0;">Senha: <b>{senha}</b></p>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">
              Seja bem-vindo(a), {primeiro_nome}! 🎉
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 16px 0;">
              Este é o seu acesso ao <b style="color:#2db8cf;">PDA - Painel de Automações</b>, a ferramenta
              interna que a equipe de Suporte e Monitoramento usa no dia a dia.
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              As informações sobre como usar a ferramenta, os recursos disponíveis e o que muda na sua rotina
              serão passadas diretamente pela equipe nos próximos passos.
            </p>
            {caixa_credenciais}
            <p style="font-size:11.5px; color:#8b98a5; margin:-6px 0 20px 0; line-height:1.6;">
              Por segurança, troque essa senha assim que possível.
            </p>
            <div style="text-align:center; margin:28px 0;">
              <a href="{LINK_PDA_WEB}" style="display:inline-block; background:linear-gradient(135deg, #2db8cf, #b0cb1c); color:#08090c; font-weight:700; font-size:14px; text-decoration:none; padding:13px 28px; border-radius:9px;">
                Acessar o PDA
              </a>
              <p style="font-size:11.5px; color:#8b98a5; margin:12px 0 0 0;">
                <a href="{LINK_PDA_WEB}" style="color:#2db8cf; text-decoration:none;">{LINK_PDA_WEB}</a>
              </p>
            </div>
            <div style="background:rgba(241,76,76,.08); border:1px solid rgba(241,76,76,.25); border-radius:9px; padding:12px 16px; margin:0 0 24px 0;">
              <p style="font-size:12.5px; color:#ff9d9d; margin:0; line-height:1.6;">
                ⚠️ O PDA só é acessível de <b>dentro da VPN da empresa</b>. Fora da VPN, o link não vai abrir.
              </p>
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0;">Desenvolvido pela equipe do PDA</p>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _enviar_email_boas_vindas(nome: str, email_destino: str, login: str, senha: str) -> None:
    """Levanta exceção em caso de falha - quem chama decide como reportar
    (a rota converte isso num JSON de erro pro operador ver na hora).

    `email_destino` (pra ONDE o e-mail vai) e `login` (o que aparece
    escrito como "Login" DENTRO do e-mail) são coisas DIFERENTES - erro
    corrigido em 07/09/2026: no botão de teste (aba Editar usuários), o
    e-mail pessoal cadastrado estava sendo usado como as duas coisas,
    mostrando o e-mail pessoal como se fosse o login de acesso, quando
    o login de verdade é o usuário do PDA (o mesmo da aba Usuários)."""
    smtp_info = _config_email_boas_vindas()
    corpo_html = _montar_email_boas_vindas_html(nome, login, senha)
    enviar_email(
        destinatario=email_destino,
        assunto="Bem-vindo(a) ao PDA - Painel de Automações",
        corpo=corpo_html,
        smtp_info=smtp_info,
        raise_on_error=True,
    )


# ---------------------------------------------------------------------------
# Alertas de 45/90 dias de empresa - pedido do solicitante em 10/09/2026. Roda
# uma vez por dia (não precisa ser mais frequente que isso) e avisa os 4
# destinatários fixos quando alguém está chegando perto de completar 45
# ou 90 dias de casa, pra dar tempo de organizar o feedback.
# ---------------------------------------------------------------------------
MARCOS_TEMPO_EMPRESA = (45, 90)
DIAS_ANTECEDENCIA_ALERTA_TEMPO_EMPRESA = 5  # avisa de X dias antes até o dia exato
def _lista_emails_env(nome: str) -> list:
    return [e.strip() for e in os.environ.get(nome, "").split(",") if e.strip()]


# Destinatários vêm de variável de ambiente (e-mails separados por vírgula) -
# nenhum endereço real fica no código. Vazio = ninguém é notificado.
DESTINATARIOS_ALERTA_TEMPO_EMPRESA = _lista_emails_env("PDA_DESTINATARIOS_TEMPO_EMPRESA")

# O alerta de feedback/alinhamento notifica os mesmos + extras opcionais.
DESTINATARIOS_ALERTA_FEEDBACK = DESTINATARIOS_ALERTA_TEMPO_EMPRESA + _lista_emails_env("PDA_DESTINATARIOS_FEEDBACK_EXTRAS")


def _caminho_alertas_tempo_empresa_json() -> str:
    return os.path.join(_base_path_app(), "alertas_tempo_empresa_enviados.json")


def _carregar_alertas_tempo_empresa_enviados() -> set:
    """Conjunto de "usuario|marco" já notificados - pra nunca mandar o
    mesmo aviso duas vezes (o job roda todo dia, então sem isso a pessoa
    receberia o mesmo e-mail repetido todo dia dentro da janela de
    antecedência)."""
    caminho = _caminho_alertas_tempo_empresa_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return set(dados)
        except Exception:
            logger.exception("Não foi possível ler alertas_tempo_empresa_enviados.json.")
    return set()


def _salvar_alertas_tempo_empresa_enviados(enviados: set) -> None:
    caminho = _caminho_alertas_tempo_empresa_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(sorted(enviados), f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar alertas_tempo_empresa_enviados.json.")


def _cargo_mais_recente(usuario: str) -> str:
    """Cargo atual da pessoa (última entrada do histórico de carreira,
    fim=None ou a mais recente por início) - "-" se não tiver nada
    cadastrado pra ela."""
    entradas = [h for h in HISTORICO_CARREIRA if h.get("usuario") == usuario]
    if not entradas:
        return "-"
    entradas.sort(key=lambda h: h.get("inicio") or "", reverse=True)
    return entradas[0].get("cargo") or "-"


def _montar_email_tempo_empresa_html(nome: str, cargo: str, data_inicio_str: str, marco_dias: int) -> str:
    """Mesma identidade visual do e-mail de boas-vindas (gradiente
    teal/lime, cabeçalho PDA) - avisa os destinatários fixos que uma
    pessoa está chegando (ou já chegou) nos 45/90 dias de empresa."""
    try:
        data_fmt = datetime.strptime(data_inicio_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        data_fmt = data_inicio_str
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">
              📌 {marco_dias} dias de casa se aproximando
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              <b style="color:#2db8cf;">{nome}</b> está completando <b>{marco_dias} dias</b> de empresa e
              precisa de um feedback.
            </p>
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 20px 0;">
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Cargo: <b>{cargo}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0;">Data de início: <b>{data_fmt}</b></p>
            </div>
            <p style="font-size:13px; color:#8b98a5; line-height:1.6; margin:0;">
              Esse aviso é automático, gerado pelo PDA - Painel de Automações.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0;">Desenvolvido pela equipe do PDA</p>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _executar_alertas_tempo_de_empresa() -> None:
    """Roda 1x por dia - pra cada usuário ATIVO com data_inicio preenchida,
    confere se está a até DIAS_ANTECEDENCIA_ALERTA_TEMPO_EMPRESA dias de
    completar 45 ou 90 dias de empresa. Manda pros 4 destinatários fixos,
    UMA vez só por (usuário, marco) - controlado por
    alertas_tempo_empresa_enviados.json."""
    hoje = date.today()
    ja_enviados = _carregar_alertas_tempo_empresa_enviados()
    enviados_agora = set()

    for usuario, info in USUARIOS_WEB.items():
        if info.get("ativo") is False:
            continue
        data_inicio_str = info.get("data_inicio")
        if not data_inicio_str:
            continue
        try:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        dias_na_empresa = (hoje - data_inicio).days
        if dias_na_empresa < 0:
            continue

        for marco in MARCOS_TEMPO_EMPRESA:
            chave = f"{usuario}|{marco}"
            if chave in ja_enviados:
                continue
            dias_restantes = marco - dias_na_empresa
            if not (0 <= dias_restantes <= DIAS_ANTECEDENCIA_ALERTA_TEMPO_EMPRESA):
                continue

            nome = info.get("nome") or usuario
            cargo = _cargo_mais_recente(usuario)
            corpo_html = _montar_email_tempo_empresa_html(nome, cargo, data_inicio_str, marco)
            try:
                smtp_info = _config_email_boas_vindas()
                for destinatario in DESTINATARIOS_ALERTA_TEMPO_EMPRESA:
                    enviar_email(
                        destinatario=destinatario,
                        assunto=f"{nome} está completando {marco} dias de empresa",
                        corpo=corpo_html,
                        smtp_info=smtp_info,
                        raise_on_error=True,
                    )
                logger.info(
                    "Alerta de %d dias de empresa enviado pra '%s' (%s destinatário(s)).",
                    marco, usuario, len(DESTINATARIOS_ALERTA_TEMPO_EMPRESA),
                )
                enviados_agora.add(chave)
            except Exception:
                logger.exception(
                    "Falha ao enviar alerta de %d dias de empresa pra '%s' - tenta de novo amanhã.",
                    marco, usuario,
                )
                # NÃO marca como enviado - assim tenta de novo no próximo
                # dia (ainda dentro da janela de antecedência)

    if enviados_agora:
        _salvar_alertas_tempo_empresa_enviados(ja_enviados | enviados_agora)


def _montar_email_feedback_inserido_html(autor_nome: str, tipo: str, data_str: str, usuario_recebido: str, nome_recebido: str) -> str:
    """Aviso pros destinatários fixos sempre que um Feedback ou
    Alinhamento é inserido - resumo (quem deu, quando, quem recebeu),
    mesma identidade visual do resto dos e-mails do PDA. Sem o TEXTO do
    feedback em si de propósito (é sensível/privado - só quem já tem
    acesso no PDA deveria ler o conteúdo completo)."""
    verbo = "um Alinhamento" if tipo == "Alinhamento" else "um Feedback"
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">
              📝 Novo {tipo.lower()} registrado
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              <b style="color:#2db8cf;">{autor_nome}</b> inseriu {verbo} sobre
              <b style="color:#b0cb1c;">{nome_recebido}</b>.
            </p>
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 20px 0;">
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Tipo: <b>{tipo}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Data: <b>{data_str}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">De: <b>{autor_nome}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0;">Para: <b>{nome_recebido}</b></p>
            </div>
            <p style="font-size:13px; color:#8b98a5; line-height:1.6; margin:0;">
              Mais informações estão disponíveis no PDA, no perfil de {nome_recebido}. Esse aviso é
              automático e não traz o conteúdo completo por ser uma informação restrita.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0;">Desenvolvido pela equipe do PDA</p>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _notificar_feedback_inserido(autor_nome: str, tipo: str, criado_em: str, usuario_recebido: str, nome_recebido: str) -> None:
    """Dispara em background o aviso pros destinatários fixos - NUNCA deve
    derrubar o cadastro do feedback em si (por isso o try/except aqui
    dentro, chamado pela rota logo depois de já ter salvo com sucesso)."""
    try:
        corpo_html = _montar_email_feedback_inserido_html(autor_nome, tipo, criado_em, usuario_recebido, nome_recebido)
        smtp_info = _config_email_boas_vindas()
        for destinatario in DESTINATARIOS_ALERTA_FEEDBACK:
            enviar_email(
                destinatario=destinatario,
                assunto=f"Novo {tipo.lower()} registrado - {nome_recebido}",
                corpo=corpo_html,
                smtp_info=smtp_info,
                raise_on_error=True,
            )
    except Exception:
        logger.exception(
            "Falha ao notificar %s inserido sobre '%s' - o registro em si já foi salvo normalmente.",
            tipo, usuario_recebido,
        )


def _manutencao_usuarios_execute_pda_login(action: str, usuario_pda: str, nome: str, senha_pda: str) -> dict:
    """Cria/desativa o LOGIN DO PRÓPRIO PDA (usuarios.json), opcional -
    só roda quando marcado no formulário. MESMA validação de
    /api/usuarios/criar e /api/usuarios/alterar-status (regex de
    usuário, tamanho mínimo de senha, checagem de duplicidade) - só que
    chamada direto em vez de via HTTP, pra entrar na mesma leva de
    resultados/prévia dos outros alvos."""
    linha_base = {"area": "-", "tenant": "PDA", "produto": "Login do PDA", "database": "usuarios.json"}
    if action == "cad":
        if not usuario_pda or not re.match(r"^[A-Za-z0-9_.\-]+$", usuario_pda):
            return {**linha_base, "status": "skipped", "message": "Usuário do PDA inválido (use apenas letras, números, . _ -)."}
        if any(u.lower() == usuario_pda.lower() for u in USUARIOS_WEB):
            return {**linha_base, "status": "skipped", "message": "Esse usuário do PDA já existe."}
        if not senha_pda or len(senha_pda) < 4:
            return {**linha_base, "status": "skipped", "message": "Senha do login PDA precisa ter ao menos 4 caracteres."}
        USUARIOS_WEB[usuario_pda] = {
            "senha": senha_pda, "nome": nome, "admin": False,
            "pode_manutencao_alertas": False, "pode_relatorios_shein": False, "pode_dash_financeiro": False,
            "pode_manutencao_rejeicoes": False, "pode_dados_sensiveis": False, "pode_manutencao_relatorios": False,
            "pode_manutencao_usuarios": False, "ativo": True, "atribuicao": "Suporte", "genero": "",
        }
        _salvar_usuarios(USUARIOS_WEB)
        return {**linha_base, "status": "success", "message": f"Login '{usuario_pda}' criado no PDA (sem permissões extras - ajuste em Usuários se precisar)."}
    else:
        if usuario_pda not in USUARIOS_WEB:
            return {**linha_base, "status": "skipped", "message": f"Usuário do PDA '{usuario_pda}' não encontrado."}
        if not USUARIOS_WEB[usuario_pda].get("ativo", True):
            return {**linha_base, "status": "skipped", "message": f"Login '{usuario_pda}' já estava desativado no PDA."}
        USUARIOS_WEB[usuario_pda]["ativo"] = False
        _salvar_usuarios(USUARIOS_WEB)
        for token in [t for t, s in SESSIONS.items() if s["usuario"] == usuario_pda]:
            SESSIONS.pop(token, None)
        return {**linha_base, "status": "success", "message": f"Login '{usuario_pda}' desativado no PDA (sessões ativas encerradas)."}


def _manutencao_usuarios_execute_target(action: str, nome: str, login: str, target: dict) -> dict:
    """Executa (ou pula) UM alvo - mesma máquina de estados do
    service.py original: SUCCESS / SKIPPED / ERROR, cada alvo com sua
    própria conexão e commit/rollback isolado, então uma falha num
    banco não afeta os outros alvos já processados ou os que vêm
    depois.

    Suporta MAIS DE UM candidato de conexão por tenant (ver
    _manutencao_usuarios_credenciais) - tenta o principal, e só tenta o
    "_fallback" (se existir) se o principal falhar ao CONECTAR (não em
    caso de erro depois de já conectado, tipo erro de permissão/SQL -
    aí o problema não é o servidor, então tentar outro não ajudaria e só
    mascararia o erro de verdade). Cada tentativa de conexão fica
    registrada em "tentativas_conexao" (server/database/user/password em
    texto puro, INTENCIONALMENTE sem sanitizar - pedido explícito do
    solicitante pra conseguir ver depois, no log, qual das duas credenciais
    funcionou) - isso NÃO aparece na mensagem devolvida pro PDA/usuário,
    só no log de auditoria (ver _manutencao_usuarios_executar)."""
    produto = target["produto"]
    area = target["area"]
    if produto not in MANUTENCAO_USUARIOS_SUPPORTED_PRODUCTS:
        return {**target, "status": "skipped", "message": f"Produto ainda não suportado: {produto}"}

    try:
        _manutencao_usuarios_validate_required_queries(area, produto, action)
        candidatos = _manutencao_usuarios_credenciais(area, target["tenant"])
    except ManutencaoUsuariosConfigError as exc:
        return {**target, "status": "skipped", "message": _manutencao_usuarios_sanitize(exc)}

    tentativas_conexao = []
    conn = None
    for credenciais in candidatos:
        conn_tentativa = conectar_banco(
            credenciais["server"], target["database"], credenciais["user"], credenciais["password"],
            raise_on_error=False,
        )
        tentativas_conexao.append({
            "db_server": credenciais["server"], "db_name": target["database"],
            "db_user": credenciais["user"], "db_password": credenciais["password"],
            "sucesso": bool(conn_tentativa),
        })
        if conn_tentativa:
            conn = conn_tentativa
            break
    # só carrega o detalhe de credenciais (com senha em texto puro) quando
    # é realmente informativo: teve mais de 1 candidato (então importa
    # registrar qual funcionou) OU nenhum conectou (erro, vale registrar
    # o que foi tentado). No caminho comum (1 candidato só, conectou de
    # primeira) fica None, e a senha nunca chega nem perto do log -
    # mesmo comportamento de antes desse fallback existir.
    detalhe_tentativas = tentativas_conexao if (len(candidatos) > 1 or not conn) else None
    if not conn:
        return {
            **target, "status": "error", "message": f"Falha ao conectar no banco {target['database']}",
            "tentativas_conexao": detalhe_tentativas,
        }
    try:
        try:
            if action == "cad":
                mensagem = _manutencao_usuarios_register(conn, area, produto, nome, login)
            else:
                mensagem = _manutencao_usuarios_deactivate(conn, area, produto, nome, login)
            conn.commit()
            return {
                **target, "status": "success", "message": _manutencao_usuarios_sanitize(mensagem),
                "tentativas_conexao": detalhe_tentativas,
            }
        except ManutencaoUsuariosSkip as exc:
            _rollback_if_possible(conn)
            return {
                **target, "status": "skipped", "message": _manutencao_usuarios_sanitize(exc),
                "tentativas_conexao": detalhe_tentativas,
            }
        except Exception as exc:
            _rollback_if_possible(conn)
            return {
                **target, "status": "error", "message": _manutencao_usuarios_sanitize(exc),
                "tentativas_conexao": detalhe_tentativas,
            }
    finally:
        fechar_conexao(conn)


def _manutencao_usuarios_validar_texto(rotulo: str, valor: str, tamanho_max: int) -> Optional[str]:
    """Mesma validação de UI do projeto original (lá era feita no
    Tkinter, aqui vira validação de servidor) - devolve a mensagem de
    erro, ou None se estiver tudo certo."""
    if not valor or valor.upper() == "NULL":
        return f"{rotulo} não pode ficar vazio."
    if len(valor) > tamanho_max:
        return f"{rotulo} excede o limite de {tamanho_max} caracteres."
    if _MANUTENCAO_USUARIOS_CARACTERES_INVALIDOS.search(valor):
        return f"{rotulo} contém caracteres inválidos."
    return None


def _manutencao_usuarios_log_path() -> str:
    pasta = os.path.join(_base_path_app(), "logs")
    os.makedirs(pasta, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(pasta, f"manutencao_usuarios_{timestamp}.jsonl")


def _manutencao_usuarios_gravar_auditoria(caminho: str, payload: dict) -> None:
    """Log de auditoria em .jsonl, MESMO FORMATO do projeto original
    (start/result/finish) - sempre sanitizado, nunca grava senha, string
    de conexão completa ou query integral. "operator" aqui é o usuário
    LOGADO NO PDA (sessao["usuario"]) - diferente do original, que usava
    getpass.getuser() porque rodava na máquina do próprio operador; como
    agora roda no servidor do PDA, getpass.getuser() pegaria a conta de
    serviço do servidor, não quem realmente clicou o botão."""
    try:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("Não foi possível gravar o log de auditoria de Manutenção de Usuários.")


def _manutencao_usuarios_execute_boas_vindas(nome: str, login: str) -> dict:
    """Dispara o e-mail de boas-vindas pro endereço informado como LOGIN
    do cadastro (normalmente já é o e-mail da pessoa) - só roda quando
    marcado no formulário, e só faz sentido pra ação de cadastro. Manda
    junto os dados de acesso de verdade: o login + a senha padrão que o
    cadastro em banco/Movidesk usa (MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL,
    a mesma exibida na tela). UM acesso só (login+senha) - não dois
    (pedido explícito do solicitante em 07/09/2026: mesmo quando também cria
    login no PDA à parte, o e-mail continua mostrando só essas
    credenciais principais)."""
    linha_base = {"area": "-", "tenant": "E-mail", "produto": "Boas-vindas", "database": f"pra {login}"}
    try:
        _exigir_senha_padrao_configurada()
        _enviar_email_boas_vindas(nome, login, login, MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL)
        return {**linha_base, "status": "success", "message": f"E-mail de boas-vindas enviado pra {login}."}
    except Exception as exc:
        logger.exception("Falha ao enviar e-mail de boas-vindas (cadastro) pra '%s'", login)
        return {**linha_base, "status": "error", "message": f"Falha ao enviar e-mail: {_manutencao_usuarios_sanitize(exc)}"}


def _manutencao_usuarios_executar(
    action: str, areas: tuple, area_valor: str, nome: str, login: str, operador: str,
    incluir_pda: bool = False, usuario_pda: str = "", senha_pda: str = "",
    enviar_boas_vindas: bool = False,
) -> dict:
    targets = _manutencao_usuarios_build_targets(areas)
    caminho_log = _manutencao_usuarios_log_path()
    _manutencao_usuarios_gravar_auditoria(caminho_log, {
        "event": "start", "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operator": operador, "action": action, "areas": list(areas),
        "nome": nome, "login": login,
        "total_targets": len(targets) + 1 + (1 if incluir_pda else 0) + (1 if enviar_boas_vindas else 0),
    })

    resultados = []

    def _registrar(resultado: dict) -> None:
        tentativas_conexao = resultado.pop("tentativas_conexao", None)
        if tentativas_conexao:
            _manutencao_usuarios_gravar_auditoria(caminho_log, {
                "event": "connection_attempts", "timestamp": datetime.now().isoformat(timespec="seconds"),
                "operator": operador, "area": resultado["area"], "tenant": resultado["tenant"],
                "produto": resultado["produto"], "attempts": tentativas_conexao,
            })
        resultados.append(resultado)
        _manutencao_usuarios_gravar_auditoria(caminho_log, {
            "event": "result", "timestamp": datetime.now().isoformat(timespec="seconds"),
            "operator": operador, "action": action, "area": resultado["area"], "tenant": resultado["tenant"],
            "produto": resultado["produto"], "database": resultado["database"],
            "status": resultado["status"], "message": resultado["message"],
        })

    # 1) Pessoa no Movidesk (API) - sempre roda, junto com o resto (pedido
    # explícito do solicitante: "mesma tela, tudo junto"). Vem primeiro porque
    # conceitualmente a identidade deveria existir antes do acesso a cada
    # produto - mas roda isolado como os outros, uma falha aqui não trava
    # os alvos de banco.
    _registrar(_manutencao_usuarios_execute_movidesk(action, nome, login, area_valor, operador))

    # 2) Login do próprio PDA - OPCIONAL, só quando marcado no formulário.
    if incluir_pda:
        _registrar(_manutencao_usuarios_execute_pda_login(action, usuario_pda, nome, senha_pda))

    # 3) E-mail de boas-vindas - OPCIONAL, só no cadastro e só quando
    # marcado. Roda isolado como os outros - se falhar, não impede o
    # resto do cadastro (banco/Movidesk/PDA) de seguir normalmente.
    if action == "cad" and enviar_boas_vindas:
        _registrar(_manutencao_usuarios_execute_boas_vindas(nome, login))

    # 4) Bancos de cada produto/cliente (fluxo já existente)
    for target in targets:
        _registrar(_manutencao_usuarios_execute_target(action, nome, login, target))

    sucesso = sum(1 for r in resultados if r["status"] == "success")
    ignorados = sum(1 for r in resultados if r["status"] == "skipped")
    erros = sum(1 for r in resultados if r["status"] == "error")
    _manutencao_usuarios_gravar_auditoria(caminho_log, {
        "event": "finish", "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operator": operador, "success": sucesso, "skipped": ignorados, "errors": erros,
    })
    logger_administracao.info(
        "Manutenção de Usuários: %s '%s' (%s) por '%s' - %d sucesso(s), %d ignorado(s), %d erro(s). Log: %s",
        "cadastro" if action == "cad" else "desativação", login, "+".join(areas), operador,
        sucesso, ignorados, erros, caminho_log,
    )
    return {
        "resultados": resultados, "sucesso": sucesso, "ignorados": ignorados, "erros": erros,
        "log": os.path.basename(caminho_log),
    }


def _criar_sessao(
    usuario: str, admin: bool, pode_manutencao_alertas: bool = False,
    pode_relatorios_shein: bool = False, pode_dash_financeiro: bool = False,
    pode_manutencao_rejeicoes: bool = False, pode_dados_sensiveis: bool = False,
    pode_manutencao_relatorios: bool = False, pode_manutencao_usuarios: bool = False,
    nome: str = None, genero: str = "",
) -> str:
    token = secrets.token_hex(32)
    SESSIONS[token] = {
        "usuario": usuario,
        "nome": nome or usuario,
        "genero": genero or "",
        "admin": admin,
        "pode_manutencao_alertas": pode_manutencao_alertas,
        "pode_relatorios_shein": pode_relatorios_shein,
        "pode_dash_financeiro": pode_dash_financeiro,
        "pode_manutencao_rejeicoes": pode_manutencao_rejeicoes,
        "pode_dados_sensiveis": pode_dados_sensiveis,
        "pode_manutencao_relatorios": pode_manutencao_relatorios,
        "pode_manutencao_usuarios": pode_manutencao_usuarios,
        "expira": datetime.now() + timedelta(minutes=DURACAO_INATIVIDADE_MINUTOS),
    }
    return token


def _sessao_atual(token: Optional[str], renovar: bool = True) -> Optional[dict]:
    """Busca a sessão pelo token. Por padrão, RENOVA o prazo de inatividade
    (sessão "deslizante" - continua valendo enquanto a pessoa usa o painel).
    `renovar=False` é usado só pela pergunta automática de status (a página
    de Alertas consulta sozinha a cada 2s) - isso NÃO conta como atividade
    de verdade, senão a sessão nunca expiraria com a aba só aberta."""
    if not token:
        return None
    sessao = SESSIONS.get(token)
    if not sessao:
        return None
    if datetime.now() > sessao["expira"]:
        SESSIONS.pop(token, None)
        return None
    if renovar:
        sessao["expira"] = datetime.now() + timedelta(minutes=DURACAO_INATIVIDADE_MINUTOS)
    return sessao


def _tem_acesso_manutencao_alertas(sessao: dict) -> bool:
    """Admins sempre têm acesso. Usuários de visualização só têm acesso à
    Manutenção de Alertas em Banco se tiverem a permissão adicional
    marcada especificamente pra eles na aba Usuários."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_manutencao_alertas"))


def _tem_acesso_relatorios_shein(sessao: dict) -> bool:
    """Mesma ideia de _tem_acesso_manutencao_alertas, mas pro card de
    Relatórios Shein - admin por padrão, liberável por pessoa na aba
    Usuários."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_relatorios_shein"))


def _tem_acesso_dash_financeiro(sessao: dict) -> bool:
    """Mesma ideia, pro card de Atualização Dash Financeiro."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_dash_financeiro"))


def _tem_acesso_manutencao_rejeicoes(sessao: dict) -> bool:
    """Mesma ideia, pro card de Manutenção Rejeições em Banco."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_manutencao_rejeicoes"))


def _tem_acesso_dados_sensiveis(sessao: dict) -> bool:
    """DIFERENTE de todas as outras permissões desse painel: aqui não tem
    "admin sempre tem acesso" - String Connections é uma permissão à
    parte, precisa estar marcada especificamente pra pessoa, mesmo que
    ela seja administradora. Pedido explícito - String Connections
    carrega strings de conexão de banco de clientes, então o acesso é
    mais restrito de propósito."""
    return bool(sessao.get("pode_dados_sensiveis"))


def _tem_acesso_manutencao_usuarios(sessao: dict) -> bool:
    """Precisa ser admin E ter a permissão especial marcada (não basta só
    uma das duas) - agora que esse card SUBSTITUIU a antiga tela
    "Usuários" (gerencia login do PDA, permissões, vínculo Movidesk E o
    cadastro/desativação em produção), reforçando o pedido do solicitante de
    04-06/09/2026: "o card é apenas para adms", mesmo que por engano
    alguém marque a permissão numa conta que não é administradora."""
    return bool(sessao.get("admin")) and bool(sessao.get("pode_manutencao_usuarios"))


def _tem_acesso_manutencao_relatorios(sessao: dict) -> bool:
    """Mesma ideia de _tem_acesso_manutencao_alertas, pro card de
    Manutenção de Relatórios em Banco."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_manutencao_relatorios"))


def _tem_acesso_dashboards_clientes(sessao: dict) -> bool:
    """Card em Beta (07/09/2026) - acesso simples de admin, sem permissão
    extra à parte (diferente de Dados Sensíveis/Manutenção de Usuários) -
    pedido do solicitante foi só "acessível apenas para ADM's"."""
    return bool(sessao.get("admin"))


def _caminho_dashboards_clientes_json() -> str:
    return os.path.join(_base_path_app(), "dashboards_clientes.json")


def _carregar_dashboards_clientes() -> dict:
    """Cliente -> lista de produtos - dados semente (Sanepar/Vivo) só pra
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
# Dashboard Sanepar > NFAg - transcrito do Power BI (Indicadores_NFAg_Sanepar
# .pbix) em 08/09/2026, a pedido do solicitante. Mesma lógica de negócio das
# medidas DAX originais (ver 02_medidas_dax.txt que ele mandou), só que
# calculada em Python a partir da mesma query SQL nativa do PBIX.
# ---------------------------------------------------------------------------
NFAG_SANEPAR_CNPJ = "76484013000145"

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


def _config_dashboard_sanepar_nfag() -> dict:
    """CREDENCIAIS_CENTRALIZADAS.env primeiro (seção
    [dashboard_sanepar_nfag]), cai pro .env.dashboard_sanepar_nfag
    tradicional se essa seção não existir (ver core/config_central.py)."""
    valores = _obter_config_hibrido(
        "dashboard_sanepar_nfag", ".env.dashboard_sanepar_nfag",
        ["db_server", "db_name", "db_user", "db_password"],
    )
    return {
        "server": valores["db_server"],
        "database": valores["db_name"],
        "username": valores["db_user"],
        "password": _obter_valor_config("dashboard_sanepar_nfag::db_password", valores["db_password"]),
    }


def _consultar_dashboard_sanepar_nfag(data_inicio: Optional[str], data_fim: Optional[str]) -> dict:
    """Mesma query nativa do PBIX (mesmo WHERE por CNPJ), com filtro de
    data OPCIONAL por cima (equivalente ao slicer "Entre" do relatório
    original) - devolve {"ok": True, ...} com tudo que os visuais do
    PBIX precisam, ou {"ok": False, "erro": str}."""
    cfg = _config_dashboard_sanepar_nfag()
    if not cfg["password"] or cfg["password"] == "PREENCHER_SENHA_AQUI":
        return {"ok": False, "erro": "Credencial do banco nfagpack_homol ainda não configurada (db_password em branco)."}

    query = (
        "SELECT ID, CHAVE_NF, IND_STATUS, DATA_INTEGRATION, EMPRESA_CNPJ, SERIE, NNF, DEMI, "
        "PROT_C_STAT, PROT_X_MOTIVO FROM documento_fiscal WHERE empresa_cnpj = ?"
    )
    params = [NFAG_SANEPAR_CNPJ]
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
        logger.exception("Erro ao consultar dashboard Sanepar/NFAg")
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


def _json_serializar_padrao(obj):
    """Handler de fallback pro json.dumps, pra tipos que vêm direto do
    banco (via pyodbc) e não são serializáveis por padrão - sem isso, um
    TypeError aqui acontece ANTES de qualquer resposta HTTP ser mandada,
    e o navegador só vê "Failed to fetch" (sem corpo, sem status, sem
    pista nenhuma do que rolou de verdade). Cobre os casos mais comuns:
    datetime.time/date/datetime (ex.: HORA_EXECUCAO vindo como objeto
    time em vez de string), Decimal (comum em colunas numéricas de
    alguns drivers), e bytes."""
    if isinstance(obj, (datetime, date, time_cls)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, (bytes, bytearray)):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


class _PainelHTTPHandler(BaseHTTPRequestHandler):
    job_states: List[JobState] = []
    state_by_nome: dict = {}

    def log_message(self, format, *args):
        pass  # silencia o log padrão do http.server no console

    def _pegar_token(self) -> Optional[str]:
        cookie_header = self.headers.get("Cookie", "")
        for parte in cookie_header.split(";"):
            parte = parte.strip()
            if parte.startswith("session="):
                return parte[len("session="):]
        return None

    def _sessao(self, renovar: bool = True) -> Optional[dict]:
        return _sessao_atual(self._pegar_token(), renovar=renovar)

    def _ler_corpo_form(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        corpo = self.rfile.read(length).decode("utf-8") if length else ""
        dados = urllib.parse.parse_qs(corpo)
        return {k: v[0] for k, v in dados.items()}

    def _enviar_json(self, dados: dict, status: int = 200) -> None:
        corpo = json.dumps(dados, default=_json_serializar_padrao).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _enviar_html(self, html: str, status: int = 200) -> None:
        corpo = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _redirecionar(self, destino: str, cookie: Optional[str] = None) -> None:
        self.send_response(303)
        self.send_header("Location", destino)
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    # -- GET --------------------------------------------------------------
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        caminho = parsed.path

        if caminho == "/login":
            query = urllib.parse.parse_qs(parsed.query)
            valor_erro = query.get("erro", ["0"])[0]
            erro = valor_erro == "1"
            desativado = valor_erro == "desativado"
            sucesso = query.get("senha_alterada", ["0"])[0] == "1"
            self._enviar_html(_montar_login_html(erro, sucesso, desativado))
            return

        if caminho == "/alterar-senha":
            erro = urllib.parse.parse_qs(parsed.query).get("erro", [None])[0]
            self._enviar_html(_montar_alterar_senha_html(erro))
            return

        if caminho == "/logout":
            token = self._pegar_token()
            if token:
                SESSIONS.pop(token, None)
            self._redirecionar("/login", cookie="session=; Path=/; Max-Age=0")
            return

        # A consulta automática de status (a cada 2s, sozinha) NAO conta
        # como atividade real - só renova a sessão em ações de verdade
        # (abrir uma página, clicar em Executar, etc.)
        sessao = self._sessao(renovar=(caminho != "/api/status"))
        if not sessao:
            if caminho.startswith("/api/"):
                self._enviar_json({"ok": False, "erro": "não autenticado"}, status=401)
            else:
                self._redirecionar("/login")
            return

        if caminho == "/" or caminho == "/index.html":
            self._enviar_html(_montar_hub_html(sessao))

        elif caminho == "/alertas":
            self._enviar_html(_montar_alertas_html(sessao))

        elif caminho == "/usuarios":
            # Antiga tela de Usuários - SUBSTITUÍDA pela Manutenção de
            # Usuários (05-06/09/2026), que agora cobre tudo que essa
            # cobria (login PDA, permissões, vínculo Movidesk) e mais o
            # cadastro/desativação em produção. Redireciona em vez de
            # deixar a URL morta pra quem tiver ela salva/em favoritos.
            self._redirecionar("/manutencao-usuarios")

        elif caminho == "/manutencao-alertas":
            if _tem_acesso_manutencao_alertas(sessao):
                self._enviar_html(_montar_manutencao_alertas_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Manutenção de Alertas em Banco"), status=200)

        elif caminho == "/manutencao-rejeicoes":
            if _tem_acesso_manutencao_rejeicoes(sessao):
                self._enviar_html(_montar_manutencao_rejeicoes_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Manutenção Rejeições em Banco"), status=200)

        elif caminho == "/manutencao-relatorios":
            if _tem_acesso_manutencao_relatorios(sessao):
                self._enviar_html(_montar_manutencao_relatorios_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Manutenção de Relatórios em Banco"), status=200)

        elif caminho == "/dashboards-clientes":
            if _tem_acesso_dashboards_clientes(sessao):
                self._enviar_html(_montar_dashboards_clientes_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Dashboards por Cliente"), status=200)

        elif caminho == "/api/dashboards-clientes":
            if not _tem_acesso_dashboards_clientes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            self._enviar_json({"ok": True, "clientes": _carregar_dashboards_clientes()})

        elif caminho == "/api/dashboards-clientes/sanepar/nfag":
            if not _tem_acesso_dashboards_clientes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            query_nfag = urllib.parse.parse_qs(parsed.query)
            data_inicio = query_nfag.get("data_inicio", [None])[0]
            data_fim = query_nfag.get("data_fim", [None])[0]
            resultado = _consultar_dashboard_sanepar_nfag(data_inicio, data_fim)
            self._enviar_json(resultado)

        elif caminho == "/sobre":
            # sem restrição de admin/permissão especial - qualquer pessoa
            # logada pode ver do que se trata o painel
            self._enviar_html(_montar_sobre_html(sessao))

        elif caminho == "/string-connections":
            if _tem_acesso_dados_sensiveis(sessao):
                self._enviar_html(_montar_string_connections_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "String Connections"), status=200)

        elif caminho == "/config-seguro":
            if _tem_acesso_dados_sensiveis(sessao):
                self._enviar_html(_montar_config_seguro_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Criptografia de Dados Sensíveis"), status=200)

        elif caminho == "/indicadores-movidesk":
            if sessao["admin"]:
                self._enviar_html(_montar_indicadores_movidesk_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Indicadores Movidesk"), status=200)

        elif caminho == "/horas-trabalhadas":
            if sessao["admin"]:
                self._enviar_html(_montar_horas_trabalhadas_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Horas Trabalhadas"), status=200)

        elif caminho == "/automacao-movidesk":
            if sessao["admin"]:
                self._enviar_html(_montar_automacao_movidesk_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Automação Movidesk"), status=200)

        elif caminho == "/dash-financeiro":
            if _tem_acesso_dash_financeiro(sessao):
                self._enviar_html(_montar_dash_financeiro_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Atualização Dash Financeiro"), status=200)

        elif caminho == "/emailpack":
            self._enviar_html(_montar_emailpack_html(sessao))

        elif caminho == "/ferias":
            self._enviar_html(_montar_ferias_html(sessao))

        elif caminho.startswith("/perfil/"):
            usuario_perfil = urllib.parse.unquote(caminho[len("/perfil/"):])
            if usuario_perfil not in USUARIOS_WEB:
                self.send_response(404)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.end_headers()
                self.wfile.write("Usuário não encontrado.".encode("utf-8"))
                return
            self._enviar_html(_montar_perfil_html(sessao, usuario_perfil))

        elif caminho == "/logs":
            if sessao["admin"]:
                self._enviar_html(_montar_logs_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Logs"), status=200)

        elif caminho == "/manutencao-usuarios":
            if _tem_acesso_manutencao_usuarios(sessao):
                self._enviar_html(_montar_manutencao_usuarios_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Manutenção de Usuários"), status=200)

        elif caminho == "/contingencias":
            self._enviar_html(_montar_contingencias_html(sessao))

        elif caminho == "/relatorios-shein":
            if _tem_acesso_relatorios_shein(sessao):
                self._enviar_html(_montar_relatorios_shein_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Relatórios Shein"), status=200)

        elif caminho.startswith("/api/relatorios-shein/"):
            if not _tem_acesso_relatorios_shein(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return

            if caminho == "/api/relatorios-shein/status":
                with _lock_relatorio_shein_auto:
                    self._enviar_json(dict(estado_relatorio_shein_automatico))
                return

            if caminho == "/api/relatorios-shein/log":
                caminho_log = os.path.join(_base_path_app(), "logs", "relatorios_shein.log")
                if not os.path.exists(caminho_log):
                    self._enviar_json({"ok": True, "linhas": [], "aviso": "Ainda não há nada registrado."})
                    return
                try:
                    ultimas = _ler_ultimas_linhas_arquivo(caminho_log, n_linhas=1000)
                    self._enviar_json({"ok": True, "linhas": ultimas})
                except Exception as e:
                    self._enviar_json({"ok": False, "erro": f"Não foi possível ler o log: {e}"}, status=500)
                return

            if caminho == "/api/relatorios-shein/existe":
                data_str = urllib.parse.parse_qs(parsed.query).get("data", [None])[0]
                try:
                    data = datetime.strptime(data_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    self._enviar_json({"ok": False, "erro": "Data inválida."}, status=400)
                    return
                data_arquivo = data.strftime("%d-%m-%Y")
                nome_notas = f"{data_arquivo}.xlsx"
                nome_canceladas = f"Canceladas_{data_arquivo}.xlsx"
                pasta = _pasta_saida_relatorios_shein(data)
                existe_notas = os.path.isfile(os.path.join(pasta, nome_notas))
                existe_canceladas = os.path.isfile(os.path.join(pasta, nome_canceladas))
                self._enviar_json({
                    "ok": True,
                    "existe": existe_notas and existe_canceladas,
                    "arquivo_notas": nome_notas if existe_notas else None,
                    "arquivo_canceladas": nome_canceladas if existe_canceladas else None,
                })
                return

            if caminho.startswith("/api/relatorios-shein/download-zip/"):
                # baixa os 2 arquivos (Notas + Canceladas) de uma data como um
                # zip só, nomeado com a própria data (ex.: 09-08-2026.zip) - o
                # zip é montado na hora, em memória, não fica salvo em disco
                data_str = urllib.parse.unquote(caminho[len("/api/relatorios-shein/download-zip/"):])
                if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", data_str):
                    self.send_response(400)
                    self.end_headers()
                    return
                pasta = _localizar_pasta_relatorio_shein_por_data_str(data_str)
                nome_notas = f"{data_str}.xlsx"
                nome_canceladas = f"Canceladas_{data_str}.xlsx"
                caminho_notas = os.path.join(pasta, nome_notas)
                caminho_canceladas = os.path.join(pasta, nome_canceladas)
                if not (os.path.isfile(caminho_notas) and os.path.isfile(caminho_canceladas)):
                    self.send_response(404)
                    self.end_headers()
                    return

                buffer_zip = io.BytesIO()
                with zipfile.ZipFile(buffer_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                    zf.write(caminho_notas, arcname=nome_notas)
                    zf.write(caminho_canceladas, arcname=nome_canceladas)
                conteudo_zip = buffer_zip.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="{data_str}.zip"')
                self.send_header("Content-Length", str(len(conteudo_zip)))
                self.end_headers()
                self.wfile.write(conteudo_zip)
                return

            if caminho.startswith("/api/relatorios-shein/download/"):
                nome_arquivo = urllib.parse.unquote(caminho[len("/api/relatorios-shein/download/"):])
                # trava contra path traversal - só permite exatamente o padrão
                # de nome que a gente mesmo gera, nunca um caminho arbitrário
                if not re.fullmatch(r"(Canceladas_)?\d{2}-\d{2}-\d{4}\.xlsx", nome_arquivo):
                    self.send_response(400)
                    self.end_headers()
                    return
                # a data sempre está no final do nome (com ou sem o prefixo
                # "Canceladas_"), usada pra reconstruir a pasta Mês/Dia certa
                data_do_nome = nome_arquivo.replace("Canceladas_", "").replace(".xlsx", "")
                pasta = _localizar_pasta_relatorio_shein_por_data_str(data_do_nome)
                caminho_completo = os.path.join(pasta, nome_arquivo)
                if not os.path.isfile(caminho_completo):
                    self.send_response(404)
                    self.end_headers()
                    return
                with open(caminho_completo, "rb") as f:
                    conteudo = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.send_header("Content-Disposition", f'attachment; filename="{nome_arquivo}"')
                self.send_header("Content-Length", str(len(conteudo)))
                self.end_headers()
                self.wfile.write(conteudo)
                return

            # nenhuma sub-rota bateu - 404 genérico
            self.send_response(404)
            self.end_headers()

        elif caminho == "/api/status":
            jobs = []
            for state in self.job_states:
                proxima_dt = _proxima_execucao(state)
                proxima = proxima_dt.strftime("%Y-%m-%d %H:%M:%S") if proxima_dt else None
                jobs.append({
                    "nome": state.job.nome,
                    "status": state.status,
                    "cor": STATUS_COLORS_WEB.get(state.status, "#d4d4d4"),
                    "ultima": state.last_run,
                    "proxima": proxima,
                    "erro": state.last_error,
                })

            self._enviar_json({"jobs": jobs})

        elif caminho == "/api/usuarios":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            usuarios = [
                {
                    "usuario": nome,
                    "nome": info.get("nome") or nome,
                    "atribuicao": info.get("atribuicao") or "Suporte",
                    "genero": info.get("genero") or "",
                    "admin": bool(info.get("admin")),
                    "pode_manutencao_alertas": bool(info.get("pode_manutencao_alertas")),
                    "pode_relatorios_shein": bool(info.get("pode_relatorios_shein")),
                    "pode_dash_financeiro": bool(info.get("pode_dash_financeiro")),
                    "pode_manutencao_rejeicoes": bool(info.get("pode_manutencao_rejeicoes")),
                    "pode_dados_sensiveis": bool(info.get("pode_dados_sensiveis")),
                    "pode_manutencao_relatorios": bool(info.get("pode_manutencao_relatorios")),
                    "pode_manutencao_usuarios": bool(info.get("pode_manutencao_usuarios")),
                    "usuario_movidesk_id": info.get("usuario_movidesk_id"),
                    "email": info.get("email") or "",
                    "data_inicio": info.get("data_inicio") or "",
                    "ativo": info.get("ativo", True),
                    "tem_foto": _caminho_foto_usuario(nome) is not None,
                }
                for nome, info in USUARIOS_WEB.items()
            ]
            usuarios.sort(key=lambda u: u["usuario"].lower())
            self._enviar_json({"usuarios": usuarios})

        elif caminho.startswith("/foto-usuario/"):
            usuario_foto = urllib.parse.unquote(caminho[len("/foto-usuario/"):])
            caminho_foto = _caminho_foto_usuario(usuario_foto)
            if not caminho_foto:
                self.send_response(404)
                self.end_headers()
                return
            extensao = os.path.splitext(caminho_foto)[1].lower()
            tipo_mime = next((m for m, e in _EXTENSOES_FOTO_PERMITIDAS.items() if e == extensao), "application/octet-stream")
            with open(caminho_foto, "rb") as f:
                conteudo_foto = f.read()
            self.send_response(200)
            self.send_header("Content-Type", tipo_mime)
            self.send_header("Content-Length", str(len(conteudo_foto)))
            self.send_header("Cache-Control", "private, max-age=300")
            self.end_headers()
            self.wfile.write(conteudo_foto)

        elif caminho == "/api/usuarios-movidesk":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            resultado = _listar_usuarios_movidesk()
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho.startswith("/api/perfil/") and caminho.endswith("/mes-anterior"):
            usuario_perfil = urllib.parse.unquote(caminho[len("/api/perfil/"):-len("/mes-anterior")].rstrip("/"))
            if usuario_perfil not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            eh_proprio_perfil = sessao["usuario"] == usuario_perfil
            if not (eh_proprio_perfil or sessao["admin"]):
                self._enviar_json({"ok": False, "erro": "sem permissão pra ver esse dado"}, status=403)
                return
            dados_mes_anterior = _montar_dados_perfil_mes_anterior(usuario_perfil)
            self._enviar_json({"ok": True, **dados_mes_anterior})

        elif caminho.startswith("/api/perfil/") and caminho.endswith("/exportar-horas"):
            # exportação de atividades do Perfil - MESMO critério de acesso
            # já usado em /api/perfil/<usuario> (pode_ver_completo): só a
            # própria pessoa ou um admin pode baixar. Ninguém mais consegue
            # exportar hora de quem não é ela mesma, mesmo sabendo o login.
            usuario_perfil = urllib.parse.unquote(caminho[len("/api/perfil/"):-len("/exportar-horas")].rstrip("/"))
            if usuario_perfil not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            eh_proprio_perfil = sessao["usuario"] == usuario_perfil
            if not (eh_proprio_perfil or sessao["admin"]):
                self._enviar_json({"ok": False, "erro": "sem permissão pra exportar as horas dessa pessoa"}, status=403)
                return
            nome_movidesk, erro_vinculo = _nome_movidesk_vinculado(usuario_perfil)
            if erro_vinculo:
                self._enviar_json({"ok": False, "erro": erro_vinculo}, status=502)
                return
            if not nome_movidesk:
                self._enviar_json({"ok": False, "erro": "essa pessoa ainda não está vinculada a um usuário do Movidesk"}, status=400)
                return
            query = urllib.parse.parse_qs(parsed.query)
            data_inicio = query.get("data_inicio", [None])[0]
            data_fim = query.get("data_fim", [None])[0]
            if not data_inicio or not data_fim:
                hoje = datetime.now().date()
                data_inicio = hoje.replace(day=1).strftime("%Y-%m-%d")
                data_fim = hoje.strftime("%Y-%m-%d")
            resultado = _consultar_horas_trabalhadas(data_inicio, data_fim, incluir_detalhe=True)
            if not resultado.get("ok"):
                self._enviar_json(resultado, status=502)
                return
            linhas_pessoa = [l for l in resultado["linhas"] if l["analista"] == nome_movidesk]
            detalhe_pessoa = [d for d in resultado["detalhe"] if d["analista"] == nome_movidesk]
            conteudo = _gerar_excel_export_horas(linhas_pessoa, detalhe_pessoa)
            nome_arquivo = f"horas_{usuario_perfil}_{data_inicio}_a_{data_fim}.xlsx"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", f'attachment; filename="{nome_arquivo}"')
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)

        elif caminho.startswith("/api/perfil/"):
            usuario_perfil = urllib.parse.unquote(caminho[len("/api/perfil/"):])
            dados_perfil = _montar_dados_perfil(usuario_perfil)
            if dados_perfil is None:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            eh_proprio_perfil = sessao["usuario"] == usuario_perfil
            # admin consegue ver o perfil completo de qualquer pessoa (pedido
            # do solicitante) - quem não é admin só vê o perfil completo do
            # próprio, e de mais ninguém
            pode_ver_completo = eh_proprio_perfil or sessao["admin"]

            # Feedback: SEPARADO de pode_ver_completo de propósito - a
            # própria pessoa NUNCA vê (mesmo sendo admin do próprio
            # perfil), só admin de mesma equipe vendo o perfil de outra
            # pessoa (ver _tem_acesso_feedback_usuario).
            pode_ver_feedback = _tem_acesso_feedback_usuario(sessao, usuario_perfil)
            feedbacks_pessoa = []
            if pode_ver_feedback:
                with _lock_feedbacks_usuarios:
                    feedbacks_pessoa = [
                        dict(f) for f in FEEDBACKS_USUARIOS if f.get("usuario") == usuario_perfil
                    ]
                feedbacks_pessoa.sort(key=lambda f: f.get("criado_em", ""), reverse=True)

            if pode_ver_completo:
                self._enviar_json({
                    "ok": True, "proprio_perfil": eh_proprio_perfil, "pode_ver_completo": True,
                    "sessao_admin": sessao["admin"],
                    "pode_ver_feedback": pode_ver_feedback, "feedbacks": feedbacks_pessoa,
                    **dados_perfil,
                })
            else:
                # quem não é a própria pessoa nem admin só vê nome e foto -
                # nada de horas trabalhadas, tickets, férias ou atribuição
                self._enviar_json({
                    "ok": True, "proprio_perfil": False, "pode_ver_completo": False,
                    "sessao_admin": sessao["admin"],
                    "pode_ver_feedback": pode_ver_feedback, "feedbacks": feedbacks_pessoa,
                    "usuario": dados_perfil["usuario"], "nome": dados_perfil["nome"],
                    "tem_foto": dados_perfil["tem_foto"],
                })

        elif caminho == "/api/ferias":
            with _lock_ferias:
                registros = [dict(f) for f in FERIAS]
            for r in registros:
                info_pessoa = USUARIOS_WEB.get(r["usuario"], {})
                r["nome"] = info_pessoa.get("nome") or r["usuario"]
                r.setdefault("tipo", "ferias")
            registros.sort(key=lambda r: r["inicio"])
            self._enviar_json({"ok": True, "registros": registros})

        elif caminho.startswith("/api/usuarios-movidesk/"):
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            id_usuario_movidesk = urllib.parse.unquote(caminho[len("/api/usuarios-movidesk/"):])
            resultado = _buscar_usuario_movidesk(id_usuario_movidesk)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/config-seguro":
            if not _tem_acesso_dados_sensiveis(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Dados Sensíveis"}, status=403)
                return
            # só os NOMES das chaves - nunca os valores, nem pra admin,
            # pela própria interface web (ver core/config_seguro.py)
            self._enviar_json({"ok": True, "chaves": _listar_chaves_config_dat()})

        elif caminho == "/api/emailpack/status":
            with _lock_estado_emailpack:
                estado_copia = dict(estado_emailpack)
            self._enviar_json({"ok": True, **estado_copia})

        elif caminho == "/api/emailpack/emails":
            with _lock_emails_emailpack:
                conhecidos = sorted(_carregar_emails_conhecidos_emailpack())
                ignorados = sorted(_carregar_emails_ignorados_emailpack())
            self._enviar_json({"ok": True, "conhecidos": conhecidos, "ignorados": ignorados})

        elif caminho == "/api/dash-financeiro/status":
            if not _tem_acesso_dash_financeiro(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            with _lock_dash_financeiro:
                produtos_rodando = set(_produtos_em_execucao)
                status_sessao = dict(estado_dash_financeiro)
            status_combinado = {}
            for produto in ORDEM_PRODUTOS_DASH_FINANCEIRO:
                if produto in produtos_rodando:
                    status_combinado[produto] = {"rodando": True}
                elif status_sessao.get(produto) is not None:
                    status_combinado[produto] = status_sessao[produto]
                else:
                    # essa sessão ainda não mexeu nesse produto (por
                    # exemplo, o programa acabou de reiniciar) - cai pro
                    # que já está salvo em disco, em vez de mostrar
                    # "nunca rodou" pra algo que na verdade já rodou
                    status_combinado[produto] = _status_disco_produto(produto)
            self._enviar_json({
                "ok": True,
                "ordem": ORDEM_PRODUTOS_DASH_FINANCEIRO,
                "status": status_combinado,
                "execucao_ativa": _dash_financeiro_execucao_ativa,
            })

        elif caminho == "/api/logs":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            nome_card = urllib.parse.parse_qs(parsed.query).get("card", [None])[0]
            info_log = LOGS_DISPONIVEIS.get(nome_card)
            if not info_log:
                self._enviar_json({"ok": False, "erro": "card de log desconhecido"}, status=400)
                return
            pasta_log, nome_arquivo = info_log
            caminho_log = os.path.join(pasta_log, nome_arquivo)
            if not os.path.exists(caminho_log):
                self._enviar_json({"ok": True, "linhas": [], "aviso": "Ainda não há nada registrado nesse log."})
                return
            try:
                ultimas = _ler_ultimas_linhas_arquivo(caminho_log, n_linhas=1000)
                self._enviar_json({"ok": True, "linhas": ultimas})
            except Exception as e:
                self._enviar_json({"ok": False, "erro": f"Não foi possível ler o log: {e}"}, status=500)

        elif caminho == "/api/string-connections":
            # leitura liberada pra quem tem acesso à Manutenção de Alertas
            # (admin ou view com a permissão extra) - é preciso ver a lista
            # pra escolher uma na hora de criar/editar um alerta. Só
            # criar/editar/excluir (rotas POST) que são admin-only.
            if not _tem_acesso_manutencao_alertas(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            conexoes = [
                {"id": id_, **info}
                for id_, info in STRING_CONNECTIONS.items()
            ]
            conexoes.sort(key=lambda c: (c["cliente"].lower(), c["produto"].lower()))
            self._enviar_json({"ok": True, "conexoes": conexoes})

        elif caminho == "/api/indicadores-movidesk":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            query_im = urllib.parse.parse_qs(parsed.query)
            data_inicio = query_im.get("data_inicio", [None])[0]
            data_fim = query_im.get("data_fim", [None])[0]
            if not data_inicio:
                primeiro_dia_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")
                data_inicio = primeiro_dia_mes
            resultado = _consultar_indicadores_movidesk(data_inicio, data_fim)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/indicadores-movidesk/horas":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            query = urllib.parse.parse_qs(parsed.query)
            data_inicio = query.get("data_inicio", [None])[0]
            data_fim = query.get("data_fim", [None])[0]
            equipe_filtro = query.get("equipe", [None])[0] or None
            if not data_inicio or not data_fim:
                self._enviar_json({"ok": False, "erro": "informe data_inicio e data_fim"}, status=400)
                return
            resultado = _consultar_horas_trabalhadas(data_inicio, data_fim, equipe_filtro=equipe_filtro)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/horas-trabalhadas/exportar":
            # exporta TODO MUNDO do período em Excel - página é admin-only,
            # então quem chega aqui já pode ver as horas de qualquer pessoa
            # mesmo (mesmo critério de /api/indicadores-movidesk/horas acima).
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            query = urllib.parse.parse_qs(parsed.query)
            data_inicio = query.get("data_inicio", [None])[0]
            data_fim = query.get("data_fim", [None])[0]
            equipe_filtro = query.get("equipe", [None])[0] or None
            if not data_inicio or not data_fim:
                self._enviar_json({"ok": False, "erro": "informe data_inicio e data_fim"}, status=400)
                return
            resultado = _consultar_horas_trabalhadas(data_inicio, data_fim, incluir_detalhe=True, equipe_filtro=equipe_filtro)
            if not resultado.get("ok"):
                self._enviar_json(resultado, status=502)
                return
            conteudo = _gerar_excel_export_horas(resultado["linhas"], resultado["detalhe"])
            nome_arquivo = f"horas_trabalhadas_{data_inicio}_a_{data_fim}.xlsx"
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", f'attachment; filename="{nome_arquivo}"')
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)

        elif caminho == "/api/manutencao-alertas":
            if not _tem_acesso_manutencao_alertas(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Alertas em Banco"}, status=403)
                return
            resultado = _listar_alertas_banco()
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho.startswith("/api/manutencao-alertas/"):
            if not _tem_acesso_manutencao_alertas(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Alertas em Banco"}, status=403)
                return
            id_texto = caminho[len("/api/manutencao-alertas/"):]
            try:
                id_alerta = int(id_texto)
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            resultado = _buscar_alerta_banco(id_alerta)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-rejeicoes":
            if not _tem_acesso_manutencao_rejeicoes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção Rejeições em Banco"}, status=403)
                return
            resultado = _listar_rejeicoes_banco()
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho.startswith("/api/manutencao-rejeicoes/"):
            if not _tem_acesso_manutencao_rejeicoes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção Rejeições em Banco"}, status=403)
                return
            id_texto = caminho[len("/api/manutencao-rejeicoes/"):]
            try:
                id_rejeicao = int(id_texto)
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            resultado = _buscar_rejeicao_banco(id_rejeicao)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-relatorios":
            if not _tem_acesso_manutencao_relatorios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Relatórios em Banco"}, status=403)
                return
            resultado = _listar_relatorios_banco()
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho.startswith("/api/manutencao-relatorios/"):
            if not _tem_acesso_manutencao_relatorios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Relatórios em Banco"}, status=403)
                return
            id_texto = caminho[len("/api/manutencao-relatorios/"):]
            try:
                id_relatorio = int(id_texto)
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            resultado = _buscar_relatorio_banco(id_relatorio)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/contingencias":
            with _lock_contingencias:
                self._enviar_json({
                    "ufs": dict(estado_contingencias["ufs"]),
                    "detalhes": dict(estado_contingencias["detalhes"]),
                    "ultima_verificacao": estado_contingencias["ultima_verificacao"],
                    "ultimo_erro": estado_contingencias["ultimo_erro"],
                })

        else:
            self.send_response(404)
            self.end_headers()

    # -- POST -------------------------------------------------------------
    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        caminho = parsed.path

        if caminho == "/login":
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            senha = dados.get("senha", "")
            info = USUARIOS_WEB.get(usuario)
            senha_esperada = info.get("senha") if info else None
            if senha_esperada is not None and senha and secrets.compare_digest(senha_esperada, senha):
                if not info.get("ativo", True):
                    logger_administracao.warning(
                        "Tentativa de login de usuário DESATIVADO: '%s' (credenciais corretas, mas conta desativada).",
                        usuario,
                    )
                    self._redirecionar("/login?erro=desativado")
                    return
                token = _criar_sessao(
                    usuario, bool(info.get("admin")),
                    bool(info.get("pode_manutencao_alertas")), bool(info.get("pode_relatorios_shein")),
                    bool(info.get("pode_dash_financeiro")), bool(info.get("pode_manutencao_rejeicoes")),
                    bool(info.get("pode_dados_sensiveis")), bool(info.get("pode_manutencao_relatorios")),
                    bool(info.get("pode_manutencao_usuarios")),
                    info.get("nome"), info.get("genero"),
                )
                logger_administracao.info("Login web bem-sucedido: usuário '%s'", usuario)
                self._redirecionar("/", cookie=f"session={token}; Path=/; HttpOnly; SameSite=Lax")
            else:
                logger_administracao.warning("Tentativa de login web falhou para usuário '%s'", usuario)
                self._redirecionar("/login?erro=1")
            return

        if caminho == "/alterar-senha":
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            senha_atual = dados.get("senha_atual", "")
            nova_senha = dados.get("nova_senha", "")
            confirma_senha = dados.get("confirma_senha", "")

            if not usuario or not senha_atual or not nova_senha or not confirma_senha:
                self._redirecionar("/alterar-senha?erro=campos")
                return

            info = USUARIOS_WEB.get(usuario)
            senha_esperada = info.get("senha") if info else None
            if senha_esperada is None or not secrets.compare_digest(senha_esperada, senha_atual):
                logger_administracao.warning("Tentativa de autoalteração de senha falhou (credenciais) para '%s'", usuario)
                self._redirecionar("/alterar-senha?erro=credenciais")
                return

            if nova_senha != confirma_senha:
                self._redirecionar("/alterar-senha?erro=confirmacao")
                return

            if len(nova_senha) < 4:
                self._redirecionar("/alterar-senha?erro=tamanho")
                return

            USUARIOS_WEB[usuario]["senha"] = nova_senha
            _salvar_usuarios(USUARIOS_WEB)
            # por segurança, invalida sessões já abertas desse usuário -
            # quem trocou a senha precisa logar de novo com a nova.
            for tok in [t for t, s in SESSIONS.items() if s["usuario"] == usuario]:
                SESSIONS.pop(tok, None)
            logger_administracao.info("Usuário '%s' alterou a própria senha (autoatendimento).", usuario)
            self._redirecionar("/login?senha_alterada=1")
            return

        sessao = self._sessao()
        if not sessao:
            self._enviar_json({"ok": False, "erro": "não autenticado"}, status=401)
            return

        if caminho == "/api/run_all":
            logger.info("Execução de TODOS os alertas disparada manualmente por '%s'.", sessao["usuario"])
            for state in self.job_states:
                disparar_job(state)
            self._enviar_json({"ok": True})

        elif caminho.startswith("/api/run/"):
            nome = urllib.parse.unquote(caminho[len("/api/run/"):])
            state = self.state_by_nome.get(nome)
            if state:
                logger.info("Execução do alerta '%s' disparada manualmente por '%s'.", nome, sessao["usuario"])
                disparar_job(state)
                self._enviar_json({"ok": True})
            else:
                self._enviar_json({"ok": False, "erro": "job nao encontrado"}, status=404)

        elif caminho == "/api/usuarios/senha":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_senha = dados.get("nova_senha", "")
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if not nova_senha or len(nova_senha) < 4:
                self._enviar_json({"ok": False, "erro": "senha precisa ter ao menos 4 caracteres"}, status=400)
                return
            USUARIOS_WEB[usuario]["senha"] = nova_senha
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info("Senha do usuário '%s' alterada por '%s' via painel web.", usuario, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/admin":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            novo_admin = dados.get("admin", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            admins_restantes = sum(1 for info in USUARIOS_WEB.values() if info.get("admin"))
            era_admin = bool(USUARIOS_WEB[usuario].get("admin"))
            if era_admin and not novo_admin and admins_restantes <= 1:
                self._enviar_json(
                    {"ok": False, "erro": "não é possível remover o último administrador"}, status=400
                )
                return

            USUARIOS_WEB[usuario]["admin"] = novo_admin
            _salvar_usuarios(USUARIOS_WEB)
            logger.info(
                "Papel do usuário '%s' alterado para %s por '%s' via painel web.",
                usuario, "admin" if novo_admin else "visualização", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-manutencao":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_manutencao_alertas"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            # se esse usuario tiver sessao(oes) aberta(s), atualiza na hora -
            # sem precisar ele deslogar e logar de novo pra permissao valer
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_manutencao_alertas"] = nova_permissao
            logger_administracao.info(
                "Permissão de Manutenção de Alertas em Banco do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-shein":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_relatorios_shein"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_relatorios_shein"] = nova_permissao
            logger_administracao.info(
                "Permissão de Relatórios Shein do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-dash-financeiro":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_dash_financeiro"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_dash_financeiro"] = nova_permissao
            logger_administracao.info(
                "Permissão de Atualização Dash Financeiro do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-manutencao-rejeicoes":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_manutencao_rejeicoes"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_manutencao_rejeicoes"] = nova_permissao
            logger_administracao.info(
                "Permissão de Manutenção Rejeições em Banco do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-string-connections":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_dados_sensiveis"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_dados_sensiveis"] = nova_permissao
            logger_administracao.info(
                "Permissão de String Connections do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-manutencao-relatorios":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_manutencao_relatorios"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_manutencao_relatorios"] = nova_permissao
            logger_administracao.info(
                "Permissão de Manutenção de Relatórios em Banco do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-manutencao-usuarios":
            # SEMPRE exige admin pra alterar essa permissão (igual às
            # outras) - mas repare que isso é diferente de POSSUIR a
            # permissão (_tem_acesso_manutencao_usuarios): admin não
            # ganha a permissão automaticamente, só pode CONCEDER ela
            # pra alguém (inclusive pra si mesmo).
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_manutencao_usuarios"] = nova_permissao
            _salvar_usuarios(USUARIOS_WEB)
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_manutencao_usuarios"] = nova_permissao
            logger_administracao.info(
                "Permissão de Manutenção de Usuários (Beta) do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/manutencao-usuarios/previa":
            if not _tem_acesso_manutencao_usuarios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Usuários"}, status=403)
                return
            dados = self._ler_corpo_form()
            action = dados.get("action", "")
            nome = (dados.get("nome") or "").strip()
            login = (dados.get("login") or "").strip()
            area_valor = dados.get("area", "")

            if action not in ("cad", "exc"):
                self._enviar_json({"ok": False, "erro": "Ação inválida."}, status=400)
                return
            erro_nome = _manutencao_usuarios_validar_texto("Nome", nome, 40)
            if erro_nome:
                self._enviar_json({"ok": False, "erro": erro_nome}, status=400)
                return
            erro_login = _manutencao_usuarios_validar_texto("Login", login, 255)
            if erro_login:
                self._enviar_json({"ok": False, "erro": erro_login}, status=400)
                return
            if area_valor == "todos":
                areas = MANUTENCAO_USUARIOS_AREAS
            elif area_valor in MANUTENCAO_USUARIOS_AREAS:
                areas = (area_valor,)
            else:
                self._enviar_json({"ok": False, "erro": "Área inválida."}, status=400)
                return

            try:
                targets = _manutencao_usuarios_build_targets(areas)
            except ManutencaoUsuariosConfigError as exc:
                self._enviar_json({"ok": False, "erro": _manutencao_usuarios_sanitize(exc)}, status=502)
                return

            # linhas "virtuais" (Movidesk sempre, Login do PDA se marcado)
            # na FRENTE da prévia - só preview, nenhuma chamada de API/
            # gravação acontece aqui, é só pra o operador ver TUDO que vai
            # rodar antes de confirmar (mesmo espírito da prévia de banco).
            targets_virtuais = [
                {"area": area_valor, "tenant": "Movidesk", "produto": "Pessoa (API)", "database": "(via API pública)"},
            ]
            if dados.get("incluir_pda", "") == "true":
                usuario_pda_previa = (dados.get("usuario_pda") or "").strip()
                targets_virtuais.append({
                    "area": "-", "tenant": "PDA", "produto": "Login do PDA",
                    "database": f"usuarios.json ({usuario_pda_previa or '?'})",
                })
            if action == "cad" and dados.get("enviar_boas_vindas", "") == "true":
                targets_virtuais.append({
                    "area": "-", "tenant": "E-mail", "produto": "Boas-vindas",
                    "database": f"pra {login or '?'}",
                })
            self._enviar_json({"ok": True, "targets": targets_virtuais + targets})

        elif caminho == "/api/manutencao-usuarios/executar":
            # AÇÃO REAL - INSERT/UPDATE de verdade em bancos de produção,
            # chamada de API real no Movidesk. Chega até aqui só depois
            # que o operador já viu a prévia E confirmou no navegador
            # (confirm() JS) - mesma trava em duas camadas do app
            # original (Tkinter): botão só habilita depois da prévia, e
            # ainda pede confirmação explícita antes de executar de fato.
            if not _tem_acesso_manutencao_usuarios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Usuários"}, status=403)
                return
            dados = self._ler_corpo_form()
            action = dados.get("action", "")
            nome = (dados.get("nome") or "").strip()
            login = (dados.get("login") or "").strip()
            area_valor = dados.get("area", "")
            incluir_pda = dados.get("incluir_pda", "") == "true"
            usuario_pda = (dados.get("usuario_pda") or "").strip()
            senha_pda = dados.get("senha_pda") or ""
            enviar_boas_vindas = action == "cad" and dados.get("enviar_boas_vindas", "") == "true"

            if action not in ("cad", "exc"):
                self._enviar_json({"ok": False, "erro": "Ação inválida."}, status=400)
                return
            erro_nome = _manutencao_usuarios_validar_texto("Nome", nome, 40)
            if erro_nome:
                self._enviar_json({"ok": False, "erro": erro_nome}, status=400)
                return
            erro_login = _manutencao_usuarios_validar_texto("Login", login, 255)
            if erro_login:
                self._enviar_json({"ok": False, "erro": erro_login}, status=400)
                return
            if area_valor == "todos":
                areas = MANUTENCAO_USUARIOS_AREAS
            elif area_valor in MANUTENCAO_USUARIOS_AREAS:
                areas = (area_valor,)
            else:
                self._enviar_json({"ok": False, "erro": "Área inválida."}, status=400)
                return
            if incluir_pda and not usuario_pda:
                self._enviar_json({"ok": False, "erro": "Informe o usuário do PDA (checkbox marcado)."}, status=400)
                return
            if enviar_boas_vindas and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", login):
                self._enviar_json(
                    {"ok": False, "erro": "Pra mandar o e-mail de boas-vindas, o Login precisa ser um e-mail válido."},
                    status=400,
                )
                return

            resultado = _manutencao_usuarios_executar(
                action, areas, area_valor, nome, login, sessao["usuario"],
                incluir_pda=incluir_pda, usuario_pda=usuario_pda, senha_pda=senha_pda,
                enviar_boas_vindas=enviar_boas_vindas,
            )
            self._enviar_json({"ok": True, **resultado})

        elif caminho == "/api/manutencao-usuarios/diagnostico":
            # SÓ CONSULTA - não grava nada em lugar nenhum (nem PDA, nem
            # Movidesk, nem banco). Cruza login+PDA+Movidesk+bancos pra
            # UMA pessoa só, de uma vez - pedido explícito do solicitante.
            if not _tem_acesso_manutencao_usuarios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Usuários"}, status=403)
                return
            dados = self._ler_corpo_form()
            login = (dados.get("login") or "").strip()
            if not login:
                self._enviar_json({"ok": False, "erro": "Informe o login pra diagnosticar."}, status=400)
                return
            resultado = _manutencao_usuarios_diagnostico(login)
            self._enviar_json({"ok": True, **resultado})

        elif caminho == "/api/config-seguro/definir":
            if not _tem_acesso_dados_sensiveis(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Dados Sensíveis"}, status=403)
                return
            dados = self._ler_corpo_form()
            chave = dados.get("chave", "").strip()
            valor = dados.get("valor", "")
            if not chave or "::" not in chave:
                self._enviar_json(
                    {"ok": False, "erro": "chave inválida (use o formato origem::campo, ex.: saas::db_password)"},
                    status=400,
                )
                return
            if not valor:
                self._enviar_json({"ok": False, "erro": "informe um valor"}, status=400)
                return
            _definir_valor_config_dat(chave, valor)
            logger_administracao.info("Chave '%s' definida/atualizada em config.dat por '%s'.", chave, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/config-seguro/remover":
            if not _tem_acesso_dados_sensiveis(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Dados Sensíveis"}, status=403)
                return
            dados = self._ler_corpo_form()
            chave = dados.get("chave", "").strip()
            removido = _remover_valor_config_dat(chave)
            if removido:
                logger_administracao.info(
                    "Chave '%s' removida de config.dat por '%s' (volta a usar o valor do .env, se houver).",
                    chave, sessao["usuario"],
                )
            self._enviar_json({"ok": True, "removido": removido})

        elif caminho == "/api/usuarios/alterar-status":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            novo_ativo = dados.get("ativo", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if usuario == sessao["usuario"] and not novo_ativo:
                self._enviar_json({"ok": False, "erro": "você não pode desativar seu próprio usuário"}, status=400)
                return
            USUARIOS_WEB[usuario]["ativo"] = novo_ativo
            _salvar_usuarios(USUARIOS_WEB)
            if not novo_ativo:
                # derruba qualquer sessao ja aberta desse usuario na hora -
                # nao adianta desativar e a pessoa continuar logada
                for token in [t for t, s in SESSIONS.items() if s["usuario"] == usuario]:
                    SESSIONS.pop(token, None)
            logger_administracao.info(
                "Usuário '%s' %s por '%s'.",
                usuario, "reativado" if novo_ativo else "desativado", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/alterar-nome":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            novo_nome = dados.get("nome", "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if not novo_nome:
                self._enviar_json({"ok": False, "erro": "o nome não pode ficar em branco"}, status=400)
                return
            if len(novo_nome) > 80:
                self._enviar_json({"ok": False, "erro": "nome muito longo (máximo 80 caracteres)"}, status=400)
                return
            nome_antigo = USUARIOS_WEB[usuario].get("nome") or usuario
            USUARIOS_WEB[usuario]["nome"] = novo_nome
            _salvar_usuarios(USUARIOS_WEB)
            # atualiza na hora qualquer sessao ja aberta desse usuario, pra
            # o "Bem-vindo" mudar sem precisar deslogar e logar de novo
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["nome"] = novo_nome
            logger_administracao.info(
                "Nome de exibição do usuário '%s' alterado de '%s' pra '%s' por '%s'.",
                usuario, nome_antigo, novo_nome, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/alterar-email":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            novo_email = dados.get("email", "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            # e-mail é opcional (pode ficar em branco) - só valida formato
            # básico quando preenchido
            if novo_email and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", novo_email):
                self._enviar_json({"ok": False, "erro": "e-mail inválido"}, status=400)
                return
            USUARIOS_WEB[usuario]["email"] = novo_email
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info(
                "E-mail do usuário '%s' alterado pra '%s' por '%s'.",
                usuario, novo_email or "(em branco)", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/alterar-data-inicio":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_data = (dados.get("data_inicio") or "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            # opcional (pode ficar em branco) - formato AAAA-MM-DD (o mesmo
            # que <input type="date"> já manda)
            if nova_data:
                try:
                    datetime.strptime(nova_data, "%Y-%m-%d")
                except ValueError:
                    self._enviar_json({"ok": False, "erro": "data inválida"}, status=400)
                    return
            USUARIOS_WEB[usuario]["data_inicio"] = nova_data or None
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info(
                "Data de início do usuário '%s' alterada pra '%s' por '%s'.",
                usuario, nova_data or "(em branco)", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/renomear":
            # Troca a CHAVE PRIMÁRIA (o login) de uma pessoa - operação
            # delicada, propaga pra todo lugar que referencia "usuario"
            # como identidade (feedbacks, histórico de carreira, sessão
            # ativa). Pedido do solicitante em 10/09/2026: padronizar o mesmo
            # nome de usuário entre o PDA e os webmonitors, pra facilitar
            # desativação de quem sai da empresa.
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario_antigo = dados.get("usuario_atual", "")
            usuario_novo = (dados.get("usuario_novo") or "").strip()
            if usuario_antigo not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if not usuario_novo or not re.match(r"^[A-Za-z0-9_.\-]+$", usuario_novo):
                self._enviar_json({"ok": False, "erro": "novo usuário inválido (use apenas letras, números, . _ -)"}, status=400)
                return
            if usuario_novo == usuario_antigo:
                self._enviar_json({"ok": False, "erro": "o novo usuário é igual ao atual"}, status=400)
                return
            if usuario_novo in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "já existe um usuário com esse nome"}, status=400)
                return

            # 1) usuarios.json - move o valor pra chave nova, remove a antiga
            USUARIOS_WEB[usuario_novo] = USUARIOS_WEB.pop(usuario_antigo)
            _salvar_usuarios(USUARIOS_WEB)

            # 2) feedbacks - tanto quem RECEBEU quanto quem foi o AUTOR
            feedbacks_afetados = 0
            for f in FEEDBACKS_USUARIOS:
                if f.get("usuario") == usuario_antigo:
                    f["usuario"] = usuario_novo
                    feedbacks_afetados += 1
                if f.get("autor") == usuario_antigo:
                    f["autor"] = usuario_novo
                    feedbacks_afetados += 1
            if feedbacks_afetados:
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            # 3) histórico de carreira
            historico_afetado = 0
            for h in HISTORICO_CARREIRA:
                if h.get("usuario") == usuario_antigo:
                    h["usuario"] = usuario_novo
                    historico_afetado += 1
            if historico_afetado:
                _salvar_historico_carreira(HISTORICO_CARREIRA)

            # 4) sessão ativa - derruba (mais simples/seguro que tentar
            # "migrar" o token no meio de uma sessão em andamento; a
            # pessoa só precisa logar de novo com o usuário novo)
            for token in [t for t, s in SESSIONS.items() if s["usuario"] == usuario_antigo]:
                SESSIONS.pop(token, None)

            logger_administracao.info(
                "Usuário renomeado de '%s' pra '%s' por '%s' (%d feedback(s), %d entrada(s) de histórico afetadas).",
                usuario_antigo, usuario_novo, sessao["usuario"], feedbacks_afetados, historico_afetado,
            )
            self._enviar_json({"ok": True, "usuario_novo": usuario_novo})

        elif caminho == "/api/usuarios/enviar-boas-vindas":
            # Requer a mesma permissão restrita da Manutenção de Usuários
            # (não basta ser admin comum) - envia de verdade pro e-mail
            # cadastrado da pessoa, então trata como ação sensível.
            if not _tem_acesso_manutencao_usuarios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Usuários"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            info_usuario = USUARIOS_WEB[usuario]
            email_destino = (info_usuario.get("email") or "").strip()
            if not email_destino:
                self._enviar_json({"ok": False, "erro": "esse usuário ainda não tem e-mail vinculado"}, status=400)
                return
            nome_pessoa = info_usuario.get("nome") or usuario
            # Senha REAL da pessoa (a que está de fato salva no
            # usuarios.json pro login dela no PDA) - não a senha padrão
            # de cadastro em banco (essa só faz sentido no fluxo de
            # Cadastro, onde é literalmente a senha sendo definida).
            senha_real = info_usuario.get("senha") or MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL
            try:
                # `usuario` (a chave do dict, ex.: "admin") é o LOGIN de
                # verdade - o mesmo que aparece na aba Usuários. O e-mail
                # cadastrado é só o ENDEREÇO de entrega, não o login -
                # eram tratados como a mesma coisa por engano antes.
                _enviar_email_boas_vindas(nome_pessoa, email_destino, usuario, senha_real)
            except Exception as exc:
                logger.exception("Falha ao enviar e-mail de boas-vindas pra '%s'", usuario)
                self._enviar_json({"ok": False, "erro": f"Falha ao enviar: {exc}"}, status=502)
                return
            logger_administracao.info(
                "E-mail de boas-vindas enviado pra '%s' (%s) por '%s'.",
                nome_pessoa, email_destino, sessao["usuario"],
            )
            self._enviar_json({"ok": True, "email": email_destino})

        elif caminho == "/api/usuarios/alterar-atribuicao":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_atribuicao = dados.get("atribuicao", "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if nova_atribuicao not in ("Suporte", "Monitoramento"):
                self._enviar_json({"ok": False, "erro": "atribuição inválida"}, status=400)
                return
            USUARIOS_WEB[usuario]["atribuicao"] = nova_atribuicao
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info(
                "Atribuição do usuário '%s' alterada pra '%s' por '%s'.",
                usuario, nova_atribuicao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/alterar-genero":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            novo_genero = dados.get("genero", "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if novo_genero not in ("M", "F", ""):
                self._enviar_json({"ok": False, "erro": "gênero inválido"}, status=400)
                return
            USUARIOS_WEB[usuario]["genero"] = novo_genero
            _salvar_usuarios(USUARIOS_WEB)
            # atualiza na hora qualquer sessao ja aberta desse usuario, pra
            # a saudacao/badge mudarem sem precisar deslogar e logar de novo
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["genero"] = novo_genero
            logger_administracao.info(
                "Gênero do usuário '%s' alterado pra '%s' por '%s'.",
                usuario, novo_genero or "(não informado)", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/upload-foto":
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            foto_data_url = dados.get("foto", "")

            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            # a propria pessoa pode trocar a sua foto; admin pode trocar a
            # de qualquer um
            if sessao["usuario"] != usuario and not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "você só pode alterar a sua própria foto"}, status=403)
                return
            if not foto_data_url:
                self._enviar_json({"ok": False, "erro": "nenhuma imagem enviada"}, status=400)
                return

            erro = _salvar_foto_usuario(usuario, foto_data_url)
            if erro:
                self._enviar_json({"ok": False, "erro": erro}, status=400)
                return
            logger_administracao.info("Foto de perfil de '%s' atualizada por '%s'.", usuario, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/ferias/criar":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            global _proximo_id_ferias
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            inicio = dados.get("inicio", "")
            fim = dados.get("fim", "")
            tipo = dados.get("tipo", "ferias").strip() or "ferias"

            if tipo not in ("ferias", "day_off", "atestado"):
                self._enviar_json({"ok": False, "erro": "tipo inválido"}, status=400)
                return
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            try:
                dt_inicio = datetime.strptime(inicio, "%Y-%m-%d").date()
                dt_fim = datetime.strptime(fim, "%Y-%m-%d").date()
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "datas inválidas"}, status=400)
                return
            if dt_fim < dt_inicio:
                self._enviar_json({"ok": False, "erro": "a data final não pode ser antes da inicial"}, status=400)
                return

            with _lock_ferias:
                conflito = next(
                    (f for f in FERIAS if f["usuario"] == usuario and _periodos_se_sobrepoem(f["inicio"], f["fim"], inicio, fim)),
                    None,
                )
                if conflito:
                    tipo_conflito = conflito.get("tipo")
                    rotulo_conflito = {"day_off": "Day Off", "atestado": "atestado"}.get(tipo_conflito, "férias")
                    self._enviar_json(
                        {"ok": False, "erro": f"já existe {rotulo_conflito} cadastrada(s) pra essa pessoa entre {conflito['inicio']} e {conflito['fim']}, que se sobrepõe"},
                        status=409,
                    )
                    return
                registro = {
                    "id": _proximo_id_ferias, "usuario": usuario, "inicio": inicio, "fim": fim, "tipo": tipo,
                    "criado_por": sessao["usuario"], "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                FERIAS.append(registro)
                _proximo_id_ferias += 1
                _salvar_ferias(FERIAS)

            nome_pessoa = USUARIOS_WEB[usuario].get("nome") or usuario
            logger_administracao.info(
                "Férias cadastradas pra '%s' (%s a %s) por '%s'.", nome_pessoa, inicio, fim, sessao["usuario"],
            )
            self._enviar_json({"ok": True, "registro": registro})

        elif caminho == "/api/ferias/excluir":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_registro = int(dados.get("id", ""))
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return

            with _lock_ferias:
                registro = next((f for f in FERIAS if f["id"] == id_registro), None)
                if not registro:
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                FERIAS.remove(registro)
                _salvar_ferias(FERIAS)

            nome_pessoa = USUARIOS_WEB.get(registro["usuario"], {}).get("nome") or registro["usuario"]
            logger_administracao.info(
                "Férias de '%s' (%s a %s) removidas por '%s'.",
                nome_pessoa, registro["inicio"], registro["fim"], sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/historico-carreira/criar":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            global _proximo_id_historico_carreira
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            cargo = (dados.get("cargo") or "").strip()
            area = dados.get("area", "")
            inicio = dados.get("inicio", "")
            fim = (dados.get("fim") or "").strip()

            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            if not cargo or len(cargo) > 60:
                self._enviar_json({"ok": False, "erro": "informe um cargo válido (até 60 caracteres)"}, status=400)
                return
            if area not in ("suporte", "monitoramento", ""):
                self._enviar_json({"ok": False, "erro": "área inválida"}, status=400)
                return
            # "AAAA-MM" (mês/ano) - mais simples que dia exato, já que
            # mudança de cargo normalmente não tem um "dia" específico
            if not re.match(r"^\d{4}-\d{2}$", inicio):
                self._enviar_json({"ok": False, "erro": "data de início inválida (use mês/ano)"}, status=400)
                return
            if fim and not re.match(r"^\d{4}-\d{2}$", fim):
                self._enviar_json({"ok": False, "erro": "data de fim inválida (use mês/ano, ou deixe em branco pro cargo atual)"}, status=400)
                return
            if fim and fim < inicio:
                self._enviar_json({"ok": False, "erro": "a data de fim não pode ser antes do início"}, status=400)
                return

            with _lock_historico_carreira:
                registro = {
                    "id": _proximo_id_historico_carreira, "usuario": usuario, "cargo": cargo,
                    "area": area, "inicio": inicio, "fim": fim or None,
                    "criado_por": sessao["usuario"], "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                HISTORICO_CARREIRA.append(registro)
                _proximo_id_historico_carreira += 1
                _salvar_historico_carreira(HISTORICO_CARREIRA)

            nome_pessoa = USUARIOS_WEB[usuario].get("nome") or usuario
            logger_administracao.info(
                "Histórico de carreira: '%s' adicionado pra '%s' (%s a %s) por '%s'.",
                cargo, nome_pessoa, inicio, fim or "atual", sessao["usuario"],
            )
            self._enviar_json({"ok": True, "registro": registro})

        elif caminho == "/api/historico-carreira/excluir":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_registro = int(dados.get("id", ""))
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return

            with _lock_historico_carreira:
                registro = next((h for h in HISTORICO_CARREIRA if h["id"] == id_registro), None)
                if not registro:
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                HISTORICO_CARREIRA.remove(registro)
                _salvar_historico_carreira(HISTORICO_CARREIRA)

            nome_pessoa = USUARIOS_WEB.get(registro["usuario"], {}).get("nome") or registro["usuario"]
            logger_administracao.info(
                "Histórico de carreira: '%s' removido de '%s' por '%s'.",
                registro["cargo"], nome_pessoa, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/feedback-usuario/criar":
            dados = self._ler_corpo_form()
            usuario_alvo = dados.get("usuario", "")
            texto = (dados.get("texto") or "").strip()
            nota_bruta = (dados.get("nota") or "").strip()
            tipo = dados.get("tipo") or "Feedback"
            link_canva = (dados.get("link_canva") or "").strip()

            if not _tem_acesso_feedback_usuario(sessao, usuario_alvo):
                self._enviar_json({"ok": False, "erro": "sem permissão pra adicionar feedback dessa pessoa"}, status=403)
                return
            if not texto or len(texto) > 2000:
                self._enviar_json({"ok": False, "erro": "informe um texto de até 2000 caracteres"}, status=400)
                return
            if tipo not in ("Feedback", "Alinhamento"):
                self._enviar_json({"ok": False, "erro": "tipo inválido"}, status=400)
                return
            if link_canva and not re.match(r"^https?://", link_canva):
                self._enviar_json({"ok": False, "erro": "link do Canva precisa começar com http:// ou https://"}, status=400)
                return
            nota = None
            if nota_bruta:
                try:
                    nota = int(nota_bruta)
                except ValueError:
                    nota = -1
                if nota < 1 or nota > 5:
                    self._enviar_json({"ok": False, "erro": "nota precisa ser de 1 a 5 (ou deixe em branco)"}, status=400)
                    return

            global _proximo_id_feedback_usuario
            with _lock_feedbacks_usuarios:
                registro = {
                    "id": _proximo_id_feedback_usuario, "usuario": usuario_alvo,
                    "autor": sessao["usuario"], "autor_nome": USUARIOS_WEB.get(sessao["usuario"], {}).get("nome") or sessao["usuario"],
                    "tipo": tipo, "texto": texto, "nota": nota, "link_canva": link_canva or None,
                    "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                FEEDBACKS_USUARIOS.append(registro)
                _proximo_id_feedback_usuario += 1
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            nome_pessoa = USUARIOS_WEB.get(usuario_alvo, {}).get("nome") or usuario_alvo
            logger_administracao.info(
                "%s adicionado sobre '%s' por '%s' (equipe %s, nota %s).",
                tipo, nome_pessoa, sessao["usuario"], USUARIOS_WEB.get(sessao["usuario"], {}).get("atribuicao"), nota,
            )
            _notificar_feedback_inserido(registro["autor_nome"], tipo, registro["criado_em"], usuario_alvo, nome_pessoa)
            self._enviar_json({"ok": True, "registro": registro})

        elif caminho == "/api/feedback-usuario/editar":
            dados = self._ler_corpo_form()
            try:
                id_registro = int(dados.get("id", ""))
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            texto = (dados.get("texto") or "").strip()
            nota_bruta = (dados.get("nota") or "").strip()
            tipo = dados.get("tipo") or "Feedback"
            link_canva = (dados.get("link_canva") or "").strip()

            if not texto or len(texto) > 2000:
                self._enviar_json({"ok": False, "erro": "informe um texto de até 2000 caracteres"}, status=400)
                return
            if tipo not in ("Feedback", "Alinhamento"):
                self._enviar_json({"ok": False, "erro": "tipo inválido"}, status=400)
                return
            if link_canva and not (link_canva.startswith("http://") or link_canva.startswith("https://")):
                self._enviar_json({"ok": False, "erro": "link do Canva precisa começar com http:// ou https://"}, status=400)
                return
            nota = None
            if nota_bruta:
                try:
                    nota = int(nota_bruta)
                except ValueError:
                    nota = -1
                if nota < 1 or nota > 5:
                    self._enviar_json({"ok": False, "erro": "nota precisa ser de 1 a 5 (ou deixe em branco)"}, status=400)
                    return

            with _lock_feedbacks_usuarios:
                registro = next((f for f in FEEDBACKS_USUARIOS if f["id"] == id_registro), None)
                if not registro:
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                # mesma checagem de acesso da exclusão - qualquer admin
                # consegue editar, não só quem escreveu originalmente
                if not _tem_acesso_feedback_usuario(sessao, registro["usuario"]):
                    self._enviar_json({"ok": False, "erro": "sem permissão pra editar esse feedback"}, status=403)
                    return
                registro["texto"] = texto
                registro["nota"] = nota
                registro["tipo"] = tipo
                registro["link_canva"] = link_canva or None
                registro["editado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                registro["editado_por"] = sessao["usuario"]
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            logger_administracao.info(
                "%s (id %d, sobre '%s') editado por '%s'.",
                tipo, id_registro, registro["usuario"], sessao["usuario"],
            )
            self._enviar_json({"ok": True, "registro": registro})

        elif caminho == "/api/feedback-usuario/excluir":
            dados = self._ler_corpo_form()
            try:
                id_registro = int(dados.get("id", ""))
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return

            with _lock_feedbacks_usuarios:
                registro = next((f for f in FEEDBACKS_USUARIOS if f["id"] == id_registro), None)
                if not registro:
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                # mesma checagem de acesso (admin de mesma equipe da PESSOA
                # DO FEEDBACK, não necessariamente quem escreveu) - qualquer
                # admin do time consegue remover, não só o autor original
                if not _tem_acesso_feedback_usuario(sessao, registro["usuario"]):
                    self._enviar_json({"ok": False, "erro": "sem permissão pra remover esse feedback"}, status=403)
                    return
                FEEDBACKS_USUARIOS.remove(registro)
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            logger_administracao.info(
                "Feedback (id %d, sobre '%s') removido por '%s'.",
                id_registro, registro["usuario"], sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/vincular-movidesk":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            id_movidesk = dados.get("id_movidesk", "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["usuario_movidesk_id"] = id_movidesk or None
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info(
                "Usuário '%s' vinculado ao ID '%s' da tabela usuarios (banco movidesk) por '%s'.",
                usuario, id_movidesk or "(desvinculado)", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios-movidesk/atualizar":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            id_usuario_movidesk = dados.get("id", "").strip()
            if not id_usuario_movidesk:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            dias_validos = {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"}
            dias_marcados = [d for d in dados.get("diasTrabalhados", "").split(",") if d.strip()]
            if any(d not in dias_validos for d in dias_marcados):
                self._enviar_json({"ok": False, "erro": "dia da semana inválido em diasTrabalhados"}, status=400)
                return
            escalas_validas = {"5x2", "6x1", "12x36", "ESTAGIO", "ESCALA_ARA"}
            escala_enviada = dados.get("escala", "").strip()
            if escala_enviada and escala_enviada not in escalas_validas:
                self._enviar_json({"ok": False, "erro": "escala inválida"}, status=400)
                return
            resultado = _atualizar_usuario_movidesk(id_usuario_movidesk, {
                "cargo": dados.get("cargo", "").strip(),
                "email": dados.get("email", "").strip(),
                "escala": escala_enviada,
                "horainicio": dados.get("horainicio", "").strip(),
                "horafim": dados.get("horafim", "").strip(),
                "diasTrabalhados": ",".join(dias_marcados),
            }, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/usuarios/criar":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "").strip()
            senha = dados.get("senha", "")
            novo_admin = dados.get("admin", "") == "true"
            pode_manutencao = dados.get("pode_manutencao_alertas", "") == "true"
            pode_shein = dados.get("pode_relatorios_shein", "") == "true"
            pode_dash = dados.get("pode_dash_financeiro", "") == "true"
            pode_rejeicoes = dados.get("pode_manutencao_rejeicoes", "") == "true"
            pode_string_conn = dados.get("pode_dados_sensiveis", "") == "true"
            pode_relatorios = dados.get("pode_manutencao_relatorios", "") == "true"
            pode_manutencao_usuarios = dados.get("pode_manutencao_usuarios", "") == "true"

            if not usuario or not re.match(r"^[A-Za-z0-9_.\-]+$", usuario):
                self._enviar_json(
                    {"ok": False, "erro": "usuário inválido (use apenas letras, números, . _ -)"}, status=400
                )
                return
            if any(u.lower() == usuario.lower() for u in USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "esse usuário já existe"}, status=400)
                return
            if not senha or len(senha) < 4:
                self._enviar_json({"ok": False, "erro": "a senha precisa ter ao menos 4 caracteres"}, status=400)
                return

            USUARIOS_WEB[usuario] = {
                "senha": senha, "admin": novo_admin,
                "pode_manutencao_alertas": pode_manutencao, "pode_relatorios_shein": pode_shein,
                "pode_dash_financeiro": pode_dash, "pode_manutencao_rejeicoes": pode_rejeicoes,
                "pode_dados_sensiveis": pode_string_conn, "pode_manutencao_relatorios": pode_relatorios,
                "pode_manutencao_usuarios": pode_manutencao_usuarios,
            }
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info(
                "Usuário '%s' criado (papel: %s) por '%s' via painel web.",
                usuario, "admin" if novo_admin else "visualização", sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/deletar":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            admins_restantes = sum(1 for info in USUARIOS_WEB.values() if info.get("admin"))
            era_admin = bool(USUARIOS_WEB[usuario].get("admin"))
            if era_admin and admins_restantes <= 1:
                self._enviar_json(
                    {"ok": False, "erro": "não é possível excluir o último administrador"}, status=400
                )
                return

            del USUARIOS_WEB[usuario]
            _salvar_usuarios(USUARIOS_WEB)
            # remove qualquer sessão ativa desse usuário - ele deixa de existir agora
            for tok in [t for t, s in SESSIONS.items() if s["usuario"] == usuario]:
                SESSIONS.pop(tok, None)
            logger_administracao.info("Usuário '%s' excluído por '%s' via painel web.", usuario, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/contingencias/atualizar":
            iniciou = _monitor_contingencias_ref.forcar_atualizacao() if _monitor_contingencias_ref else False
            if iniciou:
                logger_administracao.info("Atualização manual de Contingências disparada por '%s'.", sessao["usuario"])
                self._enviar_json({"ok": True})
            else:
                self._enviar_json({"ok": False, "erro": "já tem uma verificação em andamento - aguarde terminar"}, status=409)

        elif caminho == "/api/string-connections/criar":
            if not _tem_acesso_dados_sensiveis(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra String Connections"}, status=403)
                return
            dados = self._ler_corpo_form()
            cliente = dados.get("cliente", "").strip()
            produto = dados.get("produto", "").strip()
            conexao = dados.get("conexao", "").strip()
            if not cliente or not produto or not conexao:
                self._enviar_json({"ok": False, "erro": "preencha cliente, produto e conexão"}, status=400)
                return

            global _proximo_id_string_connection
            novo_id = str(_proximo_id_string_connection)
            _proximo_id_string_connection += 1
            STRING_CONNECTIONS[novo_id] = {
                "cliente": cliente, "produto": produto, "conexao": conexao,
                "criado_por": sessao["usuario"], "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            _salvar_string_connections(STRING_CONNECTIONS)
            logger_administracao.info(
                "String Connection criada: cliente=%s produto=%s por '%s'.", cliente, produto, sessao["usuario"]
            )
            self._enviar_json({"ok": True, "id": novo_id})

        elif caminho == "/api/string-connections/atualizar":
            if not _tem_acesso_dados_sensiveis(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra String Connections"}, status=403)
                return
            dados = self._ler_corpo_form()
            id_conexao = dados.get("id", "")
            if id_conexao not in STRING_CONNECTIONS:
                self._enviar_json({"ok": False, "erro": "não encontrada"}, status=404)
                return
            cliente = dados.get("cliente", "").strip()
            produto = dados.get("produto", "").strip()
            conexao = dados.get("conexao", "").strip()
            if not cliente or not produto or not conexao:
                self._enviar_json({"ok": False, "erro": "preencha cliente, produto e conexão"}, status=400)
                return
            STRING_CONNECTIONS[id_conexao].update({"cliente": cliente, "produto": produto, "conexao": conexao})
            _salvar_string_connections(STRING_CONNECTIONS)
            logger_administracao.info("String Connection #%s atualizada por '%s'.", id_conexao, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/string-connections/deletar":
            if not _tem_acesso_dados_sensiveis(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra String Connections"}, status=403)
                return
            dados = self._ler_corpo_form()
            id_conexao = dados.get("id", "")
            if id_conexao not in STRING_CONNECTIONS:
                self._enviar_json({"ok": False, "erro": "não encontrada"}, status=404)
                return
            del STRING_CONNECTIONS[id_conexao]
            _salvar_string_connections(STRING_CONNECTIONS)
            logger_administracao.info("String Connection #%s excluída por '%s'.", id_conexao, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/relatorios-shein/gerar":
            if not _tem_acesso_relatorios_shein(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            dados = self._ler_corpo_form()
            logger_shein.info("Geração manual do relatório de %s disparada por '%s'.", dados.get("data", "?"), sessao["usuario"])
            resultado = _gerar_relatorio_shein(dados.get("data", ""))
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/relatorios-shein/forcar-automatico":
            if not _tem_acesso_relatorios_shein(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            logger_shein.info("Execução automática diária forçada manualmente por '%s'.", sessao["usuario"])
            threading.Thread(target=_executar_relatorio_shein_diario, daemon=True).start()
            self._enviar_json({"ok": True})

        elif caminho == "/api/emailpack/executar":
            iniciou = _monitor_emailpack_ref.forcar_atualizacao() if _monitor_emailpack_ref else False
            if iniciou:
                logger_emailpack.info("Execução manual disparada por '%s'.", sessao["usuario"])
                self._enviar_json({"ok": True})
            else:
                self._enviar_json({"ok": False, "erro": "já tem uma execução em andamento - aguarde ela terminar"}, status=409)

        elif caminho == "/api/emailpack/ignorar":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            email = dados.get("email", "").strip()
            if not email:
                self._enviar_json({"ok": False, "erro": "e-mail vazio"}, status=400)
                return
            with _lock_emails_emailpack:
                ignorados = _carregar_emails_ignorados_emailpack()
                ignorados.add(email)
                _salvar_emails_ignorados_emailpack(ignorados)
            logger_emailpack.info("E-mail '%s' adicionado à lista de ignorados por '%s'.", email, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/emailpack/remover-ignorado":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            email = dados.get("email", "").strip()
            with _lock_emails_emailpack:
                ignorados = _carregar_emails_ignorados_emailpack()
                ignorados.discard(email)
                _salvar_emails_ignorados_emailpack(ignorados)
            logger_emailpack.info("E-mail '%s' removido da lista de ignorados por '%s'.", email, sessao["usuario"])
            self._enviar_json({"ok": True})

        elif caminho == "/api/dash-financeiro/executar":
            if not _tem_acesso_dash_financeiro(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            global _dash_financeiro_execucao_ativa
            with _lock_dash_financeiro:
                if _dash_financeiro_execucao_ativa:
                    self._enviar_json({"ok": False, "erro": "já tem uma execução em andamento - aguarde ela terminar"}, status=409)
                    return
                _dash_financeiro_execucao_ativa = True
            logger_dash_financeiro.info("Execução manual disparada por '%s'.", sessao["usuario"])
            threading.Thread(target=_executar_todos_dash_financeiro, daemon=True).start()
            self._enviar_json({"ok": True})

        elif caminho == "/api/manutencao-alertas/criar":
            if not _tem_acesso_manutencao_alertas(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Alertas em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            erro_validacao = _validar_dados_alerta_banco(dados)
            if erro_validacao:
                self._enviar_json({"ok": False, "erro": erro_validacao}, status=400)
                return

            dados_normalizados = dict(dados)
            dados_normalizados["tipo_banco"] = dados["tipo_banco"].strip().upper()
            dados_normalizados["disponibilidade"] = 1 if dados.get("disponibilidade") == "true" else 0

            resultado = _criar_alerta_banco(dados_normalizados, sessao["usuario"])
            if resultado.get("ok"):
                resultado["gatilho"] = _montar_texto_gatilho(dados["cliente"], dados["titulo"])
                self._enviar_json(resultado)
            else:
                self._enviar_json(resultado, status=502)

        elif caminho == "/api/manutencao-alertas/disponibilidade":
            if not _tem_acesso_manutencao_alertas(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Alertas em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_alerta = int(dados.get("id", ""))
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            novo_valor = 1 if dados.get("disponibilidade") == "true" else 0
            resultado = _alternar_disponibilidade_banco(id_alerta, novo_valor, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-alertas/atualizar":
            if not _tem_acesso_manutencao_alertas(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Alertas em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_alerta = int(dados.get("id", ""))
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            erro_validacao = _validar_dados_alerta_banco(dados)
            if erro_validacao:
                self._enviar_json({"ok": False, "erro": erro_validacao}, status=400)
                return

            dados_normalizados = dict(dados)
            dados_normalizados["tipo_banco"] = dados["tipo_banco"].strip().upper()
            dados_normalizados["disponibilidade"] = 1 if dados.get("disponibilidade") == "true" else 0

            resultado = _atualizar_alerta_banco(id_alerta, dados_normalizados, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-rejeicoes/criar":
            if not _tem_acesso_manutencao_rejeicoes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção Rejeições em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            erro_validacao = _validar_dados_rejeicao_banco(dados)
            if erro_validacao:
                self._enviar_json({"ok": False, "erro": erro_validacao}, status=400)
                return

            dados_normalizados = dict(dados)
            dados_normalizados["tipo_banco"] = dados["tipo_banco"].strip().upper()

            resultado = _criar_rejeicao_banco(dados_normalizados, sessao["usuario"])
            if resultado.get("ok"):
                resultado["gatilho"] = _montar_texto_gatilho_rejeicao(dados["cliente"])
                self._enviar_json(resultado)
            else:
                self._enviar_json(resultado, status=502)

        elif caminho == "/api/manutencao-rejeicoes/atualizar":
            if not _tem_acesso_manutencao_rejeicoes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção Rejeições em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_rejeicao = int(dados.get("id", ""))
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            erro_validacao = _validar_dados_rejeicao_banco(dados)
            if erro_validacao:
                self._enviar_json({"ok": False, "erro": erro_validacao}, status=400)
                return

            dados_normalizados = dict(dados)
            dados_normalizados["tipo_banco"] = dados["tipo_banco"].strip().upper()

            resultado = _atualizar_rejeicao_banco(id_rejeicao, dados_normalizados, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-rejeicoes/excluir":
            if not _tem_acesso_manutencao_rejeicoes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção Rejeições em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_rejeicao = int(dados.get("id", ""))
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            resultado = _excluir_rejeicao_banco(id_rejeicao, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-relatorios/criar":
            if not _tem_acesso_manutencao_relatorios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Relatórios em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            erro_validacao = _validar_dados_relatorio_banco(dados)
            if erro_validacao:
                self._enviar_json({"ok": False, "erro": erro_validacao}, status=400)
                return

            dados_normalizados = dict(dados)
            dados_normalizados["tipo_banco"] = dados["tipo_banco"].strip().upper()
            dados_normalizados["modelo_arquivo"] = dados["modelo_arquivo"].strip().upper()
            dados_normalizados["reincidencia"] = dados["reincidencia"].strip().upper()
            dados_normalizados["disponibilidade"] = 1 if dados.get("disponibilidade") == "true" else 0

            resultado = _criar_relatorio_banco(dados_normalizados, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-relatorios/atualizar":
            if not _tem_acesso_manutencao_relatorios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Relatórios em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_relatorio = int(dados.get("id", ""))
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            erro_validacao = _validar_dados_relatorio_banco(dados)
            if erro_validacao:
                self._enviar_json({"ok": False, "erro": erro_validacao}, status=400)
                return

            dados_normalizados = dict(dados)
            dados_normalizados["tipo_banco"] = dados["tipo_banco"].strip().upper()
            dados_normalizados["modelo_arquivo"] = dados["modelo_arquivo"].strip().upper()
            dados_normalizados["reincidencia"] = dados["reincidencia"].strip().upper()
            dados_normalizados["disponibilidade"] = 1 if dados.get("disponibilidade") == "true" else 0

            resultado = _atualizar_relatorio_banco(id_relatorio, dados_normalizados, sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/manutencao-relatorios/disponibilidade":
            if not _tem_acesso_manutencao_relatorios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Relatórios em Banco"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_relatorio = int(dados.get("id", ""))
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            resultado = _alterar_disponibilidade_relatorio(id_relatorio, dados.get("ativo") == "true", sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        else:
            self.send_response(404)
            self.end_headers()


def obter_ip_local() -> str:
    """Melhor esforço para achar o IP da máquina na rede local (não faz
    nenhuma conexão de verdade, só usa o SO pra descobrir qual interface
    seria usada)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# Assim que existir um registro de DNS interno (ou entrada em hosts) apontando
# esse nome para o IP desta máquina, é só preencher aqui - o servidor já
# aceita conexão por qualquer nome/IP que chegue nele, não precisa mudar mais
# nada. Deixe None para mostrar o nome de máquina "cru" (ex.: SRV-EXEMPLO01).
NOME_AMIGAVEL_WEB: Optional[str] = os.environ.get("PDA_NOME_AMIGAVEL_WEB") or None  # ver LEIA-ME sobre como fazer esse nome resolver de verdade


def iniciar_servidor_web(job_states: List[JobState], porta: int = 8765) -> Optional[str]:
    """Sobe o servidor web numa thread separada. Retorna a URL de acesso,
    ou None se não conseguiu subir o servidor (ex.: porta ocupada)."""
    _PainelHTTPHandler.job_states = job_states
    _PainelHTTPHandler.state_by_nome = {s.job.nome: s for s in job_states}

    try:
        servidor = ThreadingHTTPServer(("0.0.0.0", porta), _PainelHTTPHandler)
    except OSError as e:
        logger.error("Não foi possível subir o servidor web na porta %d: %s", porta, e)
        return None

    thread = threading.Thread(target=servidor.serve_forever, daemon=True)
    thread.start()

    hostname = socket.gethostname()
    ip = obter_ip_local()
    nome_exibido = NOME_AMIGAVEL_WEB or hostname
    logger.info(
        "Servidor web disponível em http://%s:%d/ (ou http://%s:%d/ / http://%s:%d/)",
        nome_exibido, porta, hostname, porta, ip, porta,
    )
    return f"http://{nome_exibido}:{porta}/"


# ---------------------------------------------------------------------------
# GUI (dark theme) - mesma paleta do PDA Web (ver --bg/--fg/--teal/etc. no
# CSS dos templates), pra a janela desktop e a versão web parecerem a
# mesma marca em vez de dois temas escuros genéricos diferentes.
# ---------------------------------------------------------------------------
BG = "#0b0f14"
BG_PANEL = "#181f27"
FG = "#e6edf3"
FG_DIM = "#8b98a5"
ACCENT = "#2db8cf"
COLOR_OK = "#4ec9b0"
COLOR_ERR = "#f14c4c"
COLOR_RUN = "#dcdcaa"
COLOR_WAIT = "#808080"
BORDER = "#2a323c"
LIME = "#b0cb1c"  # segunda cor do gradiente de marca (--gradiente-marca no Web)

# Atualize isso manualmente a cada entrega relevante - não tem nenhuma
# automação lendo git/commits pra preencher isso sozinho.
# Versionamento SemVer (MAJOR.MINOR.PATCH - o padrão mais usado no mundo:
# https://semver.org/lang/pt-BR/), com um 4º número opcional de build/
# revisão pra ajustes bem pequenos dentro do mesmo PATCH (ex.: 2.16.20.1).
# REGRA COMBINADA COM O SOLICITANTE (05/09/2026):
#   - MAJOR (o "2" em 2.x): só sobe quando o solicitante pedir explicitamente.
#   - MINOR (o "x" em 2.X"): sobe a cada entrega de funcionalidade nova
#     ou reformulação visual relevante (ex.: a fusão da aba de usuários).
#   - PATCH (e o 4º número, se usado): sobe a cada ajuste pequeno/correção.
# Atualize isso manualmente a cada entrega - não tem automação lendo
# git/commits pra preencher isso sozinho.
VERSAO_PDA = "2.23.0"


class AlertasApp(tk.Tk):
    def __init__(self, jobs: List[Job]):
        super().__init__()
        self.title("PDA · Painel de Automações")
        self.geometry("460x440")
        self.configure(bg=BG)
        self.minsize(420, 400)
        self.resizable(False, False)

        self.job_states: List[JobState] = [JobState(job=j) for j in jobs]
        self._log_pos = 0  # posição já renderizada de log_history

        self.url_web = iniciar_servidor_web(self.job_states)

        # Diagnóstico de .env faltantes - avisa TUDO de uma vez no log, em
        # vez de descobrir aos poucos conforme cada alerta dispara.
        faltando = _diagnosticar_envs_faltantes()
        if faltando:
            logger.warning(
                "%d arquivo(s) .env esperado(s) por alertas NÃO foram encontrados "
                "na pasta do programa - esses alertas vão falhar até os arquivos "
                "serem criados:",
                len(faltando),
            )
            for item in faltando:
                logger.warning(
                    "  - alerta '%s' precisa de .env.%s (cliente exibido: '%s')",
                    item["alerta"], item["chave_env"].lower(), item["cliente"],
                )
        else:
            logger.info("Diagnóstico de .env: todos os arquivos esperados pelos alertas foram encontrados.")

        self._configurar_estilo()
        self._montar_layout()

        self.agendador = Agendador(self.job_states)
        self.agendador.iniciar()

        # Relatório Shein automático - roda uma vez por dia junto com os
        # outros alertas (mesmo agendador global, mesma thread), sem
        # precisar de uma thread própria.
        schedule.every().day.at(HORARIO_RELATORIO_SHEIN_AUTOMATICO).do(_executar_relatorio_shein_diario)

        # Atualização Dash Financeiro - roda todo dia nesse horário, mas
        # só faz alguma coisa de verdade no dia 1 do mês (ver função pra
        # entender por quê - a lib schedule não tem agendamento nativo
        # por dia do mês).
        schedule.every().day.at(HORARIO_DASH_FINANCEIRO_AUTOMATICO).do(_executar_dash_financeiro_mensal_se_dia_1)

        global _monitor_contingencias_ref
        self.monitor_contingencias = MonitorContingencias()
        self.monitor_contingencias.iniciar()
        _monitor_contingencias_ref = self.monitor_contingencias

        global _monitor_emailpack_ref
        self.monitor_emailpack = MonitorEmailPack()
        self.monitor_emailpack.iniciar()
        _monitor_emailpack_ref = self.monitor_emailpack

        self.protocol("WM_DELETE_WINDOW", self._ao_fechar)
        self.after(150, self._drenar_fila)

    # -- estilo -------------------------------------------------------
    def _configurar_estilo(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            "Treeview",
            background=BG_PANEL,
            fieldbackground=BG_PANEL,
            foreground=FG,
            rowheight=28,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading",
            background="#2d2d30",
            foreground=ACCENT,
            relief="flat",
        )
        style.map("Treeview", background=[("selected", "#094771")])

        style.configure(
            "Dark.TButton",
            background="#333333",
            foreground=FG,
            borderwidth=0,
            focusthickness=0,
            padding=6,
        )
        style.map(
            "Dark.TButton",
            background=[("active", "#3e3e42"), ("disabled", "#2a2a2a")],
            foreground=[("disabled", FG_DIM)],
        )

    # -- layout ---------------------------------------------------------
    def _montar_layout(self) -> None:
        # Janela repensada como uma tela de lançamento simples - sem
        # tabela de alertas, sem log de execução (isso tudo já vive no
        # painel Web agora, que é onde os alertas de fato são
        # gerenciados). Só a marca (logo + PDA + versão), os créditos, e
        # um único botão de propósito claro: abrir o PDA no navegador.
        container = tk.Frame(self, bg=BG)
        container.pack(fill="both", expand=True)

        bloco_central = tk.Frame(container, bg=BG)
        bloco_central.place(relx=0.5, rely=0.42, anchor="center")

        try:
            self._logo_img = tk.PhotoImage(data=_LOGO_BASE64)
            largura_original = self._logo_img.width()
            if largura_original > 88:
                fator = max(1, round(largura_original / 72))
                self._logo_img = self._logo_img.subsample(fator, fator)
            tk.Label(bloco_central, image=self._logo_img, bg=BG).pack(pady=(0, 14))
        except Exception:
            logger.exception("Não foi possível carregar a logo na janela desktop - seguindo sem ela.")

        tk.Label(
            bloco_central, text="PDA", bg=BG, fg=ACCENT,
            font=("Segoe UI", 30, "bold"),
        ).pack()
        tk.Label(
            bloco_central, text="Painel de Automações", bg=BG, fg=FG,
            font=("Segoe UI", 12),
        ).pack(pady=(2, 0))
        tk.Label(
            bloco_central, text=f"versão {VERSAO_PDA}", bg=BG, fg=FG_DIM,
            font=("Segoe UI", 9),
        ).pack(pady=(2, 22))

        if self.url_web:
            ttk.Button(
                bloco_central, text="Abrir PDA no navegador", style="Dark.TButton",
                command=lambda: webbrowser.open(self.url_web),
            ).pack(ipadx=10, ipady=4)
            tk.Label(
                bloco_central, text=self.url_web, bg=BG, fg=FG_DIM,
                font=("Consolas", 8),
            ).pack(pady=(10, 0))
        else:
            tk.Label(
                bloco_central, text="Servidor web não disponível nesta execução\n(porta ocupada?)",
                bg=BG, fg=COLOR_ERR, font=("Segoe UI", 9), justify="center",
            ).pack()

        # -- rodapé de créditos - fixo embaixo da janela, discreto, nas
        # duas cores do gradiente de marca (teal/lime).
        rodape = tk.Frame(self, bg=BG_PANEL)
        rodape.pack(fill="x", side="bottom")
        tk.Frame(rodape, bg=BORDER, height=1).pack(fill="x")
        conteudo_rodape = tk.Frame(rodape, bg=BG_PANEL)
        conteudo_rodape.pack(pady=10)
        tk.Label(
            conteudo_rodape, text="Desenvolvido pela equipe do PDA", bg=BG_PANEL, fg=FG_DIM,
            font=("Segoe UI", 8),
        ).pack(side="left")

    # -- ações da GUI -----------------------------------------------------
    # -- atualização por polling (drena o log GERAL do sistema, que
    # continua rodando por baixo dos panos mesmo sem tabela/log visíveis
    # aqui - agendador, monitores etc. seguem ativos igual antes; só a
    # janela local não exibe mais nada disso, o painel Web sim) --------
    def _drenar_fila(self) -> None:
        # mantém a fila de log_history sendo consumida (evita crescer
        # sem necessidade caso algo mais no futuro volte a lê-la a partir
        # daqui) mesmo sem exibir - custo desprezível.
        novas_linhas = list(log_history)[self._log_pos:]
        self._log_pos += len(novas_linhas)
        self.after(150, self._drenar_fila)

    # -- fechamento -----------------------------------------------------
    def _ao_fechar(self) -> None:
        logger.info("Encerrando painel de alertas...")
        self.agendador.parar()
        self.monitor_contingencias.parar()
        self.destroy()


if __name__ == "__main__":
    try:
        app = AlertasApp(JOBS)
        app.mainloop()
    except Exception:
        import traceback
        erro = traceback.format_exc()
        try:
            logger.error("Falha fatal ao iniciar/rodar o painel:\n%s", erro)
        except Exception:
            pass
        print(erro)
        input("\n[ERRO FATAL] Ocorreu um erro. Pressione ENTER para sair...")
