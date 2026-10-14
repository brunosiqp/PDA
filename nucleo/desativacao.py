"""Aviso de usuário desativado no PDA (3.1.5.0, pedido do Igor).

Quando alguém tem o login desativado (Usuários · Status, ou "Desativar por login" na Manutenção de
Usuários), os administradores ficam sabendo: a data vai pro usuarios.json (`desativado_em`, `desativado_por`), o
mural do início mostra um aviso em vermelho e cada administrador ativo recebe a notificação no sininho. Desde a
3.3.8.1 (pedido do Igor) isso é só pra administrador: antes ia pra todo mundo.
Desativar geralmente quer dizer que a pessoa não faz mais parte da Empresa ou da equipe de sustentação.
Reativar apaga a data e as notificações (o aviso some do mural).

Quem chama grava o usuarios.json (`_salvar_usuarios`) depois de `marcar_status` e só então chama
`avisar_mudanca`, pra não avisar uma desativação que não foi gravada.
"""
import logging
from datetime import datetime

from nucleo.notificacoes import apagar_por_chave, notificar
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")

TEXTO_DESATIVADO = ("Isso geralmente indica que a pessoa não faz mais parte da Empresa "
                    "ou da equipe de sustentação.")


def _id_evento(login: str, quando: str) -> str:
    return f"saida:{login}:{quando[:10]}"


def marcar_status(login: str, ativo: bool, por: str) -> bool:
    """Muda o `ativo` e registra quando foi desativado. Devolve se mudou mesmo (desativar quem já está
    desativado não gera aviso novo)."""
    info = USUARIOS_WEB.get(login)
    if info is None:
        return False
    estava_ativo = info.get("ativo", True)
    info["ativo"] = ativo
    if estava_ativo and not ativo:
        info["desativado_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info["desativado_por"] = por
        return True
    if not estava_ativo and ativo:
        info.pop("desativado_em", None)
        info.pop("desativado_por", None)
        return True
    return False


def avisar_mudanca(login: str) -> None:
    """Depois de gravado: desativado avisa os administradores no sininho; reativado apaga esses avisos."""
    info = USUARIOS_WEB.get(login) or {}
    nome = info.get("nome") or login
    try:
        if not info.get("ativo", True) and info.get("desativado_em"):
            id_ev = _id_evento(login, info["desativado_em"])
            for outro, dados in USUARIOS_WEB.items():
                if outro == login or not dados.get("ativo", True) or outro.lower().startswith("teste") or not dados.get("admin"):
                    continue
                notificar(outro, "saida", "", f"{nome} foi desativado(a) no PDA. {TEXTO_DESATIVADO}", id_ev,
                          "/?evento=" + id_ev, f"saida:{login}")
        elif info.get("ativo", True):
            for outro in list(USUARIOS_WEB):
                apagar_por_chave(outro, f"saida:{login}")
    except Exception:
        logger.exception("Não foi possível avisar a mudança de status de '%s'.", login)


def tirar_avisos_de_quem_nao_e_admin() -> int:
    """3.3.8.1: até aqui o aviso de desativado ia pro sininho de todo mundo; tira os que ficaram com quem não é admin.
    Roda uma vez na partida; não acha nada a partir da segunda vez."""
    tirados = 0
    try:
        desativados = [l for l, d in USUARIOS_WEB.items() if not d.get("ativo", True)]
        for outro, dados in USUARIOS_WEB.items():
            if dados.get("admin"):
                continue
            for login in desativados:
                if apagar_por_chave(outro, f"saida:{login}"):
                    tirados += 1
    except Exception:
        logger.exception("Não foi possível tirar os avisos de desativado de quem não é administrador.")
    if tirados:
        logger.info("Avisos de usuário desativado tirados do sininho de quem não é administrador: %d.", tirados)
    return tirados


tirar_avisos_de_quem_nao_e_admin()  # na partida (3.3.8.1)
