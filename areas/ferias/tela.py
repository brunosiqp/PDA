"""Tela Ferias.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_FERIAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Calendário de Férias</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body { position: relative; }
  body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: radial-gradient(ellipse 900px 500px at 15% 0%, rgba(76,201,240,.07), transparent 60%),
                radial-gradient(ellipse 800px 500px at 90% 100%, rgba(155,93,229,.06), transparent 60%);
  }
  .conteudo { position: relative; z-index: 1; }

  .cabecalho-fer { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                   gap: 14px; max-width: 1120px; margin: 0 auto 22px auto; }
  .cabecalho-fer h1 { font-size: 21px; margin: 0 0 4px 0; font-weight: 800;
                       background: var(--gradiente-marca); -webkit-background-clip: text;
                       background-clip: text; color: transparent; }
  .cabecalho-fer .sub { color: var(--fg-dim); font-size: 12.5px; }

  .painel-fer { background: var(--bg-panel); backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
                border-radius: 16px; padding: 26px 28px; max-width: 1120px; margin: 0 auto 20px auto;
                border: 1px solid transparent;
                background-image: linear-gradient(var(--bg-panel), var(--bg-panel)),
                                   linear-gradient(150deg, rgba(var(--tinta),.08), rgba(var(--tinta),.01) 40%);
                background-origin: border-box; background-clip: padding-box, border-box;
                box-shadow: 0 20px 50px rgba(0,0,0,.35); }

  .nav-mes-fer { display: flex; align-items: center; justify-content: center; gap: 22px; margin-bottom: 22px; }
  .nav-mes-fer button { background: rgba(var(--tinta),.04); border: 1px solid var(--border); color: var(--fg);
                          width: 34px; height: 34px; border-radius: 9px; cursor: pointer; font-size: 16px;
                          display: flex; align-items: center; justify-content: center;
                          transition: border-color .15s, color .15s, background .15s; }
  .nav-mes-fer button:hover { border-color: var(--teal); color: var(--teal); background: rgba(45,184,207,.08); }
  .nav-mes-fer h2 { margin: 0; font-size: 17px; font-weight: 700; color: var(--fg); min-width: 190px; text-align: center; }
  .nav-mes-fer .botao-hoje-fer { width: auto; padding: 0 12px; font-size: 11px; text-transform: uppercase;
                                   letter-spacing: .04em; font-weight: 700; color: var(--fg-dim); }
  .nav-mes-fer .botao-hoje-fer:hover { color: var(--teal); }

  .grade-cabecalho-fer { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; margin-bottom: 8px; }
  .grade-cabecalho-fer div { text-align: center; font-size: 10.5px; color: var(--fg-dim);
                              text-transform: uppercase; letter-spacing: .06em; padding: 4px 0; font-weight: 700; }
  .grade-dias-fer { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; }
  .dia-ferias { min-height: 92px; border-radius: 10px; padding: 8px; background: rgba(var(--tinta),.02);
                border: 1px solid var(--border); transition: border-color .15s, background .15s; }
  .dia-ferias.fim-de-semana { background: rgba(var(--tinta),.012); }
  .dia-ferias.vazio { background: transparent; border-color: transparent; }
  .dia-ferias.hoje { border-color: var(--teal); background: rgba(45,184,207,.08);
                      box-shadow: 0 0 0 1px rgba(45,184,207,.3), inset 0 0 20px rgba(45,184,207,.05); }
  .dia-ferias:not(.vazio):hover { border-color: var(--border-forte); background: rgba(var(--tinta),.035); }
  .numero-dia-ferias { font-size: 12px; color: var(--fg-dim); margin-bottom: 6px; font-weight: 600; }
  .dia-ferias.hoje .numero-dia-ferias {
    color: #08090c; background: var(--gradiente-marca); width: 20px; height: 20px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center; font-weight: 800; }
  .tags-dia-ferias { display: flex; flex-direction: column; gap: 3px; }
  .tag-pessoa-ferias { display: flex; align-items: center; gap: 4px; font-size: 10px; font-weight: 600;
                        padding: 3px 6px 3px 4px; border-radius: 5px; cursor: default; color: #fff; }
  .tag-pessoa-ferias.day-off { border: 1px dashed rgba(var(--tinta),.5); background: transparent !important;
                                 color: var(--fg) !important; }
  .tag-pessoa-ferias.atestado { border: 1px dotted rgba(232,163,61,.75); background: rgba(232,163,61,.08) !important;
                                  color: var(--fg) !important; }
  /* afastamento (INSS e afins, 3.4.4.0) */
  .tag-pessoa-ferias.afastamento { border: 1px solid rgba(167,139,250,.7); background: rgba(167,139,250,.12) !important;
                                     color: var(--fg) !important; }
  .avatar-mini-ferias { width: 13px; height: 13px; border-radius: 50%; flex-shrink: 0; font-size: 7px;
                         font-weight: 800; display: flex; align-items: center; justify-content: center;
                         color: #08090c; background: rgba(255,255,255,.85); }
  .nome-na-tag-ferias { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .selo-tipo-ferias { flex-shrink: 0; font-size: 7.5px; font-weight: 800; letter-spacing: .02em;
                       padding: 1px 4px; border-radius: 3px; background: rgba(var(--poco),.28); }
  .tag-pessoa-ferias.day-off .selo-tipo-ferias { background: rgba(var(--tinta),.14); }

  @media (max-width: 640px) {
    .dia-ferias { min-height: 54px; padding: 5px; }
    .tag-pessoa-ferias { font-size: 8px; }
    .avatar-mini-ferias { display: none; }
    .selo-tipo-ferias { font-size: 6.5px; padding: 1px 3px; }
  }

  .legenda-fer { display: flex; gap: 20px; justify-content: center; margin-top: 18px; flex-wrap: wrap; }
  .legenda-fer-item { display: flex; align-items: center; gap: 7px; font-size: 11px; color: var(--fg-dim); }
  .legenda-marca-ferias { width: 22px; height: 12px; border-radius: 4px; background: var(--teal); }
  .legenda-marca-dayoff { width: 22px; height: 12px; border-radius: 4px; border: 1px dashed var(--fg-dim); }
  .legenda-marca-atestado { width: 22px; height: 12px; border-radius: 4px; border: 1px dotted #e8a33d;
                              background: rgba(232,163,61,.1); }
  .legenda-marca-afastamento { width: 22px; height: 12px; border-radius: 4px; border: 1px solid #a78bfa; background: rgba(167,139,250,.15); }

  .lista-fer-titulo { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
  .lista-fer-titulo h2 { margin: 0; font-size: 12.5px; color: var(--fg-dim); text-transform: uppercase;
                          letter-spacing: .07em; font-weight: 700; }
  .linha-fer { display: flex; justify-content: space-between; align-items: center; gap: 12px;
               background: rgba(var(--tinta),.02); border: 1px solid var(--border); border-radius: 10px;
               padding: 12px 16px; margin-bottom: 8px; font-size: 12.5px; transition: background .15s; }
  .linha-fer:hover { background: rgba(var(--tinta),.035); }
  .linha-fer:last-child { margin-bottom: 0; }
  .linha-fer-esquerda { display: flex; align-items: center; gap: 12px; }
  .avatar-linha-ferias { width: 34px; height: 34px; border-radius: 50%; flex-shrink: 0; font-size: 12.5px;
                          font-weight: 800; display: flex; align-items: center; justify-content: center; color: #08090c; }
  .linha-fer .nome-fer { font-weight: 700; color: var(--fg); display: flex; align-items: center; gap: 8px; }
  .linha-fer .periodo-fer { color: var(--fg-dim); font-size: 11.5px; margin-top: 2px; }
  .badge-tipo-fer { font-size: 9.5px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em;
                     padding: 2px 7px; border-radius: 5px; }
  .badge-tipo-fer.ferias { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-tipo-fer.day-off { background: rgba(var(--tinta),.06); color: var(--fg-dim); border: 1px dashed var(--border-forte); }
  .badge-tipo-fer.atestado { background: rgba(232,163,61,.12); color: #e8a33d; border: 1px dotted rgba(232,163,61,.6); }
  .badge-tipo-fer.afastamento { background: rgba(167,139,250,.14); color: #a78bfa; border: 1px solid rgba(167,139,250,.5); }
  .link-nome-fer { color: var(--fg); text-decoration: none; }
  .link-nome-fer:hover { color: var(--teal); text-decoration: underline; }
  .vazio-fer { color: var(--fg-dim); font-size: 12.5px; padding: 8px 0; }
  .btn-mini { padding: 4px 10px; font-size: 12px; }
  .erro-fer { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 0 auto 10px auto; max-width: 1120px; }

  .modal-fundo { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.6); backdrop-filter: blur(3px);
                 align-items: center; justify-content: center; z-index: 60; }
  .modal-fundo.aberto { display: flex; }
  .modal { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px;
           padding: 28px 26px; width: 340px; box-shadow: 0 20px 50px rgba(0,0,0,.5); }
  .modal h3 { margin: 0 0 16px 0; font-size: 15px; color: var(--teal); }
  .modal label { display: block; font-size: 11px; color: var(--fg-dim); margin: 12px 0 5px 0;
                 text-transform: uppercase; letter-spacing: .04em; }
  .modal input, .modal select { width: 100%; padding: 9px 10px; border-radius: 7px; border: 1px solid var(--border);
                 background: rgba(var(--poco),.28); color: var(--fg); font-size: 13px; font-family: inherit; }
  .modal input:focus, .modal select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .modal .acoes-modal { display: flex; gap: 8px; margin-top: 20px; }
  .modal .erro-modal { color: var(--erro); font-size: 12px; margin-top: 10px; min-height: 14px; }
  .seletor-tipo-fer { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px; margin-top: 6px; }
  .seletor-tipo-fer button { white-space: nowrap; font-size: 12px; }
  .seletor-tipo-fer button { flex: 1; padding: 9px; border-radius: 7px; border: 1px solid var(--border);
                               background: rgba(var(--poco),.2); color: var(--fg-dim); font-size: 12.5px;
                               font-family: inherit; cursor: pointer; transition: all .15s; }
  .seletor-tipo-fer button.ativo { border-color: var(--teal); color: var(--teal); background: rgba(45,184,207,.1); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-fer">
      <div>
        <h1>Calendário de Férias</h1>
        <div class="sub">Visualização das férias e day offs já agendados e aprovados da equipe.</div>
      </div>
      __BOTAO_NOVA_FERIAS__
    </div>

    <div class="erro-fer" id="fer-erro"></div>

    <div class="painel-fer">
      <div class="nav-mes-fer">
        <button onclick="mudarMesFerias(-1)">‹</button>
        <h2 id="fer-mes-titulo">–</h2>
        <button onclick="mudarMesFerias(1)">›</button>
        <button class="botao-hoje-fer" onclick="irParaHojeFerias()">Hoje</button>
      </div>
      <div class="grade-cabecalho-fer">
        <div>Dom</div><div>Seg</div><div>Ter</div><div>Qua</div><div>Qui</div><div>Sex</div><div>Sáb</div>
      </div>
      <div class="grade-dias-fer" id="fer-grade-dias"></div>
      <div class="legenda-fer">
        <div class="legenda-fer-item"><div class="legenda-marca-ferias"></div>Férias</div>
        <div class="legenda-fer-item"><div class="legenda-marca-dayoff"></div>Day Off</div>
        <div class="legenda-fer-item"><div class="legenda-marca-atestado"></div>Atestado</div>
        <div class="legenda-fer-item"><div class="legenda-marca-afastamento"></div>Afastamento</div>
      </div>
    </div>

    <div class="painel-fer">
      <div class="lista-fer-titulo"><h2 id="fer-titulo-lista">Períodos cadastrados</h2></div>
      <div id="fer-lista-registros"><div class="vazio-fer">Carregando...</div></div>
    </div>
  </div>

  __MODAL_NOVA_FERIAS__

  __FOOTER__

<script>
function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const PALETA_CORES_FERIAS = ['#2db8cf','#f14c4c','#e8a33d','#b0cb1c','#4ec9b0','#9cdcfe','#b389f9','#f9c74f','#6c63ff','#4cc9f0','#9b5de5','#ff8fa3'];

function corDaPessoaFerias(nome) {
  let hash = 0;
  for (let i = 0; i < nome.length; i++) hash = (hash * 31 + nome.charCodeAt(i)) >>> 0;
  return PALETA_CORES_FERIAS[hash % PALETA_CORES_FERIAS.length];
}

function iniciaisDaPessoaFerias(nome) {
  const partes = nome.trim().split(/\\s+/).filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

const HOJE_FER = new Date();
let mesAtualFerias = HOJE_FER.getMonth();
let anoAtualFerias = HOJE_FER.getFullYear();
const NOMES_MESES_FERIAS = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];

let feriasCarregadas = [];
const EH_ADMIN_FERIAS = __EH_ADMIN_JS__;
let tipoSelecionadoModal = 'ferias';

function formatarDataISOFerias(ano, mes, dia) {
  return ano + '-' + String(mes + 1).padStart(2, '0') + '-' + String(dia).padStart(2, '0');
}

function pessoasDeFeriasNoDia(dataISO) {
  return feriasCarregadas.filter(f => f.inicio <= dataISO && dataISO <= f.fim);
}

const INFO_TIPO_FERIAS = {
  ferias: { rotulo: 'Férias', selo: 'FÉ', classe: '' },
  day_off: { rotulo: 'Day Off', selo: 'DO', classe: 'day-off' },
  atestado: { rotulo: 'Atestado', selo: 'AT', classe: 'atestado' },
  afastamento: { rotulo: 'Afastamento', selo: 'AF', classe: 'afastamento' },
};

function renderizarCalendarioFerias() {
  document.getElementById('fer-mes-titulo').innerText = NOMES_MESES_FERIAS[mesAtualFerias] + ' de ' + anoAtualFerias;

  const primeiroDiaSemana = new Date(anoAtualFerias, mesAtualFerias, 1).getDay();
  const diasNoMes = new Date(anoAtualFerias, mesAtualFerias + 1, 0).getDate();
  const hojeISO = formatarDataISOFerias(HOJE_FER.getFullYear(), HOJE_FER.getMonth(), HOJE_FER.getDate());

  let html = '';
  for (let i = 0; i < primeiroDiaSemana; i++) html += '<div class="dia-ferias vazio"></div>';

  for (let dia = 1; dia <= diasNoMes; dia++) {
    const dataISO = formatarDataISOFerias(anoAtualFerias, mesAtualFerias, dia);
    const pessoasNoDia = pessoasDeFeriasNoDia(dataISO);
    const ehHoje = dataISO === hojeISO;
    const diaSemana = new Date(anoAtualFerias, mesAtualFerias, dia).getDay();
    const ehFimDeSemana = diaSemana === 0 || diaSemana === 6;
    html += `
      <div class="dia-ferias ${ehHoje ? 'hoje' : ''} ${ehFimDeSemana ? 'fim-de-semana' : ''}">
        <div class="numero-dia-ferias">${dia}</div>
        <div class="tags-dia-ferias">
          ${pessoasNoDia.map(f => {
            const cor = corDaPessoaFerias(f.nome);
            const info = INFO_TIPO_FERIAS[f.tipo] || INFO_TIPO_FERIAS.ferias;
            const temFundoSolido = info.classe === '';
            const primeiroNome = f.nome.split(' ')[0];
            const estilo = temFundoSolido ? `background:${cor};` : '';
            return `<span class="tag-pessoa-ferias ${info.classe}" style="${estilo}" title="${escaparHtml(f.nome)} · ${info.rotulo} · ${f.inicio} até ${f.fim}">
              <span class="avatar-mini-ferias" style="${temFundoSolido ? '' : `background:${cor};color:#fff;`}">${iniciaisDaPessoaFerias(f.nome)}</span>
              <span class="nome-na-tag-ferias">${escaparHtml(primeiroNome)}</span>
              <span class="selo-tipo-ferias">${info.selo}</span>
            </span>`;
          }).join('')}
        </div>
      </div>
    `;
  }
  document.getElementById('fer-grade-dias').innerHTML = html;
}

function mudarMesFerias(direcao) {
  mesAtualFerias += direcao;
  if (mesAtualFerias < 0) { mesAtualFerias = 11; anoAtualFerias--; }
  if (mesAtualFerias > 11) { mesAtualFerias = 0; anoAtualFerias++; }
  renderizarCalendarioFerias();
  renderizarListaFerias();
}

function irParaHojeFerias() {
  mesAtualFerias = HOJE_FER.getMonth();
  anoAtualFerias = HOJE_FER.getFullYear();
  renderizarCalendarioFerias();
  renderizarListaFerias();
}

function periodoNoMesExibido(periodo) {
  // "overlap" entre o periodo (inicio/fim) e o mes/ano sendo exibido no
  // calendario agora - um periodo aparece na lista se qualquer parte
  // dele cair dentro do mes visivel, mesmo que comece ou termine fora
  const primeiroDiaMes = formatarDataISOFerias(anoAtualFerias, mesAtualFerias, 1);
  const ultimoDiaDoMes = new Date(anoAtualFerias, mesAtualFerias + 1, 0).getDate();
  const ultimoDiaMes = formatarDataISOFerias(anoAtualFerias, mesAtualFerias, ultimoDiaDoMes);
  return periodo.inicio <= ultimoDiaMes && periodo.fim >= primeiroDiaMes;
}

function renderizarListaFerias() {
  const el = document.getElementById('fer-lista-registros');
  const tituloEl = document.getElementById('fer-titulo-lista');
  if (tituloEl) tituloEl.innerText = 'Períodos de ' + NOMES_MESES_FERIAS[mesAtualFerias] + ' de ' + anoAtualFerias;

  const periodosDoMes = feriasCarregadas.filter(periodoNoMesExibido);
  if (periodosDoMes.length === 0) {
    el.innerHTML = '<div class="vazio-fer">Nenhum período cadastrado nesse mês.</div>';
    return;
  }
  el.innerHTML = periodosDoMes.map(f => {
    const cor = corDaPessoaFerias(f.nome);
    const info = INFO_TIPO_FERIAS[f.tipo] || INFO_TIPO_FERIAS.ferias;
    return `
    <div class="linha-fer">
      <div class="linha-fer-esquerda">
        <div class="avatar-linha-ferias" style="background:${cor}">${iniciaisDaPessoaFerias(f.nome)}</div>
        <div>
          <div class="nome-fer"><a class="link-nome-fer" href="/perfil/${encodeURIComponent(f.usuario)}">${escaparHtml(f.nome)}</a> <span class="badge-tipo-fer ${info.classe}">${info.rotulo}</span></div>
          <div class="periodo-fer">${f.inicio} até ${f.fim}</div>
        </div>
      </div>
      ${EH_ADMIN_FERIAS ? `<button class="btn-mini btn-perigo" onclick="excluirFerias(${f.id})">Excluir</button>` : ''}
    </div>
  `;
  }).join('');
}

async function carregarFerias() {
  try {
    const resp = await fetch('/api/ferias');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('fer-erro').innerText = dados.erro || 'Não foi possível carregar.';
      return;
    }
    document.getElementById('fer-erro').innerText = '';
    feriasCarregadas = dados.registros;
    renderizarCalendarioFerias();
    renderizarListaFerias();
  } catch (e) {
    document.getElementById('fer-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

async function excluirFerias(id) {
  if (!confirm('Remover esse período?')) return;
  const resp = await fetch('/api/ferias/excluir', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'id=' + id,
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('fer-erro').innerText = dados.erro || 'Não foi possível excluir.';
    return;
  }
  carregarFerias();
}

function selecionarTipoModal(tipo) {
  tipoSelecionadoModal = tipo;
  document.getElementById('fer-botao-tipo-ferias').classList.toggle('ativo', tipo === 'ferias');
  document.getElementById('fer-botao-tipo-dayoff').classList.toggle('ativo', tipo === 'day_off');
  document.getElementById('fer-botao-tipo-atestado').classList.toggle('ativo', tipo === 'atestado');
  document.getElementById('fer-botao-tipo-afastamento').classList.toggle('ativo', tipo === 'afastamento');
}

async function abrirModalNovaFerias() {
  document.getElementById('fer-modal-erro').innerText = '';
  selecionarTipoModal('ferias');
  document.getElementById('fer-input-inicio').value = '';
  document.getElementById('fer-input-fim').value = '';
  const select = document.getElementById('fer-select-usuario');
  if (select.options.length <= 1) {
    try {
      const resp = await fetch('/api/usuarios');
      const dados = await resp.json();
      select.innerHTML = '<option value="">Selecione...</option>' +
        dados.usuarios.map(u => `<option value="${escaparHtml(u.usuario)}">${escaparHtml(u.nome || u.usuario)}</option>`).join('');
    } catch (e) {
      document.getElementById('fer-modal-erro').innerText = 'Não foi possível carregar os usuários.';
    }
  }
  document.getElementById('modal-nova-ferias').classList.add('aberto');
}

function fecharModalNovaFerias() {
  document.getElementById('modal-nova-ferias').classList.remove('aberto');
}

async function salvarNovaFerias() {
  const usuario = document.getElementById('fer-select-usuario').value;
  const inicio = document.getElementById('fer-input-inicio').value;
  const fim = document.getElementById('fer-input-fim').value;
  const erroEl = document.getElementById('fer-modal-erro');

  if (!usuario || !inicio || !fim) {
    erroEl.innerText = 'Preencha a pessoa e as duas datas.';
    return;
  }

  const resp = await fetch('/api/ferias/criar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'usuario=' + encodeURIComponent(usuario) + '&inicio=' + encodeURIComponent(inicio) +
          '&fim=' + encodeURIComponent(fim) + '&tipo=' + encodeURIComponent(tipoSelecionadoModal),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
    return;
  }
  fecharModalNovaFerias();
  carregarFerias();
}

carregarFerias();
// reconsulta a cada 10 min (3.3.4.1); com a aba escondida espera, e ao voltar busca se já passou o tempo
const INTERVALO_FERIAS_MS = 10 * 60 * 1000;
let ultimaConsultaFerias = Date.now();
setInterval(() => { if (!document.hidden) { ultimaConsultaFerias = Date.now(); carregarFerias(); } }, INTERVALO_FERIAS_MS);
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && Date.now() - ultimaConsultaFerias >= INTERVALO_FERIAS_MS) { ultimaConsultaFerias = Date.now(); carregarFerias(); }
});
</script>
</body>
</html>
"""
