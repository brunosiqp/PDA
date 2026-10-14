"""Sessões e permissões - lógica (criação/validação de sessão de login e as regras de acesso de cada card).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import secrets
from datetime import datetime
from datetime import timedelta
from typing import Optional

from nucleo.usuarios import DURACAO_INATIVIDADE_MINUTOS
from nucleo.usuarios import SESSIONS



def _criar_sessao(
    usuario: str, admin: bool, pode_manutencao_alertas: bool = False,
    pode_relatorios_cliente_a: bool = False, pode_dash_financeiro: bool = False,
    pode_manutencao_rejeicoes: bool = False, pode_dados_sensiveis: bool = False,
    pode_manutencao_relatorios: bool = False, pode_manutencao_usuarios: bool = False,
    nome: str = None, genero: str = "",
    pode_feedbacks: bool = False, pode_ver_logs: bool = False,
    pode_indicadores_mensais: bool = False,
    pode_reprocessamento_cte2: bool = False,
    pode_nnu_enchanced: bool = False,
    pode_editar_central: bool = False,
    pode_servicos_adm: bool = False,
) -> str:
    token = secrets.token_hex(32)
    SESSIONS[token] = {
        "usuario": usuario,
        "nome": nome or usuario,
        "genero": genero or "",
        "admin": admin,
        "pode_manutencao_alertas": pode_manutencao_alertas,
        "pode_relatorios_cliente_a": pode_relatorios_cliente_a,
        "pode_dash_financeiro": pode_dash_financeiro,
        "pode_manutencao_rejeicoes": pode_manutencao_rejeicoes,
        "pode_dados_sensiveis": pode_dados_sensiveis,
        "pode_manutencao_relatorios": pode_manutencao_relatorios,
        "pode_manutencao_usuarios": pode_manutencao_usuarios,
        "pode_feedbacks": pode_feedbacks,
        "pode_ver_logs": pode_ver_logs,
        "pode_indicadores_mensais": pode_indicadores_mensais,
        "pode_reprocessamento_cte2": pode_reprocessamento_cte2,
        "pode_nnu_enchanced": pode_nnu_enchanced,
        "pode_editar_central": pode_editar_central,
        "pode_servicos_adm": pode_servicos_adm,
        "expira": datetime.now() + timedelta(minutes=DURACAO_INATIVIDADE_MINUTOS),
    }
    return token


def _sessao_atual(token: Optional[str], renovar: bool = True) -> Optional[dict]:
    """Busca a sessão pelo token. Por padrão, RENOVA o prazo de inatividade
    (sessão "deslizante" - continua valendo enquanto a pessoa usa o painel).
    `renovar=False` é usado só pela pergunta automática de status (a página
    de Alertas consulta sozinha a cada 2s) - isso NÃO conta como atividade
    de verdade, senão a sessão nunca expiraria com a aba só aberta."""
    if not token:
        return None
    sessao = SESSIONS.get(token)
    if not sessao:
        return None
    if datetime.now() > sessao["expira"]:
        SESSIONS.pop(token, None)
        return None
    if renovar:
        sessao["expira"] = datetime.now() + timedelta(minutes=DURACAO_INATIVIDADE_MINUTOS)
    return sessao


def _tem_acesso_manutencao_alertas(sessao: dict) -> bool:
    """Admins sempre têm acesso. Usuários de visualização só têm acesso à
    Manutenção de Alertas em Banco se tiverem a permissão adicional
    marcada especificamente pra eles na aba Usuários."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_manutencao_alertas"))


def _tem_acesso_relatorios_cliente_a(sessao: dict) -> bool:
    """Mesma ideia de _tem_acesso_manutencao_alertas, mas pro card de
    Relatórios ClienteA - admin por padrão, liberável por pessoa na aba
    Usuários."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_relatorios_cliente_a"))


def _tem_acesso_dash_financeiro(sessao: dict) -> bool:
    """Mesma ideia, pro card de Atualização Dash Financeiro."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_dash_financeiro"))


def _tem_acesso_manutencao_rejeicoes(sessao: dict) -> bool:
    """Mesma ideia, pro card de Manutenção Rejeições em Banco."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_manutencao_rejeicoes"))


def _tem_acesso_dados_sensiveis(sessao: dict) -> bool:
    """DIFERENTE de todas as outras permissões desse painel: aqui não tem
    "admin sempre tem acesso" - String Connections é uma permissão à
    parte, precisa estar marcada especificamente pra pessoa, mesmo que
    ela seja administradora. Pedido explícito - String Connections
    carrega strings de conexão de banco de clientes, então o acesso é
    mais restrito de propósito."""
    return bool(sessao.get("pode_dados_sensiveis"))


def _tem_acesso_manutencao_usuarios(sessao: dict) -> bool:
    """Precisa ser admin E ter a permissão especial marcada (não basta só
    uma das duas) - agora que esse card SUBSTITUIU a antiga tela
    "Usuários" (gerencia login do PDA, permissões, vínculo Movidesk E o
    cadastro/desativação em produção), reforçando o pedido do Igor de
    04-06/09/2026: "o card é apenas para adms", mesmo que por engano
    alguém marque a permissão numa conta que não é administradora."""
    return bool(sessao.get("admin")) and bool(sessao.get("pode_manutencao_usuarios"))


def _tem_acesso_manutencao_relatorios(sessao: dict) -> bool:
    """Mesma ideia de _tem_acesso_manutencao_alertas, pro card de
    Manutenção de Relatórios em Banco."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_manutencao_relatorios"))


def _tem_acesso_dashboards_clientes(sessao: dict) -> bool:
    """Card em Beta (07/09/2026) - acesso simples de admin, sem permissão
    extra à parte (diferente de Dados Sensíveis/Manutenção de Usuários) -
    pedido do Igor foi só "acessível apenas para ADM's". 3.1.6.0: olha o
    cadastro atual (não só a sessão do login), pro card e a página usarem a
    mesma regra mesmo depois de alguém virar ou deixar de ser administrador."""
    from nucleo.usuarios import USUARIOS_WEB  # aqui dentro: este módulo é importado pelo de usuários
    info = USUARIOS_WEB.get(sessao.get("usuario") or "")
    return bool(info.get("admin")) if info is not None else bool(sessao.get("admin"))


def _tem_acesso_feedbacks(sessao: dict) -> bool:
    """Card dedicado de Feedbacks e Alinhamentos (13/09/2026) - MESMO
    padrão restrito de Dados Sensíveis/Manutenção de Usuários: precisa
    ser admin E ter a permissão pode_feedbacks concedida à parte (não
    ganha automático só por ser admin). Substituiu o modelo antigo, que
    era "qualquer admin vê/insere de qualquer equipe" sem permissão
    própria - agora precisa da permissão explícita."""
    return bool(sessao.get("admin")) and bool(sessao.get("pode_feedbacks"))


def _tem_acesso_logs(sessao: dict) -> bool:
    """Logs (15/09/2026) - antes era só admin. Agora admin continua tendo
    acesso automático (não muda o que já funcionava), mas dá pra
    conceder a permissão pode_ver_logs pra quem NÃO é admin também -
    pedido do Igor foi "vincular perm na leitura de logs" na aba de
    usuários, ampliando o acesso em vez de restringir."""
    return bool(sessao.get("admin")) or bool(sessao.get("pode_ver_logs"))


def _tem_acesso_reprocessamento_cte2(sessao: dict) -> bool:
    """Reprocessamento CTe2 (2.35.4.0): liga/pausa uma automação que chama a API de
    produção do CTe2, então só com a permissão pode_reprocessamento_cte2 concedida à
    parte. Ser administrador não dá acesso sozinho (e não é exigido: quem cuida do
    reprocessamento, como o Caio, que desenvolveu, pode não ser admin)."""
    return bool(sessao.get("pode_reprocessamento_cte2"))


def _tem_acesso_servicos_adm(sessao: dict) -> bool:
    """Serviços ADM (3.3.1.0): Calendário de GMUD's e Indicadores Serviços. Permissão à parte, concedida por um admin;
    ser administrador não dá acesso sozinho."""
    return bool(sessao.get("pode_servicos_adm"))


def _tem_acesso_nnu_enchanced(sessao: dict) -> bool:
    """NNU Enchanced: desde a 3.5.1.0 (pedido do Igor, mesma lógica do LongNameJanitor ClienteQ) abre pra todo mundo
    logado (tratativa guiada e acompanhar as automações); configurar, pausar, sair da simulação e rodar é só
    administrador, conferido nas rotas POST. A permissão à parte pode_nnu_enchanced (3.2.2.0) deixou de ser usada e saiu
    da tela de Usuários (a chave continua no usuarios.json)."""
    return bool(sessao)


def _tem_acesso_nnu_status(sessao: dict) -> bool:
    """NNU · status 20 → 15 (beta, 3.4.9.0): é uma aba do NNU Enchanced, então vê quem vê o NNU Enchanced (todo mundo
    desde a 3.5.1.0); mexer (configurar, ligar, simulação, rodar, reenviar e-mail) é só administrador, nas rotas POST."""
    return _tem_acesso_nnu_enchanced(sessao)


def _tem_acesso_indicadores_mensais(sessao: dict) -> bool:
    """Indicadores Mensais (2.33.7.0): grava no banco do Movidesk (efetividade
    dos tickets e justificativa do NOC), então segue o padrão restrito de
    Feedbacks: admin E a permissão pode_indicadores_mensais concedida à parte."""
    return bool(sessao.get("admin")) and bool(sessao.get("pode_indicadores_mensais"))


# ---------------------------------------------------------------------------
# Troca de senha obrigatória (2.34.7.3): quem entra com a senha padrão de
# cadastro (SenhaInicial@1) não ganha sessão; ganha um passe curto (cookie
# "troca_senha", 10 min, uso único) que libera a tela de alterar senha sem
# pedir a senha atual de novo. Só a tela de troca aceita esse passe.
# ---------------------------------------------------------------------------
DURACAO_TROCA_SENHA_MINUTOS = 10
TROCAS_SENHA_PENDENTES: dict = {}  # token -> {"usuario": str, "expira": datetime}


def criar_troca_senha_pendente(usuario: str) -> str:
    agora = datetime.now()
    for tok in [t for t, p in TROCAS_SENHA_PENDENTES.items() if p["expira"] < agora or p["usuario"] == usuario]:
        TROCAS_SENHA_PENDENTES.pop(tok, None)  # vencidos e passes antigos da mesma pessoa
    token = secrets.token_hex(24)
    TROCAS_SENHA_PENDENTES[token] = {"usuario": usuario, "expira": agora + timedelta(minutes=DURACAO_TROCA_SENHA_MINUTOS)}
    return token


def usuario_da_troca_pendente(token) -> Optional[str]:
    pendente = TROCAS_SENHA_PENDENTES.get(token or "")
    if not pendente:
        return None
    if pendente["expira"] < datetime.now():
        TROCAS_SENHA_PENDENTES.pop(token, None)
        return None
    return pendente["usuario"]


def consumir_troca_pendente(token) -> None:
    TROCAS_SENHA_PENDENTES.pop(token or "", None)
