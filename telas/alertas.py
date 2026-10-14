"""Tela Alertas Suporte.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_HTML_PAGE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .resumo { display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
  .cartao { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            padding: 12px 18px; min-width: 110px; }
  .cartao .num { font-size: 22px; font-weight: 700; }
  .cartao .rot { font-size: 11px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .04em; }
  .cabecalho-secao { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
  .cabecalho-secao h3 { margin: 0; }
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(var(--tinta),.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: rgba(var(--tinta),.06); }
  .status { font-weight: 600; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  h3 { color: var(--accent); margin: 22px 0 8px 0; font-size: 14px; }
</style>
</head>
<body>
__NAVBAR__

  <div class="conteudo">
    <div class="cabecalho-secao">
      <h3 style="margin-top:0" id="atualizado">carregando...</h3>
      <button class="btn-accent" onclick="executarTodos()">Executar todos agora</button>
    </div>

    <div class="resumo" id="resumo"></div>

    <div class="painel">
      <table>
        <thead>
          <tr>
            <th>Alerta</th><th>Status</th><th>Última execução</th>
            <th>Próxima execução</th><th>Último erro</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela"></tbody>
      </table>
    </div>
  </div>

<script>
const CORES_STATUS = {Aguardando: 'var(--wait)', Executando: 'var(--run)', OK: 'var(--ok)', Erro: 'var(--erro)'};
let linhasTabelaCriadas = false;
let ultimoResumoAssinatura = '';

function idLinha(nome) {
  return 'linha-' + nome.replace(/[^a-zA-Z0-9]/g, '_');
}

function montarLinhasTabela(jobs) {
  const corpo = document.getElementById('corpo-tabela');
  corpo.innerHTML = '';
  for (const job of jobs) {
    const tr = document.createElement('tr');
    tr.id = idLinha(job.nome);
    tr.innerHTML = `
      <td>${job.nome}</td>
      <td class="status" data-campo="status"></td>
      <td data-campo="ultima"></td>
      <td data-campo="proxima"></td>
      <td data-campo="erro"></td>
      <td><button class="btn-mini" onclick="executarUm('${job.nome.replace(/'/g, "\\\\'")}')">Executar</button></td>
    `;
    corpo.appendChild(tr);
  }
  linhasTabelaCriadas = true;
}

// Só escreve no DOM os campos que de fato mudaram desde o último poll -
// evita recriar a tabela inteira a cada 2s (menos flicker, menos trabalho
// de layout/reflow do navegador, preserva seleção de texto etc.)
function atualizarLinha(job) {
  const tr = document.getElementById(idLinha(job.nome));
  if (!tr) return;
  const campoStatus = tr.querySelector('[data-campo="status"]');
  if (campoStatus.dataset.valor !== job.status) {
    campoStatus.innerText = job.status;
    campoStatus.style.color = job.cor;
    campoStatus.dataset.valor = job.status;
  }
  const campos = {ultima: job.ultima || '-', proxima: job.proxima || '-', erro: job.erro || ''};
  for (const nomeCampo in campos) {
    const el = tr.querySelector(`[data-campo="${nomeCampo}"]`);
    if (el.dataset.valor !== campos[nomeCampo]) {
      el.innerText = campos[nomeCampo];
      el.dataset.valor = campos[nomeCampo];
    }
  }
}

async function carregarStatus() {
  try {
    const resp = await fetch('/api/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();

    document.getElementById('atualizado').innerText =
      'Atualizado às ' + new Date().toLocaleTimeString('pt-BR');

    const contagem = {Aguardando: 0, Executando: 0, OK: 0, Erro: 0};
    for (const job of dados.jobs) { contagem[job.status] = (contagem[job.status] || 0) + 1; }
    const assinaturaResumo = JSON.stringify(contagem);
    if (assinaturaResumo !== ultimoResumoAssinatura) {
      const resumo = document.getElementById('resumo');
      resumo.innerHTML = Object.entries(contagem).map(([status, n]) => `
        <div class="cartao">
          <div class="num" style="color:${CORES_STATUS[status]}">${n}</div>
          <div class="rot">${status}</div>
        </div>
      `).join('');
      ultimoResumoAssinatura = assinaturaResumo;
    }

    if (!linhasTabelaCriadas) montarLinhasTabela(dados.jobs);
    for (const job of dados.jobs) atualizarLinha(job);
  } catch (e) {
    document.getElementById('atualizado').innerText = 'Erro ao atualizar: ' + e;
  }
}

async function executarTodos() {
  await fetch('/api/run_all', { method: 'POST' });
  carregarStatus();
}

async function executarUm(nome) {
  await fetch('/api/run/' + encodeURIComponent(nome), { method: 'POST' });
  carregarStatus();
}

carregarStatus();
setInterval(carregarStatus, 2000);
</script>
__FOOTER__
</body>
</html>
"""
