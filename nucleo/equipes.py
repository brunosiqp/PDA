"""Equipes - lógica (regras de equipe (Suporte / Monitoramento / Suporte e Monitoramento) usadas em várias telas).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""




ATRIBUICAO_AMBAS = "Suporte e Monitoramento"
# 3.2.5.0: Serviços é uma equipe à parte (não conta como Suporte nem Monitoramento) e fica fora do cálculo
# de horas e da escala (ver areas/horas_trabalhadas/logica.py, _fora_do_calculo_de_horas)
ATRIBUICAO_SERVICOS = "Serviços"
ATRIBUICOES_VALIDAS = ("Suporte", "Monitoramento", ATRIBUICAO_AMBAS, ATRIBUICAO_SERVICOS)


def _equipes_da_pessoa(atribuicao: str) -> set:
    """Devolve o conjunto de equipes que essa atribuição cobre - a
    maioria das pessoas cobre só uma, mas quem tem escala 12x36 pode
    cobrir as duas (ex.: Hugo e Hugo, pedido do Igor em 08/09/2026).
    Usado em qualquer lugar que precisa comparar/filtrar por equipe, pra
    "Suporte e Monitoramento" sempre bater com as duas."""
    if atribuicao == ATRIBUICAO_AMBAS:
        return {"Suporte", "Monitoramento"}
    return {atribuicao or "Suporte"}


def _pertence_a_equipe(atribuicao: str, equipe_filtro: str) -> bool:
    """True se `atribuicao` cobre `equipe_filtro` - ou porque é
    exatamente igual, ou porque a pessoa está em "Suporte e
    Monitoramento" (cobre as duas)."""
    return equipe_filtro in _equipes_da_pessoa(atribuicao)
