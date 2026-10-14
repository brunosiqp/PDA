"""Tela Sobre.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_SOBRE_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Sobre o PDA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-sobre { text-align: center; max-width: 720px; margin: 10px auto 30px auto; }
  .cabecalho-sobre h1 { font-size: 26px; margin: 0 0 8px 0;
                         background: var(--gradiente-marca); -webkit-background-clip: text;
                         background-clip: text; color: transparent; }
  .cabecalho-sobre .sub { color: var(--fg-dim); font-size: 13.5px; line-height: 1.6; }

  .painel-sobre { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                  border: 1px solid var(--border); border-radius: 14px; padding: 26px 30px;
                  max-width: 720px; margin: 0 auto 20px auto; }
  .painel-sobre h2 { margin: 0 0 12px 0; font-size: 13px; color: var(--teal); text-transform: uppercase;
                      letter-spacing: .06em; }
  .painel-sobre p { color: var(--fg); font-size: 13.5px; line-height: 1.75; margin: 0 0 12px 0; }
  .painel-sobre p:last-child { margin-bottom: 0; }
  .painel-sobre ul { margin: 0; padding-left: 20px; color: var(--fg); font-size: 13.5px; line-height: 1.9; }

  .cartao-autor { display: flex; align-items: center; gap: 16px; flex: 1; min-width: 280px;
                  background: var(--bg-panel); border: 1px solid var(--border-forte); border-radius: 14px;
                  padding: 22px 26px; }
  .grade-autores { display: flex; flex-wrap: wrap; gap: 16px; max-width: 720px; margin: 0 auto 20px auto; }
  .avatar-autor { width: 54px; height: 54px; border-radius: 50%; flex-shrink: 0;
                   object-fit: cover; border: 2px solid var(--border-forte); }
  .info-autor .nome-autor { font-size: 15px; font-weight: 700; color: var(--fg); margin-bottom: 2px; }
  .info-autor .cargo-autor { font-size: 12px; color: var(--fg-dim); }

  .criacao-sobre { display: block; font-size: 12.5px; color: var(--fg-dim); margin-bottom: 10px; }
  .grade-numeros { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 14px;
                    max-width: 720px; margin: 0 auto 20px auto; }
  .cartao-numero { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px;
                    padding: 16px 18px; text-align: center; }
  .cartao-numero .valor { font-size: 24px; font-weight: 700; color: var(--teal); }
  .cartao-numero .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                            letter-spacing: .04em; margin-top: 4px; }

  .versao-sobre { margin-top: 14px; }
  .titulo-areas { max-width: 720px; margin: 0 auto 12px auto; font-size: 13px; color: var(--teal);
                   text-transform: uppercase; letter-spacing: .06em; font-weight: 700; }
  .grade-areas { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px;
                  max-width: 720px; margin: 0 auto 14px auto; }
  .area-sobre { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; padding: 18px 22px;
                 border-top: 2px solid var(--cor-area); }
  .area-sobre h3 { margin: 0 0 10px 0; font-size: 14px; color: var(--fg); display: flex; align-items: center; gap: 8px; }
  .area-sobre h3::before { content: ""; width: 8px; height: 8px; border-radius: 50%; background: var(--cor-area); }
  .area-sobre ul { margin: 0; padding-left: 18px; color: var(--fg); font-size: 13px; line-height: 1.75; }
  .area-sobre li::marker { color: var(--cor-area); }
  .em-construcao-sobre { max-width: 720px; margin: 0 auto 24px auto; font-size: 12px; color: var(--fg-dim); text-align: center; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-sobre">
      <h1>PDA · Painel de Automações</h1>
      <div class="sub">Central de automações, monitoramento, indicadores e ferramentas internas das equipes de Suporte e Monitoramento da Empresa.</div>
      <div class="versao-sobre">
        <span class="criacao-sobre">No ar desde __DATA_CRIACAO__ · __DIAS_PDA__ dias</span>
        <a class="link-changelog-rodape" href="/changelog" title="Ver o que mudou em cada versão"><span class="versao-rodape">v__VERSAO_SOBRE__</span><span>Ver changelog →</span></a>
      </div>
    </div>

    <div class="grade-numeros">
      <div class="cartao-numero"><div class="valor">__N_ALERTAS__</div><div class="rotulo">Alertas automáticos</div></div>
      <div class="cartao-numero"><div class="valor">__N_CLIENTES_MONITORES__</div><div class="rotulo">Clientes na Central de Monitores</div></div>
      <div class="cartao-numero"><div class="valor">__N_PRODUTOS_DF__</div><div class="rotulo">Produtos no Dash Financeiro</div></div>
      <div class="cartao-numero"><div class="valor">__N_CARDS__</div><div class="rotulo">Ferramentas no painel</div></div>
      <div class="cartao-numero"><div class="valor">__N_ACESSOS__</div><div class="rotulo">Acessos ao PDA</div></div>
    </div>

    <div class="painel-sobre">
      <h2>O que é o PDA</h2>
      <p>
        O PDA é uma aplicação web interna que centraliza, executa e monitora
        as automações das equipes de Suporte e Monitoramento. Roda num
        servidor da rede da Empresa e é acessado pelo navegador, com login
        próprio e permissões definidas por pessoa.
      </p>
      <p>
        Por trás, integra os bancos SQL Server dos clientes e do
        monitoramento, o Movidesk, o Microsoft 365 (SharePoint e e-mail), o
        Microsoft Teams e o Power BI. As credenciais ficam cifradas, cada
        automação tem o próprio log e tudo o que muda fica registrado no
        changelog.
      </p>
    </div>

    <div class="titulo-areas">O que o painel cobre hoje</div>
    <div class="grade-areas">
      __AREAS_SOBRE__
    </div>
    __EM_CONSTRUCAO_SOBRE__

    <div class="grade-autores">
      <div class="cartao-autor">
        <img class="avatar-autor" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCABAAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDRooor3z4AKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA/9k=" alt="Igor Leal">
        <div class="info-autor">
          <div class="nome-autor">Igor Leal</div>
          <div class="cargo-autor">Responsável pela Aplicação PDA · Frontend, Backend e QA</div>
        </div>
      </div>
      <div class="cartao-autor">
        <img class="avatar-autor" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCABAAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDRooor3z4AKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA/9k=" alt="Debora Sampaio">
        <div class="info-autor">
          <div class="nome-autor">Debora Sampaio</div>
          <div class="cargo-autor">Supervisão do projeto · Banco de Monitoramento &amp; Movidesk · UI/UX do PDA</div>
        </div>
      </div>
    </div>
  </div>

  __FOOTER__
</body>
</html>
"""
