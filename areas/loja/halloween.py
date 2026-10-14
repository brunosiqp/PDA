"""Halloween 2026 (3.3.7.0): tema do PDA e Caça aos Doces, prontos mas só ligados de INICIO a FIM.

Fora do período nada aparece (o tema nem é mandado pras telas). Administrador vê uma prévia abrindo qualquer tela com
`?previa_halloween=1` (grava o cookie `previa_halloween`; a faixa da prévia tem o botão pra sair): na prévia os doces
aparecem, mas achar não conta.

Caça aos Doces: 7 doces escondidos (DOCES); achou os 7 dentro do período, ganha o wallpaper exclusivo EmpresaWeen 26
na Loja de Palminhas (`concluiu`, que a Loja consulta) e aviso no sininho. Depois do FIM não dá mais pra conseguir.
Achados em halloween_26.json (fora do git): {login: {"achados": [id], "concluiu_em": "AAAA-MM-DD HH:MM:SS"}}.

**Os lugares dos doces ainda vão ser definidos pelo Igor**: os 7 abaixo são os da proposta, provisórios. Cada um é
{id, dica, pagina (regex do caminho), seletor (CSS do elemento onde o doce fica), pos (posição dentro dele)}; trocar
aqui basta (o id é o que fica gravado, então não reaproveitar id de doce que já existiu).
"""
import json
import logging
import os
import threading
from datetime import date, datetime
from typing import Optional

from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.notificacoes import notificar
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas.loja")

INICIO = date(2026, 10, 24)
FIM = date(2026, 11, 1)
ARQUIVO = "halloween_26.json"
COOKIE_PREVIA = "previa_halloween"

# PROVISÓRIO: lugares da proposta de 08/10/2026, até o Igor definir os de verdade
DOCES = [
    {"id": "d1", "dica": "Onde a Comunidade termina, entre as abóboras", "pagina": r"^/$", "seletor": ".hw-chao",
     "pos": "left: calc(4% + 22px); bottom: 34px;"},
    {"id": "d2", "dica": "Quem sobe de cargo deixou um doce pra trás", "pagina": r"^/$", "seletor": "#lista-promocoes",
     "pos": "right: 6px; top: -30px;"},
    {"id": "d3", "dica": "Um alerta sempre acorda com açúcar", "pagina": r"^/$", "seletor": '.card-hub[href="/alertas"]',
     "pos": "left: 64px; top: 22px;"},
    {"id": "d4", "dica": "No topo do pódio tem mais que medalha", "pagina": r"^/ranks-produtos", "seletor": "#podio",
     "pos": "right: 8px; top: 8px;"},
    {"id": "d5", "dica": "Escondido na história do PDA, lá no comecinho", "pagina": r"^/changelog", "seletor": "#historico-v1",
     "pos": "right: 14px; top: 12px;"},
    {"id": "d6", "dica": "Olhe bem pro seu próprio reflexo", "pagina": r"^/perfil/", "seletor": ".cabecalho-perfil",
     "pos": "right: 6px; top: 6px;"},
    {"id": "d7", "dica": "Entre os monitores de um cliente", "pagina": r"^/direcionamento-webmonitors", "seletor": ".card:nth-of-type(3)",
     "pos": "right: 52px; top: 22px;"},
]
TOTAL_DOCES = len(DOCES)

_lock = threading.Lock()


def _caminho() -> str:
    return os.path.join(_base_path_app(), ARQUIVO)


def _ler() -> dict:
    try:
        with open(_caminho(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("Não foi possível ler %s, começando vazio.", ARQUIVO)
        return {}


DADOS: dict = _ler()


def _gravar() -> bool:
    try:
        with open(_caminho() + ".tmp", "w", encoding="utf-8") as f:
            json.dump(DADOS, f, ensure_ascii=False, indent=1)
        os.replace(_caminho() + ".tmp", _caminho())
        return True
    except Exception:
        logger.exception("Não foi possível gravar %s.", ARQUIVO)
        return False


def ativo(hoje: Optional[date] = None) -> bool:
    hoje = hoje or date.today()
    return INICIO <= hoje <= FIM


def achados(login: str) -> list:
    return list((DADOS.get(login) or {}).get("achados") or [])


def concluiu(login: str) -> bool:
    return bool((DADOS.get(login) or {}).get("concluiu_em"))


def config_tela(login: str, previa: bool, hoje: Optional[date] = None) -> dict:
    """O que o tema precisa saber na tela (vai como window.PDA_HALLOWEEN)."""
    return {"ativo": ativo(hoje), "previa": bool(previa), "logado": bool(login),
            "achados": achados(login) if login else [], "concluiu": concluiu(login) if login else False,
            "total": TOTAL_DOCES, "fim": FIM.strftime("%d/%m"),
            "doces": [{k: d[k] for k in ("id", "dica", "pagina", "seletor", "pos")} for d in DOCES]}


def achar_doce(login: str, id_doce: str, hoje: Optional[date] = None) -> dict:
    if login not in USUARIOS_WEB:
        return {"ok": False, "erro": "usuário não encontrado"}
    if not ativo(hoje):
        return {"ok": False, "erro": "a Caça aos Doces não está acontecendo agora"}
    if id_doce not in {d["id"] for d in DOCES}:
        return {"ok": False, "erro": "doce desconhecido"}
    with _lock:
        reg = DADOS.setdefault(login, {"achados": []})
        if id_doce in reg.setdefault("achados", []):
            return {"ok": True, "achados": len(reg["achados"]), "total": TOTAL_DOCES, "concluiu": bool(reg.get("concluiu_em")), "novo": False}
        reg["achados"].append(id_doce)
        agora_concluiu = len(reg["achados"]) >= TOTAL_DOCES and not reg.get("concluiu_em")
        if agora_concluiu:
            reg["concluiu_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if not _gravar():
            reg["achados"].remove(id_doce)
            if agora_concluiu:
                reg.pop("concluiu_em", None)
            return {"ok": False, "erro": "não foi possível guardar o doce (detalhes no log)"}
        n = len(reg["achados"])
    logger.info("Caça aos Doces: %s achou o doce %s (%d de %d).", login, id_doce, n, TOTAL_DOCES)
    if agora_concluiu:
        logger.info("Caça aos Doces: %s achou os %d doces e ganhou o wallpaper EmpresaWeen 26.", login, TOTAL_DOCES)
        notificar(login, "halloween", "pda", "Você achou os 7 doces! O wallpaper exclusivo EmpresaWeen 26 é seu 🎃",
                  link="/loja?aba=meus", chave="halloween:iw26")
    return {"ok": True, "achados": n, "total": TOTAL_DOCES, "concluiu": n >= TOTAL_DOCES, "novo": True}


def campanha(login: str, hoje: Optional[date] = None) -> Optional[dict]:
    """Bloco "Caça aos Doces" nas campanhas do início, só no período."""
    if not ativo(hoje):
        return None
    return {"id": "empresaween26", "nome": "Caça aos Doces",
            "descricao": f"Ache os {TOTAL_DOCES} doces escondidos no PDA e ganhe o wallpaper exclusivo EmpresaWeen 26.",
            "insignia": None, "fim": FIM.isoformat(), "acao": "doces", "concluida": concluiu(login),
            "concluida_em": ((DADOS.get(login) or {}).get("concluiu_em") or "")[:10] or None}
