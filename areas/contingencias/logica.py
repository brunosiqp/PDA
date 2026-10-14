"""Contingências SEFAZ - lógica (monitoramento da SVC-AN e SVC-RS por UF nos portais da SEFAZ, com aviso no Teams).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import html as html_utils
import logging
import re
import threading
import time
from datetime import datetime
from typing import Optional

import requests

from core.config_seguro import obter_valor_config as _obter_valor_config

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


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
        os logs duplicados do Igor mostravam - o mesmo disparo
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
