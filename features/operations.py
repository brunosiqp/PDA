import os
import time
from datetime import datetime
import pandas as pd

from core.email_utils import enviar_email
from core.utils import carregar_arquivo_env

def getEnv(
    spec: str
) -> None:

    try:
        var = carregar_arquivo_env(stack_level=3, spec_env=spec, overwrite=True)
    except Exception as e:
        print(f"[ERRO] Falha ao carregar .env ({spec}): {e}")
            
    return var

def execute(
    clientes: dict
) -> None:

        # Informações para o envio de e-mail
    smtp_info = {
        "smtp_server": os.getenv("smtp_server"),
        "smtp_port": os.getenv("smtp_port"),
        "email_from": os.getenv("email_from"),
        "email_password": os.getenv("email_password"),
    }
    destinatario = os.getenv("email_to")
    relacao = pd.DataFrame(
        {
            'Cliente': list(clientes.keys()),
            'QTD': list(clientes.values())
        }
    )

    corpo = (
            f"Rotina de monitoramento da Fila de Processamento FornecedorA - {len(clientes)} pastas acima do limite\n\n"
            + "Segue em anexo a relação dos clientes com total de documentos acima de 100\n\n"
            + "Este e-mail é gerado automaticamente, favor não responder."
    )
    assunto = f"AVISO - NFSe - Fila de Processamento FornecedorA - {datetime.now()}"

    for i in range(10):
        if enviar_email(destinatario=destinatario,
                        assunto=assunto,
                        corpo=corpo,
                        smtp_info=smtp_info,
                        anexo_temp=relacao,
                        nome_arquivo_temp='relacao_clientes',
                        tipo_arquivo_temp='.xlsx',
                        retorn_erro=True):
            print(f"Email enviado com sucesso [{len(clientes)} pasta(s) acima do limite - {datetime.now()}")
            break
        time.sleep(5)
    else:
        print(f"Falha ao enviar e-mail após 10 tentativas - Nova tentativa em 1 hora. {datetime.now()}")