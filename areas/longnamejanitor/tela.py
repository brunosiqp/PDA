"""Tela do LongNameJanitor ClienteQ (beta, 3.3.2.0). Só texto; a montagem fica no alertas_gui.py."""


_LONGNAMEJANITOR_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>LongNameJanitor ClienteQ</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo-lnj { max-width: 1240px; margin: 0 auto; }
  .cab-lnj h1 { font-size: 22px; margin: 0 0 4px; background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .cab-lnj .sub { color: var(--fg-dim); font-size: 13px; max-width: 820px; line-height: 1.5; }
  .selo-beta { display: inline-block; font-size: 10.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; vertical-align: 4px;
               color: #071016; background: #e879f9; border-radius: 99px; padding: 2px 9px; margin-left: 8px; -webkit-text-fill-color: #071016; }
  .cartao-lnj { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 16px 18px; margin-top: 16px; }
  .cartao-lnj h2 { font-size: 13px; text-transform: uppercase; letter-spacing: .06em; color: var(--fg-dim); margin: 0 0 12px; }
  .estado-lnj { display: flex; justify-content: space-between; align-items: center; gap: 14px; flex-wrap: wrap; }
  .estado-lnj .tit { font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  .estado-lnj .det { font-size: 12.5px; color: var(--fg-dim); margin-top: 4px; }
  .modo { font-size: 11px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; border-radius: 99px; padding: 3px 10px; }
  .modo.sim { background: rgba(232,163,61,.18); color: #e8a33d; }
  .modo.real { background: rgba(241,76,76,.18); color: var(--erro); }
  .bolinha { width: 10px; height: 10px; border-radius: 50%; display: inline-block; background: var(--fg-dim); }
  .bolinha.on { background: #22c55e; box-shadow: 0 0 10px #22c55e; }
  .acoes-lnj { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn-lnj { font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; border-radius: 10px; padding: 8px 14px;
             border: 1px solid var(--border); background: rgba(var(--tinta), .04); color: var(--fg); }
  .btn-lnj:hover:not(:disabled) { border-color: var(--teal); }
  .btn-lnj:disabled { opacity: .5; cursor: default; }
  .btn-lnj.pri { background: var(--teal); border-color: var(--teal); color: #071016; }
  .btn-lnj.perigo { border-color: rgba(241,76,76,.5); color: var(--erro); }
  .aviso-lnj { font-size: 12.5px; line-height: 1.5; border-radius: 12px; padding: 10px 14px; margin-top: 12px; border: 1px solid var(--border); color: var(--fg-dim); }
  .aviso-lnj.atencao { border-color: rgba(232,163,61,.5); background: rgba(232,163,61,.07); color: var(--fg); }
  .aviso-lnj.perigo { border-color: rgba(241,76,76,.5); background: rgba(241,76,76,.07); color: var(--fg); }
  .numeros-lnj { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; }
  .num-lnj { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; }
  .num-lnj b { display: block; font-size: 22px; }
  .num-lnj span { font-size: 11.5px; color: var(--fg-dim); }
  .grafico-lnj { display: flex; align-items: flex-end; gap: 6px; height: 90px; margin-top: 14px; }
  .barra-lnj { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 0; }
  .barra-lnj i { width: 100%; max-width: 28px; border-radius: 6px 6px 0 0; background: linear-gradient(180deg, #e879f9, rgba(232,121,249,.35)); min-height: 2px; }
  .barra-lnj span { font-size: 9.5px; color: var(--fg-dim); }
  .pasta-lnj { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin-bottom: 8px; }
  .pasta-lnj .cam { font-family: Consolas, monospace; font-size: 12.5px; word-break: break-all; }
  .pasta-lnj .regras { font-size: 11.5px; color: var(--fg-dim); margin-top: 4px; }
  .st { font-size: 10.5px; font-weight: 800; border-radius: 99px; padding: 2px 8px; margin-left: 6px; }
  .st.ok { background: rgba(34,197,94,.15); color: #4ade80; } .st.erro { background: rgba(241,76,76,.15); color: var(--erro); } .st.neutro { background: rgba(var(--tinta), .08); color: var(--fg-dim); }
  table.tab-lnj { width: 100%; border-collapse: collapse; font-size: 12px; }
  .tab-lnj th { text-align: left; color: var(--fg-dim); font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  .tab-lnj td { padding: 7px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
  .tab-lnj td.arq { font-family: Consolas, monospace; word-break: break-all; }
  .tipo { font-size: 10.5px; font-weight: 800; border-radius: 99px; padding: 2px 8px; white-space: nowrap; }
  .tipo.apagado, .tipo.Apagado { background: rgba(241,76,76,.15); color: var(--erro); }
  .tipo.movido, .tipo.Movido { background: rgba(45,184,207,.15); color: var(--teal); }
  .tipo.simulado, .tipo.Simulado { background: rgba(232,163,61,.15); color: #e8a33d; }
  .tipo.falha, .tipo.Falha { background: rgba(167,139,250,.15); color: #a78bfa; }
  .tipo.aviso, .tipo.Aviso { background: rgba(234,179,8,.15); color: #eab308; }
  .vazio-lnj { color: var(--fg-dim); font-size: 12.5px; padding: 12px 0; }
  .barra-hist { display: flex; gap: 8px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
  .barra-hist input { font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25); border: 1px solid var(--border); border-radius: 8px; padding: 5px 8px; }
  .rolagem-lnj { max-height: 420px; overflow-y: auto; }
  /* filtro das atividades (3.4.7.0) */
  .filtro-lnj { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 10px; }
  .filtro-lnj input, .filtro-lnj select { font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25);
                                          border: 1px solid var(--border); border-radius: 8px; padding: 6px 9px; }
  .filtro-lnj input { flex: 1; min-width: 220px; }
  .filtro-lnj .resumo { font-size: 12px; color: var(--fg-dim); }
  mark.achado-lnj { background: rgba(242,183,5,.35); color: inherit; border-radius: 3px; padding: 0 1px; }
  /* editor das pastas (admin) */
  .ed-pasta { border: 1px dashed var(--border); border-radius: 12px; padding: 12px; margin-bottom: 10px; }
  .ed-campos { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px; }
  .ed-campos label { display: block; font-size: 11px; color: var(--fg-dim); margin-bottom: 4px; }
  .ed-campos input[type=text], .ed-campos input[type=number], .ed-campos select { box-sizing: border-box; width: 100%; font: inherit; font-size: 12.5px;
      color: var(--fg); background: rgba(var(--poco), .25); border: 1px solid var(--border); border-radius: 8px; padding: 6px 8px; }
  .ed-campos .larga { grid-column: 1 / -1; }
  .ed-checks { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 10px; font-size: 12.5px; color: var(--fg-dim); }
  .ed-checks label { display: inline-flex; gap: 6px; align-items: center; cursor: pointer; }
  /* caixinhas do que cada pasta faz (3.4.5.0) */
  .grupo-checks { display: flex; gap: 14px; flex-wrap: wrap; align-items: center; margin-top: 10px; padding: 8px 10px; border-radius: 10px;
                  background: rgba(var(--tinta), .03); border: 1px solid var(--border); font-size: 12.5px; color: var(--fg-dim); }
  .grupo-checks b { color: var(--fg); font-size: 12px; min-width: 170px; }
  .grupo-checks label { display: inline-flex; gap: 6px; align-items: center; cursor: pointer; }
  .grupo-checks .sep-checks { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; }
  .erro-lnj { color: var(--erro); font-size: 12.5px; margin-top: 8px; }
  .toast-lnj { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--bg-panel-solid, #181f27); border: 1px solid var(--border);
               border-radius: 12px; padding: 10px 16px; font-size: 13px; z-index: 50; box-shadow: 0 12px 30px rgba(0,0,0,.4); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-lnj">
    <div class="cab-lnj">
      <h1>LongNameJanitor ClienteQ <span class="selo-beta">Beta</span></h1>
      <div class="sub">Vigia as pastas de integração e tira de lá os arquivos com nome longo demais e move todos os arquivos do CNPJ da pasta de processados do dia pra Processado\\LongNameJanitor. NF repetida só gera aviso.
        Começa pausado e em modo simulação: primeiro mostra o que seria apagado, sem mexer em nada.</div>
    </div>

    <div class="cartao-lnj">
      <div class="estado-lnj">
        <div><div class="tit" id="lnj-titulo">Carregando...</div><div class="det" id="lnj-detalhe"></div></div>
        <div class="acoes-lnj" id="lnj-acoes" hidden>
          <button class="btn-lnj" id="lnj-btn-varrer" onclick="varrer()">Rodar uma varredura agora</button>
          <button class="btn-lnj" id="lnj-btn-tudo" onclick="moverTudo()" title="Todas as pastas e subpastas do Processado, não só a do dia">📦 Mover tudo do Processado</button>
          <button class="btn-lnj" id="lnj-btn-sim" onclick="alternarSimulacao()">Sair da simulação</button>
          <button class="btn-lnj pri" id="lnj-btn-ligar" onclick="alternarLigado()">Ligar</button>
        </div>
      </div>
      <div id="lnj-avisos"></div>
    </div>

    <div class="cartao-lnj">
      <h2>Hoje</h2>
      <div class="numeros-lnj" id="lnj-numeros"></div>
      <div class="grafico-lnj" id="lnj-grafico" title="Apagados/movidos (ou simulados) por dia, últimos 14 dias"></div>
    </div>

    <div class="cartao-lnj">
      <h2>Pastas vigiadas</h2>
      <div id="lnj-pastas"></div>
    </div>

    <div class="cartao-lnj">
      <h2>Atividade recente</h2>
      <div class="filtro-lnj" role="search">
        <input type="search" id="lnj-busca" placeholder="Buscar por chave, nome do arquivo, NF, motivo ou pasta..." oninput="filtrarAtividades()">
        <select id="lnj-filtro-tipo" onchange="filtrarAtividades()" aria-label="Ação">
          <option value="">Todas as ações</option><option value="apagado">Apagado</option><option value="movido">Movido</option>
          <option value="simulado">Simulado</option><option value="aviso">Aviso</option><option value="falha">Falha</option></select>
        <span class="resumo" id="lnj-resumo-filtro"></span>
      </div>
      <div class="rolagem-lnj" id="lnj-atividade"></div>
    </div>

    <div class="cartao-lnj">
      <h2>Histórico do dia</h2>
      <div class="barra-hist"><input type="date" id="lnj-dia" onchange="carregarHistorico()"><span id="lnj-hist-total" style="font-size:12px;color:var(--fg-dim)"></span>
        <span style="font-size:12px;color:var(--fg-dim)">· a busca e o filtro de ação de cima valem aqui também</span></div>
      <div class="rolagem-lnj" id="lnj-historico"></div>
    </div>

    <div class="cartao-lnj" id="lnj-config" hidden>
      <h2>Pastas e regras (administradores)</h2>
      <div class="ed-campos" style="margin-bottom:12px">
        <div><label>Varrer a cada (segundos)</label><input type="number" id="cfg-rescan" min="1" max="3600"></div>
        <div><label>Lembrar NFs por (dias)</label><input type="number" id="cfg-cache" min="1" max="365"></div>
      </div>
      <div id="cfg-pastas"></div>
      <div class="acoes-lnj">
        <button class="btn-lnj" onclick="adicionarPasta()">+ Pasta</button>
        <button class="btn-lnj pri" onclick="salvarConfig()">Salvar pastas</button>
      </div>
      <div class="erro-lnj" id="cfg-erro"></div>
    </div>
  </div>
  __FOOTER__
<script>
const PODE_CONTROLAR = __PODE_CONTROLAR_LNJ__;
let st = null;
function esc(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c])); }
function toast(t) { const e = document.createElement('div'); e.className = 'toast-lnj'; e.textContent = t; document.body.appendChild(e); setTimeout(() => e.remove(), 3500); }
async function postar(url, campos) {
  const r = await fetch(url, { method: 'POST', body: new URLSearchParams(campos || {}) });
  return r.json();
}

function desenhar() {
  const s = st;
  document.getElementById('lnj-titulo').innerHTML = '<span class="bolinha' + (s.ligado ? ' on' : '') + '"></span>' + (s.executando ? 'Varrendo agora...' : (s.ligado ? 'Ligado' : 'Pausado'))
    + '<span class="modo ' + (s.simulacao ? 'sim' : 'real') + '">' + (s.simulacao ? 'Modo simulação' : 'Apagando de verdade') + '</span>';
  const det = [];
  if (s.ligado) det.push('Varre a cada ' + s.rescan_segundos + ' s');
  if (s.ultima_varredura) det.push('última varredura ' + esc(s.ultima_varredura));
  if (s.alterado_em) det.push((s.ligado ? 'ligado' : 'pausado') + ' por ' + esc(s.alterado_por || '?') + ' em ' + esc(s.alterado_em));
  document.getElementById('lnj-detalhe').innerHTML = det.join(' · ');
  document.getElementById('lnj-acoes').hidden = !PODE_CONTROLAR;
  const bl = document.getElementById('lnj-btn-ligar');
  bl.textContent = s.ligado ? 'Pausar' : 'Ligar';
  bl.className = 'btn-lnj ' + (s.ligado ? '' : 'pri');
  bl.disabled = !s.ligado && (s.servico_windows === 'RUNNING' || !s.pastas.length);
  document.getElementById('lnj-btn-varrer').disabled = s.executando || !s.pastas.length;
  const bs = document.getElementById('lnj-btn-sim');
  bs.textContent = s.simulacao ? 'Sair da simulação (apagar de verdade)' : 'Voltar pra simulação';
  bs.className = 'btn-lnj ' + (s.simulacao ? 'perigo' : '');
  const av = [];
  if (s.servico_windows === 'RUNNING') av.push('<div class="aviso-lnj atencao"><b>O serviço do Windows LongNameJanitor está rodando nesta máquina.</b> Pare e remova ele (uninstall.ps1) antes de ligar aqui, pra não rodarem os dois.</div>');
  if (s.simulacao) av.push('<div class="aviso-lnj atencao"><b>Modo simulação:</b> nada é apagado nem movido. Confira em Atividade recente o que seria feito e, se estiver certo, um administrador tira da simulação.</div>');
  else av.push('<div class="aviso-lnj perigo"><b>Apagando de verdade:</b> os arquivos que casarem com as regras saem da pasta (não dá pra desfazer). Cada um fica registrado no histórico do dia.</div>');
  const repetidas = (s.hoje || {}).duplicadas || 0;
  if (repetidas) av.push('<div class="aviso-lnj atencao"><b>' + repetidas + ' NF(s) repetida(s) hoje.</b> Elas ficaram na pasta (NF repetida só gera aviso). Veja quais em Atividade recente, com o selo Aviso.</div>');
  if (!PODE_CONTROLAR) av.push('<div class="aviso-lnj">Você está acompanhando: ligar, pausar, tirar da simulação e mudar as pastas é com os administradores.</div>');
  const mt = s.mover_tudo || {};
  if (mt.rodando) av.push('<div class="aviso-lnj atencao"><b>Movendo tudo do Processado' + (mt.simulacao ? ' (simulação)' : '') + '...</b> '
    + mt.pastas + ' pasta(s), ' + mt.verificados + ' arquivo(s) verificados, ' + (mt.simulacao ? mt.simulados + ' seriam movidos' : mt.movidos + ' movidos')
    + (mt.erros ? ', ' + mt.erros + ' erro(s)' : '') + '. Começou ' + esc(mt.inicio) + ' (' + esc(mt.por) + ').</div>');
  else if (mt.fim) av.push('<div class="aviso-lnj' + (mt.erro || mt.erros ? ' perigo' : '') + '"><b>Último "Mover tudo do Processado"' + (mt.simulacao ? ' (simulação)' : '') + ':</b> '
    + esc(mt.fim) + ' por ' + esc(mt.por) + ' · ' + mt.pastas + ' pasta(s), ' + mt.verificados + ' arquivo(s) verificados, '
    + (mt.simulacao ? mt.simulados + ' seriam movidos' : mt.movidos + ' movidos') + (mt.erros ? ', ' + mt.erros + ' erro(s)' : '')
    + (mt.erro ? ' · parou: ' + esc(mt.erro) : '') + '</div>');
  const bt = document.getElementById('lnj-btn-tudo');
  if (bt) bt.disabled = !!mt.rodando || !s.pastas.some(p => p.processado);
  document.getElementById('lnj-avisos').innerHTML = av.join('');
  const h = s.hoje || {};
  const nums = [
    [s.simulacao ? (h.simulados || 0) : (h.feitos || 0), s.simulacao ? 'seriam apagados hoje' : 'apagados/movidos hoje'],
    [h.processados || 0, s.simulacao ? 'do processado (seriam movidos)' : 'movidos do processado'],
    [h.verificados || 0, 'arquivos verificados hoje'], [h.duplicadas || 0, 'NFs repetidas hoje (aviso)'],
    [h.curtos || 0, 'mantidos (nome curto)'], [h.sem_texto || 0, 'mantidos (sem o texto)'], [h.erros || 0, 'erros hoje'],
    [s.nf_cache || 0, 'NFs lembradas (' + s.nf_cache_dias + ' dias)'],
  ];
  document.getElementById('lnj-numeros').innerHTML = nums.map(n => '<div class="num-lnj"><b>' + n[0] + '</b><span>' + n[1] + '</span></div>').join('');
  const dias = s.dias || [];
  const maior = Math.max(1, ...dias.map(d => (d.feitos || 0) + (d.simulados || 0)));
  document.getElementById('lnj-grafico').innerHTML = dias.length ? dias.map(d => {
    const v = (d.feitos || 0) + (d.simulados || 0);
    return '<div class="barra-lnj" title="' + esc(d.dia) + ': ' + v + '"><i style="height:' + Math.round(v / maior * 70) + 'px"></i><span>' + esc(d.dia.slice(8)) + '/' + esc(d.dia.slice(5, 7)) + '</span></div>';
  }).join('') : '<div class="vazio-lnj">Os números por dia aparecem depois da primeira varredura.</div>';
  document.getElementById('lnj-pastas').innerHTML = s.pastas.length ? s.pastas.map(p => {
    const cls = p.estado === 'Vigiando' ? 'ok' : (p.estado === 'Sem acesso' ? 'erro' : 'neutro');
    return '<div class="pasta-lnj"><div class="cam">' + esc(p.caminho) + '<span class="st ' + cls + '">' + esc(p.estado) + '</span>'
      + (p.simulacao ? '<span class="st neutro">simulação nesta pasta</span>' : '') + '</div>'
      + (p.processar_ativo === false ? '<div class="regras">⏸ Limpeza da pasta desligada (caixinha "Limpar esta pasta")</div>'
        : '<div class="regras">' + (p.regra_nome_longo === false ? 'Nome longo: desligado'
          : (p.acao === 'mover' ? 'Move pra ' + esc(p.mover_para) : 'Apaga') + ' nomes com mais de ' + p.max_nome + ' caracteres'
            + (p.conta_extensao ? ' (contando a extensão)' : ' (sem a extensão)'))
          + ' · só arquivos que tenham ' + p.contem.map(esc).join(' ou ')
          + (p.nf_duplicada ? ' · avisa NF repetida (padrão ' + esc(p.nf_padrao) + ')' : ' · NF repetida: sem aviso') + (p.subpastas ? ' · inclui subpastas' : '') + '</div>')
      + (p.processado && p.processado_auto === false ? '<div class="regras">⏸ Manutenção automática do Processado desligada (o botão "Mover tudo" continua valendo)</div>' : '')
      + (p.processado && p.processado_auto !== false ? '<div class="regras">Move todos os arquivos que tenham ' + p.contem.map(esc).join(' ou ')
        + ' da pasta de processados do dia' + (p.processado_ontem === false ? '' : ' (e de ontem)') + ', <span class="arq-lnj">' + esc(p.processado_hoje || p.processado) + '</span>, pra <span class="arq-lnj">'
        + esc(p.processado + String.fromCharCode(92) + 'LongNameJanitor') + '</span> (substitui se já existir)'
        + (p.processado_verificados != null ? ' · ' + p.processado_verificados + ' arquivo(s) lá' : '') + '</div>' : '')
      + (p.processado_erro ? '<div class="regras" style="color:var(--erro)">' + esc(p.processado_erro) + '</div>' : '')
      + (p.ultima_varredura ? '<div class="regras">Última varredura ' + esc(p.ultima_varredura) + (p.verificados != null ? ' · ' + p.verificados + ' arquivo(s) verificados' : '') + '</div>' : '')
      + (p.erro ? '<div class="regras" style="color:var(--erro)">' + esc(p.erro) + '</div>' : '') + '</div>';
  }).join('') : '<div class="vazio-lnj">Nenhuma pasta cadastrada.</div>';
  desenharAtividades();
}
// filtro das atividades (3.4.7.0): busca em arquivo, motivo/detalhe, pasta e ação (sem acento, todas as palavras) e por ação
let historicoLinhas = [];
function semAcentoLnj(t) { return String(t || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase(); }
function passaFiltro(l) {
  const tipo = document.getElementById('lnj-filtro-tipo').value;
  if (tipo && semAcentoLnj(l.acao) !== tipo) return false;
  const termo = semAcentoLnj(document.getElementById('lnj-busca').value.trim());
  return !termo || termo.split(' ').filter(Boolean).every(p => semAcentoLnj([l.arquivo, l.detalhe, l.pasta, l.acao].join(' ')).includes(p));
}
function destacar(texto) {
  // marca cada palavra buscada no texto, sem expressão regular (o texto já sai escapado)
  const palavras = document.getElementById('lnj-busca').value.trim().toLowerCase().split(' ').filter(p => p.length > 1);
  const bruto = String(texto == null ? '' : texto);
  if (!palavras.length) return esc(bruto);
  const marcas = new Array(bruto.length).fill(false), baixo = bruto.toLowerCase();
  palavras.forEach(p => { let i = baixo.indexOf(p); while (i !== -1) { for (let k = i; k < i + p.length; k++) marcas[k] = true; i = baixo.indexOf(p, i + 1); } });
  let html = '', aberto = false;
  for (let k = 0; k < bruto.length; k++) {
    if (marcas[k] && !aberto) { html += '<mark class="achado-lnj">'; aberto = true; }
    if (!marcas[k] && aberto) { html += '</mark>'; aberto = false; }
    html += esc(bruto[k]);
  }
  return html + (aberto ? '</mark>' : '');
}
function desenharAtividades() {
  if (!st) return;
  const todas = (st.atividade || []).map(a => ({ quando: a.quando, acao: a.tipo, arquivo: a.arquivo, pasta: a.pasta, detalhe: [a.motivo, a.detalhe].filter(Boolean).join(' · ') }));
  const lista = todas.filter(passaFiltro);
  const filtrando = !!(document.getElementById('lnj-busca').value.trim() || document.getElementById('lnj-filtro-tipo').value);
  document.getElementById('lnj-resumo-filtro').textContent = filtrando ? lista.length + ' de ' + todas.length + ' na atividade recente' : '';
  document.getElementById('lnj-atividade').innerHTML = !todas.length
    ? '<div class="vazio-lnj">Nada por enquanto. A atividade da sessão atual do PDA aparece aqui; o histórico de cada dia fica logo abaixo.</div>'
    : (lista.length ? tabela(lista) : '<div class="vazio-lnj">Nada bate com a busca. Tente o Histórico do dia, logo abaixo, que guarda o dia inteiro.</div>');
}
function desenharHistorico() {
  const lista = historicoLinhas.filter(passaFiltro);
  const filtrando = !!(document.getElementById('lnj-busca').value.trim() || document.getElementById('lnj-filtro-tipo').value);
  document.getElementById('lnj-hist-total').textContent = historicoLinhas.length + ' registro(s) nesse dia' + (filtrando ? ' · ' + lista.length + ' com o filtro' : '');
  document.getElementById('lnj-historico').innerHTML = lista.length ? tabela(lista) : '<div class="vazio-lnj">' + (historicoLinhas.length ? 'Nada bate com a busca nesse dia.' : 'Nada registrado nesse dia.') + '</div>';
}
function filtrarAtividades() { desenharAtividades(); desenharHistorico(); }
function tabela(linhas) {
  const nomes = { apagado: 'Apagado', movido: 'Movido', simulado: 'Simulado', falha: 'Falha', aviso: 'Aviso' };
  return '<table class="tab-lnj"><thead><tr><th>Quando</th><th>Ação</th><th>Arquivo</th><th>Motivo</th></tr></thead><tbody>'
    + linhas.map(l => '<tr><td style="white-space:nowrap">' + esc(String(l.quando).slice(11)) + '</td><td><span class="tipo ' + esc(l.acao) + '">' + esc(nomes[l.acao] || l.acao) + '</span></td>'
      + '<td class="arq" title="' + esc(l.pasta) + '">' + destacar(l.arquivo) + '</td><td>' + destacar(l.detalhe) + '</td></tr>').join('') + '</tbody></table>';
}
async function carregar() {
  try {
    const r = await (await fetch('/api/longnamejanitor/status')).json();
    if (!r.ok) throw new Error(r.erro || 'erro');
    const primeira = !st;
    st = r;
    desenhar();
    if (primeira && PODE_CONTROLAR) montarConfig();
  } catch (e) {
    document.getElementById('lnj-titulo').textContent = 'Não foi possível carregar o status.';
  }
}
async function carregarHistorico() {
  const dia = document.getElementById('lnj-dia').value;
  const r = await (await fetch('/api/longnamejanitor/historico?dia=' + encodeURIComponent(dia))).json();
  if (!r.ok) { document.getElementById('lnj-hist-total').textContent = r.erro || ''; historicoLinhas = []; document.getElementById('lnj-historico').innerHTML = ''; return; }
  historicoLinhas = r.linhas.map(l => ({ ...l, acao: l.acao }));
  desenharHistorico();
}
async function alternarLigado() {
  const ligar = !st.ligado;
  if (ligar && !st.simulacao && !confirm('Ligar APAGANDO DE VERDADE? Os arquivos que casarem com as regras saem das pastas.')) return;
  const r = await postar('/api/longnamejanitor/ligar', { ligado: ligar ? 'true' : 'false' });
  toast(r.ok ? (ligar ? 'Ligado: a primeira varredura começa agora.' : 'Pausado.') : (r.erro || 'Não deu.'));
  carregar();
}
async function alternarSimulacao() {
  const sim = !st.simulacao;
  if (!sim && !confirm('Sair da simulação? A partir daqui o PDA APAGA (ou move) de verdade os arquivos que casarem com as regras. Conferiu a Atividade recente?')) return;
  const r = await postar('/api/longnamejanitor/simulacao', { simulacao: sim ? 'true' : 'false' });
  toast(r.ok ? (sim ? 'De volta ao modo simulação.' : 'Simulação desligada: apagando de verdade.') : (r.erro || 'Não deu.'));
  carregar();
}
async function moverTudo() {
  const texto = st.simulacao
    ? 'Simular o "Mover tudo"? Ele percorre TODAS as pastas e subpastas do Processado e registra o que seria movido pra LongNameJanitor (nada sai do lugar).'
    : 'Mover tudo do Processado? Todas as pastas e subpastas do Processado: cada arquivo com o CNPJ vai pra LongNameJanitor, substituindo o que já estiver lá. Pode demorar.';
  if (!confirm(texto)) return;
  const r = await postar('/api/longnamejanitor/mover-tudo');
  toast(r.ok ? 'Começou: o andamento aparece no topo.' : (r.erro || 'Não deu.'));
  carregar();
  const acompanhar = setInterval(async () => { await carregar(); if (!st.mover_tudo || !st.mover_tudo.rodando) { clearInterval(acompanhar); carregarHistorico(); } }, 3000);
}
async function varrer() {
  const r = await postar('/api/longnamejanitor/executar');
  toast(r.ok ? 'Varredura iniciada.' : (r.erro || 'Não deu.'));
  setTimeout(carregar, 1500); setTimeout(carregarHistorico, 2500);
}
// ---- editor das pastas ----
let pastasEd = [];
function montarConfig() {
  document.getElementById('lnj-config').hidden = false;
  document.getElementById('cfg-rescan').value = st.rescan_segundos;
  document.getElementById('cfg-cache').value = st.nf_cache_dias;
  pastasEd = st.pastas.map(p => ({ caminho: p.caminho, acao: p.acao, mover_para: p.mover_para, max_nome: p.max_nome, conta_extensao: p.conta_extensao,
    contem: p.contem.join(', '), subpastas: p.subpastas, nf_duplicada: p.nf_duplicada, nf_padrao: p.nf_padrao, processado: p.processado || '', simulacao: p.simulacao,
    processar_ativo: p.processar_ativo !== false, regra_nome_longo: p.regra_nome_longo !== false,
    processado_auto: p.processado_auto !== false, processado_ontem: p.processado_ontem !== false }));
  desenharConfig();
}
function desenharConfig() {
  document.getElementById('cfg-pastas').innerHTML = pastasEd.map((p, i) => '<div class="ed-pasta" data-i="' + i + '"><div class="ed-campos">'
    + '<div class="larga"><label>Pasta (\\\\\\\\servidor\\\\... ou C:\\\\...)</label><input type="text" data-f="caminho" value="' + esc(p.caminho) + '"></div>'
    + '<div><label>Ação</label><select data-f="acao"><option value="apagar"' + (p.acao === 'apagar' ? ' selected' : '') + '>Apagar</option><option value="mover"' + (p.acao === 'mover' ? ' selected' : '') + '>Mover</option></select></div>'
    + '<div><label>Mover pra (se for mover)</label><input type="text" data-f="mover_para" value="' + esc(p.mover_para) + '"></div>'
    + '<div><label>Nome com mais de (caracteres)</label><input type="number" data-f="max_nome" min="10" max="250" value="' + esc(p.max_nome) + '"></div>'
    + '<div><label>O nome precisa ter (vírgula)</label><input type="text" data-f="contem" value="' + esc(p.contem) + '"></div>'
    + '<div><label>Padrão da NF</label><input type="text" data-f="nf_padrao" value="' + esc(p.nf_padrao) + '"></div>'
    + '<div class="larga"><label>Pasta de processados (opcional): move todos os arquivos com o texto acima da subpasta ANO/MÊS/DIA de hoje e de ontem pra LongNameJanitor, na raiz dela (substitui se já existir)</label><input type="text" data-f="processado" value="' + esc(p.processado) + '"></div></div>'
    + '<div class="grupo-checks"><b>Pasta vigiada (Processar)</b>'
    + '<label><input type="checkbox" data-f="processar_ativo"' + (p.processar_ativo ? ' checked' : '') + '>Limpar esta pasta</label>'
    + '<span class="sep-checks">validações:</span>'
    + '<label><input type="checkbox" data-f="regra_nome_longo"' + (p.regra_nome_longo ? ' checked' : '') + '>Apagar/mover nome longo</label>'
    + '<label><input type="checkbox" data-f="nf_duplicada"' + (p.nf_duplicada ? ' checked' : '') + '>Avisar NF repetida</label></div>'
    + '<div class="grupo-checks"><b>Pasta de processados</b>'
    + '<label><input type="checkbox" data-f="processado_auto"' + (p.processado_auto ? ' checked' : '') + '>Manutenção automática (move o dia pra LongNameJanitor)</label>'
    + '<label><input type="checkbox" data-f="processado_ontem"' + (p.processado_ontem ? ' checked' : '') + '>Olhar também o dia anterior</label></div>'
    + '<div class="ed-checks"><label><input type="checkbox" data-f="conta_extensao"' + (p.conta_extensao ? ' checked' : '') + '>Conta a extensão</label>'
    + '<label><input type="checkbox" data-f="subpastas"' + (p.subpastas ? ' checked' : '') + '>Incluir subpastas</label>'
    + '<label><input type="checkbox" data-f="simulacao"' + (p.simulacao ? ' checked' : '') + '>Só simular nesta pasta</label>'
    + '<button class="btn-lnj perigo" style="margin-left:auto;padding:4px 10px" onclick="pastasEd.splice(' + i + ',1); desenharConfig()">Tirar pasta</button></div></div>').join('')
    || '<div class="vazio-lnj">Nenhuma pasta. Adicione uma.</div>';
}
document.getElementById('cfg-pastas').addEventListener('input', e => {
  const box = e.target.closest('[data-i]'); if (!box) return;
  const p = pastasEd[+box.dataset.i], f = e.target.dataset.f;
  p[f] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
});
document.getElementById('cfg-pastas').addEventListener('change', e => {
  const box = e.target.closest('[data-i]'); if (!box) return;
  const p = pastasEd[+box.dataset.i], f = e.target.dataset.f;
  p[f] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
});
function adicionarPasta() {
  pastasEd.push({ caminho: '', acao: 'apagar', mover_para: '', max_nome: 35, conta_extensao: true, contem: '', subpastas: false, nf_duplicada: true, nf_padrao: '^NF0*(\\\\d+)_', processado: '', simulacao: true,
    processar_ativo: true, regra_nome_longo: true, processado_auto: true, processado_ontem: true });
  desenharConfig();
}
async function salvarConfig() {
  const dados = { rescan_segundos: +document.getElementById('cfg-rescan').value, nf_cache_dias: +document.getElementById('cfg-cache').value,
    pastas: pastasEd.map(p => ({ ...p, max_nome: +p.max_nome, contem: String(p.contem || '').split(',').map(x => x.trim()).filter(Boolean) })) };
  const r = await postar('/api/longnamejanitor/config', { dados: JSON.stringify(dados) });
  document.getElementById('cfg-erro').textContent = r.ok ? '' : (r.erro || 'Não deu pra salvar.');
  if (r.ok) { toast('Pastas salvas.'); st = null; carregar(); }
}
document.getElementById('lnj-dia').value = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
carregar();
carregarHistorico();
setInterval(() => { if (!document.hidden) carregar(); }, 15000);
</script>
</body>
</html>
"""
