"""Dash Financeiro - lógica (consultas, geração dos CSVs mensais, status, agendamento).

Separado do alertas_gui.py em 26/09/2026. As rotas web (/dash-financeiro, /api/dash-financeiro/*)
continuam no alertas_gui.py e usam o que está aqui. Pra saber se tem execução rodando ou
ligar a trava, use execucao_ativa() / tentar_iniciar_execucao() - nunca a variável direto.
"""
import json
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import pandas as pd
import pyodbc
from dateutil.relativedelta import relativedelta

from core.config_seguro import obter_valor_config as _obter_valor_config
from nucleo.avisos_falha import registrar_resultado as registrar_resultado_job
from nucleo.caminhos import base_path_app as _base_path_app

# mesmo logger configurado no alertas_gui.py (o logging devolve o mesmo objeto pelo nome)
logger_dash_financeiro = logging.getLogger("alertas.dash_financeiro")


# ---------------------------------------------------------------------------
# Atualização Dash Financeiro - adaptado do notebook
# Atualizacao_Dash_Financeiro.ipynb que o Igor mandou. Pra cada produto
# (NFe, CTe, NFCe, CFe, NFSe Out, NFSe In, MDFe, ClienteK, SaaS), gera um CSV
# mensal com a contagem de documentos por cliente/CNPJ, salvando em
# C:\\Empresa\\Power BI\\Financeiro\\<Produto>\\. Idempotente por mês - se o
# CSV do mês já existir, não faz nada (mesmo comportamento do notebook
# original). As credenciais de banco (23 combinações distintas de
# servidor+banco) são cifradas no config.dat - ver Configurações
# Seguras/CRIPTOGRAFIA.md - não tem fallback pra texto puro porque essa
# automação nasce já protegida, não veio de um .env antigo.
# ---------------------------------------------------------------------------


PASTA_BASE_DASH_FINANCEIRO = r"C:\Empresa\Power BI\Financeiro"

# nome da pasta de saída de cada produto - a maioria bate com a chave do
# JSON, só NFSeOut/NFSeIn que têm espaço no nome da pasta de verdade
# (confirmado no print que o Igor mandou: "NFSe In", "NFSe Out")
NOME_PASTA_POR_PRODUTO = {
    "NFe": "NFe", "CTe": "CTe", "NFCe": "NFCe", "CFe": "CFe",
    "NFSeOut": "NFSe Out", "NFSeIn": "NFSe In", "MDFe": "MDFe",
    "ClienteK": "ClienteK", "SaaS": "SaaS",
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


def _credencial_reaproveitada(server: str, database: str) -> Optional[tuple]:
    """(usuário, senha) de uma conexão que o PDA já usa em outro card pro
    MESMO servidor e banco. Hoje: a base da ClienteA (cliente_a_cte_prd), que os
    Relatórios ClienteA já acessam - o Dash usa a mesma conexão em vez de pedir
    outra senha (28/09/2026: sem isso a ClienteA ficava de fora do CTe)."""
    from areas.relatorios_cliente_a.logica import _config_cliente_a  # import aqui: só precisa quando falta a senha própria
    cfg = _config_cliente_a()
    mesmo_banco = (cfg.get("database") or "").lower() == database.lower()
    mesmo_servidor = (cfg.get("server") or "").lower() == server.lower()
    if mesmo_banco and mesmo_servidor and cfg.get("username") and cfg.get("password"):
        return cfg["username"], cfg["password"]
    return None


def _conectar_dash_financeiro(server: str, database: str, uid: str):
    senha = _obter_senha_dash_financeiro(database)
    if not senha:
        reaproveitada = _credencial_reaproveitada(server, database)
        if reaproveitada:
            uid, senha = reaproveitada
            logger_dash_financeiro.info("Dash Financeiro: '%s' usando a mesma conexão dos Relatórios ClienteA.", database)
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


def _periodo_mes_anterior(mes: Optional[str] = None):
    """Mesmo cálculo do notebook: mês anterior completo (do dia 1 ao
    último dia). Desde a 2.35.1.0 aceita um mês escolhido na tela
    ("AAAA-MM", validado por validar_mes_dash_financeiro); sem ele, o
    mês anterior (o que a geração automática do dia 1 usa)."""
    if mes:
        data_ini = datetime.strptime(mes, "%Y-%m")
    else:
        data_ini = (datetime.today().replace(day=1) - relativedelta(months=1)).replace(day=1)
    data_fim = data_ini + relativedelta(months=1) - relativedelta(days=1)
    return {
        "arquivo": data_ini.strftime("%Y-%m"),
        "ini": data_ini.strftime("%Y-%m-%d"),
        "fim": data_fim.strftime("%Y-%m-%d"),
        "ini_compacto": data_ini.strftime("%Y%m%d"),  # usado só pelo CFe (formato diferente na query)
        "fim_compacto": data_fim.strftime("%Y%m%d"),
    }


MES_MAIS_ANTIGO_DASH_FINANCEIRO = "2020-01"


def validar_mes_dash_financeiro(mes) -> Optional[str]:
    """Mês vindo da tela: "AAAA-MM" entre MES_MAIS_ANTIGO_DASH_FINANCEIRO e o
    mês anterior (o mês corrente ainda não fechou, e a geração conta o mês
    inteiro). Devolve o mês limpo, None se vazio (= mês anterior) ou levanta
    ValueError com a mensagem pra tela."""
    mes = (mes or "").strip()
    if not mes:
        return None
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", mes):
        raise ValueError("Mês inválido (use AAAA-MM).")
    if mes < MES_MAIS_ANTIGO_DASH_FINANCEIRO:
        raise ValueError(f"Mês muito antigo (o mais antigo é {MES_MAIS_ANTIGO_DASH_FINANCEIRO}).")
    if mes > _periodo_mes_anterior()["arquivo"]:
        raise ValueError("Só dá pra gerar meses já fechados (até o mês anterior).")
    return mes


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


def _query_cliente_k(periodo: dict) -> str:
    data_sql = datetime.strptime(periodo["ini"], "%Y-%m-%d").strftime("%m/%Y")
    return f"""
    SELECT
      'ClienteK' as Cliente,
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
# Out, NFSe In, MDFe), e um tratamento especial pro ClienteK (conexão única,
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


def _variacoes_produto(produto: str) -> list:
    """(tipo, proces) de cada consulta do produto: NFe/CTe consultam Emissão e
    Recebimento; os outros têm uma consulta só (None, None)."""
    if produto in PRODUTOS_COM_TIPO_PROCES:
        info = PRODUTOS_COM_TIPO_PROCES[produto]
        return list(zip(info["tipos"], info["proces"]))
    return [(None, None)]


def _sql_produto(produto: str, conexao_cfg: dict, tipo, proces, periodo: dict) -> str:
    if produto in PRODUTOS_COM_TIPO_PROCES:
        query_fn = PRODUTOS_COM_TIPO_PROCES[produto]["query_fn"]
        return query_fn(conexao_cfg["cliente"], conexao_cfg["cnpj"], tipo, proces, periodo)
    return PRODUTOS_QUERY_UNICA[produto](conexao_cfg["cliente"], conexao_cfg["cnpj"], periodo)


def _consultar_conexao(produto: str, conexao_cfg: dict, periodo: dict) -> tuple:
    """Roda as consultas do mês numa conexão (uma por tipo) e devolve
    (dataframes, resumo). O resumo diz o que aconteceu com esse cliente:
    linhas e documentos trazidos, ou o erro - antes a geração só contava
    "N conexão(ões) com erro" e um cliente podia sumir do CSV sem ninguém
    saber qual nem por quê (foi o caso da ClienteA no CTe). Usada pela geração
    e pelo "Testar conexões", então o teste roda exatamente a mesma consulta."""
    resumo = {"cliente": conexao_cfg.get("cliente") or "?", "database": conexao_cfg.get("database") or "?",
              "linhas": 0, "documentos": 0, "erro": None}
    dataframes, erros = [], []
    try:
        conn = _conectar_dash_financeiro(conexao_cfg["server"], conexao_cfg["database"], conexao_cfg["uid"])
    except Exception as e:
        resumo["erro"] = f"não conectou: {e}"
        return dataframes, resumo
    try:
        for tipo, proces in _variacoes_produto(produto):
            try:
                df = pd.read_sql(_sql_produto(produto, conexao_cfg, tipo, proces, periodo), conn)
                dataframes.append(df)
                resumo["linhas"] += len(df)
                if "QTD" in df.columns and len(df):
                    resumo["documentos"] += int(pd.to_numeric(df["QTD"], errors="coerce").fillna(0).sum())
            except Exception as e:
                erros.append(f"{tipo}: {e}" if tipo else str(e))
    finally:
        conn.close()
    if erros:
        resumo["erro"] = "consulta falhou: " + "; ".join(erros)
    return dataframes, resumo


def _executar_produto_padrao(produto: str, conexoes: list, forcar: bool = False, mes: Optional[str] = None) -> dict:
    """Produtos com lista de conexões (NFe, CTe, NFCe, CFe, NFSe Out,
    NFSe In, MDFe). Uma conexão com erro não derruba as outras - só é
    pulada e reportada no resumo (mesma robustez que o notebook original
    já tinha pro NFSe Out, aplicada em todos aqui)."""
    periodo = _periodo_mes_anterior(mes)
    pasta_saida = _caminho_saida_produto(produto)
    arquivo_mes = os.path.join(pasta_saida, f"{periodo['arquivo']}.csv")

    if os.path.exists(arquivo_mes) and not forcar:
        return {"ok": True, "pulado": True, "motivo": f"{periodo['arquivo']}.csv já existe"}

    os.makedirs(pasta_saida, exist_ok=True)

    erro_permissao = _verificar_permissao_escrita(pasta_saida)
    if erro_permissao:
        return {"ok": False, "erro": erro_permissao}

    todos_dados = []
    erros = []
    por_conexao = []  # resumo de cada cliente, mostrado no card (quem trouxe dados, quem falhou e por quê)

    for conexao_cfg in conexoes:
        dataframes, resumo = _consultar_conexao(produto, conexao_cfg, periodo)
        todos_dados.extend(dataframes)
        por_conexao.append(resumo)
        if resumo["erro"]:
            erros.append(f"{resumo['cliente']} ({resumo['database']}): {resumo['erro']}")
            logger_dash_financeiro.warning(
                "Dash Financeiro (%s): erro ao consultar %s: %s", produto, resumo["cliente"], resumo["erro"],
            )
        elif not resumo["linhas"]:
            logger_dash_financeiro.warning(
                "Dash Financeiro (%s): %s conectou, mas não trouxe nenhuma linha em %s.",
                produto, resumo["cliente"], periodo["arquivo"],
            )

    if not todos_dados:
        return {"ok": False, "erro": "Nenhuma consulta retornou dados.", "erros_individuais": erros,
                "por_conexao": por_conexao}

    df_mensal = pd.concat(todos_dados, ignore_index=True)
    erro_gravacao = _salvar_csv_com_retentativa(df_mensal, arquivo_mes)
    if erro_gravacao:
        return {"ok": False, "erro": erro_gravacao, "erros_individuais": erros, "por_conexao": por_conexao}

    return {
        "ok": True, "pulado": False, "linhas": len(df_mensal),
        "conexoes_com_erro": len(erros), "erros_individuais": erros, "por_conexao": por_conexao,
    }


def _executar_cliente_k(conexoes: list, forcar: bool = False, mes: Optional[str] = None) -> dict:
    periodo = _periodo_mes_anterior(mes)
    pasta_saida = _caminho_saida_produto("ClienteK")
    arquivo_mes = os.path.join(pasta_saida, f"{periodo['arquivo']}.csv")

    if os.path.exists(arquivo_mes) and not forcar:
        return {"ok": True, "pulado": True, "motivo": f"{periodo['arquivo']}.csv já existe"}

    os.makedirs(pasta_saida, exist_ok=True)

    erro_permissao = _verificar_permissao_escrita(pasta_saida)
    if erro_permissao:
        return {"ok": False, "erro": erro_permissao}

    cfg = conexoes[0]
    conn = _conectar_dash_financeiro(cfg["server"], cfg["database"], cfg["uid"])
    try:
        df_mensal = pd.read_sql(_query_cliente_k(periodo), conn)
    finally:
        conn.close()

    erro_gravacao = _salvar_csv_com_retentativa(df_mensal, arquivo_mes)
    if erro_gravacao:
        return {"ok": False, "erro": erro_gravacao}


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
            AND NOT PRE_CPF_CNPJ = '92348594394719'
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


def _executar_saas(conexao_base: dict, forcar: bool = False, mes: Optional[str] = None) -> dict:
    """Caso especial: 1 servidor/usuário, 7 bancos diferentes (um por
    produto), 7 queries fixas (não filtra por 'cliente' como os outros -
    já vem com o Grupo de Acesso certo direto da query). Reaproveita as
    MESMAS chaves de senha em config.dat que os outros produtos já usam
    pra esses bancos (dash_financeiro::<banco>), não precisa cadastrar
    de novo."""
    periodo = _periodo_mes_anterior(mes)
    pasta_saida = _caminho_saida_produto("SaaS")
    arquivo_mes = os.path.join(pasta_saida, f"{periodo['arquivo']}.csv")

    if os.path.exists(arquivo_mes) and not forcar:
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


    return {
        "ok": True, "pulado": False, "linhas": len(df_produtos),
        "conexoes_com_erro": len(erros), "erros_individuais": erros,
    }


NOME_DF_CONSOLIDADO_ANTIGO = "df_consolidado.csv"


def _separar_df_consolidado_em_meses(produto: str) -> dict:
    """O Dash Financeiro gera só um CSV por mês (AAAA-MM.csv) desde a
    2.32.1.0 - pedido do Igor pra acabar com o df_consolidado.csv. O
    histórico que só existia dentro do consolidado (meses de antes da
    automação) é separado aqui em arquivos por mês, usando a coluna "Data"
    (MM/AAAA). Nunca sobrescreve um AAAA-MM.csv que já existe (o arquivo do
    mês é a fonte de verdade) e nunca mexe no consolidado em si: ele fica na
    pasta, parado, até o Igor apontar o Power BI pros arquivos por mês e
    apagá-lo. Idempotente - roda antes de cada geração."""
    pasta = _caminho_saida_produto(produto)
    caminho = os.path.join(pasta, NOME_DF_CONSOLIDADO_ANTIGO)
    resultado = {"criados": [], "ja_existiam": [], "linhas_sem_data": 0}
    if not os.path.isfile(caminho):
        return resultado
    try:
        # dtype=str: CNPJ com zero à esquerda não pode virar número
        df = pd.read_csv(caminho, dtype=str)
    except Exception as e:
        logger_dash_financeiro.warning("Dash Financeiro (%s): não deu pra ler o %s antigo: %s",
                                       produto, NOME_DF_CONSOLIDADO_ANTIGO, e)
        return resultado
    if "Data" not in df.columns:
        logger_dash_financeiro.warning("Dash Financeiro (%s): %s sem coluna Data, histórico não separado.",
                                       produto, NOME_DF_CONSOLIDADO_ANTIGO)
        return resultado
    datas = df["Data"].fillna("").str.strip()
    validas = datas.str.fullmatch(r"\d{2}/\d{4}")
    resultado["linhas_sem_data"] = int((~validas).sum())
    for data_mes in sorted(datas[validas].unique()):
        mes, ano = data_mes.split("/")
        destino = os.path.join(pasta, f"{ano}-{mes}.csv")
        if os.path.exists(destino):
            resultado["ja_existiam"].append(f"{ano}-{mes}")
            continue
        erro = _salvar_csv_com_retentativa(df[datas == data_mes], destino)
        if erro:
            logger_dash_financeiro.warning("Dash Financeiro (%s): %s", produto, erro)
            continue
        resultado["criados"].append(f"{ano}-{mes}")
    if resultado["criados"]:
        logger_dash_financeiro.info("Dash Financeiro (%s): histórico do %s separado em %d arquivo(s) por mês: %s.",
                                    produto, NOME_DF_CONSOLIDADO_ANTIGO, len(resultado["criados"]),
                                    ", ".join(resultado["criados"]))
    return resultado


# produtos com lista de conexões por cliente (os que dá pra testar cliente a cliente)
PRODUTOS_TESTAVEIS = [p for p in ("NFe", "CTe", "NFCe", "CFe", "NFSeOut", "NFSeIn", "MDFe")
                      if p in PRODUTOS_COM_TIPO_PROCES or p in PRODUTOS_QUERY_UNICA]


def testar_conexoes_dash_financeiro(produto: str, conexoes_json: dict, mes: Optional[str] = None) -> dict:
    """Roda a MESMA consulta da geração em cada cliente do produto, sem gravar
    nada, e diz o que aconteceu com cada um (conectou? quantas linhas e
    documentos no mês? qual o erro?). Pra descobrir na hora por que um
    cliente não aparece no CSV, sem precisar ler o log da remota."""
    if produto not in PRODUTOS_TESTAVEIS:
        return {"ok": False, "erro": f"{produto} não tem teste por cliente."}
    conexoes = conexoes_json.get(produto) or []
    if not isinstance(conexoes, list) or not conexoes:
        return {"ok": False, "erro": f"Nenhum cliente de {produto} no dash_financeiro_conexoes.json desta máquina."}
    periodo = _periodo_mes_anterior(mes)
    with ThreadPoolExecutor(max_workers=6) as executor:
        resultados = list(executor.map(lambda cfg: _consultar_conexao(produto, cfg, periodo)[1], conexoes))
    return {"ok": True, "produto": produto, "mes": periodo["arquivo"], "conexoes": resultados}


# colunas que nunca aparecem na busca (empresas pode guardar senha de certificado etc.)
_COLUNA_SENSIVEL_BUSCA = re.compile(r"senha|password|pwd|token|segredo|secret|chave|key|certificado|pfx|hash|salt", re.I)
# colunas mostradas no resultado: o que identifica a empresa e o grupo dela
_COLUNA_IDENTIFICACAO_BUSCA = re.compile(r"^(id|cnpj)$|nome|razao|fantasia|descri|grupo", re.I)
_TIPOS_TEXTO_SQL = ("varchar", "nvarchar", "char", "nchar")


def _nome_sql(nome: str) -> str:
    return "[" + nome.replace("]", "]]") + "]"


def _procurar_empresa_na_base(conn, termo: str) -> list:
    """Procura o termo nas tabelas de empresas/grupos da base (achadas pelo
    INFORMATION_SCHEMA, sem supor nome de coluna). Só leitura, termo sempre
    como parâmetro. Devolve, por tabela, as colunas de identificação das
    linhas encontradas (no máximo 20)."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE UPPER(TABLE_NAME) = 'EMPRESAS' OR UPPER(TABLE_NAME) LIKE 'GRUPO%EMPRESA%' "
        "ORDER BY TABLE_NAME, ORDINAL_POSITION"
    )
    tabelas = {}
    for schema, tabela, coluna, tipo in cursor.fetchall():
        tabelas.setdefault((schema, tabela), []).append((coluna, (tipo or "").lower()))
    achados = []
    for (schema, tabela), colunas in tabelas.items():
        texto = [c for c, t in colunas if t in _TIPOS_TEXTO_SQL and not _COLUNA_SENSIVEL_BUSCA.search(c)]
        mostrar = [c for c, _ in colunas if _COLUNA_IDENTIFICACAO_BUSCA.search(c) and not _COLUNA_SENSIVEL_BUSCA.search(c)][:8]
        if not texto or not mostrar:
            continue
        sql = (f"SELECT TOP 20 {', '.join(_nome_sql(c) for c in mostrar)} "
               f"FROM {_nome_sql(schema)}.{_nome_sql(tabela)} WITH (NOLOCK) WHERE "
               + " OR ".join(f"{_nome_sql(c)} LIKE ?" for c in texto))
        cursor.execute(sql, [f"%{termo}%"] * len(texto))
        linhas = [["" if v is None else str(v)[:120] for v in linha] for linha in cursor.fetchall()]
        achados.append({"tabela": f"{schema}.{tabela}", "colunas": mostrar, "linhas": linhas})
    return achados


def procurar_empresa_dash_financeiro(produto: str, conexoes_json: dict, termo: str) -> dict:
    """Procura uma empresa pelo nome (ou CNPJ) em cada base já cadastrada no
    produto - ex.: achar em qual base e em qual grupo (GRUPO_EMPRESA_FK) a
    ClienteA está, pra montar o filtro igual ao dos outros clientes."""
    termo = (termo or "").strip()
    if not 2 <= len(termo) <= 60:
        return {"ok": False, "erro": "Digite de 2 a 60 caracteres pra procurar."}
    conexoes = conexoes_json.get(produto) or []
    if produto not in PRODUTOS_TESTAVEIS or not isinstance(conexoes, list):
        return {"ok": False, "erro": f"{produto} não tem busca por empresa."}
    bases = {}
    for cfg in conexoes:
        chave = (cfg.get("server"), cfg.get("database"), cfg.get("uid"))
        bases.setdefault(chave, []).append(cfg.get("cliente") or "?")

    def _procurar(item):
        (server, database, uid), clientes = item
        resultado = {"database": database, "clientes": clientes, "tabelas": [], "erro": None}
        try:
            conn = _conectar_dash_financeiro(server, database, uid)
            try:
                resultado["tabelas"] = _procurar_empresa_na_base(conn, termo)
            finally:
                conn.close()
        except Exception as e:
            resultado["erro"] = str(e)
        return resultado

    with ThreadPoolExecutor(max_workers=6) as executor:
        resultados = list(executor.map(_procurar, bases.items()))
    return {"ok": True, "termo": termo, "bases": resultados}


def _clientes_dash_financeiro(produto: str, conexoes_json: dict) -> list:
    """Nomes que aparecem no card de cada produto na tela (o que entra na
    geração). SaaS não filtra por cliente - lista os bancos consultados."""
    cfg = conexoes_json.get(produto)
    if produto == "SaaS" and isinstance(cfg, dict):
        return [f"banco {b}" for b in cfg.get("bancos", [])]
    if isinstance(cfg, list):
        vistos = []
        for c in cfg:
            nome = c.get("cliente") or c.get("database", "?")
            if nome not in vistos:
                vistos.append(nome)
        return vistos
    return []


def _meses_gerados_dash_financeiro(produto: str) -> list:
    pasta = _caminho_saida_produto(produto)
    try:
        return sorted(f[:-4] for f in os.listdir(pasta) if re.fullmatch(r"\d{4}-\d{2}\.csv", f))
    except OSError:
        return []


def executar_produto_dash_financeiro(produto: str, conexoes_json: dict, forcar: bool = False,
                                     mes: Optional[str] = None) -> dict:
    """Ponto de entrada único - roteia pro tratamento certo de acordo com
    o produto. `forcar=True` gera de novo o CSV do mês mesmo se ele já
    existir (seguro desde a 2.32.1.0: sem df_consolidado, sobrescrever o
    arquivo do mês não duplica nada). Antes de gerar, separa o histórico do
    df_consolidado antigo em arquivos por mês (ver
    _separar_df_consolidado_em_meses)."""
    try:
        _separar_df_consolidado_em_meses(produto)
        if produto == "ClienteK":
            return _executar_cliente_k(conexoes_json["ClienteK"], forcar, mes)
        elif produto == "SaaS":
            return _executar_saas(conexoes_json["SaaS"], forcar, mes)
        elif produto in conexoes_json:
            return _executar_produto_padrao(produto, conexoes_json[produto], forcar, mes)
        else:
            return {"ok": False, "erro": f"Produto '{produto}' não reconhecido."}
    except Exception as e:
        logger_dash_financeiro.exception("Erro inesperado no Dash Financeiro (%s)", produto)
        return {"ok": False, "erro": str(e)}


ORDEM_PRODUTOS_DASH_FINANCEIRO = [
    "NFe", "CTe", "NFCe", "CFe", "NFSeOut", "NFSeIn", "MDFe", "ClienteK", "SaaS",
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

# andamento da rodada atual, pra tela mostrar a barra de progresso (2.35.0.0):
# quais produtos entram nela, quais já terminaram e desde quando cada um roda
_progresso_execucao: dict = {"inicio": None, "produtos": [], "concluidos": [], "inicio_produto": {}, "mes": None}


def progresso_execucao() -> dict:
    """Cópia do andamento da rodada atual (vazio se nada estiver rodando)."""
    with _lock_dash_financeiro:
        return {
            "inicio": _progresso_execucao["inicio"],
            "produtos": list(_progresso_execucao["produtos"]),
            "concluidos": list(_progresso_execucao["concluidos"]),
            "inicio_produto": dict(_progresso_execucao["inicio_produto"]),
            "mes": _progresso_execucao["mes"],
        }


def info_arquivo_mes(produto: str, mes: Optional[str] = None) -> Optional[dict]:
    """Tamanho e data do CSV do mês (escolhido ou o anterior) desse produto, ou None se não existir."""
    caminho = os.path.join(_caminho_saida_produto(produto), f"{_periodo_mes_anterior(mes)['arquivo']}.csv")
    try:
        return {
            "tamanho": os.path.getsize(caminho),
            "modificado": datetime.fromtimestamp(os.path.getmtime(caminho)).strftime("%d/%m/%Y %H:%M"),
        }
    except OSError:
        return None


def proxima_execucao_automatica() -> str:
    """Quando a geração automática roda de novo (todo dia 1 no HORARIO_DASH_FINANCEIRO_AUTOMATICO)."""
    agora = datetime.now()
    hora, minuto = (int(x) for x in HORARIO_DASH_FINANCEIRO_AUTOMATICO.split(":"))
    dia_1_no_horario = agora.replace(day=1, hour=hora, minute=minuto, second=0, microsecond=0)
    if agora.day == 1 and agora < dia_1_no_horario:
        return dia_1_no_horario.strftime("%d/%m/%Y %H:%M")
    return (dia_1_no_horario + relativedelta(months=1)).strftime("%d/%m/%Y %H:%M")


def execucao_ativa() -> bool:
    """Se tem uma rodada do Dash Financeiro em andamento agora."""
    return _dash_financeiro_execucao_ativa


def tentar_iniciar_execucao() -> bool:
    """Liga a trava de execução se ela estiver livre (verifica e liga de uma vez,
    sob o lock). Devolve False se já tinha execução rodando. Existe porque a trava
    mora neste módulo: as rotas do alertas_gui.py não podem mais fazer
    "global _dash_financeiro_execucao_ativa" - isso mudaria uma cópia de lá, não a
    daqui, e a proteção contra execução dupla deixaria de funcionar em silêncio."""
    global _dash_financeiro_execucao_ativa
    with _lock_dash_financeiro:
        if _dash_financeiro_execucao_ativa:
            return False
        _dash_financeiro_execucao_ativa = True
        return True


def _status_disco_produto(produto: str, mes: Optional[str] = None) -> Optional[dict]:
    """Monta um status "sintético" a partir do que já está salvo em
    disco, pra quando a sessão atual ainda não processou esse produto
    (por exemplo, logo depois de reiniciar o programa). Sem isso, a tela
    mostraria "nunca rodou" pra produtos que, na verdade, já têm o CSV do
    mês certinho - só que salvo numa execução de uma sessão anterior.
    Devolve None só se REALMENTE nunca gerou nada pra esse produto."""
    pasta = _caminho_saida_produto(produto)
    if not os.path.isdir(pasta):
        return None

    periodo_atual = _periodo_mes_anterior(mes)
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


def _executar_todos_dash_financeiro(produtos: Optional[list] = None, forcar: bool = False,
                                    mes: Optional[str] = None) -> dict:
    """Roda os produtos em sequência (todos, ou só os de `produtos`),
    atualizando o status de cada um conforme vai processando (a tela web
    consulta esse status a qualquer momento, mesmo com a execução ainda em
    andamento). `forcar` gera de novo o mês mesmo se o CSV já existir.
    `mes` ("AAAA-MM", já validado) gera esse mês em vez do anterior (2.35.1.0)."""
    global _dash_financeiro_execucao_ativa
    conexoes_json = _carregar_conexoes_dash_financeiro()
    resumo = {}
    da_rodada = list(produtos or ORDEM_PRODUTOS_DASH_FINANCEIRO)
    try:
        _dash_financeiro_execucao_ativa = True
        with _lock_dash_financeiro:
            _progresso_execucao.update(inicio=time.time(), produtos=da_rodada, concluidos=[], inicio_produto={},
                                       mes=_periodo_mes_anterior(mes)["arquivo"])
        for produto in da_rodada:
            inicio_produto = time.time()
            with _lock_dash_financeiro:
                _produtos_em_execucao.add(produto)
                _progresso_execucao["inicio_produto"][produto] = inicio_produto
            try:
                logger_dash_financeiro.info("Dash Financeiro: iniciando %s (%s)...", produto, _periodo_mes_anterior(mes)["arquivo"])
                resultado = executar_produto_dash_financeiro(produto, conexoes_json, forcar, mes)
                resumo[produto] = resultado
                with _lock_dash_financeiro:
                    estado_dash_financeiro[produto] = {
                        **resultado,
                        "executado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                        "duracao_s": round(time.time() - inicio_produto),
                        "mes": _periodo_mes_anterior(mes)["arquivo"],
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
                    _progresso_execucao["concluidos"].append(produto)
    finally:
        _dash_financeiro_execucao_ativa = False
        with _lock_dash_financeiro:
            _progresso_execucao.update(inicio=None, produtos=[], concluidos=[], inicio_produto={}, mes=None)
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
    resumo = _executar_todos_dash_financeiro()
    # só a execução automática avisa no Teams (a manual quem disparou já vê na tela)
    falhas = {p: r.get("erro") or "erro desconhecido" for p, r in (resumo or {}).items() if not r.get("ok")}
    registrar_resultado_job(
        "Dash Financeiro mensal", not falhas,
        "; ".join(f"{p}: {erro}" for p, erro in falhas.items()) or None, limite=1,
    )
