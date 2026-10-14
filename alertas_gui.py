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
import zlib
import gzip
import zipfile
import re
import secrets
import mimetypes
import socket
import sys
import threading
import time
import tempfile
import tkinter as tk
import urllib.parse
import webbrowser
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, date, time as time_cls
import decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tkinter import ttk
from typing import Callable, List, Optional, Union


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
    import pyodbc  # noqa: F401 - checagem na partida; quem usa são as áreas
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
    from features.operations import execute as ftp_execute, getEnv as ftp_getEnv  # noqa: F401 - checagem na partida; usado em areas/jobs_proprios
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
        "Usado pelos Relatórios ClienteA.",
        _e,
    )

try:
    import xlsxwriter  # noqa: F401 - não é usado direto no código, só precisa
    # estar instalado porque o pandas usa ele por baixo dos panos (engine=
    # "xlsxwriter") pra gerar os arquivos .xlsx dos Relatórios ClienteA. Sem
    # essa checagem aqui, o erro só aparecia na hora de gerar o relatório
    # de verdade, com uma mensagem meio críptica.
except Exception as _e:
    _falha_fatal_na_importacao(
        "xlsxwriter",
        "Rode: py -m pip install -r requirements.txt\n"
        "(ou, isolado: py -m pip install xlsxwriter)\n"
        "Usado pelos Relatórios ClienteA pra gerar os arquivos .xlsx.",
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


# Cada item de `clientes` pode ser uma string simples ("cliente_d") ou uma
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
    abrir - só avisa cedo, tudo junto, em vez de Igor descobrir aos
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


# ---------------------------------------------------------------------------
# Jobs próprios do monitoramento: mora em areas/jobs_proprios/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.jobs_proprios.logica import (  # noqa: E402
    _executar_validacao_ftp,
)




# pasta do programa: mora em nucleo/caminhos.py desde 26/09/2026 (usada também pelas áreas)
from nucleo.caminhos import base_path_app as _base_path_app  # noqa: E402


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
    definir_valor_config_dat as _definir_valor_config_dat,
    listar_chaves_config_dat as _listar_chaves_config_dat,
    remover_valor_config_dat as _remover_valor_config_dat,
)

# leitor de configuração híbrido: mora em nucleo/config.py desde 26/09/2026

# ---------------------------------------------------------------------------
# Dash Financeiro: mora em areas/dash_financeiro/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.dash_financeiro.logica import (  # noqa: E402
    HORARIO_DASH_FINANCEIRO_AUTOMATICO,
    NOME_DF_CONSOLIDADO_ANTIGO,
    ORDEM_PRODUTOS_DASH_FINANCEIRO,
    PRODUTOS_TESTAVEIS as PRODUTOS_TESTAVEIS_DASH_FINANCEIRO,
    _caminho_saida_produto,
    _carregar_conexoes_dash_financeiro,
    _clientes_dash_financeiro,
    _executar_dash_financeiro_mensal_se_dia_1,
    _executar_todos_dash_financeiro,
    _lock_dash_financeiro,
    _meses_gerados_dash_financeiro,
    _periodo_mes_anterior,
    _produtos_em_execucao,
    _status_disco_produto,
    estado_dash_financeiro,
    execucao_ativa as _dash_financeiro_execucao_ativa_agora,
    info_arquivo_mes as _info_arquivo_mes_dash_financeiro,
    progresso_execucao as _progresso_dash_financeiro,
    proxima_execucao_automatica as _proxima_execucao_dash_financeiro,
    procurar_empresa_dash_financeiro,
    tentar_iniciar_execucao as _tentar_iniciar_dash_financeiro,
    testar_conexoes_dash_financeiro,
    validar_mes_dash_financeiro,
    MES_MAIS_ANTIGO_DASH_FINANCEIRO,
)




# ---------------------------------------------------------------------------
# Lista de jobs
# ---------------------------------------------------------------------------
JOBS: List[Job] = [
    job_alerta(
        nome="Pendências FornecedorA NFSe",
        descricao="Documentos não processados pela FornecedorA.",
        clientes=[("saas", "saas__pendencias_fornecedor_a")],
    ),
    job_alerta(
        nome="NFSe Status Transitório",
        descricao=(
            "Documentos fiscais da ClienteD com status 'Transitório' por "
            "mais de 15 minutos."
        ),
        clientes=["cliente_d"],
    ),
    job_alerta(
        nome="Manifestações",
        descricao=(
            "Documentos fiscais no qual deveriam ter sido manifestados "
            "automaticamente pela aplicação e não foram."
        ),
        clientes=[
            ("cliente_ag", "cliente_ag__manifestacoes"),
            ("cliente_e", "cliente_e__manifestacoes"),
            ("saas2", "saas2__manifestacoes"),
        ],
    ),
    job_alerta(
        nome="Retorno Personalizado ClienteE",
        descricao=(
            "Documentos no qual possuem retorno personalizado configurado "
            "porém não obtiveram retorno."
        ),
        clientes=[
            ("cliente_e", "cliente_e__retorno_personalizado"),
            ("cliente_ag", "cliente_ag__retorno_personalizado"),
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
            "ClienteD-NFSe1",
            "ClienteD-NFSe2",
            "ClienteIEnterprise",
            ("ClienteIStandard", "ClienteIStandart"),  # exibição com d; o .env/senha do alerta continuam ClienteIStandart
            "ClienteE-NFe",
            "ClienteE-CTe",
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
            "cliente_i_enterprise",
            ("cliente_i_standard", "cliente_i_standart"),  # exibição com d; o .env/senha do alerta continuam cliente_i_standart
            ("cliente_e", "cliente_e__nfe_status_transitorio"),
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
        nome="CTe Incompleto ClienteF",
        descricao="CTe travados em status 0 (Incompleto) na ClienteF",
        clientes=[("saas", "saas__cte_incompleto_cliente_f")],
    ),
    # "Valor Zerado ClienteC" desativado a pedido do Igor (04/09/2026) - a
    # função _executar_valor_zerado_cliente_c() continua no código (em
    # areas/jobs_proprios/logica.py), só não é mais registrada/agendada.
    # Pra reativar, é só descomentar o Job abaixo e incluir o nome no
    # import de areas.jobs_proprios.logica lá em cima.
    # Job(
    #     nome="Valor Zerado ClienteC",
    #     executar=_executar_valor_zerado_cliente_c,
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


# Automanutenção dos logs (3.4.8.0): cada log guarda até MAX_LINHAS_LOG linhas e o excesso vai pra logs/arquivados/
# em zip (apagado 30 dias depois); antes era RotatingFileHandler por tamanho, que descartava a cópia mais antiga
from nucleo.limpeza_logs import ArquivoDeLogComLimite, MAX_LINHAS_LOG  # noqa: E402


def _criar_handler_arquivo(nome_arquivo: str, max_linhas: int = MAX_LINHAS_LOG) -> ArquivoDeLogComLimite:
    """Cria o handler de log (com limite de linhas, 3.4.8.0) pro arquivo dentro de `_PASTA_LOGS`.
    Se não conseguir escrever lá (ex.: log criado por OUTRO usuário do
    Windows numa sessão anterior, com ACL que não dá permissão de
    gravação pro usuário atual - Errno 13), cai pra um arquivo equivalente
    dentro da pasta temporária do sistema em vez de derrubar a aplicação
    inteira, avisando no console. Mesmo padrão já usado no
    monitor_emailpack_gui_corrigido_30min.py, só que aqui com o limite
    de linhas (o excesso vai pro zip em arquivados/), e com nome de fallback por arquivo
    (em vez de um nome fixo) porque essa função é chamada várias vezes,
    uma por card/automação.
    """
    caminho = os.path.join(_PASTA_LOGS, nome_arquivo)
    try:
        handler = ArquivoDeLogComLimite(caminho, max_linhas=max_linhas)
    except (PermissionError, OSError) as e:
        caminho_fallback = os.path.join(tempfile.gettempdir(), f"painelalertas_fallback_{nome_arquivo}")
        print(
            f"[AVISO] Sem permissão de escrita em '{caminho}' ({e}). "
            f"Gravando esse log em '{caminho_fallback}' até a permissão da pasta ser corrigida."
        )
        handler = ArquivoDeLogComLimite(caminho_fallback, max_linhas=max_linhas)
    handler.setFormatter(_formatter)
    return handler


logger.addHandler(_criar_handler_arquivo("alertas_suporte.log"))

# Log isolado dos Relatórios ClienteA (geração + envio ao SharePoint) -
# facilita achar e mandar exatamente o que aconteceu numa falha, sem
# precisar filtrar no meio do log dos outros 12 alertas.
logger_cliente_a = logging.getLogger("alertas.cliente_a")
logger_cliente_a.setLevel(logging.INFO)
logger_cliente_a.propagate = False  # NÃO escreve em alertas_suporte.log - só no arquivo próprio
logger_cliente_a.addHandler(_criar_handler_arquivo("relatorios_cliente_a.log"))

# Log isolado da Atualização Dash Financeiro (os 9 produtos).
logger_dash_financeiro = logging.getLogger("alertas.dash_financeiro")
logger_dash_financeiro.setLevel(logging.INFO)
logger_dash_financeiro.propagate = False
logger_dash_financeiro.addHandler(_criar_handler_arquivo("dash_financeiro.log"))

# Log isolado de ações administrativas (usuários, permissões, Manutenção
# de Alertas em Banco, String Connections, Configurações Seguras, login)
# - tudo que é "alguém mexendo em alguma configuração", separado do
# "alerta rodou/não rodou" do Alertas Suporte.
logger_administracao = logging.getLogger("alertas.administracao")
logger_administracao.setLevel(logging.INFO)
logger_administracao.propagate = False
logger_administracao.addHandler(_criar_handler_arquivo("administracao.log"))

# Acessos ao PDA (3.0.3.0): cada login soma 1; na primeira vez a contagem começa pelos logins que
# já estão no administracao.log (na pasta onde o handler conseguiu gravar, que pode ser o %TEMP%)
from nucleo.acessos import (  # noqa: E402
    DATA_CRIACAO_PDA,
    dias_do_pda as _dias_do_pda,
    iniciar_contagem as _iniciar_contagem_acessos,
    registrar_login as _registrar_login_acesso,
    resumo_acessos as _resumo_acessos,
)
_iniciar_contagem_acessos(os.path.dirname(logger_administracao.handlers[0].baseFilename))

# Log isolado do Controle de Sincronização / Automação Movidesk.
logger_automacao_movidesk = logging.getLogger("alertas.automacao_movidesk")
logger_automacao_movidesk.setLevel(logging.INFO)
logger_automacao_movidesk.propagate = False
logger_automacao_movidesk.addHandler(_criar_handler_arquivo("automacao_movidesk.log"))

# Log isolado dos Indicadores Mensais (cada efetividade/justificativa gravada no banco).
logger_indicadores_mensais = logging.getLogger("alertas.indicadores_mensais")
logger_indicadores_mensais.setLevel(logging.INFO)
logger_indicadores_mensais.propagate = False
logger_indicadores_mensais.addHandler(_criar_handler_arquivo("indicadores_mensais.log"))
# Log dos Rankings (3.1.9.0): cada rank definido/tirado e cada produto criado, renomeado ou removido
logger_rankings = logging.getLogger("alertas.rankings")
logger_rankings.setLevel(logging.INFO)
logger_rankings.propagate = False
logger_rankings.addHandler(_criar_handler_arquivo("rankings.log"))
logger_reprocessamento_cte2 = logging.getLogger("alertas.reprocessamento_cte2")
logger_reprocessamento_cte2.setLevel(logging.INFO)
logger_reprocessamento_cte2.propagate = False
logger_reprocessamento_cte2.addHandler(_criar_handler_arquivo("reprocessamento_cte2.log"))
# Log do Monitoramento de Consumo Indevido (3.4.3.0): cada verificação com ocorrência, falha e envio ao Teams
logger_consumo_indevido = logging.getLogger("alertas.consumo_indevido")
logger_consumo_indevido.setLevel(logging.INFO)
logger_consumo_indevido.propagate = False
logger_consumo_indevido.addHandler(_criar_handler_arquivo("consumo_indevido.log"))
# Log do NNU 20 → 15 (beta, 3.4.9.0): cada rodada, UPDATE, conferência do lote, fechamento e e-mail
logger_nnu_status = logging.getLogger("alertas.nnu_status")
logger_nnu_status.setLevel(logging.INFO)
logger_nnu_status.propagate = False
logger_nnu_status.addHandler(_criar_handler_arquivo("nnu_status.log"))
# Log da Loja de Palminhas (3.3.7.0): cada troca, item em uso e doce achado no Halloween (não tem histórico na tela)
logger_loja = logging.getLogger("alertas.loja")
logger_loja.setLevel(logging.INFO)
logger_loja.propagate = False
logger_loja.addHandler(_criar_handler_arquivo("loja.log"))
logger_longnamejanitor = logging.getLogger("alertas.longnamejanitor")  # LongNameJanitor ClienteQ (3.3.2.0)
logger_longnamejanitor.setLevel(logging.INFO)
logger_longnamejanitor.propagate = False
logger_longnamejanitor.addHandler(_criar_handler_arquivo("longnamejanitor.log"))

# Log isolado do Monitoramento EmailPack (varredura dos logs dos
# serviços EmailPack, agrupamento por e-mail, erros).
logger_emailpack = logging.getLogger("alertas.emailpack")
logger_emailpack.setLevel(logging.INFO)
logger_emailpack.propagate = False
logger_emailpack.addHandler(_criar_handler_arquivo("monitoramento_emailpack.log"))

# Nomes exibidos na tela de Logs, na ordem em que devem aparecer -
# mapeando pra (pasta, arquivo) do log físico correspondente. Os do PDA
# em si ficam em logs/ (pasta do programa); os da Aplicação Monitoramento
# são um programa externo separado, cujos logs vivem numa pasta fixa
# própria (C:\Empresa\Monitoramento\log) - só leitura, o PDA não escreve
# nada lá, só mostra.
CAMINHO_LOGS_MONITORAMENTO = r"C:\Empresa\Monitoramento\log"

LOGS_DISPONIVEIS = {
    "Alertas Suporte (Legacy)": (_PASTA_LOGS, "alertas_suporte.log"),
    "Relatórios ClienteA": (_PASTA_LOGS, "relatorios_cliente_a.log"),
    "Atualização Dash Financeiro": (_PASTA_LOGS, "dash_financeiro.log"),
    "Automação Movidesk": (_PASTA_LOGS, "automacao_movidesk.log"),
    "Monitoramento EmailPack": (_PASTA_LOGS, "monitoramento_emailpack.log"),
    "Indicadores Mensais": (_PASTA_LOGS, "indicadores_mensais.log"),
    "Reprocessamento CTe2": (_PASTA_LOGS, "reprocessamento_cte2.log"),
    "LongNameJanitor ClienteQ": (_PASTA_LOGS, "longnamejanitor.log"),
    "Rankings": (_PASTA_LOGS, "rankings.log"),
    "Loja de Palminhas": (_PASTA_LOGS, "loja.log"),
    "Consumo Indevido": (_PASTA_LOGS, "consumo_indevido.log"),
    "NNU 20 → 15": (_PASTA_LOGS, "nnu_status.log"),
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
    limitados a MAX_LINHAS_LOG linhas, mas essa função funciona
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

# Como os loggers isolados (cliente_a, dash financeiro, administração,
# automação movidesk) não propagam mais pro "alertas" pai (ver acima -
# propagate = False, pra não misturar nos arquivos), precisam do MESMO
# handler da tela ao vivo adicionado neles direto também, senão
# sumiriam da tela ao vivo do painel - só ficariam nos arquivos.
for _logger_isolado in (logger_cliente_a, logger_dash_financeiro, logger_administracao, logger_automacao_movidesk,
                        logger_indicadores_mensais, logger_reprocessamento_cte2):
    _logger_isolado.addHandler(_queue_handler)


# ---------------------------------------------------------------------------
# Execução dos jobs
# ---------------------------------------------------------------------------
running_jobs_lock = threading.Lock()
running_jobs: set = set()


# aviso no Teams quando um job falha / volta: mora em nucleo/avisos_falha.py desde a 2.33.2.0
from nucleo.avisos_falha import (  # noqa: E402
    definir_url_painel,
    limite_por_frequencia,
    registrar_resultado as registrar_resultado_job,
)


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
        registrar_resultado_job(nome, True)
    except Exception as e:
        state.last_run = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.status = "Erro"
        state.last_error = str(e)
        logger.exception("Erro ao executar alerta '%s': %s", nome, e)
        # aviso no Teams (nucleo/avisos_falha.py): 2 falhas seguidas pra quem
        # roda várias vezes por dia, 1 pra quem roda 1x por dia ou menos
        registrar_resultado_job(nome, False, f"{type(e).__name__}: {e}", limite_por_frequencia(state.scheduled))
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
# Contingências SEFAZ: mora em areas/contingencias/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.contingencias.logica import (  # noqa: E402
    GRADE_UF,
    MonitorContingencias,
    NOME_UF,
    SVC_POR_UF,
    _lock_contingencias,
    estado_contingencias,
)




# Referência global pro monitor em execução, pra dar pro handler HTTP
# conseguir chamar "forçar atualização agora" (setada em AlertasApp.__init__).
_monitor_contingencias_ref: Optional["MonitorContingencias"] = None


# ---------------------------------------------------------------------------
# Monitoramento EmailPack: mora em areas/emailpack/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.emailpack.logica import (  # noqa: E402
    MonitorEmailPack,
    _carregar_emails_conhecidos_emailpack,
    _carregar_emails_ignorados_emailpack,
    _lock_emails_emailpack,
    _lock_estado_emailpack,
    _salvar_emails_ignorados_emailpack,
    estado_emailpack,
)




_monitor_emailpack_ref: Optional["MonitorEmailPack"] = None


# ---------------------------------------------------------------------------
# Manutenção de Alertas em Banco
# ---------------------------------------------------------------------------
# Cria/lista/ativa-desativa registros na tabela CONFIGURACOES_ALERTA do banco
# de monitoramento (instância de homologação: 192.0.2.201\INSTANCIA_HML,
# monitoramento_empresa). Segue exatamente o schema e as regras descritas na
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

# ---------------------------------------------------------------------------
# Banco de monitoramento: mora em nucleo/ desde 26/09/2026
# ---------------------------------------------------------------------------
from nucleo.banco_monitoramento import (  # noqa: E402
    EMAIL_MONITORAMENTO_PADRAO,
)




# ---------------------------------------------------------------------------
# Manutenção de Alertas em Banco: mora em areas/manutencao_alertas/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.manutencao_alertas.logica import (  # noqa: E402
    visao_somente_leitura_alerta as _visao_leitura_alerta,
    visao_somente_leitura_lista as _visao_leitura_lista_alertas,
    _alternar_disponibilidade_banco,
    _atualizar_alerta_banco,
    _buscar_alerta_banco,
    _criar_alerta_banco,
    _listar_alertas_banco,
    _montar_texto_gatilho,
    _validar_dados_alerta_banco,
    contar_alertas_mapeados as _contar_alertas_mapeados,
)




# ---------------------------------------------------------------------------
# Manutenção Rejeições em Banco
# ---------------------------------------------------------------------------
# Mesma ideia da Manutenção de Alertas em Banco (mesmo banco de
# monitoramento, mesmo jeito de guardar o SCRIPT em base64), mas numa
# tabela mais simples - CONFIGURACOES_REJEICAO não tem TITULO, TETO_ALERTA,
# INTERVALO_MINUTOS, DESCRICAO nem DISPONIBILIDADE (não existem colunas
# assim nessa tabela, conforme a documentação que o Igor passou). O
# script aqui precisa retornar o código da rejeição E a quantidade (não
# só uma contagem, como no alerta). EMAILS é um campo de verdade editável
# aqui (client-specific) - diferente do alerta, onde é sempre travado no
# e-mail padrão do monitoramento; aqui o e-mail do monitoramento já é
# adicionado automaticamente por fora, então não precisa (nem deve)
# entrar nesse campo.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Manutenção Rejeições em Banco: mora em areas/manutencao_rejeicoes/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.manutencao_rejeicoes.logica import (  # noqa: E402
    _atualizar_rejeicao_banco,
    _buscar_rejeicao_banco,
    _criar_rejeicao_banco,
    _excluir_rejeicao_banco,
    _listar_rejeicoes_banco,
    _montar_texto_gatilho_rejeicao,
    _validar_dados_rejeicao_banco,
)




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
# 1/0 - corrigido depois de confirmar com o Igor (o "Failed to fetch"
# reportado era outra coisa - um valor de HORA_EXECUCAO vindo do banco
# como objeto time, que quebrava o json.dumps antes de mandar qualquer
# resposta - ver _normalizar_hora_execucao e _json_serializar_padrao).
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Manutenção de Relatórios em Banco: mora em areas/manutencao_relatorios/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.manutencao_relatorios.logica import (  # noqa: E402
    _alterar_disponibilidade_relatorio,
    _atualizar_relatorio_banco,
    _buscar_relatorio_banco,
    _criar_relatorio_banco,
    _listar_relatorios_banco,
    _validar_dados_relatorio_banco,
)






# ---------------------------------------------------------------------------
# Indicadores Movidesk - dashboard admin com métricas de escalonamentos,
# dúvidas e sincronização, puxadas direto do banco (Movidesk). Conexão
# própria (.env.indicadores_movidesk), separada das outras.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Movidesk (base): mora em nucleo/ desde 26/09/2026
# ---------------------------------------------------------------------------
from nucleo.movidesk import (  # noqa: E402
    ManutencaoUsuariosConfigError,
)




# ---------------------------------------------------------------------------
# Indicadores Movidesk: mora em areas/indicadores_movidesk/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.indicadores_movidesk.logica import (  # noqa: E402
    _consultar_indicadores_movidesk,
    _gerar_excel_indicadores,
)




# ---------------------------------------------------------------------------
# Horas trabalhadas (Movidesk) - baseado no relatorio_horas.py que o Igor
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


# ---------------------------------------------------------------------------
# Usuários Movidesk: mora em areas/manutencao_usuarios/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.manutencao_usuarios.movidesk import (  # noqa: E402
    _atualizar_usuario_movidesk,
    _buscar_usuario_movidesk,
    _listar_usuarios_movidesk,
    _nome_movidesk_vinculado,
    _sincronizar_usuarios_movidesk,
)




# ---------------------------------------------------------------------------
# Horas Trabalhadas: mora em areas/horas_trabalhadas/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.horas_trabalhadas.logica import (  # noqa: E402
    _consultar_horas_trabalhadas,
    _gerar_excel_export_horas,
)




# ---------------------------------------------------------------------------
# Relatórios ClienteA: mora em areas/relatorios_cliente_a/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.relatorios_cliente_a.logica import (  # noqa: E402
    HORARIO_RELATORIO_CLIENTE_A_AUTOMATICO,
    _executar_relatorio_cliente_a_diario,
    _gerar_relatorio_cliente_a,
    _localizar_pasta_relatorio_cliente_a_por_data_str,
    _lock_relatorio_cliente_a_auto,
    _pasta_saida_relatorios_cliente_a,
    estado_relatorio_cliente_a_automatico,
)




# ---------------------------------------------------------------------------
# Textos das telas (HTML/CSS/JS) - moram na pasta telas/ desde 26/09/2026.
# Importados aqui, no lugar onde ficavam, pra ordem de execução do arquivo
# continuar exatamente a mesma.
# ---------------------------------------------------------------------------
from telas.imagens import (  # noqa: E402
    _LOGO_BASE64,
    _LOGO_MONITOR_CLIENTE_H_B64,
    _LOGO_MONITOR_CLIENTE_J_B64,
    _LOGO_MONITOR_CLIENTE_L_B64,
    _LOGO_MONITOR_CLIENTE_M_B64,
    _LOGO_MONITOR_CLIENTE_A_B64,
    _LOGO_MONITOR_CLIENTE_E_B64,
    _LOGO_MONITOR_CLIENTE_N_B64,
    _LOGO_MONITOR_CLIENTE_B_B64,
    _LOGO_MONITOR_CLIENTE_I_B64,
    _LOGO_MONITOR_CLIENTE_D_B64,
    _LOGO_MONITOR_CLIENTE_P_B64,
    _LOGO_MONITOR_CLIENTE_G_B64,
    _LOGO_MONITOR_CLIENTE_O_B64,
)
from telas.comum import (  # noqa: E402
    _NAVBAR_CSS,
    _JS_ALTERNAR_SENHA,
    _NAVBAR_HTML,
    _FOOTER_HTML,
    _SVG_OLHO_ABERTO,
    _SVG_OLHO_FECHADO,
    _USUARIOS_NEGADO_TEMPLATE,
)
from telas.login import (  # noqa: E402
    _LOGIN_HTML_TEMPLATE,
    _ALTERAR_SENHA_HTML_TEMPLATE,
)
from telas.hub import (  # noqa: E402
    _HUB_HTML_TEMPLATE,
    _CARD_INDICADORES_MOVIDESK_HTML,
    _CARD_AUTOMACAO_MOVIDESK_HTML,
    _CARD_RELATORIOS_CLIENTE_A_HTML,
    _CARD_DASH_FINANCEIRO_HTML,
    _CARD_MANUTENCAO_ALERTAS_HTML,
    _CARD_MANUTENCAO_REJEICOES_HTML,
    _CARD_MANUTENCAO_RELATORIOS_HTML,
    _CARD_DASHBOARDS_CLIENTES_HTML,
    _CARD_FEEDBACKS_HTML,
    _CARD_HORAS_TRABALHADAS_HTML,
    _CARD_LOGS_HTML,
    _CARD_CHECKLISTS_HTML,
    _CARD_INDICADORES_MENSAIS_HTML,
    _CARD_REPROCESSAMENTO_CTE2_HTML,
    _CARD_NNU_ENCHANCED_HTML,
    _CARD_GERACAO_IANS_HTML,
    _CARD_GMUD_HTML,
    _CARD_INDICADORES_SERVICOS_HTML,
    _CARD_ABERTURA_GMUD_HTML,
    _CARD_LONGNAMEJANITOR_HTML,
    _CARD_LIMPEZA_MAQUINAS_HTML,
    _CARD_VERSOES_RECENTES_HTML,
    _CARD_FLUXOGRAMA_HTML,
    _CARD_CONSUMO_INDEVIDO_HTML,
    _CARD_DIRECIONAMENTO_WEBMONITORS_HTML,
    _CARD_MANUTENCAO_USUARIOS_HTML,
    _CARDS_DADOS_SENSIVEIS_HTML,
    _CARD_ALERTAS_HTML,
    _CARD_CONTINGENCIAS_HTML,
    _CARD_EMAILPACK_HTML,
    _CARD_MEU_PLANTAO_HTML,
    _CARD_FERIAS_HTML,
    _CARD_RANKS_PRODUTOS_HTML,
    _ITEM_MENU_GESTAO_HTML,
    _ITEM_MENU_GESTAO_RESTRITO_HTML,
    _BUSCA_NAVBAR_HTML,
    _SECAO_GESTAO_HTML,
)
from telas.alertas import (  # noqa: E402
    _HTML_PAGE,
)
from telas.central_monitores import (  # noqa: E402
    _DIRECIONAMENTO_WEBMONITORS_HTML,
)
from areas.string_connections.tela import (  # noqa: E402
    _STRING_CONNECTIONS_HTML_TEMPLATE,
)
from telas.config_seguro import (  # noqa: E402
    _CONFIG_SEGURO_HTML_TEMPLATE,
)
from areas.dash_financeiro.tela import (  # noqa: E402
    _DASH_FINANCEIRO_HTML_TEMPLATE,
)
from areas.emailpack.tela import (  # noqa: E402
    _EMAILPACK_HTML_TEMPLATE,
)
from telas.insignias import _INSIGNIAS_HTML  # noqa: E402
from areas.reprocessamento_cte2.tela import (  # noqa: E402
    _REPROCESSAMENTO_CTE2_HTML_TEMPLATE,
)
from areas.indicadores_mensais.tela import (  # noqa: E402
    _INDICADORES_MENSAIS_HTML_TEMPLATE,
)
from areas.ferias.tela import (  # noqa: E402
    _FERIAS_HTML_TEMPLATE,
)
from areas.perfil.tela import (  # noqa: E402
    _PERFIL_HTML_TEMPLATE,
)
from telas.logs import (  # noqa: E402
    _LOGS_HTML_TEMPLATE,
)
from areas.manutencao_usuarios.tela import (  # noqa: E402
    _MANUTENCAO_USUARIOS_HTML_TEMPLATE,
)
from areas.indicadores_movidesk.tela import (  # noqa: E402
    _INDICADORES_MOVIDESK_HTML_TEMPLATE,
)
from areas.horas_trabalhadas.tela import (  # noqa: E402
    _HORAS_TRABALHADAS_HTML_TEMPLATE,
)
from areas.automacao_movidesk.tela import (  # noqa: E402
    _AUTOMACAO_MOVIDESK_HTML_TEMPLATE,
)
from areas.manutencao_alertas.tela import (  # noqa: E402
    _MANUTENCAO_ALERTAS_HTML_TEMPLATE,
)
from areas.manutencao_rejeicoes.tela import (  # noqa: E402
    _MANUTENCAO_REJEICOES_HTML_TEMPLATE,
)
from areas.manutencao_relatorios.tela import (  # noqa: E402
    _MANUTENCAO_RELATORIOS_HTML_TEMPLATE,
)
from areas.feedbacks.tela import (  # noqa: E402
    _FEEDBACKS_HTML_TEMPLATE,
)
from areas.dashboards_clientes.tela import (  # noqa: E402
    _DASHBOARDS_CLIENTES_HTML_TEMPLATE,
)
from telas.sobre import (  # noqa: E402
    _SOBRE_HTML_TEMPLATE,
)
from areas.ranks_produtos.tela import (  # noqa: E402
    _RANKS_PRODUTOS_HTML_TEMPLATE,
)
from areas.nnu_enchanced.tela import (  # noqa: E402
    _NNU_ENCHANCED_HTML_TEMPLATE,
)
from telas.changelog import (  # noqa: E402
    _CHANGELOG_HTML_TEMPLATE,
)
from areas.relatorios_cliente_a.tela import (  # noqa: E402
    _RELATORIOS_CLIENTE_A_HTML_TEMPLATE,
)
from areas.contingencias.tela import (  # noqa: E402
    _CONTINGENCIAS_HTML_TEMPLATE,
)
_LOGO_DATA_URI = f"data:image/png;base64,{_LOGO_BASE64}"
# 3.3.4.0: a logo (27 KB) ia embutida 3 vezes em toda tela (ícone da aba, navbar e rodapé). Na hora de enviar, os
# atributos href="<logo>" e src="<logo>" viram este endereço, que o navegador guarda em cache (o ?v= é o checksum
# da imagem). O resto (JSON da Central de Monitores, Tkinter, e-mails) continua com o dado embutido.
_LOGO_BYTES = base64.b64decode(_LOGO_BASE64)
_GZIP_MINIMO = 1400  # bytes: abaixo disso o gzip não compensa
_LOGO_URL = "/logo-pda.png?v=%08x" % zlib.crc32(_LOGO_BYTES)  # muda sozinho se a imagem mudar


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


def _montar_alertas_html(sessao: dict) -> str:
    return (
        _HTML_PAGE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Alertas Suporte (Legacy)"))
        .replace("__FOOTER__", _montar_footer())
    )


# Frase de efeito da tela de login. Vazia = não aparece (tirada a pedido do Igor em
# 25/09/2026). Pra voltar, é só preencher: TAGLINE_LOGIN = "Um painel. Diversas operações."
TAGLINE_LOGIN = ""


def _data_atualizacao_pda() -> str:
    # No .exe (PyInstaller) a data de modificação do executável é a da última
    # compilação; rodando via Python, é a do próprio alertas_gui.py. Assim a data
    # acompanha cada atualização sozinha, sem mais um valor pra lembrar de trocar.
    try:
        caminho = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
        return datetime.fromtimestamp(os.path.getmtime(caminho)).strftime("%d/%m/%Y")
    except (OSError, NameError):
        return ""


def _montar_login_html(com_erro: bool, com_sucesso: bool = False, desativado: bool = False) -> str:
    if desativado:
        bloco_erro = (
            '<div class="erro erro-desativado">'
            'Este usuário está desativado. Entre em contato com a '
            '<strong>Debora Sampaio</strong> ou o <strong>Igor Leal</strong> pra reativar o acesso.'
            '</div>'
        )
    elif com_erro:
        bloco_erro = '<div class="erro">Usuário ou senha inválidos.</div>'
    else:
        bloco_erro = ""
    bloco_sucesso = '<div class="msg-sucesso">Senha alterada com sucesso. Entre com a nova senha.</div>' if com_sucesso else ""
    data_atualizacao = _data_atualizacao_pda()
    bloco_versao = (
        f'<div class="versao-login"><span class="chip-versao">v{VERSAO_PDA}</span>'
        + (f'<span>atualizado em {data_atualizacao}</span>' if data_atualizacao else '')
        + '</div>'
    )
    # tagline some por completo quando vazia (as duas cópias: a visível e a "fantasma"
    # que só existe pra alinhar o cartão de login com o painel da direita)
    tagline = html_utils.escape(TAGLINE_LOGIN)
    bloco_tagline_fantasma = f'<div class="fantasma-tagline" aria-hidden="true">{tagline}</div>' if tagline else ""
    bloco_tagline_showcase = f'<div class="tagline-showcase anim-entrada" style="animation-delay:.12s">{tagline}</div>' if tagline else ""
    n = _numeros_sobre()
    bloco_numeros = '<div class="numeros-showcase">' + "".join(
        f'<div class="numero-showcase anim-entrada" style="animation-delay:{0.20 + i * 0.03:.2f}s">'
        f'<div class="valor">{valor}</div><div class="rotulo">{rotulo}</div></div>'
        for i, (valor, rotulo) in enumerate([
            (n["alertas"], "Alertas automáticos"),
            (n["clientes_monitores"], "Clientes monitorados"),
            (n["produtos_df"], "Produtos no Dash Financeiro"),
            (n["cards"], "Ferramentas no painel"),
        ])
    ) + "</div>"
    bloco_areas = ('<div class="areas-showcase">'
                   + _html_areas_pda("area-showcase", "h4", LIMITE_ITENS_AREA_LOGIN, anim_base=0.32)
                   + "</div>")
    return (
_LOGIN_HTML_TEMPLATE
        .replace("__NUMEROS_SHOWCASE__", bloco_numeros)
        .replace("__AREAS_SHOWCASE__", bloco_areas)
        .replace("__TAGLINE_FANTASMA__", bloco_tagline_fantasma)
        .replace("__TAGLINE_SHOWCASE__", bloco_tagline_showcase)
        .replace("__VERSAO_LOGIN__", bloco_versao)
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__CAMPO_SENHA__", _campo_senha_html("senha", "current-password"))
        .replace("__ERRO__", bloco_erro)
        .replace("__SUCESSO__", bloco_sucesso)
        .replace("__JS_ALTERNAR_SENHA__", _JS_ALTERNAR_SENHA)
        .replace("__FOOTER__", _montar_footer(com_changelog=False))
    )


_MENSAGENS_ERRO_ALTERAR_SENHA = {
    "credenciais": "Usuário ou senha atual incorretos.",
    "confirmacao": "A nova senha e a confirmação não coincidem.",
    "tamanho": "A nova senha precisa ter ao menos 4 caracteres.",
    "campos": "Preencha todos os campos.",
    "padrao": "A nova senha não pode ser a senha padrão (SenhaInicial@1).",
    "igual": "A nova senha precisa ser diferente da atual.",
}


def _montar_alterar_senha_html(erro: Optional[str] = None, usuario_obrigatorio: Optional[str] = None) -> str:
    """`usuario_obrigatorio`: quem entrou com a senha padrão e precisa trocar
    (2.34.7.3) - usuário já preenchido e sem pedir a senha atual de novo."""
    bloco_erro = ""
    if erro:
        texto_erro = _MENSAGENS_ERRO_ALTERAR_SENHA.get(erro, "Não foi possível alterar a senha.")
        bloco_erro = f'<div class="erro">{texto_erro}</div>'
    if usuario_obrigatorio:
        sub = ("Você entrou com a senha padrão. Por segurança, defina uma senha nova pra continuar "
               "(diferente de SenhaInicial@1).")
        campo_usuario = (f'<input type="text" name="usuario" value="{html_utils.escape(usuario_obrigatorio)}" '
                         'readonly autocomplete="username" class="campo-fixo">')
        bloco_senha_atual = ""
        voltar = '<a class="link-alterar-senha" href="/logout">Sair sem trocar</a>'
    else:
        sub = "Informe seu usuário e a senha atual para definir uma nova senha."
        campo_usuario = '<input type="text" name="usuario" autofocus required autocomplete="username">'
        bloco_senha_atual = "<label>Senha atual</label>\n      " + _campo_senha_html("senha_atual", "current-password")
        voltar = '<a class="link-alterar-senha" href="/login">Voltar para o login</a>'
    return (
        _ALTERAR_SENHA_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__SUB_ALTERAR_SENHA__", sub)
        .replace("__CAMPO_USUARIO_ALTERAR__", campo_usuario)
        .replace("__BLOCO_SENHA_ATUAL__", bloco_senha_atual)
        .replace("__LINK_VOLTAR_ALTERAR__", voltar)
        .replace("__CAMPO_NOVA_SENHA__", _campo_senha_html("nova_senha", "new-password"))
        .replace("__CAMPO_CONFIRMA_SENHA__", _campo_senha_html("confirma_senha", "new-password"))
        .replace("__ERRO__", bloco_erro)
        .replace("__JS_ALTERNAR_SENHA__", _JS_ALTERNAR_SENHA)
        .replace("__FOOTER__", _montar_footer(com_changelog=False))
    )


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


def _montar_navbar(sessao: dict, subtitulo: str, busca_html: str = "") -> str:
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
        .replace("__BUSCA_NAVBAR__", busca_html)  # só o início manda a busca de cards (3.1.0.0)
        .replace("__USUARIO__", sessao.get("nome") or sessao["usuario"])
        .replace("__BADGE_CLASSE__", badge_classe)
        .replace("__BADGE_TEXTO__", badge_texto)
        .replace("__AVATAR_NAVBAR__", avatar_navbar)
        .replace("__LOGIN__", login)
    )


def _montar_footer(com_changelog: bool = True) -> str:
    """Rodapé comum (já vem com o logo embutido, ver bloco de otimização).
    Nas telas de quem está logado, o lado direito mostra a versão atual e o
    link pro changelog (substituiu o card Changelog do hub na 2.32.3.0, pra
    não encher o hub de cards). Login/alterar senha usam com_changelog=False:
    /changelog exige login, e o login já mostra a versão no cartão."""
    if com_changelog:
        direita = (
            # "Sobre o PDA" no lugar do texto fixo: até a 2.32.4.0 nenhuma tela
            # linkava pra /sobre (só abria digitando o endereço)
            '<div class="direita-rodape"><a class="link-sobre-rodape" href="/sobre">Sobre o PDA</a>'
            '<a class="link-changelog-rodape" href="/changelog" title="Ver o que mudou em cada versão">'
            f'<span class="versao-rodape">v{html_utils.escape(VERSAO_PDA)}</span>'
            '<span>Ver changelog →</span></a></div>'
        )
    else:
        direita = "<div>Painel de Automações</div>"
    return _FOOTER_HTML.replace("__DIREITA_RODAPE__", direita)


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


def _resolver_logos_central(html: str) -> str:
    """Logos embutidos no PDA citados nos dados da Central ("__LOGO_MONITOR_<NOME>__", "__LOGO__") viram a imagem."""
    return (
    html
    .replace("__LOGO__", _LOGO_DATA_URI)
    .replace("__LOGO_MONITOR_CLIENTE_H__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_H_B64)
    .replace("__LOGO_MONITOR_CLIENTE_J__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_J_B64)
    .replace("__LOGO_MONITOR_CLIENTE_L__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_L_B64)
    .replace("__LOGO_MONITOR_CLIENTE_M__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_M_B64)
    .replace("__LOGO_MONITOR_CLIENTE_A__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_A_B64)
    .replace("__LOGO_MONITOR_CLIENTE_E__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_E_B64)
    .replace("__LOGO_MONITOR_CLIENTE_N__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_N_B64)
    .replace("__LOGO_MONITOR_CLIENTE_B__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_B_B64)
    .replace("__LOGO_MONITOR_CLIENTE_I__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_I_B64)
    .replace("__LOGO_MONITOR_CLIENTE_D__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_D_B64)
    .replace("__LOGO_MONITOR_CLIENTE_P__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_P_B64)
    .replace("__LOGO_MONITOR_CLIENTE_G__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_G_B64)
    .replace("__LOGO_MONITOR_CLIENTE_O__", "data:image/png;base64," + _LOGO_MONITOR_CLIENTE_O_B64)
    )


def _logo_para_edicao(logo: str) -> str:
    # no editor o logo embutido vai como "embutido:NOME" (sem os __ das pontas), senão a troca dos logos acima
    # mandaria a imagem inteira de volta a cada salvamento
    m = re.match(r"^__(LOGO(?:_MONITOR_[A-Z0-9]+)?)__$", logo or "")
    return "embutido:" + m.group(1) if m else (logo or "")


def _montar_direcionamento_webmonitors_html(sessao: Optional[dict] = None) -> str:
    """Central de Monitores (3.2.8.0): clientes vêm do central_monitores.json (ou do padrão); a aba Editar e os dados
    de edição só vão pra quem é admin com a permissão pode_editar_central."""
    clientes = _central_carregar()
    lista, meta = _central_dados_pagina(clientes)
    pode = _central_pode_editar(sessao)
    edicao = [dict(c, logo=_logo_para_edicao(c.get("logo"))) for c in clientes] if pode else None
    html = (_DIRECIONAMENTO_WEBMONITORS_HTML
            .replace("__CENTRAL_META__", _central_json_script(meta))
            .replace("__CENTRAL_CLIENTES__", _central_json_script(lista))
            .replace("__CENTRAL_EDICAO__", _central_json_script(edicao))
            .replace("__PODE_EDITAR_CENTRAL__", "true" if pode else "false")
            .replace("__VERSAO_CENTRAL__", _central_versao(clientes)))
    return _resolver_logos_central(html)


def _ordem_card_hub(card: str, exclusivo: bool) -> int:
    """Posição de um card pelo andamento (3.3.2.2): beta que abre, em construção que já abre (prévia),
    beta trancado (🔒 Restrito) e em construção fechado. Dentro de cada etapa, o que só alguns veem
    (admin ou permissão à parte) vem antes do que é pra todo mundo."""
    if 'class="card-hub bloqueado"' in card:
        etapa = 3
    elif "🔒 Restrito" in card:
        etapa = 2
    elif ">Beta</span>" in card:
        etapa = 0
    else:
        etapa = 1
    return etapa * 2 + (0 if exclusivo else 1)


def _ordenar_em_breve(cards: list) -> list:
    """Em breve em sequência pelo andamento e por quem vê (sorted é estável: empate mantém a ordem da lista)."""
    return [c for c, exclusivo in sorted((par for par in cards if par[0]), key=lambda par: _ordem_card_hub(*par))]


def _montar_hub_html(sessao: dict) -> str:
    """Início (2.35.7.0): mural da equipe + seções de cards no menu da esquerda.
    Automações, Outros e Em breve (em construção e beta) pra todo mundo; Gestão de equipe só pra administrador
    (quem não é admin vê em Outros os cards de gestão que tem acesso, como Horas
    Trabalhadas e Indicadores Movidesk). Cada card com acesso restrito só entra no
    HTML se a pessoa tiver a permissão, mesmo critério das rotas em do_GET."""
    classe_conting, resumo_conting = _resumo_conting_hub()
    admin = bool(sessao.get("admin"))
    automacoes = [
        _CARD_ALERTAS_HTML,
        _CARD_CONTINGENCIAS_HTML,
        _CARD_AUTOMACAO_MOVIDESK_HTML if admin else "",
        _CARD_RELATORIOS_CLIENTE_A_HTML if _tem_acesso_relatorios_cliente_a(sessao) else "",
        _CARD_DASH_FINANCEIRO_HTML if _tem_acesso_dash_financeiro(sessao) else "",
        _CARD_MANUTENCAO_ALERTAS_HTML,  # pra todo mundo desde a 3.1.9.0 (sem permissão: só os ativos, só leitura)
        _CARD_MANUTENCAO_REJEICOES_HTML if _tem_acesso_manutencao_rejeicoes(sessao) else "",
        _CARD_MANUTENCAO_RELATORIOS_HTML if _tem_acesso_manutencao_relatorios(sessao) else "",
        _CARD_EMAILPACK_HTML,
        _CARD_REPROCESSAMENTO_CTE2_HTML,  # pra todo mundo acompanhar desde a 3.3.1.0 (controlar só admin)
        _CARD_LONGNAMEJANITOR_HTML,  # 3.4.7.0: saiu do Em breve (continua Beta); todo mundo acompanha, controlar só admin
        # 3.4.9.1: NNU Enchanced (tratativa + automações de NNU) saiu do Em breve, continua Beta. Desde a 3.5.1.0 abre pra
        # todo mundo (como o LongNameJanitor): ver é de todos, mexer nas automações é só administrador
        _CARD_NNU_ENCHANCED_HTML,
    ]
    # "Em breve": cards em construção e os que estão em beta
    # (card, exclusivo): exclusivo = só alguns veem (admin ou permissão à parte); a ordem final sai de _ordenar_em_breve
    servicos_adm = _tem_acesso_servicos_adm(sessao)
    em_breve = _ordenar_em_breve([
        (_CARD_DASHBOARDS_CLIENTES_HTML if _tem_acesso_dashboards_clientes(sessao) else "", True),
        (_CARD_CHECKLISTS_HTML, False),
        (_CARD_GERACAO_IANS_HTML if admin else "", True),  # em construção, só pra administrador
        (_CARD_FLUXOGRAMA_HTML if admin else "", True),  # beta, só administrador (3.3.1.0)
        (_CARD_CONSUMO_INDEVIDO_HTML if admin else "", True),  # beta, só administrador (3.4.3.0)
    ])
    # Operações/Serviços (3.3.9.0, pedido do Igor): seção própria logo abaixo da Gestão de equipe, pra todo mundo.
    # GMUD (beta desde a 3.3.9.0) e Indicadores Serviços continuam só com Serviços ADM; Abertura de GMUD's, Limpeza de
    # Máquinas e Versões mais recentes (em construção) aparecem pra todos. Saíram da Gestão de equipe e do Em breve.
    operacoes = [c for c, exclusivo in sorted((par for par in [
        (_CARD_GMUD_HTML if servicos_adm else "", True),
        (_CARD_INDICADORES_SERVICOS_HTML if servicos_adm else "", True),
        (_CARD_ABERTURA_GMUD_HTML, False),
        (_CARD_LIMPEZA_MAQUINAS_HTML, False),
        (_CARD_VERSOES_RECENTES_HTML, False),
    ] if par[0]), key=lambda par: _ordem_card_hub(*par))]
    gestao = [
        _CARD_INDICADORES_MENSAIS_HTML if _tem_acesso_indicadores_mensais(sessao) else "",
        _CARD_FEEDBACKS_HTML if _tem_acesso_feedbacks(sessao) else "",
        _CARD_MANUTENCAO_USUARIOS_HTML if _tem_acesso_manutencao_usuarios(sessao) else "",
        _CARDS_DADOS_SENSIVEIS_HTML if _tem_acesso_dados_sensiveis(sessao) else "",
    ]
    # 3.4.4.0 (pedido do Igor): Indicadores Movidesk, Horas Trabalhadas e Calendário de Férias ficam em Outros pra todo
    # mundo e aparecem também na Gestão de equipe. Só pro administrador: quem não é admin recebe a Gestão dentro de
    # Outros (logo abaixo), e aí eles apareceriam duas vezes.
    if admin:
        gestao += [_CARD_INDICADORES_MOVIDESK_HTML, _CARD_HORAS_TRABALHADAS_HTML, _CARD_FERIAS_HTML]
    # Horas Trabalhadas fica em Outros pra todo mundo (3.0.7.0, pedido do Igor)
    # Logs também (3.0.8.0), só pra quem tem acesso a logs; Rankings saiu do beta e veio pra cá (3.1.5.0)
    # Indicadores Movidesk também, pra todo mundo (3.1.6.0; pros administradores ele aparece de novo como aba do Indicadores Mensais)
    outros = [_CARD_DIRECIONAMENTO_WEBMONITORS_HTML, _CARD_RANKS_PRODUTOS_HTML, _CARD_INDICADORES_MOVIDESK_HTML, _CARD_HORAS_TRABALHADAS_HTML,
              _CARD_LOGS_HTML if _tem_acesso_logs(sessao) else "", _CARD_FERIAS_HTML, _CARD_MEU_PLANTAO_HTML]
    if not admin:
        outros = gestao + outros
    # 3.3.2.2: o que abre primeiro, o que ainda está em construção no fim (mantendo a ordem de cada grupo)
    outros = sorted((c for c in outros if c), key=lambda c: _ordem_card_hub(c, False) >= 6)
    nome = sessao.get("nome") or sessao["usuario"]
    return (
        _HUB_HTML_TEMPLATE
        .replace("__INSIGNIAS__", _INSIGNIAS_HTML)
        .replace("__LOJA_WALLPAPERS__", _LOJA_WALLPAPERS_HTML)
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Comunidade", _BUSCA_NAVBAR_HTML))
        .replace("__ITEM_MENU_GESTAO__", _ITEM_MENU_GESTAO_HTML if admin else _ITEM_MENU_GESTAO_RESTRITO_HTML)
        .replace("__SECAO_GESTAO__", _SECAO_GESTAO_HTML if admin else "")
        .replace("__CARDS_AUTOMACOES__", "\n".join(c for c in automacoes if c))
        .replace("__CARDS_GESTAO__", "\n".join(c for c in gestao if c))
        .replace("__CARDS_OPERACOES__", "\n".join(operacoes))
        .replace("__CARDS_OUTROS__", "\n".join(c for c in outros if c))
        .replace("__CARDS_EM_BREVE__", "\n".join(c for c in em_breve if c))
        .replace("__ADMIN_MURAL__", "true" if admin else "false")
        .replace("__VERSAO_HUB__", html_utils.escape(VERSAO_PDA))
        .replace("__PRIMEIRO_NOME_HERO__", html_utils.escape(nome.split(" ")[0]))
        .replace("__USUARIO_HERO__", html_utils.escape(nome))
        .replace("__SAUDACAO_HERO__", _saudacao_bem_vindo(sessao.get("genero", "")))
        .replace("__LOGIN_HERO__", sessao["usuario"])
        .replace("__FAVORITOS_HUB__", json.dumps(
            USUARIOS_WEB.get(sessao["usuario"], {}).get("favoritos_hub") or [], ensure_ascii=False,
        ).replace("</", "<\\/"))  # nunca fecha a tag script por acidente
        .replace("__FOOTER__", _montar_footer())
        .replace("__CLASSE_CONTING__", classe_conting)
        .replace("__RESUMO_CONTING__", resumo_conting)
    )


def _montar_usuarios_negado_html(sessao: dict, contexto: str = "Usuários") -> str:
    return (
        _USUARIOS_NEGADO_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, contexto))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_string_connections_html(sessao: dict) -> str:
    return (
        _STRING_CONNECTIONS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "String Connections"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_config_seguro_html(sessao: dict) -> str:
    return (
        _CONFIG_SEGURO_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Criptografia de Dados Sensíveis"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_dash_financeiro_html(sessao: dict) -> str:
    return (
        _DASH_FINANCEIRO_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Atualização Dash Financeiro"))
        .replace("__PODE_VER_LOG_DF__", "true" if _tem_acesso_logs(sessao) else "false")
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_reprocessamento_cte2_html(sessao: dict) -> str:
    return (
        _REPROCESSAMENTO_CTE2_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Reprocessamento CTe2"))
        .replace("__PODE_VER_LOG_RC__", "true" if _tem_acesso_logs(sessao) else "false")
        .replace("__PODE_CONTROLAR_RC__", "true" if sessao.get("admin") else "false")
        .replace("__LOGIN_AUTOR_RC__", _LOGIN_AUTOR_RC)
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_indicadores_mensais_html(sessao: dict) -> str:
    return (
        _INDICADORES_MENSAIS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Indicadores Mensais"))
        .replace("__FOOTER__", _montar_footer())
    )


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


def _montar_perfil_html(sessao: dict, usuario_perfil: str) -> str:
    return (
        _PERFIL_HTML_TEMPLATE
        .replace("__INSIGNIAS__", _INSIGNIAS_HTML)
        .replace("__LOJA_WALLPAPERS__", _LOJA_WALLPAPERS_HTML)
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
        <button type="button" id="fer-botao-tipo-afastamento" onclick="selecionarTipoModal('afastamento')" title="Afastamento pelo INSS e afins (licenças longas)">Afastamento</button>
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
        .replace("__ARQUIVADOS_LOGS__", _texto_arquivados_logs())
    )


def _texto_arquivados_logs() -> str:
    try:
        r = _resumo_arquivados_logs(*_pastas_manutencao_logs())
    except Exception:
        return ""
    if not r["zips"]:
        return ""
    return f" Hoje: {r['zips']} zip(s) guardado(s), {r['bytes'] / (1024 * 1024):.1f} MB." 


def _montar_manutencao_usuarios_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_USUARIOS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção de Usuários (Beta)"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__SENHA_PADRAO__", MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL)
    )


# Indicadores Movidesk embutido no Indicadores Mensais (3.1.6.0): sem a navbar, a página avisa a altura pra aba
# crescer junto (sem barra de rolagem dentro da aba)
_EMBUTIDO_IMX_HTML = """<style>body { padding-top: 14px !important; background: transparent !important; } body::before { display: none !important; }</style>
<script>
(function () {
  function avisarAltura() { parent.postMessage({ alturaIndicadoresMovidesk: document.documentElement.scrollHeight }, location.origin); }
  if (window.ResizeObserver) new ResizeObserver(avisarAltura).observe(document.body);
  window.addEventListener('load', avisarAltura);
  setInterval(avisarAltura, 1500);
})();
</script>
"""


def _montar_indicadores_movidesk_html(sessao: dict, embutido: bool = False) -> str:
    """embutido (3.1.6.0): a mesma tela, sem navbar e rodapé, pra aba dentro do Indicadores Mensais."""
    html = (
        _INDICADORES_MOVIDESK_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", "" if embutido else _montar_navbar(sessao, "Indicadores Movidesk"))
        .replace("__FOOTER__", "" if embutido else _montar_footer())
    )
    return html.replace("</body>", _EMBUTIDO_IMX_HTML + "</body>", 1) if embutido else html


def _montar_horas_trabalhadas_html(sessao: dict) -> str:
    return (
        _HORAS_TRABALHADAS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Horas Trabalhadas"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_automacao_movidesk_html(sessao: dict) -> str:
    return (
        _AUTOMACAO_MOVIDESK_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Automação Movidesk"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_manutencao_alertas_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_ALERTAS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção de Alertas em Banco"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__EMAIL_MONITORAMENTO__", EMAIL_MONITORAMENTO_PADRAO)
        .replace("__SO_LEITURA_ALERTAS__", "false" if _tem_acesso_manutencao_alertas(sessao) else "true")
    )


def _montar_manutencao_rejeicoes_html(sessao: dict) -> str:
    return (
        _MANUTENCAO_REJEICOES_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Manutenção Rejeições em Banco"))
        .replace("__FOOTER__", _montar_footer())
    )


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


def _montar_feedbacks_html(sessao: dict) -> str:
    return (
        _FEEDBACKS_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Feedbacks e Alinhamentos"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__EQUIPES_FEEDBACK__", json.dumps(_equipes_feedback_para_tela(), ensure_ascii=False).replace("</", "<\\/"))
        .replace("__USUARIO_LOGADO_FB__", json.dumps(sessao["usuario"]))
    )


# O que o painel cobre, por área - fonte única da página Sobre (lista completa) e
# do painel da tela de login (só os LIMITE_ITENS_AREA_LOGIN primeiros de cada
# área, então os mais importantes vêm primeiro). Mudou algo no PDA? É aqui.
AREAS_PDA = [
    {"titulo": "Monitoramento e alertas", "cor": "#2db8cf", "itens": [
        "Alertas fiscais automáticos, com agenda, status e log",
        "Contingências SEFAZ (SVC-AN e SVC-RS) por estado, com aviso no Teams",
        "Central de Monitores: atalhos pros monitores de cada cliente",
        "Logs do EmailPack por e-mail processado, com aviso no Teams",
        "Reprocessamento automático de CT-es parados no CTe2 (por Caio Peixoto)",
        "NNU Enchanced (beta): tratativa guiada dos NNUs do ClienteI",
    ]},
    {"titulo": "Relatórios e dados", "cor": "#b0cb1c", "itens": [
        "Relatórios ClienteA diários, enviados sozinhos pro SharePoint",
        "Dash Financeiro mensal pro Power BI, um arquivo por mês",
        "Manutenção de alertas, rejeições e relatórios direto no banco, com String Connections",
        "Dashboards por Cliente (Beta)",
    ]},
    {"titulo": "Equipe e Movidesk", "cor": "#e8a33d", "itens": [
        "Indicadores e automações do Movidesk",
        "Horas trabalhadas por analista",
        "Indicadores Mensais: efetividade dos tickets e justificativa do NOC",
        "Feedbacks e alinhamentos: individual, em grupo ou geral",
        "Comunidade (o início): feed da equipe com aniversários, promoções, insígnias, chegadas, colaborações e publicações com fotos, GIFs e arquivos, com palminhas e comentários",
        "Rankings: bronze, prata, ouro e Master de cada pessoa por produto, com insígnias de Rank Master, e o leaderboard de palminhas",
        "Loja de Palminhas: troque as palminhas recebidas por wallpapers pra capa do perfil e o cartão da Comunidade, sem mexer no ranking",
        "Notificações no topo de todas as telas: palminhas, comentários e versão nova",
        "Insígnias no perfil: tempo de casa, campanha PDA Beta User e destaque junto da foto",
        "Calendário de Férias e Meu Plantão",
        "E-mails automáticos de boas-vindas e de 45/90 dias de empresa",
    ]},
    {"titulo": "Acesso e segurança", "cor": "#b389f9", "itens": [
        "Usuários: login, permissões por pessoa e sincronização com o Movidesk",
        "Credenciais sensíveis cifradas, fora dos arquivos de texto",
        "Log isolado por automação",
        "Changelog com o que mudou em cada versão, a data de criação e os acessos ao PDA",
        "Cards favoritos no começo de cada seção e nos atalhos, salvos por pessoa",
    ]},
]
LIMITE_ITENS_AREA_LOGIN = 3


def _html_areas_pda(classe_card: str, tag_titulo: str, limite: Optional[int] = None, anim_base: Optional[float] = None) -> str:
    """Monta os cards de AREAS_PDA. `anim_base` liga a entrada em cascata da
    tela de login (classe anim-entrada + atraso crescente)."""
    esc = html_utils.escape
    cards = []
    for i, area in enumerate(AREAS_PDA):
        itens = "".join(f"<li>{esc(t)}</li>" for t in area["itens"][:limite])
        anim = (f' anim-entrada" style="--cor-area:{area["cor"]}; animation-delay:{anim_base + i * 0.04:.2f}s"'
                if anim_base is not None else f'" style="--cor-area:{area["cor"]}"')
        cards.append(f'<div class="{classe_card}{anim}><{tag_titulo}>{esc(area["titulo"])}</{tag_titulo}><ul>{itens}</ul></div>')
    return "\n      ".join(cards)


# "Alertas automáticos" do Sobre e do login (3.4.5.0): os alertas cadastrados na Manutenção de Alertas em Banco
# (CONFIGURACOES_ALERTA), não mais os jobs do Alertas Suporte (Legacy). O login não pode esperar o banco: o número fica
# guardado (memória + numeros_sobre.json, fora do git) e é renovado numa thread a cada 10 minutos; sem nunca ter
# conseguido ler, usa a quantidade de jobs do Legacy.
_cache_alertas_sobre = {"total": None, "em": 0.0, "buscando": False}
ARQUIVO_NUMEROS_SOBRE = "numeros_sobre.json"


def _renovar_alertas_sobre() -> None:
    try:
        res = _contar_alertas_mapeados()
        if res.get("ok"):
            _cache_alertas_sobre["total"] = res["total"]
            try:
                with open(os.path.join(_base_path_app(), ARQUIVO_NUMEROS_SOBRE), "w", encoding="utf-8") as f:
                    json.dump({"alertas_mapeados": res["total"], "ativos": res["ativos"],
                               "em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}, f)
            except OSError:
                pass
    finally:
        _cache_alertas_sobre["em"] = time.time()
        _cache_alertas_sobre["buscando"] = False


def _numero_alertas_sobre() -> int:
    if _cache_alertas_sobre["total"] is None:
        try:
            with open(os.path.join(_base_path_app(), ARQUIVO_NUMEROS_SOBRE), "r", encoding="utf-8") as f:
                _cache_alertas_sobre["total"] = int(json.load(f).get("alertas_mapeados"))
        except Exception:
            pass
    if time.time() - _cache_alertas_sobre["em"] > 600 and not _cache_alertas_sobre["buscando"]:
        _cache_alertas_sobre["buscando"] = True
        threading.Thread(target=_renovar_alertas_sobre, daemon=True, name="numeros_sobre").start()
    return _cache_alertas_sobre["total"] if _cache_alertas_sobre["total"] is not None else len(JOBS)


def _numeros_sobre() -> dict:
    """Números da página Sobre, contados a partir do próprio código (antes eram
    fixos no HTML e ficaram desatualizados - ex.: "16 cards" com 20 no hub)."""
    textos_cards = [v for k, v in globals().items()
                    if isinstance(v, str) and (k.startswith("_CARD") or k == "_HUB_HTML_TEMPLATE")]
    # card ativo é <a class="card-hub" ...>; o "Em construção" é <div class="card-hub bloqueado">
    n_cards = sum(t.count('<a class="card-hub"') for t in textos_cards)
    em_construcao = []
    for t in textos_cards:
        em_construcao += re.findall(r'<div class="card-hub bloqueado".*?<h2>([^<]+)</h2>', t, re.S)
    return {
        "alertas": _numero_alertas_sobre(),
        "clientes_monitores": len(_central_carregar()),
        "produtos_df": len(ORDEM_PRODUTOS_DASH_FINANCEIRO),
        "cards": n_cards,
        "em_construcao": [html_utils.escape(n.strip()) for n in em_construcao],
    }


def _montar_sobre_html(sessao: dict) -> str:
    n = _numeros_sobre()
    em_construcao = (
        f'<div class="em-construcao-sobre">Em construção: {", ".join(n["em_construcao"])}.</div>'
        if n["em_construcao"] else ""
    )
    return (
        _SOBRE_HTML_TEMPLATE
        .replace("__VERSAO_SOBRE__", html_utils.escape(VERSAO_PDA))
        .replace("__N_ALERTAS__", str(n["alertas"]))
        .replace("__N_CLIENTES_MONITORES__", str(n["clientes_monitores"]))
        .replace("__N_PRODUTOS_DF__", str(n["produtos_df"]))
        .replace("__N_CARDS__", str(n["cards"]))
        .replace("__N_ACESSOS__", f'{_resumo_acessos()["total"]:,}'.replace(",", "."))
        .replace("__DATA_CRIACAO__", DATA_CRIACAO_PDA.strftime("%d/%m/%Y"))
        .replace("__DIAS_PDA__", str(_dias_do_pda()))
        .replace("__EM_CONSTRUCAO_SOBRE__", em_construcao)
        .replace("__AREAS_SOBRE__", _html_areas_pda("area-sobre", "h3"))
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Sobre o PDA"))
        .replace("__FOOTER__", _montar_footer())
    )


def _html_entradas_changelog(entradas: list) -> str:
    """Linha do tempo de entradas de CHANGELOG_PDA (uma por MINOR). A primeira de todas
    (a mais recente) ganha o selo com a versão completa que está rodando."""
    esc = html_utils.escape
    ordem = list(CATEGORIAS_CHANGELOG)
    blocos = []
    for entrada in entradas:
        atual = entrada is CHANGELOG_PDA[0]
        # sorted é estável: dentro da mesma categoria, mantém a ordem em que foi escrito
        itens_ordenados = sorted(entrada["itens"], key=lambda it: ordem.index(it[0]) if it[0] in ordem else len(ordem))
        itens = "".join(
            f'<li><span class="tag-categoria" style="--cor-cat:{CATEGORIAS_CHANGELOG.get(tipo, ("", "#97a2a8"))[1]}">'
            f'{esc(CATEGORIAS_CHANGELOG.get(tipo, (tipo.capitalize(), ""))[0])}</span><span>{esc(texto)}</span></li>'
            for tipo, texto in itens_ordenados
        )
        blocos.append(
            f'<div class="entrada-changelog{" atual" if atual else ""}">'
            f'<div class="topo-entrada"><span class="chip-versao-changelog">v{esc(entrada["versao"])}</span>'
            f'<span class="data-entrada">{esc(entrada["data"])}</span>'
            + (f'<span class="selo-atual">Atual: v{esc(VERSAO_PDA)}</span>' if atual else "")
            + f'</div><h3>{esc(entrada["titulo"])}</h3><ul>{itens}</ul></div>'
        )
    return "\n        ".join(blocos)


def _montar_longnamejanitor_html(sessao: dict) -> str:
    return (
        _LONGNAMEJANITOR_HTML_TEMPLATE
        .replace("__FAVICON__", _LOGO_DATA_URI)  # importado depois da troca geral do ícone
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "LongNameJanitor ClienteQ · Beta"))
        .replace("__PODE_CONTROLAR_LNJ__", "true" if sessao.get("admin") else "false")
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_consumo_indevido_html(sessao: dict) -> str:
    return (
        _CONSUMO_INDEVIDO_HTML_TEMPLATE
        .replace("__FAVICON__", _LOGO_DATA_URI)  # importado depois da troca geral do ícone
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Consumo Indevido · Beta"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_loja_html(sessao: dict) -> str:
    return (
        _LOJA_HTML_TEMPLATE
        .replace("__FAVICON__", _LOGO_DATA_URI)  # importado depois da troca geral do ícone
        .replace("__LOJA_WALLPAPERS__", _LOJA_WALLPAPERS_HTML)
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Loja de Palminhas"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_gmud_html(sessao: dict) -> str:
    return (
        _GMUD_HTML_TEMPLATE
        .replace("__FAVICON__", _LOGO_DATA_URI)  # importado depois da troca geral do ícone
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Calendário de GMUD's · Beta"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_fluxograma_html(sessao: dict) -> str:
    return (
        _FLUXOGRAMA_HTML_TEMPLATE
        .replace("__FAVICON__", _LOGO_DATA_URI)  # importado depois da troca geral do ícone
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Fluxograma do PDA · Beta"))
        .replace("__FOOTER__", _montar_footer())
    )


_PRINTS_HISTORICO_DECODIFICADOS: dict = {}


def _print_historico(era: str):
    """JPEG da era (v1, v2, v3) pro changelog, decodificado uma vez só."""
    if era not in _PRINTS_HISTORICO_DECODIFICADOS:
        from telas.historico_prints import PRINTS_HISTORICO
        if era not in PRINTS_HISTORICO:
            return None
        _PRINTS_HISTORICO_DECODIFICADOS[era] = base64.b64decode(PRINTS_HISTORICO[era])
    return _PRINTS_HISTORICO_DECODIFICADOS[era]


def _montar_nnu_enchanced_html(sessao: dict) -> str:
    return (
        _NNU_ENCHANCED_HTML_TEMPLATE
        # 3.4.9.0: as automações de NNU são abas dentro do NNU Enchanced (hoje a do status 20 → 15)
        .replace("__NNU_AUTOMACAO_CSS__", _NNU_STATUS_CSS)
        .replace("__NNU_AUTOMACAO_STATUS__", _NNU_STATUS_CORPO)
        .replace("__NNU_AUTOMACAO_JS__", _NNU_STATUS_JS.replace("__PODE_CONTROLAR_NNU__", "true" if sessao.get("admin") else "false"))
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "NNU Enchanced · Beta"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_ranks_produtos_html(sessao: dict) -> str:
    return (
        _RANKS_PRODUTOS_HTML_TEMPLATE
        .replace("__INSIGNIAS__", _INSIGNIAS_HTML)
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Rankings"))
        .replace("__FOOTER__", _montar_footer())
    )


def _montar_changelog_html(sessao: dict) -> str:
    """Changelog por era (3.0.0.0): v3.x, v2.x e v1.x resumidas (HISTORICO_PDA); as eras
    que têm entradas em CHANGELOG_PDA ganham o "Ver detalhamento" versão por versão."""
    esc = html_utils.escape
    atalhos = "".join(
        f'<a href="#historico-v{esc(era["versao"][0])}" style="--cor-era:{esc(era["cor"])}">v{esc(era["versao"])}</a>'
        for era in HISTORICO_PDA
    )
    return (
        _CHANGELOG_HTML_TEMPLATE
        .replace("__ATALHOS_ERAS__", atalhos)
        .replace("__MARCOS_PDA__", (
            f'<span class="marco-pda">🎂 Criado em <b>{DATA_CRIACAO_PDA.strftime("%d/%m/%Y")}</b> · há {_dias_do_pda()} dias</span>'
            f'<span class="marco-pda">🚪 <b>{_resumo_acessos()["total"]:,}</b> acessos ao PDA</span>'.replace(",", ".")
        ))
        .replace("__HISTORICO_PDA__", _html_historico_pda())
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Changelog"))
        .replace("__FOOTER__", _montar_footer())
    )


# Ícones dos grupos do histórico (traço, 24x24) - chaves usadas em HISTORICO_PDA
ICONES_HISTORICO = {
    "base": '<path d="M4 7l8-4 8 4-8 4-8-4z"/><path d="M4 12l8 4 8-4"/><path d="M4 17l8 4 8-4"/>',
    "alerta": '<path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.9 1.9 0 0 0 3.4 0"/>',
    "banco": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/><path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>',
    "equipe": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/>',
    "pessoas": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.5a6.5 6.5 0 0 1 3.5 5.5"/>',
    "painel": '<rect x="3" y="4" width="18" height="14" rx="2"/><path d="M8 21h8M12 18v3"/><path d="M7 9h5M7 13h10"/>',
}


def _html_lembranca_era(era: dict) -> str:
    """Bloco "📸 Lembra?" da era (3.3.1.0): o print da época (servido por /historico-print/) e o texto."""
    lembranca = era.get("lembranca")
    if not lembranca:
        return ""
    esc = html_utils.escape
    src = f'/historico-print/{esc(lembranca["print"])}.jpg'
    return (
        '<div class="lembranca-era">'
        f'<button type="button" class="foto-lembranca" onclick="ampliarLembranca(this)" aria-label="Ampliar o print: {esc(lembranca["legenda"])}">'
        f'<img src="{src}" alt="{esc(lembranca["legenda"])}" loading="lazy"><span class="legenda-lembranca">{esc(lembranca["legenda"])}</span></button>'
        f'<div class="texto-lembranca"><div class="rotulo-lembranca">📸 Lembra?</div><p>{esc(lembranca["texto"])}</p></div>'
        '</div>'
    )


def _html_historico_pda() -> str:
    """Uma era por MAJOR (v3.x, v2.x, v1.x), com resumo, trilha opcional (jornada),
    grupos temáticos e, se a MAJOR tem entradas em CHANGELOG_PDA, o detalhamento
    versão por versão (aberto na era atual, fechado nas outras)."""
    esc = html_utils.escape
    eras = []
    for indice_era, era in enumerate(HISTORICO_PDA):
        major = era["versao"].split(".")[0]
        entradas = [e for e in CHANGELOG_PDA if e["versao"].split(".")[0] == major]
        detalhe = ""
        if entradas:
            primeira = entradas[-1]["versao"]
            # a v2 só tem changelog por versão a partir da 2.29: avisa que antes disso é só o resumo
            aviso = (f'<p class="aviso-detalhe">O changelog por versão começa na v{esc(primeira)}; antes disso, só o resumo acima.</p>'
                     if not primeira.endswith(".0") else "")
            qtd_versoes = f'{len(entradas)} {"versão" if len(entradas) == 1 else "versões"}'
            detalhe = (
                f'<details class="detalhe-era">'
                f'<summary><span class="texto-fechado">Ver detalhamento</span><span class="texto-aberto">Esconder detalhamento</span>'
                f'<span class="qtd-detalhe">{qtd_versoes} · v{esc(primeira)} a v{esc(entradas[0]["versao"])}</span></summary>'
                if len(entradas) > 1 else
                f'<details class="detalhe-era">'
                f'<summary><span class="texto-fechado">Ver detalhamento</span><span class="texto-aberto">Esconder detalhamento</span>'
                f'<span class="qtd-detalhe">{qtd_versoes} · v{esc(primeira)}</span></summary>'
            ) + f'<div class="linha-tempo">{_html_entradas_changelog(entradas)}</div>{aviso}</details>'

        grupos = "".join(
            '<div class="grupo-historico">'
            f'<div class="titulo-grupo-historico"><span class="icone-grupo-historico"><svg viewBox="0 0 24 24" fill="none" '
            f'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">{ICONES_HISTORICO.get(grupo["icone"], "")}</svg></span>'
            f'{esc(grupo["titulo"])}</div><ul>' + "".join(f"<li>{esc(item)}</li>" for item in grupo["itens"]) + "</ul></div>"
            for grupo in era["grupos"]
        )
        jornada = ""
        if era.get("jornada"):
            passos = []
            # 3.3.2.2: o laço usava "detalhe" e sobrescrevia o "Ver detalhamento" da era (na v1 sobrava "painel web" solto)
            for i, (titulo, detalhe_passo) in enumerate(era["jornada"]):
                ultimo = i == len(era["jornada"]) - 1
                passos.append(
                    f'<div class="passo-jornada{" destino" if ultimo else ""}"><span class="num-passo">{i + 1}</span>'
                    f'<div><div class="titulo-passo">{esc(titulo)}</div><div class="detalhe-passo">{esc(detalhe_passo)}</div></div></div>'
                )
            jornada = f'<div class="jornada-historico" style="--passos:{len(passos)}">' + "".join(passos) + "</div>"
        qtd = sum(len(g["itens"]) for g in era["grupos"])
        eras.append(
            f'<section class="era-historico" id="historico-v{esc(era["versao"][0])}" style="--cor-era:{esc(era["cor"])}" data-marca="v{esc(era["versao"][0])}">'
            '<div class="cab-era">'
            f'<div class="num-era">v{esc(era["versao"])}</div>'
            f'<div class="info-era"><div class="nome-era">{esc(era["nome"])}</div>'
            f'<div class="selos-era"><span class="selo-era">{esc(era["periodo"])}</span>'
            f'<span class="selo-era neutro">{len(era["grupos"])} frentes · {qtd} marcos</span></div></div>'
            "</div>"
            f'<p class="resumo-era">{esc(era["resumo"])}</p>'
            f'{_html_lembranca_era(era)}'
            f'{jornada}<div class="grupos-historico">{grupos}</div>{detalhe}'
            "</section>"
        )
    return "\n      ".join(eras)


def _montar_relatorios_cliente_a_html(sessao: dict) -> str:
    return (
        _RELATORIOS_CLIENTE_A_HTML_TEMPLATE
        .replace("__NAVBAR_CSS__", _NAVBAR_CSS)
        .replace("__NAVBAR__", _montar_navbar(sessao, "Relatórios ClienteA"))
        .replace("__FOOTER__", _montar_footer())
        .replace("__HORARIO_AUTOMATICO__", HORARIO_RELATORIO_CLIENTE_A_AUTOMATICO)
    )


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
    "_HUB_HTML_TEMPLATE", "_USUARIOS_NEGADO_TEMPLATE",
    "_MANUTENCAO_ALERTAS_HTML_TEMPLATE", "_MANUTENCAO_REJEICOES_HTML_TEMPLATE", "_MANUTENCAO_RELATORIOS_HTML_TEMPLATE", "_SOBRE_HTML_TEMPLATE", "_RELATORIOS_CLIENTE_A_HTML_TEMPLATE",
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
    # Central de Monitores: __LOGO__ vira a logo do ambiente Saas no card do cliente
    "_DIRECIONAMENTO_WEBMONITORS_HTML",
    "_CHANGELOG_HTML_TEMPLATE",
    "_RANKS_PRODUTOS_HTML_TEMPLATE",
    "_NNU_ENCHANCED_HTML_TEMPLATE",
):
    globals()[_nome_template] = (
        globals()[_nome_template]
        .replace("__FAVICON__", _LOGO_DATA_URI)
        .replace("__LOGO__", _LOGO_DATA_URI)
    )

# Ícone da aba em QUALQUER template, sem depender da lista acima: Feedbacks,
# Dashboards por Cliente e Indicadores Mensais ficaram fora dela e a aba do
# navegador aparecia sem o ícone da Empresa (2.34.3.0). O __LOGO__ continua só
# na lista, porque em alguns templates ele é trocado de outro jeito.
for _nome_template, _texto in list(globals().items()):
    if _nome_template.startswith("_") and isinstance(_texto, str) and "__FAVICON__" in _texto:
        globals()[_nome_template] = _texto.replace("__FAVICON__", _LOGO_DATA_URI)


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
# Usuários do PDA e sessões: mora em nucleo/ desde 26/09/2026
# ---------------------------------------------------------------------------
from nucleo.usuarios import (  # noqa: E402
    SESSIONS,
    USUARIOS_WEB,
    _salvar_usuarios,
    atualizar_cargos_movidesk,
    definir_favoritos_hub,
)




# ---------------------------------------------------------------------------
# Fotos de perfil
# ---------------------------------------------------------------------------
# Uma foto por login, salva como arquivo (não em base64 dentro do JSON, pra
# não inchar usuarios.json) - a própria pessoa ou um admin consegue trocar.

# ---------------------------------------------------------------------------
# Fotos de perfil: mora em nucleo/ desde 26/09/2026
# ---------------------------------------------------------------------------
from nucleo.fotos import (  # noqa: E402
    _EXTENSOES_FOTO_PERMITIDAS,
    _caminho_foto_usuario,
    _migrar_fotos_iniciais_perfil,
    _salvar_foto_usuario,
)




# ---------------------------------------------------------------------------
# Feedbacks e Alinhamentos: mora em areas/feedbacks/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.feedbacks.logica import (  # noqa: E402
    FEEDBACKS_USUARIOS,
    _descricao_alvo_feedback,
    autores_do_registro as _autores_do_registro_fb,
    destinatarios_equipe_feedback as _destinatarios_equipe_fb,
    equipe_do_registro as _equipe_do_registro_fb,
    avisar_equipe_no_sininho as _avisar_equipe_fb_no_sininho,
    equipes_feedback_para_tela as _equipes_feedback_para_tela,
    equipes_visiveis_feedback as _equipes_visiveis_fb,
    pode_ver_registro_feedback as _pode_ver_registro_fb,
    ve_todas_equipes_feedback as _ve_todas_equipes_fb,
    validar_alvos_e_autores as _validar_alvos_e_autores_fb,
    _lock_feedbacks_usuarios,
    _pasta_anexos_feedbacks,
    _salvar_anexo_feedback,
    _salvar_feedbacks_usuarios,
)






# ---------------------------------------------------------------------------
# Perfil: mora em areas/perfil/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.perfil.logica import (  # noqa: E402
    HISTORICO_CARREIRA,
    _caminho_historico_carreira_json,
    _lock_historico_carreira,
    _montar_dados_perfil,
    _montar_dados_perfil_mes_anterior,
    _salvar_historico_carreira,
)




# ---------------------------------------------------------------------------
# Calendário de Férias
# ---------------------------------------------------------------------------
# Registros simples de período de férias por usuário cadastrado no PDA -
# qualquer um logado pode ver, só admin pode cadastrar/remover.

# ---------------------------------------------------------------------------
# Calendário de Férias: mora em areas/ferias/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.ferias.logica import (  # noqa: E402
    FERIAS,
    _lock_ferias,
    _periodos_se_sobrepoem,
    _salvar_ferias,
)










_proximo_id_ferias = max([f.get("id", 0) for f in FERIAS], default=0) + 1

if not os.path.exists(_caminho_historico_carreira_json()):
    _salvar_historico_carreira(HISTORICO_CARREIRA)
_proximo_id_historico_carreira = max([h.get("id", 0) for h in HISTORICO_CARREIRA], default=0) + 1

_proximo_id_feedback_usuario = max([f.get("id", 0) for f in FEEDBACKS_USUARIOS], default=0) + 1


# ---------------------------------------------------------------------------
# Equipes: mora em nucleo/ desde 26/09/2026
# ---------------------------------------------------------------------------
from nucleo.equipes import (  # noqa: E402
    ATRIBUICOES_VALIDAS as _ATRIBUICOES_VALIDAS,
)






# ---------------------------------------------------------------------------
# String Connections - registro de strings de conexão reutilizáveis, por
# cliente + produto (ex.: "ClienteG" + "NFCom", "ClienteE" + "NFe"). Usado na
# Manutenção de Alertas em Banco pra não precisar digitar/colar a mesma
# string de conexão toda vez que um novo alerta é criado pro mesmo cliente -
# só admin mexe aqui, mas qualquer pessoa com acesso à Manutenção de Alertas
# (admin ou view com a permissão extra) pode ESCOLHER uma já cadastrada na
# hora de criar/editar um alerta.
# Guardado localmente (string_connections.json, mesmo padrão do
# usuarios.json) - não fica na tabela CONFIGURACOES_ALERTA do banco de
# monitoramento, só alimenta o campo CONEXAO na hora de criar/editar.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# String Connections: mora em areas/string_connections/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.string_connections.logica import (  # noqa: E402
    STRING_CONNECTIONS,
    _buscar_string_connection_igual,
    _salvar_string_connections,
)


_proximo_id_string_connection = max([int(k) for k in STRING_CONNECTIONS], default=0) + 1


# ---------------------------------------------------------------------------
# Manutenção de Usuários: mora em areas/manutencao_usuarios/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.manutencao_usuarios.logica import (  # noqa: E402
    MANUTENCAO_USUARIOS_AREAS,
    MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL,
    _manutencao_usuarios_build_targets,
    _manutencao_usuarios_diagnostico,
    _manutencao_usuarios_executar,
    _manutencao_usuarios_sanitize,
    _manutencao_usuarios_validar_texto,
)




# ---------------------------------------------------------------------------
# E-mails automáticos: mora em areas/emails/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.emails.logica import (  # noqa: E402
    _enviar_email_boas_vindas,
    _executar_alertas_tempo_de_empresa,
    _notificar_feedback_inserido,
)






# ---------------------------------------------------------------------------
# Sessões e permissões: mora em nucleo/ desde 26/09/2026
# ---------------------------------------------------------------------------
from nucleo.acesso import (  # noqa: E402
    _criar_sessao,
    _sessao_atual,
    consumir_troca_pendente,
    criar_troca_senha_pendente,
    usuario_da_troca_pendente,
    _tem_acesso_dados_sensiveis,
    _tem_acesso_dash_financeiro,
    _tem_acesso_dashboards_clientes,
    _tem_acesso_nnu_enchanced,
    _tem_acesso_nnu_status,
    _tem_acesso_servicos_adm,
    _tem_acesso_feedbacks,
    _tem_acesso_indicadores_mensais,
    _tem_acesso_logs,
    _tem_acesso_manutencao_alertas,
    _tem_acesso_manutencao_rejeicoes,
    _tem_acesso_manutencao_relatorios,
    _tem_acesso_manutencao_usuarios,
    _tem_acesso_relatorios_cliente_a,
)

# ---------------------------------------------------------------------------
# Insígnias do perfil (Beta User, Dev/Founder, Contributor, tempo de casa): areas/perfil/insignias.py desde a 2.35.5.0
from areas.perfil.insignias import (  # noqa: E402
    campanha as _campanha_insignias,
    conceder as _conceder_insignia,
    concessoes as _concessoes_insignias,
    definir_destaque as _definir_insignia_destaque,
    destaque_de as _insignia_destaque_de,
    insignias_de as _insignias_de,
    marcar_vistas as _marcar_insignias_vistas,
    validar_participacao as _validar_participacao_insignias,
)
# Comunicado da v3 por e-mail (3.0.3.0): já foi enviado; desde a 3.1.3.0 o botão de envio saiu do /changelog
# (ficaram só a prévia e o status, pros fundadores)
from areas.emails.comunicado_v3 import (  # noqa: E402
    montar_email_v3_html as _html_email_v3,
    status as _status_comunicado_v3,
)
from areas.perfil.insignias import FUNDADORES as _FUNDADORES_PDA, _esta_em as _esta_em_grupo_insignia  # noqa: E402


def _e_fundador(sessao: dict) -> bool:
    return _esta_em_grupo_insignia(_FUNDADORES_PDA, sessao["usuario"])


# Ranks por Produtos (Beta, 3.0.7.0): todo mundo vê; os administradores atribuem os níveis e os ouros liberam o Rank Ouro
from areas.ranks_produtos.logica import (  # noqa: E402
    arquivar_pessoa as _arquivar_pessoa_rank,
    definir_nivel as _definir_nivel_rank,
    restaurar_pessoa as _restaurar_pessoa_rank,
    mexer_produto as _mexer_produto_rank,
    visao as _visao_ranks,
)

# Mural do início (linha do tempo com palminhas): areas/mural desde a 2.35.7.0
from areas.mural.logica import (  # noqa: E402
    alternar_palma as _alternar_palma_mural,
    apagar_comentario as _apagar_comentario_mural,
    apagar_publicacao as _apagar_publicacao_mural,
    comentar as _comentar_mural,
    imagem_do_comentario as _imagem_comentario_mural,
    mural as _dados_mural,
    numeros_equipe as _numeros_equipe_mural,
    numeros_movidesk as _numeros_movidesk_mural,
    numeros_movidesk_equipe as _numeros_movidesk_equipe_mural,
    EQUIPES_GESTAO as _EQUIPES_GESTAO_MURAL,
)
# LongNameJanitor ClienteQ (beta, 3.3.2.0): areas/longnamejanitor
from areas.longnamejanitor.logica import (  # noqa: E402
    MonitorLongNameJanitor,
    definir_ligado as _definir_ligado_lnj,
    definir_simulacao as _definir_simulacao_lnj,
    ler_historico as _ler_historico_lnj,
    salvar_config as _salvar_config_lnj,
    status as _status_lnj,
    varredura_manual as _varredura_manual_lnj,
    mover_tudo_do_processado as _mover_tudo_processado_lnj,
)
from areas.longnamejanitor.tela import _LONGNAMEJANITOR_HTML_TEMPLATE  # noqa: E402
# Loja de Palminhas e Halloween 2026 (3.3.7.0): areas/loja
import areas.loja.halloween as _halloween  # noqa: E402
from areas.loja.logica import (  # noqa: E402
    comprar as _comprar_loja,
    usar as _usar_loja,
    visao as _visao_loja,
    wallpaper_de as _wallpaper_de,
)
from areas.loja.tela import _LOJA_HTML_TEMPLATE  # noqa: E402
# Monitoramento de Consumo Indevido (beta, 3.4.3.0): areas/consumo_indevido
from areas.consumo_indevido.logica import (  # noqa: E402
    MonitorConsumoIndevido,
    definir_ligado as _definir_ligado_ci,
    executar as _executar_ci,
    salvar_config as _salvar_config_ci,
    status as _status_ci,
    testar_consulta as _testar_consulta_ci,
    teste_teams as _teste_teams_ci,
)
from areas.consumo_indevido.tela import _CONSUMO_INDEVIDO_HTML_TEMPLATE  # noqa: E402
# NNU · status 20 → 15 (beta, 3.4.9.0): areas/nnu_status
from areas.nnu_status.logica import (  # noqa: E402
    MonitorNnuStatus,
    caminho_relatorio as _relatorio_nnu_status,
    definir_ligado as _ligar_nnu_status,
    definir_simulacao as _simulacao_nnu_status,
    rodar as _rodar_nnu_status,
    detalhe_lote as _detalhe_lote_nnu_status,
    reenviar_email as _reenviar_nnu_status,
    salvar_config as _config_nnu_status,
    status as _status_nnu_status,
    testar as _testar_nnu_status,
)
from areas.nnu_status.tela import _NNU_STATUS_CORPO, _NNU_STATUS_CSS, _NNU_STATUS_JS  # noqa: E402
from telas.halloween import _HALLOWEEN_HTML  # noqa: E402
from telas.loja_wallpapers import _LOJA_WALLPAPERS_HTML  # noqa: E402
# Serviços (3.3.1.0): Calendário de GMUD's; e o Fluxograma do PDA (beta, só admin)
from areas.servicos.logica import listar_gmuds as _listar_gmuds  # noqa: E402
from areas.servicos.tela import _GMUD_HTML_TEMPLATE  # noqa: E402
from telas.fluxograma import _FLUXOGRAMA_HTML_TEMPLATE  # noqa: E402
# Central de Monitores editável (3.2.8.0): areas/central_monitores
from areas.central_monitores.logica import (  # noqa: E402
    carregar as _central_carregar,
    dados_da_pagina as _central_dados_pagina,
    json_para_script as _central_json_script,
    pode_editar as _central_pode_editar,
    salvar as _central_salvar,
    versao as _central_versao,
)
# Publicações manuais na Comunidade (3.2.6.0): areas/mural/posts.py
from areas.mural.posts import (  # noqa: E402
    arquivo_do_post as _arquivo_post_mural,
    criar_post as _criar_post_mural,
    reenviar_teams as _reenviar_teams_post,
    votar as _votar_post_mural,
)
# Sininho de notificações da navbar (palminhas, comentários, versão nova): nucleo/notificacoes.py desde a 3.0.1.0
from nucleo.notificacoes import (  # noqa: E402
    listar as _listar_notificacoes,
    marcar_lidas as _marcar_notificacoes_lidas,
)

# Manutenção dos logs (3.4.8.0, antes só apagava log parado havia 30 dias): nucleo/limpeza_logs.py
from nucleo.limpeza_logs import manter_logs as _manter_logs, resumo_arquivados as _resumo_arquivados_logs  # noqa: E402
HORARIO_LIMPEZA_LOGS = "03:40"


def _pastas_manutencao_logs() -> tuple:
    return (_PASTA_LOGS, os.path.join(_base_path_app(), "reprocessamento_cte2"),
            os.path.join(_base_path_app(), "longnamejanitor", "historico"))


def _limpar_logs_antigos() -> None:
    try:
        _manter_logs(*_pastas_manutencao_logs())
    except Exception:
        logger.exception("Falha na manutenção dos logs.")


# Anúncios de uma vez só (3.2.0.0): o GIF do Mario vem de telas/anuncios.py e é decodificado uma vez
from nucleo.notificacoes import marcar_anuncio_visto as _marcar_anuncio_visto  # noqa: E402
_GIF_MARIO_CACHE: dict = {}


def _gif_mario_anuncio() -> bytes:
    if "gif" not in _GIF_MARIO_CACHE:
        import base64 as _b64
        from telas.anuncios import MARIO_GIF_BASE64
        _GIF_MARIO_CACHE["gif"] = _b64.b64decode(MARIO_GIF_BASE64)
    return _GIF_MARIO_CACHE["gif"]


# Aviso de usuário desativado (3.1.5.0): data no usuarios.json, aviso no mural e no sininho de todo mundo
from nucleo.desativacao import avisar_mudanca as _avisar_mudanca_status, marcar_status as _marcar_status_usuario  # noqa: E402

# Reprocessamento CTe2 (automação do Caio Peixoto): areas/reprocessamento_cte2/ desde a 2.35.4.0
from areas.reprocessamento_cte2.logica import (  # noqa: E402
    MonitorReprocessamentoCte2,
    DESENVOLVIDO_POR_LOGIN as _LOGIN_AUTOR_RC,
    definir_api_key as _definir_api_key_rc,
    definir_ligado as _definir_ligado_rc,
    iniciar_execucao_manual as _iniciar_ciclo_manual_rc,
    ler_registros as _ler_registros_rc,
    liberar_chave as _liberar_chave_rc,
    status as _status_rc,
)

# Indicadores Mensais (efetividade e NOC no banco do Movidesk): areas/indicadores_mensais/ desde a 2.33.7.0
# ---------------------------------------------------------------------------
from areas.indicadores_mensais.logica import (  # noqa: E402
    definir_considerar_satisfacao as _definir_considerar_satisfacao_imx,
    definir_efetividade as _definir_efetividade_imx,
    definir_justificativa_noc as _definir_justificativa_noc_imx,
    listar_efetividade_pendente as _listar_efetividade_imx,
    listar_noc_pendente as _listar_noc_imx,
    listar_satisfacao as _listar_satisfacao_imx,
)






# ---------------------------------------------------------------------------
# Dashboards por Cliente: mora em areas/dashboards_clientes/ desde 26/09/2026
# ---------------------------------------------------------------------------
from areas.dashboards_clientes.logica import (  # noqa: E402
    _carregar_dashboards_clientes,
    _consultar_dashboard_cliente_b_nfag,
)




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


def _validar_campos_historico_carreira(dados: dict):
    """Confere cargo, área e período de um item do histórico de carreira (criar e editar).
    Devolve ((cargo, area, inicio, fim), None) ou (None, mensagem de erro)."""
    cargo = (dados.get("cargo") or "").strip()
    area = dados.get("area", "")
    inicio = dados.get("inicio", "")
    fim = (dados.get("fim") or "").strip()
    if not cargo or len(cargo) > 60:
        return None, "informe um cargo válido (até 60 caracteres)"
    if area not in ("suporte", "monitoramento", ""):
        return None, "área inválida"
    # "AAAA-MM" (mês/ano) - mais simples que dia exato, já que
    # mudança de cargo normalmente não tem um "dia" específico
    if not re.match(r"^\d{4}-\d{2}$", inicio):
        return None, "data de início inválida (use mês/ano)"
    if fim and not re.match(r"^\d{4}-\d{2}$", fim):
        return None, "data de fim inválida (use mês/ano, ou deixe em branco pro cargo atual)"
    if fim and fim < inicio:
        return None, "a data de fim não pode ser antes do início"
    return (cargo, area, inicio, fim), None


def _destino_seguro(caminho: str) -> bool:
    """Só caminho do próprio PDA ("/algo"): nada de "//outro-site", esquema ou quebra de linha (redirecionamento aberto)."""
    return (isinstance(caminho, str) and caminho.startswith("/") and not caminho.startswith("//") and "\\" not in caminho
            and not any(c in caminho for c in "\r\n") and len(caminho) <= 500 and not caminho.startswith("/login"))


class _PainelHTTPHandler(BaseHTTPRequestHandler):
    job_states: List[JobState] = []
    state_by_nome: dict = {}

    def log_message(self, format, *args):
        pass  # silencia o log padrão do http.server no console

    def _pegar_token(self) -> Optional[str]:
        return self._pegar_cookie("session")

    def _pegar_cookie(self, nome: str) -> Optional[str]:
        cookie_header = self.headers.get("Cookie", "")
        for parte in cookie_header.split(";"):
            parte = parte.strip()
            if parte.startswith(nome + "="):
                return parte[len(nome) + 1:]
        return None

    def _sessao(self, renovar: bool = True) -> Optional[dict]:
        return _sessao_atual(self._pegar_token(), renovar=renovar)

    def _ler_corpo_form(self) -> dict:
        length = int(self.headers.get("Content-Length", 0) or 0)
        corpo = self.rfile.read(length).decode("utf-8") if length else ""
        dados = urllib.parse.parse_qs(corpo)
        return {k: v[0] for k, v in dados.items()}

    def _enviar_comprimido(self, corpo: bytes, tipo: str, status: int) -> None:
        """Manda o corpo com gzip quando o navegador aceita (3.3.4.0): as telas têm 100-300 KB de HTML/CSS/JS, que
        caem pra um quarto. Corpo pequeno ou cliente sem gzip (scripts, validar.py) vai como antes."""
        aceita = "gzip" in (self.headers.get("Accept-Encoding") or "").lower()
        if aceita and len(corpo) > _GZIP_MINIMO:
            corpo = gzip.compress(corpo, compresslevel=6)
        else:
            aceita = False
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        if aceita:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _enviar_json(self, dados: dict, status: int = 200) -> None:
        corpo = json.dumps(dados, default=_json_serializar_padrao).encode("utf-8")
        self._enviar_comprimido(corpo, "application/json; charset=utf-8", status)

    def _enviar_html(self, html: str, status: int = 200) -> None:
        html = self._com_halloween(html)
        # logo por endereço em vez de embutida (3.3.4.0); só em atributo href/src, nunca dentro de JSON/JS
        html = html.replace('href="' + _LOGO_DATA_URI + '"', 'href="' + _LOGO_URL + '"').replace(
            'src="' + _LOGO_DATA_URI + '"', 'src="' + _LOGO_URL + '"')
        self._enviar_comprimido(html.encode("utf-8"), "text/html; charset=utf-8", status)

    def _com_halloween(self, html: str) -> str:
        """Tema de Halloween (3.3.7.0) antes do </body>: de 24/10 a 01/11 pra todo mundo; fora disso só na prévia de
        administrador (?previa_halloween=1 ou o cookie que a própria prévia grava). Fora do período e sem prévia, nada."""
        try:
            sessao_hw = self._sessao(renovar=False)
            admin_hw = bool(sessao_hw and USUARIOS_WEB.get(sessao_hw["usuario"], {}).get("admin"))
            pediu_previa = ("previa_halloween=1" in (urllib.parse.urlparse(self.path).query or "")
                            or self._pegar_cookie(_halloween.COOKIE_PREVIA) == "1")
            previa_hw = admin_hw and pediu_previa
            if not (_halloween.ativo() or previa_hw):
                return html
            fim_body = html.rfind("</body>")
            if fim_body == -1:
                return html
            config_hw = json.dumps(_halloween.config_tela(sessao_hw["usuario"] if sessao_hw else "", previa_hw),
                                   ensure_ascii=False).replace("</", "<\\/")
            bloco = '<script type="application/json" id="pda-halloween">' + config_hw + "</" + "script>" + _HALLOWEEN_HTML
            return html[:fim_body] + bloco + html[fim_body:]
        except Exception:
            logger.exception("Halloween: não foi possível pôr o tema na tela")
            return html

    def _redirecionar(self, destino: str, cookie: Optional[str] = None) -> None:
        self.send_response(303)
        self.send_header("Location", destino)
        if cookie is not None:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()

    # -- rede de segurança (2.35.7.0) ----------------------------------------
    # Antes, uma exceção dentro de uma rota derrubava a conexão sem resposta: o
    # navegador mostrava só "Failed to fetch" e o traceback ia pro stderr, que no
    # .exe não aparece em lugar nenhum. Agora a exceção vai pro log com o caminho
    # e quem estava logado, e a tela recebe um erro 500 legível.
    def send_response(self, code, message=None):
        self._resposta_iniciada = True
        super().send_response(code, message)

    def _tratar_falha_rota(self, metodo: str) -> None:
        sessao_falha = None
        try:
            sessao_falha = self._sessao(renovar=False)
        except Exception:
            pass
        logger.exception("Erro na rota %s %s (usuário: %s).", metodo, self.path,
                         (sessao_falha or {}).get("usuario", "sem sessão"))
        if getattr(self, "_resposta_iniciada", False):
            return  # a resposta já tinha começado: não dá pra trocar por um erro
        try:
            self._enviar_json({"ok": False, "erro": "Erro inesperado no servidor do PDA (detalhes no log). Tente de novo."}, status=500)
        except Exception:
            pass

    def do_GET(self) -> None:
        self._resposta_iniciada = False
        try:
            self._rotas_get()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass  # o navegador fechou a aba no meio: nada pra responder
        except Exception:
            self._tratar_falha_rota("GET")

    def do_POST(self) -> None:
        self._resposta_iniciada = False
        try:
            self._rotas_post()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass
        except Exception:
            self._tratar_falha_rota("POST")

    # -- GET --------------------------------------------------------------
    def _rotas_get(self) -> None:
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
            # passe de troca obrigatória (login com a senha padrão): usuário fixo, sem senha atual
            usuario_obrigatorio = usuario_da_troca_pendente(self._pegar_cookie("troca_senha"))
            self._enviar_html(_montar_alterar_senha_html(erro, usuario_obrigatorio))
            return

        if caminho == "/logo-pda.png":
            # logo da Empresa (3.3.4.0): pública porque aparece no login e na Central de Monitores; o ?v= da URL troca
            # junto com a imagem, então dá pra guardar por 30 dias
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Cache-Control", "public, max-age=2592000, immutable")
            self.send_header("Content-Length", str(len(_LOGO_BYTES)))
            self.end_headers()
            self.wfile.write(_LOGO_BYTES)
            return

        if caminho == "/logout":
            token = self._pegar_token()
            if token:
                SESSIONS.pop(token, None)
            self._redirecionar("/login", cookie="session=; Path=/; Max-Age=0")
            return

        if caminho == "/direcionamento-webmonitors":
            # Pedido do Igor em 16/09/2026: card acessível DIRETO, sem
            # precisar logar no PDA - por isso fica aqui em cima, antes da
            # checagem de sessão (igual /login, /logout etc.), e não lá
            # embaixo no meio das rotas autenticadas.
            self._enviar_html(_montar_direcionamento_webmonitors_html(self._sessao(renovar=False)))
            return

        # A consulta automática de status (a cada 2s, sozinha) NAO conta
        # como atividade real - só renova a sessão em ações de verdade
        # (abrir uma página, clicar em Executar, etc.)
        sessao = self._sessao(renovar=(caminho != "/api/status"))
        if not sessao:
            if caminho.startswith("/api/"):
                self._enviar_json({"ok": False, "erro": "não autenticado"}, status=401)
            elif self.path != "/" and _destino_seguro(self.path):
                # 3.3.6.0: guarda a página pedida (ex.: o link de votação do Teams) e volta pra ela depois do login
                self._redirecionar("/login", cookie="volta=" + urllib.parse.quote(self.path, safe="") + "; Path=/; HttpOnly; SameSite=Lax; Max-Age=600")
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
            # aberta pra todo mundo desde a 3.1.9.0: sem admin nem a permissão, a tela vem em modo leitura
            self._enviar_html(_montar_manutencao_alertas_html(sessao))

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

        elif caminho == "/feedbacks":
            if _tem_acesso_feedbacks(sessao):
                self._enviar_html(_montar_feedbacks_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Feedbacks e Alinhamentos"), status=200)

        elif caminho == "/api/dashboards-clientes":
            if not _tem_acesso_dashboards_clientes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            self._enviar_json({"ok": True, "clientes": _carregar_dashboards_clientes()})

        elif caminho == "/api/dashboards-clientes/cliente_b/nfag":
            if not _tem_acesso_dashboards_clientes(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            query_nfag = urllib.parse.parse_qs(parsed.query)
            data_inicio = query_nfag.get("data_inicio", [None])[0]
            data_fim = query_nfag.get("data_fim", [None])[0]
            resultado = _consultar_dashboard_cliente_b_nfag(data_inicio, data_fim)
            self._enviar_json(resultado)

        elif caminho == "/api/feedbacks/listar":
            if not _tem_acesso_feedbacks(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Feedbacks e Alinhamentos"}, status=403)
                return
            query_fb = urllib.parse.parse_qs(parsed.query)
            filtro_usuario = query_fb.get("usuario", [None])[0]
            filtro_tipo = query_fb.get("tipo", [None])[0]
            filtro_busca = (query_fb.get("busca", [None])[0] or "").strip().lower()
            filtro_equipe = query_fb.get("equipe", [None])[0]

            with _lock_feedbacks_usuarios:
                # cada equipe só vê os registros dela (2.35.2.0)
                registros = [dict(f) for f in FEEDBACKS_USUARIOS if _pode_ver_registro_fb(f, sessao["usuario"])]

            for r in registros:
                r["descricao_alvo"] = _descricao_alvo_feedback(r)
                # registro antigo: um autor só (quem registrou) e equipe padrão
                r["autores"] = _autores_do_registro_fb(r)
                r["equipe"] = _equipe_do_registro_fb(r)

            if filtro_usuario:
                registros = [
                    r for r in registros
                    if r.get("usuario") == filtro_usuario or filtro_usuario in (r.get("usuarios") or [])
                ]
            if filtro_tipo:
                registros = [r for r in registros if r.get("tipo") == filtro_tipo]
            if filtro_equipe:
                registros = [r for r in registros if r["equipe"] == filtro_equipe]
            if filtro_busca:
                registros = [
                    r for r in registros
                    if filtro_busca in r.get("descricao_alvo", "").lower()
                    or filtro_busca in (r.get("texto") or "").lower()
                    or filtro_busca in (r.get("autor_nome") or "").lower()
                ]

            registros.sort(key=lambda r: r.get("criado_em", ""), reverse=True)
            self._enviar_json({"ok": True, "registros": registros,
                               "equipes_visiveis": _equipes_visiveis_fb(sessao["usuario"]),
                               "ve_todas_equipes": _ve_todas_equipes_fb(sessao["usuario"])})

        elif caminho == "/sobre":
            # sem restrição de admin/permissão especial - qualquer pessoa
            # logada pode ver do que se trata o painel
            self._enviar_html(_montar_sobre_html(sessao))

        elif caminho == "/changelog":
            # igual ao /sobre: qualquer pessoa logada vê o que mudou em cada versão
            self._enviar_html(_montar_changelog_html(sessao))

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
            # Sem restrição de admin (15/09/2026, pedido do Igor: "todos
            # podem ter acesso também"); ?embutido=1 é a aba do Indicadores Mensais (3.1.6.0)
            embutido_imx = urllib.parse.parse_qs(parsed.query).get("embutido", [""])[0] == "1"
            self._enviar_html(_montar_indicadores_movidesk_html(sessao, embutido_imx))

        elif caminho == "/horas-trabalhadas":
            # Sem restrição de admin (15/09/2026, pedido do Igor: "todo
            # usuário deve ter acesso ao card Horas Trabalhadas também")
            self._enviar_html(_montar_horas_trabalhadas_html(sessao))

        elif caminho == "/automacao-movidesk":
            if sessao["admin"]:
                self._enviar_html(_montar_automacao_movidesk_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Automação Movidesk"), status=200)

        elif caminho == "/reprocessamento-cte2":
            # 3.3.1.0: a página abre pra todo mundo acompanhar; as ações (POST) continuam só pra administrador
            self._enviar_html(_montar_reprocessamento_cte2_html(sessao))

        elif caminho in ("/api/reprocessamento-cte2/status", "/api/reprocessamento-cte2/registros"):
            query_rc = urllib.parse.parse_qs(parsed.query)
            if caminho.endswith("/status"):
                self._enviar_json(_status_rc(com_controle=query_rc.get("controle", [""])[0] == "1"))
            else:
                resultado_rc = _ler_registros_rc(query_rc.get("tipo", [""])[0], query_rc.get("dia", [""])[0] or None)
                self._enviar_json(resultado_rc, status=200 if resultado_rc.get("ok") else 400)

        elif caminho == "/indicadores-mensais":
            if _tem_acesso_indicadores_mensais(sessao):
                self._enviar_html(_montar_indicadores_mensais_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Indicadores Mensais"), status=200)

        elif caminho in ("/api/indicadores-mensais/efetividade", "/api/indicadores-mensais/noc",
                         "/api/indicadores-mensais/satisfacao"):
            if not _tem_acesso_indicadores_mensais(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            mes = (urllib.parse.parse_qs(parsed.query).get("mes") or [""])[0]
            listar = {"efetividade": _listar_efetividade_imx, "noc": _listar_noc_imx,
                      "satisfacao": _listar_satisfacao_imx}[caminho.rsplit("/", 1)[1]]
            resultado = listar(mes)
            # 503 = banco não respondeu (o validar.py aceita: a cópia de teste não tem credenciais)
            self._enviar_json(resultado, status=200 if resultado["ok"] else 503)

        elif caminho == "/dash-financeiro":
            if _tem_acesso_dash_financeiro(sessao):
                self._enviar_html(_montar_dash_financeiro_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Atualização Dash Financeiro"), status=200)

        elif caminho == "/emailpack":
            self._enviar_html(_montar_emailpack_html(sessao))

        elif caminho == "/ferias":
            self._enviar_html(_montar_ferias_html(sessao))

        elif caminho in ("/consumo-indevido", "/api/consumo-indevido/status"):
            # Monitoramento de Consumo Indevido (beta, 3.4.3.0): só administrador (mexe com banco e manda pro Teams)
            if not sessao.get("admin"):
                if caminho.startswith("/api/"):
                    self._enviar_json({"ok": False, "erro": "só administradores"}, status=403)
                else:
                    self._enviar_html(_montar_usuarios_negado_html(sessao, "Consumo Indevido"), status=200)
                return
            if caminho.startswith("/api/"):
                self._enviar_json(_status_ci())
            else:
                self._enviar_html(_montar_consumo_indevido_html(sessao))

        elif caminho in ("/api/nnu-status/status", "/api/nnu-status/lote") or caminho.startswith("/nnu-status/relatorio/"):
            # NNU · status 20 → 15 (beta, 3.4.9.0, aba do NNU Enchanced): ver = permissão do NNU Enchanced; mexer
            # é nas rotas POST, só administrador
            if not _tem_acesso_nnu_status(sessao):
                if caminho.startswith("/api/"):
                    self._enviar_json({"ok": False, "erro": "sem acesso"}, status=403)
                else:
                    self._enviar_html(_montar_usuarios_negado_html(sessao, "NNU Enchanced"), status=200)
                return
            if caminho == "/api/nnu-status/status":
                self._enviar_json(_status_nnu_status())
            elif caminho == "/api/nnu-status/lote":
                resultado_ns = _detalhe_lote_nnu_status(urllib.parse.parse_qs(parsed.query).get("id", [""])[0])
                self._enviar_json(resultado_ns, status=200 if resultado_ns.get("ok") else 404)
            else:
                id_ns = caminho[len("/nnu-status/relatorio/"):]
                arquivo_ns = _relatorio_nnu_status(id_ns[:-5]) if id_ns.endswith(".xlsx") else None
                if not arquivo_ns:
                    self.send_response(404)
                    self.end_headers()
                    return
                with open(arquivo_ns, "rb") as f:
                    conteudo_ns = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                self.send_header("Content-Disposition", f'attachment; filename="NNU_20_15_{os.path.basename(arquivo_ns)}"')
                self.send_header("Content-Length", str(len(conteudo_ns)))
                self.end_headers()
                self.wfile.write(conteudo_ns)

        elif caminho == "/loja":
            # Loja de Palminhas (3.3.7.0): pra todo mundo logado
            self._enviar_html(_montar_loja_html(sessao))

        elif caminho == "/api/loja":
            self._enviar_json(_visao_loja(sessao["usuario"]))

        elif caminho == "/longnamejanitor":
            # LongNameJanitor ClienteQ (beta, 3.3.2.0): todo mundo acompanha; controlar é só admin (POSTs)
            self._enviar_html(_montar_longnamejanitor_html(sessao))

        elif caminho == "/api/longnamejanitor/status":
            self._enviar_json(_status_lnj())

        elif caminho == "/api/longnamejanitor/historico":
            resultado_lnj = _ler_historico_lnj(urllib.parse.parse_qs(parsed.query).get("dia", [""])[0] or None)
            self._enviar_json(resultado_lnj, status=200 if resultado_lnj.get("ok") else 400)

        elif caminho == "/calendario-gmud":
            # Calendário de GMUD's (3.3.1.0, em construção): só com a permissão Serviços ADM
            if _tem_acesso_servicos_adm(sessao):
                self._enviar_html(_montar_gmud_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Calendário de GMUD's"), status=200)

        elif caminho == "/api/gmud":
            if not _tem_acesso_servicos_adm(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão (Serviços ADM)"}, status=403)
                return
            # 3.3.4.0: vem da tabela gmud do banco do Movidesk (ownerTeam = 'SERVIÇOS'); 503 se o banco não responder
            resultado_gmud = _listar_gmuds()
            self._enviar_json(resultado_gmud, status=200 if resultado_gmud.get("ok") else 503)

        elif caminho == "/fluxograma-pda":
            # Fluxograma do PDA (beta, 3.3.1.0): só administrador
            if sessao.get("admin"):
                self._enviar_html(_montar_fluxograma_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Fluxograma do PDA"), status=200)

        elif caminho.startswith("/historico-print/"):
            # prints de cada era no changelog (3.3.1.0), embutidos em telas/historico_prints.py
            era_print = caminho[len("/historico-print/"):].removesuffix(".jpg")
            conteudo_print = _print_historico(era_print)
            if conteudo_print is None:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(conteudo_print)))
            self.send_header("Cache-Control", "private, max-age=86400")
            self.end_headers()
            self.wfile.write(conteudo_print)

        elif caminho == "/nnu-enchanced":
            # NNU Enchanced (beta, 3.2.1.0): tratativa guiada e as automações de NNU. Desde a 3.5.1.0 abre pra todo
            # mundo logado; os controles das automações só aparecem e só funcionam pra administrador
            if _tem_acesso_nnu_enchanced(sessao):
                self._enviar_html(_montar_nnu_enchanced_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "NNU Enchanced"), status=200)

        elif caminho == "/ranks-produtos":
            self._enviar_html(_montar_ranks_produtos_html(sessao))

        elif caminho == "/api/ranks-produtos":
            self._enviar_json(_visao_ranks(sessao["usuario"], bool(sessao.get("admin"))))

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
            if _tem_acesso_logs(sessao):
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

        elif caminho == "/relatorios-cliente_a":
            if _tem_acesso_relatorios_cliente_a(sessao):
                self._enviar_html(_montar_relatorios_cliente_a_html(sessao))
            else:
                self._enviar_html(_montar_usuarios_negado_html(sessao, "Relatórios ClienteA"), status=200)

        elif caminho.startswith("/api/relatorios-cliente_a/"):
            if not _tem_acesso_relatorios_cliente_a(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return

            if caminho == "/api/relatorios-cliente_a/status":
                with _lock_relatorio_cliente_a_auto:
                    self._enviar_json(dict(estado_relatorio_cliente_a_automatico))
                return

            if caminho == "/api/relatorios-cliente_a/log":
                caminho_log = os.path.join(_base_path_app(), "logs", "relatorios_cliente_a.log")
                if not os.path.exists(caminho_log):
                    self._enviar_json({"ok": True, "linhas": [], "aviso": "Ainda não há nada registrado."})
                    return
                try:
                    ultimas = _ler_ultimas_linhas_arquivo(caminho_log, n_linhas=1000)
                    self._enviar_json({"ok": True, "linhas": ultimas})
                except Exception as e:
                    self._enviar_json({"ok": False, "erro": f"Não foi possível ler o log: {e}"}, status=500)
                return

            if caminho == "/api/relatorios-cliente_a/existe":
                data_str = urllib.parse.parse_qs(parsed.query).get("data", [None])[0]
                try:
                    data = datetime.strptime(data_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    self._enviar_json({"ok": False, "erro": "Data inválida."}, status=400)
                    return
                data_arquivo = data.strftime("%d-%m-%Y")
                nome_notas = f"{data_arquivo}.xlsx"
                nome_canceladas = f"Canceladas_{data_arquivo}.xlsx"
                pasta = _pasta_saida_relatorios_cliente_a(data)
                existe_notas = os.path.isfile(os.path.join(pasta, nome_notas))
                existe_canceladas = os.path.isfile(os.path.join(pasta, nome_canceladas))
                self._enviar_json({
                    "ok": True,
                    "existe": existe_notas and existe_canceladas,
                    "arquivo_notas": nome_notas if existe_notas else None,
                    "arquivo_canceladas": nome_canceladas if existe_canceladas else None,
                })
                return

            if caminho.startswith("/api/relatorios-cliente_a/download-zip/"):
                # baixa os 2 arquivos (Notas + Canceladas) de uma data como um
                # zip só, nomeado com a própria data (ex.: 09-08-2026.zip) - o
                # zip é montado na hora, em memória, não fica salvo em disco
                data_str = urllib.parse.unquote(caminho[len("/api/relatorios-cliente_a/download-zip/"):])
                if not re.fullmatch(r"\d{2}-\d{2}-\d{4}", data_str):
                    self.send_response(400)
                    self.end_headers()
                    return
                pasta = _localizar_pasta_relatorio_cliente_a_por_data_str(data_str)
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

            if caminho.startswith("/api/relatorios-cliente_a/download/"):
                nome_arquivo = urllib.parse.unquote(caminho[len("/api/relatorios-cliente_a/download/"):])
                # trava contra path traversal - só permite exatamente o padrão
                # de nome que a gente mesmo gera, nunca um caminho arbitrário
                if not re.fullmatch(r"(Canceladas_)?\d{2}-\d{2}-\d{4}\.xlsx", nome_arquivo):
                    self.send_response(400)
                    self.end_headers()
                    return
                # a data sempre está no final do nome (com ou sem o prefixo
                # "Canceladas_"), usada pra reconstruir a pasta Mês/Dia certa
                data_do_nome = nome_arquivo.replace("Canceladas_", "").replace(".xlsx", "")
                pasta = _localizar_pasta_relatorio_cliente_a_por_data_str(data_do_nome)
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
                    "pode_relatorios_cliente_a": bool(info.get("pode_relatorios_cliente_a")),
                    "pode_dash_financeiro": bool(info.get("pode_dash_financeiro")),
                    "pode_manutencao_rejeicoes": bool(info.get("pode_manutencao_rejeicoes")),
                    "pode_dados_sensiveis": bool(info.get("pode_dados_sensiveis")),
                    "pode_manutencao_relatorios": bool(info.get("pode_manutencao_relatorios")),
                    "pode_manutencao_usuarios": bool(info.get("pode_manutencao_usuarios")),
                    # faltavam até a 2.33.6.0: a Manutenção de Usuários abria essas duas
                    # sempre desmarcadas e o "Salvar permissões" apagava a permissão
                    "pode_feedbacks": bool(info.get("pode_feedbacks")),
                    "pode_ver_logs": bool(info.get("pode_ver_logs")),
                    "pode_indicadores_mensais": bool(info.get("pode_indicadores_mensais")),
                    "pode_reprocessamento_cte2": bool(info.get("pode_reprocessamento_cte2")),
                    "pode_nnu_enchanced": bool(info.get("pode_nnu_enchanced")),
                    "pode_editar_central": bool(info.get("pode_editar_central")),
                    "pode_publicar_comunidade": bool(info.get("pode_publicar_comunidade")),
                    "pode_servicos_adm": bool(info.get("pode_servicos_adm")),
                    "cargo": info.get("cargo") or "",
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

        elif caminho == "/anuncio/mario.gif":
            # GIF do anúncio da foto em GIF (3.2.0.0), embutido em telas/anuncios.py pra ir dentro do .exe
            conteudo_gif = _gif_mario_anuncio()
            self.send_response(200)
            self.send_header("Content-Type", "image/gif")
            self.send_header("Content-Length", str(len(conteudo_gif)))
            self.send_header("Cache-Control", "private, max-age=86400")
            self.end_headers()
            self.wfile.write(conteudo_gif)

        elif caminho.startswith("/foto-usuario/"):
            usuario_foto = urllib.parse.unquote(caminho[len("/foto-usuario/"):])
            caminho_foto = _caminho_foto_usuario(usuario_foto)
            if not caminho_foto:
                self.send_response(404)
                self.end_headers()
                return
            extensao = os.path.splitext(caminho_foto)[1].lower()
            tipo_mime = next((m for m, e in _EXTENSOES_FOTO_PERMITIDAS.items() if e == extensao), "application/octet-stream")
            # 3.2.3.0: antes o navegador guardava a foto por 5 min (max-age=300) e, depois de trocar (ex.: por um
            # GIF), a navbar e a foto ampliada continuavam com a antiga. Agora revalida sempre: a ETag muda quando
            # o arquivo muda, e foto igual responde 304 sem mandar a imagem de novo.
            info_foto = os.stat(caminho_foto)
            etag_foto = f'"{int(info_foto.st_mtime)}-{info_foto.st_size}-{extensao.lstrip(".")}"'
            if self.headers.get("If-None-Match") == etag_foto:
                self.send_response(304)
                self.send_header("ETag", etag_foto)
                self.send_header("Cache-Control", "private, no-cache")
                self.end_headers()
                return
            with open(caminho_foto, "rb") as f:
                conteudo_foto = f.read()
            self.send_response(200)
            self.send_header("Content-Type", tipo_mime)
            self.send_header("Content-Length", str(len(conteudo_foto)))
            self.send_header("ETag", etag_foto)
            self.send_header("Cache-Control", "private, no-cache")
            self.end_headers()
            self.wfile.write(conteudo_foto)

        elif caminho.startswith("/mural-comentario-imagem/"):
            # foto/GIF de um comentário (3.3.1.0): só quem vê o evento no mural agora
            id_com_img = caminho[len("/mural-comentario-imagem/"):]
            info_img = _imagem_comentario_mural(id_com_img, sessao["usuario"]) if re.fullmatch(r"[0-9a-f]{6,32}", id_com_img) else None
            if info_img is None:
                self.send_response(404)
                self.end_headers()
                return
            with open(info_img["caminho"], "rb") as f:
                conteudo_img = f.read()
            self.send_response(200)
            self.send_header("Content-Type", info_img["tipo"])
            self.send_header("Content-Length", str(len(conteudo_img)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "private, max-age=86400")
            self.end_headers()
            self.wfile.write(conteudo_img)

        elif caminho.startswith("/mural-arquivo/"):
            # foto/GIF ou arquivo de uma publicação da Comunidade (3.2.6.0): qualquer pessoa logada (o feed é de todos)
            partes_arquivo = caminho[len("/mural-arquivo/"):].split("/")
            info_arquivo = None
            if len(partes_arquivo) == 2 and partes_arquivo[1].isdigit() and re.fullmatch(r"[0-9a-f]{6,32}", partes_arquivo[0]):
                info_arquivo = _arquivo_post_mural(partes_arquivo[0], int(partes_arquivo[1]), sessao["usuario"])
            if info_arquivo is None:
                self.send_response(404)
                self.end_headers()
                return
            nome_arquivo_http = urllib.parse.quote(info_arquivo["nome"])
            if info_arquivo.get("video"):
                # vídeo (3.4.2.0): toca no feed; responde por pedaços (Range) pra barra de avançar funcionar sem baixar tudo
                tamanho_video = os.path.getsize(info_arquivo["caminho"])
                inicio_v, fim_v = 0, tamanho_video - 1
                faixa = re.fullmatch(r"bytes=(\d*)-(\d*)", (self.headers.get("Range") or "").strip())
                if faixa and (faixa.group(1) or faixa.group(2)):
                    if faixa.group(1):
                        inicio_v = int(faixa.group(1))
                        fim_v = min(int(faixa.group(2)), tamanho_video - 1) if faixa.group(2) else tamanho_video - 1
                    else:  # "bytes=-500" = os últimos 500
                        inicio_v = max(tamanho_video - int(faixa.group(2)), 0)
                    if inicio_v > fim_v or inicio_v >= tamanho_video:
                        self.send_response(416)
                        self.send_header("Content-Range", f"bytes */{tamanho_video}")
                        self.end_headers()
                        return
                    fim_v = min(fim_v, inicio_v + 8 * 1024 * 1024 - 1)  # pedaço de até 8 MB por vez
                with open(info_arquivo["caminho"], "rb") as f:
                    f.seek(inicio_v)
                    pedaco = f.read(fim_v - inicio_v + 1)
                self.send_response(206 if faixa and (faixa.group(1) or faixa.group(2)) else 200)
                self.send_header("Content-Type", info_arquivo["tipo"])
                self.send_header("Accept-Ranges", "bytes")
                if faixa and (faixa.group(1) or faixa.group(2)):
                    self.send_header("Content-Range", f"bytes {inicio_v}-{inicio_v + len(pedaco) - 1}/{tamanho_video}")
                self.send_header("Content-Length", str(len(pedaco)))
                self.send_header("Content-Disposition", f"inline; filename*=UTF-8''{nome_arquivo_http}")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "private, max-age=86400")
                self.end_headers()
                self.wfile.write(pedaco)
                return
            with open(info_arquivo["caminho"], "rb") as f:
                conteudo_arquivo = f.read()
            self.send_response(200)
            # imagem aparece no feed; o resto sempre baixa (nunca abre como página, ex.: um .html anexado)
            self.send_header("Content-Type", info_arquivo["tipo"] if info_arquivo["imagem"] else "application/octet-stream")
            self.send_header("Content-Length", str(len(conteudo_arquivo)))
            self.send_header("Content-Disposition", ("inline" if info_arquivo["imagem"] else "attachment")
                             + f"; filename*=UTF-8''{nome_arquivo_http}")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "private, max-age=86400")  # arquivo do post nunca muda (apagar tira o post)
            self.end_headers()
            self.wfile.write(conteudo_arquivo)

        elif caminho.startswith("/feedback-anexo/"):
            # Anexo é tão privado quanto o feedback em si - mesma
            # permissão (_tem_acesso_feedbacks), nunca público como as
            # fotos de perfil.
            if not _tem_acesso_feedbacks(sessao):
                self.send_response(403)
                self.end_headers()
                return
            try:
                id_feedback_anexo = int(urllib.parse.unquote(caminho[len("/feedback-anexo/"):]))
            except ValueError:
                self.send_response(400)
                self.end_headers()
                return
            with _lock_feedbacks_usuarios:
                registro_anexo = next((f for f in FEEDBACKS_USUARIOS if f["id"] == id_feedback_anexo), None)
                if registro_anexo and not _pode_ver_registro_fb(registro_anexo, sessao["usuario"]):
                    registro_anexo = None  # de outra equipe: responde como se não existisse
                nome_salvo_anexo = registro_anexo.get("anexo") if registro_anexo else None
                nome_original_anexo = registro_anexo.get("anexo_nome_original") if registro_anexo else None
            if not nome_salvo_anexo:
                self.send_response(404)
                self.end_headers()
                return
            caminho_anexo = os.path.join(_pasta_anexos_feedbacks(), nome_salvo_anexo)
            if not os.path.exists(caminho_anexo):
                self.send_response(404)
                self.end_headers()
                return
            tipo_mime_anexo, _ = mimetypes.guess_type(nome_original_anexo or nome_salvo_anexo)
            with open(caminho_anexo, "rb") as f:
                conteudo_anexo = f.read()
            self.send_response(200)
            self.send_header("Content-Type", tipo_mime_anexo or "application/octet-stream")
            self.send_header("Content-Length", str(len(conteudo_anexo)))
            self.send_header("Content-Disposition", f'attachment; filename="{nome_original_anexo or nome_salvo_anexo}"')
            self.send_header("Cache-Control", "private, no-store")
            self.end_headers()
            self.wfile.write(conteudo_anexo)

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

        elif caminho == "/api/mural":
            # linha do tempo do início (aniversários, promoções, insígnias, chegadas) e os números rápidos
            dados_mural = _dados_mural(sessao["usuario"])
            if sessao.get("admin"):
                dados_mural["equipe"] = _numeros_equipe_mural()
            self._enviar_json(dados_mural)

        elif caminho == "/comunicado/v3/previa":
            # prévia do e-mail da v3 (as fotos, que no e-mail vão por CID, aqui vêm da rota de fotos)
            if not _e_fundador(sessao):
                self._enviar_json({"ok": False, "erro": "só o Igor e a Debora"}, status=403)
                return
            self._enviar_html(_html_email_v3(sessao.get("nome") or sessao["usuario"])
                              .replace("cid:foto_igor", "/foto-usuario/igor").replace("cid:foto_debora", "/foto-usuario/debora"))

        elif caminho == "/api/comunicado/v3":
            if not _e_fundador(sessao):
                self._enviar_json({"ok": False, "erro": "só o Igor e a Debora"}, status=403)
                return
            self._enviar_json(_status_comunicado_v3())

        elif caminho == "/api/notificacoes":
            # sininho da navbar: palminhas, comentários e a versão nova do PDA
            self._enviar_json(_listar_notificacoes(sessao["usuario"], VERSAO_PDA))

        elif caminho == "/api/mural/equipe":
            # Gestão de equipe filtrada por Suporte ou Monitoramento (vazio = as duas), só administrador
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            equipe_gestao = (urllib.parse.parse_qs(parsed.query).get("equipe") or [""])[0]
            if equipe_gestao and equipe_gestao not in _EQUIPES_GESTAO_MURAL:
                self._enviar_json({"ok": False, "erro": "equipe inválida"}, status=400)
                return
            movidesk_gestao = _numeros_movidesk_equipe_mural(equipe_gestao)
            self._enviar_json({"ok": True, "equipe_filtro": equipe_gestao, "geral": _numeros_equipe_mural(equipe=equipe_gestao),
                               "movidesk": movidesk_gestao})

        elif caminho == "/api/mural/movidesk":
            # horas e tickets do mês (banco do Movidesk): à parte pra não segurar o mural
            numeros = _numeros_movidesk_mural(sessao["usuario"], bool(sessao.get("admin")))
            self._enviar_json(numeros, status=200 if numeros.get("ok") else 503)

        elif caminho == "/api/insignias/campanha":
            # convite da Beta User e insígnias novas pra comemorar, de quem está logado
            self._enviar_json(_campanha_insignias(sessao["usuario"]))

        elif caminho.startswith("/api/perfil/"):
            usuario_perfil = urllib.parse.unquote(caminho[len("/api/perfil/"):])
            dados_perfil = _montar_dados_perfil(usuario_perfil)
            if dados_perfil is None:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            eh_proprio_perfil = sessao["usuario"] == usuario_perfil
            # admin consegue ver o perfil completo de qualquer pessoa (pedido
            # do Igor) - quem não é admin só vê o perfil completo do
            # próprio, e de mais ninguém
            pode_ver_completo = eh_proprio_perfil or sessao["admin"]

            # Feedback SAIU do perfil (13/09/2026) - agora vive na tela
            # dedicada /feedbacks (card próprio, permissão própria). Aqui
            # só manda um booleano pra decidir se mostra o link "Ver
            # feedbacks desta pessoa" - a própria pessoa NUNCA vê, mesmo
            # sendo admin do próprio perfil.
            pode_ver_feedback = _tem_acesso_feedbacks(sessao) and not eh_proprio_perfil

            # insígnias (2.35.5.0): as conquistadas são públicas; quem pode editar o perfil
            # (a própria pessoa ou admin) também vê as que faltam e o que falta pra elas
            insignias_perfil = _insignias_de(usuario_perfil, com_bloqueadas=pode_ver_completo)
            if pode_ver_completo:
                self._enviar_json({
                    "ok": True, "proprio_perfil": eh_proprio_perfil, "pode_ver_completo": True,
                    "sessao_admin": sessao["admin"],
                    "wallpaper": _wallpaper_de(usuario_perfil),  # capa do perfil (Loja de Palminhas, 3.3.7.0)
                    "pode_ver_feedback": pode_ver_feedback,
                    # data de início e histórico na empresa: a própria pessoa também edita (2.35.5.0)
                    "pode_editar_perfil": True,
                    "data_inicio": (USUARIOS_WEB.get(usuario_perfil) or {}).get("data_inicio") or "",
                    "aniversario": (USUARIOS_WEB.get(usuario_perfil) or {}).get("aniversario") or "",
                    "insignias": insignias_perfil,
                    "insignia_destaque": _insignia_destaque_de(usuario_perfil, insignias_perfil),
                    # conceder Bug Hunter / PDA Contributor: só o Igor e a Debora (3.0.5.0)
                    "pode_conceder": _e_fundador(sessao),
                    "concessoes": _concessoes_insignias(usuario_perfil) if _e_fundador(sessao) else [],
                    **dados_perfil,
                })
            else:
                # perfil público (3.0.4.0): quem não é a própria pessoa nem admin vê o básico
                # (cargo, equipe, entrada na empresa, aniversário), as insígnias e o histórico
                # na empresa - nada de horas, tickets, férias ou feedbacks
                info_publica = USUARIOS_WEB.get(usuario_perfil) or {}
                self._enviar_json({
                    "ok": True, "proprio_perfil": False, "pode_ver_completo": False,
                    "sessao_admin": sessao["admin"],
                    "wallpaper": _wallpaper_de(usuario_perfil),  # todo mundo vê o wallpaper dos outros (3.3.7.0)
                    "pode_ver_feedback": False,
                    "usuario": dados_perfil["usuario"], "nome": dados_perfil["nome"],
                    "tem_foto": dados_perfil["tem_foto"],
                    "cargo": dados_perfil.get("cargo") or info_publica.get("cargo") or "",
                    "atribuicao": dados_perfil.get("atribuicao") or "",
                    "data_inicio": info_publica.get("data_inicio") or "",
                    "aniversario": info_publica.get("aniversario") or "",
                    "ativo": info_publica.get("ativo", True),  # desativado aparece em vermelho pra todo mundo (3.1.5.0)
                    "historico_carreira": dados_perfil.get("historico_carreira") or [],
                    "insignias": insignias_perfil,
                    "insignia_destaque": _insignia_destaque_de(usuario_perfil, insignias_perfil),
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
            try:
                mes_escolhido = validar_mes_dash_financeiro(urllib.parse.parse_qs(parsed.query).get("mes", [""])[0])
            except ValueError as e:
                self._enviar_json({"ok": False, "erro": str(e)}, status=400)
                return
            periodo_ref = _periodo_mes_anterior(mes_escolhido)
            progresso_df = _progresso_dash_financeiro()
            with _lock_dash_financeiro:
                produtos_rodando = set(_produtos_em_execucao)
                status_sessao = dict(estado_dash_financeiro)
            status_combinado = {}
            for produto in ORDEM_PRODUTOS_DASH_FINANCEIRO:
                # o que roda agora e a última geração desta sessão só valem pro mês delas
                sessao_produto = status_sessao.get(produto)
                if produto in produtos_rodando and progresso_df.get("mes") == periodo_ref["arquivo"]:
                    status_combinado[produto] = {"rodando": True}
                elif sessao_produto is not None and sessao_produto.get("mes", _periodo_mes_anterior()["arquivo"]) == periodo_ref["arquivo"]:
                    status_combinado[produto] = sessao_produto
                else:
                    # essa sessão ainda não mexeu nesse produto (por
                    # exemplo, o programa acabou de reiniciar) - cai pro
                    # que já está salvo em disco, em vez de mostrar
                    # "nunca rodou" pra algo que na verdade já rodou
                    status_combinado[produto] = _status_disco_produto(produto, mes_escolhido)
            # o que entra em cada produto + o que já tem salvo em disco, pro card mostrar
            try:
                conexoes_json = _carregar_conexoes_dash_financeiro()
            except Exception:
                conexoes_json = {}
            detalhes = {
                produto: {
                    "clientes": _clientes_dash_financeiro(produto, conexoes_json),
                    "meses": _meses_gerados_dash_financeiro(produto),
                    "consolidado_antigo": os.path.isfile(
                        os.path.join(_caminho_saida_produto(produto), NOME_DF_CONSOLIDADO_ANTIGO)),
                    "arquivo_mes": _info_arquivo_mes_dash_financeiro(produto, mes_escolhido),
                }
                for produto in ORDEM_PRODUTOS_DASH_FINANCEIRO
            }
            self._enviar_json({
                "ok": True,
                "ordem": ORDEM_PRODUTOS_DASH_FINANCEIRO,
                "testaveis": PRODUTOS_TESTAVEIS_DASH_FINANCEIRO,
                "status": status_combinado,
                "detalhes": detalhes,
                "mes_referencia": periodo_ref["arquivo"],
                "periodo": {"ini": periodo_ref["ini"], "fim": periodo_ref["fim"]},
                "execucao_ativa": _dash_financeiro_execucao_ativa_agora(),
                "progresso": progresso_df,
                "mes_padrao": _periodo_mes_anterior()["arquivo"],
                "mes_mais_antigo": MES_MAIS_ANTIGO_DASH_FINANCEIRO,
                "agora": time.time(),
                "automatico": {"horario": HORARIO_DASH_FINANCEIRO_AUTOMATICO,
                               "proximo": _proxima_execucao_dash_financeiro()},
            })

        elif caminho == "/api/logs":
            if not _tem_acesso_logs(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra ver logs"}, status=403)
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
            # Sem restrição de admin (15/09/2026, pedido do Igor)
            query_im = urllib.parse.parse_qs(parsed.query)
            data_inicio = query_im.get("data_inicio", [None])[0]
            data_fim = query_im.get("data_fim", [None])[0]
            equipe_filtro_im = query_im.get("equipe", [None])[0] or None
            if not data_inicio:
                primeiro_dia_mes = datetime.now().replace(day=1).strftime("%Y-%m-%d")
                data_inicio = primeiro_dia_mes
            resultado = _consultar_indicadores_movidesk(data_inicio, data_fim, equipe_filtro=equipe_filtro_im)
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/indicadores-movidesk/exportar":
            # Excel do período da tela com todos os analistas (mesmo acesso da
            # tela: aberta pra todo mundo desde 15/09/2026). Sem data = mês atual.
            query_im = urllib.parse.parse_qs(parsed.query)
            conteudo, nome_arquivo, erro = _gerar_excel_indicadores(
                query_im.get("data_inicio", [None])[0] or None,
                query_im.get("data_fim", [None])[0] or None,
                query_im.get("equipe", [None])[0] or None,
            )
            if erro:
                self._enviar_json({"ok": False, "erro": erro}, status=400 if erro.startswith("Data") else 502)
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            self.send_header("Content-Disposition", f'attachment; filename="{nome_arquivo}"')
            self.send_header("Content-Length", str(len(conteudo)))
            self.end_headers()
            self.wfile.write(conteudo)

        elif caminho == "/api/indicadores-movidesk/horas":
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
            # Página deixou de ser admin-only (15/09/2026) - continua
            # exportando TODO MUNDO do período (não só quem está
            # exportando), então qualquer pessoa logada com acesso a essa
            # tela consegue ver as horas de qualquer outra. Avisar o Igor
            # se isso não for o esperado - é uma mudança de visibilidade
            # de dados, não só de tela.
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
            resultado = _listar_alertas_banco()
            if resultado.get("ok") and not _tem_acesso_manutencao_alertas(sessao):
                resultado["registros"] = _visao_leitura_lista_alertas(resultado["registros"])  # só os ativos
                resultado["somente_leitura"] = True
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho.startswith("/api/manutencao-alertas/"):
            id_texto = caminho[len("/api/manutencao-alertas/"):]
            try:
                id_alerta = int(id_texto)
            except ValueError:
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            resultado = _buscar_alerta_banco(id_alerta)
            if resultado.get("ok") and not _tem_acesso_manutencao_alertas(sessao):
                # só leitura (3.1.9.0): alerta inativo nem existe pra essa pessoa, e a conexão nunca vai
                registro_leitura = _visao_leitura_alerta(resultado["registro"])
                if registro_leitura is None:
                    self._enviar_json({"ok": False, "erro": "alerta não encontrado"}, status=404)
                    return
                resultado = {"ok": True, "registro": registro_leitura, "somente_leitura": True}
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
    def _rotas_post(self) -> None:
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
                if secrets.compare_digest(senha, MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL):
                    # senha padrão de cadastro: não abre sessão, manda trocar (2.34.7.3)
                    passe = criar_troca_senha_pendente(usuario)
                    logger_administracao.info("Login com a senha padrão: '%s' encaminhado pra troca obrigatória.", usuario)
                    self._redirecionar(
                        "/alterar-senha",
                        cookie=f"troca_senha={passe}; Path=/; HttpOnly; SameSite=Lax; Max-Age=600",
                    )
                    return
                token = _criar_sessao(
                    usuario, bool(info.get("admin")),
                    bool(info.get("pode_manutencao_alertas")), bool(info.get("pode_relatorios_cliente_a")),
                    bool(info.get("pode_dash_financeiro")), bool(info.get("pode_manutencao_rejeicoes")),
                    bool(info.get("pode_dados_sensiveis")), bool(info.get("pode_manutencao_relatorios")),
                    bool(info.get("pode_manutencao_usuarios")),
                    info.get("nome"), info.get("genero"),
                    pode_feedbacks=bool(info.get("pode_feedbacks")),
                    pode_ver_logs=bool(info.get("pode_ver_logs")),
                    pode_indicadores_mensais=bool(info.get("pode_indicadores_mensais")),
                    pode_reprocessamento_cte2=bool(info.get("pode_reprocessamento_cte2")),
                    pode_nnu_enchanced=bool(info.get("pode_nnu_enchanced")),
                    pode_editar_central=bool(info.get("pode_editar_central")),
                    pode_servicos_adm=bool(info.get("pode_servicos_adm")),
                )
                logger_administracao.info("Login web bem-sucedido: usuário '%s'", usuario)
                _registrar_login_acesso(usuario)
                volta = urllib.parse.unquote(self._pegar_cookie("volta") or "")
                if volta:  # 3.3.6.0: volta pra página que pediu login; o cookie da volta é apagado em seguida
                    self.send_response(303)
                    self.send_header("Location", volta if _destino_seguro(volta) else "/")
                    self.send_header("Set-Cookie", f"session={token}; Path=/; HttpOnly; SameSite=Lax")
                    self.send_header("Set-Cookie", "volta=; Path=/; Max-Age=0")
                    self.end_headers()
                    return
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

            passe = self._pegar_cookie("troca_senha")
            # troca obrigatória: o passe vale só pro usuário dele e já provou a senha atual no login
            troca_obrigatoria = bool(usuario) and usuario_da_troca_pendente(passe) == usuario

            if not usuario or not nova_senha or not confirma_senha or (not senha_atual and not troca_obrigatoria):
                self._redirecionar("/alterar-senha?erro=campos")
                return

            info = USUARIOS_WEB.get(usuario)
            senha_esperada = info.get("senha") if info else None
            if senha_esperada is None or (
                not troca_obrigatoria and not secrets.compare_digest(senha_esperada, senha_atual)
            ):
                logger_administracao.warning("Tentativa de autoalteração de senha falhou (credenciais) para '%s'", usuario)
                self._redirecionar("/alterar-senha?erro=credenciais")
                return

            if secrets.compare_digest(nova_senha, MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL):
                self._redirecionar("/alterar-senha?erro=padrao")
                return
            if secrets.compare_digest(nova_senha, senha_esperada):
                self._redirecionar("/alterar-senha?erro=igual")
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
            if troca_obrigatoria:
                consumir_troca_pendente(passe)
            logger_administracao.info(
                "Usuário '%s' alterou a própria senha (%s).", usuario,
                "troca obrigatória da senha padrão" if troca_obrigatoria else "autoatendimento",
            )
            self._redirecionar("/login?senha_alterada=1", cookie="troca_senha=; Path=/; Max-Age=0")
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
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

        elif caminho == "/api/usuarios/permissao-cliente_a":
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return

            USUARIOS_WEB[usuario]["pode_relatorios_cliente_a"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_relatorios_cliente_a"] = nova_permissao
            logger_administracao.info(
                "Permissão de Relatórios ClienteA do usuário '%s' alterada para %s por '%s'.",
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
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
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_manutencao_usuarios"] = nova_permissao
            logger_administracao.info(
                "Permissão de Manutenção de Usuários (Beta) do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-feedbacks":
            # Mesmo padrão de pode_manutencao_usuarios/pode_dados_sensiveis
            # - nunca automático pra admin, precisa ser concedida à parte.
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_feedbacks"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_feedbacks"] = nova_permissao
            logger_administracao.info(
                "Permissão de Feedbacks e Alinhamentos do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/insignias/participar":
            # "Quero participar" da campanha PDA Beta User: grava de uma vez o que a
            # pessoa preencheu (foto, entrada na empresa, aniversário, e-mail, cargo atual).
            # Este "global" vale pro do_POST inteiro (também pro /api/historico-carreira/criar, mais abaixo)
            global _proximo_id_historico_carreira
            usuario_part = sessao["usuario"]
            dados_part = self._ler_corpo_form()
            foto_part = dados_part.get("foto") or ""
            dados_part["tem_foto_nova"] = "true" if foto_part else ""
            campos_part, erro_part, campo_erro_part = _validar_participacao_insignias(usuario_part, dados_part)
            if erro_part:
                self._enviar_json({"ok": False, "erro": erro_part, "campo": campo_erro_part}, status=400)
                return
            if foto_part:
                erro_foto = _salvar_foto_usuario(usuario_part, foto_part)
                if erro_foto:
                    self._enviar_json({"ok": False, "erro": erro_foto, "campo": "foto"}, status=400)
                    return
            info_part = USUARIOS_WEB[usuario_part]
            info_part["data_inicio"] = campos_part["data_inicio"]
            info_part["aniversario"] = campos_part["aniversario"]
            info_part["email"] = campos_part["email"]
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar (detalhes no log)"}, status=500)
                return
            if "historico" in campos_part:
                with _lock_historico_carreira:
                    HISTORICO_CARREIRA.append({
                        "id": _proximo_id_historico_carreira, "usuario": usuario_part, **campos_part["historico"], "fim": None,
                        "criado_por": usuario_part, "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    })
                    _proximo_id_historico_carreira += 1
                    _salvar_historico_carreira(HISTORICO_CARREIRA)
            logger_administracao.info("Campanha PDA Beta User: '%s' completou o perfil.", usuario_part)
            self._enviar_json(_campanha_insignias(usuario_part))

        elif caminho in ("/api/ranks-produtos/nivel", "/api/ranks-produtos/produto"):
            # Ranks por Produtos (Beta): administradores definem os ranks (os próprios e os de todo mundo)
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "só administradores mexem nos ranks"}, status=403)
                return
            dados_rank = self._ler_corpo_form()
            if caminho.endswith("/nivel"):
                resultado_rank = _definir_nivel_rank((dados_rank.get("usuario") or "").strip(), (dados_rank.get("produto") or "").strip(),
                                                     (dados_rank.get("nivel") or "").strip(), sessao["usuario"])
            else:
                resultado_rank = _mexer_produto_rank((dados_rank.get("acao") or "").strip(), (dados_rank.get("id") or "").strip(),
                                                     dados_rank.get("nome") or "")
            if resultado_rank.get("ok"):
                logger_administracao.info("Rankings (%s) por '%s': %s", caminho.rsplit("/", 1)[-1], sessao["usuario"],
                                          {k: v for k, v in dados_rank.items() if k in ("usuario", "produto", "nivel", "acao", "id", "nome")})
                if resultado_rank.get("texto_log"):
                    logger_rankings.info("%s %s.", sessao.get("nome") or sessao["usuario"], resultado_rank["texto_log"])
                elif not caminho.endswith("/nivel"):
                    acao_rank = (dados_rank.get("acao") or "").strip()
                    logger_rankings.info("%s %s o produto %s.", sessao.get("nome") or sessao["usuario"],
                                         {"criar": "criou", "renomear": "renomeou", "remover": "removeu"}.get(acao_rank, acao_rank),
                                         (dados_rank.get("nome") or dados_rank.get("id") or "").strip())
            self._enviar_json(resultado_rank, status=200 if resultado_rank.get("ok") else 400)

        elif caminho == "/api/insignias/conceder":
            # Bug Hunter e PDA Contributor concedidas à mão no perfil: só o Igor e a Debora
            if not _e_fundador(sessao):
                self._enviar_json({"ok": False, "erro": "só o Igor e a Debora concedem insígnias"}, status=403)
                return
            dados_conc = self._ler_corpo_form()
            alvo_conc = (dados_conc.get("usuario") or "").strip()
            resultado_conc = _conceder_insignia(alvo_conc, (dados_conc.get("id") or "").strip(), dados_conc.get("dar") == "true", sessao["usuario"])
            if resultado_conc.get("ok"):
                logger_administracao.info("Insígnia '%s' %s pra '%s' por '%s'.", dados_conc.get("id"),
                                          "concedida" if dados_conc.get("dar") == "true" else "retirada", alvo_conc, sessao["usuario"])
            self._enviar_json(resultado_conc, status=200 if resultado_conc.get("ok") else 400)

        elif caminho == "/api/insignias/destaque":
            # insígnia que aparece junto da foto (só as que a pessoa já conquistou; vazio tira o destaque)
            self._enviar_json(_definir_insignia_destaque(sessao["usuario"], (self._ler_corpo_form().get("id") or "").strip()))

        elif caminho == "/api/insignias/vista":
            ids_vistas = [i.strip() for i in (self._ler_corpo_form().get("ids") or "").split(",") if i.strip()][:20]
            self._enviar_json({"ok": _marcar_insignias_vistas(sessao["usuario"], ids_vistas)})

        elif caminho in ("/api/longnamejanitor/ligar", "/api/longnamejanitor/simulacao", "/api/longnamejanitor/executar",
                         "/api/longnamejanitor/config", "/api/longnamejanitor/mover-tudo"):
            # LongNameJanitor ClienteQ (3.3.2.0): apaga/move arquivos nas pastas de rede, então só administrador
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "só administradores mexem no LongNameJanitor"}, status=403)
                return
            dados_lnj = self._ler_corpo_form()
            if caminho.endswith("/ligar"):
                resultado_lnj = _definir_ligado_lnj(dados_lnj.get("ligado") == "true", sessao["usuario"])
            elif caminho.endswith("/simulacao"):
                resultado_lnj = _definir_simulacao_lnj(dados_lnj.get("simulacao") == "true", sessao["usuario"])
            elif caminho.endswith("/executar"):
                resultado_lnj = _varredura_manual_lnj(sessao["usuario"])
            elif caminho.endswith("/mover-tudo"):
                resultado_lnj = _mover_tudo_processado_lnj(sessao["usuario"])
            else:
                try:
                    resultado_lnj = _salvar_config_lnj(json.loads(dados_lnj.get("dados") or ""), sessao["usuario"])
                except ValueError:
                    resultado_lnj = {"ok": False, "erro": "configuração inválida"}
            if resultado_lnj.get("ok"):
                logger_administracao.info("LongNameJanitor: '%s' em %s.", sessao["usuario"], caminho.rsplit("/", 1)[1])
            self._enviar_json(resultado_lnj, status=200 if resultado_lnj.get("ok") else 400)

        elif caminho == "/api/usuarios/permissao-servicos-adm":
            # Serviços ADM (3.3.1.0): permissão à parte, só admin concede, nunca é automática
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_servicos_adm"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_servicos_adm"] = nova_permissao
            logger_administracao.info(
                "Permissão Serviços ADM do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-publicar-comunidade":
            # Comunidade: desde a 3.4.6.0 é a permissão de marcar publicação como Importante (publicar todo mundo pode);
            # admin já tem; vale na hora, pode_marcar_importante lê o usuarios.json
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_publicar_comunidade"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            logger_administracao.info(
                "Permissão de publicar como importante na Comunidade do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-editar-central":
            # Central de Monitores (3.2.8.0): permissão à parte, só admin concede; editar exige ela E ser admin
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_editar_central"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_editar_central"] = nova_permissao
            logger_administracao.info(
                "Permissão de editar a Central de Monitores do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/central-monitores/salvar":
            # aba Editar da Central de Monitores (3.2.8.0): grava clientes, logos, links e servidores
            if not _central_pode_editar(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra editar a Central de Monitores"}, status=403)
                return
            dados_central = self._ler_corpo_form()
            try:
                clientes_central = json.loads(dados_central.get("dados") or "")
            except ValueError:
                self._enviar_json({"ok": False, "erro": "dados inválidos"}, status=400)
                return
            resultado_central = _central_salvar(clientes_central, (dados_central.get("versao") or "").strip(), sessao["usuario"])
            if resultado_central.get("ok"):
                logger_administracao.info("Central de Monitores: '%s' %s.", sessao["usuario"], resultado_central["resumo"])
            self._enviar_json(resultado_central, status=200 if resultado_central.get("ok") else (409 if resultado_central.get("conflito") else 400))

        elif caminho == "/api/usuarios/permissao-nnu-enchanced":
            # NNU Enchanced (3.2.2.0): permissão à parte, só admin concede, nunca é automática
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_nnu_enchanced"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_nnu_enchanced"] = nova_permissao
            logger_administracao.info(
                "Permissão do NNU Enchanced do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/usuarios/permissao-reprocessamento-cte2":
            # mesmo padrão das outras permissões à parte: só admin concede, nunca é automática
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_reprocessamento_cte2"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_reprocessamento_cte2"] = nova_permissao
            logger_administracao.info(
                "Permissão de Reprocessamento CTe2 do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/reprocessamento-cte2/api-key":
            # x-api-key colada no card (3.1.5.0): vai cifrada pro config.dat e nunca volta pra tela; só admin (3.3.1.0)
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "só administradores mexem no Reprocessamento CTe2"}, status=403)
                return
            resultado_rc = _definir_api_key_rc(self._ler_corpo_form().get("valor", ""), sessao["usuario"])
            if resultado_rc.get("ok"):
                logger_administracao.info("Reprocessamento CTe2: x-api-key cadastrada pelo card por '%s'.", sessao["usuario"])
            self._enviar_json(resultado_rc, status=200 if resultado_rc.get("ok") else 400)

        elif caminho in ("/api/reprocessamento-cte2/ligar", "/api/reprocessamento-cte2/executar",
                         "/api/reprocessamento-cte2/liberar"):
            # liga/pausa, roda um ciclo (chama a API de produção do CTe2) ou libera uma chave bloqueada: só admin (3.3.1.0)
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "só administradores ligam, pausam, rodam ou liberam no Reprocessamento CTe2"}, status=403)
                return
            dados = self._ler_corpo_form()
            if caminho.endswith("/ligar"):
                resultado_rc = _definir_ligado_rc(dados.get("ligado", "") == "true", sessao["usuario"])
            elif caminho.endswith("/executar"):
                resultado_rc = _iniciar_ciclo_manual_rc(sessao["usuario"])
            else:
                resultado_rc = _liberar_chave_rc(dados.get("chave", ""), sessao["usuario"])
            self._enviar_json(resultado_rc, status=200 if resultado_rc.get("ok") else 400)

        elif caminho == "/api/usuarios/permissao-indicadores-mensais":
            # Mesmo padrão de pode_feedbacks: só admin concede, e nunca é automática
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_indicadores_mensais"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_indicadores_mensais"] = nova_permissao
            logger_administracao.info(
                "Permissão de Indicadores Mensais do usuário '%s' alterada para %s por '%s'.",
                usuario, nova_permissao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho in ("/api/indicadores-mensais/efetividade", "/api/indicadores-mensais/noc",
                         "/api/indicadores-mensais/satisfacao"):
            # grava no banco do Movidesk: UPDATE de uma coluna em um registro (lógica na área)
            if not _tem_acesso_indicadores_mensais(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            dados = self._ler_corpo_form()
            definir = {"efetividade": _definir_efetividade_imx, "noc": _definir_justificativa_noc_imx,
                       "satisfacao": _definir_considerar_satisfacao_imx}[caminho.rsplit("/", 1)[1]]
            resultado = definir(dados.get("id", ""), dados.get("valor", ""), sessao["usuario"])
            self._enviar_json(resultado, status=200 if resultado["ok"] else 400)

        elif caminho == "/api/usuarios/permissao-logs":
            # Só quem já é admin pode CONCEDER essa permissão (igual as
            # outras) - mas quem RECEBE não precisa ser admin (diferente
            # de pode_feedbacks/pode_manutencao_usuarios - essa é pra
            # AMPLIAR acesso pra não-admin, não uma trava extra).
            if not sessao["admin"]:
                self._enviar_json({"ok": False, "erro": "requer administrador"}, status=403)
                return
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            nova_permissao = dados.get("permitido", "") == "true"
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            USUARIOS_WEB[usuario]["pode_ver_logs"] = nova_permissao
            if not _salvar_usuarios(USUARIOS_WEB):
                self._enviar_json({"ok": False, "erro": "não foi possível gravar o usuarios.json (detalhes no log)"}, status=500)
                return
            for s in SESSIONS.values():
                if s["usuario"] == usuario:
                    s["pode_ver_logs"] = nova_permissao
            logger_administracao.info(
                "Permissão de leitura de Logs do usuário '%s' alterada para %s por '%s'.",
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
            genero_pda = (dados.get("genero_pda") or "").strip()
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
                enviar_boas_vindas=enviar_boas_vindas, genero_pda=genero_pda,
            )
            self._enviar_json({"ok": True, **resultado})

        elif caminho == "/api/manutencao-usuarios/diagnostico":
            # SÓ CONSULTA - não grava nada em lugar nenhum (nem PDA, nem
            # Movidesk, nem banco). Cruza login+PDA+Movidesk+bancos pra
            # UMA pessoa só, de uma vez - pedido explícito do Igor.
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
            mudou_status = _marcar_status_usuario(usuario, novo_ativo, sessao["usuario"])  # guarda quando foi desativado (3.1.5.0)
            _salvar_usuarios(USUARIOS_WEB)
            if mudou_status:  # desativado sai dos Rankings; reativado volta com os ranks de antes (3.3.1.0)
                (_restaurar_pessoa_rank if novo_ativo else _arquivar_pessoa_rank)(usuario, sessao["usuario"])
            if mudou_status:
                _avisar_mudanca_status(usuario)  # aviso pra todo mundo no mural e no sininho
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
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            # desde a 2.35.5.0 a própria pessoa informa a dela no perfil; admin muda a de qualquer um
            if not sessao["admin"] and sessao["usuario"] != usuario:
                self._enviar_json({"ok": False, "erro": "você só pode alterar a sua própria data de início"}, status=403)
                return
            nova_data = (dados.get("data_inicio") or "").strip()
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            # opcional (pode ficar em branco) - formato AAAA-MM-DD (o mesmo
            # que <input type="date"> já manda); não pode ser no futuro nem absurda
            if nova_data:
                try:
                    data_lida = datetime.strptime(nova_data, "%Y-%m-%d").date()
                except ValueError:
                    self._enviar_json({"ok": False, "erro": "data inválida"}, status=400)
                    return
                if data_lida > datetime.now().date() or data_lida.year < 1980:
                    self._enviar_json({"ok": False, "erro": "a data de início não pode ser no futuro"}, status=400)
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
            # ativa). Pedido do Igor em 10/09/2026: padronizar o mesmo
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
                # grupo e autores (listas) também levam o login - antes o grupo ficava com o nome velho
                for campo in ("usuarios", "autores"):
                    if usuario_antigo in (f.get(campo) or []):
                        f[campo] = [usuario_novo if u == usuario_antigo else u for u in f[campo]]
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
                # `usuario` (a chave do dict, ex.: "igor") é o LOGIN de
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
            # 3.2.5.0: aceita também "Suporte e Monitoramento" (a tela já oferecia, mas a rota recusava) e "Serviços"
            if nova_atribuicao not in _ATRIBUICOES_VALIDAS:
                self._enviar_json({"ok": False, "erro": "atribuição inválida"}, status=400)
                return
            USUARIOS_WEB[usuario]["atribuicao"] = nova_atribuicao
            _salvar_usuarios(USUARIOS_WEB)
            logger_administracao.info(
                "Atribuição do usuário '%s' alterada pra '%s' por '%s'.",
                usuario, nova_atribuicao, sessao["usuario"],
            )
            self._enviar_json({"ok": True})

        elif caminho == "/api/mural/palma":
            # palminhas num evento do mural (clicar de novo desfaz)
            resultado_palma = _alternar_palma_mural((self._ler_corpo_form().get("evento") or "").strip(), sessao["usuario"])
            self._enviar_json(resultado_palma, status=200 if resultado_palma.get("ok") else 400)

        elif caminho == "/api/mural/comentar":
            dados_com = self._ler_corpo_form()
            resultado_com = _comentar_mural((dados_com.get("evento") or "").strip(), sessao["usuario"], dados_com.get("texto") or "",
                                            imagem=dados_com.get("imagem") or "")
            self._enviar_json(resultado_com, status=200 if resultado_com.get("ok") else 400)

        elif caminho == "/api/mural/comentario/apagar":
            dados_com = self._ler_corpo_form()
            resultado_com = _apagar_comentario_mural((dados_com.get("evento") or "").strip(), (dados_com.get("id") or "").strip(),
                                                     sessao["usuario"])
            self._enviar_json(resultado_com, status=200 if resultado_com.get("ok") else 400)

        elif caminho == "/api/mural/postar":
            # publicação manual na Comunidade (3.2.6.0), por enquanto só administrador (conferido em criar_post)
            dados_post = self._ler_corpo_form()
            arquivos_post = []
            for n in range(int(dados_post.get("qtd_arquivos") or 0) if (dados_post.get("qtd_arquivos") or "0").isdigit() else 0):
                if n >= 20:
                    break
                arquivos_post.append(((dados_post.get(f"arquivo_nome_{n}") or "").strip(), dados_post.get(f"arquivo_{n}") or ""))
            votacao_post = None
            if (dados_post.get("votacao") or "").strip():
                try:
                    votacao_post = json.loads(dados_post["votacao"])
                except ValueError:
                    self._enviar_json({"ok": False, "erro": "votação inválida"}, status=400)
                    return
            coautores_post = [l for l in (dados_post.get("coautores") or "").split(",") if l.strip()][:60]
            resultado_post = _criar_post_mural(sessao["usuario"], dados_post.get("texto") or "", dados_post.get("importante") == "1",
                                               arquivos_post, votacao=votacao_post, publico=dados_post.get("publico") or "",
                                               coautores=coautores_post)
            if resultado_post.get("ok"):
                logger_administracao.info("Comunidade: '%s' publicou %s (%d arquivo(s)), id %s.", sessao["usuario"],
                                          "um aviso importante" if dados_post.get("importante") == "1" else "uma publicação",
                                          len(arquivos_post), resultado_post["id"])
            self._enviar_json(resultado_post, status=200 if resultado_post.get("ok") else 400)

        elif caminho.startswith("/api/consumo-indevido/"):
            # Consumo Indevido (beta, 3.4.3.0): tudo só administrador
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "só administradores"}, status=403)
                return
            dados_ci = self._ler_corpo_form()
            acao_ci = caminho.rsplit("/", 1)[1]
            if acao_ci == "config":
                resultado_ci = _salvar_config_ci(dados_ci, sessao["usuario"])
            elif acao_ci == "ligar":
                resultado_ci = _definir_ligado_ci(dados_ci.get("ligado") == "true", sessao["usuario"])
            elif acao_ci == "testar":
                resultado_ci = _testar_consulta_ci(dados_ci)
            elif acao_ci == "executar":
                resultado_ci = _executar_ci("manual")
            elif acao_ci == "teste-teams":
                resultado_ci = _teste_teams_ci(sessao["usuario"])
            else:
                self._enviar_json({"ok": False, "erro": "ação desconhecida"}, status=404)
                return
            if acao_ci in ("config", "ligar") and resultado_ci.get("ok"):
                logger_administracao.info("Consumo indevido: '%s' em %s.", sessao["usuario"], acao_ci)
            self._enviar_json(resultado_ci, status=200 if resultado_ci.get("ok") else 400)

        elif caminho.startswith("/api/nnu-status/"):
            # NNU · status 20 → 15 (beta, 3.4.9.0): mexer é só administrador (faz UPDATE no banco); ver é de todos (3.5.1.0)
            if not sessao.get("admin"):
                self._enviar_json({"ok": False, "erro": "só administradores"}, status=403)
                return
            dados_ns = self._ler_corpo_form()
            acao_ns = caminho.rsplit("/", 1)[1]
            if acao_ns == "config":
                resultado_ns = _config_nnu_status(dados_ns, sessao["usuario"])
            elif acao_ns == "ligar":
                resultado_ns = _ligar_nnu_status(dados_ns.get("ligado") == "true", sessao["usuario"])
            elif acao_ns == "simulacao":
                resultado_ns = _simulacao_nnu_status(dados_ns.get("simulacao") != "false", sessao["usuario"])
            elif acao_ns == "rodar":
                # varredura manual (3.4.9.3): a mesma rodada da automática, na hora
                resultado_ns = _rodar_nnu_status("manual", sessao["usuario"])
            elif acao_ns == "testar":
                resultado_ns = _testar_nnu_status(dados_ns)
            elif acao_ns == "reenviar":
                resultado_ns = _reenviar_nnu_status((dados_ns.get("id") or "").strip(), sessao["usuario"])
            else:
                self._enviar_json({"ok": False, "erro": "ação desconhecida"}, status=404)
                return
            if acao_ns in ("config", "ligar", "simulacao", "rodar") and resultado_ns.get("resultados", resultado_ns.get("ok")):
                logger_administracao.info("NNU 20 → 15: '%s' em %s.", sessao["usuario"], acao_ns)
            self._enviar_json(resultado_ns, status=200 if resultado_ns.get("ok") else 400)

        elif caminho in ("/api/loja/comprar", "/api/loja/usar"):
            # Loja de Palminhas (3.3.7.0): cada um mexe só nos próprios itens
            dados_loja = self._ler_corpo_form()
            id_loja = (dados_loja.get("id") or "").strip()
            if caminho.endswith("/comprar"):
                resultado_loja = _comprar_loja(sessao["usuario"], id_loja, usar=dados_loja.get("usar") == "1")
            else:
                resultado_loja = _usar_loja(sessao["usuario"], id_loja)
            self._enviar_json(resultado_loja, status=200 if resultado_loja.get("ok") else 400)

        elif caminho == "/api/halloween/doce":
            # Caça aos Doces (3.3.7.0): só conta de 24/10 a 01/11 (checado na logica)
            resultado_doce = _halloween.achar_doce(sessao["usuario"], (self._ler_corpo_form().get("id") or "").strip())
            self._enviar_json(resultado_doce, status=200 if resultado_doce.get("ok") else 400)

        elif caminho == "/api/mural/votar":
            # votação numa publicação da Comunidade (3.3.0.0): qualquer pessoa logada vota (votos públicos desde a 3.3.6.0)
            dados_voto = self._ler_corpo_form()
            escolhas_voto = [e.strip() for e in (dados_voto.get("opcoes") or "").split(",") if e.strip()][:10]
            resultado_voto = _votar_post_mural((dados_voto.get("id") or "").strip(), sessao["usuario"], escolhas_voto)
            self._enviar_json(resultado_voto, status=200 if resultado_voto.get("ok") else 400)

        elif caminho == "/api/mural/post/reenviar-teams":
            # 3.3.4.2: manda de novo o cartão de uma publicação importante pro Teams (só admin; checado na logica)
            id_post_teams = (self._ler_corpo_form().get("id") or "").strip()
            resultado_teams = _reenviar_teams_post(id_post_teams, sessao["usuario"])
            if resultado_teams.get("ok"):
                logger_administracao.info("Comunidade: publicação %s reenviada ao Teams por '%s'.", id_post_teams, sessao["usuario"])
            self._enviar_json(resultado_teams, status=200 if resultado_teams.get("ok") else 400)

        elif caminho == "/api/mural/post/apagar":
            id_post_apagar = (self._ler_corpo_form().get("id") or "").strip()
            resultado_apagar_post = _apagar_publicacao_mural(id_post_apagar, sessao["usuario"])
            if resultado_apagar_post.get("ok"):
                logger_administracao.info("Comunidade: publicação %s apagada por '%s'.", id_post_apagar, sessao["usuario"])
            self._enviar_json(resultado_apagar_post, status=200 if resultado_apagar_post.get("ok") else 400)

        elif caminho == "/api/notificacoes/lidas":
            self._enviar_json({"ok": _marcar_notificacoes_lidas(sessao["usuario"], VERSAO_PDA)})

        elif caminho == "/api/anuncios/visto":
            # anúncio de uma vez só (3.2.0.0, ex.: "foto de perfil pode ser GIF"): não aparece de novo pra essa pessoa
            self._enviar_json({"ok": _marcar_anuncio_visto(sessao["usuario"], (self._ler_corpo_form().get("anuncio") or "").strip())})

        elif caminho == "/api/hub/favoritos":
            # qualquer pessoa logada favorita os PRÓPRIOS cards (não mexe em
            # permissão: card sem acesso nem aparece no hub dela)
            dados = self._ler_corpo_form()
            try:
                favoritos = definir_favoritos_hub(sessao["usuario"], json.loads(dados.get("cards") or "[]"))
            except (ValueError, KeyError):
                self._enviar_json({"ok": False, "erro": "lista de favoritos inválida"}, status=400)
                return
            self._enviar_json({"ok": True, "favoritos": favoritos})

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

            if tipo not in ("ferias", "day_off", "atestado", "afastamento"):  # afastamento (INSS e afins) desde a 3.4.4.0
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
                    rotulo_conflito = {"day_off": "Day Off", "atestado": "atestado", "afastamento": "afastamento"}.get(tipo_conflito, "férias")
                    self._enviar_json(
                        {"ok": False, "erro": f"essa pessoa já tem {rotulo_conflito} cadastrado entre {conflito['inicio']} e {conflito['fim']}, que se sobrepõe a esse período"},
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
            # _proximo_id_historico_carreira: o "global" já foi declarado mais acima no
            # do_POST (rota /api/insignias/participar); repetir aqui é erro de sintaxe
            dados = self._ler_corpo_form()
            usuario = dados.get("usuario", "")
            # desde a 2.35.5.0 a própria pessoa monta o histórico dela no perfil; admin, o de qualquer um
            if not sessao["admin"] and sessao["usuario"] != usuario:
                self._enviar_json({"ok": False, "erro": "você só pode alterar o seu próprio histórico"}, status=403)
                return
            if usuario not in USUARIOS_WEB:
                self._enviar_json({"ok": False, "erro": "usuário não encontrado"}, status=404)
                return
            campos_hist, erro_hist = _validar_campos_historico_carreira(dados)
            if erro_hist:
                self._enviar_json({"ok": False, "erro": erro_hist}, status=400)
                return
            cargo, area, inicio, fim = campos_hist

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

        elif caminho == "/api/historico-carreira/editar":
            # editar um cargo já lançado (3.1.1.0): mesma permissão e validação do criar
            dados = self._ler_corpo_form()
            try:
                id_registro = int(dados.get("id", ""))
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return
            campos_hist, erro_hist = _validar_campos_historico_carreira(dados)
            if erro_hist:
                self._enviar_json({"ok": False, "erro": erro_hist}, status=400)
                return
            cargo, area, inicio, fim = campos_hist

            with _lock_historico_carreira:
                registro = next((h for h in HISTORICO_CARREIRA if h["id"] == id_registro), None)
                if not registro:
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                if not sessao["admin"] and registro.get("usuario") != sessao["usuario"]:
                    self._enviar_json({"ok": False, "erro": "você só pode alterar o seu próprio histórico"}, status=403)
                    return
                antes = f"{registro.get('cargo')} ({registro.get('inicio')} a {registro.get('fim') or 'atual'})"
                registro.update({
                    "cargo": cargo, "area": area, "inicio": inicio, "fim": fim or None,
                    "editado_por": sessao["usuario"], "editado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                _salvar_historico_carreira(HISTORICO_CARREIRA)

            nome_pessoa = USUARIOS_WEB.get(registro["usuario"], {}).get("nome") or registro["usuario"]
            logger_administracao.info(
                "Histórico de carreira: '%s' de '%s' editado pra '%s' (%s a %s) por '%s'.",
                antes, nome_pessoa, cargo, inicio, fim or "atual", sessao["usuario"],
            )
            self._enviar_json({"ok": True, "registro": registro})

        elif caminho == "/api/historico-carreira/excluir":
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
                if not sessao["admin"] and registro.get("usuario") != sessao["usuario"]:
                    self._enviar_json({"ok": False, "erro": "você só pode alterar o seu próprio histórico"}, status=403)
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
            texto = (dados.get("texto") or "").strip()
            nota_bruta = (dados.get("nota") or "").strip()
            tipo = dados.get("tipo") or "Feedback"
            link_canva = (dados.get("link_canva") or "").strip()
            anexo_data_url = dados.get("anexo_data_url") or ""
            anexo_nome = (dados.get("anexo_nome") or "").strip()

            if not _tem_acesso_feedbacks(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Feedbacks e Alinhamentos"}, status=403)
                return
            # escopo, quem recebe, autores (podem ser vários) e equipe do aviso (2.34.7.0)
            campos_fb, erro_fb = _validar_alvos_e_autores_fb(dados, sessao["usuario"])
            if erro_fb:
                self._enviar_json({"ok": False, "erro": erro_fb}, status=400)
                return
            escopo = campos_fb["escopo"]

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

            global _proximo_id_feedback_usuario
            with _lock_feedbacks_usuarios:
                registro = {
                    "id": _proximo_id_feedback_usuario,
                    **campos_fb,
                    # "autor" = quem registrou no PDA; "autores" = quem fez o feedback/alinhamento
                    "autor": sessao["usuario"],
                    "tipo": tipo, "texto": texto, "nota": nota, "link_canva": link_canva or None,
                    "anexo": None, "anexo_nome_original": None,
                    "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                FEEDBACKS_USUARIOS.append(registro)
                _proximo_id_feedback_usuario += 1
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            aviso_anexo = None
            if anexo_data_url:
                nome_salvo, erro_anexo = _salvar_anexo_feedback(registro["id"], anexo_nome, anexo_data_url)
                if erro_anexo:
                    aviso_anexo = f"Registro salvo, mas o anexo falhou: {erro_anexo}"
                    logger.warning("Falha ao anexar arquivo no feedback %d: %s", registro["id"], erro_anexo)
                else:
                    with _lock_feedbacks_usuarios:
                        registro["anexo"] = nome_salvo
                        registro["anexo_nome_original"] = anexo_nome or nome_salvo
                        _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            descricao_alvo = _descricao_alvo_feedback(registro)
            logger_administracao.info(
                "%s (escopo %s) adicionado sobre '%s' por '%s' (nota %s).",
                tipo, escopo, descricao_alvo, sessao["usuario"], nota,
            )
            _notificar_feedback_inserido(
                registro["autor_nome"], tipo, registro["criado_em"], descricao_alvo, texto, nota,
                destinatarios=_destinatarios_equipe_fb(registro["equipe"]),
                varios_autores=len(registro["autores"]) > 1, equipe=registro["equipe"],
            )
            # e no sininho de quem recebe os e-mails da equipe (3.0.5.0)
            _avisar_equipe_fb_no_sininho(registro, descricao_alvo)
            resposta = {"ok": True, "registro": registro}
            if aviso_anexo:
                resposta["aviso"] = aviso_anexo
            self._enviar_json(resposta)

        elif caminho == "/api/feedback-usuario/editar":
            if not _tem_acesso_feedbacks(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Feedbacks e Alinhamentos"}, status=403)
                return
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

            # quem recebeu, autores e equipe passaram a ser editáveis (2.34.7.0); a edição
            # não manda e-mail de novo - o aviso é só na criação
            campos_fb, erro_fb = _validar_alvos_e_autores_fb(dados, sessao["usuario"])
            if erro_fb:
                self._enviar_json({"ok": False, "erro": erro_fb}, status=400)
                return

            with _lock_feedbacks_usuarios:
                registro = next((f for f in FEEDBACKS_USUARIOS if f["id"] == id_registro), None)
                if not registro or not _pode_ver_registro_fb(registro, sessao["usuario"]):
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                registro.update(campos_fb)
                registro["texto"] = texto
                registro["nota"] = nota
                registro["tipo"] = tipo
                registro["link_canva"] = link_canva or None
                registro["editado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                registro["editado_por"] = sessao["usuario"]
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            logger_administracao.info(
                "%s (id %d, sobre '%s') editado por '%s'.",
                tipo, id_registro, _descricao_alvo_feedback(registro), sessao["usuario"],
            )
            self._enviar_json({"ok": True, "registro": registro})

        elif caminho == "/api/feedback-usuario/excluir":
            if not _tem_acesso_feedbacks(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Feedbacks e Alinhamentos"}, status=403)
                return
            dados = self._ler_corpo_form()
            try:
                id_registro = int(dados.get("id", ""))
            except (ValueError, TypeError):
                self._enviar_json({"ok": False, "erro": "id inválido"}, status=400)
                return

            with _lock_feedbacks_usuarios:
                registro = next((f for f in FEEDBACKS_USUARIOS if f["id"] == id_registro), None)
                if not registro or not _pode_ver_registro_fb(registro, sessao["usuario"]):
                    self._enviar_json({"ok": False, "erro": "registro não encontrado"}, status=404)
                    return
                descricao_alvo = _descricao_alvo_feedback(registro)
                FEEDBACKS_USUARIOS.remove(registro)
                _salvar_feedbacks_usuarios(FEEDBACKS_USUARIOS)

            logger_administracao.info(
                "Feedback (id %d, sobre '%s') removido por '%s'.",
                id_registro, descricao_alvo, sessao["usuario"],
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
            if resultado.get("ok") and dados.get("cargo", "").strip():
                # cargo editado à mão no vínculo: o cadastro do PDA acompanha na hora
                atualizar_cargos_movidesk({id_usuario_movidesk: dados.get("cargo", "").strip()})
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/usuarios-movidesk/sincronizar":
            # Botão "🔄 Atualizar lista" - diferente da rota de LEITURA
            # (/api/usuarios-movidesk, que só relê o banco), essa aqui
            # busca de verdade na API do Movidesk e sincroniza a tabela
            # (insere/atualiza/reativa/inativa) - mesma permissão restrita
            # de Manutenção de Usuários, já que é uma ação de escrita em
            # produção, igual cadastrar/desativar.
            if not _tem_acesso_manutencao_usuarios(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão pra Manutenção de Usuários"}, status=403)
                return
            resultado = _sincronizar_usuarios_movidesk()
            if resultado.get("ok"):
                logger_administracao.info(
                    "Sincronização de agentes do Movidesk disparada por '%s' - novos: %d, atualizados: %d, "
                    "reativados: %d, sem alteração: %d, inativados: %d.",
                    sessao["usuario"], resultado["novos"], resultado["atualizados"],
                    resultado["reativados"], resultado["sem_alteracao"], resultado["inativados"],
                )
                # cargo do Movidesk no cadastro do PDA de quem está vinculado (2.34.4.0)
                # só preenche quem está sem cargo: o cargo já preenchido no PDA não é sobreposto (3.2.0.0)
                cargos = atualizar_cargos_movidesk(resultado.pop("cargos_por_id", {}), sobrescrever=False)
                for login, antigo, novo in cargos["atualizados"]:
                    logger_administracao.info("Cargo de '%s' atualizado pelo Movidesk: '%s' -> '%s'.", login, antigo or "-", novo)
                resultado["cargos_pda"] = len(cargos["atualizados"])
                resultado["sem_vinculo_pda"] = cargos["sem_vinculo"]
                resultado["cargos_gravados"] = cargos["gravou"]
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

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

            # só uma string por cliente + produto: se já existe, a tela pergunta
            # e, confirmando (substituir=true), troca a conexão da que já existe
            id_existente = _buscar_string_connection_igual(cliente, produto)
            if id_existente:
                if dados.get("substituir") != "true":
                    self._enviar_json({
                        "ok": False, "duplicada": True, "id_existente": id_existente,
                        "erro": f"Já existe uma String Connection pra {cliente} · {produto}.",
                    }, status=409)
                    return
                STRING_CONNECTIONS[id_existente].update({
                    "cliente": cliente, "produto": produto, "conexao": conexao,
                    "atualizado_por": sessao["usuario"], "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                })
                _salvar_string_connections(STRING_CONNECTIONS)
                logger_administracao.info(
                    "String Connection #%s substituída (cliente=%s produto=%s) por '%s'.",
                    id_existente, cliente, produto, sessao["usuario"],
                )
                self._enviar_json({"ok": True, "id": id_existente, "substituida": True})
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
            # editar pra um cliente + produto que já tem OUTRA string: pergunta
            # e, confirmando, fica esta e a outra sai (nunca duas pro mesmo par)
            id_outra = _buscar_string_connection_igual(cliente, produto, ignorar_id=id_conexao)
            if id_outra and dados.get("substituir") != "true":
                self._enviar_json({
                    "ok": False, "duplicada": True, "id_existente": id_outra,
                    "erro": f"Já existe outra String Connection pra {cliente} · {produto}.",
                }, status=409)
                return
            STRING_CONNECTIONS[id_conexao].update({
                "cliente": cliente, "produto": produto, "conexao": conexao,
                "atualizado_por": sessao["usuario"], "atualizado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })
            if id_outra:
                del STRING_CONNECTIONS[id_outra]
            _salvar_string_connections(STRING_CONNECTIONS)
            logger_administracao.info(
                "String Connection #%s atualizada por '%s'%s.", id_conexao, sessao["usuario"],
                f" (substituiu a #{id_outra}, mesmo cliente e produto)" if id_outra else "",
            )
            self._enviar_json({"ok": True, "substituida": bool(id_outra)})

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

        elif caminho == "/api/relatorios-cliente_a/gerar":
            if not _tem_acesso_relatorios_cliente_a(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            dados = self._ler_corpo_form()
            logger_cliente_a.info("Geração manual do relatório de %s disparada por '%s'.", dados.get("data", "?"), sessao["usuario"])
            resultado = _gerar_relatorio_cliente_a(dados.get("data", ""))
            self._enviar_json(resultado, status=200 if resultado.get("ok") else 502)

        elif caminho == "/api/relatorios-cliente_a/forcar-automatico":
            if not _tem_acesso_relatorios_cliente_a(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            logger_cliente_a.info("Execução automática diária forçada manualmente por '%s'.", sessao["usuario"])
            threading.Thread(target=_executar_relatorio_cliente_a_diario, daemon=True).start()
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
            try:
                mes_escolhido = validar_mes_dash_financeiro(self._ler_corpo_form().get("mes", ""))
            except ValueError as e:
                self._enviar_json({"ok": False, "erro": str(e)}, status=400)
                return
            if not _tentar_iniciar_dash_financeiro():
                self._enviar_json({"ok": False, "erro": "já tem uma execução em andamento - aguarde ela terminar"}, status=409)
                return
            logger_dash_financeiro.info("Execução manual de %s disparada por '%s'.",
                                        _periodo_mes_anterior(mes_escolhido)["arquivo"], sessao["usuario"])
            threading.Thread(target=_executar_todos_dash_financeiro, kwargs={"mes": mes_escolhido}, daemon=True).start()
            self._enviar_json({"ok": True})

        elif caminho == "/api/dash-financeiro/gerar-de-novo":
            # refaz o CSV do mês de referência de UM produto, sobrescrevendo o
            # que já existe (ex.: incluir um cliente novo, como a ClienteA no CTe)
            if not _tem_acesso_dash_financeiro(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            corpo_df = self._ler_corpo_form()
            produto = corpo_df.get("produto", "")
            if produto not in ORDEM_PRODUTOS_DASH_FINANCEIRO:
                self._enviar_json({"ok": False, "erro": "Produto inválido."}, status=400)
                return
            try:
                mes_escolhido = validar_mes_dash_financeiro(corpo_df.get("mes", ""))
            except ValueError as e:
                self._enviar_json({"ok": False, "erro": str(e)}, status=400)
                return
            if not _tentar_iniciar_dash_financeiro():
                self._enviar_json({"ok": False, "erro": "já tem uma execução em andamento - aguarde ela terminar"}, status=409)
                return
            logger_dash_financeiro.info("Geração de novo do %s (%s) disparada por '%s'.",
                                        produto, _periodo_mes_anterior(mes_escolhido)["arquivo"], sessao["usuario"])
            threading.Thread(target=_executar_todos_dash_financeiro,
                             kwargs={"produtos": [produto], "forcar": True, "mes": mes_escolhido}, daemon=True).start()
            self._enviar_json({"ok": True})

        elif caminho in ("/api/dash-financeiro/testar-conexoes", "/api/dash-financeiro/procurar-empresa"):
            # SÓ LEITURA: roda a consulta do mês em cada cliente (ou procura uma
            # empresa nas bases) sem gravar CSV - pra ver na hora por que um
            # cliente não entrou no arquivo. POST porque abre conexão em todos os bancos.
            if not _tem_acesso_dash_financeiro(sessao):
                self._enviar_json({"ok": False, "erro": "sem permissão"}, status=403)
                return
            dados = self._ler_corpo_form()
            produto = dados.get("produto", "")
            try:
                conexoes_json = _carregar_conexoes_dash_financeiro()
            except Exception as e:
                self._enviar_json({"ok": False, "erro": f"Não foi possível ler o dash_financeiro_conexoes.json: {e}"})
                return
            if caminho.endswith("testar-conexoes"):
                try:
                    mes_escolhido = validar_mes_dash_financeiro(dados.get("mes", ""))
                except ValueError as e:
                    self._enviar_json({"ok": False, "erro": str(e)}, status=400)
                    return
                logger_dash_financeiro.info("Teste de conexões do %s (%s) disparado por '%s'.",
                                            produto, _periodo_mes_anterior(mes_escolhido)["arquivo"], sessao["usuario"])
                self._enviar_json(testar_conexoes_dash_financeiro(produto, conexoes_json, mes_escolhido))
            else:
                self._enviar_json(procurar_empresa_dash_financeiro(produto, conexoes_json, dados.get("termo", "")))

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
        s.connect(("192.0.2.246", 1))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


# Assim que existir um registro de DNS interno (ou entrada em hosts) apontando
# esse nome para o IP desta máquina, é só preencher aqui - o servidor já
# aceita conexão por qualquer nome/IP que chegue nele, não precisa mudar mais
# nada. Deixe None para mostrar o nome de máquina "cru" (ex.: srv421).
NOME_AMIGAVEL_WEB: Optional[str] = "pda.local"  # ver LEIA-ME sobre como fazer esse nome resolver de verdade


# Porta principal (obrigatória: links antigos, e-mails e favoritos usam :8765) e
# porta extra 80 (2.34.2.0), que deixa acessar sem porta na URL
# (http://pda.local/ ou http://192.0.2.198/). A 80 é opcional: se estiver
# ocupada no servidor (IIS, outro programa, HTTP.sys) o PDA sobe só na 8765 e
# avisa no log. As duas atendem pelo mesmo handler, com as mesmas sessões.
PORTA_WEB_PRINCIPAL = 8765
PORTA_WEB_SEM_PORTA_NA_URL = 80


def _subir_servidor_http(porta: int):
    servidor = ThreadingHTTPServer(("0.0.0.0", porta), _PainelHTTPHandler)
    threading.Thread(target=servidor.serve_forever, daemon=True, name=f"web-{porta}").start()
    return servidor


def iniciar_servidor_web(job_states: List[JobState], porta: int = PORTA_WEB_PRINCIPAL) -> Optional[str]:
    """Sobe o servidor web (porta principal + porta 80, se der) em threads
    separadas. Retorna a URL de acesso (sem porta quando a 80 subiu), ou None
    se nem a porta principal subiu (ex.: PDA já aberto)."""
    _PainelHTTPHandler.job_states = job_states
    _PainelHTTPHandler.state_by_nome = {s.job.nome: s for s in job_states}

    try:
        _subir_servidor_http(porta)
    except OSError as e:
        logger.error("Não foi possível subir o servidor web na porta %d: %s", porta, e)
        return None

    porta_80_ok = False
    if PORTA_WEB_SEM_PORTA_NA_URL and PORTA_WEB_SEM_PORTA_NA_URL != porta:
        try:
            _subir_servidor_http(PORTA_WEB_SEM_PORTA_NA_URL)
            porta_80_ok = True
        except OSError as e:
            # 10048 = porta em uso; 10013 = reservada/bloqueada (HTTP.sys/IIS ou política)
            logger.warning(
                "Porta %d indisponível (%s): o PDA segue só na %d. Pra acessar sem porta na URL, "
                "libere a %d no servidor (veja configurar_porta_80_servidor.bat).",
                PORTA_WEB_SEM_PORTA_NA_URL, e, porta, PORTA_WEB_SEM_PORTA_NA_URL,
            )

    hostname = socket.gethostname()
    ip = obter_ip_local()
    nome_exibido = NOME_AMIGAVEL_WEB or hostname
    enderecos = [f"http://{h}:{porta}/" for h in (nome_exibido, ip)]
    if porta_80_ok:
        enderecos = [f"http://{h}/" for h in (nome_exibido, ip)] + enderecos
    logger.info("Servidor web disponível em: %s", " · ".join(enderecos))
    return f"http://{nome_exibido}/" if porta_80_ok else f"http://{nome_exibido}:{porta}/"


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
# REGRA COMBINADA COM O IGOR (05/09/2026):
#   Formato de 4 níveis desde 25/09/2026: MAJOR.MINOR.FUNCIONALIDADE.AJUSTE
#   - MAJOR (o "2"): só sobe quando o Igor pedir explicitamente.
#   - MINOR (2.X): "fecha" uma versão do changelog - só sobe quando o Igor
#     pedir, pra juntar bastante coisa numa entrada só.
#   - FUNCIONALIDADE (2.x.X): funcionalidade nova ou mudança visual relevante
#     (zera o AJUSTE).
#   - AJUSTE (2.x.x.X): ajuste pequeno/correção.
#   - 3º e 4º vão só até 9 (máx. 2.34.9.9, regra de 01/10/2026): ajuste depois
#     do 9 sobe o 3º (2.34.5.9 -> 2.34.6.0); funcionalidade depois do 9 sobe o
#     MINOR (2.34.9.x -> 2.35.0.0, nunca 2.34.10.0), fechando o changelog.
#   - MAJOR: a v3 saiu em 02/10/2026, a pedido do Igor e em coautoria de
#     pessoa18 e pessoa40 (3.0.0.0). A v4 também só a pedido.
# Atualize isso manualmente a cada entrega - não tem automação lendo
# git/commits pra preencher isso sozinho.
VERSAO_PDA = "3.5.1.0"

# Changelog mostrado no card /changelog (aberto pra todo mundo logado), mais
# recente primeiro. Uma entrada por MINOR (rótulo só MAJOR.MINOR). Regra
# combinada com o Igor em 25/09/2026: o que sai dentro de uma MINOR (2.32.1.0,
# 2.32.1.1...) fica anotado em CHANGELOG_PENDENTE.md; quando ele pedir pra
# subir o MINOR (2.32 -> 2.33), os pendentes entram na entrada que está
# fechando (2.32), a data dela vira a do fechamento (saída da última versão
# definitiva) e abre a entrada 2.33. Cada item é (categoria, texto), com a
# categoria vinda de CATEGORIAS_CHANGELOG.
# Texto curto e direto: um título e poucos itens de uma linha, escritos pra
# quem usa o painel (não pra dev).
# Categorias de cada item do changelog, na ordem em que aparecem na entrada:
# chave -> (rótulo na etiqueta, cor da etiqueta)
CATEGORIAS_CHANGELOG = {
    "novo": ("Novo", "#4ec9b0"),          # funcionalidade que não existia
    "melhoria": ("Melhoria", "#2db8cf"),  # algo que já existia ficou melhor
    "correcao": ("Correção", "#e8a33d"),  # algo que estava errado
    "removido": ("Removido", "#f14c4c"),  # algo que saiu
}

CHANGELOG_PDA = [
    {
        "versao": "3.5", "data": "13/10/2026",
        "titulo": "NNU Enchanced no NFe e no NFCe",
        "itens": [
            ("novo", "NNU Enchanced: a automação do status 20 → 15 cobre também o NFCe do ClienteI (Standard, Enterprise e ClienteAE), com filtro NFe/NFCe na tela"),
            ("correcao", "ClienteI Standard agora aparece escrito do jeito certo nos alertas e no NNU Enchanced"),
            ("melhoria", "NNU Enchanced aberto pra todo mundo acompanhar; configurar, pausar e rodar as automações continua só com administrador"),
        ],
    },
    {
        # fechada em 13/10/2026 (3.4.9.3 foi a última; a funcionalidade seguinte passaria do 9 e abriu a 3.5)
        "versao": "3.4", "data": "13/10/2026",
        "titulo": "Comunidade em grupo e com vídeo, LongNameJanitor e NNU automáticos",
        "itens": [
            ("melhoria", "LongNameJanitor ClienteQ: os arquivos do CNPJ na pasta de processados do dia vão pra Processado/LongNameJanitor (substituindo o que já estiver lá), em vez de serem apagados; a pasta do dia troca sozinha à meia-noite"),
            ("melhoria", "NNU Enchanced (beta) foi pra Automações e ganhou abas: Tratativa guiada e as automações de NNU, começando pela do status 20 → 15"),
            ("correcao", "Indicadores Mensais abre no mês atual (abria no anterior) e troca sozinho quando o mês vira"),
            ("melhoria", "Logs se cuidam sozinhos: cada log guarda até 200 mil linhas e o excesso vai pra um zip, apagado 30 dias depois"),
            ("melhoria", "LongNameJanitor ClienteQ (beta) foi pra Automações e ganhou busca e filtro de ação na Atividade recente e no Histórico do dia"),
            ("melhoria", "Comunidade: todo mundo pode publicar; marcar a publicação como Importante (sininho pra todos e Teams) continua com quem tem permissão"),
            ("novo", "Comunidade: a cada 1.000 acessos o PDA comemora com um post no feed e um aviso no sininho"),
            ("melhoria", "Sobre o PDA: \"Alertas automáticos\" conta todos os alertas cadastrados na Manutenção de Alertas em Banco"),
            ("melhoria", "Alertas Suporte passou a se chamar Alertas Suporte (Legacy)"),
            ("melhoria", "LongNameJanitor ClienteQ: caixinhas por pasta pra escolher o que fica ligado (limpar a Processar, apagar nome longo, avisar NF repetida, manutenção automática do Processado e olhar o dia anterior)"),
            ("novo", "Calendário de Férias: novo tipo Afastamento (INSS e afins), junto de Férias, Day Off e Atestado"),
            ("novo", "Comunidade: vídeo nas publicações (MP4, WebM ou MOV, até 50 MB cada, 2 por publicação), tocando direto no feed"),
            ("novo", "Comunidade: publicação em grupo; quem publica marca as pessoas (ou uma equipe inteira) e todas aparecem como autoras e recebem as palminhas; clicando no grupo dá pra ver quem publicou"),
            ("correcao", "Comunidade: o botão Voltar ao topo sobe junto quando o rodapé aparece e não fica mais em cima do Changelog"),
            ("novo", "LongNameJanitor ClienteQ: botão \"Mover tudo do Processado\", que faz o mesmo em todas as pastas e subpastas do Processado, com o andamento na tela"),
        ],
    },
    {
        # fechada em 09/10/2026 (3.3.9.5 foi a última; a funcionalidade seguinte passaria do 9 e abriu a 3.4)
        "versao": "3.3", "data": "09/10/2026",
        "titulo": "Votações, Loja de Palminhas e uma Comunidade mais leve",
        "itens": [
            ("novo", "Comunidade: a publicação pode ter uma votação, com 2 a 6 opções, uma ou várias escolhas e prazo opcional pra encerrar"),
            ("melhoria", "Comunidade: clicar numa foto da publicação amplia ali mesmo, sem abrir outra aba, com setas pra passar as fotos"),
            ("novo", "Comunidade: publicação pra todo mundo ou só pra uma equipe (Suporte, Monitoramento ou Serviços)"),
            ("novo", "Comunidade: comentários com emojis e, nas publicações, com foto ou GIF"),
            ("novo", "Comunidade: publicação importante também chega no canal do Teams, com o texto completo e quem publicou"),
            ("melhoria", "Comunidade: a publicação da v3 saiu do topo e aparece também no filtro Publicações"),
            ("melhoria", "Rankings: quem é desativado no PDA sai dos rankings (volta se for reativado)"),
            ("melhoria", "Reprocessamento CTe2 aberto pra todo mundo acompanhar; ligar, pausar e rodar continuam com os administradores"),
            ("melhoria", "Indicadores Movidesk: o filtro de equipe vale também pras dúvidas processadas e o top solicitantes"),
            ("melhoria", "Fotos de perfil salvas com mais qualidade"),
            ("novo", "Changelog: um print de cada era e um pouco da história de como o PDA cresceu"),
            ("novo", "Em breve: LongNameJanitor ClienteQ, Limpeza de Máquinas e Versões mais recentes"),
            ("melhoria", "Central de Monitores: PowerDocs da ClienteH com o link novo"),
            ("novo", "LongNameJanitor ClienteQ (beta): tira das pastas de integração os arquivos com nome longo e as NFs repetidas, com modo simulação, números do dia e histórico"),
            ("melhoria", "GIF animado de até 5 MB na foto de perfil e nos comentários; as fotos do feed só carregam quando aparecem na tela"),
            ("melhoria", "Em breve: os cards ficam em sequência pelo andamento, primeiro os em beta, depois os em construção"),
            ("correcao", "Changelog: o detalhamento da v2 voltou a aparecer, com as versões da mais antiga pra mais nova"),
            ("melhoria", "LongNameJanitor ClienteQ: varre as pastas a cada 2 segundos, como o serviço antigo, sem repetir registros no histórico"),
            ("melhoria", "PDA mais leve: as telas chegam comprimidas (cerca de 6 vezes menores) e a logo fica guardada no navegador"),
            ("melhoria", "LongNameJanitor ClienteQ: o motivo diz cada regra que bateu (nome longo, NF repetida ou as duas) e, com duas cópias da mesma NF, fica a mais antiga"),
            ("melhoria", "Calendário de Férias: atualiza sozinho a cada 10 minutos"),
            ("correcao", "Comunidade: comentário ou publicação com uma palavra enorme sem espaço não vaza mais pra fora do card"),
            ("melhoria", "Votação pra uma equipe: junto do resultado aparece quem da equipe ainda não votou"),
            ("correcao", "Comunidade: quem está de day off aparece como \"Day off\" no bloco De férias (antes aparecia como férias)"),
            ("novo", "Seção Operações/Serviços no menu da Comunidade, logo abaixo de Gestão de equipe: Limpeza de Máquinas, Versões mais recentes e o novo Abertura de GMUD's (em construção)"),
            ("melhoria", "Comunidade: botão \"Voltar ao topo\" (com o texto), que aparece quando você rola bastante o feed"),
            ("correcao", "Publicação pra uma equipe aparece só pra essa equipe e pra quem publicou (antes administradores de outras equipes também viam)"),
            ("melhoria", "Comunidade mais leve: o feed abre com os primeiros acontecimentos e carrega o resto ao rolar até o fim (ou no \"Ver mais\"); comentários mostram só os mais recentes que cabem no espaço, com \"Ver comentários anteriores\""),
            ("novo", "Loja de Palminhas: troque as palminhas recebidas por wallpapers (Padrão Empresa, 67 e os de eventos) pra capa do perfil e o cartão da Comunidade; o ranking não muda"),
            ("novo", "Perfil com capa: o wallpaper de cada pessoa aparece no perfil dela, com a foto ao lado das informações"),
            ("melhoria", "Votação com prazo (1 hora, 4 horas, até o fim do dia, dias ou data e hora): quando acaba, mostra \"Votação encerrada\" e o resultado final com a opção vencedora"),
            ("melhoria", "Votações da Comunidade públicas: dá pra ver quem votou em cada opção"),
            ("novo", "Aviso fixo no topo da Comunidade com as votações abertas que você ainda não votou"),
            ("novo", "Votação no aviso importante do Teams: cada opção vira um botão que abre o PDA pra confirmar o voto (e o login volta pro link)"),
            ("melhoria", "LongNameJanitor: também limpa a pasta de processados do dia (Processado/ano/mês/dia), apagando todos os arquivos do CNPJ; NF repetida passa a só gerar aviso no monitor"),
            ("correcao", "Aviso importante no Teams: o botão \"Abrir na Comunidade\" abre pelo IP do PDA (antes usava o nome pda.local, que não abre fora das máquinas configuradas)"),
        ],
    },
    {
        "versao": "3.2", "data": "06/10/2026",
        "titulo": "Comunidade, publicações, rankings por equipe e foto em GIF",
        "itens": [
            ("novo", "Aviso no início pra quem já tem foto: agora dá pra usar um GIF animado como foto de perfil"),
            ("novo", "Mural: clicar em quem bateu palmas mostra a lista completa, com foto de cada um"),
            ("correcao", "Sincronizar com o Movidesk não troca mais o cargo já preenchido no PDA, e o perfil mostra o cargo do PDA"),
            ("novo", "NNU Enchanced (beta): tratativa guiada dos NNUs do ClienteI, com leitura da chave, prazo de 7 dias, comparação dos XMLs e mensagem pro time ClienteI (acesso com permissão à parte)"),
            ("melhoria", "Logs com mais de 30 dias são apagados sozinhos, pra economizar espaço"),
            ("novo", "Mural e sininho avisam quando alguém sai de férias e quando volta, com filtro Férias no feed"),
            ("melhoria", "Mural: o filtro Aniversários mostra os aniversários dos últimos 90 dias"),
            ("novo", "Central de Monitores: cliente ClienteG na visão Infraestrutura (Graylog, RabbitMQ, PowerDocs, Kubernetes e os servidores Jumper, JMeter, NFCe e Linux)"),
            ("correcao", "Trocar a foto de perfil (inclusive por um GIF) atualiza em todo lugar; antes a foto antiga podia continuar na navbar e na foto ampliada"),
            ("correcao", "Mural: o feed vem do acontecimento mais recente pro mais antigo, pela data e hora (antes misturava a ordem dentro do mesmo dia)"),
            ("melhoria", "Rankings: leaderboard de Produtos e Ranking geral por pontos, em que todo nível conta (Master 4, Ouro 3, Prata 2, Bronze 1)"),
            ("novo", "Equipe Serviços, à parte de Suporte e Monitoramento (aparece no perfil); quem é dela não entra no cálculo de horas nem na meta pela escala"),
            ("correcao", "O aviso de que dá pra usar GIF na foto de perfil aparece uma vez só (antes voltava a cada visita se a pessoa não clicasse em nada)"),
            ("melhoria", "O início agora se chama Comunidade"),
            ("novo", "Comunidade: administradores publicam no feed com texto, fotos, GIFs e arquivos anexados; marcar como importante avisa todo mundo no sininho"),
            ("melhoria", "Meu Plantão com o crédito da Debora Sampaio, com foto e link pro perfil"),
            ("melhoria", "Comunidade: as laterais acompanham a página ao rolar, então dá pra ver tudo delas (favoritos, aniversariantes...) mesmo quando passam do tamanho da tela"),
            ("novo", "Rankings: ranking geral e por equipe (Suporte, Monitoramento e Serviços) em Produtos e Palminhas"),
            ("melhoria", "Central de Monitores: cliente ClienteO (PowerDocs), PowerDocs 2 e Graylog no Saas e PowerDocs de produção e homologação nos monitores da ClienteG"),
        ],
    },
    {
        "versao": "3.1", "data": "05/10/2026",
        "titulo": "Rankings, palminhas, férias no início e a equipe mais visível",
        "itens": [
            ("novo", "Rankings: aba Atribuir ranks pros administradores, por pessoa ou por produto, com um clique por nível"),
            ("novo", "Rankings: aba Meus produtos, com os seus produtos agrupados por nível"),
            ("melhoria", "Busca de cards no cabeçalho do início"),
            ("melhoria", "Rankings: quem só visualiza vê Produtos, Ranking geral e Meus produtos, sem poder alterar nada"),
            ("melhoria", "Insígnia de Rank Master por nível: a nova substitui a anterior, como a de tempo de casa"),
            ("melhoria", "Perfil: dá pra editar um cargo já lançado no histórico na empresa (cargo, área e período)"),
            ("melhoria", "Campanha PDA Beta User vai até 31/12/2026: depois disso a insígnia não pode mais ser conquistada"),
            ("novo", "Rankings: leaderboard de palminhas, com o top 10 de quem mais recebeu palminhas no mural"),
            ("melhoria", "Ranks por Produtos agora se chama Rankings, com os placares de produtos e de palminhas"),
            ("melhoria", "Rankings saiu do beta e foi pra aba Outros"),
            ("novo", "Usuário desativado no PDA aparece em vermelho no mural e no perfil, com aviso no sininho de todo mundo"),
            ("novo", "Início: bloco De férias na lateral, com quem está de férias ou de day off hoje pelo Calendário de Férias"),
            ("melhoria", "Indicadores Movidesk foi pra aba Outros, aberto pra todo mundo, e também virou uma aba do Indicadores Mensais"),
            ("melhoria", "Changelog: o detalhamento de cada era vem fechado e abre no clique"),
            ("novo", "Central de Monitores: produtos de cada servidor do Saas e do ClienteI na visão Infraestrutura; clicar num produto mostra onde ele roda"),
            ("novo", "Manutenção de Alertas em Banco aberta pra todo mundo: sem permissão, dá pra ver os alertas ativos e como estão configurados"),
            ("novo", "Foto de perfil aceita GIF animado"),
            ("melhoria", "Card da Central de Monitores com o crédito do Wagner Faria, com foto e link pro perfil"),
            ("melhoria", "Rankings: saíram a Visão por produto e as Últimas alterações (as alterações ficam no log Rankings, no card Logs)"),
            ("melhoria", "Horas Trabalhadas: a gerência fica fora do cálculo de horas (lista, metas e números da equipe)"),
        ],
    },
    {
        "versao": "3.0", "data": "04/10/2026",
        "titulo": "PDA v3 · o início vira o mural da equipe, com insígnias e ranks",
        "itens": [
            ("novo", "Início novo, com o mural da equipe: aniversários, promoções, insígnias conquistadas e quem chegou, com palminhas pra cada um"),
            ("novo", "Início: seus números ao entrar (horas e tickets do mês, tempo de casa e palminhas), aniversariantes do mês e as próximas insígnias de tempo de casa"),
            ("melhoria", "Início: menu à esquerda com Automações, Gestão de equipe (administradores), Outros e Em breve; favoritos viram atalhos e Automações tem busca"),
            ("melhoria", "Changelog por era: v3.x, v2.x e v1.x resumidos, com o detalhamento versão por versão da v3.x e da v2.x"),
            ("novo", "Colaborações no mural: quando duas ou mais pessoas fazem algo juntas, como a v3 publicada por Igor Leal e Debora Sampaio"),
            ("novo", "Feedbacks e alinhamentos feitos a mais de uma mão aparecem no mural pros autores e pros administradores responsáveis pelas equipes, com o time e o atalho pro registro"),
            ("novo", "Comentários em cada acontecimento do mural, além das palminhas"),
            ("novo", "Sininho de notificações no topo: palminhas, comentários e versão nova do PDA, com atalho pro changelog"),
            ("novo", "Início: as últimas promoções na lateral, abaixo dos aniversariantes"),
            ("novo", "Insígnia de Ferro pra quem tem menos de 1 ano de casa: um número novo a cada mês (de 1 a 11), até virar Bronze com 1 ano"),
            ("novo", "Gestão de equipe: escolha ver os indicadores de Suporte, de Monitoramento ou dos dois"),
            ("novo", "Campanhas: com mais de uma no ar, elas se revezam na lateral; sem campanha (ou com todas concluídas) aparece \"Nova campanha em breve\""),
            ("novo", "Parabéns com balões e confete pra quem faz aniversário, no primeiro acesso do dia"),
            ("novo", "Mural: aviso de tempo de casa a cada ano completo, em destaque no dia"),
            ("novo", "Quantos acessos o PDA já teve e o dia em que ele foi criado (05/08/2026), no changelog e no Sobre; a cada aniversário do PDA, todo mundo é avisado"),
            ("novo", "E-mail de apresentação da v3 pra todo mundo cadastrado no PDA"),
            ("melhoria", "Mural: a insígnia em destaque de cada pessoa aparece junto da foto"),
            ("novo", "Clique na foto de alguém (no mural ou no perfil) pra ver ela grande, com a insígnia em destaque e o atalho pro perfil"),
            ("novo", "Perfil dos colegas aberto pra todo mundo: cargo, equipe, entrada na empresa, aniversário, insígnias e histórico (sem indicadores, férias e feedbacks)"),
            ("novo", "Insígnia Bug Hunter, pra quem acha e reporta um bug no PDA, com campanha na lateral do início (os requisitos aparecem ao clicar)"),
            ("novo", "Igor e Debora concedem a Bug Hunter e a PDA Contributor direto no perfil; quem ganha fica sabendo pelo sininho"),
            ("novo", "Novo feedback ou alinhamento avisa no sininho quem recebe os e-mails da equipe, com o atalho pro registro"),
            ("novo", "Card Ranks por Produtos (em construção) e as insígnias de Rank Ouro (1, 3, 5, 7 e 10 produtos), já no perfil, bloqueadas por enquanto"),
            ("novo", "Ranks por Produtos (beta): bronze, prata, ouro e Master de cada pessoa em NFSe, NFCom, NFCe, NFe, AgenteNFCe, CTe, MDFe, NFAg, NF3e e CTe2, definidos pelos administradores"),
            ("novo", "Insígnias de Rank Master liberadas pelos ranks: 1, 3, 5, 7 e 10 produtos no Master"),
            ("novo", "Busca de cards no topo do início: ache qualquer card do painel sem ir até a seção (atalho: tecla /)"),
            ("novo", "Ranks por Produtos: leaderboard com pódio de quem tem mais produtos no Master (o ouro desempata)"),
            ("melhoria", "Changelog e Sobre o PDA também na lateral do início, abaixo de Promoções"),
            ("melhoria", "No início, o perfil fica só no cartão da lateral (o atalho do topo saiu)"),
            ("melhoria", "Horas Trabalhadas e Logs foram pra aba Outros"),
            ("melhoria", "Gestão de equipe aparece como Restrito pra quem não é administrador"),
            ("melhoria", "O aviso da v3 fica fixado no topo do mural"),
            ("melhoria", "Toda insígnia desbloqueada agora avisa a pessoa no sininho e aparece no mural, não só as concedidas à mão"),
            ("melhoria", "PDA Contributor também pra Igor Leal, Debora Sampaio, Eduardo Yamada e Sabrina Barros"),
            ("melhoria", "Feedbacks e alinhamentos no mural são só aviso, sem palminhas nem comentários"),
            ("melhoria", "Descrições das insígnias começando com letra maiúscula"),
            ("melhoria", "Campanha concluída continua na lateral com o selo \"Campanha concluída\" até acabar; dá pra ter mais de uma campanha ao mesmo tempo"),
            ("melhoria", "Palminhas: o indicador mostra recebidas e enviadas"),
            ("correcao", "Erros inesperados do servidor agora aparecem como mensagem na tela (e vão pro log) em vez de \"Failed to fetch\""),
            ("correcao", "Celular: o botão Sair não fica mais fora da tela"),
            ("removido", "Lateral \"Insígnias chegando\" do início, por enquanto"),
        ],
    },
    {
        "versao": "2.35", "data": "02/10/2026",
        "titulo": "Dash Financeiro e Manutenção de Usuários redesenhados",
        "itens": [
            ("melhoria", "Dash Financeiro: resumo do mês de referência no topo (gerados, pendentes e com problema) e o botão já diz quantos produtos faltam"),
            ("novo", "Dash Financeiro: barra de progresso ao vivo da geração, produto a produto, com o tempo decorrido e aviso quando termina"),
            ("melhoria", "Dash Financeiro: cada produto mostra o arquivo do mês (data e tamanho), quantos clientes vieram com dados, vazios ou com erro, e os últimos 12 meses"),
            ("novo", "Dash Financeiro: filtros Pendentes/Com problema, log da atualização na própria tela (pra quem vê logs) e confirmação antes de gerar"),
            ("novo", "Dash Financeiro: escolha o mês a gerar (seletor no topo ou clicando no mês da linha do tempo); gerar, gerar de novo e testar conexões usam o mês escolhido"),
            ("melhoria", "Manutenção de Usuários redesenhada: a lista de pessoas é a tela, com busca e filtros, e tudo de cada pessoa abre numa gaveta com abas (dados, acesso, Movidesk, sistemas, desativar)"),
            ("melhoria", "Manutenção de Usuários: novo usuário e desativação numa gaveta própria, com prévia dos alvos e confirmação; permissões em interruptores"),
            ("novo", "Feedbacks e Alinhamentos: equipe Serviços (aviso pra Eduardo e Sergio), já escolhida quando o registro é pra Edson ou Everton Tavares"),
            ("melhoria", "Feedbacks e Alinhamentos: a equipe Indústria Suporte agora se chama Suporte Indústria"),
            ("melhoria", "Feedbacks e Alinhamentos: cada registro só aparece pra quem recebe os e-mails da equipe dele (além de quem registrou e dos autores), na lista, no perfil e nos anexos; a gerência vê os de todas as equipes"),
            ("novo", "Card Reprocessamento CTe2, desenvolvido por Caio Peixoto, com permissão própria: acha CT-es parados e pede o reprocessamento pela API, com liga/pausa, sucessos, erros e liberação de chaves bloqueadas"),
            ("melhoria", "Central de Monitores: botão Monitores/Infraestrutura no topo; RabbitMQ, Graylog, FTP e servidores ficam numa visão própria, sem misturar com os monitores"),
            ("novo", "Insígnias no perfil, com uma em destaque junto da foto: tempo de casa (1 ano bronze, 2 prata, 3 ouro, 4 platina e diamante de 5 a 15 anos, uma insígnia por ano), PDA Dev/Founder e PDA Contributor"),
            ("novo", "Campanha PDA Beta User: ao entrar, quem ainda não tem a insígnia pode participar completando o perfil (foto, entrada na empresa, aniversário, e-mail e cargo) e já destacar a insígnia ganha"),
            ("melhoria", "Perfil: cada pessoa informa a própria data de entrada na empresa e monta o próprio histórico na empresa"),
            ("novo", "Ajuste da foto de perfil: zoom e arrastar pra enquadrar no círculo antes de salvar (no perfil e na campanha)"),
            ("correcao", "Campanha PDA Beta User: o mês do cargo era recusado sem dizer o porquê; agora tem \"desde que entrei\", só mostra meses válidos e aponta o erro no campo certo"),
            ("removido", "Card em construção Direcionamento Servidores"),
        ],
    },
    {
        "versao": "2.34", "data": "01/10/2026",
        "titulo": "Indicadores Mensais",
        "itens": [
            ("novo", "Card Indicadores Mensais, com permissão própria: o fechamento do mês no Movidesk numa tela só, por mês"),
            ("novo", "Avaliação de Efetividade: tickets do Monitoramento sem efetividade, marcados como Sim ou Não"),
            ("novo", "NOC Pendente: chamados com a primeira resposta fora do prazo, com a justificativa escolhida numa lista (grava ao escolher)"),
            ("novo", "Considerar/Desconsiderar Satisfação: pesquisas \"Insatisfeito\" do mês, com a descrição da insatisfação e filtro do que já foi marcado"),
            ("melhoria", "Número do ticket clicável, abrindo direto no Movidesk (Efetividade, NOC e Satisfação)"),
            ("melhoria", "Manutenção de Usuários: \"Sincronizar com Movidesk\" traz o cargo de cada pessoa vinculada pro PDA (lista, cabeçalho e perfil)"),
            ("melhoria", "Central de Monitores: etiqueta PRD/HML em cada monitor e filtro por ambiente; seção de infraestrutura em cada cliente"),
            ("novo", "Central de Monitores: monitores de homologação do Saas, NFSeR, cliente ClienteP, RabbitMQ e FTP, e servidores da ClienteJ e do ClienteI (clique copia o endereço)"),
            ("novo", "Feedbacks e Alinhamentos: escolha da equipe que recebe o aviso por e-mail (Monitoramento, Indústria Suporte, Suporte NFSe) e mais de um autor por registro"),
            ("melhoria", "Feedbacks e Alinhamentos: na edição dá pra mudar quem recebeu, os autores e a equipe"),
            ("melhoria", "Perfil: quem tem a permissão de Feedbacks vê ali mesmo os feedbacks e alinhamentos que a pessoa recebeu"),
            ("novo", "Quem entra com a senha padrão (SenhaInicial@1) é levado direto pra trocar a senha antes de usar o painel"),
            ("melhoria", "Feedbacks e Alinhamentos: anexo com área de clicar ou arrastar e o arquivo escolhido num cartão (trocar/remover)"),
            ("novo", "Changelog: histórico de tudo que veio antes da v2.29, em duas eras (v2.x e v1.x)"),
            ("melhoria", "Feedbacks e Alinhamentos redesenhado: lista em cartões com abas por tipo e o formulário numa gaveta lateral, em etapas"),
            ("melhoria", "Feedbacks e Alinhamentos: logins desativados e de teste não aparecem mais pra escolher"),
            ("melhoria", "Central de Monitores: clientes organizados pelo tamanho, em colunas equilibradas; servidores do Saas"),
            ("correcao", "Feedbacks e Alinhamentos: o botão Editar escondia o formulário inteiro"),
            ("correcao", "Feedbacks, Indicadores Mensais e Dashboards por Cliente voltam a mostrar o ícone da Empresa na aba do navegador"),
            ("melhoria", "Acesso sem porta no endereço (http://pda.local/ ou pelo IP) quando a porta 80 estiver liberada no servidor; o endereço com :8765 continua valendo"),
            ("removido", "Card em construção \"Considerar/Desconsiderar Pesquisa de Satisfação\", que virou o Indicadores Mensais"),
        ],
    },
    {
        "versao": "2.33", "data": "30/09/2026",
        "titulo": "Cards favoritos, aviso de falhas no Teams e diagnóstico do Dash Financeiro",
        "itens": [
            ("novo", "Favoritar cards: clique na estrela do card pra ele ir pro começo do painel (fica salvo pra você em qualquer computador)"),
            ("novo", "Aviso no Teams quando uma automação falha (e outro quando volta a funcionar)"),
            ("novo", "Dash Financeiro: botão \"Testar conexões\" por produto e busca de empresa nas bases, sem gerar arquivo"),
            ("novo", "Indicadores: Excel do período escolhido na tela com os tickets de todos os analistas, por organização e o detalhe de cada ticket"),
            ("melhoria", "Manutenção de Usuários: campo de gênero no cadastro e na edição (usado no Bem-vindo/Bem-vinda)"),
            ("melhoria", "Excel de horas (Perfil e Horas Trabalhadas): colunas Organização, Cliente e Categoria no Detalhe por Ticket"),
            ("correcao", "ClienteA volta a entrar no CTe do Dash Financeiro, usando a mesma conexão dos Relatórios ClienteA"),
            ("correcao", "Dash Financeiro: cliente que ficava de fora do arquivo sem aviso agora aparece no card com o motivo"),
            ("correcao", "Cada card do hub com a sua cor (Dash Financeiro tinha a mesma dos Relatórios ClienteA)"),
            ("correcao", "Card do hub não fica mais com a borda de cima cortada ao passar o mouse"),
            ("correcao", "Manutenção de Usuários: flag Administrador junto das permissões especiais, salva no mesmo botão, e a tela avisa se algo não gravou"),
            ("correcao", "Manutenção de Usuários: Feedbacks e Leitura de Logs abriam sempre desmarcadas e salvar as permissões tirava essas duas da pessoa"),
            ("correcao", "Central de Monitores: o produto selecionado no filtro não some mais no tema escuro; Publicador da ClienteH com o link novo"),
        ],
    },
    {
        "versao": "2.32", "data": "26/09/2026",
        "titulo": "Modo claro, Changelog e Relatórios ClienteA no SharePoint",
        "itens": [
            ("novo", "Modo claro em todas as telas, pelo botão de lua/sol na barra do topo (o escuro continua sendo o padrão)"),
            ("novo", "Changelog, aberto pra todo mundo, com o que mudou em cada versão"),
            ("novo", "ClienteA (CTe) incluída no Dash Financeiro"),
            ("novo", "Dash Financeiro: botão \"Gerar de novo\" por produto"),
            ("melhoria", "Dash Financeiro gera um arquivo por mês e mostra os clientes e os meses gerados de cada produto"),
            ("melhoria", "Tela de login e página Sobre com o resumo do PDA, os números e as áreas do painel"),
            ("melhoria", "Changelog e Sobre no rodapé de todas as telas, junto com a versão atual"),
            ("melhoria", "Telas proporcionais em monitor grande (2K e 4K) e com a mesma largura em todos os cards"),
            ("melhoria", "Relatório ClienteA é apagado do servidor depois de conferido no SharePoint, sem acumular no disco"),
            ("correcao", "Envio automático dos relatórios ClienteA pro SharePoint, agora na estrutura Ano/Mês/Dia"),
            ("correcao", "Quem tem a permissão de Feedbacks ou de Logs não perde mais o acesso ao entrar de novo"),
            ("correcao", "Tela de login com o mesmo aspecto em qualquer tamanho de monitor"),
            ("correcao", "Central de Monitores: ícone na aba do navegador"),
            ("removido", "Central de Monitores: botão \"?\" que não fazia nada"),
        ],
    },
    {
        "versao": "2.30", "data": "25/09/2026",
        "titulo": "Versão na tela de login e Central de Monitores completa",
        "itens": [
            ("novo", "Tela de login mostra a versão atual e a data da última atualização"),
            ("novo", "Novos monitores: ClienteD (NFSe), CTe 2 no Saas e ClienteI Demo"),
            ("melhoria", "Central de Monitores: logo de todos os clientes e botão Voltar pro hub"),
            ("correcao", "Links do ClienteI Enterprise e ClienteI Standard"),
        ],
    },
    {
        "versao": "2.29", "data": "24/09/2026",
        "titulo": "Central de Monitores",
        "itens": [
            ("novo", "ClienteI na Central de Monitores, com os ambientes Enterprise, Standard e ClienteAE"),
            ("melhoria", "Card \"Direcionamento WebMonitor's\" agora se chama Central de Monitores"),
            ("melhoria", "Logo da Empresa no card do Saas"),
        ],
    },
]


# Eras do PDA, uma por MAJOR, mais recente primeiro: é o que a página /changelog mostra
# (3.0.0.0). Cada era tem o resumo e os grupos por tema; a v3.x e a v2.x têm também o
# "Ver detalhamento", com as entradas de CHANGELOG_PDA da mesma MAJOR (o changelog por
# versão começa na v2.29). A v2.x antes da 2.29 e a v1.x foram reconstruídas do código, das
# pastas legadas (Alertas Consolidado, PainelAlertas) e do HANDOFF (2.34.9.0), sem datas.
# "icone" é uma chave de ICONES_HISTORICO. Ao fechar uma MINOR, vale olhar se o resumo e os
# grupos da era atual ainda contam a história; MAJOR nova = era nova aqui no começo.
HISTORICO_PDA = [
    {
        "versao": "3.x", "nome": "Painel da equipe", "periodo": "desde 02/10/2026", "cor": "#b0cb1c",
        # "lembranca" (3.3.1.0): o print da época e um texto de quem viu o PDA crescer
        "lembranca": {"print": "v3", "legenda": "A Comunidade em outubro de 2026",
                      "texto": "Lembra quando o PDA era só um título azul e um botão Entrar? Hoje ele abre com a foto de todo "
                               "mundo, aniversário, palminha, votação e até ranking. Virou o lugar onde a equipe se encontra "
                               "antes de começar o dia, e cada versão nova continua saindo do mesmo jeito: pedido no chat, "
                               "teste, changelog e zip."},
        "resumo": "Na v3 o PDA deixa de ser só uma grade de ferramentas e vira o lugar da equipe: quem entra "
                  "vê primeiro o que está acontecendo com as pessoas (aniversários, promoções, insígnias e "
                  "quem chegou), bate palminhas, acompanha os próprios números e acha as ferramentas num "
                  "menu organizado por seção.",
        "grupos": [
            {"titulo": "Mural da equipe", "icone": "pessoas", "itens": [
                "Linha do tempo com aniversários, promoções, insígnias e chegadas, tudo a partir do perfil de cada um",
                "Palminhas e comentários em cada acontecimento, com aviso no sininho",
                "Colaborações: o que duas ou mais pessoas fazem juntas, como publicar uma versão ou um alinhamento",
                "Aniversariantes do mês e as últimas promoções",
                "Comunidade: publicações com fotos, GIFs, arquivos e votação, e aviso no sininho quando é importante",
            ]},
            {"titulo": "Insígnias e ranks", "icone": "equipe", "itens": [
                "Insígnias novas: Ferro (meses de casa), Bug Hunter e Rank Master, cada uma avisando quem ganhou",
                "Rankings: bronze, prata, ouro e Master de cada pessoa por produto e o leaderboard de palminhas, no geral e por equipe",
                "Perfil dos colegas aberto, com a foto ampliada, as insígnias e o histórico na empresa",
            ]},
            {"titulo": "Início organizado", "icone": "painel", "itens": [
                "Seus números ao entrar: horas e tickets do mês, tempo de casa e palminhas",
                "Menu por seção: Automações, Gestão de equipe, Outros e Em breve",
                "Gestão de equipe com horas e tickets da equipe e quem está fora hoje",
            ]},
        ],
    },
    {
        "versao": "2.x", "nome": "Painel de Automações", "periodo": "v2.0 a v2.35", "cor": "#2db8cf",
        "lembranca": {"print": "v2", "legenda": "Os primeiros cards do painel",
                      "texto": "Foi aqui que o painel ganhou cara de painel: seis cards, metade ainda \"em construção\", "
                               "um \"Bem-vindo, igor\" em minúsculas e muita vontade de crescer. Cada card que saía da "
                               "construção era uma pequena festa, e os 6 viraram dezenas."},
        "resumo": "O Painel de Alertas ganhou um painel web: o mesmo programa passou a servir as telas pelo "
                  "navegador, com login e permissões por pessoa, e virou o lugar de quase toda a rotina do "
                  "Suporte e do Monitoramento: alertas, bancos, relatórios, indicadores e gestão da equipe. "
                  "Da v2.29 em diante cada versão ganhou o seu changelog, e a v2 terminou com o perfil "
                  "ganhando insígnias e a campanha PDA Beta User.",
        "grupos": [
            {"titulo": "Base do painel", "icone": "base", "itens": [
                "Painel web dentro do próprio programa, acessado pelo navegador na rede da VPN",
                "Login com sessão e permissões por pessoa, card a card",
                "Hub de cards com páginas, mostrando só o que cada pessoa pode usar",
                "Log de execução isolado por automação, numa tela própria",
                "Credenciais centralizadas num só arquivo e dados sensíveis cifrados",
            ]},
            {"titulo": "Monitoramento e alertas", "icone": "alerta", "itens": [
                "Os alertas da v1 viraram automações do painel, cada uma com a sua agenda",
                "Alertas Suporte (Legacy): status, próxima execução e \"Executar agora\" pelo navegador",
                "Contingências SEFAZ (SVC-AN e SVC-RS) por estado, com aviso no Teams",
                "Monitoramento EmailPack, agrupado por e-mail processado",
                "Central de Monitores: atalhos pros monitores de cada cliente, sem login, com visão de Infraestrutura",
                "Reprocessamento CTe2 (por Caio Peixoto) e aviso no Teams quando um job falha seguido",
            ]},
            {"titulo": "Bancos e relatórios", "icone": "banco", "itens": [
                "Manutenção de Alertas, Rejeições e Relatórios direto no banco, com busca em qualquer campo",
                "String Connections reutilizáveis por cliente e produto",
                "Relatórios ClienteA diários em Excel, com envio pro SharePoint",
                "Dash Financeiro mensal pro Power BI, um arquivo por mês, escolhendo o mês a gerar",
                "Dashboards por Cliente (Beta)",
            ]},
            {"titulo": "Equipe e Movidesk", "icone": "equipe", "itens": [
                "Horas Trabalhadas por analista, com escala, feriados, metas e Excel",
                "Indicadores Movidesk: escalonamentos, dúvidas e sincronização",
                "Automação Movidesk: controle de sincronização das integrações",
                "Indicadores Mensais: efetividade, NOC pendente e satisfação do mês",
                "Calendário de Férias e Meu Plantão",
                "Perfil de cada pessoa, com horas do mês e histórico na empresa",
            ]},
            {"titulo": "Pessoas e gestão", "icone": "pessoas", "itens": [
                "Manutenção de Usuários: cadastro e desativação nos bancos e no Movidesk",
                "Sincronização dos agentes do Movidesk, sem apagar ninguém",
                "Feedbacks e Alinhamentos individuais, em grupo ou gerais, com anexo e separados por equipe",
                "Insígnias no perfil e a campanha PDA Beta User",
                "E-mails automáticos de boas-vindas e de 45/90 dias de empresa, com a identidade do PDA",
            ]},
        ],
    },
    {
        "versao": "1.x", "nome": "Alertas e Painel de Alertas", "periodo": "antes do painel web", "cor": "#e8a33d",
        "lembranca": {"print": "v1", "legenda": "O Painel de Alertas no comecinho",
                      "texto": "Tudo começou assim: um fundo escuro, um título azul e um botão Entrar. Nada de mural, nada de "
                               "foto, nada de palminha. Só a vontade de não deixar nenhum alerta passar em branco."},
        "resumo": "Tudo começou com alertas separados, cada um um programa próprio que consultava o banco de hora "
                  "em hora e avisava por e-mail. Depois eles foram reunidos num painel de janela única, que "
                  "acabou virando a base do PDA.",
        "jornada": [
            ("Alertas separados", "um programa por alerta"),
            ("Painel de Alertas", "todos numa janela só"),
            ("Painel autocontido", "roda em qualquer máquina"),
            ("PDA v2", "painel web"),
        ],
        "grupos": [
            {"titulo": "Alertas independentes", "icone": "alerta", "itens": [
                "12 alertas, cada um com o seu executável, rodando de hora em hora e avisando por e-mail ao passar do limite",
                "Pendências FornecedorA NFSe, NFSe e NFe em status transitório, Manifestações e Retorno Personalizado",
                "Fila de E-mail, Fila de Processamento, CTe em Status 30, CTe Incompleto e CTe2 SaaS Status Inicial",
                "NFe Duplicidade e NFCe Inutilizadas",
            ]},
            {"titulo": "Biblioteca alerta_core", "icone": "base", "itens": [
                "Base comum pros alertas: cliente, consulta no banco, limite, tabela e e-mail",
                "Configuração de cada cliente e do e-mail em arquivos próprios",
                "Modelo pronto pra criar alerta novo",
            ]},
            {"titulo": "Relatório gerencial de horas", "icone": "equipe", "itens": [
                "Horas por analista no mês, a partir do Movidesk e da escala de cada um",
                "Planilha Excel com destaques, enviada por e-mail",
            ]},
            {"titulo": "Painel de Alertas", "icone": "painel", "itens": [
                "Todos os alertas num processo só, numa janela escura com status, agenda e log",
                "Botão \"Executar agora\" por alerta e agendas diferentes (dias úteis, de 30 em 30 minutos...)",
                "Validação FTP como primeira automação fora do padrão dos alertas",
                "Versão autocontida: copiar a pasta e rodar, sem instalar nada no servidor",
            ]},
        ],
    },
]


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
        definir_url_painel(self.url_web)  # botão "Abrir no PDA" dos avisos de falha no Teams

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

        # Relatório ClienteA automático - roda uma vez por dia junto com os
        # outros alertas (mesmo agendador global, mesma thread), sem
        # precisar de uma thread própria.
        schedule.every().day.at(HORARIO_RELATORIO_CLIENTE_A_AUTOMATICO).do(_executar_relatorio_cliente_a_diario)

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

        # só roda ciclos enquanto estiver ligado no card (começa pausado)
        self.monitor_reprocessamento_cte2 = MonitorReprocessamentoCte2()
        self.monitor_reprocessamento_cte2.iniciar()

        # LongNameJanitor ClienteQ (3.3.2.0): também começa pausado e em modo simulação
        self.monitor_longnamejanitor = MonitorLongNameJanitor()
        self.monitor_longnamejanitor.iniciar()

        # Monitoramento de Consumo Indevido (beta, 3.4.3.0): só verifica enquanto estiver ligado no card (começa desligado)
        self.monitor_consumo_indevido = MonitorConsumoIndevido()
        self.monitor_consumo_indevido.iniciar()

        # NNU 20 → 15 (beta, 3.4.9.0): começa pausado e em simulação; o lote aberto é acompanhado mesmo pausado
        self.monitor_nnu_status = MonitorNnuStatus()
        self.monitor_nnu_status.iniciar()

        # Manutenção dos logs (3.4.8.0; antes, 3.2.1.0, só apagava os parados há 30 dias): na partida (numa thread,
        # pra não atrasar a janela) e todo dia de madrugada
        threading.Thread(target=_limpar_logs_antigos, daemon=True, name="limpeza_logs").start()
        schedule.every().day.at(HORARIO_LIMPEZA_LOGS).do(_limpar_logs_antigos)

        try:
            _migrar_fotos_iniciais_perfil()
        except Exception:
            logger.exception("Falha ao migrar fotos iniciais de perfil")

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
            conteudo_rodape, text="Desenvolvido por", bg=BG_PANEL, fg=FG_DIM,
            font=("Segoe UI", 8),
        ).pack(side="left")
        tk.Label(
            conteudo_rodape, text="Igor Leal", bg=BG_PANEL, fg=ACCENT,
            font=("Segoe UI", 8, "bold"),
        ).pack(side="left", padx=(4, 0))
        tk.Label(
            conteudo_rodape, text="e", bg=BG_PANEL, fg=FG_DIM, font=("Segoe UI", 8),
        ).pack(side="left", padx=4)
        tk.Label(
            conteudo_rodape, text="Debora Sampaio", bg=BG_PANEL, fg=LIME,
            font=("Segoe UI", 8, "bold"),
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
