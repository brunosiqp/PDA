"""Tema de Halloween (3.3.7.0): cores, títulos com fonte de terror, enfeites e a Caça aos Doces.

Não fica em nenhum template: o `_enviar_html` (alertas_gui) põe `_HALLOWEEN_HTML` antes do </body> de toda tela só
de 24/10 a 01/11 (areas/loja/halloween.py) ou na prévia de administrador, junto com a configuração em JSON
(`<script type="application/json" id="pda-halloween">`: doces, achados, prévia). Fora disso nada disso chega às telas.
"""
from telas.loja_wallpapers import _ARTE_HALLOWEEN_HTML, _CSS_WALLPAPER_IW

_CSS_HALLOWEEN = r"""<style>
  @import url('https://fonts.googleapis.com/css2?family=Creepster&display=swap');
  /* 1. cores: só as variáveis que o PDA já usa em todas as telas */
  :root[data-sazonal="halloween"] {
    --bg: #0c0812; --bg-panel: rgba(30,19,42,.72); --bg-panel-solid: #1a1124;
    --fg: #f3e9ff; --fg-dim: #a893bd; --teal: #ff7a1a; --lime: #9b5de5; --accent: #ff7a1a;
    --border: rgba(255,140,40,.13); --border-forte: rgba(255,140,40,.28);
    --gradiente-marca: linear-gradient(135deg, #ff7a1a, #9b5de5); --navbar-bg: rgba(20,11,29,.8); --toast-bg: rgba(26,17,36,.97);
  }
  :root[data-sazonal="halloween"][data-tema="claro"] {
    --bg: #f4eefb; --bg-panel: rgba(255,255,255,.86); --bg-panel-solid: #ffffff; --fg: #24132f; --fg-dim: #6c5a7c;
    --teal: #d9580a; --lime: #7a3fc7; --accent: #d9580a; --border: rgba(122,63,199,.16); --border-forte: rgba(122,63,199,.3);
    --gradiente-marca: linear-gradient(135deg, #e8661a, #7a3fc7); --navbar-bg: rgba(255,255,255,.85);
  }
  :root[data-sazonal="halloween"] body { background: radial-gradient(ellipse at 50% -10%, rgba(255,122,26,.16), transparent 50%),
      radial-gradient(circle at 0% 100%, rgba(155,93,229,.18), transparent 45%), var(--bg) fixed; }
  :root[data-sazonal="halloween"][data-tema="claro"] body { background: radial-gradient(ellipse at 50% -10%, rgba(255,122,26,.14), transparent 50%), radial-gradient(circle at 0% 100%, rgba(155,93,229,.14), transparent 45%), var(--bg) fixed; }
  /* 2. títulos com fonte de terror (só os h1 das páginas; navbar e textos continuam Raleway) */
  :root[data-sazonal="halloween"] .conteudo h1, :root[data-sazonal="halloween"] .topo-secao h1 { font-family: 'Creepster', 'Raleway', sans-serif !important; font-weight: 400 !important; letter-spacing: .045em !important; }
  :root[data-sazonal="halloween"] .topo-secao h1 { font-size: 34px; color: #ff7a1a; text-shadow: 0 0 18px rgba(255,122,26,.35); }
  :root[data-sazonal="halloween"] .topo-secao h1 .link-nome-hero { color: #c8a6ff; }
  :root[data-sazonal="halloween"][data-tema="claro"] .topo-secao h1 { color: #d9580a; text-shadow: none; }
  :root[data-sazonal="halloween"] .item-menu.ativo { background: linear-gradient(90deg, rgba(255,122,26,.2), rgba(255,122,26,.04)); }
  :root[data-sazonal="halloween"] .cartao-eu::before { background: linear-gradient(120deg, rgba(255,122,26,.45), rgba(155,93,229,.42)) !important; }
  :root[data-sazonal="halloween"] .ind .barra span { background: repeating-linear-gradient(-45deg, #ff7a1a 0 8px, #ffb347 8px 16px) !important; }
  :root[data-sazonal="halloween"] .indicadores-mural > .ind:nth-child(1) { --cor-ind: #ff7a1a !important; }
  :root[data-sazonal="halloween"] .indicadores-mural > .ind:nth-child(2) { --cor-ind: #b47cff !important; }
  :root[data-sazonal="halloween"] .indicadores-mural > .ind:nth-child(3) { --cor-ind: #7cfc00 !important; }
  :root[data-sazonal="halloween"] .indicadores-mural > .ind:nth-child(4) { --cor-ind: #ff4d6d !important; }
  /* Central de Monitores: página pública com paleta própria */
  :root[data-sazonal="halloween"]:not([data-theme="light"]) { --bg-0: #0c0812; --bg-1: #120b1a; --bg-2: #1a1124; --surface: rgba(30,19,42,.6); --surface-strong: rgba(30,19,42,.82);
    --text-0: #f3e9ff; --text-1: #d9c7f0; --text-2: #a893bd; --glow: rgba(255,122,26,.2); --shadow: rgba(0,0,0,.5); }
  :root[data-sazonal="halloween"] { --turquoise: #ff7a1a; --turquoise-strong: #e8661a; }
  :root[data-sazonal="halloween"] h1.title { font-family: 'Creepster', 'Sora', sans-serif !important; font-weight: 400 !important; letter-spacing: .045em; color: #ff7a1a; }
  :root[data-sazonal="halloween"] .bloco-campanha { background: linear-gradient(135deg, rgba(255,122,26,.2), rgba(155,93,229,.2)); border-color: rgba(255,122,26,.45); }
  :root[data-sazonal="halloween"] .bloco-campanha button { background: linear-gradient(90deg, #ff7a1a, #ff9a3d); color: #1a0d05; }
  :root[data-sazonal="halloween"] .evento.destacado { box-shadow: 0 0 0 2px #ff7a1a, 0 0 30px -6px rgba(255,122,26,.6); }
  /* 3. cards: cor em rodízio, brilho de baixo, borda de cima acesa e enfeite no canto */
  :root[data-sazonal="halloween"] .grade-hub > .card-hub:nth-child(5n+1) { --accent-card: #ff7a1a !important; }
  :root[data-sazonal="halloween"] .grade-hub > .card-hub:nth-child(5n+2) { --accent-card: #b47cff !important; }
  :root[data-sazonal="halloween"] .grade-hub > .card-hub:nth-child(5n+3) { --accent-card: #7cfc00 !important; }
  :root[data-sazonal="halloween"] .grade-hub > .card-hub:nth-child(5n+4) { --accent-card: #ff4d6d !important; }
  :root[data-sazonal="halloween"] .grade-hub > .card-hub:nth-child(5n+5) { --accent-card: #ffd34d !important; }
  :root[data-sazonal="halloween"] .card-hub { background: radial-gradient(120% 70% at 50% 125%, color-mix(in srgb, var(--accent-card) 17%, transparent), transparent 62%), var(--bg-panel);
    border-color: color-mix(in srgb, var(--accent-card) 24%, transparent); box-shadow: inset 0 2px 0 color-mix(in srgb, var(--accent-card) 70%, transparent); overflow: hidden; }
  :root[data-sazonal="halloween"] .card-hub:hover { box-shadow: inset 0 2px 0 var(--accent-card), 0 0 0 1px color-mix(in srgb, var(--accent-card) 45%, transparent), 0 16px 38px color-mix(in srgb, var(--accent-card) 24%, transparent); }
  :root[data-sazonal="halloween"] .card-hub .icone { background: color-mix(in srgb, var(--accent-card) 15%, transparent) !important; box-shadow: 0 0 16px color-mix(in srgb, var(--accent-card) 40%, transparent), inset 0 0 0 1px color-mix(in srgb, var(--accent-card) 35%, transparent); }
  :root[data-sazonal="halloween"]:not([data-decor="desligado"]) .card-hub::after { content: ""; position: absolute; right: 10px; bottom: 10px; width: 40px; height: 40px; pointer-events: none;
    background: var(--enfeite) no-repeat center / contain; opacity: .8; transition: transform .25s, opacity .25s, filter .25s; }
  :root[data-sazonal="halloween"] .card-hub:hover::after { opacity: 1; transform: scale(1.14) rotate(-6deg); filter: drop-shadow(0 0 8px var(--accent-card)); }
  :root[data-sazonal="halloween"] .card-hub.bloqueado { opacity: .78; filter: saturate(.75); }
  :root[data-sazonal="halloween"] .card-hub .tag-em-breve { color: #c8a6ff; background: rgba(155,93,229,.2); border-radius: 99px; padding: 2px 9px 2px 7px; }
  /* 4. enfeites fixos */
  .hw-decor, .hw-decor * { pointer-events: none; }
  .hw-decor { display: none; }
  :root[data-sazonal="halloween"]:not([data-decor="desligado"]) .hw-decor { display: block; }
  :root[data-sazonal="halloween"][data-decor-calma] .hw-mexe { display: none !important; }
  .hw-teia { position: fixed; z-index: 0; width: 190px; height: 190px; opacity: .45; top: 60px; }
  .hw-teia.e { left: 0; } .hw-teia.d { right: 0; transform: scaleX(-1); }
  :root[data-sazonal="halloween"][data-tema="claro"] .hw-teia { opacity: .5; filter: invert(.55) sepia(1) hue-rotate(220deg); }
  .hw-lua { position: fixed; z-index: 0; top: 92px; right: 128px; width: 70px; height: 70px; opacity: .9; filter: drop-shadow(0 0 22px rgba(255,233,168,.55)); }
  .hw-aranha { position: fixed; z-index: 30; top: 58px; left: 74%; width: 2px; animation: hw-desce 7s ease-in-out infinite; }
  .hw-aranha i { display: block; width: 1px; height: 100%; margin: 0 auto; background: rgba(243,233,255,.45); }
  .hw-aranha svg { position: absolute; bottom: -20px; left: -14px; width: 30px; height: 30px; animation: hw-balanca 3s ease-in-out infinite; transform-origin: top center; }
  @keyframes hw-desce { 0%, 100% { height: 30px; } 50% { height: 170px; } }
  @keyframes hw-balanca { 0%, 100% { transform: rotate(-8deg); } 50% { transform: rotate(8deg); } }
  .hw-morcego { position: fixed; z-index: 30; width: 38px; top: 120px; left: -60px; animation: hw-voa 16s linear infinite; }
  .hw-morcego.m2 { top: 230px; width: 26px; animation-duration: 22s; animation-delay: -9s; opacity: .75; }
  .hw-morcego svg { width: 100%; animation: hw-bate .25s ease-in-out infinite alternate; }
  @keyframes hw-voa { 0% { left: -60px; transform: translateY(0); } 25% { transform: translateY(-34px); } 50% { transform: translateY(12px); } 75% { transform: translateY(-22px); } 100% { left: 104%; transform: translateY(0); } }
  @keyframes hw-bate { from { transform: scaleY(1); } to { transform: scaleY(.45); } }
  .navbar .marca { position: relative; }
  .hw-ab-logo { position: absolute; left: 18px; bottom: -6px; width: 22px; z-index: 2; filter: drop-shadow(0 0 6px rgba(255,140,40,.7)); }
  .hw-chao { position: relative; height: 70px; margin-top: 10px; overflow: hidden; }
  .hw-chao .nevoa { position: absolute; inset: auto 0 0 0; height: 70px; background: linear-gradient(0deg, rgba(168,147,189,.16), transparent); }
  .hw-chao svg { position: absolute; bottom: 6px; filter: drop-shadow(0 0 10px rgba(255,140,40,.5)); }
  .hw-chao .a1 { left: 4%; width: 54px; } .hw-chao .a2 { left: calc(4% + 48px); width: 34px; } .hw-chao .a3 { right: 4%; width: 48px; }
  .hw-chao .lp { right: calc(4% + 62px); width: 36px; filter: none; opacity: .8; bottom: 2px; }
  .chama { animation: hw-tremula 1.6s ease-in-out infinite; }
  @keyframes hw-tremula { 0%, 100% { opacity: 1; } 40% { opacity: .75; } 60% { opacity: .95; } 80% { opacity: .7; } }
  :root[data-sazonal="halloween"]:not([data-decor="desligado"]) .cartao-eu { overflow: visible; padding-top: 34px; }
  .hw-chapeu { position: absolute; top: -44px; left: 50%; width: 84px; transform: translateX(-50%) rotate(-7deg); transform-origin: 50% 82%; z-index: 3;
    filter: drop-shadow(0 0 8px rgba(155,93,229,.75)) drop-shadow(0 4px 5px rgba(0,0,0,.55)); animation: hw-chapeu 4s ease-in-out infinite; }
  @keyframes hw-chapeu { 0%, 100% { transform: translateX(-50%) rotate(-7deg); } 50% { transform: translateX(-50%) rotate(-3deg); } }
  .hw-fantasma { position: absolute; right: 12px; top: 10px; width: 28px; opacity: .85; animation: hw-flutua 3.4s ease-in-out infinite; }
  @keyframes hw-flutua { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
  .bloco-lado { position: relative; }
  /* 5. doces escondidos (aparecem mesmo com a decoração desligada: é o jogo) */
  .hw-doce { position: absolute; z-index: 6; width: 30px; height: 22px; padding: 0; border: 0; background: none; cursor: pointer; display: none; animation: hw-doce 5s ease-in-out infinite; }
  :root[data-sazonal="halloween"] .hw-doce { display: block; }
  .hw-doce svg { width: 100%; height: 100%; filter: drop-shadow(0 2px 3px rgba(0,0,0,.45)); }
  .hw-doce:hover { transform: scale(1.25) rotate(-10deg); animation: none; }
  .hw-doce.achado { animation: hw-pega .6s ease-out forwards; pointer-events: none; }
  @keyframes hw-doce { 0%, 88%, 100% { transform: rotate(0); } 91% { transform: rotate(-14deg); } 94% { transform: rotate(12deg); } 97% { transform: rotate(-6deg); } }
  @keyframes hw-pega { to { transform: translateY(-40px) scale(1.8); opacity: 0; } }
  .hw-toast { position: fixed; left: 50%; bottom: 28px; transform: translateX(-50%); z-index: 99; background: #1a1124; color: #f3e9ff; border: 1px solid rgba(255,122,26,.5);
    border-radius: 14px; padding: 12px 18px; font-weight: 800; font-size: 14px; box-shadow: 0 14px 40px rgba(0,0,0,.5), 0 0 30px -8px #ff7a1a; display: flex; gap: 10px; align-items: center; }
  .hw-toast svg { width: 34px; height: 24px; }
  .hw-progresso { display: flex; gap: 3px; margin: 8px 0 6px; flex-wrap: wrap; }
  .hw-progresso span { width: 22px; height: 16px; display: grid; place-items: center; border-radius: 6px; background: rgba(var(--tinta), .06); border: 1px dashed rgba(var(--tinta), .18); }
  .hw-progresso span svg { width: 20px; height: 14px; }
  .hw-progresso span.ok { border: 1px solid rgba(255,122,26,.5); background: rgba(255,122,26,.12); }
  .hw-progresso span:not(.ok) svg { opacity: .18; filter: grayscale(1); }
  .hw-camp-txt { font-size: 11.5px; color: var(--fg-dim); }
  .camp-wp-mini { width: 54px; height: 54px; border-radius: 12px; flex-shrink: 0; border: 1px solid rgba(255,122,26,.4); }
  .hw-fundo { position: fixed; inset: 0; z-index: 90; background: rgba(5,2,10,.66); display: grid; place-items: center; padding: 16px; }
  .hw-modal { width: 100%; max-width: 460px; background: #1a1124; border: 1px solid rgba(255,122,26,.35); border-radius: 20px; padding: 22px; color: #f3e9ff; position: relative; overflow: hidden; box-sizing: border-box; }
  .hw-modal h3 { margin: 0 0 4px; font-family: 'Creepster', Raleway, sans-serif; font-weight: 400; letter-spacing: .05em; font-size: 28px; color: #ff7a1a; }
  .hw-modal p { margin: 0 0 12px; font-size: 13px; color: #a893bd; }
  .hw-dica { display: flex; gap: 10px; align-items: center; font-size: 13px; padding: 8px 10px; border-radius: 10px; background: rgba(255,255,255,.04); margin-bottom: 6px; }
  .hw-dica svg { width: 26px; height: 18px; flex: none; }
  .hw-dica.falta svg { opacity: .2; filter: grayscale(1); }
  .hw-dica.ok { background: rgba(255,122,26,.1); } .hw-dica.ok b { color: #ffb347; }
  .hw-modal .fechar { position: absolute; right: 14px; top: 12px; background: none; border: 0; color: #a893bd; font-size: 20px; cursor: pointer; }
  .hw-modal .previa-wp { border-radius: 14px; overflow: hidden; border: 1px solid rgba(255,122,26,.35); margin: 8px 0 14px; text-align: left; background: #1a1124; }
  .hw-modal .previa-wp .wp-iw { height: 120px; }
  .hw-botoes { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; }
  .hw-botoes button, .hw-botoes a { font: inherit; font-size: 13px; font-weight: 800; border-radius: 10px; padding: 8px 16px; cursor: pointer; border: 1px solid rgba(255,255,255,.2); background: none; color: #f3e9ff; text-decoration: none; }
  .hw-botoes .pri { border: 0; color: #1a0d05; background: linear-gradient(90deg, #ff7a1a, #ffb347); }
  .hw-faixa { display: flex; align-items: center; justify-content: center; gap: 10px; flex-wrap: wrap; font-size: 12px; font-weight: 700; padding: 6px 16px;
    background: linear-gradient(90deg, rgba(255,122,26,.16), rgba(155,93,229,.16)); border-bottom: 1px solid var(--border); color: var(--fg); position: relative; z-index: 5; }
  .hw-faixa button { font: inherit; font-size: 11.5px; font-weight: 800; border: 1px solid var(--border-forte); background: none; color: var(--fg); border-radius: 99px; padding: 2px 10px; cursor: pointer; }
  .hw-faixa.previa { background: repeating-linear-gradient(-45deg, rgba(255,122,26,.18) 0 12px, rgba(155,93,229,.18) 12px 24px); }
  @media (prefers-reduced-motion: reduce) { .hw-aranha, .hw-aranha svg, .hw-morcego, .hw-morcego svg, .chama, .hw-fantasma, .hw-chapeu, .hw-doce { animation: none !important; } .hw-morcego { display: none !important; } }
""" + _CSS_WALLPAPER_IW + """
</style>
"""

_SCRIPT_HALLOWEEN = r"""<script>
(function () {
  let C = {};
  try { C = JSON.parse(document.getElementById('pda-halloween').textContent); } catch (e) { return; }
  const A = window.HW_ARTE, svg = A.svg, root = document.documentElement;
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  root.dataset.sazonal = 'halloween';
  try { if (localStorage.getItem('pda-hw-decor') === 'desligado') root.dataset.decor = 'desligado'; } catch (e) {}
  if (/\/(logs|manutencao-|indicadores-|dash-financeiro|relatorios-cliente_a|string-connections|config-seguro|longnamejanitor)/.test(location.pathname)) root.dataset.decorCalma = '1';
  const uri = (vb, corpo) => 'url("data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + vb + '">' + corpo + '</svg>') + '")';
  const MORCEGO_CLARO = A.MORCEGO.replace('#14091f', '#5b3478').replace('stroke-width="1"', 'stroke-width="1.4"');
  const ARANHA_FIO = '<line x1="20" y1="0" x2="20" y2="20" stroke="rgba(243,233,255,.6)"/><g transform="translate(0 7)">' + A.ARANHA + '</g>';
  const ENFEITES = [uri('0 0 170 170', A.teia()), uri('0 0 64 56', A.ABOBORA.replace('class="chama" ', '')), uri('0 0 64 32', MORCEGO_CLARO), uri('0 0 40 48', A.VELA), uri('0 0 40 48', ARANHA_FIO), uri('0 0 40 40', A.LUA)];
  const est = document.createElement('style');
  est.textContent = ENFEITES.map((u, i) => ':root[data-sazonal="halloween"] .grade-hub > .card-hub:nth-child(6n+' + (i + 1) + ') { --enfeite: ' + u + '; }').join('\n');
  document.head.appendChild(est);
  const add = (html, onde) => { const t = document.createElement('template'); t.innerHTML = html.trim(); const el = t.content.firstChild; (onde || document.body).appendChild(el); return el; };

  // ---------- enfeites
  add(svg('0 0 170 170', A.teia(), 'hw-decor hw-teia e'));
  add(svg('0 0 170 170', A.teia(), 'hw-decor hw-teia d'));
  add(svg('0 0 40 40', A.LUA, 'hw-decor hw-lua'));
  add('<div class="hw-decor hw-aranha hw-mexe"><i></i>' + svg('0 0 40 40', A.ARANHA) + '</div>');
  if (document.querySelector('.layout-mural')) {
    add('<div class="hw-decor hw-mexe hw-morcego">' + svg('0 0 64 32', A.MORCEGO) + '</div>');
    add('<div class="hw-decor hw-mexe hw-morcego m2">' + svg('0 0 64 32', A.MORCEGO) + '</div>');
  }
  const marca = document.querySelector('.navbar .marca');
  if (marca) add(svg('0 0 64 56', A.ABOBORA, 'hw-decor hw-ab-logo'), marca);
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    const texto = C.previa && !C.ativo
      ? '🎃 Prévia do Halloween: só você vê, e achar doce não conta. O tema liga sozinho de 24/10 a ' + esc(C.fim) + '.'
      : '🦇 O PDA está fantasiado pro Halloween até ' + esc(C.fim) + (C.logado ? ' · ache os ' + C.total + ' doces escondidos 🍬' : '');
    const f = add('<div class="hw-faixa' + (C.previa && !C.ativo ? ' previa' : '') + '"><span>' + texto + '</span>'
      + (C.logado ? '<button type="button" data-dicas>Ver dicas</button>' : '')
      + '<button type="button" data-decor>' + (root.dataset.decor === 'desligado' ? 'Ligar decoração' : 'Desligar decoração pra mim') + '</button>'
      + (C.previa ? '<button type="button" data-sair>Sair da prévia</button>' : '') + '</div>', navbar.parentNode);
    navbar.after(f);
    f.querySelector('[data-decor]').onclick = ev => {
      const desligar = root.dataset.decor !== 'desligado';
      if (desligar) root.dataset.decor = 'desligado'; else delete root.dataset.decor;
      try { localStorage.setItem('pda-hw-decor', desligar ? 'desligado' : ''); } catch (e) {}
      ev.target.textContent = desligar ? 'Ligar decoração' : 'Desligar decoração pra mim';
    };
    const dicas = f.querySelector('[data-dicas]'); if (dicas) dicas.onclick = () => window.abrirDicasDoces();
    const sair = f.querySelector('[data-sair]');
    if (sair) sair.onclick = () => { document.cookie = 'previa_halloween=; path=/; max-age=0'; location.href = location.pathname; };
  }
  if (C.previa) document.cookie = 'previa_halloween=1; path=/; max-age=86400; samesite=lax';
  const rodape = document.querySelector('.rodape, footer');
  if (rodape) rodape.before(add('<div class="hw-decor hw-chao"><div class="nevoa"></div>' + svg('0 0 64 56', A.ABOBORA, 'a1') + svg('0 0 64 56', A.ABOBORA, 'a2')
    + svg('0 0 40 48', A.LAPIDE, 'lp') + svg('0 0 64 56', A.ABOBORA, 'a3') + '</div>'));
  const fotoEu = document.querySelector('.cartao-eu .foto-eu');
  if (fotoEu) add(svg('0 0 100 80', A.CHAPEU, 'hw-decor hw-chapeu hw-mexe'), fotoEu);
  const blocoLado = document.querySelector('.lado-inicio .bloco-lado');
  if (blocoLado) add(svg('0 0 40 48', A.FANTASMA, 'hw-decor hw-fantasma hw-mexe'), blocoLado);

  // ---------- Caça aos Doces
  const DOCES = (C.doces || []).map(d => ({ ...d, re: new RegExp(d.pagina) }));
  let achados = (C.achados || []).slice();
  function toast(html) {
    document.querySelectorAll('.hw-toast').forEach(t => t.remove());
    const t = add('<div class="hw-toast">' + html + '</div>');
    setTimeout(() => t.remove(), 3800);
  }
  async function pegar(d, b) {
    b.classList.add('achado'); setTimeout(() => b.remove(), 700);
    if (!C.ativo) { toast(svg('0 0 48 32', A.DOCE) + '<span>Prévia: esse é o doce ' + esc(d.id) + '. Achar não conta.</span>'); return; }
    try {
      const r = await (await fetch('/api/halloween/doce', { method: 'POST', body: new URLSearchParams({ id: d.id }) })).json();
      if (!r.ok) { toast('<span>' + esc(r.erro || 'Não deu pra guardar o doce.') + '</span>'); return; }
      if (achados.indexOf(d.id) === -1) achados.push(d.id);
      if (r.concluiu && r.novo) abrirComemoracao();
      else toast(svg('0 0 48 32', A.DOCE) + '<span>Você achou um doce! <b style="color:#ffb347">' + r.achados + ' de ' + r.total + '</b></span>');
      atualizarCampanha();
    } catch (e) { toast('<span>Não deu pra guardar o doce agora. Tente de novo.</span>'); }
  }
  function plantarDoces() {
    if (!C.logado) return;
    DOCES.forEach(d => {
      if (!d.re.test(location.pathname) || achados.indexOf(d.id) !== -1 || document.querySelector('[data-doce="' + d.id + '"]')) return;
      let alvo = null;
      try { alvo = document.querySelector(d.seletor); } catch (e) { return; }
      if (!alvo) return;
      if (getComputedStyle(alvo).position === 'static') alvo.style.position = 'relative';
      const b = add('<button type="button" class="hw-doce" data-doce="' + esc(d.id) + '" style="' + esc(d.pos) + '" aria-label="Um doce!">' + svg('0 0 48 32', A.DOCE) + '</button>', alvo);
      b.addEventListener('click', ev => { ev.preventDefault(); ev.stopPropagation(); pegar(d, b); });
    });
  }
  window.abrirDicasDoces = function () {
    const f = add('<div class="hw-fundo"><div class="hw-modal" role="dialog" aria-modal="true" aria-label="Caça aos Doces"><button class="fechar" aria-label="Fechar">×</button><h3>Caça aos Doces</h3>'
      + '<p>Tem ' + C.total + ' doces escondidos pelo PDA, na Comunidade e dentro dos cards. Achou, clicou, é seu. Com todos, o wallpaper exclusivo <b style="color:#ffb347">EmpresaWeen 26</b> é seu, pra capa do perfil e o cartão da Comunidade. Vale até ' + esc(C.fim) + '.</p>'
      + DOCES.map((d, i) => '<div class="hw-dica ' + (achados.indexOf(d.id) !== -1 ? 'ok' : 'falta') + '">' + svg('0 0 48 32', A.DOCE) + '<span>' + (achados.indexOf(d.id) !== -1 ? '<b>Achado!</b> ' : (i + 1) + '. ') + esc(d.dica) + '</span></div>').join('')
      + '</div></div>');
    f.addEventListener('click', ev => { if (ev.target === f || ev.target.classList.contains('fechar')) f.remove(); });
  };
  function abrirComemoracao() {
    const foto = (document.querySelector('.cartao-eu img, .foto-perfil') || {}).src || '';
    const f = add('<div class="hw-fundo"><div class="hw-modal" style="text-align:center" role="dialog" aria-modal="true" aria-label="Achou todos os doces"><button class="fechar" aria-label="Fechar">×</button>'
      + '<h3>Achou os ' + C.total + ' doces!</h3><p>O wallpaper exclusivo <b style="color:#ffb347">EmpresaWeen 26</b> é seu. Ele vai pra capa do seu perfil e pro seu cartão da Comunidade, e fica em Meus itens na Loja pra sempre.</p>'
      + '<div class="previa-wp">' + window.wallpaperEmpresaween('capa') + '</div>'
      + '<div class="hw-botoes"><button type="button" class="pri" data-usar>Usar agora</button><a href="/loja?aba=meus">Ver na Loja</a><button type="button" class="fechar-b">Depois</button></div></div></div>');
    f.addEventListener('click', async ev => {
      if (ev.target.hasAttribute('data-usar')) {
        const r = await (await fetch('/api/loja/usar', { method: 'POST', body: new URLSearchParams({ id: 'iw26' }) })).json();
        if (r.ok) location.reload();
        return;
      }
      if (ev.target === f || ev.target.classList.contains('fechar') || ev.target.classList.contains('fechar-b')) f.remove();
    });
  }
  // bloco "Caça aos Doces" nas campanhas do início (a campanha só vem do servidor no período)
  function htmlCampanhaDoces(c) {
    const n = achados.length;
    return '<div class="bloco-campanha' + (c.concluida ? ' concluida' : '') + '">' + window.wallpaperEmpresaween('mini').replace('class="wp-iw mini"', 'class="wp-iw mini camp-wp-mini"')
      + '<div><b>' + esc(c.nome) + '</b><span>' + esc(c.descricao) + ' <b class="prazo-camp">Até ' + esc(C.fim) + '</b></span>'
      + '<div class="hw-progresso">' + DOCES.map(d => '<span class="' + (achados.indexOf(d.id) !== -1 ? 'ok' : '') + '">' + svg('0 0 48 32', A.DOCE) + '</span>').join('') + '</div>'
      + '<span class="hw-camp-txt">' + n + ' de ' + C.total + ' doces</span> <button onclick="abrirDicasDoces()">Ver dicas</button></div>'
      + (c.concluida ? '<div class="selo-concluida"><div class="check">✓</div><b>Campanha concluída</b><span>Wallpaper EmpresaWeen 26 é seu</span></div>' : '') + '</div>';
  }
  if (typeof window.htmlCampanha === 'function') {
    const original = window.htmlCampanha;
    window.htmlCampanha = function (c) { return c && c.acao === 'doces' ? htmlCampanhaDoces(c) : original(c); };
  }
  function atualizarCampanha() {
    try { if (muralAtual) { (muralAtual.campanhas || []).forEach(c => { if (c.acao === 'doces') c.concluida = achados.length >= C.total; }); desenharCampanhas(muralAtual.campanhas || []); } } catch (e) { /* fora do início */ }
  }
  plantarDoces();
  new MutationObserver(plantarDoces).observe(document.body, { childList: true, subtree: true });
})();
</script>
"""

_HALLOWEEN_HTML = _CSS_HALLOWEEN + _ARTE_HALLOWEEN_HTML + _SCRIPT_HALLOWEEN
