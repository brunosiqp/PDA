"""Wallpapers da Loja de Palminhas (3.3.7.0): desenho de cada wallpaper e onde ele aparece.

`_ARTE_HALLOWEEN_HTML` (a tag script com os desenhos) traz os desenhos do Halloween (abóbora, morcego, lua, doce...), usados pelo wallpaper EmpresaWeen 26
(que vale o ano todo) e pelo tema de Halloween (telas/halloween.py). `_LOJA_WALLPAPERS_HTML` entra no __LOJA_WALLPAPERS__
do início, do perfil e da Loja: CSS + `wallpaperLoja(id, tamanho)`, `aplicarWallpaperCartao(id)` (faixa do cartão na
Comunidade), `aplicarCapaPerfil(dados)` (capa do perfil, com foto à esquerda metade sobre a capa) e
`abrirPersonalizarLoja()` (trocar o wallpaper pelo próprio perfil). Só texto; a regra fica em areas/loja/logica.py.
"""

_ARTE_HALLOWEEN_HTML = r"""<script>
if (!window.HW_ARTE) {
  const svg = (vb, corpo, classe, extra) => '<svg class="' + (classe || '') + '" viewBox="' + vb + '" aria-hidden="true" ' + (extra || '') + '>' + corpo + '</svg>';
  const ABOBORA = '<ellipse cx="32" cy="32" rx="30" ry="22" fill="#e8661a"/><ellipse cx="20" cy="32" rx="13" ry="21" fill="#f07a22"/><ellipse cx="44" cy="32" rx="13" ry="21" fill="#f07a22"/>'
    + '<ellipse cx="32" cy="32" rx="11" ry="22" fill="#ff8c2e"/><path d="M30 11c0-5 2-8 6-9l1 3c-3 1-4 3-4 6z" fill="#3f7d20"/>'
    + '<g class="chama" fill="#ffd34d"><path d="M17 26l7-6 3 8z"/><path d="M47 26l-7-6-3 8z"/><path d="M15 36c5 6 29 6 34 0l-4 6-4-3-4 4-4-4-4 4-4-4-4 3z"/></g>';
  const ARANHA = '<g stroke="#120b1a" stroke-width="2" fill="none" stroke-linecap="round"><path d="M14 18l-9-6M14 22L3 22M14 26l-9 6M14 30l-7 8M26 18l9-6M26 22l11 0M26 26l9 6M26 30l7 8"/></g>'
    + '<ellipse cx="20" cy="27" rx="8" ry="10" fill="#120b1a"/><circle cx="20" cy="15" r="6" fill="#120b1a"/><circle cx="18" cy="14" r="1.4" fill="#ff3b3b"/><circle cx="22" cy="14" r="1.4" fill="#ff3b3b"/>';
  const MORCEGO = '<path d="M32 12c-2-4-5-5-5-5l1 5c-6-6-14-6-20-3 4 1 7 4 7 8 3-3 7-2 9 1 2-2 5-3 8-3s6 1 8 3c2-3 6-4 9-1 0-4 3-7 7-8-6-3-14-3-20 3l1-5s-3 1-5 5z" fill="#14091f" stroke="#9b5de5" stroke-width="1"/>';
  const CHAPEU = '<defs><linearGradient id="hw-gc" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3b1f52"/><stop offset=".55" stop-color="#6a3d91"/><stop offset="1" stop-color="#2c173e"/></linearGradient>'
    + '<linearGradient id="hw-ga" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7a4aa6"/><stop offset="1" stop-color="#2a1638"/></linearGradient></defs>'
    + '<ellipse cx="50" cy="66" rx="47" ry="11" fill="url(#hw-ga)" stroke="#c8a6ff" stroke-width="1.2"/>'
    + '<path d="M30 64C34 46 39 32 48 20C54 12 63 6 75 9C67 12 62 18 60 27C58 40 63 52 70 64Z" fill="url(#hw-gc)" stroke="#c8a6ff" stroke-width="1.2" stroke-linejoin="round"/>'
    + '<path d="M75 9l4-3-1 5z" fill="#c8a6ff"/><path d="M31.5 58C43 61.5 57 61.5 68.5 58L70 64C57 67.5 43 67.5 30 64Z" fill="#ff7a1a"/>'
    + '<rect x="44" y="57.5" width="12" height="9" rx="1.5" fill="none" stroke="#ffd34d" stroke-width="2.2"/>'
    + '<path d="M44 38l1.6 3.4 3.6.4-2.7 2.4.8 3.6-3.3-1.9-3.3 1.9.8-3.6-2.7-2.4 3.6-.4z" fill="#ffd34d" opacity=".9"/><circle cx="57" cy="30" r="1.4" fill="#ffd34d"/><circle cx="52" cy="48" r="1" fill="#ffd34d"/>';
  const FANTASMA = '<path d="M20 2C10 2 4 10 4 20v24l6-5 5 5 5-5 5 5 5-5 6 5V20C36 10 30 2 20 2z" fill="#f3e9ff" opacity=".92"/><circle cx="14" cy="18" r="3" fill="#120b1a"/><circle cx="26" cy="18" r="3" fill="#120b1a"/><ellipse cx="20" cy="27" rx="3" ry="4" fill="#120b1a"/>';
  const LAPIDE = '<path d="M6 46V18C6 8 34 8 34 18v28z" fill="#3a3046"/><path d="M14 22h12M20 16v18" stroke="#6d5f80" stroke-width="3"/><path d="M0 46h40" stroke="#241a30" stroke-width="4"/>';
  const VELA = '<rect x="15" y="20" width="10" height="24" rx="2" fill="#f3e9ff"/><path d="M15 26c3 2 7 2 10 0" stroke="#d9c7f0" fill="none"/><path d="M20 4c4 5 5 9 0 14-5-5-4-9 0-14z" fill="#ffd34d"/><path d="M20 9c2 3 2 5 0 8-2-3-2-5 0-8z" fill="#ff7a1a"/>';
  const LUA = '<path d="M28 6a16 16 0 1 0 6 26A13 13 0 0 1 28 6z" fill="#ffe9a8"/><circle cx="17" cy="20" r="2" fill="#e8cf7d"/><circle cx="22" cy="30" r="1.4" fill="#e8cf7d"/>';
  // o doce: bala embrulhada com as pontas torcidas (listras laranja e roxo)
  const DOCE = '<defs><clipPath id="hw-dc"><ellipse cx="24" cy="16" rx="11" ry="9"/></clipPath></defs>'
    + '<path d="M13 16L3 8l2 8-2 8z" fill="#c8a6ff"/><path d="M35 16l10-8-2 8 2 8z" fill="#c8a6ff"/>'
    + '<ellipse cx="24" cy="16" rx="11" ry="9" fill="#ff7a1a"/>'
    + '<g clip-path="url(#hw-dc)" fill="#9b5de5"><path d="M14 4l6 0-8 24h-6z"/><path d="M26 4l6 0-8 24h-6z"/><path d="M38 4l6 0-8 24h-6z"/></g>'
    + '<ellipse cx="20" cy="12" rx="4" ry="2" fill="#fff" opacity=".45"/>';
  const COLINA = '<path d="M0 60 C 90 22 170 40 250 30 S 420 6 520 26 S 700 44 800 18 L 800 80 L 0 80 Z" fill="#0d0616"/>'
    + '<path d="M0 70 C 120 48 260 62 400 52 S 640 40 800 56 L 800 80 L 0 80 Z" fill="#080310"/>'
    + '<g fill="#1e1230"><path d="M300 34v-12a8 8 0 0 1 16 0v12z"/><path d="M332 30v-9a6 6 0 0 1 12 0v9z"/><path d="M560 30v-11a7 7 0 0 1 14 0v11z"/></g>'
    + '<g stroke="#0d0616" stroke-width="3" fill="none" stroke-linecap="round"><path d="M660 26 L664 -4 M664 6 L652 -6 M663 0 L676 -10 M664 12 L678 4"/></g>';
  function teia() {
    let s = '<g fill="none" stroke="rgba(243,233,255,.7)" stroke-width="1">';
    const raios = 7, an = [];
    for (let i = 0; i < raios; i++) { const a = (Math.PI / 2) * (i / (raios - 1)); an.push(a); s += '<line x1="0" y1="0" x2="' + (Math.cos(a) * 170).toFixed(1) + '" y2="' + (Math.sin(a) * 170).toFixed(1) + '"/>'; }
    for (let r = 24; r <= 160; r += 22) {
      let d = '';
      for (let i = 0; i < raios; i++) {
        const x = Math.cos(an[i]) * r, y = Math.sin(an[i]) * r;
        if (i === 0) { d = 'M' + x.toFixed(1) + ' ' + y.toFixed(1); continue; }
        const am = (an[i] + an[i - 1]) / 2, rc = r * .86;
        d += ' Q' + (Math.cos(am) * rc).toFixed(1) + ' ' + (Math.sin(am) * rc).toFixed(1) + ' ' + x.toFixed(1) + ' ' + y.toFixed(1);
      }
      s += '<path d="' + d + '"/>';
    }
    return s + '</g>';
  }
  window.HW_ARTE = { svg, ABOBORA, ARANHA, MORCEGO, CHAPEU, FANTASMA, LAPIDE, VELA, LUA, DOCE, COLINA, teia };
  // wallpaper EmpresaWeen 26 (prêmio da Caça aos Doces; vale o ano todo). tipo: capa | faixa | mini
  window.wallpaperEmpresaween = function (tipo) {
    const doces = tipo === 'capa' ? [[38, 70, -18], [55, 80, 12], [84, 74, -8]].map(([x, y, r]) => '<span class="doce-wp" style="left:' + x + '%;top:' + y + '%;transform:rotate(' + r + 'deg)">' + svg('0 0 48 32', DOCE) + '</span>').join('') : '';
    return '<div class="wp-iw ' + tipo + '"><div class="estrelas"></div>' + svg('0 0 40 40', LUA, 'lua')
      + '<span class="bat">' + svg('0 0 64 32', MORCEGO) + '</span><span class="bat b2">' + svg('0 0 64 32', MORCEGO) + '</span>'
      + svg('0 0 800 80', COLINA, 'colina', 'preserveAspectRatio="none"') + doces
      + svg('0 0 64 56', ABOBORA, 'ab a1') + svg('0 0 64 56', ABOBORA, 'ab a2') + svg('0 0 64 56', ABOBORA, 'ab a3')
      + '<div class="titulo-iw">EmpresaWeen 26<small>Caça aos Doces · Halloween 2026</small></div></div>';
  };
}
</script>
"""

_CSS_WALLPAPER_IW = r"""
  .wp-iw { position: relative; overflow: hidden; background: radial-gradient(circle at 78% 30%, rgba(255,233,168,.22), transparent 28%),
             linear-gradient(180deg, #120624 0%, #2a0f45 55%, #4a1a3d 100%); }
  .wp-iw .estrelas { position: absolute; inset: 0; background-image: radial-gradient(1.4px 1.4px at 12% 22%, #fff, transparent), radial-gradient(1px 1px at 30% 12%, #fff, transparent),
    radial-gradient(1.2px 1.2px at 46% 34%, #fff, transparent), radial-gradient(1px 1px at 62% 16%, #fff, transparent), radial-gradient(1.5px 1.5px at 88% 52%, #fff, transparent),
    radial-gradient(1px 1px at 22% 48%, #fff, transparent), radial-gradient(1.2px 1.2px at 70% 44%, #fff, transparent), radial-gradient(1px 1px at 94% 14%, #fff, transparent);
    opacity: .8; animation: iw-pisca 3.5s ease-in-out infinite alternate; }
  @keyframes iw-pisca { from { opacity: .45; } to { opacity: .95; } }
  .wp-iw .lua { position: absolute; right: 16%; top: 12%; height: 62%; aspect-ratio: 1; filter: drop-shadow(0 0 14px rgba(255,233,168,.7)); }
  .wp-iw .colina { position: absolute; left: 0; right: 0; bottom: 0; width: 100%; height: 48%; }
  .wp-iw .ab { position: absolute; bottom: 4%; height: 30%; aspect-ratio: 64/56; filter: drop-shadow(0 0 10px rgba(255,140,40,.75)); }
  .wp-iw .ab.a1 { left: 5%; } .wp-iw .ab.a2 { left: calc(5% + 6.5%); height: 21%; } .wp-iw .ab.a3 { right: 6%; height: 26%; }
  .wp-iw .bat { position: absolute; height: 16%; aspect-ratio: 2; left: -10%; top: 18%; animation: iw-voa 12s linear infinite; }
  .wp-iw .bat.b2 { top: 34%; height: 11%; animation-duration: 17s; animation-delay: -6s; }
  .wp-iw .bat svg { width: 100%; height: 100%; animation: iw-bate .25s ease-in-out infinite alternate; }
  @keyframes iw-bate { from { transform: scaleY(1); } to { transform: scaleY(.45); } }
  @keyframes iw-voa { 0% { left: -10%; transform: translateY(0); } 50% { transform: translateY(-40%); } 100% { left: 108%; transform: translateY(0); } }
  .wp-iw .doce-wp { position: absolute; height: 11%; aspect-ratio: 48/32; opacity: .9; }
  .wp-iw .doce-wp svg { width: 100%; height: 100%; }
  .wp-iw .titulo-iw { position: absolute; left: 4.5%; top: 16%; font-family: 'Creepster', Raleway, sans-serif; color: #ff7a1a; font-size: 34px; letter-spacing: .05em;
    text-shadow: 0 0 18px rgba(255,122,26,.6), 0 2px 0 rgba(0,0,0,.4); line-height: 1; }
  .wp-iw .titulo-iw small { display: block; font-family: Raleway, sans-serif; font-size: 11px; font-weight: 800; letter-spacing: .14em; text-transform: uppercase; color: #d9c7f0; text-shadow: none; margin-top: 6px; }
  .wp-iw.faixa .titulo-iw, .wp-iw.mini .titulo-iw, .wp-iw.mini .bat, .wp-iw.mini .doce-wp { display: none; }
  .wp-iw.mini .lua { right: 10%; top: 10%; height: 40%; } .wp-iw.mini .ab.a2 { display: none; }
  /* na capa a foto cobre o canto esquerdo e o Personalizar o direito: abóboras no meio */
  .wp-iw.capa .ab.a1 { left: 22%; } .wp-iw.capa .ab.a2 { left: calc(22% + 5.5%); } .wp-iw.capa .ab.a3 { right: 26%; }
  .wp-iw .chama { animation: iw-tremula 1.6s ease-in-out infinite; }
  @keyframes iw-tremula { 0%, 100% { opacity: 1; } 40% { opacity: .75; } 60% { opacity: .95; } 80% { opacity: .7; } }
  @media (prefers-reduced-motion: reduce) { .wp-iw .estrelas, .wp-iw .bat, .wp-iw .bat svg, .wp-iw .chama { animation: none !important; } }
"""

_ESTILO_LOJA_HTML = r"""<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Creepster&display=swap">
<style>
  .lj-wp { position: relative; overflow: hidden; }
  .wp-inv { background: radial-gradient(circle at 12% 130%, rgba(45,184,207,.16), transparent 45%), radial-gradient(circle at 92% -20%, rgba(176,203,28,.10), transparent 40%),
      linear-gradient(115deg, #22303a 0%, #2c3c48 55%, #1f2b34 100%); }
  .wp-inv .arcos-inv { position: absolute; inset: 0; width: 100%; height: 100%; }
  .wp-inv .marca-inv { position: absolute; top: 50%; left: 50%; transform: translate(-30%, -50%); display: flex; align-items: center; gap: 12px; color: #fff; }
  .wp-inv .marca-inv img { width: 46px; height: 46px; border-radius: 9px; }
  .wp-inv .marca-inv b { font-family: Raleway, sans-serif; font-weight: 500; font-size: 40px; letter-spacing: -.01em; line-height: 1; }
  .wp-inv .pill-inv { font-family: Raleway, sans-serif; font-size: 13px; font-weight: 600; color: #e6edf3; background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.14);
      border-radius: 8px 2px 8px 2px; padding: 6px 14px; margin-right: 26px; white-space: nowrap; }
  .tam-card.wp-inv .marca-inv { transform: translate(-50%, -50%); } .tam-card.wp-inv .pill-inv { display: none; } .tam-card.wp-inv .marca-inv b { font-size: 30px; } .tam-card.wp-inv .marca-inv img { width: 36px; height: 36px; }
  .tam-faixa.wp-inv .marca-inv { left: auto; right: 10px; top: 8px; transform: none; gap: 6px; }
  .tam-faixa.wp-inv .pill-inv, .tam-mini.wp-inv .pill-inv { display: none; }
  .tam-faixa.wp-inv .marca-inv img { width: 18px; height: 18px; border-radius: 4px; }
  .tam-faixa.wp-inv .marca-inv b { font-size: 13px; font-weight: 600; }
  .tam-mini.wp-inv .marca-inv { transform: translate(-50%, -50%); gap: 6px; }
  .tam-mini.wp-inv .marca-inv img { width: 24px; height: 24px; border-radius: 5px; } .tam-mini.wp-inv .marca-inv b { font-size: 18px; }
  @media (max-width: 640px) { .tam-capa.wp-inv .pill-inv { display: none; } .tam-capa.wp-inv .marca-inv { transform: translate(-40%, -50%); } }
  .wp-67 { background: radial-gradient(circle at 18% 120%, #ff8a00 0, transparent 55%), radial-gradient(circle at 85% -20%, #ffd400 0, transparent 50%), linear-gradient(115deg, #2a0f4d, #6a1b9a 45%, #c2185b); }
  .wp-67 .padrao67 { position: absolute; inset: -40px; opacity: .13; font-weight: 900; font-size: 18px; color: #fff; letter-spacing: 8px; line-height: 28px; transform: rotate(-12deg); white-space: pre; }
  .wp-67 .seis, .wp-67 .sete { position: absolute; top: 50%; font-weight: 900; color: #fff; line-height: 1; text-shadow: 0 4px 0 rgba(0,0,0,.25), 0 0 24px rgba(255,212,0,.55); animation: lj-balanca 1.1s ease-in-out infinite; }
  .wp-67 .sete { animation-delay: -.55s; }
  .wp-67 .maos { position: absolute; display: none; animation: lj-mao 1.1s ease-in-out infinite; }
  @keyframes lj-balanca { 0%, 100% { transform: translateY(-64%); } 50% { transform: translateY(-36%); } }
  @keyframes lj-mao { 0%, 100% { transform: rotate(-12deg); } 50% { transform: rotate(12deg); } }
  .tam-faixa.wp-67 .seis, .tam-faixa.wp-67 .sete { font-size: 40px; } .tam-faixa.wp-67 .seis { left: 16px; } .tam-faixa.wp-67 .sete { right: 16px; }
  .tam-capa.wp-67 .seis, .tam-capa.wp-67 .sete { font-size: 104px; } .tam-capa.wp-67 .seis { right: 150px; } .tam-capa.wp-67 .sete { right: 64px; }
  .tam-capa.wp-67 .maos { display: block; right: 244px; top: 42%; font-size: 36px; }
  .tam-card.wp-67 .seis, .tam-card.wp-67 .sete { font-size: 64px; } .tam-card.wp-67 .seis { left: calc(50% - 64px); } .tam-card.wp-67 .sete { left: calc(50% + 8px); }
  .tam-mini.wp-67 .seis, .tam-mini.wp-67 .sete { font-size: 26px; } .tam-mini.wp-67 .seis { left: 8px; } .tam-mini.wp-67 .sete { right: 8px; } .tam-mini .padrao67 { display: none; }
  .wp-gptw { background: radial-gradient(circle at 90% 10%, rgba(255,255,255,.18), transparent 40%), linear-gradient(120deg, #0d1b3d 0%, #13306e 55%, #c8102e 140%); }
  .wp-gptw .listras { position: absolute; inset: 0; background: repeating-linear-gradient(-45deg, rgba(255,255,255,.05) 0 12px, transparent 12px 26px); }
  .wp-gptw .brilho { position: absolute; top: -50%; left: -30%; width: 40%; height: 200%; transform: rotate(20deg); background: linear-gradient(90deg, transparent, rgba(255,255,255,.14), transparent); animation: lj-brilho 5s ease-in-out infinite; }
  @keyframes lj-brilho { 0% { left: -40%; } 60%, 100% { left: 130%; } }
  .wp-gptw .texto-gptw { position: absolute; left: 22px; top: 22px; color: #fff; font-weight: 900; }
  .wp-gptw .texto-gptw small { display: block; font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; opacity: .8; }
  .wp-gptw .texto-gptw b { font-size: 26px; }
  .tam-faixa.wp-gptw .texto-gptw, .tam-mini.wp-gptw .texto-gptw { display: none; } .tam-card.wp-gptw .texto-gptw b { font-size: 20px; }
  .lj-selo-gptw { position: absolute; right: 22px; top: 12px; width: 62px; height: 100px; background: #c8102e; color: #fff; border-radius: 4px; display: flex; flex-direction: column; align-items: center;
    justify-content: space-between; padding: 7px 4px 6px; box-shadow: 0 6px 18px rgba(0,0,0,.4); font-family: Arial, sans-serif; text-align: center; transform-origin: top right; box-sizing: border-box; }
  .lj-selo-gptw .t1 { font-size: 8.5px; font-weight: 800; line-height: 1.05; } .lj-selo-gptw .t2 { font-size: 7px; font-weight: 700; background: #fff; color: #c8102e; border-radius: 2px; padding: 2px 3px; }
  .lj-selo-gptw .t3 { font-size: 6.5px; line-height: 1.15; }
  .tam-faixa .lj-selo-gptw { right: 10px; top: 6px; transform: scale(.48); } .tam-card .lj-selo-gptw { transform: scale(.82); } .tam-mini .lj-selo-gptw { right: 6px; top: 4px; transform: scale(.4); }
  .lj-chip { display: inline-flex; align-items: center; vertical-align: 2px; margin-left: 5px; font-size: 10.5px; font-weight: 900; padding: 2px 7px; border-radius: 6px; color: #fff; -webkit-text-fill-color: #fff; letter-spacing: 0; font-family: Raleway, sans-serif; }
  .lj-chip-67 { background: linear-gradient(90deg, #ff8a00, #c2185b); } .lj-chip-gptw { background: #c8102e; } .lj-chip-iw { background: linear-gradient(90deg, #ff7a1a, #9b5de5); }
  .lj-anel-67 { box-shadow: 0 0 0 4px var(--bg-panel-solid, #181f27), 0 0 0 7px #ff8a00, 0 0 18px 6px rgba(194,24,91,.5) !important; }
  .lj-anel-gptw { box-shadow: 0 0 0 4px var(--bg-panel-solid, #181f27), 0 0 0 7px #c8102e !important; }
  .lj-anel-iw { box-shadow: 0 0 0 4px var(--bg-panel-solid, #181f27), 0 0 0 7px #ff7a1a, 0 0 18px 6px rgba(155,93,229,.5) !important; }
  /* cartão da Comunidade com o wallpaper na faixa de cima */
  .cartao-eu.lj-com-wp::before { display: none !important; }
  .cartao-eu > .lj-wp.tam-faixa { position: absolute; inset: 0 0 auto 0; height: 58px; border-radius: 18px 18px 0 0; }
  .cartao-eu > .lj-wp.tam-faixa.wp-iw { height: 58px; }
  /* cabeçalho do perfil com capa: foto à esquerda (metade sobre a capa) e as informações sempre ao lado dela */
  .lj-capa { height: 176px; border-radius: 18px 18px 0 0; border: 1px solid var(--border); border-bottom: 0; }
  .lj-capa + .cabecalho-perfil { display: grid; grid-template-columns: 128px minmax(0, 1fr); column-gap: 22px; align-items: start; flex-wrap: nowrap;
    background: var(--bg-panel); border: 1px solid var(--border); border-top: 0; border-radius: 0 0 18px 18px; padding: 0 26px 22px; position: relative; }
  .lj-capa + .cabecalho-perfil .foto-perfil-wrap { width: 128px; height: 128px; margin-top: -64px; }
  .lj-capa + .cabecalho-perfil .foto-perfil { width: 128px; height: 128px; border: 5px solid var(--bg-panel-solid, #181f27); font-size: 40px; box-sizing: border-box; }
  .lj-capa + .cabecalho-perfil .botao-trocar-foto { bottom: 4px; right: 4px; }
  .lj-capa + .cabecalho-perfil .info-cabecalho-perfil { padding-top: 16px; min-width: 0; }
  .lj-capa + .cabecalho-perfil .info-cabecalho-perfil h1 { font-size: 24px; }
  @media (max-width: 640px) { .lj-capa { height: 130px; } .lj-capa + .cabecalho-perfil { grid-template-columns: 1fr; padding: 0 18px 18px; } .lj-capa + .cabecalho-perfil .info-cabecalho-perfil { padding-top: 8px; } }
  .lj-personalizar { position: absolute; right: 14px; top: 14px; z-index: 3; font: inherit; font-size: 12px; font-weight: 800; cursor: pointer; color: #fff;
    background: rgba(0,0,0,.45); border: 1px solid rgba(255,255,255,.25); border-radius: 99px; padding: 6px 12px; backdrop-filter: blur(6px); }
  .lj-personalizar:hover { background: rgba(0,0,0,.6); }
  /* modal (Personalizar e as trocas da Loja) */
  .lj-fundo { position: fixed; inset: 0; background: rgba(0,0,0,.6); display: grid; place-items: center; z-index: 80; padding: 16px; }
  .lj-modal { width: 100%; max-width: 440px; background: var(--bg-panel-solid, #181f27); border: 1px solid var(--border-forte); border-radius: 18px; overflow: hidden; }
  .lj-modal .prev { height: 130px; position: relative; } .lj-modal .prev > .lj-wp { position: absolute; inset: 0; }
  .lj-modal .corpo { padding: 16px 18px 18px; } .lj-modal h4 { margin: 0; font-size: 18px; }
  .nota-lj { font-size: 12px; color: var(--fg-dim); margin: 0 0 14px; }
  .acoes-lj { display: flex; gap: 8px; justify-content: flex-end; flex-wrap: wrap; }
  .btn-lj { font: inherit; font-size: 12.5px; font-weight: 900; border-radius: 10px; padding: 7px 14px; cursor: pointer; border: 0; color: #1a1205; background: linear-gradient(90deg, #f2b705, #fb923c); text-decoration: none; display: inline-flex; align-items: center; }
  .btn-lj.sec { background: none; color: var(--fg); border: 1px solid var(--border-forte); }
  .btn-lj.uso { background: rgba(176,203,28,.16); color: var(--lime); cursor: default; }
  .btn-lj:disabled { opacity: .6; cursor: default; }
  .opcoes-lj { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 12px 0; }
  .opcao-lj { border: 2px solid var(--border); border-radius: 12px; overflow: hidden; cursor: pointer; background: none; padding: 0; color: inherit; font: inherit; text-align: left; }
  .opcao-lj.ativa { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.25); }
  .opcao-lj .mini { height: 62px; position: relative; } .opcao-lj .mini > .lj-wp, .opcao-lj .mini > .wp-iw { position: absolute; inset: 0; }
  .opcao-lj span { display: block; padding: 7px 10px; font-weight: 800; font-size: 12.5px; }
  @media (prefers-reduced-motion: reduce) { .wp-67 .seis, .wp-67 .sete, .wp-67 .maos, .wp-gptw .brilho { animation: none !important; } }
""" + _CSS_WALLPAPER_IW + """
</style>
"""

_SCRIPT_LOJA_HTML = r"""<script>
(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const ENFEITE = {
    '67': { chip: '<span class="lj-chip lj-chip-67">67</span>', anel: 'lj-anel-67' },
    gptw26: { chip: '<span class="lj-chip lj-chip-gptw">GPTW 26</span>', anel: 'lj-anel-gptw' },
    iw26: { chip: '<span class="lj-chip lj-chip-iw">🎃 26</span>', anel: 'lj-anel-iw' },
  };
  const PADRAO67 = Array(9).fill('67 67 67 67 67 67 67 67 67 67 67 67 67').join('\n');
  const SELO_GPTW = '<div class="lj-selo-gptw"><span class="t1">Great<br>Place<br>To<br>Work.</span><span class="t2">CERTIFICADA</span><span class="t3">2026<br>BRA</span></div>';
  const ARCOS_INV = '<svg class="arcos-inv" viewBox="0 0 800 200" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><g fill="none" stroke="rgba(255,255,255,.07)" stroke-width="1.2">'
    + '<circle cx="-40" cy="240" r="260"/><circle cx="-40" cy="240" r="340"/><circle cx="120" cy="-180" r="300"/><circle cx="860" cy="260" r="220"/></g></svg>';
  // tam: faixa (cartão da Comunidade) | capa (perfil) | card (Loja) | mini (Personalizar) | limpo (EmpresaWeen sem título)
  function wallpaperLoja(id, tam) {
    if (id === 'iw26') {
      const tipo = tam === 'card' || tam === 'capa' ? 'capa' : (tam === 'limpo' ? 'faixa' : tam);
      return window.wallpaperEmpresaween(tipo).replace('class="wp-iw', 'class="lj-wp tam-' + tam + ' wp-iw');
    }
    if (id === '67') return '<div class="lj-wp tam-' + tam + ' wp-67"><div class="padrao67">' + PADRAO67 + '</div><span class="seis">6</span><span class="sete">7</span><span class="maos">🤲</span></div>';
    if (id === 'gptw26') return '<div class="lj-wp tam-' + tam + ' wp-gptw"><div class="listras"></div><div class="brilho"></div><div class="texto-gptw"><small>Great Place to Work</small><b>Certificada 2026</b></div>' + SELO_GPTW + '</div>';
    // Padrão Empresa (banner institucional): azul petróleo, arcos finos, logo e "Especialista em eDocs"
    const logo = (document.querySelector('.navbar .marca img, .navbar img') || {}).src || '';
    return '<div class="lj-wp tam-' + tam + ' wp-inv">' + ARCOS_INV
      + '<div class="marca-inv"><span class="pill-inv">Especialista em eDocs</span>' + (logo ? '<img src="' + logo + '" alt="">' : '') + '<b>empresa</b></div></div>';
  }
  window.wallpaperLoja = wallpaperLoja;
  window.ENFEITE_LOJA = ENFEITE;
  const elemento = html => { const t = document.createElement('template'); t.innerHTML = html.trim(); return t.content.firstChild; };

  // faixa do cartão da Comunidade (o próprio cartão): wallpaper, selo no nome e anel na foto
  window.aplicarWallpaperCartao = function (id) {
    const cartao = document.querySelector('.cartao-eu');
    if (!cartao) return;
    cartao.querySelectorAll(':scope > .lj-wp').forEach(e => e.remove());
    cartao.querySelectorAll('.nome-eu .lj-chip').forEach(e => e.remove());
    cartao.classList.add('lj-com-wp');
    cartao.prepend(elemento(wallpaperLoja(id || 'padrao', 'faixa')));
    const nome = cartao.querySelector('.nome-eu'), enf = ENFEITE[id];
    if (nome && enf) nome.insertAdjacentHTML('beforeend', enf.chip);
    const foto = cartao.querySelector('.foto-eu .avatar-mural');
    if (foto) { Object.values(ENFEITE).forEach(e => foto.classList.remove(e.anel)); if (enf) foto.classList.add(enf.anel); }
  };

  // capa do perfil (todo mundo vê a de todo mundo); o Personalizar só no próprio perfil
  window.aplicarCapaPerfil = function (dados) {
    const cab = document.querySelector('.cabecalho-perfil');
    if (!cab || !dados) return;
    const antiga = cab.previousElementSibling;
    if (antiga && antiga.classList.contains('lj-capa')) antiga.remove();
    const id = dados.wallpaper || 'padrao', enf = ENFEITE[id];
    const capa = elemento(wallpaperLoja(id, 'capa'));
    capa.classList.add('lj-capa');
    if (dados.proprio_perfil) {
      capa.insertAdjacentHTML('beforeend', '<button type="button" class="lj-personalizar">🎨 Personalizar</button>');
      capa.querySelector('.lj-personalizar').onclick = window.abrirPersonalizarLoja;
    }
    cab.before(capa);
    const h1 = cab.querySelector('h1');
    if (h1 && enf && !h1.querySelector('.lj-chip')) h1.insertAdjacentHTML('beforeend', enf.chip);
    const foto = cab.querySelector('.foto-perfil');
    if (foto && enf) foto.classList.add(enf.anel);
  };

  window.abrirPersonalizarLoja = async function () {
    let dados;
    try { dados = await (await fetch('/api/loja')).json(); if (!dados.ok) throw new Error(dados.erro); }
    catch (e) { alert('Não foi possível abrir seus itens agora.'); return; }
    const meus = dados.itens.filter(i => i.tem);
    const f = elemento('<div class="lj-fundo"><div class="lj-modal" role="dialog" aria-modal="true" aria-label="Wallpaper do perfil"><div class="corpo"><h4>🎨 Wallpaper do perfil</h4>'
      + '<p class="nota-lj" style="margin:4px 0 0">Aparece na capa do seu perfil e no seu cartão da Comunidade. Todo mundo vê.</p>'
      + '<div class="opcoes-lj">' + meus.map(i => '<button type="button" class="opcao-lj' + (i.usando ? ' ativa' : '') + '" data-id="' + esc(i.id) + '"><div class="mini">'
        + wallpaperLoja(i.id, i.id === 'iw26' ? 'limpo' : 'mini') + '</div><span>' + esc(i.nome) + (i.usando ? ' · em uso' : '') + '</span></button>').join('') + '</div>'
      + '<div class="acoes-lj"><a class="btn-lj sec" href="/loja">🛍️ Conseguir mais na Loja</a><button type="button" class="btn-lj" data-fechar>Pronto</button></div></div></div></div>');
    document.body.appendChild(f);
    f.addEventListener('click', async ev => {
      const o = ev.target.closest('.opcao-lj');
      if (o) {
        const r = await (await fetch('/api/loja/usar', { method: 'POST', body: new URLSearchParams({ id: o.dataset.id }) })).json();
        if (r.ok) location.reload(); else alert(r.erro || 'Não deu pra trocar.');
        return;
      }
      if (ev.target === f || ev.target.hasAttribute('data-fechar')) f.remove();
    });
  };
})();
</script>
"""

_LOJA_WALLPAPERS_HTML = _ESTILO_LOJA_HTML + _ARTE_HALLOWEEN_HTML + _SCRIPT_LOJA_HTML
