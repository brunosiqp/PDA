"""Tela do Monitoramento de Consumo Indevido (beta, 3.4.3.0, /consumo-indevido, só administrador). Só texto."""

_CONSUMO_INDEVIDO_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Consumo Indevido</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo.conteudo-ci { max-width: 1180px; }
  .cab-ci h1 { font-size: 26px; margin: 0 0 4px; font-weight: 800; display: flex; align-items: center; gap: 10px; }
  .cab-ci .beta { font-size: 11px; font-weight: 800; letter-spacing: .08em; color: var(--run, #e8a33d); border: 1px solid currentColor; border-radius: 99px; padding: 2px 9px; }
  .cab-ci .sub { color: var(--fg-dim); font-size: 13.5px; max-width: 760px; line-height: 1.5; margin-bottom: 16px; }
  .cartao-ci { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 18px; margin-bottom: 16px; }
  .cartao-ci h2 { font-size: 11.5px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); margin: 0 0 12px; }
  .estado-ci { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; }
  .estado-ci .tit { font-size: 18px; font-weight: 800; display: flex; align-items: center; gap: 8px; }
  .estado-ci .det { font-size: 12.5px; color: var(--fg-dim); margin-top: 4px; }
  .bolinha { width: 10px; height: 10px; border-radius: 50%; background: var(--fg-dim); display: inline-block; }
  .bolinha.on { background: #22c55e; box-shadow: 0 0 10px #22c55e; }
  .acoes-ci { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn-ci { font: inherit; font-size: 12.5px; font-weight: 700; border-radius: 10px; padding: 8px 14px; cursor: pointer; border: 1px solid var(--border-forte);
            background: none; color: var(--fg); }
  .btn-ci.pri { background: var(--teal); border-color: var(--teal); color: #071016; }
  .btn-ci:disabled { opacity: .5; cursor: default; }
  .aviso-ci { margin-top: 12px; font-size: 12.5px; border-radius: 10px; padding: 9px 12px; border: 1px solid var(--border); background: rgba(var(--tinta), .03); }
  .aviso-ci.atencao { border-color: rgba(232,163,61,.5); background: rgba(232,163,61,.08); }
  .aviso-ci.perigo { border-color: rgba(241,76,76,.5); background: rgba(241,76,76,.08); }
  .campos-ci { display: grid; grid-template-columns: 2fr 2fr 1fr; gap: 12px; }
  .campos-ci label, .campo-sql label { display: block; font-size: 11.5px; color: var(--fg-dim); margin-bottom: 4px; }
  .campos-ci input, .campos-ci select, .campo-sql textarea { box-sizing: border-box; width: 100%; font: inherit; font-size: 13px; color: var(--fg);
            background: rgba(var(--poco), .25); border: 1px solid var(--border); border-radius: 10px; padding: 8px 10px; }
  .campo-sql { margin-top: 12px; }
  .campo-sql textarea { font-family: Consolas, monospace; font-size: 12.5px; min-height: 160px; resize: vertical; }
  .dica-ci { font-size: 11.5px; color: var(--fg-dim); margin-top: 6px; line-height: 1.5; }
  .erro-ci { color: var(--erro); font-size: 12.5px; margin-top: 8px; }
  .ok-ci { color: var(--lime); font-size: 12.5px; margin-top: 8px; }
  .tabela-ci-wrap { overflow-x: auto; max-height: 420px; overflow-y: auto; border: 1px solid var(--border); border-radius: 10px; margin-top: 10px; }
  table.tab-ci { border-collapse: collapse; font-size: 12px; width: 100%; }
  .tab-ci th { position: sticky; top: 0; background: var(--bg-panel-solid, #181f27); text-align: left; padding: 7px 9px; color: var(--fg-dim); font-size: 11px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tab-ci td { padding: 6px 9px; border-bottom: 1px solid var(--border); white-space: nowrap; max-width: 320px; overflow: hidden; text-overflow: ellipsis; }
  .vazio-ci { color: var(--fg-dim); font-size: 12.5px; padding: 8px 0; }
  .toast-ci { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); background: var(--bg-panel-solid, #181f27); border: 1px solid var(--border);
              border-radius: 12px; padding: 10px 16px; font-size: 13px; z-index: 50; box-shadow: 0 12px 30px rgba(0,0,0,.4); }
  @media (max-width: 760px) { .campos-ci { grid-template-columns: 1fr; } }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-ci">
    <div class="cab-ci">
      <h1>Monitoramento de Consumo Indevido <span class="beta">BETA</span></h1>
      <div class="sub">Roda uma consulta no banco de tempos em tempos e manda um aviso no Teams quando aparece consumo indevido novo
        (cada linha que a consulta devolve é uma ocorrência). Começa desligado: escolha o banco, escreva a consulta, teste e só então ligue.</div>
    </div>

    <div class="cartao-ci">
      <div class="estado-ci">
        <div><div class="tit" id="ci-titulo">Carregando...</div><div class="det" id="ci-detalhe"></div></div>
        <div class="acoes-ci">
          <button class="btn-ci" id="ci-btn-agora" onclick="verificarAgora()">Verificar agora</button>
          <button class="btn-ci" onclick="testarTeams()">Testar o Teams</button>
          <button class="btn-ci pri" id="ci-btn-ligar" onclick="alternarLigado()">Ligar</button>
        </div>
      </div>
      <div id="ci-avisos"></div>
    </div>

    <div class="cartao-ci">
      <h2>Banco e consulta</h2>
      <div class="campos-ci">
        <div><label for="ci-conexao">Banco (String Connection)</label><select id="ci-conexao"><option value="">Escolha...</option></select></div>
        <div><label for="ci-titulo-cartao">Título do aviso no Teams</label><input type="text" id="ci-titulo-cartao" maxlength="120"></div>
        <div><label for="ci-intervalo">Verificar a cada (minutos)</label><input type="number" id="ci-intervalo" min="5" max="1440"></div>
      </div>
      <div class="campo-sql"><label for="ci-consulta">Consulta (só SELECT)</label>
        <textarea id="ci-consulta" spellcheck="false" placeholder="SELECT cliente, documento, quantidade, data FROM ... WHERE ..."></textarea>
        <div class="dica-ci">Cada linha devolvida vira uma ocorrência; a mesma linha (todas as colunas iguais) só avisa uma vez a cada 7 dias.
          Só leitura: INSERT, UPDATE, DELETE, EXEC e afins são recusados, e a consulta roda numa transação que sempre volta.
          As primeiras 6 colunas aparecem no cartão do Teams. Banco novo: cadastre em String Connections.</div></div>
      <div class="acoes-ci" style="margin-top:12px">
        <button class="btn-ci" onclick="testarConsulta()">Testar a consulta</button>
        <button class="btn-ci pri" onclick="salvar()">Salvar</button>
      </div>
      <div id="ci-msg-config"></div>
      <div id="ci-teste"></div>
    </div>

    <div class="cartao-ci">
      <h2>Última verificação</h2>
      <div id="ci-ultimas"><div class="vazio-ci">Ainda não rodou.</div></div>
    </div>
  </div>
  __FOOTER__
<script>
(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  let st = null, configMontada = false;
  function toast(t) { const e = document.createElement('div'); e.className = 'toast-ci'; e.textContent = t; document.body.appendChild(e); setTimeout(() => e.remove(), 3800); }
  async function postar(url, campos) { return (await fetch(url, { method: 'POST', body: new URLSearchParams(campos || {}) })).json(); }
  function tabela(colunas, linhas) {
    if (!linhas || !linhas.length) return '<div class="vazio-ci">Nenhuma linha: nada de consumo indevido.</div>';
    return '<div class="tabela-ci-wrap"><table class="tab-ci"><thead><tr>' + colunas.map(c => '<th>' + esc(c) + '</th>').join('') + '</tr></thead><tbody>'
      + linhas.map(l => '<tr>' + l.map(v => '<td title="' + esc(v) + '">' + esc(v) + '</td>').join('') + '</tr>').join('') + '</tbody></table></div>';
  }
  function desenhar() {
    document.getElementById('ci-titulo').innerHTML = '<span class="bolinha' + (st.ligado ? ' on' : '') + '"></span>' + (st.executando ? 'Verificando agora...' : (st.ligado ? 'Ligado' : 'Desligado'));
    const det = [];
    if (st.ligado) det.push('verifica a cada ' + st.config.intervalo_min + ' min');
    if (st.ultimo) det.push('última verificação ' + esc(st.ultimo.quando));
    if (st.alterado_em) det.push((st.ligado ? 'ligado' : 'desligado') + ' por ' + esc(st.alterado_por || '?') + ' em ' + esc(st.alterado_em));
    document.getElementById('ci-detalhe').innerHTML = det.join(' · ');
    const bl = document.getElementById('ci-btn-ligar');
    bl.textContent = st.ligado ? 'Desligar' : 'Ligar'; bl.className = 'btn-ci ' + (st.ligado ? '' : 'pri');
    document.getElementById('ci-btn-agora').disabled = st.executando;
    const av = [];
    if (!st.webhook_cadastrado) av.push('<div class="aviso-ci atencao"><b>Workflow do Teams não cadastrado.</b> Cadastre a chave <code>teams::consumo_indevido_webhook</code> em Criptografia de Dados Sensíveis; sem ela os avisos só ficam aqui e no log "Consumo Indevido".</div>');
    if (st.ultimo && !st.ultimo.ok) av.push('<div class="aviso-ci perigo"><b>A última verificação falhou:</b> ' + esc(st.ultimo.erro) + '</div>');
    else if (st.ultimo) av.push('<div class="aviso-ci' + (st.ultimo.novas ? ' atencao' : '') + '">' + st.ultimo.total + ' linha(s) na última verificação, ' + st.ultimo.novas + ' nova(s)'
      + (st.ultimo.teams ? ' · Teams: ' + esc(st.ultimo.teams) : '') + '.</div>');
    document.getElementById('ci-avisos').innerHTML = av.join('');
    if (!configMontada) {
      configMontada = true;
      document.getElementById('ci-conexao').innerHTML = '<option value="">Escolha...</option>' + st.conexoes.map(c => '<option value="' + esc(c.id) + '"' + (c.id === st.config.conexao_id ? ' selected' : '') + '>' + esc(c.nome) + '</option>').join('');
      document.getElementById('ci-titulo-cartao').value = st.config.titulo || '';
      document.getElementById('ci-intervalo').value = st.config.intervalo_min || 15;
      document.getElementById('ci-consulta').value = st.config.consulta || '';
    }
    document.getElementById('ci-ultimas').innerHTML = st.ultimas ? tabela(st.ultimas.colunas, st.ultimas.linhas) : '<div class="vazio-ci">Ainda não rodou.</div>';
  }
  function camposConfig() {
    return { conexao_id: document.getElementById('ci-conexao').value, titulo: document.getElementById('ci-titulo-cartao').value,
             intervalo_min: document.getElementById('ci-intervalo').value, consulta: document.getElementById('ci-consulta').value };
  }
  async function carregar() {
    try { st = await (await fetch('/api/consumo-indevido/status')).json(); if (!st.ok) throw new Error(st.erro); desenhar(); }
    catch (e) { document.getElementById('ci-titulo').textContent = 'Não foi possível carregar.'; }
  }
  window.testarConsulta = async function () {
    const caixa = document.getElementById('ci-teste');
    caixa.innerHTML = '<div class="vazio-ci">Rodando a consulta...</div>';
    const r = await postar('/api/consumo-indevido/testar', camposConfig());
    caixa.innerHTML = r.ok ? '<div class="ok-ci">' + r.total + ' linha(s)' + (r.total > 50 ? ' (mostrando 50)' : '') + '. Nada foi pro Teams.</div>' + tabela(r.colunas, r.linhas)
      : '<div class="erro-ci">' + esc(r.erro || 'Não deu.') + '</div>';
  };
  window.salvar = async function () {
    const r = await postar('/api/consumo-indevido/config', camposConfig());
    document.getElementById('ci-msg-config').innerHTML = r.ok ? '<div class="ok-ci">Salvo.</div>' : '<div class="erro-ci">' + esc(r.erro || 'Não deu pra salvar.') + '</div>';
    if (r.ok) carregar();
  };
  window.alternarLigado = async function () {
    const ligar = !st.ligado;
    const r = await postar('/api/consumo-indevido/ligar', { ligado: ligar ? 'true' : 'false' });
    toast(r.ok ? (ligar ? 'Ligado: a primeira verificação começa agora.' : 'Desligado.') : (r.erro || 'Não deu.'));
    carregar();
  };
  window.verificarAgora = async function () {
    document.getElementById('ci-btn-agora').disabled = true;
    const r = await postar('/api/consumo-indevido/executar');
    toast(r.ok ? (r.erro ? 'Falhou: ' + r.erro : r.total + ' linha(s), ' + r.novas + ' nova(s)' + (r.teams ? ' · Teams: ' + r.teams : '')) : (r.erro || 'Não deu.'));
    carregar();
  };
  window.testarTeams = async function () {
    const r = await postar('/api/consumo-indevido/teste-teams');
    toast(r.ok ? 'Mensagem de teste enviada pro Teams.' : (r.erro || 'Não deu.'));
  };
  carregar();
  setInterval(() => { if (!document.hidden) carregar(); }, 30000);
})();
</script>
</body>
</html>
"""
