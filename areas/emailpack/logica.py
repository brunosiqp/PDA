"""Monitoramento EmailPack - lógica (varredura dos logs dos serviços EmailPack por e-mail processado, com aviso no Teams e por e-mail).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

import requests

from core.config_seguro import obter_valor_config as _obter_valor_config
from nucleo.caminhos import base_path_app as _base_path_app

logger_emailpack = logging.getLogger("alertas.emailpack")  # mesmo logger configurado no alertas_gui.py


# ---------------------------------------------------------------------------
# Monitoramento EmailPack
# ---------------------------------------------------------------------------
# Varre os logs dos serviços EmailPack (via caminho de rede UNC) procurando
# erros por e-mail processado, e avisa no Teams quando encontra algo (ou,
# opcionalmente, um "heartbeat" de sucesso quando não encontra nada). Portado
# do script standalone monitor_emailpack_gui.py (versão com contexto por
# thread persistente entre ciclos) - a lógica central é a mesma; só a
# interface mudou (GUI Tkinter -> card + página web do PDA).
#
# IMPORTANTE sobre o motivo do contexto por thread: como a leitura é por
# OFFSET (só linhas novas desde a última vez), é bem comum a linha
# "Verificando caixa de entrada do endereço 'X'" cair num ciclo e o
# ERROR/FATAL correspondente só aparecer no ciclo seguinte, na mesma
# thread do log. Uma versão anterior que associava o e-mail só dentro do
# mesmo lote de linhas lidas de uma vez perdia essa associação nesse caso
# (o erro ficava "órfão", sem e-mail, e podia nem ser notificado) - por
# isso agora o "último e-mail visto por thread" é salvo em disco e
# carregado de novo no próximo ciclo, junto com os offsets.

def _diretorios_padrao_emailpack() -> List[str]:
    return [
        r"\\srv576\EmailPack\EmailPackServiceGeral\log",
        r"\\srv576\EmailPack\EmailPackServiceGeral2\log",
        r"\\srv576\EmailPack\EmailPackServiceEmpresa\log",
        r"\\srv576\EmailPack\EmailPackServiceEmpresa2\log",
        r"\\srv576\EmailPack\EmailPackServiceEmpresa3\log",
        r"\\srv576\EmailPack\EmailPackSemAutenticacao\log",
    ]


CONFIG_EMAILPACK = {
    "diretorios_log": (
        os.environ["EMAILPACK_DIRS"].split(";")
        if os.environ.get("EMAILPACK_DIRS")
        else _diretorios_padrao_emailpack()
    ),
    "extensoes_log": (".log",),
    "pasta_monitoramento": os.environ.get(
        "EMAILPACK_PASTA_MON", os.path.join(_base_path_app(), "logs", "emailpack")
    ),
    "niveis_erro": {"ERROR", "FATAL"},
    "dedup_minutos": int(os.environ.get("EMAILPACK_DEDUP_MIN", "9")),
    "heartbeat_sucesso": os.environ.get("EMAILPACK_HEARTBEAT", "1") == "1",
    "encoding_log": os.environ.get("EMAILPACK_LOG_ENCODING", "cp1252"),
    "linhas_stack_no_alerta": 3,
    "limite_caracteres_card": 4000,
    "intervalo_execucao_segundos": int(os.environ.get("EMAILPACK_INTERVALO_SEG", "600")),  # 10 min
    "timeout_diretorio_segundos": float(os.environ.get("EMAILPACK_TIMEOUT_DIR", "5")),
    "identificacao_alerta": os.environ.get("EMAILPACK_IDENTIFICACAO", "PDA"),
    "unc_servidor": os.environ.get("EMAILPACK_UNC_SERVIDOR", r"\\srv576\EmailPack"),
    "unc_usuario": os.environ.get("EMAILPACK_UNC_USUARIO", ""),
}
# a senha do compartilhamento UNC e o webhook do Teams seguem o mesmo
# padrão de credencial cifrada (Configurações Seguras) que o resto do
# PDA usa - nada de senha em texto puro em .env. O valor literal abaixo
# é só o fallback padrão (mesmo webhook que já estava configurado no
# script original), usado só enquanto ninguém sobrescrever via
# Configurações Seguras ou variável de ambiente.
_WEBHOOK_EMAILPACK_PADRAO = (
    "https://example.invalid/"
    "powerautomate/automations/direct/cu/29/workflows/0000000000000000000084e0c0eafaa9/"
    "triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&"
    "sig=REMOVIDO"
)


def _senha_unc_emailpack() -> str:
    return _obter_valor_config("emailpack::UNC_SENHA", os.getenv("EMAILPACK_UNC_SENHA", ""))


def _webhook_teams_emailpack() -> str:
    return _obter_valor_config(
        "teams::emailpack_webhook", os.getenv("EMAILPACK_TEAMS_WEBHOOK", _WEBHOOK_EMAILPACK_PADRAO)
    )


RE_LINHA_EMAILPACK = re.compile(
    r"^(?P<ts>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})\s+"
    r"\[(?P<thread>\d+)\]\s+(?P<nivel>\w+)\s+(?P<logger>\S+)\s+-\s+(?P<msg>.*)$"
)
RE_ENDERECO_EMAILPACK = re.compile(r"Verificando caixa de entrada do endere[cç]o '([^']+)'")
RE_EMAIL_SOLTO_EMAILPACK = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


@dataclass
class _LogEntryEmailPack:
    timestamp: datetime
    thread: str
    nivel: str
    logger: str
    mensagem: str


@dataclass
class _ResumoErroEmailPack:
    quantidade: int = 0
    primeira: Optional[datetime] = None
    ultima: Optional[datetime] = None
    mensagem: str = ""
    mensagens: List[str] = field(default_factory=list)


_executor_rede_emailpack = ThreadPoolExecutor(max_workers=8, thread_name_prefix="checagem_unc_emailpack")
_autenticacao_tentada_emailpack = False


def _dir_existe_com_timeout_emailpack(dir_path: Path, timeout_seg: float) -> bool:
    future = _executor_rede_emailpack.submit(dir_path.is_dir)
    try:
        return future.result(timeout=timeout_seg)
    except Exception:
        return False


def _autenticar_compartilhamento_emailpack() -> None:
    global _autenticacao_tentada_emailpack
    if _autenticacao_tentada_emailpack:
        return
    _autenticacao_tentada_emailpack = True

    servidor = CONFIG_EMAILPACK.get("unc_servidor")
    usuario = CONFIG_EMAILPACK.get("unc_usuario")
    senha = _senha_unc_emailpack()
    if not (servidor and usuario and senha):
        return

    try:
        resultado = subprocess.run(
            ["net", "use", servidor, senha, f"/user:{usuario}"],
            capture_output=True, text=True, timeout=15,
        )
        if resultado.returncode == 0:
            logger_emailpack.info("Autenticado no compartilhamento %s", servidor)
        else:
            logger_emailpack.warning(
                "Falha ao autenticar no compartilhamento %s (código %s): %s",
                servidor, resultado.returncode, resultado.stderr.strip(),
            )
    except FileNotFoundError:
        pass
    except Exception as exc:
        logger_emailpack.warning("Erro ao tentar autenticar no compartilhamento %s: %s", servidor, exc)


def _listar_arquivos_log_emailpack() -> Dict[str, list]:
    arquivos_por_dir: Dict[str, list] = {}
    timeout = CONFIG_EMAILPACK["timeout_diretorio_segundos"]
    for dir_str in CONFIG_EMAILPACK["diretorios_log"]:
        dir_path = Path(dir_str)
        if not _dir_existe_com_timeout_emailpack(dir_path, timeout):
            logger_emailpack.warning(
                "Diretório configurado não encontrado/acessível (ou sem resposta em %.0fs): %s",
                timeout, dir_str,
            )
            continue
        try:
            encontrados = [
                p for p in dir_path.iterdir()
                if p.is_file() and p.suffix.lower() in CONFIG_EMAILPACK["extensoes_log"]
            ]
        except Exception as exc:
            logger_emailpack.warning("Falha ao listar arquivos em '%s': %s", dir_str, exc)
            continue
        arquivos_por_dir[dir_str] = sorted(encontrados)
    return arquivos_por_dir


def _nome_servico_emailpack(caminho_arquivo: Path) -> str:
    partes = caminho_arquivo.parts
    try:
        idx = len(partes) - 1 - partes[::-1].index("log")
        return partes[idx - 1]
    except ValueError:
        return caminho_arquivo.parent.name


def _carregar_estado_monitoramento_emailpack(arquivo_estado: Path):
    """Devolve (offsets, thread_context, thread_inicio). thread_context
    guarda, por arquivo e por thread do log, qual foi o último e-mail
    visto ("Verificando caixa de entrada de X") - e thread_inicio, o
    horário em que essa associação começou. Os dois persistem entre
    ciclos (por isso um erro que aparece num ciclo seguinte ao da linha
    de início continua sendo associado ao e-mail certo).

    Compatibilidade: se o JSON salvo for do formato antigo (só
    {arquivo: offset}, sem contexto de thread), migra automaticamente."""
    if not arquivo_estado.exists():
        return {}, {}, {}
    try:
        estado = json.loads(arquivo_estado.read_text(encoding="utf-8"))
    except Exception:
        return {}, {}, {}

    if isinstance(estado, dict) and "offsets" in estado:
        offsets = estado.get("offsets") if isinstance(estado.get("offsets"), dict) else {}
        thread_context = estado.get("thread_context") if isinstance(estado.get("thread_context"), dict) else {}
        thread_inicio = estado.get("thread_inicio") if isinstance(estado.get("thread_inicio"), dict) else {}
        offsets_validos = {}
        for k, v in offsets.items():
            try:
                offsets_validos[str(k)] = int(v)
            except Exception:
                pass
        return offsets_validos, thread_context, thread_inicio

    if isinstance(estado, dict):
        # formato antigo (so offset simples) - migra sem contexto de thread
        offsets_validos = {}
        for k, v in estado.items():
            try:
                offsets_validos[str(k)] = int(v)
            except Exception:
                pass
        return offsets_validos, {}, {}

    return {}, {}, {}


def _salvar_estado_monitoramento_emailpack(arquivo_estado: Path, offsets: dict, thread_context: dict, thread_inicio: dict) -> None:
    arquivo_estado.parent.mkdir(parents=True, exist_ok=True)
    estado = {
        "versao": 2,
        "atualizado_em": datetime.now().isoformat(),
        "offsets": offsets,
        "thread_context": thread_context,
        "thread_inicio": thread_inicio,
    }
    arquivo_estado.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding="utf-8")


_lock_emails_emailpack = threading.Lock()


def _caminho_emails_conhecidos_emailpack() -> Path:
    return Path(CONFIG_EMAILPACK["pasta_monitoramento"]) / "emails_conhecidos.json"


def _caminho_emails_ignorados_emailpack() -> Path:
    return Path(CONFIG_EMAILPACK["pasta_monitoramento"]) / "emails_ignorados.json"


def _carregar_emails_conhecidos_emailpack() -> set:
    caminho = _caminho_emails_conhecidos_emailpack()
    if not caminho.exists():
        return set()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dados, list):
            return set(dados)
    except Exception:
        logger_emailpack.exception("Não foi possível ler emails_conhecidos.json.")
    return set()


def _salvar_emails_conhecidos_emailpack(emails: set) -> None:
    caminho = _caminho_emails_conhecidos_emailpack()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(sorted(emails), indent=2, ensure_ascii=False), encoding="utf-8")


def _carregar_emails_ignorados_emailpack() -> set:
    caminho = _caminho_emails_ignorados_emailpack()
    if not caminho.exists():
        return set()
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
        if isinstance(dados, list):
            return set(dados)
    except Exception:
        logger_emailpack.exception("Não foi possível ler emails_ignorados.json.")
    return set()


def _salvar_emails_ignorados_emailpack(emails: set) -> None:
    caminho = _caminho_emails_ignorados_emailpack()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(sorted(emails), indent=2, ensure_ascii=False), encoding="utf-8")


def _ler_novas_linhas_emailpack(caminho_arquivo: Path, offsets: dict) -> list:
    chave = str(caminho_arquivo)
    tamanho_atual = caminho_arquivo.stat().st_size
    primeira_vez = chave not in offsets
    offset = int(offsets.get(chave, 0))

    if offset > tamanho_atual:
        offset = 0  # log rotacionou/truncou - recomeça do início

    if primeira_vez:
        # não apita histórico antigo na primeira vez que vê o arquivo -
        # só marca a posição atual e passa a ler dali em diante
        offsets[chave] = tamanho_atual
        return []

    with open(caminho_arquivo, "r", encoding=CONFIG_EMAILPACK["encoding_log"], errors="replace") as f:
        f.seek(offset)
        linhas = f.readlines()
        novo_offset = f.tell()

    offsets[chave] = novo_offset
    return linhas


def _parse_linhas_emailpack(linhas: list) -> List[_LogEntryEmailPack]:
    entradas: List[_LogEntryEmailPack] = []
    for linha_bruta in linhas:
        linha = linha_bruta.rstrip("\n").rstrip("\r")
        if not linha.strip():
            continue
        m = RE_LINHA_EMAILPACK.match(linha)
        if m:
            try:
                ts = datetime.strptime(m.group("ts"), "%Y-%m-%d %H:%M:%S,%f")
            except Exception:
                continue
            entradas.append(
                _LogEntryEmailPack(
                    timestamp=ts,
                    thread=m.group("thread"),
                    nivel=m.group("nivel").strip(),
                    logger=m.group("logger"),
                    mensagem=m.group("msg"),
                )
            )
        elif entradas:
            entradas[-1].mensagem += "\n" + linha.strip()
    return entradas


def _limpar_mensagem_para_alerta_emailpack(msg: str) -> str:
    msg = msg.strip()
    if not msg:
        return "(sem detalhe)"
    linhas = msg.splitlines()
    principal = linhas[0].strip()
    extras = [l.strip() for l in linhas[1: 1 + CONFIG_EMAILPACK["linhas_stack_no_alerta"]] if l.strip()]
    if extras:
        return principal + "\n" + "\n".join(extras)
    return principal


def _descobrir_email_fallback_emailpack(texto: str) -> Optional[str]:
    m = RE_EMAIL_SOLTO_EMAILPACK.search(texto or "")
    return m.group(0) if m else None


def _parse_iso_data_emailpack(valor: Optional[str]) -> Optional[datetime]:
    if not valor:
        return None
    try:
        return datetime.fromisoformat(valor)
    except Exception:
        return None


def _registrar_erros_por_ordem_thread_emailpack(
    erros_por_servico: Dict[str, Dict[str, _ResumoErroEmailPack]],
    servico: str,
    caminho_arquivo: Path,
    entradas: List[_LogEntryEmailPack],
    thread_context: dict,
    thread_inicio: dict,
    emails_conhecidos: Optional[set] = None,
) -> None:
    """Associa cada ERROR/FATAL ao último e-mail visto na MESMA thread
    (persistindo isso em thread_context/thread_inicio pros próximos
    ciclos) - em vez de só agrupar dentro do lote de linhas lido agora,
    o que perdia a associação quando a linha "verificando caixa de
    entrada" e o erro correspondente caíam em ciclos diferentes.
    Se emails_conhecidos for passado, todo endereço visto (mesmo sem
    erro nenhum) é acumulado ali - vira o "cache" de endereços já
    processados alguma vez, usado pra montar a lista de quem dá pra
    marcar como ignorado."""
    bucket = erros_por_servico.setdefault(servico, {})
    chave_arquivo = str(caminho_arquivo)
    contexto_arquivo = thread_context.setdefault(chave_arquivo, {})
    inicio_arquivo = thread_inicio.setdefault(chave_arquivo, {})

    for e in entradas:
        m_email = RE_ENDERECO_EMAILPACK.search(e.mensagem)
        if m_email:
            contexto_arquivo[e.thread] = m_email.group(1)
            inicio_arquivo[e.thread] = e.timestamp.isoformat()
            if emails_conhecidos is not None:
                emails_conhecidos.add(m_email.group(1))

        if e.nivel not in CONFIG_EMAILPACK["niveis_erro"]:
            continue

        email = contexto_arquivo.get(e.thread)
        if not email:
            email = _descobrir_email_fallback_emailpack(e.mensagem) or f"(sem_email_thread_{e.thread})"

        mensagem_alerta = _limpar_mensagem_para_alerta_emailpack(e.mensagem)
        resumo = bucket.setdefault(email, _ResumoErroEmailPack())
        resumo.quantidade += 1
        resumo.mensagem = mensagem_alerta
        resumo.mensagens.append(mensagem_alerta)

        inicio_email = _parse_iso_data_emailpack(inicio_arquivo.get(e.thread)) or e.timestamp
        if resumo.primeira is None or inicio_email < resumo.primeira:
            resumo.primeira = inicio_email
        if resumo.ultima is None or e.timestamp >= resumo.ultima:
            resumo.ultima = e.timestamp


def _enviar_teams_alerta_emailpack(titulo: str, mensagem: str, nivel: str = "erro") -> None:
    webhook_url = _webhook_teams_emailpack()
    if not webhook_url:
        logger_emailpack.warning("Webhook do Teams não configurado. Alerta NÃO enviado: %s", titulo)
        return

    estilo = {"sucesso": "good", "aviso": "warning"}.get(nivel, "attention")
    prefixo = {"sucesso": "[OK]", "aviso": "[ATENÇÃO]"}.get(nivel, "[ERRO]")

    limite = CONFIG_EMAILPACK["limite_caracteres_card"]
    mensagem_cortada = mensagem if len(mensagem) < limite else mensagem[:limite] + "\n... (cortado, ver log de execução)"

    card = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "type": "AdaptiveCard",
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "Container",
                            "style": estilo,
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{prefixo} {titulo}",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "wrap": True,
                                }
                            ],
                        },
                        {"type": "TextBlock", "text": mensagem_cortada, "wrap": True},
                        {
                            "type": "TextBlock",
                            "text": f"{CONFIG_EMAILPACK['identificacao_alerta']} | {datetime.now():%Y-%m-%d %H:%M:%S}",
                            "isSubtle": True,
                            "size": "Small",
                            "wrap": True,
                        },
                    ],
                },
            }
        ],
    }

    try:
        resp = requests.post(webhook_url, json=card, timeout=15)
        resp.raise_for_status()
        logger_emailpack.info("Notificação Teams enviada [%s]: %s", nivel, titulo)
    except requests.RequestException as exc:
        logger_emailpack.error("Falha ao enviar notificação Teams: %s", exc)


def _calcular_hash_emailpack(texto: str) -> str:
    return hashlib.md5(texto.encode("utf-8")).hexdigest()


def _caminho_dedup_fallback_emailpack(arquivo_estado: Path) -> Path:
    """Caminho de fallback (em %TEMP%, gravável por qualquer usuário) pro
    estado de dedup - mesmo caso de ACL entre usuários do Windows já
    visto nos logs/relatórios (ver _criar_handler_arquivo). Usa o mesmo
    nome de arquivo, só numa pasta alternativa."""
    pasta_fallback = Path(tempfile.gettempdir()) / "painelalertas_fallback_dedup_erros_email"
    return pasta_fallback / arquivo_estado.name


def _deve_reenviar_emailpack(hash_atual: str, arquivo_estado: Path, dedup_minutos: int) -> bool:
    if dedup_minutos <= 0:
        return True
    caminho_real = arquivo_estado
    if not caminho_real.exists():
        # se o estado principal não existe (nunca foi gravado, ou foi
        # parar no fallback numa rodada anterior por causa da ACL),
        # confere o fallback antes de assumir que é a primeira vez
        caminho_fallback = _caminho_dedup_fallback_emailpack(arquivo_estado)
        caminho_real = caminho_fallback if caminho_fallback.exists() else caminho_real
    if not caminho_real.exists():
        return True
    try:
        estado = json.loads(caminho_real.read_text(encoding="utf-8"))
        hash_anterior = estado.get("hash")
        data_anterior = datetime.fromisoformat(estado.get("data"))
    except Exception:
        return True
    dentro_da_janela = (datetime.now() - data_anterior) < timedelta(minutes=dedup_minutos)
    return not (hash_anterior == hash_atual and dentro_da_janela)


def _gravar_estado_dedup_emailpack(hash_atual: str, arquivo_estado: Path) -> None:
    conteudo = json.dumps({"hash": hash_atual, "data": datetime.now().isoformat()})
    try:
        arquivo_estado.parent.mkdir(parents=True, exist_ok=True)
        arquivo_estado.write_text(conteudo, encoding="utf-8")
    except (PermissionError, OSError) as e:
        # mesmo caso de ACL entre usuários do Windows já visto antes nos
        # logs (Errno 13) - cai pro fallback em vez de derrubar o ciclo
        # de monitoramento inteiro por causa de UM arquivo de dedup
        caminho_fallback = _caminho_dedup_fallback_emailpack(arquivo_estado)
        logger_emailpack.warning(
            "Sem permissão de escrita em '%s' (%s). Gravando o estado de dedup em '%s' até a "
            "permissão da pasta ser corrigida.", arquivo_estado, e, caminho_fallback,
        )
        caminho_fallback.parent.mkdir(parents=True, exist_ok=True)
        caminho_fallback.write_text(conteudo, encoding="utf-8")


def _nome_arquivo_seguro_emailpack(texto: str) -> str:
    seguro = re.sub(r"[^A-Za-z0-9_.@-]+", "_", texto or "sem_nome")
    return seguro[:150].strip("._") or "sem_nome"


def _formatar_texto_alerta_email_emailpack(servico: str, email: str, resumo: _ResumoErroEmailPack) -> str:
    primeira = resumo.primeira.strftime("%H:%M:%S") if resumo.primeira else "?"
    ultima = resumo.ultima.strftime("%H:%M:%S") if resumo.ultima else "?"

    mensagens_distintas: List[str] = []
    for msg in resumo.mensagens:
        if msg not in mensagens_distintas:
            mensagens_distintas.append(msg)
        if len(mensagens_distintas) >= 3:
            break

    partes = [
        f"**Serviço:** {servico}",
        f"**E-mail:** {email}",
        f"**Ocorrências:** {resumo.quantidade}",
        f"**Primeiro erro:** {primeira}",
        f"**Último erro:** {ultima}",
        "",
        "**Mensagem:**",
    ]
    if mensagens_distintas:
        for msg in mensagens_distintas:
            partes.append(msg)
            partes.append("")
    else:
        partes.append("(sem detalhe)")
    return "\n".join(partes).strip()


def _enviar_alertas_por_email_emailpack(
    pasta_estado: Path,
    erros_por_servico: Dict[str, Dict[str, _ResumoErroEmailPack]],
    emails_ignorados: Optional[set] = None,
) -> None:
    """Manda um card separado no Teams pra cada (serviço, e-mail) com
    erro - com dedup granular por par serviço+e-mail (não um hash
    combinado de tudo), pra um e-mail com erro novo não ficar esperando
    a janela de dedup de outro e-mail que já tinha sido avisado.
    E-mails na lista de ignorados continuam registrados/visíveis na tela
    do PDA (pra não esconder informação), só não geram card no Teams."""
    pasta_dedup_email = pasta_estado / "dedup_erros_email"
    try:
        pasta_dedup_email.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError) as e:
        # mesmo problema de ACL, só que na CRIAÇÃO da pasta - sem isso,
        # nenhum alerta desse ciclo seria enviado. _gravar_estado_dedup_emailpack
        # já cai pro fallback em %TEMP% sozinho quando grava cada arquivo,
        # então só logamos aqui e seguimos (a pasta pode nem ser
        # necessária se _deve_reenviar_emailpack achar tudo no fallback).
        logger_emailpack.warning(
            "Sem permissão pra criar '%s' (%s). O dedup vai cair pro fallback "
            "em %%TEMP%% conforme necessário.", pasta_dedup_email, e,
        )
    emails_ignorados = emails_ignorados or set()

    total_enviados = 0
    total_suprimidos = 0
    total_ignorados = 0

    for servico, emails in erros_por_servico.items():
        for email, resumo in sorted(emails.items()):
            if email in emails_ignorados:
                total_ignorados += 1
                continue

            try:
                texto_email = _formatar_texto_alerta_email_emailpack(servico, email, resumo)
                hash_email = _calcular_hash_emailpack(f"{servico}|{email}|{texto_email}")
                arquivo_estado_email = pasta_dedup_email / f"{_nome_arquivo_seguro_emailpack(servico)}__{_nome_arquivo_seguro_emailpack(email)}.json"

                if _deve_reenviar_emailpack(hash_email, arquivo_estado_email, CONFIG_EMAILPACK["dedup_minutos"]):
                    _enviar_teams_alerta_emailpack(f"Monitoramento EmailPack - Erro em {email}", texto_email, "erro")
                    _gravar_estado_dedup_emailpack(hash_email, arquivo_estado_email)
                    total_enviados += 1
                else:
                    logger_emailpack.info(
                        "Erro de %s/%s já notificado há menos de %d min. Card não reenviado.",
                        servico, email, CONFIG_EMAILPACK["dedup_minutos"],
                    )
                    total_suprimidos += 1
            except Exception:
                # UM e-mail/serviço com problema (dedup, envio ao Teams,
                # etc.) não pode travar o ciclo inteiro - os outros
                # serviços/e-mails que TAMBÉM têm erro real pra avisar
                # continuam sendo processados normalmente.
                logger_emailpack.exception(
                    "Falha ao processar o alerta de %s/%s - seguindo pros próximos.", servico, email,
                )

    if total_ignorados:
        logger_emailpack.info("%d card(s) não enviado(s) por estarem na lista de e-mails ignorados.", total_ignorados)

    logger_emailpack.info("Cards por e-mail enviados: %d; suprimidos por dedup: %d", total_enviados, total_suprimidos)


# Estado do último ciclo, pra tela web mostrar sem precisar reprocessar
# nada - atualizado no final de cada _executar_ciclo_emailpack.
estado_emailpack: dict = {
    "ultima_execucao": None, "executando": False,
    "total_linhas_novas": 0, "servicos_verificados": 0, "arquivos_verificados": 0,
    "dirs_ausentes": [], "erros_por_servico": {}, "ultimo_erro_execucao": None,
}
_lock_estado_emailpack = threading.Lock()


def _executar_ciclo_emailpack() -> None:
    """Um ciclo completo de monitoramento - mesma lógica do script
    original (executar_ciclo), só que gravando o resumo em
    estado_emailpack no final, pra tela web mostrar."""
    pasta = Path(CONFIG_EMAILPACK["pasta_monitoramento"])
    arquivo_estado_monitoramento = pasta / "ultimo_offset.json"
    arquivo_estado_dirs = pasta / "ultimo_aviso_dirs.json"

    logger_emailpack.info("===== Iniciando ciclo de monitoramento (%d diretórios) =====", len(CONFIG_EMAILPACK["diretorios_log"]))

    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    _autenticar_compartilhamento_emailpack()
    arquivos_por_dir = _listar_arquivos_log_emailpack()
    dirs_ausentes = [d for d in CONFIG_EMAILPACK["diretorios_log"] if d not in arquivos_por_dir]

    offsets, thread_context, thread_inicio = _carregar_estado_monitoramento_emailpack(arquivo_estado_monitoramento)
    emails_conhecidos = _carregar_emails_conhecidos_emailpack()
    qtd_emails_conhecidos_antes = len(emails_conhecidos)
    erros_por_servico: Dict[str, Dict[str, _ResumoErroEmailPack]] = {}
    total_linhas_novas = 0
    total_entradas_parseadas = 0
    arquivos_com_falha_leitura = []

    for dir_str, arquivos in arquivos_por_dir.items():
        for caminho in arquivos:
            servico = _nome_servico_emailpack(caminho)
            try:
                linhas_novas = _ler_novas_linhas_emailpack(caminho, offsets)
            except Exception as exc:
                logger_emailpack.error("Falha ao ler '%s': %s", caminho, exc)
                arquivos_com_falha_leitura.append(f"{servico}/{caminho.name}: {exc}")
                continue

            if not linhas_novas:
                continue

            total_linhas_novas += len(linhas_novas)
            entradas = _parse_linhas_emailpack(linhas_novas)
            total_entradas_parseadas += len(entradas)
            _registrar_erros_por_ordem_thread_emailpack(
                erros_por_servico, servico, caminho, entradas, thread_context, thread_inicio, emails_conhecidos,
            )

    try:
        _salvar_estado_monitoramento_emailpack(arquivo_estado_monitoramento, offsets, thread_context, thread_inicio)
    except Exception as exc:
        logger_emailpack.warning("Não foi possível salvar o estado de monitoramento: %s", exc)
    if len(emails_conhecidos) != qtd_emails_conhecidos_antes:
        try:
            _salvar_emails_conhecidos_emailpack(emails_conhecidos)
            logger_emailpack.info(
                "Cache de e-mails conhecidos atualizado: %d novo(s), %d no total.",
                len(emails_conhecidos) - qtd_emails_conhecidos_antes, len(emails_conhecidos),
            )
        except Exception:
            logger_emailpack.exception("Não foi possível salvar o cache de e-mails conhecidos.")
    logger_emailpack.info("Total de linhas novas lidas: %d", total_linhas_novas)
    logger_emailpack.info("Total de entradas de log parseadas: %d", total_entradas_parseadas)

    if dirs_ausentes:
        texto = "\n".join(f"- {d}" for d in dirs_ausentes)
        hash_dirs = _calcular_hash_emailpack(texto)
        if _deve_reenviar_emailpack(hash_dirs, arquivo_estado_dirs, CONFIG_EMAILPACK["dedup_minutos"]):
            _enviar_teams_alerta_emailpack(
                f"Monitoramento EmailPack - {len(dirs_ausentes)} diretório(s) inacessível(is)", texto, "aviso",
            )
            _gravar_estado_dedup_emailpack(hash_dirs, arquivo_estado_dirs)
        else:
            logger_emailpack.info("Aviso de diretórios ausentes já notificado recentemente. Não reenviado.")

    if erros_por_servico:
        total_emails = sum(len(v) for v in erros_por_servico.values())
        total_ocorrencias = sum(r.quantidade for emails in erros_por_servico.values() for r in emails.values())

        for servico, emails in erros_por_servico.items():
            for email, resumo in sorted(emails.items()):
                primeira_linha = resumo.mensagem.splitlines()[0] if resumo.mensagem else "(sem detalhe)"
                logger_emailpack.error("[%s] %s -> %dx | %s", servico, email, resumo.quantidade, primeira_linha)

        logger_emailpack.info(
            "Enviando cards separados por e-mail: %d e-mail(s), %d ocorrência(s).", total_emails, total_ocorrencias,
        )
        emails_ignorados = _carregar_emails_ignorados_emailpack()
        _enviar_alertas_por_email_emailpack(pasta, erros_por_servico, emails_ignorados)
    elif not dirs_ausentes:
        logger_emailpack.info("Nenhum ERROR/FATAL encontrado nas linhas novas.")
        if CONFIG_EMAILPACK["heartbeat_sucesso"]:
            _enviar_teams_alerta_emailpack(
                "Monitoramento EmailPack - OK",
                f"Nenhum ERROR/FATAL encontrado nas linhas novas. {total_linhas_novas} linha(s) nova(s), "
                f"{total_entradas_parseadas} entrada(s) parseada(s), "
                f"{sum(len(v) for v in arquivos_por_dir.values())} arquivo(s), "
                f"{len(arquivos_por_dir)} diretório(s) verificado(s).",
                "sucesso",
            )

    if arquivos_com_falha_leitura:
        logger_emailpack.warning("Arquivos com falha de leitura: %s", "; ".join(arquivos_com_falha_leitura))

    logger_emailpack.info("===== Ciclo finalizado =====")

    with _lock_estado_emailpack:
        estado_emailpack["ultima_execucao"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        estado_emailpack["total_linhas_novas"] = total_linhas_novas
        estado_emailpack["servicos_verificados"] = len(arquivos_por_dir)
        estado_emailpack["arquivos_verificados"] = sum(len(v) for v in arquivos_por_dir.values())
        estado_emailpack["dirs_ausentes"] = dirs_ausentes
        estado_emailpack["erros_por_servico"] = {
            servico: {
                email: {
                    "quantidade": r.quantidade,
                    "primeira": r.primeira.strftime("%H:%M:%S") if r.primeira else None,
                    "ultima": r.ultima.strftime("%H:%M:%S") if r.ultima else None,
                    "mensagem": r.mensagem.splitlines()[0] if r.mensagem else "",
                }
                for email, r in emails.items()
            }
            for servico, emails in erros_por_servico.items()
        }
        estado_emailpack["ultimo_erro_execucao"] = None


class MonitorEmailPack:
    """Mesma ideia de MonitorContingencias - thread própria, roda de
    tempos em tempos (padrão: 10 em 10 min, igual o script original),
    com trava contra rodadas sobrepostas (manual batendo com a
    periódica, ou clique duplo no botão)."""

    def __init__(self, intervalo_segundos: int = None):
        self.intervalo_segundos = intervalo_segundos or CONFIG_EMAILPACK["intervalo_execucao_segundos"]
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock_execucao = threading.Lock()
        self._executando = False

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _rodar_com_trava(self) -> None:
        with self._lock_execucao:
            if self._executando:
                return
            self._executando = True
        with _lock_estado_emailpack:
            estado_emailpack["executando"] = True
        try:
            _executar_ciclo_emailpack()
        except Exception as e:
            logger_emailpack.exception("Erro fatal no ciclo de monitoramento EmailPack")
            with _lock_estado_emailpack:
                estado_emailpack["ultimo_erro_execucao"] = str(e)
            try:
                _enviar_teams_alerta_emailpack(
                    "Monitoramento EmailPack - FALHA NO SCRIPT", f"Erro fatal: {e}", "erro"
                )
            except Exception:
                pass
        finally:
            with self._lock_execucao:
                self._executando = False
            with _lock_estado_emailpack:
                estado_emailpack["executando"] = False

    def _loop(self) -> None:
        self._rodar_com_trava()
        while not self._stop.is_set():
            if self._stop.wait(self.intervalo_segundos):
                break
            self._rodar_com_trava()

    def forcar_atualizacao(self) -> bool:
        with self._lock_execucao:
            if self._executando:
                return False
        threading.Thread(target=self._rodar_com_trava, daemon=True).start()
        return True

    def parar(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
