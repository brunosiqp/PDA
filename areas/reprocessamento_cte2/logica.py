"""Reprocessamento CTe2 - lógica (2.35.4.0).

Desenvolvido por Caio Peixoto como serviço do Windows em .NET
("Reprocessamento de CT-e", ReprocessamentoCte.exe) e trazido pro PDA com a
mesma regra, consulta a consulta:

1. A cada ciclo (60 s), lê no banco de ORIGEM os CT-es parados (INTERF_CTE com
   IND_STATUS 0, 1 ou 2 e emissão há mais de 1 minuto), paginando por chave.
2. Cada chave entra na tabela de CONTROLE (dbo.CONTROLE_REPROCESSAMENTO_CTE) como
   OBSERVANDO. Só fica elegível com duas detecções e o tempo mínimo.
3. Elegível: reconsulta a origem. Se a aplicação já resolveu, só tira do controle.
4. Ainda parada: reserva a chave de forma atômica (OBSERVANDO -> ENVIANDO) e faz o
   POST na API do CTe2 com a x-api-key.
5. Sucesso ou falha, a chave sai do controle (a tabela não guarda histórico).
   Qualquer falha (HTTP sem sucesso, timeout, rede, envio interrompido) grava a
   chave em documentos-bloqueados.log e ela nunca mais é tentada, nem depois de
   reiniciar. Liberar é manual (no card).

Diferenças do serviço original: começa DESLIGADO e só roda quando alguém liga no
card (estado gravado em reprocessamento_cte2/estado.json); não liga se o serviço
do Windows estiver rodando nesta máquina (os dois juntos teriam listas de
bloqueio separadas); credenciais no padrão do PDA (seção [reprocessamento_cte2]
do CREDENCIAIS_CENTRALIZADAS.env, senhas e x-api-key no config.dat cifrado).
"""
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional

import requests

from core.config_seguro import obter_valor_config as _obter_valor_config
from core.db_utils import conectar_banco
from nucleo.avisos_falha import registrar_resultado as registrar_resultado_job
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_config_hibrido

logger_reprocessamento_cte2 = logging.getLogger("alertas.reprocessamento_cte2")

DESENVOLVIDO_POR = "Caio Peixoto"
DESENVOLVIDO_POR_LOGIN = "caio.peixoto"  # foto e link pro perfil no crédito (3.1.5.0)

# mesmos valores do appsettings.json do serviço original
API_BASE_URL_PADRAO = "https://saas.example.app/cte2/api/v2/documentos-fiscais/reprocessar/"
INTERVALO_SEGUNDOS = 60
LIMITE_POR_CICLO = 100
LIMITE_LEITURA_CANDIDATOS = 1000
INTERVALO_ENTRE_CHAMADAS_MS = 200
MINUTOS_CONFIRMACAO = 1
MINUTOS_EXPIRACAO_RESERVA = 10
MINUTOS_EXPIRACAO_OBSERVACAO = 5
TIMEOUT_API_SEGUNDOS = 30
NOME_SERVICO_WINDOWS = "ReprocessamentoCte"

# ConsultaSql / ConsultaRevalidacaoSql do serviço, com "?" do pyodbc no lugar dos parâmetros nomeados
CONSULTA_CANDIDATOS = (
    "SELECT DISTINCT TOP (?) CONVERT(varchar(100), incx.A_ID) AS CHAVE "
    "FROM INTERF_CTE inc INNER JOIN INTERF_CTE_XML incx ON inc.ID = incx.INTERF_CTE_FK "
    "WHERE inc.IND_STATUS IN (0, 1, 2) AND incx.B_DHEMI <= DATEADD(MINUTE, -1, GETDATE()) "
    "AND incx.A_ID IS NOT NULL AND (? = '' OR CONVERT(varchar(100), incx.A_ID) > ?) ORDER BY CHAVE"
)
CONSULTA_REVALIDACAO = (
    "SELECT COUNT(1) FROM INTERF_CTE inc INNER JOIN INTERF_CTE_XML incx ON inc.ID = incx.INTERF_CTE_FK "
    "WHERE CONVERT(varchar(100), incx.A_ID) = ? AND inc.IND_STATUS IN (0, 1, 2) "
    "AND incx.B_DHEMI <= DATEADD(MINUTE, -1, GETDATE())"
)

SQL_RETIRAR_RESERVAS_EXPIRADAS = """
SET NOCOUNT ON;
DECLARE @Minutos int = ?;
DELETE FROM dbo.CONTROLE_REPROCESSAMENTO_CTE
OUTPUT deleted.A_ID
 WHERE STATUS_CONTROLE = 'ENVIANDO'
   AND ULTIMA_ATUALIZACAO <= DATEADD(MINUTE, -@Minutos, SYSDATETIME());
"""
SQL_LIMPAR_OBSERVACOES_EXPIRADAS = """
SET NOCOUNT ON;
DECLARE @Minutos int = ?;
DELETE FROM dbo.CONTROLE_REPROCESSAMENTO_CTE
 WHERE STATUS_CONTROLE = 'OBSERVANDO'
   AND ULTIMA_DETECCAO <= DATEADD(MINUTE, -@Minutos, SYSDATETIME());
"""
SQL_REGISTRAR_OBSERVACAO = """
SET NOCOUNT ON;
SET XACT_ABORT ON;
DECLARE @Chave varchar(100) = ?, @MinutosConfirmacao int = ?;
SET TRANSACTION ISOLATION LEVEL SERIALIZABLE;
BEGIN TRANSACTION;

IF EXISTS (SELECT 1 FROM dbo.CONTROLE_REPROCESSAMENTO_CTE WITH (UPDLOCK, HOLDLOCK) WHERE A_ID = @Chave)
BEGIN
    UPDATE dbo.CONTROLE_REPROCESSAMENTO_CTE
       SET ULTIMA_DETECCAO = SYSDATETIME(),
           QUANTIDADE_DETECCOES = QUANTIDADE_DETECCOES + 1,
           ULTIMA_ATUALIZACAO = SYSDATETIME()
     WHERE A_ID = @Chave AND STATUS_CONTROLE = 'OBSERVANDO';
END
ELSE
BEGIN
    INSERT INTO dbo.CONTROLE_REPROCESSAMENTO_CTE
        (A_ID, PRIMEIRA_DETECCAO, ULTIMA_DETECCAO, QUANTIDADE_DETECCOES, STATUS_CONTROLE, ULTIMA_ATUALIZACAO)
    VALUES
        (@Chave, SYSDATETIME(), SYSDATETIME(), 1, 'OBSERVANDO', SYSDATETIME());
END;

DECLARE @Elegivel bit = 0;
IF EXISTS
(
    SELECT 1 FROM dbo.CONTROLE_REPROCESSAMENTO_CTE
     WHERE A_ID = @Chave
       AND STATUS_CONTROLE = 'OBSERVANDO'
       AND QUANTIDADE_DETECCOES >= 2
       AND PRIMEIRA_DETECCAO <= DATEADD(MINUTE, -@MinutosConfirmacao, SYSDATETIME())
) SET @Elegivel = 1;

COMMIT TRANSACTION;
SELECT @Elegivel;
"""
SQL_TENTAR_RESERVAR = """
SET NOCOUNT ON;
DECLARE @Chave varchar(100) = ?, @MinutosConfirmacao int = ?;
UPDATE dbo.CONTROLE_REPROCESSAMENTO_CTE WITH (ROWLOCK, UPDLOCK)
   SET STATUS_CONTROLE = 'ENVIANDO',
       ULTIMA_ATUALIZACAO = SYSDATETIME()
 WHERE A_ID = @Chave
   AND STATUS_CONTROLE = 'OBSERVANDO'
   AND QUANTIDADE_DETECCOES >= 2
   AND PRIMEIRA_DETECCAO <= DATEADD(MINUTE, -@MinutosConfirmacao, SYSDATETIME());
SELECT @@ROWCOUNT;
"""
SQL_REMOVER_CONTROLE = "SET NOCOUNT ON; DELETE FROM dbo.CONTROLE_REPROCESSAMENTO_CTE WHERE A_ID = ?;"
SQL_RESUMO_CONTROLE = (
    "SELECT STATUS_CONTROLE, COUNT(1) FROM dbo.CONTROLE_REPROCESSAMENTO_CTE GROUP BY STATUS_CONTROLE"
)

CHAVES_CONFIG = [
    "ORIGEM_SERVER", "ORIGEM_DATABASE", "ORIGEM_USER", "ORIGEM_PASSWORD",
    "CONTROLE_SERVER", "CONTROLE_DATABASE", "CONTROLE_USER", "CONTROLE_PASSWORD",
    "API_KEY", "API_BASE_URL",
]
# segredos: o config.dat cifrado (Criptografia de Dados Sensíveis) tem prioridade sobre o arquivo de credenciais
CHAVES_SECRETAS = ("ORIGEM_PASSWORD", "CONTROLE_PASSWORD", "API_KEY")
ROTULOS_CONFIG = {
    "ORIGEM_SERVER": "servidor da origem", "ORIGEM_DATABASE": "banco da origem", "ORIGEM_USER": "usuário da origem",
    "ORIGEM_PASSWORD": "senha da origem", "CONTROLE_SERVER": "servidor do controle",
    "CONTROLE_DATABASE": "banco do controle", "CONTROLE_USER": "usuário do controle",
    "CONTROLE_PASSWORD": "senha do controle", "API_KEY": "x-api-key",
}
RE_CHAVE = re.compile(r"^[A-Za-z0-9]{1,100}$")


class ConfiguracaoIncompleta(RuntimeError):
    """Falta credencial: vira aviso no log, sem o rastro do erro a cada ciclo."""


# ---------------------------------------------------------------------------
# configuração e arquivos
# ---------------------------------------------------------------------------
# Origem automática (3.1.5.0, pedido do Igor: "não quero ter que fazer isso manual"): sem ORIGEM_* próprios,
# usa uma String Connection de CTe2 (de preferência do cliente Saas) ou, sem ela, a conexão do alerta
# "CTe2 SaaS Status Inicial", que consulta a mesma INTERF_CTE no mesmo banco.
SECAO_ALERTA_CTE2 = "alerta__saas__cte2_status_inicial"
ENV_ALERTA_CTE2 = ".env.saas__cte2_status_inicial"
CHAVE_SENHA_ALERTA_CTE2 = "saas__cte2_status_inicial::db_password"  # mesma chave que o alerta usa no config.dat
CHAVES_ORIGEM = ("ORIGEM_SERVER", "ORIGEM_DATABASE", "ORIGEM_USER", "ORIGEM_PASSWORD")
CHAVES_CONTROLE = ("CONTROLE_SERVER", "CONTROLE_DATABASE", "CONTROLE_USER", "CONTROLE_PASSWORD")


def _ler_string_connection(texto: str) -> dict:
    """'Server=x;Database=y;User Id=z;Password=w' -> {ORIGEM_SERVER, ...} (só o que der pra ler)."""
    partes = {}
    for pedaco in str(texto or "").split(";"):
        if "=" in pedaco:
            nome, valor = pedaco.split("=", 1)
            partes[" ".join(nome.split()).casefold()] = valor.strip()
    def pega(*nomes):
        return next((partes[n] for n in nomes if partes.get(n)), "")
    return {"ORIGEM_SERVER": pega("server", "data source", "address", "addr", "network address"),
            "ORIGEM_DATABASE": pega("database", "initial catalog"),
            "ORIGEM_USER": pega("user id", "uid", "user", "username"),
            "ORIGEM_PASSWORD": pega("password", "pwd")}


def _origem_por_string_connection() -> Optional[dict]:
    try:
        from areas.string_connections.logica import STRING_CONNECTIONS
    except Exception:
        return None
    candidatas = []
    for info in STRING_CONNECTIONS.values():
        produto = "".join(str(info.get("produto") or "").split()).casefold()
        if "cte2" not in produto:
            continue
        valores = _ler_string_connection(info.get("conexao"))
        if all(valores.values()):
            saas = "saas" in str(info.get("cliente") or "").casefold()
            candidatas.append((0 if saas else 1, f"String Connection {info.get('cliente')} · {info.get('produto')}", valores))
    if not candidatas:
        return None
    candidatas.sort(key=lambda c: c[0])
    return {**candidatas[0][2], "_FONTE": candidatas[0][1]}


def _origem_pelo_alerta() -> Optional[dict]:
    try:
        sec = _obter_config_hibrido(SECAO_ALERTA_CTE2, ENV_ALERTA_CTE2, ["db_server", "db_name", "db_user", "db_password"])
    except Exception:
        logger_reprocessamento_cte2.exception("Não foi possível ler a conexão do alerta CTe2 SaaS Status Inicial.")
        return None
    valores = {"ORIGEM_SERVER": (sec.get("db_server") or "").strip(), "ORIGEM_DATABASE": (sec.get("db_name") or "").strip(),
               "ORIGEM_USER": (sec.get("db_user") or "").strip(),
               "ORIGEM_PASSWORD": _obter_valor_config(CHAVE_SENHA_ALERTA_CTE2, sec.get("db_password") or "")}
    return {**valores, "_FONTE": "conexão do alerta CTe2 SaaS Status Inicial"} if all(valores.values()) else None


def _config() -> dict:
    valores = _obter_config_hibrido("reprocessamento_cte2", ".env.reprocessamento_cte2", CHAVES_CONFIG)
    for chave in CHAVES_SECRETAS:
        valores[chave] = _obter_valor_config(f"reprocessamento_cte2::{chave}", valores.get(chave) or "")
    valores["API_BASE_URL"] = (valores.get("API_BASE_URL") or API_BASE_URL_PADRAO).strip()
    # origem: a configurada à mão manda; sem nada configurado, a automática (tudo de uma fonte só, pra não misturar)
    if any((valores.get(c) or "").strip() for c in CHAVES_ORIGEM):
        valores["_FONTE_ORIGEM"] = "configuração do Reprocessamento CTe2"
    else:
        auto = _origem_por_string_connection() or _origem_pelo_alerta()
        if auto:
            valores.update({c: auto[c] for c in CHAVES_ORIGEM})
            valores["_FONTE_ORIGEM"] = auto["_FONTE"]
    # controle: sem banco de controle configurado, o controle fica no próprio PDA (controle.json)
    valores["_CONTROLE_LOCAL"] = not any((valores.get(c) or "").strip() for c in CHAVES_CONTROLE)
    return valores


def config_faltando() -> list:
    """Nomes (nunca valores) do que falta configurar."""
    cfg = _config()
    chaves = [c for c in ROTULOS_CONFIG if not (cfg["_CONTROLE_LOCAL"] and c in CHAVES_CONTROLE)]
    return [ROTULOS_CONFIG[c] for c in chaves if not (cfg.get(c) or "").strip()]


def definir_api_key(valor: str, usuario: str) -> dict:
    """Grava a x-api-key cifrada no config.dat (Criptografia de Dados Sensíveis), pelo próprio card."""
    valor = (valor or "").strip()
    if not 8 <= len(valor) <= 500 or any(ch.isspace() for ch in valor):
        return {"ok": False, "erro": "x-api-key inválida (8 a 500 caracteres, sem espaços)"}
    try:
        from core.config_seguro import definir_valor_config_dat
        definir_valor_config_dat("reprocessamento_cte2::API_KEY", valor)
    except Exception:
        logger_reprocessamento_cte2.exception("Não foi possível gravar a x-api-key.")
        return {"ok": False, "erro": "não foi possível gravar (detalhes no log)"}
    logger_reprocessamento_cte2.info("x-api-key cadastrada pelo card por '%s'.", usuario)
    return {"ok": True}


def pasta_dados() -> str:
    pasta = os.path.join(_base_path_app(), "reprocessamento_cte2")
    os.makedirs(pasta, exist_ok=True)
    return pasta


def _arquivo_bloqueados() -> str:
    return os.path.join(pasta_dados(), "documentos-bloqueados.log")


def _arquivo_estado() -> str:
    return os.path.join(pasta_dados(), "estado.json")


def _arquivo_auditoria(tipo: str, dia: Optional[datetime] = None) -> str:
    return os.path.join(pasta_dados(), f"{tipo}-{(dia or datetime.now()):%Y%m%d}.log")


def _limitar(texto, n: int = 1000):
    if texto is None or not str(texto).strip():
        return None
    texto = str(texto)
    return texto if len(texto) <= n else texto[:n]


# ---------------------------------------------------------------------------
# bloqueio definitivo (RegistroFalhasDefinitivas) e auditoria (ProcessamentoAudit)
# ---------------------------------------------------------------------------
_lock_arquivos = threading.Lock()
_chaves_bloqueadas: set = set()
_bloqueadas_carregadas = False


def _carregar_bloqueadas() -> None:
    global _bloqueadas_carregadas
    with _lock_arquivos:
        if _bloqueadas_carregadas:
            return
        _chaves_bloqueadas.clear()
        caminho = _arquivo_bloqueados()
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                for linha in f:
                    try:
                        chave = (json.loads(linha).get("chave") or "").strip()
                        if chave:
                            _chaves_bloqueadas.add(chave.upper())
                    except Exception:
                        logger_reprocessamento_cte2.warning("Linha inválida ignorada no registro de bloqueio definitivo.")
        _bloqueadas_carregadas = True
    logger_reprocessamento_cte2.info("Foram carregadas %d chave(s) bloqueadas para novas tentativas.", len(_chaves_bloqueadas))


def esta_bloqueada(chave: str) -> bool:
    _carregar_bloqueadas()
    return chave.upper() in _chaves_bloqueadas


def _registrar_bloqueio(chave: str, status_http: Optional[int], motivo: str) -> None:
    _carregar_bloqueadas()
    with _lock_arquivos:
        if chave.upper() in _chaves_bloqueadas:
            return
        linha = json.dumps({"dataHora": datetime.now().astimezone().isoformat(), "chave": chave,
                            "statusHttp": status_http, "motivo": _limitar(motivo) or ""}, ensure_ascii=False)
        with open(_arquivo_bloqueados(), "a", encoding="utf-8") as f:
            f.write(linha + "\n")
        _chaves_bloqueadas.add(chave.upper())


def _auditar(tipo: str, chave: str, status_http: Optional[int], resposta, erro=None) -> None:
    linha = json.dumps({"dataHora": datetime.now().astimezone().isoformat(), "chave": chave, "statusHttp": status_http,
                        "resposta": _limitar(resposta), "erro": _limitar(erro)}, ensure_ascii=False)
    with _lock_arquivos:
        with open(_arquivo_auditoria(tipo), "a", encoding="utf-8") as f:
            f.write(linha + "\n")


def liberar_chave(chave: str, usuario: str) -> dict:
    """Tira a chave do bloqueio definitivo (o passo manual do guia original, com
    cópia do arquivo antes). Ela volta a ser candidata no próximo ciclo."""
    chave = (chave or "").strip()
    if not RE_CHAVE.match(chave):
        return {"ok": False, "erro": "Chave inválida."}
    _carregar_bloqueadas()
    with _lock_arquivos:
        if chave.upper() not in _chaves_bloqueadas:
            return {"ok": False, "erro": "Essa chave não está bloqueada."}
        caminho = _arquivo_bloqueados()
        shutil.copy2(caminho, caminho + ".bak")
        mantidas = []
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                try:
                    if (json.loads(linha).get("chave") or "").strip().upper() == chave.upper():
                        continue
                except Exception:
                    pass
                mantidas.append(linha)
        temporario = caminho + ".tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            f.writelines(mantidas)
        os.replace(temporario, caminho)
        _chaves_bloqueadas.discard(chave.upper())
    logger_reprocessamento_cte2.info("Chave %s liberada do bloqueio definitivo por '%s'.", chave, usuario)
    return {"ok": True}


def ler_registros(tipo: str, dia: Optional[str] = None, limite: int = 300) -> dict:
    """Últimos registros (mais recentes primeiro) de sucessos/erros de um dia ou dos bloqueados."""
    if tipo == "bloqueados":
        caminho = _arquivo_bloqueados()
    elif tipo in ("sucessos", "erros"):
        try:
            data = datetime.strptime(dia, "%Y-%m-%d") if dia else datetime.now()
        except ValueError:
            return {"ok": False, "erro": "Dia inválido (use AAAA-MM-DD)."}
        caminho = _arquivo_auditoria(tipo, data)
    else:
        return {"ok": False, "erro": "Tipo inválido."}
    registros, total = [], 0
    if os.path.exists(caminho):
        with _lock_arquivos:
            with open(caminho, encoding="utf-8") as f:
                linhas = f.readlines()
        total = len(linhas)
        for linha in reversed(linhas[-limite:]):
            try:
                registros.append(json.loads(linha))
            except Exception:
                continue
    return {"ok": True, "tipo": tipo, "total": total, "registros": registros}


def _contar_linhas(caminho: str) -> int:
    if not os.path.exists(caminho):
        return 0
    with _lock_arquivos:
        with open(caminho, encoding="utf-8") as f:
            return sum(1 for _ in f)


# ---------------------------------------------------------------------------
# liga/desliga (persistido) e serviço do Windows
# ---------------------------------------------------------------------------
def _ler_estado_persistido() -> dict:
    try:
        with open(_arquivo_estado(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ligado": False}


def esta_ligado() -> bool:
    return bool(_ler_estado_persistido().get("ligado"))


_cache_servico = {"quando": 0.0, "estado": None}


def estado_servico_windows() -> Optional[str]:
    """RUNNING/STOPPED/... do serviço original nesta máquina, ou None se não existir.
    Consulta o sc.exe no máximo a cada 30 s."""
    if os.name != "nt":
        return None
    if time.time() - _cache_servico["quando"] < 30:
        return _cache_servico["estado"]
    estado = None
    try:
        saida = subprocess.run(["sc", "query", NOME_SERVICO_WINDOWS], capture_output=True, timeout=10,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        # 3.3.2.1: o sc.exe responde na página de código do console (cp850); ler como UTF-8 dava UnicodeDecodeError
        saida = (saida or b"").decode("cp850", errors="replace")
        m = re.search(r"STATE\s*:\s*\d+\s+(\w+)", saida)
        estado = m.group(1) if m else None
    except Exception:
        estado = None
    _cache_servico.update(quando=time.time(), estado=estado)
    return estado


def definir_ligado(ligado: bool, usuario: str) -> dict:
    if ligado:
        faltando = config_faltando()
        if faltando:
            return {"ok": False, "erro": "Configuração incompleta: falta " + ", ".join(faltando) + "."}
        _cache_servico["quando"] = 0.0
        if estado_servico_windows() == "RUNNING":
            return {"ok": False, "erro": f"O serviço do Windows '{NOME_SERVICO_WINDOWS}' está rodando nesta máquina. "
                                         "Pare (e remova) o serviço antes de ligar aqui, pra não rodarem os dois."}
    with _lock_arquivos:
        temporario = _arquivo_estado() + ".tmp"
        with open(temporario, "w", encoding="utf-8") as f:
            json.dump({"ligado": bool(ligado), "alterado_por": usuario,
                       "alterado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}, f, ensure_ascii=False)
        os.replace(temporario, _arquivo_estado())
    logger_reprocessamento_cte2.info("Reprocessamento CTe2 %s por '%s'.", "LIGADO" if ligado else "PAUSADO", usuario)
    if ligado:
        _acordar.set()
    return {"ok": True}


# ---------------------------------------------------------------------------
# bancos
# ---------------------------------------------------------------------------
def _conectar(prefixo: str, autocommit: bool):
    cfg = _config()
    return conectar_banco(cfg[f"{prefixo}_SERVER"], cfg[f"{prefixo}_DATABASE"], cfg[f"{prefixo}_USER"],
                          cfg[f"{prefixo}_PASSWORD"], autocommit=autocommit, raise_on_error=True)


def _primeiro_resultado(cursor):
    """Num lote com várias instruções, pula até o primeiro conjunto que tem linhas."""
    while cursor.description is None:
        if not cursor.nextset():
            return None
    return cursor


def _buscar_candidatos() -> list:
    resultado, apos_chave = [], ""
    conn = _conectar("ORIGEM", autocommit=True)
    try:
        cursor = conn.cursor()
        while len(resultado) < LIMITE_POR_CICLO:
            lidas, ultima = 0, apos_chave
            cursor.execute(CONSULTA_CANDIDATOS, LIMITE_LEITURA_CANDIDATOS, apos_chave, apos_chave)
            for (valor,) in cursor.fetchall():
                lidas += 1
                chave = str(valor).strip() if valor is not None else ""
                if not chave:
                    continue
                ultima = chave
                if not esta_bloqueada(chave):
                    resultado.append(chave)
            if lidas < LIMITE_LEITURA_CANDIDATOS or ultima == apos_chave:
                break
            apos_chave = ultima
    finally:
        conn.close()
    vistas, unicas = set(), []
    for chave in resultado:
        if chave.upper() not in vistas:
            vistas.add(chave.upper())
            unicas.append(chave)
    return unicas[:LIMITE_POR_CICLO]


def _continua_travado(chave: str) -> bool:
    conn = _conectar("ORIGEM", autocommit=True)
    try:
        cursor = conn.cursor()
        cursor.execute(CONSULTA_REVALIDACAO, chave)
        return int(cursor.fetchone()[0]) > 0
    finally:
        conn.close()


def _controle(sql: str, *parametros, buscar: str = ""):
    """Roda um lote na database de controle. buscar: '' (nada), 'escalar' ou 'todas'."""
    conn = _conectar("CONTROLE", autocommit=True)  # os lotes controlam a própria transação
    try:
        cursor = conn.cursor()
        cursor.execute(sql, *parametros)
        if not buscar:
            return None
        cursor = _primeiro_resultado(cursor)
        if cursor is None:
            return None if buscar == "escalar" else []
        if buscar == "escalar":
            linha = cursor.fetchone()
            return linha[0] if linha else None
        return cursor.fetchall()
    finally:
        conn.close()


# Controle no próprio PDA (3.1.5.0): quando não tem banco de controle configurado, a mesma regra da
# dbo.CONTROLE_REPROCESSAMENTO_CTE roda num arquivo (reprocessamento_cte2/controle.json). Com um PDA só
# rodando a automação, não precisa de banco pra coordenar; o arquivo guarda as reservas pra uma queda no
# meio do envio continuar virando bloqueio na próxima partida.
_lock_controle_local = threading.Lock()
_controle_local: dict = {}
_controle_local_carregado = {"ok": False}


def _arquivo_controle_local() -> str:
    return os.path.join(pasta_dados(), "controle.json")


def _ctl_carregar() -> None:
    if _controle_local_carregado["ok"]:
        return
    try:
        with open(_arquivo_controle_local(), encoding="utf-8") as f:
            _controle_local.update(json.load(f) or {})
    except FileNotFoundError:
        pass
    except Exception:
        logger_reprocessamento_cte2.exception("controle.json ilegível: começando o controle vazio.")
    _controle_local_carregado["ok"] = True


def _ctl_gravar() -> None:
    caminho = _arquivo_controle_local()
    with open(caminho + ".tmp", "w", encoding="utf-8") as f:
        json.dump(_controle_local, f, ensure_ascii=False)
    os.replace(caminho + ".tmp", caminho)


def _antes(iso: str, minutos: int) -> bool:
    """O instante iso é de mais de `minutos` atrás (ou igual)?"""
    try:
        return datetime.fromisoformat(iso) <= datetime.now() - timedelta(minutes=minutos)
    except (TypeError, ValueError):
        return True


def _ctl_local(acao: str, chave: str = "", minutos: int = 0):
    agora = datetime.now().isoformat(timespec="seconds")
    with _lock_controle_local:
        _ctl_carregar()
        if acao == "retirar_reservas":
            saem = [c for c, r in _controle_local.items() if r["status"] == "ENVIANDO" and _antes(r["ultima_atualizacao"], minutos)]
        elif acao == "limpar_observacoes":
            saem = [c for c, r in _controle_local.items() if r["status"] == "OBSERVANDO" and _antes(r["ultima_deteccao"], minutos)]
        elif acao == "remover":
            saem = [chave] if chave in _controle_local else []
        elif acao == "resumo":
            resumo: dict = {}
            for r in _controle_local.values():
                resumo[r["status"]] = resumo.get(r["status"], 0) + 1
            return resumo
        elif acao == "registrar":
            r = _controle_local.get(chave)
            if r is None:
                _controle_local[chave] = {"primeira_deteccao": agora, "ultima_deteccao": agora, "deteccoes": 1,
                                          "status": "OBSERVANDO", "ultima_atualizacao": agora}
            elif r["status"] == "OBSERVANDO":
                r.update(ultima_deteccao=agora, deteccoes=r["deteccoes"] + 1, ultima_atualizacao=agora)
            r = _controle_local[chave]
            _ctl_gravar()
            return r["status"] == "OBSERVANDO" and r["deteccoes"] >= 2 and _antes(r["primeira_deteccao"], minutos)
        elif acao == "reservar":
            r = _controle_local.get(chave)
            if not (r and r["status"] == "OBSERVANDO" and r["deteccoes"] >= 2 and _antes(r["primeira_deteccao"], minutos)):
                return 0
            r.update(status="ENVIANDO", ultima_atualizacao=agora)
            _ctl_gravar()
            return 1
        else:
            raise ValueError(acao)
        for c in saem:
            _controle_local.pop(c, None)
        if saem:
            _ctl_gravar()
        return saem


def _ctl(acao: str, chave: str = "", minutos: int = 0):
    """Uma operação do controle, no banco de controle configurado ou no próprio PDA."""
    if _config()["_CONTROLE_LOCAL"]:
        return _ctl_local(acao, chave, minutos)
    if acao == "retirar_reservas":
        return [str(c) for (c,) in (_controle(SQL_RETIRAR_RESERVAS_EXPIRADAS, minutos, buscar="todas") or [])]
    if acao == "limpar_observacoes":
        return _controle(SQL_LIMPAR_OBSERVACOES_EXPIRADAS, minutos)
    if acao == "registrar":
        return bool(_controle(SQL_REGISTRAR_OBSERVACAO, chave, minutos, buscar="escalar"))
    if acao == "reservar":
        return int(_controle(SQL_TENTAR_RESERVAR, chave, minutos, buscar="escalar") or 0)
    if acao == "remover":
        return _controle(SQL_REMOVER_CONTROLE, chave)
    if acao == "resumo":
        return {str(status): int(qtd) for status, qtd in (_controle(SQL_RESUMO_CONTROLE, buscar="todas") or [])}
    raise ValueError(acao)


def resumo_tabela_controle() -> dict:
    return _ctl("resumo")


# ---------------------------------------------------------------------------
# ciclo (Worker.ExecutarCicloAsync)
# ---------------------------------------------------------------------------
_lock_ciclo = threading.Lock()
_lock_estado = threading.Lock()
estado_execucao = {"executando": False, "ultimo_ciclo": None, "proximo_ciclo": None, "ciclo_atual": None}
_acordar = threading.Event()


def _reprocessar(chave: str, cfg: dict, resumo: dict) -> None:
    url = cfg["API_BASE_URL"].rstrip("/") + "/" + urllib.parse.quote(chave, safe="")
    try:
        resposta = requests.post(url, headers={"x-api-key": cfg["API_KEY"]}, timeout=TIMEOUT_API_SEGUNDOS)
        corpo = resposta.text or ""
        if 200 <= resposta.status_code < 300:
            _auditar("sucessos", chave, resposta.status_code, corpo)
            _ctl("remover", chave)
            resumo["sucessos"] += 1
            logger_reprocessamento_cte2.info("Chave %s reprocessada. HTTP %d.", chave, resposta.status_code)
            return
        erro = "A API retornou uma resposta sem sucesso."
        _auditar("erros", chave, resposta.status_code, corpo, erro)
        _registrar_bloqueio(chave, resposta.status_code, f"{erro} {(corpo or '')[:500]}")
        _ctl("remover", chave)
        resumo["erros"] += 1
        nivel = logging.WARNING if resposta.status_code in (429, 503) else logging.ERROR
        logger_reprocessamento_cte2.log(nivel, "API recusou a chave %s. HTTP %d: %s", chave, resposta.status_code, (corpo or "")[:500])
    except requests.Timeout:
        erro = "Tempo limite da requisição excedido."
        _auditar("erros", chave, None, None, erro)
        _registrar_bloqueio(chave, None, erro)
        _ctl("remover", chave)
        resumo["erros"] += 1
        logger_reprocessamento_cte2.error("Tempo esgotado ao reprocessar a chave %s.", chave)
    except requests.RequestException as e:
        _auditar("erros", chave, None, None, str(e))
        _registrar_bloqueio(chave, None, str(e))
        _ctl("remover", chave)
        resumo["erros"] += 1
        logger_reprocessamento_cte2.error("Erro de comunicação ao reprocessar a chave %s: %s", chave, e)


def executar_ciclo(origem: str = "agendado") -> dict:
    """Um ciclo completo. Devolve o resumo (também guardado em estado_execucao)."""
    if not _lock_ciclo.acquire(blocking=False):
        return {"ok": False, "erro": "Já tem um ciclo em andamento."}
    inicio = datetime.now()
    resumo = {"ok": True, "origem": origem, "inicio": inicio.strftime("%d/%m/%Y %H:%M:%S"), "fim": None,
              "candidatos": 0, "aguardando": 0, "resolvidos": 0, "enviados": 0, "sucessos": 0, "erros": 0,
              "reservas_expiradas": 0, "erro": None}
    with _lock_estado:
        estado_execucao["executando"] = True
        estado_execucao["ciclo_atual"] = resumo
    try:
        faltando = config_faltando()
        if faltando:
            raise ConfiguracaoIncompleta("Configuração incompleta: falta " + ", ".join(faltando) + ".")
        cfg = _config()
        _carregar_bloqueadas()

        for chave_expirada in (_ctl("retirar_reservas", minutos=MINUTOS_EXPIRACAO_RESERVA) or []):
            motivo = "Resultado desconhecido: o runner foi interrompido durante o envio. Nova tentativa bloqueada."
            _registrar_bloqueio(str(chave_expirada), None, motivo)
            _auditar("erros", str(chave_expirada), None, None, motivo)
            resumo["reservas_expiradas"] += 1

        _ctl("limpar_observacoes", minutos=MINUTOS_EXPIRACAO_OBSERVACAO)

        chaves = _buscar_candidatos()
        resumo["candidatos"] = len(chaves)
        logger_reprocessamento_cte2.info("%d chave(s) não bloqueadas seguirão para observação.", len(chaves))

        for chave in chaves:
            if origem == "agendado" and not esta_ligado():
                logger_reprocessamento_cte2.info("Pausado no meio do ciclo: as chaves restantes ficam pro próximo.")
                break
            if not _ctl("registrar", chave, MINUTOS_CONFIRMACAO):
                resumo["aguardando"] += 1
                continue
            if not _continua_travado(chave):
                _ctl("remover", chave)
                resumo["resolvidos"] += 1
                logger_reprocessamento_cte2.info("Chave %s foi resolvida pela aplicação antes do envio; API não chamada.", chave)
                continue
            if _ctl("reservar", chave, MINUTOS_CONFIRMACAO) != 1:
                continue
            resumo["enviados"] += 1
            _reprocessar(chave, cfg, resumo)
            if INTERVALO_ENTRE_CHAMADAS_MS > 0:
                time.sleep(INTERVALO_ENTRE_CHAMADAS_MS / 1000)
    except ConfiguracaoIncompleta as e:
        resumo["ok"] = False
        resumo["erro"] = str(e)
        logger_reprocessamento_cte2.warning("Ciclo não rodou: %s", e)
    except Exception as e:
        resumo["ok"] = False
        resumo["erro"] = str(e)
        logger_reprocessamento_cte2.exception("Falha no ciclo de reprocessamento.")
    finally:
        resumo["fim"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resumo["duracao_s"] = round((datetime.now() - inicio).total_seconds(), 1)
        with _lock_estado:
            estado_execucao["executando"] = False
            estado_execucao["ciclo_atual"] = None
            estado_execucao["ultimo_ciclo"] = resumo
        _lock_ciclo.release()
    if origem == "agendado":
        # aviso no Teams só depois de 5 ciclos seguidos com falha (~5 min), pra não avisar por soluço de rede
        registrar_resultado_job("Reprocessamento CTe2", resumo["ok"], resumo["erro"], limite=5)
    return resumo


def iniciar_execucao_manual(usuario: str) -> dict:
    faltando = config_faltando()
    if faltando:
        return {"ok": False, "erro": "Configuração incompleta: falta " + ", ".join(faltando) + "."}
    if _lock_ciclo.locked():
        return {"ok": False, "erro": "Já tem um ciclo em andamento."}
    logger_reprocessamento_cte2.info("Ciclo manual disparado por '%s'.", usuario)
    threading.Thread(target=executar_ciclo, kwargs={"origem": "manual"}, daemon=True).start()
    return {"ok": True}


def status(com_controle: bool = False) -> dict:
    with _lock_estado:
        copia = {k: (dict(v) if isinstance(v, dict) else v) for k, v in estado_execucao.items()}
    persistido = _ler_estado_persistido()
    _carregar_bloqueadas()
    resposta = {
        "ok": True,
        "ligado": bool(persistido.get("ligado")),
        "alterado_por": persistido.get("alterado_por"),
        "alterado_em": persistido.get("alterado_em"),
        "executando": copia["executando"],
        "ciclo_atual": copia["ciclo_atual"],
        "ultimo_ciclo": copia["ultimo_ciclo"],
        "proximo_ciclo": copia["proximo_ciclo"],
        "faltando": config_faltando(),
        "servico_windows": estado_servico_windows(),
        "hoje": {"sucessos": _contar_linhas(_arquivo_auditoria("sucessos")),
                 "erros": _contar_linhas(_arquivo_auditoria("erros"))},
        "bloqueadas": len(_chaves_bloqueadas),
        "intervalo_segundos": INTERVALO_SEGUNDOS,
        "regras": {"limite_por_ciclo": LIMITE_POR_CICLO, "minutos_confirmacao": MINUTOS_CONFIRMACAO,
                   "expiracao_observacao": MINUTOS_EXPIRACAO_OBSERVACAO, "expiracao_reserva": MINUTOS_EXPIRACAO_RESERVA},
        "api": _config()["API_BASE_URL"],
        "desenvolvido_por": DESENVOLVIDO_POR,
        "fonte_origem": _config().get("_FONTE_ORIGEM"),
        "controle_local": _config()["_CONTROLE_LOCAL"],
    }
    if com_controle and not resposta["faltando"]:
        try:
            resposta["controle"] = resumo_tabela_controle()
        except Exception as e:
            resposta["controle_erro"] = str(e)
    return resposta


# ---------------------------------------------------------------------------
# thread do agendamento
# ---------------------------------------------------------------------------
class MonitorReprocessamentoCte2:
    """Roda um ciclo a cada INTERVALO_SEGUNDOS enquanto estiver ligado no card."""

    def __init__(self):
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True, name="reprocessamento_cte2")
        self._thread.start()

    def parar(self) -> None:
        self._stop.set()
        _acordar.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            if esta_ligado():
                executar_ciclo("agendado")
                espera = INTERVALO_SEGUNDOS
            else:
                espera = 5  # desligado: só confere de vez em quando se foi ligado
            with _lock_estado:
                estado_execucao["proximo_ciclo"] = (
                    (datetime.now() + timedelta(seconds=espera)).strftime("%d/%m/%Y %H:%M:%S") if esta_ligado() else None)
            _acordar.wait(espera)
            _acordar.clear()
