"""Central de Monitores (HTML feito pelo Wagner Faria, adaptado).

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_DIRECIONAMENTO_WEBMONITORS_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Central de Monitores · Empresa eDocs</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<script>
  (function(){
    try {
      // mesma escolha do resto do PDA; escuro é o padrão (não segue o sistema operacional)
      var t = localStorage.getItem('pda-tema') === 'claro' ? 'light' : 'dark';
      if (!t) t = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', t);
    } catch(e) { document.documentElement.setAttribute('data-theme','dark'); }
  })();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@500;600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --turquoise: oklch(0.7 0.13 205);
    --turquoise-strong: oklch(0.6 0.14 205);
    --lime: oklch(0.83 0.19 120);
    --font-head: 'Sora', sans-serif;
    --font-body: 'DM Sans', sans-serif;
    box-sizing: border-box;
  }

  * { box-sizing: inherit; margin: 0; padding: 0; }

  :root[data-theme="light"] {
    --bg-0: oklch(0.97 0.01 210);
    --bg-1: oklch(0.94 0.02 205);
    --bg-2: oklch(0.99 0.01 100);
    --surface: oklch(0.99 0.005 210 / 0.62);
    --surface-strong: oklch(0.99 0.005 210 / 0.85);
    --border: oklch(0.7 0.05 205 / 0.28);
    --text-0: oklch(0.22 0.03 240);
    --text-1: oklch(0.4 0.03 240);
    --text-2: oklch(0.55 0.02 240);
    --shadow: oklch(0.5 0.1 205 / 0.14);
    --glow: oklch(0.7 0.13 205 / 0.22);
  }

  :root[data-theme="dark"] {
    --bg-0: oklch(0.16 0.025 240);
    --bg-1: oklch(0.13 0.03 250);
    --bg-2: oklch(0.2 0.03 220);
    --surface: oklch(0.27 0.03 235 / 0.55);
    --surface-strong: oklch(0.3 0.03 235 / 0.75);
    --border: oklch(0.65 0.08 205 / 0.22);
    --text-0: oklch(0.96 0.01 210);
    --text-1: oklch(0.85 0.02 210);
    --text-2: oklch(0.68 0.02 220);
    --shadow: oklch(0.1 0.02 240 / 0.45);
    --glow: oklch(0.7 0.13 205 / 0.28);
  }

  html, body {
    min-height: 100%;
    background:
      radial-gradient(1100px 620px at 12% -10%, var(--glow), transparent 60%),
      radial-gradient(900px 560px at 100% 0%, oklch(0.83 0.19 120 / 0.14), transparent 55%),
      var(--bg-0);
    background-attachment: fixed;
    color: var(--text-0);
    font-family: var(--font-body);
    -webkit-font-smoothing: antialiased;
  }

  body {
    padding-top: env(safe-area-inset-top, 0px);
    padding-bottom: env(safe-area-inset-bottom, 0px);
  }

  h1, h2, h3, .font-head { font-family: var(--font-head); }

  /* monitor grande: mesma régua de ampliação do resto do PDA */
  @media (min-width: 2300px) and (min-height: 1100px) { .wrap { zoom: 1.2; } }
  @media (min-width: 3200px) and (min-height: 1700px) { .wrap { zoom: 1.6; } }

  .wrap {
    max-width: 1180px;
    margin: 0 auto;
    padding: 28px 24px 80px;
  }

  /* ---------- Header ---------- */
  header.top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 24px;
    padding-bottom: 28px;
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .brand-mark {
    width: 46px;
    height: 46px;
    border-radius: 13px;
    display: grid;
    place-items: center;
    background: var(--bg-2);
    border: 1px solid var(--border);
    box-shadow: 0 6px 20px var(--shadow);
    flex-shrink: 0;
    padding: 6px;
  }

  .brand-mark img { width: 100%; height: 100%; object-fit: contain; }

  .brand-name {
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 0.82rem;
    letter-spacing: 0.04em;
    color: var(--text-2);
  }

  h1.title {
    font-size: clamp(1.5rem, 2.6vw, 2.1rem);
    font-weight: 700;
    line-height: 1.15;
    margin-top: 2px;
  }

  .subtitle {
    color: var(--text-2);
    font-size: 0.96rem;
    margin-top: 6px;
    max-width: 46ch;
  }

  .top-right {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .stats {
    display: flex;
    gap: 10px;
  }

  .stat-pill {
    background: var(--surface);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 8px 16px;
    text-align: center;
    min-width: 84px;
  }

  .stat-pill .num {
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 1.25rem;
    color: var(--turquoise-strong);
  }

  :root[data-theme="dark"] .stat-pill .num { color: oklch(0.78 0.13 205); }

  .stat-pill .lbl {
    font-size: 0.68rem;
    color: var(--text-2);
    margin-top: 1px;
  }

  .theme-toggle {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: var(--surface);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    display: grid;
    place-items: center;
    cursor: pointer;
    color: var(--text-1);
    flex-shrink: 0;
    transition: transform 0.15s ease, border-color 0.15s ease;
  }
  /* botão de voltar pro hub do PDA (mesmo visual dos botões do canto direito) */
  .back-btn {
    height: 42px;
    padding: 0 14px 0 10px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: var(--surface);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
    color: var(--text-1);
    text-decoration: none;
    font-family: var(--font-head);
    font-size: 0.85rem;
    font-weight: 600;
    transition: transform 0.15s ease, border-color 0.15s ease, color 0.15s ease;
  }
  .back-btn:hover { border-color: var(--turquoise); color: var(--text-0); }
  .back-btn:active { transform: scale(0.95); }
  .back-btn svg { width: 18px; height: 18px; }

  .theme-toggle:hover { border-color: var(--turquoise); }
  .theme-toggle:active { transform: scale(0.93); }
  .theme-toggle svg { width: 19px; height: 19px; }
  .theme-toggle .sun { display: none; }
  :root[data-theme="dark"] .theme-toggle .sun { display: block; }
  :root[data-theme="dark"] .theme-toggle .moon { display: none; }

  /* ---------- Controls ---------- */
  .controls {
    position: sticky;
    top: 12px;
    z-index: 30;
    background: var(--surface-strong);
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 10px 30px var(--shadow);
    margin-bottom: 30px;
  }

  .search-row {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  /* visão Monitores x Infraestrutura (2.35.3.0): a infraestrutura (RabbitMQ, Graylog,
     FTP, servidores) saiu de dentro dos cards de monitores e ganhou visão própria */
  .modo-toggle {
    display: inline-flex;
    padding: 4px;
    gap: 4px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: var(--bg-2);
    flex-shrink: 0;
  }
  :root[data-theme="dark"] .modo-toggle { background: oklch(0.19 0.025 235); }
  .modo-btn {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border: none;
    background: transparent;
    color: var(--text-1);
    font-family: var(--font-body);
    font-size: 0.86rem;
    font-weight: 600;
    padding: 7px 14px;
    border-radius: 9px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .modo-btn svg { width: 15px; height: 15px; }
  .modo-btn:hover { color: var(--text-0); }
  .modo-btn .n {
    font-size: 0.7rem;
    font-weight: 700;
    padding: 1px 7px;
    border-radius: 100px;
    background: var(--border);
    color: var(--text-1);
  }
  .modo-btn.ativo { background: var(--turquoise); color: oklch(0.15 0.02 240); }
  /* editar (3.2.8.0) */
  body.editando .search-box, body.editando .result-count, body.editando .clear-btn, body.editando .chip-row,
  body.editando #grid { display: none !important; }
  .editor { margin-top: 18px; background: var(--bg-1, oklch(0.2 0.02 240)); border: 1px solid var(--line, oklch(0.32 0.02 240));
            border-radius: 16px; padding: 18px; }
  .ed-topo { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap; }
  .ed-topo b { font-size: 1.05rem; }
  .ed-estado { font-size: .78rem; color: var(--text-2, #9aa); margin-left: 8px; }
  .ed-estado.sujo { color: oklch(0.8 0.15 75); font-weight: 700; }
  .ed-dica { font-size: .78rem; color: var(--text-2, #9aa); margin-top: 4px; }
  .ed-acoes-topo { display: flex; gap: 8px; }
  .ed-btn { font: inherit; font-size: .82rem; font-weight: 600; border-radius: 10px; padding: 7px 14px; cursor: pointer;
            border: 1px solid var(--line, oklch(0.32 0.02 240)); background: transparent; color: var(--text-0, #eee); }
  .ed-btn:hover { border-color: var(--turquoise); }
  .ed-btn.pri { background: var(--turquoise); border-color: var(--turquoise); color: oklch(0.15 0.02 240); }
  .ed-btn:disabled { opacity: .5; cursor: default; }
  .ed-btn.perigo { color: oklch(0.7 0.18 25); border-color: oklch(0.7 0.18 25 / .5); }
  .ed-btn.mini { padding: 4px 9px; font-size: .75rem; }
  .ed-erro { margin-top: 12px; padding: 10px 12px; border-radius: 10px; font-size: .85rem; color: oklch(0.75 0.17 25);
             background: oklch(0.65 0.2 25 / .1); border: 1px solid oklch(0.65 0.2 25 / .4); }
  .ed-corpo { display: grid; grid-template-columns: 250px minmax(0, 1fr); gap: 18px; margin-top: 16px; align-items: start; }
  .ed-lista { display: flex; flex-direction: column; gap: 6px; position: sticky; top: 12px; }
  .ed-cli { display: flex; align-items: center; gap: 8px; width: 100%; text-align: left; font: inherit; font-size: .85rem; cursor: pointer;
            border: 1px solid transparent; border-radius: 10px; padding: 6px 8px; background: transparent; color: var(--text-0, #eee); }
  .ed-cli:hover { background: oklch(0.5 0.02 240 / .12); }
  .ed-cli.ativo { border-color: var(--turquoise); background: oklch(0.7 0.13 205 / .1); }
  .ed-cli .nm { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .ed-cli .qt { font-size: .7rem; color: var(--text-2, #9aa); }
  .ed-cli .mv { display: inline-flex; gap: 2px; }
  .ed-cli .mv span { padding: 0 4px; border-radius: 6px; color: var(--text-2, #9aa); }
  .ed-cli .mv span:hover { color: var(--text-0, #eee); background: oklch(0.5 0.02 240 / .2); }
  .ed-badge { width: 30px; height: 30px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; flex: none;
              color: #fff; font-weight: 800; font-size: .7rem; overflow: hidden; }
  .ed-badge img { width: 100%; height: 100%; object-fit: contain; }
  .ed-badge.grande { width: 64px; height: 64px; border-radius: 14px; font-size: 1rem; }
  .ed-novo { margin-top: 6px; }
  .ed-form h3 { font-size: .8rem; text-transform: uppercase; letter-spacing: .05em; color: var(--text-2, #9aa); margin: 22px 0 10px; }
  .ed-form h3:first-child { margin-top: 0; }
  .ed-campos { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
  .ed-campo label { display: block; font-size: .72rem; color: var(--text-2, #9aa); margin-bottom: 4px; }
  .ed-form input[type=text], .ed-form input[type=url], .ed-form select, .ed-form textarea {
      box-sizing: border-box; width: 100%; font: inherit; font-size: .84rem; color: var(--text-0, #eee);
      background: oklch(0.15 0.02 240 / .5); border: 1px solid var(--line, oklch(0.32 0.02 240)); border-radius: 8px; padding: 6px 8px; }
  .ed-form textarea { resize: vertical; min-height: 58px; font-family: ui-monospace, Consolas, monospace; font-size: .8rem; }
  .ed-form input:focus, .ed-form select:focus, .ed-form textarea:focus { outline: none; border-color: var(--turquoise); }
  .ed-cor { display: flex; gap: 6px; align-items: center; }
  .ed-cor input[type=color] { width: 38px; height: 32px; padding: 0; border: none; background: none; cursor: pointer; flex: none; }
  .ed-logo { display: flex; gap: 14px; align-items: center; flex-wrap: wrap; }
  .ed-linha { display: grid; gap: 6px; align-items: center; padding: 6px 0; border-bottom: 1px dashed var(--line, oklch(0.32 0.02 240)); }
  .ed-linha.lk { grid-template-columns: 120px minmax(110px, 1fr) minmax(180px, 2fr) 74px 64px auto; }
  .ed-linha.sv { grid-template-columns: minmax(120px, 1fr) 74px minmax(200px, 2fr) auto; }
  .ed-linha.ap { grid-template-columns: minmax(130px, 1fr) 74px minmax(200px, 2fr) auto; }
  .ed-linha .acoes { display: inline-flex; gap: 4px; }
  .ed-infra { display: inline-flex; gap: 4px; align-items: center; font-size: .75rem; color: var(--text-2, #9aa); cursor: pointer; }
  .ed-vazio { font-size: .8rem; color: var(--text-2, #9aa); padding: 4px 0 8px; }
  .ed-rodape { margin-top: 24px; padding-top: 14px; border-top: 1px solid var(--line, oklch(0.32 0.02 240)); }
  @media (max-width: 860px) {
    .ed-corpo { grid-template-columns: minmax(0, 1fr); }
    .ed-lista { position: static; }
    .ed-linha.lk, .ed-linha.sv, .ed-linha.ap { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  }
  .modo-btn.ativo .n { background: oklch(0.15 0.02 240 / 0.18); color: oklch(0.15 0.02 240); }

  /* cada visão mostra só a sua parte do card e só os seus filtros de tipo */
  .grid.modo-monitores .infra-titulo, .grid.modo-monitores .infra-list { display: none; }
  .grid.modo-infra .link-list, .grid.modo-infra .infra-titulo { display: none; }
  .chip-row.modo-monitores [data-grupo="infra"], .chip-row.modo-infra [data-grupo="doc"] { display: none; }

  .search-box {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px 14px;
  }

  :root[data-theme="dark"] .search-box { background: oklch(0.19 0.025 235); }

  .search-box svg { width: 17px; height: 17px; color: var(--text-2); flex-shrink: 0; }

  .search-box input {
    border: none;
    outline: none;
    background: transparent;
    color: var(--text-0);
    font-family: var(--font-body);
    font-size: 0.95rem;
    width: 100%;
  }
  .search-box input::placeholder { color: var(--text-2); }

  .result-count {
    font-size: 0.82rem;
    color: var(--text-2);
    white-space: nowrap;
    padding: 0 4px;
  }

  .clear-btn {
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-1);
    font-family: var(--font-body);
    font-size: 0.82rem;
    padding: 9px 14px;
    border-radius: 12px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s ease, border-color 0.15s ease, opacity 0.15s ease;
  }
  .clear-btn:hover { border-color: var(--turquoise); }
  .clear-btn:disabled { opacity: 0.35; cursor: default; }
  .clear-btn:disabled:hover { border-color: var(--border); }

  .chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 12px;
  }

  .chip {
    font-family: var(--font-body);
    font-size: 0.82rem;
    font-weight: 500;
    padding: 7px 14px;
    border-radius: 100px;
    border: 1px solid var(--border);
    background: var(--bg-2);
    color: var(--text-1);
    cursor: pointer;
    transition: transform 0.12s ease, border-color 0.15s ease, background 0.15s ease, color 0.15s ease;
  }
  :root[data-theme="dark"] .chip { background: oklch(0.19 0.025 235); }
  .chip:hover { transform: translateY(-1px); border-color: var(--chip-c, var(--turquoise)); }
  /* o fundo escuro acima tem mais peso que .chip.active: sem repetir o seletor com o tema,
     o chip selecionado ficava com fundo escuro e texto escuro (invisível) */
  .chip.active, :root[data-theme="dark"] .chip.active {
    background: var(--chip-c, var(--turquoise));
    border-color: var(--chip-c, var(--turquoise));
    color: oklch(0.15 0.02 240);
  }

  /* ---------- Grid ---------- */
  /* colunas montadas pelo JS (organizarColunas): cada card vai pra coluna mais curta,
     do maior cliente pro menor, sem os buracos que a grade em linhas deixava */
  .grid {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-start;
    gap: 20px;
  }

  .card {
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px;
    box-shadow: 0 8px 24px var(--shadow);
    opacity: 0;
    transform: translateY(10px);
    animation: cardIn 0.45s ease forwards;
    animation-delay: var(--d, 0ms);
    transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
  }

  .card:hover {
    transform: translateY(-3px);
    border-color: oklch(0.7 0.13 205 / 0.55);
    box-shadow: 0 14px 34px var(--shadow), 0 0 0 1px var(--glow);
  }

  @keyframes cardIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .card.hidden { display: none; }

  .card-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 10px;
    margin-bottom: 14px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
  }

  .card-head-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 0;
  }

  .logo-badge {
    width: 40px;
    height: 40px;
    border-radius: 11px;
    flex-shrink: 0;
    display: grid;
    place-items: center;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 0.92rem;
    color: #fff;
    letter-spacing: -0.01em;
    box-shadow: 0 4px 12px var(--shadow);
  }

  /* cliente com logo própria: a imagem ocupa o selo inteiro no lugar das iniciais */
  .logo-badge.com-logo {
    overflow: hidden;
  }

  .logo-badge.com-logo img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    display: block;
  }

  .card-head h2 {
    font-size: 1.08rem;
    font-weight: 700;
  }

  .card-head .csub {
    font-size: 0.78rem;
    color: var(--text-2);
    margin-top: 2px;
  }

  .count-badge {
    font-family: var(--font-head);
    font-size: 0.72rem;
    font-weight: 600;
    color: var(--text-2);
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 100px;
    padding: 3px 10px;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .link-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .link-btn {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: var(--text-0);
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 0.88rem;
    font-weight: 500;
    transition: background 0.15s ease, border-color 0.15s ease, transform 0.12s ease;
  }
  :root[data-theme="dark"] .link-btn { background: oklch(0.19 0.025 235); }

  /* cliente já cadastrado mas ainda sem links dos ambientes */
  .link-vazio {
    border: 1px dashed var(--border);
    border-radius: 12px;
    padding: 10px 12px;
    font-size: 0.85rem;
    color: var(--text-2);
    text-align: center;
  }

  .link-btn:hover {
    border-color: var(--tag-c, var(--turquoise));
    transform: translateX(2px);
  }

  .link-btn .tag {
    font-family: var(--font-head);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.01em;
    color: oklch(0.15 0.02 240);
    background: var(--tag-c, var(--turquoise));
    border-radius: 7px;
    padding: 3px 8px;
    flex-shrink: 0;
  }

  .link-btn .lbl { flex: 1; }

  .link-btn .go {
    width: 14px; height: 14px;
    color: var(--text-2);
    flex-shrink: 0;
    transition: transform 0.15s ease, color 0.15s ease;
  }
  .link-btn:hover .go { color: var(--tag-c, var(--turquoise)); transform: translate(2px,-2px); }

  .link-btn.dim { display: none; }

  /* ambiente do link (2.34.5.0): PRD discreto, HML destacado pra não confundir com produção */
  .link-btn .env {
    font-family: var(--font-head);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    border-radius: 6px;
    padding: 2px 6px;
    border: 1px solid;
    flex-shrink: 0;
  }
  .link-btn .env.prd { color: oklch(0.72 0.14 150); border-color: oklch(0.72 0.14 150 / 0.4); }
  .link-btn .env.hml { color: oklch(0.8 0.15 75); border-color: oklch(0.8 0.15 75 / 0.6); background: oklch(0.8 0.15 75 / 0.14); }

  /* filtros: rótulo de cada grupo (Ambiente / Tipo) e um divisor entre eles */
  .chip-rotulo {
    align-self: center;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-2);
    margin-right: 2px;
  }
  .chip-sep { width: 1px; align-self: stretch; background: var(--border); margin: 2px 6px; }
  .chip-quebra { flex-basis: 100%; height: 0; }
  .chip.env-hml { --chip-c: oklch(0.8 0.15 75); }
  .chip.env-prd { --chip-c: oklch(0.72 0.14 150); }

  /* links de infraestrutura (RabbitMQ, Graylog, servidores): seção própria no fim do card,
     em linhas mais compactas que as dos monitores (lado a lado o nome não cabia) */
  .infra-titulo {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-2);
    margin: 14px 0 8px 0;
    padding-top: 12px;
    border-top: 1px dashed var(--border);
  }
  .infra-titulo.hidden { display: none; }
  .infra-list { display: flex; flex-direction: column; gap: 6px; }
  .link-btn.infra { min-width: 0; padding: 6px 10px; font-size: 0.8rem; gap: 8px; border-radius: 10px; }
  .link-btn.infra .tag { font-size: 0.62rem; padding: 2px 7px; }

  /* servidores (IP / nome de máquina): não são páginas, então não viram link;
     cada um é uma etiqueta que copia o endereço ao clicar */
  .srv-grupo { padding: 2px 0 4px 0; }
  .srv-grupo.dim { display: none; }
  .srv-cab { display: flex; align-items: center; gap: 6px; font-size: 0.74rem; font-weight: 600; color: var(--text-1); margin-bottom: 5px; }
  .srv-cab .env { font-family: var(--font-head); font-size: 0.56rem; font-weight: 700; letter-spacing: 0.05em; border-radius: 5px; padding: 1px 5px; border: 1px solid; }
  .srv-cab .env.prd { color: oklch(0.72 0.14 150); border-color: oklch(0.72 0.14 150 / 0.4); }
  .srv-cab .env.hml { color: oklch(0.8 0.15 75); border-color: oklch(0.8 0.15 75 / 0.6); background: oklch(0.8 0.15 75 / 0.14); }
  .srv-chips { display: flex; flex-wrap: wrap; gap: 5px; }
  .srv-chip {
    font-family: Consolas, 'Cascadia Mono', monospace;
    font-size: 0.74rem;
    color: var(--text-0);
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 7px;
    padding: 3px 8px;
    cursor: pointer;
    transition: border-color 0.15s ease, color 0.15s ease;
  }
  :root[data-theme="dark"] .srv-chip { background: oklch(0.19 0.025 235); }
  .srv-chip:hover { border-color: var(--turquoise); }
  .srv-chip.copiado { border-color: oklch(0.72 0.14 150); color: oklch(0.72 0.14 150); }
  .link-btn.infra .lbl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  /* produtos por servidor (3.1.7.0): uma linha por servidor, IP à esquerda e os produtos em etiquetas por família */
  .app-srv-titulo { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; font-size: 0.74rem; font-weight: 600; color: var(--text-1); margin-top: 6px; }
  .app-srv-titulo .dica { font-size: 0.66rem; font-weight: 400; color: var(--text-2, var(--text-1)); opacity: 0.75; }
  .app-srv { display: grid; grid-template-columns: 148px minmax(0, 1fr); gap: 8px; align-items: start; padding: 7px 8px;
             border: 1px solid var(--border); border-radius: 10px; transition: opacity 0.15s ease, border-color 0.15s ease, background 0.15s ease; }
  .app-host { display: flex; flex-direction: column; align-items: flex-start; gap: 3px; }
  .app-qtd { font-size: 0.64rem; color: var(--text-1); opacity: 0.8; padding-left: 2px; }
  .app-prods { display: flex; flex-wrap: wrap; gap: 4px; }
  .app-prod { --cor: oklch(0.7 0.02 240); font: inherit; font-size: 0.68rem; font-weight: 600; line-height: 1.2; cursor: pointer;
              color: var(--cor); background: color-mix(in oklch, var(--cor) 13%, transparent);
              border: 1px solid color-mix(in oklch, var(--cor) 40%, transparent); border-radius: 999px; padding: 2px 8px;
              transition: background 0.15s ease, transform 0.15s ease; }
  .app-prod:hover { background: color-mix(in oklch, var(--cor) 24%, transparent); }
  .app-prod.ativo { background: var(--cor); color: oklch(0.18 0.02 240); border-color: var(--cor); }
  .app-prod.fam-nfe { --cor: oklch(0.72 0.13 230); }
  .app-prod.fam-nfce { --cor: oklch(0.74 0.14 195); }
  .app-prod.fam-cte { --cor: oklch(0.74 0.15 145); }
  .app-prod.fam-mdfe { --cor: oklch(0.78 0.14 100); }
  .app-prod.fam-nfse { --cor: oklch(0.72 0.15 300); }
  .app-prod.fam-email { --cor: oklch(0.75 0.13 60); }
  .app-prod.fam-powerdocs { --cor: oklch(0.72 0.16 20); }
  .app-prod.fam-publicador { --cor: oklch(0.74 0.12 340); }
  .app-prod.fam-outro { --cor: oklch(0.76 0.03 240); }
  .com-destaque .app-srv:not(.destaque) { opacity: 0.35; }
  .com-destaque .app-srv.destaque { border-color: var(--turquoise); background: color-mix(in oklch, var(--turquoise) 8%, transparent); }
  @media (max-width: 520px) { .app-srv { grid-template-columns: minmax(0, 1fr); } }
  .infra-list:not(:has(.app-srv:not(.dim))) .app-srv-titulo { display: none; }  /* filtro sem nenhum servidor: some o título */

  .coluna-grid { flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 20px; }
  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--text-2);
    width: 100%;
  }
  .empty-state svg { width: 40px; height: 40px; margin-bottom: 12px; opacity: 0.5; }
  .empty-state p { font-size: 0.95rem; }

  footer.foot {
    text-align: center;
    color: var(--text-2);
    font-size: 0.78rem;
    margin-top: 50px;
  }

  /* ---------- App visibility gate ---------- */
  .wrap { display: none; }
  body.authed .wrap { display: block; }
  body.authed #authOverlay { display: none; }

  /* ---------- Modal overlay (auth + settings) ---------- */
  .modal-overlay {
    position: fixed;
    inset: 0;
    z-index: 200;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background:
      radial-gradient(1100px 620px at 12% -10%, var(--glow), transparent 60%),
      radial-gradient(900px 560px at 100% 0%, oklch(0.83 0.19 120 / 0.14), transparent 55%),
      var(--bg-0);
  }
  .modal-overlay.hidden { display: none; }

  .modal-card {
    width: 100%;
    max-width: 400px;
    background: var(--surface-strong);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 28px;
    box-shadow: 0 20px 50px var(--shadow);
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal-card .mc-logo {
    width: 52px; height: 52px;
    border-radius: 14px;
    background: var(--bg-2);
    border: 1px solid var(--border);
    display: grid; place-items: center;
    padding: 7px;
    margin: 0 auto 14px;
  }
  .modal-card .mc-logo img { width: 100%; height: 100%; object-fit: contain; }

  .modal-card h2 {
    font-size: 1.2rem;
    text-align: center;
    margin-bottom: 4px;
  }
  .modal-card .mc-sub {
    text-align: center;
    color: var(--text-2);
    font-size: 0.85rem;
    margin-bottom: 22px;
  }

  .field {
    margin-bottom: 14px;
  }
  .field label {
    display: block;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--text-1);
    margin-bottom: 6px;
  }
  .field input {
    width: 100%;
    background: var(--bg-2);
    border: 1px solid var(--border);
    border-radius: 11px;
    padding: 10px 13px;
    font-family: var(--font-body);
    font-size: 0.92rem;
    color: var(--text-0);
    outline: none;
    transition: border-color 0.15s ease;
  }
  :root[data-theme="dark"] .field input { background: oklch(0.19 0.025 235); }
  .field input:focus { border-color: var(--turquoise); }
  .field-hint { font-size: 0.72rem; color: var(--text-2); margin-top: 5px; }

  .btn-primary {
    width: 100%;
    background: linear-gradient(135deg, var(--turquoise) 0%, var(--lime) 100%);
    border: none;
    border-radius: 12px;
    padding: 12px;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 0.92rem;
    color: oklch(0.15 0.02 240);
    cursor: pointer;
    transition: opacity 0.15s ease, transform 0.12s ease;
  }
  .btn-primary:hover { opacity: 0.92; }
  .btn-primary:active { transform: scale(0.98); }
  .btn-primary:disabled { opacity: 0.55; cursor: default; }

  .btn-secondary {
    width: 100%;
    background: transparent;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 11px;
    font-family: var(--font-body);
    font-weight: 600;
    font-size: 0.88rem;
    color: var(--text-1);
    cursor: pointer;
    transition: border-color 0.15s ease;
  }
  .btn-secondary:hover { border-color: var(--turquoise); }

  .btn-danger { color: oklch(0.6 0.2 25); }
  .btn-danger:hover { border-color: oklch(0.6 0.2 25); }

  .form-error {
    background: oklch(0.6 0.2 25 / 0.12);
    border: 1px solid oklch(0.6 0.2 25 / 0.4);
    color: oklch(0.55 0.2 25);
    font-size: 0.82rem;
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 14px;
    display: none;
  }
  .form-error.show { display: block; }

  .form-success {
    background: oklch(0.75 0.15 145 / 0.15);
    border: 1px solid oklch(0.7 0.15 145 / 0.5);
    color: oklch(0.45 0.12 150);
    font-size: 0.82rem;
    border-radius: 10px;
    padding: 9px 12px;
    margin-bottom: 14px;
    display: none;
  }
  :root[data-theme="dark"] .form-success { color: oklch(0.85 0.15 145); }
  .form-success.show { display: block; }

  .auth-switch {
    text-align: center;
    font-size: 0.82rem;
    color: var(--text-2);
    margin-top: 16px;
  }
  .auth-switch a {
    color: var(--turquoise-strong);
    cursor: pointer;
    font-weight: 600;
    text-decoration: none;
  }
  :root[data-theme="dark"] .auth-switch a { color: oklch(0.78 0.13 205); }

  .divider {
    height: 1px;
    background: var(--border);
    margin: 20px 0;
    border: none;
  }

  /* ---------- Avatar / settings trigger ---------- */
  .avatar-btn {
    width: 42px;
    height: 42px;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: var(--surface);
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    display: grid;
    place-items: center;
    cursor: pointer;
    overflow: hidden;
    flex-shrink: 0;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 0.85rem;
    color: var(--text-0);
    background-size: cover;
    background-position: center;
    transition: border-color 0.15s ease, transform 0.12s ease;
  }
  .avatar-btn:hover { border-color: var(--turquoise); }
  .avatar-btn:active { transform: scale(0.94); }

  .avatar-upload {
    width: 84px; height: 84px;
    border-radius: 50%;
    margin: 0 auto 16px;
    background: var(--bg-2);
    border: 2px dashed var(--border);
    display: grid;
    place-items: center;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    background-size: cover;
    background-position: center;
    font-family: var(--font-head);
    font-weight: 700;
    font-size: 1.6rem;
    color: var(--text-2);
    transition: border-color 0.15s ease;
  }
  .avatar-upload:hover { border-color: var(--turquoise); }
  .avatar-upload .cam {
    position: absolute;
    bottom: 0; left: 0; right: 0;
    background: oklch(0.15 0.02 240 / 0.55);
    color: #fff;
    font-size: 0.6rem;
    text-align: center;
    padding: 4px 0;
    font-family: var(--font-body);
    font-weight: 600;
  }

  .settings-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 6px;
  }
  .settings-row h2 { font-size: 1.15rem; text-align: left; margin: 0; }
  .icon-btn {
    width: 32px; height: 32px;
    border-radius: 9px;
    border: 1px solid var(--border);
    background: transparent;
    display: grid; place-items: center;
    cursor: pointer;
    color: var(--text-2);
    flex-shrink: 0;
    transition: border-color 0.15s ease, color 0.15s ease;
  }
  .icon-btn:hover { border-color: var(--turquoise); color: var(--text-0); }
  .icon-btn svg { width: 16px; height: 16px; }

  .section-label {
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--text-2);
    margin-bottom: 10px;
  }

  @media (prefers-reduced-motion: reduce) {
    .card, .chip, .link-btn, .theme-toggle { animation: none !important; transition: none !important; }
    .card { opacity: 1; transform: none; }
  }

  @media (max-width: 640px) {
    header.top { flex-direction: column; }
    .top-right { width: 100%; justify-content: space-between; }
    .search-row { flex-wrap: wrap; }
    .modo-toggle { width: 100%; box-sizing: border-box; }
    .modo-btn { flex: 1 1 0; min-width: 0; justify-content: center; padding: 7px 8px; }
    .modo-btn svg { display: none; }
    .result-count { order: 3; width: 100%; }
    /* no celular o voltar vira só a seta, pra não apertar o título */
    .back-btn { padding: 0; width: 42px; justify-content: center; }
    .back-btn span { display: none; }
  }
</style>
</head>
<body class="authed">
<div id="authOverlay" class="modal-overlay">
  <div class="modal-card">
    <div class="mc-logo"><img src="" id="authLogoImg" alt="Empresa"></div>

    <!-- Setup (primeiro acesso) -->
    <form id="setupForm">
      <h2>Criar acesso</h2>
      <p class="mc-sub">Configure o acesso local a este painel.</p>
      <div class="form-error" id="setupError"></div>
      <div class="field">
        <label for="setupName">Nome de exibição</label>
        <input type="text" id="setupName" autocomplete="name" required>
      </div>
      <div class="field">
        <label for="setupUser">Usuário</label>
        <input type="text" id="setupUser" autocomplete="username" required>
      </div>
      <div class="field">
        <label for="setupPass">Senha</label>
        <input type="password" id="setupPass" autocomplete="new-password" required minlength="4">
      </div>
      <div class="field">
        <label for="setupPass2">Confirmar senha</label>
        <input type="password" id="setupPass2" autocomplete="new-password" required minlength="4">
      </div>
      <button type="submit" class="btn-primary">Criar acesso e entrar</button>
    </form>

    <!-- Login -->
    <form id="loginForm" style="display:none">
      <h2>Entrar</h2>
      <p class="mc-sub">Acesse a Central de Monitores.</p>
      <div class="form-error" id="loginError"></div>
      <div class="field">
        <label for="loginUser">Usuário</label>
        <input type="text" id="loginUser" autocomplete="username" required>
      </div>
      <div class="field">
        <label for="loginPass">Senha</label>
        <input type="password" id="loginPass" autocomplete="current-password" required>
      </div>
      <button type="submit" class="btn-primary">Entrar</button>
      <div class="auth-switch"><a id="resetAccessLink">Esqueci meus dados de acesso</a></div>
    </form>
  </div>
</div>

<div id="settingsModal" class="modal-overlay hidden">
  <div class="modal-card">
    <div class="settings-row">
      <h2>Configurações</h2>
      <button class="icon-btn" id="closeSettings" aria-label="Fechar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
      </button>
    </div>
    <p class="mc-sub" style="text-align:left;margin-bottom:18px;">Perfil e acesso deste dispositivo.</p>

    <form id="settingsForm">
      <div class="form-error" id="settingsError"></div>
      <div class="form-success" id="settingsSuccess">Alterações salvas.</div>

      <div class="avatar-upload" id="avatarUpload">
        <span id="avatarInitials">?</span>
        <div class="cam">ALTERAR FOTO</div>
      </div>
      <input type="file" id="avatarFile" accept="image/*" style="display:none">

      <div class="section-label">Perfil</div>
      <div class="field">
        <label for="settName">Nome de exibição</label>
        <input type="text" id="settName">
      </div>
      <div class="field">
        <label for="settUser">Usuário</label>
        <input type="text" id="settUser">
      </div>

      <hr class="divider">

      <div class="section-label">Alterar senha (opcional)</div>
      <div class="field">
        <label for="settCurPass">Senha atual</label>
        <input type="password" id="settCurPass" autocomplete="current-password">
      </div>
      <div class="field">
        <label for="settNewPass">Nova senha</label>
        <input type="password" id="settNewPass" autocomplete="new-password" minlength="4">
      </div>
      <div class="field">
        <label for="settNewPass2">Confirmar nova senha</label>
        <input type="password" id="settNewPass2" autocomplete="new-password" minlength="4">
        <div class="field-hint">Deixe os campos de senha em branco para mantê-la como está.</div>
      </div>

      <button type="submit" class="btn-primary" style="margin-bottom:10px;">Salvar alterações</button>
      <button type="button" class="btn-secondary btn-danger" id="logoutBtn">Sair</button>
    </form>
  </div>
</div>

<div class="wrap">


  <header class="top">
    <div class="brand">
      <a class="back-btn" href="/" title="Voltar ao hub do PDA" aria-label="Voltar ao hub do PDA">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        <span>Voltar</span>
      </a>
      <div class="brand-mark">
        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAIAAAAlC+aJAAAAgElEQVR4nNXOQREAIAzAsFI/+McFlhCxB9coyNrnUiZxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEidxEufvwNQDbrgCNC99lLIAAAAASUVORK5CYII=" alt="Empresa" />
      </div>
      <div>
        <div class="brand-name">EMPRESA</div>
        <h1 class="title">Central de Monitores</h1>
        <p class="subtitle">Acesso rápido aos monitores fiscais de cada cliente, organizados por tipo de documento.</p>
      </div>
    </div>
    <div class="top-right">
      <div class="stats">
        <div class="stat-pill"><div class="num" id="statClients">0</div><div class="lbl">clientes</div></div>
        <div class="stat-pill"><div class="num" id="statMonitors">0</div><div class="lbl">monitores</div></div>
      </div>
      <button class="theme-toggle" id="themeToggle" aria-label="Alternar tema">
        <svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
        <svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>
      </button>
    </div>
  </header>

  <div class="controls">
    <div class="search-row">
      <div class="modo-toggle" role="tablist" aria-label="O que mostrar">
        <button class="modo-btn ativo" data-modo="monitores" role="tab" aria-selected="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/></svg>
          Monitores <span class="n" id="nModoMonitores">0</span>
        </button>
        <button class="modo-btn" data-modo="infra" role="tab" aria-selected="false">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="7" rx="2"/><rect x="3" y="13" width="18" height="7" rx="2"/><path d="M7 7.5h.01M7 16.5h.01"/></svg>
          Infraestrutura <span class="n" id="nModoInfra">0</span>
        </button>
        <button class="modo-btn" data-modo="editar" role="tab" aria-selected="false" hidden title="Editar clientes, monitores e infraestrutura">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>
          Editar
        </button>
      </div>
      <div class="search-box">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
        <input type="text" id="searchInput" placeholder="Buscar por cliente, monitor ou tipo de documento…">
      </div>
      <span class="result-count" id="resultCount"></span>
      <button class="clear-btn" id="clearBtn">Limpar filtros</button>
    </div>
    <div class="chip-row" id="chipRow"></div>
  </div>

  <div class="grid" id="grid"></div>

  <!-- Editar (3.2.8.0): só pra administrador com a permissão pode_editar_central -->
  <section class="editor" id="editorCentral" hidden aria-label="Editar a Central de Monitores">
    <div class="ed-topo">
      <div><b>Editar a Central</b> <span class="ed-estado" id="edEstado">Sem alterações</span>
        <div class="ed-dica">As mudanças só valem depois de salvar. A página é aberta pra todo mundo, sem login.</div></div>
      <div class="ed-acoes-topo">
        <button type="button" class="ed-btn sec" id="edDescartar">Descartar</button>
        <button type="button" class="ed-btn pri" id="edSalvar" disabled>Salvar alterações</button>
      </div>
    </div>
    <div class="ed-erro" id="edErro" hidden></div>
    <div class="ed-corpo">
      <aside class="ed-lista">
        <div id="edClientes"></div>
        <button type="button" class="ed-btn sec ed-novo" id="edNovo">+ Novo cliente</button>
      </aside>
      <div class="ed-form" id="edForm"></div>
    </div>
  </section>

  <footer class="foot">Central de Monitores Empresa · eDocs · HTML base da página desenvolvido por Wagner Faria</footer>
</div>

<script>
  // ---------- Theme toggle ----------
  (function(){
    var root = document.documentElement;
    var btn = document.getElementById('themeToggle');
    btn.addEventListener('click', function(){
      var current = root.getAttribute('data-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('pda-tema', next === 'light' ? 'claro' : 'escuro'); } catch(e) {}
    });
  })();

  // ---------- Auth logo (reaproveita a logo já embutida no cabeçalho) ----------
  (function(){
    var src = document.querySelector('.brand-mark img').getAttribute('src');
    document.getElementById('authLogoImg').setAttribute('src', src);
  })();

  // ---------- Auth & Settings ----------
  (function(){
    var ACCOUNT_KEY = 'empresa-account';
    var SESSION_KEY = 'empresa-session';

    var authOverlay = document.getElementById('authOverlay');
    var setupForm = document.getElementById('setupForm');
    var loginForm = document.getElementById('loginForm');
    var setupError = document.getElementById('setupError');
    var loginError = document.getElementById('loginError');
    var resetAccessLink = document.getElementById('resetAccessLink');

    var avatarBtn = document.getElementById('avatarBtn');
    var settingsModal = document.getElementById('settingsModal');
    var closeSettings = document.getElementById('closeSettings');
    var settingsForm = document.getElementById('settingsForm');
    var settingsError = document.getElementById('settingsError');
    var settingsSuccess = document.getElementById('settingsSuccess');
    var avatarUpload = document.getElementById('avatarUpload');
    var avatarFile = document.getElementById('avatarFile');
    var avatarInitials = document.getElementById('avatarInitials');
    var logoutBtn = document.getElementById('logoutBtn');

    function getAccount(){
      try { return JSON.parse(localStorage.getItem(ACCOUNT_KEY) || 'null'); }
      catch(e){ return null; }
    }
    function saveAccount(acc){
      try { localStorage.setItem(ACCOUNT_KEY, JSON.stringify(acc)); return true; }
      catch(e){ return false; }
    }
    function getInitials(name){
      var parts = (name || '').trim().split(/\\s+/).filter(Boolean);
      if (parts.length === 0) return '?';
      if (parts.length === 1) return parts[0].slice(0,2).toUpperCase();
      return (parts[0][0] + parts[parts.length-1][0]).toUpperCase();
    }
    async function sha256Hex(str){
      var buf = new TextEncoder().encode(str);
      var hashBuf = await crypto.subtle.digest('SHA-256', buf);
      return Array.prototype.map.call(new Uint8Array(hashBuf), function(b){ return b.toString(16).padStart(2,'0'); }).join('');
    }
    function randomSaltHex(){
      var arr = new Uint8Array(16);
      crypto.getRandomValues(arr);
      return Array.prototype.map.call(arr, function(b){ return b.toString(16).padStart(2,'0'); }).join('');
    }
    function resizeImageFile(file, maxSize){
      return new Promise(function(resolve, reject){
        var reader = new FileReader();
        reader.onload = function(e){
          var img = new Image();
          img.onload = function(){
            var scale = Math.min(1, maxSize / Math.max(img.width, img.height));
            var w = Math.round(img.width * scale);
            var h = Math.round(img.height * scale);
            var canvas = document.createElement('canvas');
            canvas.width = w; canvas.height = h;
            canvas.getContext('2d').drawImage(img, 0, 0, w, h);
            resolve(canvas.toDataURL('image/jpeg', 0.85));
          };
          img.onerror = reject;
          img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    }

    function showError(el, msg){ el.textContent = msg; el.classList.add('show'); }
    function hideError(el){ el.classList.remove('show'); }

    function applyAvatar(el, account){
      // o botão de conta (#avatarBtn) foi tirado da página no PDA 2.30.3: sem ele, não faz nada
      if (!el) return;
      if (account && account.photo) {
        el.style.backgroundImage = 'url(' + account.photo + ')';
        if (el === avatarUpload) { avatarInitials.textContent = ''; }
        else { el.textContent = ''; }
      } else {
        el.style.backgroundImage = '';
        var txt = getInitials(account ? account.name : '');
        if (el === avatarUpload) { avatarInitials.textContent = txt; }
        else { el.textContent = txt; }
      }
    }

    function onAuthed(account){
      document.body.classList.add('authed');
      applyAvatar(avatarBtn, account);
    }

    function showLoginScreen(){
      var account = getAccount();
      if (account) {
        setupForm.style.display = 'none';
        loginForm.style.display = 'block';
      } else {
        setupForm.style.display = 'block';
        loginForm.style.display = 'none';
      }
    }

    // ---- Boot ----
    var existingAccount = getAccount();
    if (existingAccount && sessionStorage.getItem(SESSION_KEY) === '1') {
      onAuthed(existingAccount);
    } else {
      showLoginScreen();
    }

    // ---- Setup (primeiro acesso) ----
    setupForm.addEventListener('submit', async function(ev){
      ev.preventDefault();
      hideError(setupError);
      var name = document.getElementById('setupName').value.trim();
      var user = document.getElementById('setupUser').value.trim();
      var pass = document.getElementById('setupPass').value;
      var pass2 = document.getElementById('setupPass2').value;
      if (!name || !user || !pass) { showError(setupError, 'Preencha todos os campos.'); return; }
      if (pass.length < 4) { showError(setupError, 'A senha precisa ter ao menos 4 caracteres.'); return; }
      if (pass !== pass2) { showError(setupError, 'As senhas não coincidem.'); return; }
      var salt = randomSaltHex();
      var hash = await sha256Hex(salt + pass);
      var account = { name: name, username: user, salt: salt, hash: hash, photo: null };
      saveAccount(account);
      sessionStorage.setItem(SESSION_KEY, '1');
      onAuthed(account);
    });

    // ---- Login ----
    loginForm.addEventListener('submit', async function(ev){
      ev.preventDefault();
      hideError(loginError);
      var user = document.getElementById('loginUser').value.trim();
      var pass = document.getElementById('loginPass').value;
      var account = getAccount();
      if (!account) { showLoginScreen(); return; }
      var hash = await sha256Hex(account.salt + pass);
      if (user.toLowerCase() === account.username.toLowerCase() && hash === account.hash) {
        sessionStorage.setItem(SESSION_KEY, '1');
        onAuthed(account);
      } else {
        showError(loginError, 'Usuário ou senha inválidos.');
      }
    });

    resetAccessLink.addEventListener('click', function(){
      if (confirm('Isso vai apagar a conta local e as configurações salvas neste navegador. Deseja continuar?')) {
        try { localStorage.removeItem(ACCOUNT_KEY); sessionStorage.removeItem(SESSION_KEY); } catch(e){}
        location.reload();
      }
    });

    // ---- Settings modal ----
    function openSettings(){
      var account = getAccount();
      if (!account) return;
      hideError(settingsError);
      settingsSuccess.classList.remove('show');
      document.getElementById('settName').value = account.name || '';
      document.getElementById('settUser').value = account.username || '';
      document.getElementById('settCurPass').value = '';
      document.getElementById('settNewPass').value = '';
      document.getElementById('settNewPass2').value = '';
      applyAvatar(avatarUpload, account);
      settingsModal.classList.remove('hidden');
    }
    function closeSettingsModal(){ settingsModal.classList.add('hidden'); }

    // login local da página fica desligado no PDA (body nasce com "authed"), então o botão
    // de conta nunca tinha conta pra abrir e foi removido; o guard evita erro que pararia
    // o script inteiro, inclusive a montagem dos cards dos clientes logo abaixo
    if (avatarBtn) avatarBtn.addEventListener('click', openSettings);
    closeSettings.addEventListener('click', closeSettingsModal);
    settingsModal.addEventListener('click', function(ev){ if (ev.target === settingsModal) closeSettingsModal(); });

    avatarUpload.addEventListener('click', function(){ avatarFile.click(); });
    var pendingPhoto = null;
    avatarFile.addEventListener('change', async function(){
      var file = avatarFile.files[0];
      if (!file) return;
      try {
        pendingPhoto = await resizeImageFile(file, 200);
        avatarUpload.style.backgroundImage = 'url(' + pendingPhoto + ')';
        avatarInitials.textContent = '';
      } catch(e) {
        showError(settingsError, 'Não foi possível carregar essa imagem.');
      }
    });

    settingsForm.addEventListener('submit', async function(ev){
      ev.preventDefault();
      hideError(settingsError);
      settingsSuccess.classList.remove('show');
      var account = getAccount();
      if (!account) return;

      var name = document.getElementById('settName').value.trim();
      var user = document.getElementById('settUser').value.trim();
      var curPass = document.getElementById('settCurPass').value;
      var newPass = document.getElementById('settNewPass').value;
      var newPass2 = document.getElementById('settNewPass2').value;

      if (!name || !user) { showError(settingsError, 'Nome e usuário não podem ficar em branco.'); return; }

      if (newPass || newPass2 || curPass) {
        if (!curPass) { showError(settingsError, 'Informe a senha atual para alterá-la.'); return; }
        var curHash = await sha256Hex(account.salt + curPass);
        if (curHash !== account.hash) { showError(settingsError, 'Senha atual incorreta.'); return; }
        if (newPass.length < 4) { showError(settingsError, 'A nova senha precisa ter ao menos 4 caracteres.'); return; }
        if (newPass !== newPass2) { showError(settingsError, 'A confirmação de nova senha não coincide.'); return; }
        account.salt = randomSaltHex();
        account.hash = await sha256Hex(account.salt + newPass);
      }

      account.name = name;
      account.username = user;
      if (pendingPhoto) { account.photo = pendingPhoto; pendingPhoto = null; }

      saveAccount(account);
      applyAvatar(avatarBtn, account);
      settingsSuccess.classList.add('show');
    });

    logoutBtn.addEventListener('click', function(){
      sessionStorage.removeItem(SESSION_KEY);
      location.reload();
    });
  })();

  // ---------- Data ----------
  // tipos de monitor + de infraestrutura; o filtro só mostra os que têm algum link cadastrado
  var TYPES = ['NFe','NFCe','CTe','MDFe','NFSe','NFSeR','NFSe Soft','Publicador','PowerDocs','ClienteI','RabbitMQ','Graylog','Kubernetes','FTP','Servidor'];
  // ambiente de cada link (2.34.5.0): sem "env" no link = PRD
  var ENVS = ['PRD','HML'];
  // tipos que vão pra seção "Infraestrutura" do card (ou link com grupo: 'infra')
  var TIPOS_INFRA = ['RabbitMQ','Graylog','Kubernetes','FTP','Servidor'];  // Kubernetes desde a 3.2.3.0 (ClienteG)

  var TAG_COLORS = {
    'NFe':          'oklch(0.7 0.13 205)',
    'NFCe':         'oklch(0.83 0.19 120)',
    'CTe':          'oklch(0.72 0.15 300)',
    'MDFe':         'oklch(0.75 0.17 55)',
    'NFSe':         'oklch(0.68 0.16 255)',
    'NFSe Soft':    'oklch(0.72 0.13 230)',
    'NFSeR':        'oklch(0.66 0.14 280)',
    'Publicador':   'oklch(0.7 0.18 350)',
    'PowerDocs':    'oklch(0.78 0.15 85)',
    'ClienteI':         'oklch(0.74 0.14 165)',
    'RabbitMQ':     'oklch(0.72 0.17 45)',
    'Graylog':      'oklch(0.7 0.12 15)',
    'Kubernetes':   'oklch(0.66 0.15 262)',
    'Servidor':     'oklch(0.68 0.05 240)',
    'FTP':          'oklch(0.7 0.1 190)',
    'Outros':       'oklch(0.6 0.02 240)'
  };

  // Monogramas coloridos por marca (aproximação das cores oficiais de cada empresa,
  // usados apenas como identificador visual — não reproduzem os logotipos originais).
  // Com `logo` (data URI ou URL), a imagem substitui as iniciais; `logoBg` é o fundo
  // atrás dela (padrão transparente, pra logo que já vem recortada).
  var CLIENT_META = __CENTRAL_META__;  // 3.2.8.0: vem do servidor (areas/central_monitores)

  // Cada link: { label, type, url, env? ('PRD' padrão | 'HML'), grupo? ('infra') }.
  // Servidores (IP/nome de máquina, sem página): servidores: [{ grupo, env?, itens: [...] }] no cliente.
  // Produtos por servidor (3.1.7.0): aplicacoes: [{ host, env?, produtos: [...] }] no cliente; cada servidor vira uma
  // linha com o IP (copia) e os produtos (clicar num produto destaca os servidores onde ele roda).
  // Ex. de infraestrutura no card: { label: 'RabbitMQ PRD', type: 'RabbitMQ', url: 'http://...' }
  var clients = __CENTRAL_CLIENTES__;  // 3.2.8.0: vem do servidor (central_monitores.json ou o padrão)

  clients.forEach(function(c){
    c.links.forEach(function(l){
      l.env = (l.env || 'PRD').toUpperCase();
      l.infra = l.grupo === 'infra' || TIPOS_INFRA.indexOf(l.type) !== -1;
    });
    (c.servidores || []).forEach(function(s){ s.env = (s.env || 'PRD').toUpperCase(); });
    (c.aplicacoes || []).forEach(function(s){ s.env = (s.env || 'PRD').toUpperCase(); });
  });
  // família do produto pela cor da etiqueta (NFePackRT e NFePackWebScraping ficam na família NFe etc.)
  function familiaProduto(p){
    var n = String(p).toLowerCase();
    if (n.indexOf('nfse') === 0) return 'nfse';
    if (n.indexOf('nfce') === 0) return 'nfce';
    if (n.indexOf('nfe') === 0) return 'nfe';
    if (n.indexOf('cte') === 0) return 'cte';
    if (n.indexOf('mdfe') === 0) return 'mdfe';
    if (n.indexOf('email') === 0) return 'email';
    if (n.indexOf('powerdocs') === 0) return 'powerdocs';
    if (n.indexOf('publicador') === 0) return 'publicador';
    return 'outro';
  }
  // clicar num produto destaca os servidores que rodam ele (clicar de novo, ou em outro, troca/limpa)
  function destacarProduto(lista, produto){
    var atual = lista.dataset.produtoDestaque === produto ? '' : produto;
    lista.dataset.produtoDestaque = atual;
    lista.classList.toggle('com-destaque', !!atual);
    lista.querySelectorAll('.app-srv').forEach(function(l){
      l.classList.toggle('destaque', !!atual && l.dataset.produtos.indexOf('|' + atual + '|') !== -1);
    });
    lista.querySelectorAll('.app-prod').forEach(function(b){ b.classList.toggle('ativo', !!atual && b.dataset.prod === atual); });
  }
  function monitoresDe(c){ return c.links.filter(function(l){ return !l.infra; }); }
  function infraDe(c){ return c.links.filter(function(l){ return l.infra; }); }

  // ---------- Build stats ----------
  var totalMonitors = clients.reduce(function(sum, c){ return sum + monitoresDe(c).length; }, 0);
  document.getElementById('statClients').textContent = clients.length;
  document.getElementById('statMonitors').textContent = totalMonitors;

  // ---------- Build chips ----------
  var chipRow = document.getElementById('chipRow');
  var activeTypes = new Set();
  var activeEnvs = new Set();
  function rotuloChips(texto, grupo){
    var r = document.createElement('span');
    r.className = 'chip-rotulo';
    r.textContent = texto;
    if (grupo) r.dataset.grupo = grupo;
    chipRow.appendChild(r);
  }
  rotuloChips('Ambiente');
  ENVS.forEach(function(e){
    var chip = document.createElement('button');
    chip.className = 'chip env-' + e.toLowerCase();
    chip.textContent = e;
    chip.dataset.env = e;
    chip.title = e === 'HML' ? 'Homologação' : 'Produção';
    chip.addEventListener('click', function(){
      if (activeEnvs.has(e)) { activeEnvs.delete(e); chip.classList.remove('active'); }
      else { activeEnvs.add(e); chip.classList.add('active'); }
      render();
    });
    chipRow.appendChild(chip);
  });
  var sep = document.createElement('span');
  sep.className = 'chip-sep';
  chipRow.appendChild(sep);
  var tiposUsados = new Set();
  clients.forEach(function(c){
    c.links.forEach(function(l){ tiposUsados.add(l.type); });
    if ((c.servidores || []).length || (c.aplicacoes || []).length) tiposUsados.add('Servidor');
  });
  // dois grupos de filtro: tipos de documento e, separado, infraestrutura (2.34.7.2).
  // ClienteI é produto, não tipo de documento: a etiqueta continua no link, mas sem filtro
  var TIPOS_SEM_FILTRO = ['ClienteI', 'Outros'];
  var tiposFiltro = TYPES.filter(function(t){ return tiposUsados.has(t) && TIPOS_SEM_FILTRO.indexOf(t) === -1; });
  var tiposDocumento = tiposFiltro.filter(function(t){ return TIPOS_INFRA.indexOf(t) === -1; });
  var tiposInfraestrutura = tiposFiltro.filter(function(t){ return TIPOS_INFRA.indexOf(t) !== -1; });
  // cada visão mostra só o seu grupo de tipos (2.35.3.0); por isso não precisa mais da quebra de linha
  rotuloChips('Tipo', 'doc');
  tiposDocumento.forEach(function(t){ criarChipTipo(t, 'doc'); });
  if (tiposInfraestrutura.length) {
    rotuloChips('Tipo', 'infra');
    tiposInfraestrutura.forEach(function(t){ criarChipTipo(t, 'infra'); });
  }
  function criarChipTipo(t, grupo){
    var chip = document.createElement('button');
    chip.className = 'chip';
    chip.dataset.grupo = grupo;
    chip.textContent = t;
    chip.style.setProperty('--chip-c', TAG_COLORS[t]);
    chip.dataset.type = t;
    chip.addEventListener('click', function(){
      if (activeTypes.has(t)) { activeTypes.delete(t); chip.classList.remove('active'); }
      else { activeTypes.add(t); chip.classList.add('active'); }
      render();
    });
    chipRow.appendChild(chip);
  }

  // ---------- Build grid ----------
  var grid = document.getElementById('grid');
  var searchInput = document.getElementById('searchInput');
  var resultCount = document.getElementById('resultCount');
  var clearBtn = document.getElementById('clearBtn');

  // Copia pra área de transferência. Pelo IP/nome em http o navigator.clipboard não
  // existe (só em https/localhost), então cai no textarea + execCommand; se os dois
  // falharem, a promessa rejeita e quem chamou seleciona o texto pro Ctrl+C.
  function copiarTexto(texto){
    function viaTextarea(){
      var area = document.createElement('textarea');
      area.value = texto;
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.appendChild(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      area.remove();
      return ok ? Promise.resolve() : Promise.reject(new Error('sem acesso à área de transferência'));
    }
    if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto).catch(viaTextarea);
    return viaTextarea();
  }

  function escapeHtml(s){
    return s.replace(/[&<>"']/g, function(c){
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];
    });
  }

  var totalInfra = 0;
  clients.forEach(function(client, ci){
    var card = document.createElement('div');
    card.className = 'card';
    var nInfraCliente = infraDe(client).length + (client.servidores || []).reduce(function(s, g){ return s + g.itens.length; }, 0)
      + (client.aplicacoes || []).length;
    totalInfra += nInfraCliente;
    card.dataset.nMonitores = monitoresDe(client).length;
    card.dataset.nInfra = nInfraCliente;
    card.style.setProperty('--d', (ci * 55) + 'ms');
    card.dataset.client = client.name.toLowerCase();

    var meta = CLIENT_META[client.name] || { color: 'oklch(0.6 0.02 240)', initials: client.name.slice(0,2).toUpperCase() };
    var head = document.createElement('div');
    head.className = 'card-head';
    head.innerHTML =
      '<div class="card-head-left">' +
        (meta.logo
          ? '<div class="logo-badge com-logo" style="background:' + (meta.logoBg || 'transparent') + '"><img src="' + meta.logo + '" alt="' + escapeHtml(client.name) + '"></div>'
          : '<div class="logo-badge" style="background:' + meta.color + (meta.initials.length > 2 ? ';font-size:0.68rem' : '') + '">' + meta.initials + '</div>') +
        '<div><h2>' + escapeHtml(client.name) + '</h2>' +
        (client.sub ? '<div class="csub">' + escapeHtml(client.sub) + '</div>' : '') + '</div>' +
      '</div>' +
      '<span class="count-badge">' + (monitoresDe(client).length === 0 ? (client.links.length ? 'só infra' : 'em breve') : monitoresDe(client).length + ' monitor' + (monitoresDe(client).length > 1 ? 'es' : '')) + '</span>';
    card.appendChild(head);

    var list = document.createElement('div');
    list.className = 'link-list';

    function criarLink(link){
      var a = document.createElement('a');
      a.className = 'link-btn' + (link.infra ? ' infra' : '');
      a.href = link.url;
      a.target = '_blank';
      a.rel = 'noopener noreferrer';
      a.style.setProperty('--tag-c', TAG_COLORS[link.type] || TAG_COLORS['Outros']);
      a.dataset.type = link.type;
      a.dataset.env = link.env;
      a.dataset.search = (client.name + ' ' + link.label + ' ' + link.type + ' ' + link.env).toLowerCase();
      a.title = link.label + ' · ' + (link.env === 'HML' ? 'Homologação' : 'Produção');
      a.innerHTML =
        '<span class="tag">' + escapeHtml(link.type) + '</span>' +
        '<span class="lbl">' + escapeHtml(link.label) + '</span>' +
        '<span class="env ' + link.env.toLowerCase() + '">' + escapeHtml(link.env) + '</span>' +
        '<svg class="go" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 17 17 7M9 7h8v8"/></svg>';
      return a;
    }
    monitoresDe(client).forEach(function(link){ list.appendChild(criarLink(link)); });

    if (client.links.length === 0) {
      var vazio = document.createElement('div');
      vazio.className = 'link-vazio';
      vazio.textContent = 'Links dos ambientes em breve';
      list.appendChild(vazio);
    }

    card.appendChild(list);

    var infra = infraDe(client);
    var servidores = client.servidores || [];
    var aplicacoes = client.aplicacoes || [];
    if (infra.length || servidores.length || aplicacoes.length) {
      var titulo = document.createElement('div');
      titulo.className = 'infra-titulo';
      titulo.textContent = 'Infraestrutura';
      card.appendChild(titulo);
      var listaInfra = document.createElement('div');
      listaInfra.className = 'infra-list';
      infra.forEach(function(link){ listaInfra.appendChild(criarLink(link)); });
      servidores.forEach(function(s){
        var bloco = document.createElement('div');
        bloco.className = 'srv-grupo';
        bloco.dataset.type = 'Servidor';
        bloco.dataset.env = s.env;
        bloco.dataset.search = (client.name + ' servidor ' + s.grupo + ' ' + s.itens.join(' ') + ' ' + s.env).toLowerCase();
        bloco.innerHTML =
          '<div class="srv-cab">' + escapeHtml(s.grupo) + ' <span class="env ' + s.env.toLowerCase() + '">' + s.env + '</span></div>' +
          '<div class="srv-chips">' + s.itens.map(function(h){
            return '<button type="button" class="srv-chip" title="Clique pra copiar" data-host="' + escapeHtml(h) + '">' + escapeHtml(h) + '</button>';
          }).join('') + '</div>';
        listaInfra.appendChild(bloco);
      });
      if (aplicacoes.length) {
        var tituloApp = document.createElement('div');
        tituloApp.className = 'app-srv-titulo';
        tituloApp.innerHTML = 'Produtos por servidor <span class="dica">clique num produto pra ver onde ele roda</span>';
        listaInfra.appendChild(tituloApp);
      }
      aplicacoes.forEach(function(s){
        var linha = document.createElement('div');
        linha.className = 'srv-grupo app-srv';
        linha.dataset.type = 'Servidor';
        linha.dataset.env = s.env;
        linha.dataset.produtos = '|' + s.produtos.join('|') + '|';
        linha.dataset.search = (client.name + ' servidor ' + s.host + ' ' + s.produtos.join(' ') + ' ' + s.env).toLowerCase();
        linha.innerHTML =
          '<div class="app-host"><button type="button" class="srv-chip" title="Clique pra copiar" data-host="' + escapeHtml(s.host) + '">'
          + escapeHtml(s.host) + '</button><span class="app-qtd">' + s.produtos.length + (s.produtos.length === 1 ? ' produto' : ' produtos') + '</span></div>'
          + '<div class="app-prods">' + s.produtos.map(function(p){
            return '<button type="button" class="app-prod fam-' + familiaProduto(p) + '" data-prod="' + escapeHtml(p) + '">' + escapeHtml(p) + '</button>';
          }).join('') + '</div>';
        listaInfra.appendChild(linha);
      });
      listaInfra.addEventListener('click', function(ev){
        var prod = ev.target.closest('.app-prod');
        if (prod) { destacarProduto(listaInfra, prod.dataset.prod); return; }
        var chip = ev.target.closest('.srv-chip');
        if (!chip) return;
        var host = chip.dataset.host;
        copiarTexto(host).then(function(){
          chip.classList.add('copiado');
          chip.textContent = 'copiado ✓';
          setTimeout(function(){ chip.classList.remove('copiado'); chip.textContent = host; }, 1200);
        }, function(){
          // não deu pra copiar sozinho: deixa o endereço selecionado pro Ctrl+C
          var faixa = document.createRange();
          faixa.selectNodeContents(chip);
          var sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(faixa);
          chip.title = 'Selecionado · aperte Ctrl+C';
        });
      });
      card.appendChild(listaInfra);
    }
    grid.appendChild(card);
  });

  // empty state
  var emptyState = document.createElement('div');
  emptyState.className = 'empty-state';
  emptyState.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>' +
    '<p>Nenhum monitor encontrado para esses filtros.</p>';
  emptyState.style.display = 'none';
  grid.appendChild(emptyState);

  // ---------- Visão: Monitores x Infraestrutura ----------
  var modo = 'monitores';
  try { if (localStorage.getItem('central-modo') === 'infra') modo = 'infra'; } catch (e) { /* sem localStorage: fica em Monitores */ }
  // Editar (3.2.8.0): só pra quem pode; depois de salvar a página recarrega e volta direto pro editor
  var PODE_EDITAR = __PODE_EDITAR_CENTRAL__;
  var VERSAO_CENTRAL = '__VERSAO_CENTRAL__';
  var DADOS_EDICAO = __CENTRAL_EDICAO__;
  var btnModoEditar = document.querySelector('.modo-btn[data-modo="editar"]');
  if (btnModoEditar) btnModoEditar.hidden = !PODE_EDITAR;
  try { if (PODE_EDITAR && sessionStorage.getItem('central-reabrir-editor')) { modo = 'editar'; sessionStorage.removeItem('central-reabrir-editor'); } } catch (e) {}
  document.getElementById('nModoMonitores').textContent = totalMonitors;
  document.getElementById('nModoInfra').textContent = totalInfra;
  var botoesModo = document.querySelectorAll('.modo-btn');
  function aplicarModo(novo){
    if (novo === 'editar' && !PODE_EDITAR) novo = 'monitores';
    modo = novo;
    document.body.classList.toggle('editando', modo === 'editar');
    document.getElementById('editorCentral').hidden = modo !== 'editar';
    if (modo === 'editar') { botoesModo.forEach(function(b){ var a = b.dataset.modo === 'editar'; b.classList.toggle('ativo', a); b.setAttribute('aria-selected', a ? 'true' : 'false'); }); edIniciar(); return; }
    try { localStorage.setItem('central-modo', modo); } catch (e) { /* só não lembra da escolha */ }
    botoesModo.forEach(function(b){
      var ativo = b.dataset.modo === modo;
      b.classList.toggle('ativo', ativo);
      b.setAttribute('aria-selected', ativo ? 'true' : 'false');
    });
    grid.classList.toggle('modo-monitores', modo === 'monitores');
    grid.classList.toggle('modo-infra', modo === 'infra');
    chipRow.classList.toggle('modo-monitores', modo === 'monitores');
    chipRow.classList.toggle('modo-infra', modo === 'infra');
    // filtro de tipo da outra visão ficaria ativo e escondido: desmarca
    chipRow.querySelectorAll('.chip[data-grupo]').forEach(function(c){
      if (c.dataset.grupo !== (modo === 'infra' ? 'infra' : 'doc') && activeTypes.has(c.dataset.type)) {
        activeTypes.delete(c.dataset.type);
        c.classList.remove('active');
      }
    });
    searchInput.placeholder = modo === 'infra'
      ? 'Buscar por cliente, RabbitMQ, Graylog, FTP, servidor ou IP…'
      : 'Buscar por cliente, monitor ou tipo de documento…';
    emptyState.querySelector('p').textContent = modo === 'infra'
      ? 'Nenhum acesso de infraestrutura encontrado para esses filtros.'
      : 'Nenhum monitor encontrado para esses filtros.';
    render();
  }
  botoesModo.forEach(function(b){ b.addEventListener('click', function(){ if (b.dataset.modo !== modo) aplicarModo(b.dataset.modo); }); });

  function render(){
    var q = searchInput.value.trim().toLowerCase();
    var cards = grid.querySelectorAll('.card');
    var visiveisNaVisao = 0;
    var visibleClients = 0;
    var seletorVisao = modo === 'infra' ? '.infra-list .link-btn, .infra-list .srv-grupo' : '.link-list .link-btn';

    cards.forEach(function(card){
      var links = card.querySelectorAll('.link-btn, .srv-grupo');
      var daVisao = card.querySelectorAll(seletorVisao);
      var anyVisible = false;

      links.forEach(function(link){ link.classList.add('dim'); });  // o que não é da visão fica escondido
      daVisao.forEach(function(link){
        var matchesType = activeTypes.size === 0 || activeTypes.has(link.dataset.type);
        var matchesEnv = activeEnvs.size === 0 || activeEnvs.has(link.dataset.env);
        var matchesSearch = !q || link.dataset.search.indexOf(q) !== -1;
        var show = matchesType && matchesEnv && matchesSearch;
        link.classList.toggle('dim', !show);
        if (!show) return;
        anyVisible = true;
        visiveisNaVisao += link.classList.contains('srv-grupo') ? link.querySelectorAll('.srv-chip').length : 1;
      });

      // cliente sem links ainda: aparece só na visão Monitores, sem filtro de tipo, ou quando a busca bate no nome dele
      if (links.length === 0) {
        anyVisible = modo === 'monitores' && activeTypes.size === 0 && activeEnvs.size === 0 && (!q || card.dataset.client.indexOf(q) !== -1);
      }

      // o selo do card conta o que a visão mostra
      var selo = card.querySelector('.count-badge');
      if (selo) {
        if (modo === 'infra') {
          var nInfra = Number(card.dataset.nInfra);
          selo.textContent = nInfra + (nInfra === 1 ? ' acesso' : ' acessos');
        } else {
          var nMon = Number(card.dataset.nMonitores);
          selo.textContent = nMon ? nMon + ' monitor' + (nMon > 1 ? 'es' : '') : (links.length ? 'só infra' : 'em breve');
        }
      }

      card.classList.toggle('hidden', !anyVisible);
      if (anyVisible) visibleClients++;
    });

    emptyState.style.display = visibleClients === 0 ? 'block' : 'none';
    resultCount.textContent = (modo === 'infra'
      ? visiveisNaVisao + (visiveisNaVisao !== 1 ? ' acessos' : ' acesso')
      : visiveisNaVisao + ' monitor' + (visiveisNaVisao !== 1 ? 'es' : '')) +
      ' · ' + visibleClients + ' cliente' + (visibleClients !== 1 ? 's' : '');
    clearBtn.disabled = (q === '' && activeTypes.size === 0 && activeEnvs.size === 0);
    organizarColunas();
  }

  // Cards organizados pelo tamanho (2.34.7.0): do cliente com mais acessos visíveis
  // pro menor, cada um entra na coluna mais curta naquele momento. Refaz a cada
  // filtro (o tamanho muda) e quando a largura muda o número de colunas.
  var LARGURA_MIN_COLUNA = 300, ESPACO_COLUNAS = 20;
  function organizarColunas(){
    var cards = Array.prototype.slice.call(grid.querySelectorAll('.card'));
    var largura = grid.clientWidth || window.innerWidth;
    var n = Math.max(1, Math.floor((largura + ESPACO_COLUNAS) / (LARGURA_MIN_COLUNA + ESPACO_COLUNAS)));
    var colunas = Array.prototype.slice.call(grid.querySelectorAll('.coluna-grid'));
    if (colunas.length !== n) {
      colunas.forEach(function(c){ c.remove(); });
      colunas = [];
      for (var i = 0; i < n; i++) {
        var col = document.createElement('div');
        col.className = 'coluna-grid';
        grid.insertBefore(col, emptyState);
        colunas.push(col);
      }
    }
    var alturas = colunas.map(function(){ return 0; });
    function tamanho(card){ return card.querySelectorAll('.link-btn:not(.dim), .srv-grupo:not(.dim) .srv-chip').length; }
    var visiveis = cards.filter(function(c){ return !c.classList.contains('hidden'); });
    var escondidos = cards.filter(function(c){ return c.classList.contains('hidden'); });
    // mede cada card já na largura de coluna (as colunas têm a mesma largura); fora dela
    // a altura sai errada e as colunas ficam desequilibradas
    visiveis.forEach(function(card){ colunas[0].appendChild(card); });
    var altura = new Map(visiveis.map(function(card){ return [card, card.offsetHeight]; }));
    visiveis.sort(function(a, b){ return altura.get(b) - altura.get(a) || tamanho(b) - tamanho(a) || a.dataset.client.localeCompare(b.dataset.client); });
    visiveis.forEach(function(card){
      var menor = alturas.indexOf(Math.min.apply(null, alturas));
      colunas[menor].appendChild(card);
      alturas[menor] += altura.get(card) + ESPACO_COLUNAS;
    });
    escondidos.forEach(function(card){ colunas[0].appendChild(card); });
  }
  var colunasAgendadas = null;
  window.addEventListener('resize', function(){
    cancelAnimationFrame(colunasAgendadas);
    colunasAgendadas = requestAnimationFrame(organizarColunas);
  });

  // ---------- Editar (3.2.8.0) ----------
  // Tudo é editado numa cópia local; "Salvar alterações" manda a lista inteira pro servidor, que confere cada campo
  // (a página é pública) e recusa se outra pessoa salvou no meio. Logo embutida no PDA vem como "embutido:NOME".
  var ED = null;
  var TIPOS_ED = TYPES.concat(['Outros']);
  function edClone(o){ return JSON.parse(JSON.stringify(o)); }
  function edIniciar(){
    if (ED) return;
    var base = edClone(DADOS_EDICAO || []);
    base.forEach(function(c){ c._orig = c.name; });
    ED = { clientes: base, sel: base.length ? 0 : -1, sujo: false };
    edDesenharTudo();
  }
  function edAtual(){ return ED.sel >= 0 ? ED.clientes[ED.sel] : null; }
  function edMarcar(){ ED.sujo = true; edEstado(); }
  function edEstado(){
    var el = document.getElementById('edEstado');
    el.textContent = ED.sujo ? 'Alterações não salvas' : 'Sem alterações';
    el.classList.toggle('sujo', ED.sujo);
    document.getElementById('edSalvar').disabled = !ED.sujo;
  }
  function edErro(msg){
    var el = document.getElementById('edErro');
    el.hidden = !msg;
    el.textContent = msg || '';
    if (msg) el.scrollIntoView({ block: 'nearest' });
  }
  function edLogoSrc(c){
    if (!c.logo) return '';
    if (c.logo.indexOf('embutido:') === 0) { var m = CLIENT_META[c._orig]; return (m && m.logo) || ''; }
    return c.logo;
  }
  function edBadge(c, grande){
    var src = edLogoSrc(c);
    var cls = 'ed-badge' + (grande ? ' grande' : '');
    if (src) return '<span class="' + cls + ' com-logo" style="background:' + escapeHtml(c.logoBg || 'transparent') + '"><img src="' + escapeHtml(src) + '" alt=""></span>';
    return '<span class="' + cls + '" style="background:' + escapeHtml(c.color || 'oklch(0.6 0.02 240)') + '">' + escapeHtml(c.initials || String(c.name || '?').slice(0, 2).toUpperCase()) + '</span>';
  }
  function edOpcoes(lista, atual){
    return lista.map(function(v){ return '<option' + (v === atual ? ' selected' : '') + '>' + escapeHtml(v) + '</option>'; }).join('');
  }
  function edDesenharTudo(){ edDesenharLista(); edDesenharForm(); edEstado(); edErro(''); }
  function edDesenharLista(){
    document.getElementById('edClientes').innerHTML = ED.clientes.map(function(c, i){
      var n = c.links.length + c.servidores.length + c.aplicacoes.length;
      return '<button type="button" class="ed-cli' + (i === ED.sel ? ' ativo' : '') + '" data-cli="' + i + '">' + edBadge(c)
        + '<span class="nm">' + escapeHtml(c.name || '(sem nome)') + '</span><span class="qt">' + n + '</span>'
        + '<span class="mv"><span data-mover="-1" title="Subir">&#8593;</span><span data-mover="1" title="Descer">&#8595;</span></span></button>';
    }).join('') || '<div class="ed-vazio">Nenhum cliente.</div>';
  }
  function edCampo(rotulo, html){ return '<div class="ed-campo"><label>' + rotulo + '</label>' + html + '</div>'; }
  function edHex(v){ return /^#[0-9a-fA-F]{6}$/.test(v || '') ? v : '#2db8cf'; }
  function edDesenharForm(){
    var c = edAtual();
    var f = document.getElementById('edForm');
    if (!c) { f.innerHTML = '<div class="ed-vazio">Escolha um cliente na lista ou crie um novo.</div>'; return; }
    var h = '<h3>Cliente</h3><div class="ed-campos">'
      + edCampo('Nome', '<input type="text" maxlength="40" data-c="name" value="' + escapeHtml(c.name) + '">')
      + edCampo('Subtítulo (opcional)', '<input type="text" maxlength="60" data-c="sub" value="' + escapeHtml(c.sub || '') + '">')
      + edCampo('Iniciais (sem logo)', '<input type="text" maxlength="3" data-c="initials" value="' + escapeHtml(c.initials || '') + '">')
      + edCampo('Cor (sem logo)', '<div class="ed-cor"><input type="color" data-cor="color" value="' + edHex(c.color) + '"><input type="text" maxlength="160" data-c="color" value="' + escapeHtml(c.color || '') + '"></div>')
      + '</div>'
      + '<h3>Logo</h3><div class="ed-logo">' + edBadge(c, true)
      + '<label class="ed-btn sec mini">Trocar logo<input type="file" accept="image/png,image/jpeg,image/webp,image/gif" data-logo hidden></label>'
      + (c.logo ? '<button type="button" class="ed-btn sec mini" data-acao="tirar-logo">Tirar logo</button>' : '')
      + edCampo('Fundo atrás da logo', '<div class="ed-cor"><input type="color" data-cor="logoBg" value="' + edHex(c.logoBg) + '"><input type="text" maxlength="160" data-c="logoBg" placeholder="transparente" value="' + escapeHtml(c.logoBg || '') + '"></div>')
      + '</div>';
    h += '<h3>Links (monitores e infraestrutura)</h3>';
    h += c.links.length ? c.links.map(function(l, i){
      return '<div class="ed-linha lk" data-l="' + i + '">'
        + '<select data-f="type" aria-label="Tipo">' + edOpcoes(TIPOS_ED, l.type) + '</select>'
        + '<input type="text" maxlength="50" data-f="label" placeholder="Nome" value="' + escapeHtml(l.label) + '">'
        + '<input type="url" maxlength="500" data-f="url" placeholder="https://..." value="' + escapeHtml(l.url) + '">'
        + '<select data-f="env" aria-label="Ambiente">' + edOpcoes(ENVS, l.env || 'PRD') + '</select>'
        + '<label class="ed-infra" title="Mostrar na visão Infraestrutura mesmo sendo de outro tipo"><input type="checkbox" data-f="grupo"' + (l.grupo === 'infra' ? ' checked' : '') + '>Infra</label>'
        + '<span class="acoes"><button type="button" class="ed-btn mini" data-acao="sobe-l" title="Subir">&#8593;</button><button type="button" class="ed-btn mini" data-acao="desce-l" title="Descer">&#8595;</button><button type="button" class="ed-btn mini perigo" data-acao="tira-l" title="Tirar">&#215;</button></span></div>';
    }).join('') : '<div class="ed-vazio">Nenhum link.</div>';
    h += '<button type="button" class="ed-btn sec mini" data-acao="add-l">+ Adicionar link</button>';
    h += '<h3>Servidores (copiam o endereço ao clicar)</h3>';
    h += c.servidores.length ? c.servidores.map(function(s, i){
      return '<div class="ed-linha sv" data-s="' + i + '">'
        + '<input type="text" maxlength="40" data-f="grupo" placeholder="Grupo (ex.: Jumper)" value="' + escapeHtml(s.grupo) + '">'
        + '<select data-f="env" aria-label="Ambiente">' + edOpcoes(ENVS, s.env || 'PRD') + '</select>'
        + '<textarea data-f="itens" placeholder="Um endereço por linha">' + escapeHtml(s.itens.join(String.fromCharCode(10))) + '</textarea>'
        + '<span class="acoes"><button type="button" class="ed-btn mini perigo" data-acao="tira-s" title="Tirar">&#215;</button></span></div>';
    }).join('') : '<div class="ed-vazio">Nenhum grupo de servidores.</div>';
    h += '<button type="button" class="ed-btn sec mini" data-acao="add-s">+ Grupo de servidores</button>';
    h += '<h3>Produtos por servidor</h3>';
    h += c.aplicacoes.length ? c.aplicacoes.map(function(a, i){
      return '<div class="ed-linha ap" data-a="' + i + '">'
        + '<input type="text" maxlength="120" data-f="host" placeholder="IP ou nome do servidor" value="' + escapeHtml(a.host) + '">'
        + '<select data-f="env" aria-label="Ambiente">' + edOpcoes(ENVS, a.env || 'PRD') + '</select>'
        + '<input type="text" data-f="produtos" placeholder="Produtos separados por vírgula" value="' + escapeHtml(a.produtos.join(', ')) + '">'
        + '<span class="acoes"><button type="button" class="ed-btn mini perigo" data-acao="tira-a" title="Tirar">&#215;</button></span></div>';
    }).join('') : '<div class="ed-vazio">Nenhum servidor com produtos.</div>';
    h += '<button type="button" class="ed-btn sec mini" data-acao="add-a">+ Servidor com produtos</button>';
    h += '<div class="ed-rodape"><button type="button" class="ed-btn perigo" data-acao="excluir">Excluir o cliente ' + escapeHtml(c.name) + '</button></div>';
    f.innerHTML = h;
  }
  function edSeparar(texto, sep){
    return String(texto || '').split(sep).map(function(x){ return x.trim(); }).filter(Boolean);
  }
  function edAoDigitar(e){
    var c = edAtual();
    var el = e.target;
    if (!c) return;
    if (el.dataset.c) { c[el.dataset.c] = el.value; if (el.dataset.c === 'color' || el.dataset.c === 'logoBg') { var p = el.parentNode.querySelector('input[type=color]'); if (p && /^#[0-9a-fA-F]{6}$/.test(el.value)) p.value = el.value; } }
    else if (el.dataset.cor) { c[el.dataset.cor] = el.value; var tx = el.parentNode.querySelector('input[type=text]'); if (tx) tx.value = el.value; }
    else if (el.dataset.f) {
      var linha = el.closest('[data-l],[data-s],[data-a]');
      if (!linha) return;
      if (linha.dataset.l !== undefined) {
        var l = c.links[+linha.dataset.l];
        if (el.dataset.f === 'grupo') l.grupo = el.checked ? 'infra' : ''; else l[el.dataset.f] = el.value;
      } else if (linha.dataset.s !== undefined) {
        var s = c.servidores[+linha.dataset.s];
        s[el.dataset.f] = el.dataset.f === 'itens' ? edSeparar(el.value, String.fromCharCode(10)) : el.value;
      } else {
        var a = c.aplicacoes[+linha.dataset.a];
        a[el.dataset.f] = el.dataset.f === 'produtos' ? edSeparar(el.value, ',') : el.value;
      }
    } else return;
    edMarcar();
    edDesenharLista();
    if (el.dataset.c || el.dataset.cor) { var b = document.querySelector('#edForm .ed-badge.grande'); if (b) b.outerHTML = edBadge(c, true); }
  }
  function edMover(lista, i, d){
    var j = i + d;
    if (j < 0 || j >= lista.length) return false;
    var x = lista[i]; lista[i] = lista[j]; lista[j] = x;
    return true;
  }
  function edNomeLivre(base){
    var nome = base, n = 2;
    var usados = ED.clientes.map(function(c){ return String(c.name).toLowerCase(); });
    while (usados.indexOf(nome.toLowerCase()) !== -1) nome = base + ' ' + (n++);
    return nome;
  }
  function edCarregarLogo(arquivo){
    var c = edAtual();
    if (!c || !arquivo) return;
    if (!/^image[/](png|jpeg|webp|gif)$/.test(arquivo.type)) { edErro('A logo precisa ser PNG, JPG, WebP ou GIF.'); return; }
    var leitor = new FileReader();
    leitor.onload = function(){
      var img = new Image();
      img.onload = function(){
        // reduz pra 128x128 sem distorcer (fundo transparente); GIF animado fica parado no primeiro quadro
        var tam = 128, canvas = document.createElement('canvas');
        canvas.width = canvas.height = tam;
        var esc = Math.min(tam / img.width, tam / img.height, 1);
        var w = Math.round(img.width * esc), hh = Math.round(img.height * esc);
        canvas.getContext('2d').drawImage(img, Math.round((tam - w) / 2), Math.round((tam - hh) / 2), w, hh);
        c.logo = canvas.toDataURL('image/png');
        edMarcar(); edDesenharLista(); edDesenharForm(); edErro('');
      };
      img.onerror = function(){ edErro('Não foi possível abrir essa imagem.'); };
      img.src = leitor.result;
    };
    leitor.readAsDataURL(arquivo);
  }
  function edAoClicar(e){
    var cli = e.target.closest('[data-cli]');
    if (cli && e.currentTarget.id === 'edClientes') {
      var i = +cli.dataset.cli, mv = e.target.closest('[data-mover]');
      if (mv) { if (edMover(ED.clientes, i, +mv.dataset.mover)) { if (ED.sel === i) ED.sel = i + (+mv.dataset.mover); else if (ED.sel === i + (+mv.dataset.mover)) ED.sel = i; edMarcar(); } edDesenharLista(); return; }
      ED.sel = i; edDesenharLista(); edDesenharForm(); return;
    }
    var bt = e.target.closest('[data-acao]');
    var c = edAtual();
    if (!bt || !c) return;
    var linha = bt.closest('[data-l],[data-s],[data-a]');
    var idx = linha ? +(linha.dataset.l || linha.dataset.s || linha.dataset.a) : -1;
    switch (bt.dataset.acao) {
      case 'add-l': c.links.push({ label: '', type: 'NFe', url: '', env: 'PRD', grupo: '' }); break;
      case 'tira-l': c.links.splice(idx, 1); break;
      case 'sobe-l': if (!edMover(c.links, idx, -1)) return; break;
      case 'desce-l': if (!edMover(c.links, idx, 1)) return; break;
      case 'add-s': c.servidores.push({ grupo: '', env: 'PRD', itens: [] }); break;
      case 'tira-s': c.servidores.splice(idx, 1); break;
      case 'add-a': c.aplicacoes.push({ host: '', env: 'PRD', produtos: [] }); break;
      case 'tira-a': c.aplicacoes.splice(idx, 1); break;
      case 'tirar-logo': c.logo = ''; break;
      case 'excluir':
        if (!confirm('Excluir o cliente ' + c.name + ' da Central? Só vale depois de salvar.')) return;
        ED.clientes.splice(ED.sel, 1);
        ED.sel = Math.min(ED.sel, ED.clientes.length - 1);
        break;
      default: return;
    }
    edMarcar(); edDesenharLista(); edDesenharForm();
    if (bt.dataset.acao.indexOf('add-') === 0) { var ult = document.querySelectorAll('#edForm .ed-linha'); var campos = Array.prototype.filter.call(ult, function(x){ return x.dataset[bt.dataset.acao.slice(4)] !== undefined; }); if (campos.length) { var foco = campos[campos.length - 1].querySelector('input'); if (foco) foco.focus(); } }
  }
  function edParaSalvar(){
    return ED.clientes.map(function(c){
      var x = edClone(c);
      delete x._orig;
      if (x.logo && x.logo.indexOf('embutido:') === 0) x.logo = '__' + x.logo.slice(9) + '__';
      x.servidores = x.servidores.filter(function(s){ return s.grupo || s.itens.length; });
      x.aplicacoes = x.aplicacoes.filter(function(a){ return a.host || a.produtos.length; });
      return x;
    });
  }
  async function edSalvar(){
    var bt = document.getElementById('edSalvar');
    bt.disabled = true; bt.textContent = 'Salvando...';
    edErro('');
    try {
      var resp = await fetch('/api/central-monitores/salvar', { method: 'POST',
        body: new URLSearchParams({ dados: JSON.stringify(edParaSalvar()), versao: VERSAO_CENTRAL }) });
      if (resp.status === 401) { edErro('Sua sessão no PDA expirou: entre de novo no PDA (em outra aba) e salve outra vez.'); return; }
      var r = await resp.json();
      if (!r.ok) { edErro(r.erro || 'Não foi possível salvar.'); return; }
      ED.sujo = false;
      try { sessionStorage.setItem('central-reabrir-editor', '1'); } catch (e) {}
      location.reload();
    } catch (e) {
      edErro('Não foi possível salvar agora (' + e.message + ').');
    } finally {
      bt.textContent = 'Salvar alterações';
      if (ED && ED.sujo) bt.disabled = false;
    }
  }
  document.getElementById('edForm').addEventListener('input', edAoDigitar);
  document.getElementById('edForm').addEventListener('change', function(e){
    if (e.target.dataset.logo !== undefined) { edCarregarLogo(e.target.files && e.target.files[0]); e.target.value = ''; return; }
    if (e.target.type === 'checkbox' || e.target.tagName === 'SELECT') edAoDigitar(e);
  });
  document.getElementById('edForm').addEventListener('click', edAoClicar);
  document.getElementById('edClientes').addEventListener('click', edAoClicar);
  document.getElementById('edNovo').addEventListener('click', function(){
    ED.clientes.push({ name: edNomeLivre('Novo cliente'), sub: '', color: '#2db8cf', initials: 'NC', logo: '', logoBg: '', links: [], servidores: [], aplicacoes: [], _orig: '' });
    ED.sel = ED.clientes.length - 1;
    edMarcar(); edDesenharLista(); edDesenharForm();
    var nome = document.querySelector('#edForm input[data-c="name"]'); if (nome) { nome.focus(); nome.select(); }
  });
  document.getElementById('edSalvar').addEventListener('click', edSalvar);
  document.getElementById('edDescartar').addEventListener('click', function(){
    if (ED && ED.sujo && !confirm('Descartar todas as alterações que ainda não foram salvas?')) return;
    ED = null; edIniciar();
  });
  window.addEventListener('beforeunload', function(e){ if (ED && ED.sujo) { e.preventDefault(); e.returnValue = ''; } });

  searchInput.addEventListener('input', render);
  clearBtn.addEventListener('click', function(){
    searchInput.value = '';
    activeTypes.clear();
    activeEnvs.clear();
    chipRow.querySelectorAll('.chip').forEach(function(c){ c.classList.remove('active'); });
    render();
  });

  aplicarModo(modo);
</script>
</body>
</html>
"""
