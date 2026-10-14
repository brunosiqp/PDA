"""Tela String Connections.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_STRING_CONNECTIONS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>String Connections</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: var(--largura-pagina); margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 13px; }
  th { color: var(--teal); background: rgba(var(--tinta),.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  td.conexao-truncada { max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
                         color: var(--fg-dim); font-family: Consolas, monospace; font-size: 11.5px; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  .btn-perigo { color: var(--erro); border-color: rgba(241,76,76,.4); }
  .acoes-linha { display: flex; gap: 6px; }
  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; }
  .modal-fundo.aberto { display: flex; }
  .modal { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 28px 26px; width: 380px; box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal h3 { margin: 0 0 16px 0; font-size: 15px; color: var(--teal); }
  .modal label { display: block; font-size: 11px; color: var(--fg-dim); margin: 12px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal input, .modal textarea { width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(var(--poco),.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal textarea { font-family: Consolas, monospace; font-size: 12px; min-height: 70px; resize: vertical; }
  .modal input:focus, .modal textarea:focus { outline: none; border-color: var(--teal);
                 box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .modal .acoes-modal { display: flex; gap: 8px; margin-top: 20px; }
  .modal .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .modal p.aviso-exclusao { color: var(--fg-dim); font-size: 13px; line-height: 1.5; margin: 0 0 6px 0; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: var(--largura-pagina); }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .sub-secao { color: var(--fg-dim); font-size: 12.5px; max-width: var(--largura-pagina); margin: 0 auto 16px auto; line-height: 1.5; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">String Connections</h3>
      <button class="btn-accent" onclick="abrirModalNovaConexao()">+ Nova conexão</button>
    </div>
    <div class="sub-secao">
      Strings de conexão reutilizáveis por cliente e produto (ex.: ClienteG · NFCom, ClienteE · NFe).
      Ficam disponíveis pra escolher na hora de criar ou editar um alerta em
      "Manutenção de Alertas em Banco", sem precisar digitar a conexão de novo toda vez.
    </div>
    <div class="painel">
      <table>
        <thead><tr><th>Cliente</th><th>Produto</th><th>Conexão</th><th></th></tr></thead>
        <tbody id="corpo-tabela-conexoes">
          <tr><td colspan="4" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-nova-conexao">
    <div class="modal">
      <h3 id="titulo-modal-conexao">Nova String Connection</h3>
      <label>Cliente</label>
      <input type="text" id="conexao-cliente" placeholder="Ex.: ClienteG">
      <label>Produto</label>
      <input type="text" id="conexao-produto" placeholder="Ex.: NFCom">
      <label>String de conexão</label>
      <textarea id="conexao-valor" placeholder="Servidor, banco, usuário, senha..."></textarea>
      <div class="erro-modal" id="modal-conexao-erro"></div>
      <div class="acoes-modal">
        <button class="btn-secundario" onclick="fecharModalConexao()">Cancelar</button>
        <button class="btn-accent" id="botao-salvar-conexao" onclick="salvarConexao()">Criar</button>
      </div>
    </div>
  </div>

  <div class="modal-fundo" id="modal-excluir-conexao">
    <div class="modal">
      <h3>Excluir String Connection</h3>
      <p class="aviso-exclusao">
        Tem certeza que quer excluir a conexão de <strong id="nome-conexao-excluir"></strong>?
        Alertas que já usam essa conexão continuam funcionando (a string fica salva no alerta),
        só não vai mais aparecer como opção pronta pra novos alertas.
      </p>
      <div class="erro-modal" id="modal-excluir-conexao-erro"></div>
      <div class="acoes-modal">
        <button class="btn-secundario" onclick="fecharModalExcluirConexao()">Cancelar</button>
        <button class="btn-accent btn-perigo" onclick="confirmarExcluirConexao()">Excluir</button>
      </div>
    </div>
  </div>

  __FOOTER__

  <div class="toast" id="toast"></div>

<script>
let idEmEdicaoConexao = null;
let idParaExcluirConexao = null;

// aviso rápido embaixo da tela - a página chamava mostrarToast desde a 2.28.1
// sem ter a função, e o script parava antes de recarregar a lista
function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

async function carregarStringConnections() {
  const resp = await fetch('/api/string-connections');
  if (resp.status === 401) { window.location.href = '/login'; return; }
  if (resp.status === 403) { window.location.href = '/'; return; }
  const dados = await resp.json();
  const corpo = document.getElementById('corpo-tabela-conexoes');
  if (!dados.ok) {
    corpo.innerHTML = '<tr><td colspan="4" style="color:var(--fg-dim)">Não foi possível carregar.</td></tr>';
    return;
  }
  if (dados.conexoes.length === 0) {
    corpo.innerHTML = '<tr><td colspan="4" style="color:var(--fg-dim)">Nenhuma String Connection cadastrada ainda.</td></tr>';
    return;
  }
  corpo.innerHTML = dados.conexoes.map(c => `
    <tr>
      <td>${c.cliente}</td>
      <td>${c.produto}</td>
      <td class="conexao-truncada" title="${c.conexao.replace(/"/g, '&quot;')}">${c.conexao}</td>
      <td>
        <div class="acoes-linha">
          <button class="btn-mini" onclick='abrirModalEditarConexao(${JSON.stringify(c)})'>Editar</button>
          <button class="btn-mini btn-perigo" onclick="abrirModalExcluirConexao('${c.id}', '${c.cliente} · ${c.produto}')">Excluir</button>
        </div>
      </td>
    </tr>
  `).join('');
}

function abrirModalNovaConexao() {
  idEmEdicaoConexao = null;
  document.getElementById('titulo-modal-conexao').innerText = 'Nova String Connection';
  document.getElementById('botao-salvar-conexao').innerText = 'Criar';
  document.getElementById('conexao-cliente').value = '';
  document.getElementById('conexao-produto').value = '';
  document.getElementById('conexao-valor').value = '';
  document.getElementById('modal-conexao-erro').innerText = '';
  document.getElementById('modal-nova-conexao').classList.add('aberto');
}

function abrirModalEditarConexao(c) {
  idEmEdicaoConexao = c.id;
  document.getElementById('titulo-modal-conexao').innerText = 'Editar String Connection';
  document.getElementById('botao-salvar-conexao').innerText = 'Salvar';
  document.getElementById('conexao-cliente').value = c.cliente;
  document.getElementById('conexao-produto').value = c.produto;
  document.getElementById('conexao-valor').value = c.conexao;
  document.getElementById('modal-conexao-erro').innerText = '';
  document.getElementById('modal-nova-conexao').classList.add('aberto');
}

function fecharModalConexao() {
  document.getElementById('modal-nova-conexao').classList.remove('aberto');
}

async function salvarConexao(substituir) {
  const cliente = document.getElementById('conexao-cliente').value.trim();
  const produto = document.getElementById('conexao-produto').value.trim();
  const conexao = document.getElementById('conexao-valor').value.trim();
  const erroEl = document.getElementById('modal-conexao-erro');
  if (!cliente || !produto || !conexao) {
    erroEl.innerText = 'Preencha cliente, produto e a string de conexão.';
    return;
  }
  const corpo = 'cliente=' + encodeURIComponent(cliente) + '&produto=' + encodeURIComponent(produto) +
                '&conexao=' + encodeURIComponent(conexao) +
                (idEmEdicaoConexao ? '&id=' + encodeURIComponent(idEmEdicaoConexao) : '') +
                (substituir === true ? '&substituir=true' : '');
  const url = idEmEdicaoConexao ? '/api/string-connections/atualizar' : '/api/string-connections/criar';
  const resp = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: corpo });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModalConexao();
    mostrarToast(dados.substituida ? 'String Connection substituída.' : 'String Connection salva.');
    carregarStringConnections();
  } else if (dados.duplicada && substituir !== true) {
    // só uma string por cliente + produto: pergunta antes de trocar a que já existe
    const texto = idEmEdicaoConexao
      ? dados.erro + '\\n\\nSalvar esta e excluir a outra?'
      : dados.erro + '\\n\\nSubstituir a string existente pela nova?';
    if (confirm(texto)) {
      salvarConexao(true);
    } else {
      erroEl.innerText = dados.erro + ' Nada foi alterado.';
    }
  } else {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
  }
}

function abrirModalExcluirConexao(id, nome) {
  idParaExcluirConexao = id;
  document.getElementById('nome-conexao-excluir').innerText = nome;
  document.getElementById('modal-excluir-conexao-erro').innerText = '';
  document.getElementById('modal-excluir-conexao').classList.add('aberto');
}

function fecharModalExcluirConexao() {
  document.getElementById('modal-excluir-conexao').classList.remove('aberto');
}

async function confirmarExcluirConexao() {
  const resp = await fetch('/api/string-connections/deletar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(idParaExcluirConexao),
  });
  const dados = await resp.json();
  if (dados.ok) {
    fecharModalExcluirConexao();
    mostrarToast('String Connection excluída.');
    carregarStringConnections();
  } else {
    document.getElementById('modal-excluir-conexao-erro').innerText = dados.erro || 'Não foi possível excluir.';
  }
}

carregarStringConnections();
</script>
</body>
</html>
"""
