"""E-mails automáticos - lógica (boas-vindas, marcos de 45/90 dias de empresa e aviso de feedback registrado, com fotos via CID).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import html as html_utils
import json
import logging
import os
import smtplib
from datetime import date
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from areas.perfil.logica import HISTORICO_CARREIRA
from core.config_seguro import obter_valor_config as _obter_valor_config
from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.config import _obter_config_hibrido
from nucleo.fotos import _caminho_foto_usuario
from nucleo.usuarios import USUARIOS_WEB

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


# ---------------------------------------------------------------------------
# E-mail de boas-vindas - pedido do Igor em 06/09/2026, com disparo
# opcional já embutido no Cadastro (checkbox) desde 07/09/2026.
# ---------------------------------------------------------------------------
LINK_PDA_WEB = "http://192.0.2.198:8765/"


def _config_email_boas_vindas() -> dict:
    """Credenciais SMTP dos e-mails automáticos do PDA (boas-vindas, 45/90
    dias de empresa, notificação de feedback/alinhamento) -
    CREDENCIAIS_CENTRALIZADAS.env primeiro (seção [boas_vindas_email]),
    cai pro .env.boas_vindas tradicional se essa seção não existir.

    Desde 12/09/2026 usa a MESMA conta dos alertas legados
    (avisos@example.com, seção [infra_email]) - antes era
    uma conta própria separada (suporte@example.com), trocada a
    pedido do Igor. A seção continua separada de [infra_email] mesmo
    assim (não lê de lá diretamente), só que hoje as duas apontam pra
    mesma conta - assim, se um dia precisar separar de novo, é só trocar
    os valores aqui sem mexer nos alertas legados."""
    valores = _obter_config_hibrido(
        "boas_vindas_email", ".env.boas_vindas",
        ["smtp_server", "smtp_port", "email_from", "email_password"],
    )
    return {
        "smtp_server": valores["smtp_server"],
        "smtp_port": valores["smtp_port"],
        "email_from": valores["email_from"],
        "email_password": _obter_valor_config("boas_vindas::email_password", valores["email_password"]),
    }


def _enviar_email_com_fotos(destinatario: str, assunto: str, corpo_html: str, smtp_info: dict) -> None:
    """Envia um e-mail HTML com as fotos do Igor/Debora embutidas via CID
    (Content-ID) - a forma que REALMENTE funciona no Outlook desktop,
    diferente de data:image;base64 direto no <img src>, que o Outlook
    não renderiza (usa o motor do Word, sem suporte a data URI).

    Usa smtplib + email (biblioteca padrão do Python) em vez de
    enviar_email() de core/email_utils.py, porque esse módulo já
    existia no ambiente do Igor antes de eu começar a mexer aqui - não
    tenho o código-fonte dele pra confirmar se suporta anexo/CID, então
    prefiro não arriscar mudar um módulo que eu nunca vi por dentro.

    O `corpo_html` já deve trazer src="cid:foto_igor" e
    src="cid:foto_debora" nos lugares certos - essa função só anexa os
    arquivos de fotos_usuarios/igor.* e fotos_usuarios/debora.* com
    esses Content-IDs (usa a mesma _caminho_foto_usuario() já usada pro
    resto do app, então funciona com qualquer extensão suportada, não
    só .jpg)."""
    msg = MIMEMultipart("related")
    msg["Subject"] = assunto
    msg["From"] = smtp_info["email_from"]
    msg["To"] = destinatario

    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    for cid, usuario_foto in (("foto_igor", "igor"), ("foto_debora", "debora")):
        caminho = _caminho_foto_usuario(usuario_foto)
        if not caminho:
            continue
        try:
            with open(caminho, "rb") as f:
                img = MIMEImage(f.read())
            img.add_header("Content-ID", f"<{cid}>")
            img.add_header("Content-Disposition", "inline", filename=os.path.basename(caminho))
            msg.attach(img)
        except Exception:
            logger.exception("Não foi possível anexar a foto '%s' (%s) no e-mail.", usuario_foto, caminho)

    with smtplib.SMTP(smtp_info["smtp_server"], int(smtp_info["smtp_port"]), timeout=30) as server:
        server.starttls()
        server.login(smtp_info["email_from"], smtp_info["email_password"])
        server.sendmail(smtp_info["email_from"], [destinatario], msg.as_string())


def _montar_email_boas_vindas_html(nome: str, login: str, senha: str) -> str:
    """E-mail de boas-vindas pro novo colaborador - avisa que esse é o
    acesso ao PDA, traz o link direto, os dados de acesso (login/senha)
    que o Igor acabou de cadastrar, e avisa que só funciona dentro da
    VPN da Empresa. UMA caixa de credenciais só - login e senha são o
    MESMO acesso (pedido explícito do Igor em 07/09/2026, não dois
    acessos separados). Sem o parágrafo "qualquer dúvida, acione o Igor
    e a Debora" (removido em 07/09/2026) - o rodapé com "Desenvolvido
    por" já deixa claro quem procurar."""
    primeiro_nome = (nome or "").strip().split(" ")[0] or "tudo bem"

    caixa_credenciais = f"""
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 18px 0;">
              <p style="font-size:11px; color:#2db8cf; text-transform:uppercase; letter-spacing:.04em; font-weight:700; margin:0 0 10px 0;">Dados de acesso</p>
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Login: <b>{login}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0;">Senha: <b>{senha}</b></p>
            </div>"""

    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">
              Seja bem-vindo(a), {primeiro_nome}! 🎉
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 16px 0;">
              Este é o seu acesso ao <b style="color:#2db8cf;">PDA - Painel de Automações</b>, a ferramenta
              interna que a equipe de Suporte e Monitoramento da Empresa usa no dia a dia.
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              As informações sobre como usar a ferramenta, os recursos disponíveis e o que muda na sua rotina
              serão passadas diretamente pela equipe nos próximos passos.
            </p>
            {caixa_credenciais}
            <p style="font-size:11.5px; color:#8b98a5; margin:-6px 0 20px 0; line-height:1.6;">
              Por segurança, troque essa senha assim que possível.
            </p>
            <div style="text-align:center; margin:28px 0;">
              <a href="{LINK_PDA_WEB}" style="display:inline-block; background:linear-gradient(135deg, #2db8cf, #b0cb1c); color:#08090c; font-weight:700; font-size:14px; text-decoration:none; padding:13px 28px; border-radius:9px;">
                Acessar o PDA
              </a>
              <p style="font-size:11.5px; color:#8b98a5; margin:12px 0 0 0;">
                <a href="{LINK_PDA_WEB}" style="color:#2db8cf; text-decoration:none;">{LINK_PDA_WEB}</a>
              </p>
            </div>
            <div style="background:rgba(241,76,76,.08); border:1px solid rgba(241,76,76,.25); border-radius:9px; padding:12px 16px; margin:0 0 24px 0;">
              <p style="font-size:12.5px; color:#ff9d9d; margin:0; line-height:1.6;">
                ⚠️ O PDA só é acessível de <b>dentro da VPN da Empresa</b>. Fora da VPN, o link não vai abrir.
              </p>
            </div>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0 0 14px 0;">Desenvolvido por</p>
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_igor" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #2db8cf;" alt="Igor Leal">
                    <div style="font-size:11px; color:#2db8cf; font-weight:700; line-height:1.4;">Igor Leal</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Analista Sênior</div>
                  </td>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_debora" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #b0cb1c;" alt="Debora Sampaio">
                    <div style="font-size:11px; color:#b0cb1c; font-weight:700; line-height:1.4;">Debora Sampaio</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Especialista</div>
                  </td>
                </tr>
              </table>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _enviar_email_boas_vindas(nome: str, email_destino: str, login: str, senha: str) -> None:
    """Levanta exceção em caso de falha - quem chama decide como reportar
    (a rota converte isso num JSON de erro pro operador ver na hora).

    `email_destino` (pra ONDE o e-mail vai) e `login` (o que aparece
    escrito como "Login" DENTRO do e-mail) são coisas DIFERENTES - erro
    corrigido em 07/09/2026: no botão de teste (aba Editar usuários), o
    e-mail pessoal cadastrado estava sendo usado como as duas coisas,
    mostrando o e-mail pessoal como se fosse o login de acesso, quando
    o login de verdade é o usuário do PDA (o mesmo da aba Usuários)."""
    smtp_info = _config_email_boas_vindas()
    corpo_html = _montar_email_boas_vindas_html(nome, login, senha)
    _enviar_email_com_fotos(
        destinatario=email_destino,
        assunto="Bem-vindo(a) ao PDA - Painel de Automações",
        corpo_html=corpo_html,
        smtp_info=smtp_info,
    )


# ---------------------------------------------------------------------------
# Alertas de 45/90 dias de empresa - pedido do Igor em 10/09/2026. Roda
# uma vez por dia (não precisa ser mais frequente que isso) e avisa os 4
# destinatários fixos quando alguém está chegando perto de completar 45
# ou 90 dias de casa, pra dar tempo de organizar o feedback.
# ---------------------------------------------------------------------------
MARCOS_TEMPO_EMPRESA = (45, 90)
DIAS_ANTECEDENCIA_ALERTA_TEMPO_EMPRESA = 5  # avisa de X dias antes até o dia exato
DESTINATARIOS_ALERTA_TEMPO_EMPRESA = [
    "debora.almeida@example.com",
    "debora@example.com",
    "everton.nogueira@example.com",
    "igor.leal@example.com",
]

# Lista PRÓPRIA (não herda mais de DESTINATARIOS_ALERTA_TEMPO_EMPRESA) -
# pedido do Igor em 14/09/2026: tirar a debora.almeida SÓ do alerta de
# feedback/alinhamento (o de 45/90 dias continua com ela normalmente).
DESTINATARIOS_ALERTA_FEEDBACK = [
    "debora@example.com",
    "everton.nogueira@example.com",
    "igor.leal@example.com",
    "contato74@example.com",
]


def _caminho_alertas_tempo_empresa_json() -> str:
    return os.path.join(_base_path_app(), "alertas_tempo_empresa_enviados.json")


def _carregar_alertas_tempo_empresa_enviados() -> set:
    """Conjunto de "usuario|marco" já notificados - pra nunca mandar o
    mesmo aviso duas vezes (o job roda todo dia, então sem isso a pessoa
    receberia o mesmo e-mail repetido todo dia dentro da janela de
    antecedência)."""
    caminho = _caminho_alertas_tempo_empresa_json()
    if os.path.exists(caminho):
        try:
            with open(caminho, "r", encoding="utf-8") as f:
                dados = json.load(f)
            if isinstance(dados, list):
                return set(dados)
        except Exception:
            logger.exception("Não foi possível ler alertas_tempo_empresa_enviados.json.")
    return set()


def _salvar_alertas_tempo_empresa_enviados(enviados: set) -> None:
    caminho = _caminho_alertas_tempo_empresa_json()
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            json.dump(sorted(enviados), f, indent=2, ensure_ascii=False)
    except Exception:
        logger.exception("Não foi possível salvar alertas_tempo_empresa_enviados.json.")


def _cargo_mais_recente(usuario: str) -> str:
    """Cargo atual da pessoa (última entrada do histórico de carreira,
    fim=None ou a mais recente por início) - "-" se não tiver nada
    cadastrado pra ela."""
    entradas = [h for h in HISTORICO_CARREIRA if h.get("usuario") == usuario]
    if not entradas:
        return "-"
    entradas.sort(key=lambda h: h.get("inicio") or "", reverse=True)
    return entradas[0].get("cargo") or "-"


def _montar_email_tempo_empresa_html(nome: str, cargo: str, data_inicio_str: str, marco_dias: int) -> str:
    """Mesma identidade visual do e-mail de boas-vindas (gradiente
    teal/lime, cabeçalho PDA) - avisa os destinatários fixos que uma
    pessoa está chegando (ou já chegou) nos 45/90 dias de empresa."""
    try:
        data_fmt = datetime.strptime(data_inicio_str, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        data_fmt = data_inicio_str
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">
              📌 {marco_dias} dias de casa se aproximando
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              <b style="color:#2db8cf;">{nome}</b> está completando <b>{marco_dias} dias</b> de empresa e
              precisa de um feedback.
            </p>
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 20px 0;">
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Cargo: <b>{cargo}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0;">Data de início: <b>{data_fmt}</b></p>
            </div>
            <p style="font-size:13px; color:#8b98a5; line-height:1.6; margin:0;">
              Esse aviso é automático, gerado pelo PDA - Painel de Automações.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0 0 14px 0;">Desenvolvido por</p>
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_igor" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #2db8cf;" alt="Igor Leal">
                    <div style="font-size:11px; color:#2db8cf; font-weight:700; line-height:1.4;">Igor Leal</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Analista Sênior</div>
                  </td>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_debora" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #b0cb1c;" alt="Debora Sampaio">
                    <div style="font-size:11px; color:#b0cb1c; font-weight:700; line-height:1.4;">Debora Sampaio</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Especialista</div>
                  </td>
                </tr>
              </table>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _executar_alertas_tempo_de_empresa() -> None:
    """Roda 1x por dia - pra cada usuário ATIVO com data_inicio preenchida,
    confere se está a até DIAS_ANTECEDENCIA_ALERTA_TEMPO_EMPRESA dias de
    completar 45 ou 90 dias de empresa. Manda pros 4 destinatários fixos,
    UMA vez só por (usuário, marco) - controlado por
    alertas_tempo_empresa_enviados.json."""
    hoje = date.today()
    ja_enviados = _carregar_alertas_tempo_empresa_enviados()
    enviados_agora = set()

    for usuario, info in USUARIOS_WEB.items():
        if info.get("ativo") is False:
            continue
        data_inicio_str = info.get("data_inicio")
        if not data_inicio_str:
            continue
        try:
            data_inicio = datetime.strptime(data_inicio_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue
        dias_na_empresa = (hoje - data_inicio).days
        if dias_na_empresa < 0:
            continue

        for marco in MARCOS_TEMPO_EMPRESA:
            chave = f"{usuario}|{marco}"
            if chave in ja_enviados:
                continue
            dias_restantes = marco - dias_na_empresa
            if not (0 <= dias_restantes <= DIAS_ANTECEDENCIA_ALERTA_TEMPO_EMPRESA):
                continue

            nome = info.get("nome") or usuario
            cargo = _cargo_mais_recente(usuario)
            corpo_html = _montar_email_tempo_empresa_html(nome, cargo, data_inicio_str, marco)
            try:
                smtp_info = _config_email_boas_vindas()
                for destinatario in DESTINATARIOS_ALERTA_TEMPO_EMPRESA:
                    _enviar_email_com_fotos(
                        destinatario=destinatario,
                        assunto=f"{nome} está completando {marco} dias de empresa",
                        corpo_html=corpo_html,
                        smtp_info=smtp_info,
                    )
                logger.info(
                    "Alerta de %d dias de empresa enviado pra '%s' (%s destinatário(s)).",
                    marco, usuario, len(DESTINATARIOS_ALERTA_TEMPO_EMPRESA),
                )
                enviados_agora.add(chave)
            except Exception:
                logger.exception(
                    "Falha ao enviar alerta de %d dias de empresa pra '%s' - tenta de novo amanhã.",
                    marco, usuario,
                )
                # NÃO marca como enviado - assim tenta de novo no próximo
                # dia (ainda dentro da janela de antecedência)

    if enviados_agora:
        _salvar_alertas_tempo_empresa_enviados(ja_enviados | enviados_agora)


def _montar_email_feedback_inserido_html(autor_nome: str, tipo: str, data_str: str, descricao_alvo: str, texto: str, nota: Optional[int],
                                        varios_autores: bool = False, equipe: str = "") -> str:
    """Aviso pros destinatários fixos sempre que um Feedback ou
    Alinhamento é inserido - resumo (quem deu, quando, quem recebeu) MAIS
    o texto completo do registro (pedido do Igor em 14/09/2026 - antes
    não trazia o texto de propósito, mudou pra trazer).

    `descricao_alvo` já vem pronta de quem chama - "Fulano" (individual),
    "Fulano, Ciclano e Beltrano" (grupo) ou "toda a equipe" (geral) -
    essa função não sabe/não precisa saber o escopo, só exibe o texto."""
    verbo = "um Alinhamento" if tipo == "Alinhamento" else "um Feedback"
    acao = "inseriram" if varios_autores else "inseriu"  # 2.34.7.0: pode ter mais de um autor
    bloco_equipe = f'<p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Equipe: <b>{html_utils.escape(equipe)}</b></p>' if equipe else ""
    texto_seguro = html_utils.escape(texto or "")
    bloco_nota = f'<p style="font-size:14px; color:#e6edf3; margin:8px 0 0 0;">Nota: <b>{"★" * nota}{"☆" * (5 - nota)}</b></p>' if nota else ""
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">
              📝 Novo {tipo.lower()} registrado
            </p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              <b style="color:#2db8cf;">{autor_nome}</b> {acao} {verbo} sobre
              <b style="color:#b0cb1c;">{descricao_alvo}</b>.
            </p>
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 20px 0;">
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Tipo: <b>{tipo}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">Data: <b>{data_str}</b></p>
              <p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">De: <b>{autor_nome}</b></p>
              {bloco_equipe}
              <p style="font-size:14px; color:#e6edf3; margin:0;">Para: <b>{descricao_alvo}</b></p>
              {bloco_nota}
            </div>
            <p style="font-size:11px; color:#8b98a5; text-transform:uppercase; letter-spacing:.04em; margin:0 0 8px 0;">Conteúdo</p>
            <div style="background:rgba(0,0,0,.2); border:1px solid rgba(255,255,255,.08); border-radius:9px; padding:16px 18px; margin:0 0 20px 0;">
              <p style="font-size:13.5px; color:#e6edf3; line-height:1.7; margin:0; white-space:pre-wrap;">{texto_seguro}</p>
            </div>
            <p style="font-size:13px; color:#8b98a5; line-height:1.6; margin:0;">
              Esse é um aviso automático do PDA - Painel de Automações. Mais detalhes (edição, remoção,
              histórico completo) na tela de Feedbacks e Alinhamentos.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0 0 14px 0;">Desenvolvido por</p>
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_igor" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #2db8cf;" alt="Igor Leal">
                    <div style="font-size:11px; color:#2db8cf; font-weight:700; line-height:1.4;">Igor Leal</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Analista Sênior</div>
                  </td>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_debora" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #b0cb1c;" alt="Debora Sampaio">
                    <div style="font-size:11px; color:#b0cb1c; font-weight:700; line-height:1.4;">Debora Sampaio</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Especialista</div>
                  </td>
                </tr>
              </table>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _notificar_feedback_inserido(autor_nome: str, tipo: str, criado_em: str, descricao_alvo: str, texto: str, nota: Optional[int],
                                 destinatarios: Optional[list] = None, varios_autores: bool = False, equipe: str = "") -> None:
    """Dispara em background o aviso pros destinatários fixos - NUNCA deve
    derrubar o cadastro do feedback em si (por isso o try/except aqui
    dentro, chamado pela rota logo depois de já ter salvo com sucesso)."""
    try:
        corpo_html = _montar_email_feedback_inserido_html(autor_nome, tipo, criado_em, descricao_alvo, texto, nota, varios_autores, equipe)
        smtp_info = _config_email_boas_vindas()
        # 2.34.7.0: lista da equipe escolhida no registro; sem lista, a de sempre (Monitoramento)
        for destinatario in (destinatarios or DESTINATARIOS_ALERTA_FEEDBACK):
            _enviar_email_com_fotos(
                destinatario=destinatario,
                assunto=f"Novo {tipo.lower()} registrado - {descricao_alvo}",
                corpo_html=corpo_html,
                smtp_info=smtp_info,
            )
    except Exception:
        logger.exception(
            "Falha ao notificar %s inserido sobre '%s' - o registro em si já foi salvo normalmente.",
            tipo, descricao_alvo,
        )


# ---------------------------------------------------------------------------
# Insígnia PDA Beta User conquistada (2.35.5.0): avisa os responsáveis das equipes
# do Feedbacks (a lista chega já sem repetição, ver areas/perfil/insignias.py).
# ---------------------------------------------------------------------------
def _montar_email_insignia_beta_html(nome: str, email: str, data_inicio: str, aniversario: str, cargo: str) -> str:
    try:
        data_fmt = datetime.strptime(data_inicio, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        data_fmt = data_inicio or "-"
    esc = html_utils.escape
    linhas = "".join(
        f'<p style="font-size:14px; color:#e6edf3; margin:0 0 6px 0;">{rotulo}: <b>{esc(valor or "-")}</b></p>'
        for rotulo, valor in (("Cargo", cargo), ("Na empresa desde", data_fmt), ("Aniversário", aniversario), ("E-mail", email))
    )
    return f"""<!DOCTYPE html>
<html lang="pt-br">
<head><meta charset="utf-8"></head>
<body style="margin:0; padding:0; background:#0b0f14; font-family:'Segoe UI', Arial, sans-serif;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#0b0f14; padding:32px 16px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:520px; background:#181f27; border-radius:16px; overflow:hidden; border:1px solid rgba(255,255,255,.09);">
        <tr>
          <td style="background:linear-gradient(135deg, #2db8cf, #b0cb1c); padding:36px 32px; text-align:center;">
            <div style="font-size:26px; font-weight:800; color:#08090c; letter-spacing:.02em;">PDA</div>
            <div style="font-size:13px; color:#08090c; opacity:.85; margin-top:2px;">Painel de Automações</div>
          </td>
        </tr>
        <tr>
          <td style="padding:36px 32px 8px 32px;">
            <p style="font-size:20px; color:#e6edf3; margin:0 0 18px 0; font-weight:700;">&#127942; Nova insígnia PDA Beta User</p>
            <p style="font-size:14.5px; color:#c7d0d9; line-height:1.7; margin:0 0 20px 0;">
              <b style="color:#2db8cf;">{esc(nome)}</b> participou da campanha, completou o perfil no PDA e ganhou a insígnia
              <b>PDA Beta User</b>.
            </p>
            <div style="background:rgba(45,184,207,.06); border:1px solid rgba(45,184,207,.25); border-radius:9px; padding:16px 18px; margin:0 0 20px 0;">
              {linhas}
            </div>
            <p style="font-size:13px; color:#8b98a5; line-height:1.6; margin:0;">
              Esse aviso é automático, gerado pelo PDA - Painel de Automações.
            </p>
          </td>
        </tr>
        <tr>
          <td style="padding:0 32px 32px 32px;">
            <div style="border-top:1px solid rgba(255,255,255,.09); padding-top:20px; text-align:center;">
              <p style="font-size:11px; color:#8b98a5; margin:0 0 14px 0;">Desenvolvido por</p>
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
                <tr>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_igor" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #2db8cf;" alt="Igor Leal">
                    <div style="font-size:11px; color:#2db8cf; font-weight:700; line-height:1.4;">Igor Leal</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Analista Sênior</div>
                  </td>
                  <td style="padding:0 14px; text-align:center;">
                    <img src="cid:foto_debora" width="48" height="48" style="width:48px; height:48px; border-radius:50%; object-fit:cover; display:block; margin:0 auto 6px auto; border:2px solid #b0cb1c;" alt="Debora Sampaio">
                    <div style="font-size:11px; color:#b0cb1c; font-weight:700; line-height:1.4;">Debora Sampaio</div>
                    <div style="font-size:9.5px; color:#8b98a5; line-height:1.4;">Especialista</div>
                  </td>
                </tr>
              </table>
            </div>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def notificar_insignia_beta(nome: str, email: str, data_inicio: str, aniversario: str, destinatarios: list, login: str = "") -> int:
    """Manda o aviso pra cada destinatário (uma vez cada). Devolve quantos saíram.
    Falha de envio de um não impede os outros e nunca derruba quem chamou."""
    cargo = _cargo_mais_recente(login) if login else ""
    corpo_html = _montar_email_insignia_beta_html(nome, email, data_inicio, aniversario, cargo)
    smtp_info = _config_email_boas_vindas()
    enviados, vistos = 0, set()
    for destinatario in destinatarios:
        chave = (destinatario or "").strip().lower()
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        try:
            _enviar_email_com_fotos(destinatario=destinatario, assunto=f"{nome} ganhou a insígnia PDA Beta User",
                                    corpo_html=corpo_html, smtp_info=smtp_info)
            enviados += 1
        except Exception:
            logger.exception("Falha ao avisar %s sobre a insígnia PDA Beta User de '%s'.", destinatario, nome)
    logger.info("Insígnia PDA Beta User de '%s': aviso enviado pra %d pessoa(s).", nome, enviados)
    return enviados
