"""Notificações do sininho da navbar (3.0.1.0).

Cada pessoa tem uma lista em notificacoes.json ({login: [notificação]}), com trava e
gravação via .tmp. Quem cria é o mural (palminhas e comentários); a de versão nova não
é gravada: sai na hora quando a versão que está rodando é diferente da última que a
pessoa viu (`versao_vista` no usuarios.json), até ela abrir o sininho.

Notificação: {id, tipo ("palma"/"comentario"), de (login), evento, texto, link,
criado_em ("AAAA-MM-DD HH:MM:SS"), lida, chave}. `chave` evita duplicar (a mesma palma
batida e desfeita várias vezes vira uma notificação só) e permite apagar ao desfazer.
"""
import json
import logging
import os
import threading
import uuid
from datetime import date, datetime

from nucleo.acessos import aniversario_do_pda, anos_do_pda

from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.fotos import _caminho_foto_usuario
from nucleo.usuarios import USUARIOS_WEB, _salvar_usuarios

logger = logging.getLogger("alertas")

MAX_NOTIFICACOES_POR_PESSOA = 60
DIAS_AVISO_ANIVERSARIO_PDA = 30  # o "PDA fez N anos" fica no sininho por esse tempo, até a pessoa abrir
_lock_notificacoes = threading.Lock()


def _caminho() -> str:
    return os.path.join(_base_path_app(), "notificacoes.json")


def _carregar() -> dict:
    try:
        with open(_caminho(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("Não foi possível ler notificacoes.json, começando vazio.")
        return {}


NOTIFICACOES: dict = _carregar()


def _salvar() -> bool:
    caminho = _caminho()
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(NOTIFICACOES, f, indent=1, ensure_ascii=False)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não foi possível gravar notificacoes.json.")
        return False


def notificar(para: str, tipo: str, de: str, texto: str, evento: str = "", link: str = "", chave: str = "") -> None:
    """Cria uma notificação pra `para` (nunca pra quem fez a ação). Com `chave`, não
    duplica: se já existe uma com a mesma chave, só volta a ficar não lida e no topo."""
    if not para or para == de or para not in USUARIOS_WEB:
        return
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _lock_notificacoes:
        lista = NOTIFICACOES.setdefault(para, [])
        existente = next((n for n in lista if chave and n.get("chave") == chave), None)
        if existente:
            lista.remove(existente)
        lista.insert(0, {"id": uuid.uuid4().hex[:12], "tipo": tipo, "de": de, "evento": evento, "texto": texto,
                         "link": link, "criado_em": agora, "lida": False, "chave": chave})
        del lista[MAX_NOTIFICACOES_POR_PESSOA:]
        _salvar()


def apagar_por_chave(para: str, chave: str) -> bool:
    """Desfazer a ação (ex.: tirar a palma) apaga a notificação que ela tinha criado. Devolve se apagou alguma."""
    with _lock_notificacoes:
        lista = NOTIFICACOES.get(para) or []
        restantes = [n for n in lista if n.get("chave") != chave]
        if len(restantes) != len(lista):
            NOTIFICACOES[para] = restantes
            _salvar()
            return True
    return False


def listar(login: str, versao_atual: str) -> dict:
    """Notificações de quem está logado, mais recentes primeiro, já com nome/foto de quem
    fez. A de versão nova vem na frente enquanto a pessoa não viu essa versão."""
    with _lock_notificacoes:
        lista = [dict(n) for n in NOTIFICACOES.get(login) or []]
    for n in lista:
        info = USUARIOS_WEB.get(n.get("de")) or {}
        n["de_nome"] = info.get("nome") or n.get("de") or ""
        n["de_foto"] = bool(n.get("de")) and _caminho_foto_usuario(n["de"]) is not None
        n.pop("chave", None)
    aviso_pda = _aviso_aniversario_pda(login)
    if aviso_pda:
        lista.insert(0, aviso_pda)
    if (USUARIOS_WEB.get(login) or {}).get("versao_vista") != versao_atual:
        lista.insert(0, {"id": "versao", "tipo": "versao", "de": "", "de_nome": "PDA", "de_foto": False,
                         "texto": f"O PDA foi atualizado pra v{versao_atual}. Veja o que mudou.",
                         "link": "/changelog", "criado_em": "", "lida": False})
    return {"ok": True, "itens": lista, "nao_lidas": sum(1 for n in lista if not n.get("lida"))}


def _aviso_aniversario_pda(login: str, hoje: date = None):
    """Aniversário do PDA (criado em 05/08/2026): avisa todo mundo por DIAS_AVISO_ANIVERSARIO_PDA dias."""
    hoje = hoje or date.today()
    anos = anos_do_pda(hoje)
    if anos < 1 or (hoje - aniversario_do_pda(anos)).days > DIAS_AVISO_ANIVERSARIO_PDA:
        return None
    if f"pda_ano_{anos}" in ((USUARIOS_WEB.get(login) or {}).get("avisos_vistos") or []):
        return None
    return {"id": f"pda_ano_{anos}", "tipo": "pda", "de": "", "de_nome": "PDA", "de_foto": False,
            "texto": f"O PDA completou {anos} {'ano' if anos == 1 else 'anos'}! 🎂 Obrigado por fazer parte dessa história.",
            "link": "/?evento=pda:ano:" + str(anos), "criado_em": "", "lida": False}


# Anúncios que aparecem uma vez por pessoa (3.2.0.0), guardados em avisos_vistos do usuarios.json.
# "gif_perfil": a foto de perfil pode ser GIF; só pra quem já tem foto.
ANUNCIOS_CONHECIDOS = ("gif_perfil",)


def anuncio_pendente(login: str) -> str:
    """Id do anúncio que essa pessoa ainda não viu (ou "")."""
    info = USUARIOS_WEB.get(login) or {}
    vistos = info.get("avisos_vistos") or []
    if "gif_perfil" not in vistos and _caminho_foto_usuario(login) is not None:
        return "gif_perfil"
    return ""


def marcar_anuncio_visto(login: str, anuncio: str) -> bool:
    if anuncio not in ANUNCIOS_CONHECIDOS:
        return False
    info = USUARIOS_WEB.get(login)
    if info is None:
        return False
    vistos = info.get("avisos_vistos") or []
    if anuncio in vistos:
        return True
    info["avisos_vistos"] = vistos + [anuncio]
    return _salvar_usuarios(USUARIOS_WEB)


def marcar_lidas(login: str, versao_atual: str) -> bool:
    with _lock_notificacoes:
        mudou = False
        for n in NOTIFICACOES.get(login) or []:
            if not n.get("lida"):
                n["lida"] = True
                mudou = True
        if mudou:
            _salvar()
    info = USUARIOS_WEB.get(login)
    if info is None:
        return True
    mudou_usuario = False
    if info.get("versao_vista") != versao_atual:
        info["versao_vista"] = versao_atual
        mudou_usuario = True
    aviso_pda = _aviso_aniversario_pda(login)
    if aviso_pda:
        info["avisos_vistos"] = (info.get("avisos_vistos") or []) + [aviso_pda["id"]]
        mudou_usuario = True
    return _salvar_usuarios(USUARIOS_WEB) if mudou_usuario else True
