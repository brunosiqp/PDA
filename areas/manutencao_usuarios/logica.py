"""Manutenção de Usuários - lógica (cadastro/desativação em produção (bancos, Movidesk, login do PDA), diagnóstico multi-banco e auditoria).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import json
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from dotenv import dotenv_values
import requests

from areas.emails.logica import _enviar_email_boas_vindas
from core.db_utils import _rollback_if_possible
from core.db_utils import conectar_banco
from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_secao_central
from nucleo.movidesk import MOVIDESK_API_BASE
from nucleo.movidesk import MOVIDESK_AREA_PARA_ACCESS_PROFILE
from nucleo.movidesk import MOVIDESK_AREA_PARA_TEAMS
from nucleo.movidesk import ManutencaoUsuariosConfigError
from nucleo.movidesk import _movidesk_api_token
from nucleo.movidesk import ocultar_token
from nucleo.usuarios import SESSIONS
from nucleo.usuarios import USUARIOS_WEB
from nucleo.usuarios import _salvar_usuarios

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py
logger_administracao = logging.getLogger("alertas.administracao")  # mesmo logger configurado no alertas_gui.py


# ---------------------------------------------------------------------------
# Manutenção de Usuários (Beta) - cadastro/desativação de usuário
# administrador em produção, nos bancos de cada cliente
# ---------------------------------------------------------------------------
# Porta pro PDA da ferramenta desktop "QG de Manutenção de Usuário"
# (Tkinter, standalone) que o Igor já usava - mesma lógica de negócio
# (config.py + service.py + security.py de lá), só trocando a UI Tkinter
# pelas rotas web e reaproveitando os helpers de banco que o PDA já tem
# (core.db_utils) em vez da classe DatabaseRepository própria que o
# original tinha.
#
# Config trazida como arquivos PRÓPRIOS (pedido explícito - futuramente
# a ideia é unificar tudo num .env só, mas por enquanto fica separado):
#   - manutencao_usuarios_bases.json  (área -> tenant -> produto -> banco)
#   - .env.manutencao_usuarios.shared        (queries, comuns a todas as áreas)
#   - .env.manutencao_usuarios.suporte       (credenciais de conexão, área Suporte)
#   - .env.manutencao_usuarios.monitoramento (credenciais de conexão, área Monitoramento)
# Nomeados assim (em vez de ".env.suporte"/".env.monitoramento" como no
# projeto original) porque o PDA JÁ TINHA um ".env.monitoramento" próprio
# pra outra coisa (banco de monitoramento interno) - colidiria.
MANUTENCAO_USUARIOS_AREAS = ("suporte", "monitoramento")
MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL = "SenhaInicial@1"  # só informativo - a senha já vem hasheada fixa nas próprias queries de INSERT

MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS = {
    "NFe": (
        "db_nfe_insert_emis1", "db_nfe_insert_emis2", "db_nfe_insert_dest1", "db_nfe_insert_dest2",
        "db_nfe_insert_trans1", "db_nfe_insert_trans2", "db_nfe_insert_oper",
    ),
    "NFe2": (
        "db_nfe2_insert_emis1", "db_nfe2_insert_emis2", "db_nfe2_insert_dest1", "db_nfe2_insert_dest2",
        "db_nfe2_insert_trans1", "db_nfe2_insert_trans2", "db_nfe2_insert_oper",
    ),
    "NFCe": (
        "db_nfce_insert_emis1", "db_nfce_insert_emis2", "db_nfce_insert_dest1", "db_nfce_insert_dest2",
        "db_nfce_insert_trans1", "db_nfce_insert_trans2", "db_nfce_insert_oper",
    ),
}
MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS = {"CTe", "CTe2", "NFSeOut"}
MANUTENCAO_USUARIOS_FIXED_MDFE_ROLES = (1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13)
MANUTENCAO_USUARIOS_SUPPORTED_PRODUCTS = (
    set(MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS) | MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS | {"MDFe", "NFSeIn"}
)

# mesmo padrão de caracteres proibidos do app original (evita quebrar as
# queries parametrizadas com caractere estranho no nome/login)
_MANUTENCAO_USUARIOS_CARACTERES_INVALIDOS = re.compile(r"[\[\]{}!#$%¨&*()+='\"\\|?/;,:]")

_manutencao_usuarios_bases_cache: Optional[dict] = None
_manutencao_usuarios_env_cache: dict = {}




class ManutencaoUsuariosSkip(RuntimeError):
    """Motivo de SKIP visível pro operador (ex.: usuário já existe,
    usuário não encontrado) - diferente de um erro de banco de verdade."""
    pass


def _manutencao_usuarios_sanitize(mensagem: object) -> str:
    """Porta de security.sanitize_message do projeto original - nunca
    deixa senha/PWD vazar pra mensagem de resultado ou log de auditoria,
    mesmo que apareça dentro de uma exceção de conexão do pyodbc."""
    texto = str(mensagem)
    for padrao in (
        re.compile(r"(PWD|PASSWORD|SENHA)\s*=\s*[^;,\s]+", re.IGNORECASE),
        re.compile(r"(db_password_[A-Za-z0-9_]+)\s*=\s*[^\s]+", re.IGNORECASE),
    ):
        texto = padrao.sub(lambda m: f"{m.group(1)}=<oculto>", texto)
    texto = ocultar_token(texto)  # 3.2.7.1: o erro do requests trazia a URL com o token da API do Movidesk
    return texto.replace("\r", " ").replace("\n", " ").strip()


def _carregar_manutencao_usuarios_bases() -> dict:
    global _manutencao_usuarios_bases_cache
    if _manutencao_usuarios_bases_cache is not None:
        return _manutencao_usuarios_bases_cache
    caminho = os.path.join(_base_path_app(), "manutencao_usuarios_bases.json")
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            dados = json.load(f)
    except Exception as exc:
        raise ManutencaoUsuariosConfigError(f"Falha ao carregar manutencao_usuarios_bases.json: {exc}") from exc

    if not isinstance(dados, dict):
        raise ManutencaoUsuariosConfigError("manutencao_usuarios_bases.json precisa conter um objeto JSON.")
    for area in MANUTENCAO_USUARIOS_AREAS:
        if area not in dados or not isinstance(dados[area], dict):
            raise ManutencaoUsuariosConfigError(f"Área obrigatória ausente em manutencao_usuarios_bases.json: {area}")
        for tenant, produtos in dados[area].items():
            if not isinstance(tenant, str) or not isinstance(produtos, dict):
                raise ManutencaoUsuariosConfigError(f"Tenant inválido em manutencao_usuarios_bases.json: {tenant}")
            for produto, database in produtos.items():
                if not isinstance(produto, str) or not isinstance(database, str) or not database:
                    raise ManutencaoUsuariosConfigError(
                        f"Produto/banco inválido em manutencao_usuarios_bases.json: {tenant}/{produto}"
                    )
    _manutencao_usuarios_bases_cache = dados
    return dados


def _manutencao_usuarios_build_targets(areas: tuple) -> list:
    """Monta a lista de alvos (área, tenant, produto, banco) pras áreas
    pedidas - mesmo formato de "target" do projeto original, só que como
    dict em vez de dataclass Target (padrão já usado no resto do PDA)."""
    bases = _carregar_manutencao_usuarios_bases()
    targets = []
    for area in areas:
        for tenant, produtos in bases.get(area, {}).items():
            for produto, database in produtos.items():
                targets.append({"area": area, "tenant": tenant, "produto": produto, "database": database})
    return targets


def _manutencao_usuarios_load_env(area: str) -> dict:
    if area in _manutencao_usuarios_env_cache:
        return _manutencao_usuarios_env_cache[area]

    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seções
    # [manutencao_usuarios_shared] + [manutencao_usuarios_{area}]) - cai
    # pros dois .env.manutencao_usuarios.* tradicionais se QUALQUER uma
    # das duas seções não existir lá (arquivo ainda não migrado nessa
    # máquina, ver core/config_central.py).
    shared_central = _obter_secao_central("manutencao_usuarios_shared")
    area_central = _obter_secao_central(f"manutencao_usuarios_{area}")
    if shared_central and area_central:
        resultado = {**shared_central, **area_central}
        _manutencao_usuarios_env_cache[area] = resultado
        return resultado

    base = _base_path_app()
    caminho_shared = os.path.join(base, ".env.manutencao_usuarios.shared")
    caminho_area = os.path.join(base, f".env.manutencao_usuarios.{area}")
    if not os.path.exists(caminho_shared):
        raise ManutencaoUsuariosConfigError("Arquivo de configuração não encontrado: .env.manutencao_usuarios.shared")
    if not os.path.exists(caminho_area):
        raise ManutencaoUsuariosConfigError(f"Arquivo de configuração não encontrado: .env.manutencao_usuarios.{area}")
    shared = dotenv_values(caminho_shared)
    valores_area = dotenv_values(caminho_area)
    merged = {**shared, **valores_area}
    resultado = {k: v for k, v in merged.items() if v is not None}
    _manutencao_usuarios_env_cache[area] = resultado
    return resultado


def _manutencao_usuarios_credenciais(area: str, tenant: str) -> list:
    """Devolve uma LISTA de candidatos de conexão pro tenant - normalmente
    só 1 (o principal), mas pode ter um 2º candidato "_fallback" (ex.:
    tenant com 2 servidores válidos, caso do cliente_d em 04/09/2026 - pedido
    do Igor) que só é tentado se o principal falhar ao conectar."""
    env = _manutencao_usuarios_load_env(area)

    def montar(sufixo: str) -> Optional[dict]:
        server = (env.get(f"db_server_{tenant}{sufixo}") or "").strip()
        user = (env.get(f"db_user_{tenant}{sufixo}") or "").strip()
        password = (env.get(f"db_password_{tenant}{sufixo}") or "").strip()
        if not (server and user and password):
            return None
        return {"server": server, "user": user, "password": password}

    principal = montar("")
    if not principal:
        faltando = [
            chave for chave, valor in {
                f"db_server_{tenant}": env.get(f"db_server_{tenant}"),
                f"db_user_{tenant}": env.get(f"db_user_{tenant}"),
                f"db_password_{tenant}": env.get(f"db_password_{tenant}"),
            }.items() if not (valor or "").strip()
        ]
        raise ManutencaoUsuariosConfigError(f"Credenciais ausentes: {', '.join(faltando)}")

    candidatos = [principal]
    fallback = montar("_fallback")
    if fallback:
        candidatos.append(fallback)
    return candidatos


def _manutencao_usuarios_query(area: str, key: str) -> str:
    valor = (_manutencao_usuarios_load_env(area).get(key) or "").strip()
    if not valor:
        raise ManutencaoUsuariosConfigError(f"Query ausente: {key}")
    return valor


def _manutencao_usuarios_prefix(produto: str) -> str:
    return f"db_{produto.lower()}"


def _manutencao_usuarios_permission_query_keys(produto: str) -> list:
    if produto in MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS:
        return list(MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS[produto])
    if produto in MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS:
        prefix = _manutencao_usuarios_prefix(produto)
        return [f"{prefix}_select_max_role", f"{prefix}_insert_permis"]
    if produto == "MDFe":
        return ["db_mdfe_insert_permis"]
    return []


def _manutencao_usuarios_validate_required_queries(area: str, produto: str, action: str) -> None:
    prefix = _manutencao_usuarios_prefix(produto)
    required = [f"{prefix}_select_id"]
    if action == "cad":
        required.extend([f"{prefix}_select_login", f"{prefix}_insert_usuar"])
        required.extend(_manutencao_usuarios_permission_query_keys(produto))
    else:
        required.append(f"{prefix}_delete")
    for key in required:
        _manutencao_usuarios_query(area, key)


def _manutencao_usuarios_find_user_id(conn, area: str, produto: str, nome: str, login: str, missing_message: str) -> int:
    query = _manutencao_usuarios_query(area, f"{_manutencao_usuarios_prefix(produto)}_select_id")
    linhas, _colunas = executar_query(conn, query, params=(nome, login), fetch=True, raise_on_error=True)
    if not linhas:
        raise ManutencaoUsuariosSkip(missing_message)
    return int(linhas[0][0])


def _manutencao_usuarios_max_role(conn, area: str, produto: str) -> int:
    query = _manutencao_usuarios_query(area, f"{_manutencao_usuarios_prefix(produto)}_select_max_role")
    linhas, _colunas = executar_query(conn, query, fetch=True, raise_on_error=True)
    if not linhas:
        raise ManutencaoUsuariosSkip("Não foi possível coletar as permissões do produto.")
    return int(linhas[0][0])


def _manutencao_usuarios_grant_permissions(conn, area: str, produto: str, user_id: int) -> None:
    if produto in MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS:
        for key in MANUTENCAO_USUARIOS_NFE_PERMISSION_KEYS[produto]:
            executar_query(conn, _manutencao_usuarios_query(area, key), params=user_id, raise_on_error=True)
        return
    if produto in MANUTENCAO_USUARIOS_ROLE_PERMISSION_PRODUCTS:
        max_role = _manutencao_usuarios_max_role(conn, area, produto)
        query = _manutencao_usuarios_query(area, f"{_manutencao_usuarios_prefix(produto)}_insert_permis")
        for role in range(1, max_role + 1):
            executar_query(conn, query, params=(role, user_id), raise_on_error=True)
        return
    if produto == "MDFe":
        query = _manutencao_usuarios_query(area, "db_mdfe_insert_permis")
        for role in MANUTENCAO_USUARIOS_FIXED_MDFE_ROLES:
            executar_query(conn, query, params=(role, user_id), raise_on_error=True)


def _manutencao_usuarios_register(conn, area: str, produto: str, nome: str, login: str) -> str:
    prefix = _manutencao_usuarios_prefix(produto)
    select_login = _manutencao_usuarios_query(area, f"{prefix}_select_login")
    duplicadas, _colunas = executar_query(conn, select_login, params=login, fetch=True, raise_on_error=True)
    if duplicadas:
        raise ManutencaoUsuariosSkip("Usuário já existe neste produto.")

    executar_query(
        conn, _manutencao_usuarios_query(area, f"{prefix}_insert_usuar"),
        params=(nome, login), raise_on_error=True,
    )
    user_id = _manutencao_usuarios_find_user_id(
        conn, area, produto, nome, login, "Não foi possível localizar o ID do usuário."
    )
    _manutencao_usuarios_grant_permissions(conn, area, produto, user_id)
    return "Cadastro realizado."


def _manutencao_usuarios_deactivate(conn, area: str, produto: str, nome: str, login: str) -> str:
    prefix = _manutencao_usuarios_prefix(produto)
    user_id = _manutencao_usuarios_find_user_id(conn, area, produto, nome, login, "Usuário não encontrado.")
    executar_query(conn, _manutencao_usuarios_query(area, f"{prefix}_delete"), params=user_id, raise_on_error=True)
    return "Desativação realizada."




def _movidesk_api_buscar_pessoa_por_username(login: str) -> Optional[dict]:
    """Busca a pessoa no Movidesk pelo userName (login/e-mail) via API,
    pra achar o GUID dela - necessário pra DESATIVAR (a API pede o id,
    não o userName), já que a tabela SQL 'usuarios' que o PDA já usa não
    guarda esse GUID (só um id numérico próprio, diferente)."""
    token = _movidesk_api_token()
    resposta = requests.get(
        MOVIDESK_API_BASE,
        params={"token": token, "$filter": f"userName eq '{login}'"},
        timeout=20,
    )
    resposta.raise_for_status()
    resultado = resposta.json()
    if isinstance(resultado, list) and resultado:
        return resultado[0]
    return None


def _movidesk_api_criar_pessoa(nome: str, login: str, area_valor: str, operador: str) -> dict:
    """Cria a pessoa no Movidesk via API - senha inicial e demais valores
    fixos seguem o mesmo padrão dos cadastros em banco (mesma senha
    padrão exibida na tela, mesmo texto de 'oriente a trocar')."""
    token = _movidesk_api_token()
    access_profile = MOVIDESK_AREA_PARA_ACCESS_PROFILE.get(area_valor, "MONITORAMENTO")
    teams = MOVIDESK_AREA_PARA_TEAMS.get(area_valor, ["MONITORAMENTO"])
    corpo = {
        "isActive": True,
        "personType": 1,
        "profileType": 1,
        "accessProfile": access_profile,
        "businessName": nome,
        "userName": login,
        "password": MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL,
        "role": "Assistente",
        "cultureId": "pt-BR",
        "timeZoneId": "America/Sao_Paulo",
        "observations": f"Usuário criado via PDA (Manutenção de Usuários) por {operador} em {datetime.now().strftime('%d/%m/%Y %H:%M')}.",
        "emails": [{"emailType": "Profissional", "email": login, "isDefault": True}],
        "teams": teams,
    }
    resposta = requests.post(
        MOVIDESK_API_BASE, params={"token": token}, json=corpo, timeout=30,
    )
    if resposta.status_code == 400:
        # 3.2.7.1: o cadastro do Suporte sempre voltava 400 (o do Monitoramento passava). O perfil de acesso
        # "SUPORTE" foi um palpite (só "MONITORAMENTO" tinha sido confirmado). Antes de desistir, pega o perfil de
        # acesso que os agentes ativos da mesma equipe usam no Movidesk e tenta de novo uma vez com ele.
        perfil_da_equipe = _movidesk_perfil_de_acesso_da_equipe(token, teams[0])
        if perfil_da_equipe and perfil_da_equipe != access_profile:
            logger.info("Movidesk recusou o perfil de acesso '%s'; tentando de novo com '%s' (usado pela equipe %s).",
                        access_profile, perfil_da_equipe, teams[0])
            corpo["accessProfile"] = perfil_da_equipe
            resposta = requests.post(MOVIDESK_API_BASE, params={"token": token}, json=corpo, timeout=30)
    if resposta.status_code >= 400:
        # o motivo vem no corpo da resposta (antes só aparecia "400 Bad Request", sem dizer o que estava errado)
        raise MovideskRecusou(f"{resposta.status_code} · {_movidesk_motivo(resposta)} "
                              f"(perfil de acesso '{corpo['accessProfile']}', equipe {', '.join(teams)})")
    return resposta.json()


class MovideskRecusou(Exception):
    """A API do Movidesk respondeu erro; a mensagem já vem com o motivo e sem o token."""


def _movidesk_motivo(resposta) -> str:
    try:
        dados = resposta.json()
    except ValueError:
        dados = None
    if isinstance(dados, dict):
        partes = [str(dados.get(k)) for k in ("message", "Message", "error", "errors", "ModelState") if dados.get(k)]
        texto = " · ".join(partes) or json.dumps(dados, ensure_ascii=False)
    else:
        texto = (resposta.text or "").strip() or "sem detalhe na resposta"
    return ocultar_token(" ".join(texto.split()))[:400]


def _sem_acento(texto: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode().strip().upper()


def _movidesk_perfil_de_acesso_da_equipe(token: str, equipe: str) -> Optional[str]:
    """Perfil de acesso (accessProfile) mais usado pelos agentes ativos que estão na `equipe` no Movidesk.
    Uma consulta só (até 100 agentes); qualquer falha devolve None e o cadastro segue com o erro original."""
    try:
        resposta = requests.get(MOVIDESK_API_BASE, params={
            "token": token, "$select": "id,accessProfile,teams",
            "$filter": "profileType eq 1 and isActive eq true", "$top": 100,
        }, timeout=30)
        if resposta.status_code >= 400:
            return None
        contagem = {}
        alvo = _sem_acento(equipe)
        for pessoa in resposta.json() or []:
            perfil = (pessoa.get("accessProfile") or "").strip()
            if perfil and any(_sem_acento(t) == alvo for t in pessoa.get("teams") or []):
                contagem[perfil] = contagem.get(perfil, 0) + 1
        return max(contagem, key=contagem.get) if contagem else None
    except Exception:
        logger.warning("Não foi possível consultar o perfil de acesso da equipe %s no Movidesk.", equipe)
        return None


def _movidesk_api_desativar_pessoa(person_id: str) -> None:
    token = _movidesk_api_token()
    resposta = requests.patch(
        MOVIDESK_API_BASE, params={"token": token, "id": person_id},
        json={"isActive": False}, timeout=20,
    )
    resposta.raise_for_status()


def _manutencao_usuarios_execute_movidesk(action: str, nome: str, login: str, area_valor: str, operador: str) -> dict:
    """Roda o cadastro/desativação da PESSOA no Movidesk via API - formato
    de retorno igual ao de um "alvo" de banco (area/tenant/produto/
    database/status/message), pra entrar na mesma tabela de prévia e de
    resultado sem precisar de UI separada."""
    linha_base = {"area": area_valor, "tenant": "Movidesk", "produto": "Pessoa (API)", "database": "(via API pública)"}
    try:
        if action == "cad":
            resultado = _movidesk_api_criar_pessoa(nome, login, area_valor, operador)
            person_id = resultado.get("id", "?")
            return {**linha_base, "status": "success", "message": f"Pessoa criada no Movidesk (id {person_id})."}
        else:
            pessoa = _movidesk_api_buscar_pessoa_por_username(login)
            if not pessoa:
                return {**linha_base, "status": "skipped", "message": "Pessoa não encontrada no Movidesk pelo login informado."}
            if pessoa.get("isActive") is False:
                return {**linha_base, "status": "skipped", "message": "Pessoa já estava desativada no Movidesk."}
            _movidesk_api_desativar_pessoa(pessoa["id"])
            return {**linha_base, "status": "success", "message": f"Pessoa desativada no Movidesk (id {pessoa['id']})."}
    except ManutencaoUsuariosConfigError as exc:
        return {**linha_base, "status": "skipped", "message": _manutencao_usuarios_sanitize(exc)}
    except MovideskRecusou as exc:
        return {**linha_base, "status": "error", "message": f"O Movidesk recusou: {_manutencao_usuarios_sanitize(exc)}"}
    except requests.exceptions.RequestException as exc:
        return {**linha_base, "status": "error", "message": f"Falha na API do Movidesk: {_manutencao_usuarios_sanitize(exc)}"}
    except Exception as exc:
        logger.exception("Erro inesperado na integração Movidesk (Manutenção de Usuários)")
        return {**linha_base, "status": "error", "message": _manutencao_usuarios_sanitize(exc)}


def _manutencao_usuarios_verificar_target(login: str, target: dict) -> dict:
    """SÓ CONSULTA (nunca insere/desativa nada) se `login` já existe no
    banco desse alvo - reaproveita a MESMA query de checagem de
    duplicidade (`{prefix}_select_login`) que o cadastro já usa pra
    evitar duplicar usuário, só que aqui é sempre somente-leitura. Usado
    pelo modo "Diagnóstico" (cruzamento de usuários) - pedido explícito
    do Igor de ver, pra uma pessoa só, em quais bancos ela existe.
    status "success" = existe nesse banco, "skipped" = não existe (não é
    um erro, só informação), "error" = não deu pra nem checar."""
    produto = target["produto"]
    area = target["area"]
    linha_base = dict(target)
    if produto not in MANUTENCAO_USUARIOS_SUPPORTED_PRODUCTS:
        return {**linha_base, "status": "skipped", "message": "Produto ainda não suportado nesse diagnóstico."}

    try:
        prefix = _manutencao_usuarios_prefix(produto)
        query = _manutencao_usuarios_query(area, f"{prefix}_select_login")
        candidatos = _manutencao_usuarios_credenciais(area, target["tenant"])
    except ManutencaoUsuariosConfigError as exc:
        return {**linha_base, "status": "error", "message": _manutencao_usuarios_sanitize(exc)}

    conn = None
    for credenciais in candidatos:
        conn = conectar_banco(
            credenciais["server"], target["database"], credenciais["user"], credenciais["password"],
            raise_on_error=False,
        )
        if conn:
            break
    if not conn:
        return {**linha_base, "status": "error", "message": f"Falha ao conectar no banco {target['database']}"}
    try:
        linhas, _colunas = executar_query(conn, query, params=login, fetch=True, raise_on_error=True)
        if linhas:
            return {**linha_base, "status": "success", "message": "Encontrado nesse banco."}
        return {**linha_base, "status": "skipped", "message": "Não encontrado."}
    except Exception as exc:
        return {**linha_base, "status": "error", "message": _manutencao_usuarios_sanitize(exc)}
    finally:
        fechar_conexao(conn)


def _manutencao_usuarios_diagnostico(login: str) -> dict:
    """Cruza, pra UM login só: vínculo com o Movidesk (via API) e
    presença em TODOS os bancos de cliente (suporte + monitoramento de
    uma vez) - o "cruzamento de usuários" pedido pelo Igor. Roda os
    ~33 bancos em paralelo (ThreadPoolExecutor) - em sequência (como o
    cadastro/desativação fazem, um por um, de propósito pra não
    sobrecarregar) ficaria bem mais lento pra uma consulta que é só
    diagnóstico, sem gravar nada."""
    targets = _manutencao_usuarios_build_targets(MANUTENCAO_USUARIOS_AREAS)
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados_bancos = list(executor.map(
            lambda t: _manutencao_usuarios_verificar_target(login, t), targets,
        ))
    resultados_bancos.sort(key=lambda r: (r["area"], r["tenant"], r["produto"]))

    pessoa_movidesk = None
    erro_movidesk = None
    try:
        pessoa_movidesk = _movidesk_api_buscar_pessoa_por_username(login)
    except ManutencaoUsuariosConfigError as exc:
        erro_movidesk = _manutencao_usuarios_sanitize(exc)
    except requests.exceptions.RequestException as exc:
        erro_movidesk = f"Falha na API do Movidesk: {_manutencao_usuarios_sanitize(exc)}"
    except Exception as exc:
        logger.exception("Erro inesperado ao consultar Movidesk no Diagnóstico")
        erro_movidesk = _manutencao_usuarios_sanitize(exc)

    return {
        "resultados_bancos": resultados_bancos,
        "movidesk": pessoa_movidesk,
        "erro_movidesk": erro_movidesk,
    }


def _manutencao_usuarios_execute_pda_login(action: str, usuario_pda: str, nome: str, senha_pda: str, genero: str = "") -> dict:
    """Cria/desativa o LOGIN DO PRÓPRIO PDA (usuarios.json), opcional -
    só roda quando marcado no formulário. MESMA validação que a antiga
    /api/usuarios/criar (removida na 2.32.7.2) e /api/usuarios/alterar-status (regex de
    usuário, tamanho mínimo de senha, checagem de duplicidade) - só que
    chamada direto em vez de via HTTP, pra entrar na mesma leva de
    resultados/prévia dos outros alvos."""
    linha_base = {"area": "-", "tenant": "PDA", "produto": "Login do PDA", "database": "usuarios.json"}
    if action == "cad":
        if not usuario_pda or not re.match(r"^[A-Za-z0-9_.\-]+$", usuario_pda):
            return {**linha_base, "status": "skipped", "message": "Usuário do PDA inválido (use apenas letras, números, . _ -)."}
        if any(u.lower() == usuario_pda.lower() for u in USUARIOS_WEB):
            return {**linha_base, "status": "skipped", "message": "Esse usuário do PDA já existe."}
        if not senha_pda or len(senha_pda) < 4:
            return {**linha_base, "status": "skipped", "message": "Senha do login PDA precisa ter ao menos 4 caracteres."}
        USUARIOS_WEB[usuario_pda] = {
            "senha": senha_pda, "nome": nome, "admin": False,
            "pode_manutencao_alertas": False, "pode_relatorios_cliente_a": False, "pode_dash_financeiro": False,
            "pode_manutencao_rejeicoes": False, "pode_dados_sensiveis": False, "pode_manutencao_relatorios": False,
            "pode_manutencao_usuarios": False, "ativo": True, "atribuicao": "Suporte",
            "genero": genero if genero in ("M", "F") else "",
        }
        _salvar_usuarios(USUARIOS_WEB)
        return {**linha_base, "status": "success", "message": f"Login '{usuario_pda}' criado no PDA (sem permissões extras - ajuste em Usuários se precisar)."}
    else:
        if usuario_pda not in USUARIOS_WEB:
            return {**linha_base, "status": "skipped", "message": f"Usuário do PDA '{usuario_pda}' não encontrado."}
        if not USUARIOS_WEB[usuario_pda].get("ativo", True):
            return {**linha_base, "status": "skipped", "message": f"Login '{usuario_pda}' já estava desativado no PDA."}
        from nucleo.desativacao import avisar_mudanca, marcar_status  # aviso pra todo mundo (3.1.5.0)
        marcar_status(usuario_pda, False, "Manutenção de Usuários")
        _salvar_usuarios(USUARIOS_WEB)
        from areas.ranks_produtos.logica import arquivar_pessoa  # sai dos Rankings (3.3.1.0)
        arquivar_pessoa(usuario_pda, "Manutenção de Usuários")
        avisar_mudanca(usuario_pda)
        for token in [t for t, s in SESSIONS.items() if s["usuario"] == usuario_pda]:
            SESSIONS.pop(token, None)
        return {**linha_base, "status": "success", "message": f"Login '{usuario_pda}' desativado no PDA (sessões ativas encerradas)."}


def _manutencao_usuarios_execute_target(action: str, nome: str, login: str, target: dict) -> dict:
    """Executa (ou pula) UM alvo - mesma máquina de estados do
    service.py original: SUCCESS / SKIPPED / ERROR, cada alvo com sua
    própria conexão e commit/rollback isolado, então uma falha num
    banco não afeta os outros alvos já processados ou os que vêm
    depois.

    Suporta MAIS DE UM candidato de conexão por tenant (ver
    _manutencao_usuarios_credenciais) - tenta o principal, e só tenta o
    "_fallback" (se existir) se o principal falhar ao CONECTAR (não em
    caso de erro depois de já conectado, tipo erro de permissão/SQL -
    aí o problema não é o servidor, então tentar outro não ajudaria e só
    mascararia o erro de verdade). Cada tentativa de conexão fica
    registrada em "tentativas_conexao" (server/database/user/password em
    texto puro, INTENCIONALMENTE sem sanitizar - pedido explícito do
    Igor pra conseguir ver depois, no log, qual das duas credenciais
    funcionou) - isso NÃO aparece na mensagem devolvida pro PDA/usuário,
    só no log de auditoria (ver _manutencao_usuarios_executar)."""
    produto = target["produto"]
    area = target["area"]
    if produto not in MANUTENCAO_USUARIOS_SUPPORTED_PRODUCTS:
        return {**target, "status": "skipped", "message": f"Produto ainda não suportado: {produto}"}

    try:
        _manutencao_usuarios_validate_required_queries(area, produto, action)
        candidatos = _manutencao_usuarios_credenciais(area, target["tenant"])
    except ManutencaoUsuariosConfigError as exc:
        return {**target, "status": "skipped", "message": _manutencao_usuarios_sanitize(exc)}

    tentativas_conexao = []
    conn = None
    for credenciais in candidatos:
        conn_tentativa = conectar_banco(
            credenciais["server"], target["database"], credenciais["user"], credenciais["password"],
            raise_on_error=False,
        )
        tentativas_conexao.append({
            "db_server": credenciais["server"], "db_name": target["database"],
            "db_user": credenciais["user"], "db_password": credenciais["password"],
            "sucesso": bool(conn_tentativa),
        })
        if conn_tentativa:
            conn = conn_tentativa
            break
    # só carrega o detalhe de credenciais (com senha em texto puro) quando
    # é realmente informativo: teve mais de 1 candidato (então importa
    # registrar qual funcionou) OU nenhum conectou (erro, vale registrar
    # o que foi tentado). No caminho comum (1 candidato só, conectou de
    # primeira) fica None, e a senha nunca chega nem perto do log -
    # mesmo comportamento de antes desse fallback existir.
    detalhe_tentativas = tentativas_conexao if (len(candidatos) > 1 or not conn) else None
    if not conn:
        return {
            **target, "status": "error", "message": f"Falha ao conectar no banco {target['database']}",
            "tentativas_conexao": detalhe_tentativas,
        }
    try:
        try:
            if action == "cad":
                mensagem = _manutencao_usuarios_register(conn, area, produto, nome, login)
            else:
                mensagem = _manutencao_usuarios_deactivate(conn, area, produto, nome, login)
            conn.commit()
            return {
                **target, "status": "success", "message": _manutencao_usuarios_sanitize(mensagem),
                "tentativas_conexao": detalhe_tentativas,
            }
        except ManutencaoUsuariosSkip as exc:
            _rollback_if_possible(conn)
            return {
                **target, "status": "skipped", "message": _manutencao_usuarios_sanitize(exc),
                "tentativas_conexao": detalhe_tentativas,
            }
        except Exception as exc:
            _rollback_if_possible(conn)
            return {
                **target, "status": "error", "message": _manutencao_usuarios_sanitize(exc),
                "tentativas_conexao": detalhe_tentativas,
            }
    finally:
        fechar_conexao(conn)


def _manutencao_usuarios_validar_texto(rotulo: str, valor: str, tamanho_max: int) -> Optional[str]:
    """Mesma validação de UI do projeto original (lá era feita no
    Tkinter, aqui vira validação de servidor) - devolve a mensagem de
    erro, ou None se estiver tudo certo."""
    if not valor or valor.upper() == "NULL":
        return f"{rotulo} não pode ficar vazio."
    if len(valor) > tamanho_max:
        return f"{rotulo} excede o limite de {tamanho_max} caracteres."
    if _MANUTENCAO_USUARIOS_CARACTERES_INVALIDOS.search(valor):
        return f"{rotulo} contém caracteres inválidos."
    return None


def _manutencao_usuarios_log_path() -> str:
    pasta = os.path.join(_base_path_app(), "logs")
    os.makedirs(pasta, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(pasta, f"manutencao_usuarios_{timestamp}.jsonl")


def _manutencao_usuarios_gravar_auditoria(caminho: str, payload: dict) -> None:
    """Log de auditoria em .jsonl, MESMO FORMATO do projeto original
    (start/result/finish) - sempre sanitizado, nunca grava senha, string
    de conexão completa ou query integral. "operator" aqui é o usuário
    LOGADO NO PDA (sessao["usuario"]) - diferente do original, que usava
    getpass.getuser() porque rodava na máquina do próprio operador; como
    agora roda no servidor do PDA, getpass.getuser() pegaria a conta de
    serviço do servidor, não quem realmente clicou o botão."""
    try:
        with open(caminho, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        logger.exception("Não foi possível gravar o log de auditoria de Manutenção de Usuários.")


def _manutencao_usuarios_execute_boas_vindas(nome: str, login: str) -> dict:
    """Dispara o e-mail de boas-vindas pro endereço informado como LOGIN
    do cadastro (normalmente já é o e-mail da pessoa) - só roda quando
    marcado no formulário, e só faz sentido pra ação de cadastro. Manda
    junto os dados de acesso de verdade: o login + a senha padrão que o
    cadastro em banco/Movidesk usa (MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL,
    a mesma exibida na tela). UM acesso só (login+senha) - não dois
    (pedido explícito do Igor em 07/09/2026: mesmo quando também cria
    login no PDA à parte, o e-mail continua mostrando só essas
    credenciais principais)."""
    linha_base = {"area": "-", "tenant": "E-mail", "produto": "Boas-vindas", "database": f"pra {login}"}
    try:
        _enviar_email_boas_vindas(nome, login, login, MANUTENCAO_USUARIOS_SENHA_PADRAO_LABEL)
        return {**linha_base, "status": "success", "message": f"E-mail de boas-vindas enviado pra {login}."}
    except Exception as exc:
        logger.exception("Falha ao enviar e-mail de boas-vindas (cadastro) pra '%s'", login)
        return {**linha_base, "status": "error", "message": f"Falha ao enviar e-mail: {_manutencao_usuarios_sanitize(exc)}"}


def _manutencao_usuarios_executar(
    action: str, areas: tuple, area_valor: str, nome: str, login: str, operador: str,
    incluir_pda: bool = False, usuario_pda: str = "", senha_pda: str = "",
    enviar_boas_vindas: bool = False, genero_pda: str = "",
) -> dict:
    targets = _manutencao_usuarios_build_targets(areas)
    caminho_log = _manutencao_usuarios_log_path()
    _manutencao_usuarios_gravar_auditoria(caminho_log, {
        "event": "start", "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operator": operador, "action": action, "areas": list(areas),
        "nome": nome, "login": login,
        "total_targets": len(targets) + 1 + (1 if incluir_pda else 0) + (1 if enviar_boas_vindas else 0),
    })

    resultados = []

    def _registrar(resultado: dict) -> None:
        tentativas_conexao = resultado.pop("tentativas_conexao", None)
        if tentativas_conexao:
            _manutencao_usuarios_gravar_auditoria(caminho_log, {
                "event": "connection_attempts", "timestamp": datetime.now().isoformat(timespec="seconds"),
                "operator": operador, "area": resultado["area"], "tenant": resultado["tenant"],
                "produto": resultado["produto"], "attempts": tentativas_conexao,
            })
        resultados.append(resultado)
        _manutencao_usuarios_gravar_auditoria(caminho_log, {
            "event": "result", "timestamp": datetime.now().isoformat(timespec="seconds"),
            "operator": operador, "action": action, "area": resultado["area"], "tenant": resultado["tenant"],
            "produto": resultado["produto"], "database": resultado["database"],
            "status": resultado["status"], "message": resultado["message"],
        })

    # 1) Pessoa no Movidesk (API) - sempre roda, junto com o resto (pedido
    # explícito do Igor: "mesma tela, tudo junto"). Vem primeiro porque
    # conceitualmente a identidade deveria existir antes do acesso a cada
    # produto - mas roda isolado como os outros, uma falha aqui não trava
    # os alvos de banco.
    _registrar(_manutencao_usuarios_execute_movidesk(action, nome, login, area_valor, operador))

    # 2) Login do próprio PDA - OPCIONAL, só quando marcado no formulário.
    if incluir_pda:
        _registrar(_manutencao_usuarios_execute_pda_login(action, usuario_pda, nome, senha_pda, genero_pda))

    # 3) E-mail de boas-vindas - OPCIONAL, só no cadastro e só quando
    # marcado. Roda isolado como os outros - se falhar, não impede o
    # resto do cadastro (banco/Movidesk/PDA) de seguir normalmente.
    if action == "cad" and enviar_boas_vindas:
        _registrar(_manutencao_usuarios_execute_boas_vindas(nome, login))

    # 4) Bancos de cada produto/cliente (fluxo já existente)
    for target in targets:
        _registrar(_manutencao_usuarios_execute_target(action, nome, login, target))

    sucesso = sum(1 for r in resultados if r["status"] == "success")
    ignorados = sum(1 for r in resultados if r["status"] == "skipped")
    erros = sum(1 for r in resultados if r["status"] == "error")
    _manutencao_usuarios_gravar_auditoria(caminho_log, {
        "event": "finish", "timestamp": datetime.now().isoformat(timespec="seconds"),
        "operator": operador, "success": sucesso, "skipped": ignorados, "errors": erros,
    })
    logger_administracao.info(
        "Manutenção de Usuários: %s '%s' (%s) por '%s' - %d sucesso(s), %d ignorado(s), %d erro(s). Log: %s",
        "cadastro" if action == "cad" else "desativação", login, "+".join(areas), operador,
        sucesso, ignorados, erros, caminho_log,
    )
    return {
        "resultados": resultados, "sucesso": sucesso, "ignorados": ignorados, "erros": erros,
        "log": os.path.basename(caminho_log),
    }
