"""Comunicado da v3 por e-mail (3.0.3.0).

Um e-mail bonito apresentando a v3 do PDA, mandado uma vez pra cada e-mail cadastrado no
PDA (usuarios.json, só quem está ativo). Quem dispara é o Igor ou a Debora, pelo painel
que aparece pra eles no /changelog (com prévia antes). Cada pessoa recebe o seu (com o
primeiro nome), nunca com a lista dos outros. O que já saiu fica em
comunicados_enviados.json ({"v3": {"enviados": {email: quando}, "falhas": {email: erro},
"iniciado_em", "por"}}), então disparar de novo só manda pra quem ainda não recebeu.
"""
import html as html_utils
import json
import logging
import os
import re
import threading
import time
from datetime import datetime

from areas.emails.logica import LINK_PDA_WEB, _config_email_boas_vindas, _enviar_email_com_fotos
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

ID_COMUNICADO = "v3"
ASSUNTO_V3 = "🚀 Chegou a v3 do PDA: o painel agora é da equipe"
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_lock = threading.Lock()
_em_andamento = {"ativo": False}

NOVIDADES_V3 = [
    ("🏠", "Um início novo, com o mural da equipe",
     "Aniversários, promoções, tempo de casa, insígnias conquistadas e quem chegou: tudo numa linha do tempo, logo que você entra."),
    ("👏", "Palminhas e comentários",
     "Bata palminhas e deixe um recado em cada acontecimento. Quem recebeu fica sabendo na hora."),
    ("🏅", "Insígnias no seu perfil",
     "Tempo de casa (do Ferro ao Diamante), PDA Beta User e outras. Escolha uma pra ficar em destaque junto da sua foto."),
    ("🔔", "Sininho de notificações",
     "Palminhas, comentários e as novidades de cada versão do PDA, no topo de todas as telas."),
    ("🧭", "Tudo mais fácil de achar",
     "Menu à esquerda com Automações, Outros e Em breve, favoritos como atalho e busca nas automações."),
]


def _caminho() -> str:
    return os.path.join(_base_path_app(), "comunicados_enviados.json")


def _ler() -> dict:
    try:
        with open(_caminho(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("comunicados_enviados.json ilegível.")
        return {}


def _gravar(dados: dict) -> None:
    caminho = _caminho()
    with open(caminho + ".tmp", "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=1, ensure_ascii=False)
    os.replace(caminho + ".tmp", caminho)


def destinatarios() -> list:
    """[(login, nome, email)] de quem está ativo e tem e-mail válido, cada e-mail uma vez."""
    vistos, lista = set(), []
    for login, info in USUARIOS_WEB.items():
        email = (info.get("email") or "").strip()
        if not info.get("ativo", True) or login.lower().startswith("teste") or not _RE_EMAIL.match(email):
            continue
        if email.lower() in vistos:
            continue
        vistos.add(email.lower())
        lista.append((login, info.get("nome") or login, email))
    return lista


def montar_email_v3_html(nome: str) -> str:
    esc = html_utils.escape
    primeiro = esc((nome or "").split(" ")[0] or "pessoal")
    itens = "".join(f"""
              <tr>
                <td style="padding:0 0 12px 0;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#1f2833; border:1px solid #2a3542; border-radius:12px;">
                    <tr>
                      <td width="54" valign="top" style="padding:16px 0 16px 16px; font-size:26px; line-height:1;">{icone}</td>
                      <td style="padding:14px 18px 14px 6px;">
                        <div style="font-size:15px; font-weight:700; color:#e6edf3; margin:0 0 4px 0;">{esc(titulo)}</div>
                        <div style="font-size:13px; color:#a9b4bf; line-height:1.55;">{esc(texto)}</div>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>""" for icone, titulo, texto in NOVIDADES_V3)
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>PDA v3</title></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px; background:#151c24; border-radius:18px; overflow:hidden; border:1px solid #26303b;">
        <tr>
          <td bgcolor="#2db8cf" style="background:#2db8cf; background-image:linear-gradient(135deg, #2db8cf 0%, #6fc27a 55%, #b0cb1c 100%); padding:44px 32px 40px 32px; text-align:center;">
            <div style="font-size:13px; font-weight:800; letter-spacing:.28em; color:#08131a; opacity:.75;">PAINEL DE AUTOMAÇÕES</div>
            <div style="font-size:72px; font-weight:900; color:#08131a; line-height:1; margin:10px 0 6px 0; letter-spacing:-.03em;">v3</div>
            <div style="font-size:19px; font-weight:700; color:#08131a;">O PDA agora é o painel da equipe 🚀</div>
          </td>
        </tr>
        <tr>
          <td style="padding:34px 32px 10px 32px;">
            <p style="font-size:19px; color:#e6edf3; margin:0 0 14px 0; font-weight:700;">Oi, {primeiro}! 👋</p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 10px 0;">
              Hoje sai a <b style="color:#2db8cf;">versão 3 do PDA</b>. Ele continua sendo o lugar das nossas automações,
              alertas e indicadores, e agora também é onde a equipe se encontra: dá pra acompanhar o que está
              acontecendo com as pessoas, comemorar junto e conhecer melhor quem trabalha do seu lado.
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 22px 0;">Olha o que tem de novo:</p>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{itens}
            </table>
          </td>
        </tr>
        <tr>
          <td style="padding:6px 32px 8px 32px;">
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#1d2a1c; border:1px solid #3d5a1e; border-radius:12px;">
              <tr>
                <td style="padding:16px 18px; font-size:13.5px; color:#d9e7c4; line-height:1.6;">
                  <b style="color:#b0cb1c;">🎯 Campanha PDA Beta User:</b> complete seu perfil (foto, entrada na empresa,
                  aniversário, e-mail e cargo) e ganhe a insígnia da fase beta. O convite aparece assim que você entra.
                </td>
              </tr>
            </table>
          </td>
        </tr>
        <tr>
          <td align="center" style="padding:26px 32px 34px 32px;">
            <table role="presentation" cellpadding="0" cellspacing="0">
              <tr>
                <td bgcolor="#2db8cf" style="border-radius:12px; background:#2db8cf;">
                  <a href="{LINK_PDA_WEB}" style="display:inline-block; padding:15px 34px; font-size:15px; font-weight:800; color:#08131a; text-decoration:none; border-radius:12px;">Abrir o PDA →</a>
                </td>
              </tr>
            </table>
            <p style="font-size:12px; color:#8b98a5; margin:12px 0 0 0;">{LINK_PDA_WEB} (na rede da Empresa)</p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid #26303b; padding-top:22px; text-align:center;">
              <p style="font-size:12.5px; color:#a9b4bf; margin:0 0 14px 0;">Feito com carinho por</p>
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="padding:0 16px; text-align:center;">
                    <img src="cid:foto_igor" width="56" height="56" style="width:56px; height:56px; border-radius:50%; display:block; margin:0 auto 6px auto; border:2px solid #2db8cf;" alt="Igor Leal">
                    <div style="font-size:12px; color:#2db8cf; font-weight:700;">Igor Leal</div>
                  </td>
                  <td style="padding:0 16px; text-align:center;">
                    <img src="cid:foto_debora" width="56" height="56" style="width:56px; height:56px; border-radius:50%; display:block; margin:0 auto 6px auto; border:2px solid #b0cb1c;" alt="Debora Sampaio">
                    <div style="font-size:12px; color:#b0cb1c; font-weight:700;">Debora Sampaio</div>
                  </td>
                </tr>
              </table>
              <p style="font-size:11px; color:#6b7785; margin:18px 0 0 0;">PDA · Painel de Automações · no ar desde 05/08/2026</p>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def status() -> dict:
    with _lock:
        registro = _ler().get(ID_COMUNICADO) or {}
    enviados = registro.get("enviados") or {}
    lista = destinatarios()
    return {"ok": True, "destinatarios": len(lista), "enviados": len(enviados),
            "pendentes": sum(1 for _, _, e in lista if e.lower() not in enviados),
            "falhas": len(registro.get("falhas") or {}), "iniciado_em": registro.get("iniciado_em"), "por": registro.get("por"),
            "em_andamento": _em_andamento["ativo"]}


def _enviar_todos(por: str, enviar=None) -> None:
    enviar = enviar or _enviar_email_com_fotos
    try:
        smtp_info = _config_email_boas_vindas()
        for login, nome, email in destinatarios():
            with _lock:
                dados = _ler()
                registro = dados.setdefault(ID_COMUNICADO, {})
                if email.lower() in (registro.get("enviados") or {}):
                    continue
            try:
                enviar(destinatario=email, assunto=ASSUNTO_V3, corpo_html=montar_email_v3_html(nome), smtp_info=smtp_info)
                resultado = ("enviados", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            except Exception as e:
                logger.exception("Comunicado da v3: falha ao mandar pra %s.", email)
                resultado = ("falhas", str(e)[:200])
            with _lock:
                dados = _ler()
                registro = dados.setdefault(ID_COMUNICADO, {})
                registro.setdefault(resultado[0], {})[email.lower()] = resultado[1]
                if resultado[0] == "enviados":
                    (registro.get("falhas") or {}).pop(email.lower(), None)
                _gravar(dados)
            time.sleep(0.5)  # não metralhar o servidor de e-mail
    except Exception:
        logger.exception("Comunicado da v3: envio interrompido.")
    finally:
        _em_andamento["ativo"] = False
        logger.info("Comunicado da v3: rodada disparada por '%s' terminou (%s).", por, status())


def disparar(por: str, enviar=None) -> dict:
    """Manda (numa thread) pra quem ainda não recebeu. Devolve o status na hora."""
    with _lock:
        if _em_andamento["ativo"]:
            return {"ok": False, "erro": "o envio já está em andamento"}
        dados = _ler()
        registro = dados.setdefault(ID_COMUNICADO, {})
        registro.setdefault("iniciado_em", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        registro["por"] = por
        _gravar(dados)
        _em_andamento["ativo"] = True
    if not any(e.lower() not in (registro.get("enviados") or {}) for _, _, e in destinatarios()):
        _em_andamento["ativo"] = False
        return {"ok": False, "erro": "todo mundo já recebeu o comunicado da v3"}
    threading.Thread(target=_enviar_todos, args=(por, enviar), daemon=True, name="ComunicadoV3").start()
    return {**status(), "ok": True}
