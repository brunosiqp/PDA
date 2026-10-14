"""Central de Monitores editável (3.2.8.0).

Até a 3.2.7.2 os clientes, links, servidores e logos ficavam fixos no JS da página. Agora ficam em
central_monitores.json (fora do git, como os outros dados que o PDA grava); sem o arquivo, vale CLIENTES_PADRAO.
A página continua pública (sem login), mas a aba Editar e a gravação só existem pra quem é administrador E tem a
permissão à parte pode_editar_central.

A página é pública, então tudo que vem da edição é conferido aqui antes de gravar: URL só http/https, cor/fundo
sem nada que saia do atributo style, logo só imagem em data URI (ou um dos logos embutidos) e texto sem < >.
"""
import copy
import hashlib
import json
import logging
import os
import re
import threading
from typing import Optional

from areas.central_monitores.dados_padrao import CLIENTES_PADRAO
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

# os mesmos tipos e ambientes do JS da página (TYPES / ENVS)
TIPOS = ("NFe", "NFCe", "CTe", "MDFe", "NFSe", "NFSeR", "NFSe Soft", "Publicador", "PowerDocs", "ClienteI",
         "RabbitMQ", "Graylog", "Kubernetes", "FTP", "Servidor", "Outros")
AMBIENTES = ("PRD", "HML")
MAX_CLIENTES = 100
MAX_LINKS = 80
MAX_GRUPOS_SERVIDORES = 30
MAX_ITENS_GRUPO = 60
MAX_APLICACOES = 40
MAX_PRODUTOS = 40
MAX_BYTES_LOGO = 400 * 1024          # data URI da logo (a tela reduz pra 128 px antes de mandar)
MAX_BYTES_TOTAL = 5 * 1024 * 1024    # o JSON inteiro

_RE_COR = re.compile(r"^[#a-zA-Z0-9(),.%\s-]{1,160}$")   # #hex, oklch(...), linear-gradient(...): sem ; " ' < >
_RE_INICIAIS = re.compile(r"^[A-Za-z0-9]{1,3}$")
_RE_LOGO_EMBUTIDO = re.compile(r"^__LOGO(_MONITOR_[A-Z0-9]+)?__$")
_RE_LOGO_DATA = re.compile(r"^data:image/(png|jpeg|webp|gif);base64,[A-Za-z0-9+/]+=*$")
_RE_URL = re.compile(r"^https?://[^\s\"'<>`]{1,500}$", re.IGNORECASE)
_RE_HOST = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
_RE_PRODUTO = re.compile(r"^[A-Za-z0-9 ._()+-]{1,40}$")

# links trocados a pedido depois que a Central virou editável: valem também pra quem já salvou pela aba Editar
LINKS_ATUALIZADOS = {
    "https://cliente_h.example.app/powerdocs#/": "https://cliente_h.example.app/powerdocs/#/login",  # 3.3.1.0
}

_lock = threading.Lock()


def _caminho() -> str:
    return os.path.join(_base_path_app(), "central_monitores.json")


def carregar() -> list:
    """Clientes atuais (o arquivo gravado pela aba Editar ou, sem ele, o padrão)."""
    try:
        with open(_caminho(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        if isinstance(dados, dict) and isinstance(dados.get("clientes"), list):
            for c in dados["clientes"]:
                for l in (c.get("links") or []) if isinstance(c, dict) else []:
                    if isinstance(l, dict) and l.get("url") in LINKS_ATUALIZADOS:
                        l["url"] = LINKS_ATUALIZADOS[l["url"]]
            return dados["clientes"]
        logger.warning("central_monitores.json sem a lista de clientes; usando o padrão.")
    except FileNotFoundError:
        pass
    except Exception:
        logger.exception("Não foi possível ler central_monitores.json; usando o padrão.")
    return copy.deepcopy(CLIENTES_PADRAO)


def versao(clientes: list) -> str:
    """Marca da versão dos dados: quem salva manda a que abriu, e se alguém salvou no meio a gravação é recusada."""
    return hashlib.sha1(json.dumps(clientes, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def pode_editar(sessao: Optional[dict]) -> bool:
    """Administrador (no usuarios.json atual) E a permissão à parte pode_editar_central."""
    if not sessao:
        return False
    info = USUARIOS_WEB.get(sessao.get("usuario")) or {}
    return bool(info.get("admin")) and info.get("ativo", True) and bool(sessao.get("pode_editar_central"))


def _texto(valor, nome: str, maximo: int, obrigatorio: bool = True) -> str:
    texto = " ".join(str(valor or "").split())
    if obrigatorio and not texto:
        raise ValueError(f"{nome} está vazio")
    if len(texto) > maximo:
        raise ValueError(f"{nome} passa de {maximo} caracteres")
    if "<" in texto or ">" in texto:
        raise ValueError(f"{nome} não pode ter < ou >")
    return texto


def _ambiente(valor) -> str:
    env = str(valor or "PRD").strip().upper()
    if env not in AMBIENTES:
        raise ValueError(f"ambiente inválido: {env}")
    return env


def _cliente(c: dict, n: int) -> dict:
    if not isinstance(c, dict):
        raise ValueError(f"cliente {n} inválido")
    nome = _texto(c.get("name"), f"o nome do cliente {n}", 40)
    onde = f"no cliente {nome}"
    cor = str(c.get("color") or "").strip()
    if cor and not _RE_COR.match(cor):
        raise ValueError(f"cor inválida {onde}")
    fundo = str(c.get("logoBg") or "").strip()
    if fundo and not _RE_COR.match(fundo):
        raise ValueError(f"fundo da logo inválido {onde}")
    iniciais = str(c.get("initials") or "").strip().upper()
    if iniciais and not _RE_INICIAIS.match(iniciais):
        raise ValueError(f"as iniciais {onde} têm que ser de 1 a 3 letras ou números")
    logo = str(c.get("logo") or "").strip()
    if logo and not (_RE_LOGO_EMBUTIDO.match(logo) or _RE_LOGO_DATA.match(logo)):
        raise ValueError(f"logo inválida {onde} (só PNG, JPG, WebP ou GIF)")
    if len(logo) > MAX_BYTES_LOGO:
        raise ValueError(f"a logo {onde} está grande demais")

    links = c.get("links") or []
    if not isinstance(links, list) or len(links) > MAX_LINKS:
        raise ValueError(f"links demais {onde} (até {MAX_LINKS})")
    links_ok = []
    for i, l in enumerate(links, 1):
        if not isinstance(l, dict):
            raise ValueError(f"link {i} inválido {onde}")
        tipo = str(l.get("type") or "").strip()
        if tipo not in TIPOS:
            raise ValueError(f"tipo inválido no link {i} {onde}")
        url = str(l.get("url") or "").strip()
        if not _RE_URL.match(url):
            raise ValueError(f"o link {i} {onde} precisa de um endereço http:// ou https:// válido")
        grupo = str(l.get("grupo") or "").strip()
        links_ok.append({"label": _texto(l.get("label"), f"o nome do link {i} {onde}", 50), "type": tipo, "url": url,
                         "env": _ambiente(l.get("env")), "grupo": "infra" if grupo == "infra" else ""})

    servidores = c.get("servidores") or []
    if not isinstance(servidores, list) or len(servidores) > MAX_GRUPOS_SERVIDORES:
        raise ValueError(f"grupos de servidores demais {onde}")
    servidores_ok = []
    for i, s in enumerate(servidores, 1):
        itens = [str(h).strip() for h in (s.get("itens") or []) if str(h).strip()] if isinstance(s, dict) else None
        if not itens or len(itens) > MAX_ITENS_GRUPO:
            raise ValueError(f"o grupo de servidores {i} {onde} precisa de 1 a {MAX_ITENS_GRUPO} endereços")
        ruins = [h for h in itens if not _RE_HOST.match(h)]
        if ruins:
            raise ValueError(f"endereço inválido {onde}: {ruins[0][:60]} (só nome de máquina ou IP, sem http://)")
        servidores_ok.append({"grupo": _texto(s.get("grupo"), f"o nome do grupo de servidores {i} {onde}", 40),
                              "env": _ambiente(s.get("env")), "itens": itens})

    aplicacoes = c.get("aplicacoes") or []
    if not isinstance(aplicacoes, list) or len(aplicacoes) > MAX_APLICACOES:
        raise ValueError(f"servidores com produtos demais {onde}")
    aplicacoes_ok = []
    for i, a in enumerate(aplicacoes, 1):
        if not isinstance(a, dict):
            raise ValueError(f"servidor com produtos {i} inválido {onde}")
        host = str(a.get("host") or "").strip()
        if not _RE_HOST.match(host):
            raise ValueError(f"endereço inválido no servidor com produtos {i} {onde}")
        produtos = [" ".join(str(p).split()) for p in (a.get("produtos") or []) if str(p).strip()]
        if not produtos or len(produtos) > MAX_PRODUTOS or not all(_RE_PRODUTO.match(p) for p in produtos):
            raise ValueError(f"produtos inválidos no servidor {host} {onde} (1 a {MAX_PRODUTOS}, só letras, números e . _ - ( ) +)")
        aplicacoes_ok.append({"host": host, "env": _ambiente(a.get("env")), "produtos": produtos})

    return {"name": nome, "sub": _texto(c.get("sub"), f"o subtítulo {onde}", 60, obrigatorio=False), "color": cor,
            "initials": iniciais, "logo": logo, "logoBg": fundo, "links": links_ok, "servidores": servidores_ok,
            "aplicacoes": aplicacoes_ok}


def validar(clientes) -> list:
    """Devolve a lista limpa ou levanta ValueError com a mensagem pra tela."""
    if not isinstance(clientes, list):
        raise ValueError("formato inválido")
    if len(clientes) > MAX_CLIENTES:
        raise ValueError(f"no máximo {MAX_CLIENTES} clientes")
    limpos = [_cliente(c, n) for n, c in enumerate(clientes, 1)]
    nomes = [c["name"].lower() for c in limpos]
    repetido = next((c["name"] for c in limpos if nomes.count(c["name"].lower()) > 1), None)
    if repetido:
        raise ValueError(f"tem dois clientes com o nome {repetido}")
    if len(json.dumps(limpos, ensure_ascii=False).encode("utf-8")) > MAX_BYTES_TOTAL:
        raise ValueError("os dados passam do tamanho máximo (logos grandes demais?)")
    return limpos


def resumo_mudancas(antes: list, depois: list) -> str:
    """Texto curto pro log: clientes criados, removidos e alterados."""
    a = {c["name"]: c for c in antes}
    d = {c["name"]: c for c in depois}
    partes = []
    novos = [n for n in d if n not in a]
    removidos = [n for n in a if n not in d]
    alterados = [n for n in d if n in a and json.dumps(a[n], sort_keys=True) != json.dumps(d[n], sort_keys=True)]
    if novos:
        partes.append("criou " + ", ".join(novos))
    if removidos:
        partes.append("removeu " + ", ".join(removidos))
    if alterados:
        partes.append("alterou " + ", ".join(alterados))
    if not partes and [c["name"] for c in antes] != [c["name"] for c in depois]:
        partes.append("mudou a ordem dos clientes")
    return "; ".join(partes) or "salvou sem mudanças"


def salvar(clientes, versao_aberta: str, por: str) -> dict:
    try:
        limpos = validar(clientes)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    with _lock:
        atuais = carregar()
        if versao_aberta != versao(atuais):
            return {"ok": False, "conflito": True,
                    "erro": "Outra pessoa salvou a Central enquanto você editava. Recarregue a página e refaça as mudanças."}
        caminho = _caminho()
        try:
            if os.path.exists(caminho):
                with open(caminho, "rb") as f:
                    anterior = f.read()
                with open(caminho + ".bak", "wb") as f:  # cópia da versão anterior, pra desfazer à mão se precisar
                    f.write(anterior)
            with open(caminho + ".tmp", "w", encoding="utf-8") as f:
                json.dump({"clientes": limpos, "alterado_por": por}, f, ensure_ascii=False, indent=1)
            os.replace(caminho + ".tmp", caminho)
        except Exception:
            logger.exception("Não foi possível gravar central_monitores.json.")
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    return {"ok": True, "versao": versao(limpos), "resumo": resumo_mudancas(atuais, limpos)}


def json_para_script(valor) -> str:
    """JSON pra entrar direto num bloco script do HTML (sem deixar fechar a tag nem quebrar em U+2028)."""
    return (json.dumps(valor, ensure_ascii=False).replace("</", "<\\/").replace(" ", "\\u2028")
            .replace(" ", "\\u2029"))


def dados_da_pagina(clientes: list) -> tuple:
    """(clients, CLIENT_META) no formato que o JS da página já usava."""
    lista, meta = [], {}
    for c in clientes:
        item = {"name": c["name"], "sub": c.get("sub") or "", "links": [], "servidores": [], "aplicacoes": []}
        for l in c.get("links") or []:
            link = {"label": l["label"], "type": l["type"], "url": l["url"], "env": l.get("env") or "PRD"}
            if l.get("grupo") == "infra":
                link["grupo"] = "infra"
            item["links"].append(link)
        item["servidores"] = [dict(s) for s in c.get("servidores") or []]
        item["aplicacoes"] = [dict(s) for s in c.get("aplicacoes") or []]
        lista.append(item)
        m = {"color": c.get("color") or "oklch(0.6 0.02 240)", "initials": c.get("initials") or c["name"][:2].upper()}
        if c.get("logo"):
            m["logo"] = c["logo"]
        if c.get("logoBg"):
            m["logoBg"] = c["logoBg"]
        meta[c["name"]] = m
    return lista, meta
