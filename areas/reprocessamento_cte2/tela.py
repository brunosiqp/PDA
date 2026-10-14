"""Tela Reprocessamento CTe2 (2.35.4.0).

Só texto (HTML/CSS/JS); a lógica fica em areas/reprocessamento_cte2/logica.py.
Automação desenvolvida por Caio Peixoto (crédito no cabeçalho e no card).
"""


_REPROCESSAMENTO_CTE2_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Reprocessamento CTe2</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  :root { --ambar-rc: #e8a33d; }
  :root[data-tema="claro"] { --ambar-rc: #a8670a; }
  .cabecalho-rc { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px;
                  max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .cabecalho-rc h1 { font-size: 20px; margin: 0 0 4px 0; background: var(--gradiente-marca); -webkit-background-clip: text;
                     background-clip: text; color: transparent; }
  .cabecalho-rc .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; max-width: 620px; }
  .credito-rc { display: inline-flex; align-items: center; gap: 6px; margin-top: 8px; font-size: 11.5px; color: var(--fg-dim);
                border: 1px solid var(--border); border-radius: 999px; padding: 3px 10px 3px 4px; background: rgba(var(--tinta),.03); }
  .credito-rc .ini { width: 20px; height: 20px; border-radius: 50%; background: var(--gradiente-marca); color: #08090c;
                     font-size: 9.5px; font-weight: 800; display: grid; place-items: center; }
  .credito-rc b { color: var(--fg); font-weight: 700; }
  /* foto do autor e link pro perfil dele (3.1.5.0) */
  a.credito-rc { text-decoration: none; transition: border-color .15s; }
  a.credito-rc:hover { border-color: var(--teal); }
  .credito-rc img.ini { object-fit: cover; background: rgba(var(--tinta),.08); }
  .fonte-rc { max-width: var(--largura-pagina); margin: 0 auto 14px auto; font-size: 12px; color: var(--fg-dim); }
  .fonte-rc b { color: var(--fg); font-weight: 700; }
  .form-chave-rc { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .form-chave-rc input { flex: 1; min-width: 220px; background: rgba(var(--poco),.28); border: 1px solid var(--border); color: var(--fg);
                         border-radius: 8px; padding: 8px 10px; font: inherit; font-size: 12.5px; }

  .erro-rc { color: var(--erro); font-size: 12.5px; max-width: var(--largura-pagina); margin: 0 auto 10px auto; }
  .erro-rc:empty { display: none; }
  .aviso-rc { max-width: var(--largura-pagina); margin: 0 auto 14px auto; border-radius: 12px; padding: 12px 16px; font-size: 12.5px;
              line-height: 1.6; border: 1px solid; }
  .aviso-rc.perigo { background: rgba(241,76,76,.07); border-color: rgba(241,76,76,.35); color: var(--fg); }
  .aviso-rc.atencao { background: rgba(232,163,61,.07); border-color: rgba(232,163,61,.35); color: var(--fg); }
  .aviso-rc b { color: var(--fg); }
  .aviso-rc code { font-size: 11.5px; background: rgba(var(--tinta),.07); padding: 1px 6px; border-radius: 5px; }

  /* interruptor principal */
  .painel-rc { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 18px 22px; max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .painel-rc h2 { margin: 0 0 6px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .06em; }
  .estado-rc { display: flex; align-items: center; justify-content: space-between; gap: 18px; flex-wrap: wrap; position: relative; overflow: hidden; }
  .estado-rc::before { content: ''; position: absolute; left: -22px; top: -18px; bottom: -18px; width: 4px; background: var(--cor-estado, var(--border)); }
  .estado-rc.ligado { --cor-estado: var(--ok); }
  .estado-rc.pausado { --cor-estado: var(--ambar-rc); }
  .estado-rc .titulo { display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 800; color: var(--fg); }
  .estado-rc .detalhe { font-size: 12px; color: var(--fg-dim); margin-top: 4px; line-height: 1.5; }
  .pulso-rc { width: 10px; height: 10px; border-radius: 50%; background: var(--cor-estado, var(--fg-dim)); flex: none; }
  .estado-rc.ligado .pulso-rc { box-shadow: 0 0 0 0 rgba(78,201,176,.6); animation: pulso-rc 1.8s infinite; }
  @keyframes pulso-rc { 0% { box-shadow: 0 0 0 0 rgba(78,201,176,.55); } 70% { box-shadow: 0 0 0 10px rgba(78,201,176,0); } 100% { box-shadow: 0 0 0 0 rgba(78,201,176,0); } }
  .acoes-rc { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn-sec-rc { background: rgba(var(--tinta),.04); border: 1px solid var(--border); color: var(--fg); border-radius: 9px; padding: 9px 14px;
                font-size: 12.5px; cursor: pointer; font-family: inherit; display: inline-flex; align-items: center; gap: 7px; }
  .btn-sec-rc:hover:not(:disabled) { border-color: var(--teal); }
  .btn-sec-rc:disabled, .btn-accent:disabled { opacity: .5; cursor: default; }
  .btn-pausar-rc { background: rgba(232,163,61,.10); border: 1px solid rgba(232,163,61,.5); color: var(--ambar-rc); border-radius: 9px;
                   padding: 9px 16px; font-size: 12.5px; font-weight: 700; cursor: pointer; font-family: inherit; }
  .btn-pausar-rc:hover { background: rgba(232,163,61,.18); }
  .giro-rc { width: 12px; height: 12px; border-radius: 50%; border: 2px solid currentColor; border-right-color: transparent;
             display: inline-block; animation: giro-rc .8s linear infinite; flex: none; }
  @keyframes giro-rc { to { transform: rotate(360deg); } }

  /* números */
  .numeros-rc { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .numero-rc { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; padding: 13px 16px; position: relative; overflow: hidden;
               text-align: left; font-family: inherit; color: var(--fg); }
  .numero-rc::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--cor-n, var(--teal)); }
  button.numero-rc { cursor: pointer; }
  button.numero-rc:hover { border-color: var(--cor-n, var(--teal)); }
  .numero-rc .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .06em; }
  .numero-rc .valor { font-size: 24px; font-weight: 800; margin-top: 3px; line-height: 1.1; }
  .numero-rc .extra { font-size: 11px; color: var(--fg-dim); margin-top: 3px; }

  /* último ciclo: funil */
  .funil-rc { display: grid; grid-template-columns: repeat(auto-fit, minmax(118px, 1fr)); gap: 8px; margin-top: 10px; }
  .etapa-rc { border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; background: rgba(var(--tinta),.02); }
  .etapa-rc .n { font-size: 20px; font-weight: 800; color: var(--fg); }
  .etapa-rc .t { font-size: 11px; color: var(--fg-dim); margin-top: 2px; line-height: 1.35; }
  .etapa-rc.ok .n { color: var(--ok); }
  .etapa-rc.erro .n { color: var(--erro); }
  .meta-ciclo-rc { font-size: 12px; color: var(--fg-dim); display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .meta-ciclo-rc .erro { color: var(--erro); }

  details.como-rc summary { cursor: pointer; font-size: 12.5px; font-weight: 700; color: var(--fg); list-style: none; display: flex; justify-content: space-between; }
  details.como-rc summary::-webkit-details-marker { display: none; }
  details.como-rc summary .seta { color: var(--fg-dim); transition: transform .2s; }
  details.como-rc[open] summary .seta { transform: rotate(90deg); }
  .passos-rc { margin: 12px 0 0 0; padding: 0; list-style: none; counter-reset: passo; display: flex; flex-direction: column; gap: 8px; }
  .passos-rc li { counter-increment: passo; display: flex; gap: 10px; font-size: 12.5px; color: var(--fg-dim); line-height: 1.5; }
  .passos-rc li::before { content: counter(passo); width: 20px; height: 20px; border-radius: 50%; flex: none; display: grid; place-items: center;
                          font-size: 10.5px; font-weight: 800; background: rgba(45,184,207,.15); color: var(--teal); }
  .passos-rc b { color: var(--fg); }

  /* registros */
  .topo-registros-rc { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
  .abas-rc { display: inline-flex; border: 1px solid var(--border); border-radius: 9px; overflow: hidden; }
  .abas-rc button { background: none; border: none; color: var(--fg-dim); padding: 8px 14px; font-size: 12.5px; cursor: pointer; font-family: inherit; }
  .abas-rc button + button { border-left: 1px solid var(--border); }
  .abas-rc button.ativa { background: rgba(45,184,207,.14); color: var(--fg); font-weight: 700; }
  .abas-rc .n { font-size: 10.5px; opacity: .7; margin-left: 4px; }
  .filtros-reg-rc { display: flex; gap: 8px; flex-wrap: wrap; }
  .filtros-reg-rc input { background: rgba(var(--poco),.25); border: 1px solid var(--border); color: var(--fg); border-radius: 8px; padding: 7px 10px;
                          font-size: 12.5px; font-family: inherit; }
  .filtros-reg-rc input[type="date"] { color-scheme: dark; }
  :root[data-tema="claro"] .filtros-reg-rc input[type="date"] { color-scheme: light; }
  .rolagem-rc { overflow-x: auto; }
  table.tabela-rc { width: 100%; border-collapse: collapse; font-size: 12px; }
  .tabela-rc th { text-align: left; color: var(--fg-dim); font-weight: 600; font-size: 10.5px; text-transform: uppercase; letter-spacing: .04em;
                  padding: 7px 8px; border-bottom: 1px solid var(--border); white-space: nowrap; }
  .tabela-rc td { padding: 8px; border-bottom: 1px solid rgba(var(--tinta),.06); vertical-align: top; word-break: break-word; }
  .tabela-rc .chave { font-family: Consolas, monospace; font-size: 11.5px; white-space: nowrap; }
  .tabela-rc .detalhe { color: var(--fg-dim); max-width: 520px; }
  .http-rc { display: inline-block; font-size: 10.5px; font-weight: 700; padding: 2px 8px; border-radius: 999px; white-space: nowrap; }
  .http-rc.ok { background: rgba(78,201,176,.15); color: var(--ok); }
  .http-rc.erro { background: rgba(241,76,76,.14); color: var(--erro); }
  .http-rc.nada { background: rgba(var(--tinta),.07); color: var(--fg-dim); }
  .btn-liberar-rc { background: none; border: 1px solid var(--border); color: var(--fg); border-radius: 7px; padding: 5px 10px; font-size: 11.5px;
                    cursor: pointer; font-family: inherit; white-space: nowrap; }
  .btn-liberar-rc:hover { border-color: var(--teal); }
  .copiar-rc { background: none; border: none; color: var(--fg-dim); cursor: pointer; padding: 0 0 0 6px; font-size: 11px; }
  .copiar-rc:hover { color: var(--teal); }
  .vazio-rc { color: var(--fg-dim); font-size: 12.5px; padding: 18px 6px; text-align: center; }
  .rodape-tabela-rc { font-size: 11.5px; color: var(--fg-dim); margin-top: 8px; }

  .log-rc summary { cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center; }
  .log-rc summary::-webkit-details-marker { display: none; }
  .log-rc summary h2 { margin: 0; }
  .log-rc pre { margin: 12px 0 0 0; max-height: 300px; overflow: auto; font-size: 11.5px; line-height: 1.5; background: rgba(var(--poco),.25);
                border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px; white-space: pre-wrap; word-break: break-word; color: var(--fg); }
  .log-rc .l-erro { color: var(--erro); }
  .log-rc .l-aviso { color: var(--ambar-rc); }

  /* modal e toast */
  .veu-rc { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: none; align-items: center; justify-content: center; z-index: 90; padding: 16px; }
  .veu-rc.aberto { display: flex; }
  .modal-rc { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px; max-width: 460px; width: 100%; padding: 22px;
              box-shadow: 0 20px 60px rgba(0,0,0,.45); }
  .modal-rc h3 { margin: 0 0 10px 0; font-size: 16px; color: var(--fg); }
  .modal-rc .corpo { font-size: 13px; color: var(--fg-dim); line-height: 1.55; }
  .modal-rc .corpo b { color: var(--fg); }
  .botoes-modal-rc { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
  .toast-rc { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px); opacity: 0; z-index: 95; background: var(--bg-panel-solid);
              border: 1px solid var(--border-forte); color: var(--fg); padding: 10px 18px; border-radius: 10px; font-size: 13px;
              transition: opacity .2s, transform .2s; pointer-events: none; max-width: calc(100% - 32px); }
  .toast-rc.mostrar { opacity: 1; transform: translateX(-50%) translateY(0); }

  @media (max-width: 640px) {
    .acoes-rc { width: 100%; }
    .acoes-rc > * { flex: 1; justify-content: center; }
    .numeros-rc { grid-template-columns: 1fr 1fr; }
  }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-rc">
      <div>
        <h1>Reprocessamento CTe2</h1>
        <div class="sub">Acha CT-es parados no CTe2 e pede o reprocessamento pela API, com confirmação em dois ciclos antes de enviar.
          Chave que falhar uma vez fica bloqueada até alguém liberar.</div>
        <a class="credito-rc" href="/perfil/__LOGIN_AUTOR_RC__" title="Automação criada por Caio Peixoto e trazida pro PDA · ver perfil"><img class="ini" src="/foto-usuario/__LOGIN_AUTOR_RC__" alt="" onerror="this.outerHTML='&lt;span class=&quot;ini&quot;&gt;RR&lt;/span&gt;'">Desenvolvido por <b>Caio Peixoto</b></a>
      </div>
    </div>

    <div class="erro-rc" id="rc-erro"></div>
    <div id="rc-avisos"></div>
    <div class="fonte-rc" id="rc-fonte"></div>

    <div class="painel-rc">
      <div class="estado-rc" id="rc-estado">
        <div>
          <div class="titulo"><span class="pulso-rc"></span><span id="rc-estado-titulo">Carregando...</span></div>
          <div class="detalhe" id="rc-estado-detalhe"></div>
        </div>
        <div class="acoes-rc" id="rc-acoes">
          <button class="btn-sec-rc" id="rc-btn-ciclo" onclick="pedirCicloRC()" disabled>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>
            Rodar um ciclo agora
          </button>
          <button class="btn-accent" id="rc-btn-ligar" onclick="alternarLigadoRC()" disabled>Ligar</button>
        </div>
      </div>
    </div>

    <div class="aviso-rc" id="rc-so-leitura" hidden>Você está acompanhando: ligar, pausar, rodar um ciclo e liberar chaves é com os administradores.</div>
    <div class="numeros-rc" id="rc-numeros"></div>

    <div class="painel-rc">
      <h2>Último ciclo</h2>
      <div class="meta-ciclo-rc" id="rc-meta-ciclo">Nenhum ciclo rodou desde que o PDA abriu.</div>
      <div class="funil-rc" id="rc-funil"></div>
    </div>

    <div class="painel-rc">
      <div class="topo-registros-rc">
        <div class="abas-rc" id="rc-abas">
          <button data-tipo="sucessos" class="ativa" onclick="mudarAbaRC('sucessos')">Sucessos</button>
          <button data-tipo="erros" onclick="mudarAbaRC('erros')">Erros</button>
          <button data-tipo="bloqueados" onclick="mudarAbaRC('bloqueados')">Bloqueadas <span class="n" id="rc-n-bloqueadas"></span></button>
        </div>
        <div class="filtros-reg-rc">
          <input type="date" id="rc-dia" onchange="carregarRegistrosRC()" title="Dia dos sucessos e erros">
          <input type="text" id="rc-busca" placeholder="Filtrar por chave..." oninput="desenharRegistrosRC()">
        </div>
      </div>
      <div class="rolagem-rc" id="rc-registros"><div class="vazio-rc">Carregando...</div></div>
      <div class="rodape-tabela-rc" id="rc-rodape-registros"></div>
    </div>

    <div class="painel-rc">
      <details class="como-rc">
        <summary>Como funciona <span class="seta">&#9654;</span></summary>
        <ol class="passos-rc">
          <li><span>A cada <b>60 segundos</b>, procura no banco de origem CT-es com status 0, 1 ou 2 emitidos há mais de 1 minuto (até 100 por ciclo, sem as chaves bloqueadas).</span></li>
          <li><span>Na primeira vez, a chave entra na tabela de controle como <b>observando</b>. Só segue com <b>duas detecções</b> e pelo menos 1 minuto.</span></li>
          <li><span>Antes de enviar, <b>reconsulta</b> a chave na origem: se a aplicação já resolveu, só tira do controle e não chama a API.</span></li>
          <li><span>Ainda parada: <b>reserva</b> a chave (enviando) e faz o POST na API do CTe2 com a x-api-key.</span></li>
          <li><span>Deu certo ou não, a chave sai da tabela de controle (ela não guarda histórico). Observação sem nova detecção some depois de 5 minutos.</span></li>
          <li><span><b>Qualquer falha</b> (HTTP sem sucesso, tempo esgotado, rede ou envio interrompido) bloqueia a chave pra sempre. Pra tentar de novo, libere na aba Bloqueadas.</span></li>
        </ol>
      </details>
    </div>

    <details class="painel-rc log-rc" id="rc-log" style="display:none" ontoggle="if (this.open) carregarLogRC()">
      <summary><h2>Log</h2><span style="color:var(--fg-dim)">&#9654;</span></summary>
      <pre id="rc-log-conteudo">Carregando...</pre>
    </details>
  </div>

  <div class="veu-rc" id="rc-veu" onclick="if (event.target === this) fecharModalRC(false)">
    <div class="modal-rc" role="dialog" aria-modal="true">
      <h3 id="rc-modal-titulo"></h3>
      <div class="corpo" id="rc-modal-corpo"></div>
      <div class="botoes-modal-rc">
        <button class="btn-sec-rc" onclick="fecharModalRC(false)">Cancelar</button>
        <button class="btn-accent" id="rc-modal-ok" onclick="fecharModalRC(true)">Confirmar</button>
      </div>
    </div>
  </div>
  <div class="toast-rc" id="rc-toast"></div>

  __FOOTER__

<script>
const PODE_VER_LOG_RC = __PODE_VER_LOG_RC__;
// 3.3.1.0: todo mundo acompanha; ligar, pausar, rodar um ciclo, liberar chave e colar a x-api-key só administrador
const PODE_CONTROLAR_RC = __PODE_CONTROLAR_RC__;
let statusRC = null;
let abaRC = 'sucessos';
let registrosRC = [];
let totalRegistrosRC = 0;

function escaparRC(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
function numeroRC(n) { return Number(n || 0).toLocaleString('pt-BR'); }
function dataHoraRC(iso) {
  const d = new Date(iso);
  return isNaN(d) ? escaparRC(iso || '') : d.toLocaleString('pt-BR');
}
function hojeRC() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}

function mostrarToastRC(texto) {
  const el = document.getElementById('rc-toast');
  el.innerText = texto;
  el.classList.add('mostrar');
  clearTimeout(mostrarToastRC.t);
  mostrarToastRC.t = setTimeout(() => el.classList.remove('mostrar'), 3500);
}

let respostaModalRC = null;
function confirmarRC(titulo, corpo, botao) {
  document.getElementById('rc-modal-titulo').innerText = titulo;
  document.getElementById('rc-modal-corpo').innerHTML = corpo;
  document.getElementById('rc-modal-ok').innerText = botao || 'Confirmar';
  document.getElementById('rc-veu').classList.add('aberto');
  document.getElementById('rc-modal-ok').focus();
  return new Promise(r => { respostaModalRC = r; });
}
function fecharModalRC(ok) {
  document.getElementById('rc-veu').classList.remove('aberto');
  if (respostaModalRC) { respostaModalRC(ok); respostaModalRC = null; }
}
document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharModalRC(false); });

async function postarRC(url, campos) {
  const resp = await fetch(url, { method: 'POST', body: new URLSearchParams(campos || {}) });
  if (resp.status === 401) { window.location.href = '/login'; return null; }
  if (resp.status === 403) { window.location.href = '/'; return null; }
  return resp.json();
}

// ---------------- status ----------------
async function carregarStatusRC(comControle) {
  const erroEl = document.getElementById('rc-erro');
  try {
    const resp = await fetch('/api/reprocessamento-cte2/status' + (comControle ? '?controle=1' : ''));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível carregar o status.'; return; }
    erroEl.innerText = '';
    const tinhaControle = statusRC && statusRC.controle;
    statusRC = dados;
    if (!dados.controle && tinhaControle && !comControle) statusRC.controle = tinhaControle;
    desenharStatusRC();
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
  }
}

function desenharStatusRC() {
  const s = statusRC;
  // avisos
  const avisos = [];
  if (s.servico_windows === 'RUNNING') {
    avisos.push('<div class="aviso-rc perigo"><b>O serviço do Windows "ReprocessamentoCte" está rodando nesta máquina.</b> ' +
      'Pare e remova o serviço (<code>remover-servico.ps1</code>) antes de ligar aqui, pra não rodarem os dois ao mesmo tempo.</div>');
  }
  // 3.1.5.0: a origem vem sozinha (String Connection de CTe2 ou a conexão do alerta CTe2 SaaS Status Inicial) e o
  // controle fica no próprio PDA; na prática só a x-api-key pode faltar, e ela é colada aqui mesmo
  const soChave = s.faltando.length === 1 && s.faltando[0] === 'x-api-key';
  if (soChave && !PODE_CONTROLAR_RC) {
    avisos.push('<div class="aviso-rc atencao"><b>Falta só a x-api-key da API do CTe2.</b> Um administrador cola aqui no card.</div>');
  } else if (soChave) {
    avisos.push('<div class="aviso-rc atencao"><b>Falta só a x-api-key da API do CTe2.</b> Cole aqui: ela vai cifrada pra Criptografia de Dados Sensíveis e não aparece mais na tela.' +
      '<div class="form-chave-rc"><input type="password" id="rc-api-key" placeholder="x-api-key" autocomplete="off">' +
      '<button class="btn-accent" onclick="salvarApiKeyRC()">Salvar</button></div></div>');
  } else if (s.faltando.length) {
    avisos.push('<div class="aviso-rc atencao"><b>Falta configurar:</b> ' + escaparRC(s.faltando.join(', ')) + '. ' +
      'O PDA procura o banco do CTe2 sozinho numa String Connection de CTe2 ou na conexão do alerta CTe2 SaaS Status Inicial; ' +
      'se nenhuma das duas existir, cadastre uma String Connection com o produto CTe2. A x-api-key vai em Criptografia de Dados Sensíveis ' +
      '(<code>reprocessamento_cte2::API_KEY</code>).</div>');
  }
  document.getElementById('rc-avisos').innerHTML = avisos.join('');
  const fonte = [];
  if (s.fonte_origem) fonte.push('Banco do CTe2: <b>' + escaparRC(s.fonte_origem) + '</b>');
  fonte.push('Controle das chaves: <b>' + (s.controle_local ? 'no próprio PDA' : 'banco de controle configurado') + '</b>');
  document.getElementById('rc-fonte').innerHTML = fonte.join(' · ');

  // estado
  const estado = document.getElementById('rc-estado');
  estado.className = 'estado-rc ' + (s.ligado ? 'ligado' : 'pausado');
  let titulo = s.ligado ? 'Ligado' : 'Pausado';
  if (s.executando) titulo += ' · rodando um ciclo agora';
  document.getElementById('rc-estado-titulo').innerHTML = (s.executando ? '<span class="giro-rc" style="color:var(--teal)"></span> ' : '') + escaparRC(titulo);
  const partes = [];
  if (s.ligado) partes.push('Roda a cada ' + s.intervalo_segundos + ' segundos' + (s.proximo_ciclo && !s.executando ? ' · próximo ciclo ' + escaparRC(s.proximo_ciclo.slice(11)) : ''));
  else partes.push('Nenhum envio automático acontece enquanto estiver pausado.');
  if (s.alterado_em) partes.push((s.ligado ? 'Ligado' : 'Pausado') + ' por ' + escaparRC(s.alterado_por || '?') + ' em ' + escaparRC(s.alterado_em));
  document.getElementById('rc-estado-detalhe').innerHTML = partes.join(' · ');
  const btnLigar = document.getElementById('rc-btn-ligar');
  btnLigar.className = s.ligado ? 'btn-pausar-rc' : 'btn-accent';
  btnLigar.innerText = s.ligado ? 'Pausar' : 'Ligar';
  btnLigar.disabled = !s.ligado && (s.faltando.length > 0 || s.servico_windows === 'RUNNING');
  const btnCiclo = document.getElementById('rc-btn-ciclo');
  btnCiclo.disabled = s.executando || s.faltando.length > 0 || s.servico_windows === 'RUNNING';
  document.getElementById('rc-acoes').hidden = !PODE_CONTROLAR_RC;
  document.getElementById('rc-so-leitura').hidden = PODE_CONTROLAR_RC;

  // números
  const controle = s.controle || null;
  const numeros = [
    { rotulo: 'Sucessos hoje', valor: numeroRC(s.hoje.sucessos), cor: 'var(--ok)', aba: 'sucessos' },
    { rotulo: 'Erros hoje', valor: numeroRC(s.hoje.erros), cor: s.hoje.erros ? 'var(--erro)' : 'var(--ok)', aba: 'erros' },
    { rotulo: 'Chaves bloqueadas', valor: numeroRC(s.bloqueadas), cor: s.bloqueadas ? 'var(--ambar-rc)' : 'var(--ok)', aba: 'bloqueados', extra: 'não são mais tentadas' },
    { rotulo: 'Na tabela de controle', valor: controle ? numeroRC((controle.OBSERVANDO || 0) + (controle.ENVIANDO || 0)) : '-', cor: 'var(--teal)',
      extra: controle ? numeroRC(controle.OBSERVANDO || 0) + ' observando · ' + numeroRC(controle.ENVIANDO || 0) + ' enviando'
        : (s.controle_erro ? 'não consultou: ' + escaparRC(s.controle_erro).slice(0, 60) : 'consultado ao abrir a tela') },
  ];
  document.getElementById('rc-numeros').innerHTML = numeros.map(n => n.aba
    ? `<button class="numero-rc" style="--cor-n:${n.cor}" onclick="mudarAbaRC('${n.aba}')"><div class="rotulo">${n.rotulo}</div><div class="valor">${n.valor}</div>${n.extra ? `<div class="extra">${n.extra}</div>` : ''}</button>`
    : `<div class="numero-rc" style="--cor-n:${n.cor}"><div class="rotulo">${n.rotulo}</div><div class="valor">${n.valor}</div>${n.extra ? `<div class="extra">${n.extra}</div>` : ''}</div>`
  ).join('');
  document.getElementById('rc-n-bloqueadas').innerText = s.bloqueadas;

  // último ciclo (ou o que está rodando)
  const c = s.ciclo_atual || s.ultimo_ciclo;
  const meta = document.getElementById('rc-meta-ciclo');
  const funil = document.getElementById('rc-funil');
  if (!c) {
    meta.innerText = 'Nenhum ciclo rodou desde que o PDA abriu.';
    funil.innerHTML = '';
  } else {
    meta.innerHTML = (s.ciclo_atual ? '<span class="giro-rc" style="color:var(--teal)"></span> Rodando desde ' + escaparRC(c.inicio)
        : escaparRC(c.inicio) + ' · ' + (c.duracao_s != null ? c.duracao_s + ' s' : '')) +
      ' · ' + (c.origem === 'manual' ? 'disparado à mão' : 'automático') +
      (c.erro ? ' · <span class="erro" title="' + escaparRC(c.erro) + '">' + escaparRC(c.erro.length > 220 ? c.erro.slice(0, 220) + '…' : c.erro) + '</span>' : '');
    const etapas = [
      { n: c.candidatos, t: 'chaves paradas encontradas' },
      { n: c.aguardando, t: 'aguardando a 2ª detecção' },
      { n: c.resolvidos, t: 'resolvidas sozinhas (sem chamar a API)' },
      { n: c.enviados, t: 'enviadas pra API' },
      { n: c.sucessos, t: 'reprocessadas', cls: 'ok' },
      { n: c.erros + (c.reservas_expiradas || 0), t: 'falharam e foram bloqueadas', cls: (c.erros + (c.reservas_expiradas || 0)) ? 'erro' : '' },
    ];
    funil.innerHTML = etapas.map(e => `<div class="etapa-rc ${e.cls || ''}"><div class="n">${numeroRC(e.n)}</div><div class="t">${e.t}</div></div>`).join('');
  }
}

async function salvarApiKeyRC() {
  const campo = document.getElementById('rc-api-key');
  if (!campo || !campo.value.trim()) return;
  try {
    const r = await postarRC('/api/reprocessamento-cte2/api-key', { valor: campo.value.trim() });
    if (!r) return;
    if (!r.ok) { mostrarToastRC(r.erro || 'Não foi possível salvar.'); return; }
    campo.value = '';
    mostrarToastRC('x-api-key salva.');
    carregarStatusRC();
  } catch (e) { mostrarToastRC('Não foi possível salvar: ' + e); }
}

async function alternarLigadoRC() {
  if (!statusRC) return;
  const ligar = !statusRC.ligado;
  if (ligar) {
    const ok = await confirmarRC('Ligar o Reprocessamento CTe2?',
      'A cada <b>60 segundos</b> o PDA procura CT-es parados e, depois da confirmação em dois ciclos, chama a <b>API de produção</b> do CTe2 pra reprocessar. ' +
      'Chave que falhar fica bloqueada. Dá pra pausar a qualquer momento.', 'Ligar');
    if (!ok) return;
  }
  const dados = await postarRC('/api/reprocessamento-cte2/ligar', { ligado: ligar ? 'true' : 'false' });
  if (!dados) return;
  document.getElementById('rc-erro').innerText = dados.ok ? '' : (dados.erro || 'Não foi possível mudar.');
  if (dados.ok) mostrarToastRC(ligar ? 'Ligado: o primeiro ciclo começa agora.' : 'Pausado: nenhum envio novo.');
  await carregarStatusRC();
  agendarStatusRC();
}

async function pedirCicloRC() {
  const ok = await confirmarRC('Rodar um ciclo agora?',
    'Roda <b>um ciclo</b> na hora, mesmo pausado: registra as chaves paradas e envia pra API as que já foram confirmadas no ciclo anterior. ' +
    'Como a confirmação pede duas detecções, normalmente o primeiro ciclo só observa.', 'Rodar agora');
  if (!ok) return;
  const dados = await postarRC('/api/reprocessamento-cte2/executar');
  if (!dados) return;
  document.getElementById('rc-erro').innerText = dados.ok ? '' : (dados.erro || 'Não foi possível rodar.');
  await carregarStatusRC();
  agendarStatusRC();
}

let timerRC = null;
let estavaExecutandoRC = false;
function agendarStatusRC() {
  clearTimeout(timerRC);
  const espera = document.hidden ? 60000 : (statusRC && statusRC.executando ? 2500 : 10000);
  timerRC = setTimeout(async () => {
    await carregarStatusRC();
    // terminou um ciclo: atualiza as listas e a tabela de controle
    if (estavaExecutandoRC && statusRC && !statusRC.executando) { carregarRegistrosRC(); carregarStatusRC(true); if (logAbertoRC()) carregarLogRC(); }
    estavaExecutandoRC = !!(statusRC && statusRC.executando);
    agendarStatusRC();
  }, espera);
}
document.addEventListener('visibilitychange', () => { if (!document.hidden) carregarStatusRC(); agendarStatusRC(); });

// ---------------- registros ----------------
function mudarAbaRC(tipo) {
  abaRC = tipo;
  document.querySelectorAll('#rc-abas button').forEach(b => b.classList.toggle('ativa', b.dataset.tipo === tipo));
  document.getElementById('rc-dia').style.display = tipo === 'bloqueados' ? 'none' : '';
  carregarRegistrosRC();
}

async function carregarRegistrosRC() {
  const parametros = new URLSearchParams({ tipo: abaRC });
  const dia = document.getElementById('rc-dia').value;
  if (abaRC !== 'bloqueados' && dia) parametros.set('dia', dia);
  try {
    const resp = await fetch('/api/reprocessamento-cte2/registros?' + parametros);
    const dados = await resp.json();
    if (!dados.ok) { document.getElementById('rc-registros').innerHTML = '<div class="vazio-rc">' + escaparRC(dados.erro || 'Erro ao carregar.') + '</div>'; return; }
    registrosRC = dados.registros || [];
    totalRegistrosRC = dados.total || 0;
    desenharRegistrosRC();
  } catch (e) {
    document.getElementById('rc-registros').innerHTML = '<div class="vazio-rc">Erro ao carregar: ' + escaparRC(e) + '</div>';
  }
}

function etiquetaHttpRC(status, ok) {
  if (status == null) return '<span class="http-rc nada">sem resposta</span>';
  return `<span class="http-rc ${ok ? 'ok' : 'erro'}">HTTP ${escaparRC(status)}</span>`;
}

function desenharRegistrosRC() {
  const busca = document.getElementById('rc-busca').value.trim().toUpperCase();
  const lista = registrosRC.filter(r => !busca || String(r.chave || '').toUpperCase().includes(busca));
  const alvo = document.getElementById('rc-registros');
  const vazios = { sucessos: 'Nenhum reprocessamento com sucesso nesse dia.', erros: 'Nenhum erro nesse dia.', bloqueados: 'Nenhuma chave bloqueada.' };
  if (!lista.length) {
    alvo.innerHTML = '<div class="vazio-rc">' + (busca ? 'Nenhuma chave com esse filtro.' : vazios[abaRC]) + '</div>';
  } else if (abaRC === 'bloqueados') {
    alvo.innerHTML = '<table class="tabela-rc"><thead><tr><th>Quando</th><th>Chave</th><th>Resposta</th><th>Motivo</th><th></th></tr></thead><tbody>' +
      lista.map(r => `<tr><td>${dataHoraRC(r.dataHora)}</td><td class="chave">${escaparRC(r.chave)}<button class="copiar-rc" title="Copiar" data-chave="${escaparRC(r.chave)}" onclick="copiarRC(this.dataset.chave)">&#10697;</button></td>
        <td>${etiquetaHttpRC(r.statusHttp, false)}</td><td class="detalhe">${escaparRC(r.motivo)}</td>
        <td>${PODE_CONTROLAR_RC ? `<button class="btn-liberar-rc" data-chave="${escaparRC(r.chave)}" onclick="liberarRC(this.dataset.chave)">Liberar</button>` : ''}</td></tr>`).join('') + '</tbody></table>';
  } else {
    const ok = abaRC === 'sucessos';
    alvo.innerHTML = '<table class="tabela-rc"><thead><tr><th>Quando</th><th>Chave</th><th>Resposta</th><th>' + (ok ? 'Retorno da API' : 'Erro') + '</th></tr></thead><tbody>' +
      lista.map(r => `<tr><td>${dataHoraRC(r.dataHora)}</td><td class="chave">${escaparRC(r.chave)}<button class="copiar-rc" title="Copiar" data-chave="${escaparRC(r.chave)}" onclick="copiarRC(this.dataset.chave)">&#10697;</button></td>
        <td>${etiquetaHttpRC(r.statusHttp, ok)}</td><td class="detalhe">${escaparRC(ok ? (r.resposta || '-') : [r.erro, r.resposta].filter(Boolean).join(' · '))}</td></tr>`).join('') + '</tbody></table>';
  }
  document.getElementById('rc-rodape-registros').innerText = totalRegistrosRC > registrosRC.length
    ? `Mostrando os ${registrosRC.length} mais recentes de ${numeroRC(totalRegistrosRC)}.` : (totalRegistrosRC ? numeroRC(totalRegistrosRC) + ' registro(s).' : '');
}

function copiarRC(texto) {
  const fim = () => mostrarToastRC('Chave copiada.');
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(texto).then(fim); return; }
  const area = document.createElement('textarea');
  area.value = texto; area.style.position = 'fixed'; area.style.opacity = '0';
  document.body.appendChild(area); area.select();
  try { document.execCommand('copy'); fim(); } catch (e) { /* sem área de transferência */ }
  area.remove();
}

async function liberarRC(chave) {
  const ok = await confirmarRC('Liberar a chave?',
    `<b>${escaparRC(chave)}</b> sai do bloqueio definitivo e volta a ser candidata: se ainda estiver parada, passa pela confirmação em dois ciclos e é enviada de novo pra API.`,
    'Liberar');
  if (!ok) return;
  const dados = await postarRC('/api/reprocessamento-cte2/liberar', { chave });
  if (!dados) return;
  if (!dados.ok) { document.getElementById('rc-erro').innerText = dados.erro || 'Não foi possível liberar.'; return; }
  mostrarToastRC('Chave liberada.');
  carregarRegistrosRC();
  carregarStatusRC();
}

// ---------------- log ----------------
function logAbertoRC() { return PODE_VER_LOG_RC && document.getElementById('rc-log').open; }
async function carregarLogRC() {
  const pre = document.getElementById('rc-log-conteudo');
  try {
    const dados = await (await fetch('/api/logs?card=' + encodeURIComponent('Reprocessamento CTe2'))).json();
    if (!dados.ok) { pre.innerText = dados.erro || 'Não foi possível ler o log.'; return; }
    const linhas = (dados.linhas || []).slice(-120).map(l => String(l).trimEnd());
    if (!linhas.length) { pre.innerText = dados.aviso || 'Ainda não há nada registrado nesse log.'; return; }
    pre.innerHTML = linhas.map(l => `<span class="${/ERROR|falha|recusou|esgotado/i.test(l) ? 'l-erro' : (/WARNING|indisponível/i.test(l) ? 'l-aviso' : '')}">${escaparRC(l)}</span>`).join(String.fromCharCode(10));
    pre.scrollTop = pre.scrollHeight;
  } catch (e) {
    pre.innerText = 'Erro ao ler o log: ' + e;
  }
}

document.getElementById('rc-dia').value = hojeRC();
document.getElementById('rc-dia').max = hojeRC();
if (PODE_VER_LOG_RC) document.getElementById('rc-log').style.display = '';
carregarStatusRC(true).then(agendarStatusRC);
carregarRegistrosRC();
</script>
</body>
</html>
"""
