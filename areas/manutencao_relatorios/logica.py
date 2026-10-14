"""Manutenção de Relatórios em Banco - lógica (cadastro/edição dos relatórios da tabela CONFIGURACOES_RELATORIO).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import base64
import logging
import re
from datetime import datetime
from datetime import time as time_cls
from typing import Optional

from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.banco_monitoramento import TIPOS_BANCO_VALIDOS
from nucleo.banco_monitoramento import _conectar_monitoramento

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py
logger_administracao = logging.getLogger("alertas.administracao")  # mesmo logger configurado no alertas_gui.py


MODELOS_ARQUIVO_VALIDOS = {"P", "C", "T"}
REINCIDENCIAS_VALIDAS = {"DIARIO", "SEMANAL", "MENSAL"}
DIAS_SEMANA_VALIDOS = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
}


def _normalizar_hora_execucao(valor) -> str:
    """HORA_EXECUCAO pode vir do banco como string ('08:00'), como objeto
    datetime.time (comum com pyodbc em colunas TIME), ou até como
    datetime completo em alguns drivers - normaliza tudo pra uma string
    limpa 'HH:MM' (sem segundos), que é o formato que o campo <input
    type="time"> do formulário e a validação (_validar_dados_relatorio_
    banco) esperam. Sem isso, um objeto time chegava intacto até o
    json.dumps e quebrava a resposta inteira (era a causa do "Failed to
    fetch" reportado)."""
    if valor is None:
        return ""
    if isinstance(valor, str):
        return valor[:5]  # corta eventuais segundos tipo '08:00:00' -> '08:00'
    if isinstance(valor, (time_cls, datetime)):
        return valor.strftime("%H:%M")
    return str(valor)[:5]


def _listar_relatorios_banco() -> dict:
    """Lista os registros de CONFIGURACOES_RELATORIO (sem CONEXAO/SCRIPT -
    mesmo motivo das outras duas manutenções: sensível/extenso demais pra
    tabela)."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        resultado = executar_query(
            conn,
            "SELECT ID, CLIENTE, TITULO_EMAIL, TIPO_BANCO, MODELO_ARQUIVO, REINCIDENCIA, "
            "HORA_EXECUCAO, DISPONIBILIDADE FROM CONFIGURACOES_RELATORIO ORDER BY ID DESC",
            fetch=True,
            raise_on_error=True,
        )
        linhas, colunas = resultado
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        for registro in registros:
            registro["hora_execucao"] = _normalizar_hora_execucao(registro.get("hora_execucao"))
            if registro.get("disponibilidade") is not None:
                registro["disponibilidade"] = int(registro["disponibilidade"])
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_relatorio_banco(id_relatorio: int) -> dict:
    """Busca um registro completo de CONFIGURACOES_RELATORIO por ID,
    incluindo CONEXAO/SCRIPT - usado pra abrir o formulário de edição já
    preenchido. O SCRIPT volta decodificado de base64 pra texto puro."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT ID, CONEXAO, SCRIPT, EMAILS, TIPO_BANCO, CLIENTE, TITULO_EMAIL, "
            "CORPO_EMAIL, NOME_ARQUIVO, MODELO_ARQUIVO, REINCIDENCIA, DIA_SEMANA, "
            "DIA_MENSAL, HORA_EXECUCAO, DISPONIBILIDADE, AGRUPADOR_RELATORIO "
            "FROM CONFIGURACOES_RELATORIO WHERE ID = ?",
            params=(id_relatorio,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "relatório não encontrado"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        if registro.get("script"):
            try:
                registro["script"] = base64.b64decode(registro["script"]).decode("utf-8")
            except Exception:
                pass
        registro["hora_execucao"] = _normalizar_hora_execucao(registro.get("hora_execucao"))
        if registro.get("disponibilidade") is not None:
            registro["disponibilidade"] = int(registro["disponibilidade"])
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar relatório em CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _campos_relatorio_para_query(dados: dict) -> tuple:
    """Monta a tupla de valores na mesma ordem usada pelo INSERT/UPDATE -
    função única pra não duplicar essa lista comprida em dois lugares e
    arriscar desalinhar a ordem em algum dos dois."""
    return (
        dados["conexao"], dados["script_base64"], dados["emails"], dados["tipo_banco"],
        dados["cliente"], dados["titulo_email"], dados["corpo_email"], dados["nome_arquivo"],
        dados["modelo_arquivo"], dados["reincidencia"], dados.get("dia_semana") or None,
        dados.get("dia_mensal") or None, dados["hora_execucao"], dados["disponibilidade"],
        dados.get("agrupador_relatorio") or None,
    )


def _criar_relatorio_banco(dados: dict, usuario_executor: str) -> dict:
    dados = dict(dados)
    dados["script_base64"] = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "INSERT INTO CONFIGURACOES_RELATORIO "
            "(CONEXAO, SCRIPT, EMAILS, TIPO_BANCO, CLIENTE, TITULO_EMAIL, CORPO_EMAIL, "
            "NOME_ARQUIVO, MODELO_ARQUIVO, REINCIDENCIA, DIA_SEMANA, DIA_MENSAL, "
            "HORA_EXECUCAO, DISPONIBILIDADE, AGRUPADOR_RELATORIO) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=_campos_relatorio_para_query(dados),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info(
            "Novo relatório criado em CONFIGURACOES_RELATORIO: cliente=%s, titulo_email=%s, por='%s'",
            dados["cliente"], dados["titulo_email"], usuario_executor,
        )
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao inserir em CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_relatorio_banco(id_relatorio: int, dados: dict, usuario_executor: str) -> dict:
    dados = dict(dados)
    dados["script_base64"] = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_RELATORIO SET "
            "CONEXAO=?, SCRIPT=?, EMAILS=?, TIPO_BANCO=?, CLIENTE=?, TITULO_EMAIL=?, "
            "CORPO_EMAIL=?, NOME_ARQUIVO=?, MODELO_ARQUIVO=?, REINCIDENCIA=?, DIA_SEMANA=?, "
            "DIA_MENSAL=?, HORA_EXECUCAO=?, DISPONIBILIDADE=?, AGRUPADOR_RELATORIO=? "
            "WHERE ID=?",
            params=_campos_relatorio_para_query(dados) + (id_relatorio,),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Relatório ID=%s atualizado em CONFIGURACOES_RELATORIO por '%s'.", id_relatorio, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _alterar_disponibilidade_relatorio(id_relatorio: int, ativo: bool, usuario_executor: str) -> dict:
    """Ativa/desativa um relatório. Convenção 1=ativo, 0=inativo - igual
    CONFIGURACOES_ALERTA (a documentação inicial dizia 1/2, mas a tabela
    real usa 1/0 - corrigido depois de confirmar com o Igor)."""
    novo_valor = 1 if ativo else 0
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_RELATORIO SET DISPONIBILIDADE = ? WHERE ID = ?",
            params=(novo_valor, id_relatorio),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info(
            "Relatório ID=%s teve disponibilidade alterada pra %s por '%s'.", id_relatorio, novo_valor, usuario_executor
        )
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao alterar disponibilidade em CONFIGURACOES_RELATORIO")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _validar_dados_relatorio_banco(dados: dict) -> Optional[str]:
    obrigatorios = [
        "conexao", "script", "emails", "tipo_banco", "cliente", "titulo_email",
        "corpo_email", "nome_arquivo", "modelo_arquivo", "reincidencia", "hora_execucao",
    ]
    for campo in obrigatorios:
        if not dados.get(campo, "").strip():
            return f"O campo '{campo}' é obrigatório."

    if dados["tipo_banco"].upper() not in TIPOS_BANCO_VALIDOS:
        return "Tipo de banco precisa ser ORACLE ou SQL."

    if dados["modelo_arquivo"].upper() not in MODELOS_ARQUIVO_VALIDOS:
        return "Modelo do arquivo precisa ser P (planilha), C (csv) ou T (txt)."

    reincidencia = dados["reincidencia"].upper()
    if reincidencia not in REINCIDENCIAS_VALIDAS:
        return "Reincidência precisa ser DIARIO, SEMANAL ou MENSAL."

    # dia_semana só é validado/obrigatório pra reincidência SEMANAL - se
    # não informado nesse caso, a documentação diz pra assumir Terça-Feira
    dia_semana = (dados.get("dia_semana") or "").strip()
    if reincidencia == "SEMANAL":
        if not dia_semana:
            dados["dia_semana"] = "Tuesday"
        elif dia_semana not in DIAS_SEMANA_VALIDOS:
            return "Dia da semana precisa ser um dia em inglês (ex.: Monday, Tuesday...)."
    else:
        dados["dia_semana"] = ""

    # dia_mensal só é validado/obrigatório pra reincidência MENSAL
    dia_mensal = (dados.get("dia_mensal") or "").strip()
    if reincidencia == "MENSAL":
        try:
            dia_mensal_num = int(dia_mensal)
            if not (1 <= dia_mensal_num <= 31):
                raise ValueError
        except (ValueError, TypeError):
            return "Dia do mês precisa ser um número de 1 a 31 (obrigatório pra reincidência MENSAL)."
    else:
        dados["dia_mensal"] = ""

    hora = dados["hora_execucao"].strip()
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", hora):
        return "Hora de execução precisa estar no formato HH:MM (00:00 a 23:59)."

    return None
