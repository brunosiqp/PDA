"""Insígnias do perfil (2.35.5.0).

- PDA Dev/Founder: só Debora Sampaio e Igor Leal.
- PDA Contributor: Wagner Faria, Caio Peixoto, Igor Leal, Debora Sampaio, Eduardo Yamada e Sabrina Barros.
- PDA Beta User: campanha. A pessoa recebe o convite no hub, clica em "Quero
  participar" e informa o que falta: foto de perfil, data em que entrou na empresa,
  aniversário, e-mail da Empresa e o histórico na empresa (cargo atual). Com tudo
  preenchido, desbloqueia e fica gravada (usuarios.json, "insignias") mesmo se algo
  for apagado depois. No desbloqueio, um e-mail avisa os responsáveis das equipes
  do Feedbacks (EQUIPES_FEEDBACK), uma vez por pessoa.
- Tempo de casa: pelos anos completos desde a data de início, com o número na
  insígnia e a cor do nível (1 bronze, 2 prata, 3 ouro, 4 platina, 5+ diamante).
  Antes de 1 ano, ferro com os meses completos (1 a 11), desde a 3.0.2.0.

A pessoa escolhe uma insígnia pra ficar em destaque junto da foto ("insignia_destaque").
As que ela ainda não viu ("insignias_vistas") aparecem numa comemoração no próximo
acesso ao hub ou ao perfil.
"""
import logging
import re
import threading
import unicodedata
from datetime import date, datetime
from typing import Optional

from areas.perfil.logica import HISTORICO_CARREIRA, _lock_historico_carreira
from nucleo.fotos import _caminho_foto_usuario
from nucleo.usuarios import USUARIOS_WEB, _salvar_usuarios

logger = logging.getLogger("alertas")


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(texto.lower().split())


# login e, de reserva, o nome (o login pode ser diferente na remota)
FUNDADORES = {"logins": {"debora", "igor"}, "nomes": {"debora sampaio", "igor leal"}}
# 3.0.4.0: Igor, Debora, Eduardo Yamada e Sabrina Barros também (pedido do Igor)
CONTRIBUIDORES = {"logins": {"wagner.faria", "caio.peixoto", "igor", "debora", "eduardo", "toledo"},
                  "nomes": {"wagner faria", "caio peixoto", "igor leal", "debora sampaio", "eduardo yamada", "sabrina barros"}}
# Bug Hunter (3.0.5.0): achou e reportou um bug no PDA. Quem já tinha achado ganhou pela lista
# abaixo; os próximos o Igor ou a Debora concedem no perfil, depois de aprovar o bug.
BUG_HUNTERS = {"logins": {"paula", "ivan.campos", "ivan.igarashi", "douglas", "igor", "debora", "eduardo"},
               "nomes": {"paula matos", "ivan campos", "ivan igarashi", "douglas queiroz", "igor leal", "debora sampaio", "eduardo yamada"}}
# Insígnias que o Igor e a Debora concedem (ou tiram) à mão no perfil; ficam em usuarios.json
# "insignias" ({id: "AAAA-MM-DD"}). Quem está na lista fixa (CONTRIBUIDORES/BUG_HUNTERS)
# já tem e não dá pra tirar por ali.
# Rank Master: ter N produtos no Rank Master (o nível acima do ouro) no card Ranks por Produtos.
# Nasceram como Rank Ouro (desenho na 3.0.5.0, liberadas pelos ouros na 3.0.7.0); na 3.0.9.0 o Igor
# criou o Master e as insígnias passaram a contar os produtos no Master (ids rank_master_N).
METAS_RANK_MASTER = [1, 3, 5, 7, 10]
# Palminhas recebidas no mural (3.1.3.0): por nível, como o Rank Master (fica só a maior meta alcançada)
METAS_PALMAS = [10, 50, 100, 250, 1000]
# 3.1.8.0, pedido do Igor: "por agora não crie e nem mostre em nenhum lugar as insígnias das palminhas, mas deixe
# isso salvo". Desligadas aqui: não entram em insignias_de (então não desbloqueiam, não avisam, não aparecem no
# perfil, no mural nem no destaque) e a tela dos Rankings esconde as metas. O leaderboard de palminhas continua.
# Pra ligar de novo, é só trocar pra True (o desenho e os textos continuam em telas/insignias.py).
INSIGNIAS_PALMAS_ATIVAS = False


def rotulo_palmas(n: int) -> str:
    return f"{n // 1000}k" if n >= 1000 and n % 1000 == 0 else str(n)
INSIGNIAS_CONCEDIVEIS = {"contribuidor": "PDA Contributor", "bug_hunter": "Bug Hunter"}
_GRUPO_FIXO = {"contribuidor": CONTRIBUIDORES, "bug_hunter": BUG_HUNTERS}
REQUISITOS_BUG_HUNTER = [
    "Encontre um bug no PDA: visual (algo desalinhado, texto errado, tela quebrada no celular ou no modo claro) ou de funcionamento (botão que não responde, erro, número que não bate).",
    "Reporte pro Igor Leal ou pra Debora Sampaio, com um print e o passo a passo pra ver o problema acontecer.",
    "Depois da aprovação, eles liberam a insígnia no seu perfil e você fica sabendo pelo sininho.",
]

# Diamante a partir de 5 anos, com o número de cada ano na insígnia, mapeado até
# ANOS_TEMPO_MAXIMO (o colaborador mais antigo hoje tem 15). Cada ano completo é uma
# insígnia nova (id tempo_N), que entra na comemoração uma vez.
ANOS_TEMPO_MAXIMO = 15
NIVEIS_TEMPO = [  # (anos mínimos, id, nome)
    (5, "diamante", "Diamante"),
    (4, "platina", "Platina"),
    (3, "ouro", "Ouro"),
    (2, "prata", "Prata"),
    (1, "bronze", "Bronze"),
]
# Antes de 1 ano (3.0.2.0): insígnia de ferro com o número de meses completos (1 a 11), id
# tempo_mN, uma nova a cada mês; com 12 meses vira a de bronze (1 ano). Começa com "tempo_"
# pra quem destacou continuar com a de tempo de casa quando ela muda.
NIVEL_MESES = ("ferro", "Ferro")

REQUISITOS_BETA = [
    ("foto", "Adicionar uma foto de perfil"),
    ("data_inicio", "Informar o dia em que entrou na empresa"),
    ("aniversario", "Informar o dia do seu aniversário"),
    ("email", "Informar seu e-mail da Empresa"),
    ("historico", "Adicionar seu histórico na empresa"),
]
# a campanha Beta User vai até este dia, inclusive (3.1.2.0, pedido do Igor): depois dele ninguém mais
# consegue a insígnia (quem já tem continua com ela)
FIM_CAMPANHA_BETA = "2026-12-31"


def campanha_beta_aberta(hoje: Optional[date] = None) -> bool:
    return (hoje or date.today()).isoformat() <= FIM_CAMPANHA_BETA


def _fim_beta_br() -> str:
    a, m, d = FIM_CAMPANHA_BETA.split("-")
    return f"{d}/{m}/{a}"


DOMINIO_EMAIL = "example.com"
RE_EMAIL_EMPRESA = re.compile(r"^[A-Za-z0-9._%+-]+@empresa\.com\.br$", re.I)
NOMES_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
               "setembro", "outubro", "novembro", "dezembro"]


def _esta_em(grupo: dict, login: str) -> bool:
    info = USUARIOS_WEB.get(login) or {}
    return login in grupo["logins"] or _normalizar(info.get("nome") or "") in grupo["nomes"]


def _data_inicio(login: str) -> Optional[date]:
    try:
        return datetime.strptime((USUARIOS_WEB.get(login) or {}).get("data_inicio") or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def aniversario_valido(valor: str) -> bool:
    """"MM-DD" (só dia e mês: o ano não é pedido)."""
    try:
        datetime.strptime("2000-" + (valor or ""), "%Y-%m-%d")  # 2000 é bissexto: aceita 02-29
        return True
    except ValueError:
        return False


def aniversario_legivel(valor: str) -> str:
    if not aniversario_valido(valor):
        return ""
    mes, dia = valor.split("-")
    return f"{int(dia)} de {NOMES_MESES[int(mes) - 1]}"


def _anos_completos(inicio: date, hoje: date) -> int:
    return max(hoje.year - inicio.year - ((hoje.month, hoje.day) < (inicio.month, inicio.day)), 0)


def _aniversario_empresa(inicio: date, anos: int) -> date:
    try:
        return inicio.replace(year=inicio.year + anos)
    except ValueError:  # 29/02
        return inicio.replace(year=inicio.year + anos, day=28)


def _meses_completos(inicio: date, hoje: date) -> int:
    return max((hoje.year - inicio.year) * 12 + hoje.month - inicio.month - (hoje.day < inicio.day), 0)


def _somar_meses(inicio: date, meses: int) -> date:
    total = inicio.month - 1 + meses
    ano, mes = inicio.year + total // 12, total % 12 + 1
    for dia in (inicio.day, 30, 29, 28):  # 31/01 + 1 mês = 28 ou 29/02
        try:
            return date(ano, mes, dia)
        except ValueError:
            continue


def insignia_meses(inicio: date, hoje: date) -> Optional[dict]:
    """A de ferro de quem tem de 1 a 11 meses completos (None fora disso)."""
    meses = _meses_completos(inicio, hoje)
    if not 1 <= meses <= 11:
        return None
    proximo = ({"meses": meses + 1, "nivel_nome": "Ferro", "data": _somar_meses(inicio, meses + 1).isoformat()} if meses < 11
               else {"anos": 1, "nivel_nome": "Bronze", "data": _aniversario_empresa(inicio, 1).isoformat()})
    return {"id": f"tempo_m{meses}", "tipo": "tempo", "nivel": NIVEL_MESES[0], "nivel_nome": NIVEL_MESES[1], "anos": 0, "meses": meses,
            "nome": f"{meses} {'mês' if meses == 1 else 'meses'} de empresa", "descricao": "Nível Ferro",
            "desbloqueada": True, "quando": _somar_meses(inicio, meses).isoformat(), "proximo": proximo}


def _masters_rank(login: str) -> int:
    # import aqui dentro: ranks_produtos importa METAS_RANK_MASTER daqui (evita import circular)
    try:
        from areas.ranks_produtos.logica import masters_de
        return masters_de(login)
    except Exception:
        logger.exception("Não foi possível contar os Rank Master de '%s'.", login)
        return 0


def _palmas_recebidas(login: str) -> int:
    # import aqui dentro: o mural importa este módulo (evita import circular)
    try:
        from areas.mural.logica import palmas_recebidas
        return palmas_recebidas(login)
    except Exception:
        logger.exception("Não foi possível contar as palminhas de '%s'.", login)
        return 0


def _insignia_palmas(n: int, recebidas: int, alcancada: bool) -> dict:
    proxima = next((m for m in METAS_PALMAS if recebidas < m), None)
    return {"id": f"palmas_{n}", "tipo": "palmas", "palmas": n, "nome": f"{rotulo_palmas(n)} palminhas",
            "descricao": (f"Recebeu {rotulo_palmas(n)} palminhas no mural" if alcancada else f"Receba {rotulo_palmas(n)} palminhas no mural"),
            "desbloqueada": alcancada, "quando": None, "recebidas": recebidas,
            "proximo": {"palmas": proxima, "faltam": proxima - recebidas} if proxima else None}


def nivel_tempo(anos: int) -> Optional[tuple]:
    return next(((i, n) for minimo, i, n in NIVEIS_TEMPO if anos >= minimo), None)


def _tem_historico(login: str) -> bool:
    with _lock_historico_carreira:
        return any(h.get("usuario") == login for h in HISTORICO_CARREIRA)


def requisitos_beta(login: str) -> list:
    info = USUARIOS_WEB.get(login) or {}
    feito = {
        "foto": _caminho_foto_usuario(login) is not None,
        "data_inicio": _data_inicio(login) is not None,
        "aniversario": aniversario_valido(info.get("aniversario") or ""),
        "email": bool(RE_EMAIL_EMPRESA.match((info.get("email") or "").strip())),
        "historico": _tem_historico(login),
    }
    return [{"id": i, "nome": n, "feito": feito[i]} for i, n in REQUISITOS_BETA]


# ---------------------------------------------------------------------------
# aviso por e-mail quando alguém ganha a Beta User
# ---------------------------------------------------------------------------
def destinatarios_aviso_beta() -> list:
    """Todos os e-mails das equipes do Feedbacks (EQUIPES_FEEDBACK), cada pessoa uma vez só."""
    from areas.feedbacks.logica import EQUIPES_FEEDBACK  # aqui dentro: só precisa no envio
    vistos, lista = set(), []
    for pessoas in EQUIPES_FEEDBACK.values():
        for _nome, email, *_ in pessoas:
            chave = (email or "").strip().lower()
            if chave and chave not in vistos:
                vistos.add(chave)
                lista.append(email.strip())
    return lista


def _avisar_beta(login: str) -> None:
    try:
        from areas.emails.logica import notificar_insignia_beta
        info = USUARIOS_WEB.get(login) or {}
        notificar_insignia_beta(
            nome=info.get("nome") or login,
            email=info.get("email") or "",
            data_inicio=info.get("data_inicio") or "",
            aniversario=aniversario_legivel(info.get("aniversario") or ""),
            destinatarios=destinatarios_aviso_beta(),
            login=login,
        )
    except Exception:
        logger.exception("Falha ao avisar por e-mail a insígnia PDA Beta User de '%s'.", login)


# chamado quando a Beta User é desbloqueada (troca nos testes pra não mandar e-mail)
ao_desbloquear_beta = lambda login: threading.Thread(target=_avisar_beta, args=(login,), daemon=True).start()  # noqa: E731


def _desbloqueios(login: str) -> dict:
    """Insígnias que ficam gravadas depois de conquistadas ({id: "AAAA-MM-DD"}).
    Grava a Beta User na primeira vez que os requisitos estão completos."""
    info = USUARIOS_WEB.get(login)
    if info is None:
        return {}
    gravadas = dict(info.get("insignias") or {})
    if "beta_user" not in gravadas and campanha_beta_aberta() and all(r["feito"] for r in requisitos_beta(login)):
        gravadas["beta_user"] = date.today().isoformat()
        info["insignias"] = gravadas
        _salvar_usuarios(USUARIOS_WEB)
        ao_desbloquear_beta(login)
    return gravadas


def insignias_de(login: str, com_bloqueadas: bool = False) -> list:
    """Insígnias da pessoa, na ordem de exibição. Cada uma:
    {id, tipo, nome, descricao, desbloqueada, quando, destaque, ...}. Com
    com_bloqueadas, inclui a Beta User e a de tempo de casa ainda não conquistadas
    (pro próprio perfil mostrar o que falta)."""
    info = USUARIOS_WEB.get(login)
    if info is None:
        return []
    hoje = date.today()
    gravadas = _desbloqueios(login)
    lista = []
    if _esta_em(FUNDADORES, login):
        lista.append({"id": "fundador", "tipo": "fundador", "nome": "PDA Dev/Founder",
                      "descricao": "Criou e desenvolve o PDA", "desbloqueada": True, "quando": None})
    if _esta_em(CONTRIBUIDORES, login) or "contribuidor" in gravadas:
        lista.append({"id": "contribuidor", "tipo": "contribuidor", "nome": "PDA Contributor",
                      "descricao": "Contribuiu com o desenvolvimento do PDA", "desbloqueada": True, "quando": gravadas.get("contribuidor")})
    if _esta_em(BUG_HUNTERS, login) or "bug_hunter" in gravadas:
        lista.append({"id": "bug_hunter", "tipo": "bug", "nome": "Bug Hunter", "descricao": "Achou e reportou um bug no PDA",
                      "desbloqueada": True, "quando": gravadas.get("bug_hunter")})
    elif com_bloqueadas:
        lista.append({"id": "bug_hunter", "tipo": "bug", "nome": "Bug Hunter", "descricao": "Ache e reporte um bug no PDA",
                      "desbloqueada": False, "quando": None, "requisitos_texto": REQUISITOS_BUG_HUNTER})

    if "beta_user" in gravadas:
        lista.append({"id": "beta_user", "tipo": "beta", "nome": "PDA Beta User",
                      "descricao": "Participou da campanha da fase beta do PDA", "desbloqueada": True, "quando": gravadas["beta_user"]})
    elif com_bloqueadas and campanha_beta_aberta():
        lista.append({"id": "beta_user", "tipo": "beta", "nome": "PDA Beta User",
                      "descricao": "Participe da campanha pra desbloquear", "desbloqueada": False, "quando": None,
                      "requisitos": requisitos_beta(login), "fim_campanha": FIM_CAMPANHA_BETA})
    elif com_bloqueadas:
        lista.append({"id": "beta_user", "tipo": "beta", "nome": "PDA Beta User",
                      "descricao": f"Campanha encerrada em {_fim_beta_br()}", "desbloqueada": False, "quando": None,
                      "encerrada": True, "fim_campanha": FIM_CAMPANHA_BETA})

    inicio = _data_inicio(login)
    anos = _anos_completos(inicio, hoje) if inicio else 0
    nivel = nivel_tempo(anos)
    if nivel:
        # acima do mapeado continua mostrando o número de anos (e o id fica no último mapeado)
        lista.append({"id": f"tempo_{min(anos, ANOS_TEMPO_MAXIMO)}", "tipo": "tempo", "nivel": nivel[0], "nivel_nome": nivel[1], "anos": anos,
                      "nome": f"{anos} {'ano' if anos == 1 else 'anos'} de empresa", "descricao": f"Nível {nivel[1]}",
                      "desbloqueada": True, "quando": _aniversario_empresa(inicio, anos).isoformat(),
                      "proximo": {"anos": anos + 1, "nivel_nome": nivel_tempo(anos + 1)[1],
                                  "data": _aniversario_empresa(inicio, anos + 1).isoformat()}})
    elif inicio and insignia_meses(inicio, hoje):
        lista.append(insignia_meses(inicio, hoje))
    elif com_bloqueadas:
        falta = None
        if inicio:
            falta = {"anos": 1, "nivel_nome": "Bronze", "data": _aniversario_empresa(inicio, 1).isoformat(),
                     "dias": (_aniversario_empresa(inicio, 1) - hoje).days}
        lista.append({"id": "tempo_1", "tipo": "tempo", "nivel": "bronze", "nivel_nome": "Bronze", "anos": 1,
                      "nome": "1 ano de empresa", "descricao": "Nível Bronze", "desbloqueada": False, "quando": None,
                      "sem_data_inicio": inicio is None, "proximo": falta})

    # Rank Master funciona por nível, como o tempo de casa (3.1.0.0): fica só a maior meta alcançada,
    # com a próxima na descrição; subir de nível troca a insígnia (id novo = comemoração nova)
    masters = _masters_rank(login)
    alcancada = max((m for m in METAS_RANK_MASTER if masters >= m), default=None)
    proxima = next((m for m in METAS_RANK_MASTER if masters < m), None)
    if alcancada or com_bloqueadas:
        n = alcancada or METAS_RANK_MASTER[0]
        produtos = "produto" if n == 1 else "produtos"
        lista.append({"id": f"rank_master_{n}", "tipo": "rank", "produtos": n, "nome": f"Rank Master · {n} {produtos}",
                      "descricao": (f"Tem {n} {produtos} no Rank Master" if alcancada else f"Tenha {n} {produtos} no Rank Master"),
                      "desbloqueada": bool(alcancada), "quando": None, "masters": masters,
                      "proximo": {"produtos": proxima, "faltam": proxima - masters} if proxima else None})

    recebidas = _palmas_recebidas(login) if INSIGNIAS_PALMAS_ATIVAS else 0
    alcancada_p = max((m for m in METAS_PALMAS if recebidas >= m), default=None)
    if INSIGNIAS_PALMAS_ATIVAS and (alcancada_p or com_bloqueadas):
        lista.append(_insignia_palmas(alcancada_p or METAS_PALMAS[0], recebidas, bool(alcancada_p)))

    destaque = destaque_de(login, lista)
    for i in lista:
        i["destaque"] = i["desbloqueada"] and i["id"] == destaque
    return lista


def destaque_de(login: str, lista: Optional[list] = None) -> Optional[str]:
    """Id da insígnia em destaque, se ainda for uma conquistada (a de tempo de casa
    acompanha o nível: quem destacou 'tempo_2' continua com a de tempo ao subir)."""
    escolhida = (USUARIOS_WEB.get(login) or {}).get("insignia_destaque")
    if not escolhida:
        return None
    ganhas = [i for i in (lista if lista is not None else insignias_de(login)) if i["desbloqueada"]]
    if escolhida.startswith("tempo_"):
        tempo = next((i for i in ganhas if i["tipo"] == "tempo"), None)
        return tempo["id"] if tempo else None
    if escolhida.startswith("rank_master_"):  # acompanha o nível, como o tempo de casa
        rank = next((i for i in ganhas if i["tipo"] == "rank"), None)
        return rank["id"] if rank else None
    if escolhida.startswith("palmas_"):
        palmas = next((i for i in ganhas if i["tipo"] == "palmas"), None)
        return palmas["id"] if palmas else None
    return escolhida if any(i["id"] == escolhida for i in ganhas) else None


def insignia_em_destaque(login: str) -> Optional[dict]:
    """A insígnia que a pessoa destacou, pronta pro desenho (tipo/nivel/anos), SEM
    efeitos colaterais: diferente de insignias_de, não grava a Beta User nem manda
    e-mail. É a que o mural usa pra mostrar a insígnia de cada pessoa junto da foto
    (3.0.1.0) - abrir o mural não pode desbloquear insígnia dos outros."""
    info = USUARIOS_WEB.get(login) or {}
    escolhida = info.get("insignia_destaque") or ""
    if escolhida == "fundador" and _esta_em(FUNDADORES, login):
        return {"id": "fundador", "tipo": "fundador", "nome": "PDA Dev/Founder"}
    gravadas = info.get("insignias") or {}
    if escolhida == "contribuidor" and (_esta_em(CONTRIBUIDORES, login) or "contribuidor" in gravadas):
        return {"id": "contribuidor", "tipo": "contribuidor", "nome": "PDA Contributor"}
    if escolhida == "bug_hunter" and (_esta_em(BUG_HUNTERS, login) or "bug_hunter" in gravadas):
        return {"id": "bug_hunter", "tipo": "bug", "nome": "Bug Hunter"}
    if escolhida.startswith("rank_master_"):  # a do nível atual, não necessariamente a que foi destacada
        n = max((m for m in METAS_RANK_MASTER if _masters_rank(login) >= m), default=None)
        if n:
            return {"id": f"rank_master_{n}", "tipo": "rank", "produtos": n, "nome": f"Rank Master · {n} {'produto' if n == 1 else 'produtos'}"}
    if escolhida.startswith("palmas_") and INSIGNIAS_PALMAS_ATIVAS:  # a do nível atual
        n = max((m for m in METAS_PALMAS if _palmas_recebidas(login) >= m), default=None)
        if n:
            return {"id": f"palmas_{n}", "tipo": "palmas", "palmas": n, "nome": f"{rotulo_palmas(n)} palminhas"}
    if escolhida == "beta_user" and "beta_user" in (info.get("insignias") or {}):
        return {"id": "beta_user", "tipo": "beta", "nome": "PDA Beta User"}
    if escolhida.startswith("tempo_"):
        inicio = _data_inicio(login)
        anos = _anos_completos(inicio, date.today()) if inicio else 0
        nivel = nivel_tempo(anos)
        if nivel:
            return {"id": f"tempo_{min(anos, ANOS_TEMPO_MAXIMO)}", "tipo": "tempo", "nivel": nivel[0], "nivel_nome": nivel[1],
                    "anos": anos, "nome": f"{anos} {'ano' if anos == 1 else 'anos'} de empresa"}
        if inicio and insignia_meses(inicio, date.today()):
            return insignia_meses(inicio, date.today())
    return None


def concessoes(login: str) -> list:
    """Pro painel "Conceder insígnias" do perfil (só Igor e Debora veem): o estado de cada concedível."""
    gravadas = (USUARIOS_WEB.get(login) or {}).get("insignias") or {}
    return [{"id": i, "nome": nome, "tem": _esta_em(_GRUPO_FIXO[i], login) or i in gravadas,
             "fixa": _esta_em(_GRUPO_FIXO[i], login), "quando": gravadas.get(i)} for i, nome in INSIGNIAS_CONCEDIVEIS.items()]


def conceder(login: str, id_insignia: str, dar: bool, por: str) -> dict:
    """Dá ou tira uma insígnia concedível (Bug Hunter, PDA Contributor). Quem decide se pode é a rota."""
    info = USUARIOS_WEB.get(login)
    if info is None:
        return {"ok": False, "erro": "usuário não encontrado"}
    if id_insignia not in INSIGNIAS_CONCEDIVEIS:
        return {"ok": False, "erro": "essa insígnia não é concedida à mão"}
    if _esta_em(_GRUPO_FIXO[id_insignia], login):
        return {"ok": False, "erro": "essa pessoa já tem pela lista fixa (só muda no código)"}
    gravadas = dict(info.get("insignias") or {})
    if dar and id_insignia not in gravadas:
        gravadas[id_insignia] = date.today().isoformat()
        # o aviso de quem concedeu sai logo abaixo; o registro de desbloqueio só não repete (o mural usa a data acima)
        registro = dict(info.get("insignias_desbloqueio") or {})
        registro[id_insignia] = {"data": date.today().isoformat(), "mural": False, "em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        info["insignias_desbloqueio"] = registro
        # volta a ser "nova" pra comemoração aparecer no próximo acesso dela
        info["insignias_vistas"] = [v for v in (info.get("insignias_vistas") or []) if v != id_insignia]
    elif not dar:
        gravadas.pop(id_insignia, None)
        registro = dict(info.get("insignias_desbloqueio") or {})
        registro.pop(id_insignia, None)  # se conceder de novo, avisa de novo
        info["insignias_desbloqueio"] = registro
        if info.get("insignia_destaque") == id_insignia:
            info["insignia_destaque"] = None
    info["insignias"] = gravadas
    if not _salvar_usuarios(USUARIOS_WEB):
        return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    if dar:
        from nucleo.notificacoes import notificar  # aqui dentro: nucleo não depende das áreas
        nome_por = (USUARIOS_WEB.get(por) or {}).get("nome") or por
        notificar(login, "insignia", por, f"{nome_por} te deu a insígnia {INSIGNIAS_CONCEDIVEIS[id_insignia]}! 🏅", "", f"/perfil/{login}#insignias",
                  f"insignia:{id_insignia}:{login}")
    return {"ok": True, "concessoes": concessoes(login)}


# ---------------------------------------------------------------------------
# aviso de toda insígnia desbloqueada (3.0.6.0)
# ---------------------------------------------------------------------------
# Antes só a Bug Hunter e a PDA Contributor concedidas à mão avisavam. Agora, na primeira vez
# que o PDA vê uma insígnia desbloqueada de alguém (lista fixa, Founder, Beta User, tempo de
# casa, Ferro...), grava em usuarios.json "insignias_desbloqueio" ({id: {"data", "mural"}}) e:
# - se a pessoa ainda não tinha visto essa insígnia (insignias_vistas), avisa no sininho dela;
# - e marca "mural": o mural anuncia (as de tempo de casa e a Beta User já têm aviso próprio lá).
# Quem já tinha visto (ex.: comemorou antes desta versão) não recebe aviso repetido.
INTERVALO_VARREDURA_DESBLOQUEIOS = 300  # segundos entre uma varredura de todo mundo e outra
_ultima_varredura = {"em": 0.0}


def registrar_desbloqueios(login: str, hoje: Optional[date] = None) -> list:
    """Registra (e avisa) as insígnias desbloqueadas de `login` que ainda não foram registradas."""
    info = USUARIOS_WEB.get(login)
    if info is None or not info.get("ativo", True):
        return []
    hoje = hoje or date.today()
    registro = dict(info.get("insignias_desbloqueio") or {})
    novas = [i for i in insignias_de(login) if i["desbloqueada"] and i["id"] not in registro]
    if not novas:
        return []
    vistas = set(info.get("insignias_vistas") or [])
    for i in novas:
        # "em" (3.2.4.0): hora do desbloqueio, pra ordenar o feed do mural
        registro[i["id"]] = {"data": hoje.isoformat(), "mural": i["id"] not in vistas, "em": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    info["insignias_desbloqueio"] = registro
    if not _salvar_usuarios(USUARIOS_WEB):
        return []
    from nucleo.notificacoes import notificar  # aqui dentro: nucleo não depende das áreas
    for i in novas:
        if i["id"] not in vistas:
            notificar(login, "insignia", "", f"Você desbloqueou a insígnia {i['nome']}! 🏅", "", f"/perfil/{login}#insignias",
                      f"desbloqueio:{i['id']}:{login}")
    return novas


_limpeza_palmas = {"feita": False}


def _limpar_rastros_insignias_palmas() -> None:
    """Insígnias de palminhas desligadas (3.1.8.0): uma vez por partida, tira do sininho os avisos de desbloqueio
    que já tinham saído e o registro de desbloqueio (se um dia forem ligadas de novo, avisam de novo)."""
    if INSIGNIAS_PALMAS_ATIVAS or _limpeza_palmas["feita"]:
        return
    _limpeza_palmas["feita"] = True
    from nucleo.notificacoes import apagar_por_chave
    mudou = False
    for login, info in USUARIOS_WEB.items():
        registro = info.get("insignias_desbloqueio") or {}
        for id_ins in [i for i in registro if i.startswith("palmas_")]:
            registro.pop(id_ins, None)
            mudou = True
        for n in METAS_PALMAS:
            apagar_por_chave(login, f"desbloqueio:palmas_{n}:{login}")
    if mudou:
        _salvar_usuarios(USUARIOS_WEB)


def registrar_desbloqueios_de_todos(forcar: bool = False) -> None:
    """Varre todo mundo (no máximo a cada INTERVALO_VARREDURA_DESBLOQUEIOS): chamada pelo mural."""
    import time
    try:
        _limpar_rastros_insignias_palmas()
    except Exception:
        logger.exception("Não foi possível limpar os avisos das insígnias de palminhas.")
    agora = time.time()
    if not forcar and agora - _ultima_varredura["em"] < INTERVALO_VARREDURA_DESBLOQUEIOS:
        return
    _ultima_varredura["em"] = agora
    for login in list(USUARIOS_WEB):
        if login.lower().startswith("teste"):
            continue
        try:
            registrar_desbloqueios(login)
        except Exception:
            logger.exception("Não foi possível registrar as insígnias desbloqueadas de '%s'.", login)


def definir_destaque(login: str, id_insignia: str) -> dict:
    info = USUARIOS_WEB.get(login)
    if info is None:
        return {"ok": False, "erro": "usuário não encontrado"}
    if id_insignia and not any(i["id"] == id_insignia and i["desbloqueada"] for i in insignias_de(login)):
        return {"ok": False, "erro": "essa insígnia ainda não foi conquistada"}
    info["insignia_destaque"] = id_insignia or None
    if not _salvar_usuarios(USUARIOS_WEB):
        return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    return {"ok": True, "destaque": id_insignia or None}


# ---------------------------------------------------------------------------
# campanha: convite, formulário de participação e comemoração
# ---------------------------------------------------------------------------
def campanha(login: str) -> dict:
    """O que o hub/perfil mostram ao abrir: o convite da Beta User (se ainda não
    tem), o que já está preenchido (pro formulário) e as insígnias novas pra comemorar."""
    info = USUARIOS_WEB.get(login) or {}
    insignias = insignias_de(login)
    vistas = set(info.get("insignias_vistas") or [])
    novas = [i for i in insignias if i["desbloqueada"] and i["id"] not in vistas]
    tem_beta = any(i["id"] == "beta_user" for i in insignias)
    with _lock_historico_carreira:
        atual = sorted((h for h in HISTORICO_CARREIRA if h.get("usuario") == login), key=lambda h: h.get("inicio") or "")
    return {
        "ok": True,
        "usuario": login,
        "primeiro_nome": ((info.get("nome") or login).split() or [login])[0],
        "convite_beta": not tem_beta and campanha_beta_aberta(),
        "requisitos": requisitos_beta(login) if not tem_beta else [],
        "fim_beta": FIM_CAMPANHA_BETA,
        "beta_aberta": campanha_beta_aberta(),
        "atual": {
            "data_inicio": info.get("data_inicio") or "",
            "aniversario": info.get("aniversario") or "",
            "email": info.get("email") or "",
            "tem_foto": _caminho_foto_usuario(login) is not None,
            "cargo_atual": (atual[-1].get("cargo") if atual else "") or "",
            "cargo_pda": info.get("cargo") or "",
        },
        "hoje": date.today().isoformat(),
        "destaque": destaque_de(login, insignias),
        "novas": novas,
    }


def _mes_legivel(aaaa_mm: str) -> str:
    ano, mes = aaaa_mm.split("-")
    return f"{NOMES_MESES[int(mes) - 1]} de {ano}"


def validar_participacao(login: str, dados: dict) -> tuple:
    """Confere o formulário "Quero participar". Devolve (campos, None, None) ou
    (None, erro, campo) - campo diz qual pedaço do formulário marcar em vermelho.
    campos: data_inicio, aniversario, email e, se a pessoa ainda não tem histórico,
    historico = {cargo, area, inicio}. Foto é tratada na rota (tem_foto_nova).
    O cargo pode ser "desde que entrei" (cargo_desde_entrada=true: usa o mês de
    entrada) ou um mês/ano entre a entrada e o mês atual do SERVIDOR (2.35.6.0: o
    calendário do navegador deixava escolher um mês que o servidor ainda não tinha
    chegado e a mensagem não dizia o porquê)."""
    if login not in USUARIOS_WEB:
        return None, "usuário não encontrado", None
    if not campanha_beta_aberta():
        return None, f"a campanha PDA Beta User terminou em {_fim_beta_br()}", None
    hoje = date.today()
    mes_atual = hoje.strftime("%Y-%m")
    campos = {}

    if _caminho_foto_usuario(login) is None and dados.get("tem_foto_nova") != "true":
        return None, "Adicione uma foto de perfil.", "foto"

    data_inicio = (dados.get("data_inicio") or "").strip()
    try:
        lida = datetime.strptime(data_inicio, "%Y-%m-%d").date()
    except ValueError:
        return None, "Informe o dia em que você entrou na empresa.", "data_inicio"
    if lida > hoje:
        return None, f"A data de entrada não pode ser depois de hoje ({hoje.strftime('%d/%m/%Y')}).", "data_inicio"
    if lida.year < 1980:
        return None, "Confira o ano em que você entrou na empresa.", "data_inicio"
    campos["data_inicio"] = data_inicio

    try:
        aniversario = f"{int(dados.get('aniversario_mes') or 0):02d}-{int(dados.get('aniversario_dia') or 0):02d}"
    except ValueError:
        aniversario = ""
    if not aniversario_valido(aniversario):
        return None, "Informe um dia e um mês de aniversário que existam.", "aniversario"
    campos["aniversario"] = aniversario

    email = (dados.get("email") or "").strip()
    if not RE_EMAIL_EMPRESA.match(email):
        return None, f"Use seu e-mail da Empresa (termina com @{DOMINIO_EMAIL}).", "email"
    campos["email"] = email.lower()

    if not _tem_historico(login):
        cargo = (dados.get("cargo") or "").strip()
        area = (dados.get("area") or "").strip()
        if not cargo or len(cargo) > 60:
            return None, "Informe seu cargo atual (até 60 caracteres).", "cargo"
        if dados.get("cargo_desde_entrada") == "true":
            inicio_cargo = data_inicio[:7]
        else:
            inicio_cargo = (dados.get("cargo_inicio") or "").strip()
            if not re.match(r"^\d{4}-(0[1-9]|1[0-2])$", inicio_cargo):
                return None, "Escolha o mês e o ano em que você começou nesse cargo.", "cargo_inicio"
            if inicio_cargo > mes_atual:
                return None, f"Esse mês ainda não chegou: escolha até {_mes_legivel(mes_atual)}.", "cargo_inicio"
            if inicio_cargo < data_inicio[:7]:
                return None, f"O cargo não pode ter começado antes da sua entrada ({_mes_legivel(data_inicio[:7])}).", "cargo_inicio"
        if area not in ("suporte", "monitoramento", ""):
            return None, "Área inválida.", "cargo"
        campos["historico"] = {"cargo": cargo, "area": area, "inicio": inicio_cargo}
    return campos, None, None


def marcar_vistas(login: str, ids: list) -> bool:
    info = USUARIOS_WEB.get(login)
    if info is None:
        return False
    validos = {i["id"] for i in insignias_de(login)}
    vistas = list(info.get("insignias_vistas") or [])
    for i in ids:
        if i in validos and i not in vistas:
            vistas.append(i)
    info["insignias_vistas"] = vistas
    return _salvar_usuarios(USUARIOS_WEB)
