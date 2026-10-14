"""Feedbacks e Alinhamentos - lógica (registros de feedback/alinhamento (feedbacks_usuarios.json) e anexos).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import base64
import json
import logging
import os
import re
import threading

from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


_PASTA_ANEXOS_FEEDBACKS_NOME = "anexos_feedbacks"
_TAMANHO_MAXIMO_ANEXO_FEEDBACK_BYTES = 10 * 1024 * 1024  # 10MB decodificado


def _pasta_anexos_feedbacks() -> str:
    caminho = os.path.join(_base_path_app(), _PASTA_ANEXOS_FEEDBACKS_NOME)
    os.makedirs(caminho, exist_ok=True)
    return caminho


def _salvar_anexo_feedback(id_feedback: int, nome_arquivo: str, data_url: str):
    """Recebe uma data URL genérica (qualquer tipo de arquivo, não só
    imagem), valida tamanho, e salva em disco associado ao id do
    feedback/alinhamento. Devolve (nome_salvo, None) se deu certo, ou
    (None, mensagem_de_erro) se falhou - mesmo padrão de
    _salvar_foto_usuario, só que devolvendo o nome salvo também (porque
    aqui, diferente da foto, o nome do arquivo original importa pra
    exibir/baixar depois)."""
    m = re.match(r"^data:([\w.+/-]*);base64,(.+)$", data_url, re.DOTALL)
    if not m:
        return None, "formato de arquivo inválido"
    base64_dados = m.group(2)
    try:
        bytes_arquivo = base64.b64decode(base64_dados, validate=True)
    except Exception:
        return None, "não foi possível decodificar o arquivo"
    if len(bytes_arquivo) == 0:
        return None, "arquivo vazio"
    if len(bytes_arquivo) > _TAMANHO_MAXIMO_ANEXO_FEEDBACK_BYTES:
        return None, f"arquivo muito grande (máximo {_TAMANHO_MAXIMO_ANEXO_FEEDBACK_BYTES // (1024*1024)}MB)"

    nome_seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", (nome_arquivo or "anexo").strip()) or "anexo"
    nome_salvo = f"{id_feedback}_{nome_seguro}"
    caminho = os.path.join(_pasta_anexos_feedbacks(), nome_salvo)
    try:
        with open(caminho, "wb") as f:
            f.write(bytes_arquivo)
    except Exception as e:
        logger.exception("Falha ao salvar anexo do feedback/alinhamento %s", id_feedback)
        return None, f"falha ao salvar: {e}"
    return nome_salvo, None


def _caminho_feedbacks_usuarios_json() -> str:
    return os.path.join(_base_path_app(), "feedbacks_usuarios.json")


def _carregar_feedbacks_usuarios() -> list:
    caminho = _caminho_feedbacks_usuarios_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
        except Exception:
            logger.exception("Não foi possível ler feedbacks_usuarios.json, começando vazio.")
    return []


def _salvar_feedbacks_usuarios(dados: list) -> None:
    caminho = _caminho_feedbacks_usuarios_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar feedbacks_usuarios.json.")


# Feedback interno sobre a pessoa - DIFERENTE de tudo mais no perfil: o
# PRÓPRIO USUÁRIO NUNCA VÊ isso, nem sendo admin vendo o próprio perfil.
# Só é visível/editável por admins da MESMA equipe (mesma "atribuicao":
# Suporte ou Monitoramento) da pessoa que está sendo vista - pedido
# explícito do Igor (feedback de gestão, não é algo do funcionário ver).
FEEDBACKS_USUARIOS: list = _carregar_feedbacks_usuarios()


_lock_feedbacks_usuarios = threading.Lock()


def _nomes_em_lista_pt(nomes: list) -> str:
    """Junta uma lista de nomes no estilo "A, B e C" (português) - usado
    pra descrever o grupo de um Alinhamento em grupo."""
    nomes = [n for n in nomes if n]
    if not nomes:
        return ""
    if len(nomes) == 1:
        return nomes[0]
    return ", ".join(nomes[:-1]) + " e " + nomes[-1]


def _descricao_alvo_feedback(registro: dict) -> str:
    """Descrição pronta pra exibir/mandar por e-mail de quem um
    feedback/alinhamento é sobre - funciona pros 3 escopos sem quem
    chama precisar saber qual é."""
    escopo = registro.get("escopo") or "individual"
    if escopo == "geral":
        return "toda a equipe (Alinhamento Geral)"
    if escopo == "grupo":
        nomes = [USUARIOS_WEB.get(u, {}).get("nome") or u for u in (registro.get("usuarios") or [])]
        return _nomes_em_lista_pt(nomes) or "grupo (sem pessoas)"
    usuario = registro.get("usuario")
    return USUARIOS_WEB.get(usuario, {}).get("nome") or usuario or "-"


# ---------------------------------------------------------------------------
# Equipe que recebe o aviso por e-mail (2.34.7.0): cada registro escolhe uma, e
# o e-mail de "novo feedback/alinhamento" vai só pras pessoas dela (antes ia
# sempre pra mesma lista, a do Monitoramento). (nome, e-mail, login no PDA) - o nome
# aparece na tela pra mostrar quem vai ser avisado; o e-mail fica só aqui.
# Desde a 2.35.2.0 a mesma lista diz QUEM VÊ os registros da equipe (ver
# pode_ver_registro_feedback). O login vai escrito porque o e-mail do
# usuarios.json não serve pra achar a pessoa (tem gente sem e-mail e gente com o
# e-mail de outra); o e-mail ainda vale como reserva. Ao renomear um login no
# PDA, trocar aqui também.
# ---------------------------------------------------------------------------
EQUIPES_FEEDBACK = {
    "Monitoramento": [
        ("Debora Sampaio", "debora@example.com", "debora"),
        ("Igor Leal", "igor.leal@example.com", "igor"),
        ("Everton Nogueira", "everton.nogueira@example.com", "nogueira"),
        ("Eduardo Yamada", "contato74@example.com", "eduardo"),
    ],
    "Suporte Indústria": [
        ("Sergio Henriques", "sergio.henriques@example.com", "sergio.henriques"),
        ("Ivan Campos", "ivan.campos@example.com", "ivan.campos"),
        ("Caio Peixoto", "caio.peixoto@example.com", "caio.peixoto"),
    ],
    "Suporte NFSe": [
        ("Sergio Henriques", "sergio.henriques@example.com", "sergio.henriques"),
        ("Ivan Campos", "ivan.campos@example.com", "ivan.campos"),
        ("Paula Freitas", "paula.matos@example.com", "paula"),
        ("Renan Klein", "renan.guerra@example.com", "renan"),
    ],
    "Serviços": [
        ("Eduardo Yamada", "contato74@example.com", "eduardo"),
        ("Sergio Henriques", "sergio.henriques@example.com", "sergio.henriques"),
    ],
}
# registro antigo (sem equipe) e o padrão do formulário: a lista que já era usada
EQUIPE_FEEDBACK_PADRAO = "Monitoramento"

# Quem costuma RECEBER os registros de cada equipe (logins), quando a equipe não é
# uma das atribuições do PDA (2.35.0.1). A tela usa pra marcar o grupo de uma vez
# ("+ Serviços") e pra já sugerir a equipe do aviso quando a pessoa escolhida é dela.
MEMBROS_EQUIPE_FEEDBACK = {
    "Serviços": ["edson.gomes", "rocha"],
}

# nome antigo -> nome novo (2.35.0.1: "Indústria Suporte" virou "Suporte Indústria");
# registros gravados com o nome antigo continuam caindo na equipe certa
EQUIPES_FEEDBACK_RENOMEADAS = {"Indústria Suporte": "Suporte Indústria"}


def nome_atual_equipe(equipe):
    return EQUIPES_FEEDBACK_RENOMEADAS.get(equipe, equipe)


def equipe_do_registro(registro: dict) -> str:
    equipe = nome_atual_equipe(registro.get("equipe"))
    return equipe if equipe in EQUIPES_FEEDBACK else EQUIPE_FEEDBACK_PADRAO


def destinatarios_equipe_feedback(equipe: str) -> list:
    return [email for _, email, _ in EQUIPES_FEEDBACK.get(nome_atual_equipe(equipe)) or EQUIPES_FEEDBACK[EQUIPE_FEEDBACK_PADRAO]]


def logins_da_equipe_feedback(equipe: str) -> set:
    """Logins de quem recebe os e-mails da equipe (e por isso vê os registros
    dela): o login escrito em EQUIPES_FEEDBACK e, de reserva, quem tem no PDA o
    mesmo e-mail de algum destinatário."""
    pessoas = EQUIPES_FEEDBACK.get(nome_atual_equipe(equipe)) or []
    logins = {login for _, _, login in pessoas if login in USUARIOS_WEB}
    emails = {email.lower() for _, email, _ in pessoas}
    logins |= {u for u, info in USUARIOS_WEB.items() if (info.get("email") or "").strip().lower() in emails}
    return logins


# Quem vê os registros de TODAS as equipes, mesmo sem receber os e-mails delas (2.35.5.1):
# a gerência. Login e, de reserva, o nome (sem acento e sem diferenciar maiúscula).
VEEM_TODAS_EQUIPES_FEEDBACK = {"logins": {"toledo"}, "nomes": {"sabrina barros"}}


def _normalizar_nome(texto: str) -> str:
    import unicodedata
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return " ".join(texto.lower().split())


def ve_todas_equipes_feedback(usuario: str) -> bool:
    nome = (USUARIOS_WEB.get(usuario) or {}).get("nome") or ""
    return usuario in VEEM_TODAS_EQUIPES_FEEDBACK["logins"] or _normalizar_nome(nome) in VEEM_TODAS_EQUIPES_FEEDBACK["nomes"]


def equipes_visiveis_feedback(usuario: str) -> list:
    """Equipes cujos registros essa pessoa vê (as que ela recebe por e-mail; a gerência vê todas)."""
    if ve_todas_equipes_feedback(usuario):
        return list(EQUIPES_FEEDBACK)
    return [nome for nome in EQUIPES_FEEDBACK if usuario in logins_da_equipe_feedback(nome)]


def pode_ver_registro_feedback(registro: dict, usuario: str) -> bool:
    """Separação por equipe (2.35.2.0): o registro de uma equipe só aparece pra
    quem recebe os e-mails dela; quem registrou e os autores também continuam
    vendo o que fizeram. Vale pra lista, perfil, anexo, edição e exclusão. A
    permissão pode_feedbacks continua sendo exigida antes disso."""
    if usuario == registro.get("autor") or usuario in autores_do_registro(registro):
        return True
    if ve_todas_equipes_feedback(usuario):  # gerência: vê os de todas as equipes
        return True
    return usuario in logins_da_equipe_feedback(equipe_do_registro(registro))


def equipes_feedback_para_tela() -> list:
    """Só nomes (sem e-mail) pro formulário mostrar quem vai receber o aviso."""
    return [{"nome": nome, "pessoas": [p for p, _, _ in pessoas], "membros": MEMBROS_EQUIPE_FEEDBACK.get(nome, [])}
            for nome, pessoas in EQUIPES_FEEDBACK.items()]


def autores_do_registro(registro: dict) -> list:
    """Logins de quem fez o feedback/alinhamento (2.34.7.0: podem ser vários).
    Registro antigo só tem "autor" (quem registrou), que vira o único autor."""
    autores = [a for a in (registro.get("autores") or []) if a]
    return autores or ([registro["autor"]] if registro.get("autor") else [])


def nomes_autores(autores: list) -> str:
    return _nomes_em_lista_pt([USUARIOS_WEB.get(a, {}).get("nome") or a for a in autores])


def validar_alvos_e_autores(dados: dict, quem_registra: str):
    """Valida escopo, quem recebe, autores e equipe vindos do formulário (mesma
    regra pra criar e editar). Devolve (campos, None) ou (None, erro).
    Regras: alvo e autores precisam existir no PDA; ninguém recebe um registro
    do qual é autor (nem quem está registrando)."""
    escopo = dados.get("escopo") or "individual"
    if escopo not in ("individual", "grupo", "geral"):
        return None, "escopo inválido"
    usuario_alvo = (dados.get("usuario") or "").strip()
    usuarios_grupo = [u.strip() for u in (dados.get("usuarios") or "").split(",") if u.strip()] if escopo == "grupo" else []
    autores = []
    for a in (dados.get("autores") or "").split(","):
        a = a.strip()
        if a and a not in autores:
            autores.append(a)
    if not autores:
        autores = [quem_registra]
    invalidos = [a for a in autores if a not in USUARIOS_WEB]
    if invalidos:
        return None, f"autor(es) inválido(s): {', '.join(invalidos)}"
    equipe = nome_atual_equipe((dados.get("equipe") or EQUIPE_FEEDBACK_PADRAO).strip())
    if equipe not in EQUIPES_FEEDBACK:
        return None, "equipe inválida"
    proibidos = set(autores) | {quem_registra}
    if escopo == "individual":
        if not usuario_alvo or usuario_alvo not in USUARIOS_WEB:
            return None, "selecione uma pessoa válida"
        if usuario_alvo in proibidos:
            return None, "quem recebe não pode ser um dos autores (nem quem está registrando)"
    elif escopo == "grupo":
        if not usuarios_grupo:
            return None, "selecione ao menos uma pessoa pro grupo"
        invalidos = [u for u in usuarios_grupo if u not in USUARIOS_WEB]
        if invalidos:
            return None, f"pessoa(s) inválida(s) no grupo: {', '.join(invalidos)}"
        if proibidos & set(usuarios_grupo):
            return None, "o grupo não pode incluir os autores (nem quem está registrando)"
    return {
        "escopo": escopo,
        "usuario": usuario_alvo if escopo == "individual" else None,
        "usuarios": usuarios_grupo,
        "autores": autores,
        "autor_nome": nomes_autores(autores),
        "equipe": equipe,
    }, None


def avisar_equipe_no_sininho(registro: dict, descricao_alvo: str) -> int:
    """Novo feedback/alinhamento vira notificação no sininho (3.0.5.0) de quem recebe os
    e-mails da equipe do registro (os mesmos que veem o registro), menos quem fez/registrou.
    O link abre o registro na tela de Feedbacks. Devolve quantos foram avisados."""
    from nucleo.notificacoes import notificar  # aqui dentro: só precisa no envio
    tipo = (registro.get("tipo") or "Feedback").lower()
    equipe = equipe_do_registro(registro)
    quem_fez = set(autores_do_registro(registro)) | {registro.get("autor")}
    autor_nome = registro.get("autor_nome") or nomes_autores(autores_do_registro(registro))
    verbo = "registraram" if len(autores_do_registro(registro)) > 1 else "registrou"
    texto = f"{autor_nome} {verbo} {'um novo alinhamento' if tipo == 'alinhamento' else 'um novo feedback'} para {descricao_alvo} · {equipe}"
    avisados = 0
    for login in sorted(logins_da_equipe_feedback(equipe) - quem_fez):
        notificar(login, "feedback", registro.get("autor") or "", texto, "", f"/feedbacks?registro={registro.get('id')}",
                  f"feedback:{registro.get('id')}:{login}")
        avisados += 1
    return avisados
