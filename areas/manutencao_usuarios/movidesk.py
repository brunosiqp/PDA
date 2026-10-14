"""Usuários Movidesk - lógica (leitura, sincronização e edição da tabela 'usuarios' do banco do Movidesk (agentes)).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import logging
import time
from typing import Optional

import requests

from areas.manutencao_relatorios.logica import _normalizar_hora_execucao
from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.movidesk import MOVIDESK_API_BASE
from nucleo.movidesk import _conectar_indicadores_movidesk
from nucleo.movidesk import _movidesk_api_token
from nucleo.movidesk import ocultar_token
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py
logger_administracao = logging.getLogger("alertas.administracao")  # mesmo logger configurado no alertas_gui.py


def _listar_usuarios_movidesk() -> dict:
    """Lista os usuários da tabela 'usuarios' (banco movidesk, mesma
    conexão de Indicadores Movidesk/Apontamentos) - usado tanto pra
    popular o select de vínculo na aba Usuários do PDA quanto pra
    carregar a escala de todo mundo de uma vez só (_carregar_escala_
    horas), sem precisar de uma consulta por pessoa."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT id, nome, email, cargo, escala, ativo FROM usuarios ORDER BY nome",
            fetch=True,
            raise_on_error=True,
        )
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar usuarios (banco movidesk)")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


# ---------------------------------------------------------------------------
# Sincronização de agentes do Movidesk -> tabela 'usuarios' - pedido do
# Igor em 16/09/2026: o botão "Atualizar lista" (vínculo Movidesk, aba
# Editar usuários) deve fazer a MESMA coisa que o script standalone dele
# (sincronizacao_agentes_movidesk.py) faz - buscar os agentes ativos
# direto na API do Movidesk e sincronizar a tabela usuarios (insere
# novo, atualiza quem mudou, reativa, e INATIVA - nunca apaga - quem não
# voltou mais da API), em vez de só reler o que já está no banco.
# ---------------------------------------------------------------------------
MOVIDESK_SYNC_IDS_IGNORADOS = {"9188270456"}
MOVIDESK_SYNC_PAGE_SIZE = 100


def _movidesk_buscar_agentes_ativos() -> list:
    """Busca TODOS os agentes ativos (profileType 1 ou 3, isActive) da
    API do Movidesk, paginado - mesmo filtro/campos/limite de página do
    script original. Levanta exceção se a API não devolver nada (mesma
    proteção do script: nunca deixa uma resposta vazia/quebrada acabar
    inativando a tabela inteira por engano)."""
    token = _movidesk_api_token()
    agentes: list = []
    skip = 0
    while True:
        params = {
            "token": token,
            "$select": "id,businessName,userName,role",
            "$filter": "(profileType eq 1 or profileType eq 3) and isActive eq true",
            "$orderby": "id",
            "$top": MOVIDESK_SYNC_PAGE_SIZE,
            "$skip": skip,
        }
        resposta = requests.get(MOVIDESK_API_BASE, params=params, timeout=(15, 120))
        resposta.raise_for_status()
        dados = resposta.json()
        if not isinstance(dados, list):
            raise RuntimeError("Resposta inesperada da API do Movidesk (esperava uma lista).")
        agentes.extend(dados)
        if len(dados) < MOVIDESK_SYNC_PAGE_SIZE:
            break
        skip += MOVIDESK_SYNC_PAGE_SIZE
        time.sleep(7)  # respeita o limite de taxa da API, igual o script original
    if not agentes:
        raise RuntimeError("A API não retornou nenhum agente ativo - sincronização cancelada por segurança.")
    return agentes


def _movidesk_validar_agentes(agentes: list) -> list:
    """Mesma validação do script original (id/nome/email preenchidos,
    sem duplicidade) - só que aqui PULA silenciosamente um registro
    inválido em vez de derrubar a sincronização inteira, já que essa
    função roda a partir de um clique na tela (melhor sincronizar o que
    der certo do que falhar tudo por causa de 1 registro estranho)."""
    resultado = []
    ids_encontrados: set = set()
    for pessoa in agentes:
        id_movidesk = str(pessoa.get("id") or "").strip()
        if not id_movidesk or id_movidesk in MOVIDESK_SYNC_IDS_IGNORADOS or id_movidesk in ids_encontrados:
            continue
        nome = str(pessoa.get("businessName") or "").strip()
        email = str(pessoa.get("userName") or "").strip()
        if not nome or not email:
            continue
        cargo = pessoa.get("role")
        if cargo is not None:
            cargo = str(cargo).strip() or None
        ids_encontrados.add(id_movidesk)
        resultado.append({"id": id_movidesk, "nome": nome, "email": email, "cargo": cargo})
    return resultado


def _movidesk_sincronizar_tabela_usuarios(agentes: list) -> dict:
    """Mesma lógica de sincronização do script original: insere quem é
    novo, atualiza (e reativa) quem mudou, reativa quem só estava
    inativo, e INATIVA (nunca apaga) quem não voltou mais da API - os
    IDs de MOVIDESK_SYNC_IDS_IGNORADOS nunca são tocados de jeito
    nenhum (nem inseridos, nem atualizados, nem inativados). Não mexe na
    coluna 'escala' nem nas de horário/dias - essas são geridas dentro
    do PDA (vínculo Movidesk da aba Editar usuários), o Movidesk não
    sabe nada sobre isso."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn, "SELECT id, nome, email, cargo, ativo FROM usuarios",
            fetch=True, raise_on_error=True,
        )
        colunas_lower = [c.lower() for c in colunas]
        existentes = {}
        for linha in linhas:
            row = dict(zip(colunas_lower, linha))
            existentes[str(row["id"])] = {
                "nome": row.get("nome"), "email": row.get("email"),
                "cargo": row.get("cargo"), "ativo": bool(row.get("ativo")),
            }

        ids_api = {a["id"] for a in agentes}
        ids_considerados_ativos = ids_api | MOVIDESK_SYNC_IDS_IGNORADOS
        ids_banco = set(existentes.keys())
        ids_para_inativar = ids_banco - ids_considerados_ativos

        novos = atualizados = sem_alteracao = reativados = 0

        for id_movidesk in ids_para_inativar:
            if existentes[id_movidesk]["ativo"]:
                executar_query(conn, "UPDATE usuarios SET ativo = 0 WHERE id = ?", params=(id_movidesk,), raise_on_error=True)

        for agente in agentes:
            id_movidesk, nome, email, cargo = agente["id"], agente["nome"], agente["email"], agente["cargo"]
            atual = existentes.get(id_movidesk)

            if atual is None:
                executar_query(
                    conn, "INSERT INTO usuarios (id, nome, email, cargo, ativo) VALUES (?, ?, ?, ?, 1)",
                    params=(id_movidesk, nome, email, cargo), raise_on_error=True,
                )
                novos += 1
                continue

            mudou = atual["nome"] != nome or atual["email"] != email or atual["cargo"] != cargo
            estava_inativo = not atual["ativo"]
            if mudou:
                executar_query(
                    conn, "UPDATE usuarios SET nome = ?, email = ?, cargo = ?, ativo = 1 WHERE id = ?",
                    params=(nome, email, cargo, id_movidesk), raise_on_error=True,
                )
                atualizados += 1
            elif estava_inativo:
                executar_query(conn, "UPDATE usuarios SET ativo = 1 WHERE id = ?", params=(id_movidesk,), raise_on_error=True)
                reativados += 1
            else:
                sem_alteracao += 1

        return {
            "ok": True, "novos": novos, "atualizados": atualizados, "reativados": reativados,
            "sem_alteracao": sem_alteracao, "inativados": len(ids_para_inativar), "total_api": len(agentes),
        }
    except requests.exceptions.RequestException as e:
        # sem traceback: o erro do requests traz a URL com o token da API (3.2.7.1)
        logger.error("Erro ao sincronizar tabela usuarios com o Movidesk: %s", ocultar_token(e))
        return {"ok": False, "erro": ocultar_token(e)}
    except Exception as e:
        logger.exception("Erro ao sincronizar tabela usuarios com o Movidesk")
        return {"ok": False, "erro": ocultar_token(e)}
    finally:
        fechar_conexao(conn)


def _sincronizar_usuarios_movidesk() -> dict:
    """Função principal chamada pelo botão "Atualizar lista" (vínculo
    Movidesk) - busca os agentes ativos DIRETO da API do Movidesk (não
    só relê a tabela) e sincroniza a tabela usuarios, com o mesmo
    comportamento do script standalone sincronizacao_agentes_movidesk.py."""
    try:
        agentes_api = _movidesk_buscar_agentes_ativos()
    except Exception as e:
        logger.exception("Erro ao buscar agentes ativos na API do Movidesk")
        return {"ok": False, "erro": f"Erro ao consultar a API do Movidesk: {e}"}

    agentes_validados = _movidesk_validar_agentes(agentes_api)
    if not agentes_validados:
        return {"ok": False, "erro": "Nenhum agente válido restou após a validação - sincronização cancelada."}

    resultado = _movidesk_sincronizar_tabela_usuarios(agentes_validados)
    if resultado.get("ok"):
        logger.info(
            "Sincronização de agentes do Movidesk concluída - novos: %d, atualizados: %d, "
            "reativados: %d, sem alteração: %d, inativados: %d (total da API: %d).",
            resultado["novos"], resultado["atualizados"], resultado["reativados"],
            resultado["sem_alteracao"], resultado["inativados"], resultado["total_api"],
        )
        # cargo de cada agente, pro alertas_gui copiar pro cadastro do PDA (2.34.4.0)
        resultado["cargos_por_id"] = {a["id"]: a["cargo"] for a in agentes_validados}
    return resultado


def _buscar_usuario_movidesk(id_usuario: str) -> dict:
    """Busca um registro completo da tabela usuarios por ID (o id nessa
    tabela é texto, não numérico - confirmado na amostra de dados: IDs
    tipo '9858757035', '971081452' etc.)."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT id, nome, email, cargo, escala, horainicio, horafim, diasTrabalhados, ativo "
            "FROM usuarios WHERE id = ?",
            params=(id_usuario,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "usuário não encontrado na tabela usuarios"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        registro["horainicio"] = _normalizar_hora_execucao(registro.get("horainicio"))
        registro["horafim"] = _normalizar_hora_execucao(registro.get("horafim"))
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar usuario (banco movidesk)")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_usuario_movidesk(id_usuario: str, dados: dict, usuario_executor: str) -> dict:
    """Atualiza cargo/email/escala/horário/dias trabalhados de um
    registro da tabela usuarios (banco movidesk). Não mexe no ID nem no
    nome - esses continuam vindo de onde quer que essa tabela seja
    alimentada (provavelmente sincronizada do Movidesk em si)."""
    conn, erro = _conectar_indicadores_movidesk()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE usuarios SET cargo=?, email=?, escala=?, horainicio=?, horafim=?, diasTrabalhados=? "
            "WHERE id=?",
            params=(
                dados.get("cargo") or None, dados.get("email") or None, dados.get("escala") or None,
                dados.get("horainicio") or None, dados.get("horafim") or None,
                dados.get("diasTrabalhados") or None, id_usuario,
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info(
            "Usuário Movidesk ID=%s (tabela usuarios) atualizado por '%s'.", id_usuario, usuario_executor
        )
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar usuario (banco movidesk)")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _nome_movidesk_vinculado(usuario_login: str) -> "tuple[Optional[str], Optional[str]]":
    """Devolve (nome_em_maiusculo, erro) da pessoa vinculada no Movidesk
    pra esse login do PDA - ou (None, None) se não tiver vínculo, ou
    (None, mensagem_erro) se o vínculo existir mas a consulta falhar."""
    info = USUARIOS_WEB.get(usuario_login, {})
    id_movidesk = info.get("usuario_movidesk_id")
    if not id_movidesk:
        return None, None
    detalhe = _buscar_usuario_movidesk(id_movidesk)
    if not detalhe.get("ok"):
        return None, detalhe.get("erro")
    nome_movidesk = str(detalhe["registro"].get("nome") or "").strip().upper()
    return (nome_movidesk or None), None
