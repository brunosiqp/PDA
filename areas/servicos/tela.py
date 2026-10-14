"""Telas da área Serviços (3.3.1.0): Calendário de GMUD's. Só texto (HTML/CSS/JS); a montagem fica no alertas_gui.py."""


_GMUD_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Calendário de GMUD's</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo-gmud { max-width: 1320px; margin: 0 auto; }
  .cab-gmud { display: flex; justify-content: space-between; align-items: flex-end; gap: 14px; flex-wrap: wrap; margin-bottom: 18px; }
  .cab-gmud h1 { font-size: 22px; margin: 0 0 4px; background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .cab-gmud .sub { color: var(--fg-dim); font-size: 13px; max-width: 760px; line-height: 1.5; }
  .selo-construcao { display: inline-block; font-size: 10.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; vertical-align: 4px;
                     color: #0b0f14; background: #e0b354; border-radius: 99px; padding: 2px 9px; margin-left: 8px; -webkit-text-fill-color: #0b0f14; }
  .aviso-gmud { display: flex; gap: 12px; align-items: center; justify-content: space-between; flex-wrap: wrap; font-size: 12.5px; color: var(--fg-dim);
                border: 1px dashed rgba(224,179,84,.55); background: rgba(224,179,84,.07); border-radius: 12px; padding: 10px 14px; margin-bottom: 16px; }
  .aviso-gmud b { color: var(--fg); }
  .btn-gmud { font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; border-radius: 9px; padding: 6px 12px;
              border: 1px solid var(--border); background: rgba(var(--tinta), .04); color: var(--fg); }
  .btn-gmud:hover { border-color: var(--teal); }
  .btn-gmud.ativo { background: var(--teal); border-color: var(--teal); color: #071016; }
  .grade-gmud { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 18px; align-items: start; }
  .cartao-gmud { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 16px 18px; }
  /* calendário */
  .topo-cal { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
  .topo-cal h2 { font-size: 18px; margin: 0; flex: 1; }
  .nav-cal { width: 34px; height: 34px; border-radius: 10px; border: 1px solid var(--border); background: rgba(var(--tinta), .04); color: var(--fg);
             cursor: pointer; font-size: 18px; line-height: 1; }
  .nav-cal:hover { border-color: var(--teal); }
  .semana-cal, .dias-cal { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 6px; }
  .semana-cal div { font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: var(--fg-dim); text-align: center; padding: 4px 0; }
  .dia-cal { min-height: 104px; border: 1px solid var(--border); border-radius: 11px; padding: 6px 7px; background: rgba(var(--tinta), .015);
             display: flex; flex-direction: column; gap: 4px; cursor: pointer; text-align: left; font: inherit; color: var(--fg); min-width: 0; }
  .dia-cal:hover { border-color: rgba(45,184,207,.55); }
  .dia-cal.fora { opacity: .38; }
  .dia-cal.fim-semana { background: rgba(var(--poco), .18); }
  .dia-cal.hoje { border-color: var(--teal); box-shadow: inset 0 0 0 1px var(--teal); }
  .dia-cal.escolhido { background: rgba(45,184,207,.10); border-color: var(--teal); }
  .dia-cal .num { font-size: 12.5px; font-weight: 800; display: flex; justify-content: space-between; align-items: center; }
  .dia-cal.hoje .num span:first-child { background: var(--teal); color: #071016; border-radius: 99px; padding: 0 7px; }
  .chip-gmud { display: flex; align-items: center; gap: 5px; font-size: 11px; line-height: 1.25; border-radius: 7px; padding: 3px 5px; min-width: 0;
               background: color-mix(in srgb, var(--cor-st) 16%, transparent); border-left: 3px solid var(--cor-st); }
  /* GMUD de vários dias (3.3.2.1): a barra atravessa os dias, sem a borda arredondada do lado que continua */
  .chip-gmud.continua-depois { border-top-right-radius: 0; border-bottom-right-radius: 0; margin-right: -8px; }
  .chip-gmud.continua-antes { border-left-width: 0; border-top-left-radius: 0; border-bottom-left-radius: 0; margin-left: -8px; padding-left: 8px; }
  .chip-gmud .seta-cont { color: var(--cor-st); font-weight: 800; flex: none; }
  .periodo-gmud { font-size: 10.5px; color: var(--fg-dim); }
  .chip-gmud .tit { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .chip-gmud .hr { color: var(--fg-dim); font-weight: 700; flex: none; }
  .mais-cal { font-size: 10.5px; color: var(--fg-dim); font-weight: 700; padding-left: 3px; }
  .av-gmud { width: 18px; height: 18px; border-radius: 50%; object-fit: cover; flex: none; display: inline-flex; align-items: center; justify-content: center;
             font-size: 8.5px; font-weight: 800; color: #fff; background: var(--cor-av, #3b82f6); }
  .av-gmud.g { width: 34px; height: 34px; font-size: 12px; }
  /* filtros e busca (3.4.3.0) */
  .filtros-gmud { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin: 0 0 14px; }
  .filtros-gmud input[type=search], .filtros-gmud select { font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25);
                       border: 1px solid var(--border); border-radius: 10px; padding: 7px 10px; }
  .filtros-gmud input[type=search] { flex: 1; min-width: 220px; }
  .chips-status-gmud { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip-st-gmud { font: inherit; font-size: 11.5px; font-weight: 700; border-radius: 99px; padding: 5px 10px; cursor: pointer; color: var(--fg-dim);
                  background: rgba(var(--tinta), .04); border: 1px solid var(--border); }
  .chip-st-gmud.ativo { color: var(--fg); border-color: var(--cor-st); background: color-mix(in srgb, var(--cor-st) 18%, transparent); }
  .resumo-filtro-gmud { font-size: 12px; color: var(--fg-dim); }
  .resumo-filtro-gmud button { font: inherit; font-size: 12px; background: none; border: none; color: var(--teal); cursor: pointer; padding: 0 0 0 6px; }
  .legenda-cal { display: flex; flex-wrap: wrap; gap: 12px; margin-top: 12px; font-size: 11.5px; color: var(--fg-dim); }
  .legenda-cal span { display: inline-flex; align-items: center; gap: 5px; }
  .legenda-cal i { width: 10px; height: 10px; border-radius: 3px; background: var(--cor-st); display: inline-block; }
  /* caixas */
  .lado-gmud { display: flex; flex-direction: column; gap: 14px; }
  .caixa-gmud h3 { font-size: 13.5px; margin: 0 0 4px; display: flex; align-items: center; gap: 8px; }
  .caixa-gmud .dica { font-size: 11.5px; color: var(--fg-dim); margin-bottom: 10px; }
  .item-gmud { display: flex; gap: 10px; align-items: center; padding: 9px 0; border-top: 1px solid var(--border); min-width: 0; }
  .item-gmud:first-of-type { border-top: none; }
  .item-gmud .info { flex: 1; min-width: 0; }
  .item-gmud .t { font-size: 12.5px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .item-gmud .d { font-size: 11px; color: var(--fg-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .prazo { font-size: 11px; font-weight: 800; border-radius: 99px; padding: 2px 8px; flex: none; white-space: nowrap; }
  .prazo.ok { background: rgba(34,197,94,.14); color: #4ade80; }
  .prazo.atencao { background: rgba(232,163,61,.16); color: #e8a33d; }
  .prazo.critico { background: rgba(241,76,76,.16); color: var(--erro); }
  .vazio-gmud { font-size: 12.5px; color: var(--fg-dim); padding: 14px 4px; text-align: center; line-height: 1.5; }
  a.item-gmud { text-decoration: none; color: inherit; }
  a.item-gmud:hover .t { color: var(--teal); }
  @media (max-width: 1100px) { .grade-gmud { grid-template-columns: minmax(0, 1fr); } }
  @media (max-width: 640px) { .dia-cal { min-height: 64px; } .chip-gmud .tit, .chip-gmud .hr { display: none; } }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-gmud">
    <div class="cab-gmud">
      <div>
        <h1>Calendário de GMUD's <span class="selo-construcao">Beta</span></h1>
        <div class="sub">As GMUDs do mês num calendário, as vencidas e próximas a vencer pelo SLA e as próximas a serem executadas pela data de agendamento.</div>
      </div>
      <button class="btn-gmud" id="btn-exemplo" onclick="alternarExemplo()">Ver com exemplos</button>
    </div>
    <div class="aviso-gmud" id="aviso-gmud"><span id="texto-aviso-gmud"><b>Carregando</b> as GMUDs de Serviços do banco do Movidesk...</span></div>
    <div class="filtros-gmud" role="search">
      <input type="search" id="busca-gmud" placeholder="Buscar por título, cliente, ticket ou responsável..." oninput="aplicarFiltrosGmud()">
      <select id="filtro-resp-gmud" onchange="aplicarFiltrosGmud()" aria-label="Responsável"><option value="">Todos os responsáveis</option></select>
      <select id="filtro-cliente-gmud" onchange="aplicarFiltrosGmud()" aria-label="Cliente"><option value="">Todos os clientes</option></select>
      <div class="chips-status-gmud" id="chips-status-gmud" aria-label="Status"></div>
      <span class="resumo-filtro-gmud" id="resumo-filtro-gmud"></span>
    </div>

    <div class="grade-gmud">
      <div class="cartao-gmud">
        <div class="topo-cal">
          <button class="nav-cal" onclick="andarMes(-1)" aria-label="Mês anterior">&#8249;</button>
          <h2 id="titulo-mes"></h2>
          <button class="btn-gmud" onclick="irParaHoje()">Hoje</button>
          <button class="nav-cal" onclick="andarMes(1)" aria-label="Próximo mês">&#8250;</button>
        </div>
        <div class="semana-cal"><div>Dom</div><div>Seg</div><div>Ter</div><div>Qua</div><div>Qui</div><div>Sex</div><div>Sáb</div></div>
        <div class="dias-cal" id="dias-cal"></div>
        <div class="legenda-cal" id="legenda-cal"></div>
      </div>
      <div class="lado-gmud">
        <div class="cartao-gmud caixa-gmud dia-detalhe" id="caixa-dia" hidden><h3 id="titulo-dia"></h3><div id="lista-dia"></div></div>
        <div class="cartao-gmud caixa-gmud">
          <h3>⏳ Vencidas e próximas a vencer (SLA)</h3>
          <div class="dica">As vencidas primeiro, depois do prazo mais curto pro mais longo: o SLA do ticket e, sem ele, o fim da demanda. Resolvidas e fechadas ficam de fora.</div>
          <div id="lista-sla"></div>
        </div>
        <div class="cartao-gmud caixa-gmud">
          <h3>🗓️ Próximas a serem executadas</h3>
          <div class="dica">Conforme a data de agendamento.</div>
          <div id="lista-execucao"></div>
        </div>
      </div>
    </div>
  </div>
  __FOOTER__
<script>
// Cada GMUD: { id, titulo, cliente, agendada_para: "AAAA-MM-DD HH:MM", termina_em: "AAAA-MM-DD HH:MM" (opcional; pode ser
// outro dia, 3.3.2.1), prazo_sla: "AAAA-MM-DD HH:MM", status, responsaveis: [login], link }
const STATUS_GMUD = {
  agendada: { nome: 'Agendada', cor: '#2db8cf' },
  aprovacao: { nome: 'Em aprovação', cor: '#e8a33d' },
  execucao: { nome: 'Em execução', cor: '#a78bfa' },
  concluida: { nome: 'Concluída', cor: '#22c55e' },
  cancelada: { nome: 'Cancelada', cor: '#97a2a8' },
};
const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
let gmuds = [], gmudsReais = [], pessoas = {}, exemplo = false, integrado = false;
// filtros (3.4.3.0): valem pro calendário, pras duas caixas e pro detalhe do dia; `todasGmuds` guarda a lista inteira
let todasGmuds = [];
const filtroStatusGmud = new Set();
function semAcentoGmud(t) { return String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
function chaveResp(g) { return (g.responsaveis || []).length ? g.responsaveis.join(',') : (g.responsavel_nome || ''); }
function montarOpcoesFiltrosGmud() {
  const resp = document.getElementById('filtro-resp-gmud'), cli = document.getElementById('filtro-cliente-gmud');
  const escolhidoR = resp.value, escolhidoC = cli.value;
  const nomesResp = new Map();
  todasGmuds.forEach(g => { const k = chaveResp(g); if (k && !nomesResp.has(k)) nomesResp.set(k, nomesDe(g)); });
  resp.innerHTML = '<option value="">Todos os responsáveis</option>' + Array.from(nomesResp.entries()).sort((a, b) => a[1].localeCompare(b[1]))
    .map(([k, n]) => '<option value="' + esc(k) + '"' + (k === escolhidoR ? ' selected' : '') + '>' + esc(n) + '</option>').join('');
  const clientes = Array.from(new Set(todasGmuds.map(g => g.cliente).filter(Boolean))).sort((a, b) => a.localeCompare(b));
  cli.innerHTML = '<option value="">Todos os clientes</option>' + clientes.map(c => '<option value="' + esc(c) + '"' + (c === escolhidoC ? ' selected' : '') + '>' + esc(c) + '</option>').join('');
  document.getElementById('chips-status-gmud').innerHTML = Object.entries(STATUS_GMUD).map(([k, s]) =>
    '<button type="button" class="chip-st-gmud' + (filtroStatusGmud.has(k) ? ' ativo' : '') + '" style="--cor-st:' + s.cor + '" onclick="alternarStatusGmud(' + "'" + k + "'" + ')">' + s.nome + '</button>').join('');
}
function alternarStatusGmud(st) { if (filtroStatusGmud.has(st)) filtroStatusGmud.delete(st); else filtroStatusGmud.add(st); montarOpcoesFiltrosGmud(); aplicarFiltrosGmud(); }
function limparFiltrosGmud() {
  document.getElementById('busca-gmud').value = ''; document.getElementById('filtro-resp-gmud').value = ''; document.getElementById('filtro-cliente-gmud').value = '';
  filtroStatusGmud.clear(); montarOpcoesFiltrosGmud(); aplicarFiltrosGmud();
}
function aplicarFiltrosGmud() {
  const termo = semAcentoGmud(document.getElementById('busca-gmud').value.trim());
  const resp = document.getElementById('filtro-resp-gmud').value, cli = document.getElementById('filtro-cliente-gmud').value;
  gmuds = todasGmuds.filter(g => (!filtroStatusGmud.size || filtroStatusGmud.has(g.status)) && (!resp || chaveResp(g) === resp) && (!cli || g.cliente === cli)
    && (!termo || termo.split(' ').every(p => semAcentoGmud([g.titulo, g.cliente, g.id, nomesDe(g), (STATUS_GMUD[g.status] || {}).nome].join(' ')).includes(p))));
  const filtrando = gmuds.length !== todasGmuds.length || termo || resp || cli || filtroStatusGmud.size;
  document.getElementById('resumo-filtro-gmud').innerHTML = filtrando
    ? gmuds.length + ' de ' + todasGmuds.length + ' GMUD(s)<button type="button" onclick="limparFiltrosGmud()">limpar filtros</button>' : '';
  desenhar();
  // buscou algo que não está no mês aberto: vai pro mês da primeira que bateu
  if (termo && gmuds.length && !gmuds.some(g => diasDaGmud(g).some(d => d.slice(0, 7) === iso(mesAtual).slice(0, 7)))) {
    const primeira = gmuds.find(g => g.agendada_para);
    if (primeira) { mesAtual = new Date(primeira.agendada_para.slice(0, 7) + '-01T12:00:00'); desenhar(); }
  }
}
let mesAtual = new Date(); mesAtual.setDate(1);
let diaEscolhido = '';

function esc(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c])); }
function iso(d) { return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
function dataDe(texto) { return texto ? new Date(String(texto).replace(' ', 'T')) : null; }
function corNome(nome) { let h = 0; for (const c of String(nome || '')) h = (h * 31 + c.charCodeAt(0)) % 360; return 'hsl(' + h + ',55%,45%)'; }
function avatar(login, grande) {
  const p = pessoas[login] || { login, nome: login, tem_foto: false };
  const cls = 'av-gmud' + (grande ? ' g' : '');
  if (p.tem_foto) return '<img class="' + cls + '" src="/foto-usuario/' + encodeURIComponent(p.login) + '" alt="" loading="lazy" decoding="async" title="' + esc(p.nome) + '">';
  const partes = String(p.nome || '?').split(' ').filter(Boolean);
  const ini = ((partes[0] || '?')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
  return '<span class="' + cls + '" style="--cor-av:' + corNome(p.nome) + '" title="' + esc(p.nome) + '">' + esc(ini) + '</span>';
}
// dias (AAAA-MM-DD) que a GMUD atravessa: do início ao fim (no máximo 62 dias, pra um fim errado não travar a tela)
function diasDaGmud(g) {
  const ini = (g.agendada_para || '').slice(0, 10);
  if (!ini) return [];
  const fim = (g.termina_em || '').slice(0, 10);
  if (!fim || fim <= ini) return [ini];
  const dias = [];
  const d = new Date(ini + 'T12:00:00'), ultimo = new Date(fim + 'T12:00:00');
  while (d <= ultimo && dias.length < 62) { dias.push(iso(d)); d.setDate(d.getDate() + 1); }
  return dias;
}
function dataCurta(texto) { return texto ? texto.slice(8, 10) + '/' + texto.slice(5, 7) + ' ' + texto.slice(11, 16) : ''; }
function periodoTexto(g) {
  if (!g.termina_em) return dataCurta(g.agendada_para);
  if (g.termina_em.slice(0, 10) === g.agendada_para.slice(0, 10)) return dataCurta(g.agendada_para) + '–' + g.termina_em.slice(11, 16);
  return dataCurta(g.agendada_para) + ' → ' + dataCurta(g.termina_em);
}
function prazosTexto(g) {
  return [g.prazo_sla ? 'SLA ' + dataCurta(g.prazo_sla) : '', g.fim_demanda ? 'fim da demanda ' + dataCurta(g.fim_demanda) : ''].filter(Boolean).join(' · ');
}
function emAndamento(g, agora) {
  const ini = dataDe(g.agendada_para), fim = dataDe(g.termina_em);
  return !!ini && !!fim && ini <= agora && agora <= fim;
}
// responsável sem login no PDA (3.3.4.0): mostra o nome que veio do Movidesk
function nomesDe(g) { return (g.responsaveis || []).length ? g.responsaveis.map(l => (pessoas[l] || {}).nome || l).join(', ') : (g.responsavel_nome || ''); }

function chipDia(item) {
  const g = item.g, pos = item.pos;
  const cls = 'chip-gmud' + (pos === 'inicio' || pos === 'meio' ? ' continua-depois' : '') + (pos === 'meio' || pos === 'fim' ? ' continua-antes' : '');
  let hora = esc(String(g.agendada_para || '').slice(11, 16));
  if (pos === 'meio') hora = 'dia todo';
  if (pos === 'fim') hora = 'até ' + esc(String(g.termina_em || '').slice(11, 16));
  return '<span class="' + cls + '" style="--cor-st:' + (STATUS_GMUD[g.status] || STATUS_GMUD.agendada).cor + '" title="' + esc(g.titulo + ' · ' + periodoTexto(g) + ' · ' + nomesDe(g)) + '">'
    + (pos === 'meio' || pos === 'fim' ? '<span class="seta-cont">◂</span>' : avatar((g.responsaveis || [])[0] || g.responsavel_nome || ''))
    + '<span class="hr">' + hora + '</span><span class="tit">' + esc(g.titulo) + '</span>'
    + (pos === 'inicio' || pos === 'meio' ? '<span class="seta-cont">▸</span>' : '') + '</span>';
}
function desenharCalendario() {
  const nomeMes = MESES[mesAtual.getMonth()];
  document.getElementById('titulo-mes').textContent = nomeMes.charAt(0).toUpperCase() + nomeMes.slice(1) + ' de ' + mesAtual.getFullYear();
  const inicio = new Date(mesAtual); inicio.setDate(1 - inicio.getDay());
  const hoje = iso(new Date());
  const porDia = {};
  gmuds.forEach(g => {
    const dias = diasDaGmud(g);
    dias.forEach((d, i) => (porDia[d] = porDia[d] || []).push({ g, pos: dias.length === 1 ? 'unico' : (i === 0 ? 'inicio' : (i === dias.length - 1 ? 'fim' : 'meio')) }));
  });
  // quem vem de outro dia fica em cima (a barra continua na mesma altura), depois pela hora de início
  const ordemPos = { meio: 0, fim: 1, inicio: 2, unico: 2 };
  Object.values(porDia).forEach(l => l.sort((a, b) => (ordemPos[a.pos] - ordemPos[b.pos]) || String(a.g.agendada_para).localeCompare(String(b.g.agendada_para))));
  let html = '';
  for (let i = 0; i < 42; i++) {
    const d = new Date(inicio); d.setDate(inicio.getDate() + i);
    const chave = iso(d);
    const doDia = porDia[chave] || [];
    const cls = ['dia-cal'];
    if (d.getMonth() !== mesAtual.getMonth()) cls.push('fora');
    if (d.getDay() === 0 || d.getDay() === 6) cls.push('fim-semana');
    if (chave === hoje) cls.push('hoje');
    if (chave === diaEscolhido) cls.push('escolhido');
    html += '<button type="button" class="' + cls.join(' ') + '" onclick="escolherDia(' + "'" + chave + "'" + ')" aria-label="' + d.getDate() + ' de ' + MESES[d.getMonth()] + (doDia.length ? ', ' + doDia.length + ' GMUD' : '') + '">'
      + '<span class="num"><span>' + d.getDate() + '</span>' + (doDia.length ? '<span style="color:var(--fg-dim);font-weight:700">' + doDia.length + '</span>' : '') + '</span>'
      + doDia.slice(0, 3).map(item => chipDia(item)).join('')
      + (doDia.length > 3 ? '<span class="mais-cal">+' + (doDia.length - 3) + ' mais</span>' : '')
      + '</button>';
  }
  document.getElementById('dias-cal').innerHTML = html;
  // até 6 semanas: some com a 6ª linha quando ela é toda do mês seguinte
  const dias = document.querySelectorAll('#dias-cal .dia-cal');
  const ultimaLinhaFora = Array.from(dias).slice(35).every(b => b.classList.contains('fora'));
  if (ultimaLinhaFora) Array.from(dias).slice(35).forEach(b => b.remove());
  document.getElementById('legenda-cal').innerHTML = Object.values(STATUS_GMUD).map(s => '<span><i style="--cor-st:' + s.cor + '"></i>' + s.nome + '</span>').join('');
}

function prazoTexto(alvo) {
  const ms = alvo - new Date();
  const horas = Math.round(ms / 36e5);
  if (ms < 0) return { txt: 'vencida há ' + (Math.abs(horas) >= 48 ? Math.round(Math.abs(horas) / 24) + ' d' : Math.abs(horas) + ' h'), cls: 'critico' };
  if (horas < 24) return { txt: 'vence em ' + Math.max(horas, 1) + ' h', cls: 'critico' };
  if (horas < 72) return { txt: 'vence em ' + Math.round(horas / 24) + ' d', cls: 'atencao' };
  return { txt: 'vence em ' + Math.round(horas / 24) + ' d', cls: 'ok' };
}
function itemHtml(g, extra) {
  const tag = g.link ? 'a' : 'div';
  return '<' + tag + ' class="item-gmud"' + (g.link ? ' href="' + esc(g.link) + '" target="_blank" rel="noopener"' : '') + '>'
    + '<span style="display:inline-flex">' + ((g.responsaveis || []).length ? g.responsaveis.slice(0, 2) : [g.responsavel_nome || '']).map(l => avatar(l, true)).join('') + '</span>'
    + '<div class="info"><div class="t">' + esc(g.titulo) + '</div><div class="d">' + esc([g.cliente, nomesDe(g)].filter(Boolean).join(' · ')) + '</div></div>'
    + extra + '</' + tag + '>';
}
function desenharCaixas() {
  const vazio = 'Nada por aqui.';
  const abertas = gmuds.filter(g => g.status !== 'concluida' && g.status !== 'cancelada');
  // prazo = SLA do ticket (slaSolutionDate); sem SLA, o fim da demanda (dataFimDemanda, 3.3.7.1)
  const prazoDe = g => g.prazo_sla || g.fim_demanda || '';
  // 3.3.8.4: aqui só saem as que estão com status Resolvido ou Fechado no Movidesk (sem a coluna de status, as concluídas/canceladas)
  const foraDoSla = g => g.status_movidesk ? ['resolvido', 'fechado'].indexOf(g.status_movidesk.toLowerCase()) !== -1 : (g.status === 'concluida' || g.status === 'cancelada');
  const porSla = gmuds.filter(g => prazoDe(g) && !foraDoSla(g)).sort((a, b) => String(prazoDe(a)).localeCompare(String(prazoDe(b)))).slice(0, 12);
  document.getElementById('lista-sla').innerHTML = porSla.length ? porSla.map(g => {
    const p = prazoTexto(dataDe(prazoDe(g)));
    return itemHtml(g, '<span class="prazo ' + p.cls + '" title="' + esc(prazosTexto(g)) + '">' + (g.prazo_sla ? '' : 'demanda · ') + p.txt + '</span>');
  }).join('') : '<div class="vazio-gmud">' + vazio + '</div>';
  const agora = new Date();
  // as que já começaram e ainda não terminaram (GMUD de vários dias) entram primeiro, como "em andamento"
  const porData = abertas.filter(g => g.agendada_para && (emAndamento(g, agora) || dataDe(g.agendada_para) >= new Date(agora.getTime() - 36e5)))
    .sort((a, b) => (emAndamento(b, agora) - emAndamento(a, agora)) || String(a.agendada_para).localeCompare(String(b.agendada_para))).slice(0, 8);
  document.getElementById('lista-execucao').innerHTML = porData.length ? porData.map(g => itemHtml(g,
    emAndamento(g, agora) ? '<span class="prazo atencao" title="' + esc(periodoTexto(g)) + '">em andamento · até ' + esc(dataCurta(g.termina_em)) + '</span>'
      : '<span class="prazo ok">' + esc(periodoTexto(g)) + '</span>')).join('') : '<div class="vazio-gmud">' + vazio + '</div>';
}
function desenharDia() {
  const caixa = document.getElementById('caixa-dia');
  caixa.hidden = !diaEscolhido;
  if (!diaEscolhido) return;
  const d = new Date(diaEscolhido + 'T12:00:00');
  document.getElementById('titulo-dia').textContent = ['Domingo', 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'][d.getDay()] + ', ' + d.getDate() + ' de ' + MESES[d.getMonth()];
  const doDia = gmuds.filter(g => diasDaGmud(g).indexOf(diaEscolhido) !== -1).sort((a, b) => String(a.agendada_para).localeCompare(String(b.agendada_para)));
  document.getElementById('lista-dia').innerHTML = doDia.length ? doDia.map(g => {
    const s = STATUS_GMUD[g.status] || STATUS_GMUD.agendada;
    const varios = diasDaGmud(g).length > 1;
    return itemHtml(g, '<span style="display:flex;flex-direction:column;align-items:flex-end;gap:2px">'
      + '<span class="prazo" style="background:color-mix(in srgb,' + s.cor + ' 18%,transparent);color:' + s.cor + '">' + s.nome + '</span>'
      + '<span class="periodo-gmud">' + esc(varios ? periodoTexto(g) : periodoTexto(g).slice(6)) + '</span>'
      + (prazosTexto(g) ? '<span class="periodo-gmud">' + esc(prazosTexto(g)) + '</span>' : '') + '</span>');
  }).join('')
    : '<div class="vazio-gmud">Nenhuma GMUD agendada nesse dia.</div>';
}
function desenhar() { desenharCalendario(); desenharCaixas(); desenharDia(); }
function andarMes(n) { mesAtual.setMonth(mesAtual.getMonth() + n); desenhar(); }
function irParaHoje() { mesAtual = new Date(); mesAtual.setDate(1); diaEscolhido = iso(new Date()); desenhar(); }
function escolherDia(chave) { diaEscolhido = diaEscolhido === chave ? '' : chave; desenhar(); }

// "Ver com exemplos": dados inventados com as fotos de verdade da equipe, só pra validar o layout
function gerarExemplos() {
  const logins = Object.keys(pessoas);
  const pick = i => logins.length ? [logins[i % logins.length]] : [];
  const base = new Date(); base.setHours(0, 0, 0, 0);
  const em = (dias, hora) => { const d = new Date(base); d.setDate(d.getDate() + dias); return iso(d) + ' ' + hora; };
  const titulos = ['Atualização do NFePack', 'Migração do banco NFSe', 'Troca de certificado', 'Janela de manutenção Saas', 'Deploy do PowerDocs 2',
                   'Ajuste de fila RabbitMQ', 'Atualização do CTe2', 'Reindexação de tabelas', 'Novo servidor de e-mail', 'Virada de versão MDFe'];
  const clientes = ['ClienteH', 'ClienteJ', 'Saas', 'ClienteG', 'ClienteE', 'ClienteO', 'ClienteI', 'ClienteA', 'ClienteM', 'ClienteB'];
  const st = ['agendada', 'aprovacao', 'agendada', 'execucao', 'agendada', 'concluida', 'agendada', 'aprovacao', 'agendada', 'cancelada'];
  const desloc = [0, 1, 2, 2, 4, -3, 6, 9, 12, -1, 15, 3, 7];
  const lista = desloc.map((dd, i) => ({
    id: 'ex' + i, titulo: titulos[i % titulos.length], cliente: clientes[i % clientes.length], status: st[i % st.length],
    agendada_para: em(dd, ['08:00', '10:30', '14:00', '19:00', '22:00'][i % 5]),
    termina_em: em(dd, ['10:00', '12:00', '17:00', '21:00', '23:30'][i % 5]),
    prazo_sla: i % 5 === 0 ? '' : em(dd + ((i % 4) - 1), ['09:00', '18:00', '12:00'][i % 3]), fim_demanda: em(dd + 2, '18:00'), responsaveis: pick(i).concat(i % 3 === 0 ? pick(i + 1) : []),
  }));
  // de vários dias: uma janela de madrugada (22h → 4h do dia seguinte), uma de 3 dias e uma que já está em andamento
  lista.push({ id: 'exm1', titulo: 'Virada do banco NFe (janela noturna)', cliente: 'Saas', status: 'agendada', agendada_para: em(5, '22:00'),
               termina_em: em(6, '04:00'), prazo_sla: em(5, '18:00'), responsaveis: pick(2) });
  lista.push({ id: 'exm2', titulo: 'Migração de servidores ClienteH', cliente: 'ClienteH', status: 'aprovacao', agendada_para: em(10, '20:00'),
               termina_em: em(12, '06:00'), prazo_sla: em(9, '12:00'), responsaveis: pick(3).concat(pick(4)) });
  lista.push({ id: 'exm3', titulo: 'Reprocessamento em lote CTe', cliente: 'ClienteJ', status: 'execucao', agendada_para: em(-1, '21:00'),
               termina_em: em(1, '07:00'), prazo_sla: em(1, '09:00'), responsaveis: pick(5) });
  return lista;
}
function alternarExemplo() {
  exemplo = !exemplo;
  todasGmuds = exemplo ? gerarExemplos() : gmudsReais;
  montarOpcoesFiltrosGmud(); aplicarFiltrosGmud();
  document.getElementById('btn-exemplo').classList.toggle('ativo', exemplo);
  document.getElementById('btn-exemplo').textContent = exemplo ? 'Tirar os exemplos' : 'Ver com exemplos';
  desenhar();
}

async function carregar() {
  try {
    const r = await (await fetch('/api/gmud')).json();
    (r.pessoas || []).forEach(p => { pessoas[p.login] = p; });
    if (!r.ok) throw new Error(r.erro || 'erro');
    (r.pessoas || []).forEach(p => { pessoas[p.login] = p; });
    gmudsReais = r.gmuds || [];
    integrado = !!r.integrado;
    if (integrado) document.getElementById('aviso-gmud').hidden = true;
    if (!exemplo) { todasGmuds = gmudsReais; montarOpcoesFiltrosGmud(); aplicarFiltrosGmud(); }
  } catch (e) {
    // banco do Movidesk fora do ar (3.3.4.0): o aviso diz por quê, o calendário fica vazio
    document.getElementById('texto-aviso-gmud').innerHTML = '<b>Não deu pra buscar as GMUDs</b> no banco do Movidesk: ' + esc(e.message || 'erro') + '. Tente de novo em instantes.';
  }
  desenhar();
}
desenhar();
carregar();
</script>
</body>
</html>
"""
