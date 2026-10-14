"""Manutenção Rejeições em Banco - lógica (cadastro/edição das rejeições da tabela CONFIGURACOES_REJEICAO).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import base64
import logging
from typing import Optional

from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.banco_monitoramento import TIPOS_BANCO_VALIDOS
from nucleo.banco_monitoramento import _conectar_monitoramento

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py
logger_administracao = logging.getLogger("alertas.administracao")  # mesmo logger configurado no alertas_gui.py


def _listar_rejeicoes_banco() -> dict:
    """Lista os registros de CONFIGURACOES_REJEICAO (sem trazer SCRIPT nem
    CONEXAO na listagem - mesmo motivo do alerta: sensível/extenso demais
    pra tabela)."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        resultado = executar_query(
            conn,
            "SELECT ID, CLIENTE, TIPO_BANCO, TIPO_AGENDAMENTO, EMAILS FROM CONFIGURACOES_REJEICAO ORDER BY ID DESC",
            fetch=True,
            raise_on_error=True,
        )
        linhas, colunas = resultado
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _criar_rejeicao_banco(dados: dict, usuario_executor: str) -> dict:
    """Insere um novo registro em CONFIGURACOES_REJEICAO. Mesma conversão
    de SCRIPT pra base64 do alerta."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "INSERT INTO CONFIGURACOES_REJEICAO (CONEXAO, SCRIPT, CLIENTE, EMAILS, TIPO_BANCO, TIPO_AGENDAMENTO) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            params=(
                dados["conexao"], script_base64, dados["cliente"],
                dados.get("emails", "").strip(), dados["tipo_banco"], dados["tipo_agendamento"],
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Nova rejeição criada em CONFIGURACOES_REJEICAO: cliente=%s, por='%s'", dados["cliente"], usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao inserir em CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_rejeicao_banco(id_rejeicao: int) -> dict:
    """Busca um registro completo de CONFIGURACOES_REJEICAO por ID,
    incluindo CONEXAO/SCRIPT (não trazidos na listagem) - usado pra abrir
    o formulário de edição já preenchido. O SCRIPT volta decodificado de
    base64 pra texto puro."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT ID, CLIENTE, TIPO_BANCO, TIPO_AGENDAMENTO, EMAILS, CONEXAO, SCRIPT "
            "FROM CONFIGURACOES_REJEICAO WHERE ID = ?",
            params=(id_rejeicao,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "rejeição não encontrada"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        if registro.get("script"):
            try:
                registro["script"] = base64.b64decode(registro["script"]).decode("utf-8")
            except Exception:
                pass
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar rejeição em CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_rejeicao_banco(id_rejeicao: int, dados: dict, usuario_executor: str) -> dict:
    """Atualiza todos os campos editáveis de um registro existente em
    CONFIGURACOES_REJEICAO."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_REJEICAO SET "
            "CONEXAO=?, SCRIPT=?, CLIENTE=?, EMAILS=?, TIPO_BANCO=?, TIPO_AGENDAMENTO=? "
            "WHERE ID=?",
            params=(
                dados["conexao"], script_base64, dados["cliente"],
                dados.get("emails", "").strip(), dados["tipo_banco"], dados["tipo_agendamento"],
                id_rejeicao,
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Rejeição ID=%s atualizada em CONFIGURACOES_REJEICAO por '%s'.", id_rejeicao, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _excluir_rejeicao_banco(id_rejeicao: int, usuario_executor: str) -> dict:
    """Exclui um registro de CONFIGURACOES_REJEICAO. Diferente do alerta
    (que só ativa/desativa via DISPONIBILIDADE), a rejeição não tem essa
    coluna - excluir é a única forma de tirar uma regra de circulação."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "DELETE FROM CONFIGURACOES_REJEICAO WHERE ID = ?",
            params=(id_rejeicao,),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Rejeição ID=%s excluída de CONFIGURACOES_REJEICAO por '%s'.", id_rejeicao, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao excluir de CONFIGURACOES_REJEICAO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _validar_dados_rejeicao_banco(dados: dict) -> Optional[str]:
    """'emails' é OPCIONAL aqui (ao contrário do alerta) - a documentação
    mostra até um INSERT de exemplo sem esse campo. O e-mail do
    monitoramento já é adicionado por fora, automaticamente.
    'tipo_agendamento' é obrigatório (VARCHAR livre - a documentação não
    especificou uma lista fechada de valores válidos, diferente de
    tipo_banco)."""
    obrigatorios = ["conexao", "script", "cliente", "tipo_banco", "tipo_agendamento"]
    for campo in obrigatorios:
        if not dados.get(campo, "").strip():
            return f"O campo '{campo}' é obrigatório."
    if dados["tipo_banco"].upper() not in TIPOS_BANCO_VALIDOS:
        return "Tipo de banco precisa ser ORACLE ou SQL."
    return None


def _montar_texto_gatilho_rejeicao(cliente: str) -> dict:
    """Mesma ideia do gatilho de alerta, adaptado pra rejeição (que não
    tem título)."""
    return {
        "nome": f"{cliente} - [REJEIÇÃO]",
        "solicitante": f"OA {cliente}",
        "servico": f"Monitoramento > Rejeições > {cliente}",
    }
