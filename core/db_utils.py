# encoding: utf-8

import logging
import re
from typing import Any

import pyodbc

logger = logging.getLogger(__name__)


def conectar_banco(
    server: str,
    database: str,
    username: str,
    password: str,
    driver: str = "ODBC Driver 17 for SQL Server",
    timeout: int = 30,
    autocommit: bool = False,
    raise_on_error: bool = False,
) -> pyodbc.Connection | bool:
    """
    Conecta ao SQL Server usando pyodbc.

    Por compatibilidade, retorna False em caso de erro. Use raise_on_error=True
    para levantar a excecao original.
    """
    try:
        for nome, valor in {
            "server": server,
            "database": database,
            "username": username,
            "password": password,
            "driver": driver,
        }.items():
            if not valor:
                raise ValueError(f"{nome} e obrigatorio.")

        conn_str = (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"Connection Timeout={int(timeout)}"
        )
        return pyodbc.connect(conn_str, autocommit=autocommit)

    except (pyodbc.Error, ValueError) as exc:
        logger.exception("Erro ao conectar ao banco de dados.")
        if raise_on_error:
            raise
        return False


def _rollback_if_possible(conn: pyodbc.Connection) -> None:
    try:
        conn.rollback()
    except pyodbc.Error as exc:
        logger.debug("Rollback nao executado: %s", exc)
    except AttributeError:
        logger.debug("Objeto de conexao nao possui rollback.")


def _extract_duplicate_value(error: pyodbc.IntegrityError) -> str | None:
    message = " ".join(str(arg) for arg in error.args)
    match = re.search(r"The duplicate key value is \((.*?)\)", message)
    if match:
        return match.group(1)
    return None


def _normalize_params(params: tuple[Any, ...] | list[Any] | str | Any | None) -> Any:
    if params is None:
        return None
    if isinstance(params, tuple):
        return params
    if isinstance(params, list):
        return tuple(params)
    return (params,)


def executar_query(
    conn: pyodbc.Connection,
    query: str,
    fetch: bool = False,
    commit: bool = False,
    params: tuple | str | None = None,
    raise_on_error: bool = False,
) -> tuple[list[tuple], list[str]] | bool:
    """
    Executa uma query SQL.

    Por compatibilidade, retorna ([], []) quando nao ha fetch e False quando
    ocorre erro. Use raise_on_error=True para levantar excecoes.
    """
    try:
        if conn is None:
            raise ValueError("conn e obrigatorio.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query deve ser uma string nao vazia.")

        normalized_params = _normalize_params(params)

        with conn.cursor() as cursor:
            if normalized_params is not None:
                cursor.execute(query, normalized_params)
            else:
                cursor.execute(query)

            if fetch:
                rows = cursor.fetchall()
                description = cursor.description or []
                colunas = [desc[0] for desc in description]
                resultados = [tuple(row) for row in rows]
                return resultados, colunas

            if commit:
                conn.commit()

        return [], []

    except pyodbc.IntegrityError as exc:
        valor_duplicado = _extract_duplicate_value(exc)
        if valor_duplicado:
            logger.warning("Valor duplicado: %s", valor_duplicado)
        else:
            logger.exception("Erro de integridade ao executar query.")

        _rollback_if_possible(conn)
        if raise_on_error:
            raise
        return False

    except (pyodbc.Error, ValueError) as exc:
        logger.exception("Erro ao executar query.")
        if conn is not None:
            _rollback_if_possible(conn)
        if raise_on_error:
            raise
        return False

    except Exception:
        logger.exception("Erro inesperado ao executar query.")
        if conn is not None:
            _rollback_if_possible(conn)
        if raise_on_error:
            raise
        return False


def fechar_conexao(conexao: pyodbc.Connection, raise_on_error: bool = False) -> bool:
    """
    Fecha a conexao com o banco de dados.

    Retorna True em sucesso e False em erro, mantendo um contrato simples para
    scripts. Use raise_on_error=True para levantar a excecao.
    """
    try:
        if not conexao:
            # cobre tanto None quanto False (conectar_banco retorna False,
            # nao None, quando a conexao falha - checar só "is None" deixava
            # esse caso escapar e cair no conexao.close() abaixo, que
            # quebrava com AttributeError por "bool" nao ter .close())
            raise ValueError("conexao e obrigatoria.")
        conexao.close()
        return True
    except (pyodbc.Error, ValueError, AttributeError):
        logger.exception("Erro ao fechar conexao.")
        if raise_on_error:
            raise
        return False
