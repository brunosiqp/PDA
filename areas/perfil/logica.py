"""Perfil - lógica (dados do perfil de cada pessoa (indicadores, horas, histórico de carreira)).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import json
import logging
import os
import threading
from datetime import date
from datetime import datetime
from datetime import timedelta
from typing import Optional

from areas.ferias.logica import FERIAS
from areas.ferias.logica import _lock_ferias
from areas.horas_trabalhadas.logica import _consultar_horas_trabalhadas
from areas.horas_trabalhadas.logica import _contar_tickets_acao_total
from areas.horas_trabalhadas.logica import _minutos_para_horas_str
from areas.manutencao_usuarios.movidesk import _buscar_usuario_movidesk
from areas.manutencao_usuarios.movidesk import _nome_movidesk_vinculado
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.fotos import _caminho_foto_usuario
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


def _calcular_resumo_horas_periodo(nome_movidesk: str, data_inicio: date, data_fim: date) -> dict:
    """Calcula horas trabalhadas, meta e tickets com ação de uma pessoa
    (pelo nome dela no Movidesk) num período específico - usado tanto
    pro mês atual quanto pra comparação com o mês anterior no perfil,
    evitando duplicar essa lógica nos dois lugares."""
    resultado = {"percentual": None, "horas": None, "meta": None, "tickets": None, "erro": None}
    resultado_horas = _consultar_horas_trabalhadas(data_inicio.strftime("%Y-%m-%d"), data_fim.strftime("%Y-%m-%d"))
    if not resultado_horas.get("ok"):
        resultado["erro"] = resultado_horas.get("erro")
        return resultado
    linhas_pessoa = [l for l in resultado_horas["linhas"] if l["analista"] == nome_movidesk]
    total_minutos = sum(l["minutos_trabalhados"] for l in linhas_pessoa)
    total_tickets = sum(l["qtd_tickets"] for l in linhas_pessoa)
    meta_minutos = resultado_horas["meta_periodo_por_analista"].get(nome_movidesk, 0)
    resultado["horas"] = _minutos_para_horas_str(total_minutos)
    resultado["meta"] = _minutos_para_horas_str(meta_minutos)
    resultado["percentual"] = round(total_minutos / meta_minutos * 100, 1) if meta_minutos > 0 else None
    resultado["tickets"] = total_tickets
    return resultado




_NOMES_MESES_PT = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]


def _montar_dados_perfil_mes_anterior(usuario_login: str) -> dict:
    """Mesmo resumo de horas/tickets que aparece no perfil, mas pro mês
    ANTERIOR ao atual (mês fechado por completo, sem o "corte até hoje"
    que o mês corrente tem) - usado na opção de comparação no perfil."""
    hoje = datetime.now().date()
    primeiro_dia_atual = hoje.replace(day=1)
    ultimo_dia_anterior = primeiro_dia_atual - timedelta(days=1)
    primeiro_dia_anterior = ultimo_dia_anterior.replace(day=1)

    resultado = {
        "nome_mes": f"{_NOMES_MESES_PT[primeiro_dia_anterior.month - 1]} de {primeiro_dia_anterior.year}",
        "vinculado_movidesk": bool(USUARIOS_WEB.get(usuario_login, {}).get("usuario_movidesk_id")),
        "percentual_horas_mes": None, "horas_trabalhadas_mes": None,
        "meta_horas_mes": None, "tickets_mes": None, "erro_horas": None,
    }

    nome_movidesk, erro_vinculo = _nome_movidesk_vinculado(usuario_login)
    if erro_vinculo:
        resultado["erro_horas"] = erro_vinculo
        return resultado
    if not nome_movidesk:
        return resultado

    resumo = _calcular_resumo_horas_periodo(nome_movidesk, primeiro_dia_anterior, ultimo_dia_anterior)
    resultado["percentual_horas_mes"] = resumo["percentual"]
    resultado["horas_trabalhadas_mes"] = resumo["horas"]
    resultado["meta_horas_mes"] = resumo["meta"]
    resultado["tickets_mes"] = resumo["tickets"]
    resultado["erro_horas"] = resumo["erro"]
    return resultado


def _montar_dados_perfil(usuario_login: str) -> Optional[dict]:
    """Junta as informações de perfil de uma pessoa: nome, atribuição,
    férias/day off futuros ou em andamento, % de horas trabalhadas no
    mês atual, e quantidade de tickets com ação no mês. Devolve None se
    o usuário não existir."""
    info = USUARIOS_WEB.get(usuario_login)
    if not info:
        return None

    hoje = datetime.now().date()
    primeiro_dia_mes = hoje.replace(day=1)

    dados = {
        "usuario": usuario_login,
        "nome": info.get("nome") or usuario_login,
        "atribuicao": info.get("atribuicao") or "Suporte",
        "admin": bool(info.get("admin")),
        "ativo": info.get("ativo", True),
        "tem_foto": _caminho_foto_usuario(usuario_login) is not None,
    }

    # Férias/Day Off futuros ou em andamento (a partir de hoje)
    hoje_iso = hoje.strftime("%Y-%m-%d")
    with _lock_ferias:
        periodos_pessoa = [
            dict(f) for f in FERIAS
            if f.get("usuario") == usuario_login and f.get("fim", "") >= hoje_iso
        ]
    for p in periodos_pessoa:
        p.setdefault("tipo", "ferias")
    periodos_pessoa.sort(key=lambda p: p["inicio"])
    dados["periodos_futuros"] = periodos_pessoa

    # Histórico de carreira (cargos/áreas ao longo do tempo) - do mais
    # RECENTE pro mais antigo (pedido explícito), pra ficar tipo LinkedIn
    with _lock_historico_carreira:
        historico_pessoa = [
            dict(h) for h in HISTORICO_CARREIRA if h.get("usuario") == usuario_login
        ]
    historico_pessoa.sort(key=lambda h: h["inicio"], reverse=True)
    dados["historico_carreira"] = historico_pessoa

    # % de horas trabalhadas no mês + tickets com ação - só dá pra
    # calcular se a pessoa estiver vinculada a um registro da tabela
    # usuarios (banco movidesk), já que é o "nome oficial" usado nos
    # apontamentos de horas
    id_movidesk = info.get("usuario_movidesk_id")
    dados["vinculado_movidesk"] = bool(id_movidesk)
    # cargo do PDA (preenchido à mão ou pela sincronização com o Movidesk): desde a 3.2.0.0 ele manda;
    # o do banco do Movidesk só entra quando o PDA não tem cargo nenhum
    dados["cargo"] = info.get("cargo") or None
    dados["percentual_horas_mes"] = None
    dados["horas_trabalhadas_mes"] = None
    dados["meta_horas_mes"] = None
    dados["tickets_mes"] = None
    dados["erro_horas"] = None
    dados["tickets_acao_total"] = None
    dados["primeira_atividade"] = None
    dados["total_horas_trabalhadas"] = None
    dados["erro_indicadores_gerais"] = None

    if id_movidesk:
        detalhe = _buscar_usuario_movidesk(id_movidesk)
        if detalhe.get("ok"):
            dados["cargo"] = dados["cargo"] or detalhe["registro"].get("cargo") or None
            nome_movidesk = str(detalhe["registro"].get("nome") or "").strip().upper()
            if nome_movidesk:
                resumo = _calcular_resumo_horas_periodo(nome_movidesk, primeiro_dia_mes, hoje)
                dados["percentual_horas_mes"] = resumo["percentual"]
                dados["horas_trabalhadas_mes"] = resumo["horas"]
                dados["meta_horas_mes"] = resumo["meta"]
                dados["tickets_mes"] = resumo["tickets"]
                dados["erro_horas"] = resumo["erro"]

                # indicadores gerais (desde sempre, sem filtro de período) -
                # pedido explícito do Igor: diferente do resumo acima
                # (sempre só do mês atual), esse total olha TODOS os
                # apontamentos já feitos por essa pessoa
                total_geral = _contar_tickets_acao_total(nome_movidesk)
                if total_geral.get("ok"):
                    dados["tickets_acao_total"] = total_geral["total_tickets"]
                    dados["primeira_atividade"] = total_geral["primeira_atividade"]
                    dados["total_horas_trabalhadas"] = total_geral["total_horas"]
                else:
                    dados["erro_indicadores_gerais"] = total_geral.get("erro")
        else:
            dados["erro_horas"] = detalhe.get("erro")

    # Data de início manual (opcional, preenchida em Editar usuários)
    # SUBSTITUI a "primeira atividade" calculada a partir do Movidesk -
    # pedido do Igor em 15/09/2026, já que a data de início é mais
    # confiável (o histórico de apontamentos antigo pode ter buracos ou
    # estar incompleto). Quando isso acontece, o perfil mostra um aviso
    # avisando que valores antigos podem variar/estar incompletos.
    dados["primeira_atividade_e_data_inicio_manual"] = False
    data_inicio_pessoa = info.get("data_inicio")
    if data_inicio_pessoa:
        try:
            dados["primeira_atividade"] = datetime.strptime(data_inicio_pessoa, "%Y-%m-%d").strftime("%d/%m/%Y")
            dados["primeira_atividade_e_data_inicio_manual"] = True
        except (ValueError, TypeError):
            pass

    return dados


def _caminho_historico_carreira_json() -> str:
    return os.path.join(_base_path_app(), "historico_carreira.json")


def _carregar_historico_carreira() -> list:
    caminho = _caminho_historico_carreira_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return dados
        except Exception:
            logger.exception("Não foi possível ler historico_carreira.json, começando vazio.")
    return []


def _salvar_historico_carreira(dados: list) -> None:
    caminho = _caminho_historico_carreira_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar historico_carreira.json.")


# Histórico de carreira (cargos/áreas ao longo do tempo) exibido no
# Perfil - cada item: {id, usuario, cargo, area ("suporte"/"monitoramento"
# /""), inicio ("AAAA-MM"), fim ("AAAA-MM" ou None se for o cargo atual)}.
# "piloto" com os dados reais do Igor (pedido dele mesmo, 04/09/2026),
# só é usado se o arquivo ainda não existir - depois disso quem manda é
# o historico_carreira.json.
_HISTORICO_CARREIRA_PILOTO: list = [
    {"id": 1, "usuario": "igor", "cargo": "Assistente de Suporte", "area": "suporte", "inicio": "2024-10", "fim": "2025-05"},
    {"id": 2, "usuario": "igor", "cargo": "Analista Júnior", "area": "suporte", "inicio": "2025-06", "fim": "2026-05"},
    {"id": 3, "usuario": "igor", "cargo": "Analista Pleno", "area": "monitoramento", "inicio": "2026-06", "fim": "2026-08"},
    {"id": 4, "usuario": "igor", "cargo": "Analista Sênior", "area": "monitoramento", "inicio": "2026-09", "fim": None},
]
HISTORICO_CARREIRA: list = _carregar_historico_carreira() or list(_HISTORICO_CARREIRA_PILOTO)


_lock_historico_carreira = threading.Lock()
