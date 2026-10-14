"""Tela Changelog.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_CHANGELOG_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Changelog do PDA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-changelog { text-align: center; max-width: 720px; margin: 10px auto 30px auto; }
  .historico { margin-top: 6px; }
  /* data de criação e acessos (3.0.3.0) */
  .marcos-pda { display: flex; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
  .marco-pda { font-size: 12px; color: var(--fg-dim); padding: 5px 12px; border-radius: 999px; border: 1px solid var(--border); background: rgba(var(--tinta),.03); }
  .marco-pda b { color: var(--fg); }
  .cabecalho-changelog h1 { font-size: 26px; margin: 0 0 8px 0;
                             background: var(--gradiente-marca); -webkit-background-clip: text;
                             background-clip: text; color: transparent; }
  .cabecalho-changelog .sub { color: var(--fg-dim); font-size: 13.5px; line-height: 1.6; }

  /* Linha do tempo: cada versão tem uma calha à esquerda (--calha). O ponto fica
     centralizado no eixo da calha (--eixo) e na altura do selo de versão (--altura-no:
     padding do card + metade da linha do selo). A linha é feita de segmentos que ligam
     um ponto ao próximo (::after em cada entrada menos a última) - começa e termina
     nos pontos, nunca sobra traço, e acompanha qualquer altura de card. Tudo sai das
     mesmas variáveis, então ponto e linha não desalinham. */
  .linha-tempo { --calha: 36px; --eixo: 13px; --no: 14px; --espaco: 16px; --pad-card: 20px; --altura-no: 31px;
                  max-width: 760px; margin: 18px 0 6px 0; display: flex; flex-direction: column; gap: var(--espaco); }
  .entrada-changelog { position: relative; margin-left: var(--calha); background: var(--bg-panel);
                        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px); border: 1px solid var(--border);
                        border-radius: 14px; padding: var(--pad-card) 24px; }
  .entrada-changelog::before { content: ""; position: absolute; box-sizing: border-box; width: var(--no); height: var(--no);
                                left: calc(var(--eixo) - var(--calha) - var(--no) / 2 - 1px); /* -1px: borda do card */
                                top: calc(var(--altura-no) - var(--no) / 2);
                                border-radius: 50%; background: var(--bg); border: 2px solid rgba(45,184,207,.75); z-index: 1; }
  .entrada-changelog:not(:last-child)::after { content: ""; position: absolute; width: 2px; border-radius: 1px;
                                left: calc(var(--eixo) - var(--calha) - 1px - 1px);
                                top: calc(var(--altura-no) + var(--no) / 2 + 3px);
                                bottom: calc(-1 * (var(--espaco) + var(--altura-no) + 2px) + var(--no) / 2 + 3px); /* 2px: bordas dos dois cards */
                                background: rgba(45,184,207,.35); }
  .entrada-changelog.atual { border-color: rgba(45,184,207,.45); }
  .entrada-changelog.atual::before { background: var(--gradiente-marca); border: 0;
                                      box-shadow: 0 0 0 4px rgba(45,184,207,.18), 0 0 14px rgba(45,184,207,.55); }
  @media (max-width: 640px) {
    .linha-tempo { --calha: 26px; --eixo: 9px; --no: 12px; }
    .entrada-changelog { padding: var(--pad-card) 18px; }
  }
  .topo-entrada { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
  .chip-versao-changelog { font-weight: 700; font-size: 12px; color: var(--fg); padding: 3px 10px; border-radius: 999px;
                            border: 1px solid transparent;
                            background-image: linear-gradient(var(--bg-panel), var(--bg-panel)), var(--gradiente-marca);
                            background-origin: border-box; background-clip: padding-box, border-box; }
  .data-entrada { font-size: 12px; color: var(--fg-dim); }
  .selo-atual { font-size: 10.5px; font-weight: 700; color: var(--teal); text-transform: uppercase; letter-spacing: .05em; }
  .entrada-changelog h3 { margin: 0 0 8px 0; font-size: 15px; color: var(--fg); }
  .entrada-changelog ul { margin: 0; padding: 0; list-style: none; color: var(--fg); font-size: 13.5px; line-height: 1.6; }
  .entrada-changelog li { display: flex; align-items: baseline; gap: 10px; padding: 3px 0; }
  /* etiqueta de categoria (Novo / Melhoria / Correção / Removido) antes de cada item */
  .tag-categoria { flex-shrink: 0; min-width: 84px; text-align: center; font-size: 10px; font-weight: 700;
                    text-transform: uppercase; letter-spacing: .04em; padding: 2px 8px; border-radius: 6px;
                    color: var(--cor-cat); background: color-mix(in srgb, var(--cor-cat) 15%, transparent);
                    border: 1px solid color-mix(in srgb, var(--cor-cat) 35%, transparent); }
  /* ---------- atalhos do topo ---------- */
  .atalhos-changelog { display: inline-flex; gap: 6px; margin-top: 16px; padding: 4px; border-radius: 999px;
                        background: rgba(var(--tinta),.04); border: 1px solid var(--border); }
  .atalhos-changelog a { font-size: 12px; font-weight: 600; color: var(--fg-dim); text-decoration: none; padding: 6px 14px; border-radius: 999px;
                          display: inline-block; white-space: nowrap; line-height: 1.3; }
  .atalhos-changelog a:hover { color: var(--fg); background: rgba(var(--tinta),.06); }
  .atalhos-changelog a::before { content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%;
                                  background: var(--cor-era); margin-right: 7px; vertical-align: 1px; }
  html { scroll-behavior: smooth; }
  .era-historico { scroll-margin-top: 80px; }

  /* "Ver detalhamento" (3.0.0.0): as versões da era, dentro do card dela */
  .detalhe-era { position: relative; margin-top: 22px; border-top: 1px dashed color-mix(in srgb, var(--cor-era) 35%, transparent); padding-top: 18px; }
  .detalhe-era summary { list-style: none; cursor: pointer; display: inline-flex; align-items: center; gap: 10px; flex-wrap: wrap;
                          font-size: 13px; font-weight: 700; color: var(--cor-era); padding: 8px 16px; border-radius: 999px;
                          border: 1px solid color-mix(in srgb, var(--cor-era) 45%, transparent);
                          background: color-mix(in srgb, var(--cor-era) 10%, transparent); transition: background .15s; }
  .detalhe-era summary::-webkit-details-marker { display: none; }
  .detalhe-era summary::before { content: "▸"; transition: transform .2s; display: inline-block; }
  .detalhe-era[open] summary::before { transform: rotate(90deg); }
  .detalhe-era summary:hover { background: color-mix(in srgb, var(--cor-era) 18%, transparent); }
  .detalhe-era summary .qtd-detalhe { font-weight: 600; color: var(--fg-dim); font-size: 12px; }
  .detalhe-era .texto-aberto, .detalhe-era[open] .texto-fechado { display: none; }
  .detalhe-era[open] .texto-aberto { display: inline; }
  .detalhe-era .entrada-changelog { background: rgba(var(--poco),.22); }
  .aviso-detalhe { font-size: 12px; color: var(--fg-dim); margin: 14px 0 0 0; }

  /* ---------- histórico: outra cara, de arquivo ---------- */
  .divisor-historico { max-width: 920px; margin: 64px auto 26px auto; display: flex; align-items: center; gap: 16px;
                        color: var(--fg-dim); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .14em; }
  .divisor-historico::before, .divisor-historico::after { content: ""; flex: 1; height: 1px;
                        background: repeating-linear-gradient(90deg, rgba(var(--tinta),.25) 0 6px, transparent 6px 12px); }
  .historico { max-width: 920px; margin: 0 auto 30px auto; display: flex; flex-direction: column; gap: 26px; }
  .cab-historico { text-align: center; max-width: 640px; margin: 0 auto 4px auto; }
  .olho-historico { display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: .18em; text-transform: uppercase;
                     color: #e8a33d; padding: 4px 12px; border-radius: 999px; border: 1px solid rgba(232,163,61,.4);
                     background: rgba(232,163,61,.08); margin-bottom: 12px; }
  .cab-historico h2 { font-size: 28px; margin: 0 0 10px 0; color: var(--fg); letter-spacing: -.01em; }
  .cab-historico p { color: var(--fg-dim); font-size: 13.5px; line-height: 1.65; margin: 0; }

  .era-historico { position: relative; overflow: hidden; border-radius: 22px; padding: 30px 32px 28px 32px;
                    border: 1px solid color-mix(in srgb, var(--cor-era) 32%, transparent);
                    background:
                      radial-gradient(120% 90% at 100% 0%, color-mix(in srgb, var(--cor-era) 16%, transparent) 0%, transparent 55%),
                      var(--bg-panel); }
  /* marca d'água gigante com a versão, no canto */
  .era-historico::before { content: attr(data-marca); position: absolute; right: -10px; top: -46px; font-size: 220px; font-weight: 900;
                            line-height: 1; letter-spacing: -.06em; color: var(--cor-era); opacity: .07; pointer-events: none; }
  .cab-era { position: relative; display: flex; align-items: center; gap: 18px; flex-wrap: wrap; }
  .num-era { font-size: 46px; font-weight: 900; line-height: 1; letter-spacing: -.03em;
             background: linear-gradient(135deg, var(--cor-era), color-mix(in srgb, var(--cor-era) 45%, var(--fg)));
             -webkit-background-clip: text; background-clip: text; color: transparent; }
  .nome-era { font-size: 20px; font-weight: 800; color: var(--fg); }
  .selos-era { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
  .selo-era { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; color: var(--cor-era);
              background: color-mix(in srgb, var(--cor-era) 13%, transparent); border: 1px solid color-mix(in srgb, var(--cor-era) 35%, transparent); }
  .selo-era.neutro { color: var(--fg-dim); background: rgba(var(--tinta),.05); border-color: var(--border); }
  .resumo-era { position: relative; color: var(--fg); font-size: 14px; line-height: 1.7; margin: 16px 0 0 0; max-width: 700px; opacity: .92; }

  /* trilha em grade (uma coluna por etapa), com a seta desenhada entre uma etapa e a próxima */
  .jornada-historico { position: relative; display: grid; grid-template-columns: repeat(var(--passos, 4), minmax(0, 1fr)); gap: 26px; margin-top: 20px; }
  .passo-jornada { position: relative; display: flex; gap: 10px; align-items: center; padding: 10px 12px; border-radius: 12px;
                   background: rgba(var(--poco),.2); border: 1px dashed color-mix(in srgb, var(--cor-era) 40%, transparent); }
  .passo-jornada.destino { border: 1px solid rgba(45,184,207,.55); background: rgba(45,184,207,.08); }
  .num-passo { width: 24px; height: 24px; border-radius: 50%; display: grid; place-items: center; flex-shrink: 0; font-size: 11px; font-weight: 800;
               color: #0b0f14; background: var(--cor-era); }
  .passo-jornada.destino .num-passo { background: var(--gradiente-marca); }
  .titulo-passo { font-size: 12.5px; font-weight: 700; color: var(--fg); }
  .detalhe-passo { font-size: 11px; color: var(--fg-dim); }
  .passo-jornada:not(:last-child)::after { content: "→"; position: absolute; right: -19px; top: 50%; transform: translateY(-50%);
                                            color: color-mix(in srgb, var(--cor-era) 70%, var(--fg-dim)); font-weight: 700; font-size: 14px; }
  @media (max-width: 860px) {
    .jornada-historico { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .passo-jornada:not(:last-child)::after { display: none; }
  }

  .grupos-historico { position: relative; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin-top: 22px; }
  /* número ímpar de grupos: o último ocupa a linha toda, sem card sozinho pela metade */
  .grupo-historico:last-child:nth-child(odd) { grid-column: 1 / -1; }
  .grupo-historico:last-child:nth-child(odd) ul { columns: 2; column-gap: 28px; }
  .grupo-historico li { break-inside: avoid; }
  .grupo-historico { padding: 16px 18px; border-radius: 14px; background: rgba(var(--poco),.22); border: 1px solid var(--border);
                      transition: border-color .15s, transform .15s; }
  .grupo-historico:hover { border-color: color-mix(in srgb, var(--cor-era) 45%, transparent); transform: translateY(-2px); }
  .titulo-grupo-historico { display: flex; align-items: center; gap: 10px; font-size: 13.5px; font-weight: 700; color: var(--fg); margin-bottom: 10px; }
  .icone-grupo-historico { width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; flex-shrink: 0;
                            color: var(--cor-era); background: color-mix(in srgb, var(--cor-era) 14%, transparent); }
  .icone-grupo-historico svg { width: 17px; height: 17px; }
  .grupo-historico ul { margin: 0; padding: 0; list-style: none; }
  .grupo-historico li { position: relative; padding: 4px 0 4px 16px; font-size: 12.8px; line-height: 1.55; color: var(--fg); opacity: .9; }
  .grupo-historico li::before { content: ""; position: absolute; left: 2px; top: 11px; width: 6px; height: 6px; border-radius: 50%;
                                 background: var(--cor-era); opacity: .8; }
  .fim-historico { text-align: center; font-size: 11px; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--fg-dim);
                    padding-top: 6px; }
  .fim-historico::before { content: ""; display: block; width: 10px; height: 10px; border-radius: 50%; margin: 0 auto 10px auto;
                            background: #e8a33d; box-shadow: 0 0 0 4px rgba(232,163,61,.18); }
  @media (max-width: 640px) {
    .era-historico { padding: 22px 18px; }
    .era-historico::before { font-size: 150px; top: -30px; }
    .num-era { font-size: 36px; }
    .cab-historico h2 { font-size: 23px; }
    .grupos-historico { grid-template-columns: 1fr; }
    .grupo-historico:last-child:nth-child(odd) ul { columns: 1; }
  }
  /* lembrança de cada era (3.3.1.0): o print da época e um texto nostálgico */
  .lembranca-era { position: relative; display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); gap: 18px; align-items: center;
                   margin: 18px 0 4px; padding: 14px; border-radius: 16px; border: 1px solid color-mix(in srgb, var(--cor-era) 35%, transparent);
                   background: linear-gradient(135deg, color-mix(in srgb, var(--cor-era) 10%, transparent), transparent 70%); }
  .foto-lembranca { position: relative; display: block; padding: 0; border: none; background: none; cursor: zoom-in; border-radius: 12px; overflow: hidden;
                    box-shadow: 0 12px 30px rgba(0,0,0,.35); transform: rotate(-1deg); transition: transform .25s ease; }
  .foto-lembranca:hover, .foto-lembranca:focus-visible { transform: rotate(0deg) scale(1.01); outline: none; }
  .foto-lembranca img { display: block; width: 100%; filter: saturate(.9) sepia(.12); transition: filter .25s ease; }
  .foto-lembranca:hover img { filter: none; }
  .legenda-lembranca { position: absolute; left: 10px; bottom: 10px; font-size: 11px; font-weight: 800; color: #fff; background: rgba(0,0,0,.6);
                       border-radius: 99px; padding: 3px 10px; letter-spacing: .02em; }
  .rotulo-lembranca { font-size: 11px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; color: var(--cor-era); margin-bottom: 6px; }
  .texto-lembranca p { margin: 0; font-size: 14px; line-height: 1.7; color: var(--fg); font-style: italic; opacity: .92; }
  .fundo-lembranca { position: fixed; inset: 0; z-index: 460; background: rgba(0,0,0,.88); display: flex; align-items: center; justify-content: center;
                     padding: 40px; box-sizing: border-box; cursor: zoom-out; }
  .fundo-lembranca img { max-width: 100%; max-height: 100%; border-radius: 10px; box-shadow: 0 20px 60px rgba(0,0,0,.6); }
  .fundo-lembranca span { position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,.85); font-size: 13px; }
  @media (max-width: 760px) { .lembranca-era { grid-template-columns: minmax(0, 1fr); } }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-changelog">
      <h1>Changelog</h1>
      <div class="sub">O PDA por era: cada versão grande resumida por tema e, na v3.x e na v2.x, o detalhamento
        de cada versão, separado por tipo de mudança.</div>
      <div class="marcos-pda">__MARCOS_PDA__</div>
      <nav class="atalhos-changelog">
        __ATALHOS_ERAS__
      </nav>
    </div>

    <!-- Eras (3.0.0.0): v3.x, v2.x e v1.x, com o detalhamento por versão dentro de cada uma -->
    <div class="historico" id="historico">
      __HISTORICO_PDA__
      <div class="fim-historico">Início do PDA</div>
    </div>
  </div>

  __FOOTER__
<script>
// print da era ampliado na própria página (3.3.1.0): fecha clicando ou no Esc
function ampliarLembranca(botao) {
  const img = botao.querySelector('img');
  const fundo = document.createElement('div');
  fundo.className = 'fundo-lembranca';
  fundo.setAttribute('role', 'dialog');
  fundo.setAttribute('aria-label', img.alt);
  fundo.innerHTML = '<img alt=""><span></span>';
  fundo.querySelector('img').src = img.src;
  fundo.querySelector('span').textContent = img.alt;
  const fechar = () => { fundo.remove(); document.removeEventListener('keydown', teclas); botao.focus(); };
  const teclas = e => { if (e.key === 'Escape') fechar(); };
  fundo.addEventListener('click', fechar);
  document.addEventListener('keydown', teclas);
  document.body.appendChild(fundo);
}
</script>
</body>
</html>
"""
