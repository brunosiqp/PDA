"""Tela Manutencao Relatorios.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_MANUTENCAO_RELATORIOS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção de Relatórios em Banco</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  .painel { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
            border: 1px solid var(--border); border-radius: 12px;
            overflow: hidden; max-width: var(--largura-pagina); margin: 0 auto; }
  table { width: 100%; border-collapse: collapse; }
  th, td { text-align: left; padding: 10px 12px; border-bottom: 1px solid var(--border); font-size: 12.5px;
           white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 180px; }
  th { color: var(--teal); background: rgba(var(--tinta),.03); font-weight: 600; }
  tr:last-child td { border-bottom: none; }
  .cabecalho-secao-usuarios { display: flex; justify-content: space-between; align-items: center;
                              margin: 0 auto 14px auto; max-width: var(--largura-pagina); }
  h3.titulo { color: var(--teal); margin: 0; font-size: 14px; }
  .filtros-alertas { display: flex; gap: 10px; margin: 0 auto 14px auto; max-width: var(--largura-pagina); flex-wrap: wrap; }
  .filtros-alertas input[type="text"], .filtros-alertas select { flex: 1; min-width: 160px; padding: 8px 12px;
                    border-radius: 8px; border: 1px solid var(--border); background: rgba(var(--poco),.28);
                    color: var(--fg); font-size: 13px; }
  .filtros-alertas input[type="text"]:focus, .filtros-alertas select:focus { outline: none; border-color: var(--teal); }
  .acoes-linha { display: flex; gap: 6px; }
  .badge-status { display: inline-block; padding: 2px 9px; border-radius: 6px; font-size: 11px; font-weight: 700; }
  .badge-ativo { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-inativo { background: rgba(var(--tinta),.08); color: var(--fg-dim); }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; padding: 24px; }
  .modal-fundo.aberto { display: flex; }
  .modal-largo { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 30px 32px; width: 100%; max-width: 620px; max-height: 88vh; overflow-y: auto;
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
  .linha-tripla { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0 14px; }
  .dica-campo { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.4; }
  .acoes-modal { display: flex; gap: 8px; margin-top: 22px; }
  .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .campo-checkbox { display: flex; align-items: center; gap: 9px; margin-top: 16px; }
  .campo-checkbox input[type="checkbox"] { width: auto; flex: 0 0 auto; padding: 0; }
  .campo-checkbox label { display: block; margin: 0; text-transform: none; letter-spacing: normal;
                           font-size: 13px; color: var(--fg); flex: 1; text-align: left; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-secao-usuarios">
      <h3 class="titulo">Relatórios cadastrados (CONFIGURACOES_RELATORIO)</h3>
      <button class="btn-accent" onclick="abrirModalNovoRelatorio()">+ Novo relatório</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro-banco" style="display:none; max-width:var(--largura-pagina); margin:0 auto 16px auto;"></div>

    <div class="filtros-alertas">
      <input type="text" id="filtro-cliente-rel" placeholder="Buscar por cliente, título ou tipo..." oninput="aplicarFiltrosRelatorios()">
      <select id="filtro-status-rel" onchange="aplicarFiltrosRelatorios()">
        <option value="">Todos os status</option>
        <option value="1">Ativos</option>
        <option value="0">Inativos</option>
      </select>
    </div>

    <div class="painel">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>Cliente</th><th>Título e-mail</th><th>Tipo</th><th>Modelo</th>
            <th>Reincidência</th><th>Hora</th><th>Status</th><th></th>
          </tr>
        </thead>
        <tbody id="corpo-tabela-relatorios">
          <tr><td colspan="9" style="color:var(--fg-dim)">Carregando...</td></tr>
        </tbody>
      </table>
    </div>
  </div>

  <div class="modal-fundo" id="modal-novo-relatorio">
    <div class="modal-largo">
      <h3 id="titulo-modal-relatorio">Novo relatório em CONFIGURACOES_RELATORIO</h3>

      <div class="linha-dupla">
        <div>
          <label>Cliente</label>
          <input type="text" id="relatorio-cliente" placeholder="Nome do cliente">
        </div>
        <div>
          <label>Tipo de banco</label>
          <select id="relatorio-tipo-banco">
            <option value="SQL">SQL Server</option>
            <option value="ORACLE">Oracle</option>
          </select>
        </div>
      </div>

      <label>Conexão</label>
      <select id="relatorio-conexao-select" onchange="aplicarConexaoSelecionadaRelatorio()">
        <option value="">Selecione uma String Connection...</option>
      </select>
      <input type="hidden" id="relatorio-conexao">
      <div class="dica-campo" id="dica-conexao-nao-cadastrada-relatorio" style="display:none; color:var(--erro)">
        Este relatório usa uma conexão que não está cadastrada em String Connections - selecione uma da lista pra substituir.
      </div>

      <label>Script</label>
      <textarea id="relatorio-script" placeholder="SELECT ... (todos os dados desejados no relatório)"></textarea>
      <div class="dica-campo">SQL puro - a conversão pra base64 é feita automaticamente.</div>

      <label>E-mails</label>
      <input type="text" id="relatorio-emails" placeholder="contato87@example.com, contato35@example.com">
      <div class="dica-campo">Separados por vírgula.</div>

      <div class="linha-dupla">
        <div>
          <label>Título do e-mail</label>
          <input type="text" id="relatorio-titulo-email">
        </div>
        <div>
          <label>Nome do arquivo</label>
          <input type="text" id="relatorio-nome-arquivo">
        </div>
      </div>

      <label>Corpo do e-mail</label>
      <textarea id="relatorio-corpo-email" style="font-family:inherit; min-height:70px"></textarea>

      <div class="linha-tripla">
        <div>
          <label>Modelo do arquivo</label>
          <select id="relatorio-modelo-arquivo">
            <option value="P">Planilha</option>
            <option value="C">CSV</option>
            <option value="T">TXT</option>
          </select>
        </div>
        <div>
          <label>Reincidência</label>
          <select id="relatorio-reincidencia" onchange="atualizarCamposReincidencia()">
            <option value="DIARIO">Diário</option>
            <option value="SEMANAL">Semanal</option>
            <option value="MENSAL">Mensal</option>
          </select>
        </div>
        <div>
          <label>Hora de execução</label>
          <input type="time" id="relatorio-hora-execucao">
        </div>
      </div>

      <div id="campo-dia-semana" style="display:none">
        <label>Dia da semana</label>
        <select id="relatorio-dia-semana">
          <option value="Monday">Segunda-feira</option>
          <option value="Tuesday">Terça-feira</option>
          <option value="Wednesday">Quarta-feira</option>
          <option value="Thursday">Quinta-feira</option>
          <option value="Friday">Sexta-feira</option>
          <option value="Saturday">Sábado</option>
          <option value="Sunday">Domingo</option>
        </select>
        <div class="dica-campo">Se não escolher, assume Terça-feira.</div>
      </div>

      <div id="campo-dia-mensal" style="display:none">
        <label>Dia do mês</label>
        <input type="number" id="relatorio-dia-mensal" min="1" max="31" placeholder="1 a 31">
      </div>

      <label>Agrupador do relatório <span style="text-transform:none; color:var(--fg-dim)">(opcional)</span></label>
      <input type="text" id="relatorio-agrupador" placeholder="Só preencher se precisar juntar vários relatórios num e-mail só">
      <div class="dica-campo">Nome do agrupador cadastrado em AGRUPADOR_RELATORIO - deixe em branco na maioria dos casos.</div>

      <div class="campo-checkbox">
        <input type="checkbox" id="relatorio-disponibilidade" checked>
        <label for="relatorio-disponibilidade">Ativar este relatório imediatamente</label>
      </div>

      <div class="erro-modal" id="erro-novo-relatorio"></div>
      <div class="acoes-modal">
        <button class="btn-accent" id="botao-salvar-relatorio" onclick="salvarRelatorioBanco()" style="flex:1">Criar relatório</button>
        <button onclick="fecharModalNovoRelatorio()" style="flex:1">Cancelar</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast"></div>

  __FOOTER__

<script>
let idEmEdicaoRelatorio = null;
let todosOsRelatorios = [];
let stringConnectionsDisponiveis = [];

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

function atualizarCamposReincidencia() {
  const valor = document.getElementById('relatorio-reincidencia').value;
  document.getElementById('campo-dia-semana').style.display = valor === 'SEMANAL' ? 'block' : 'none';
  document.getElementById('campo-dia-mensal').style.display = valor === 'MENSAL' ? 'block' : 'none';
}

async function carregarRelatoriosBanco() {
  const avisoEl = document.getElementById('aviso-erro-banco');
  try {
    const resp = await fetch('/api/manutencao-relatorios');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível carregar os relatórios do banco de monitoramento: ' + (dados.erro || 'erro desconhecido.');
      document.getElementById('corpo-tabela-relatorios').innerHTML =
        '<tr><td colspan="9" style="color:var(--fg-dim)">Sem dados no momento.</td></tr>';
      return;
    }
    avisoEl.style.display = 'none';
    todosOsRelatorios = dados.registros;
    aplicarFiltrosRelatorios();
  } catch (e) {
    avisoEl.style.display = 'block';
    avisoEl.innerText = '⚠ Erro ao carregar: ' + e;
  }
}

function aplicarFiltrosRelatorios() {
  const filtroBusca = document.getElementById('filtro-cliente-rel').value.trim().toLowerCase();
  const filtroStatus = document.getElementById('filtro-status-rel').value;
  let filtrados = todosOsRelatorios;
  if (filtroBusca) {
    filtrados = filtrados.filter(r =>
      (r.cliente || '').toLowerCase().includes(filtroBusca) ||
      (r.titulo_email || '').toLowerCase().includes(filtroBusca) ||
      (r.tipo_banco || '').toLowerCase().includes(filtroBusca)
    );
  }
  if (filtroStatus) {
    filtrados = filtrados.filter(r => String(Number(r.disponibilidade)) === filtroStatus);
  }

  const corpo = document.getElementById('corpo-tabela-relatorios');
  if (todosOsRelatorios.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum relatório cadastrado ainda.</td></tr>';
    return;
  }
  if (filtrados.length === 0) {
    corpo.innerHTML = '<tr><td colspan="9" style="color:var(--fg-dim)">Nenhum relatório bate com o filtro.</td></tr>';
    return;
  }
  corpo.innerHTML = filtrados.map(r => {
    const ativo = Number(r.disponibilidade) === 1;
    const badge = ativo ? '<span class="badge-status badge-ativo">Ativo</span>' : '<span class="badge-status badge-inativo">Inativo</span>';
    return `
    <tr>
      <td>${r.id}</td>
      <td>${r.cliente || ''}</td>
      <td>${r.titulo_email || ''}</td>
      <td>${r.tipo_banco || ''}</td>
      <td>${r.modelo_arquivo || ''}</td>
      <td>${r.reincidencia || ''}</td>
      <td>${r.hora_execucao || ''}</td>
      <td>${badge}</td>
      <td>
        <div class="acoes-linha">
          <button class="btn-mini" onclick="abrirModalEditarRelatorio(${r.id})">Editar</button>
          <button class="btn-mini" onclick="alternarDisponibilidadeRelatorio(${r.id}, ${!ativo})">${ativo ? 'Desativar' : 'Ativar'}</button>
        </div>
      </td>
    </tr>
  `;
  }).join('');
}

function abrirModalNovoRelatorio() {
  idEmEdicaoRelatorio = null;
  document.getElementById('titulo-modal-relatorio').innerText = 'Novo relatório em CONFIGURACOES_RELATORIO';
  document.getElementById('botao-salvar-relatorio').innerText = 'Criar relatório';
  document.getElementById('erro-novo-relatorio').innerText = '';
  document.getElementById('relatorio-cliente').value = '';
  document.getElementById('relatorio-tipo-banco').value = 'SQL';
  document.getElementById('relatorio-conexao').value = '';
  document.getElementById('relatorio-conexao-select').value = '';
  document.getElementById('dica-conexao-nao-cadastrada-relatorio').style.display = 'none';
  document.getElementById('relatorio-script').value = '';
  document.getElementById('relatorio-emails').value = '';
  document.getElementById('relatorio-titulo-email').value = '';
  document.getElementById('relatorio-nome-arquivo').value = '';
  document.getElementById('relatorio-corpo-email').value = '';
  document.getElementById('relatorio-modelo-arquivo').value = 'P';
  document.getElementById('relatorio-reincidencia').value = 'DIARIO';
  document.getElementById('relatorio-dia-semana').value = 'Tuesday';
  document.getElementById('relatorio-dia-mensal').value = '';
  document.getElementById('relatorio-hora-execucao').value = '08:00';
  document.getElementById('relatorio-agrupador').value = '';
  document.getElementById('relatorio-disponibilidade').checked = true;
  atualizarCamposReincidencia();
  document.getElementById('modal-novo-relatorio').classList.add('aberto');
}

async function abrirModalEditarRelatorio(id) {
  const resp = await fetch('/api/manutencao-relatorios/' + id);
  const dados = await resp.json();
  if (!dados.ok) {
    mostrarToast(dados.erro || 'Não foi possível carregar esse relatório.');
    return;
  }
  const r = dados.registro;
  idEmEdicaoRelatorio = id;
  document.getElementById('titulo-modal-relatorio').innerText = 'Editar relatório #' + id + ' (CONFIGURACOES_RELATORIO)';
  document.getElementById('botao-salvar-relatorio').innerText = 'Salvar alterações';
  document.getElementById('erro-novo-relatorio').innerText = '';
  document.getElementById('relatorio-cliente').value = r.cliente || '';
  document.getElementById('relatorio-tipo-banco').value = r.tipo_banco || 'SQL';
  document.getElementById('relatorio-conexao').value = r.conexao || '';
  document.getElementById('relatorio-script').value = r.script || '';
  document.getElementById('relatorio-emails').value = r.emails || '';
  document.getElementById('relatorio-titulo-email').value = r.titulo_email || '';
  document.getElementById('relatorio-nome-arquivo').value = r.nome_arquivo || '';
  document.getElementById('relatorio-corpo-email').value = r.corpo_email || '';
  document.getElementById('relatorio-modelo-arquivo').value = r.modelo_arquivo || 'P';
  document.getElementById('relatorio-reincidencia').value = r.reincidencia || 'DIARIO';
  document.getElementById('relatorio-dia-semana').value = r.dia_semana || 'Tuesday';
  document.getElementById('relatorio-dia-mensal').value = r.dia_mensal || '';
  document.getElementById('relatorio-hora-execucao').value = r.hora_execucao || '08:00';
  document.getElementById('relatorio-agrupador').value = r.agrupador_relatorio || '';
  document.getElementById('relatorio-disponibilidade').checked = Number(r.disponibilidade) === 1;
  atualizarCamposReincidencia();

  const selectConexao = document.getElementById('relatorio-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-relatorio');
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

  document.getElementById('modal-novo-relatorio').classList.add('aberto');
}

function fecharModalNovoRelatorio() {
  document.getElementById('modal-novo-relatorio').classList.remove('aberto');
  carregarRelatoriosBanco();
}

function _corpoFormularioRelatorio() {
  return 'cliente=' + encodeURIComponent(document.getElementById('relatorio-cliente').value) +
    '&tipo_banco=' + encodeURIComponent(document.getElementById('relatorio-tipo-banco').value) +
    '&conexao=' + encodeURIComponent(document.getElementById('relatorio-conexao').value) +
    '&script=' + encodeURIComponent(document.getElementById('relatorio-script').value) +
    '&emails=' + encodeURIComponent(document.getElementById('relatorio-emails').value) +
    '&titulo_email=' + encodeURIComponent(document.getElementById('relatorio-titulo-email').value) +
    '&nome_arquivo=' + encodeURIComponent(document.getElementById('relatorio-nome-arquivo').value) +
    '&corpo_email=' + encodeURIComponent(document.getElementById('relatorio-corpo-email').value) +
    '&modelo_arquivo=' + encodeURIComponent(document.getElementById('relatorio-modelo-arquivo').value) +
    '&reincidencia=' + encodeURIComponent(document.getElementById('relatorio-reincidencia').value) +
    '&dia_semana=' + encodeURIComponent(document.getElementById('relatorio-dia-semana').value) +
    '&dia_mensal=' + encodeURIComponent(document.getElementById('relatorio-dia-mensal').value) +
    '&hora_execucao=' + encodeURIComponent(document.getElementById('relatorio-hora-execucao').value) +
    '&agrupador_relatorio=' + encodeURIComponent(document.getElementById('relatorio-agrupador').value) +
    '&disponibilidade=' + (document.getElementById('relatorio-disponibilidade').checked ? 'true' : 'false');
}

async function salvarRelatorioBanco() {
  const erroEl = document.getElementById('erro-novo-relatorio');

  if (!document.getElementById('relatorio-conexao').value) {
    erroEl.innerText = 'Selecione uma String Connection pra esse relatório.';
    return;
  }

  const url = idEmEdicaoRelatorio === null ? '/api/manutencao-relatorios/criar' : '/api/manutencao-relatorios/atualizar';
  const corpo = idEmEdicaoRelatorio === null
    ? _corpoFormularioRelatorio()
    : 'id=' + encodeURIComponent(idEmEdicaoRelatorio) + '&' + _corpoFormularioRelatorio();

  const resp = await fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: corpo,
  });
  const dados = await resp.json();
  if (!dados.ok) {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
    return;
  }
  mostrarToast(idEmEdicaoRelatorio === null ? 'Relatório criado.' : 'Relatório #' + idEmEdicaoRelatorio + ' atualizado.');
  fecharModalNovoRelatorio();
}

async function alternarDisponibilidadeRelatorio(id, ativar) {
  const resp = await fetch('/api/manutencao-relatorios/disponibilidade', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + encodeURIComponent(id) + '&ativo=' + (ativar ? 'true' : 'false'),
  });
  const dados = await resp.json();
  if (dados.ok) {
    mostrarToast('Relatório #' + id + (ativar ? ' ativado.' : ' desativado.'));
    carregarRelatoriosBanco();
  } else {
    mostrarToast(dados.erro || 'Não foi possível alterar.');
  }
}

async function carregarStringConnectionsParaSelect() {
  try {
    const resp = await fetch('/api/string-connections');
    const dados = await resp.json();
    if (!dados.ok) return;
    stringConnectionsDisponiveis = dados.conexoes;
    const select = document.getElementById('relatorio-conexao-select');
    select.innerHTML = '<option value="">Selecione uma String Connection...</option>' +
      dados.conexoes.map(c => `<option value="${c.id}">${c.cliente} · ${c.produto}</option>`).join('');
  } catch (e) {
    // sem conexao pra rede/erro qualquer - falha silenciosa aqui esta ok
  }
}

function aplicarConexaoSelecionadaRelatorio() {
  const select = document.getElementById('relatorio-conexao-select');
  const avisoNaoCadastrada = document.getElementById('dica-conexao-nao-cadastrada-relatorio');
  const encontrada = stringConnectionsDisponiveis.find(c => c.id === select.value);
  if (encontrada) {
    document.getElementById('relatorio-conexao').value = encontrada.conexao;
    avisoNaoCadastrada.style.display = 'none';
  } else {
    document.getElementById('relatorio-conexao').value = '';
  }
}

carregarRelatoriosBanco();
carregarStringConnectionsParaSelect();
</script>

</body>
</html>
"""
