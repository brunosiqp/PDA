"""Automanutenção dos logs (3.4.8.0, pedido do Igor: "salvar um limite de linhas por log e o resto zipar, os
arquivos zipados apagar após 30 dias que foi zipado"). Substitui a limpeza da 3.2.1.0, que só apagava log parado
havia 30 dias (e a rotação por tamanho, que jogava fora a cópia mais antiga sem guardar).

1. **Limite de linhas** (`ArquivoDeLogComLimite`, o handler de todos os logs do PDA): cada log guarda até
   `MAX_LINHAS_LOG` (200 mil) linhas. Quando passa, as mais antigas vão pra um zip em `logs/arquivados/` e o log
   continua com as `LINHAS_APOS_CORTE` (100 mil) mais novas, então a tela de Logs nunca fica vazia depois do corte.
   O zip se chama `<log>_<primeiro dia>_a_<último dia>.zip`, com o trecho cortado dentro.
2. **Arquivos de um dia só** (os registros `manutencao_usuarios_*.jsonl`, a auditoria diária do CTe2
   `sucessos-/erros-AAAAMMDD.log` e o histórico diário do LongNameJanitor `AAAA-MM-DD.csv`): parados há mais de
   `DIAS_PARA_ZIPAR` (7) dias, viram `<nome>.zip` na subpasta `arquivados/` da própria pasta e o original sai.
3. **Zips com mais de `DIAS_GUARDAR_ZIPS` (30) dias** desde que foram criados (data de modificação do zip) são
   apagados, em todas as pastas `arquivados/` acima.
Também na manutenção: as cópias da rotação antiga (`*.log.1`, `*.log.2`...) viram zip (uma vez, na primeira
partida) e um `*.log` de `logs/` que não é de nenhum handler (ex.: monitoramento_execucao.log, de um script à
parte) recebe o mesmo limite de linhas e, parado há 30 dias, vai inteiro pro zip.

Roda na partida do PDA e todo dia de madrugada. Nunca mexe em arquivo de estado: ultimo_offset.json,
ultimo_erro.json, dedup_erros_email/, logs/emailpack/, documentos-bloqueados.log, estado.json/controle.json do
CTe2 e os logs da Aplicação Monitoramento (programa externo, só leitura). Nada é apagado sem antes estar num zip.
"""
import logging
import os
import re
import time
import zipfile
from typing import Iterable, List, Optional

logger = logging.getLogger("alertas")

MAX_LINHAS_LOG = 200_000      # limite de cada log (~30 MB no log mais falador, o alertas_suporte.log)
LINHAS_APOS_CORTE = 100_000   # o que fica no log depois de mandar as antigas pro zip
DIAS_PARA_ZIPAR = 7           # arquivo de um dia só, parado há mais que isso, vira zip
DIAS_GUARDAR_ZIPS = 30        # zip apagado depois disso (contado de quando foi zipado)
DIAS_LOG_PARADO = 30          # *.log sem handler parado há mais que isso vai inteiro pro zip
PASTA_ARQUIVADOS = "arquivados"
ESPERA_APOS_FALHA_S = 600     # corte que falhou (zip sem permissão etc.) só tenta de novo depois disso

_RE_LOG = re.compile(r"^.+\.log$", re.I)
_RE_COPIA_ROTACAO = re.compile(r"^.+\.log\.\d+$", re.I)
_RE_JSONL_MANUTENCAO = re.compile(r"^manutencao_usuarios_\d{8}_\d{6}\.jsonl$", re.I)
_RE_AUDITORIA_CTE2 = re.compile(r"^(sucessos|erros)-\d{8}\.log$", re.I)
_RE_HISTORICO_LNJ = re.compile(r"^\d{4}-\d{2}-\d{2}\.csv$", re.I)
_RE_DIA_NA_LINHA = re.compile(rb"^(\d{4}-\d{2}-\d{2})")

# logs abertos pelos handlers deste PDA: a manutenção diária não corta esses (o próprio handler cuida, com a trava dele)
_ARQUIVOS_COM_HANDLER = set()


def _chave(caminho: str) -> str:
    return os.path.normcase(os.path.abspath(caminho))


def contar_linhas(caminho: str) -> int:
    try:
        total, ultimo = 0, b"\n"
        with open(caminho, "rb") as f:
            for bloco in iter(lambda: f.read(1 << 20), b""):
                total += bloco.count(b"\n")
                ultimo = bloco[-1:]
        return total + (0 if ultimo == b"\n" else 1)  # última linha sem \n conta também
    except OSError:
        return 0


def _separar_linhas(dados: bytes) -> List[bytes]:
    if not dados:
        return []
    partes = dados.split(b"\n")
    linhas = [p + b"\n" for p in partes[:-1]]
    if partes[-1]:
        linhas.append(partes[-1])
    return linhas


def _nome_livre(pasta: str, base: str, ext: str = ".zip") -> str:
    caminho, n = os.path.join(pasta, base + ext), 2
    while os.path.exists(caminho):
        caminho, n = os.path.join(pasta, f"{base}_{n}{ext}"), n + 1
    return caminho


def _gravar_zip(destino: str, nome_dentro: str, dados: bytes) -> None:
    """Grava num .tmp e só troca pelo nome final com o zip completo (queda no meio não deixa zip quebrado)."""
    tmp = destino + ".tmp"
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr(nome_dentro, dados)
    os.replace(tmp, destino)


def _pasta_arquivados(pasta: str) -> str:
    destino = os.path.join(pasta, PASTA_ARQUIVADOS)
    os.makedirs(destino, exist_ok=True)
    return destino


def _dia_da_linha(linha: bytes) -> Optional[str]:
    m = _RE_DIA_NA_LINHA.match(linha)
    return m.group(1).decode() if m else None


def cortar_log(caminho: str, max_linhas: int = MAX_LINHAS_LOG, manter: int = LINHAS_APOS_CORTE) -> dict:
    """Se o log passou de `max_linhas`, manda as mais antigas pro zip e deixa as `manter` mais novas.
    O zip é gravado ANTES de reescrever o log: se der erro no meio, nada se perde."""
    with open(caminho, "rb") as f:
        linhas = _separar_linhas(f.read())
    if len(linhas) <= max_linhas:
        return {"cortou": False, "linhas": len(linhas)}
    manter = max(0, min(manter, max_linhas))
    antigas, novas = (linhas[:-manter], linhas[-manter:]) if manter else (linhas, [])
    base = os.path.splitext(os.path.basename(caminho))[0]
    de, ate = _dia_da_linha(antigas[0]), next((d for d in map(_dia_da_linha, reversed(antigas)) if d), None)
    trecho = f"{base}_{de or 'inicio'}_a_{ate or time.strftime('%Y-%m-%d')}"
    destino = _nome_livre(_pasta_arquivados(os.path.dirname(caminho)), trecho)
    _gravar_zip(destino, os.path.basename(destino)[:-4] + ".log", b"".join(antigas))
    with open(caminho, "wb") as f:
        f.writelines(novas)
    return {"cortou": True, "linhas": len(novas), "zipadas": len(antigas), "zip": os.path.basename(destino)}


def zipar_arquivo(caminho: str) -> str:
    """Arquivo inteiro vira `arquivados/<nome>.zip` e o original sai. Devolve o nome do zip."""
    nome = os.path.basename(caminho)
    destino = _nome_livre(_pasta_arquivados(os.path.dirname(caminho)), nome)
    with open(caminho, "rb") as f:
        _gravar_zip(destino, nome, f.read())
    os.remove(caminho)
    return os.path.basename(destino)


class ArquivoDeLogComLimite(logging.FileHandler):
    """FileHandler que conta as linhas gravadas e, passando de `max_linhas`, corta o log (`cortar_log`) antes de
    gravar a próxima. Roda dentro da trava do handler, então duas threads nunca cortam/escrevem ao mesmo tempo."""

    def __init__(self, caminho: str, max_linhas: int = MAX_LINHAS_LOG, manter: int = LINHAS_APOS_CORTE, encoding: str = "utf-8"):
        super().__init__(caminho, mode="a", encoding=encoding)
        self.max_linhas, self.manter = max_linhas, manter
        self.linhas = contar_linhas(self.baseFilename)
        self._nao_cortar_ate = 0.0
        _ARQUIVOS_COM_HANDLER.add(_chave(self.baseFilename))

    def _cortar(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None
        r = None
        try:
            r = cortar_log(self.baseFilename, self.max_linhas, self.manter)
            self.linhas = r["linhas"]
        except Exception as e:  # sem permissão na pasta, disco cheio...: segue gravando e tenta de novo mais tarde
            self.linhas = contar_linhas(self.baseFilename)
            self._nao_cortar_ate = time.time() + ESPERA_APOS_FALHA_S
            print(f"[AVISO] Não deu pra mandar pro zip as linhas antigas de {self.baseFilename}: {e}")
        finally:
            self.stream = self._open()
        if r and r["cortou"]:  # só depois de reabrir: pode ser este mesmo handler que grava o aviso (trava é RLock)
            logger.info("Log %s passou de %d linhas: %d mais antigas foram pro zip %s; ficaram as %d mais novas.",
                        os.path.basename(self.baseFilename), self.max_linhas, r["zipadas"], r["zip"], r["linhas"])

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            n = msg.count("\n") + 1
            if self.linhas + n > self.max_linhas and time.time() >= self._nao_cortar_ate:
                self._cortar()
            if self.stream is None:
                self.stream = self._open()
            self.stream.write(msg + self.terminator)
            self.flush()
            self.linhas += n
        except RecursionError:
            raise
        except Exception:
            self.handleError(record)


def _arquivos(pasta: str, regra) -> Iterable[str]:
    if pasta and os.path.isdir(pasta):
        for nome in os.listdir(pasta):
            caminho = os.path.join(pasta, nome)
            if os.path.isfile(caminho) and regra.match(nome):
                yield caminho


def manter_logs(pasta_logs: str, pasta_cte2: str = "", pasta_historico_lnj: str = "", agora: float = None,
                max_linhas: int = MAX_LINHAS_LOG, manter: int = LINHAS_APOS_CORTE) -> dict:
    """A manutenção do dia (partida + madrugada). Devolve o que fez, também resumido numa linha do log principal."""
    agora = agora if agora is not None else time.time()
    r = {"cortados": [], "zipados": [], "zips_apagados": [], "erros": [], "bytes_liberados": 0}

    def tentar(nome: str, acao) -> None:
        try:
            acao()
        except Exception as e:
            r["erros"].append(f"{nome} ({e.__class__.__name__})")

    # 1. cópias da rotação antiga (até a 3.4.7.0) e *.log que não são de handler deste PDA
    for caminho in _arquivos(pasta_logs, _RE_COPIA_ROTACAO):
        tentar(os.path.basename(caminho), lambda c=caminho: r["zipados"].append(zipar_arquivo(c)))
    for caminho in _arquivos(pasta_logs, _RE_LOG):
        if _chave(caminho) in _ARQUIVOS_COM_HANDLER:
            continue

        def cuidar(c=caminho):
            if agora - os.path.getmtime(c) > DIAS_LOG_PARADO * 86400:
                r["zipados"].append(zipar_arquivo(c))
                return
            res = cortar_log(c, max_linhas, manter)
            if res["cortou"]:
                r["cortados"].append(f"{os.path.basename(c)} -> {res['zip']}")
        tentar(os.path.basename(caminho), cuidar)

    # 2. arquivos de um dia só, parados há mais de DIAS_PARA_ZIPAR dias
    for pasta, regra in ((pasta_logs, _RE_JSONL_MANUTENCAO), (pasta_cte2, _RE_AUDITORIA_CTE2), (pasta_historico_lnj, _RE_HISTORICO_LNJ)):
        for caminho in _arquivos(pasta, regra):
            try:
                parado = agora - os.path.getmtime(caminho) > DIAS_PARA_ZIPAR * 86400
            except OSError:
                continue
            if parado:
                tentar(os.path.basename(caminho), lambda c=caminho: r["zipados"].append(zipar_arquivo(c)))

    # 3. zips com mais de DIAS_GUARDAR_ZIPS dias desde que foram feitos (e .tmp de zip que caiu no meio)
    for pasta in (pasta_logs, pasta_cte2, pasta_historico_lnj):
        arquivados = os.path.join(pasta, PASTA_ARQUIVADOS) if pasta else ""
        for caminho in _arquivos(arquivados, re.compile(r"^.+\.zip(\.tmp)?$", re.I)):
            try:
                info = os.stat(caminho)
                velho = agora - info.st_mtime > (DIAS_GUARDAR_ZIPS * 86400 if caminho.lower().endswith(".zip") else 86400)
                if velho:
                    os.remove(caminho)
                    r["zips_apagados"].append(os.path.basename(caminho))
                    r["bytes_liberados"] += info.st_size
            except OSError as e:
                r["erros"].append(f"{os.path.basename(caminho)} ({e.__class__.__name__})")

    if any(r[k] for k in ("cortados", "zipados", "zips_apagados", "erros")):
        logger.info("Manutenção dos logs: %d cortado(s), %d arquivo(s) zipado(s), %d zip(s) com mais de %d dias apagado(s) "
                    "(%.1f MB), %d com erro. %s", len(r["cortados"]), len(r["zipados"]), len(r["zips_apagados"]),
                    DIAS_GUARDAR_ZIPS, r["bytes_liberados"] / (1024 * 1024), len(r["erros"]),
                    "; ".join(r["cortados"] + r["zipados"] + r["zips_apagados"] + r["erros"])[:1500])
    return r


def resumo_arquivados(*pastas: str) -> dict:
    """Quantos zips e quanto ocupam (pra tela de Logs)."""
    qtd, total = 0, 0
    for pasta in pastas:
        for caminho in _arquivos(os.path.join(pasta, PASTA_ARQUIVADOS) if pasta else "", re.compile(r"^.+\.zip$", re.I)):
            try:
                total += os.path.getsize(caminho)
                qtd += 1
            except OSError:
                pass
    return {"zips": qtd, "bytes": total}
