"""Tela Manutencao Alertas.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_MANUTENCAO_ALERTAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção de Alertas em Banco</title>
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
  .barra-selecao-lote { display: flex; align-items: center; gap: 10px; padding: 10px 14px;
                         background: rgba(45,184,207,.08); border-bottom: 1px solid var(--border);
                         font-size: 12.5px; color: var(--fg-dim); }
  .barra-selecao-lote span { color: var(--teal); font-weight: 600; margin-right: 4px; }
  button.btn-mini:disabled { opacity: .35; cursor: not-allowed; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: var(--largura-pagina); }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .badge-status { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 10px;
                  font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .badge-status.ativo { background: rgba(78,201,176,.15); color: var(--ok); border: 1px solid rgba(78,201,176,.35); }
  .badge-status.inativo { background: rgba(139,152,165,.15); color: var(--fg-dim); border: 1px solid var(--border); }

  .filtros-alertas { display: flex; gap: 10px; margin: 0 auto 14px auto; max-width: var(--largura-pagina); flex-wrap: wrap; }
  .filtros-alertas input[type="text"] { flex: 1; min-width: 180px; padding: 8px 12px; border-radius: 8px;
                    border: 1px solid var(--border); background: rgba(var(--poco),.28); color: var(--fg); font-size: 13px; }
  .filtros-alertas input[type="text"]:focus { outline: none; border-color: var(--teal); }
  .filtros-alertas select { padding: 8px 12px; border-radius: 8px; font-size: 13px; }
  .acoes-linha { display: flex; gap: 6px; }
  input[readonly] { opacity: .65; cursor: not-allowed; }
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
  .modal-largo textarea { font-family: Consolas, monospace; font-size: 12.5px; resize: vertical; min-height: 70px; }
  .modal-largo input:focus, .modal-largo select:focus, .modal-largo textarea:focus {
                 outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .linha-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 0 14px; }
  .dica-campo { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.4; }
  .campo-checkbox { display: flex; align-items: center; gap: 8px; margin-top: 16px; }
  .campo-checkbox input { width: auto; }
  .campo-checkbox label { margin: 0; text-transform: none; font-size: 13px; color: var(--fg); letter-spacing: 0; }
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
  /* modo visualização (3.1.9.0) */
  body.so-leitura .so-edicao, body.so-leitura #barra-selecao-lote { display: none !important; }
  .aviso-leitura { max-width: var(--largura-pagina); margin: 0 auto 14px auto; font-size: 12.5px; color: var(--fg-dim);
                   background: rgba(var(--tinta), .04); border: 1px dashed var(--border); border-radius: 12px; padding: 10px 14px; line-height: 1.5; }
  .aviso-leitura b { color: var(--fg); }
  .selo-ativo { display: inline-block; font-size: 11px; font-weight: 800; color: var(--lime); background: rgba(176,203,28,.14); border-radius: 999px; padding: 2px 9px; }
  .grade-ver { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0 18px; }
  .campo-ver { margin-bottom: 12px; }
  .campo-ver > span { display: block; font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; color: var(--fg-dim); margin-bottom: 4px; }
  .campo-ver > div { font-size: 13.5px; color: var(--fg); word-break: break-word; }
  .script-ver { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: Consolas, 'Cascadia Mono', monospace; font-size: 12.5px;
                background: rgba(var(--poco), .3); border: 1px solid var(--border); border-radius: 10px; padding: 12px; max-height: 340px; overflow: auto; color: var(--fg); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Alertas cadastrados (CONFIGURACOES_ALERTA)</h3>
      <button class="btn-accent so-edicao" onclick="abrirModalNovoAlerta()">+ Novo alerta</button>
    </div>
    <div class="aviso-leitura" id="aviso-leitura" hidden>👁️ <b>Modo visualização:</b> você vê os alertas <b>ativos</b> e como cada um está configurado (o SELECT que abre o alerta, teto, intervalo e descrição). Criar, editar e ativar/desativar fica com quem tem permissão.</div>

    <div class="aviso-scraping" id="aviso-erro-banco" style="display:none; max-width:var(--largura-pagina); margin:0 auto 16px auto;"></div>

    <div class="filtros-alertas">
      <input type="text" id="filtro-cliente" placeholder="Buscar por nome, cliente ou tipo..." oninput="aplicarFiltrosAlertas()">
      <select id="filtro-status" class="so-edicao" onchange="aplicarFiltrosAlertas()">
        <option value="">Todos os status</option>
        <option value="1">Ativo</option>
        <option value="0">Inativo</option>
      </select>
    </div>

    <div class="painel">
      <div class="barra-selecao-lote" id="barra-selecao-lote" style="display:none">
        <span id="texto-selecao-lote"></span>
        <button class="btn-mini" onclick="alterarDisponibilidadeLote(true)">Ativar selecionados</button>
        <button class="btn-mini" onclick="alterarDisponibilidadeLote(false)">Desativar selecionados</button>
        <button class="btn-mini" onclick="limparSelecaoAlertas()">Limpar seleção</button>
      </div>
      <table>
        <thead>
          <tr>
            <th class="so-edicao"><input type="checkbox" id="checkbox-selecionar-todos" onchange="alternarSelecionarTodosAlertas(this.checked)"></th>
            <th>ID</th><th>Cliente</th><th>Título</th><th>Tipo</th><th>Teto</th><th>Intervalo</th><th>Status</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela-alertas">
          <tr><td colspan="9" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-novo-alerta">
    <div class="modal-largo">
      <h3 id="titulo-modal-alerta">Novo alerta em CONFIGURACOES_ALERTA</h3>

      <div id="form-novo-alerta">
        <div class="linha-dupla">
          <div>
            <label>Cliente</label>
            <input type="text" id="alerta-cliente" placeholder="Nome do cliente">
          </div>
          <div>
            <label>Tipo de banco</label>
            <select id="alerta-tipo-banco">
              <option value="SQL">SQL Server</option>
              <option value="ORACLE">Oracle</option>
            </select>
          </div>
        </div>

        <label>Título</label>
        <input type="text" id="alerta-titulo" value="[ALERTA] ">
        <div class="dica-campo">Precisa começar com "[ALERTA]" - já vem preenchido, só complete.</div>

        <label>Conexão</label>
        <select id="alerta-conexao-select" onchange="aplicarConexaoSelecionada()">
          <option value="">Selecione uma String Connection...</option>
        </select>
        <input type="hidden" id="alerta-conexao">
        <div class="dica-campo" id="dica-conexao-nao-cadastrada" style="display:none; color:var(--erro)">
          Este alerta usa uma conexão que não está cadastrada em String Connections - selecione uma da lista pra substituir.
        </div>

        <label>Script</label>
        <textarea id="alerta-script" placeholder="SELECT COUNT(*) FROM ..."></textarea>
        <div class="dica-campo">SQL puro - a conversão pra base64 é feita automaticamente. Precisa sempre trazer um número exato (via COUNT) pra comparar com o Teto do alerta.</div>

        <div class="linha-dupla">
          <div>
            <label>Teto do alerta</label>
            <input type="number" id="alerta-teto" placeholder="Ex.: 10" step="any">
          </div>
          <div>
            <label>Intervalo (minutos)</label>
            <input type="number" id="alerta-intervalo" placeholder="Ex.: 15" min="1" step="1">
          </div>
        </div>

        <label>E-mails</label>
        <input type="text" id="alerta-emails" value="__EMAIL_MONITORAMENTO__" readonly>
        <div class="dica-campo dica-travado">Sempre o e-mail padrão do monitoramento - não é editável.</div>

        <label>Descrição (corpo do e-mail)</label>
        <textarea id="alerta-descricao" placeholder="Texto que vai no corpo do e-mail enviado"></textarea>

        <div class="campo-checkbox">
          <input type="checkbox" id="alerta-disponibilidade" checked>
          <label for="alerta-disponibilidade">Ativar este alerta imediatamente</label>
        </div>

        <div class="erro-modal" id="erro-novo-alerta"></div>
        <div class="acoes-modal">
          <button class="btn-accent" id="botao-salvar-alerta" onclick="salvarAlertaBanco()" style="flex:1">Criar alerta</button>
          <button onclick="fecharModalNovoAlerta()" style="flex:1">Cancelar</button>
        </div>
      </div>

      <div id="sucesso-novo-alerta" style="display:none">
        <div class="bloco-sucesso">
          <div class="icone-ok">
            <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
          </div>
          <h4>Alerta criado com sucesso</h4>
          <p>
            Falta um passo manual: solicitar a criação do gatilho no Movidesk
            (peça pra algum N2 ou N3). Use estes dados na
            abertura do serviço:
          </p>
          <div class="bloco-gatilho" id="texto-gatilho"></div>
          <div class="acoes-modal">
            <button class="btn-accent" onclick="copiarTextoGatilho()" style="flex:1">Copiar texto</button>
            <button onclick="fecharModalNovoAlerta()" style="flex:1">Fechar</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- só leitura (3.1.9.0): a configuração do alerta, sem a conexão -->
  <div class="modal-fundo" id="modal-ver-alerta">
    <div class="modal-largo">
      <h3 id="titulo-ver-alerta">Alerta</h3>
      <div id="corpo-ver-alerta"></div>
      <div class="acoes-modal"><button onclick="document.getElementById('modal-ver-alerta').classList.remove('aberto')" style="flex:1">Fechar</button></div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  __FOOTER__

<script>
// sem admin nem a permissão da Manutenção de Alertas: só os ativos, só leitura, sem conexão (3.1.9.0)
const SO_LEITURA_ALERTAS = __SO_LEITURA_ALERTAS__;
if (SO_LEITURA_ALERTAS) {
  document.body.classList.add('so-leitura');
  document.getElementById('aviso-leitura').hidden = false;
}
function escAlerta(t) {
  return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
async function abrirVerAlerta(id) {
  const resp = await fetch('/api/manutencao-alertas/' + id);
  if (resp.status === 401) { window.location.href = '/login'; return; }
  const dados = await resp.json();
  if (!dados.ok) { mostrarToast(dados.erro || 'Não foi possível carregar esse alerta.'); return; }
  const r = dados.registro;
  const campo = (rotulo, valor) => '<div class="campo-ver"><span>' + rotulo + '</span><div>' + valor + '</div></div>';
  document.getElementById('titulo-ver-alerta').innerText = 'Alerta #' + r.id;
  document.getElementById('corpo-ver-alerta').innerHTML =
    '<div class="grade-ver">' + campo('Cliente', escAlerta(r.cliente)) + campo('Título', escAlerta(r.titulo))
    + campo('Tipo de banco', escAlerta(r.tipo_banco === 'ORACLE' ? 'Oracle' : 'SQL Server'))
    + campo('Teto do alerta', escAlerta(r.teto_alerta)) + campo('Intervalo', escAlerta(r.intervalo_minutos) + ' min')
    + campo('Status', Number(r.disponibilidade) === 1 ? '<span class="selo-ativo">Ativo</span>' : 'Inativo') + '</div>'
    + campo('E-mails', escAlerta(r.emails)) + campo('Descrição (corpo do e-mail)', escAlerta(r.descricao).replace(/\\n/g, '<br>') || '·')
    + '<div class="campo-ver"><span>SELECT usado na abertura do alerta</span><pre class="script-ver">' + escAlerta(r.script) + '</pre></div>'
    + '<div class="dica-campo">A conexão (String Connection) do alerta não aparece no modo visualização.</div>';
  document.getElementById('modal-ver-alerta').classList.add('aberto');
}
let gatilhoAtual = null;
let idEmEdicao = null;  // null = criando um novo; numero = editando esse ID
let todosOsAlertas = [];

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

async function carregarAlertasBanco() {
  const avisoEl = document.getElementById('aviso-erro-banco');
  try {
    const resp = await fetch('/api/manutencao-alertas');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível carregar os alertas do banco de monitoramento: ' + (dados.erro || 'erro desconhecido.');
      document.getElementById('corpo-tabela-alertas').innerHTML =
        '<tr><td colspan="9" style="color:var(--fg-dim)">Sem dados no momento.</td></tr>';
      return;
    }
    avisoEl.style.display = 'none';
    todosOsAlertas = dados.registros;
    aplicarFiltrosAlertas();
  } catch (e) {
    avisoEl.style.display = 'block';
    avisoEl.innerText = '⚠ Erro ao carregar: ' + e;
  }
}

function aplicarFiltrosAlertas() {
  const filtroBusca = document.getElementById('filtro-cliente').value.trim().toLowerCase();
  const filtroStatus = document.getElementById('filtro-status').value;

  let filtrados = todosOsAlertas;
  if (filtroBusca) {
    // busca inteligente - bate em qualquer um dos campos (não só cliente)
    filtrados = filtrados.filter(r =>
      (r.cliente || '').toLowerCase().includes(filtroBusca) ||
      (r.titulo || '').toLowerCase().includes(filtroBusca) ||
      (r.tipo_banco || '').toLowerCase().includes(filtroBusca)
    );
  }
  if (filtroStatus !== '') {
    filtrados = filtrados.filter(r => String(Number(r.disponibilidade) === 1 ? 1 : 0) === filtroStatus);
  }

  const corpo = document.getElementById('corpo-tabela-alertas');
  if (todosOsAlertas.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum alerta cadastrado ainda.</td></tr>';
    return;
  }
  if (filtrados.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum alerta bate com o filtro.</td></tr>';
    return;
  }
  corpo.innerHTML = filtrados.map(r => `
    <tr>
      <td class="so-edicao"><input type="checkbox" class="checkbox-alerta" value="${r.id}" ${idsSelecionadosAlertas.has(String(r.id)) ? 'checked' : ''} onchange="atualizarSelecaoAlertas()"></td>
      <td>${r.id}</td>
      <td>${r.cliente || ''}</td>
      <td>${r.titulo || ''}</td>
      <td>${r.tipo_banco || ''}</td>
      <td>${r.teto_alerta ?? ''}</td>
      <td>${r.intervalo_minutos ?? ''} min</td>
      <td>${SO_LEITURA_ALERTAS ? '<span class="selo-ativo">Ativo</span>' : `
        <select onchange="alternarDisponibilidadeBanco(${r.id}, this.value)">
          <option value="true" ${Number(r.disponibilidade) === 1 ? 'selected' : ''}>Ativo</option>
          <option value="false" ${Number(r.disponibilidade) !== 1 ? 'selected' : ''}>Inativo</option>
        </select>`}
      </td>
      <td>${SO_LEITURA_ALERTAS ? `<button class="btn-mini" onclick="abrirVerAlerta(${r.id})">Ver configuração</button>`
        : `<button class="btn-mini btn-editar-alerta" onclick="abrirModalEditarAlerta(${r.id})">Editar</button>`}</td>
    </tr>
  `).join('');
  atualizarSelecaoAlertas();
}

// --- Seleção em lote (ativar/desativar vários alertas de uma vez) ---
let idsSelecionadosAlertas = new Set();

function atualizarSelecaoAlertas() {
  const marcados = Array.from(document.querySelectorAll('.checkbox-alerta:checked')).map(c => c.value);
  idsSelecionadosAlertas = new Set(marcados);

  const barra = document.getElementById('barra-selecao-lote');
  const texto = document.getElementById('texto-selecao-lote');
  if (idsSelecionadosAlertas.size > 0) {
    barra.style.display = 'flex';
    texto.innerText = idsSelecionadosAlertas.size + ' selecionado(s)';
  } else {
    barra.style.display = 'none';
  }

  // com mais de um alerta marcado, editar não faz sentido (só dá pra
  // editar um de cada vez) - desabilita os botões de editar até a
  // seleção voltar pra 0 ou 1
  const desabilitarEdicao = idsSelecionadosAlertas.size > 1;
  document.querySelectorAll('.btn-editar-alerta').forEach(btn => {
    btn.disabled = desabilitarEdicao;
    btn.title = desabilitarEdicao ? 'Desmarque para editar apenas um alerta por vez' : '';
  });

  const todos = document.querySelectorAll('.checkbox-alerta');
  const checkboxTodos = document.getElementById('checkbox-selecionar-todos');
  if (checkboxTodos) {
    checkboxTodos.checked = todos.length > 0 && idsSelecionadosAlertas.size === todos.length;
    checkboxTodos.indeterminate = idsSelecionadosAlertas.size > 0 && idsSelecionadosAlertas.size < todos.length;
  }
}

function alternarSelecionarTodosAlertas(marcarTodos) {
  document.querySelectorAll('.checkbox-alerta').forEach(c => { c.checked = marcarTodos; });
  atualizarSelecaoAlertas();
}

function limparSelecaoAlertas() {
  document.querySelectorAll('.checkbox-alerta').forEach(c => { c.checked = false; });
  atualizarSelecaoAlertas();
}

async function alterarDisponibilidadeLote(ativar) {
  const ids = Array.from(idsSelecionadosAlertas);
  if (ids.length === 0) return;
  let sucesso = 0, falha = 0;
  for (const id of ids) {
    try {
      const resp = await fetch('/api/manutencao-alertas/disponibilidade', {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded'},
        body: 'id=' + encodeURIComponent(id) + '&disponibilidade=' + (ativar ? 'true' : 'false'),
      });
      const dados = await resp.json();
      if (dados.ok) sucesso++; else falha++;
    } catch (e) {
      falha++;
    }
  }
  mostrarToast(
    `${sucesso} alerta(s) ${ativar ? 'ativado(s)' : 'desativado(s)'}` + (falha > 0 ? `, ${falha} falhou(aram)` : '')
  );
  idsSelecionadosAlertas.clear();
  carregarAlertasBanco();
}

async function alternarDisponibilidadeBanco(id, valor) {
  const resp = await fetch('/api/manutencao-alertas/disponibilidade', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(id) + '&disponibilidade=' + valor,
  });
  const dados = await resp.json();
  if (dados.ok) {
    mostrarToast('Disponibilidade do alerta #' + id + ' atualizada.');
  } else {
    mostrarToast(dados.erro || 'Não foi possível atualizar.');
  }
  carregarAlertasBanco();
}

function abrirModalNovoAlerta() {
  idEmEdicao = null;
  document.getElementById('titulo-modal-alerta').innerText = 'Novo alerta em CONFIGURACOES_ALERTA';
  document.getElementById('botao-salvar-alerta').innerText = 'Criar alerta';
  document.getElementById('form-novo-alerta').style.display = 'block';
  document.getElementById('sucesso-novo-alerta').style.display = 'none';
  document.getElementById('erro-novo-alerta').innerText = '';
  document.getElementById('alerta-cliente').value = '';
  document.getElementById('alerta-tipo-banco').value = 'SQL';
  document.getElementById('alerta-titulo').value = '[ALERTA] ';
  document.getElementById('alerta-conexao').value = '';
  document.getElementById('alerta-conexao-select').value = '';
  document.getElementById('dica-conexao-nao-cadastrada').style.display = 'none';
  document.getElementById('alerta-script').value = '';
  document.getElementById('alerta-teto').value = '';
  document.getElementById('alerta-intervalo').value = '';
  document.getElementById('alerta-descricao').value = '';
  document.getElementById('alerta-disponibilidade').checked = true;
  document.getElementById('modal-novo-alerta').classList.add('aberto');
}

async function abrirModalEditarAlerta(id) {
  const resp = await fetch('/api/manutencao-alertas/' + id);
  const dados = await resp.json();
  if (!dados.ok) {
    mostrarToast(dados.erro || 'Não foi possível carregar esse alerta.');
    return;
  }
  const r = dados.registro;
  idEmEdicao = id;
  document.getElementById('titulo-modal-alerta').innerText = 'Editar alerta #' + id + ' (CONFIGURACOES_ALERTA)';
  document.getElementById('botao-salvar-alerta').innerText = 'Salvar alterações';
  document.getElementById('form-novo-alerta').style.display = 'block';
  document.getElementById('sucesso-novo-alerta').style.display = 'none';
  document.getElementById('erro-novo-alerta').innerText = '';
  document.getElementById('alerta-cliente').value = r.cliente || '';
  document.getElementById('alerta-tipo-banco').value = r.tipo_banco || 'SQL';
  document.getElementById('alerta-titulo').value = r.titulo || '[ALERTA] ';
  document.getElementById('alerta-conexao').value = r.conexao || '';
  document.getElementById('alerta-script').value = r.script || '';
  document.getElementById('alerta-teto').value = r.teto_alerta ?? '';
  document.getElementById('alerta-intervalo').value = r.intervalo_minutos ?? '';
  document.getElementById('alerta-descricao').value = r.descricao || '';
  document.getElementById('alerta-disponibilidade').checked = Number(r.disponibilidade) === 1;

  // acha qual String Connection cadastrada corresponde à conexão já
  // salva nesse alerta, pra deixar selecionada no dropdown - sem
  // mostrar o valor bruto em campo nenhum. Se não achar nenhuma
  // correspondência (alerta criado antes dessa funcionalidade existir,
  // ou editado direto no banco), avisa sem revelar a string.
  const selectConexao = document.getElementById('alerta-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada');
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

  document.getElementById('modal-novo-alerta').classList.add('aberto');
}

function fecharModalNovoAlerta() {
  document.getElementById('modal-novo-alerta').classList.remove('aberto');
  carregarAlertasBanco();
}

function _corpoFormularioAlerta() {
  return 'cliente=' + encodeURIComponent(document.getElementById('alerta-cliente').value) +
    '&tipo_banco=' + encodeURIComponent(document.getElementById('alerta-tipo-banco').value) +
    '&titulo=' + encodeURIComponent(document.getElementById('alerta-titulo').value) +
    '&conexao=' + encodeURIComponent(document.getElementById('alerta-conexao').value) +
    '&script=' + encodeURIComponent(document.getElementById('alerta-script').value) +
    '&teto_alerta=' + encodeURIComponent(document.getElementById('alerta-teto').value) +
    '&intervalo_minutos=' + encodeURIComponent(document.getElementById('alerta-intervalo').value) +
    '&emails=' + encodeURIComponent(document.getElementById('alerta-emails').value) +
    '&descricao=' + encodeURIComponent(document.getElementById('alerta-descricao').value) +
    '&disponibilidade=' + (document.getElementById('alerta-disponibilidade').checked ? 'true' : 'false');
}

async function salvarAlertaBanco() {
  const erroEl = document.getElementById('erro-novo-alerta');

  if (!document.getElementById('alerta-conexao').value) {
    erroEl.innerText = 'Selecione uma String Connection pra esse alerta.';
    return;
  }

  if (idEmEdicao === null) {
    const resp = await fetch('/api/manutencao-alertas/criar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: _corpoFormularioAlerta(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível criar o alerta.';
      return;
    }
    gatilhoAtual = dados.gatilho;
    document.getElementById('texto-gatilho').innerHTML =
      '<b>Nome:</b> ' + gatilhoAtual.nome + '<br>' +
      '<b>Solicitante:</b> ' + gatilhoAtual.solicitante + '<br>' +
      '<b>Serviço:</b> ' + gatilhoAtual.servico;
    document.getElementById('form-novo-alerta').style.display = 'none';
    document.getElementById('sucesso-novo-alerta').style.display = 'block';
  } else {
    const resp = await fetch('/api/manutencao-alertas/atualizar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(idEmEdicao) + '&' + _corpoFormularioAlerta(),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível salvar as alterações.';
      return;
    }
    mostrarToast('Alerta #' + idEmEdicao + ' atualizado.');
    fecharModalNovoAlerta();
  }
}

function copiarTextoGatilho() {
  if (!gatilhoAtual) return;
  const texto = 'Nome: ' + gatilhoAtual.nome + '\\nSolicitante: ' + gatilhoAtual.solicitante +
    '\\nServiço: ' + gatilhoAtual.servico;
  copiarTextoParaAreaDeTransferencia(texto);
}

// navigator.clipboard só funciona em "contexto seguro" (HTTPS ou
// localhost) - como o painel roda em HTTP puro na rede interna
// (http://pda.local:8765/, não https), essa API fica indisponível
// no navegador e a chamada falhava sem erro visível nenhum. Esse
// fallback usa o método antigo (textarea invisível + document.execCommand)
// que funciona independente de HTTPS.
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

// --- String Connections no formulário de alerta (preenchimento rápido) ---
let stringConnectionsDisponiveis = [];

async function carregarStringConnectionsParaSelect() {
  try {
    const resp = await fetch('/api/string-connections');
    const dados = await resp.json();
    if (!dados.ok) return;
    stringConnectionsDisponiveis = dados.conexoes;
    const select = document.getElementById('alerta-conexao-select');
    select.innerHTML = '<option value="">Selecione uma String Connection...</option>' +
      dados.conexoes.map(c => `<option value="${c.id}">${c.cliente} · ${c.produto}</option>`).join('');
  } catch (e) {
    // sem conexao pra rede/erro qualquer - falha silenciosa aqui esta ok,
    // o usuario so nao vai ter opcoes pra escolher ate a pagina recarregar
  }
}

function aplicarConexaoSelecionada() {
  const select = document.getElementById('alerta-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada');
  const encontrada = stringConnectionsDisponiveis.find(c => c.id === select.value);
  if (encontrada) {
    document.getElementById('alerta-conexao').value = encontrada.conexao;
    avisoNaoCadastrada.style.display = 'none';
  } else {
    document.getElementById('alerta-conexao').value = '';
  }
}

carregarAlertasBanco();
if (!SO_LEITURA_ALERTAS) carregarStringConnectionsParaSelect();  // a lista de String Connections nem é pedida no modo leitura
</script>

</body>
</html>
"""
