"""Tela Automacao Movidesk.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_AUTOMACAO_MOVIDESK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Automação Movidesk</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-am { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1120px; margin: 0 auto 22px auto; }
  .cabecalho-am h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-am .sub { color: var(--fg-dim); font-size: 12.5px; }
  .filtro-am { display: flex; align-items: end; gap: 10px; }
  .filtro-am label { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 5px;
                      text-transform: uppercase; letter-spacing: .04em; }

  .painel-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1120px; margin: 0 auto 20px auto; }
  .painel-im h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }

  .tabela-im-rolagem { overflow-x: auto; border-radius: 10px; }
  table.tabela-im { width: 100%; border-collapse: collapse; min-width: 100%; }
  table.tabela-im th, table.tabela-im td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border);
                                             font-size: 12.5px; white-space: nowrap; overflow: hidden;
                                             text-overflow: ellipsis; max-width: 220px; }
  table.tabela-im th { color: var(--teal); font-weight: 600; text-transform: uppercase; font-size: 10.5px;
                        letter-spacing: .03em; background: rgba(var(--tinta),.03); position: sticky; top: 0; }
  table.tabela-im tbody tr { transition: background .12s; }
  table.tabela-im tbody tr:hover { background: rgba(var(--tinta),.03); }
  table.tabela-im tbody tr:nth-child(even) { background: rgba(var(--tinta),.015); }
  table.tabela-im tr:last-child td { border-bottom: none; }
  .vazio-im { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .erro-im { color: var(--erro); font-size: 12.5px; }
  .carregando-im { color: var(--fg-dim); font-size: 12.5px; }

  .aviso-em-breve-am { max-width: 1120px; margin: 0 auto 20px auto; color: var(--fg-dim); font-size: 12px;
                        line-height: 1.5; background: rgba(var(--tinta),.03); border: 1px dashed var(--border-forte);
                        border-radius: 10px; padding: 12px 16px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-am">
      <div>
        <h1>Automação Movidesk</h1>
        <div class="sub">NOC, Satisfação, Uptime, Tickets, GMUD, Jira e outras automações de atendimento.</div>
      </div>
    </div>

    <div class="aviso-em-breve-am">
      As demais automações de NOC/Satisfação/Uptime/GMUD/Jira ainda estão
      em construção - por enquanto esse card já traz o Controle de
      Sincronização, que estava misturado no Indicadores Movidesk antes.
    </div>

    <div class="painel-im">
      <h2>Controle de sincronização</h2>
      <div id="am-tabela-sincronizacao"><div class="carregando-im">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

<script>
function formatarNomeColuna(nomeCru) {
  if (!nomeCru.includes('_') && nomeCru !== nomeCru.toUpperCase()) {
    return nomeCru;
  }
  return nomeCru
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\\b\\w/g, c => c.toUpperCase());
}

function renderizarTabelaDinamica(linhas, elementoDestino) {
  if (!linhas || linhas.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum registro no período.</div>';
    return;
  }
  const colunas = Object.keys(linhas[0]);
  const cabecalho = colunas.map(c => `<th>${formatarNomeColuna(c)}</th>`).join('');
  const linhasHtml = linhas.slice(0, 200).map(l =>
    '<tr>' + colunas.map(c => `<td title="${String(l[c] ?? '').replace(/"/g, '&quot;')}">${l[c]}</td>`).join('') + '</tr>'
  ).join('');
  const avisoLimite = linhas.length > 200
    ? `<div class="vazio-im">Mostrando as primeiras 200 de ${linhas.length} linhas.</div>` : '';
  elementoDestino.innerHTML = `<div class="tabela-im-rolagem"><table class="tabela-im"><thead><tr>${cabecalho}</tr></thead><tbody>${linhasHtml}</tbody></table></div>${avisoLimite}`;
}

async function carregarSincronizacao() {
  const primeiroDiaMes = new Date().toISOString().slice(0, 8) + '01';
  const el = document.getElementById('am-tabela-sincronizacao');
  el.innerHTML = '<div class="carregando-im">Carregando...</div>';
  try {
    const resp = await fetch('/api/indicadores-movidesk?data_inicio=' + primeiroDiaMes);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      el.innerHTML = `<div class="erro-im">⚠ ${dados.erro || 'Não foi possível carregar.'}</div>`;
      return;
    }
    const sinc = dados.sincronizacao;
    if (sinc.ok) {
      renderizarTabelaDinamica(sinc.dados, el);
    } else {
      el.innerHTML = `<div class="erro-im">⚠ ${sinc.erro}</div>`;
    }
  } catch (e) {
    el.innerHTML = '<div class="erro-im">⚠ Erro ao carregar: ' + e + '</div>';
  }
}

carregarSincronizacao();
</script>
</body>
</html>
"""
