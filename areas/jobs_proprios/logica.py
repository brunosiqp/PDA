"""Jobs próprios do monitoramento - lógica (jobs que não são um Alerta de cliente: Validação FTP (pastas FornecedorA paradas no FTP) e Valor Zerado ClienteC (desativado na lista JOBS, código mantido)).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import logging
import os

import pyodbc

from core.config_seguro import obter_valor_config as _obter_valor_config
from features.operations import execute as ftp_execute
from features.operations import getEnv as ftp_getEnv
from nucleo.config import _obter_config_hibrido

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _executar_validacao_ftp() -> None:
    """Lógica original do ValidacaoFTP: conta arquivos parados por cliente
    numa pasta de rede e dispara e-mail se algum cliente passar do limite."""
    ftp_getEnv("email")

    dir_base = os.path.join(
        r"\\srv278.example.net\FTP", "integracao"
    )
    dic_clientes = {
        cliente: os.path.join(dir_base, cliente) for cliente in os.listdir(dir_base)
    }

    clientes_acima = {}
    for cliente, caminho in dic_clientes.items():
        dir_fornecedor_a = os.path.join(caminho, "FornecedorA")
        if not os.path.isdir(dir_fornecedor_a):
            continue
        total_arq = sum(1 for entry in os.scandir(dir_fornecedor_a) if entry.is_file())
        if total_arq >= 100:
            clientes_acima[cliente] = total_arq

    if clientes_acima:
        ftp_execute(clientes_acima)
    else:
        logger.info("Validação FTP: nenhuma pasta acima do limite.")


def _executar_valor_zerado_cliente_c() -> None:
    """Zera o status de documentos rejeitados por 'valor de serviço 0' pra
    reprocessamento, para os tomadores ClienteC. Lógica SQL identica ao script
    original valor_zerado_CLIENTE_C.py - só a leitura do .env e o logging que
    foram adaptados pra entrar no padrão do painel."""
    # CREDENCIAIS_CENTRALIZADAS.env primeiro (seção [infra_cliente_c_valor_zerado]),
    # cai pro .env tradicional (bare, sem sufixo) se essa seção não existir.
    valores = _obter_config_hibrido(
        "infra_cliente_c_valor_zerado", ".env",
        ["DB_SERVER", "DB_DATABASE", "DB_USER", "DB_PASSWORD"],
    )
    servidor = valores["DB_SERVER"]
    banco = valores["DB_DATABASE"]
    usuario = valores["DB_USER"]
    senha = _obter_valor_config("cliente_c::DB_PASSWORD", valores["DB_PASSWORD"])

    conn = None
    try:
        conn = pyodbc.connect(
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={servidor};"
            f"DATABASE={banco};"
            f"UID={usuario};"
            f"PWD={senha};"
        )
        cursor = conn.cursor()

        sql = """
        update documento_recebido
        set ind_status = 1
        from documento_recebido DR INNER JOIN EVENTOS_DOC_RECEBIDO ES ON DR.ID = ES.DOCUMENTO_RECEBIDO_FK
        where DR.val_servico = 0.0000
            and DR.tomador_fk in (68, 69, 71, 72, 73, 74, 75, 76, 77, 78, 79)
            and DR.ind_status = 3
            AND ES.MENSAGEM LIKE '%Valor total do serviço não pode ser 0%'
            AND dt_emissao >= DATEFROMPARTS(YEAR(GETDATE()), MONTH(GETDATE()), 1)
            AND DT_EMISSAO >= DATEADD(DAY, -1, GETDATE())
        """
        cursor.execute(sql)
        conn.commit()
        logger.info("Valor Zerado ClienteC: %d registro(s) atualizado(s).", cursor.rowcount)
        cursor.close()
    finally:
        if conn:
            conn.close()
