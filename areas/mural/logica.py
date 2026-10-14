"""Mural do início (2.35.7.0, comentários e colaborações na 3.0.1.0): a linha do tempo da equipe no hub.

Eventos, todos calculados do que o PDA já guarda (nada é cadastrado à mão, fora as
publicações de versão em PUBLICACOES_MURAL):
- aniversário: `aniversario` ("MM-DD") de quem está ativo, de DIAS_ANIVERSARIO_MURAL
  atrás até hoje (o de hoje fica em destaque);
- promoção: item do histórico na empresa que começou nos últimos DIAS_MURAL dias e
  tem um cargo anterior da mesma pessoa (o primeiro item é a entrada, não promoção);
- chegada: `data_inicio` nos últimos DIAS_MURAL dias (boas-vindas);
- insígnia: a Beta User gravada em `insignias` e cada ano de casa completo
  (aniversário de empresa), nos últimos DIAS_MURAL dias;
- colaboração (tipo "colab"), um evento de duas ou mais pessoas juntas:
  * publicação de versão (PUBLICACOES_MURAL, ex.: Igor e Debora publicaram a v3);
  * feedback/alinhamento feito por dois ou mais autores no card Feedbacks e
    Alinhamentos. Esse só aparece pros autores e pros administradores que recebem os
    e-mails de alguma equipe (e a gerência), nunca com o texto do registro; o link
    "Ver alinhamento" só vai pra quem pode abrir o registro.

Palminhas: quem clica bate palma num evento (clicar de novo desfaz); ninguém bate no
próprio evento. Ficam em mural_palmas.json ({id: {"pessoas": [logins], "quem":
[logins]}}; as pessoas do evento ficam junto pra contar as recebidas depois que ele sai
do mural). Comentários em mural_comentarios.json ({id: [{id, login, texto,
criado_em}]}). Os dois com trava e gravação via .tmp; o id do evento é estável (ex.:
"aniv:ana:2026"), então nada se perde quando a lista é recalculada. Palma e comentário
viram notificação no sininho (nucleo/notificacoes.py) pras pessoas do evento.
"""
import json
import logging
import os
import threading
import uuid
from datetime import date, datetime, timedelta
from typing import Optional

from areas.feedbacks.logica import (EQUIPES_FEEDBACK, FEEDBACKS_USUARIOS, _lock_feedbacks_usuarios, autores_do_registro,
                                    equipe_do_registro, logins_da_equipe_feedback, pode_ver_registro_feedback,
                                    ve_todas_equipes_feedback)
from areas.ferias.logica import FERIAS, _lock_ferias
from areas.perfil.insignias import registrar_desbloqueios, registrar_desbloqueios_de_todos
from areas.perfil.insignias import FIM_CAMPANHA_BETA
from areas.perfil.insignias import (FUNDADORES, NIVEL_MESES, _aniversario_empresa, _anos_completos, _esta_em, _meses_completos,
                                    _somar_meses, aniversario_valido, insignia_em_destaque, insignias_de, nivel_tempo)
from areas.perfil.logica import HISTORICO_CARREIRA, _lock_historico_carreira
from nucleo.acessos import DATA_CRIACAO_PDA, aniversario_do_pda, anos_do_pda, marcos_de_acessos
from nucleo.desativacao import TEXTO_DESATIVADO, _id_evento as _id_saida
from nucleo.notificacoes import anuncio_pendente, marcar_anuncio_visto
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.equipes import _pertence_a_equipe
from nucleo.fotos import _caminho_foto_usuario
from nucleo.notificacoes import apagar_por_chave, notificar
from areas.mural.posts import _decodificar, _eh_imagem, _pasta_arquivos
from areas.mural.posts import (apagar_post, autores_do_post, pessoas_para_grupo, pode_marcar_importante, pode_ver_post,
                               posts as _posts_manuais, pode_postar, visao_votacao)
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

DIAS_MURAL = 30
DIAS_ANIVERSARIO_MURAL = 7
# 3.2.2.0: o filtro "Aniversários" mostra os dos últimos 90 dias; no "Tudo" continuam só os da última semana
# (os mais antigos vêm com "so_filtro": true e a tela esconde no Tudo)
DIAS_ANIVERSARIO_FILTRO = 90
# férias (3.2.2.0): aviso no sininho de quem sai e de quem volta, até 2 dias depois (se o PDA estava fechado no dia)
DIAS_TOLERANCIA_AVISO_FERIAS = 2
INTERVALO_AVISO_FERIAS = 600  # segundos entre uma varredura e outra (roda junto do /api/mural)
DIAS_PROXIMOS_ANIVERSARIOS = 30
MAX_QUEM_BATEU = 3  # nomes mostrados no "Fulano, Beltrano e mais 4"
MAX_PROMOCOES_LADO = 5
MAX_TEXTO_COMENTARIO = 500
MAX_BYTES_IMAGEM_COMENTARIO = 3 * 1024 * 1024  # foto no comentário de publicação (3.3.1.0)
MAX_BYTES_GIF_COMENTARIO = 5 * 1024 * 1024     # GIF animado no comentário (3.3.2.1)
EXTENSAO_IMAGEM = {"image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif", "image/webp": ".webp"}
NOMES_MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

# Publicações de versão que entram no mural como colaboração. "grupo" diz de quem é
# (FUNDADORES = Igor Leal e Debora Sampaio, achados pelo login ou pelo nome).
PUBLICACOES_MURAL = [
    # "fixado": fica no topo do mural, mesmo depois dos 30 dias, até alguém tirar (3.0.5.0: a v3; desafixada na 3.3.1.0).
    # "filtros": também aparece nesses filtros do feed (a v3 é colaboração e publicação). "permanente": não some depois
    # dos 30 dias; passado esse prazo, fica só nos filtros (fora do "Tudo")
    {"id": "versao:3.0", "data": "2026-10-02", "grupo": FUNDADORES, "verbo": "publicaram a v3 do PDA",
     "filtros": ["post"], "permanente": True,
     "detalhe": "O início virou o mural da equipe, com palminhas, comentários e as novidades de cada um.",
     "link": {"href": "/changelog", "texto": "Ver changelog"}},
]

# Campanhas mostradas na lateral do início (pode ter mais de uma ao mesmo tempo). Ficam
# até "fim" ("AAAA-MM-DD", None = sem data); quem concluiu vê o selo "Concluída" por cima.
# "acao" diz o que o "Quero participar" abre: "beta" = formulário da Beta User, "bug" = os requisitos da Bug Hunter.
CAMPANHAS_MURAL = [
    {"id": "beta_user", "nome": "PDA Beta User", "descricao": "Complete seu perfil e ganhe a insígnia da fase beta.",
     "insignia": {"tipo": "beta"}, "fim": FIM_CAMPANHA_BETA, "acao": "beta"},
    {"id": "bug_hunter", "nome": "Bug Hunter", "descricao": "Ache e reporte um bug no PDA e ganhe a insígnia de caçador de bugs.",
     "insignia": {"tipo": "bug"}, "fim": None, "acao": "bug"},
]


_lock_palmas = threading.Lock()
_lock_comentarios = threading.Lock()


def _ler_json(nome: str) -> dict:
    try:
        with open(os.path.join(_base_path_app(), nome), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        logger.exception("Não foi possível ler %s, começando vazio.", nome)
        return {}


def _gravar_json(nome: str, dados: dict) -> bool:
    caminho = os.path.join(_base_path_app(), nome)
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=1, ensure_ascii=False)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não foi possível gravar %s.", nome)
        return False


PALMAS: dict = _ler_json("mural_palmas.json")
COMENTARIOS: dict = _ler_json("mural_comentarios.json")


def _ativo(login: str) -> bool:
    info = USUARIOS_WEB.get(login) or {}
    return info.get("ativo", True) and not login.lower().startswith("teste")


def _nome(login: str) -> str:
    return (USUARIOS_WEB.get(login) or {}).get("nome") or login


def _primeiro_nome(login: str) -> str:
    return _nome(login).split(" ")[0]


def _juntar(nomes: list) -> str:
    nomes = [n for n in nomes if n]
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1] if nomes else ""


def _data(valor: str) -> Optional[date]:
    try:
        return datetime.strptime((valor or "")[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _pessoa(login: str) -> dict:
    """O que a tela precisa pra desenhar a pessoa (foto ou iniciais + insígnia em destaque)."""
    info = USUARIOS_WEB.get(login) or {}
    return {"login": login, "nome": _nome(login), "tem_foto": _caminho_foto_usuario(login) is not None,
            "cargo": info.get("cargo") or "", "equipe": info.get("atribuicao") or "",
            "destaque": insignia_em_destaque(login)}


def _aniversario_no_ano(mm_dd: str, ano: int) -> date:
    mes, dia = (int(x) for x in mm_dd.split("-"))
    try:
        return date(ano, mes, dia)
    except ValueError:  # 29/02 em ano que não é bissexto
        return date(ano, 2, 28)


def _proximo_aniversario(mm_dd: str, hoje: date) -> date:
    data = _aniversario_no_ano(mm_dd, hoje.year)
    return data if data >= hoje else _aniversario_no_ano(mm_dd, hoje.year + 1)


def _insignia_tempo(anos: int) -> dict:
    nivel = nivel_tempo(anos)
    return {"tipo": "tempo", "nivel": nivel[0], "nivel_nome": nivel[1], "anos": anos}


def _quando(dia: date, momento: str = "") -> str:
    """Data e hora do evento pra ordenar o feed (3.2.4.0). `momento` = "AAAA-MM-DD HH:MM:SS" de quando aconteceu de
    verdade (feedback criado, insígnia desbloqueada, usuário desativado); sem ele, o evento é do dia inteiro e fica
    no começo do dia (aniversário, férias, promoção, tempo de casa...)."""
    momento = (momento or "").strip().replace("T", " ")
    if len(momento) >= 19 and momento[:10] == dia.isoformat():
        return momento[:10] + "T" + momento[11:19]
    return dia.isoformat() + "T00:00:00"


def _evento(id_evento: str, tipo: str, dia: date, logins: list, titulo: str, detalhe: str, momento: str = "", **extra) -> dict:
    pessoas = [_pessoa(l) for l in logins]
    return {"id": id_evento, "tipo": tipo, "data": dia.isoformat(), "quando": _quando(dia, momento), "pessoa": pessoas[0],
            "pessoas": pessoas, "titulo": titulo, "detalhe": detalhe, **extra}


# ---------------------------------------------------------------------------
# quem vê as colaborações de feedback/alinhamento
# ---------------------------------------------------------------------------
def _responsavel_de_equipe(login: str) -> bool:
    """Administrador que recebe os e-mails de alguma equipe do Feedbacks, ou a gerência."""
    if not (USUARIOS_WEB.get(login) or {}).get("admin"):
        return False
    return ve_todas_equipes_feedback(login) or any(login in logins_da_equipe_feedback(e) for e in EQUIPES_FEEDBACK)


def _pode_abrir_feedbacks(login: str) -> bool:
    info = USUARIOS_WEB.get(login) or {}
    return bool(info.get("admin")) and bool(info.get("pode_feedbacks"))


def _eventos_colab_feedback(limite: date, hoje: date, viewer: str) -> list:
    if not viewer:
        return []
    with _lock_feedbacks_usuarios:
        registros = [dict(f) for f in FEEDBACKS_USUARIOS]
    responsavel = _responsavel_de_equipe(viewer)
    lista = []
    for r in registros:
        autores = [a for a in autores_do_registro(r) if a in USUARIOS_WEB]
        dia = _data(r.get("criado_em") or "")
        if len(autores) < 2 or not dia or not (limite <= dia <= hoje):
            continue
        if viewer not in autores and not responsavel:
            continue
        tipo = (r.get("tipo") or "Feedback").lower()
        equipe = equipe_do_registro(r)
        escopo = r.get("escopo") or "individual"
        qtd = len(r.get("usuarios") or []) if escopo == "grupo" else (0 if escopo == "geral" else 1)
        # o time só aparece quando o registro é pra 2 ou mais pessoas (ou geral); individual
        # não diz quem recebeu (o feedback é privado)
        if escopo == "geral" or qtd >= 2:
            alvo = f"para o time {equipe}"
            detalhe = (f"{'Alinhamento' if tipo == 'alinhamento' else 'Feedback'} "
                       + ("geral" if escopo == "geral" else f"para {qtd} pessoas") + " no card Feedbacks e Alinhamentos")
        else:
            alvo = "individual"
            detalhe = f"Registrado no card Feedbacks e Alinhamentos · time {equipe}"
        extra = {}
        if _pode_abrir_feedbacks(viewer) and pode_ver_registro_feedback(r, viewer):
            extra["link"] = {"href": f"/feedbacks?registro={r.get('id')}",
                             "texto": "Ver alinhamento" if tipo == "alinhamento" else "Ver feedback"}
        artigo = "um alinhamento" if tipo == "alinhamento" else "um feedback"
        lista.append(_evento(f"fb:{r.get('id')}", "colab", dia, autores,
                             f"{_juntar([_nome(a) for a in autores])} fizeram {artigo} {alvo}", detalhe,
                             momento=r.get("criado_em") or "", **extra))
    return lista


# ---------------------------------------------------------------------------
# eventos
# ---------------------------------------------------------------------------
def eventos(hoje: Optional[date] = None, viewer: str = "") -> list:
    """Eventos dos últimos DIAS_MURAL dias que `viewer` pode ver, do mais recente pro
    mais antigo. Cada um: {id, tipo, data, pessoa, pessoas, titulo, detalhe, insignia?, link?}."""
    hoje = hoje or date.today()
    limite = hoje - timedelta(days=DIAS_MURAL)
    lista = []
    for login, info in USUARIOS_WEB.items():
        if not _ativo(login):
            continue
        primeiro = _primeiro_nome(login)

        aniv = info.get("aniversario") or ""
        if aniversario_valido(aniv):
            for ano in (hoje.year, hoje.year - 1):  # aniversário em 30/12 visto em 02/01
                dia = _aniversario_no_ano(aniv, ano)
                if hoje - timedelta(days=DIAS_ANIVERSARIO_FILTRO) <= dia <= hoje:
                    recente = dia >= hoje - timedelta(days=DIAS_ANIVERSARIO_MURAL)
                    lista.append(_evento(f"aniv:{login}:{ano}", "aniversario", dia, [login],
                                         f"{'Hoje é' if dia == hoje else 'Foi'} aniversário de {primeiro}!",
                                         "Deixe suas palminhas e os parabéns" if dia == hoje
                                         else ("Ainda dá tempo de dar os parabéns" if recente else "Os parabéns valem o ano todo"),
                                         hoje=dia == hoje, so_filtro=not recente))

        inicio = _data(info.get("data_inicio") or "")
        if inicio:
            if limite <= inicio <= hoje:
                lista.append(_evento(f"chegada:{login}", "chegada", inicio, [login], f"{primeiro} chegou na Empresa",
                                     (f"Agora como {info['cargo']}. " if info.get("cargo") else "") + "Dê as boas-vindas!"))
            for n in range(_anos_completos(inicio, hoje), 0, -1):
                dia = _aniversario_empresa(inicio, n)
                if dia < limite:
                    break
                # aniversário de empresa (3.0.3.0: tipo próprio, "Tempo de casa", em destaque no dia)
                anos_txt = f"{n} {'ano' if n == 1 else 'anos'}"
                lista.append(_evento(f"tempo:{login}:{n}", "tempo", dia, [login],
                                     f"Hoje {primeiro} faz {anos_txt} de Empresa!" if dia == hoje else f"{primeiro} completou {anos_txt} de Empresa",
                                     f"Parabéns pelos {anos_txt} de casa! Conquistou a insígnia nível {nivel_tempo(n)[1]}",
                                     insignia=_insignia_tempo(n), hoje=dia == hoje))
            if _anos_completos(inicio, hoje) == 0:  # antes de 1 ano: a de ferro, um número novo por mês (3.0.2.0)
                for m in range(min(_meses_completos(inicio, hoje), 11), 0, -1):
                    dia = _somar_meses(inicio, m)
                    if dia < limite:
                        break
                    lista.append(_evento(f"tempo:{login}:m{m}", "insignia", dia, [login],
                                         f"{primeiro} completou {m} {'mês' if m == 1 else 'meses'} de Empresa",
                                         "Conquistou a insígnia de tempo de casa nível Ferro",
                                         insignia={"tipo": "tempo", "nivel": NIVEL_MESES[0], "nivel_nome": NIVEL_MESES[1], "anos": 0, "meses": m}))

        # insígnias concedidas à mão pelo Igor ou pela Debora (3.0.5.0)
        for id_ins, nome_ins, tipo_ins in (("bug_hunter", "Bug Hunter", "bug"), ("contribuidor", "PDA Contributor", "contribuidor")):
            concedida = _data((info.get("insignias") or {}).get(id_ins) or "")
            if concedida and limite <= concedida <= hoje:
                lista.append(_evento(f"ins:{login}:{id_ins}", "insignia", concedida, [login], f"{primeiro} conquistou a insígnia {nome_ins}",
                                     "Achou e reportou um bug no PDA" if id_ins == "bug_hunter" else "Contribuiu com o desenvolvimento do PDA",
                                     momento=((info.get("insignias_desbloqueio") or {}).get(id_ins) or {}).get("em") or "",
                                     insignia={"tipo": tipo_ins}))

        # toda insígnia desbloqueada que ainda não tinha sido vista (3.0.6.0); tempo de casa e Beta User têm aviso próprio
        for id_ins, reg in (info.get("insignias_desbloqueio") or {}).items():
            dia = _data((reg or {}).get("data") or "")
            if not (reg or {}).get("mural") or id_ins.startswith("tempo") or id_ins == "beta_user" or not dia or not (limite <= dia <= hoje):
                continue
            ins = next((i for i in insignias_de(login) if i["id"] == id_ins and i["desbloqueada"]), None)
            if ins:
                lista.append(_evento(f"ins:{login}:{id_ins}", "insignia", dia, [login], f"{primeiro} conquistou a insígnia {ins['nome']}",
                                     ins.get("descricao") or "", momento=(reg or {}).get("em") or "", insignia={k: ins[k] for k in ("tipo", "nivel", "nivel_nome", "anos", "meses", "produtos", "palmas") if k in ins}))

        beta = _data((info.get("insignias") or {}).get("beta_user") or "")
        if beta and limite <= beta <= hoje:
            lista.append(_evento(f"ins:{login}:beta_user", "insignia", beta, [login],
                                 f"{primeiro} conquistou a insígnia PDA Beta User",
                                 "Completou o perfil na campanha da fase beta do PDA", insignia={"tipo": "beta"}))

    for promo in _promocoes():
        dia = _data(promo["inicio"] + "-01")
        if dia and limite.replace(day=1) <= dia <= hoje:
            lista.append(_evento(f"promo:{promo['id']}", "promocao", dia, [promo["login"]],
                                 f"{_primeiro_nome(promo['login'])} agora é {promo['para']}",
                                 f"Antes: {promo['de']}" + (f" · agora no {promo['area'].capitalize()}" if promo["mudou_area"] else ""),
                                 de=promo["de"], para=promo["para"]))

    for pub in PUBLICACOES_MURAL:
        dia = _data(pub["data"])
        autores = sorted((l for l in USUARIOS_WEB if _ativo(l) and _esta_em(pub["grupo"], l)), key=_nome)
        if dia and autores and (pub.get("fixado") or pub.get("permanente") or limite <= dia <= hoje) and dia <= hoje:
            lista.append(_evento(pub["id"], "colab", dia, autores, f"{_juntar([_nome(a) for a in autores])} {pub['verbo']}",
                                 pub["detalhe"], link=pub.get("link"), fixado=bool(pub.get("fixado")),
                                 tambem=list(pub.get("filtros") or []),
                                 so_filtro=bool(pub.get("permanente")) and not pub.get("fixado") and dia < limite))

    lista += _eventos_colab_feedback(limite, hoje, viewer)

    # publicações manuais na Comunidade (3.2.6.0): texto, fotos/GIFs e anexos, com a hora em que foram postadas
    admin_viewer = bool((USUARIOS_WEB.get(viewer) or {}).get("admin"))
    for post in _posts_manuais():
        dia = _data((post.get("criado_em") or "")[:10])
        if not dia or not (limite <= dia <= hoje) or post["autor"] not in USUARIOS_WEB:
            continue
        if not pode_ver_post(post, viewer):  # publicação só pra uma equipe (3.3.1.0; sem exceção pra admin desde a 3.3.8.2)
            continue
        arquivos = [{"url": f"/mural-arquivo/{post['id']}/{n}", "nome": a["nome"], "tamanho": a.get("tamanho", 0),
                     "imagem": bool(a.get("imagem")), "video": bool(a.get("video"))} for n, a in enumerate(post.get("arquivos") or [])]
        # publicação em grupo (3.4.1.0): as fotos de todos, "Fulano e mais N publicaram" e as palminhas pra cada um
        autores = [a for a in autores_do_post(post) if a in USUARIOS_WEB] or [post["autor"]]
        quem = _nome(post["autor"]) + (f" e mais {len(autores) - 1} publicaram" if len(autores) > 1 else " publicou")
        lista.append(_evento(f"post:{post['id']}", "post", dia, autores,
                             quem + (" um aviso importante" if post.get("importante") else ""),
                             post.get("texto") or "", momento=post.get("criado_em") or "", importante=bool(post.get("importante")),
                             arquivos=arquivos, pode_apagar=viewer == post["autor"] or admin_viewer, hoje=dia == hoje,
                             pode_reenviar_teams=admin_viewer and bool(post.get("importante")),
                             votacao=visao_votacao(post, viewer, hoje), publico=post.get("publico") or ""))

    # aniversário do PDA (criado em 05/08/2026), com as fotos de quem criou
    anos_pda = anos_do_pda(hoje)
    if anos_pda >= 1 and aniversario_do_pda(anos_pda) >= limite:
        criadores = sorted((l for l in USUARIOS_WEB if _ativo(l) and _esta_em(FUNDADORES, l)), key=_nome)
        if criadores:
            dia = aniversario_do_pda(anos_pda)
            lista.append(_evento(f"pda:ano:{anos_pda}", "pda", dia, criadores,
                                 f"O PDA completou {anos_pda} {'ano' if anos_pda == 1 else 'anos'}! 🎂",
                                 f"Criado em {DATA_CRIACAO_PDA.strftime('%d/%m/%Y')} por {_juntar([_nome(c) for c in criadores])}. "
                                 "Obrigado a todo mundo que usa o painel!", link={"href": "/changelog", "texto": "Ver a história do PDA"},
                                 hoje=dia == hoje))

    # marcos de acessos (3.4.5.0): a cada 1.000 acessos, um post de comemoração assinado por quem criou o PDA
    for marco, quando in sorted(marcos_de_acessos().items()):
        dia = _data(quando[:10])
        if not dia or not (limite <= dia <= hoje):
            continue
        criadores = sorted((l for l in USUARIOS_WEB if _ativo(l) and _esta_em(FUNDADORES, l)), key=_nome)
        if not criadores:
            continue
        numero = f"{marco:,}".replace(",", ".")
        proximo = f"{marco + 1000:,}".replace(",", ".")
        lista.append(_evento(f"pda:acessos:{marco}", "marco", dia, criadores, f"O PDA chegou a {numero} acessos! 🎉",
                             f"São {numero} logins desde que o PDA nasceu, em {DATA_CRIACAO_PDA.strftime('%d/%m/%Y')}. "
                             f"Cada acesso é alguém usando o painel no dia a dia: obrigado por isso! Bora pros {proximo}? 🚀",
                             momento=quando, numero=marco, link={"href": "/sobre", "texto": "Ver os números do PDA"}, hoje=dia == hoje))

    # férias (3.2.2.0): saída no dia do início e volta no dia seguinte ao fim, pelo Calendário de Férias (só férias, não day off)
    for f in _ferias_do_calendario():
        login = f["usuario"]
        if not _ativo(login):
            continue
        inicio, fim = _data(f.get("inicio") or ""), _data(f.get("fim") or "")
        if not inicio or not fim:
            continue
        volta = fim + timedelta(days=1)
        if limite <= inicio <= hoje:
            lista.append(_evento(f"ferias:ida:{login}:{inicio.isoformat()}", "ferias", inicio, [login],
                                 f"{_primeiro_nome(login)} saiu de férias! 🏖️",
                                 f"Volta em {volta.strftime('%d/%m')}. Bom descanso, protetor solar e nada de abrir o Teams!",
                                 volta=volta.isoformat(), fase="ida", hoje=inicio == hoje))
        if limite <= volta <= hoje:
            lista.append(_evento(f"ferias:volta:{login}:{volta.isoformat()}", "ferias", volta, [login],
                                 f"{_primeiro_nome(login)} voltou das férias! 🌴",
                                 "Bem-vindo(a) de volta! Bate umas palminhas e conta como foi.",
                                 fase="volta", hoje=volta == hoje))

    # usuário desativado no PDA (3.1.5.0): aviso em vermelho a partir do dia em que foi desativado; desde a 3.3.8.1 só
    # administrador vê (antes era todo mundo)
    viewer_admin = bool((USUARIOS_WEB.get(viewer) or {}).get("admin"))
    for login, info in USUARIOS_WEB.items():
        if not viewer_admin or info.get("ativo", True) or login.lower().startswith("teste"):
            continue
        dia = _data((info.get("desativado_em") or "")[:10])
        if dia and limite <= dia <= hoje:
            lista.append(_evento(_id_saida(login, info["desativado_em"]), "saida", dia, [login],
                                 f"{_nome(login)} foi desativado(a) no PDA", TEXTO_DESATIVADO, momento=info.get("desativado_em") or "",
                                 hoje=dia == hoje))

    # feedback/alinhamento no mural é só aviso: sem comentário (3.0.3.0) e sem palminhas (3.0.4.0); usuário desativado também
    for e in lista:
        e["interativo"] = e["comentavel"] = not (e["id"].startswith("fb:") or e["id"].startswith("saida:"))

    # o mesmo evento pode vir de dois caminhos (concessão à mão e registro de desbloqueio): fica um só
    vistos_ids, unicos = set(), []
    for e in lista:
        if e["id"] not in vistos_ids:
            vistos_ids.add(e["id"])
            unicos.append(e)
    lista = unicos

    # do mais recente pro mais antigo pela data E hora (3.2.4.0: antes era só pelo dia, e dentro do dia por tipo, o que
    # embaralhava o feed). Empate de horário (eventos do dia inteiro, todos às 00:00): aniversário do PDA, aniversário,
    # tempo de casa, colaboração, promoção, insígnia, chegada e férias
    ordem = {"saida": -2, "marco": -1, "pda": -1, "ferias": 6, "aniversario": 0, "tempo": 1, "colab": 2, "promocao": 3, "insignia": 4, "chegada": 5, "post": 7}
    lista.sort(key=lambda e: (e["quando"], -ordem[e["tipo"]]), reverse=True)
    lista.sort(key=lambda e: not e.get("fixado"))  # fixados no topo (sort estável: o resto mantém a ordem)
    return lista


def _promocoes() -> list:
    """Todas as promoções do histórico (cargo novo depois de outro da mesma pessoa), mais recentes primeiro."""
    with _lock_historico_carreira:
        historico = [dict(h) for h in HISTORICO_CARREIRA]
    por_pessoa = {}
    for h in historico:
        por_pessoa.setdefault(h.get("usuario"), []).append(h)
    lista = []
    for login, itens in por_pessoa.items():
        if login not in USUARIOS_WEB or not _ativo(login):
            continue
        itens.sort(key=lambda h: h.get("inicio") or "")
        for anterior, item in zip(itens, itens[1:]):
            if not item.get("inicio"):
                continue
            lista.append({"id": item.get("id"), "login": login, "inicio": item["inicio"], "de": anterior.get("cargo"),
                          "para": item.get("cargo"), "area": item.get("area") or "",
                          "mudou_area": bool(item.get("area")) and (anterior.get("area") or "") != item.get("area")})
    lista.sort(key=lambda p: (p["inicio"], str(p["id"])), reverse=True)
    return lista


def promocoes_recentes(limite: int = MAX_PROMOCOES_LADO) -> list:
    lista = []
    for p in _promocoes()[:limite]:
        ano, mes = p["inicio"].split("-")
        lista.append({**_pessoa(p["login"]), "de": p["de"], "para": p["para"], "quando": f"{NOMES_MESES_CURTOS[int(mes) - 1]} {ano}"})
    return lista


def _quem_e(evento: dict) -> list:
    return [p["login"] for p in evento.get("pessoas") or [evento["pessoa"]]]


def _comentarios_do_evento(id_evento: str, login: str) -> list:
    with _lock_comentarios:
        lista = [dict(c) for c in COMENTARIOS.get(id_evento) or []]
    admin = bool((USUARIOS_WEB.get(login) or {}).get("admin"))
    return [{"id": c["id"], "login": c["login"], "nome": _nome(c["login"]), "tem_foto": _caminho_foto_usuario(c["login"]) is not None,
             "texto": c["texto"], "criado_em": c["criado_em"], "pode_apagar": c["login"] == login or admin,
             "imagem": ("/mural-comentario-imagem/" + c["id"]) if c.get("imagem") else ""} for c in lista]


def _pasta_imagens_comentarios() -> str:
    pasta = os.path.join(_pasta_arquivos(), "comentarios")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def imagem_do_comentario(id_comentario: str, login: str) -> Optional[dict]:
    """{caminho, tipo} da foto/GIF de um comentário que `login` vê no mural agora, ou None."""
    with _lock_comentarios:
        achado = next(((ev, c) for ev, lista in COMENTARIOS.items() for c in lista
                       if c.get("id") == id_comentario and c.get("imagem")), None)
    if achado is None or _evento_visivel(achado[0], login) is None:
        return None
    caminho = os.path.join(_pasta_imagens_comentarios(), os.path.basename(achado[1]["imagem"]))
    return {"caminho": caminho, "tipo": achado[1].get("imagem_tipo") or "image/png"} if os.path.isfile(caminho) else None


def _com_interacoes(evento: dict, login: str) -> dict:
    with _lock_palmas:
        quem = list((PALMAS.get(evento["id"]) or {}).get("quem") or [])
    # quem bateu por último aparece primeiro; a própria pessoa vira "você"
    recentes = [l for l in reversed(quem) if l != login][:MAX_QUEM_BATEU]
    # todo mundo que bateu (3.2.0.0), pra lista completa ao clicar no "Fulano e mais N": mais recente primeiro
    todos = [{"login": l, "nome": _nome(l), "tem_foto": _caminho_foto_usuario(l) is not None,
              "equipe": (USUARIOS_WEB.get(l) or {}).get("atribuicao") or "", "eu": l == login}
             for l in reversed(quem) if l in USUARIOS_WEB]
    return {**evento, "palmas": len(quem), "bati": login in quem, "meu": login in _quem_e(evento),
            "quem": (["você"] if login in quem else []) + [_primeiro_nome(l) for l in recentes],
            "quem_todos": todos, "comentarios": _comentarios_do_evento(evento["id"], login)}


def proximos_aniversarios(hoje: Optional[date] = None) -> list:
    hoje = hoje or date.today()
    lista = []
    for login, info in USUARIOS_WEB.items():
        aniv = info.get("aniversario") or ""
        if not _ativo(login) or not aniversario_valido(aniv):
            continue
        dia = _proximo_aniversario(aniv, hoje)
        faltam = (dia - hoje).days
        if faltam <= DIAS_PROXIMOS_ANIVERSARIOS:
            lista.append({**_pessoa(login), "data": dia.isoformat(), "faltam": faltam,
                          "quando": "hoje" if faltam == 0 else ("amanhã" if faltam == 1 else f"{dia.day} {NOMES_MESES_CURTOS[dia.month - 1]}")})
    lista.sort(key=lambda p: p["faltam"])
    return lista


def campanhas(login: str, hoje: Optional[date] = None) -> list:
    """Campanhas no ar, com se a pessoa já concluiu (fica na tela com o selo até o fim)."""
    hoje = hoje or date.today()
    gravadas = (USUARIOS_WEB.get(login) or {}).get("insignias") or {}
    ganhas = {i["id"] for i in insignias_de(login) if i["desbloqueada"]}  # inclui quem ganhou pela lista fixa
    lista = []
    for c in CAMPANHAS_MURAL:
        if c.get("fim") and hoje.isoformat() > c["fim"]:
            continue
        lista.append({**c, "concluida": c["id"] in ganhas, "concluida_em": gravadas.get(c["id"])})
    from areas.loja.halloween import campanha as _campanha_halloween  # Caça aos Doces (3.3.7.0), só de 24/10 a 01/11
    doces = _campanha_halloween(login, hoje)
    if doces:
        lista.insert(0, doces)
    return lista


def _texto_tempo_de_casa(inicio: date, hoje: date) -> str:
    meses = (hoje.year - inicio.year) * 12 + hoje.month - inicio.month - (hoje.day < inicio.day)
    anos, meses = divmod(max(meses, 0), 12)
    partes = ([f"{anos} {'ano' if anos == 1 else 'anos'}"] if anos else []) + ([f"{meses} {'mês' if meses == 1 else 'meses'}"] if meses else [])
    return " e ".join(partes) or "começando agora"


def _pessoas_da_palma(v: dict) -> list:
    return v.get("pessoas") or ([v["pessoa"]] if v.get("pessoa") else [])


def palmas_recebidas_por_pessoa() -> dict:
    """{login: palminhas recebidas} de todo mundo, contando também eventos que já saíram do mural
    (é o que alimenta o leaderboard e as insígnias de palminhas, 3.1.3.0)."""
    total: dict = {}
    with _lock_palmas:
        for v in PALMAS.values():
            n = len(v.get("quem") or [])
            for p in _pessoas_da_palma(v):
                total[p] = total.get(p, 0) + n
    return total


def palmas_recebidas(login: str) -> int:
    return palmas_recebidas_por_pessoa().get(login, 0)


def meus_numeros(login: str, hoje: Optional[date] = None) -> dict:
    """Indicadores rápidos de quem entrou (sem banco: horas e tickets vêm à parte,
    em /api/mural/movidesk, porque dependem do banco do Movidesk)."""
    hoje = hoje or date.today()
    info = USUARIOS_WEB.get(login) or {}
    inicio = _data(info.get("data_inicio") or "")
    insignias = [i for i in insignias_de(login) if i["desbloqueada"]]
    with _lock_palmas:
        recebidas = sum(len(v.get("quem") or []) for v in PALMAS.values() if login in _pessoas_da_palma(v))
        enviadas = sum(1 for v in PALMAS.values() if login in (v.get("quem") or []))
    hoje_iso = hoje.isoformat()
    with _lock_ferias:
        proximas = sorted((f for f in FERIAS if f.get("usuario") == login and (f.get("fim") or "") >= hoje_iso),
                          key=lambda f: f.get("inicio") or "")
    ferias = proximas[0] if proximas else None
    return {
        "tempo_de_casa": _texto_tempo_de_casa(inicio, hoje) if inicio else None,
        "desde": inicio.isoformat() if inicio else None,
        "insignias": len(insignias),
        "insignia_tempo": next((i for i in insignias if i["tipo"] == "tempo"), None),
        "palmas_recebidas": recebidas,
        "palmas_enviadas": enviadas,
        "ferias": {"inicio": ferias.get("inicio"), "fim": ferias.get("fim"), "tipo": ferias.get("tipo", "ferias")} if ferias else None,
    }


def mural(login: str, hoje: Optional[date] = None) -> dict:
    """Tudo que o início precisa num GET só (/api/mural)."""
    hoje = hoje or date.today()
    registrar_desbloqueios_de_todos()  # avisa insígnias desbloqueadas de todo mundo (no máximo a cada 5 min)
    try:
        avisar_ferias_do_dia(hoje)  # sininho de quem saiu e de quem voltou de férias (no máximo a cada 10 min)
    except Exception:
        logger.exception("Não foi possível avisar as férias do dia.")
    insignias = insignias_de(login)
    destaque = next((i for i in insignias if i.get("destaque")), None)
    # 3.2.5.1: o anúncio (ex.: foto em GIF) conta como visto já na primeira entrega. Antes só gravava ao clicar
    # em "Trocar minha foto"/"Agora não"; quem recarregava ou saía da página sem clicar via o cartão toda vez.
    anuncio = anuncio_pendente(login)
    if anuncio:
        marcar_anuncio_visto(login, anuncio)
    return {
        "ok": True,
        "hoje": hoje.isoformat(),
        "eventos": [_com_interacoes(e, login) for e in eventos(hoje, login)],
        "aniversarios": proximos_aniversarios(hoje),
        "de_ferias": de_ferias_hoje(hoje),
        "promocoes": promocoes_recentes(),
        "campanhas": campanhas(login, hoje),
        "meus_numeros": meus_numeros(login, hoje),
        "eu": {**_pessoa(login), "destaque": destaque, "admin": bool((USUARIOS_WEB.get(login) or {}).get("admin")),
               "aniversario_hoje": _faz_aniversario_hoje(login, hoje), "anuncio": anuncio, "pode_postar": pode_postar(login),
               "pode_importante": pode_marcar_importante(login),  # 3.4.6.0: só o "Importante" depende de permissão
               "wallpaper": _wallpaper_do_cartao(login)},
        # quem dá pra pôr numa publicação em grupo (3.4.1.0), só pra quem pode publicar
        "pessoas_grupo": pessoas_para_grupo() if pode_postar(login) else [],
    }


def _wallpaper_do_cartao(login: str) -> str:
    """Wallpaper da Loja de Palminhas na faixa do cartão (3.3.7.0); import tardio porque a Loja lê as palminhas daqui."""
    try:
        from areas.loja.logica import wallpaper_de
        return wallpaper_de(login)
    except Exception:
        logger.exception("Loja: não foi possível ler o wallpaper de '%s'.", login)
        return "padrao"


def _ferias_do_calendario() -> list:
    """Férias (não day off) do Calendário de Férias."""
    with _lock_ferias:
        return [dict(f) for f in FERIAS if f.get("usuario") and (f.get("tipo") or "ferias") == "ferias"]


_ultimo_aviso_ferias = {"em": 0.0}


def avisar_ferias_do_dia(hoje: Optional[date] = None, forcar: bool = False) -> list:
    """Sininho de todo mundo quando alguém sai de férias (no início) e quando volta (dia seguinte ao fim), 3.2.2.0.
    Cada aviso sai uma vez só (registro em mural_avisos_ferias.json); se o PDA estava fechado no dia, ainda
    sai até DIAS_TOLERANCIA_AVISO_FERIAS dias depois. Roda junto do /api/mural, no máximo a cada 10 min."""
    import time
    if not forcar and time.time() - _ultimo_aviso_ferias["em"] < INTERVALO_AVISO_FERIAS:
        return []
    _ultimo_aviso_ferias["em"] = time.time()
    hoje = hoje or date.today()
    enviados = _ler_json("mural_avisos_ferias.json")
    novos = []
    for f in _ferias_do_calendario():
        login = f["usuario"]
        inicio, fim = _data(f.get("inicio") or ""), _data(f.get("fim") or "")
        if not inicio or not fim or not _ativo(login):
            continue
        volta = fim + timedelta(days=1)
        nome = _primeiro_nome(login)
        if inicio <= hoje <= fim and (hoje - inicio).days <= DIAS_TOLERANCIA_AVISO_FERIAS:
            chave = f"ferias:ida:{login}:{inicio.isoformat()}"
            if chave not in enviados:
                novos.append((chave, login, f"🏖️ {nome} saiu de férias! Volta em {volta.strftime('%d/%m')}. Boas férias!"))
        if volta <= hoje and (hoje - volta).days <= DIAS_TOLERANCIA_AVISO_FERIAS:
            chave = f"ferias:volta:{login}:{volta.isoformat()}"
            if chave not in enviados:
                novos.append((chave, login, f"🌴 {nome} voltou das férias! Bem-vindo(a) de volta."))
    for chave, login, texto in novos:
        for outro, dados in USUARIOS_WEB.items():
            if outro != login and _ativo(outro):
                notificar(outro, "ferias", login, texto, chave, _link_evento(chave), chave)
        enviados[chave] = hoje.isoformat()
    if novos:
        # o registro guarda só os últimos 90 dias
        corte = (hoje - timedelta(days=90)).isoformat()
        _gravar_json("mural_avisos_ferias.json", {k: v for k, v in enviados.items() if v >= corte})
    return [c for c, _, _ in novos]


def de_ferias_hoje(hoje: Optional[date] = None) -> list:
    """Quem está de férias (ou day off) hoje pelo Calendário de Férias, pra lateral do início (3.1.6.0).
    Só pessoas ativas; quem volta antes aparece primeiro."""
    hoje_iso = (hoje or date.today()).isoformat()
    with _lock_ferias:
        fora = [dict(f) for f in FERIAS if (f.get("inicio") or "") <= hoje_iso <= (f.get("fim") or "")]
    vistos, lista = set(), []
    for f in sorted(fora, key=lambda f: f.get("fim") or ""):
        login = f.get("usuario")
        if login in vistos or not _ativo(login):
            continue
        vistos.add(login)
        lista.append({**_pessoa(login), "tipo": f.get("tipo", "ferias"), "inicio": f.get("inicio"), "fim": f.get("fim")})
    return lista


def _faz_aniversario_hoje(login: str, hoje: date) -> bool:
    aniv = (USUARIOS_WEB.get(login) or {}).get("aniversario") or ""
    return aniversario_valido(aniv) and _aniversario_no_ano(aniv, hoje.year) == hoje


def _evento_visivel(id_evento: str, login: str, hoje: Optional[date] = None) -> Optional[dict]:
    return next((e for e in eventos(hoje, login) if e["id"] == id_evento), None)


def _link_evento(id_evento: str) -> str:
    return "/?evento=" + id_evento


def alternar_palma(id_evento: str, login: str, hoje: Optional[date] = None) -> dict:
    """Bate (ou desfaz) a palma de `login` num evento que ele vê no mural agora."""
    evento = _evento_visivel(id_evento, login, hoje)
    if evento is None:
        return {"ok": False, "erro": "esse evento não está mais no mural"}
    if not evento.get("interativo", True):
        return {"ok": False, "erro": "feedbacks e alinhamentos não recebem palminhas"}
    pessoas = _quem_e(evento)
    if login in pessoas:
        return {"ok": False, "erro": "as palminhas são dos colegas: no seu evento você só recebe"}
    with _lock_palmas:
        registro = PALMAS.setdefault(id_evento, {"pessoas": pessoas, "quem": []})
        registro["pessoas"] = pessoas
        registro.pop("pessoa", None)
        quem = registro.setdefault("quem", [])
        bateu = login not in quem
        if bateu:
            quem.append(login)
        else:
            quem.remove(login)
        if not quem:
            PALMAS.pop(id_evento, None)
        if not _gravar_json("mural_palmas.json", PALMAS):
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    chave = f"palma:{id_evento}:{login}"
    for p in pessoas:
        if bateu:
            notificar(p, "palma", login, f"{_nome(login)} bateu palminhas: {evento['titulo']}", id_evento, _link_evento(id_evento), chave)
            try:  # a palma pode ter fechado uma meta das insígnias de palminhas (3.1.3.0): avisa na hora
                registrar_desbloqueios(p)
            except Exception:
                logger.exception("Não foi possível registrar as insígnias de palminhas de '%s'.", p)
        else:
            apagar_por_chave(p, chave)
    return {"ok": True, **{k: v for k, v in _com_interacoes(evento, login).items() if k in ("palmas", "bati", "quem", "quem_todos")}}


def comentar(id_evento: str, login: str, texto: str, hoje: Optional[date] = None, imagem: str = "") -> dict:
    """imagem (3.3.1.0): data URL de uma foto/GIF (PNG, JPEG ou WebP até 3 MB; GIF até 5 MB), só em comentário de publicação."""
    texto = " ".join((texto or "").split())  # comentário é uma linha: tira quebras e espaços repetidos
    conteudo_imagem, tipo_imagem = None, ""
    if imagem:
        if not id_evento.startswith("post:"):
            return {"ok": False, "erro": "foto ou GIF no comentário só nas publicações"}
        tipo_imagem, conteudo_imagem = _decodificar(imagem)
        if not conteudo_imagem or not _eh_imagem(tipo_imagem, conteudo_imagem):
            return {"ok": False, "erro": "a imagem precisa ser PNG, JPG, GIF ou WebP"}
        limite_img = MAX_BYTES_GIF_COMENTARIO if tipo_imagem == "image/gif" else MAX_BYTES_IMAGEM_COMENTARIO
        if len(conteudo_imagem) > limite_img:
            return {"ok": False, "erro": f"a imagem passa de {limite_img // (1024 * 1024)} MB"}
    if not texto and conteudo_imagem is None:
        return {"ok": False, "erro": "escreva alguma coisa"}
    if len(texto) > MAX_TEXTO_COMENTARIO:
        return {"ok": False, "erro": f"comentário muito longo (até {MAX_TEXTO_COMENTARIO} caracteres)"}
    evento = _evento_visivel(id_evento, login, hoje)
    if evento is None:
        return {"ok": False, "erro": "esse evento não está mais no mural"}
    if not evento.get("comentavel", True):
        return {"ok": False, "erro": "feedbacks e alinhamentos não recebem comentários"}
    novo = {"id": uuid.uuid4().hex[:10], "login": login, "texto": texto, "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    caminho_imagem = None
    if conteudo_imagem is not None:
        novo["imagem"] = novo["id"] + EXTENSAO_IMAGEM.get(tipo_imagem, ".png")
        novo["imagem_tipo"] = tipo_imagem
        caminho_imagem = os.path.join(_pasta_imagens_comentarios(), novo["imagem"])
        try:
            with open(caminho_imagem, "wb") as f:
                f.write(conteudo_imagem)
        except Exception:
            logger.exception("Não foi possível gravar a imagem do comentário.")
            return {"ok": False, "erro": "não foi possível gravar a imagem (detalhes no log)"}
    with _lock_comentarios:
        lista = COMENTARIOS.setdefault(id_evento, [])
        anteriores = {c["login"] for c in lista}
        lista.append(novo)
        if not _gravar_json("mural_comentarios.json", COMENTARIOS):
            lista.pop()
            if caminho_imagem:
                try:
                    os.remove(caminho_imagem)
                except OSError:
                    pass
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    texto_aviso = texto or "📷 mandou uma imagem"
    resumo = texto_aviso if len(texto_aviso) <= 80 else texto_aviso[:77] + "..."
    pessoas = _quem_e(evento)
    for p in pessoas:
        notificar(p, "comentario", login, f"{_nome(login)} comentou: \"{resumo}\"", id_evento, _link_evento(id_evento))
    for p in anteriores - set(pessoas):  # quem já tinha comentado fica sabendo da resposta
        notificar(p, "comentario", login, f"{_nome(login)} também comentou em: {evento['titulo']}", id_evento, _link_evento(id_evento))
    return {"ok": True, "comentarios": _comentarios_do_evento(id_evento, login)}


def apagar_publicacao(id_post: str, login: str) -> dict:
    """Apaga uma publicação manual (quem publicou ou admin), com as palminhas e os comentários dela (3.2.6.0)."""
    resultado = apagar_post(id_post, login)
    if not resultado.get("ok"):
        return resultado
    id_evento = "post:" + id_post
    with _lock_comentarios:
        comentarios_post = COMENTARIOS.pop(id_evento, None)
        if comentarios_post is not None:
            _gravar_json("mural_comentarios.json", COMENTARIOS)
    for c in comentarios_post or []:
        if c.get("imagem"):
            try:
                os.remove(os.path.join(_pasta_imagens_comentarios(), os.path.basename(c["imagem"])))
            except OSError:
                pass
    with _lock_palmas:
        if PALMAS.pop(id_evento, None) is not None:
            _gravar_json("mural_palmas.json", PALMAS)
    return {"ok": True}


def apagar_comentario(id_evento: str, id_comentario: str, login: str) -> dict:
    """Quem escreveu ou um administrador apaga."""
    admin = bool((USUARIOS_WEB.get(login) or {}).get("admin"))
    with _lock_comentarios:
        lista = COMENTARIOS.get(id_evento) or []
        alvo = next((c for c in lista if c["id"] == id_comentario), None)
        if alvo is None:
            return {"ok": False, "erro": "comentário não encontrado"}
        if alvo["login"] != login and not admin:
            return {"ok": False, "erro": "só quem escreveu (ou um administrador) apaga"}
        lista.remove(alvo)
        if not lista:
            COMENTARIOS.pop(id_evento, None)
        if not _gravar_json("mural_comentarios.json", COMENTARIOS):
            return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    if alvo.get("imagem"):
        try:
            os.remove(os.path.join(_pasta_imagens_comentarios(), os.path.basename(alvo["imagem"])))
        except OSError:
            pass
    return {"ok": True, "comentarios": _comentarios_do_evento(id_evento, login)}


# ---------------------------------------------------------------------------
# números do Movidesk (banco): carregam à parte pra não segurar o mural
# ---------------------------------------------------------------------------
PERCENTUAL_ALERTA_HORAS = 80  # abaixo disso a pessoa conta como "abaixo da meta" na gestão
# 3.2.6.1 (pedido do Igor): fora do % de horas da equipe (Gestão de equipe na Comunidade), em Ambos e em Monitoramento.
# Continuam no Horas Trabalhadas, no perfil e nos próprios números de cada um. (login no PDA, nome)
FORA_DO_PERCENTUAL_DA_EQUIPE = (
    ("nogueira", "Everton Nogueira"),
    ("debora", "Debora Sampaio"),
    ("igor", "Igor Leal"),
)
EQUIPES_GESTAO = ("Suporte", "Monitoramento")  # filtro da Gestão de equipe (3.0.2.0); vazio = as duas


def _somar_por_analista(resultado: dict) -> dict:
    por_analista = {}
    for linha in resultado.get("linhas") or []:
        soma = por_analista.setdefault(linha["analista"], {"minutos": 0, "tickets": 0})
        soma["minutos"] += linha["minutos_trabalhados"]
        soma["tickets"] += linha["qtd_tickets"]
    return por_analista


def _resumo_horas(minutos: int, tickets: int, meta: int) -> dict:
    from areas.horas_trabalhadas.logica import _minutos_para_horas_str
    return {"horas": _minutos_para_horas_str(minutos), "meta": _minutos_para_horas_str(meta), "tickets": tickets,
            "percentual": round(minutos / meta * 100, 1) if meta else None}


def _resumo_da_equipe(resultado: dict) -> dict:
    """Horas x meta, tickets e quantos estão abaixo de PERCENTUAL_ALERTA_HORAS, de uma consulta de apontamentos."""
    from areas.horas_trabalhadas.logica import filtro_por_pessoas
    fora = filtro_por_pessoas(FORA_DO_PERCENTUAL_DA_EQUIPE)
    metas = {a: m for a, m in (resultado.get("meta_periodo_por_analista") or {}).items() if not fora(a)}
    por_analista = {a: s for a, s in _somar_por_analista(resultado).items() if not fora(a)}
    abaixo = [a for a, meta in metas.items()
              if meta and por_analista.get(a, {"minutos": 0})["minutos"] / meta * 100 < PERCENTUAL_ALERTA_HORAS]
    return {**_resumo_horas(sum(s["minutos"] for s in por_analista.values()), resultado.get("total_tickets_periodo") or 0, sum(metas.values())),
            "pessoas": len(metas), "abaixo_meta": len(abaixo), "limite_alerta": PERCENTUAL_ALERTA_HORAS}


def numeros_movidesk_equipe(equipe: str, hoje: Optional[date] = None) -> dict:
    """Só os números da equipe (Suporte, Monitoramento ou as duas), pro filtro da Gestão de equipe."""
    from areas.horas_trabalhadas.logica import _consultar_horas_trabalhadas
    hoje = hoje or date.today()
    resultado = _consultar_horas_trabalhadas(hoje.replace(day=1).isoformat(), hoje.isoformat(), equipe_filtro=equipe or None)
    if not resultado.get("ok"):
        return {"ok": False, "erro": resultado.get("erro") or "o banco do Movidesk não respondeu"}
    return {"ok": True, "equipe": _resumo_da_equipe(resultado)}


def numeros_movidesk(login: str, com_equipe: bool, hoje: Optional[date] = None) -> dict:
    """Horas e tickets do mês de quem entrou e, pra administrador, da equipe toda.
    Uma consulta só de apontamentos (a mesma do Horas Trabalhadas)."""
    from areas.horas_trabalhadas.logica import _consultar_horas_trabalhadas
    from areas.manutencao_usuarios.movidesk import _nome_movidesk_vinculado
    hoje = hoje or date.today()
    resposta = {"ok": True, "eu": None, "equipe": None, "erro": None}
    nome_movidesk, erro_vinculo = _nome_movidesk_vinculado(login)
    if not nome_movidesk and not com_equipe:
        resposta["eu"] = {"vinculado": False, "erro": erro_vinculo}
        return resposta
    resultado = _consultar_horas_trabalhadas(hoje.replace(day=1).isoformat(), hoje.isoformat())
    if not resultado.get("ok"):
        return {"ok": False, "erro": resultado.get("erro") or "o banco do Movidesk não respondeu"}
    metas = resultado.get("meta_periodo_por_analista") or {}
    if nome_movidesk:
        meu = _somar_por_analista(resultado).get(nome_movidesk, {"minutos": 0, "tickets": 0})
        resposta["eu"] = {"vinculado": True, **_resumo_horas(meu["minutos"], meu["tickets"], metas.get(nome_movidesk, 0))}
    else:
        resposta["eu"] = {"vinculado": False, "erro": erro_vinculo}
    if com_equipe:
        resposta["equipe"] = _resumo_da_equipe(resultado)
    return resposta


def numeros_equipe(hoje: Optional[date] = None, equipe: str = "") -> dict:
    """Números da gestão que não dependem do banco: pessoas por equipe e quem está fora hoje
    (só de uma equipe, com `equipe`; quem é "Suporte e Monitoramento" conta nas duas)."""
    hoje = hoje or date.today()
    hoje_iso = hoje.isoformat()
    ativos = [l for l in USUARIOS_WEB if _ativo(l)
              and (not equipe or _pertence_a_equipe(USUARIOS_WEB[l].get("atribuicao") or "Suporte", equipe))]
    equipes = {}
    for l in ativos:
        equipe = (USUARIOS_WEB[l].get("atribuicao") or "Suporte")
        equipes[equipe] = equipes.get(equipe, 0) + 1
    with _lock_ferias:
        fora = [dict(f) for f in FERIAS if (f.get("inicio") or "") <= hoje_iso <= (f.get("fim") or "")]
    return {"ativos": len(ativos), "equipes": equipes,
            "fora_hoje": [{**_pessoa(f["usuario"]), "tipo": f.get("tipo", "ferias"), "fim": f.get("fim")}
                          for f in fora if f.get("usuario") in ativos],
            "sem_data_inicio": sum(1 for l in ativos if not _data(USUARIOS_WEB[l].get("data_inicio") or ""))}
