"""Tela de login e de alterar senha.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_LOGIN_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações - Entrar</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body {
    display: flex; flex-direction: column; min-height: 100vh; position: relative; overflow-x: hidden;
    --mx: 20%; --my: 30%;
  }
  body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; transition: background .3s ease;
    background:
      radial-gradient(ellipse 800px 560px at var(--mx) var(--my), rgba(45,184,207,.14), transparent 60%),
      radial-gradient(ellipse 900px 700px at 88% 84%, rgba(176,203,28,.08), transparent 60%);
  }
  body::after {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .5;
    background-image:
      linear-gradient(rgba(var(--tinta),.012) 1px, transparent 1px),
      linear-gradient(90deg, rgba(var(--tinta),.012) 1px, transparent 1px);
    background-size: 42px 42px;
    mask-image: radial-gradient(ellipse 1200px 900px at 50% 45%, black, transparent 75%);
  }

  @keyframes entrada { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: translateY(0); } }
  @keyframes girar { to { transform: rotate(360deg); } }
  @keyframes pulsarPonto { 0%, 100% { box-shadow: 0 0 0 0 rgba(78,201,176,.55); } 70% { box-shadow: 0 0 0 6px rgba(78,201,176,0); } }
  @keyframes brilhoTagline { 0%, 100% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } }

  /* align-content: center (com flex-wrap) centraliza a linha dos dois cards na tela
     em vez de esticá-la até a altura da janela - em monitor alto sobrava metade do
     painel vazio. Os cards continuam com a MESMA altura entre si (align-items: stretch
     vale dentro da linha, que tem a altura do conteúdo mais alto). */
  .centro { flex: 1; display: flex; align-items: stretch; align-content: center; justify-content: center; gap: 64px;
             padding: 56px 64px; flex-wrap: wrap; position: relative; z-index: 1; }

  .anim-entrada { opacity: 0; animation: entrada .65s cubic-bezier(.16,1,.3,1) forwards; }

  .coluna-login { display: flex; flex-direction: column; gap: 22px; width: 380px; flex-shrink: 0; }
  .fantasma-tagline { visibility: hidden; font-style: italic; font-size: 21px; font-weight: 600;
                       margin: 0; padding: 0 12px; line-height: normal; }

  .anim-entrada { opacity: 0; animation: entrada .65s cubic-bezier(.16,1,.3,1) forwards; }

  .cartao-login {
    background: var(--bg-panel); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 22px; padding: 44px 38px; width: 100%; flex: 1; min-height: 0; position: relative;
    box-shadow: 0 28px 70px rgba(0,0,0,.6), inset 0 1px 0 rgba(var(--tinta),.05);
    border: 1px solid transparent;
    background-image: linear-gradient(var(--bg-panel), var(--bg-panel)),
                       linear-gradient(140deg, rgba(45,184,207,.5), rgba(var(--tinta),.06) 40%, rgba(176,203,28,.35));
    background-origin: border-box; background-clip: padding-box, border-box;
    animation-delay: .05s;
    display: flex; flex-direction: column;
  }
  .corpo-login { flex: 1; display: flex; flex-direction: column; justify-content: center; min-height: 0; }
  .rodape-login { flex-shrink: 0; }
  /* versão atual no rodapé do login, pra todo mundo ver que o PDA está sendo atualizado */
  .versao-login { display: flex; align-items: center; justify-content: center; gap: 8px;
                   font-size: 11px; color: var(--fg-dim); margin-bottom: 14px; }
  .chip-versao { font-weight: 700; font-size: 10.5px; color: var(--fg); padding: 3px 9px; border-radius: 999px;
                  border: 1px solid transparent;
                  background-image: linear-gradient(var(--bg-panel), var(--bg-panel)), var(--gradiente-marca);
                  background-origin: border-box; background-clip: padding-box, border-box; }
  .divisor-rodape-login { height: 1px; margin: 28px 0 18px 0;
                           background: linear-gradient(90deg, transparent, var(--border-forte), transparent); }
  .cartao-login::before {
    content: ""; position: absolute; top: 0; left: 10%; right: 10%; height: 2px; border-radius: 2px;
    background: var(--gradiente-marca); filter: blur(.5px);
    box-shadow: 0 0 16px 1px rgba(45,184,207,.5);
  }
  .cartao-login .logo-login { display: flex; justify-content: center; margin-bottom: 22px; position: relative; }
  .cartao-login .logo-login::before {
    content: ""; position: absolute; width: 90px; height: 90px; border-radius: 50%;
    background: radial-gradient(circle, rgba(45,184,207,.35), transparent 70%); filter: blur(6px);
  }
  .cartao-login .logo-login img { height: 60px; width: 60px; position: relative;
                                    filter: drop-shadow(0 8px 22px rgba(45,184,207,.4)); }
  .cartao-login h1 {
    background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent;
    font-size: 22px; margin: 0 0 6px 0; text-align: center; font-weight: 800; letter-spacing: -.01em;
  }
  .badge-status-login { display: flex; align-items: center; justify-content: center; gap: 6px;
                         color: var(--fg-dim); font-size: 11.5px; text-align: center; margin-bottom: 28px; }
  .ponto-online { width: 6px; height: 6px; border-radius: 50%; background: var(--ok);
                   animation: pulsarPonto 2s infinite; flex-shrink: 0; }

  label { display: block; font-size: 10.5px; color: var(--fg-dim); margin: 16px 0 6px 0;
          text-transform: uppercase; letter-spacing: .06em; font-weight: 600; }
  .campo-com-icone { position: relative; }
  .campo-com-icone svg.icone-campo { position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
                                       width: 15px; height: 15px; color: var(--fg-dim); pointer-events: none;
                                       transition: color .15s ease; z-index: 1; }
  .campo-com-icone:focus-within svg.icone-campo { color: var(--teal); }
  input {
    width: 100%; padding: 11px 13px 11px 36px; border-radius: 9px; border: 1px solid var(--border);
    background: rgba(var(--poco),.3); color: var(--fg); font-size: 14px; font-family: inherit;
    transition: border-color .18s ease, box-shadow .18s ease, background .18s ease;
    position: relative;
  }
  input:focus {
    outline: none; border-color: var(--teal); background: rgba(var(--poco),.4);
    box-shadow: 0 0 0 3px rgba(45,184,207,.16), 0 0 18px -4px rgba(45,184,207,.5);
  }
  .campo-senha { position: relative; }
  .campo-senha input { padding-left: 36px; padding-right: 40px; }
  .campo-senha .alternar-senha { position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
                                   background: none; border: none; padding: 4px; cursor: pointer;
                                   color: var(--fg-dim); display: flex; transition: color .15s ease; }
  .campo-senha .alternar-senha:hover { color: var(--teal); }
  .campo-senha .alternar-senha svg { width: 16px; height: 16px; }

  button.entrar {
    width: 100%; margin-top: 26px; padding: 12px; border-radius: 9px; font-size: 14.5px;
    font-family: inherit; font-weight: 700; letter-spacing: .01em; position: relative; overflow: hidden;
    box-shadow: 0 8px 24px rgba(45,184,207,.25); transition: transform .15s ease, box-shadow .15s ease;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  button.entrar:hover { transform: translateY(-1px); box-shadow: 0 12px 32px rgba(45,184,207,.4); }
  button.entrar:active { transform: translateY(0) scale(.98); }
  button.entrar .spinner-entrar {
    display: none; width: 15px; height: 15px; border-radius: 50%;
    border: 2px solid rgba(11,15,20,.35); border-top-color: #0b0f14; animation: girar .7s linear infinite;
  }
  button.entrar.carregando .texto-entrar { opacity: .001; }
  button.entrar.carregando .spinner-entrar { display: block; position: absolute; }

  .erro { color: var(--erro); font-size: 12px; text-align: center; margin-top: 14px; }
  .erro-desativado { background: rgba(241,76,76,.1); border: 1px solid rgba(241,76,76,.3);
                      border-radius: 10px; padding: 12px 14px; font-size: 12px; line-height: 1.6;
                      text-align: left; }
  .erro-desativado strong { color: var(--fg); }
  .msg-sucesso { color: var(--ok); font-size: 12px; text-align: center; margin-top: 14px; }

  .link-alterar-senha { display: inline-block; text-align: center; margin-top: 0; font-size: 11.5px;
                         color: var(--fg-dim); text-decoration: none; position: relative; width: 100%; }
  .link-alterar-senha::after {
    content: ""; position: absolute; left: 50%; bottom: -2px; width: 0; height: 1px;
    background: var(--teal); transition: width .25s ease, left .25s ease;
  }
  .link-alterar-senha:hover { color: var(--teal); }
  .link-alterar-senha:hover::after { width: 100px; left: calc(50% - 50px); }

  .coluna-showcase { flex: 1 1 600px; max-width: 1200px; display: flex; flex-direction: column; gap: 22px; }
  .tagline-showcase {
    font-style: italic; font-size: 21px; text-align: center; font-weight: 600; margin: 0; padding: 0 12px;
    letter-spacing: .01em; background: linear-gradient(100deg, var(--fg) 30%, var(--teal) 45%, var(--lime) 55%, var(--fg) 70%);
    background-size: 250% auto; -webkit-background-clip: text; background-clip: text; color: transparent;
  }
  .tagline-showcase.anim-entrada {
    /* combina a entrada em cascata com o brilho continuo numa unica
       declaracao de animation - se ficassem em regras separadas com a
       mesma especificidade, a que vem depois no CSS apaga a outra
       (as duas mexem na mesma propriedade "animation"), travando o
       elemento em opacity:0 pra sempre. */
    animation: entrada .65s cubic-bezier(.16,1,.3,1) .12s forwards,
               brilhoTagline 7s ease-in-out .8s infinite;
  }

  .painel-showcase {
    background: var(--bg-panel); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-radius: 22px; position: relative; overflow: hidden; padding: 48px 56px;
    box-shadow: 0 28px 70px rgba(0,0,0,.45), inset 0 1px 0 rgba(var(--tinta),.04);
    border: 1px solid transparent;
    background-image: linear-gradient(var(--bg-panel), var(--bg-panel)),
                       linear-gradient(160deg, rgba(var(--tinta),.09), rgba(var(--tinta),.02) 30%, rgba(45,184,207,.18));
    background-origin: border-box; background-clip: padding-box, border-box;
    animation-delay: .16s;
    flex: 1; min-height: 0; display: flex; flex-direction: column; justify-content: center;
  }
  .painel-showcase::after {
    content: ""; position: absolute; top: -120px; right: -120px; width: 340px; height: 340px;
    border-radius: 50%; background: radial-gradient(circle, rgba(45,184,207,.13), transparent 70%);
    pointer-events: none;
  }
  .texto-showcase { position: relative; z-index: 1; }
  .texto-showcase p { color: var(--fg); font-size: 14.5px; line-height: 1.9; margin: 0 0 16px 0; }
  .texto-showcase p:last-of-type { margin-bottom: 0; }

  /* números e áreas: mesmo conteúdo da página Sobre (AREAS_PDA / _numeros_sobre), em versão compacta */
  .numeros-showcase { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 28px 0 16px 0;
                       position: relative; z-index: 1; }
  .numero-showcase { background: rgba(var(--tinta),.03); border: 1px solid var(--border); border-radius: 14px;
                      padding: 14px 10px; text-align: center; transform-style: preserve-3d; will-change: transform;
                      transition: transform .12s ease, border-color .25s ease; }
  .numero-showcase:hover { border-color: var(--teal); }
  .numero-showcase .valor { font-size: 24px; font-weight: 700; line-height: 1.1; background: var(--gradiente-marca);
                             -webkit-background-clip: text; background-clip: text; color: transparent; }
  .numero-showcase .rotulo { font-size: 9.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em;
                              margin-top: 5px; line-height: 1.35; }
  .areas-showcase { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin: 0 0 28px 0;
                     position: relative; z-index: 1; }
  .area-showcase { background: rgba(var(--tinta),.03); border: 1px solid var(--border); border-top: 2px solid var(--cor-area);
                    border-radius: 14px; padding: 14px 16px; transform-style: preserve-3d; will-change: transform;
                    transition: transform .12s ease, background .25s ease, box-shadow .25s ease; }
  .area-showcase:hover { background: rgba(var(--tinta),.055);
                          box-shadow: 0 12px 28px -10px color-mix(in srgb, var(--cor-area) 45%, transparent); }
  .area-showcase h4 { margin: 0 0 8px 0; font-size: 12.5px; color: var(--fg); font-weight: 700;
                       display: flex; align-items: center; gap: 8px; }
  .area-showcase h4::before { content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--cor-area); flex-shrink: 0; }
  .area-showcase ul { margin: 0; padding-left: 16px; font-size: 12px; line-height: 1.65; color: var(--fg); opacity: .88; }
  .area-showcase li::marker { color: var(--cor-area); }

  .label-desenvolvido-por { text-align: center; font-size: 10.5px; color: var(--fg-dim);
                             text-transform: uppercase; letter-spacing: .08em; margin-bottom: 15px;
                             position: relative; z-index: 1; }
  .equipe-showcase { display: flex; gap: 16px; flex-wrap: wrap; justify-content: center; position: relative; z-index: 1; }
  .cartao-autor-showcase {
    display: flex; align-items: center; gap: 13px; background: rgba(var(--tinta),.03);
    border-radius: 14px; padding: 15px 20px 15px 16px; flex: 1; min-width: 260px; position: relative;
    border: 1px solid var(--border-forte); overflow: hidden;
    transition: transform .12s ease, background .2s ease, box-shadow .2s ease;
    transform-style: preserve-3d; will-change: transform;
  }
  .cartao-autor-showcase::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--gradiente-marca);
  }
  .cartao-autor-showcase:hover { background: rgba(var(--tinta),.06); box-shadow: 0 14px 30px -10px rgba(0,0,0,.5); }
  .avatar-autor-showcase { width: 44px; height: 44px; border-radius: 50%; object-fit: cover;
                            border: 2px solid var(--border-forte); flex-shrink: 0; }
  .cartao-autor-showcase .nome-autor-showcase { font-size: 13.5px; font-weight: 700; color: var(--fg); }
  .cartao-autor-showcase .cargo-autor-showcase { font-size: 10.5px; color: var(--fg-dim); line-height: 1.5; margin-top: 3px; }

  @media (max-width: 1000px) {
    .centro { justify-content: center; }
    .coluna-showcase { max-width: 620px; }
  }
  @media (max-width: 640px) {
    .painel-showcase { padding: 34px 26px; }
    .numeros-showcase { grid-template-columns: repeat(2, 1fr); }
    .areas-showcase { grid-template-columns: 1fr; }
  }
  /* Monitor grande: amplia a tela de login INTEIRA na mesma proporção (cartão, painel,
     textos, espaços), em vez de só a fonte - assim a composição fica igual em qualquer
     monitor. Base = 1920px; 2560px fica 20% maior, 4K 60% maior. */
  @media (min-width: 2300px) and (min-height: 1100px) { .centro { zoom: 1.2; } }
  @media (min-width: 3200px) and (min-height: 1700px) { .centro { zoom: 1.6; } }

  /* tela baixa (ex.: notebook 1366x768): aperta os respiros pra caber sem rolar */
  @media (max-height: 860px) and (min-width: 1001px) {
    .centro { padding-top: 24px; padding-bottom: 24px; }
    .painel-showcase { padding: 30px 40px; }
    .cartao-login { padding: 30px 32px; }
    .numeros-showcase { margin: 18px 0 12px 0; }
    .areas-showcase { margin-bottom: 18px; }
    .texto-showcase p { line-height: 1.7; }
  }
  @media (prefers-reduced-motion: reduce) {
    .anim-entrada { animation: none; opacity: 1; }
    .tagline-showcase { animation: none; }
    .ponto-online { animation: none; }
  }
</style>
</head>
<body>
  <div class="centro">
    <div class="coluna-login">
      __TAGLINE_FANTASMA__
      <form class="cartao-login anim-entrada" method="POST" action="/login" id="form-login" style="animation-delay:.05s">
      <div class="corpo-login">
        <div class="logo-login"><img src="__LOGO__" alt="Empresa"></div>
        <h1>Painel de Automações</h1>
        <div class="badge-status-login"><span class="ponto-online"></span>PDA Empresa · acesso restrito</div>
        <label>Usuário</label>
        <div class="campo-com-icone">
          <svg class="icone-campo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
          </svg>
          <input type="text" name="usuario" autofocus required autocomplete="username">
        </div>
        <label>Senha</label>
        <div class="campo-com-icone">
          <svg class="icone-campo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          __CAMPO_SENHA__
        </div>
        <button class="btn-accent entrar" type="submit">
          <span class="texto-entrar">Entrar</span>
          <span class="spinner-entrar"></span>
        </button>
        __ERRO__
        __SUCESSO__
      </div>
      <div class="rodape-login">
        <div class="divisor-rodape-login"></div>
        __VERSAO_LOGIN__
        <a class="link-alterar-senha" href="/alterar-senha">Alterar minha senha</a>
      </div>
      </form>
    </div>

    <div class="coluna-showcase">
      __TAGLINE_SHOWCASE__

      <div class="painel-showcase anim-entrada" style="animation-delay:.16s">
      <div class="texto-showcase">
        <p>
          O PDA reúne em um só lugar as automações, o monitoramento, os
          indicadores e as ferramentas do dia a dia das equipes de Suporte e
          Monitoramento da Empresa, com login próprio, permissões por pessoa
          e credenciais cifradas.
        </p>
      </div>

      __NUMEROS_SHOWCASE__
      __AREAS_SHOWCASE__

      <div class="label-desenvolvido-por">Desenvolvido por</div>
      <div class="equipe-showcase">
        <div class="cartao-autor-showcase anim-entrada" style="animation-delay:.42s">
          <img class="avatar-autor-showcase" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCABAAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDRooor3z4AKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA/9k=" alt="Igor Leal">
          <div>
            <div class="nome-autor-showcase">Igor Leal</div>
            <div class="cargo-autor-showcase">Responsável pela Aplicação PDA · Frontend, Backend e QA</div>
          </div>
        </div>
        <div class="cartao-autor-showcase anim-entrada" style="animation-delay:.46s">
          <img class="avatar-autor-showcase" src="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCABAAEADASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwDRooor3z4AKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooA/9k=" alt="Debora Sampaio">
          <div>
            <div class="nome-autor-showcase">Debora Sampaio</div>
            <div class="cargo-autor-showcase">Supervisão do projeto · Banco de Monitoramento &amp; Movidesk · UI/UX do PDA</div>
          </div>
        </div>
      </div>
    </div>
    </div>
  </div>

  __FOOTER__
<script>__JS_ALTERNAR_SENHA__</script>
<script>
(function () {
  // glow de fundo que segue o mouse suavemente (throttle via rAF)
  let ultimoX = 20, ultimoY = 30, pendente = false;
  document.addEventListener('mousemove', function (e) {
    ultimoX = (e.clientX / window.innerWidth) * 100;
    ultimoY = (e.clientY / window.innerHeight) * 100;
    if (!pendente) {
      pendente = true;
      requestAnimationFrame(function () {
        document.body.style.setProperty('--mx', ultimoX + '%');
        document.body.style.setProperty('--my', ultimoY + '%');
        pendente = false;
      });
    }
  });

  // tilt 3D leve nos cards de feature e nos cards de autor
  function aplicarTilt(seletor, intensidade) {
    document.querySelectorAll(seletor).forEach(function (card) {
      card.addEventListener('mousemove', function (e) {
        const r = card.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        card.style.transform = 'perspective(600px) rotateY(' + (px * intensidade) + 'deg) rotateX(' + (-py * intensidade) + 'deg) translateY(-2px)';
      });
      card.addEventListener('mouseleave', function () {
        card.style.transform = '';
      });
    });
  }
  aplicarTilt('.numero-showcase', 8);
  aplicarTilt('.area-showcase', 4);
  aplicarTilt('.cartao-autor-showcase', 4);

  // spinner no botao ao enviar o formulario (o proprio submit continua normal)
  const form = document.getElementById('form-login');
  if (form) {
    form.addEventListener('submit', function () {
      const btn = form.querySelector('button.entrar');
      if (btn) btn.classList.add('carregando');
    });
  }
})();
</script>
</body>
</html>
"""


_ALTERAR_SENHA_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações - Alterar senha</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body { display: flex; flex-direction: column; min-height: 100vh; }
  .centro { flex: 1; display: flex; align-items: center; justify-content: center; padding: 24px; }
  .cartao-login {
    background: var(--bg-panel); backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid var(--border-forte); border-radius: 20px;
    padding: 42px 36px; width: 360px;
    box-shadow: 0 24px 64px rgba(0,0,0,.55);
  }
  .cartao-login .logo-login { display: flex; justify-content: center; margin-bottom: 20px; }
  .cartao-login .logo-login img { height: 50px; width: 50px; filter: drop-shadow(0 6px 20px rgba(45,184,207,.35)); }
  .cartao-login h1 {
    background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent;
    font-size: 19px; margin: 0 0 4px 0; text-align: center; font-weight: 700;
  }
  .cartao-login .sub { color: var(--fg-dim); font-size: 12px; text-align: center; margin-bottom: 22px; line-height: 1.5; }
  label { display: block; font-size: 10.5px; color: var(--fg-dim); margin: 15px 0 5px 0;
          text-transform: uppercase; letter-spacing: .05em; }
  input {
    width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border);
    background: rgba(var(--poco),.28); color: var(--fg); font-size: 14px;
    transition: border-color .15s ease, box-shadow .15s ease;
  }
  input:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  input.campo-fixo { opacity: .75; cursor: default; }
  button.entrar { width: 100%; margin-top: 24px; padding: 11px; border-radius: 8px; font-size: 14px; }
  .erro { color: var(--erro); font-size: 12px; text-align: center; margin-top: 14px; }
  .link-alterar-senha { display: block; text-align: center; margin-top: 18px; font-size: 11.5px;
                         color: var(--fg-dim); text-decoration: none; }
  .link-alterar-senha:hover { color: var(--teal); }
</style>
</head>
<body>
  <div class="centro">
    <form class="cartao-login" method="POST" action="/alterar-senha">
      <div class="logo-login"><img src="__LOGO__" alt="Empresa"></div>
      <h1>Alterar senha</h1>
      <div class="sub">__SUB_ALTERAR_SENHA__</div>
      <label>Usuário</label>
      __CAMPO_USUARIO_ALTERAR__
      __BLOCO_SENHA_ATUAL__
      <label>Nova senha</label>
      __CAMPO_NOVA_SENHA__
      <label>Confirmar nova senha</label>
      __CAMPO_CONFIRMA_SENHA__
      <button class="btn-accent entrar" type="submit">Salvar nova senha</button>
      __ERRO__
      __LINK_VOLTAR_ALTERAR__
    </form>
  </div>
  __FOOTER__
<script>__JS_ALTERNAR_SENHA__</script>
</body>
</html>
"""
