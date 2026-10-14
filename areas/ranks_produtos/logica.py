"""Rankings (Beta, 3.0.7.0 como "Ranks por Produtos"; renomeado na 3.1.4.0): o nível de cada pessoa em cada produto.

Cada pessoa tem, por produto, um nível bronze, prata, ouro ou master (ou nenhum); o Master, acima
do ouro, entrou na 3.0.9.0. Todo mundo logado vê o ranking; os administradores atribuem os níveis
(os próprios e os de todo mundo) e mexem na lista de produtos. Os produtos no Master liberam as
insígnias de Rank Master (1, 3, 5, 7 e 10 produtos, em areas/perfil/insignias.py, via masters_de).

Dados em ranks_produtos.json (fora do git):
{"produtos": [{"id", "nome"}], "niveis": {login: {id_produto: "bronze"|"prata"|"ouro"|"master"}},
 "alteracoes": [{"quando", "por", "usuario", "produto", "de", "para"}]}  (últimas 300)
"""
import json
import logging
import os
import re
import threading
import unicodedata
from datetime import datetime

from areas.perfil.insignias import INSIGNIAS_PALMAS_ATIVAS, METAS_PALMAS, METAS_RANK_MASTER
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.fotos import _caminho_foto_usuario
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

NIVEIS = ["bronze", "prata", "ouro", "master"]
NOMES_NIVEIS = {"bronze": "Bronze", "prata": "Prata", "ouro": "Ouro", "master": "Master"}
MEDALHAS = {"bronze": "🥉", "prata": "🥈", "ouro": "🥇", "master": "👑"}
MAX_ALTERACOES = 300
# lista de partida (dá pra mudar na própria tela); só usada se o arquivo ainda não existe
PRODUTOS_INICIAIS = ["NFSe", "NFCom", "NFCe", "NFe", "AgenteNFCe", "CTe", "MDFe", "NFAg", "NF3e", "CTe2"]

_lock = threading.Lock()


def _caminho() -> str:
    return os.path.join(_base_path_app(), "ranks_produtos.json")


def _id_produto(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")[:40]


def _carregar() -> dict:
    try:
        with open(_caminho(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, dict):
            dados.setdefault("produtos", [])
            dados.setdefault("niveis", {})
            dados.setdefault("alteracoes", [])
            dados.setdefault("arquivados", {})  # ranks de quem foi desativado no PDA (3.3.1.0), pra voltar se reativar
            return dados
    except FileNotFoundError:
        pass
    except Exception:
        logger.exception("ranks_produtos.json ilegível: começando com a lista de partida.")
    return {"produtos": [{"id": _id_produto(n), "nome": n} for n in PRODUTOS_INICIAIS], "niveis": {}, "alteracoes": [], "arquivados": {}}


DADOS: dict = _carregar()


def _gravar() -> bool:
    caminho = _caminho()
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(DADOS, f, indent=1, ensure_ascii=False)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não foi possível gravar ranks_produtos.json.")
        return False


def arquivar_pessoa(login: str, por: str) -> int:
    """Desativado no PDA (3.3.1.0): sai dos Rankings de verdade. Os níveis vão pra "arquivados" (não somem: reativar
    devolve) e a mudança vai pro log "Rankings". Devolve quantos produtos a pessoa tinha."""
    with _lock:
        meus = DADOS["niveis"].pop(login, None)
        if not meus:
            return 0
        DADOS.setdefault("arquivados", {})[login] = meus
        if not _gravar():
            DADOS["niveis"][login] = DADOS["arquivados"].pop(login)
            return 0
    logging.getLogger("alertas.rankings").info("%s saiu dos Rankings (desativado no PDA por %s): %d produto(s) guardado(s).",
                                               (USUARIOS_WEB.get(login) or {}).get("nome") or login, por, len(meus))
    return len(meus)


def restaurar_pessoa(login: str, por: str) -> int:
    """Reativado no PDA: os ranks guardados na desativação voltam (sem passar por cima de algum dado depois)."""
    with _lock:
        guardados = (DADOS.get("arquivados") or {}).pop(login, None)
        if not guardados:
            return 0
        atuais = DADOS["niveis"].setdefault(login, {})
        for produto, nivel in guardados.items():
            atuais.setdefault(produto, nivel)
        if not _gravar():
            return 0
    logging.getLogger("alertas.rankings").info("%s voltou pros Rankings (reativado no PDA por %s): %d produto(s) devolvido(s).",
                                               (USUARIOS_WEB.get(login) or {}).get("nome") or login, por, len(guardados))
    return len(guardados)


def _ativo(login: str) -> bool:
    info = USUARIOS_WEB.get(login) or {}
    return info.get("ativo", True) and not login.lower().startswith("teste")


def _arquivar_quem_ja_esta_desativado() -> list:
    """Na partida (3.3.1.0): quem já estava desativado antes desta versão também sai dos Rankings (vai pros arquivados)."""
    desativados = [l for l in list(DADOS["niveis"]) if l in USUARIOS_WEB and not USUARIOS_WEB[l].get("ativo", True)]
    for login in desativados:
        arquivar_pessoa(login, "limpeza da 3.3.1.0")
    return desativados


try:
    _arquivar_quem_ja_esta_desativado()
except Exception:
    logger.exception("Não foi possível tirar dos Rankings quem já estava desativado.")


def _contagem(niveis: dict) -> dict:
    return {n: sum(1 for v in niveis.values() if v == n) for n in NIVEIS}


def masters_de(login: str) -> int:
    """Quantos produtos (dos que existem) a pessoa tem no Rank Master: é o que libera as insígnias de Rank Master."""
    with _lock:
        ids = {p["id"] for p in DADOS["produtos"]}
        return sum(1 for p, n in (DADOS["niveis"].get(login) or {}).items() if p in ids and n == "master")


def progresso_rank_master(qtd_master: int) -> dict:
    """Quantas metas de Rank Master a pessoa já alcançou (insígnias liberadas) e qual é a próxima."""
    alcancadas = [m for m in METAS_RANK_MASTER if qtd_master >= m]
    proxima = next((m for m in METAS_RANK_MASTER if qtd_master < m), None)
    return {"alcancadas": alcancadas, "proxima": proxima, "faltam": (proxima - qtd_master) if proxima else 0}


def visao(login: str, pode_editar: bool) -> dict:
    """Tudo que a tela precisa: produtos, pessoas (com níveis e contagem) e o que dá pra fazer."""
    with _lock:
        produtos = [dict(p) for p in DADOS["produtos"]]
        niveis = {l: dict(v) for l, v in DADOS["niveis"].items()}
        alteracoes = list(DADOS["alteracoes"][-15:])[::-1]
    ids = {p["id"] for p in produtos}
    pessoas = []
    for l, info in USUARIOS_WEB.items():
        if not _ativo(l):
            continue
        meus = {p: n for p, n in (niveis.get(l) or {}).items() if p in ids and n in NIVEIS}
        cont = _contagem(meus)
        pessoas.append({"login": l, "nome": info.get("nome") or l, "tem_foto": _caminho_foto_usuario(l) is not None,
                        "equipe": info.get("atribuicao") or "", "cargo": info.get("cargo") or "", "niveis": meus,
                        "contagem": cont, "pontos": cont["master"] * 4 + cont["ouro"] * 3 + cont["prata"] * 2 + cont["bronze"],
                        "rank_master": progresso_rank_master(cont["master"])})
    # ranking (3.2.4.0): por pontos, todo nível conta (Master 4, Ouro 3, Prata 2, Bronze 1); empate: mais masters, ouros,
    # pratas, bronzes, nome. É a mesma ordem do leaderboard de Produtos
    pessoas.sort(key=lambda p: (-p["pontos"], -p["contagem"]["master"], -p["contagem"]["ouro"], -p["contagem"]["prata"],
                                -p["contagem"]["bronze"], p["nome"].lower()))
    nomes = {p["id"]: p["nome"] for p in produtos}
    for a in alteracoes:
        a["produto_nome"] = nomes.get(a.get("produto"), a.get("produto"))
        a["usuario_nome"] = (USUARIOS_WEB.get(a.get("usuario")) or {}).get("nome") or a.get("usuario")
        a["por_nome"] = (USUARIOS_WEB.get(a.get("por")) or {}).get("nome") or a.get("por")
    if not pode_editar:
        alteracoes = []  # quem só visualiza não tem a aba de alterações (3.1.0.0)
    # leaderboard de palminhas recebidas no mural (3.1.3.0): todo mundo ativo com pelo menos uma, mais recebidas primeiro
    try:
        from areas.mural.logica import palmas_recebidas_por_pessoa  # aqui dentro: o mural importa as insígnias
        contagem_palmas = palmas_recebidas_por_pessoa()
    except Exception:
        logger.exception("Não foi possível contar as palminhas pro leaderboard.")
        contagem_palmas = {}
    por_login = {p["login"]: p for p in pessoas}
    palmas = sorted(({"login": l, "nome": por_login[l]["nome"], "tem_foto": por_login[l]["tem_foto"], "equipe": por_login[l]["equipe"],
                      "cargo": por_login[l]["cargo"], "palmas": n} for l, n in contagem_palmas.items() if n > 0 and l in por_login),
                    key=lambda p: (-p["palmas"], p["nome"].lower()))
    return {"ok": True, "produtos": produtos, "pessoas": pessoas, "pode_editar": pode_editar, "eu": login,
            "metas_rank_master": METAS_RANK_MASTER, "alteracoes": alteracoes,
            "palmas": palmas, "minhas_palmas": contagem_palmas.get(login, 0), "metas_palmas": METAS_PALMAS if INSIGNIAS_PALMAS_ATIVAS else [],  # desligadas na 3.1.8.0
            "por_produto": {p["id"]: _contagem({l: v.get(p["id"]) for l, v in niveis.items() if _ativo(l)}) for p in produtos}}


def definir_nivel(usuario: str, produto: str, nivel: str, por: str) -> dict:
    """nivel "" tira o rank daquele produto."""
    if usuario not in USUARIOS_WEB:
        return {"ok": False, "erro": "usuário não encontrado"}
    if nivel and nivel not in NIVEIS:
        return {"ok": False, "erro": "nível inválido"}
    with _lock:
        if not any(p["id"] == produto for p in DADOS["produtos"]):
            return {"ok": False, "erro": "produto não encontrado"}
        meus = DADOS["niveis"].setdefault(usuario, {})
        antes = meus.get(produto) or ""
        if antes == nivel:
            return {"ok": True, "mudou": False}
        if nivel:
            meus[produto] = nivel
        else:
            meus.pop(produto, None)
        DADOS["alteracoes"].append({"quando": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "por": por, "usuario": usuario,
                                    "produto": produto, "de": antes, "para": nivel})
        del DADOS["alteracoes"][:-MAX_ALTERACOES]
        if not _gravar():
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
        nome_produto = next(p["nome"] for p in DADOS["produtos"] if p["id"] == produto)
    # texto pro log "Rankings" (3.1.9.0: as últimas alterações saíram da tela e ficam no card Logs)
    nome_pessoa = (USUARIOS_WEB.get(usuario) or {}).get("nome") or usuario
    texto_log = (f"definiu {NOMES_NIVEIS[nivel]} de {nome_pessoa} em {nome_produto}" + (f" (antes {NOMES_NIVEIS[antes]})" if antes else "")
                 if nivel else f"tirou o rank de {nome_pessoa} em {nome_produto} (era {NOMES_NIVEIS[antes]})")
    if nivel and usuario != por:
        from nucleo.notificacoes import notificar
        medalha = MEDALHAS[nivel]
        nome_por = (USUARIOS_WEB.get(por) or {}).get("nome") or por
        notificar(usuario, "rank", por, f"{nome_por} definiu seu rank em {nome_produto}: {NOMES_NIVEIS[nivel]} {medalha}", "",
                  "/ranks-produtos", f"rank:{produto}:{usuario}")
    return {"ok": True, "mudou": True, "texto_log": texto_log}


def mexer_produto(acao: str, id_produto: str, nome: str) -> dict:
    """acao: criar | renomear | remover. Remover também tira os níveis daquele produto."""
    nome = " ".join((nome or "").split())[:40]
    with _lock:
        produtos = DADOS["produtos"]
        if acao == "criar":
            novo_id = _id_produto(nome)
            if not novo_id:
                return {"ok": False, "erro": "informe o nome do produto"}
            if any(p["id"] == novo_id for p in produtos):
                return {"ok": False, "erro": "esse produto já existe"}
            produtos.append({"id": novo_id, "nome": nome})
        elif acao == "renomear":
            alvo = next((p for p in produtos if p["id"] == id_produto), None)
            if not alvo or not nome:
                return {"ok": False, "erro": "produto ou nome inválido"}
            alvo["nome"] = nome
        elif acao == "remover":
            if not any(p["id"] == id_produto for p in produtos):
                return {"ok": False, "erro": "produto não encontrado"}
            DADOS["produtos"] = [p for p in produtos if p["id"] != id_produto]
            for niveis in DADOS["niveis"].values():
                niveis.pop(id_produto, None)
        else:
            return {"ok": False, "erro": "ação inválida"}
        if not _gravar():
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    return {"ok": True}
