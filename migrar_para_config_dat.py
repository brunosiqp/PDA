# encoding: utf-8
"""
migrar_para_config_dat.py

Lê os arquivos .env já existentes na pasta do programa e cifra as
credenciais sensíveis (senhas de banco, tokens) pro config.dat, usando
Fernet (ver core/config_seguro.py e CRIPTOGRAFIA.md pra entender como
isso funciona por baixo dos panos).

NÃO É DESTRUTIVO: os arquivos .env originais NÃO são apagados nem
alterados por esse script. Depois de confirmar que tudo continua
funcionando com o config.dat, é seguro (e recomendado) apagar a LINHA
da senha/token de dentro de cada .env manualmente (não o arquivo
inteiro - as outras variáveis como db_server, query, etc. continuam
sendo lidas normalmente do .env, só a senha some de lá) - mas isso é
uma decisão sua, esse script não faz isso sozinho.

SEGURO RODAR MAIS DE UMA VEZ: se uma chave já estiver migrada, esse
script só sobrescreve com o valor atual do .env (não duplica nem dá
erro).

Como rodar (na pasta do programa, junto do alertas_gui.py):
    py migrar_para_config_dat.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import dotenv_values

from core.config_seguro import definir_valor_config_dat, listar_chaves_config_dat

PASTA_BASE = os.path.dirname(os.path.abspath(__file__))

# Arquivos com um formato PRÓPRIO (fora do padrão genérico de cliente),
# cada um com seu campo sensível e o nome de origem já combinando com o
# que os loaders dedicados em alertas_gui.py esperam encontrar.
ARQUIVOS_ESPECIAIS = {
    ".env": [("cliente_c", "DB_PASSWORD")],
    ".env.sharepoint": [("sharepoint", "SHAREPOINT_PASSWORD")],
    ".env.cliente_a": [("cliente_a", "CLIENTE_A_DB_PASSWORD")],
    ".env.monitoramento": [("monitoramento", "MONITORAMENTO_DB_PASSWORD")],
    ".env.indicadores_movidesk": [("indicadores_movidesk", "db_password")],
    ".env.indicadores_workflow": [("indicadores_workflow", "db_password")],  # não usado no app atual, migrado por completude
    ".env.horas_movidesk": [("horas_movidesk", "MOVIDESK_TOKEN")],
    ".env.email": [("email", "email_password")],  # não usado no app atual, migrado por completude
}


def migrar_arquivo_especial(nome_arquivo: str, campos: list) -> list:
    caminho = os.path.join(PASTA_BASE, nome_arquivo)
    migrados = []
    if not os.path.exists(caminho):
        return migrados
    valores = dotenv_values(caminho)
    for origem, campo in campos:
        valor = valores.get(campo)
        if valor:
            definir_valor_config_dat(f"{origem}::{campo}", valor)
            migrados.append(f"{origem}::{campo}")
    return migrados


def migrar_clientes_genericos() -> list:
    """Todo .env.<nome> que NÃO está na lista de arquivos especiais acima
    é tratado como um cliente genérico (mesmo padrão usado pela classe
    Cliente em alerta_core/cliente.py) - migra o campo db_password."""
    migrados = []
    for nome_arquivo in sorted(os.listdir(PASTA_BASE)):
        if not nome_arquivo.startswith(".env."):
            continue
        if nome_arquivo in ARQUIVOS_ESPECIAIS:
            continue
        if nome_arquivo.endswith(".example"):
            continue
        caminho = os.path.join(PASTA_BASE, nome_arquivo)
        valores = dotenv_values(caminho)
        senha = valores.get("db_password")
        if not senha:
            continue
        origem = nome_arquivo[len(".env."):].lower()
        definir_valor_config_dat(f"{origem}::db_password", senha)
        migrados.append(f"{origem}::db_password")
    return migrados


def main():
    print("=" * 70)
    print("Migração de credenciais para config.dat (cifrado com Fernet)")
    print("=" * 70)
    print()

    total_migrado = []

    print("Arquivos com formato próprio (SharePoint, ClienteA, Monitoramento, etc.):")
    for nome_arquivo, campos in ARQUIVOS_ESPECIAIS.items():
        migrados = migrar_arquivo_especial(nome_arquivo, campos)
        if migrados:
            for chave in migrados:
                print(f"  OK  {nome_arquivo} -> {chave}")
            total_migrado.extend(migrados)
        elif os.path.exists(os.path.join(PASTA_BASE, nome_arquivo)):
            print(f"  --  {nome_arquivo} encontrado, mas sem valor pra migrar")
        else:
            print(f"  --  {nome_arquivo} não existe nessa pasta (pulado)")

    print()
    print("Clientes genéricos (.env.<nome>, campo db_password):")
    migrados_clientes = migrar_clientes_genericos()
    for chave in migrados_clientes:
        print(f"  OK  {chave}")
    total_migrado.extend(migrados_clientes)

    print()
    print("=" * 70)
    print(f"Total migrado nesta execução: {len(total_migrado)} chave(s)")
    print(f"Total de chaves em config.dat agora: {len(listar_chaves_config_dat())}")
    print("=" * 70)
    print()
    print("Os arquivos .env originais NÃO foram alterados nem apagados.")
    print("O programa já vai preferir os valores cifrados automaticamente")
    print("a partir de agora - não precisa reiniciar nada além do normal.")
    print()
    print("Se quiser, agora é seguro remover manualmente só a LINHA da")
    print("senha/token de dentro de cada .env (mantendo as outras")
    print("variáveis) - mas isso é opcional e não é feito por este script.")


if __name__ == "__main__":
    main()
