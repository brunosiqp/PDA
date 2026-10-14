"""Tela Relatorios ClienteA.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_RELATORIOS_CLIENTE_A_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Relatórios ClienteA</title>
<link rel="icon" type="image/png" href="__FAVICON__">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
__NAVBAR_CSS__
  /* gerar e baixar lado a lado (formulários curtos); envio automático embaixo, largura inteira */
  .grade-cliente_a { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20px;
                  max-width: var(--largura-pagina); margin: 0 auto; align-items: stretch; }
  .grade-cliente_a > .painel-cliente_a { max-width: none; margin: 0; }
  @media (max-width: 900px) { .grade-cliente_a { grid-template-columns: 1fr; } }
  .painel-cliente_a { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                  border: 1px solid var(--border); border-radius: 16px; padding: 28px 30px;
                  max-width: var(--largura-pagina); margin: 0 auto; }
  .painel-cliente_a h2 { margin: 0 0 6px 0; font-size: 16px; color: var(--teal); }
  .painel-cliente_a .sub-cliente_a { color: var(--fg-dim); font-size: 12.5px; line-height: 1.6; margin-bottom: 22px; }
  .painel-cliente_a label { display: block; font-size: 11px; color: var(--fg-dim); margin: 0 0 6px 0;
                         text-transform: uppercase; letter-spacing: .04em; }
  .painel-cliente_a input[type="date"] { width: 100%; padding: 10px 12px; border-radius: 8px;
                                       border: 1px solid var(--border); background: rgba(var(--poco),.28);
                                       color: var(--fg); font-size: 14px; }
  .painel-cliente_a input[type="date"]:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .painel-cliente_a button.btn-accent { width: 100%; margin-top: 18px; padding: 12px; font-size: 14px; }
  .erro-cliente_a { color: var(--erro); font-size: 12.5px; margin-top: 14px; text-align: center; min-height: 14px; }
  .carregando-cliente_a { display: none; text-align: center; color: var(--fg-dim); font-size: 12.5px; margin-top: 16px; }
  .btn-secundario { width: 100%; margin-top: 8px; padding: 11px; font-size: 13.5px; border-radius: 8px;
                     background: rgba(var(--tinta),.04); color: var(--fg); border: 1px solid var(--border-forte);
                     cursor: pointer; transition: background .15s, border-color .15s; }
  .btn-secundario:hover { background: rgba(var(--tinta),.08); border-color: var(--teal); }
  .carregando-cliente_a.visivel { display: block; }
  .spinner-cliente_a { width: 22px; height: 22px; border: 3px solid rgba(45,184,207,.2); border-top-color: var(--teal);
                    border-radius: 50%; margin: 0 auto 10px auto; animation: girar-spinner 0.8s linear infinite; }
  @keyframes girar-spinner { to { transform: rotate(360deg); } }

  .resultado-cliente_a { display: none; margin-top: 20px; padding-top: 20px; border-top: 1px solid var(--border); }
  .resultado-cliente_a.visivel { display: block; }
  .resultado-cliente_a .linha-resultado { display: flex; justify-content: space-between; align-items: center;
                    background: rgba(var(--poco),.2); border: 1px solid var(--border); border-radius: 10px;
                    padding: 12px 16px; margin-bottom: 10px; }
  .resultado-cliente_a .linha-resultado .info-arquivo { font-size: 13px; }
  .resultado-cliente_a .linha-resultado .info-arquivo .contagem { color: var(--fg-dim); font-size: 11.5px; margin-top: 2px; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="grade-cliente_a">
    <div class="painel-cliente_a">
      <h2>Relatórios ClienteA</h2>
      <div class="sub-cliente_a">
        Gera os relatórios de Notas e Canceladas (CTe) do cliente ClienteA pra
        uma data específica, direto do banco de produção. Pode demorar um
        pouco dependendo do volume do dia.
      </div>

      <label>Data</label>
      <input type="date" id="cliente_a-data">

      <button class="btn-accent" onclick="gerarRelatorioClienteA()">Gerar relatório</button>

      <div class="carregando-cliente_a" id="carregando-cliente_a">
        <div class="spinner-cliente_a"></div>
        Consultando o banco e montando as planilhas...
      </div>

      <div class="erro-cliente_a" id="erro-cliente_a"></div>

      <div class="resultado-cliente_a" id="resultado-cliente_a">
        <div class="linha-resultado">
          <div class="info-arquivo">
            Notas
            <div class="contagem" id="contagem-notas"></div>
          </div>
        </div>
        <div class="linha-resultado">
          <div class="info-arquivo">
            Canceladas
            <div class="contagem" id="contagem-canceladas"></div>
          </div>
        </div>
        <a class="btn-link" id="link-zip-gerado" href="#" style="display:block; text-align:center; margin-top:10px;">Baixar (.zip)</a>
      </div>
    </div>

    <div class="painel-cliente_a">
      <h2>Baixar relatório já gerado</h2>
      <div class="sub-cliente_a">
        Se o relatório de um dia já foi gerado antes (manualmente ou pelo
        envio automático das 08:00), baixa direto sem precisar consultar o
        banco de novo - vai pra pasta Downloads do navegador.
      </div>

      <label>Data</label>
      <input type="date" id="cliente_a-data-baixar">

      <button class="btn-secundario" onclick="baixarRelatorioExistente()">Baixar relatório do dia</button>

      <div class="erro-cliente_a" id="erro-cliente_a-baixar"></div>
    </div>

    </div>

    <div class="painel-cliente_a" style="margin-top:20px">
      <h2>Envio automático diário</h2>
      <div class="sub-cliente_a">
        Todos os dias às __HORARIO_AUTOMATICO__, o relatório do dia anterior é
        gerado e enviado sozinho pro SharePoint
        (Relatorio_ClienteA/&lt;Ano&gt;/&lt;Mês&gt;/&lt;DD-MM-AAAA&gt;). Depois de conferido
        lá, o arquivo é apagado do servidor · pra baixar um dia antigo, use o SharePoint.
      </div>
      <div id="status-automatico-cliente_a" style="font-size:12.5px; color:var(--fg-dim); margin-bottom:14px;">Carregando status...</div>
      <button onclick="forcarRelatorioAutomatico()">Testar envio automático agora</button>
      <button onclick="alternarLogClienteA()" id="botao-log-cliente_a" style="margin-left:8px">Ver log isolado</button>
      <div id="log-cliente_a-container" style="display:none; margin-top:14px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
          <span style="font-size:11px; color:var(--fg-dim); text-transform:uppercase; letter-spacing:.04em;">
            Últimas linhas de cliente_a_relatorios.log
          </span>
          <button onclick="carregarLogClienteA()" class="btn-mini">Atualizar</button>
        </div>
        <pre id="log-cliente_a-conteudo" style="background:rgba(var(--poco),.35); border:1px solid var(--border);
             border-radius:8px; padding:12px 14px; max-height:360px; overflow-y:auto; font-size:11px;
             font-family:Consolas,monospace; color:var(--fg-dim); white-space:pre-wrap; word-break:break-word;
             margin:0;">Carregando...</pre>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
(function () {
  const hoje = new Date();
  const ontem = new Date(hoje);
  ontem.setDate(hoje.getDate() - 1);
  document.getElementById('cliente_a-data').value = ontem.toISOString().slice(0, 10);
})();

async function carregarStatusAutomaticoClienteA() {
  try {
    const resp = await fetch('/api/relatorios-cliente_a/status');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    const el = document.getElementById('status-automatico-cliente_a');
    if (!dados.ultima_execucao) {
      el.innerText = 'Ainda não rodou nesta execução do programa.';
    } else if (dados.ultimo_erro) {
      el.innerHTML = '<span style="color:var(--erro)">⚠ Última tentativa (' + dados.ultima_execucao + ') falhou: ' + dados.ultimo_erro + '</span>';
    } else {
      el.innerHTML = '<span style="color:var(--ok)">✓ Último envio bem-sucedido: ' + dados.ultimo_sucesso + '</span>';
    }
  } catch (e) {
    document.getElementById('status-automatico-cliente_a').innerText = 'Erro ao consultar status: ' + e;
  }
}

async function forcarRelatorioAutomatico() {
  const resp = await fetch('/api/relatorios-cliente_a/forcar-automatico', { method: 'POST' });
  if (resp.status === 401) { window.location.href = '/login'; return; }
  document.getElementById('status-automatico-cliente_a').innerText = 'Disparado - rodando em segundo plano, atualize em alguns instantes...';
  setTimeout(carregarStatusAutomaticoClienteA, 4000);
  setTimeout(() => {
    if (document.getElementById('log-cliente_a-container').style.display !== 'none') carregarLogClienteA();
  }, 4000);
}

let logClienteAVisivel = false;
function alternarLogClienteA() {
  logClienteAVisivel = !logClienteAVisivel;
  document.getElementById('log-cliente_a-container').style.display = logClienteAVisivel ? 'block' : 'none';
  document.getElementById('botao-log-cliente_a').innerText = logClienteAVisivel ? 'Esconder log isolado' : 'Ver log isolado';
  if (logClienteAVisivel) carregarLogClienteA();
}

async function carregarLogClienteA() {
  const el = document.getElementById('log-cliente_a-conteudo');
  el.innerText = 'Carregando...';
  try {
    const resp = await fetch('/api/relatorios-cliente_a/log');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { el.innerText = 'Erro: ' + dados.erro; return; }
    if (dados.linhas.length === 0) {
      el.innerText = dados.aviso || 'Ainda não há nada registrado.';
      return;
    }
    el.innerText = dados.linhas.join('\\n');
    el.scrollTop = el.scrollHeight;
  } catch (e) {
    el.innerText = 'Erro ao carregar: ' + e;
  }
}

carregarStatusAutomaticoClienteA();
async function gerarRelatorioClienteA() {
  const data = document.getElementById('cliente_a-data').value;
  const erroEl = document.getElementById('erro-cliente_a');
  const carregandoEl = document.getElementById('carregando-cliente_a');
  const resultadoEl = document.getElementById('resultado-cliente_a');
  erroEl.innerText = '';
  resultadoEl.classList.remove('visivel');

  if (!data) {
    erroEl.innerText = 'Selecione uma data.';
    return;
  }

  carregandoEl.classList.add('visivel');
  try {
    const resp = await fetch('/api/relatorios-cliente_a/gerar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'data=' + encodeURIComponent(data),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    carregandoEl.classList.remove('visivel');

    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível gerar o relatório.';
      return;
    }

    document.getElementById('contagem-notas').innerText = dados.linhas_notas + ' linha(s)';
    document.getElementById('contagem-canceladas').innerText = dados.linhas_canceladas + ' linha(s)';
    const [ano, mes, dia] = data.split('-');
    const dataArquivo = dia + '-' + mes + '-' + ano;
    document.getElementById('link-zip-gerado').href = '/api/relatorios-cliente_a/download-zip/' + encodeURIComponent(dataArquivo);
    resultadoEl.classList.add('visivel');
  } catch (e) {
    carregandoEl.classList.remove('visivel');
    erroEl.innerText = 'Erro ao gerar: ' + e;
  }
}

async function baixarRelatorioExistente() {
  const data = document.getElementById('cliente_a-data-baixar').value;
  const erroEl = document.getElementById('erro-cliente_a-baixar');
  erroEl.innerText = '';
  erroEl.style.color = '';
  if (!data) {
    erroEl.innerText = 'Selecione uma data.';
    return;
  }
  try {
    const resp = await fetch('/api/relatorios-cliente_a/existe?data=' + encodeURIComponent(data));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível conferir.';
      return;
    }
    if (!dados.existe) {
      erroEl.innerText = 'Ainda não existe relatório gerado pra esse dia (gere na seção de cima primeiro).';
      return;
    }
    // baixa um zip só com os 2 arquivos, nomeado com a data - o navegador
    // salva na pasta Downloads dele, igual qualquer outro download normal
    const [ano, mes, dia] = data.split('-');
    const dataArquivo = dia + '-' + mes + '-' + ano;
    const link = document.createElement('a');
    link.href = '/api/relatorios-cliente_a/download-zip/' + encodeURIComponent(dataArquivo);
    link.download = dataArquivo + '.zip';
    document.body.appendChild(link);
    link.click();
    link.remove();

    erroEl.style.color = 'var(--ok)';
    erroEl.innerText = 'Baixando ' + dataArquivo + '.zip...';
  } catch (e) {
    erroEl.style.color = '';
    erroEl.innerText = 'Erro ao baixar: ' + e;
  }
}
</script>
</body>
</html>
"""
