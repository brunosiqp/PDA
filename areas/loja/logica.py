"""Loja de Palminhas (3.3.7.0): troca as palminhas recebidas por wallpapers pro perfil e pro cartão da Comunidade.

Regras combinadas com o Igor (proposta de 08/10/2026):
- saldo da Loja = palminhas recebidas (as mesmas do leaderboard, `palmas_recebidas`, retroativo: conta tudo o que a
  pessoa já recebeu) - palminhas gastas na Loja. **Gastar nunca mexe no ranking**: o leaderboard continua contando
  as recebidas;
- abas Vitrine (compra com palminhas), Eventos (itens de data especial que não estão à venda) e Meus itens; sem
  histórico pra pessoa (cada troca vai pro log "Loja"), sem selos e molduras;
- o saldo só aparece dentro da Loja;
- "Padrão Empresa" (o banner institucional) todo mundo tem e é o que aparece pra quem não escolheu outro;
- todo mundo vê o wallpaper dos outros ao abrir o perfil;
- EmpresaWeen 26 é exclusivo da Caça aos Doces do Halloween (areas/loja/halloween.py); GPTW26 fica "Em breve" e
  todo mundo ganha quando a Empresa conquistar o GPTW 2026 (`GPTW26_CONQUISTADO = True`).

Dados em loja.json (fora do git): {login: {"gastas": int, "itens": [id], "usando": id, "trocas": [{id, preco, em}]}}.
"""
import json
import logging
import os
import threading
from datetime import date, datetime
from typing import Optional

import areas.loja.halloween as halloween
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas.loja")

ARQUIVO = "loja.json"
GPTW26_CONQUISTADO = False  # virar True quando a Empresa ganhar o GPTW 2026: todo mundo passa a ter o wallpaper
ITEM_PADRAO = "padrao"

ITENS = [
    {"id": "padrao", "aba": "vitrine", "tipo": "Wallpaper", "nome": "Padrão Empresa", "preco": 0,
     "desc": "O banner da Empresa: todo mundo tem e é o que aparece pra quem não escolheu outro."},
    {"id": "67", "aba": "vitrine", "tipo": "Wallpaper", "nome": "67", "preco": 67,
     "desc": 'Six seven 🤲: o 6 e o 7 balançando, selo "67" no seu nome e anel laranja na foto.'},
    {"id": "iw26", "aba": "eventos", "tipo": "Wallpaper de evento", "nome": "EmpresaWeen 26", "evento": "Halloween 2026",
     "inicio": halloween.INICIO.isoformat(), "fim": halloween.FIM.isoformat(), "exclusivo": True,
     "desc": f'Ache os {halloween.TOTAL_DOCES} doces escondidos no PDA durante o Halloween. Selo "🎃 26" no nome e anel laranja na foto. Exclusivo: depois do evento não dá mais pra conseguir.'},
    {"id": "gptw26", "aba": "eventos", "tipo": "Wallpaper de evento", "nome": "GPTW26", "evento": "Great Place To Work 2026",
     "empresa": True,
     "desc": 'Todo mundo ganha quando a Empresa conquistar o GPTW 2026. Selo GPTW na capa e no cartão e chip "GPTW 26" no nome.'},
]
_POR_ID = {i["id"]: i for i in ITENS}

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


def _recebidas(login: str) -> int:
    from areas.mural.logica import palmas_recebidas  # tardio: o mural também consulta a Loja (wallpaper do cartão)
    return palmas_recebidas(login)


def itens_de(login: str) -> list:
    """Ids que a pessoa tem: o padrão, o que trocou, o EmpresaWeen se achou os doces e o GPTW26 se a Empresa ganhou."""
    reg = DADOS.get(login) or {}
    tem = [ITEM_PADRAO] + [i for i in reg.get("itens") or [] if i in _POR_ID and i != ITEM_PADRAO]
    if halloween.concluiu(login) and "iw26" not in tem:
        tem.append("iw26")
    if GPTW26_CONQUISTADO and "gptw26" not in tem:
        tem.append("gptw26")
    return tem


def wallpaper_de(login: str) -> str:
    """O wallpaper em uso (o que todo mundo vê no perfil e no cartão); padrão se o escolhido não vale mais."""
    usando = (DADOS.get(login) or {}).get("usando") or ITEM_PADRAO
    return usando if usando in itens_de(login) else ITEM_PADRAO


def saldo(login: str) -> dict:
    recebidas = _recebidas(login)
    gastas = int((DADOS.get(login) or {}).get("gastas") or 0)
    return {"recebidas": recebidas, "gastas": gastas, "saldo": max(recebidas - gastas, 0)}


def visao(login: str, hoje: Optional[date] = None) -> dict:
    hoje = hoje or date.today()
    tem = itens_de(login)
    usando = wallpaper_de(login)
    itens = []
    for it in ITENS:
        estado = "meu" if it["id"] in tem else "loja"
        if it["aba"] == "eventos" and estado != "meu":
            if it.get("empresa"):
                estado = "breve"
            elif hoje.isoformat() < it["inicio"]:
                estado = "antes"
            elif hoje.isoformat() > it["fim"]:
                estado = "encerrado"
            else:
                estado = "vivo"
        itens.append({**it, "tem": it["id"] in tem, "usando": it["id"] == usando, "estado": estado})
    return {"ok": True, **saldo(login), "usando": usando, "itens": itens, "hoje": hoje.isoformat(),
            "doces": {"achados": len(halloween.achados(login)), "total": halloween.TOTAL_DOCES, "ativo": halloween.ativo(hoje)}}


def comprar(login: str, id_item: str, usar: bool = False) -> dict:
    """Troca palminhas por um item da Vitrine. O ranking não muda (só soma em `gastas`)."""
    if login not in USUARIOS_WEB:
        return {"ok": False, "erro": "usuário não encontrado"}
    it = _POR_ID.get(id_item)
    if not it or it["aba"] != "vitrine" or not it.get("preco"):
        return {"ok": False, "erro": "esse item não está à venda"}
    with _lock:
        if id_item in itens_de(login):
            return {"ok": False, "erro": "você já tem esse item"}
        s = saldo(login)
        if s["saldo"] < it["preco"]:
            return {"ok": False, "erro": f"faltam {it['preco'] - s['saldo']} palminhas"}
        reg = DADOS.setdefault(login, {})
        antes = json.loads(json.dumps(reg))
        reg["gastas"] = int(reg.get("gastas") or 0) + it["preco"]
        reg.setdefault("itens", []).append(id_item)
        reg.setdefault("trocas", []).append({"id": id_item, "preco": it["preco"], "em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        if usar:
            reg["usando"] = id_item
        if not _gravar():
            DADOS[login] = antes
            return {"ok": False, "erro": "não foi possível gravar a troca (detalhes no log)"}
    logger.info("Loja: %s trocou %d palminhas por %s (saldo %d -> %d).", login, it["preco"], it["nome"], s["saldo"], s["saldo"] - it["preco"])
    return visao(login)


def usar(login: str, id_item: str) -> dict:
    if login not in USUARIOS_WEB:
        return {"ok": False, "erro": "usuário não encontrado"}
    if id_item not in itens_de(login):
        return {"ok": False, "erro": "você não tem esse item"}
    with _lock:
        reg = DADOS.setdefault(login, {})
        antes = reg.get("usando")
        reg["usando"] = id_item
        if not _gravar():
            if antes is None:
                reg.pop("usando", None)
            else:
                reg["usando"] = antes
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    logger.info("Loja: %s passou a usar %s.", login, _POR_ID[id_item]["nome"])
    return visao(login)
