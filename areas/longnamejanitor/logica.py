"""LongNameJanitor ClienteQ (beta, 3.3.2.0): vigia pastas e apaga (ou move) arquivos com nome longo e NF repetida.

Trazido do serviço do Windows em C# (LongNameJanitor.exe, painel na porta 5080) que o Igor mandou em 07/10/2026.
Veio só o .exe compilado (sem o código-fonte); a regra abaixo foi montada a partir das mensagens, dos campos do
/api/status e da configuração do próprio programa:
- a cada `rescan_segundos` (padrão 2 s, como o serviço; 3.3.3.0, antes era em minutos), cada pasta (com ou sem
  subpastas) é varrida;
- arquivo que não tem nenhum dos textos de `contem` (ex.: o CNPJ) fica ("sem o texto");
- tem o texto e o nome passa de `max_nome` caracteres (contando a extensão se `conta_extensao`): vai pra ação da
  pasta, apagar ou mover pra `mover_para` (com data e hora no nome se já existir um igual), motivo
  "nome com N+ caracteres";
- com `nf_duplicada`, o número da NF sai do nome pelo `nf_padrao` (ex.: ^NF0*(\\d+)_): NF já vista nos últimos
  `nf_cache_dias` em outro arquivo da pasta vira **só um aviso** no monitor ("NF X repetida (primeiro: arquivo)") e o
  arquivo fica (3.3.5.0; antes ia pra ação); a primeira vez só entra no cache;
- senão fica ("nome curto");
- **pasta de processados** (3.3.5.0, `processado`, ex.: ...\\CaixaSaida\\Processado): em toda varredura, a pasta do dia
  (`processado\\AAAA\\MM\\DD`, e a de ontem, pra não perder o que chegou perto da meia-noite) é olhada e TODO arquivo
  com um texto de `contem` (o CNPJ) vai pra ação, sem olhar tamanho do nome nem NF. Pasta do dia que ainda não existe
  não é erro;
- arquivo em uso fica pra próxima varredura; sem permissão conta como erro; pasta inacessível tenta de novo.

Diferenças do serviço (de propósito, como no Reprocessamento CTe2): **começa pausado e em modo simulação** (mostra o
que seria apagado/movido sem mexer em nada), não liga se o serviço do Windows LongNameJanitor estiver rodando nesta
máquina, e só administrador liga, tira da simulação, roda uma varredura ou muda as pastas.

Dados em longnamejanitor/ ao lado do programa (fora do git): config.json, estado.json (ligado), stats.json,
nf-cache.json e historico/AAAA-MM-DD.csv (mesmo formato do serviço: data_hora;acao;arquivo;pasta;detalhe).

Varrendo a cada 2 s (3.3.3.0), nada pode se repetir a cada volta: em simulação cada arquivo é registrado uma vez só
(`_ja_simulados`), "arquivo em uso" e "sem acesso" vão pro log só quando mudam, o nf-cache só é gravado quando muda e
o stats.json quando algo foi feito/simulado/falhou ou a cada `GRAVAR_STATS_A_CADA` segundos. Os números "verificados"
de hoje contam cada arquivo uma vez por varredura (como o serviço), então crescem rápido.
"""
import io
import json
import logging
import os
import re
import shutil
import subprocess
import threading
import time
import zipfile
from collections import deque
from datetime import date, datetime, timedelta
from typing import Optional

from nucleo.caminhos import base_path_app as _base_path_app

logger = logging.getLogger("alertas.longnamejanitor")

NOME_SERVICO_WINDOWS = "LongNameJanitor"
ACOES = ("apagar", "mover")
MAX_PASTAS = 30
MAX_ATIVIDADE = 300
RESCAN_MIN_S, RESCAN_MAX_S = 1, 3600
GRAVAR_STATS_A_CADA = 60  # segundos: sem nada feito, o stats.json não precisa ser gravado a cada 2 s

# a configuração que o serviço usa hoje (appsettings.local.json de 07/10/2026), já em modo simulação
CONFIG_PADRAO = {
    "rescan_segundos": 2,
    "nf_cache_dias": 30,
    "simulacao": True,
    "pastas": [{
        "caminho": r"\\192.0.2.71\clientsaas\nfe\Integracao\CaixaSaida\Processar",
        "acao": "apagar", "mover_para": "", "max_nome": 35, "conta_extensao": True,
        "contem": ["9344831097451"], "subpastas": False, "nf_duplicada": True, "nf_padrao": r"^NF0*(\d+)_",
        "processado": r"\\192.0.2.71\clientsaas\nfe\Integracao\CaixaSaida\Processado",
        "simulacao": False,
    }],
}

_lock = threading.Lock()
_acordar = threading.Event()
_cache_servico = {"quando": 0.0, "estado": None}
estado_execucao = {"executando": False, "ultima_varredura": None, "proxima": None, "ultimo_resultado": None}
estado_pastas: dict = {}  # caminho -> {estado, desde, ultima_varredura, erro, tentar_em, verificados, feitos}
atividade: deque = deque(maxlen=MAX_ATIVIDADE)
_ja_simulados: set = set()   # (caminho do arquivo, motivo) já registrados em simulação; zera ao mudar config/simulação
_ja_avisados: set = set()    # (caminho do arquivo, motivo) de NF repetida já avisados (o arquivo fica, então voltaria toda varredura)
LIMITE_LEMBRADOS = 50000     # os dois conjuntos acima zeram se passarem disso (só faria registrar de novo)
_em_uso_avisados: set = set()  # arquivos travados já avisados no log
_stats_gravado = {"quando": 0.0}
_stats_memoria: dict = {}


# ---------------------------------------------------------------------------------------------------- arquivos
def pasta_dados() -> str:
    pasta = os.path.join(_base_path_app(), "longnamejanitor")
    os.makedirs(os.path.join(pasta, "historico"), exist_ok=True)
    return pasta


def _ler(nome: str, padrao):
    caminho = os.path.join(pasta_dados(), nome)
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return padrao
    except Exception:
        logger.exception("Não deu pra ler %s; começando do zero (cópia em .bad).", caminho)
        try:
            shutil.copy(caminho, caminho + ".bad")
        except OSError:
            pass
        return padrao


def _gravar(nome: str, dados) -> bool:
    caminho = os.path.join(pasta_dados(), nome)
    try:
        with open(caminho + ".tmp", "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=1)
        os.replace(caminho + ".tmp", caminho)
        return True
    except Exception:
        logger.exception("Não deu pra salvar %s.", caminho)
        return False


# 3.4.5.0 (pedido do Igor): o que cada pasta faz é escolhido nas caixinhas do editor
# - processar_ativo: limpar a pasta vigiada (Processar); dentro dela, regra_nome_longo (apagar/mover nome longo) e
#   nf_duplicada (avisar NF repetida, que já existia);
# - processado_auto: manutenção automática da pasta de processados do dia (mover pra LongNameJanitor) e processado_ontem
#   (olhar também a do dia anterior). O botão "Mover tudo do Processado" funciona independente delas.
CHAVES_LIGADAS_POR_PADRAO = ("processar_ativo", "regra_nome_longo", "processado_auto", "processado_ontem")


def config() -> dict:
    cfg = _ler("config.json", None)
    if not isinstance(cfg, dict):
        cfg = json.loads(json.dumps(CONFIG_PADRAO))
    # 3.3.3.0: o intervalo passou de minutos pra segundos; config antiga (rescan_minutos) vai pro padrão de 2 s
    cfg.pop("rescan_minutos", None)
    for k, v in CONFIG_PADRAO.items():
        if k != "pastas":
            cfg.setdefault(k, v)
    cfg.setdefault("pastas", [])
    for p in cfg["pastas"]:
        if isinstance(p, dict):
            # 3.4.5.0: o que cada pasta faz vira caixinha; config de antes = tudo ligado, como funcionava
            for chave in CHAVES_LIGADAS_POR_PADRAO:
                p.setdefault(chave, True)
        if isinstance(p, dict) and "processado" not in p:
            # 3.3.5.0: config de antes, a pasta de processados é a irmã da "Processar" (CaixaSaida\Processado)
            cam = str(p.get("caminho") or "").rstrip("\\")
            p["processado"] = cam[:-len("Processar")] + "Processado" if cam.lower().endswith("\\processar") else ""
    return cfg


def esta_ligado() -> bool:
    return bool(_ler("estado.json", {}).get("ligado"))


def estado_servico_windows() -> Optional[str]:
    """RUNNING/STOPPED/... do serviço em C# nesta máquina (None se não existir). No máximo a cada 30 s."""
    if os.name != "nt":
        return None
    if time.time() - _cache_servico["quando"] < 30:
        return _cache_servico["estado"]
    estado = None
    try:
        saida = subprocess.run(["sc", "query", NOME_SERVICO_WINDOWS], capture_output=True, timeout=10,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        texto = (saida or b"").decode("cp850", errors="replace")  # o sc.exe responde na página de código do console
        m = re.search(r"STATE\s*:\s*\d+\s+(\w+)", texto)
        estado = m.group(1) if m else None
    except Exception:
        estado = None
    _cache_servico.update(quando=time.time(), estado=estado)
    return estado


# ---------------------------------------------------------------------------------------------------- validação
_RE_CAMINHO = re.compile(r"^(\\\\[^\\/:*?\"<>|\r\n]+\\[^:*?\"<>|\r\n]+|[A-Za-z]:\\[^:*?\"<>|\r\n]*)$")


def _validar_pasta(p: dict, n: int) -> dict:
    if not isinstance(p, dict):
        raise ValueError(f"pasta {n} inválida")
    caminho = str(p.get("caminho") or "").strip().rstrip("\\")
    if not _RE_CAMINHO.match(caminho):
        raise ValueError(f"pasta {n}: caminho inválido (use \\\\servidor\\compartilhamento\\... ou C:\\...)")
    acao = str(p.get("acao") or "apagar").strip()
    if acao not in ACOES:
        raise ValueError(f"pasta {n}: ação tem que ser apagar ou mover")
    mover_para = str(p.get("mover_para") or "").strip().rstrip("\\")
    if acao == "mover" and not _RE_CAMINHO.match(mover_para):
        raise ValueError(f"pasta {n}: mover precisa de uma pasta de destino válida")
    if acao == "mover" and os.path.normcase(mover_para) == os.path.normcase(caminho):
        raise ValueError(f"pasta {n}: o destino não pode ser a própria pasta")
    try:
        max_nome = int(p.get("max_nome"))
    except (TypeError, ValueError):
        raise ValueError(f"pasta {n}: tamanho máximo do nome inválido")
    if not 10 <= max_nome <= 250:
        raise ValueError(f"pasta {n}: tamanho máximo do nome entre 10 e 250")
    contem = [str(t).strip() for t in (p.get("contem") or []) if str(t).strip()]
    if not contem:
        # sem texto obrigatório, qualquer arquivo com nome longo seria apagado: perigoso demais pra deixar sem querer
        raise ValueError(f"pasta {n}: informe pelo menos um texto que o nome precisa ter (ex.: o CNPJ)")
    padrao = str(p.get("nf_padrao") or r"^NF0*(\d+)_").strip()
    try:
        if re.compile(padrao).groups < 1:
            raise ValueError
    except (re.error, ValueError):
        raise ValueError(f"pasta {n}: padrão da NF inválido (precisa de um grupo, ex.: ^NF0*(\\d+)_)")
    processado = str(p.get("processado") or "").strip().rstrip("\\")
    if processado and not _RE_CAMINHO.match(processado):
        raise ValueError(f"pasta {n}: pasta de processados inválida (use \\\\servidor\\compartilhamento\\... ou C:\\...)")
    if processado and os.path.normcase(processado) == os.path.normcase(caminho):
        raise ValueError(f"pasta {n}: a pasta de processados não pode ser a própria pasta vigiada")
    return {"caminho": caminho, "acao": acao, "mover_para": mover_para if acao == "mover" else "", "max_nome": max_nome, "processado": processado,
            "conta_extensao": bool(p.get("conta_extensao", True)), "contem": contem[:10], "subpastas": bool(p.get("subpastas")),
            "nf_duplicada": bool(p.get("nf_duplicada")), "nf_padrao": padrao, "simulacao": bool(p.get("simulacao")),
            **{chave: bool(p.get(chave, True)) for chave in CHAVES_LIGADAS_POR_PADRAO}}


def salvar_config(dados: dict, usuario: str) -> dict:
    try:
        if not isinstance(dados, dict):
            raise ValueError("configuração inválida")
        pastas = dados.get("pastas") or []
        if not isinstance(pastas, list) or len(pastas) > MAX_PASTAS:
            raise ValueError(f"até {MAX_PASTAS} pastas")
        limpas = [_validar_pasta(p, n) for n, p in enumerate(pastas, 1)]
        caminhos = [os.path.normcase(p["caminho"]) for p in limpas]
        if len(set(caminhos)) != len(caminhos):
            raise ValueError("tem pasta repetida")
        rescan = dados.get("rescan_segundos")
        rescan = 2 if rescan in (None, "") else int(rescan)  # 0 digitado é recusado abaixo, não vira o padrão
        cache_dias = int(dados.get("nf_cache_dias") or 30)
        if not RESCAN_MIN_S <= rescan <= RESCAN_MAX_S or not 1 <= cache_dias <= 365:
            raise ValueError(f"varredura de {RESCAN_MIN_S} a {RESCAN_MAX_S} segundos e cache de NF de 1 a 365 dias")
    except (ValueError, TypeError) as e:
        return {"ok": False, "erro": str(e)}
    cfg = config()
    cfg.update({"pastas": limpas, "rescan_segundos": rescan, "nf_cache_dias": cache_dias})
    if not _gravar("config.json", cfg):
        return {"ok": False, "erro": "não deu pra salvar (detalhes no log)"}
    _ja_simulados.clear()  # regra nova: o que seria feito pode ter mudado, então registra de novo
    _ja_avisados.clear()
    logger.info("Configuração do LongNameJanitor alterada por %s: %d pasta(s).", usuario, len(limpas))
    _acordar.set()
    return {"ok": True}


def definir_simulacao(simulacao: bool, usuario: str) -> dict:
    cfg = config()
    cfg["simulacao"] = bool(simulacao)
    if not _gravar("config.json", cfg):
        return {"ok": False, "erro": "não deu pra salvar (detalhes no log)"}
    _ja_simulados.clear()
    logger.info("LongNameJanitor %s por %s.", "em modo simulação" if simulacao else "APAGANDO DE VERDADE (simulação desligada)", usuario)
    return {"ok": True}


def definir_ligado(ligado: bool, usuario: str) -> dict:
    if ligado and estado_servico_windows() == "RUNNING":
        return {"ok": False, "erro": "o serviço do Windows LongNameJanitor está rodando nesta máquina: pare ele antes, pra não rodarem os dois"}
    if ligado and not config()["pastas"]:
        return {"ok": False, "erro": "cadastre pelo menos uma pasta antes de ligar"}
    if not _gravar("estado.json", {"ligado": bool(ligado), "alterado_por": usuario,
                                   "alterado_em": datetime.now().strftime("%d/%m/%Y %H:%M:%S")}):
        return {"ok": False, "erro": "não deu pra salvar (detalhes no log)"}
    logger.info("LongNameJanitor %s por %s.", "ligado" if ligado else "pausado", usuario)
    _acordar.set()
    return {"ok": True}


# ---------------------------------------------------------------------------------------------------- regra
def _nf_repetida(nome: str, pasta: dict, cache_nf: dict):
    """(numero, primeiro_arquivo) se a NF desse nome já foi vista em OUTRO arquivo da pasta; (numero, None) se é a primeira
    vez; (None, None) se o nome não tem NF pelo padrão. O número é comparado sem zeros à esquerda (NF000123 = NF123)."""
    m = re.search(pasta["nf_padrao"], nome)
    if not m:
        return None, None
    numero = (m.group(1) or "").lstrip("0") or "0"
    primeiro = cache_nf.get(os.path.normcase(pasta["caminho"]) + "|" + numero)
    if primeiro and primeiro.get("arquivo") != nome:
        return numero, primeiro.get("arquivo")
    return numero, None


def decidir(nome: str, pasta: dict, cache_nf: dict, caminho_arquivo: str, agora: datetime) -> tuple:
    """(acao_ou_None, motivo, tipo): tipo = longo | duplicada | longo_duplicada | curto | sem_texto.

    3.3.5.0: NF repetida sozinha não vai mais pra ação: volta (None, motivo, "duplicada") e a varredura só avisa.

    3.3.4.1: as duas regras são olhadas sempre e o motivo diz cada uma que bateu ("nome com 36+ caracteres",
    "NF 123 repetida (primeiro: arquivo)" ou as duas juntas). Antes o nome longo era checado primeiro e a NF nem era
    olhada, então todo arquivo longo saía só como "nome com 36+" mesmo sendo NF repetida.
    O cache de NF só guarda arquivo que FICA na pasta: um arquivo que vai ser apagado/movido (por nome longo) não vira
    o "primeiro" da NF, senão a cópia boa que chegasse depois seria apagada como repetida e não sobraria nenhuma.
    Separado da varredura pra dar pra testar sem disco."""
    if not any(t in nome for t in pasta["contem"]):
        return None, "", "sem_texto"
    base = nome if pasta["conta_extensao"] else os.path.splitext(nome)[0]
    longo = pasta.get("regra_nome_longo", True) and len(base) > pasta["max_nome"]
    numero, primeiro = _nf_repetida(nome, pasta, cache_nf) if pasta["nf_duplicada"] else (None, None)
    repetida = f"NF {numero} repetida (primeiro: {primeiro})" if primeiro else ""
    if longo:
        motivo = f"nome com {pasta['max_nome'] + 1}+ caracteres" + (" e " + repetida if repetida else "")
        return pasta["acao"], motivo, "longo_duplicada" if repetida else "longo"
    if repetida:  # o arquivo fica (não entra no cache: o "primeiro" continua sendo o de antes)
        return None, repetida, "duplicada"
    if numero is not None:  # primeira vez dessa NF e o arquivo fica: ele vira o "primeiro"
        cache_nf[os.path.normcase(pasta["caminho"]) + "|" + numero] = {"arquivo": nome, "em": agora.strftime("%Y-%m-%d %H:%M:%S")}
    return None, "", "curto"


def _limpar_cache(cache_nf: dict, dias: int, agora: datetime) -> dict:
    corte = (agora - timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    return {k: v for k, v in cache_nf.items() if isinstance(v, dict) and (v.get("em") or "") >= corte}


def _historico(agora: datetime, acao: str, arquivo: str, pasta: str, detalhe: str) -> None:
    caminho = os.path.join(pasta_dados(), "historico", agora.strftime("%Y-%m-%d") + ".csv")
    novo = not os.path.exists(caminho)
    try:
        with open(caminho, "a", encoding="utf-8-sig" if novo else "utf-8", newline="") as f:
            if novo:
                f.write("data_hora;acao;arquivo;pasta;detalhe\r\n")
            limpa = lambda s: str(s).replace(";", ",").replace("\r", " ").replace("\n", " ")
            f.write(";".join(limpa(x) for x in (agora.strftime("%Y-%m-%d %H:%M:%S"), acao, arquivo, pasta, detalhe)) + "\r\n")
    except Exception:
        logger.exception("Não deu pra gravar o histórico em %s.", caminho)


def _registrar(agora: datetime, tipo: str, arquivo: str, pasta: str, detalhe: str, motivo: str = "") -> None:
    atividade.appendleft({"quando": agora.strftime("%Y-%m-%d %H:%M:%S"), "tipo": tipo, "arquivo": arquivo, "pasta": pasta,
                          "detalhe": detalhe, "motivo": motivo})
    nomes = {"apagado": "Apagado", "movido": "Movido", "simulado": "Simulado", "falha": "Falha", "aviso": "Aviso"}
    _historico(agora, nomes.get(tipo, tipo), arquivo, pasta, " · ".join(x for x in (motivo, detalhe) if x))


def _destino_livre(pasta_destino: str, nome: str, agora: datetime) -> str:
    destino = os.path.join(pasta_destino, nome)
    if not os.path.exists(destino):
        return destino
    raiz, ext = os.path.splitext(nome)
    return os.path.join(pasta_destino, f"{raiz}_{agora.strftime('%Y%m%d_%H%M%S%f')[:-3]}{ext}")


def _arquivos(pasta: dict):
    """Arquivos da pasta do mais antigo pro mais novo (3.3.4.1): com duas cópias da mesma NF na mesma varredura, quem
    fica é a que chegou primeiro e a mais nova é a repetida (antes a ordem era a do disco, qualquer uma podia ficar)."""
    achados = []

    def juntar(caminho):
        with os.scandir(caminho) as it:
            for e in it:
                try:
                    if e.is_file():
                        achados.append((e.stat().st_mtime, caminho, e.name))
                    elif pasta["subpastas"] and e.is_dir():
                        juntar(e.path)
                except OSError:
                    continue  # sumiu no meio da listagem
    juntar(pasta["caminho"])
    achados.sort()
    for _, raiz, nome in achados:
        yield raiz, nome


RESULTADO_VAZIO = {"verificados": 0, "feitos": 0, "simulados": 0, "duplicadas": 0, "erros": 0, "curtos": 0, "sem_texto": 0,
                   "processados": 0}


def _lembrar(conjunto: set, chave) -> bool:
    """True se é a primeira vez dessa chave (e guarda); varrendo a cada 2 s, o mesmo arquivo voltaria toda volta."""
    if chave in conjunto:
        return False
    if len(conjunto) >= LIMITE_LEMBRADOS:
        conjunto.clear()
    conjunto.add(chave)
    return True


def _aplicar(acao: str, raiz: str, nome: str, pasta: dict, motivo: str, simulacao: bool, res: dict, agora: datetime) -> bool:
    """Apaga/move (ou simula) um arquivo e registra. True se fez ou simulou agora."""
    origem = os.path.join(raiz, nome)
    if simulacao:
        if not _lembrar(_ja_simulados, (os.path.normcase(origem), motivo)):
            return False
        res["simulados"] += 1
        _registrar(agora, "simulado", nome, raiz, "seria apagado" if acao == "apagar" else "seria movido para " + pasta["mover_para"], motivo)
        return True
    try:
        if acao == "apagar":
            os.remove(origem)
            _registrar(agora, "apagado", nome, raiz, "", motivo)
            logger.info("Apagado (%s): %s", motivo, origem)
        else:
            destino = _destino_livre(pasta["mover_para"], nome, agora)
            shutil.move(origem, destino)
            _registrar(agora, "movido", nome, raiz, "-> " + destino, motivo)
            logger.info("Movido (%s): %s -> %s", motivo, origem, destino)
        res["feitos"] += 1
        _em_uso_avisados.discard(origem)
        return True
    except PermissionError as e:
        em_uso = getattr(e, "winerror", None) == 32
        if em_uso:  # arquivo em uso: fica pra próxima varredura, sem contar como erro (avisa no log uma vez)
            if origem not in _em_uso_avisados:
                _em_uso_avisados.add(origem)
                logger.info("Ainda travado, fica pra próxima varredura: %s", origem)
            return False
        res["erros"] += 1
        _registrar(agora, "falha", nome, raiz, "sem permissão", motivo)
        logger.warning("Sem permissão: %s", origem)
    except FileNotFoundError:
        return False  # sumiu entre a listagem e a ação (outro processo pegou)
    except OSError as e:
        res["erros"] += 1
        _registrar(agora, "falha", nome, raiz, str(e)[:200], motivo)
        logger.warning("Falha em %s: %s", origem, e)
    return False


def varrer_pasta(pasta: dict, cfg: dict, cache_nf: dict, stats: dict, agora: datetime) -> dict:
    simulacao = cfg.get("simulacao", True) or pasta.get("simulacao")
    res = dict(RESULTADO_VAZIO)
    if not pasta.get("processar_ativo", True):  # 3.4.5.0: limpeza da Processar desligada nas caixinhas
        return res
    for raiz, nome in _arquivos(pasta):
        res["verificados"] += 1
        acao, motivo, tipo = decidir(nome, pasta, cache_nf, os.path.join(raiz, nome), agora)
        if tipo == "duplicada":  # 3.3.5.0: NF repetida só avisa no monitor, uma vez por arquivo; o arquivo fica
            if _lembrar(_ja_avisados, (os.path.normcase(os.path.join(raiz, nome)), motivo)):
                res["duplicadas"] += 1
                _registrar(agora, "aviso", nome, raiz, "ficou na pasta (só aviso)", motivo)
            continue
        if acao is None:
            res["curtos" if tipo == "curto" else "sem_texto"] += 1
            continue
        _aplicar(acao, raiz, nome, pasta, motivo, simulacao, res, agora)
    return res


def pastas_do_dia_processado(pasta: dict, agora: datetime) -> list:
    """processado\\AAAA\\MM\\DD de hoje e de ontem (o que chega perto da meia-noite cai na pasta do dia anterior)."""
    base = pasta.get("processado") or ""
    if not base:
        return []
    dias = (agora, agora - timedelta(days=1)) if pasta.get("processado_ontem", True) else (agora,)
    return [os.path.join(base, d.strftime("%Y"), d.strftime("%m"), d.strftime("%d")) for d in dias]


PASTA_MOVIDOS_PROCESSADO = "LongNameJanitor"  # 3.3.9.6: subpasta na raiz do Processado que recebe os arquivos do CNPJ


def _mover_substituindo(raiz: str, nome: str, destino_pasta: str, motivo: str, simulacao: bool, res: dict, agora: datetime) -> bool:
    """Move pra `destino_pasta`, substituindo o arquivo de mesmo nome se já estiver lá (pedido do Igor, 3.3.9.6).
    True se moveu ou simulou agora; arquivo em uso fica pra próxima varredura, como no _aplicar."""
    origem = os.path.join(raiz, nome)
    destino = os.path.join(destino_pasta, nome)
    if simulacao:
        if not _lembrar(_ja_simulados, (os.path.normcase(origem), motivo)):
            return False
        res["simulados"] += 1
        _registrar(agora, "simulado", nome, raiz, "seria movido para " + destino_pasta + " (substitui se já existir)", motivo)
        return True
    try:
        os.makedirs(destino_pasta, exist_ok=True)
        substituiu = os.path.exists(destino)
        try:
            os.replace(origem, destino)  # mesma unidade/compartilhamento: troca de uma vez, já substituindo
        except OSError as e:
            if getattr(e, "winerror", None) != 17:  # 17 = outra unidade; o resto (em uso, permissão) trata embaixo
                raise
            if substituiu:
                os.remove(destino)
            shutil.move(origem, destino)
        _registrar(agora, "movido", nome, raiz, "-> " + destino + (" (substituiu o que estava lá)" if substituiu else ""), motivo)
        logger.info("Movido (%s): %s -> %s%s", motivo, origem, destino, " (substituído)" if substituiu else "")
        res["feitos"] += 1
        _em_uso_avisados.discard(origem)
        return True
    except PermissionError as e:
        if getattr(e, "winerror", None) == 32:
            if origem not in _em_uso_avisados:
                _em_uso_avisados.add(origem)
                logger.info("Ainda travado, fica pra próxima varredura: %s", origem)
            return False
        res["erros"] += 1
        _registrar(agora, "falha", nome, raiz, "sem permissão", motivo)
        logger.warning("Sem permissão: %s", origem)
    except FileNotFoundError:
        return False
    except OSError as e:
        res["erros"] += 1
        _registrar(agora, "falha", nome, raiz, str(e)[:200], motivo)
        logger.warning("Falha em %s: %s", origem, e)
    return False


def varrer_processado(pasta: dict, cfg: dict, agora: datetime) -> dict:
    """3.3.5.0: na pasta de processados do dia, TODO arquivo com o texto de `contem` (o CNPJ) sai de lá. Desde a 3.3.9.6
    vai pra `processado\\LongNameJanitor` (raiz do Processado, substituindo se já existir) em vez de seguir a ação da pasta.
    Pasta do dia que ainda não existe não conta; sem acesso levanta OSError (quem chama mostra no estado da pasta)."""
    simulacao = cfg.get("simulacao", True) or pasta.get("simulacao")
    res = dict(RESULTADO_VAZIO)
    destino_pasta = os.path.join(pasta["processado"], PASTA_MOVIDOS_PROCESSADO)
    for dia_pasta in pastas_do_dia_processado(pasta, agora):
        try:
            with os.scandir(dia_pasta) as it:
                nomes = sorted(e.name for e in it if e.is_file())
        except FileNotFoundError:
            continue
        rel = os.path.join(*dia_pasta.rstrip("\\").split("\\")[-3:]) if "\\" in dia_pasta else dia_pasta
        for nome in nomes:
            res["verificados"] += 1
            if not any(t in nome for t in pasta["contem"]):
                res["sem_texto"] += 1
                continue
            motivo = f"processado do CNPJ ({rel})"
            if _mover_substituindo(dia_pasta, nome, destino_pasta, motivo, simulacao, res, agora):
                res["processados"] += 1
    return res


# "Mover tudo do Processado" (3.3.9.6): botão que percorre TODAS as pastas e subpastas da pasta de processados (não só a
# do dia) e move pra LongNameJanitor, substituindo, todo arquivo com o texto de `contem`. Roda numa thread (pode ser o
# arquivo de anos num compartilhamento de rede); respeita a simulação; o progresso vai pro status (`mover_tudo`).
estado_mover_tudo = {"rodando": False, "por": "", "inicio": None, "fim": None, "simulacao": True,
                     "pastas": 0, "verificados": 0, "movidos": 0, "simulados": 0, "erros": 0, "erro": ""}


def _rodar_mover_tudo(pastas: list, cfg: dict) -> None:
    agora = datetime.now()
    try:
        for pasta in pastas:
            simulacao = cfg.get("simulacao", True) or pasta.get("simulacao")
            base = pasta["processado"]
            destino_pasta = os.path.join(base, PASTA_MOVIDOS_PROCESSADO)
            if not os.path.isdir(base):
                raise OSError(f"pasta de processados inacessível: {base}")
            for raiz, subpastas, arquivos in os.walk(base):
                # a própria pasta LongNameJanitor não entra (senão mexeria no que já foi movido)
                subpastas[:] = [d for d in subpastas if os.path.normcase(os.path.join(raiz, d)) != os.path.normcase(destino_pasta)]
                estado_mover_tudo["pastas"] += 1
                rel = os.path.relpath(raiz, base)
                for nome in sorted(arquivos):
                    estado_mover_tudo["verificados"] += 1
                    if not any(t in nome for t in pasta["contem"]):
                        continue
                    res = dict(RESULTADO_VAZIO)
                    _mover_substituindo(raiz, nome, destino_pasta, f"processado do CNPJ (mover tudo: {rel})", simulacao, res, agora)
                    estado_mover_tudo["movidos"] += res["feitos"]
                    estado_mover_tudo["simulados"] += res["simulados"]
                    estado_mover_tudo["erros"] += res["erros"]
    except Exception as e:
        logger.exception("Mover tudo do Processado parou")
        estado_mover_tudo["erro"] = str(e)[:300]
    finally:
        estado_mover_tudo["rodando"] = False
        estado_mover_tudo["fim"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        logger.info("Mover tudo do Processado (%s) terminou: %d pasta(s), %d arquivo(s) verificados, %d %s, %d erro(s).",
                    estado_mover_tudo["por"], estado_mover_tudo["pastas"], estado_mover_tudo["verificados"],
                    estado_mover_tudo["movidos"] or estado_mover_tudo["simulados"],
                    "movido(s)" if estado_mover_tudo["movidos"] else "simulado(s)", estado_mover_tudo["erros"])


def mover_tudo_do_processado(usuario: str) -> dict:
    cfg = config()
    pastas = [p for p in cfg["pastas"] if p.get("processado")]
    if not pastas:
        return {"ok": False, "erro": "nenhuma pasta com pasta de processados cadastrada"}
    with _lock:
        if estado_mover_tudo["rodando"]:
            return {"ok": False, "erro": "já está movendo tudo do Processado; espere terminar"}
        estado_mover_tudo.update(rodando=True, por=usuario, inicio=datetime.now().strftime("%d/%m/%Y %H:%M:%S"), fim=None,
                                 simulacao=bool(cfg.get("simulacao", True) or any(p.get("simulacao") for p in pastas)),
                                 pastas=0, verificados=0, movidos=0, simulados=0, erros=0, erro="")
    logger.info("Mover tudo do Processado pedido por %s (%s).", usuario, "simulação" if estado_mover_tudo["simulacao"] else "movendo de verdade")
    threading.Thread(target=_rodar_mover_tudo, args=(pastas, cfg), daemon=True, name="longnamejanitor_mover_tudo").start()
    return {"ok": True}


def executar_varredura(origem: str = "agendado") -> dict:
    """Uma varredura de todas as pastas. Nunca levanta exceção."""
    with _lock:
        if estado_execucao["executando"]:
            return {"ok": False, "erro": "já tem uma varredura em andamento"}
        estado_execucao["executando"] = True
    agora = datetime.now()
    cfg = config()
    try:
        cache_lido = _ler("nf-cache.json", {})
        cache_nf = _limpar_cache(cache_lido, int(cfg.get("nf_cache_dias") or 30), agora)
        tamanho_cache = (len(cache_lido), len(cache_nf))
        stats = _stats_memoria.get("dados") or _ler("stats.json", {})
        _stats_memoria["dados"] = stats  # a volta seguinte soma em cima desta, mesmo sem ter gravado no disco
        stats.setdefault("primeira_vez", agora.strftime("%Y-%m-%d %H:%M:%S"))
        dia = stats.setdefault("por_dia", {}).setdefault(agora.strftime("%Y-%m-%d"), {})
        total = dict(RESULTADO_VAZIO)
        for pasta in cfg["pastas"]:
            ep = estado_pastas.setdefault(pasta["caminho"], {"estado": "Conectando", "desde": agora.strftime("%Y-%m-%d %H:%M:%S")})
            try:
                res = varrer_pasta(pasta, cfg, cache_nf, stats, agora)
                if ep.get("estado") != "Vigiando":
                    ep.update(estado="Vigiando", desde=agora.strftime("%Y-%m-%d %H:%M:%S"))
                ep.update(ultima_varredura=agora.strftime("%Y-%m-%d %H:%M:%S"), erro="", verificados=res["verificados"], feitos=res["feitos"] + res["simulados"])
                for k, v in res.items():
                    total[k] += v
                if pasta.get("processado") and pasta.get("processado_auto", True):
                    try:
                        rp = varrer_processado(pasta, cfg, agora)
                        for k, v in rp.items():
                            total[k] += v
                        ep.update(processado_erro="", processado_verificados=rp["verificados"])
                    except OSError as e:
                        if not ep.get("processado_erro"):
                            logger.warning("%s: sem acesso à pasta de processados (%s)", pasta["processado"], e)
                            total["erros"] += 1
                        ep["processado_erro"] = f"Pasta de processados inacessível: {e}"[:300]
            except OSError as e:
                if ep.get("estado") != "Sem acesso":  # só na mudança: a cada 2 s viraria uma enxurrada no log
                    logger.warning("%s: sem acesso, tenta de novo na próxima varredura (%s)", pasta["caminho"], e)
                    ep["desde"] = agora.strftime("%Y-%m-%d %H:%M:%S")
                    total["erros"] += 1
                ep.update(estado="Sem acesso", erro=f"Pasta inacessível: {e}"[:300], ultima_varredura=agora.strftime("%Y-%m-%d %H:%M:%S"))
        for k, v in total.items():
            dia[k] = dia.get(k, 0) + v
            stats[k] = stats.get(k, 0) + v
        # guarda só os últimos 90 dias de números diários
        corte = (agora - timedelta(days=90)).strftime("%Y-%m-%d")
        stats["por_dia"] = {d: v for d, v in stats["por_dia"].items() if d >= corte}
        houve_algo = total["feitos"] or total["simulados"] or total["erros"]
        if houve_algo or time.time() - _stats_gravado["quando"] >= GRAVAR_STATS_A_CADA or origem == "manual":
            _gravar("stats.json", stats)
            _stats_gravado["quando"] = time.time()
        if len(cache_nf) != tamanho_cache[1] or tamanho_cache[0] != tamanho_cache[1]:  # entrou NF nova ou venceu alguma
            _gravar("nf-cache.json", cache_nf)
        resultado = {"ok": True, "origem": origem, "quando": agora.strftime("%d/%m/%Y %H:%M:%S"), **total,
                     "simulacao": cfg.get("simulacao", True)}
        if total["feitos"] or total["simulados"] or total["erros"]:
            logger.info("Varredura (%s): %d verificado(s), %d %s, %d erro(s).", origem, total["verificados"],
                        total["feitos"] or total["simulados"], "feito(s)" if total["feitos"] else "simulado(s)", total["erros"])
        return resultado
    except Exception as e:
        logger.exception("Erro na varredura do LongNameJanitor")
        return {"ok": False, "erro": str(e)}
    finally:
        with _lock:
            estado_execucao["executando"] = False
            estado_execucao["ultima_varredura"] = agora.strftime("%d/%m/%Y %H:%M:%S")


def varredura_manual(usuario: str) -> dict:
    if estado_execucao["executando"]:
        return {"ok": False, "erro": "já tem uma varredura em andamento"}
    if not config()["pastas"]:
        return {"ok": False, "erro": "nenhuma pasta cadastrada"}
    logger.info("Varredura manual do LongNameJanitor pedida por %s.", usuario)
    threading.Thread(target=executar_varredura, kwargs={"origem": "manual"}, daemon=True, name="longnamejanitor_manual").start()
    return {"ok": True}


def _abrir_historico(caminho: str):
    """O CSV do dia; se a manutenção dos logs (3.4.8.0) já zipou (parado há 7 dias), lê de historico/arquivados/<dia>.csv.zip."""
    if os.path.exists(caminho):
        return open(caminho, "r", encoding="utf-8-sig")
    nome = os.path.basename(caminho)
    zipado = os.path.join(os.path.dirname(caminho), "arquivados", nome + ".zip")
    if not os.path.exists(zipado):
        raise FileNotFoundError(caminho)
    with zipfile.ZipFile(zipado) as z:
        texto = z.read(nome).decode("utf-8-sig", errors="replace")
    return io.StringIO(texto)


def ler_historico(dia: Optional[str] = None, limite: int = 500) -> dict:
    dia = dia or date.today().isoformat()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dia):
        return {"ok": False, "erro": "dia inválido"}
    caminho = os.path.join(pasta_dados(), "historico", dia + ".csv")
    linhas = []
    try:
        with _abrir_historico(caminho) as f:
            for i, linha in enumerate(f):
                partes = linha.rstrip("\r\n").split(";")
                if i == 0 or len(partes) < 5:
                    continue
                linhas.append(dict(zip(("quando", "acao", "arquivo", "pasta", "detalhe"), partes[:5])))
    except FileNotFoundError:
        pass
    return {"ok": True, "dia": dia, "linhas": linhas[::-1][:limite], "total": len(linhas)}


def status() -> dict:
    cfg = config()
    stats = _stats_memoria.get("dados") or _ler("stats.json", {})
    hoje = stats.get("por_dia", {}).get(date.today().isoformat(), {})
    est = _ler("estado.json", {})
    dias = sorted(stats.get("por_dia", {}).items())[-14:]
    return {
        "ok": True, "ligado": bool(est.get("ligado")), "alterado_por": est.get("alterado_por"), "alterado_em": est.get("alterado_em"),
        "simulacao": cfg.get("simulacao", True), "rescan_segundos": cfg.get("rescan_segundos"), "nf_cache_dias": cfg.get("nf_cache_dias"),
        "servico_windows": estado_servico_windows(), "executando": estado_execucao["executando"],
        "ultima_varredura": estado_execucao["ultima_varredura"], "proxima": estado_execucao["proxima"],
        "hoje": hoje, "total": {k: stats.get(k, 0) for k in ("verificados", "feitos", "simulados", "duplicadas", "erros", "processados")},
        "primeira_vez": stats.get("primeira_vez"), "nf_cache": len(_ler("nf-cache.json", {})),
        "dias": [{"dia": d, **v} for d, v in dias],
        "pastas": [{**p, **estado_pastas.get(p["caminho"], {"estado": "Aguardando a primeira varredura"}),
                    "processado_hoje": (pastas_do_dia_processado(p, datetime.now()) or [""])[0]} for p in cfg["pastas"]],
        "atividade": list(atividade),  # as últimas MAX_ATIVIDADE (300); a tela filtra (3.4.7.0)
        "mover_tudo": dict(estado_mover_tudo),
    }


class MonitorLongNameJanitor:
    """Uma varredura a cada `rescan_segundos` enquanto estiver ligado no card (conta do fim de uma ao começo da outra)."""

    def __init__(self):
        self._stop = threading.Event()

    def iniciar(self) -> None:
        threading.Thread(target=self._loop, daemon=True, name="longnamejanitor").start()

    def parar(self) -> None:
        self._stop.set()
        _acordar.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            if esta_ligado() and estado_servico_windows() != "RUNNING":
                executar_varredura("agendado")
                espera = max(RESCAN_MIN_S, min(RESCAN_MAX_S, int(config().get("rescan_segundos") or 2)))
            else:
                espera = 10
            estado_execucao["proxima"] = (datetime.now() + timedelta(seconds=espera)).strftime("%d/%m/%Y %H:%M:%S") if esta_ligado() else None
            _acordar.wait(espera)
            _acordar.clear()
