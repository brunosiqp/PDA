# encoding: utf-8
"""
testar_webhook_teams_contingencias.py

Dispara MANUALMENTE os avisos do Teams pras contingências que estiverem
acontecendo agora de verdade (ativas ou agendadas) - sem esperar uma
mudança de estado real acontecer no monitoramento. Serve pra testar se
o Workflow do Teams está recebendo e postando certo, usando o MESMO
código de consulta e de envio que o painel usa em produção (não é uma
simulação separada - importa direto do alertas_gui.py, então testa a
coisa real).

Como funciona:
  1. Consulta a SVC-RS e a SVC-AN direto nos sites da SEFAZ (mesmas
     funções que o monitoramento de verdade usa).
  2. Pra cada UF que estiver EM CONTINGÊNCIA agora, dispara um aviso de
     "Entrada de Contingência" (forçado, mesmo que o painel já tenha
     avisado antes - esse script não olha o estado anterior, só o
     estado atual).
  3. Pra cada UF AGENDADA agora, dispara um aviso de "Contingência
     Agendada" (forçado, mesma lógica).
  4. Não testa "Saída de Contingência" de propósito - esse evento só
     faz sentido como TRANSIÇÃO (de ativa pra normal), não como "estado
     atual" pra forçar (não tem uma UF "em estado de encerrada agora").

Se não tiver nenhuma contingência ativa nem agendada no momento em que
você rodar, o script avisa isso e não dispara nada (não é erro - só não
tem gatilho de teste real disponível nesse instante).

Rode na pasta do programa:
    py testar_webhook_teams_contingencias.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import alertas_gui as pda


def main():
    print("=" * 70)
    print("Teste do webhook do Teams - Contingências SEFAZ")
    print("=" * 70)
    print()

    webhook = pda._obter_webhook_teams_contingencias()
    if not webhook:
        print("ERRO: nenhum webhook do Teams cadastrado ainda em config.dat.")
        print("Rode primeiro: py cadastrar_webhook_teams_contingencias.py")
        return
    print("Webhook cadastrado: OK (a URL em si não é exibida aqui por segurança).")
    print()

    print("Consultando o estado real das contingências (direto na SEFAZ - pode levar alguns segundos)...")
    ufs_ativas = {}       # uf -> {"inicio": ..., "fim": ...}
    ufs_agendadas = []
    avisos_consulta = []

    try:
        rs_dados = pda._consultar_svc_rs()
        for uf, info in rs_dados.items():
            if info["status"] == "ativa":
                ufs_ativas[uf] = {"inicio": info["inicio"], "fim": info["fim"]}
    except Exception as e:
        avisos_consulta.append(f"Não consegui checar a SVC-RS agora: {e}")

    try:
        an_dados = pda._consultar_svc_an()
        for uf in an_dados.get("ativas", []):
            ufs_ativas.setdefault(uf, {})
        for uf in an_dados.get("agendadas", []):
            ufs_agendadas.append(uf)
    except Exception as e:
        avisos_consulta.append(f"Não consegui checar a SVC-AN agora: {e}")

    if avisos_consulta:
        print()
        for aviso in avisos_consulta:
            print(f"  aviso: {aviso}")

    print()
    print(f"Encontrado agora: {len(ufs_ativas)} UF(s) em contingência ativa, {len(ufs_agendadas)} agendada(s).")
    print()

    if not ufs_ativas and not ufs_agendadas:
        print("Nenhuma contingência ativa nem agendada nesse momento - nada pra disparar.")
        print("(Não é erro - só não tem gatilho de teste real disponível agora. Tenta de novo")
        print(" quando alguma UF estiver em contingência ou agendada.)")
        return

    print("Disparando os avisos de teste pro Teams...")
    for uf, detalhes in ufs_ativas.items():
        print(f"  -> {uf}: Entrada de Contingência (forçado)")
        pda._enviar_notificacao_teams_contingencia(uf, "iniciada", detalhes)

    for uf in ufs_agendadas:
        print(f"  -> {uf}: Contingência Agendada (forçado)")
        pda._enviar_notificacao_teams_contingencia(uf, "agendada")

    print()
    print("Pronto - confere o canal do Teams pra ver se as mensagens chegaram certinho.")
    print("Se alguma falhar, o motivo fica registrado em logs/alertas_suporte.log")
    print("(procure por 'Contingências' nesse arquivo, ou veja pela aba Logs do painel).")


if __name__ == "__main__":
    main()
