"""Insígnias: visual compartilhado pelo hub e pelo perfil (2.35.5.0).

Um bloco só (CSS + JS) colocado no lugar de __INSIGNIAS__:
- svgInsignia(insignia, tamanho, brilho): desenha a insígnia (moldura hexagonal em
  degradê, miolo escuro, símbolo e faixa). Beta User, Dev/Founder, Contributor e
  tempo de casa (número + cor do nível).
- verificarCampanhaInsignias(modo): pergunta /api/insignias/campanha e mostra o
  convite da Beta User (só no hub; "Agora não" adia pro dia seguinte) ou a
  comemoração das insígnias novas (hub e perfil), que pergunta se a pessoa quer
  destacar a insígnia junto da foto.
- abrirParticipacaoIns(): o formulário do "Quero participar" (foto, entrada na
  empresa, aniversário, e-mail da Empresa e cargo atual se não tiver histórico),
  enviado pra /api/insignias/participar.
A lógica (quem ganha o quê) fica em areas/perfil/insignias.py.
"""


_INSIGNIAS_HTML = """
<style>
  .insignia-svg { display: block; overflow: visible; }
  .brilho-insignia { animation: brilho-ins 3.6s ease-in-out infinite; }
  @keyframes brilho-ins { 0%, 55% { transform: rotate(25deg) translateX(-40px); } 100% { transform: rotate(25deg) translateX(190px); } }
  .insignia-bloqueada .insignia-svg { filter: grayscale(1) brightness(.6); opacity: .6; }

  .fundo-ins { position: fixed; inset: 0; z-index: 200; display: flex; align-items: center; justify-content: center; padding: 16px;
               background: rgba(5,8,12,.62); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); animation: aparecer-ins .25s ease; }
  @keyframes aparecer-ins { from { opacity: 0; } }
  .cartao-ins { position: relative; width: min(460px, 100%); max-height: calc(100vh - 32px); overflow-y: auto; border-radius: 22px; text-align: center;
                background: var(--bg-panel-solid); border: 1px solid var(--border-forte); box-shadow: 0 30px 80px rgba(0,0,0,.55);
                animation: subir-ins .35s cubic-bezier(.2,.9,.3,1.2); }
  @keyframes subir-ins { from { transform: translateY(24px) scale(.97); opacity: 0; } }
  .topo-ins { position: relative; padding: 32px 24px 14px; overflow: hidden; border-radius: 22px 22px 0 0;
              background: radial-gradient(120% 90% at 50% 0%, rgba(45,184,207,.30), rgba(176,203,28,.10) 45%, transparent 75%); }
  .topo-ins::after { content: ''; position: absolute; inset: 0; pointer-events: none;
                     background-image: radial-gradient(rgba(var(--tinta),.10) 1px, transparent 1px); background-size: 14px 14px;
                     mask-image: linear-gradient(to bottom, #000, transparent 85%); -webkit-mask-image: linear-gradient(to bottom, #000, transparent 85%); }
  .selo-ins { display: inline-flex; align-items: center; gap: 6px; font-size: 10.5px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase;
              color: var(--lime); background: rgba(176,203,28,.12); border: 1px solid rgba(176,203,28,.35); padding: 4px 11px; border-radius: 999px;
              position: relative; z-index: 1; }
  .palco-ins { position: relative; z-index: 1; margin: 16px auto 2px; min-height: 150px; display: flex; align-items: center; justify-content: center; gap: 14px; flex-wrap: wrap; }
  .palco-ins .aura { position: absolute; width: 150px; height: 150px; left: 50%; top: 50%; margin: -75px 0 0 -75px; border-radius: 50%;
                     background: conic-gradient(from 0deg, rgba(45,184,207,0), rgba(45,184,207,.45), rgba(176,203,28,.45), rgba(45,184,207,0));
                     filter: blur(18px); animation: girar-ins 6s linear infinite; }
  @keyframes girar-ins { to { transform: rotate(360deg); } }
  .palco-ins .item-ins { position: relative; animation: flutuar-ins 3.2s ease-in-out infinite; }
  .palco-ins .item-ins:nth-child(3) { animation-delay: -1s; }
  .palco-ins .item-ins:nth-child(4) { animation-delay: -2s; }
  @keyframes flutuar-ins { 50% { transform: translateY(-6px); } }
  .cadeado-ins { position: absolute; z-index: 2; bottom: 14px; right: 4px; width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
                 background: var(--bg-panel-solid); border: 2px solid var(--border-forte); color: var(--fg); box-shadow: 0 6px 16px rgba(0,0,0,.4); }
  .cadeado-ins svg { width: 16px; height: 16px; }
  .corpo-ins { padding: 6px 28px 24px; }
  .corpo-ins h2 { margin: 0 0 8px; font-size: 21px; line-height: 1.25; color: var(--fg); }
  .corpo-ins h2 span { background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .corpo-ins p { margin: 0 auto; max-width: 370px; font-size: 13.5px; color: var(--fg-dim); line-height: 1.6; }
  .passos-ins { margin: 16px 0 18px; display: flex; flex-direction: column; gap: 7px; text-align: left; }
  .passo-ins { display: flex; align-items: center; gap: 11px; padding: 9px 13px; border-radius: 12px; border: 1px solid var(--border);
               background: rgba(var(--tinta),.025); font-size: 13px; color: var(--fg); }
  .passo-ins .bola { width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; flex: none; font-size: 12px; font-weight: 800;
                     background: rgba(var(--tinta),.08); color: var(--fg-dim); }
  .passo-ins.feito { color: var(--fg-dim); }
  .passo-ins.feito .bola { background: rgba(78,201,176,.18); color: var(--ok); }
  .passo-ins.feito .txt { text-decoration: line-through; text-decoration-color: rgba(var(--tinta),.3); }
  .passo-ins.agora { border-color: rgba(45,184,207,.55); background: rgba(45,184,207,.07); }
  .passo-ins.agora .bola { background: var(--gradiente-marca); color: #0b0f14; }
  .passo-ins.premio .bola { background: rgba(176,203,28,.14); color: var(--lime); }
  .passo-ins .dica { margin-left: auto; font-size: 11px; color: var(--fg-dim); white-space: nowrap; }
  .botoes-ins { display: flex; flex-direction: column; gap: 8px; }
  .btn-ins { display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 13px 16px; border-radius: 12px;
             font-size: 14px; font-weight: 800; font-family: inherit; cursor: pointer; border: none; background: var(--gradiente-marca); color: #0b0f14;
             box-shadow: 0 10px 26px rgba(45,184,207,.28); text-decoration: none; }
  .btn-ins svg { width: 17px; height: 17px; }
  .btn-depois-ins { background: none; border: none; color: var(--fg-dim); font-size: 12.5px; cursor: pointer; padding: 6px; font-family: inherit; }
  .rodape-ins { margin-top: 4px; font-size: 11px; color: var(--fg-dim); opacity: .85; }
  .fechar-ins { position: absolute; top: 12px; right: 12px; z-index: 3; width: 32px; height: 32px; border-radius: 9px; display: grid; place-items: center;
                background: rgba(var(--poco),.35); border: 1px solid var(--border); color: var(--fg-dim); cursor: pointer; padding: 0; }
  .fechar-ins svg { width: 14px; height: 14px; }
  .nomes-novas-ins { display: flex; justify-content: center; gap: 6px; flex-wrap: wrap; margin-top: 12px; }
  .nomes-novas-ins span { font-size: 11.5px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: rgba(var(--tinta),.07); color: var(--fg); }
  .confete-ins { position: absolute; top: -10px; width: 7px; height: 12px; border-radius: 2px; opacity: .9; animation: cair-ins 2.6s linear infinite; }
  @keyframes cair-ins { to { transform: translateY(260px) rotate(540deg); opacity: 0; } }
  /* convite: o que vamos pedir */
  .titulo-reqs-ins { font-size: 10.5px; font-weight: 800; letter-spacing: .07em; text-transform: uppercase; color: var(--fg-dim); margin: 16px 0 8px; }
  .reqs-ins { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-bottom: 18px; }
  .req-chip-ins { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 6px 11px; border-radius: 999px; color: var(--fg);
                  border: 1px solid var(--border); background: rgba(var(--tinta),.03); }
  .req-chip-ins .ic { font-size: 12px; }
  .req-chip-ins.feito { color: var(--fg-dim); border-color: rgba(78,201,176,.35); }
  .req-chip-ins.feito .ic { color: var(--ok); font-weight: 800; }
  /* formulário de participação */
  .form-ins { padding-top: 26px; text-align: left; }
  .form-ins h2, .form-ins p, .form-ins > .selo-ins { text-align: center; }
  .form-ins > .selo-ins { display: flex; width: fit-content; margin-left: auto; margin-right: auto; }
  .campos-part-ins { display: flex; flex-direction: column; gap: 12px; margin: 18px 0 10px; }
  .campo-ins label { display: block; font-size: 12px; font-weight: 700; color: var(--fg); margin-bottom: 6px; }
  .campo-ins label .opc { font-weight: 400; color: var(--fg-dim); margin-left: 4px; }
  .campo-ins input, .campo-ins select { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border); background: rgba(var(--poco),.28);
                                       color: var(--fg); font-size: 13.5px; font-family: inherit; color-scheme: dark; box-sizing: border-box; }
  :root[data-tema="claro"] .campo-ins input, :root[data-tema="claro"] .campo-ins select { color-scheme: light; }
  .campo-ins input:focus, .campo-ins select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .linha-ins { display: flex; gap: 8px; }
  .mini-rotulo-ins { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 4px; }
  .linha-ins > * { flex: 1; min-width: 0; }
  .foto-campo-ins { display: flex; align-items: center; gap: 14px; padding: 12px; border: 1px dashed rgba(45,184,207,.45); border-radius: 14px; background: rgba(45,184,207,.04); }
  .foto-prev-ins { width: 72px; height: 72px; border-radius: 50%; flex: none; display: grid; place-items: center; cursor: pointer; padding: 0; overflow: hidden;
                   background: rgba(var(--tinta),.06); border: 2px solid var(--border-forte); color: var(--fg-dim); }
  .foto-prev-ins svg { width: 26px; height: 26px; }
  .foto-prev-ins img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .foto-prev-ins.tem { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.2); }
  .dica-ins { font-size: 11.5px; color: var(--fg-dim); margin: -2px 0 8px; }
  .btn-sec-ins { background: rgba(var(--tinta),.05); border: 1px solid var(--border); color: var(--fg); border-radius: 8px; padding: 6px 12px; font-size: 12px;
                 cursor: pointer; font-family: inherit; }
  .btn-sec-ins:hover { border-color: var(--teal); }
  .area-ins { display: flex; gap: 6px; margin-top: 8px; }
  .area-ins button { flex: 1; padding: 7px; border-radius: 9px; border: 1px solid var(--border); background: transparent; color: var(--fg-dim); cursor: pointer;
                     font-size: 12px; font-family: inherit; }
  .area-ins button.ativa { border-color: var(--teal); color: var(--fg); background: rgba(45,184,207,.10); font-weight: 700; }
  .pronto-ins { font-size: 12.5px; color: var(--fg-dim); padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(78,201,176,.35); background: rgba(78,201,176,.06); }
  .pronto-ins b { color: var(--fg); }
  .erro-ins { color: var(--erro); font-size: 12.5px; min-height: 18px; margin: 4px 0 8px; text-align: center; }
  .btn-ins:disabled { opacity: .6; cursor: default; }
  /* erro por campo e opção "desde que entrei" (2.35.6.0) */
  .erro-campo-ins { color: var(--erro); font-size: 11.5px; margin-top: 5px; min-height: 0; }
  .erro-campo-ins:empty { display: none; }
  .campo-ins.com-erro input, .campo-ins.com-erro select { border-color: var(--erro); box-shadow: 0 0 0 3px rgba(241,76,76,.15); }
  .campo-ins.com-erro .foto-campo-ins { border-color: var(--erro); }
  .campo-ins label.opcao-check-ins, .opcao-check-ins { display: flex; align-items: flex-start; gap: 10px; padding: 10px 12px; border: 1px solid var(--border); border-radius: 10px;
                     cursor: pointer; font-weight: 400 !important; background: rgba(var(--tinta),.02); }
  .opcao-check-ins input { position: absolute; opacity: 0; pointer-events: none; }
  .caixa-check-ins { width: 18px; height: 18px; border-radius: 5px; border: 2px solid var(--border-forte); flex: none; margin-top: 1px; display: grid; place-items: center; }
  .opcao-check-ins input:checked + .caixa-check-ins { background: var(--teal); border-color: var(--teal); }
  .opcao-check-ins input:checked + .caixa-check-ins::after { content: ''; width: 5px; height: 9px; border: solid #0b0f14; border-width: 0 2px 2px 0; transform: rotate(45deg) translate(-1px, -1px); }
  .opcao-check-ins b { font-size: 12.5px; color: var(--fg); }
  .opc-linha { display: block; font-size: 11px; color: var(--fg-dim); margin-top: 2px; }
  #part-cargo-quando { margin-top: 8px; }
  /* ajuste da foto */
  .fundo-recorte-ins { z-index: 220; }
  .recorte-ins { width: min(400px, 100%); }
  .dica-gif-ins { font-size: 12px !important; opacity: .85; margin-top: -4px !important; }
  .palco-recorte-ins { position: relative; width: min(280px, 100%); aspect-ratio: 1; margin: 16px auto 12px; border-radius: 16px; overflow: hidden;
                       background: repeating-conic-gradient(rgba(var(--tinta),.06) 0 25%, transparent 0 50%) 0 0 / 20px 20px; touch-action: none; }
  .palco-recorte-ins canvas { width: 100%; height: 100%; display: block; cursor: grab; }
  .palco-recorte-ins canvas:active { cursor: grabbing; }
  .mascara-recorte-ins { position: absolute; inset: 0; pointer-events: none; border-radius: 50%; box-shadow: 0 0 0 999px rgba(5,8,12,.6);
                         outline: 2px solid rgba(45,184,207,.85); outline-offset: -2px; }
  .zoom-recorte-ins { display: flex; align-items: center; gap: 10px; justify-content: center; }
  .zoom-recorte-ins input[type="range"] { flex: 1; max-width: 220px; accent-color: var(--teal); }
  .btn-zoom-ins { width: 30px; height: 30px; border-radius: 8px; border: 1px solid var(--border); background: rgba(var(--tinta),.05); color: var(--fg);
                  font-size: 16px; cursor: pointer; display: grid; place-items: center; padding: 0; }
  .linha-botoes-ins { flex-direction: row; margin-top: 10px; }
  .linha-botoes-ins > * { flex: 1; }
  /* comemoração: escolher a insígnia pra destacar */
  .escolha-ins { background: none; border: none; padding: 6px; border-radius: 16px; cursor: default; }
  .palco-ins .escolha-ins[onclick] { cursor: pointer; }
  .palco-ins .escolha-ins[onclick]:not(.selecionada) { opacity: .62; }
  .palco-ins .escolha-ins[onclick].selecionada { box-shadow: 0 0 0 2px var(--teal); background: rgba(45,184,207,.08); }
  .pergunta-destaque-ins { margin: 18px 0 14px; padding: 12px 14px; border-radius: 12px; border: 1px solid rgba(176,203,28,.35); background: rgba(176,203,28,.06); }
  .pergunta-destaque-ins .t { font-size: 13.5px; font-weight: 800; color: var(--fg); }
  .pergunta-destaque-ins .d { font-size: 12px; color: var(--fg-dim); margin-top: 3px; }
  @media (prefers-reduced-motion: reduce) {
    .brilho-insignia, .palco-ins .aura, .palco-ins .item-ins, .confete-ins { animation: none; }
    .confete-ins { display: none; }
  }
  /* foto ampliada (3.0.4.0): clicar na foto de alguém abre ela grande, com a insígnia em destaque e o link pro perfil */
  .passos-bug-ins { display: flex; flex-direction: column; gap: 10px; text-align: left; margin: 4px 0 18px; }
  .passo-bug-ins { display: flex; gap: 12px; align-items: flex-start; padding: 11px 13px; border-radius: 12px;
                   background: rgba(var(--tinta), .04); border: 1px solid var(--border); }
  .passo-bug-ins .num-bug-ins { font-size: 20px; line-height: 1.2; flex-shrink: 0; }
  .passo-bug-ins b { display: block; font-size: 13.5px; color: var(--fg); margin-bottom: 3px; }
  .passo-bug-ins span { font-size: 12.5px; color: var(--fg-dim); line-height: 1.5; }
  .fundo-foto-pessoa { position: fixed; inset: 0; z-index: 260; display: flex; align-items: center; justify-content: center; padding: 16px;
                       background: rgba(4,8,12,.78); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); animation: aparecer-foto .2s ease; }
  @keyframes aparecer-foto { from { opacity: 0; } to { opacity: 1; } }
  .cartao-foto-pessoa { position: relative; text-align: center; animation: crescer-foto .28s cubic-bezier(.2,1.2,.4,1); }
  @keyframes crescer-foto { from { transform: scale(.85); } to { transform: scale(1); } }
  .cartao-foto-pessoa .moldura-foto { position: relative; width: min(340px, 78vw); height: min(340px, 78vw); margin: 0 auto; }
  .cartao-foto-pessoa .foto-grande { width: 100%; height: 100%; border-radius: 50%; object-fit: cover; display: flex; align-items: center; justify-content: center;
                                     font-size: 96px; font-weight: 800; color: #fff; background: var(--cor-av, #2db8cf);
                                     box-shadow: 0 0 0 6px rgba(255,255,255,.08), 0 30px 80px rgba(0,0,0,.6); }
  .cartao-foto-pessoa .ins-grande { position: absolute; right: 2%; bottom: 0; filter: drop-shadow(0 6px 12px rgba(0,0,0,.6)); }
  .cartao-foto-pessoa .nome-grande { font-size: 22px; font-weight: 800; color: #fff; margin-top: 18px; }
  .cartao-foto-pessoa .cargo-grande { font-size: 13.5px; color: rgba(255,255,255,.72); margin-top: 4px; }
  .cartao-foto-pessoa .acoes-foto { margin-top: 16px; display: flex; gap: 10px; justify-content: center; }
  .cartao-foto-pessoa .acoes-foto a, .cartao-foto-pessoa .acoes-foto button { border: none; border-radius: 12px; padding: 10px 20px; font: inherit;
                                     font-size: 13.5px; font-weight: 800; cursor: pointer; text-decoration: none; }
  .cartao-foto-pessoa .acoes-foto a { background: #2db8cf; color: #071016; }
  .cartao-foto-pessoa .acoes-foto button { background: rgba(255,255,255,.12); color: #fff; }
</style>
<script>
// Foto ampliada (3.0.4.0). p = {login, nome, tem_foto, cargo, equipe, destaque}; noPerfil esconde o "Ver perfil"
function abrirFotoPessoa(p, noPerfil) {
  if (!p || !p.login) return;
  document.querySelectorAll('.fundo-foto-pessoa').forEach(f => f.remove());
  const partes = String(p.nome || p.login).trim().split(' ').filter(Boolean);
  const iniciais = ((partes[0] || '?')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
  const cores = ['#2db8cf', '#7c9a12', '#c084fc', '#f97316', '#e85d75', '#3b82f6', '#14b8a6', '#d4a017'];
  let h = 0;
  for (const c of String(p.nome || p.login)) h = (h * 31 + c.charCodeAt(0)) % 997;
  const foto = p.tem_foto
    ? '<img class="foto-grande" src="/foto-usuario/' + encodeURIComponent(p.login) + '" alt="">'
    : '<div class="foto-grande" style="--cor-av:' + cores[h % cores.length] + '">' + escaparIns(iniciais) + '</div>';
  const fundo = document.createElement('div');
  fundo.className = 'fundo-foto-pessoa';
  fundo.setAttribute('role', 'dialog');
  fundo.setAttribute('aria-modal', 'true');
  fundo.innerHTML = '<div class="cartao-foto-pessoa"><div class="moldura-foto">' + foto
    + (p.destaque ? '<span class="ins-grande">' + svgInsignia(p.destaque, 96, true) + '</span>' : '') + '</div>'
    + '<div class="nome-grande">' + escaparIns(p.nome || p.login) + '</div>'
    + '<div class="cargo-grande">' + escaparIns([p.cargo, p.equipe].filter(Boolean).join(' · ')) + '</div>'
    + '<div class="acoes-foto">' + (noPerfil ? '' : '<a href="/perfil/' + encodeURIComponent(p.login) + '">Ver perfil</a>')
    + '<button type="button">Fechar</button></div></div>';
  const fechar = () => { fundo.remove(); document.removeEventListener('keydown', aoTeclar); };
  const aoTeclar = e => { if (e.key === 'Escape') fechar(); };
  fundo.querySelector('button').onclick = fechar;
  fundo.addEventListener('click', e => { if (e.target === fundo || e.target.classList.contains('cartao-foto-pessoa')) fechar(); });
  document.addEventListener('keydown', aoTeclar);
  document.body.appendChild(fundo);
}

// ---------------- desenho das insígnias ----------------
const CORES_TEMPO_INS = {
  bronze: ['#f0b07a', '#b5652c'], prata: ['#f3f4f6', '#8e99a6'], ouro: ['#ffe08a', '#c8921a'],
  platina: ['#e9f6fb', '#6fa8bd'], diamante: ['#a5f3fc', '#a78bfa'], ferro: ['#9ba3ab', '#3a4048'],
};
const ICONES_INS = {
  inseto: '<path d="M8.5 7.5a3.5 3.5 0 0 1 7 0"/><rect x="7" y="7.5" width="10" height="12" rx="5"/><path d="M12 10v9.5M2.5 13.5H7M17 13.5h4.5M4 8l3 2M20 8l-3 2M4 19l3-2M20 19l-3-2M9.5 4.5 8 3M14.5 4.5 16 3"/>',
  codigo: '<path d="M8 7l-5 5 5 5M16 7l5 5-5 5M13.5 4.5l-3 15"/>',
  quebra: '<path d="M10 3.5a2 2 0 0 1 4 0V5h4a1 1 0 0 1 1 1v4h-1.5a2 2 0 0 0 0 4H19v4a1 1 0 0 1-1 1h-4v-1.5a2 2 0 0 0-4 0V19H6a1 1 0 0 1-1-1v-4h1.5a2 2 0 0 0 0-4H5V6a1 1 0 0 1 1-1h4z"/>',
};
let contadorIns = 0;

function hexagonoIns(cx, cy, r) {
  const pts = [];
  for (let a = 0; a < 360; a += 60) {
    const rad = (a - 90) * Math.PI / 180;
    pts.push((cx + r * Math.cos(rad)).toFixed(1) + ',' + (cy + r * Math.sin(rad)).toFixed(1));
  }
  return pts.join(' ');
}

function visualIns(ins) {
  if (ins.tipo === 'fundador') return { c1: '#b389f9', c2: '#ffb347', faixa: 'DEV · FOUNDER', icone: 'codigo' };
  if (ins.tipo === 'contribuidor') return { c1: '#4cc9f0', c2: '#9b5de5', faixa: 'CONTRIBUTOR', icone: 'quebra' };
  if (ins.tipo === 'rank') return { c1: '#f5d0fe', c2: '#9333ea', faixa: 'RANK MASTER', numero: ins.produtos,
                                    unidade: ins.produtos === 1 ? 'PRODUTO' : 'PRODUTOS' };
  if (ins.tipo === 'bug') return { c1: '#fca5a5', c2: '#ea580c', faixa: 'BUG HUNTER', icone: 'inseto' };
  if (ins.tipo === 'palmas') {  // palminhas recebidas (3.1.3.0): a cor esquenta a cada nível
    const cores = { 10: ['#fef08a', '#eab308'], 50: ['#fed7aa', '#f97316'], 100: ['#fecdd3', '#f43f5e'], 250: ['#f5d0fe', '#c026d3'], 1000: ['#a5f3fc', '#f59e0b'] };
    const c = cores[ins.palmas] || cores[10];
    const n = ins.palmas >= 1000 && ins.palmas % 1000 === 0 ? (ins.palmas / 1000) + 'K' : ins.palmas;
    return { c1: c[0], c2: c[1], faixa: 'PALMINHAS', numero: n, unidade: 'RECEBIDAS', diamante: ins.palmas >= 1000 };
  }
  if (ins.tipo === 'tempo') {
    const cores = CORES_TEMPO_INS[ins.nivel] || CORES_TEMPO_INS.bronze;
    // ferro (menos de 1 ano): o número é de meses (3.0.2.0)
    const meses = ins.nivel === 'ferro' && ins.meses;
    return { c1: cores[0], c2: cores[1], faixa: (ins.nivel_nome || '').toUpperCase(), numero: meses || ins.anos, diamante: ins.nivel === 'diamante',
             unidade: meses ? (meses === 1 ? 'MÊS' : 'MESES') : (ins.anos === 1 ? 'ANO' : 'ANOS') };
  }
  return { c1: '#2db8cf', c2: '#b0cb1c', faixa: 'BETA USER', beta: true };
}

function svgInsignia(ins, tamanho, brilho) {
  const v = visualIns(ins);
  const u = 'ins' + (++contadorIns);
  tamanho = tamanho || 120;
  let simbolo;
  if (v.beta) {
    simbolo = `<text x="60" y="76" text-anchor="middle" font-family="Georgia, 'Times New Roman', serif" font-size="50" font-weight="700" fill="url(#g${u})">β</text>`;
  } else if (v.numero !== undefined) {
    const n = String(v.numero);
    simbolo = `<text x="60" y="${n.length > 1 ? 67 : 68}" text-anchor="middle" font-family="Raleway, 'Segoe UI', Arial, sans-serif" font-size="${n.length > 1 ? 34 : 44}" font-weight="900" fill="url(#g${u})">${n}</text>` +
      `<text x="60" y="84.5" text-anchor="middle" font-family="Raleway, 'Segoe UI', Arial, sans-serif" font-size="7.5" font-weight="800" letter-spacing="1.6" fill="${v.c1}" opacity=".85">${v.unidade}</text>`;
  } else {
    simbolo = `<g transform="translate(36 30) scale(2)" fill="none" stroke="url(#g${u})" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICONES_INS[v.icone]}</g>`;
  }
  const faiscas = v.diamante
    ? '<path d="M88 22 l2 5 5 2 -5 2 -2 5 -2 -5 -5 -2 5 -2z" fill="#fff" opacity=".9"/><path d="M30 36 l1.4 3.4 3.4 1.4 -3.4 1.4 -1.4 3.4 -1.4 -3.4 -3.4 -1.4 3.4 -1.4z" fill="#fff" opacity=".75"/>'
    : '<circle cx="86" cy="34" r="2.2" fill="#fff" opacity=".85"/><circle cx="36" cy="42" r="1.4" fill="#fff" opacity=".6"/>';
  const tamFaixa = v.faixa.length > 11 ? 8.2 : (v.faixa.length > 9 ? 9.5 : 11);
  return `<svg class="insignia-svg" width="${tamanho}" height="${Math.round(tamanho * 1.1)}" viewBox="0 0 120 132" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="${ins.nome || ''}">
    <defs>
      <linearGradient id="g${u}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${v.c1}"/><stop offset="1" stop-color="${v.c2}"/></linearGradient>
      <radialGradient id="m${u}" cx="50%" cy="38%" r="70%"><stop offset="0" stop-color="#1d2a36"/><stop offset="1" stop-color="#0b1118"/></radialGradient>
      <clipPath id="c${u}"><polygon points="${hexagonoIns(60, 58, 43)}"/></clipPath>
      <filter id="s${u}" x="-30%" y="-30%" width="160%" height="160%"><feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="${v.c1}" flood-opacity=".35"/></filter>
    </defs>
    <g filter="url(#s${u})">
      <polygon points="${hexagonoIns(60, 58, 51)}" fill="url(#g${u})"/>
      <polygon points="${hexagonoIns(60, 58, 43)}" fill="url(#m${u})"/>
      <polygon points="${hexagonoIns(60, 58, 37)}" fill="none" stroke="url(#g${u})" stroke-opacity=".35" stroke-width="1.2"/>
    </g>
    <g clip-path="url(#c${u})">${simbolo}${faiscas}
      ${brilho ? '<rect class="brilho-insignia" x="-60" y="-10" width="26" height="160" fill="#fff" opacity=".13" transform="rotate(25 60 58)"/>' : ''}
    </g>
    <path d="M8 94 L22 90 L22 112 L8 116 L14 103 Z" fill="url(#g${u})" opacity=".75"/>
    <path d="M112 94 L98 90 L98 112 L112 116 L106 103 Z" fill="url(#g${u})" opacity=".75"/>
    <path d="M18 88 H102 V110 H18 Z" fill="url(#g${u})"/>
    <path d="M18 110 L22 114 L22 110 Z M102 110 L98 114 L98 110 Z" fill="#000" opacity=".35"/>
    <text x="60" y="103.5" text-anchor="middle" font-family="Raleway, 'Segoe UI', Arial, sans-serif" font-size="${tamFaixa}" font-weight="800" letter-spacing="1.3" fill="#0b0f14">${v.faixa}</text>
  </svg>`;
}

// ---------------- convite, participação e comemoração ----------------
const ICONE_X_INS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';
const ICONE_CADEADO_INS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';
const ICONE_CAMERA_INS = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>';
const ICONE_ESTRELA_INS = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 2l3.1 6.3 6.9 1-5 4.9 1.2 6.8L12 17.8 5.8 21l1.2-6.8-5-4.9 6.9-1z"/></svg>';
const ICONES_REQ_INS = { foto: '&#128247;', data_inicio: '&#128188;', aniversario: '&#127874;', email: '&#9993;', historico: '&#128200;' };
const ROTULOS_CURTOS_INS = { foto: 'Foto de perfil', data_inicio: 'Entrada na empresa', aniversario: 'Aniversário', email: 'E-mail da Empresa', historico: 'Cargo atual' };
const MESES_INS = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
const CHAVE_ADIADO_INS = 'pda-convite-beta-adiado';
let campanhaAtualIns = null;
let modoAtualIns = 'hub';

function escaparIns(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
function hojeIns() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function fecharIns(el) { const f = el.closest('.fundo-ins'); if (f) f.remove(); }
function abrirFundoIns(html, rotulo) {
  document.querySelectorAll('.fundo-ins:not(.fundo-recorte-ins)').forEach(f => f.remove());
  const fundo = document.createElement('div');
  fundo.className = 'fundo-ins';
  fundo.innerHTML = `<div class="cartao-ins" role="dialog" aria-modal="true" aria-label="${escaparIns(rotulo)}">${html}</div>`;
  document.body.appendChild(fundo);
  return fundo;
}
// avisa a página (o perfil recarrega os dados) depois de participar ou destacar
function avisarMudancaIns() { if (typeof window.aoMudarInsigniasIns === 'function') window.aoMudarInsigniasIns(); }

// Campanha Bug Hunter (3.0.5.0): não abre sozinha ao entrar; só mostra os requisitos quando a pessoa clica
const REQUISITOS_BUG_HUNTER_INS = [
  ['🔍', 'Encontre um bug no PDA', 'Visual (algo desalinhado, texto errado, tela quebrada no celular ou no modo claro) ou de funcionamento (botão que não responde, erro, número que não bate).'],
  ['📸', 'Reporte pro Igor Leal ou pra Debora Sampaio', 'Mande um print e o passo a passo pra gente ver o problema acontecer.'],
  ['🏅', 'Aprovação e insígnia', 'Depois da aprovação, eles liberam a Bug Hunter no seu perfil e você fica sabendo pelo sininho.'],
];
function abrirRequisitosBugHunterIns() {
  const passos = REQUISITOS_BUG_HUNTER_INS.map(([ic, titulo, texto], i) =>
    `<div class="passo-bug-ins"><span class="num-bug-ins">${ic}</span><div><b>${i + 1}. ${escaparIns(titulo)}</b><span>${escaparIns(texto)}</span></div></div>`).join('');
  abrirFundoIns(`
      <button class="fechar-ins" aria-label="Fechar" onclick="this.closest('.fundo-ins').remove()">${ICONE_X_INS}</button>
      <div class="topo-ins">
        <span class="selo-ins">&#128027; Campanha · Insígnia exclusiva</span>
        <div class="palco-ins"><div class="aura"></div><div class="item-ins insignia-bloqueada">${svgInsignia({ tipo: 'bug', nome: 'Bug Hunter' }, 128, false)}<span class="cadeado-ins">${ICONE_CADEADO_INS}</span></div></div>
      </div>
      <div class="corpo-ins">
        <h2>Vire um<br><span>Bug Hunter</span></h2>
        <p>Achou algo estranho no PDA? Reporte e ganhe a insígnia de caçador de bugs, que fica no seu perfil à vista de todo mundo.</p>
        <div class="titulo-reqs-ins">Como ganhar</div>
        <div class="passos-bug-ins">${passos}</div>
        <div class="botoes-ins">
          <button class="btn-ins" onclick="this.closest('.fundo-ins').remove()">${ICONE_ESTRELA_INS} Entendi, vou caçar!</button>
        </div>
      </div>`, 'Campanha Bug Hunter');
}

function abrirConviteBetaIns(c) {
  campanhaAtualIns = c;
  const pendentes = c.requisitos.filter(r => !r.feito).length;
  const itens = c.requisitos.map(r => `<div class="req-chip-ins ${r.feito ? 'feito' : ''}"><span class="ic">${r.feito ? '&#10003;' : ICONES_REQ_INS[r.id]}</span>${escaparIns(ROTULOS_CURTOS_INS[r.id] || r.nome)}</div>`).join('');
  abrirFundoIns(`
      <button class="fechar-ins" aria-label="Agora não" onclick="adiarConviteIns(this)">${ICONE_X_INS}</button>
      <div class="topo-ins">
        <span class="selo-ins">&#10024; Campanha · Insígnia exclusiva</span>
        <div class="palco-ins"><div class="aura"></div><div class="item-ins insignia-bloqueada">${svgInsignia({ tipo: 'beta', nome: 'PDA Beta User' }, 128, false)}<span class="cadeado-ins">${ICONE_CADEADO_INS}</span></div></div>
      </div>
      <div class="corpo-ins">
        <h2>Desbloqueie a insígnia<br><span>PDA Beta User</span></h2>
        <p>Participe da campanha da fase beta: complete seu perfil e ganhe a insígnia, que fica junto da sua foto, à vista de todo mundo.${c.fim_beta ? ' <b>A campanha vai até ' + c.fim_beta.split('-').reverse().join('/') + '</b>; depois disso a insígnia não pode mais ser conquistada.' : ''}</p>
        <div class="titulo-reqs-ins">O que vamos pedir</div>
        <div class="reqs-ins">${itens}</div>
        <div class="botoes-ins">
          <button class="btn-ins" onclick="abrirParticipacaoIns()">${ICONE_ESTRELA_INS} Quero participar</button>
          <button class="btn-depois-ins" onclick="adiarConviteIns(this)">Agora não</button>
        </div>
        <div class="rodape-ins">${pendentes === 1 ? 'Falta só 1 item' : 'São ' + pendentes + ' itens'} · leva menos de 2 minutos</div>
      </div>`, 'Campanha PDA Beta User');
}

function adiarConviteIns(el) {
  try { localStorage.setItem(CHAVE_ADIADO_INS, hojeIns()); } catch (e) { /* sem localStorage: volta no próximo acesso */ }
  fecharIns(el);
}

// ---- formulário "Quero participar" ----
let fotoNovaIns = '';
let arquivoFotoIns = null;  // o arquivo escolhido, pra reabrir o ajuste

function opcoesMesAnoIns(c) {
  // meses e anos possíveis pro cargo: da entrada na empresa até o mês atual do servidor
  const hoje = (c.hoje || hojeIns());
  const anoAtual = Number(hoje.slice(0, 4));
  const entrada = document.getElementById('part-data-inicio').value || (c.atual || {}).data_inicio || '';
  const anoMin = entrada ? Number(entrada.slice(0, 4)) : anoAtual - 30;
  const anoSel = document.getElementById('part-cargo-ano');
  const atual = anoSel.value;
  let html = '<option value="">Ano</option>';
  for (let a = anoAtual; a >= anoMin; a--) html += `<option value="${a}">${a}</option>`;
  anoSel.innerHTML = html;
  if (atual && Number(atual) >= anoMin && Number(atual) <= anoAtual) anoSel.value = atual;
  atualizarMesesCargoIns(c);
}

function atualizarMesesCargoIns(c) {
  c = c || campanhaAtualIns;
  const hoje = (c && c.hoje) || hojeIns();
  const entrada = document.getElementById('part-data-inicio').value || '';
  const ano = document.getElementById('part-cargo-ano').value;
  const mesSel = document.getElementById('part-cargo-mes');
  const atual = mesSel.value;
  let html = '<option value="">Mês</option>';
  MESES_INS.forEach((m, i) => {
    const aaaaMm = ano + '-' + String(i + 1).padStart(2, '0');
    const fora = ano && (aaaaMm > hoje.slice(0, 7) || (entrada && aaaaMm < entrada.slice(0, 7)));
    if (!fora) html += `<option value="${i + 1}">${m}</option>`;
  });
  mesSel.innerHTML = html;
  if (atual && [...mesSel.options].some(o => o.value === atual)) mesSel.value = atual;
}

function alternarDesdeEntradaIns(marcado) {
  document.getElementById('part-cargo-quando').style.display = marcado ? 'none' : 'flex';
  limparErroIns('cargo_inicio');
  if (!marcado) opcoesMesAnoIns(campanhaAtualIns);
}

function limparErroIns(campo) {
  const bloco = document.querySelector(`[data-campo="${campo}"]`);
  if (bloco) bloco.classList.remove('com-erro');
  const msg = document.querySelector(`[data-erro="${campo}"]`);
  if (msg) msg.innerText = '';
}

function mostrarErroIns(campo, mensagem) {
  document.querySelectorAll('.campo-ins.com-erro').forEach(b => b.classList.remove('com-erro'));
  document.querySelectorAll('.erro-campo-ins').forEach(m => { m.innerText = ''; });
  const bloco = campo && document.querySelector(`[data-campo="${campo}"]`);
  const msg = campo && document.querySelector(`[data-erro="${campo}"]`);
  if (bloco && msg) {
    bloco.classList.add('com-erro');
    msg.innerText = mensagem;
    bloco.scrollIntoView({ behavior: 'smooth', block: 'center' });
    document.getElementById('part-erro').innerText = '';
  } else {
    document.getElementById('part-erro').innerText = mensagem;
  }
}

function abrirParticipacaoIns(c) {
  c = c || campanhaAtualIns;
  if (!c) return;
  campanhaAtualIns = c;
  fotoNovaIns = '';
  arquivoFotoIns = null;
  const a = c.atual || {};
  const req = Object.fromEntries((c.requisitos || []).map(r => [r.id, r.feito]));
  const [mesAniv, diaAniv] = (a.aniversario || '-').split('-');
  const opcoesDia = '<option value="">Dia</option>' + Array.from({ length: 31 }, (_, i) => i + 1)
    .map(d => `<option value="${d}" ${Number(diaAniv) === d ? 'selected' : ''}>${d}</option>`).join('');
  const opcoesMes = '<option value="">Mês</option>' + MESES_INS
    .map((m, i) => `<option value="${i + 1}" ${Number(mesAniv) === i + 1 ? 'selected' : ''}>${m}</option>`).join('');
  const hoje = c.hoje || hojeIns();
  const fotoAtual = a.tem_foto ? `<img src="/foto-usuario/${encodeURIComponent(c.usuario)}?t=${Date.now()}" alt="">` : ICONE_CAMERA_INS;
  const blocoHistorico = req.historico
    ? `<div class="campo-ins"><div class="pronto-ins">&#10003; Histórico na empresa já preenchido${a.cargo_atual ? ' · cargo atual: <b>' + escaparIns(a.cargo_atual) + '</b>' : ''}</div></div>`
    : `<div class="campo-ins" data-campo="cargo">
         <label for="part-cargo">Seu cargo atual <span class="opc">vira o primeiro item do seu histórico na empresa</span></label>
         <input type="text" id="part-cargo" maxlength="60" placeholder="Ex.: Analista de Suporte" value="${escaparIns(a.cargo_pda || '')}" oninput="limparErroIns('cargo')">
         <div class="area-ins" id="part-area">
           <button type="button" data-area="suporte" onclick="escolherAreaIns(this)">Suporte</button>
           <button type="button" data-area="monitoramento" onclick="escolherAreaIns(this)">Monitoramento</button>
           <button type="button" data-area="" class="ativa" onclick="escolherAreaIns(this)">Outra</button>
         </div>
         <div class="erro-campo-ins" data-erro="cargo"></div>
       </div>
       <div class="campo-ins" data-campo="cargo_inicio">
         <label class="opcao-check-ins">
           <input type="checkbox" id="part-cargo-desde-entrada" checked onchange="alternarDesdeEntradaIns(this.checked)">
           <span class="caixa-check-ins"></span>
           <span><b>Estou nesse cargo desde que entrei na empresa</b><span class="opc-linha">Desmarque se você mudou de cargo depois.</span></span>
         </label>
         <div class="linha-ins" id="part-cargo-quando" style="display:none">
           <div><span class="mini-rotulo-ins">Nesse cargo desde · mês</span><select id="part-cargo-mes" onchange="limparErroIns('cargo_inicio')"><option value="">Mês</option></select></div>
           <div><span class="mini-rotulo-ins">ano</span><select id="part-cargo-ano" onchange="atualizarMesesCargoIns(); limparErroIns('cargo_inicio')"><option value="">Ano</option></select></div>
         </div>
         <div class="erro-campo-ins" data-erro="cargo_inicio"></div>
       </div>`;
  abrirFundoIns(`
      <button class="fechar-ins" aria-label="Fechar" onclick="fecharIns(this)">${ICONE_X_INS}</button>
      <div class="corpo-ins form-ins">
        <span class="selo-ins" style="margin-top:6px">&#10024; Campanha PDA Beta User</span>
        <h2 style="margin-top:12px">Complete seu perfil</h2>
        <p>Preencha tudo e a insígnia é desbloqueada na hora.</p>
        <div class="campos-part-ins">
          <div class="campo-ins" data-campo="foto">
            <div class="foto-campo-ins">
              <button type="button" class="foto-prev-ins ${a.tem_foto ? 'tem' : ''}" id="part-foto-prev" onclick="document.getElementById('part-foto').click()" title="Escolher foto">${fotoAtual}</button>
              <div>
                <label>Foto de perfil</label>
                <div class="dica-ins" id="part-foto-dica">${a.tem_foto ? 'Você já tem foto. Quer trocar? Aceita JPG, PNG, WEBP ou GIF animado.' : 'JPG, PNG, WEBP ou GIF animado. Depois de escolher, você ajusta o tamanho e o enquadramento (o GIF entra inteiro).'}</div>
                <button type="button" class="btn-sec-ins" onclick="document.getElementById('part-foto').click()">${a.tem_foto ? 'Trocar foto' : 'Escolher foto'}</button>
                <button type="button" class="btn-sec-ins" id="part-foto-ajustar" style="display:none" onclick="ajustarFotoFormIns()">Ajustar</button>
              </div>
              <input type="file" id="part-foto" accept="image/jpeg,image/png,image/webp,image/gif" style="display:none" onchange="lerFotoIns(this)">
            </div>
            <div class="erro-campo-ins" data-erro="foto"></div>
          </div>
          <div class="campo-ins" data-campo="data_inicio">
            <label for="part-data-inicio">Quando você entrou na empresa?</label>
            <input type="date" id="part-data-inicio" max="${hoje}" min="1980-01-01" value="${escaparIns(a.data_inicio || '')}"
                   onchange="limparErroIns('data_inicio'); if (document.getElementById('part-cargo-ano')) opcoesMesAnoIns(campanhaAtualIns)">
            <div class="erro-campo-ins" data-erro="data_inicio"></div>
          </div>
          <div class="campo-ins" data-campo="aniversario">
            <label>Seu aniversário <span class="opc">só dia e mês</span></label>
            <div class="linha-ins"><select id="part-aniv-dia" onchange="limparErroIns('aniversario')">${opcoesDia}</select><select id="part-aniv-mes" onchange="limparErroIns('aniversario')">${opcoesMes}</select></div>
            <div class="erro-campo-ins" data-erro="aniversario"></div>
          </div>
          <div class="campo-ins" data-campo="email">
            <label for="part-email">Seu e-mail da Empresa</label>
            <input type="email" id="part-email" placeholder="contato80@example.com" value="${escaparIns(a.email || '')}" oninput="limparErroIns('email')">
            <div class="erro-campo-ins" data-erro="email"></div>
          </div>
          ${blocoHistorico}
        </div>
        <div class="erro-ins" id="part-erro"></div>
        <div class="botoes-ins">
          <button class="btn-ins" id="part-enviar" onclick="enviarParticipacaoIns()">${ICONE_ESTRELA_INS} Desbloquear minha insígnia</button>
          <button class="btn-depois-ins" onclick="adiarConviteIns(this)">Agora não</button>
        </div>
      </div>`, 'Participar da campanha PDA Beta User');
}

function escolherAreaIns(botao) {
  botao.parentElement.querySelectorAll('button').forEach(b => b.classList.toggle('ativa', b === botao));
}

function lerFotoIns(input) {
  const arquivo = input.files && input.files[0];
  input.value = '';
  if (!arquivo) return;
  arquivoFotoIns = arquivo;
  ajustarFotoFormIns();
}

function ajustarFotoFormIns() {
  if (!arquivoFotoIns) return;
  abrirRecorteFotoIns(arquivoFotoIns, dataUrl => {
    fotoNovaIns = dataUrl;
    const prev = document.getElementById('part-foto-prev');
    prev.classList.add('tem');
    prev.innerHTML = `<img src="${fotoNovaIns}" alt="">`;
    document.getElementById('part-foto-dica').innerText = 'Foto pronta. Ela vai pro seu perfil.';
    document.getElementById('part-foto-ajustar').style.display = '';
    limparErroIns('foto');
  }, msg => mostrarErroIns('foto', msg));
}

async function enviarParticipacaoIns() {
  const c = campanhaAtualIns;
  const botao = document.getElementById('part-enviar');
  const hoje = c.hoje || hojeIns();
  const campos = {
    data_inicio: document.getElementById('part-data-inicio').value,
    aniversario_dia: document.getElementById('part-aniv-dia').value,
    aniversario_mes: document.getElementById('part-aniv-mes').value,
    email: document.getElementById('part-email').value.trim(),
  };
  const cargo = document.getElementById('part-cargo');
  const desdeEntrada = document.getElementById('part-cargo-desde-entrada');
  if (cargo) {
    campos.cargo = cargo.value.trim();
    const area = document.querySelector('#part-area button.ativa');
    campos.area = area ? area.dataset.area : '';
    if (desdeEntrada.checked) {
      campos.cargo_desde_entrada = 'true';
    } else {
      const mes = document.getElementById('part-cargo-mes').value;
      const ano = document.getElementById('part-cargo-ano').value;
      campos.cargo_inicio = mes && ano ? ano + '-' + String(mes).padStart(2, '0') : '';
    }
  }
  // a mesma conferência do servidor, campo a campo, pra apontar o que falta
  if (!c.atual.tem_foto && !fotoNovaIns) return mostrarErroIns('foto', 'Escolha uma foto de perfil.');
  if (!campos.data_inicio) return mostrarErroIns('data_inicio', 'Informe o dia em que você entrou na empresa.');
  if (campos.data_inicio > hoje) return mostrarErroIns('data_inicio', 'A data de entrada não pode ser depois de hoje.');
  if (!campos.aniversario_dia || !campos.aniversario_mes) return mostrarErroIns('aniversario', 'Escolha o dia e o mês do seu aniversário.');
  if (!/@empresa[.]com[.]br$/i.test(campos.email)) return mostrarErroIns('email', 'Use seu e-mail da Empresa (termina com @example.com).');
  if (cargo && !campos.cargo) return mostrarErroIns('cargo', 'Informe seu cargo atual.');
  if (cargo && !desdeEntrada.checked && !campos.cargo_inicio) return mostrarErroIns('cargo_inicio', 'Escolha o mês e o ano em que você começou nesse cargo.');
  if (fotoNovaIns) campos.foto = fotoNovaIns;
  mostrarErroIns(null, '');
  botao.disabled = true;
  botao.innerHTML = 'Salvando...';
  try {
    const resp = await fetch('/api/insignias/participar', { method: 'POST', body: new URLSearchParams(campos) });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      mostrarErroIns(dados.campo, dados.erro || 'Não foi possível salvar.');
      botao.disabled = false;
      botao.innerHTML = ICONE_ESTRELA_INS + ' Desbloquear minha insígnia';
      return;
    }
    campanhaAtualIns = dados;
    avisarMudancaIns();
    if (dados.novas && dados.novas.length) abrirComemoracaoIns(dados, modoAtualIns);
    else document.querySelectorAll('.fundo-ins').forEach(f => f.remove());
  } catch (e) {
    mostrarErroIns(null, 'O servidor do PDA não respondeu. Confira sua conexão e tente de novo; se continuar, avise o time do PDA.');
    botao.disabled = false;
    botao.innerHTML = ICONE_ESTRELA_INS + ' Desbloquear minha insígnia';
  }
}

// ---- ajuste da foto: zoom, arrastar pra enquadrar no círculo, sai quadrada de 512 a 1024 px (3.3.1.0) ----
const LADO_RECORTE_INS = 280;
let recorteIns = null;

const TAMANHO_MAXIMO_FOTO_INS = 5 * 1024 * 1024;  // GIF: o mesmo limite do servidor (nucleo/fotos.py, 5 MB desde a 3.3.2.1)
function abrirRecorteFotoIns(arquivo, aoConfirmar, aoErro) {
  if (!/^image[/](jpeg|png|webp|gif)$/.test(arquivo.type)) { if (aoErro) aoErro('Escolha uma imagem JPG, PNG, WEBP ou GIF.'); return; }
  if (arquivo.type === 'image/gif') {
    // GIF (3.1.9.0): vai inteiro, sem recorte (recortar no navegador congelaria a animação); o círculo centraliza sozinho
    if (arquivo.size > TAMANHO_MAXIMO_FOTO_INS) { if (aoErro) aoErro('GIF muito grande: o máximo é 5 MB.'); return; }
    const leitorGif = new FileReader();
    leitorGif.onload = () => aoConfirmar(leitorGif.result);
    leitorGif.onerror = () => { if (aoErro) aoErro('Não deu pra ler esse GIF. Tente outro.'); };
    leitorGif.readAsDataURL(arquivo);
    return;
  }
  const leitor = new FileReader();
  leitor.onload = () => {
    const img = new Image();
    img.onload = () => montarRecorteIns(img, aoConfirmar);
    img.onerror = () => { if (aoErro) aoErro('Não deu pra ler essa imagem. Tente outra.'); };
    img.src = leitor.result;
  };
  leitor.readAsDataURL(arquivo);
}

function montarRecorteIns(img, aoConfirmar) {
  document.querySelectorAll('.fundo-recorte-ins').forEach(f => f.remove());
  const S = LADO_RECORTE_INS;
  const base = Math.max(S / img.width, S / img.height);
  recorteIns = { img, base, zoom: 1, ox: (S - img.width * base) / 2, oy: (S - img.height * base) / 2, aoConfirmar };
  const fundo = document.createElement('div');
  fundo.className = 'fundo-ins fundo-recorte-ins';
  fundo.innerHTML = `
    <div class="cartao-ins recorte-ins" role="dialog" aria-modal="true" aria-label="Ajustar foto">
      <div class="corpo-ins">
        <h2 style="margin-top:22px">Ajuste sua foto</h2>
        <p>Arraste pra enquadrar e use o zoom pra deixar do tamanho certo.</p>
        <p class="dica-gif-ins">Também aceita <b>GIF animado</b> (até 5 MB): ele entra inteiro, sem recorte, e fica centralizado no círculo.</p>
        <div class="palco-recorte-ins" id="palco-recorte">
          <canvas id="canvas-recorte" width="${S}" height="${S}"></canvas>
          <div class="mascara-recorte-ins"></div>
        </div>
        <div class="zoom-recorte-ins">
          <button type="button" class="btn-zoom-ins" onclick="mudarZoomIns(-0.15)" aria-label="Diminuir">&#8722;</button>
          <input type="range" id="zoom-recorte" min="1" max="4" step="0.01" value="1" oninput="definirZoomIns(Number(this.value))" aria-label="Zoom">
          <button type="button" class="btn-zoom-ins" onclick="mudarZoomIns(0.15)" aria-label="Aumentar">+</button>
        </div>
        <button type="button" class="btn-depois-ins" onclick="centralizarRecorteIns()">Centralizar</button>
        <div class="botoes-ins linha-botoes-ins">
          <button class="btn-sec-ins" onclick="this.closest('.fundo-recorte-ins').remove()">Cancelar</button>
          <button class="btn-ins" onclick="confirmarRecorteIns(this)">Usar esta foto</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(fundo);
  const canvas = document.getElementById('canvas-recorte');
  let arrasto = null;
  canvas.addEventListener('pointerdown', e => { arrasto = { x: e.clientX, y: e.clientY, ox: recorteIns.ox, oy: recorteIns.oy }; canvas.setPointerCapture(e.pointerId); });
  canvas.addEventListener('pointermove', e => {
    if (!arrasto) return;
    const escalaTela = S / canvas.getBoundingClientRect().width;
    recorteIns.ox = arrasto.ox + (e.clientX - arrasto.x) * escalaTela;
    recorteIns.oy = arrasto.oy + (e.clientY - arrasto.y) * escalaTela;
    desenharRecorteIns();
  });
  canvas.addEventListener('pointerup', () => { arrasto = null; });
  canvas.addEventListener('wheel', e => { e.preventDefault(); mudarZoomIns(e.deltaY < 0 ? 0.1 : -0.1); }, { passive: false });
  desenharRecorteIns();
}

function limitarRecorteIns() {
  const r = recorteIns, S = LADO_RECORTE_INS;
  const w = r.img.width * r.base * r.zoom, h = r.img.height * r.base * r.zoom;
  r.ox = Math.min(0, Math.max(S - w, r.ox));
  r.oy = Math.min(0, Math.max(S - h, r.oy));
}

function desenharRecorteIns() {
  const r = recorteIns, S = LADO_RECORTE_INS;
  limitarRecorteIns();
  const ctx = document.getElementById('canvas-recorte').getContext('2d');
  ctx.clearRect(0, 0, S, S);
  ctx.drawImage(r.img, r.ox, r.oy, r.img.width * r.base * r.zoom, r.img.height * r.base * r.zoom);
}

function definirZoomIns(z) {
  const r = recorteIns, S = LADO_RECORTE_INS;
  z = Math.min(4, Math.max(1, z));
  // mantém o centro da área visível no lugar ao mudar o zoom
  const cx = (S / 2 - r.ox) / (r.base * r.zoom), cy = (S / 2 - r.oy) / (r.base * r.zoom);
  r.zoom = z;
  r.ox = S / 2 - cx * r.base * z;
  r.oy = S / 2 - cy * r.base * z;
  document.getElementById('zoom-recorte').value = z;
  desenharRecorteIns();
}
function mudarZoomIns(passo) { definirZoomIns(recorteIns.zoom + passo); }
function centralizarRecorteIns() {
  const r = recorteIns, S = LADO_RECORTE_INS;
  r.ox = (S - r.img.width * r.base * r.zoom) / 2;
  r.oy = (S - r.img.height * r.base * r.zoom) / 2;
  desenharRecorteIns();
}

function confirmarRecorteIns(botao) {
  // 3.3.1.0: sai na maior resolução que a foto original dá pro pedaço escolhido (entre 512 e 1024 px), com
  // suavização de alta qualidade e JPEG 92%; antes era sempre 512 px a 90%, e foto boa ficava borrada na foto ampliada
  const r = recorteIns, S = LADO_RECORTE_INS;
  const ladoNaOrigem = S / (r.base * r.zoom);
  const SAIDA = Math.round(Math.min(1024, Math.max(512, ladoNaOrigem))), k = SAIDA / S;
  const canvas = document.createElement('canvas');
  canvas.width = SAIDA;
  canvas.height = SAIDA;
  const ctx = canvas.getContext('2d');
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.fillStyle = '#ffffff';  // PNG transparente não fica preto no JPEG
  ctx.fillRect(0, 0, SAIDA, SAIDA);
  ctx.drawImage(r.img, r.ox * k, r.oy * k, r.img.width * r.base * r.zoom * k, r.img.height * r.base * r.zoom * k);
  const dataUrl = canvas.toDataURL('image/jpeg', 0.92);
  botao.closest('.fundo-recorte-ins').remove();
  r.aoConfirmar(dataUrl);
}

// ---- comemoração com "destacar agora?" ----
function abrirComemoracaoIns(c, modo) {
  campanhaAtualIns = c;
  const novas = c.novas;
  const cores = ['#2db8cf', '#b0cb1c', '#e8a33d', '#b389f9', '#ff8fa3', '#4ec9b0'];
  let confete = '';
  for (let i = 0; i < 26; i++) {
    confete += `<span class="confete-ins" style="left:${(i * 37) % 100}%;background:${cores[i % 6]};animation-delay:-${((i * 0.37) % 2.4).toFixed(2)}s;animation-duration:${(2.2 + (i % 5) * 0.3).toFixed(1)}s"></span>`;
  }
  const tamanho = novas.length === 1 ? 140 : (novas.length === 2 ? 110 : 92);
  const sugerida = (novas.find(n => n.id === 'beta_user') || novas[0]).id;
  const titulo = novas.length === 1
    ? (novas[0].id === 'beta_user' ? `Parabéns, ${escaparIns(c.primeiro_nome)}!<br>Você é <span>PDA Beta User</span>`
                                   : `Parabéns, ${escaparIns(c.primeiro_nome)}!<br>Nova insígnia: <span>${escaparIns(novas[0].nome)}</span>`)
    : `Parabéns, ${escaparIns(c.primeiro_nome)}!<br>Você ganhou <span>${novas.length} insígnias</span>`;
  const fundo = abrirFundoIns(`
      <button class="fechar-ins" aria-label="Fechar" onclick="concluirComemoracaoIns(this)">${ICONE_X_INS}</button>
      <div class="topo-ins">${confete}
        <span class="selo-ins">&#127881; ${novas.length === 1 ? 'Insígnia desbloqueada' : 'Insígnias desbloqueadas'}</span>
        <div class="palco-ins"><div class="aura"></div>${novas.map(n => `<button type="button" class="item-ins escolha-ins ${n.id === sugerida ? 'selecionada' : ''}" data-id="${escaparIns(n.id)}"
            title="${escaparIns(n.nome)}" ${novas.length > 1 ? 'onclick="escolherDestaqueIns(this)"' : ''}>${svgInsignia(n, tamanho, true)}</button>`).join('')}</div>
        ${novas.length > 1 ? '<div class="nomes-novas-ins">' + novas.map(n => '<span>' + escaparIns(n.nome) + '</span>').join('') + '</div>' : ''}
      </div>
      <div class="corpo-ins" id="corpo-comemoracao-ins">
        <h2>${titulo}</h2>
        <p>${novas.length === 1 ? escaparIns(textoNovaIns(novas[0])) : 'Elas já aparecem no seu perfil, à vista de todo mundo.'}</p>
        <div class="pergunta-destaque-ins">
          <div class="t">Quer destacar ${novas.length === 1 ? 'essa insígnia' : 'uma delas'} agora?</div>
          <div class="d">A insígnia em destaque aparece junto da sua foto no perfil.${novas.length > 1 ? ' Toque numa delas pra escolher.' : ''}</div>
        </div>
        <div class="botoes-ins">
          <button class="btn-ins" onclick="destacarIns(this)">${ICONE_ESTRELA_INS} Destacar agora</button>
          <button class="btn-depois-ins" onclick="concluirComemoracaoIns(this)">Agora não</button>
        </div>
      </div>`, 'Insígnia desbloqueada');
  fundo.dataset.ids = novas.map(n => n.id).join(',');
  fundo.dataset.modo = modo;
}

function escolherDestaqueIns(botao) {
  botao.closest('.palco-ins').querySelectorAll('.escolha-ins').forEach(b => b.classList.toggle('selecionada', b === botao));
}

async function destacarIns(botao) {
  const fundo = botao.closest('.fundo-ins');
  const escolhida = fundo.querySelector('.escolha-ins.selecionada') || fundo.querySelector('.escolha-ins');
  const id = escolhida ? escolhida.dataset.id : '';
  const nome = escolhida ? escolhida.title : '';
  botao.disabled = true;
  marcarVistasIns(fundo.dataset.ids);
  try {
    const dados = await (await fetch('/api/insignias/destaque', { method: 'POST', body: new URLSearchParams({ id }) })).json();
    if (!dados.ok) throw new Error(dados.erro || 'não foi possível destacar');
    avisarMudancaIns();
    const usuario = (campanhaAtualIns || {}).usuario || '';
    document.getElementById('corpo-comemoracao-ins').innerHTML = `
      <h2>Pronto! <span>${escaparIns(nome)}</span><br>em destaque</h2>
      <p>Ela aparece junto da sua foto no perfil. Dá pra trocar quando quiser, na seção Insígnias do seu perfil.</p>
      <div class="botoes-ins" style="margin-top:18px">
        ${fundo.dataset.modo === 'hub' ? `<a class="btn-ins" href="/perfil/${encodeURIComponent(usuario)}#insignias">Ver no meu perfil</a>` : ''}
        <button class="${fundo.dataset.modo === 'hub' ? 'btn-depois-ins' : 'btn-ins'}" onclick="fecharIns(this)">Fechar</button>
      </div>`;
  } catch (e) {
    botao.disabled = false;
    botao.insertAdjacentHTML('afterend', '<div class="erro-ins">' + escaparIns(e.message || e) + '</div>');
  }
}

function textoNovaIns(n) {
  if (n.id === 'beta_user') return 'Seu perfil está completo e a insígnia já aparece nele. Obrigado por usar o PDA desde o começo.';
  if (n.tipo === 'fundador') return 'Pra quem criou e desenvolve o PDA. Ela aparece no seu perfil, à vista de todo mundo.';
  if (n.tipo === 'contribuidor') return 'Pra quem contribuiu com o desenvolvimento do PDA. Obrigado! Ela aparece no seu perfil.';
  if (n.tipo === 'rank') return 'Você tem ' + n.produtos + (n.produtos === 1 ? ' produto' : ' produtos') + ' no Rank Master, nos Rankings. Ela aparece no seu perfil.';
  if (n.tipo === 'palmas') return 'Você recebeu ' + (n.palmas >= 1000 ? (n.palmas / 1000) + 'k' : n.palmas) + ' palminhas dos colegas no mural. Ela muda a cada meta e aparece no seu perfil.';
  if (n.tipo === 'bug') return 'Você achou e reportou um bug no PDA. Valeu por deixar o painel melhor! Ela aparece no seu perfil.';
  if (n.tipo === 'tempo' && n.nivel === 'ferro') return n.meses + (n.meses === 1 ? ' mês' : ' meses') + ' de empresa, nível Ferro. Ela ganha um número novo a cada mês e vira Bronze com 1 ano.';
  if (n.tipo === 'tempo') return n.anos + (n.anos === 1 ? ' ano' : ' anos') + ' de empresa, nível ' + n.nivel_nome + '. A insígnia muda de cor a cada ano completo.';
  return 'Ela já aparece no seu perfil.';
}

function marcarVistasIns(ids) {
  try {
    const corpo = new URLSearchParams({ ids: ids || '' });
    if (navigator.sendBeacon) navigator.sendBeacon('/api/insignias/vista', corpo);
    else fetch('/api/insignias/vista', { method: 'POST', body: corpo, keepalive: true });
  } catch (e) { /* tenta de novo no próximo acesso */ }
}

function concluirComemoracaoIns(el) {
  const fundo = el.closest('.fundo-ins');
  if (fundo) marcarVistasIns(fundo.dataset.ids);
  fecharIns(el);
}

// modo 'hub': convite (uma vez por dia) ou comemoração; modo 'perfil': só a comemoração
async function verificarCampanhaInsignias(modo) {
  modoAtualIns = modo;
  try {
    const resp = await fetch('/api/insignias/campanha');
    if (!resp.ok) return;
    const c = await resp.json();
    campanhaAtualIns = c;
    if (!c.ok || document.querySelector('.fundo-ins')) return;
    if (c.novas && c.novas.length) { abrirComemoracaoIns(c, modo); return; }
    if (modo !== 'hub' || !c.convite_beta) return;
    let adiado = null;
    try { adiado = localStorage.getItem(CHAVE_ADIADO_INS); } catch (e) { adiado = null; }
    if (adiado === hojeIns()) return;
    abrirConviteBetaIns(c);
  } catch (e) { /* campanha é opcional: erro aqui nunca atrapalha a tela */ }
}

// pro botão "Participar" do perfil: busca o que já está preenchido e abre o formulário
async function abrirParticipacaoDoPerfilIns() {
  modoAtualIns = 'perfil';
  try {
    const c = await (await fetch('/api/insignias/campanha')).json();
    if (c.ok) abrirParticipacaoIns(c);
  } catch (e) { /* sem rede: o botão não faz nada */ }
}

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  const fundo = document.querySelector('.fundo-ins');
  if (!fundo) return;
  const fechar = fundo.querySelector('.fechar-ins');
  if (fechar) fechar.click();
});
</script>
"""
