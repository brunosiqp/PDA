"""Acessos ao PDA e marcos do painel (3.0.3.0).

- DATA_CRIACAO_PDA: o dia em que o PDA nasceu (05/08/2026). Aparece no changelog e no Sobre,
  e a cada aniversário o PDA avisa todo mundo (mural e sininho).
- Contagem de acessos: cada login bem-sucedido soma 1 (a mesma pessoa logando 100 vezes conta
  100). Na primeira vez que roda, a contagem começa pelos logins que já estão nos logs
  (administracao.log e as cópias .1, .2, .3 da rotação, linha "Login web bem-sucedido"); daí
  em diante cada login soma na hora. Fica em acessos_pda.json (fora do git):
  {"total", "por_usuario": {login: n}, "primeiro_registro", "contado_dos_logs", "contando_desde"}.
  Os logs giram (2 MB x 3 cópias), então o que já tinha saído deles antes da primeira contagem
  não entra: o número inicial é "pelo menos".
- Marcos (3.4.5.0): a cada MARCO_ACESSOS (1.000) acessos o PDA comemora: grava em "marcos" ({"1000": "AAAA-MM-DD HH:MM:SS"}),
  o mural mostra o post "O PDA chegou a 1.000 acessos!" e todo mundo ativo recebe o aviso no sininho. Se o PDA já passou
  de um marco sem ter registrado (primeira partida com esta versão), comemora só o maior, uma vez.
"""
import json
import logging
import os
import re
import threading
from datetime import date, datetime

from nucleo.caminhos import base_path_app as _base_path_app

logger = logging.getLogger("alertas")

DATA_CRIACAO_PDA = date(2026, 8, 5)
MARCO_ACESSOS = 1000
_RE_LOGIN_LOG = re.compile(r"^(\d{4}-\d{2}-\d{2}) [\d:]+ \| \w+\s*\| Login web bem-sucedido: usuário '([^']+)'")
_lock_acessos = threading.Lock()
ACESSOS: dict = {}


def _caminho() -> str:
    return os.path.join(_base_path_app(), "acessos_pda.json")


def _gravar() -> None:
    caminho = _caminho()
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(ACESSOS, f, indent=1, ensure_ascii=False)
        os.replace(caminho + ".tmp", caminho)
    except Exception:
        logger.exception("Não foi possível gravar acessos_pda.json.")


def contar_logins_nos_logs(pasta_logs: str) -> dict:
    """Logins bem-sucedidos que ainda estão nos logs de administração (todas as cópias da rotação)."""
    total, por_usuario, primeiro = 0, {}, None
    for nome in ("administracao.log", "administracao.log.1", "administracao.log.2", "administracao.log.3"):
        try:
            with open(os.path.join(pasta_logs, nome), "r", encoding="utf-8", errors="replace") as f:
                for linha in f:
                    m = _RE_LOGIN_LOG.match(linha)
                    if m:
                        total += 1
                        por_usuario[m.group(2)] = por_usuario.get(m.group(2), 0) + 1
                        primeiro = min(primeiro or m.group(1), m.group(1))
        except FileNotFoundError:
            continue
        except Exception:
            logger.exception("Não foi possível ler %s pra contar os acessos.", nome)
    return {"total": total, "por_usuario": por_usuario, "primeiro": primeiro}


def iniciar_contagem(pasta_logs: str) -> None:
    """Carrega a contagem; na primeira vez, começa pelos logins que estão nos logs."""
    global ACESSOS
    with _lock_acessos:
        try:
            with open(_caminho(), "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, dict) and isinstance(dados.get("total"), int):
                ACESSOS = dados
                return
        except FileNotFoundError:
            pass
        except Exception:
            logger.exception("acessos_pda.json ilegível: recontando pelos logs.")
        dos_logs = contar_logins_nos_logs(pasta_logs)
        ACESSOS = {"total": dos_logs["total"], "por_usuario": dos_logs["por_usuario"], "primeiro_registro": dos_logs["primeiro"],
                   "contado_dos_logs": dos_logs["total"], "contando_desde": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        _gravar()
        logger.info("Contagem de acessos iniciada com %d login(s) encontrados nos logs.", dos_logs["total"])
    conferir_marcos()


def registrar_login(login: str) -> None:
    with _lock_acessos:
        if not ACESSOS:  # iniciar_contagem não rodou (não deveria acontecer): começa do zero sem perder o login
            ACESSOS.update({"total": 0, "por_usuario": {}, "primeiro_registro": date.today().isoformat(),
                            "contado_dos_logs": 0, "contando_desde": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        ACESSOS["total"] = int(ACESSOS.get("total") or 0) + 1
        por_usuario = ACESSOS.setdefault("por_usuario", {})
        por_usuario[login] = por_usuario.get(login, 0) + 1
        _gravar()
    conferir_marcos()


def marcos_de_acessos() -> dict:
    """{1000: "AAAA-MM-DD HH:MM:SS", 2000: ...} dos marcos já comemorados."""
    with _lock_acessos:
        return {int(n): quando for n, quando in (ACESSOS.get("marcos") or {}).items() if str(n).isdigit()}


def conferir_marcos() -> None:
    """Chegou num múltiplo de 1.000 que ainda não foi comemorado: grava e avisa todo mundo no sininho (uma vez só)."""
    with _lock_acessos:
        total = int(ACESSOS.get("total") or 0)
        marco = (total // MARCO_ACESSOS) * MARCO_ACESSOS
        marcos = ACESSOS.setdefault("marcos", {})
        if marco < MARCO_ACESSOS or str(marco) in marcos:
            return
        marcos[str(marco)] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        _gravar()
    logger.info("O PDA chegou a %d acessos: post de comemoração no mural e aviso no sininho.", marco)
    try:
        from nucleo.notificacoes import notificar
        from nucleo.usuarios import USUARIOS_WEB
        numero = f"{marco:,}".replace(",", ".")
        for login, info in list(USUARIOS_WEB.items()):
            if info.get("ativo", True) and not login.lower().startswith("teste"):
                notificar(login, "marco", "pda", f"🎉 O PDA chegou a {numero} acessos! Obrigado por fazer parte",
                          f"pda:acessos:{marco}", f"/?evento=pda:acessos:{marco}", f"marco:{marco}")
    except Exception:
        logger.exception("Não foi possível avisar o marco de %d acessos no sininho.", marco)


def resumo_acessos() -> dict:
    with _lock_acessos:
        return {"total": int(ACESSOS.get("total") or 0), "pessoas": len(ACESSOS.get("por_usuario") or {}),
                "primeiro_registro": ACESSOS.get("primeiro_registro")}


def anos_do_pda(hoje: date = None) -> int:
    hoje = hoje or date.today()
    return max(hoje.year - DATA_CRIACAO_PDA.year - ((hoje.month, hoje.day) < (DATA_CRIACAO_PDA.month, DATA_CRIACAO_PDA.day)), 0)


def aniversario_do_pda(anos: int) -> date:
    return DATA_CRIACAO_PDA.replace(year=DATA_CRIACAO_PDA.year + anos)


def dias_do_pda(hoje: date = None) -> int:
    return ((hoje or date.today()) - DATA_CRIACAO_PDA).days
