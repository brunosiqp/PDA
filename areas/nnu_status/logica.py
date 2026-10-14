"""NNU Enchanced · status 20 → 15 (beta, 3.4.9.0, ajustado na 3.4.9.1): automação da frente 7 do escopo de 13/10/2026
(docs/escopos/melhorias_alertas_2026-10.md). É uma aba dentro do card NNU Enchanced.

Regra passada pelo Igor: na INTERF_NFE_NAO_UTILZ, IND_STATUS_PROC = 15 WHERE IND_STATUS_PROC = 20, **automático**
(diferente da tratativa guiada, que é manual; desde a 3.4.9.3 o administrador também pode rodar uma varredura na hora):
1. A cada 2 horas, em cada base ClienteI, pega os NUMSEQ com IND_STATUS_PROC = 20.
2. ANTES do UPDATE, guarda esses NUMSEQ (o "lote", em nnu_status/lotes/<id>.json).
3. UPDATE de 20 para 15 só desses NUMSEQ (e só se ainda estiverem no 20).
4. Acompanha o lote. O relatório só sai quando TODOS os NUMSEQ do lote estiverem no status 10, no status 20 ou não
   existirem mais na tabela; com qualquer um em 15, 25, 31 (ou outro status), espera.
5. Guarda o histórico da execução e o relatório (Excel em nnu_status/relatorios/<id>.xlsx).
6. Manda por e-mail a relação, com todos os cenários e o status final de cada registro.

Bases (3.4.9.4): ClienteI Standard, ClienteI Enterprise e ClienteI ClienteAE, em NFe e em NFCe (filtro NFe/NFCe na tela). Cada uma pela
String Connection do cliente ClienteI com aquele produto, de preferência a do usuário usuario_leitura; sem ela, a conexão do alerta
(só NFe Standard/Enterprise). Sempre na base principal: servidor 192.0.2.127 vira 192.0.2.78 (`_na_principal`).
Dá pra marcar/desmarcar cada uma ou incluir outra String Connection na configuração. Cada base tem o seu lote; um lote por base de cada vez (se na hora da rodada o lote
daquela base ainda não fechou, ela espera e roda assim que ele fechar). Tabela e colunas têm padrão (INTERF_NFE_NAO_UTILZ,
NUM_SEQ_NFE_NAO_UTILZ, IND_STATUS_PROC) e podem ser corrigidas na tela; nomes conferidos (`_identificador`) e entre colchetes.

**Liga sozinho** (é automático) e começa em **modo simulação** (só guarda o lote e o relatório do que seria alterado, sem
UPDATE e sem e-mail) até um administrador sair da simulação uma vez. O acompanhamento continua mesmo pausado (só lê).

Dados em nnu_status/ ao lado do programa (fora do git): config.json, estado.json, lotes/ e relatorios/ (apagados depois
de `DIAS_GUARDAR_LOTES`).
"""
import json
import logging
import os
import re
import threading
from datetime import datetime, timedelta
from typing import Optional

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_config_hibrido

logger = logging.getLogger("alertas.nnu_status")

STATUS_DE, STATUS_PARA = 20, 15
STATUS_FINAIS = (10, 20)            # + "não existe mais"; qualquer outro (15, 25, 31...) segura o relatório
CHUNK = 500                         # NUMSEQ por comando (limite de parâmetros do SQL Server é 2100)
DIAS_GUARDAR_LOTES = 180
MAX_LOTES_NA_TELA = 60
TENTAR_DE_NOVO_MIN = 10       # rodada em que alguma base falhou: a próxima é daqui a 10 min
FMT = "%Y-%m-%d %H:%M:%S"
# bases do ClienteI (3.4.9.4, pedido do Igor: Standard, Enterprise e ClienteAE, em NFe e NFCe): id -> (nome, produto, seção do
# alerta ou None, .env legado, palavra do cliente na String Connection). Primeiro a String Connection do cliente ClienteI com a
# palavra e o produto, de preferência a do usuário usuario_leitura (`USUARIO_PREFERIDO`); sem ela, a conexão do alerta (só NFe:
# Standard e Enterprise têm). O id "cliente_i_standart" (com t) é interno: é o nome do .env e da senha no config.dat do alerta.
FONTES_ALERTA = {
    "cliente_i_standart": ("ClienteI Standard", "NFe", "alerta__cliente_i_standart", ".env.ClienteIStandart", "standar"),
    "cliente_i_enterprise": ("ClienteI Enterprise", "NFe", "alerta__cliente_i_enterprise", ".env.ClienteIEnterprise", "enterprise"),
    "cliente_i_ae": ("ClienteI ClienteAE", "NFe", None, None, "cliente_ae"),
    "cliente_i_standart_nfce": ("ClienteI Standard", "NFCe", None, None, "standar"),
    "cliente_i_enterprise_nfce": ("ClienteI Enterprise", "NFCe", None, None, "enterprise"),
    "cliente_i_ae_nfce": ("ClienteI ClienteAE", "NFCe", None, None, "cliente_ae"),
}
USUARIO_PREFERIDO = "op_assistida"
BASES_PADRAO = [f"alerta:{k}" for k in FONTES_ALERTA]
_BASES_PADRAO_ANTIGOS = ({"alerta:cliente_i_enterprise", "alerta:cliente_i_standart"},                       # 3.4.9.1
                         {"alerta:cliente_i_enterprise", "alerta:cliente_i_standart", "alerta:cliente_i_ae"})   # 3.4.9.2/3.4.9.3
# 3.4.9.4: o UPDATE vai sempre na base principal. Nas nossas bases a secundária é o .70 e a principal o .71 (ex.:
# 192.0.2.127\INSTANCIA_PRD -> 192.0.2.78\INSTANCIA_PRD); a conexão do alerta e algumas String Connections apontam pro .70
SERVIDOR_SECUNDARIO, SERVIDOR_PRINCIPAL = "192.0.2.127", "192.0.2.78"
# 3.4.9.2: na INTERF_NFE_NAO_UTILZ o "NUMSEQ" é a coluna NUM_SEQ_NFE_NAO_UTILZ (o padrão NUMSEQ dava "Invalid column name")
COLUNA_NUMSEQ_PADRAO = "NUM_SEQ_NFE_NAO_UTILZ"
CONFIG_PADRAO = {"bases": BASES_PADRAO, "tabela": "INTERF_NFE_NAO_UTILZ", "coluna_numseq": COLUNA_NUMSEQ_PADRAO, "coluna_status": "IND_STATUS_PROC",
                 "intervalo_horas": 2, "acompanhar_min": 10, "max_por_rodada": 5000, "emails": "", "espera_max_horas": 0}
LIMITES = {"intervalo_horas": (1, 24), "acompanhar_min": (2, 120), "max_por_rodada": (1, 50000), "espera_max_horas": (0, 168)}
_RE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")
_RE_EMAIL = re.compile(r"^[^@\s,;<>\"']+@[^@\s,;<>\"']+\.[^@\s,;<>\"']+$")
_RE_ID_LOTE = re.compile(r"\d{8}-\d{6}(_\d+)?")

_lock = threading.Lock()
_acordar = threading.Event()
estado_execucao = {"executando": "", "ultima_conferencia": None}


# ------------------------------------------------------------------------------------------------ arquivos
def _pasta(*sub: str) -> str:
    pasta = os.path.join(_base_path_app(), "nnu_status", *sub)
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _ler_json(caminho: str, padrao):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return dados if isinstance(dados, type(padrao)) else padrao
    except FileNotFoundError:
        return padrao
    except Exception:
        logger.exception("Não foi possível ler %s.", caminho)
        return padrao


def _gravar_json(caminho: str, dados) -> bool:
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1, default=str)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não foi possível gravar %s.", caminho)
        return False


def config() -> dict:
    cfg = {**CONFIG_PADRAO, **_ler_json(os.path.join(_pasta(), "config.json"), {})}
    if not isinstance(cfg.get("bases"), list) or set(cfg["bases"]) in _BASES_PADRAO_ANTIGOS:
        cfg["bases"] = list(BASES_PADRAO)  # sem config ou com um padrão antigo (sem o ClienteAE ou sem o NFCe)
    # quem marcou a String Connection de uma base ClienteI à mão (ex.: "CLIENTE_I ClienteAE · NFe" na 3.4.9.1) passa a usar a base ClienteI
    # equivalente, que lê a mesma String Connection: não aparece duas vezes nem roda duas vezes no mesmo banco
    for chave, (_, produto, _, _, palavra) in FONTES_ALERTA.items():
        sc = _sc_cliente_i(palavra, produto)
        if sc and f"sc:{sc}" in cfg["bases"]:
            cfg["bases"] = [b for b in cfg["bases"] if b != f"sc:{sc}"]
            if f"alerta:{chave}" not in cfg["bases"]:
                cfg["bases"].append(f"alerta:{chave}")
    if str(cfg.get("coluna_numseq") or "").upper() == "NUMSEQ":  # config salva com o padrão antigo (3.4.9.0/3.4.9.1)
        cfg["coluna_numseq"] = COLUNA_NUMSEQ_PADRAO
    return cfg


def _estado() -> dict:
    est = _ler_json(os.path.join(_pasta(), "estado.json"), {})
    est.setdefault("ligado", True)       # automático: liga sozinho (pausar é a exceção)
    est.setdefault("simulacao", True)    # até um administrador sair da simulação
    est.setdefault("lotes_abertos", {})  # {base: id do lote}
    est.setdefault("aguardando", [])     # bases cuja rodada esperou o lote anterior fechar
    return est


def _gravar_estado(est: dict) -> bool:
    return _gravar_json(os.path.join(_pasta(), "estado.json"), est)


def _caminho_lote(id_lote: str) -> str:
    return os.path.join(_pasta("lotes"), id_lote + ".json")


def ler_lote(id_lote: str) -> Optional[dict]:
    if not _RE_ID_LOTE.fullmatch(id_lote or ""):
        return None
    return _ler_json(_caminho_lote(id_lote), {}) or None


def _gravar_lote(lote: dict) -> bool:
    return _gravar_json(_caminho_lote(lote["id"]), lote)


def caminho_relatorio(id_lote: str) -> Optional[str]:
    if not _RE_ID_LOTE.fullmatch(id_lote or ""):
        return None
    caminho = os.path.join(_pasta("relatorios"), id_lote + ".xlsx")
    return caminho if os.path.isfile(caminho) else None


# ------------------------------------------------------------------------------------------------ bases
def _conexoes() -> dict:
    try:
        from areas.string_connections.logica import STRING_CONNECTIONS
        return STRING_CONNECTIONS
    except Exception:
        return {}


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


def _credenciais(base: str) -> Optional[dict]:
    """{server, database, user, password} da base, ou None se não existir/estiver incompleta."""
    tipo, _, chave = str(base or "").partition(":")
    if tipo == "alerta" and chave in FONTES_ALERTA:
        return _credenciais_cliente_i(chave)
    elif tipo == "sc" and chave in _conexoes():
        dados = _na_principal(_ler_string(_conexoes()[chave].get("conexao")))
    else:
        return None
    return dados if all(dados.values()) else None


def _sc_cliente_i(palavra: str, produto: str) -> Optional[str]:
    """Id da String Connection do cliente ClienteI com a palavra (ex.: cliente_ae) e o produto (NFe ou NFCe), de preferência a do
    usuário usuario_leitura."""
    achadas = []
    for i, c in _conexoes().items():
        cliente = str(c.get("cliente") or "").casefold()
        prod = "".join(str(c.get("produto") or "").split()).casefold()
        if "cliente_i" in cliente and palavra in cliente and prod == produto.casefold():
            usuario = _ler_string(c.get("conexao"))["user"].casefold()
            achadas.append((0 if usuario == USUARIO_PREFERIDO else 1, i))
    return sorted(achadas)[0][1] if achadas else None


def _na_principal(dados: dict) -> dict:
    """Troca o servidor secundário (.70) pelo principal (.71), mantendo a instância (ex.: \\INSTANCIA_PRD)."""
    servidor = dados.get("server") or ""
    if servidor == SERVIDOR_SECUNDARIO or servidor.startswith(SERVIDOR_SECUNDARIO + "\\") or servidor.startswith(SERVIDOR_SECUNDARIO + ","):
        dados = {**dados, "server": SERVIDOR_PRINCIPAL + servidor[len(SERVIDOR_SECUNDARIO):]}
    return dados


def _credenciais_alerta(chave: str) -> Optional[dict]:
    _, _, secao, env, _ = FONTES_ALERTA[chave]
    if not secao:
        return None
    try:
        sec = _obter_config_hibrido(secao, env, ["db_server", "db_name", "db_user", "db_password"])
    except Exception:
        logger.exception("Não foi possível ler a conexão do alerta %s.", chave)
        return None
    dados = {"server": (sec.get("db_server") or "").strip(), "database": (sec.get("db_name") or "").strip(),
             "user": (sec.get("db_user") or "").strip(),
             "password": _obter_valor_config(f"{chave}::db_password", sec.get("db_password") or "")}  # mesma chave do alerta
    return dados if all(dados.values()) else None


def _credenciais_cliente_i(chave: str) -> Optional[dict]:
    _, produto, _, _, palavra = FONTES_ALERTA[chave]
    sc = _sc_cliente_i(palavra, produto)
    if sc:
        dados = _ler_string(_conexoes()[sc].get("conexao"))
        if all(dados.values()):
            return _na_principal(dados)
    dados = _credenciais_alerta(chave)
    return _na_principal(dados) if dados else None


def _origem_cliente_i(chave: str) -> str:
    _, produto, _, _, palavra = FONTES_ALERTA[chave]
    sc = _sc_cliente_i(palavra, produto)
    if sc:
        usuario = _ler_string(_conexoes()[sc].get("conexao"))["user"]
        return f"String Connection {nome_base('sc:' + sc)}" + (f" ({usuario})" if usuario else "")
    if _credenciais_alerta(chave):
        return "conexão do alerta"
    return f"sem conexão: cadastre a String Connection CLIENTE_I {FONTES_ALERTA[chave][0].split(' ', 1)[1]} · {produto} (usuario_leitura)"


def nome_base(base: str) -> str:
    tipo, _, chave = str(base or "").partition(":")
    if tipo == "alerta" and chave in FONTES_ALERTA:
        return f"{FONTES_ALERTA[chave][0]} · {FONTES_ALERTA[chave][1]}"
    if tipo == "sc":
        c = _conexoes().get(chave) or {}
        return f"{c.get('cliente') or '?'} · {c.get('produto') or '?'}"
    return base


def produto_base(base: str) -> str:
    tipo, _, chave = str(base or "").partition(":")
    if tipo == "alerta" and chave in FONTES_ALERTA:
        return FONTES_ALERTA[chave][1]
    if tipo == "sc":
        return str((_conexoes().get(chave) or {}).get("produto") or "")
    return ""


def bases_para_tela(selecionadas: list) -> list:
    """Bases que dá pra marcar (nunca a string nem a senha): as dos alertas do ClienteI primeiro, depois as String Connections."""
    saida = [{"id": f"alerta:{k}", "nome": f"{v[0]} · {v[1]}", "produto": v[1], "origem": _origem_cliente_i(k),
              "ok": _credenciais(f"alerta:{k}") is not None} for k, v in FONTES_ALERTA.items()]
    saida += sorted(({"id": f"sc:{i}", "nome": nome_base(f"sc:{i}"), "produto": str(c.get("produto") or ""), "origem": "String Connection",
                      "ok": True} for i, c in _conexoes().items()), key=lambda b: b["nome"].lower())
    for b in saida:
        b["marcada"] = b["id"] in selecionadas
    return saida


def _identificador(nome: str, partes_max: int = 1) -> Optional[str]:
    """Nome de tabela/coluna conferido e entre colchetes (tabela aceita esquema: dbo.TABELA ou banco.dbo.TABELA)."""
    pedacos = str(nome or "").strip().split(".")
    if not 1 <= len(pedacos) <= partes_max or not all(_RE_IDENT.match(p) for p in pedacos):
        return None
    return ".".join("[" + p + "]" for p in pedacos)


def _sql(cfg: dict) -> dict:
    tabela = _identificador(cfg.get("tabela"), 3)
    numseq = _identificador(cfg.get("coluna_numseq"))
    status = _identificador(cfg.get("coluna_status"))
    if not tabela:
        raise ValueError("tabela inválida (ex.: INTERF_NFE_NAO_UTILZ ou dbo.INTERF_NFE_NAO_UTILZ; só letras, números e _)")
    if not numseq or not status:
        raise ValueError("nome de coluna inválido (só letras, números e _)")
    return {"tabela": tabela, "numseq": numseq, "status": status}


def _conectar(base: str):
    dados = _credenciais(base)
    if not dados:
        raise ValueError(f"a conexão da base {nome_base(base)} não está completa (servidor, banco, usuário e senha)")
    return conectar_banco(dados["server"], dados["database"], dados["user"], dados["password"], autocommit=False, raise_on_error=True)


def _fechar(conn) -> None:
    if conn is not None:
        try:
            conn.rollback()
            conn.close()
        except Exception:
            pass


def _ler_no_status_de(conn, s: dict, limite: int) -> list:
    cur = conn.cursor()
    cur.execute(f"SELECT TOP ({int(limite)}) {s['numseq']}, {s['status']} FROM {s['tabela']} WITH (NOLOCK) "
                f"WHERE {s['status']} = ? ORDER BY {s['numseq']}", [STATUS_DE])
    return [(linha[0], linha[1]) for linha in cur.fetchall()]


def _int_ou_none(valor):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None if valor is None else str(valor)


def _status_atuais(conn, s: dict, valores: list) -> dict:
    """{str(numseq): status} dos que ainda existem. Com mais de uma linha pro mesmo NUMSEQ, vale a que ainda não
    terminou (é ela que segura o relatório)."""
    atuais = {}
    cur = conn.cursor()
    for i in range(0, len(valores), CHUNK):
        pedaco = valores[i:i + CHUNK]
        cur.execute(f"SELECT {s['numseq']}, {s['status']} FROM {s['tabela']} WITH (NOLOCK) "
                    f"WHERE {s['numseq']} IN ({', '.join('?' * len(pedaco))})", pedaco)
        for numseq, status in cur.fetchall():
            chave, st = str(numseq), _int_ou_none(status)
            if chave not in atuais or atuais[chave] in STATUS_FINAIS:
                atuais[chave] = st
    return atuais


def _erro_texto(e: Exception) -> str:
    return str(e) if isinstance(e, (ValueError, RuntimeError)) else f"o banco recusou ({type(e).__name__}): {str(e)[:300]}"


# ------------------------------------------------------------------------------------------------ lote
def _novo_id(agora: datetime) -> str:
    base, n = agora.strftime("%Y%m%d-%H%M%S"), 2
    id_lote = base
    while os.path.exists(_caminho_lote(id_lote)):
        id_lote, n = f"{base}_{n}", n + 1
    return id_lote


def _registrar_status(lote: dict, atuais: dict, agora: datetime) -> None:
    quando = agora.strftime(FMT)
    for chave, reg in lote["registros"].items():
        st = atuais.get(chave, "ausente")
        if not reg["historico"] or reg["historico"][-1][1] != st:
            reg["historico"].append([quando, st])
        reg["atual"] = st
    lote["ultima_conferencia"] = quando


def _terminou(st) -> bool:
    return st == "ausente" or st in STATUS_FINAIS


def contagem_por_status(lote: dict) -> dict:
    cont = {}
    for reg in lote["registros"].values():
        chave = str(reg.get("atual"))
        cont[chave] = cont.get(chave, 0) + 1
    return cont


def cenario(reg: dict) -> str:
    """Caminho do registro: '20 → 15 → 10', '20 → 15 → não existe mais'..."""
    passos = [reg.get("antes", STATUS_DE)] + [st for _, st in reg["historico"]]
    limpo = []
    for p in passos:
        if not limpo or limpo[-1] != p:
            limpo.append(p)
    return " → ".join("não existe mais" if p == "ausente" else str(p) for p in limpo)


def resultado_final(reg: dict) -> str:
    st = reg.get("atual")
    if st == "ausente":
        return "Não existe mais na tabela"
    if st == 10:
        return "Terminou no status 10"
    if st == 20:
        return "Voltou pro status 20"
    return f"Ainda no status {st}"


def _rodar_base(base: str, cfg: dict, est: dict, origem: str, usuario: str) -> dict:
    """Rodada de uma base: lê os NUMSEQ no 20, grava o lote e (fora da simulação) faz o UPDATE pra 15. Levanta em erro."""
    agora, conn = datetime.now(), None
    simulacao = bool(est.get("simulacao", True))
    resumo = {"base": base, "nome": nome_base(base), "produto": produto_base(base), "ok": True, "simulacao": simulacao, "encontrados": 0, "lote": None}
    try:
        s = _sql(cfg)
        conn = _conectar(base)
        linhas = _ler_no_status_de(conn, s, max(1, min(50000, int(cfg.get("max_por_rodada") or 5000))))
        resumo["encontrados"] = len(linhas)
        if not linhas:
            resumo["mensagem"] = "nenhum NNU no status 20"
            logger.info("NNU 20 → 15 (%s, %s): nenhum NNU no status 20.", origem, resumo["nome"])
            return resumo
        # 2. guarda os NUMSEQ ANTES do UPDATE
        lote = {"id": _novo_id(agora), "base": base, "base_nome": resumo["nome"], "produto": produto_base(base),
                "inicio": agora.strftime(FMT), "origem": origem,
                "usuario": usuario, "simulacao": simulacao, "tabela": cfg["tabela"], "coluna_numseq": cfg["coluna_numseq"],
                "coluna_status": cfg["coluna_status"], "situacao": "simulado" if simulacao else "gravando", "atualizados": 0,
                "registros": {str(n): {"valor": n if isinstance(n, (int, str)) else str(n), "antes": _int_ou_none(st), "historico": [],
                                       "atual": _int_ou_none(st)} for n, st in linhas}}
        if not _gravar_lote(lote):
            raise RuntimeError("não foi possível gravar o lote antes do UPDATE (nada foi alterado)")
        resumo["lote"] = lote["id"]
        if simulacao:
            lote.update(situacao="simulado", fechado_em=agora.strftime(FMT), motivo="simulação: nada foi alterado")
            lote["relatorio"] = _gerar_relatorio(lote)
            _gravar_lote(lote)
            resumo["mensagem"] = f"simulação: {len(linhas)} NNU(s) seriam alterados de 20 pra 15"
            logger.info("NNU 20 → 15 (%s, %s, simulação): %d NUMSEQ no status 20, lote %s (nada alterado).",
                        origem, resumo["nome"], len(linhas), lote["id"])
            return resumo
        # 3. UPDATE só desses NUMSEQ e só se ainda estiverem no 20 (tudo numa transação)
        valores = [r["valor"] for r in lote["registros"].values()]
        cur, total = conn.cursor(), 0
        for i in range(0, len(valores), CHUNK):
            pedaco = valores[i:i + CHUNK]
            cur.execute(f"UPDATE {s['tabela']} SET {s['status']} = ? WHERE {s['status']} = ? "
                        f"AND {s['numseq']} IN ({', '.join('?' * len(pedaco))})", [STATUS_PARA, STATUS_DE] + pedaco)
            total += max(0, cur.rowcount or 0)
        conn.commit()
        for reg in lote["registros"].values():
            reg["historico"].append([agora.strftime(FMT), STATUS_DE])
        _registrar_status(lote, _status_atuais(conn, s, valores), datetime.now())
        lote.update(situacao="acompanhando", atualizados=total)
        _gravar_lote(lote)
        est["lotes_abertos"][base] = lote["id"]
        resumo["atualizados"] = total
        resumo["mensagem"] = f"{total} de {len(linhas)} NNU(s) alterados de 20 pra 15; acompanhando o lote"
        logger.info("NNU 20 → 15 (%s, %s): %d NUMSEQ no status 20, %d alterado(s) pra 15, lote %s.",
                    origem, resumo["nome"], len(linhas), total, lote["id"])
        return resumo
    finally:
        _fechar(conn)


def _rodar_bases(bases: list, origem: str, usuario: str, est: dict) -> list:
    cfg = config()
    resultados = []
    for base in bases:
        if base in est["lotes_abertos"]:
            if base not in est["aguardando"]:
                est["aguardando"].append(base)
            resultados.append({"base": base, "nome": nome_base(base), "produto": produto_base(base), "ok": True,
                               "mensagem": f"esperando o lote {est['lotes_abertos'][base]} fechar; roda assim que ele fechar"})
            continue
        try:
            resultados.append(_rodar_base(base, cfg, est, origem, usuario))
        except Exception as e:
            erro = _erro_texto(e)
            logger.warning("NNU 20 → 15 (%s, %s): a rodada falhou: %s", origem, nome_base(base), erro)
            resultados.append({"base": base, "nome": nome_base(base), "produto": produto_base(base), "ok": False, "erro": erro})
        if base in est["aguardando"]:
            est["aguardando"].remove(base)
    return resultados


def rodar(origem: str = "agendado", usuario: str = "") -> dict:
    """Rodada de todas as bases marcadas. Nunca levanta."""
    with _lock:
        if estado_execucao["executando"]:
            return {"ok": False, "erro": "já tem uma rodada ou conferência em andamento"}
        estado_execucao["executando"] = "rodada"
    try:
        est = _estado()
        bases = config()["bases"]
        if not bases:
            est["ultima_rodada"] = {"quando": datetime.now().strftime(FMT), "origem": origem, "resultados": [],
                                    "erro": "nenhuma base marcada na configuração"}
            _gravar_estado(est)
            return {"ok": False, "erro": "nenhuma base marcada na configuração"}
        resultados = _rodar_bases(bases, origem, usuario, est)
        est["ultima_rodada"] = {"quando": datetime.now().strftime(FMT), "origem": origem, "resultados": resultados}
        _gravar_estado(est)
        return {"ok": all(r["ok"] for r in resultados), "resultados": resultados}
    except Exception as e:
        logger.exception("Erro na rodada do NNU 20 → 15")
        return {"ok": False, "erro": str(e)}
    finally:
        with _lock:
            estado_execucao["executando"] = ""


def _conferir_lote(lote: dict, est: dict, agora: datetime) -> dict:
    conn = None
    try:
        cfg = {**config(), "tabela": lote["tabela"], "coluna_numseq": lote["coluna_numseq"], "coluna_status": lote["coluna_status"]}
        s = _sql(cfg)
        conn = _conectar(lote["base"])
        _registrar_status(lote, _status_atuais(conn, s, [r["valor"] for r in lote["registros"].values()]), agora)
    finally:
        _fechar(conn)
    pendentes = sum(1 for r in lote["registros"].values() if not _terminou(r["atual"]))
    espera_max = int(config().get("espera_max_horas") or 0)
    venceu = espera_max and agora - datetime.strptime(lote["inicio"], FMT) > timedelta(hours=espera_max)
    if not pendentes or venceu:
        lote.update(situacao="fechado", fechado_em=agora.strftime(FMT),
                    motivo="todos no status 10, no 20 ou fora da tabela" if not pendentes
                    else f"passou de {espera_max} h com {pendentes} ainda processando (limite da configuração)")
        lote["relatorio"] = _gerar_relatorio(lote)
        lote["email"] = _enviar_relatorio(lote)
        est["lotes_abertos"].pop(lote["base"], None)
        logger.info("NNU 20 → 15 (%s): lote %s fechado (%s); e-mail: %s.", lote.get("base_nome"), lote["id"], lote["motivo"],
                    "enviado" if lote["email"].get("ok") else lote["email"].get("erro"))
    _gravar_lote(lote)
    return {"base": lote["base"], "nome": lote.get("base_nome"), "lote": lote["id"], "ok": True, "pendentes": pendentes,
            "fechou": lote["situacao"] == "fechado"}


def conferir(origem: str = "agendado") -> dict:
    """Relê cada lote aberto; fecha (relatório + e-mail) o que terminou e roda a base que estava esperando. Nunca levanta."""
    with _lock:
        if estado_execucao["executando"]:
            return {"ok": False, "erro": "já tem uma rodada ou conferência em andamento"}
        estado_execucao["executando"] = "conferencia"
    try:
        est = _estado()
        agora, resultados = datetime.now(), []
        for base, id_lote in list(est["lotes_abertos"].items()):
            lote = ler_lote(id_lote)
            if not lote:
                est["lotes_abertos"].pop(base, None)
                continue
            try:
                resultados.append(_conferir_lote(lote, est, agora))
            except Exception as e:
                erro = _erro_texto(e)
                logger.warning("NNU 20 → 15 (%s): a conferência do lote %s falhou: %s", lote.get("base_nome"), id_lote, erro)
                resultados.append({"base": base, "nome": lote.get("base_nome"), "lote": id_lote, "ok": False, "erro": erro})
        # base que esperou o lote anterior: roda agora que ele fechou (se a automação estiver ligada)
        liberadas = [b for b in est["aguardando"] if b not in est["lotes_abertos"]]
        if liberadas and est.get("ligado"):
            rodada = _rodar_bases(liberadas, "agendado (esperou o lote anterior)", "", est)
            ultima = est.get("ultima_rodada") or {}
            est["ultima_rodada"] = {"quando": datetime.now().strftime(FMT), "origem": "agendado (esperou o lote anterior)",
                                    "resultados": rodada + [r for r in ultima.get("resultados", []) if r.get("base") not in liberadas]}
        if resultados:
            est["ultima_conferencia"] = {"quando": agora.strftime(FMT), "resultados": resultados}
        _gravar_estado(est)
        return {"ok": all(r["ok"] for r in resultados), "resultados": resultados}
    except Exception as e:
        logger.exception("Erro na conferência do NNU 20 → 15")
        return {"ok": False, "erro": str(e)}
    finally:
        with _lock:
            estado_execucao["executando"] = ""
            estado_execucao["ultima_conferencia"] = datetime.now()


# ------------------------------------------------------------------------------------------------ relatório e e-mail
def _linhas_relatorio(lote: dict) -> list:
    linhas = []
    for chave, reg in sorted(lote["registros"].items(), key=lambda kv: (len(kv[0]), kv[0])):
        ultima = reg["historico"][-1][0] if reg["historico"] else lote["inicio"]
        linhas.append([reg["valor"], reg.get("antes"), "não existe mais" if reg.get("atual") == "ausente" else reg.get("atual"),
                       resultado_final(reg), cenario(reg), ultima, max(0, len(reg["historico"]) - 1)])
    return linhas


def resumo_cenarios(lote: dict) -> dict:
    cont = {}
    for reg in lote["registros"].values():
        chave = resultado_final(reg) if lote.get("situacao") != "simulado" else "Seria alterado de 20 pra 15"
        cont[chave] = cont.get(chave, 0) + 1
    return dict(sorted(cont.items(), key=lambda kv: -kv[1]))


def _gerar_relatorio(lote: dict) -> str:
    """Excel com Resumo, Registros (status final e cenário de cada NUMSEQ) e Histórico (cada mudança de status)."""
    import xlsxwriter
    destino = os.path.join(_pasta("relatorios"), lote["id"] + ".xlsx")
    wb = xlsxwriter.Workbook(destino + ".tmp.xlsx")
    try:
        neg = wb.add_format({"bold": True})
        cab = wb.add_format({"bold": True, "bg_color": "#1f3b4d", "font_color": "#ffffff", "border": 1})
        ws = wb.add_worksheet("Resumo")
        ws.set_column(0, 0, 34)
        ws.set_column(1, 1, 60)
        info = [("Lote", lote["id"]), ("Base", lote.get("base_nome") or "-"), ("Início", lote["inicio"]),
                ("Fechado em", lote.get("fechado_em") or "-"), ("Situação", lote["situacao"]), ("Motivo", lote.get("motivo") or "-"),
                ("Simulação", "sim" if lote["simulacao"] else "não"), ("Tabela", lote["tabela"]), ("Coluna NUMSEQ", lote["coluna_numseq"]),
                ("Coluna de status", lote["coluna_status"]), ("NUMSEQ no status 20 antes do UPDATE", len(lote["registros"])),
                ("Alterados pra 15 (linhas do UPDATE)", lote.get("atualizados", 0))]
        for i, (k, v) in enumerate(info):
            ws.write(i, 0, k, neg)
            ws.write(i, 1, v)
        lin = len(info) + 1
        ws.write(lin, 0, "Cenário", cab)
        ws.write(lin, 1, "Quantidade", cab)
        for i, (k, v) in enumerate(resumo_cenarios(lote).items(), start=lin + 1):
            ws.write(i, 0, k)
            ws.write(i, 1, v)
        ws2 = wb.add_worksheet("Registros")
        colunas = ["NUMSEQ", "Status antes", "Status final", "Resultado", "Cenário (caminho)", "Última mudança", "Mudanças"]
        for c, t in enumerate(colunas):
            ws2.write(0, c, t, cab)
        for r, linha in enumerate(_linhas_relatorio(lote), start=1):
            for c, v in enumerate(linha):
                ws2.write(r, c, v)
        ws2.set_column(0, 2, 14)
        ws2.set_column(3, 4, 34)
        ws2.set_column(5, 6, 20)
        ws2.autofilter(0, 0, max(1, len(lote["registros"])), len(colunas) - 1)
        ws2.freeze_panes(1, 0)
        ws3 = wb.add_worksheet("Histórico")
        for c, t in enumerate(["NUMSEQ", "Quando", "Status"]):
            ws3.write(0, c, t, cab)
        r = 1
        for reg in lote["registros"].values():
            for quando, st in reg["historico"]:
                ws3.write(r, 0, reg["valor"])
                ws3.write(r, 1, quando)
                ws3.write(r, 2, "não existe mais" if st == "ausente" else st)
                r += 1
        ws3.set_column(0, 2, 20)
        ws3.freeze_panes(1, 0)
    finally:
        wb.close()
    os.replace(destino + ".tmp.xlsx", destino)
    return os.path.basename(destino)


def _destinatarios(texto: str) -> list:
    return [e for e in (x.strip() for x in re.split(r"[,;\s]+", str(texto or ""))) if e]


def _corpo_email(lote: dict) -> str:
    from html import escape
    linhas = "".join(f"<tr><td style='padding:4px 10px;border-bottom:1px solid #ddd'>{escape(k)}</td>"
                     f"<td style='padding:4px 10px;border-bottom:1px solid #ddd;text-align:right'><b>{v}</b></td></tr>"
                     for k, v in resumo_cenarios(lote).items())
    return (f"<div style='font-family:Segoe UI,Arial,sans-serif;font-size:14px;color:#1b1b1b'>"
            f"<div style='background:linear-gradient(90deg,#2db8cf,#b0cb1c);color:#fff;padding:14px 18px;border-radius:10px 10px 0 0'>"
            f"<b style='font-size:18px'>PDA</b> · NNU Enchanced · status 20 → 15</div>"
            f"<div style='border:1px solid #ddd;border-top:0;padding:16px 18px;border-radius:0 0 10px 10px'>"
            f"<p>O lote <b>{escape(lote['id'])}</b> da base <b>{escape(lote.get('base_nome') or '')}</b> (início {escape(lote['inicio'])}) "
            f"terminou: {escape(lote.get('motivo') or '')}.</p>"
            f"<p>{len(lote['registros'])} NUMSEQ estavam no status 20 na {escape(lote['tabela'])}; {lote.get('atualizados', 0)} foram alterados pra 15.</p>"
            f"<table style='border-collapse:collapse;font-size:13px'>{linhas}</table>"
            f"<p style='color:#666;font-size:12px'>A relação completa (status final e o caminho de cada registro) está no Excel anexo.</p></div></div>")


def _enviar_relatorio(lote: dict, usuario: str = "") -> dict:
    para = _destinatarios(config().get("emails"))
    quando = datetime.now().strftime(FMT)
    if not para:
        return {"ok": False, "erro": "nenhum destinatário configurado", "quando": quando}
    caminho = caminho_relatorio(lote["id"])
    try:
        from areas.emails.logica import _config_email_boas_vindas
        from core.email_utils import enviar_email
        assunto = (f"PDA · NNU 20 → 15 · {lote.get('base_nome') or ''} · lote {lote['inicio'][:16]} · "
                   f"{len(lote['registros'])} registro(s)")
        enviar_email(para, assunto, _corpo_email(lote), _config_email_boas_vindas(), anexos=[caminho] if caminho else None,
                     raise_on_error=True)
        return {"ok": True, "para": para, "quando": quando, "por": usuario}
    except Exception as e:
        logger.warning("NNU 20 → 15: e-mail do lote %s não foi: %s", lote["id"], type(e).__name__)
        return {"ok": False, "erro": f"o e-mail não foi ({type(e).__name__}: {str(e)[:200]})", "quando": quando}


def reenviar_email(id_lote: str, usuario: str) -> dict:
    lote = ler_lote(id_lote)
    if not lote or lote.get("situacao") != "fechado":
        return {"ok": False, "erro": "só dá pra reenviar o e-mail de um lote fechado"}
    lote["email"] = _enviar_relatorio(lote, usuario)
    _gravar_lote(lote)
    logger.info("NNU 20 → 15: e-mail do lote %s reenviado por %s: %s.", id_lote, usuario, "ok" if lote["email"]["ok"] else lote["email"]["erro"])
    return {"ok": lote["email"]["ok"], "erro": lote["email"].get("erro", "")}


# ------------------------------------------------------------------------------------------------ tela / controle
def _bases_do_form(dados: dict) -> list:
    bruto = dados.get("bases")
    return [b for b in (x.strip() for x in str(bruto or "").split(",")) if b] if bruto is not None else None


def salvar_config(dados: dict, usuario: str) -> dict:
    atual = config()
    novo = {k: str(dados.get(k) if dados.get(k) is not None else atual.get(k, v)).strip()
            for k, v in CONFIG_PADRAO.items() if k != "bases"}
    for k, (minimo, maximo) in LIMITES.items():
        try:
            novo[k] = int(novo[k])
        except ValueError:
            return {"ok": False, "erro": f"valor inválido em {k}"}
        if not minimo <= novo[k] <= maximo:
            return {"ok": False, "erro": f"{k}: de {minimo} a {maximo}"}
    bases = _bases_do_form(dados)
    bases = atual["bases"] if bases is None else bases
    validas = {b["id"] for b in bases_para_tela([])}
    if not bases or any(b not in validas for b in bases):
        return {"ok": False, "erro": "marque pelo menos uma base"}
    novo["bases"] = bases
    try:
        _sql(novo)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    emails = _destinatarios(novo["emails"])
    invalidos = [e for e in emails if not _RE_EMAIL.match(e)]
    if invalidos:
        return {"ok": False, "erro": "e-mail inválido: " + ", ".join(invalidos[:3])}
    novo["emails"] = ", ".join(emails)
    novo.update(alterado_por=usuario, alterado_em=datetime.now().strftime(FMT))
    if not _gravar_json(os.path.join(_pasta(), "config.json"), novo):
        return {"ok": False, "erro": "não foi possível salvar (detalhes no log)"}
    logger.info("NNU 20 → 15: configuração alterada por %s (bases %s, a cada %d h).", usuario,
                ", ".join(nome_base(b) for b in bases), novo["intervalo_horas"])
    _acordar.set()
    return {"ok": True}


def testar(dados: dict) -> dict:
    """Com a configuração da tela (sem salvar): em cada base, quantos estão no 20 e por status. Só leitura."""
    cfg = {**config(), **{k: dados.get(k) for k in ("tabela", "coluna_numseq", "coluna_status") if dados.get(k) is not None}}
    bases = _bases_do_form(dados) or cfg["bases"]
    try:
        s = _sql(cfg)
    except ValueError as e:
        return {"ok": False, "erro": str(e)}
    saida = []
    for base in bases:
        conn = None
        try:
            conn = _conectar(base)
            cur = conn.cursor()
            cur.execute(f"SELECT {s['status']}, COUNT(*) FROM {s['tabela']} WITH (NOLOCK) WHERE {s['status']} IN (10, 15, 20, 25, 31) "
                        f"GROUP BY {s['status']} ORDER BY {s['status']}")
            por_status = {str(st): n for st, n in cur.fetchall()}
            amostra = [str(n) for n, _ in _ler_no_status_de(conn, s, 10)]
            saida.append({"base": base, "nome": nome_base(base), "ok": True, "total": por_status.get("20", 0), "por_status": por_status,
                          "amostra": amostra})
        except Exception as e:
            saida.append({"base": base, "nome": nome_base(base), "ok": False, "erro": _erro_texto(e)})
        finally:
            _fechar(conn)
    return {"ok": True, "bases": saida}


def definir_ligado(ligado: bool, usuario: str) -> dict:
    est = _estado()
    est.update(ligado=bool(ligado), alterado_por=usuario, alterado_em=datetime.now().strftime(FMT))
    if not _gravar_estado(est):
        return {"ok": False, "erro": "não foi possível salvar (detalhes no log)"}
    logger.info("NNU 20 → 15 %s por %s.", "retomado" if ligado else "pausado", usuario)
    _acordar.set()
    return {"ok": True}


def definir_simulacao(simulacao: bool, usuario: str) -> dict:
    est = _estado()
    est.update(simulacao=bool(simulacao), simulacao_por=usuario, simulacao_em=datetime.now().strftime(FMT))
    if not simulacao:
        est.pop("ultima_rodada_agendada", None)  # saiu da simulação: a primeira rodada de verdade é já
    if not _gravar_estado(est):
        return {"ok": False, "erro": "não foi possível salvar (detalhes no log)"}
    logger.info("NNU 20 → 15: modo simulação %s por %s.", "ligado" if simulacao else "DESLIGADO (UPDATE de verdade)", usuario)
    _acordar.set()
    return {"ok": True}


def _proxima_rodada(est: dict, cfg: dict, agora: Optional[datetime] = None) -> Optional[datetime]:
    if not est.get("ligado"):
        return None
    try:
        base = datetime.strptime(est.get("ultima_rodada_agendada") or "", FMT)
    except ValueError:
        return agora or datetime.now()  # nunca rodou: a primeira é já
    ultima = est.get("ultima_rodada") or {}
    if ultima.get("erro") or any(not r.get("ok") for r in ultima.get("resultados", [])):
        return base + timedelta(minutes=TENTAR_DE_NOVO_MIN)  # 3.4.9.2: rodada com falha tenta de novo logo, não espera 2 h
    return base + timedelta(hours=int(cfg.get("intervalo_horas") or 2))


def _resumo_lote(lote: dict) -> dict:
    produto = lote.get("produto") or ("NFe" if lote.get("base") in ("alerta:cliente_i_standart", "alerta:cliente_i_enterprise", "alerta:cliente_i_ae") else "")
    return {"id": lote["id"], "base": lote.get("base"), "base_nome": lote.get("base_nome") or "-", "produto": produto, "inicio": lote["inicio"],
            "situacao": lote["situacao"], "simulacao": lote["simulacao"], "total": len(lote["registros"]),
            "atualizados": lote.get("atualizados", 0), "fechado_em": lote.get("fechado_em"), "motivo": lote.get("motivo"),
            "relatorio": bool(lote.get("relatorio")), "email": lote.get("email"), "cenarios": resumo_cenarios(lote),
            "por_status": contagem_por_status(lote)}


def _registros_tela(lote: dict, com_resultado: bool = False) -> list:
    return [{"numseq": str(r["valor"]), "antes": r.get("antes"), "atual": r.get("atual"), "cenario": cenario(r),
             **({"resultado": resultado_final(r)} if com_resultado else {})} for r in lote["registros"].values()]


def lotes_recentes() -> list:
    pasta = _pasta("lotes")
    nomes = sorted((n for n in os.listdir(pasta) if n.endswith(".json")), reverse=True)[:MAX_LOTES_NA_TELA]
    return [_resumo_lote(lote) for lote in (ler_lote(n[:-5]) for n in nomes) if lote]


def status() -> dict:
    cfg, est = config(), _estado()
    abertos = [lote for lote in (ler_lote(i) for i in est["lotes_abertos"].values()) if lote]
    proxima = _proxima_rodada(est, cfg)
    return {"ok": True, "ligado": bool(est.get("ligado")), "simulacao": bool(est.get("simulacao", True)),
            "alterado_por": est.get("alterado_por"), "alterado_em": est.get("alterado_em"),
            "executando": estado_execucao["executando"], "ultima_rodada": est.get("ultima_rodada"),
            "ultima_conferencia": est.get("ultima_conferencia"), "aguardando": [nome_base(b) for b in est["aguardando"]],
            "proxima": ("agora" if proxima <= datetime.now() else proxima.strftime("%d/%m %H:%M")) if proxima else None,
            "config": {k: cfg.get(k) for k in CONFIG_PADRAO}, "bases": bases_para_tela(cfg["bases"]),
            "lotes_abertos": [{**_resumo_lote(lote), "registros": _registros_tela(lote)} for lote in abertos],
            "lotes": lotes_recentes()}


def detalhe_lote(id_lote: str) -> dict:
    lote = ler_lote(id_lote)
    if not lote:
        return {"ok": False, "erro": "lote não encontrado"}
    return {"ok": True, **_resumo_lote(lote), "registros": _registros_tela(lote, True)}


def apagar_lotes_antigos(agora: Optional[datetime] = None) -> int:
    corte = ((agora or datetime.now()) - timedelta(days=DIAS_GUARDAR_LOTES)).strftime("%Y%m%d")
    abertos = set(_estado()["lotes_abertos"].values())
    apagados = 0
    for sub, ext in (("lotes", ".json"), ("relatorios", ".xlsx")):
        pasta = _pasta(sub)
        for nome in os.listdir(pasta):
            if nome.endswith(ext) and nome[:8].isdigit() and nome[:8] < corte and nome[:-len(ext)] not in abertos:
                try:
                    os.remove(os.path.join(pasta, nome))
                    apagados += 1
                except OSError:
                    pass
    if apagados:
        logger.info("NNU 20 → 15: %d arquivo(s) de lotes com mais de %d dias apagados.", apagados, DIAS_GUARDAR_LOTES)
    return apagados


class MonitorNnuStatus:
    """Automático: rodada a cada `intervalo_horas` (enquanto não estiver pausado) e conferência dos lotes abertos a cada
    `acompanhar_min` (sempre: só lê)."""

    def __init__(self):
        self._stop = threading.Event()
        self._limpou_em = None

    def iniciar(self) -> None:
        threading.Thread(target=self._loop, daemon=True, name="nnu_status").start()

    def _passo(self) -> None:
        cfg, est = config(), _estado()
        agora = datetime.now()
        if est["lotes_abertos"] or est["aguardando"]:
            ultima = estado_execucao["ultima_conferencia"]
            if ultima is None or agora - ultima >= timedelta(minutes=int(cfg.get("acompanhar_min") or 10)):
                conferir("agendado")
                est = _estado()
        proxima = _proxima_rodada(est, cfg, agora)
        if proxima and agora >= proxima:
            est["ultima_rodada_agendada"] = agora.strftime(FMT)
            _gravar_estado(est)
            rodar("agendado")
        if self._limpou_em != agora.date():
            self._limpou_em = agora.date()
            apagar_lotes_antigos(agora)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._passo()
            except Exception:
                logger.exception("Erro no ciclo do NNU 20 → 15")
            _acordar.wait(30)
            _acordar.clear()
