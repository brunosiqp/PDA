"""Pedaços compartilhados por várias telas: CSS base (paleta, tema claro/escuro), navbar, rodapé, ícones do campo de senha e a página de acesso negado.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


# CSS/JS compartilhados entre hub, usuários e alertas (navbar + variáveis de
# cor + o pequeno "toast" usado pelo card de Relatórios).
_NAVBAR_CSS = """
  </style>
  <script>
    /* Aplica o tema salvo ANTES de desenhar a página (sem piscar). O escuro é SEMPRE
       o padrão: só vira claro se a pessoa escolheu claro no botão (lua/sol) da navbar.
       Não segue o tema do sistema operacional, de propósito. */
    (function () {
      try { if (localStorage.getItem('pda-tema') === 'claro') document.documentElement.setAttribute('data-tema', 'claro'); } catch (e) {}
    })();
  </script>
  <style>
  @import url('https://fonts.googleapis.com/css2?family=Raleway:wght@400;500;600;700;800&display=swap');
  /* largura padrão das telas de ferramenta (2.32.6.1): todas usam essa medida, pra o
     conteúdo não "pular" de tamanho ao trocar de card. Telas de leitura (Sobre,
     Changelog, Perfil) ficam mais estreitas de propósito. */
  :root { --largura-pagina: 1120px; }
  :root {
    --bg: #0b0f14; --bg-panel: rgba(24,31,39,.66); --bg-panel-solid: #181f27;
    --fg: #e6edf3; --fg-dim: #8b98a5;
    --teal: #2db8cf; --lime: #b0cb1c; --grayblue: #97a2a8; --lightgray: #d4dee0;
    --accent: #2db8cf; --border: rgba(var(--tinta),.09); --border-forte: rgba(var(--tinta),.18);
    --ok: #4ec9b0; --erro: #f14c4c; --run: #dcdcaa; --wait: #808080;
    --gradiente-marca: linear-gradient(135deg, var(--teal), var(--lime));
    /* superfícies translúcidas: rgba(var(--tinta), .03) etc. Escuro = véu branco
       (igual ao de sempre); claro = véu azul-acinzentado. --poco é o fundo "afundado"
       dos campos (preto translúcido no escuro, branco no claro). */
    --tinta: 255,255,255; --poco: 0,0,0;
    --navbar-bg: rgba(14,18,23,.72); --toast-bg: rgba(24,31,39,.96);
    color-scheme: dark;
  }
  /* Modo claro (opcional, pelo botão da navbar). Cores de marca escurecidas pra
     manter contraste de texto sobre fundo branco; gradiente um pouco mais fechado
     pelo mesmo motivo (ele também vira texto nos títulos). */
  :root[data-tema="claro"] {
    --bg: #eef2f6; --bg-panel: rgba(255,255,255,.82); --bg-panel-solid: #ffffff;
    --fg: #16202b; --fg-dim: #566677;
    --teal: #0e8aa1; --lime: #6b8500; --grayblue: #5f6b73; --lightgray: #2c3740;
    --accent: #0e8aa1; --border: rgba(16,32,48,.12); --border-forte: rgba(16,32,48,.22);
    --ok: #13876e; --erro: #d33a3a; --run: #967a09; --wait: #6b7280;
    --gradiente-marca: linear-gradient(135deg, #169fb8, #86a30c);
    --tinta: 16,32,48; --poco: 255,255,255;
    --navbar-bg: rgba(255,255,255,.8); --toast-bg: rgba(255,255,255,.97);
    color-scheme: light;
  }
  /* troca de tema suave (só durante a troca, pra não deixar a página toda "lenta") */
  html.tema-trocando, html.tema-trocando *, html.tema-trocando *::before, html.tema-trocando *::after {
    transition: background-color .3s ease, color .3s ease, border-color .3s ease, fill .3s ease, stroke .3s ease !important;
  }
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body {
    background: var(--bg); color: var(--fg);
    font-family: 'Raleway', 'Segoe UI', -apple-system, BlinkMacSystemFont, Arial, sans-serif;
    margin: 0; min-height: 100vh; position: relative;
    display: flex; flex-direction: column;
  }
  /* Visual dos <select> em todo o site - fundo sólido (não translúcido) pra
     combinar com a lista de opções nativa do navegador, que também respeita
     o tema escuro graças ao color-scheme acima. Sem isso, o navegador abria
     o dropdown com fundo branco padrão do sistema, destoando do resto. */
  select {
    background-color: var(--bg-panel-solid); color: var(--fg);
    border: 1px solid var(--border); border-radius: 8px;
    padding: 8px 32px 8px 12px; font-size: 13px; font-family: inherit;
    appearance: none; -webkit-appearance: none; -moz-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%238b98a5' stroke-width='1.6' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");
    background-repeat: no-repeat; background-position: right 12px center;
    cursor: pointer; transition: border-color .15s, box-shadow .15s;
  }
  select:hover { border-color: var(--border-forte); }
  select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  select option { background-color: var(--bg-panel-solid); color: var(--fg); }
  body::before {
    content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background:
      radial-gradient(ellipse 800px 550px at 10% -10%, rgba(45,184,207,.15), transparent 60%),
      radial-gradient(ellipse 650px 550px at 105% 8%, rgba(176,203,28,.10), transparent 60%),
      radial-gradient(ellipse 900px 650px at 50% 120%, rgba(45,184,207,.08), transparent 60%);
  }
  a { color: inherit; }
  [hidden] { display: none !important; }  /* 3.1.0.0: estilos como "button { display: inline-block }" anulavam o hidden */
  .navbar { display: flex; justify-content: space-between; align-items: center;
            padding: 13px 28px; border-bottom: 1px solid var(--border);
            background: var(--navbar-bg); backdrop-filter: blur(14px) saturate(140%);
            -webkit-backdrop-filter: blur(14px) saturate(140%);
            position: sticky; top: 0; z-index: 40; }
  .navbar .marca { display: flex; align-items: center; gap: 12px; }
  .navbar .marca img { height: 30px; width: 30px; display: block; }
  .navbar h1 { font-size: 17px; margin: 0; font-weight: 700;
               background: var(--gradiente-marca); -webkit-background-clip: text;
               background-clip: text; color: transparent; }
  .navbar h1 a { text-decoration: none; }
  .navbar .sub { color: var(--fg-dim); font-size: 11px; margin-top: 1px; }
  .navbar .acoes { display: flex; gap: 10px; align-items: center; }
  .navbar .usuario-info { font-size: 12px; color: var(--fg-dim); text-align: right; }
  .navbar .usuario-info b { color: var(--fg); }
  /* celular (2.35.7.0): o nome e o selo ao lado da foto empurravam o "Sair" pra fora da tela;
     ficam só a foto e a setinha (o nome continua no menu da foto) */
  @media (max-width: 600px) {
    .navbar { padding: 10px 14px; }
    .navbar .acoes { gap: 6px; }
    .navbar .usuario-info { display: none; }
    .navbar .acoes .btn-link { padding: 8px 12px; }
  }

  .usuario-area-navbar { position: relative; }

  /* sininho de notificações (3.0.1.0): palminhas, comentários e versão nova */
  .area-sino { position: relative; }
  .botao-sino { position: relative; width: 38px; height: 38px; padding: 0; display: flex; align-items: center; justify-content: center; border-radius: 10px; }
  .botao-sino svg { width: 18px; height: 18px; }
  .botao-sino.tocando svg { animation: tocar-sino 1s ease 2; transform-origin: 50% 10%; }
  @keyframes tocar-sino { 0%, 100% { transform: rotate(0); } 20% { transform: rotate(16deg); } 40% { transform: rotate(-14deg); } 60% { transform: rotate(8deg); } 80% { transform: rotate(-5deg); } }
  .contador-sino { position: absolute; top: -5px; right: -5px; min-width: 18px; height: 18px; border-radius: 99px; padding: 0 5px;
                   background: #f14c4c; color: #fff; font-size: 10.5px; font-weight: 800; display: none; align-items: center; justify-content: center;
                   box-shadow: 0 0 0 2px var(--bg); box-sizing: border-box; }
  .contador-sino.visivel { display: flex; }
  .painel-sino { display: none; position: absolute; top: calc(100% + 8px); right: 0; width: 360px; max-width: calc(100vw - 24px);
                 background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
                 box-shadow: 0 18px 40px rgba(0,0,0,.45); z-index: 90; overflow: hidden; }
  .painel-sino.aberto { display: block; }
  .cab-sino { display: flex; align-items: center; justify-content: space-between; padding: 12px 14px; border-bottom: 1px solid var(--border);
              font-size: 13.5px; font-weight: 800; color: var(--fg); }
  .lista-sino { max-height: 420px; overflow-y: auto; }
  .item-sino { display: flex; gap: 10px; padding: 11px 14px; border-bottom: 1px solid var(--border); text-decoration: none; color: var(--fg);
               font-size: 12.8px; line-height: 1.45; transition: background .15s; }
  .item-sino:hover { background: rgba(var(--tinta), .05); }
  .item-sino.nao-lida { background: rgba(45,184,207,.07); }
  .item-sino .av-sino { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; flex-shrink: 0; display: flex; align-items: center;
                        justify-content: center; font-weight: 800; font-size: 12px; color: #fff; background: #2db8cf; position: relative; }
  .item-sino .av-sino.versao { background: var(--gradiente-marca); color: #0b0f14; }
  .item-sino .icone-tipo-sino { position: absolute; right: -4px; bottom: -3px; font-size: 12px; }
  .item-sino .quando-sino { font-size: 11px; color: var(--fg-dim); margin-top: 2px; }
  .item-sino .btn-sino { display: inline-block; margin-top: 6px; font-size: 11.5px; font-weight: 800; color: #071016; background: var(--teal);
                         border-radius: 8px; padding: 4px 10px; }
  .vazio-sino { padding: 26px 16px; text-align: center; color: var(--fg-dim); font-size: 12.5px; }
  .botao-usuario-navbar { display: flex; align-items: center; gap: 9px; background: transparent; border: none;
                            cursor: pointer; padding: 5px 8px 5px 5px; border-radius: 10px;
                            transition: background .15s ease; font-family: inherit; }
  .botao-usuario-navbar:hover { background: rgba(var(--tinta),.05); }
  .avatar-navbar { width: 32px; height: 32px; border-radius: 50%; object-fit: cover; flex-shrink: 0;
                     border: 1px solid var(--border-forte); }
  .avatar-navbar-generico { background: rgba(var(--tinta),.07); display: flex; align-items: center;
                              justify-content: center; color: var(--fg-dim); }
  .avatar-navbar-generico svg { width: 18px; height: 18px; }
  .seta-menu-navbar { width: 13px; height: 13px; color: var(--fg-dim); flex-shrink: 0;
                        transition: transform .15s ease; }
  .seta-menu-navbar.girada { transform: rotate(180deg); }
  .dropdown-usuario-navbar { display: none; position: absolute; top: calc(100% + 8px); right: 0; min-width: 190px;
                               background: var(--bg-panel-solid); border: 1px solid var(--border-forte);
                               border-radius: 10px; padding: 8px; box-shadow: 0 14px 32px rgba(0,0,0,.45); z-index: 80; }
  .dropdown-usuario-navbar.aberto { display: block; }
  .cargo-dropdown-navbar { font-size: 11.5px; color: var(--fg-dim); padding: 5px 9px 11px 9px;
                             border-bottom: 1px solid var(--border); margin-bottom: 6px; }
  .link-ver-perfil-navbar { display: block; padding: 7px 9px; border-radius: 7px; color: var(--fg);
                              text-decoration: none; font-size: 12.5px; font-weight: 600;
                              transition: background .15s ease, color .15s ease; }
  .link-ver-perfil-navbar:hover { background: rgba(45,184,207,.1); color: var(--teal); }
  .badge { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 10px;
           font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .badge-admin { background: rgba(45,184,207,.15); color: var(--teal); border: 1px solid rgba(45,184,207,.35); }
  .badge-view { background: rgba(139,152,165,.15); color: var(--fg-dim); border: 1px solid var(--border); }
  button, .btn-link { background: rgba(var(--tinta),.06); color: var(--fg); border: 1px solid var(--border);
           padding: 9px 16px; border-radius: 8px; cursor: pointer; font-size: 13px;
           text-decoration: none; display: inline-block; transition: all .15s ease; }
  button:hover, .btn-link:hover { background: rgba(var(--tinta),.11); border-color: var(--border-forte); }
  .btn-accent { background: var(--gradiente-marca); color: #0b0f14; font-weight: 700; border: none; }
  .btn-accent:hover { background: var(--gradiente-marca); filter: brightness(1.1); box-shadow: 0 6px 20px rgba(45,184,207,.25); }
  .conteudo { padding: 30px 28px; max-width: var(--largura-pagina); margin: 0 auto; flex: 1 0 auto; width: 100%; }
  .rodape { margin-top: 44px; padding: 20px 28px; border-top: 1px solid var(--border);
            display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px;
            color: var(--fg-dim); font-size: 11px; }
  .rodape .marca-rodape { display: flex; align-items: center; gap: 8px; }
  .rodape .marca-rodape img { height: 15px; width: 15px; opacity: .75; }
  /* versão + link do changelog: cor da marca bem viva pra ficar claro que dá pra clicar */
  .rodape .direita-rodape { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
  .link-changelog-rodape { display: inline-flex; align-items: center; gap: 8px; text-decoration: none;
                            font-size: 11.5px; font-weight: 700; color: var(--lime); padding: 5px 12px 5px 5px;
                            border-radius: 999px; border: 1px solid transparent;
                            background-image: linear-gradient(var(--bg-panel), var(--bg-panel)), var(--gradiente-marca);
                            background-origin: border-box; background-clip: padding-box, border-box;
                            transition: box-shadow .2s ease, transform .15s ease; }
  .link-changelog-rodape:hover { box-shadow: 0 0 16px rgba(176,203,28,.35); transform: translateY(-1px); }
  /* "Sobre o PDA": mesmo formato do botão do changelog, só que discreto (turquesa, sem preenchimento) */
  .link-sobre-rodape { display: inline-flex; align-items: center; text-decoration: none; font-size: 11.5px;
                        font-weight: 700; color: var(--teal); padding: 5px 12px; border-radius: 999px;
                        border: 1px solid rgba(45,184,207,.45); transition: box-shadow .2s ease, transform .15s ease; }
  .link-sobre-rodape:hover { box-shadow: 0 0 14px rgba(45,184,207,.35); transform: translateY(-1px); }
  .link-changelog-rodape .versao-rodape { background: var(--gradiente-marca); color: #0b0f14; padding: 2px 8px;
                                           border-radius: 999px; font-size: 10.5px; }
  .toast { position: fixed; bottom: 26px; left: 50%; transform: translateX(-50%) translateY(20px);
           background: var(--toast-bg); backdrop-filter: blur(10px); border: 1px solid var(--border-forte); color: var(--fg);
           padding: 13px 22px; border-radius: 10px; font-size: 13px; box-shadow: 0 14px 34px rgba(0,0,0,.5);
           opacity: 0; pointer-events: none; transition: opacity .25s ease, transform .25s ease; z-index: 50; }
  .toast.mostrar { opacity: 1; transform: translateX(-50%) translateY(0); }

  /* campo de senha com botao de mostrar/ocultar ("olhinho") */
  .campo-senha { position: relative; }
  .campo-senha input { width: 100%; padding-right: 38px; }
  .alternar-senha { position: absolute; right: 4px; top: 50%; transform: translateY(-50%);
                     background: none; border: none; padding: 5px; margin: 0; cursor: pointer;
                     display: flex; align-items: center; justify-content: center; border-radius: 6px; }
  .alternar-senha:hover { background: rgba(var(--tinta),.08); }
  .alternar-senha svg { width: 16px; height: 16px; stroke: var(--fg-dim); pointer-events: none; }

  .btn-perigo { background: rgba(241,76,76,.12); color: #ff8080; border: 1px solid rgba(241,76,76,.3); }

  /* botão de tema (lua/sol) - mesmo desenho do da Central de Monitores */
  .botao-tema { width: 36px; height: 36px; padding: 0; border-radius: 10px; border: 1px solid var(--border);
                 background: rgba(var(--tinta),.05); display: grid; place-items: center; cursor: pointer;
                 color: var(--fg-dim); transition: transform .15s ease, border-color .15s ease, color .15s ease; }
  .botao-tema:hover { border-color: var(--teal); color: var(--teal); background: rgba(var(--tinta),.08); }
  .botao-tema:active { transform: scale(.92); }
  .botao-tema svg { width: 18px; height: 18px; }
  .botao-tema .lua { display: none; }
  :root[data-tema="claro"] .botao-tema .sol { display: none; }
  :root[data-tema="claro"] .botao-tema .lua { display: block; }

  /* ajustes pontuais do modo claro: textos claros que só funcionavam no fundo escuro */
  :root[data-tema="claro"] .btn-perigo { color: var(--erro); }
  :root[data-tema="claro"] .btn-accent, :root[data-tema="claro"] .link-changelog-rodape .versao-rodape { color: #06121a; }
  :root[data-tema="claro"] .pilula-ausencia-ht.feriado { color: var(--erro); }
  :root[data-tema="claro"] .tarja-ausencias-ht .titulo-tarja-ht { color: #0f7fa8; }
  :root[data-tema="claro"] .aviso-beta-dc b { color: #b0297a; }
  :root[data-tema="claro"] .uf-tile.normal { color: #0b5a48; }
  :root[data-tema="claro"] .uf-tile.agendada { color: #5c4d00; }
  :root[data-tema="claro"] body::before { opacity: .7; }
  /* hub no claro: sombra leve pra dar profundidade no fundo branco, e ícones um pouco
     mais escuros (as cores de card foram escolhidas pro fundo escuro; as claras, como o
     amarelo do ClienteA/Dash, sumiam no branco) */
  :root[data-tema="claro"] .card-hub { box-shadow: 0 1px 2px rgba(16,32,48,.05), 0 6px 18px rgba(16,32,48,.06); }
  :root[data-tema="claro"] .card-hub:hover { box-shadow: 0 16px 34px rgba(16,32,48,.12), 0 0 22px -12px var(--accent-card, var(--teal)); }
  :root[data-tema="claro"] .card-hub .icone svg { filter: brightness(.7) saturate(1.3); }
  :root[data-tema="claro"] .cabecalho-conting h1, :root[data-tema="claro"] .mini-painel h3 { color: var(--erro); }
  :root[data-tema="claro"] .uf-tile.desconhecido { background: rgba(16,32,48,.07); color: var(--fg-dim); }
  /* etiquetas do changelog: mesma cor da categoria, escurecida pra ler no branco */
  :root[data-tema="claro"] .tag-categoria { color: color-mix(in srgb, var(--cor-cat) 58%, #000); }
  .btn-perigo:hover { background: rgba(241,76,76,.2); border-color: #f14c4c; }

  /* mensagens de sucesso/erro em paginas de formulario (login, alterar senha) */
  .msg-sucesso { color: var(--ok); font-size: 12px; text-align: center; margin-top: 14px; }

  /* Monitor grande: amplia a página na mesma proporção (mesma régua do login), pro
     conteúdo não ficar pequeno no meio da tela - sem isso o container de 1120px vira
     44% da largura em 2560px e 29% em 4K. O zoom vai nos BLOCOS (navbar, conteúdo,
     rodapé, caixa dos modais e toast) e não no body: no body o modal (position: fixed;
     inset: 0) deixava uma faixa descoberta e aparecia rolagem vertical. */
  @media (min-width: 2300px) and (min-height: 1100px) {
    .navbar, .conteudo, .rodape, .modal-fundo > *, .toast { zoom: 1.2; }
  }
  @media (min-width: 3200px) and (min-height: 1700px) {
    .navbar, .conteudo, .rodape, .modal-fundo > *, .toast { zoom: 1.6; }
  }
"""


_JS_ALTERNAR_SENHA = """
function alternarSenha(inputId, botao) {
  const input = document.getElementById(inputId);
  const aberto = botao.querySelector('.olho-aberto');
  const fechado = botao.querySelector('.olho-fechado');
  if (input.type === 'password') {
    input.type = 'text';
    aberto.style.display = 'none';
    fechado.style.display = '';
  } else {
    input.type = 'password';
    aberto.style.display = '';
    fechado.style.display = 'none';
  }
}
"""


_NAVBAR_HTML = """
  <div class="navbar">
    <div class="marca">
      <img src="__LOGO__" alt="Empresa">
      <div>
        <h1><a href="/">Painel de Automações</a></h1>
        <div class="sub">__SUBTITULO__</div>
      </div>
    </div>
    __BUSCA_NAVBAR__
    <div class="acoes">
      <button class="botao-tema" type="button" onclick="alternarTemaPda()" title="Alternar modo claro/escuro" aria-label="Alternar modo claro/escuro">
        <svg class="sol" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
        <svg class="lua" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
      </button>
      <div class="area-sino">
        <button class="botao-sino" id="botao-sino" type="button" onclick="alternarSinoPda(event)" title="Notificações" aria-label="Notificações">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>
          <span class="contador-sino" id="contador-sino"></span>
        </button>
        <div class="painel-sino" id="painel-sino">
          <div class="cab-sino"><span>Notificações</span></div>
          <div class="lista-sino" id="lista-sino"><div class="vazio-sino">Carregando...</div></div>
        </div>
      </div>
      <div class="usuario-area-navbar">
        <button class="botao-usuario-navbar" onclick="alternarMenuUsuarioNavbar(event)" type="button">
          __AVATAR_NAVBAR__
          <div class="usuario-info">
            <b>__USUARIO__</b> <span class="badge __BADGE_CLASSE__">__BADGE_TEXTO__</span>
          </div>
          <svg class="seta-menu-navbar" id="seta-menu-navbar" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <div class="dropdown-usuario-navbar" id="dropdown-usuario-navbar">
          <div class="cargo-dropdown-navbar" id="cargo-dropdown-navbar">Carregando...</div>
          <a href="/perfil/__LOGIN__" class="link-ver-perfil-navbar">Ver perfil</a>
        </div>
      </div>
      <a class="btn-link" href="/logout">Sair</a>
    </div>
  </div>
  <script>
    // Botão lua/sol: alterna o tema e guarda a escolha (padrão continua escuro)
    function alternarTemaPda() {
      const raiz = document.documentElement;
      const vaiParaClaro = raiz.getAttribute('data-tema') !== 'claro';
      raiz.classList.add('tema-trocando');
      if (vaiParaClaro) raiz.setAttribute('data-tema', 'claro'); else raiz.removeAttribute('data-tema');
      try { localStorage.setItem('pda-tema', vaiParaClaro ? 'claro' : 'escuro'); } catch (e) {}
      setTimeout(function () { raiz.classList.remove('tema-trocando'); }, 350);
      window.dispatchEvent(new CustomEvent('pda-tema-trocado', { detail: vaiParaClaro ? 'claro' : 'escuro' }));
    }
    // Intercepta TODA chamada fetch() de QUALQUER página - se a sessão
    // expirou (90 min sem atividade) e a API responde 401, redireciona
    // pro login automaticamente, em vez de cada função JS precisar
    // lembrar de tratar isso na mão (o que já vinha esquecendo em vários
    // lugares, mostrando o JSON de erro cru pro usuário em vez de só
    // mandar logar de novo).
    (function () {
      const fetchOriginal = window.fetch;
      window.fetch = async function (...args) {
        const resposta = await fetchOriginal(...args);
        if (resposta.status === 401 && !window.location.pathname.startsWith('/login')) {
          window.location.href = '/login';
        }
        return resposta;
      };
    })();

    // Menu dropdown do usuário na navbar (foto/ícone + nome + cargo +
    // link "Ver perfil") - o cargo só é buscado (via /api/perfil/) na
    // primeira vez que o menu abre, pra não pesar toda página com uma
    // consulta ao Movidesk sem necessidade.
    let _cargoNavbarJaCarregado = false;
    function alternarMenuUsuarioNavbar(ev) {
      ev.stopPropagation();
      const dropdown = document.getElementById('dropdown-usuario-navbar');
      const seta = document.getElementById('seta-menu-navbar');
      const vaiAbrir = !dropdown.classList.contains('aberto');
      dropdown.classList.toggle('aberto', vaiAbrir);
      if (seta) seta.classList.toggle('girada', vaiAbrir);
      if (vaiAbrir) carregarCargoNavbar();
    }
    document.addEventListener('click', function (ev) {
      const area = document.querySelector('.usuario-area-navbar');
      const dropdown = document.getElementById('dropdown-usuario-navbar');
      if (area && dropdown && !area.contains(ev.target)) {
        dropdown.classList.remove('aberto');
        const seta = document.getElementById('seta-menu-navbar');
        if (seta) seta.classList.remove('girada');
      }
    });
    // Sininho (3.0.1.0): busca ao abrir a página e a cada 90 s com a aba visível; abrir o
    // painel marca tudo como lido (inclusive o aviso de versão nova)
    let _notificacoesPda = [];
    function _escSino(t) {
      return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
    }
    function _quandoSino(texto) {
      if (!texto) return '';
      const d = new Date(texto.replace(' ', 'T'));
      const min = Math.round((Date.now() - d) / 60000);
      if (isNaN(min)) return '';
      if (min < 1) return 'agora';
      if (min < 60) return 'há ' + min + ' min';
      if (min < 1440) return 'há ' + Math.round(min / 60) + ' h';
      const dias = Math.round(min / 1440);
      return dias === 1 ? 'ontem' : 'há ' + dias + ' dias';
    }
    function _avatarSino(n) {
      if (n.tipo === 'versao' || n.tipo === 'pda' || n.tipo === 'marco' || n.tipo === 'halloween') return '<span class="av-sino versao">PDA</span>';
      if (!n.de) return '<span class="av-sino versao">🏅</span>';  // aviso do próprio PDA (ex.: insígnia desbloqueada)
      const icone = {palma: '👏', insignia: '🏅', feedback: '📝', rank: '🥇', saida: '🚫', ferias: '🏖️', post: '📢', halloween: '🎃', loja: '🛍️', marco: '🎉'}[n.tipo] || '💬';
      const partes = String(n.de_nome || '?').split(' ').filter(Boolean);
      const iniciais = ((partes[0] || '?')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
      const foto = n.de_foto ? '<img class="av-sino" src="/foto-usuario/' + encodeURIComponent(n.de) + '" alt="">' : _escSino(iniciais);
      return n.de_foto ? '<span style="position:relative;flex-shrink:0">' + foto + '<span class="icone-tipo-sino">' + icone + '</span></span>'
        : '<span class="av-sino">' + foto + '<span class="icone-tipo-sino">' + icone + '</span></span>';
    }
    function _desenharSino() {
      const lista = document.getElementById('lista-sino');
      if (!lista) return;
      lista.innerHTML = _notificacoesPda.length ? _notificacoesPda.map(n =>
        '<a class="item-sino' + (n.lida ? '' : ' nao-lida') + '" href="' + _escSino(n.link || '#') + '">' + _avatarSino(n)
        + '<div><div>' + _escSino(n.texto) + '</div>'
        + (n.tipo === 'versao' ? '<span class="btn-sino">Ver changelog</span>' : '<div class="quando-sino">' + _quandoSino(n.criado_em) + '</div>')
        + '</div></a>').join('') : '<div class="vazio-sino">Nada por aqui ainda. Palminhas e comentários nos seus acontecimentos aparecem aqui.</div>';
    }
    async function carregarSinoPda() {
      try {
        const resp = await fetch('/api/notificacoes');
        if (!resp.ok) return;
        const dados = await resp.json();
        if (!dados.ok) return;
        const antes = _notificacoesPda.filter(n => !n.lida).length;
        _notificacoesPda = dados.itens || [];
        const contador = document.getElementById('contador-sino');
        contador.textContent = dados.nao_lidas > 9 ? '9+' : String(dados.nao_lidas);
        contador.classList.toggle('visivel', dados.nao_lidas > 0);
        if (dados.nao_lidas > antes) {
          const botao = document.getElementById('botao-sino');
          botao.classList.remove('tocando'); void botao.offsetWidth; botao.classList.add('tocando');
        }
        _desenharSino();
      } catch (e) { /* sem rede: tenta de novo na próxima rodada */ }
    }
    function alternarSinoPda(ev) {
      ev.stopPropagation();
      const painel = document.getElementById('painel-sino');
      const vaiAbrir = !painel.classList.contains('aberto');
      painel.classList.toggle('aberto', vaiAbrir);
      if (vaiAbrir && _notificacoesPda.some(n => !n.lida)) {
        document.getElementById('contador-sino').classList.remove('visivel');
        fetch('/api/notificacoes/lidas', {method: 'POST'}).then(() => {
          setTimeout(() => { _notificacoesPda.forEach(n => { n.lida = true; }); _desenharSino(); }, 4000);
        }).catch(() => {});
      }
    }
    document.addEventListener('click', function (ev) {
      const area = document.querySelector('.area-sino');
      const painel = document.getElementById('painel-sino');
      if (area && painel && !area.contains(ev.target)) painel.classList.remove('aberto');
    });
    carregarSinoPda();
    setInterval(function () { if (!document.hidden) carregarSinoPda(); }, 90000);

    async function carregarCargoNavbar() {
      if (_cargoNavbarJaCarregado) return;
      const el = document.getElementById('cargo-dropdown-navbar');
      try {
        const resp = await fetch('/api/perfil/__LOGIN__');
        const dados = await resp.json();
        if (dados.ok) {
          el.innerText = dados.cargo || 'Cargo não definido';
          _cargoNavbarJaCarregado = true;
        } else {
          el.style.display = 'none';
        }
      } catch (e) {
        el.style.display = 'none';
      }
    }
  </script>
"""


_FOOTER_HTML = """
  <div class="rodape">
    <div class="marca-rodape">
      <img src="__LOGO__" alt="Empresa">
      <span>Empresa · PDA</span>
    </div>
    __DIREITA_RODAPE__
  </div>
"""


_SVG_OLHO_ABERTO = (
    '<svg class="olho-aberto" viewBox="0 0 24 24" fill="none" stroke-width="1.8" '
    'stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/>'
    "</svg>"
)


_SVG_OLHO_FECHADO = (
    '<svg class="olho-fechado" style="display:none" viewBox="0 0 24 24" fill="none" '
    'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'
    '<path d="M3 3l18 18"/><path d="M10.6 10.6a3 3 0 0 0 4.24 4.24"/>'
    '<path d="M9.88 4.24A10.94 10.94 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-3.09 4.19'
    'M6.1 6.1C3.2 8 1 12 1 12a18.6 18.6 0 0 0 5.06 5.94A10.94 10.94 0 0 0 12 20c1.06 0 2.07-.17 3-.47"/>'
    "</svg>"
)


_USUARIOS_NEGADO_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Usuários - acesso restrito</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .aviso { max-width: 480px; margin: 60px auto; background: var(--bg-panel); backdrop-filter: blur(12px);
           -webkit-backdrop-filter: blur(12px); border: 1px solid var(--border-forte);
           border-radius: 16px; padding: 34px; text-align: center; }
  .aviso .icone { width: 56px; height: 56px; border-radius: 50%; background: rgba(241,76,76,.14);
                  display: flex; align-items: center; justify-content: center; margin: 0 auto 18px auto;
                  box-shadow: inset 0 0 0 1px rgba(241,76,76,.25); }
  .aviso .icone svg { width: 26px; height: 26px; stroke: var(--erro); }
  .aviso h2 { margin: 0 0 10px 0; font-size: 17px; }
  .aviso p { color: var(--fg-dim); font-size: 13px; line-height: 1.6; margin: 0 0 20px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="aviso">
      <div class="icone">
        <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9"/><path d="M12 8v5"/><path d="M12 16h.01"/>
        </svg>
      </div>
      <h2>Acesso restrito</h2>
      <p>Para acessar esta página é preciso ter permissão de administrador.
         Fale com um administrador do painel se precisar de acesso.</p>
      <a class="btn-link" href="/">Voltar pra Comunidade</a>
    </div>
  </div>
  __FOOTER__
</body>
</html>
"""
