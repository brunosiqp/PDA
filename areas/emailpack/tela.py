"""Tela Emailpack.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_EMAILPACK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Monitoramento EmailPack</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-ep { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .cabecalho-ep h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-ep .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; max-width: 640px; }
  #ep-botao-executar:disabled { opacity: .55; cursor: default; }

  .erro-ep { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 0 auto 10px auto; max-width: var(--largura-pagina); }

  .painel-ep { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .painel-ep h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }

  .grade-status-ep { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; }
  .cartao-numero-ep { text-align: center; }
  .cartao-numero-ep .numero { font-size: 24px; font-weight: 800; color: var(--teal); }
  .cartao-numero-ep .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                               letter-spacing: .04em; margin-top: 4px; }

  .badge-ep { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 6px;
              font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .03em; }
  .badge-ep.rodando { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-ep.parado { background: rgba(var(--tinta),.06); color: var(--fg-dim); }
  .badge-ep .ponto { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
  .badge-ep.rodando .ponto { animation: pulso-ponto-ep 1.2s infinite; }
  @keyframes pulso-ponto-ep { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }

  .aviso-dirs-ep { background: rgba(232,163,61,.08); border: 1px solid rgba(232,163,61,.25);
                    border-radius: 10px; padding: 12px 16px; font-size: 12px; color: #e8a33d;
                    line-height: 1.6; margin-bottom: 16px; }
  .aviso-dirs-ep ul { margin: 6px 0 0 0; padding-left: 18px; }

  .vazio-ep { color: var(--fg-dim); font-size: 12.5px; padding: 8px 0; }
  .servico-ep { margin-bottom: 18px; }
  .servico-ep:last-child { margin-bottom: 0; }
  .servico-ep .nome-servico-ep { font-size: 12.5px; font-weight: 700; color: var(--fg); margin-bottom: 10px; }
  .barra-email-ep { margin-bottom: 12px; }
  .barra-email-ep:last-child { margin-bottom: 0; }
  .rotulo-barra-email-ep { font-size: 11.5px; color: var(--fg-dim); margin-bottom: 5px; overflow: hidden;
                             text-overflow: ellipsis; white-space: nowrap; }
  .trilho-barra-email-ep { position: relative; height: 24px; background: rgba(var(--tinta),.04);
                             border-radius: 6px; overflow: hidden; display: flex; align-items: center; }
  .preenchimento-barra-email-ep { position: absolute; left: 0; top: 0; bottom: 0; border-radius: 6px;
                                    background: linear-gradient(90deg, rgba(241,76,76,.5), rgba(241,76,76,.85));
                                    transition: width .5s ease; }
  .contagem-barra-email-ep { position: relative; z-index: 1; margin-left: auto; margin-right: 9px;
                               font-size: 11px; font-weight: 700; color: var(--fg); }
  .controle-ignorar-ep { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
  .controle-ignorar-ep select { flex: 1; min-width: 220px; padding: 8px 10px; border-radius: 7px;
                                  border: 1px solid var(--border); background: rgba(var(--poco),.28);
                                  color: var(--fg); font-size: 12.5px; font-family: inherit; }
  .controle-ignorar-ep select:focus { outline: none; border-color: var(--teal); }
  .linha-ignorado-ep { display: flex; justify-content: space-between; align-items: center;
                        background: rgba(var(--tinta),.02); border: 1px solid var(--border);
                        border-radius: 8px; padding: 9px 14px; margin-bottom: 6px; font-size: 12.5px; }
  .linha-ignorado-ep:last-child { margin-bottom: 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-ep">
      <div>
        <h1>Monitoramento EmailPack</h1>
        <div class="sub">
          Varre os logs dos serviços EmailPack (NOC, Geral, Empresa, Sem
          Autenticação) procurando erros por e-mail processado, e avisa no
          Teams quando encontra algo.
        </div>
      </div>
      <button class="btn-accent" id="ep-botao-executar" onclick="executarEmailPack()">Executar agora</button>
    </div>

    <div class="erro-ep" id="ep-erro"></div>

    <div class="painel-ep">
      <h2>Status</h2>
      <div class="grade-status-ep">
        <div class="cartao-numero-ep">
          <div id="ep-badge-status"><span class="badge-ep parado"><span class="ponto"></span>Carregando...</span></div>
          <div class="rotulo">Situação</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-ultima-execucao">–</div>
          <div class="rotulo">Última execução</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-linhas">–</div>
          <div class="rotulo">Linhas novas processadas</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-servicos">–</div>
          <div class="rotulo">Serviços verificados</div>
        </div>
        <div class="cartao-numero-ep">
          <div class="numero" id="ep-arquivos">–</div>
          <div class="rotulo">Arquivos verificados</div>
        </div>
      </div>
    </div>

    <div class="painel-ep">
      <h2>E-mails ignorados <span style="text-transform:none; font-weight:400; letter-spacing:normal;">(não geram aviso no Teams)</span></h2>
      __CONTROLE_IGNORAR_EP__
      <div id="ep-lista-ignorados"><div class="vazio-ep">Carregando...</div></div>
    </div>

    <div class="painel-ep">
      <h2>Erros encontrados na última execução</h2>
      <div id="ep-erros-servicos"><div class="vazio-ep">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

<script>
function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function renderizarErrosPorServico(errosPorServico) {
  const el = document.getElementById('ep-erros-servicos');
  const servicos = Object.keys(errosPorServico || {});
  if (servicos.length === 0) {
    el.innerHTML = '<div class="vazio-ep">Nenhum erro encontrado na última execução. ✓</div>';
    return;
  }

  // acha a maior contagem entre TODOS os servicos/emails, pra as barras
  // ficarem proporcionais entre si (nao so dentro do proprio servico)
  let maiorQuantidade = 1;
  for (const servico of servicos) {
    for (const email of Object.keys(errosPorServico[servico])) {
      maiorQuantidade = Math.max(maiorQuantidade, errosPorServico[servico][email].quantidade);
    }
  }

  el.innerHTML = servicos.map(servico => {
    const emails = errosPorServico[servico];
    const entradasOrdenadas = Object.keys(emails)
      .map(email => ({ email, quantidade: emails[email].quantidade }))
      .sort((a, b) => b.quantidade - a.quantidade);

    const barras = entradasOrdenadas.map(({ email, quantidade }) => {
      const largura = Math.max(6, Math.round((quantidade / maiorQuantidade) * 100));
      return `
        <div class="barra-email-ep">
          <div class="rotulo-barra-email-ep" title="${escaparHtml(email)}">${escaparHtml(email)}</div>
          <div class="trilho-barra-email-ep">
            <div class="preenchimento-barra-email-ep" style="width:${largura}%"></div>
            <span class="contagem-barra-email-ep">${quantidade}x</span>
          </div>
        </div>
      `;
    }).join('');

    return `<div class="servico-ep"><div class="nome-servico-ep">${escaparHtml(servico)}</div>${barras}</div>`;
  }).join('');
}

async function carregarStatusEmailPack() {
  try {
    const resp = await fetch('/api/emailpack/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível carregar o status.';
      return;
    }
    document.getElementById('ep-erro').innerText = '';

    const badgeEl = document.getElementById('ep-badge-status');
    const botao = document.getElementById('ep-botao-executar');
    if (dados.executando) {
      badgeEl.innerHTML = '<span class="badge-ep rodando"><span class="ponto"></span>Rodando</span>';
      botao.disabled = true;
      botao.innerText = 'Executando...';
    } else {
      badgeEl.innerHTML = '<span class="badge-ep parado"><span class="ponto"></span>Aguardando</span>';
      botao.disabled = false;
      botao.innerText = 'Executar agora';
    }

    document.getElementById('ep-ultima-execucao').innerText = dados.ultima_execucao || 'nunca rodou';
    document.getElementById('ep-linhas').innerText = dados.total_linhas_novas ?? '–';
    document.getElementById('ep-servicos').innerText = dados.servicos_verificados ?? '–';
    document.getElementById('ep-arquivos').innerText = dados.arquivos_verificados ?? '–';

    const painelErros = document.querySelectorAll('.painel-ep')[1];
    const avisoExistente = painelErros.querySelector('.aviso-dirs-ep');
    if (avisoExistente) avisoExistente.remove();
    if (dados.dirs_ausentes && dados.dirs_ausentes.length > 0) {
      const aviso = document.createElement('div');
      aviso.className = 'aviso-dirs-ep';
      aviso.innerHTML = `⚠ ${dados.dirs_ausentes.length} diretório(s) inacessível(is):<ul>` +
        dados.dirs_ausentes.map(d => `<li>${escaparHtml(d)}</li>`).join('') + '</ul>';
      painelErros.insertBefore(aviso, painelErros.querySelector('h2').nextSibling);
    }

    renderizarErrosPorServico(dados.erros_por_servico);
  } catch (e) {
    document.getElementById('ep-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

async function executarEmailPack() {
  const botao = document.getElementById('ep-botao-executar');
  if (botao.disabled) return;
  botao.disabled = true;
  botao.innerText = 'Executando...';
  try {
    const resp = await fetch('/api/emailpack/executar', { method: 'POST' });
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível executar.';
    }
  } catch (e) {
    document.getElementById('ep-erro').innerText = 'Erro ao executar: ' + e;
  } finally {
    setTimeout(carregarStatusEmailPack, 1000);
  }
}

const EH_ADMIN_EP = __EH_ADMIN_EP__;

function renderizarListaIgnorados(ignorados) {
  const el = document.getElementById('ep-lista-ignorados');
  if (ignorados.length === 0) {
    el.innerHTML = '<div class="vazio-ep">Nenhum e-mail ignorado.</div>';
    return;
  }
  el.innerHTML = ignorados.map(email => `
    <div class="linha-ignorado-ep">
      <span>${escaparHtml(email)}</span>
      ${EH_ADMIN_EP ? `<button class="btn-mini btn-perigo" onclick="removerIgnorado('${escaparHtml(email)}')">Remover</button>` : ''}
    </div>
  `).join('');
}

async function carregarEmailsEmailPack() {
  try {
    const resp = await fetch('/api/emailpack/emails');
    const dados = await resp.json();
    if (!dados.ok) return;

    renderizarListaIgnorados(dados.ignorados);

    if (EH_ADMIN_EP) {
      const select = document.getElementById('ep-select-ignorar');
      const disponiveis = dados.conhecidos.filter(e => !dados.ignorados.includes(e));
      select.innerHTML = '<option value="">Selecione um e-mail pra ignorar...</option>' +
        disponiveis.map(e => `<option value="${escaparHtml(e)}">${escaparHtml(e)}</option>`).join('');
    }
  } catch (e) {
    console.warn('Não foi possível carregar e-mails do EmailPack:', e);
  }
}

async function ignorarEmail() {
  const select = document.getElementById('ep-select-ignorar');
  const email = select.value;
  if (!email) return;
  const resp = await fetch('/api/emailpack/ignorar', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'email=' + encodeURIComponent(email),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível ignorar.';
    return;
  }
  carregarEmailsEmailPack();
}

async function removerIgnorado(email) {
  const resp = await fetch('/api/emailpack/remover-ignorado', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'email=' + encodeURIComponent(email),
  });
  const dados = await resp.json();
  if (!dados.ok) {
    document.getElementById('ep-erro').innerText = dados.erro || 'Não foi possível remover.';
    return;
  }
  carregarEmailsEmailPack();
}

carregarStatusEmailPack();
setInterval(carregarStatusEmailPack, 8000);
carregarEmailsEmailPack();
setInterval(carregarEmailsEmailPack, 15000);
</script>
</body>
</html>
"""
