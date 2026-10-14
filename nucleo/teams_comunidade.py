"""Publicação importante da Comunidade retransmitida no Teams (3.3.1.0).

Quando alguém marca uma publicação como importante, além do sininho do PDA sai um cartão (Adaptive Card) no canal do
Teams pelo Workflow do Power Automate: texto completo, quem publicou, pra quem, votação e quantos anexos, com o botão
"Abrir na Comunidade". A URL do Workflow (uma por público desde a 3.3.4.3, ver CHAVES_WEBHOOK_POR_PUBLICO) fica cifrada no config.dat (cadastrar em
Criptografia de Dados Sensíveis): ela leva a assinatura (sig) que deixa qualquer um postar no canal, então não vai pro
código nem pro git. Sem ela, o aviso só vai pro log. Nunca levanta exceção (roda numa thread à parte).
"""
import logging
import threading
from datetime import datetime

import requests

from core.config_seguro import obter_valor_config as _obter_valor_config

logger = logging.getLogger("alertas")

CHAVE_WEBHOOK_COMUNIDADE = "teams::comunidade_webhook"  # a primeira (3.3.1.0); desde a 3.3.4.3 vale como a do Monitoramento
# 3.3.4.3: um Workflow (canal) por público da publicação. A chave antiga continua valendo pro Monitoramento, que era o
# canal dela; Serviços ainda não tem canal (sem chave, só o sininho).
CHAVES_WEBHOOK_POR_PUBLICO = {
    "": ("teams::comunidade_webhook_todos",),
    "Monitoramento": ("teams::comunidade_webhook_monitoramento", CHAVE_WEBHOOK_COMUNIDADE),
    "Suporte": ("teams::comunidade_webhook_suporte",),
    "Serviços": ("teams::comunidade_webhook_servicos",),
}


def _webhook_do_publico(publico: str) -> tuple:
    """(url, chave_principal) do canal desse público; url vazia se nenhuma chave dele estiver cadastrada."""
    chaves = CHAVES_WEBHOOK_POR_PUBLICO.get(publico or "", CHAVES_WEBHOOK_POR_PUBLICO[""])
    for chave in chaves:
        url = _obter_valor_config(chave, "")
        if url:
            return url, chave
    return "", chaves[0]
IP_PDA = "192.0.2.198"
LINK_PDA_PADRAO = f"http://{IP_PDA}:8765/"  # o mesmo dos e-mails; vale quando a janela ainda não informou a URL
MAX_TEXTO_CARTAO = 4000  # o Teams corta mensagem muito grande; o resto fica no PDA


def _url_pda() -> str:
    """Link do PDA pro cartão do Teams, sempre pelo IP: o nome pda.local só resolve em máquina com o hosts
    configurado (fora dela o botão dava ERR_NAME_NOT_RESOLVED). A porta segue a da janela (sem porta quando a 80 subiu)."""
    try:
        from urllib.parse import urlparse
        import nucleo.avisos_falha as avisos_falha  # a janela informa a URL do painel aqui quando o servidor sobe
        if not avisos_falha._url_painel:
            return LINK_PDA_PADRAO
        porta = urlparse(avisos_falha._url_painel).port
        return f"http://{IP_PDA}" + (f":{porta}" if porta and porta != 80 else "") + "/"
    except Exception:
        return LINK_PDA_PADRAO


def montar_cartao(post: dict, autor_nome: str, publico: str) -> dict:
    texto = post.get("texto") or ""
    if len(texto) > MAX_TEXTO_CARTAO:
        texto = texto[:MAX_TEXTO_CARTAO].rstrip() + "…\n\n(continua no PDA)"
    quando = post.get("criado_em") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        quando_txt = datetime.strptime(quando[:16], "%Y-%m-%d %H:%M").strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        quando_txt = quando
    iniciais = "".join(p[0] for p in autor_nome.split()[:2]).upper() or "?"
    para = "Todo mundo" if not publico else f"Equipe {publico}"
    corpo = [
        {"type": "Container", "style": "warning", "bleed": True, "items": [
            {"type": "TextBlock", "text": "📢  AVISO IMPORTANTE · COMUNIDADE DO PDA", "weight": "Bolder", "size": "Small",
             "color": "Warning", "wrap": True, "spacing": "None"},
        ]},
        {"type": "ColumnSet", "spacing": "Medium", "columns": [
            {"type": "Column", "width": "auto", "verticalContentAlignment": "Center", "items": [
                {"type": "Container", "style": "accent", "minHeight": "44px", "verticalContentAlignment": "Center", "items": [
                    {"type": "TextBlock", "text": iniciais, "weight": "Bolder", "size": "Large", "horizontalAlignment": "Center",
                     "spacing": "None"}]},
            ]},
            {"type": "Column", "width": "stretch", "verticalContentAlignment": "Center", "items": [
                {"type": "TextBlock", "text": autor_nome, "weight": "Bolder", "size": "Medium", "wrap": True, "spacing": "None"},
                {"type": "TextBlock", "text": f"publicou pra {'todo mundo' if not publico else 'a equipe ' + publico} · {quando_txt}",
                 "isSubtle": True, "size": "Small", "wrap": True, "spacing": "None"},
            ]},
        ]},
    ]
    if texto:
        corpo.append({"type": "TextBlock", "text": texto, "wrap": True, "spacing": "Medium"})
    votacao = post.get("votacao")
    if votacao:
        corpo.append({"type": "TextBlock", "text": "📊 Votação" + (" (pode marcar mais de uma)" if votacao.get("multipla") else ""),
                      "weight": "Bolder", "spacing": "Medium", "wrap": True})
        corpo.append({"type": "TextBlock", "wrap": True, "spacing": "Small",
                      "text": "\n".join(f"- {o['texto']}" for o in votacao.get("opcoes") or [])})
        if votacao.get("fim"):
            dia, _, hora = votacao["fim"].partition("T")
            corpo.append({"type": "TextBlock", "text": "Encerra em " + "/".join(reversed(dia.split("-"))) + (f" às {hora[:5]}" if hora else ""),
                          "isSubtle": True, "size": "Small", "spacing": "None"})
        # 3.3.6.0: o Workflow do Teams não recebe resposta de botão (Action.Submit só funciona com bot), então cada
        # opção abre o PDA já nela (?votar=) e a pessoa confirma o voto lá
        corpo.append({"type": "TextBlock", "text": "Clique na sua opção: o PDA abre e você confirma o voto.",
                      "isSubtle": True, "size": "Small", "spacing": "Small", "wrap": True})
        corpo.append({"type": "ActionSet", "spacing": "Small", "actions": [
            {"type": "Action.OpenUrl", "title": o["texto"][:60],
             "url": _url_pda() + "?evento=post:" + post["id"] + "&votar=" + o["id"]}
            for o in (votacao.get("opcoes") or [])[:6] if o.get("id")]})
    arquivos = post.get("arquivos") or []
    fotos = sum(1 for a in arquivos if a.get("imagem"))
    videos = sum(1 for a in arquivos if a.get("video"))
    outros = len(arquivos) - fotos - videos
    partes = []
    if fotos:
        partes.append(f"🖼️ {fotos} {'foto' if fotos == 1 else 'fotos'}")
    if videos:
        partes.append(f"🎬 {videos} {'vídeo' if videos == 1 else 'vídeos'}")
    if outros:
        partes.append(f"📎 {outros} {'arquivo' if outros == 1 else 'arquivos'}")
    if partes:
        corpo.append({"type": "TextBlock", "text": " · ".join(partes) + " · veja na Comunidade", "isSubtle": True,
                      "size": "Small", "spacing": "Medium", "wrap": True})
    corpo.append({"type": "FactSet", "spacing": "Medium", "facts": [{"title": "Pra quem", "value": para}]})
    conteudo = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "msteams": {"width": "Full"},
        "body": corpo,
        "actions": [{"type": "Action.OpenUrl", "title": "Abrir na Comunidade", "url": _url_pda() + "?evento=post:" + post["id"]}],
    }
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": conteudo}]}


def _enviar(post: dict, autor_nome: str, publico: str) -> dict:
    """Manda o cartão e devolve {ok, erro} (o erro nunca leva a URL do Workflow)."""
    webhook, chave = _webhook_do_publico(publico)
    canal = publico or "Todos"
    if not webhook:
        logger.warning("Publicação importante %s (%s) não foi pro Teams: cadastre o Workflow em Criptografia de Dados Sensíveis (%s).",
                       post.get("id"), canal, chave)
        return {"ok": False, "erro": f"o Workflow do Teams de {canal} não está cadastrado (chave {chave} em Criptografia de Dados Sensíveis)"}
    try:
        resposta = requests.post(webhook, json=montar_cartao(post, autor_nome, publico), timeout=20)
        resposta.raise_for_status()
        logger.info("Publicação importante %s de %s retransmitida no Teams (canal %s).", post.get("id"), autor_nome, canal)
        return {"ok": True}
    except Exception as e:
        # o erro do requests traz a URL com a assinatura do Workflow: só o tipo do erro e o status vão pro log
        status = getattr(getattr(e, "response", None), "status_code", None)
        detalhe = type(e).__name__ + (f", HTTP {status}" if status else "")
        logger.warning("Não foi possível retransmitir a publicação importante %s no Teams (%s).", post.get("id"), detalhe)
        return {"ok": False, "erro": f"o Teams não aceitou o envio ({detalhe})"}


def enviar_agora(post: dict, autor_nome: str, publico: str = "") -> dict:
    """Envio na hora, esperando a resposta (3.3.4.2: botão "Reenviar ao Teams" da Comunidade)."""
    return _enviar(dict(post), autor_nome, publico)


def avisar(post: dict, autor_nome: str, publico: str = "") -> None:
    """Dispara numa thread pra não segurar a resposta da publicação."""
    threading.Thread(target=_enviar, args=(dict(post), autor_nome, publico), daemon=True, name="TeamsComunidade").start()
