"""Publicações manuais na Comunidade (3.2.6.0): post com texto, fotos/GIFs e arquivos anexados.

Desde a 3.4.6.0 todo mundo ativo publica (`pode_postar`); marcar como Importante (sininho pra todos e Teams) é de
administrador ou de quem tem a permissão pode_publicar_comunidade (`pode_marcar_importante`; antes ela era pra publicar). Fica em mural_posts.json ({id: post}) e os arquivos
em anexos_mural/ (os dois fora do git). Cada post vira um evento do feed (`post:<id>`, montado em
areas/mural/logica.py), com palminhas e comentários como os outros. "Importante" avisa todo mundo ativo no
sininho. Quem publicou ou um administrador apaga (some o post, os arquivos e os comentários dele).

Este módulo não importa areas/mural/logica.py (é o logica.py que importa daqui).
"""
import base64
import json
import logging
import os
import re
import threading
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.equipes import _pertence_a_equipe
from nucleo.fotos import _caminho_foto_usuario
from nucleo.notificacoes import apagar_por_chave, notificar
from nucleo.teams_comunidade import avisar as _avisar_teams_comunidade, enviar_agora as _enviar_teams_agora
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

MAX_TEXTO_POST = 3000
MAX_IMAGENS_POST = 6
MAX_ANEXOS_POST = 4
MAX_BYTES_IMAGEM = 5 * 1024 * 1024      # foto/GIF: até 5 MB cada
MAX_BYTES_ANEXO = 10 * 1024 * 1024      # outros arquivos: até 10 MB cada (mesmo teto dos anexos do Feedbacks)
MAX_BYTES_TOTAL = 80 * 1024 * 1024      # somando tudo de uma publicação (era 30 MB até a 3.4.2.0, que trouxe vídeo)
# vídeo na publicação (3.4.2.0): MP4, WebM ou MOV, assinatura conferida, toca direto no feed
MAX_VIDEOS_POST = 2
MAX_BYTES_VIDEO = 50 * 1024 * 1024
TIPOS_VIDEO = ("video/mp4", "video/webm", "video/quicktime")
# imagem que o navegador mostra no feed: confere a assinatura (não basta o tipo que veio na data URL)
ASSINATURAS_IMAGEM = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}

# votação na publicação (3.3.0.0): 2 a 6 opções, dá pra mudar até encerrar (votos públicos desde a 3.3.6.0)
MIN_OPCOES_VOTACAO = 2
MAX_OPCOES_VOTACAO = 6
MAX_TEXTO_OPCAO = 100
MAX_DIAS_VOTACAO = 30  # o post sai do feed em 30 dias, então a votação não passa disso

# pra quem é a publicação (3.3.1.0): "" = todo mundo, ou uma equipe
PUBLICOS = ("", "Suporte", "Monitoramento", "Serviços")

_lock_posts = threading.Lock()


def _pasta_arquivos() -> str:
    pasta = os.path.join(_base_path_app(), "anexos_mural")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _caminho_json() -> str:
    return os.path.join(_base_path_app(), "mural_posts.json")


def _ler() -> dict:
    try:
        with open(_caminho_json(), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("Não foi possível ler mural_posts.json, começando vazio.")
        return {}


def _gravar() -> bool:
    caminho = _caminho_json()
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(POSTS, f, indent=1, ensure_ascii=False)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não foi possível gravar mural_posts.json.")
        return False


POSTS: dict = _ler()


def pode_postar(login: str) -> bool:
    """3.4.6.0 (pedido do Igor): qualquer pessoa ativa publica (fotos, vídeo, arquivos, votação, em grupo)."""
    info = USUARIOS_WEB.get(login)
    return bool(info) and info.get("ativo", True) and not login.lower().startswith("teste")


def pode_marcar_importante(login: str) -> bool:
    """Publicação importante (aviso no sininho de quem vê e envio ao Teams): administrador ou a permissão à parte
    pode_publicar_comunidade (3.4.6.0; até a 3.4.5.0 ela era a permissão de publicar). Lê o usuarios.json atual."""
    info = USUARIOS_WEB.get(login) or {}
    return info.get("ativo", True) and (bool(info.get("admin")) or bool(info.get("pode_publicar_comunidade")))


def _nome(login: str) -> str:
    return (USUARIOS_WEB.get(login) or {}).get("nome") or login


def _decodificar(data_url: str):
    m = re.match(r"^data:([\w.+/-]*);base64,(.+)$", data_url or "", re.DOTALL)
    if not m:
        return None, None
    try:
        return m.group(1).lower(), base64.b64decode(m.group(2), validate=True)
    except Exception:
        return None, None


def _nome_seguro(nome: str) -> str:
    base = os.path.basename((nome or "").replace("\\", "/")).strip()
    return (re.sub(r"[^A-Za-z0-9_.-]", "_", base) or "arquivo")[:80]


def _eh_imagem(tipo: str, conteudo: bytes) -> bool:
    assinaturas = ASSINATURAS_IMAGEM.get(tipo)
    if not assinaturas or not conteudo.startswith(assinaturas):
        return False
    return tipo != "image/webp" or conteudo[8:12] == b"WEBP"


def _eh_video(tipo: str, conteudo: bytes) -> bool:
    """MP4/MOV têm "ftyp" no byte 4; WebM começa com o cabeçalho EBML. Nome ou tipo sozinhos não bastam."""
    if tipo not in TIPOS_VIDEO:
        return False
    if tipo == "video/webm":
        return conteudo.startswith(b"\x1a\x45\xdf\xa3")
    return conteudo[4:8] == b"ftyp"


def _momento_fim(fim: str) -> Optional[datetime]:
    """Quando a votação encerra. "AAAA-MM-DDTHH:MM" (3.3.7.0, prazo com hora) encerra nesse minuto; "AAAA-MM-DD" (antes
    da 3.3.7.0) vale o dia inteiro, então encerra à meia-noite seguinte. Vazio = sem prazo."""
    fim = str(fim or "").strip()
    if not fim:
        return None
    if "T" in fim:
        return datetime.strptime(fim[:16], "%Y-%m-%dT%H:%M")
    return datetime.combine(date.fromisoformat(fim), datetime.min.time()) + timedelta(days=1)


def _agora(hoje=None) -> datetime:
    """Relógio da votação: sem nada, agora; com um datetime, ele; com um date (testes), esse dia ao meio-dia."""
    if hoje is None:
        return datetime.now()
    if isinstance(hoje, datetime):
        return hoje
    return datetime.now() if hoje == date.today() else datetime.combine(hoje, datetime.min.time()) + timedelta(hours=12)


def _validar_votacao(votacao, hoje: date):
    """{"opcoes": [texto], "multipla": bool, "fim": "AAAA-MM-DDTHH:MM" (ou "AAAA-MM-DD") ou ""} -> (votação pronta, erro)."""
    if not votacao:
        return None, None
    if not isinstance(votacao, dict):
        return None, "votação inválida"
    textos = [" ".join(str(o or "").split()) for o in (votacao.get("opcoes") or [])]
    textos = [o for o in textos if o]
    if not MIN_OPCOES_VOTACAO <= len(textos) <= MAX_OPCOES_VOTACAO:
        return None, f"a votação precisa de {MIN_OPCOES_VOTACAO} a {MAX_OPCOES_VOTACAO} opções"
    if any(len(o) > MAX_TEXTO_OPCAO for o in textos):
        return None, f"cada opção pode ter até {MAX_TEXTO_OPCAO} caracteres"
    if len({o.lower() for o in textos}) != len(textos):
        return None, "tem opção repetida na votação"
    fim = str(votacao.get("fim") or "").strip()[:16]
    if fim:
        try:
            momento = _momento_fim(fim)
        except ValueError:
            return None, "data de encerramento inválida"
        agora = _agora(hoje)
        if momento <= agora:
            return None, "o encerramento da votação tem que ser depois de agora"
        if momento > agora + timedelta(days=MAX_DIAS_VOTACAO):
            return None, f"a votação pode durar até {MAX_DIAS_VOTACAO} dias"
    return {"opcoes": [{"id": f"o{n}", "texto": o} for n, o in enumerate(textos, 1)],
            "multipla": bool(votacao.get("multipla")), "fim": fim}, None


MAX_COAUTORES = 30  # publicação em grupo (3.4.1.0): quem publica + até 30 pessoas


def autores_do_post(post: dict) -> list:
    """Quem publicou: o autor e, numa publicação em grupo (3.4.1.0), as pessoas escolhidas (todas recebem as palminhas)."""
    return list(post.get("autores") or [post.get("autor")])


def nome_dos_autores(post: dict) -> str:
    """"Fulano", "Fulano e Beltrano" ou "Fulano, Beltrano e Ciclano" (cartão do Teams)."""
    nomes = [_nome(l) for l in autores_do_post(post) if l]
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def pessoas_para_grupo() -> list:
    """Quem dá pra pôr numa publicação em grupo: ativos, sem login de teste, a equipe junto pra marcar por equipe."""
    return sorted(({"login": l, "nome": i.get("nome") or l, "equipe": i.get("atribuicao") or "",
                    "tem_foto": _caminho_foto_usuario(l) is not None}
                   for l, i in USUARIOS_WEB.items() if i.get("ativo", True) and not l.lower().startswith("teste")),
                  key=lambda p: p["nome"].lower())


def _validar_coautores(autor: str, coautores) -> tuple:
    """(lista limpa, erro). Só gente ativa, sem repetir, sem o próprio autor."""
    limpos = []
    for l in coautores or []:
        l = str(l or "").strip()
        if not l or l == autor or l in limpos:
            continue
        info = USUARIOS_WEB.get(l)
        if info is None or not info.get("ativo", True) or l.lower().startswith("teste"):
            return [], f"'{l}' não pode entrar na publicação em grupo"
        limpos.append(l)
    if len(limpos) > MAX_COAUTORES:
        return [], f"no máximo {MAX_COAUTORES} pessoas além de você numa publicação em grupo"
    return limpos, None


def pode_ver_post(post: dict, login: str) -> bool:
    """Publicação de equipe (3.3.1.0): só a equipe ("Suporte e Monitoramento" entra nas duas) e quem publicou.
    Sem equipe: todo mundo. 3.3.8.2 (o Igor pediu pra garantir): administrador de outra equipe NÃO vê mais (antes via
    tudo pra moderar e uma votação do Monitoramento apareceu pra quem é do Suporte), quem está sem equipe no cadastro
    não conta como Suporte e sem login não vê. Vale no feed, no voto, nos comentários, nos arquivos, no sininho."""
    publico = post.get("publico") or ""
    if not publico:
        return True
    if not login:
        return False
    if login in autores_do_post(post):  # quem publicou (e, desde a 3.4.1.0, quem está no grupo que publicou)
        return True
    equipe = ((USUARIOS_WEB.get(login) or {}).get("atribuicao") or "").strip()
    return bool(equipe) and _pertence_a_equipe(equipe, publico)


def criar_post(autor: str, texto: str, importante: bool, arquivos: list, votacao=None, hoje: Optional[date] = None,
               publico: str = "", coautores=None) -> dict:
    """arquivos = [(nome, data_url)]. Imagem válida (PNG, JPEG, GIF, WebP) vira foto do post; o resto, anexo.
    votacao (opcional, 3.3.0.0) = {"opcoes": [texto], "multipla": bool, "fim": "AAAA-MM-DD" ou ""}.
    Confere tudo antes de gravar qualquer arquivo."""
    if not pode_postar(autor):
        return {"ok": False, "erro": "você não tem permissão pra publicar na Comunidade"}
    if importante and not pode_marcar_importante(autor):
        return {"ok": False, "erro": "marcar como importante precisa da permissão \"Publicar como importante\" (peça a um administrador)"}
    texto = (texto or "").replace("\r\n", "\n").strip()
    if len(texto) > MAX_TEXTO_POST:
        return {"ok": False, "erro": f"texto muito longo (até {MAX_TEXTO_POST} caracteres)"}
    publico = (publico or "").strip()
    if publico not in PUBLICOS:
        return {"ok": False, "erro": "escolha pra quem é a publicação: todo mundo, Suporte, Monitoramento ou Serviços"}
    votacao, erro_votacao = _validar_votacao(votacao, hoje or date.today())
    if erro_votacao:
        return {"ok": False, "erro": erro_votacao}
    coautores, erro_grupo = _validar_coautores(autor, coautores)
    if erro_grupo:
        return {"ok": False, "erro": erro_grupo}
    if votacao and not texto:
        return {"ok": False, "erro": "escreva a pergunta da votação no texto da publicação"}
    imagens, videos, anexos = [], [], []
    for nome, data_url in arquivos:
        tipo, conteudo = _decodificar(data_url)
        if conteudo is None:
            return {"ok": False, "erro": f"não foi possível ler o arquivo {nome or ''}".strip()}
        if not conteudo:
            return {"ok": False, "erro": f"o arquivo {nome} está vazio"}
        if _eh_imagem(tipo, conteudo):
            if len(conteudo) > MAX_BYTES_IMAGEM:
                return {"ok": False, "erro": f"a imagem {nome} passa de {MAX_BYTES_IMAGEM // (1024 * 1024)} MB"}
            imagens.append((nome, tipo, conteudo))
        elif _eh_video(tipo, conteudo):
            if len(conteudo) > MAX_BYTES_VIDEO:
                return {"ok": False, "erro": f"o vídeo {nome} passa de {MAX_BYTES_VIDEO // (1024 * 1024)} MB"}
            videos.append((nome, tipo, conteudo))
        else:
            if len(conteudo) > MAX_BYTES_ANEXO:
                return {"ok": False, "erro": f"o arquivo {nome} passa de {MAX_BYTES_ANEXO // (1024 * 1024)} MB"}
            anexos.append((nome, tipo, conteudo))
    if len(imagens) > MAX_IMAGENS_POST:
        return {"ok": False, "erro": f"no máximo {MAX_IMAGENS_POST} fotos/GIFs por publicação"}
    if len(videos) > MAX_VIDEOS_POST:
        return {"ok": False, "erro": f"no máximo {MAX_VIDEOS_POST} vídeos por publicação"}
    if len(anexos) > MAX_ANEXOS_POST:
        return {"ok": False, "erro": f"no máximo {MAX_ANEXOS_POST} arquivos anexados por publicação"}
    if sum(len(c) for _, _, c in imagens + videos + anexos) > MAX_BYTES_TOTAL:
        return {"ok": False, "erro": f"os arquivos somam mais de {MAX_BYTES_TOTAL // (1024 * 1024)} MB"}
    if not texto and not imagens and not videos and not anexos:
        return {"ok": False, "erro": "escreva alguma coisa ou adicione uma foto ou arquivo"}

    id_post = uuid.uuid4().hex[:10]
    salvos, gravados = [], []
    try:
        for n, (nome, tipo, conteudo) in enumerate(imagens + videos + anexos):
            arquivo = f"{id_post}_{n}_{_nome_seguro(nome)}"
            caminho = os.path.join(_pasta_arquivos(), arquivo)
            with open(caminho, "wb") as f:
                f.write(conteudo)
            gravados.append(caminho)
            salvos.append({"arquivo": arquivo, "nome": (nome or arquivo)[:120], "tipo": tipo or "application/octet-stream",
                           "tamanho": len(conteudo), "imagem": n < len(imagens),
                           "video": len(imagens) <= n < len(imagens) + len(videos)})
    except Exception:
        logger.exception("Não foi possível gravar os arquivos da publicação.")
        for c in gravados:
            try:
                os.remove(c)
            except OSError:
                pass
        return {"ok": False, "erro": "não foi possível gravar os arquivos (detalhes no log)"}

    post = {"id": id_post, "autor": autor, "texto": texto, "importante": bool(importante),
            "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "arquivos": salvos, "publico": publico}
    if coautores:  # publicação em grupo (3.4.1.0): todos aparecem como autores e recebem as palminhas
        post["autores"] = [autor] + coautores
    if votacao:
        post["votacao"] = votacao
        post["votos"] = {}
    with _lock_posts:
        POSTS[id_post] = post
        if not _gravar():
            POSTS.pop(id_post, None)
            for c in gravados:
                try:
                    os.remove(c)
                except OSError:
                    pass
            return {"ok": False, "erro": "não foi possível gravar a publicação (detalhes no log)"}

    autores = autores_do_post(post)
    for outro in autores[1:]:  # quem foi posto no grupo fica sabendo
        notificar(outro, "post", autor, f"👥 {_nome(autor)} te colocou numa publicação em grupo na Comunidade",
                  "post:" + id_post, "/?evento=post:" + id_post, "grupo:" + id_post)
    if post["importante"]:
        resumo = " ".join(texto.split())
        resumo = resumo if len(resumo) <= 90 else resumo[:87] + "..."
        aviso = (f"📢 {_nome(autor)} publicou um aviso importante" + (f" pra equipe {publico}" if publico else "")
                 + (f": \"{resumo}\"" if resumo else " na Comunidade"))
        for login, info in USUARIOS_WEB.items():
            if (login not in autores and info.get("ativo", True) and not login.lower().startswith("teste")
                    and pode_ver_post(post, login)):
                notificar(login, "post", autor, aviso, "post:" + id_post, "/?evento=post:" + id_post, "post:" + id_post)
        _avisar_teams_comunidade(post, nome_dos_autores(post), publico)  # retransmite no canal do Teams (3.3.1.0)
    return {"ok": True, "id": id_post}


def reenviar_teams(id_post: str, login: str) -> dict:
    """Manda de novo o cartão de uma publicação importante pro Teams (3.3.4.2), sem mexer em palminhas e comentários.
    Só administrador; serve pra quando o Workflow foi cadastrado depois ou o Teams falhou na hora."""
    if not (USUARIOS_WEB.get(login) or {}).get("admin"):
        return {"ok": False, "erro": "só administradores reenviam ao Teams"}
    with _lock_posts:
        post = POSTS.get(id_post)
        post = dict(post) if post else None
    if post is None:
        return {"ok": False, "erro": "publicação não encontrada"}
    if not post.get("importante"):
        return {"ok": False, "erro": "só publicações importantes vão pro Teams"}
    return _enviar_teams_agora(post, nome_dos_autores(post), post.get("publico") or "")


def apagar_post(id_post: str, login: str) -> dict:
    """Quem publicou ou um administrador. Leva junto os arquivos."""
    admin = bool((USUARIOS_WEB.get(login) or {}).get("admin"))
    with _lock_posts:
        post = POSTS.get(id_post)
        if post is None:
            return {"ok": False, "erro": "publicação não encontrada"}
        if post["autor"] != login and not admin:
            return {"ok": False, "erro": "só quem publicou (ou um administrador) apaga"}
        POSTS.pop(id_post)
        if not _gravar():
            POSTS[id_post] = post
            return {"ok": False, "erro": "não foi possível apagar (detalhes no log)"}
    for a in post.get("arquivos") or []:
        try:
            os.remove(os.path.join(_pasta_arquivos(), a["arquivo"]))
        except OSError:
            pass
    return {"ok": True, "post": post}


def _votacao_encerrada(votacao: dict, hoje=None) -> bool:
    momento = _momento_fim(votacao.get("fim"))
    return momento is not None and _agora(hoje) >= momento


def visao_votacao(post: dict, login: str, hoje: Optional[date] = None) -> Optional[dict]:
    """Como a votação aparece pra `login`: opções com a contagem, o que ele marcou, quantas pessoas votaram e, desde a
    3.3.6.0 (pedido do Igor: votação pública), quem votou em cada opção (`quem`, mais recente primeiro)."""
    votacao = post.get("votacao")
    if not votacao:
        return None
    votos = post.get("votos") or {}
    contagem = {o["id"]: 0 for o in votacao["opcoes"]}
    quem = {o["id"]: [] for o in votacao["opcoes"]}
    for votante, escolhas in reversed(list(votos.items())):
        info = USUARIOS_WEB.get(votante) or {}
        pessoa = {"login": votante, "nome": info.get("nome") or votante, "equipe": info.get("atribuicao") or "",
                  "tem_foto": _caminho_foto_usuario(votante) is not None, "eu": votante == login}
        for i in escolhas:
            if i in contagem:
                contagem[i] += 1
                quem[i].append(pessoa)
    return {"opcoes": [{"id": o["id"], "texto": o["texto"], "votos": contagem[o["id"]], "quem": quem[o["id"]]} for o in votacao["opcoes"]],
            "multipla": votacao.get("multipla", False), "fim": votacao.get("fim") or "",
            # momento exato do encerramento (a tela fecha a votação sozinha quando ele passa, sem recarregar)
            "fim_em": (_momento_fim(votacao.get("fim")) or datetime.min).strftime("%Y-%m-%dT%H:%M") if votacao.get("fim") else "",
            "encerrada": _votacao_encerrada(votacao, hoje), "votantes": len(votos),
            "meus": list(votos.get(login) or []), "faltam": _faltam_votar(post, votos, login)}


def _faltam_votar(post: dict, votos: dict, login: str) -> list:
    """3.3.9.4: votação pra uma equipe mostra quem dela ainda não votou (ativos, sem login de teste, quem publicou também
    conta se não votou). Pra todo mundo (sem `publico`) volta vazio: a lista seria a empresa inteira."""
    if not post.get("publico"):
        return []
    faltam = []
    for outro, info in USUARIOS_WEB.items():
        if outro in votos or not info.get("ativo", True) or outro.lower().startswith("teste") or not pode_ver_post(post, outro):
            continue
        faltam.append({"login": outro, "nome": info.get("nome") or outro, "equipe": info.get("atribuicao") or "",
                       "tem_foto": _caminho_foto_usuario(outro) is not None, "eu": outro == login})
    return sorted(faltam, key=lambda p: (not p["eu"], p["nome"].lower()))


def votar(id_post: str, login: str, escolhas: list, hoje: Optional[date] = None) -> dict:
    """Grava (ou troca) o voto de `login`. escolhas vazio = tira o voto. Uma opção só, se não for múltipla."""
    hoje = hoje or date.today()
    if login not in USUARIOS_WEB:
        return {"ok": False, "erro": "usuário não encontrado"}
    with _lock_posts:
        post = POSTS.get(id_post)
        if post is None or not post.get("votacao") or not pode_ver_post(post, login):
            return {"ok": False, "erro": "essa votação não existe mais"}
        votacao = post["votacao"]
        if _votacao_encerrada(votacao, hoje):
            return {"ok": False, "erro": "essa votação já encerrou"}
        validas = [o["id"] for o in votacao["opcoes"]]
        pedidas = set(escolhas or [])
        if any(e not in validas for e in pedidas):
            return {"ok": False, "erro": "opção inválida"}
        escolhas = [e for e in validas if e in pedidas]  # na ordem das opções, sem repetir
        if len(escolhas) > 1 and not votacao.get("multipla"):
            return {"ok": False, "erro": "essa votação aceita uma opção só"}
        votos = post.setdefault("votos", {})
        antes = votos.get(login)
        if escolhas:
            votos[login] = escolhas
        else:
            votos.pop(login, None)
        if not _gravar():
            if antes is None:
                votos.pop(login, None)
            else:
                votos[login] = antes
            return {"ok": False, "erro": "não foi possível gravar o voto (detalhes no log)"}
        return {"ok": True, "votacao": visao_votacao(post, login, hoje)}


def posts() -> list:
    with _lock_posts:
        return [dict(p) for p in POSTS.values()]


def arquivo_do_post(id_post: str, indice: int, login: str = "") -> Optional[dict]:
    """{caminho, nome, tipo, imagem} do arquivo `indice` do post, ou None (também se for de equipe que `login` não vê)."""
    with _lock_posts:
        post = POSTS.get(id_post)
        if post is not None and not pode_ver_post(post, login):
            post = None
        arquivos = list((post or {}).get("arquivos") or [])
    if not 0 <= indice < len(arquivos):
        return None
    a = arquivos[indice]
    caminho = os.path.join(_pasta_arquivos(), a["arquivo"])
    if not os.path.isfile(caminho):
        return None
    return {"caminho": caminho, "nome": a["nome"], "tipo": a["tipo"], "imagem": a.get("imagem", False), "video": a.get("video", False)}


def tirar_avisos_de_quem_nao_ve() -> int:
    """3.3.8.2: até aqui o aviso de publicação importante de uma equipe ia também pro sininho dos administradores das
    outras equipes; apaga os que ficaram com quem não vê a publicação. Roda na carga do módulo; depois não acha nada."""
    tirados = 0
    try:
        for id_post, post in list(POSTS.items()):
            if not post.get("publico"):
                continue
            for login in list(USUARIOS_WEB):
                if not pode_ver_post(post, login) and apagar_por_chave(login, "post:" + id_post):
                    tirados += 1
    except Exception:
        logger.exception("Não foi possível tirar os avisos de publicação de equipe de quem não é da equipe.")
    if tirados:
        logger.info("Avisos de publicação de equipe tirados do sininho de quem não é da equipe: %d.", tirados)
    return tirados


tirar_avisos_de_quem_nao_ve()  # na partida (3.3.8.2)
