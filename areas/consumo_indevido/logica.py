"""Monitoramento de Consumo Indevido (beta, 3.4.3.0): consulta um banco de tempos em tempos e avisa no Teams.

Pedido do Igor: "card para monitoramento de Consumo indevido que se conecte no banco e envie um workflow para o teams
quando identificado consumo indevido". Como a regra (banco e consulta) ainda não foi passada, tudo é configurável pela
tela, só por administrador:
- banco: uma das String Connections já cadastradas (`conexao_id`; a senha nunca vai pra tela);
- consulta: um SELECT (ou WITH ... SELECT) que devolve uma linha por consumo indevido. Só leitura: `_consulta_segura`
  recusa qualquer outra instrução, e a consulta roda numa transação que sempre volta (rollback) no fim;
- intervalo: de 5 em 5 minutos até 1 vez por dia.
Linha nova (que não tinha aparecido nos últimos `DIAS_LEMBRAR` dias, comparando todas as colunas) vira um cartão no
Teams pelo Workflow cadastrado em Criptografia de Dados Sensíveis (`CHAVE_WEBHOOK`). Sem o Workflow, só registra no log
e na tela (e avisa de novo quando ele for cadastrado). **Começa desligado.**

Dados em consumo_indevido/ ao lado do programa (fora do git): config.json, estado.json (vistos, último resultado).
"""
import hashlib
import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta
from typing import Optional

import requests

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco
from nucleo.caminhos import base_path_app as _base_path_app

logger = logging.getLogger("alertas.consumo_indevido")

CHAVE_WEBHOOK = "teams::consumo_indevido_webhook"
INTERVALO_MIN, INTERVALO_MAX = 5, 1440
LIMITE_LINHAS = 500          # lidas por execução
LINHAS_NO_CARTAO = 10        # mostradas no Teams (o resto fica "e mais N")
COLUNAS_NO_CARTAO = 6
DIAS_LEMBRAR = 7
MAX_CONSULTA = 8000
PALAVRAS_PROIBIDAS = ("insert", "update", "delete", "merge", "drop", "alter", "create", "truncate", "exec", "execute",
                      "grant", "revoke", "deny", "into", "backup", "restore", "shutdown", "dbcc", "openrowset", "opendatasource",
                      "bulk", "sp_", "xp_", "waitfor", "use")
CONFIG_PADRAO = {"conexao_id": "", "consulta": "", "intervalo_min": 15, "titulo": "Consumo indevido identificado"}

_lock = threading.Lock()
_acordar = threading.Event()
estado_execucao = {"executando": False}


# ------------------------------------------------------------------------------------------------ arquivos
def _pasta() -> str:
    pasta = os.path.join(_base_path_app(), "consumo_indevido")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _ler(nome: str, padrao):
    try:
        with open(os.path.join(_pasta(), nome), "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, type(padrao)) else padrao
    except FileNotFoundError:
        return padrao
    except Exception:
        logger.exception("Não foi possível ler consumo_indevido/%s; começando do zero.", nome)
        return padrao


def _gravar(nome: str, dados) -> bool:
    caminho = os.path.join(_pasta(), nome)
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, default=str)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não foi possível gravar consumo_indevido/%s.", nome)
        return False


def config() -> dict:
    return {**CONFIG_PADRAO, **_ler("config.json", {})}


def _estado() -> dict:
    est = _ler("estado.json", {})
    est.setdefault("vistos", {})
    return est


# ------------------------------------------------------------------------------------------------ banco
def _conexoes() -> dict:
    try:
        from areas.string_connections.logica import STRING_CONNECTIONS
        return STRING_CONNECTIONS
    except Exception:
        return {}


def conexoes_para_tela() -> list:
    """Só cliente e produto (nunca a string com a senha)."""
    return sorted(({"id": i, "nome": f"{c.get('cliente') or '?'} · {c.get('produto') or '?'}"} for i, c in _conexoes().items()),
                  key=lambda c: c["nome"].lower())


def _ler_string(texto: str) -> dict:
    partes = {}
    for pedaco in str(texto or "").split(";"):
        if "=" in pedaco:
            nome, valor = pedaco.split("=", 1)
            partes[" ".join(nome.split()).casefold()] = valor.strip()
    pega = lambda *nomes: next((partes[n] for n in nomes if partes.get(n)), "")
    return {"server": pega("server", "data source", "address", "addr", "network address"),
            "database": pega("database", "initial catalog"), "user": pega("user id", "uid", "user", "username"),
            "password": pega("password", "pwd")}


def _consulta_segura(sql: str) -> Optional[str]:
    """Erro (texto) se a consulta não for só leitura; None se estiver ok. Tira comentários antes de olhar."""
    sql = str(sql or "").strip()
    if not sql:
        return "escreva a consulta"
    if len(sql) > MAX_CONSULTA:
        return f"consulta muito longa (até {MAX_CONSULTA} caracteres)"
    limpo = re.sub(r"--[^\n]*", " ", re.sub(r"/\*.*?\*/", " ", sql, flags=re.S))
    sem_textos = re.sub(r"'(?:[^']|'')*'", "''", limpo)  # o que está entre aspas não conta como instrução
    if not re.match(r"^\s*(select|with)\b", sem_textos, re.I):
        return "a consulta tem que começar com SELECT (ou WITH ... SELECT)"
    if ";" in sem_textos.strip().rstrip(";"):
        return "uma consulta só, sem ponto e vírgula no meio"
    for palavra in PALAVRAS_PROIBIDAS:
        padrao = r"\b" + re.escape(palavra) + (r"\w*" if palavra.endswith("_") else r"\b")
        if re.search(padrao, sem_textos, re.I):
            return f"a consulta só pode ler dados (tem \"{palavra.upper()}\")"
    return None


def rodar_consulta(cfg: Optional[dict] = None) -> dict:
    """{ok, colunas, linhas, erro}. Roda numa transação que sempre volta: nada que a consulta fizer fica gravado."""
    cfg = cfg or config()
    erro = _consulta_segura(cfg.get("consulta"))
    if erro:
        return {"ok": False, "erro": erro}
    info = _conexoes().get(cfg.get("conexao_id") or "")
    if not info:
        return {"ok": False, "erro": "escolha o banco (uma String Connection cadastrada)"}
    dados = _ler_string(info.get("conexao"))
    if not all(dados.values()):
        return {"ok": False, "erro": "a String Connection escolhida está incompleta (servidor, banco, usuário e senha)"}
    conn = None
    try:
        conn = conectar_banco(dados["server"], dados["database"], dados["user"], dados["password"], autocommit=False, raise_on_error=True)
        cursor = conn.cursor()
        cursor.execute(cfg["consulta"].strip().rstrip(";"))
        if cursor.description is None:
            return {"ok": False, "erro": "a consulta não devolveu colunas"}
        colunas = [d[0] or f"coluna {i + 1}" for i, d in enumerate(cursor.description)]
        linhas = [[_texto(v) for v in linha] for linha in cursor.fetchmany(LIMITE_LINHAS)]
        return {"ok": True, "colunas": colunas, "linhas": linhas}
    except Exception as e:
        logger.warning("Consumo indevido: a consulta falhou (%s).", type(e).__name__)
        return {"ok": False, "erro": f"o banco recusou a consulta: {str(e)[:300]}"}
    finally:
        if conn is not None:
            try:
                conn.rollback()
                conn.close()
            except Exception:
                pass


def _texto(valor) -> str:
    if valor is None:
        return ""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m/%Y %H:%M:%S")
    return str(valor)


def _assinatura(linha: list) -> str:
    return hashlib.sha1("\x1f".join(linha).encode("utf-8")).hexdigest()


# ------------------------------------------------------------------------------------------------ Teams
def _url_pda() -> str:
    try:
        from nucleo.teams_comunidade import _url_pda as url
        return url()
    except Exception:
        return "http://192.0.2.198:8765/"


def montar_cartao(titulo: str, colunas: list, linhas: list, teste: bool = False) -> dict:
    corpo = [{"type": "TextBlock", "text": ("🧪 TESTE · " if teste else "") + "⚠️ " + titulo, "weight": "Bolder", "size": "Medium", "wrap": True,
              "color": "Attention"},
             {"type": "TextBlock", "isSubtle": True, "size": "Small", "spacing": "None", "wrap": True,
              "text": (f"{len(linhas)} ocorrência(s) nova(s)" if not teste else "Mensagem de teste do PDA") + " · "
              + datetime.now().strftime("%d/%m/%Y %H:%M")}]
    for linha in linhas[:LINHAS_NO_CARTAO]:
        corpo.append({"type": "FactSet", "separator": True, "spacing": "Medium",
                      "facts": [{"title": str(c), "value": (str(v) or "-")[:200]} for c, v in list(zip(colunas, linha))[:COLUNAS_NO_CARTAO]]})
    if len(linhas) > LINHAS_NO_CARTAO:
        corpo.append({"type": "TextBlock", "text": f"e mais {len(linhas) - LINHAS_NO_CARTAO} no PDA", "isSubtle": True, "wrap": True})
    conteudo = {"type": "AdaptiveCard", "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "version": "1.4",
                "msteams": {"width": "Full"}, "body": corpo,
                "actions": [{"type": "Action.OpenUrl", "title": "Abrir no PDA", "url": _url_pda() + "consumo-indevido"}]}
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": conteudo}]}


def _enviar_teams(cartao: dict) -> dict:
    webhook = _obter_valor_config(CHAVE_WEBHOOK, "")
    if not webhook:
        return {"ok": False, "erro": f"o Workflow do Teams não está cadastrado (chave {CHAVE_WEBHOOK} em Criptografia de Dados Sensíveis)"}
    try:
        resposta = requests.post(webhook, json=cartao, timeout=20)
        resposta.raise_for_status()
        return {"ok": True}
    except Exception as e:
        status = getattr(getattr(e, "response", None), "status_code", None)  # nunca a URL (tem a assinatura do Workflow)
        return {"ok": False, "erro": "o Teams não aceitou o envio (" + type(e).__name__ + (f", HTTP {status}" if status else "") + ")"}


# ------------------------------------------------------------------------------------------------ ciclo
def executar(origem: str = "agendado") -> dict:
    """Roda a consulta e avisa no Teams as linhas novas. Nunca levanta exceção."""
    with _lock:
        if estado_execucao["executando"]:
            return {"ok": False, "erro": "já tem uma verificação rodando"}
        estado_execucao["executando"] = True
    agora = datetime.now()
    try:
        cfg = config()
        est = _estado()
        res = rodar_consulta(cfg)
        resumo = {"quando": agora.strftime("%d/%m/%Y %H:%M:%S"), "origem": origem, "ok": res["ok"], "erro": res.get("erro", ""),
                  "total": len(res.get("linhas") or []), "novas": 0, "teams": ""}
        if res["ok"]:
            corte = (agora - timedelta(days=DIAS_LEMBRAR)).isoformat()
            est["vistos"] = {k: v for k, v in est["vistos"].items() if v >= corte}
            novas = [l for l in res["linhas"] if _assinatura(l) not in est["vistos"]]
            resumo["novas"] = len(novas)
            est["ultimas"] = {"colunas": res["colunas"], "linhas": res["linhas"][:100]}
            if novas:
                envio = _enviar_teams(montar_cartao(cfg.get("titulo") or CONFIG_PADRAO["titulo"], res["colunas"], novas))
                resumo["teams"] = "enviado" if envio["ok"] else envio["erro"]
                if envio["ok"]:  # sem Workflow (ou Teams fora), não marca: avisa de novo na próxima
                    for l in novas:
                        est["vistos"][_assinatura(l)] = agora.isoformat()
                logger.info("Consumo indevido (%s): %d linha(s), %d nova(s); Teams: %s.", origem, len(res["linhas"]), len(novas), resumo["teams"])
        else:
            logger.warning("Consumo indevido (%s): %s", origem, res.get("erro"))
        est["ultimo"] = resumo
        _gravar("estado.json", est)
        return {"ok": True, **resumo}
    except Exception as e:
        logger.exception("Erro no monitoramento de consumo indevido")
        return {"ok": False, "erro": str(e)}
    finally:
        with _lock:
            estado_execucao["executando"] = False


def esta_ligado() -> bool:
    return bool(_estado().get("ligado"))


def definir_ligado(ligado: bool, usuario: str) -> dict:
    if ligado:
        cfg = config()
        erro = _consulta_segura(cfg.get("consulta")) or ("" if cfg.get("conexao_id") in _conexoes() else "escolha o banco antes de ligar")
        if erro:
            return {"ok": False, "erro": erro}
    est = _estado()
    est.update(ligado=bool(ligado), alterado_por=usuario, alterado_em=datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    if not _gravar("estado.json", est):
        return {"ok": False, "erro": "não foi possível salvar (detalhes no log)"}
    logger.info("Consumo indevido %s por %s.", "ligado" if ligado else "pausado", usuario)
    _acordar.set()
    return {"ok": True}


def salvar_config(dados: dict, usuario: str) -> dict:
    consulta = str(dados.get("consulta") or "").strip()
    erro = _consulta_segura(consulta)
    if erro:
        return {"ok": False, "erro": erro}
    conexao_id = str(dados.get("conexao_id") or "")
    if conexao_id not in _conexoes():
        return {"ok": False, "erro": "escolha o banco (uma String Connection cadastrada)"}
    try:
        intervalo = int(dados.get("intervalo_min") or 15)
    except (TypeError, ValueError):
        return {"ok": False, "erro": "intervalo inválido"}
    if not INTERVALO_MIN <= intervalo <= INTERVALO_MAX:
        return {"ok": False, "erro": f"intervalo de {INTERVALO_MIN} a {INTERVALO_MAX} minutos"}
    titulo = " ".join(str(dados.get("titulo") or CONFIG_PADRAO["titulo"]).split())[:120] or CONFIG_PADRAO["titulo"]
    novo = {"conexao_id": conexao_id, "consulta": consulta, "intervalo_min": intervalo, "titulo": titulo,
            "alterado_por": usuario, "alterado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
    if not _gravar("config.json", novo):
        return {"ok": False, "erro": "não foi possível salvar (detalhes no log)"}
    logger.info("Consumo indevido: configuração alterada por %s (intervalo %d min).", usuario, intervalo)
    _acordar.set()
    return {"ok": True}


def testar_consulta(dados: dict) -> dict:
    """Roda a consulta da tela (sem salvar e sem mandar nada pro Teams) e devolve até 50 linhas."""
    cfg = {**config(), "consulta": dados.get("consulta") or "", "conexao_id": dados.get("conexao_id") or ""}
    res = rodar_consulta(cfg)
    if res["ok"]:
        res["total"] = len(res["linhas"])
        res["linhas"] = res["linhas"][:50]
    return res


def teste_teams(usuario: str) -> dict:
    cartao = montar_cartao(config().get("titulo") or CONFIG_PADRAO["titulo"], ["Exemplo", "Quem pediu"], [["Mensagem de teste", usuario]], teste=True)
    res = _enviar_teams(cartao)
    logger.info("Consumo indevido: teste do Teams por %s: %s.", usuario, "ok" if res["ok"] else res["erro"])
    return res


def status() -> dict:
    cfg, est = config(), _estado()
    return {"ok": True, "ligado": bool(est.get("ligado")), "alterado_por": est.get("alterado_por"), "alterado_em": est.get("alterado_em"),
            "executando": estado_execucao["executando"], "config": {k: cfg.get(k) for k in ("conexao_id", "consulta", "intervalo_min", "titulo")},
            "conexoes": conexoes_para_tela(), "ultimo": est.get("ultimo"), "ultimas": est.get("ultimas"),
            "webhook_cadastrado": bool(_obter_valor_config(CHAVE_WEBHOOK, "")), "lembrados": len(est.get("vistos") or {})}


class MonitorConsumoIndevido:
    """Uma verificação a cada `intervalo_min` enquanto estiver ligado (começa desligado)."""

    def __init__(self):
        self._stop = threading.Event()

    def iniciar(self) -> None:
        threading.Thread(target=self._loop, daemon=True, name="consumo_indevido").start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            if esta_ligado():
                executar("agendado")
                espera = max(INTERVALO_MIN, min(INTERVALO_MAX, int(config().get("intervalo_min") or 15))) * 60
            else:
                espera = 30
            _acordar.wait(espera)
            _acordar.clear()
