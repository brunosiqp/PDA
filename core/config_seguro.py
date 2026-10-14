# encoding: utf-8
"""
Criptografia de configurações sensíveis (Fernet + config.dat).

Guarda credenciais sensíveis (senhas de banco, tokens de API) cifradas
num único arquivo (config.dat), em vez de espalhadas em texto puro em
vários arquivos .env. Como funciona:

  - chave.key: a chave de criptografia (gerada automaticamente na
    primeira vez que algo for salvo em config.dat, se ainda não existir).
    Fica na mesma pasta do programa, ao lado do config.dat.
  - config.dat: um "dicionário" só, com todas as chaves sensíveis
    migradas, cifrado inteiro com essa chave (ninguém lê o conteúdo sem
    ter o chave.key também).
  - obter_valor_config(chave, padrao): busca primeiro no config.dat (se
    existir e tiver essa chave); se não achar, usa o "padrao" informado
    (tipicamente o valor que já vinha de um .env comum) - ou seja, dá
    pra migrar aos poucos, uma credencial de cada vez, sem quebrar nada
    que ainda não foi migrado.

CONVENÇÃO DE NOMES DE CHAVE: "{origem}::{campo}", tudo minúsculo, onde
"origem" identifica de qual .env aquele valor veio (ex.: "saas",
"sharepoint", "cliente_e-cte") e "campo" é o nome original da variável
nesse .env (ex.: "db_password", "SHAREPOINT_PASSWORD"). Isso deixa
rastreável de onde cada valor cifrado veio, sem precisar abrir o
config.dat pra saber (que, sendo cifrado, não dá pra abrir mesmo sem a
chave).

SEJA REALISTA SOBRE O QUE ISSO PROTEGE: como o programa roda sozinho
(sem alguém digitando uma senha toda vez que liga), a chave PRECISA
estar em algum arquivo acessível pro programa conseguir decifrar
sozinho - então isso não impede alguém com acesso total ao servidor de
ler as credenciais (essa pessoa também tem acesso ao chave.key). O que
isso protege de verdade: exposição ACIDENTAL - alguém abrindo um .env
sem querer, um print de tela, um arquivo indo parar num lugar errado
(backup, repositório git, etc.) - nesses casos, sem o chave.key ao
lado, o conteúdo de config.dat é só bytes ilegíveis.
"""
import json
import logging
import os
import sys
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("alertas.config_seguro")


def _base_path_app() -> str:
    """Mesma lógica do _base_path_app() do alertas_gui.py, duplicada aqui
    de propósito (não importada de lá) pra evitar import circular - esse
    módulo precisa poder ser importado tanto pelo alertas_gui.py quanto
    pelo alerta_core/cliente.py, e alertas_gui.py importa coisas de
    alerta_core."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # 2 níveis acima: core/config_seguro.py -> core/ -> pasta do programa
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_CAMINHO_CHAVE_FERNET = os.path.join(_base_path_app(), "chave.key")
_CAMINHO_CONFIG_DAT = os.path.join(_base_path_app(), "config.dat")
_config_dat_cache: Optional[dict] = None


def obter_ou_criar_chave_fernet() -> bytes:
    """Lê a chave de chave.key - cria uma nova (e salva) se ainda não
    existir. Esse arquivo precisa ficar junto do config.dat sempre - sem
    ele, o conteúdo cifrado não pode ser recuperado (nem por mim, nem por
    ninguém - não tem "esqueci a senha" em criptografia simétrica)."""
    if os.path.exists(_CAMINHO_CHAVE_FERNET):
        with open(_CAMINHO_CHAVE_FERNET, "rb") as f:
            return f.read().strip()
    chave = Fernet.generate_key()
    with open(_CAMINHO_CHAVE_FERNET, "wb") as f:
        f.write(chave)
    logger.warning(
        "Nova chave de criptografia gerada em chave.key (primeira vez que "
        "algo foi salvo em config.dat). NÃO apague nem compartilhe esse "
        "arquivo - sem ele, o config.dat vira ilegível pra sempre."
    )
    return chave


def carregar_config_dat(forcar_releitura: bool = False) -> dict:
    """Decifra e carrega o config.dat inteiro como um dict (com cache em
    memória, pra não ficar decifrando o arquivo a cada consulta). Retorna
    {} se o arquivo ainda não existir (nada migrado ainda) ou se não
    puder ser decifrado (chave errada/arquivo corrompido) - nesse caso
    despenca de volta pros .env normais pra tudo, sem travar o
    programa."""
    global _config_dat_cache
    if _config_dat_cache is not None and not forcar_releitura:
        return _config_dat_cache
    if not os.path.exists(_CAMINHO_CONFIG_DAT):
        _config_dat_cache = {}
        return _config_dat_cache
    try:
        chave = obter_ou_criar_chave_fernet()
        f = Fernet(chave)
        with open(_CAMINHO_CONFIG_DAT, "rb") as arq:
            conteudo_cifrado = arq.read()
        conteudo_decifrado = f.decrypt(conteudo_cifrado)
        _config_dat_cache = json.loads(conteudo_decifrado.decode("utf-8"))
    except InvalidToken:
        logger.error(
            "Não consegui decifrar config.dat - a chave em chave.key não "
            "bate com a que cifrou esse arquivo (ou o arquivo está "
            "corrompido). As configurações que estariam lá não vão ser "
            "encontradas - caindo de volta pros arquivos .env normais "
            "pra elas."
        )
        _config_dat_cache = {}
    except Exception:
        logger.exception("Erro inesperado ao ler config.dat")
        _config_dat_cache = {}
    return _config_dat_cache


def salvar_config_dat(dados: dict) -> None:
    """Cifra o dict inteiro e grava/sobrescreve config.dat."""
    global _config_dat_cache
    chave = obter_ou_criar_chave_fernet()
    f = Fernet(chave)
    conteudo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
    conteudo_cifrado = f.encrypt(conteudo)
    with open(_CAMINHO_CONFIG_DAT, "wb") as arq:
        arq.write(conteudo_cifrado)
    _config_dat_cache = dados


def definir_valor_config_dat(chave: str, valor: str) -> None:
    """Adiciona/atualiza UMA chave em config.dat, sem apagar as outras já
    migradas."""
    dados = dict(carregar_config_dat())
    dados[chave] = valor
    salvar_config_dat(dados)


def remover_valor_config_dat(chave: str) -> bool:
    dados = dict(carregar_config_dat())
    if chave not in dados:
        return False
    del dados[chave]
    salvar_config_dat(dados)
    return True


def obter_valor_config(chave: str, padrao: str = "") -> str:
    """Busca um valor em config.dat (cifrado) primeiro; se a chave não
    estiver lá, usa o "padrao" informado (tipicamente lido de um .env
    comum, mantendo compatibilidade com o que ainda não foi migrado)."""
    return carregar_config_dat().get(chave, padrao)


def listar_chaves_config_dat() -> list:
    """Lista só os NOMES das chaves cadastradas (nunca os valores) - pra
    uso em telas administrativas, sem nunca expor a credencial de
    verdade pela interface."""
    return sorted(carregar_config_dat().keys())
