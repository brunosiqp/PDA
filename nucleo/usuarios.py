"""Usuários do PDA e sessões - lógica (cadastro de login (usuarios.json) e sessões ativas do servidor web).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import copy
import json
import logging
import os
import threading
import time

from nucleo.caminhos import base_path_app as _base_path_app

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


# ---------------------------------------------------------------------------
# Autenticação do servidor web (sessão simples via cookie, em memória) +
# usuários com papel (admin / visualização), persistidos em usuarios.json
# ---------------------------------------------------------------------------
# Usuários "de fábrica" - só valem na PRIMEIRA vez que o programa roda (pra
# criar o usuarios.json). Depois disso, qualquer alteração feita pela aba
# "Usuários" (senha, admin ou não) é lida/gravada em usuarios.json, do lado
# do alertas_gui.py/.exe - editar essa lista aqui não tem mais efeito depois
# que o arquivo já existir.
USUARIOS_WEB_PADRAO: dict = {
    "igor": {"senha": "troque-esta-senha", "nome": "Igor Leal", "admin": True, "pode_manutencao_alertas": True, "pode_relatorios_cliente_a": True, "pode_dash_financeiro": True, "pode_manutencao_rejeicoes": True, "pode_dados_sensiveis": True, "pode_manutencao_relatorios": True, "pode_manutencao_usuarios": True, "ativo": True, "atribuicao": "Suporte", "genero": "M"},
    "debora": {"senha": "troque-esta-senha", "nome": "Debora Sampaio", "admin": True, "pode_manutencao_alertas": True, "pode_relatorios_cliente_a": True, "pode_dash_financeiro": True, "pode_manutencao_rejeicoes": True, "pode_dados_sensiveis": True, "pode_manutencao_relatorios": True, "pode_manutencao_usuarios": True, "ativo": True, "atribuicao": "Suporte", "genero": "F"},
    "renan": {"senha": "troque-esta-senha", "nome": "renan", "admin": False, "pode_manutencao_alertas": False, "pode_relatorios_cliente_a": False, "pode_dash_financeiro": False, "pode_manutencao_rejeicoes": False, "pode_dados_sensiveis": False, "pode_manutencao_relatorios": False, "pode_manutencao_usuarios": False, "ativo": True, "atribuicao": "Suporte", "genero": ""},
    "ramos": {"senha": "troque-esta-senha", "nome": "ramos", "admin": False, "pode_manutencao_alertas": False, "pode_relatorios_cliente_a": False, "pode_dash_financeiro": False, "pode_manutencao_rejeicoes": False, "pode_dados_sensiveis": False, "pode_manutencao_relatorios": False, "pode_manutencao_usuarios": False, "ativo": True, "atribuicao": "Suporte", "genero": ""},
}

DURACAO_INATIVIDADE_MINUTOS = 90  # desconecta depois de 90 min sem atividade real do usuário
SESSIONS: dict = {}  # token -> {"usuario": str, "admin": bool, "pode_manutencao_alertas": bool, "pode_relatorios_cliente_a": bool, "pode_dash_financeiro": bool, "pode_manutencao_rejeicoes": bool, "pode_dados_sensiveis": bool, "pode_manutencao_relatorios": bool, "pode_manutencao_usuarios": bool, "expira": datetime}


def _caminho_usuarios_json() -> str:
    return os.path.join(_base_path_app(), "usuarios.json")


def _carregar_usuarios() -> dict:
    global _estado_gravado
    caminho = _caminho_usuarios_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = _completar_campos(json.load(f))
            _estado_gravado = copy.deepcopy(dados)
            return dados
        except Exception:
            logger.exception("Não foi possível ler usuarios.json, usando padrão de fábrica.")
    # primeira execução (ou arquivo corrompido): parte do padrão de fábrica
    # e já grava em disco, pra próximas execuções lerem daqui em diante.
    dados = {u: dict(info) for u, info in USUARIOS_WEB_PADRAO.items()}
    _salvar_usuarios(dados)
    return dados


def _completar_campos(dados: dict) -> dict:
    # compatibilidade com usuarios.json de versões anteriores, que
    # não tinham esses campos ainda - assume sem a permissão extra
    for login, info in dados.items():
        info.setdefault("pode_manutencao_alertas", False)
        info.setdefault("pode_relatorios_cliente_a", False)
        info.setdefault("pode_dash_financeiro", False)
        info.setdefault("pode_manutencao_rejeicoes", False)
        info.setdefault("pode_manutencao_relatorios", False)
        info.setdefault("pode_manutencao_usuarios", False)
        info.setdefault("usuario_movidesk_id", None)
        info.setdefault("email", None)
        info.setdefault("data_inicio", None)
        info.setdefault("pode_feedbacks", False)
        info.setdefault("pode_ver_logs", False)
        info.setdefault("pode_indicadores_mensais", False)
        info.setdefault("pode_reprocessamento_cte2", False)
        info.setdefault("pode_nnu_enchanced", False)
        info.setdefault("pode_editar_central", False)  # editar a Central de Monitores (3.2.8.0)
        info.setdefault("pode_publicar_comunidade", False)
        info.setdefault("pode_servicos_adm", False)  # Calendário de GMUD's e Indicadores Serviços (3.3.1.0)  # publicar na Comunidade sem ser admin (3.3.0.0)
        info.setdefault("ativo", True)
        # nome de exibição (usado no "Bem-vindo, X" e em qualquer
        # lugar que mostre quem é a pessoa) é separado do login
        # (usado só pra entrar, nunca editável) - quem já existia
        # antes dessa separação recebe o próprio login como nome
        # inicial, editável dali em diante por um admin.
        info.setdefault("nome", login)
        # atribuicao da pessoa dentro da operacao - usado no perfil
        # dela; todo mundo comeca como "Suporte" por padrao, o admin
        # ajusta manualmente quem e "Monitoramento" via Editar usuario
        info.setdefault("atribuicao", "Suporte")
        # genero usado so pra flexao de texto (Bem-vindo/Bem-vinda,
        # Administrador/Administradora) - vazio = nao informado,
        # nesse caso usa uma forma neutra em vez de forcar
        # masculino ou feminino
        info.setdefault("genero", "")
        # "pode_string_connections" virou "pode_dados_sensiveis" (agora
        # cobre String Connections E Criptografia de Dados Sensíveis
        # juntos) - quem já tinha a permissão antiga marcada continua
        # com acesso, sem precisar marcar de novo manualmente.
        if "pode_dados_sensiveis" not in info:
            info["pode_dados_sensiveis"] = info.pop("pode_string_connections", False)
        else:
            info.pop("pode_string_connections", None)
    return dados


_trava_gravacao_usuarios = threading.Lock()
# Como estava o usuarios.json na última vez que este PDA leu ou gravou (3.2.8.1). Se, na hora de gravar, o arquivo
# estiver diferente disso, alguém mexeu nele por fora (outro PDA aberto na mesma pasta, edição à mão...): o que mudou
# lá e este PDA não mexeu é mantido, em vez de ser sobrescrito pela cópia da memória. Antes, uma sincronização com o
# Movidesk (que grava os cargos) desfazia a equipe trocada pelo outro PDA.
_estado_gravado = None


def _mesclar_alteracoes_externas(dados: dict, anterior: dict, disco: dict) -> list:
    """Traz pra `dados` (memória) o que mudou no `disco` desde `anterior` e a memória não alterou. Devolve
    ["login.campo", ...] do que veio de fora. Login novo lá entra; login que sumiu lá não é apagado aqui."""
    trazidos = []
    for login, info_disco in disco.items():
        if login not in anterior:
            if login not in dados:
                dados[login] = copy.deepcopy(info_disco)
                trazidos.append(login + " (novo)")
            continue
        info_mem, info_ant = dados.get(login), anterior[login]
        if not isinstance(info_mem, dict) or not isinstance(info_disco, dict) or not isinstance(info_ant, dict):
            continue
        for campo in set(info_disco) | set(info_ant):
            no_disco, antes = info_disco.get(campo, None), info_ant.get(campo, None)
            if no_disco != antes and info_mem.get(campo, None) == antes:
                if campo in info_disco:
                    info_mem[campo] = copy.deepcopy(no_disco)
                else:
                    info_mem.pop(campo, None)
                trazidos.append(f"{login}.{campo}")
    return trazidos


def _salvar_usuarios(dados: dict) -> bool:
    """Grava o usuarios.json e devolve se deu certo.

    Até a 2.33.5.3 cada rota abria o arquivo com "w" sem trava. O "Salvar
    permissões" da Manutenção de Usuários manda as 9 permissões ao mesmo tempo
    (o servidor atende em threads), então várias gravações se atropelavam:
    erro de arquivo em uso no Windows (engolido pelo except) ou arquivo com
    o conteúdo de uma gravação velha. Na memória ficava certo, mas ao reiniciar
    o PDA a permissão "sumia". Agora uma gravação por vez, e o texto vai
    primeiro pra um .tmp que substitui o arquivo de uma vez só (nunca fica
    arquivo pela metade)."""
    global _estado_gravado
    caminho = _caminho_usuarios_json()
    temporario = caminho + ".tmp"
    with _trava_gravacao_usuarios:
        if _estado_gravado is not None and os.path.exists(caminho):
            try:
                with open(caminho, "r", encoding="utf-8") as f:
                    disco = _completar_campos(json.load(f))
            except Exception:
                disco = None  # arquivo sendo trocado agora ou corrompido: grava o da memória, como antes
            if disco is not None and disco != _estado_gravado:
                trazidos = _mesclar_alteracoes_externas(dados, _estado_gravado, disco)
                if trazidos:
                    logger.warning("usuarios.json foi alterado por fora deste PDA (outro PDA aberto na mesma pasta?); "
                                   "mantido o que mudou lá: %s", ", ".join(sorted(trazidos)[:40]))
        for tentativa in range(5):
            try:
                texto = json.dumps(dados, indent=2, ensure_ascii=False)
                with open(temporario, "w", encoding="utf-8") as f:
                    f.write(texto)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temporario, caminho)
                _estado_gravado = copy.deepcopy(dados)
                return True
            except Exception:
                # arquivo aberto por outro programa (antivírus, backup) costuma liberar logo
                if tentativa == 4:
                    logger.exception("Não foi possível salvar usuarios.json.")
                    return False
                time.sleep(0.2 * (tentativa + 1))
    return False


def atualizar_cargos_movidesk(cargos_por_id: dict, sobrescrever: bool = True) -> dict:
    """Copia o cargo do Movidesk (tabela usuarios / API, campo "role") pro
    cadastro do PDA de quem está vinculado (usuario_movidesk_id), no campo
    "cargo" (2.34.4.0). Quem não tem vínculo não muda: não dá pra saber quem é.
    Cargo vazio no Movidesk não apaga o que o PDA já tinha. Grava o
    usuarios.json uma vez só, e só se algo mudou.
    sobrescrever=False (3.2.0.0, a sincronização "Atualizar Movidesk"): só preenche quem está SEM cargo no
    PDA; cargo já preenchido nunca é trocado pela sincronização (editar à mão no vínculo continua valendo).
    Devolve {"atualizados": [(login, antigo, novo)], "sem_vinculo": n, "gravou": bool}."""
    cargos = {str(k): (str(v).strip() if v is not None else "") for k, v in (cargos_por_id or {}).items()}
    atualizados, sem_vinculo = [], 0
    for login, info in USUARIOS_WEB.items():
        id_movidesk = str(info.get("usuario_movidesk_id") or "").strip()
        if not id_movidesk:
            sem_vinculo += 1
            continue
        novo = cargos.get(id_movidesk)
        if not novo or novo == (info.get("cargo") or ""):
            continue
        if not sobrescrever and (info.get("cargo") or "").strip():
            continue
        atualizados.append((login, info.get("cargo") or "", novo))
        info["cargo"] = novo
    gravou = _salvar_usuarios(USUARIOS_WEB) if atualizados else True
    return {"atualizados": atualizados, "sem_vinculo": sem_vinculo, "gravou": gravou}


LIMITE_FAVORITOS_HUB = 40


def definir_favoritos_hub(usuario: str, cards) -> list:
    """Grava os cards favoritos do hub dessa pessoa (vão pro começo da
    grade, na ordem em que foram favoritados). Cada card é identificado
    pelo href dele, que não muda quando a ordem dos cards muda. Fica no
    usuarios.json pra acompanhar a pessoa em qualquer computador (em vez
    do localStorage, que é por navegador)."""
    if not isinstance(cards, list):
        raise ValueError("lista de favoritos inválida")
    limpos = []
    for card in cards:
        if isinstance(card, str) and 0 < len(card) <= 300 and card not in limpos:
            limpos.append(card)
    limpos = limpos[:LIMITE_FAVORITOS_HUB]
    USUARIOS_WEB[usuario]["favoritos_hub"] = limpos
    _salvar_usuarios(USUARIOS_WEB)
    return limpos


USUARIOS_WEB: dict = _carregar_usuarios()


# Logins de teste apagados a pedido do Igor (2.34.9.0). Roda na partida: se algum
# ainda existir, guarda uma cópia do usuarios.json antes (usuarios.json.bak_remocao_teste)
# e apaga só esses logins. Depois de apagados não faz mais nada.
LOGINS_REMOVIDOS = ("teste", "teste123")


def _remover_logins_de_teste() -> list:
    presentes = [login for login in LOGINS_REMOVIDOS if login in USUARIOS_WEB]
    if not presentes:
        return []
    caminho = _caminho_usuarios_json()
    copia = caminho + ".bak_remocao_teste"
    try:
        if os.path.exists(caminho) and not os.path.exists(copia):
            with open(caminho, "r", encoding="utf-8") as origem, open(copia, "w", encoding="utf-8") as destino:
                destino.write(origem.read())
    except Exception:
        logger.exception("Não consegui guardar a cópia do usuarios.json - os logins de teste não foram apagados.")
        return []
    for login in presentes:
        USUARIOS_WEB.pop(login, None)
    if not _salvar_usuarios(USUARIOS_WEB):
        return []
    logger.info("Logins de teste apagados: %s (cópia anterior em %s).", ", ".join(presentes), os.path.basename(copia))
    return presentes


_remover_logins_de_teste()
