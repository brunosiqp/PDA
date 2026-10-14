"""Manutenção de Alertas em Banco - lógica (cadastro/edição dos alertas da tabela CONFIGURACOES_ALERTA).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import base64
import logging
from typing import Optional

from core.db_utils import executar_query
from core.db_utils import fechar_conexao
from nucleo.banco_monitoramento import EMAIL_MONITORAMENTO_PADRAO
from nucleo.banco_monitoramento import TIPOS_BANCO_VALIDOS
from nucleo.banco_monitoramento import _conectar_monitoramento

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py
logger_administracao = logging.getLogger("alertas.administracao")  # mesmo logger configurado no alertas_gui.py


def _listar_alertas_banco() -> dict:
    """Lista os registros de CONFIGURACOES_ALERTA (sem trazer SCRIPT nem
    CONEXAO na listagem - ficam guardados, mas não expostos na tabela por
    serem sensíveis/extensos)."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        resultado = executar_query(
            conn,
            "SELECT ID, CLIENTE, TITULO, TIPO_BANCO, TETO_ALERTA, INTERVALO_MINUTOS, "
            "EMAILS, DISPONIBILIDADE FROM CONFIGURACOES_ALERTA ORDER BY ID DESC",
            fetch=True,
            raise_on_error=True,
        )
        linhas, colunas = resultado
        colunas_lower = [c.lower() for c in colunas]
        registros = [dict(zip(colunas_lower, linha)) for linha in linhas]
        return {"ok": True, "registros": registros}
    except Exception as e:
        logger.exception("Erro ao listar CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def contar_alertas_mapeados() -> dict:
    """Quantos alertas estão cadastrados em CONFIGURACOES_ALERTA (o número "Alertas automáticos" do Sobre e do login,
    3.4.5.0) e quantos estão ligados. {"ok", "total", "ativos"} ou {"ok": False, "erro"}."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, _ = executar_query(conn, "SELECT COUNT(*), SUM(CASE WHEN DISPONIBILIDADE = 1 THEN 1 ELSE 0 END) FROM CONFIGURACOES_ALERTA",
                                   fetch=True, raise_on_error=True)
        total, ativos = linhas[0] if linhas else (0, 0)
        return {"ok": True, "total": int(total or 0), "ativos": int(ativos or 0)}
    except Exception as e:
        logger.exception("Erro ao contar CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def visao_somente_leitura_lista(registros: list) -> list:
    """Quem só visualiza (3.1.9.0: card aberto pra todo mundo) vê só os alertas ativos."""
    return [r for r in registros if str(r.get("disponibilidade")) in ("1", "True", "true")]


def visao_somente_leitura_alerta(registro: dict) -> Optional[dict]:
    """Um alerta pra quem só visualiza: só se estiver ativo e NUNCA com a conexão (a String Connection
    não sai do servidor pra essa pessoa). O SELECT, o teto, o intervalo, os e-mails e a descrição vão."""
    if str(registro.get("disponibilidade")) not in ("1", "True", "true"):
        return None
    return {k: v for k, v in registro.items() if k != "conexao"}


def _criar_alerta_banco(dados: dict, usuario_executor: str) -> dict:
    """Insere um novo registro em CONFIGURACOES_ALERTA. O SCRIPT chega em
    texto puro (SQL normal) e é convertido pra base64 aqui dentro - quem usa
    o formulário não precisa se preocupar em codificar nada na mão. O e-mail
    é sempre o padrão do monitoramento, mesmo que outra coisa tenha vindo
    do formulário (o campo é travado no front, e reforçado aqui também)."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "INSERT INTO CONFIGURACOES_ALERTA "
            "(CONEXAO, SCRIPT, CLIENTE, EMAILS, TIPO_BANCO, TETO_ALERTA, TITULO, "
            "DESCRICAO, INTERVALO_MINUTOS, DISPONIBILIDADE) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            params=(
                dados["conexao"], script_base64, dados["cliente"], EMAIL_MONITORAMENTO_PADRAO,
                dados["tipo_banco"], dados["teto_alerta"], dados["titulo"],
                dados["descricao"], dados["intervalo_minutos"], dados["disponibilidade"],
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Novo alerta criado em CONFIGURACOES_ALERTA: cliente=%s, titulo=%s, por='%s'", dados["cliente"], dados["titulo"], usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao inserir em CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _buscar_alerta_banco(id_alerta: int) -> dict:
    """Busca um registro completo de CONFIGURACOES_ALERTA por ID, incluindo
    CONEXAO/SCRIPT/DESCRICAO (não trazidos na listagem) - usado pra abrir o
    formulário de edição já preenchido. O SCRIPT volta decodificado de
    base64 pra texto puro, pra edição ficar natural."""
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        linhas, colunas = executar_query(
            conn,
            "SELECT ID, CLIENTE, TITULO, TIPO_BANCO, TETO_ALERTA, INTERVALO_MINUTOS, "
            "EMAILS, DISPONIBILIDADE, CONEXAO, SCRIPT, DESCRICAO "
            "FROM CONFIGURACOES_ALERTA WHERE ID = ?",
            params=(id_alerta,),
            fetch=True,
            raise_on_error=True,
        )
        if not linhas:
            return {"ok": False, "erro": "alerta não encontrado"}
        colunas_lower = [c.lower() for c in colunas]
        registro = dict(zip(colunas_lower, linhas[0]))
        if registro.get("script"):
            try:
                registro["script"] = base64.b64decode(registro["script"]).decode("utf-8")
            except Exception:
                pass  # se não vier em base64 válido por algum motivo, devolve como veio
        return {"ok": True, "registro": registro}
    except Exception as e:
        logger.exception("Erro ao buscar alerta em CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _atualizar_alerta_banco(id_alerta: int, dados: dict, usuario_executor: str) -> dict:
    """Atualiza TODOS os campos editáveis de um registro existente em
    CONFIGURACOES_ALERTA. Mesma regra do e-mail travado da criação."""
    script_base64 = base64.b64encode(dados["script"].encode("utf-8")).decode("ascii")
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_ALERTA SET "
            "CONEXAO=?, SCRIPT=?, CLIENTE=?, EMAILS=?, TIPO_BANCO=?, TETO_ALERTA=?, "
            "TITULO=?, DESCRICAO=?, INTERVALO_MINUTOS=?, DISPONIBILIDADE=? "
            "WHERE ID=?",
            params=(
                dados["conexao"], script_base64, dados["cliente"], EMAIL_MONITORAMENTO_PADRAO,
                dados["tipo_banco"], dados["teto_alerta"], dados["titulo"],
                dados["descricao"], dados["intervalo_minutos"], dados["disponibilidade"],
                id_alerta,
            ),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Alerta ID=%s atualizado em CONFIGURACOES_ALERTA por '%s'.", id_alerta, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _alternar_disponibilidade_banco(id_alerta: int, novo_valor: int, usuario_executor: str) -> dict:
    conn, erro = _conectar_monitoramento()
    if erro:
        return {"ok": False, "erro": erro}
    try:
        executar_query(
            conn,
            "UPDATE CONFIGURACOES_ALERTA SET DISPONIBILIDADE = ? WHERE ID = ?",
            params=(novo_valor, id_alerta),
            commit=True,
            raise_on_error=True,
        )
        logger_administracao.info("Disponibilidade do alerta ID=%s alterada para %s por '%s'", id_alerta, novo_valor, usuario_executor)
        return {"ok": True}
    except Exception as e:
        logger.exception("Erro ao atualizar disponibilidade em CONFIGURACOES_ALERTA")
        return {"ok": False, "erro": str(e)}
    finally:
        fechar_conexao(conn)


def _validar_dados_alerta_banco(dados: dict) -> Optional[str]:
    """Valida os campos do formulário contra as regras documentadas.
    Retorna a mensagem de erro, ou None se está tudo certo.

    'emails' não entra na validação: esse campo é travado no e-mail padrão
    do monitoramento (EMAIL_MONITORAMENTO_PADRAO) e sempre sobrescrito no
    backend, então validar o que veio do formulário pra esse campo
    especificamente não faz sentido - o valor final nunca é o que foi
    enviado."""
    obrigatorios = ["conexao", "script", "cliente", "tipo_banco", "titulo", "descricao"]
    for campo in obrigatorios:
        if not dados.get(campo, "").strip():
            return f"O campo '{campo}' é obrigatório."
    if dados["tipo_banco"].upper() not in TIPOS_BANCO_VALIDOS:
        return "Tipo de banco precisa ser ORACLE ou SQL."
    if not dados["titulo"].strip().startswith("[ALERTA]"):
        return "O título precisa começar com '[ALERTA]'."
    try:
        float(dados["teto_alerta"])
    except (ValueError, TypeError):
        return "Teto do alerta precisa ser um número."
    try:
        intervalo = int(dados["intervalo_minutos"])
        if intervalo <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return "Intervalo (minutos) precisa ser um número inteiro positivo."
    return None


def _montar_texto_gatilho(cliente: str, titulo: str) -> dict:
    """Monta o texto pronto pra colar na abertura do gatilho no Movidesk,
    seguindo o padrão documentado (Nome / Solicitante / Serviço)."""
    titulo_sem_prefixo = titulo.strip()
    if titulo_sem_prefixo.upper().startswith("[ALERTA]"):
        titulo_sem_prefixo = titulo_sem_prefixo[len("[ALERTA]"):].strip()
    return {
        "nome": f"{cliente} - [ALERTA] - {titulo_sem_prefixo}",
        "solicitante": f"OA {cliente}",
        "servico": f"Monitoramento > Alertas > {cliente} > {titulo_sem_prefixo}",
    }
