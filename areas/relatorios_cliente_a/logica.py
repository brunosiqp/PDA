"""Relatórios ClienteA - lógica (banco ClienteA, geração dos Excel, envio pro SharePoint, limpeza local).

Separado do alertas_gui.py em 26/09/2026. As rotas web (/relatorios-cliente_a, /api/relatorios-cliente_a/*)
e o agendamento diário continuam no alertas_gui.py e usam o que está aqui.
"""
import base64
import json
import logging
import os
import re
import threading
import urllib.parse
from datetime import datetime, timedelta

import pandas as pd
import requests

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco, fechar_conexao
from nucleo.avisos_falha import registrar_resultado as registrar_resultado_job
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_config_hibrido

# mesmos loggers configurados no alertas_gui.py (o logging devolve o mesmo objeto pelo nome)
logger = logging.getLogger("alertas")
logger_cliente_a = logging.getLogger("alertas.cliente_a")


# ---------------------------------------------------------------------------
# Relatórios ClienteA
# ---------------------------------------------------------------------------
# Porta pro painel web o processo que hoje roda manualmente num notebook
# Jupyter: consulta CTe/CTe-canceladas do banco de produção do ClienteA
# (cliente_a_cte_prd) pra uma data específica, e gera os dois arquivos Excel
# (Notas e Canceladas) exatamente como o notebook fazia - incluindo o
# split em "Parte 1"/"Parte 2" quando passa de ~1 milhão de linhas.
#
# Igual às outras integrações externas deste projeto: eu não tenho acesso
# de rede ao servidor 192.0.2.78 daqui, então não consigo testar a
# conexão de verdade - toda a lógica (consulta, geração do Excel, split de
# planilha) foi testada com dados e conexão simulados. Teste na prática
# antes de confiar pra decisão real.
# ---------------------------------------------------------------------------

MAX_LINHAS_POR_ABA_EXCEL = 1_048_576 - 1


def _config_cliente_a() -> dict:
    """Lê as credenciais do banco ClienteA - CREDENCIAIS_CENTRALIZADAS.env
    primeiro (seção [infra_cliente_a]), cai pro .env.cliente_a tradicional se
    essa seção não existir (ver core/config_central.py)."""
    valores = _obter_config_hibrido(
        "infra_cliente_a", ".env.cliente_a",
        ["CLIENTE_A_DB_SERVER", "CLIENTE_A_DB_DATABASE", "CLIENTE_A_DB_USER", "CLIENTE_A_DB_PASSWORD"],
    )
    return {
        "server": valores["CLIENTE_A_DB_SERVER"],
        "database": valores["CLIENTE_A_DB_DATABASE"],
        "username": valores["CLIENTE_A_DB_USER"],
        "password": _obter_valor_config("cliente_a::CLIENTE_A_DB_PASSWORD", valores["CLIENTE_A_DB_PASSWORD"]),
    }


def _conectar_cliente_a():
    cfg = _config_cliente_a()
    if not all(cfg.values()):
        return None, "Credenciais do banco ClienteA não configuradas (.env.cliente_a)."
    try:
        conn = conectar_banco(cfg["server"], cfg["database"], cfg["username"], cfg["password"])
    except Exception as e:
        logger.exception("Erro inesperado ao conectar no banco ClienteA")
        return None, f"Erro inesperado ao conectar: {e}"
    if not conn:
        return None, "Não foi possível conectar ao banco ClienteA."
    return conn, None


def _pasta_saida_relatorios_cliente_a(data: datetime) -> str:
    """Pasta local onde os relatórios de um dia específico ficam salvos -
    organizada em Mês (inglês) / DD-MM-YYYY, espelhando exatamente a
    mesma estrutura usada no SharePoint (ver _enviar_relatorio_cliente_a_
    sharepoint) - pedido pra manter os dois arquivamentos consistentes a
    partir de agora. Cria a pasta se ainda não existir."""
    pasta = os.path.join(
        _base_path_app(), "relatorios_cliente_a_saida",
        MESES_INGLES[data.month], data.strftime("%d-%m-%Y"),
    )
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _localizar_pasta_relatorio_cliente_a_por_data_str(data_arquivo: str) -> str:
    """Reconstrói a pasta local (Mês/DD-MM-YYYY) a partir de uma data no
    formato 'DD-MM-YYYY' (o mesmo formato usado no nome dos arquivos) -
    usado pelas rotas que só recebem a data em texto, sem um objeto
    datetime já pronto."""
    data_obj = datetime.strptime(data_arquivo, "%d-%m-%Y")
    return _pasta_saida_relatorios_cliente_a(data_obj)


def _construir_queries_cliente_a(data: datetime) -> tuple:
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


def _dataframe_cliente_a(query: str, conn) -> "pd.DataFrame":
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


def _gravar_excel_cliente_a(df: "pd.DataFrame", caminho: str, nome_aba: str) -> None:
    """Grava um DataFrame em Excel, dividindo em 'Parte 1'/'Parte 2' se
    passar do limite de linhas de uma aba (igual o notebook original)."""
    with pd.ExcelWriter(caminho, engine="xlsxwriter") as writer:
        if len(df) > MAX_LINHAS_POR_ABA_EXCEL:
            df.iloc[:MAX_LINHAS_POR_ABA_EXCEL].to_excel(writer, sheet_name=f"{nome_aba} Parte 1", index=False)
            df.iloc[MAX_LINHAS_POR_ABA_EXCEL:].to_excel(writer, sheet_name=f"{nome_aba} Parte 2", index=False)
        else:
            df.to_excel(writer, sheet_name=nome_aba, index=False)


def _gerar_relatorio_cliente_a(data_str: str) -> dict:
    """Gera os relatórios de Notas e Canceladas do ClienteA pra uma data
    (formato YYYY-MM-DD). Retorna os nomes dos arquivos gerados (prontos
    pra download) e a contagem de linhas de cada um."""
    try:
        data = datetime.strptime(data_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        logger_cliente_a.error("Data inválida recebida: %r", data_str)
        return {"ok": False, "erro": "Data inválida."}

    logger_cliente_a.info("Iniciando geração do relatório ClienteA pra %s.", data.strftime("%d-%m-%Y"))

    conn, erro = _conectar_cliente_a()
    if erro:
        logger_cliente_a.error("Falha ao conectar no banco ClienteA: %s", erro)
        return {"ok": False, "erro": erro}

    pasta = None
    try:
        query_notas, query_canceladas = _construir_queries_cliente_a(data)
        df_notas = _dataframe_cliente_a(query_notas, conn)
        logger_cliente_a.info("Query de Notas retornou %d linha(s).", len(df_notas))
        df_canceladas = _dataframe_cliente_a(query_canceladas, conn)
        logger_cliente_a.info("Query de Canceladas retornou %d linha(s).", len(df_canceladas))

        data_arquivo = data.strftime("%d-%m-%Y")
        pasta = _pasta_saida_relatorios_cliente_a(data)
        # padrão de nomenclatura pedido pelo cliente (voltou a como era antes
        # de 07/08): Notas sem prefixo nenhum, Canceladas só com "Canceladas_"
        # na frente - sem "ClienteA_" em nenhum dos dois.
        nome_notas = f"{data_arquivo}.xlsx"
        nome_canceladas = f"Canceladas_{data_arquivo}.xlsx"
        _gravar_excel_cliente_a(df_notas, os.path.join(pasta, nome_notas), "Notas")
        logger_cliente_a.info("Arquivo '%s' gravado em %s.", nome_notas, pasta)
        _gravar_excel_cliente_a(df_canceladas, os.path.join(pasta, nome_canceladas), "Canceladas")
        logger_cliente_a.info("Arquivo '%s' gravado em %s.", nome_canceladas, pasta)

        logger.info(
            "Relatório ClienteA gerado pra %s: %d notas, %d canceladas.",
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
        # permissão de escrita NA PASTA LOCAL relatorios_cliente_a_saida,
        # mesma causa raiz do Errno 13 já visto no log do EmailPack:
        # a pasta/arquivo foi criado por outra sessão do Windows e o
        # usuário atual não tem permissão de gravação nela. Mensagem
        # separada da genérica abaixo pra não confundir com falha de
        # conexão/autenticação no Graph.
        logger_cliente_a.exception("Sem permissão pra gravar o relatório ClienteA localmente (pasta %s)", pasta)
        return {
            "ok": False,
            "erro": (
                f"Sem permissão pra gravar o arquivo localmente: {e}. "
                "Isso não é falha de conexão com o SharePoint - o problema é "
                "de permissão NTFS na pasta relatorios_cliente_a_saida (provavelmente "
                "criada por outra sessão do Windows). Confira em Propriedades → "
                "Segurança da pasta se o usuário que roda essa automação tem "
                "permissão de Modificar."
            ),
        }
    except Exception as e:
        logger_cliente_a.exception("Erro ao gerar relatório ClienteA pra %s", data_str)
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)
        logger_cliente_a.info("Conexão com o banco ClienteA encerrada.")


# ---------------------------------------------------------------------------
# Envio automático dos Relatórios ClienteA pro SharePoint - todos os dias às
# 08:00, o relatório do dia anterior é gerado e enviado sozinho.
# ---------------------------------------------------------------------------
# ATENÇÃO - leia antes de confiar nisso:
#   A autenticação usa o fluxo "usuário e senha direto" do Microsoft Graph
#   (ROPC - Resource Owner Password Credentials), porque é o único jeito
#   de autenticar só com login/senha, sem precisar registrar um aplicativo
#   próprio no Azure AD da Empresa (o que eu não tenho como fazer sozinho -
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
#   Também não tenho como confirmar se a pasta "Relatorio_ClienteA" fica no
#   OneDrive pessoal da conta suporte@example.com ou num site de
#   equipe do SharePoint - pela captura de tela que você mandou (o
#   círculo com o nome "Suporte eDOCs" no canto), parece OneDrive pessoal,
#   e foi assim que implementei por padrão (usa o endpoint /me/drive, que
#   automaticamente aponta pro drive de quem autenticou). Se na prática for
#   um site de equipe, cola a URL completa (a que aparece na barra do
#   navegador com a pasta aberta) no campo SHAREPOINT_SITE_URL do
#   .env.sharepoint que o comportamento muda sozinho.
#
#   Por fim: não tenho acesso à internet daqui pra testar nada disso de
#   verdade contra o Microsoft Graph. Toda a lógica (autenticação, criação
#   de pastas, upload) foi testada com respostas HTTP simuladas.
#
#   ATUALIZAÇÃO 2.31.0 (25/09/2026): o log mostrou que o envio falhou TODO dia
#   desde 12/08 - login OK, mas 404 em qualquer drive, inclusive o da própria
#   suporte@ (que é a dona da pasta). Causa provável: o token do app Azure
#   PowerShell não traz permissão de arquivos. Mudou: (1) o login tenta os apps
#   do Office/Teams antes e registra no log as permissões de cada token;
#   (2) a pasta Relatorio_ClienteA é achada pelo link de compartilhamento (API
#   /shares), sem adivinhar drive; (3) estrutura AAAA/Mês/DD-MM-AAAA, com pasta
#   de ano/mês criada sozinha; (4) cópia local apagada depois de conferido o
#   tamanho no SharePoint, mais uma varredura dos dias anteriores.
# ---------------------------------------------------------------------------

CLIENT_ID_GRAPH_ROPC = "1950a258-227b-4e31-a9cf-717495945fc2"  # cliente público oficial da Microsoft (Azure PowerShell) - permite ROPC sem precisar de client secret

# Apps públicos da própria Microsoft tentados no login ROPC, em ordem. Motivo (2.31.0):
# com o Azure PowerShell, único usado até a 2.30.x, o login funciona mas o token sai
# SEM permissão de arquivos (Files.*/Sites.*) e o SharePoint responde 404 "itemNotFound"
# até pro OneDrive da própria conta - foi o erro de TODO dia de 12/08 a 25/09/2026.
# Os apps do Office/Teams recebem essas permissões. O escopo de cada token vai pro log.
CLIENTES_GRAPH_ROPC = [
    ("Microsoft Office", "d3590ed6-52b3-4102-aeff-aad2292ab01c"),
    ("Microsoft Teams", "1fec8e78-bce4-4aaf-ab1b-5451cc387264"),
    ("Azure PowerShell", CLIENT_ID_GRAPH_ROPC),
]
ESCOPOS_ARQUIVOS_GRAPH = {
    "Files.ReadWrite", "Files.ReadWrite.All", "Sites.ReadWrite.All",
    "Sites.Manage.All", "Sites.FullControl.All",
}

# Link de compartilhamento da pasta Relatorio_ClienteA (OneDrive do suporte@), passado
# pelo Igor em 25/09/2026. Achar a pasta pelo link não depende de adivinhar em que
# drive/caminho ela está. SHAREPOINT_PASTA_URL no [infra_sharepoint] sobrescreve.
LINK_PASTA_RELATORIO_CLIENTE_A_PADRAO = (
    "https://empresa-my.sharepoint.com/:f:/g/personal/usuario_example_com/"
    "LINK_DE_EXEMPLO?e=XXXX"
)

# Depois de confirmar que o arquivo chegou inteiro no SharePoint (mesmo tamanho),
# apaga a cópia local pra não acumular relatório no disco do servidor.
LIMPAR_RELATORIOS_CLIENTE_A_APOS_ENVIO = True

MESES_INGLES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December",
}

HORARIO_RELATORIO_CLIENTE_A_AUTOMATICO = "08:00"

estado_relatorio_cliente_a_automatico: dict = {
    "ultima_execucao": None,
    "ultimo_sucesso": None,
    "ultimo_erro": None,
}
_lock_relatorio_cliente_a_auto = threading.Lock()


def _config_sharepoint() -> dict:
    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seção [infra_sharepoint]),
    # cai pro .env.sharepoint tradicional se essa seção não existir -
    # ver core/config_central.py.
    valores = _obter_config_hibrido(
        "infra_sharepoint", ".env.sharepoint",
        ["SHAREPOINT_LOGIN", "SHAREPOINT_PASSWORD", "SHAREPOINT_TENANT",
         "SHAREPOINT_SITE_URL", "SHAREPOINT_DRIVE_OWNER_EMAIL", "SHAREPOINT_PASTA_URL"],
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
        "pasta_url": valores["SHAREPOINT_PASTA_URL"].strip() or LINK_PASTA_RELATORIO_CLIENTE_A_PADRAO,
    }


def _obter_token_sharepoint(cfg: dict):
    """Autentica via ROPC (usuário+senha) contra o Microsoft Graph. Ver
    aviso no topo da seção sobre a limitação de MFA. Retorna (token, erro)."""
    if not cfg["login"] or not cfg["senha"] or not cfg["tenant"]:
        return None, "Credenciais do SharePoint não configuradas (.env.sharepoint)."
    # tenta cada app de CLIENTES_GRAPH_ROPC até sair um token COM permissão de
    # arquivos; se nenhum tiver, usa o primeiro token que funcionou (e avisa no log)
    falhas, token_sem_arquivos = [], None
    for nome_app, client_id in CLIENTES_GRAPH_ROPC:
        try:
            resposta = requests.post(
                f"https://login.microsoftonline.com/{cfg['tenant']}/oauth2/v2.0/token",
                data={
                    "grant_type": "password",
                    "client_id": client_id,
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
                falhas.append(f"{nome_app}: {corpo.get('error_description', resposta.text)[:200]}")
                continue
            token = corpo.get("access_token")
            escopos = _escopos_do_token(token)
            logger_cliente_a.info("Login no Microsoft 365 via app '%s' OK · permissões: %s",
                              nome_app, " ".join(sorted(escopos)) or "(não informadas)")
            if escopos & ESCOPOS_ARQUIVOS_GRAPH:
                return token, None
            falhas.append(f"{nome_app}: login OK, mas sem permissão de arquivos")
            token_sem_arquivos = token_sem_arquivos or token
        except Exception as e:
            falhas.append(f"{nome_app}: erro inesperado ({e})")
    if token_sem_arquivos:
        logger_cliente_a.warning(
            "Nenhum app recebeu permissão de arquivos (Files.*/Sites.*); tentando mesmo assim, "
            "mas o SharePoint deve responder 404. Tentativas: %s", " | ".join(falhas))
        return token_sem_arquivos, None
    return None, "Falha ao autenticar no Microsoft 365/SharePoint: " + " | ".join(falhas)


def _escopos_do_token(token: str) -> set:
    """Lê as permissões (claim "scp") de dentro do token JWT, só pra diagnóstico
    no log - não valida assinatura e nunca registra o token em si."""
    try:
        carga = token.split(".")[1]
        carga += "=" * (-len(carga) % 4)
        return set(json.loads(base64.urlsafe_b64decode(carga)).get("scp", "").split())
    except Exception:
        return set()


def _resolver_pasta_por_link(token: str, link: str):
    """Acha a pasta do OneDrive/SharePoint a partir do link de compartilhamento
    (API /shares do Graph). Retorna (url_do_item, nome_da_pasta, None) ou
    (None, None, erro). A url_do_item serve de raiz pros caminhos relativos
    (ver _garantir_pasta_sharepoint)."""
    codificado = "u!" + base64.urlsafe_b64encode(link.encode("utf-8")).decode("ascii").rstrip("=")
    try:
        resp = requests.get(
            f"https://graph.microsoft.com/v1.0/shares/{codificado}/driveItem",
            headers={"Authorization": f"Bearer {token}"}, timeout=20,
        )
    except requests.exceptions.RequestException as e:
        return None, None, f"erro de rede ao abrir o link da pasta ({e})"
    if resp.status_code != 200:
        return None, None, f"link da pasta não abriu: {resp.status_code} {resp.text[:200]}"
    item = resp.json()
    drive_id = (item.get("parentReference") or {}).get("driveId")
    if not drive_id or not item.get("id") or "folder" not in item:
        return None, None, "o link não aponta pra uma pasta"
    return f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item['id']}", item.get("name", ""), None


def _extrair_site_do_link_sharepoint(url: str):
    """Tenta extrair (hostname, tipo, identificador) de uma URL do
    SharePoint/OneDrive, aceitando os formatos mais comuns que aparecem
    quando alguém copia o link direto da barra de endereço OU usa o botão
    "copiar link" da interface (que gera uma URL tipo
    /shared?id=%2Fpersonal%2F...%2FRelatorio_ClienteA%2F... com o caminho
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
         "suporte_empresa_com_br" -> "suporte@example.com"), via
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
                "equipe do SharePoint. Se a pasta 'Relatorio_ClienteA' na verdade fica dentro de "
                "um site de equipe (ex: um site chamado 'Suporte eDOCs'), copie a URL de dentro "
                "dessa pasta (que deve conter '/sites/' em vez de '/personal/', e o domínio "
                "SEM o '-my') e cole em SHAREPOINT_SITE_URL no .env.sharepoint."
            )

    return None, (
        f"Não consegui acessar nenhum dos {len(candidatos)} endereço(s) tentado(s) pro drive do "
        f"SharePoint/OneDrive:\n{detalhes}\n"
        "Isso costuma acontecer quando a conta de login é uma caixa de e-mail compartilhada "
        "(sem OneDrive próprio) e a URL/e-mail configurado em SHAREPOINT_SITE_URL ou "
        "SHAREPOINT_DRIVE_OWNER_EMAIL (.env.sharepoint) também não bateu. Confira se a URL "
        "está exatamente certa (copiada da barra de endereço, com a pasta Relatorio_ClienteA "
        "aberta), ou se a conta de login tem permissão de acessar esse local."
        + dica_tipo_url
    )


def _garantir_pasta_sharepoint(token: str, raiz: str, caminho_pastas: list):
    """Garante que a cadeia de pastas exista no SharePoint/OneDrive,
    criando as que faltarem (é isso que cria sozinho a pasta do ano novo e
    do mês novo). `raiz` é o endereço Graph de um item-pasta JÁ RESOLVIDO:
    a pasta do link de compartilhamento (".../drives/{id}/items/{id}") ou a
    raiz de um drive (".../drive/root"); os caminhos são relativos a ela.
    Retorna None se deu certo, ou a mensagem de erro."""
    cabecalhos = {"Authorization": f"Bearer {token}"}
    caminho_acumulado = ""
    for pasta in caminho_pastas:
        caminho_pai = caminho_acumulado
        caminho_acumulado = f"{caminho_acumulado}/{pasta}" if caminho_acumulado else pasta

        resp = requests.get(f"{raiz}:/{caminho_acumulado}", headers=cabecalhos, timeout=20)
        if resp.status_code == 200:
            continue  # já existe
        if resp.status_code != 404:
            return f"Erro ao verificar pasta '{caminho_acumulado}': {resp.status_code} {resp.text[:200]}"

        url_criar = f"{raiz}:/{caminho_pai}:/children" if caminho_pai else f"{raiz}/children"
        resp_criar = requests.post(
            url_criar,
            headers={**cabecalhos, "Content-Type": "application/json"},
            json={"name": pasta, "folder": {}, "@microsoft.graph.conflictBehavior": "replace"},
            timeout=20,
        )
        if resp_criar.status_code not in (200, 201):
            return f"Erro ao criar pasta '{caminho_acumulado}': {resp_criar.status_code} {resp_criar.text[:200]}"
    return None


LIMITE_UPLOAD_SIMPLES_GRAPH = 250 * 1024 * 1024  # limite do PUT .../content do Graph


def _enviar_arquivo_sharepoint(token: str, raiz: str, caminho_local: str, caminho_remoto: str):
    """Envia um arquivo local pro caminho remoto (relativo à `raiz`, ver
    _garantir_pasta_sharepoint) e confere que o tamanho que chegou é o mesmo
    do arquivo local - só com essa confirmação a cópia local pode ser apagada.
    Upload simples do Graph (até 250MB; o relatório de notas tem ~30MB).
    Retorna None se deu certo, ou a mensagem de erro."""
    tamanho_local = os.path.getsize(caminho_local)
    if tamanho_local > LIMITE_UPLOAD_SIMPLES_GRAPH:
        return (f"'{os.path.basename(caminho_local)}' tem {tamanho_local // (1024 * 1024)}MB, acima do "
                "limite de 250MB do envio simples - precisa implementar envio em partes (upload session)")
    with open(caminho_local, "rb") as f:
        conteudo = f.read()
    resp = requests.put(
        f"{raiz}:/{caminho_remoto}:/content",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/octet-stream"},
        data=conteudo,
        timeout=300,  # ~30MB: 60s era pouco em link mais lento
    )
    if resp.status_code not in (200, 201):
        return f"Erro ao enviar '{caminho_remoto}': {resp.status_code} {resp.text[:300]}"
    try:
        tamanho_remoto = resp.json().get("size")
    except Exception:
        tamanho_remoto = None
    if tamanho_remoto != tamanho_local:
        return (f"'{caminho_remoto}' chegou com tamanho diferente no SharePoint "
                f"({tamanho_remoto} bytes lá, {tamanho_local} aqui)")
    return None


def _tamanho_remoto_sharepoint(token: str, raiz: str, caminho_remoto: str):
    """Tamanho do arquivo no SharePoint, ou None se não existir/der erro."""
    try:
        resp = requests.get(f"{raiz}:/{caminho_remoto}", headers={"Authorization": f"Bearer {token}"}, timeout=20)
        return resp.json().get("size") if resp.status_code == 200 else None
    except Exception:
        return None


def _apagar_arquivos_locais_confirmados(pasta_dia: str, nomes: list) -> int:
    """Apaga só os arquivos listados (já confirmados no SharePoint) e remove a
    pasta do dia e a do mês se ficarem vazias. Nunca apaga arquivo que não
    está na lista - se aparecer outra coisa na pasta, ela fica. Retorna
    quantos arquivos apagou."""
    apagados = 0
    for nome in nomes:
        caminho = os.path.join(pasta_dia, nome)
        if os.path.isfile(caminho):
            os.remove(caminho)
            apagados += 1
    for pasta in (pasta_dia, os.path.dirname(pasta_dia)):
        try:
            os.rmdir(pasta)  # só remove se estiver vazia
        except OSError:
            break
    return apagados


def _limpar_relatorios_cliente_a_ja_enviados(token: str, raiz: str, exceto_pasta: str = "") -> None:
    """Varre relatorios_cliente_a_saida/<Mês>/<DD-MM-AAAA>/ e apaga o que JÁ está
    no SharePoint com o mesmo tamanho (ex.: relatórios gerados manualmente pela
    tela, ou dias que o Igor subiu na mão). O que não estiver lá fica e vai
    pro log, pra ninguém perder arquivo."""
    base_local = os.path.join(_base_path_app(), "relatorios_cliente_a_saida")
    if not os.path.isdir(base_local):
        return
    for nome_mes in sorted(os.listdir(base_local)):
        pasta_mes = os.path.join(base_local, nome_mes)
        if not os.path.isdir(pasta_mes):
            continue
        for nome_dia in sorted(os.listdir(pasta_mes)):
            pasta_dia = os.path.join(pasta_mes, nome_dia)
            if not os.path.isdir(pasta_dia) or os.path.normcase(pasta_dia) == os.path.normcase(exceto_pasta):
                continue
            try:
                data = datetime.strptime(nome_dia, "%d-%m-%Y")
            except ValueError:
                continue  # pasta que não é de relatório: não mexe
            remoto = f"{data.year}/{MESES_INGLES[data.month]}/{nome_dia}"
            confirmados, pendentes = [], []
            for nome in (f"{nome_dia}.xlsx", f"Canceladas_{nome_dia}.xlsx"):
                caminho = os.path.join(pasta_dia, nome)
                if not os.path.isfile(caminho):
                    continue
                if _tamanho_remoto_sharepoint(token, raiz, f"{remoto}/{nome}") == os.path.getsize(caminho):
                    confirmados.append(nome)
                else:
                    pendentes.append(nome)
            if not confirmados and not pendentes:
                # pasta vazia (a tela recria a pasta do dia só de consultar se ele existe)
                _apagar_arquivos_locais_confirmados(pasta_dia, [])
            if confirmados:
                _apagar_arquivos_locais_confirmados(pasta_dia, confirmados)
                logger_cliente_a.info("Limpeza: %s apagado(s) do servidor (já estão no SharePoint em %s).",
                                  ", ".join(confirmados), remoto)
            if pendentes:
                logger_cliente_a.warning("Limpeza: %s mantido(s) no servidor - não encontrado(s) com o mesmo "
                                     "tamanho no SharePoint em %s.", ", ".join(pendentes), remoto)


def _enviar_relatorio_cliente_a_sharepoint(data: datetime, nome_notas: str, nome_canceladas: str) -> dict:
    """Sobe os dois arquivos do relatório do dia pro SharePoint, na estrutura
    Relatorio_ClienteA/<AAAA>/<MêsEmInglês>/<DD-MM-AAAA>/ (mês sempre em inglês,
    igual já está lá - não depende do idioma da máquina). Pastas de ano/mês que
    ainda não existem são criadas na hora. Depois de confirmar cada arquivo
    (mesmo tamanho lá e aqui), apaga a cópia local e varre o que sobrou de
    dias anteriores (ver _limpar_relatorios_cliente_a_ja_enviados)."""
    logger_cliente_a.info("Iniciando envio ao SharePoint pra %s.", data.strftime("%d-%m-%Y"))
    cfg = _config_sharepoint()

    token, erro = _obter_token_sharepoint(cfg)
    if erro:
        logger_cliente_a.error("Falha ao autenticar no Microsoft Graph: %s", erro)
        return {"ok": False, "erro": erro}

    subpastas = [str(data.year), MESES_INGLES[data.month], data.strftime("%d-%m-%Y")]
    # 1º caminho: a pasta Relatorio_ClienteA pelo link de compartilhamento
    raiz, nome_pasta, erro_link = _resolver_pasta_por_link(token, cfg["pasta_url"])
    if raiz:
        logger_cliente_a.info("Pasta do link encontrada: '%s'.", nome_pasta)
    else:
        # 2º caminho (como era até a 2.30.x): adivinha o drive e usa Relatorio_ClienteA na raiz dele
        logger_cliente_a.warning("Não deu pra usar o link da pasta (%s); tentando pelo drive da conta.", erro_link)
        base, erro_drive = _resolver_base_graph_drive(token, cfg)
        if erro_drive:
            erro_final = f"Link da pasta: {erro_link}\n\nDrive da conta: {erro_drive}"
            logger_cliente_a.error("Não foi possível chegar na pasta do SharePoint: %s", erro_final)
            return {"ok": False, "erro": erro_final}
        logger_cliente_a.info("Drive resolvido: %s", base)
        raiz = f"{base}/root"
        subpastas = ["Relatorio_ClienteA"] + subpastas

    erro_pasta = _garantir_pasta_sharepoint(token, raiz, subpastas)
    if erro_pasta:
        logger_cliente_a.error("Falha ao criar/conferir a pasta '%s': %s", "/".join(subpastas), erro_pasta)
        return {"ok": False, "erro": erro_pasta}
    caminho_pastas_str = "/".join(subpastas)
    logger_cliente_a.info("Pasta '%s' confirmada no SharePoint.", caminho_pastas_str)

    pasta_local = _pasta_saida_relatorios_cliente_a(data)
    for nome_arquivo in (nome_notas, nome_canceladas):
        erro_envio = _enviar_arquivo_sharepoint(
            token, raiz, os.path.join(pasta_local, nome_arquivo), f"{caminho_pastas_str}/{nome_arquivo}"
        )
        if erro_envio:
            logger_cliente_a.error("Falha ao enviar '%s': %s", nome_arquivo, erro_envio)
            return {"ok": False, "erro": erro_envio}
        logger_cliente_a.info("Arquivo '%s' enviado e conferido (mesmo tamanho no SharePoint).", nome_arquivo)

    logger_cliente_a.info("Envio ao SharePoint concluído com sucesso pra %s.", data.strftime("%d-%m-%Y"))

    if LIMPAR_RELATORIOS_CLIENTE_A_APOS_ENVIO:
        # limpeza nunca derruba o envio que já deu certo: qualquer erro só vai pro log
        try:
            apagados = _apagar_arquivos_locais_confirmados(pasta_local, [nome_notas, nome_canceladas])
            logger_cliente_a.info("Limpeza: %d arquivo(s) de %s apagado(s) do servidor.", apagados, data.strftime("%d-%m-%Y"))
            if raiz.endswith("/root"):
                # modo antigo: os caminhos da varredura (AAAA/Mês/Dia) não batem com Relatorio_ClienteA/...
                logger_cliente_a.info("Varredura de dias anteriores pulada (pasta resolvida pelo modo antigo).")
            else:
                _limpar_relatorios_cliente_a_ja_enviados(token, raiz, exceto_pasta=pasta_local)
        except Exception:
            logger_cliente_a.exception("Falha na limpeza dos relatórios locais (o envio já tinha dado certo).")
    return {"ok": True}


NOME_JOB_CLIENTE_A_DIARIO = "Relatório ClienteA diário"


def _executar_relatorio_cliente_a_diario() -> None:
    """Roda 1x por dia (agendado via `schedule`, junto com os outros
    alertas): gera o relatório de ONTEM e envia pro SharePoint."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ontem = datetime.now() - timedelta(days=1)
    logger_cliente_a.info("=" * 60)
    logger_cliente_a.info("Execução automática diária iniciada (relatório de %s).", ontem.strftime("%d-%m-%Y"))
    try:
        resultado = _gerar_relatorio_cliente_a(ontem.strftime("%Y-%m-%d"))
        if not resultado.get("ok"):
            raise RuntimeError(resultado.get("erro", "erro desconhecido ao gerar o relatório"))

        resultado_envio = _enviar_relatorio_cliente_a_sharepoint(
            ontem, resultado["arquivo_notas"], resultado["arquivo_canceladas"]
        )
        if not resultado_envio.get("ok"):
            raise RuntimeError(resultado_envio.get("erro", "erro desconhecido ao enviar pro SharePoint"))

        with _lock_relatorio_cliente_a_auto:
            estado_relatorio_cliente_a_automatico["ultima_execucao"] = agora
            estado_relatorio_cliente_a_automatico["ultimo_sucesso"] = agora
            estado_relatorio_cliente_a_automatico["ultimo_erro"] = None
        logger_cliente_a.info("Relatório ClienteA automático de %s enviado ao SharePoint.", ontem.strftime("%d-%m-%Y"))
        logger_cliente_a.info("Execução automática diária concluída com SUCESSO.")
        registrar_resultado_job(NOME_JOB_CLIENTE_A_DIARIO, True)
    except Exception as e:
        with _lock_relatorio_cliente_a_auto:
            estado_relatorio_cliente_a_automatico["ultima_execucao"] = agora
            estado_relatorio_cliente_a_automatico["ultimo_erro"] = str(e)
        logger.exception("Erro ao rodar o relatório ClienteA automático diário")
        logger_cliente_a.exception("Execução automática diária FALHOU.")
        registrar_resultado_job(NOME_JOB_CLIENTE_A_DIARIO, False, str(e), limite=1)  # roda 1x por dia: avisa na 1ª falha
