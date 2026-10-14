# encoding: utf-8
"""
cadastrar_webhook_teams_contingencias.py

Cadastra em config.dat (cifrado) a URL do Workflow do Teams usada pros
avisos de Contingências SEFAZ (agendada / entrada / saída). Rode UMA VEZ,
na pasta do programa:

    py cadastrar_webhook_teams_contingencias.py

Não mexe em nenhuma outra chave já cadastrada (senhas do Dash
Financeiro, SharePoint, etc.) - só adiciona/atualiza essa uma.

Se precisar trocar a URL do webhook depois (ex.: recriou o Workflow no
Teams), é só rodar esse script de novo com a URL nova, ou usar a tela
Configurações Seguras no painel (chave: teams::contingencias_webhook).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.config_seguro import definir_valor_config_dat, obter_valor_config

URL_WEBHOOK_TEAMS_CONTINGENCIAS = (
    "https://example.invalid/"
    "powerautomate/automations/direct/cu/05/workflows/0000000000000000000084e0c0eafaa9/"
    "triggers/manual/paths/invoke?api-version=1&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&"
    "sig=REMOVIDO"
)


def main():
    print("Cadastrando o webhook do Teams (Contingências SEFAZ) em config.dat...")
    definir_valor_config_dat("teams::contingencias_webhook", URL_WEBHOOK_TEAMS_CONTINGENCIAS)
    confirmacao = obter_valor_config("teams::contingencias_webhook", "")
    if confirmacao == URL_WEBHOOK_TEAMS_CONTINGENCIAS:
        print("OK - cadastrado e confirmado com sucesso.")
        print()
        print("Os avisos de Contingência Agendada / Entrada de Contingência /")
        print("Saída de Contingência já vão passar a disparar pro Teams na")
        print("próxima vez que o monitoramento detectar uma mudança de status -")
        print("não precisa reiniciar nada além do normal.")
        print()
        print("Pode apagar este arquivo agora, se quiser (a URL já está cifrada")
        print("em config.dat, que é o que o programa realmente usa).")
    else:
        print("ALGO DEU ERRADO - o valor lido de volta não bateu com o que foi salvo.")


if __name__ == "__main__":
    main()
