"""Tela Manutencao Rejeicoes.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_MANUTENCAO_REJEICOES_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção Rejeições em Banco</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: var(--largura-pagina); margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(var(--tinta),.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: var(--largura-pagina); }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .filtros-alertas { display: flex; gap: 10px; margin: 0 auto 14px auto; max-width: var(--largura-pagina); flex-wrap: wrap; }
  .filtros-alertas input[type="text"] { flex: 1; min-width: 180px; padding: 8px 12px; border-radius: 8px;
                    border: 1px solid var(--border); background: rgba(var(--poco),.28); color: var(--fg); font-size: 13px; }
  .filtros-alertas input[type="text"]:focus { outline: none; border-color: var(--teal); }
  .acoes-linha { display: flex; gap: 6px; }
  .dica-campo.dica-travado { color: var(--run); }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; padding: 24px; }
  .modal-fundo.aberto { display: flex; }
  .modal-largo { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 30px 32px; width: 100%; max-width: 560px; max-height: 88vh; overflow-y: auto;
           box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal-largo h3 { margin: 0 0 18px 0; font-size: 16px; color: var(--teal); }
  .modal-largo label { display: block; font-size: 11px; color: var(--fg-dim); margin: 14px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal-largo input, .modal-largo select, .modal-largo textarea {
                 width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(var(--poco),.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal-largo textarea { font-family: Consolas, monospace; font-size: 12.5px; resize: vertical; min-height: 90px; }
  .modal-largo input:focus, .modal-largo select:focus, .modal-largo textarea:focus {
                 outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .linha-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
  .dica-campo { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.4; }
  .acoes-modal { display: flex; gap: 8px; margin-top: 22px; }
  .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }

  .bloco-sucesso { text-align: center; }
  .bloco-sucesso .icone-ok { width: 52px; height: 52px; border-radius: 50%; background: rgba(78,201,176,.15);
                              display: flex; align-items: center; justify-content: center; margin: 0 auto 16px auto; }
  .bloco-sucesso .icone-ok svg { width: 26px; height: 26px; stroke: var(--ok); }
  .bloco-sucesso h4 { margin: 0 0 8px 0; font-size: 15px; }
  .bloco-sucesso p { color: var(--fg-dim); font-size: 12.5px; line-height: 1.6; text-align: left; }
  .bloco-gatilho { background: rgba(var(--poco),.25); border: 1px solid var(--border); border-radius: 10px;
                   padding: 14px 16px; text-align: left; font-family: Consolas, monospace; font-size: 12px;
                   margin: 14px 0; line-height: 1.8; }
  .bloco-gatilho b { color: var(--teal); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Rejeições cadastradas (CONFIGURACOES_REJEICAO)</h3>
      <button class="btn-accent" onclick="abrirModalNovaRejeicao()">+ Nova rejeição</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro-banco" style="display:none; max-width:var(--largura-pagina); margin:0 auto 16px auto;"></div>

    <div class="filtros-alertas">
      <input type="text" id="filtro-cliente" placeholder="Buscar por cliente, tipo ou agendamento..." oninput="aplicarFiltrosRejeicoes()">
    </div>

    <div class="painel">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Cliente</th><th>Tipo</th><th>Agendamento</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela-rejeicoes">
          <tr><td colspan="5" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-nova-rejeicao">
    <div class="modal-largo">
      <h3 id="titulo-modal-rejeicao">Nova rejeição em CONFIGURACOES_REJEICAO</h3>

      <div id="form-nova-rejeicao">
        <div class="linha-dupla">
          <div>
            <label>Cliente</label>
            <input type="text" id="rejeicao-cliente" placeholder="Nome do cliente">
          </div>
          <div>
            <label>Tipo de banco</label>
            <select id="rejeicao-tipo-banco">
              <option value="SQL">SQL Server</option>
              <option value="ORACLE">Oracle</option>
            </select>
          </div>
        </div>

        <label>Tipo de agendamento</label>
        <input type="text" id="rejeicao-tipo-agendamento" placeholder="Ex.: DIARIO">
        <div class="dica-campo">Campo obrigatório.</div>

        <label>Conexão</label>
        <select id="rejeicao-conexao-select" onchange="aplicarConexaoSelecionadaRejeicao()">
          <option value="">Selecione uma String Connection...</option>
        </select>
        <input type="hidden" id="rejeicao-conexao">
        <div class="dica-campo" id="dica-conexao-nao-cadastrada-rejeicao" style="display:none; color:var(--erro)">
          Esta rejeição usa uma conexão que não está cadastrada em String Connections - selecione uma da lista pra substituir.
        </div>

        <label>Script</label>
        <textarea id="rejeicao-script" placeholder="SELECT codigo_rejeicao, COUNT(*) FROM ..."></textarea>
        <div class="dica-campo">SQL puro - a conversão pra base64 é feita automaticamente. Precisa sempre retornar o código da rejeição E a quantidade, pra rejeição abrir corretamente.</div>

        <div class="erro-modal" id="erro-nova-rejeicao"></div>
        <div class="acoes-modal">
          <button class="btn-accent" id="botao-salvar-rejeicao" onclick="salvarRejeicaoBanco()" style="flex:1">Criar rejeição</button>
          <button onclick="fecharModalNovaRejeicao()" style="flex:1">Cancelar</button>
        </div>
      </div>

      <div id="sucesso-nova-rejeicao" style="display:none">
        <div class="bloco-sucesso">
          <div class="icone-ok">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
          </div>
          <h4>Rejeição criada com sucesso</h4>
          <p>
            Falta um passo manual: solicitar a criação do gatilho no Movidesk
            (peça pra algum N2 ou N3). Use estes dados na
            abertura do serviço:
          </p>
          <div class="bloco-gatilho" id="texto-gatilho-rejeicao"></div>
          <div class="acoes-modal">
            <button class="btn-accent" onclick="copiarTextoGatilhoRejeicao()" style="flex:1">Copiar texto</button>
            <button onclick="fecharModalNovaRejeicao()" style="flex:1">Fechar</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <div class="modal-fundo" id="modal-excluir-rejeicao">
    <div class="modal-largo" style="max-width:420px">
      <h3>Excluir rejeição</h3>
      <p style="color:var(--fg-dim); font-size:13px; line-height:1.6">
        Tem certeza que quer excluir a rejeição <b id="nome-rejeicao-excluir"></b>?
        Essa ação não pode ser desfeita.
      </p>
      <div class="erro-modal" id="erro-excluir-rejeicao"></div>
      <div class="acoes-modal">
        <button class="btn-mini btn-perigo" onclick="confirmarExclusaoRejeicao()" style="flex:1">Excluir</button>
        <button onclick="fecharModalExcluirRejeicao()" style="flex:1">Cancelar</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  __FOOTER__

<script>
let gatilhoAtualRejeicao = null;
let idEmEdicaoRejeicao = null;
let idParaExcluirRejeicao = null;
let todasAsRejeicoes = [];

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

async function carregarRejeicoesBanco() {
  const avisoEl = document.getElementById('aviso-erro-banco');
  try {
    const resp = await fetch('/api/manutencao-rejeicoes');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível carregar as rejeições do banco de monitoramento: ' + (dados.erro || 'erro desconhecido.');
      document.getElementById('corpo-tabela-rejeicoes').innerHTML =
        '<tr><td colspan="5" style="color:var(--fg-dim)">Sem dados no momento.</td></tr>';
      return;
    }
    avisoEl.style.display = 'none';
    todasAsRejeicoes = dados.registros;
    aplicarFiltrosRejeicoes();
  } catch (e) {
    avisoEl.style.display = 'block';
    avisoEl.innerText = '⚠ Erro ao carregar: ' + e;
  }
}

function aplicarFiltrosRejeicoes() {
  const filtroBusca = document.getElementById('filtro-cliente').value.trim().toLowerCase();
  let filtrados = todasAsRejeicoes;
  if (filtroBusca) {
    filtrados = filtrados.filter(r =>
      (r.cliente || '').toLowerCase().includes(filtroBusca) ||
      (r.tipo_banco || '').toLowerCase().includes(filtroBusca) ||
      (r.tipo_agendamento || '').toLowerCase().includes(filtroBusca)
    );
  }

  const corpo = document.getElementById('corpo-tabela-rejeicoes');
  if (todasAsRejeicoes.length === 0) {
    corpo.innerHTML = '<tr><td colspan="5" style="color:var(--fg-dim)">Nenhuma rejeição cadastrada ainda.</td></tr>';
    return;
  }
  if (filtrados.length === 0) {
    corpo.innerHTML = '<tr><td colspan="5" style="color:var(--fg-dim)">Nenhuma rejeição bate com o filtro.</td></tr>';
    return;
  }
  corpo.innerHTML = filtrados.map(r => `
    <tr>
      <td>${r.id}</td>
      <td>${r.cliente || ''}</td>
      <td>${r.tipo_banco || ''}</td>
      <td>${r.tipo_agendamento || ''}</td>
      <td>
        <div class="acoes-linha">
          <button class="btn-mini" onclick="abrirModalEditarRejeicao(${r.id})">Editar</button>
          <button class="btn-mini btn-perigo" onclick="abrirModalExcluirRejeicao(${r.id}, '${(r.cliente || '').replace(/'/g, "\\\\'")}')">Excluir</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function abrirModalNovaRejeicao() {
  idEmEdicaoRejeicao = null;
  document.getElementById('titulo-modal-rejeicao').innerText = 'Nova rejeição em CONFIGURACOES_REJEICAO';
  document.getElementById('botao-salvar-rejeicao').innerText = 'Criar rejeição';
  document.getElementById('form-nova-rejeicao').style.display = 'block';
  document.getElementById('sucesso-nova-rejeicao').style.display = 'none';
  document.getElementById('erro-nova-rejeicao').innerText = '';
  document.getElementById('rejeicao-cliente').value = '';
  document.getElementById('rejeicao-tipo-banco').value = 'SQL';
  document.getElementById('rejeicao-tipo-agendamento').value = '';
  document.getElementById('rejeicao-conexao').value = '';
  document.getElementById('rejeicao-conexao-select').value = '';
  document.getElementById('dica-conexao-nao-cadastrada-rejeicao').style.display = 'none';
  document.getElementById('rejeicao-script').value = '';
  document.getElementById('modal-nova-rejeicao').classList.add('aberto');
}

async function abrirModalEditarRejeicao(id) {
  const resp = await fetch('/api/manutencao-rejeicoes/' + id);
  const dados = await resp.json();
  if (!dados.ok) {
    mostrarToast(dados.erro || 'Não foi possível carregar essa rejeição.');
    return;
  }
  const r = dados.registro;
  idEmEdicaoRejeicao = id;
  document.getElementById('titulo-modal-rejeicao').innerText = 'Editar rejeição #' + id + ' (CONFIGURACOES_REJEICAO)';
  document.getElementById('botao-salvar-rejeicao').innerText = 'Salvar alterações';
  document.getElementById('form-nova-rejeicao').style.display = 'block';
  document.getElementById('sucesso-nova-rejeicao').style.display = 'none';
  document.getElementById('erro-nova-rejeicao').innerText = '';
  document.getElementById('rejeicao-cliente').value = r.cliente || '';
  document.getElementById('rejeicao-tipo-banco').value = r.tipo_banco || 'SQL';
  document.getElementById('rejeicao-tipo-agendamento').value = r.tipo_agendamento || '';
  document.getElementById('rejeicao-conexao').value = r.conexao || '';
  document.getElementById('rejeicao-script').value = r.script || '';

  const selectConexao = document.getElementById('rejeicao-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-rejeicao');
  const encontrada = stringConnectionsDisponiveis.find(c => c.conexao === r.conexao);
  if (encontrada) {
    selectConexao.value = encontrada.id;
    avisoNaoCadastrada.style.display = 'none';
  } else if (r.conexao) {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'block';
  } else {
    selectConexao.value = '';
    avisoNaoCadastrada.style.display = 'none';
  }

  document.getElementById('modal-nova-rejeicao').classList.add('aberto');
}

function fecharModalNovaRejeicao() {
  document.getElementById('modal-nova-rejeicao').classList.remove('aberto');
  carregarRejeicoesBanco();
}

function _corpoFormularioRejeicao() {
  return 'cliente=' + encodeURIComponent(document.getElementById('rejeicao-cliente').value) +
    '&tipo_banco=' + encodeURIComponent(document.getElementById('rejeicao-tipo-banco').value) +
    '&tipo_agendamento=' + encodeURIComponent(document.getElementById('rejeicao-tipo-agendamento').value) +
    '&conexao=' + encodeURIComponent(document.getElementById('rejeicao-conexao').value) +
    '&script=' + encodeURIComponent(document.getElementById('rejeicao-script').value);
}

async function salvarRejeicaoBanco() {
  const erroEl = document.getElementById('erro-nova-rejeicao');

  if (!document.getElementById('rejeicao-conexao').value) {
    erroEl.innerText = 'Selecione uma String Connection pra essa rejeição.';
    return;
  }

  if (idEmEdicaoRejeicao === null) {
    const resp = await fetch('/api/manutencao-rejeicoes/criar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: _corpoFormularioRejeicao(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível criar a rejeição.';
      return;
    }
    gatilhoAtualRejeicao = dados.gatilho;
    document.getElementById('texto-gatilho-rejeicao').innerHTML =
      '<b>Nome:</b> ' + gatilhoAtualRejeicao.nome + '<br>' +
      '<b>Solicitante:</b> ' + gatilhoAtualRejeicao.solicitante + '<br>' +
      '<b>Serviço:</b> ' + gatilhoAtualRejeicao.servico;
    document.getElementById('form-nova-rejeicao').style.display = 'none';
    document.getElementById('sucesso-nova-rejeicao').style.display = 'block';
  } else {
    const resp = await fetch('/api/manutencao-rejeicoes/atualizar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(idEmEdicaoRejeicao) + '&' + _corpoFormularioRejeicao(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível salvar as alterações.';
      return;
    }
    mostrarToast('Rejeição #' + idEmEdicaoRejeicao + ' atualizada.');
    fecharModalNovaRejeicao();
  }
}

function abrirModalExcluirRejeicao(id, cliente) {
  idParaExcluirRejeicao = id;
  document.getElementById('nome-rejeicao-excluir').innerText = '#' + id + ' (' + cliente + ')';
  document.getElementById('erro-excluir-rejeicao').innerText = '';
  document.getElementById('modal-excluir-rejeicao').classList.add('aberto');
}

function fecharModalExcluirRejeicao() {
  document.getElementById('modal-excluir-rejeicao').classList.remove('aberto');
}

async function confirmarExclusaoRejeicao() {
  const resp = await fetch('/api/manutencao-rejeicoes/excluir', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(idParaExcluirRejeicao),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('erro-excluir-rejeicao').innerText = dados.erro || 'Não foi possível excluir.';
    return;
  }
  mostrarToast('Rejeição #' + idParaExcluirRejeicao + ' excluída.');
  fecharModalExcluirRejeicao();
  carregarRejeicoesBanco();
}

function copiarTextoGatilhoRejeicao() {
  if (!gatilhoAtualRejeicao) return;
  const texto = 'Nome: ' + gatilhoAtualRejeicao.nome + '\\nSolicitante: ' + gatilhoAtualRejeicao.solicitante +
    '\\nServiço: ' + gatilhoAtualRejeicao.servico;
  copiarTextoParaAreaDeTransferencia(texto);
}

// navigator.clipboard só funciona em "contexto seguro" (HTTPS ou
// localhost) - como o painel roda em HTTP puro na rede interna, essa API
// fica indisponível no navegador. Mesmo fallback já usado em outras
// telas do painel.
function copiarTextoParaAreaDeTransferencia(texto) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(texto)
      .then(() => mostrarToast('Texto copiado.'))
      .catch(() => copiarViaTextareaFallback(texto));
  } else {
    copiarViaTextareaFallback(texto);
  }
}

function copiarViaTextareaFallback(texto) {
  const areaTemp = document.createElement('textarea');
  areaTemp.value = texto;
  areaTemp.style.position = 'fixed';
  areaTemp.style.left = '-9999px';
  areaTemp.style.top = '0';
  document.body.appendChild(areaTemp);
  areaTemp.focus();
  areaTemp.select();
  try {
    const sucesso = document.execCommand('copy');
    mostrarToast(sucesso ? 'Texto copiado.' : 'Não foi possível copiar automaticamente - selecione e copie manualmente.');
  } catch (e) {
    mostrarToast('Não foi possível copiar automaticamente - selecione e copie manualmente.');
  }
  document.body.removeChild(areaTemp);
}

// --- String Connections no formulário (preenchimento rápido) ---
let stringConnectionsDisponiveis = [];

async function carregarStringConnectionsParaSelect() {
  try {
    const resp = await fetch('/api/string-connections');
    const dados = await resp.json();
    if (!dados.ok) return;
    stringConnectionsDisponiveis = dados.conexoes;
    const select = document.getElementById('rejeicao-conexao-select');
    select.innerHTML = '<option value="">Selecione uma String Connection...</option>' +
      dados.conexoes.map(c => `<option value="${c.id}">${c.cliente} · ${c.produto}</option>`).join('');
  } catch (e) {
    // sem conexao pra rede/erro qualquer - falha silenciosa aqui esta ok
  }
}

function aplicarConexaoSelecionadaRejeicao() {
  const select = document.getElementById('rejeicao-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-rejeicao');
  const encontrada = stringConnectionsDisponiveis.find(c => c.id === select.value);
  if (encontrada) {
    document.getElementById('rejeicao-conexao').value = encontrada.conexao;
    avisoNaoCadastrada.style.display = 'none';
  } else {
    document.getElementById('rejeicao-conexao').value = '';
  }
}

carregarRejeicoesBanco();
carregarStringConnectionsParaSelect();
</script>

</body>
</html>
"""
