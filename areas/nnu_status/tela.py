"""NNU Enchanced · automação status 20 → 15 (beta, 3.4.9.0): aba dentro do card NNU Enchanced (pedido do Igor: as
automações de NNU ficam organizadas dentro do NNU Enchanced). Três pedaços colocados no template do NNU Enchanced:
o CSS (`__NNU_AUTOMACAO_CSS__`), o corpo da aba (`__NNU_AUTOMACAO_STATUS__`) e o script (`__NNU_AUTOMACAO_JS__`).
Automática (3.4.9.1): sem botão de rodar; vê quem tem a permissão do NNU Enchanced, só administrador pausa, sai da simulação e configura. Só texto; a montagem fica no alertas_gui.py."""

_NNU_STATUS_CSS = r"""  .cartao-ns { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 18px; margin-bottom: 16px; }
  .cartao-ns h2 { font-size: 11.5px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); margin: 0 0 12px; display: flex; justify-content: space-between; gap: 10px; align-items: center; }
  .estado-ns { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
  .estado-ns .tit { font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .estado-ns .det { font-size: 12.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.5; }
  .bolinha { width: 10px; height: 10px; border-radius: 50%; background: var(--fg-dim); display: inline-block; }
  .bolinha.on { background: #22c55e; box-shadow: 0 0 10px #22c55e; }
  .selo-ns { font-size: 10.5px; font-weight: 800; letter-spacing: .06em; border-radius: 99px; padding: 3px 9px; border: 1px solid currentColor; }
  .selo-ns.sim { color: #e8a33d; } .selo-ns.real { color: var(--erro); }
  .acoes-ns { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn-ns { font: inherit; font-size: 12.5px; font-weight: 700; border-radius: 10px; padding: 8px 14px; cursor: pointer; border: 1px solid var(--border-forte, var(--border));
            background: none; color: var(--fg); text-decoration: none; display: inline-flex; align-items: center; gap: 6px; }
  .btn-ns.pri { background: var(--teal); border-color: var(--teal); color: #071016; }
  .btn-ns.mini { font-size: 11.5px; padding: 5px 10px; border-radius: 8px; }
  .btn-ns:disabled { opacity: .5; cursor: default; }
  .aviso-ns { margin-top: 12px; font-size: 12.5px; border-radius: 10px; padding: 9px 12px; border: 1px solid var(--border); background: rgba(var(--tinta), .03); line-height: 1.5; }
  .aviso-ns.atencao { border-color: rgba(232,163,61,.5); background: rgba(232,163,61,.08); }
  .aviso-ns.perigo { border-color: rgba(241,76,76,.5); background: rgba(241,76,76,.08); }
  .aviso-ns.bom { border-color: rgba(176,203,28,.45); background: rgba(176,203,28,.07); }
  .regra-ns ol { margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.7; color: var(--fg-dim); }
  .regra-ns b { color: var(--fg); }
  .chips-ns { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }
  .chip-ns { border-radius: 12px; padding: 8px 12px; border: 1px solid var(--border); background: rgba(var(--tinta), .03); min-width: 92px; }
  .chip-ns .n { font-size: 20px; font-weight: 800; }
  .chip-ns .r { font-size: 11px; color: var(--fg-dim); }
  .chip-ns.espera { border-color: rgba(232,163,61,.5); } .chip-ns.espera .n { color: #e8a33d; }
  .chip-ns.fim .n { color: var(--lime); }
  .barra-ns { height: 8px; border-radius: 99px; background: rgba(var(--tinta), .08); overflow: hidden; margin: 6px 0 14px; }
  .barra-ns span { display: block; height: 100%; background: linear-gradient(90deg, var(--teal), var(--lime)); }
  .tabela-ns-wrap { overflow-x: auto; max-height: 440px; overflow-y: auto; border: 1px solid var(--border); border-radius: 10px; }
  table.tab-ns { border-collapse: collapse; font-size: 12.5px; width: 100%; }
  .tab-ns th { position: sticky; top: 0; background: var(--bg-panel-solid, #181f27); text-align: left; padding: 8px 10px; color: var(--fg-dim); font-size: 11px; border-bottom: 1px solid var(--border); white-space: nowrap; z-index: 1; }
  .tab-ns td { padding: 7px 10px; border-bottom: 1px solid var(--border); vertical-align: top; }
  .tab-ns td.num { font-family: Consolas, monospace; }
  .st { display: inline-block; font-weight: 800; font-size: 11.5px; border-radius: 6px; padding: 1px 7px; background: rgba(var(--tinta), .07); }
  .st.s10, .st.s20, .st.sausente { color: var(--lime); } .st.s15, .st.s25, .st.s31, .st.soutro { color: #e8a33d; }
  .sit { font-size: 11px; font-weight: 800; border-radius: 99px; padding: 2px 9px; border: 1px solid currentColor; white-space: nowrap; }
  .sit.acompanhando { color: #e8a33d; } .sit.fechado { color: var(--lime); } .sit.simulado { color: var(--fg-dim); }
  .filtro-ns { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin-bottom: 10px; }
  .filtro-ns input { font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25); border: 1px solid var(--border); border-radius: 8px; padding: 6px 9px; min-width: 220px; }
  .campos-ns { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
  .campos-ns label { display: block; font-size: 11.5px; color: var(--fg-dim); margin-bottom: 4px; }
  .campos-ns input, .campos-ns select { box-sizing: border-box; width: 100%; font: inherit; font-size: 13px; color: var(--fg);
            background: rgba(var(--poco), .25); border: 1px solid var(--border); border-radius: 10px; padding: 8px 10px; }
  .campos-ns .largo { grid-column: span 3; }
  .dica-ns { font-size: 11.5px; color: var(--fg-dim); margin-top: 6px; line-height: 1.5; }
  .erro-ns { color: var(--erro); font-size: 12.5px; margin-top: 8px; }
  .ok-ns { color: var(--lime); font-size: 12.5px; margin-top: 8px; }
  .vazio-ns { color: var(--fg-dim); font-size: 12.5px; padding: 8px 0; }
  .cen-ns { font-size: 11.5px; color: var(--fg-dim); line-height: 1.5; }
  .det-lote td { background: rgba(var(--tinta), .02); }
  .toast-ns { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--bg-panel-solid, #181f27); border: 1px solid var(--border);
              border-radius: 12px; padding: 10px 16px; font-size: 13px; z-index: 50; box-shadow: 0 12px 30px rgba(0,0,0,.4); max-width: 90vw; }
  body:not(.pode-controlar-ns) .so-admin-ns { display: none !important; }
  @media (max-width: 760px) { .campos-ns { grid-template-columns: 1fr; } .campos-ns .largo { grid-column: span 1; } }
  .intro-ns { color: var(--fg-dim); font-size: 13.5px; line-height: 1.55; max-width: 860px; margin: 0 0 16px; }
  .intro-ns b { color: var(--fg); }
  .bases-ns { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
  .bases-ns label { display: inline-flex; gap: 7px; align-items: center; font-size: 12.5px; border: 1px solid var(--border); border-radius: 10px;
                    padding: 7px 11px; cursor: pointer; background: rgba(var(--tinta), .03); }
  .bases-ns label small { color: var(--fg-dim); font-size: 11px; }
  .bases-ns label.sem-conexao { opacity: .6; }
  .filtro-prod-ns { display: inline-flex; gap: 4px; padding: 4px; border: 1px solid var(--border); border-radius: 12px; margin: 0 0 16px; background: rgba(var(--tinta), .03); }
  .filtro-prod-ns button { font: inherit; font-size: 12.5px; font-weight: 700; color: var(--fg-dim); background: none; border: 0; border-radius: 9px; padding: 6px 14px; cursor: pointer; }
  .filtro-prod-ns button.ativo { background: var(--teal); color: #071016; }
  .grupo-bases-ns { flex-basis: 100%; font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--fg-dim); margin-top: 6px; }
  .lote-base-ns + .lote-base-ns { margin-top: 18px; padding-top: 16px; border-top: 1px solid var(--border); }
  .lote-base-ns h3 { font-size: 14px; margin: 0 0 10px; display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
  .lote-base-ns h3 span { font-size: 12px; font-weight: 400; color: var(--fg-dim); }
"""

_NNU_STATUS_CORPO = r"""    <div class="intro-ns">Automático: a cada <b class="ns-h">2</b> hora(s), em cada base do ClienteI (NFe e NFCe), passa os NNUs da <b class="ns-tabela">INTERF_NFE_NAO_UTILZ</b>
      do <b>IND_STATUS_PROC 20</b> pro <b>15</b>, acompanha cada NUMSEQ até terminar e manda por e-mail o relatório com o caminho e o status final de cada um.
      Trabalha sozinha; se precisar, um administrador também roda uma varredura na hora. Começa em modo simulação até um administrador liberar.</div>

    <div class="filtro-prod-ns" id="ns-filtro-prod" role="group" aria-label="Filtrar por produto">
      <button data-prod="" onclick="filtrarProdutoNs('')">Todos</button>
      <button data-prod="NFe" onclick="filtrarProdutoNs('NFe')">NFe</button>
      <button data-prod="NFCe" onclick="filtrarProdutoNs('NFCe')">NFCe</button>
    </div>

    <div class="cartao-ns">
      <div class="estado-ns">
        <div><div class="tit" id="ns-titulo">Carregando...</div><div class="det" id="ns-detalhe"></div></div>
        <div class="acoes-ns so-admin-ns">
          <button class="btn-ns" id="ns-btn-rodar" onclick="rodarAgora()" title="Roda uma varredura agora em todas as bases marcadas, fora do horário automático">Rodar varredura agora</button>
          <button class="btn-ns" id="ns-btn-sim" onclick="alternarSimulacao()">Simulação</button>
          <button class="btn-ns" id="ns-btn-ligar" onclick="alternarLigado()">Pausar</button>
        </div>
      </div>
      <div id="ns-avisos"></div>
    </div>

    <div class="cartao-ns regra-ns">
      <h2>Regra</h2>
      <ol>
        <li>A cada <b class="ns-h">2</b> hora(s), em cada base marcada, pega os NUMSEQ com <b>IND_STATUS_PROC = 20</b> e <b>guarda a lista antes</b> de mexer (o lote).</li>
        <li><b>UPDATE <span class="ns-tabela">INTERF_NFE_NAO_UTILZ</span> SET IND_STATUS_PROC = 15 WHERE IND_STATUS_PROC = 20</b>, só nesses NUMSEQ.</li>
        <li>Confere o lote a cada <b id="ns-regra-min">10</b> min. O relatório <b>só sai</b> quando todos estiverem no <b>10</b>, no <b>20</b> ou <b>não existirem mais</b> na tabela; com qualquer um em 15, 25 ou 31, espera.</li>
        <li>Guarda o lote e o relatório (Excel) aqui embaixo e manda o e-mail com todos os cenários e o status final de cada registro.</li>
        <li>Um lote por base de cada vez: se o anterior ainda não fechou, a rodada daquela base espera e roda assim que ele fechar.</li>
      </ol>
    </div>

    <div class="cartao-ns" id="ns-cartao-lote" hidden>
      <h2><span>Lotes em acompanhamento</span></h2>
      <div class="filtro-ns"><input type="search" id="ns-busca" placeholder="Buscar NUMSEQ..." oninput="desenharAbertos()"><span class="cen-ns">os que ainda estão processando aparecem primeiro</span></div>
      <div id="ns-abertos"></div>
    </div>

    <div class="cartao-ns">
      <h2>Lotes</h2>
      <div id="ns-lotes"><div class="vazio-ns">Nenhum lote ainda.</div></div>
    </div>

    <div class="cartao-ns so-admin-ns">
      <h2>Configuração</h2>
      <label style="font-size:11.5px;color:var(--fg-dim)">Bases (cada uma pela String Connection do ClienteI com o usuário usuario_leitura; sem ela, a conexão do alerta. Sempre na base principal, .71)</label>
      <div class="bases-ns" id="ns-bases"></div>
      <div class="campos-ns" style="margin-top:12px">
        <div><label for="ns-tabela">Tabela</label><input type="text" id="ns-tabela" maxlength="200"></div>
        <div><label for="ns-col-numseq">Coluna do NUMSEQ</label><input type="text" id="ns-col-numseq" maxlength="128"></div>
        <div><label for="ns-col-status">Coluna do status</label><input type="text" id="ns-col-status" maxlength="128"></div>
        <div><label for="ns-intervalo">Rodar a cada (horas)</label><input type="number" id="ns-intervalo" min="1" max="24"></div>
        <div><label for="ns-acompanhar">Conferir os lotes a cada (min)</label><input type="number" id="ns-acompanhar" min="2" max="120"></div>
        <div><label for="ns-max">Máximo de NUMSEQ por rodada (por base)</label><input type="number" id="ns-max" min="1" max="50000"></div>
        <div class="largo"><label for="ns-emails">E-mails do relatório (separados por vírgula)</label><input type="text" id="ns-emails" maxlength="2000"></div>
        <div><label for="ns-espera">Mandar mesmo assim depois de (h, 0 = nunca)</label><input type="number" id="ns-espera" min="0" max="168"></div>
      </div>
      <div class="dica-ns">Tabela e colunas já vêm com a regra (INTERF_NFE_NAO_UTILZ, NUM_SEQ_NFE_NAO_UTILZ, IND_STATUS_PROC); só mexa se o nome for outro.
        "Testar" só lê: em cada base, quantos estão no 20 e em cada status, sem alterar nada.
        Pelo escopo o relatório só sai quando o lote termina; o "mandar mesmo assim" é uma saída pra lote travado (0 = espera pra sempre).</div>
      <div class="acoes-ns" style="margin-top:12px">
        <button class="btn-ns" onclick="testar()">Testar</button>
        <button class="btn-ns pri" onclick="salvar()">Salvar</button>
      </div>
      <div id="ns-msg-config"></div>
    </div>
"""

_NNU_STATUS_JS = r"""<script>
(function () {
  const PODE = __PODE_CONTROLAR_NNU__;
  if (PODE) document.body.classList.add('pode-controlar-ns');
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const FINAIS = ['10', '20', 'ausente'];
  let st = null, configMontada = false, abertos = {};
  // filtro NFe/NFCe (3.4.9.4): vale pros lotes abertos, o histórico e o resultado da última rodada
  let filtroProd = '';
  try { filtroProd = localStorage.getItem('pda-nnu-produto') || ''; } catch (e) {}
  const passaProd = x => !filtroProd || (x.produto || '') === filtroProd;
  window.filtrarProdutoNs = function (prod) {
    filtroProd = prod;
    try { localStorage.setItem('pda-nnu-produto', prod); } catch (e) {}
    if (st) desenhar();
  };
  function toast(t) { const e = document.createElement('div'); e.className = 'toast-ns'; e.textContent = t; document.body.appendChild(e); setTimeout(() => e.remove(), 4200); }
  async function postar(url, campos) { return (await fetch(url, { method: 'POST', body: new URLSearchParams(campos || {}) })).json(); }
  function nomeSt(s) { return s === 'ausente' ? 'não existe mais' : (s == null ? '-' : String(s)); }
  function seloSt(s) { const k = String(s); const cls = ['10', '15', '20', '25', '31', 'ausente'].includes(k) ? 's' + k : 'soutro'; return '<span class="st ' + cls + '">' + esc(nomeSt(s)) + '</span>'; }
  function seloSit(l) { return '<span class="sit ' + esc(l.situacao) + '">' + ({ acompanhando: 'Acompanhando', fechado: 'Fechado', simulado: 'Simulação', gravando: 'Gravando' }[l.situacao] || esc(l.situacao)) + '</span>'; }

  function desenhar() {
    document.getElementById('ns-titulo').innerHTML = '<span class="bolinha' + (st.ligado ? ' on' : '') + '"></span>'
      + (st.executando === 'rodada' ? 'Rodando agora...' : st.executando === 'conferencia' ? 'Conferindo os lotes...' : (st.ligado ? 'Automático' : 'Pausado'))
      + ' <span class="selo-ns ' + (st.simulacao ? 'sim">SIMULAÇÃO' : 'real">ALTERANDO DE VERDADE') + '</span>';
    const det = [];
    if (st.ligado) det.push('roda a cada ' + st.config.intervalo_horas + ' h' + (st.proxima ? ' · próxima: ' + esc(st.proxima) : ''));
    if (st.ultima_rodada) det.push('última rodada ' + esc(st.ultima_rodada.quando));
    if (st.aguardando && st.aguardando.length) det.push('esperando o lote anterior fechar: ' + st.aguardando.map(esc).join(', '));
    if (st.alterado_em) det.push((st.ligado ? 'retomado' : 'pausado') + ' por ' + esc(st.alterado_por || '?') + ' em ' + esc(st.alterado_em));
    document.getElementById('ns-detalhe').innerHTML = det.join(' · ');
    document.querySelectorAll('.ns-h').forEach(e => { e.textContent = st.config.intervalo_horas; });
    document.querySelectorAll('.ns-tabela').forEach(e => { e.textContent = st.config.tabela; });
    document.getElementById('ns-regra-min').textContent = st.config.acompanhar_min;
    const bl = document.getElementById('ns-btn-ligar');
    bl.textContent = st.ligado ? 'Pausar' : 'Retomar'; bl.className = 'btn-ns ' + (st.ligado ? '' : 'pri');
    document.getElementById('ns-btn-sim').textContent = st.simulacao ? 'Sair da simulação' : 'Voltar pra simulação';
    document.getElementById('ns-btn-rodar').disabled = !!st.executando;
    document.getElementById('ns-btn-sim').className = 'btn-ns ' + (st.simulacao ? 'pri' : '');
    const av = [];
    if (!st.ligado) av.push('<div class="aviso-ns atencao"><b>Pausado.</b> As rodadas não acontecem até retomar; os lotes abertos continuam sendo acompanhados.</div>');
    if (st.simulacao) av.push('<div class="aviso-ns atencao"><b>Modo simulação:</b> as rodadas só registram o que seria alterado (lote e Excel), sem UPDATE e sem e-mail.'
      + (PODE ? ' Confira os lotes simulados e clique em "Sair da simulação" pra valer.' : '') + '</div>');
    else av.push('<div class="aviso-ns perigo">Fora da simulação: as rodadas fazem o UPDATE de verdade no banco.</div>');
    if (!st.config.emails) av.push('<div class="aviso-ns atencao">Nenhum e-mail configurado pro relatório: o lote fecha e o Excel fica aqui, mas ninguém recebe.</div>');
    document.querySelectorAll('#ns-filtro-prod button').forEach(b => b.classList.toggle('ativo', b.dataset.prod === filtroProd));
    ((st.ultima_rodada && st.ultima_rodada.resultados) || []).filter(passaProd).forEach(r => {
      av.push('<div class="aviso-ns ' + (r.ok ? 'bom' : 'perigo') + '"><b>' + esc(r.nome) + ':</b> ' + esc(r.ok ? (r.mensagem || 'ok') : 'a rodada falhou: ' + r.erro) + '</div>');
    });
    if (st.ultima_rodada && st.ultima_rodada.erro) av.push('<div class="aviso-ns perigo">' + esc(st.ultima_rodada.erro) + '</div>');
    ((st.ultima_conferencia && st.ultima_conferencia.resultados) || []).filter(r => !r.ok && passaProd({ produto: (st.bases.find(b => b.id === r.base) || {}).produto })).forEach(r => {
      av.push('<div class="aviso-ns perigo"><b>' + esc(r.nome) + ':</b> a conferência do lote falhou: ' + esc(r.erro) + '</div>');
    });
    document.getElementById('ns-avisos').innerHTML = av.join('');
    if (PODE && !configMontada) montarConfig();
    desenharAbertos();
    desenharLotes();
  }

  function chips(porStatus) {
    const ordem = Object.keys(porStatus).sort((a, b) => (FINAIS.includes(a) - FINAIS.includes(b)) || a.localeCompare(b, 'pt', { numeric: true }));
    return ordem.map(k => '<div class="chip-ns ' + (FINAIS.includes(k) ? 'fim' : 'espera') + '"><div class="n">' + porStatus[k] + '</div><div class="r">'
      + (k === 'ausente' ? 'não existem mais' : 'no status ' + esc(k)) + '</div></div>').join('');
  }
  window.desenharAbertos = function () {
    const lotes = ((st && st.lotes_abertos) || []).filter(passaProd);
    document.getElementById('ns-cartao-lote').hidden = !lotes.length;
    if (!lotes.length) return;
    const termo = document.getElementById('ns-busca').value.trim();
    document.getElementById('ns-abertos').innerHTML = lotes.map(lote => {
      const total = lote.total, feitos = lote.registros.filter(r => FINAIS.includes(String(r.atual))).length;
      const linhas = lote.registros.filter(r => !termo || r.numseq.includes(termo))
        .sort((a, b) => FINAIS.includes(String(a.atual)) - FINAIS.includes(String(b.atual)));
      return '<div class="lote-base-ns"><h3>' + esc(lote.base_nome) + '<span>lote ' + esc(lote.id) + ' · início ' + esc(lote.inicio) + ' · '
        + lote.atualizados + ' alterado(s) pra 15' + (termo ? ' · ' + linhas.length + ' de ' + total + ' com a busca' : '') + '</span></h3>'
        + '<div class="chips-ns">' + chips(lote.por_status) + '<div class="chip-ns"><div class="n">' + (total - feitos) + '</div><div class="r">segurando o relatório</div></div></div>'
        + '<div class="barra-ns"><span style="width:' + (total ? Math.round(feitos * 100 / total) : 0) + '%"></span></div>'
        + tabelaRegistros(linhas.slice(0, 1000), false)
        + (linhas.length > 1000 ? '<div class="cen-ns">Mostrando 1000 de ' + linhas.length + '; use a busca.</div>' : '') + '</div>';
    }).join('');
  };
  function tabelaRegistros(regs, comResultado) {
    if (!regs.length) return '<div class="vazio-ns">Nada aqui.</div>';
    return '<div class="tabela-ns-wrap"><table class="tab-ns"><thead><tr><th>NUMSEQ</th><th>Antes</th><th>Agora</th><th>Caminho</th>' + (comResultado ? '<th>Resultado</th>' : '') + '</tr></thead><tbody>'
      + regs.map(r => '<tr><td class="num">' + esc(r.numseq) + '</td><td>' + seloSt(r.antes) + '</td><td>' + seloSt(r.atual) + '</td><td class="cen-ns">' + esc(r.cenario) + '</td>'
        + (comResultado ? '<td>' + esc(r.resultado) + '</td>' : '') + '</tr>').join('') + '</tbody></table></div>';
  }
  function desenharLotes() {
    const lotes = (st.lotes || []).filter(passaProd);
    if (!lotes.length) { document.getElementById('ns-lotes').innerHTML = '<div class="vazio-ns">' + (filtroProd ? 'Nenhum lote de ' + esc(filtroProd) + ' ainda.' : 'Nenhum lote ainda.') + '</div>'; return; }
    document.getElementById('ns-lotes').innerHTML = '<div class="tabela-ns-wrap" style="max-height:none"><table class="tab-ns"><thead><tr><th>Início</th><th>Base</th><th>Situação</th><th>NUMSEQ</th><th>Alterados</th><th>Cenários</th><th>E-mail</th><th></th></tr></thead><tbody>'
      + lotes.map(l => {
        const email = l.email ? (l.email.ok ? '✓ ' + esc(l.email.quando) : '<span style="color:var(--erro)">' + esc(l.email.erro) + '</span>') : (l.situacao === 'fechado' ? '-' : '');
        const cen = Object.entries(l.cenarios || {}).map(([k, v]) => v + ' · ' + esc(k)).join('<br>');
        return '<tr><td>' + esc(l.inicio) + '</td><td>' + esc(l.base_nome) + '</td><td>' + seloSit(l) + (l.motivo ? '<div class="cen-ns">' + esc(l.motivo) + '</div>' : '') + '</td>'
          + '<td>' + l.total + '</td><td>' + (l.simulacao ? '-' : l.atualizados) + '</td><td class="cen-ns">' + cen + '</td><td class="cen-ns">' + email + '</td>'
          + '<td style="white-space:nowrap"><button class="btn-ns mini" onclick="verLote(\'' + esc(l.id) + '\')">' + (abertos[l.id] ? 'Fechar' : 'Ver') + '</button> '
          + (l.relatorio ? '<a class="btn-ns mini" href="/nnu-status/relatorio/' + encodeURIComponent(l.id) + '.xlsx">Excel</a> ' : '')
          + (PODE && l.situacao === 'fechado' ? '<button class="btn-ns mini" onclick="reenviar(\'' + esc(l.id) + '\')">Reenviar e-mail</button>' : '') + '</td></tr>'
          + (abertos[l.id] ? '<tr class="det-lote"><td colspan="8">' + abertos[l.id] + '</td></tr>' : '');
      }).join('') + '</tbody></table></div>';
  }
  window.verLote = async function (id) {
    if (abertos[id]) { delete abertos[id]; desenharLotes(); return; }
    abertos[id] = '<div class="vazio-ns">Carregando...</div>'; desenharLotes();
    const r = await (await fetch('/api/nnu-status/lote?id=' + encodeURIComponent(id))).json();
    abertos[id] = r.ok ? tabelaRegistros(r.registros, true) : '<div class="erro-ns">' + esc(r.erro) + '</div>';
    desenharLotes();
  };

  const CAMPOS = { tabela: 'ns-tabela', coluna_numseq: 'ns-col-numseq', coluna_status: 'ns-col-status', intervalo_horas: 'ns-intervalo',
                   acompanhar_min: 'ns-acompanhar', max_por_rodada: 'ns-max', emails: 'ns-emails', espera_max_horas: 'ns-espera' };
  function montarConfig() {
    configMontada = true;
    // as 3 bases ClienteI NFe na frente; as outras String Connections recolhidas (abertas se alguma estiver marcada)
    const caixa = b => '<label class="' + (b.ok ? '' : 'sem-conexao') + '" title="' + (b.ok ? '' : 'Conexão incompleta nesta máquina') + '">'
      + '<input type="checkbox" value="' + esc(b.id) + '"' + (b.marcada ? ' checked' : '') + '>' + esc(b.nome) + ' <small>' + esc(b.origem) + (b.ok || b.origem.startsWith('sem conexão') ? '' : ' · sem conexão') + '</small></label>';
    const cliente_i = st.bases.filter(b => b.id.startsWith('alerta:')), outras = st.bases.filter(b => !b.id.startsWith('alerta:'));
    const grupo = prod => { const lista = cliente_i.filter(b => b.produto === prod); return lista.length ? '<div class="grupo-bases-ns">ClienteI · ' + prod + '</div>' + lista.map(caixa).join('') : ''; };
    document.getElementById('ns-bases').innerHTML = grupo('NFe') + grupo('NFCe')
      + (outras.length ? '<details style="flex-basis:100%;margin-top:4px"' + (outras.some(b => b.marcada) ? ' open' : '') + '><summary style="cursor:pointer;font-size:12px;color:var(--fg-dim)">Outras bases (String Connections, ' + outras.length + ')</summary>'
        + '<div class="bases-ns" style="margin-top:8px">' + outras.map(caixa).join('') + '</div></details>' : '');
    Object.entries(CAMPOS).forEach(([k, id]) => { document.getElementById(id).value = st.config[k] == null ? '' : st.config[k]; });
  }
  function camposConfig() {
    const o = { bases: [...document.querySelectorAll('#ns-bases input:checked')].map(i => i.value).join(',') };
    Object.entries(CAMPOS).forEach(([k, id]) => { o[k] = document.getElementById(id).value; });
    return o;
  }

  async function carregar() {
    try { st = await (await fetch('/api/nnu-status/status')).json(); if (!st.ok) throw new Error(st.erro); desenhar(); }
    catch (e) { document.getElementById('ns-titulo').textContent = 'Não foi possível carregar.'; }
  }
  window.testar = async function () {
    const caixa = document.getElementById('ns-msg-config');
    caixa.innerHTML = '<div class="vazio-ns">Consultando (só leitura)...</div>';
    const r = await postar('/api/nnu-status/testar', camposConfig());
    if (!r.ok) { caixa.innerHTML = '<div class="erro-ns">' + esc(r.erro || 'Não deu.') + '</div>'; return; }
    caixa.innerHTML = r.bases.map(b => b.ok
      ? '<div class="ok-ns"><b>' + esc(b.nome) + ':</b> ' + b.total + ' NUMSEQ no status 20 agora · por status: '
        + (Object.entries(b.por_status).map(([k, v]) => k + ' = ' + v).join(' · ') || 'nenhum em 10/15/20/25/31')
        + (b.amostra.length ? ' · primeiros: ' + b.amostra.map(esc).join(', ') : '') + '</div>'
      : '<div class="erro-ns"><b>' + esc(b.nome) + ':</b> ' + esc(b.erro) + '</div>').join('') + '<div class="dica-ns">Nada foi alterado.</div>';
  };
  window.salvar = async function () {
    const r = await postar('/api/nnu-status/config', camposConfig());
    document.getElementById('ns-msg-config').innerHTML = r.ok ? '<div class="ok-ns">Salvo.</div>' : '<div class="erro-ns">' + esc(r.erro || 'Não deu pra salvar.') + '</div>';
    if (r.ok) carregar();
  };
  window.alternarLigado = async function () {
    const ligar = !st.ligado;
    const r = await postar('/api/nnu-status/ligar', { ligado: ligar ? 'true' : 'false' });
    toast(r.ok ? (ligar ? 'Retomado: volta a rodar sozinho.' : 'Pausado (os lotes abertos continuam sendo acompanhados).') : (r.erro || 'Não deu.'));
    setTimeout(carregar, 600);
  };
  window.alternarSimulacao = async function () {
    const sair = st.simulacao;
    if (sair && !confirm('Sair da simulação? A próxima rodada (em instantes) já faz o UPDATE de 20 pra 15 de verdade, e as seguintes também.')) return;
    const r = await postar('/api/nnu-status/simulacao', { simulacao: sair ? 'false' : 'true' });
    toast(r.ok ? (sair ? 'Simulação desligada: a próxima rodada já é de verdade.' : 'De volta à simulação.') : (r.erro || 'Não deu.'));
    setTimeout(carregar, 600);
  };
  // varredura manual (3.4.9.3): mesma rodada da automática, em todas as bases marcadas; base com lote aberto espera ele fechar
  window.rodarAgora = async function () {
    if (!st.simulacao && !confirm('Fora da simulação: a varredura faz o UPDATE de 20 pra 15 de verdade em todas as bases marcadas. Rodar agora?')) return;
    const bt = document.getElementById('ns-btn-rodar');
    bt.disabled = true; bt.textContent = 'Rodando...';
    try {
      const r = await postar('/api/nnu-status/rodar');
      toast(r.resultados ? r.resultados.map(x => x.nome + ': ' + (x.ok ? x.mensagem : 'falhou')).join(' · ') : (r.erro || 'Não deu.'));
    } finally { bt.textContent = 'Rodar varredura agora'; carregar(); }
  };
  window.reenviar = async function (id) {
    const r = await postar('/api/nnu-status/reenviar', { id: id });
    toast(r.ok ? 'E-mail reenviado.' : (r.erro || 'Não deu.'));
    carregar();
  };
  carregar();
  // só atualiza com a aba da automação aberta (e a página visível)
  setInterval(() => { const aba = document.getElementById('aba-nnu-status-20-15'); if (!document.hidden && aba && !aba.hidden) carregar(); }, 20000);
  window.recarregarNnuStatus = carregar;
})();
</script>
"""
