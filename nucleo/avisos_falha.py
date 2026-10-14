"""Aviso no Teams quando um job automático falha (e quando volta a funcionar).

Criado na 2.33.2.0 porque falha de job só ficava no log: o envio da ClienteA pro
SharePoint falhou todo dia de 12/08 a 25/09/2026 sem ninguém perceber.

Regra: avisa uma vez quando o job chega em `limite` falhas seguidas e fica
quieto nas próximas; quando ele volta a rodar certo, avisa que voltou (com
quantas falhas foram e desde quando). Job que roda várias vezes por dia usa
limite 2 (uma falha isolada, tipo timeout de banco, não vira mensagem); job
que roda 1x por dia ou menos usa limite 1 (senão levaria um dia pra saber).

A URL do Workflow do Teams fica cifrada no config.dat, chave
`teams::falhas_jobs_webhook` (cadastrar em Criptografia de Dados Sensíveis).
Sem ela, o aviso só vai pro log. O controle é em memória: reiniciar o PDA
zera a contagem (um job que continuar falhando avisa de novo).
"""
import logging
import threading
from datetime import datetime
from typing import List, Optional

import requests

from core.config_seguro import obter_valor_config as _obter_valor_config

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py

CHAVE_WEBHOOK_FALHAS_JOBS = "teams::falhas_jobs_webhook"
LIMITE_ERRO_TEXTO = 600  # erro muito longo (traceback de banco) não cabe bem no cartão

_lock = threading.Lock()
_estado: dict = {}  # nome do job -> {"falhas": int, "desde": str, "avisado": bool, "ultimo_erro": str}
_url_painel: Optional[str] = None


def definir_url_painel(url: Optional[str]) -> None:
    """URL do painel web (ex.: http://pda.local:8765/), pro botão "Abrir
    no PDA" do cartão. Definida pela janela assim que o servidor sobe."""
    global _url_painel
    _url_painel = url


def limite_por_frequencia(agendamentos: List) -> int:
    """1 se o job roda no máximo 1x por dia, 2 se roda mais que isso. Conta
    as execuções por dia a partir dos `schedule.Job` registrados pra ele."""
    execucoes_por_dia = 0.0
    for ag in agendamentos or []:
        unidade, intervalo = getattr(ag, "unit", None), max(getattr(ag, "interval", 1) or 1, 1)
        if unidade in ("seconds", "minutes", "hours"):
            return 2
        if unidade == "days":
            execucoes_por_dia += 1 / intervalo
        elif unidade == "weeks":  # every().monday.at(...): uma execução por semana cada
            execucoes_por_dia += 1 / (7 * intervalo)
    return 1 if execucoes_por_dia <= 1.5 else 2


def registrar_resultado(nome: str, ok: bool, erro: Optional[str] = None, limite: int = 2) -> None:
    """Chamar ao fim de cada execução de job. Decide se precisa avisar e,
    se precisar, manda o cartão numa thread à parte (Teams lento ou fora do
    ar nunca atrasa nem derruba o job)."""
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")
    evento = None
    with _lock:
        est = _estado.setdefault(nome, {"falhas": 0, "desde": None, "avisado": False, "ultimo_erro": None})
        if ok:
            if est["avisado"]:
                evento = ("voltou", dict(est))
            _estado[nome] = {"falhas": 0, "desde": None, "avisado": False, "ultimo_erro": None}
        else:
            est["falhas"] += 1
            est["desde"] = est["desde"] or agora
            est["ultimo_erro"] = (erro or "erro sem mensagem").strip()
            if est["falhas"] >= max(limite, 1) and not est["avisado"]:
                est["avisado"] = True
                evento = ("falhou", dict(est))
    if evento:
        threading.Thread(target=_enviar, args=(nome, evento[0], evento[1], agora), daemon=True,
                         name=f"aviso-teams-{nome}").start()


def estado_atual() -> dict:
    """Cópia do controle (pra diagnóstico/testes)."""
    with _lock:
        return {k: dict(v) for k, v in _estado.items()}


def montar_cartao(nome: str, evento: str, est: dict, agora: str) -> dict:
    """Adaptive Card no formato que o Workflow do Teams aceita (o mesmo das
    Contingências)."""
    if evento == "falhou":
        titulo, cor = f"🔴 Job com falha: {nome}", "Attention"
        fatos = [
            {"title": "Falhas seguidas", "value": str(est["falhas"])},
            {"title": "Falhando desde", "value": est["desde"] or agora},
            {"title": "Erro", "value": _cortar(est["ultimo_erro"])},
        ]
        rodape = "Próximas falhas não geram aviso; quando voltar a funcionar, chega outra mensagem."
    else:
        titulo, cor = f"🟢 Job voltou a funcionar: {nome}", "Good"
        fatos = [
            {"title": "Voltou em", "value": agora},
            {"title": "Estava falhando desde", "value": est["desde"] or "?"},
            {"title": "Falhas no período", "value": str(est["falhas"])},
        ]
        rodape = None
    corpo = [
        {"type": "TextBlock", "text": titulo, "weight": "Bolder", "size": "Medium", "color": cor, "wrap": True},
        {"type": "FactSet", "facts": fatos},
    ]
    if rodape:
        corpo.append({"type": "TextBlock", "text": rodape, "isSubtle": True, "size": "Small", "wrap": True})
    conteudo = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": corpo,
    }
    if _url_painel:
        conteudo["actions"] = [{"type": "Action.OpenUrl", "title": "Abrir no PDA", "url": _url_painel.rstrip("/") + "/alertas"}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": conteudo}]}


def _cortar(texto: Optional[str]) -> str:
    texto = texto or ""
    return texto if len(texto) <= LIMITE_ERRO_TEXTO else texto[:LIMITE_ERRO_TEXTO] + "…"


def _enviar(nome: str, evento: str, est: dict, agora: str) -> None:
    """Nunca levanta exceção: falha de aviso só vai pro log."""
    webhook_url = _obter_valor_config(CHAVE_WEBHOOK_FALHAS_JOBS, "")
    descricao = "falhou" if evento == "falhou" else "voltou a funcionar"
    if not webhook_url:
        logger.warning(
            "Aviso de falha: '%s' %s, mas o webhook do Teams não está configurado "
            "(cadastre em Criptografia de Dados Sensíveis: %s).", nome, descricao, CHAVE_WEBHOOK_FALHAS_JOBS,
        )
        return
    try:
        resposta = requests.post(webhook_url, json=montar_cartao(nome, evento, est, agora), timeout=15)
        resposta.raise_for_status()
        logger.info("Aviso de falha: Teams avisado que '%s' %s.", nome, descricao)
    except Exception as e:
        logger.warning("Aviso de falha: não foi possível avisar o Teams sobre '%s' (%s): %s", nome, descricao, e)
