"""Tela Indicadores Mensais (Avaliação de Efetividade, NOC Pendente e Considerar/Desconsiderar Satisfação).

Só texto (HTML/CSS/JS); a lógica fica em logica.py e as rotas no alertas_gui.py.
Sem barra invertida no JS deste template (vira escape do Python).
"""


_INDICADORES_MENSAIS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Indicadores Mensais</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-imx { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                   gap: 14px; max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .cabecalho-imx h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-imx .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; max-width: 640px; }
  .periodo-imx { display: flex; align-items: flex-end; gap: 8px; }
  .periodo-imx label { display: block; font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                       letter-spacing: .05em; margin-bottom: 5px; }
  .campo-imx { background: rgba(var(--poco),.2); border: 1px solid var(--border); color: var(--fg);
               border-radius: 8px; padding: 8px 10px; font-size: 13px; font-family: inherit; }
  .campo-imx:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  input[type="month"].campo-imx { color-scheme: dark; }
  :root[data-tema="claro"] input[type="month"].campo-imx { color-scheme: light; }

  .abas-imx { display: flex; gap: 6px; flex-wrap: wrap; max-width: var(--largura-pagina); margin: 0 auto 14px auto;
              border-bottom: 1px solid var(--border); }
  .aba-imx { background: none; border: none; border-bottom: 2px solid transparent; color: var(--fg-dim);
             padding: 10px 14px; font-size: 13px; font-weight: 600; cursor: pointer; display: flex;
             align-items: center; gap: 8px; margin-bottom: -1px; font-family: inherit; }
  .aba-imx:hover:not(:disabled) { color: var(--fg); }
  .aba-imx.ativa { color: var(--fg); border-bottom-color: var(--teal); }
  .aba-imx:disabled { cursor: default; opacity: .5; }
  .contador-imx { font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 999px;
                  background: rgba(var(--tinta),.08); color: var(--fg-dim); }
  .contador-imx.pendente { background: rgba(232,163,61,.15); color: #e8a33d; }
  .contador-imx.zerado { background: rgba(78,201,176,.15); color: var(--ok); }
  .tag-breve-imx { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .04em; color: var(--run); }

  .painel-imx { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
                max-width: var(--largura-pagina); margin: 0 auto 20px auto; display: none; }
  .painel-imx.ativo { display: block; }
  .painel-movidesk-imx { padding: 0 !important; background: none !important; border: none !important; backdrop-filter: none !important; }
  .painel-movidesk-imx iframe { width: 100%; min-height: 900px; border: 0; display: block; background: transparent; }
  .painel-imx h2 { margin: 0 0 6px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .06em; }
  .painel-imx .sub-painel { color: var(--fg-dim); font-size: 12px; margin-bottom: 16px; line-height: 1.5; }
  .barra-imx { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
  .barra-imx .campo-imx { min-width: 200px; }
  .barra-imx .busca { flex: 1 0 280px; }
  .barra-imx select.campo-imx { min-width: 170px; }
  /* sem espaço na linha, o resumo desce pra linha de baixo em vez de espremer a busca */
  .resumo-imx { font-size: 12px; color: var(--fg-dim); margin-left: auto; white-space: nowrap; }

  .rolagem-imx { overflow-x: auto; }
  .tabela-imx { width: 100%; border-collapse: collapse; font-size: 12.5px; }
  .tabela-imx th { text-align: left; color: var(--fg-dim); font-weight: 600; font-size: 10.5px; text-transform: uppercase;
                   letter-spacing: .04em; padding: 8px 10px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabela-imx td { padding: 9px 10px; border-bottom: 1px solid rgba(var(--tinta),.06); vertical-align: middle; }
  .tabela-imx tr.salvo td { background: rgba(78,201,176,.05); }
  .tabela-imx .id-imx { font-family: Consolas, monospace; font-size: 12px; color: var(--teal); white-space: nowrap; }
  .tabela-imx a.link-ticket-imx { color: var(--teal); text-decoration: none; border-bottom: 1px dashed rgba(45,184,207,.5); }
  .tabela-imx a.link-ticket-imx:hover { border-bottom-style: solid; }
  .tabela-imx a.link-ticket-imx::after { content: " ↗"; font-size: 10px; opacity: .7; }
  .tabela-imx .fraco { color: var(--fg-dim); font-size: 11.5px; }
  .comentario-imx { font-size: 12px; line-height: 1.5; max-width: 360px; white-space: pre-wrap; word-break: break-word; }
  .comentario-imx + .comentario-imx { margin-top: 6px; padding-top: 6px; border-top: 1px dashed rgba(var(--tinta),.12); }
  .equipe-imx { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 10.5px; font-weight: 700;
                letter-spacing: .03em; background: rgba(var(--tinta),.07); color: var(--fg); white-space: nowrap; }
  .tabela-imx .assunto { max-width: 340px; }
  .nowrap { white-space: nowrap; }

  /* Sim / Não lado a lado: o escolhido fica pintado */
  .seletor-imx { display: inline-flex; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }
  .seletor-imx button { background: rgba(var(--tinta),.03); border: none; color: var(--fg); padding: 6px 14px;
                        font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit; white-space: nowrap; }
  .seletor-imx button + button { border-left: 1px solid var(--border); }
  .seletor-imx button:hover:not(:disabled) { background: rgba(var(--tinta),.08); }
  .seletor-imx button.escolhido.sim { background: rgba(78,201,176,.2); color: var(--ok); }
  .seletor-imx button.escolhido.nao { background: rgba(241,76,76,.18); color: var(--erro); }
  .seletor-imx button:disabled { cursor: default; opacity: .6; }
  .status-linha-imx { font-size: 11px; margin-top: 4px; min-height: 13px; }
  .status-linha-imx.ok { color: var(--ok); }
  .status-linha-imx.erro { color: var(--erro); }

  .seletor-imx button.escolhido.considerar { background: rgba(78,201,176,.2); color: var(--ok); }
  .seletor-imx button.escolhido.desconsiderar { background: rgba(var(--tinta),.12); color: var(--fg); }
  .respostas-imx { font-size: 10px; color: var(--fg-dim); margin-left: 4px; }

  .tempo-imx { display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 700;
               background: rgba(232,163,61,.15); color: #e8a33d; white-space: nowrap; }
  .tempo-imx.muito { background: rgba(241,76,76,.15); color: var(--erro); }
  .justificativa-imx { display: flex; gap: 6px; align-items: center; }
  .justificativa-imx select { min-width: 230px; }
  .btn-mini-imx { padding: 6px 12px; font-size: 12px; border-radius: 8px; border: 1px solid var(--border);
                  background: rgba(var(--tinta),.05); color: var(--fg); cursor: pointer; font-family: inherit; white-space: nowrap; }
  .btn-mini-imx:hover:not(:disabled) { border-color: var(--teal); }
  .btn-mini-imx:disabled { opacity: .45; cursor: default; }
  .detalhes-imx td { background: rgba(var(--poco),.15); }
  .grade-detalhes-imx { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 6px 16px; font-size: 11.5px; }
  .grade-detalhes-imx .rotulo { color: var(--fg-dim); font-size: 10px; text-transform: uppercase; letter-spacing: .04em; }
  .grade-detalhes-imx .valor { word-break: break-word; }

  .vazio-imx { text-align: center; color: var(--fg-dim); font-size: 13px; padding: 34px 10px; }
  .vazio-imx .grande { font-size: 15px; color: var(--ok); font-weight: 700; margin-bottom: 4px; }
  .erro-imx { color: var(--erro); font-size: 12.5px; padding: 12px 0; }
  .breve-imx { text-align: center; padding: 40px 10px; color: var(--fg-dim); font-size: 13px; line-height: 1.6; }

  @media (max-width: 700px) {
    .barra-imx .campo-imx { min-width: 0; width: 100%; }
    .barra-imx .busca { flex-basis: 100%; }
    .resumo-imx { margin-left: 0; white-space: normal; }
    .justificativa-imx { flex-direction: column; align-items: stretch; }
    .justificativa-imx select { min-width: 0; }
  }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-imx">
      <div>
        <h1>Indicadores Mensais</h1>
        <div class="sub">
          Pendências que fecham os indicadores do mês, direto no banco do Movidesk:
          efetividade dos tickets do Monitoramento, justificativa do NOC fora do prazo
          e quais pesquisas "Insatisfeito" entram no indicador de satisfação.
        </div>
      </div>
      <div class="periodo-imx">
        <div>
          <label for="imx-mes">Mês</label>
          <input type="month" id="imx-mes" class="campo-imx">
        </div>
        <button class="btn-accent" onclick="carregarTudoIMX()">Atualizar</button>
      </div>
    </div>

    <div class="abas-imx">
      <button class="aba-imx ativa" data-aba="efetividade" onclick="trocarAbaIMX('efetividade')">
        Avaliação de Efetividade <span class="contador-imx" id="imx-contador-efetividade">...</span>
      </button>
      <button class="aba-imx" data-aba="noc" onclick="trocarAbaIMX('noc')">
        NOC Pendente <span class="contador-imx" id="imx-contador-noc">...</span>
      </button>
      <button class="aba-imx" data-aba="satisfacao" onclick="trocarAbaIMX('satisfacao')">
        Considerar/Desconsiderar Satisfação <span class="contador-imx" id="imx-contador-satisfacao">...</span>
      </button>
      <button class="aba-imx" data-aba="movidesk" onclick="trocarAbaIMX('movidesk')">Indicadores Movidesk</button>
    </div>

    <!-- Indicadores Movidesk (3.1.6.0): a tela inteira do card, embutida (carrega na primeira vez que abre a aba) -->
    <div class="painel-imx painel-movidesk-imx" id="imx-painel-movidesk">
      <iframe id="imx-frame-movidesk" title="Indicadores Movidesk" loading="lazy"></iframe>
    </div>

    <!-- Avaliação de Efetividade -->
    <div class="painel-imx ativo" id="imx-painel-efetividade">
      <h2>Tickets sem efetividade</h2>
      <div class="sub-painel">
        Tickets do Monitoramento resolvidos <b>nos últimos 30 dias</b> (fechados ou não, não depende do mês escolhido acima), dos clientes da avaliação,
        com a efetividade em branco. Clique em Sim ou Não pra gravar na hora; dá pra trocar
        enquanto o ticket estiver na tela. Ao atualizar, os marcados saem da lista.
      </div>
      <div class="barra-imx">
        <input type="text" class="campo-imx busca" id="imx-busca-efetividade" placeholder="Buscar por ticket, cliente, assunto ou responsável..." oninput="desenharEfetividadeIMX()">
        <select class="campo-imx" id="imx-org-efetividade" onchange="desenharEfetividadeIMX()">
          <option value="">Todas as organizações</option>
        </select>
        <span class="resumo-imx" id="imx-resumo-efetividade"></span>
      </div>
      <div id="imx-conteudo-efetividade"><div class="vazio-imx">Carregando...</div></div>
    </div>

    <!-- NOC Pendente -->
    <div class="painel-imx" id="imx-painel-noc">
      <h2>NOC fora do prazo sem justificativa</h2>
      <div class="sub-painel" id="imx-sub-noc">
        Chamados do NOC criados no mês com a primeira resposta acima do prazo e sem justificativa.
        Escolha a justificativa e ela grava na hora.
      </div>
      <div class="barra-imx">
        <input type="text" class="campo-imx busca" id="imx-busca-noc" placeholder="Buscar em qualquer campo..." oninput="desenharNocIMX()">
        <span class="resumo-imx" id="imx-resumo-noc"></span>
      </div>
      <div id="imx-conteudo-noc"><div class="vazio-imx">Carregando...</div></div>
    </div>

    <!-- Considerar/Desconsiderar pesquisa de satisfação -->
    <div class="painel-imx" id="imx-painel-satisfacao">
      <h2>Pesquisas de satisfação "Insatisfeito"</h2>
      <div class="sub-painel">
        Tickets do Suporte, Monitoramento e Serviços fechados no mês com pesquisa "Insatisfeito".
        Marque se a avaliação entra (Considerar) ou não (Não considerar) no indicador; grava na hora
        e dá pra trocar depois. Se o ticket tiver mais de uma resposta, a marcação vale pra todas.
      </div>
      <div class="barra-imx">
        <input type="text" class="campo-imx busca" id="imx-busca-satisfacao" placeholder="Buscar por ticket, organização, assunto ou descrição..." oninput="desenharSatisfacaoIMX()">
        <select class="campo-imx" id="imx-status-satisfacao" onchange="desenharSatisfacaoIMX()">
          <option value="pendente">Sem marcação</option>
          <option value="S">Considerados</option>
          <option value="N">Não considerados</option>
          <option value="">Todos</option>
        </select>
        <select class="campo-imx" id="imx-time-satisfacao" onchange="desenharSatisfacaoIMX()">
          <option value="">Todos os times</option>
          <option value="SUPORTE">Suporte</option>
          <option value="MONITORAMENTO">Monitoramento</option>
          <option value="SERVIÇOS">Serviços</option>
        </select>
        <span class="resumo-imx" id="imx-resumo-satisfacao"></span>
      </div>
      <div id="imx-conteudo-satisfacao"><div class="vazio-imx">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

  <div class="toast" id="toast"></div>

<script>
const MESES_IMX = ['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'];
let ticketsEfetividadeIMX = [];
let opcoesEfetividadeIMX = ['Sim', 'Não'];
let registrosNocIMX = [];
let opcoesNocIMX = [];
const salvosEfetividadeIMX = {};   // id -> valor gravado nesta visita
const salvosNocIMX = {};
const detalhesAbertosNocIMX = new Set();

function escaparIMX(v) {
  return String(v == null ? '' : v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// ID do ticket clicável (abre no Movidesk em outra aba); sem link, só o número
function linkTicketIMX(t) {
  const texto = '#' + escaparIMX(t.id);
  return t.link
    ? '<a class="link-ticket-imx" href="' + escaparIMX(t.link) + '" target="_blank" rel="noopener" title="Abrir o ticket no Movidesk">' + texto + '</a>'
    : texto;
}

function mostrarToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3000);
}

function nomeMesIMX(valor) {
  const [ano, mes] = (valor || '').split('-');
  return mes ? MESES_IMX[parseInt(mes, 10) - 1] + '/' + ano : '';
}

// 3.4.8.1: abre no mês atual (antes, o anterior) e acompanha a virada do mês sozinho enquanto ninguém escolheu outro
function mesAtualIMX() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}
let mesSeguidoIMX = null;  // o mês atual que a tela está seguindo; null = a pessoa escolheu um mês à mão
function conferirViradaDoMesIMX() {
  if (!mesSeguidoIMX || mesAtualIMX() === mesSeguidoIMX) return;
  document.getElementById('imx-mes').value = mesAtualIMX();
  carregarTudoIMX();
}

function trocarAbaIMX(aba) {
  document.querySelectorAll('.aba-imx[data-aba]').forEach(b => b.classList.toggle('ativa', b.dataset.aba === aba));
  document.querySelectorAll('.painel-imx').forEach(p => p.classList.toggle('ativo', p.id === 'imx-painel-' + aba));
  try { localStorage.setItem('imx-aba', aba); } catch (e) {}
  const frame = document.getElementById('imx-frame-movidesk');
  if (aba === 'movidesk' && !frame.getAttribute('src')) frame.setAttribute('src', '/indicadores-movidesk?embutido=1');
}
window.addEventListener('message', e => {
  if (e.origin !== location.origin || !e.data || !e.data.alturaIndicadoresMovidesk) return;
  document.getElementById('imx-frame-movidesk').style.height = Math.max(600, e.data.alturaIndicadoresMovidesk) + 'px';
});

function atualizarContadorIMX(id, pendentes) {
  const el = document.getElementById(id);
  el.innerText = pendentes;
  el.className = 'contador-imx ' + (pendentes > 0 ? 'pendente' : 'zerado');
}

async function buscarJSONIMX(url, opcoes) {
  const resp = await fetch(url, opcoes);
  if (resp.status === 401) { window.location.href = '/login'; throw new Error('sessão expirada'); }
  if (resp.status === 403) { window.location.href = '/'; throw new Error('sem acesso'); }
  return resp.json();
}

function postIMX(url, campos) {
  const corpo = Object.entries(campos).map(([k, v]) => k + '=' + encodeURIComponent(v)).join('&');
  return buscarJSONIMX(url, { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: corpo });
}

function carregarTudoIMX() {
  const campo = document.getElementById('imx-mes');
  if (!campo.value) campo.value = mesAtualIMX();
  const mes = campo.value;
  // mês atual não vai pro endereço: recarregar (ou abrir amanhã) segue o mês corrente; outro mês fica no link pra compartilhar
  mesSeguidoIMX = mes === mesAtualIMX() ? mes : null;
  try { history.replaceState(null, '', mesSeguidoIMX ? location.pathname : '?mes=' + mes); } catch (e) {}
  carregarEfetividadeIMX(mes);
  carregarNocIMX(mes);
  carregarSatisfacaoIMX(mes);
}

// ---------------- Avaliação de Efetividade ----------------
async function carregarEfetividadeIMX(mes) {
  const conteudo = document.getElementById('imx-conteudo-efetividade');
  conteudo.innerHTML = '<div class="vazio-imx">Consultando o banco...</div>';
  document.getElementById('imx-contador-efetividade').innerText = '...';
  for (const k of Object.keys(salvosEfetividadeIMX)) delete salvosEfetividadeIMX[k];
  try {
    const dados = await buscarJSONIMX('/api/indicadores-mensais/efetividade?mes=' + encodeURIComponent(mes));
    if (!dados.ok) {
      conteudo.innerHTML = '<div class="erro-imx">' + escaparIMX(dados.erro || 'Não foi possível consultar.') + '</div>';
      document.getElementById('imx-contador-efetividade').innerText = '!';
      return;
    }
    ticketsEfetividadeIMX = dados.tickets || [];
    opcoesEfetividadeIMX = dados.opcoes || opcoesEfetividadeIMX;
    const orgs = [...new Set(ticketsEfetividadeIMX.map(t => t.organizacao).filter(Boolean))].sort();
    const select = document.getElementById('imx-org-efetividade');
    const atual = select.value;
    select.innerHTML = '<option value="">Todas as organizações</option>' +
      orgs.map(o => '<option value="' + escaparIMX(o) + '">' + escaparIMX(o) + '</option>').join('');
    select.value = orgs.includes(atual) ? atual : '';
    desenharEfetividadeIMX();
  } catch (e) {
    conteudo.innerHTML = '<div class="erro-imx">Erro ao consultar: ' + escaparIMX(e.message) + '</div>';
  }
}

function desenharEfetividadeIMX() {
  const conteudo = document.getElementById('imx-conteudo-efetividade');
  const termo = document.getElementById('imx-busca-efetividade').value.trim().toLowerCase();
  const org = document.getElementById('imx-org-efetividade').value;
  const mes = document.getElementById('imx-mes').value;
  const pendentes = ticketsEfetividadeIMX.filter(t => !salvosEfetividadeIMX[t.id]).length;
  atualizarContadorIMX('imx-contador-efetividade', pendentes);

  if (!ticketsEfetividadeIMX.length) {
    conteudo.innerHTML = '<div class="vazio-imx"><div class="grande">Tudo em dia</div>Nenhum ticket sem efetividade nos últimos 30 dias.</div>';
    document.getElementById('imx-resumo-efetividade').innerText = '';
    return;
  }
  const lista = ticketsEfetividadeIMX.filter(t => {
    if (org && t.organizacao !== org) return false;
    if (!termo) return true;
    return [t.id, t.organizacao, t.cliente, t.assunto, t.responsavel, t.categoria].join(' ').toLowerCase().includes(termo);
  });
  document.getElementById('imx-resumo-efetividade').innerText =
    pendentes + ' pendente(s) de ' + ticketsEfetividadeIMX.length + (lista.length !== ticketsEfetividadeIMX.length ? ' · ' + lista.length + ' no filtro' : '');
  if (!lista.length) {
    conteudo.innerHTML = '<div class="vazio-imx">Nenhum ticket bate com o filtro.</div>';
    return;
  }
  conteudo.innerHTML = '<div class="rolagem-imx"><table class="tabela-imx"><thead><tr>' +
    '<th>Ticket</th><th>Organização · Cliente</th><th>Assunto</th><th>Responsável</th><th>Resolvido em</th><th>Efetividade</th>' +
    '</tr></thead><tbody>' + lista.map(t => {
      const salvo = salvosEfetividadeIMX[t.id];
      const botoes = opcoesEfetividadeIMX.map(op => {
        const classe = (salvo === op ? 'escolhido ' : '') + (op === 'Sim' ? 'sim' : 'nao');
        return '<button class="' + classe + '" onclick="definirEfetividadeIMX(' + Number(t.id) + ', ' + "'" + op + "'" + ', this)">' + escaparIMX(op) + '</button>';
      }).join('');
      return '<tr id="imx-ef-' + Number(t.id) + '" class="' + (salvo ? 'salvo' : '') + '">' +
        '<td class="id-imx">' + linkTicketIMX(t) + '</td>' +
        '<td>' + escaparIMX(t.organizacao) + '<div class="fraco">' + escaparIMX(t.cliente) + '</div></td>' +
        '<td class="assunto">' + escaparIMX(t.assunto) + (t.categoria ? '<div class="fraco">' + escaparIMX(t.categoria) + '</div>' : '') + '</td>' +
        '<td>' + escaparIMX(t.responsavel) + '</td>' +
        '<td class="nowrap fraco">' + escaparIMX(t.resolvido_em) + '</td>' +
        '<td><div class="seletor-imx">' + botoes + '</div>' +
        '<div class="status-linha-imx ' + (salvo ? 'ok' : '') + '">' + (salvo ? 'Salvo: ' + escaparIMX(salvo) : '') + '</div></td>' +
        '</tr>';
    }).join('') + '</tbody></table></div>';
}

async function definirEfetividadeIMX(id, valor, botao) {
  const linha = document.getElementById('imx-ef-' + id);
  const status = linha.querySelector('.status-linha-imx');
  linha.querySelectorAll('.seletor-imx button').forEach(b => b.disabled = true);
  status.className = 'status-linha-imx';
  status.innerText = 'Gravando...';
  try {
    const dados = await postIMX('/api/indicadores-mensais/efetividade', { id: id, valor: valor });
    if (dados.ok) {
      salvosEfetividadeIMX[id] = valor;
      mostrarToast('Ticket #' + id + ': efetividade ' + valor + '.');
      desenharEfetividadeIMX();
      return;
    }
    status.className = 'status-linha-imx erro';
    status.innerText = dados.erro || 'Não foi possível gravar.';
  } catch (e) {
    status.className = 'status-linha-imx erro';
    status.innerText = 'Erro: ' + e.message;
  }
  linha.querySelectorAll('.seletor-imx button').forEach(b => b.disabled = false);
}

// ---------------- NOC Pendente ----------------
async function carregarNocIMX(mes) {
  const conteudo = document.getElementById('imx-conteudo-noc');
  conteudo.innerHTML = '<div class="vazio-imx">Consultando o banco...</div>';
  document.getElementById('imx-contador-noc').innerText = '...';
  for (const k of Object.keys(salvosNocIMX)) delete salvosNocIMX[k];
  detalhesAbertosNocIMX.clear();
  try {
    const dados = await buscarJSONIMX('/api/indicadores-mensais/noc?mes=' + encodeURIComponent(mes));
    if (!dados.ok) {
      conteudo.innerHTML = '<div class="erro-imx">' + escaparIMX(dados.erro || 'Não foi possível consultar.') + '</div>';
      document.getElementById('imx-contador-noc').innerText = '!';
      return;
    }
    registrosNocIMX = dados.registros || [];
    opcoesNocIMX = dados.opcoes || [];
    document.getElementById('imx-sub-noc').innerText =
      'Chamados do NOC criados no mês com a primeira resposta acima de ' + dados.limite_minutos +
      ' minutos e sem justificativa. Escolha a justificativa e ela grava na hora.';
    desenharNocIMX();
  } catch (e) {
    conteudo.innerHTML = '<div class="erro-imx">Erro ao consultar: ' + escaparIMX(e.message) + '</div>';
  }
}

function textoBuscaNocIMX(r) {
  return [r.id, r.criado_em, r.tempo_minutos, ...Object.values(r.detalhes || {})].join(' ').toLowerCase();
}

function desenharNocIMX() {
  const conteudo = document.getElementById('imx-conteudo-noc');
  const termo = document.getElementById('imx-busca-noc').value.trim().toLowerCase();
  const mes = document.getElementById('imx-mes').value;
  const pendentes = registrosNocIMX.filter(r => !salvosNocIMX[r.id]).length;
  atualizarContadorIMX('imx-contador-noc', pendentes);

  if (!registrosNocIMX.length) {
    conteudo.innerHTML = '<div class="vazio-imx"><div class="grande">Tudo em dia</div>Nenhum chamado do NOC fora do prazo sem justificativa em ' + escaparIMX(nomeMesIMX(mes)) + '.</div>';
    document.getElementById('imx-resumo-noc').innerText = '';
    return;
  }
  const lista = registrosNocIMX.filter(r => !termo || textoBuscaNocIMX(r).includes(termo));
  document.getElementById('imx-resumo-noc').innerText =
    pendentes + ' pendente(s) de ' + registrosNocIMX.length + (lista.length !== registrosNocIMX.length ? ' · ' + lista.length + ' no filtro' : '');
  if (!lista.length) {
    conteudo.innerHTML = '<div class="vazio-imx">Nenhum chamado bate com a busca.</div>';
    return;
  }
  conteudo.innerHTML = '<div class="rolagem-imx"><table class="tabela-imx"><thead><tr>' +
    '<th>Ticket</th><th>Criado em</th><th>1ª resposta</th><th>Detalhes</th><th>Justificativa</th>' +
    '</tr></thead><tbody>' + lista.map(r => {
      const id = Number(r.id);
      const salvo = salvosNocIMX[r.id];
      const minutos = Number(r.tempo_minutos);
      const opcoes = '<option value="">Escolha a justificativa...</option>' + opcoesNocIMX.map(op =>
        '<option value="' + escaparIMX(op) + '"' + (salvo === op ? ' selected' : '') + '>' + escaparIMX(op) + '</option>').join('');
      const aberto = detalhesAbertosNocIMX.has(id);
      const detalhes = Object.entries(r.detalhes || {}).filter(([k, v]) => v !== null && v !== '');
      let html = '<tr id="imx-noc-' + id + '" class="' + (salvo ? 'salvo' : '') + '">' +
        '<td class="id-imx">' + linkTicketIMX({ id: r.ticket != null ? r.ticket : r.id, link: r.link }) +
          (r.ticket != null && String(r.ticket) !== String(r.id) ? '<div class="respostas-imx">NOC ' + escaparIMX(r.id) + '</div>' : '') + '</td>' +
        '<td class="nowrap fraco">' + escaparIMX(r.criado_em) + '</td>' +
        '<td><span class="tempo-imx' + (minutos > 120 ? ' muito' : '') + '">' + escaparIMX(r.tempo_minutos) + ' min</span></td>' +
        '<td><button class="btn-mini-imx" onclick="alternarDetalhesNocIMX(' + id + ')">' + (aberto ? 'Esconder' : 'Ver (' + detalhes.length + ')') + '</button></td>' +
        '<td><div class="justificativa-imx">' +
          '<select class="campo-imx" onchange="salvarJustificativaNocIMX(' + id + ')">' + opcoes + '</select>' +
        '</div><div class="status-linha-imx ' + (salvo ? 'ok' : '') + '">' + (salvo ? 'Salvo: ' + escaparIMX(salvo) : '') + '</div></td>' +
        '</tr>';
      if (aberto) {
        html += '<tr class="detalhes-imx"><td colspan="5"><div class="grade-detalhes-imx">' +
          (detalhes.length ? detalhes.map(([k, v]) =>
            '<div><div class="rotulo">' + escaparIMX(k) + '</div><div class="valor">' + escaparIMX(v) + '</div></div>').join('')
            : '<div class="fraco">Sem outros campos preenchidos.</div>') +
          '</div></td></tr>';
      }
      return html;
    }).join('') + '</tbody></table></div>';
}

function alternarDetalhesNocIMX(id) {
  if (detalhesAbertosNocIMX.has(id)) detalhesAbertosNocIMX.delete(id); else detalhesAbertosNocIMX.add(id);
  desenharNocIMX();
}

// grava assim que a justificativa é escolhida (2.34.3.1, antes tinha botão Salvar);
// se der erro, o select volta pro que estava gravado, pra não parecer salvo
async function salvarJustificativaNocIMX(id) {
  const linha = document.getElementById('imx-noc-' + id);
  const select = linha.querySelector('select');
  const status = linha.querySelector('.status-linha-imx');
  const valor = select.value;
  const anterior = salvosNocIMX[id] || '';
  if (!valor || valor === anterior) { select.value = anterior; return; }
  select.disabled = true;
  status.className = 'status-linha-imx';
  status.innerText = 'Gravando...';
  try {
    const dados = await postIMX('/api/indicadores-mensais/noc', { id: id, valor: valor });
    if (dados.ok) {
      salvosNocIMX[id] = valor;
      mostrarToast('NOC ' + id + ': ' + valor + '.');
      desenharNocIMX();
      return;
    }
    status.className = 'status-linha-imx erro';
    status.innerText = dados.erro || 'Não foi possível gravar.';
  } catch (e) {
    status.className = 'status-linha-imx erro';
    status.innerText = 'Erro: ' + e.message;
  }
  select.value = anterior;
  select.disabled = false;
}

// ---------------- Considerar/Desconsiderar satisfação ----------------
let ticketsSatisfacaoIMX = [];
let opcoesSatisfacaoIMX = { S: 'Considerar', N: 'Não considerar' };
const marcadosAgoraSatisfacaoIMX = new Set();   // continuam na tela até atualizar, mesmo saindo do filtro

async function carregarSatisfacaoIMX(mes) {
  const conteudo = document.getElementById('imx-conteudo-satisfacao');
  conteudo.innerHTML = '<div class="vazio-imx">Consultando o banco...</div>';
  document.getElementById('imx-contador-satisfacao').innerText = '...';
  marcadosAgoraSatisfacaoIMX.clear();
  try {
    const dados = await buscarJSONIMX('/api/indicadores-mensais/satisfacao?mes=' + encodeURIComponent(mes));
    if (!dados.ok) {
      conteudo.innerHTML = '<div class="erro-imx">' + escaparIMX(dados.erro || 'Não foi possível consultar.') + '</div>';
      document.getElementById('imx-contador-satisfacao').innerText = '!';
      return;
    }
    ticketsSatisfacaoIMX = dados.tickets || [];
    opcoesSatisfacaoIMX = dados.opcoes || opcoesSatisfacaoIMX;
    desenharSatisfacaoIMX();
  } catch (e) {
    conteudo.innerHTML = '<div class="erro-imx">Erro ao consultar: ' + escaparIMX(e.message) + '</div>';
  }
}

function desenharSatisfacaoIMX() {
  const conteudo = document.getElementById('imx-conteudo-satisfacao');
  const termo = document.getElementById('imx-busca-satisfacao').value.trim().toLowerCase();
  const status = document.getElementById('imx-status-satisfacao').value;
  const time = document.getElementById('imx-time-satisfacao').value;
  const mes = document.getElementById('imx-mes').value;
  const pendentes = ticketsSatisfacaoIMX.filter(t => !t.considerar).length;
  atualizarContadorIMX('imx-contador-satisfacao', pendentes);

  if (!ticketsSatisfacaoIMX.length) {
    conteudo.innerHTML = '<div class="vazio-imx"><div class="grande">Nada por aqui</div>Nenhuma pesquisa "Insatisfeito" em tickets fechados em ' + escaparIMX(nomeMesIMX(mes)) + '.</div>';
    document.getElementById('imx-resumo-satisfacao').innerText = '';
    return;
  }
  const lista = ticketsSatisfacaoIMX.filter(t => {
    if (time && t.time !== time) return false;
    if (status === 'pendente' && t.considerar && !marcadosAgoraSatisfacaoIMX.has(t.id)) return false;
    if ((status === 'S' || status === 'N') && t.considerar !== status) return false;
    if (!termo) return true;
    return [t.id, t.organizacao, t.assunto, t.time, ...(t.comentarios || [])].join(' ').toLowerCase().includes(termo);
  });
  const considerados = ticketsSatisfacaoIMX.filter(t => t.considerar === 'S').length;
  const desconsiderados = ticketsSatisfacaoIMX.filter(t => t.considerar === 'N').length;
  document.getElementById('imx-resumo-satisfacao').innerText =
    ticketsSatisfacaoIMX.length + ' ticket(s) · ' + pendentes + ' sem marcação · ' + considerados + ' considerado(s) · ' + desconsiderados + ' não';
  if (!lista.length) {
    conteudo.innerHTML = '<div class="vazio-imx">' + (status === 'pendente' && !termo && !time
      ? '<div class="grande">Tudo marcado</div>Todas as pesquisas do mês já têm Considerar ou Não considerar.'
      : 'Nenhum ticket bate com o filtro.') + '</div>';
    return;
  }
  conteudo.innerHTML = '<div class="rolagem-imx"><table class="tabela-imx"><thead><tr>' +
    '<th>Ticket</th><th>Equipe</th><th>Assunto</th><th>Descrição da insatisfação</th><th>Considerar?</th>' +
    '</tr></thead><tbody>' + lista.map(t => {
      const id = Number(t.id);
      const botoes = Object.entries(opcoesSatisfacaoIMX).map(([valor, rotulo]) => {
        const classe = (t.considerar === valor ? 'escolhido ' : '') + (valor === 'S' ? 'considerar' : 'desconsiderar');
        return '<button class="' + classe + '" onclick="definirSatisfacaoIMX(' + id + ', ' + "'" + valor + "'" + ')">' + escaparIMX(rotulo) + '</button>';
      }).join('');
      const marcadoAgora = marcadosAgoraSatisfacaoIMX.has(t.id);
      const comentarios = (t.comentarios || []).length
        ? t.comentarios.map(c => '<div class="comentario-imx">' + escaparIMX(c) + '</div>').join('')
        : '<span class="fraco">Sem descrição</span>';
      return '<tr id="imx-sat-' + id + '" class="' + (marcadoAgora ? 'salvo' : '') + '">' +
        '<td class="id-imx">' + linkTicketIMX(t) + (t.respostas > 1 ? '<div class="respostas-imx">' + t.respostas + ' respostas</div>' : '') + '</td>' +
        '<td><span class="equipe-imx">' + escaparIMX(t.time) + '</span></td>' +
        '<td class="assunto">' + escaparIMX(t.assunto) + '<div class="fraco">' + escaparIMX(t.organizacao) + '</div></td>' +
        '<td>' + comentarios + '</td>' +
        '<td><div class="seletor-imx">' + botoes + '</div>' +
        '<div class="status-linha-imx ' + (marcadoAgora ? 'ok' : '') + '">' +
          (marcadoAgora ? 'Salvo: ' + escaparIMX(opcoesSatisfacaoIMX[t.considerar]) : (t.considerar ? '' : '<span class="fraco">Sem marcação</span>')) +
        '</div></td></tr>';
    }).join('') + '</tbody></table></div>';
}

async function definirSatisfacaoIMX(id, valor) {
  const linha = document.getElementById('imx-sat-' + id);
  const status = linha.querySelector('.status-linha-imx');
  linha.querySelectorAll('.seletor-imx button').forEach(b => b.disabled = true);
  status.className = 'status-linha-imx';
  status.innerText = 'Gravando...';
  try {
    const dados = await postIMX('/api/indicadores-mensais/satisfacao', { id: id, valor: valor });
    if (dados.ok) {
      const ticket = ticketsSatisfacaoIMX.find(t => Number(t.id) === id);
      if (ticket) { ticket.considerar = valor; marcadosAgoraSatisfacaoIMX.add(ticket.id); }
      mostrarToast('Ticket #' + id + ': ' + opcoesSatisfacaoIMX[valor] + '.');
      desenharSatisfacaoIMX();
      return;
    }
    status.className = 'status-linha-imx erro';
    status.innerText = dados.erro || 'Não foi possível gravar.';
  } catch (e) {
    status.className = 'status-linha-imx erro';
    status.innerText = 'Erro: ' + e.message;
  }
  linha.querySelectorAll('.seletor-imx button').forEach(b => b.disabled = false);
}

// ---------------- início ----------------
(function iniciarIMX() {
  const doLink = new URLSearchParams(window.location.search).get('mes');
  document.getElementById('imx-mes').value = /^[0-9]{4}-[0-9]{2}$/.test(doLink || '') ? doLink : mesAtualIMX();
  let aba = 'efetividade';
  try { aba = localStorage.getItem('imx-aba') || aba; } catch (e) {}
  trocarAbaIMX(['noc', 'satisfacao', 'movidesk'].includes(aba) ? aba : 'efetividade');
  document.getElementById('imx-mes').addEventListener('change', carregarTudoIMX);
  carregarTudoIMX();
  setInterval(conferirViradaDoMesIMX, 60000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) conferirViradaDoMesIMX(); });
})();
</script>
</body>
</html>
"""
