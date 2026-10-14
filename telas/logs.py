"""Tela Logs.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_LOGS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Logs</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-logs { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                     gap: 14px; max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .cabecalho-logs h1 { font-size: 20px; margin: 0 0 4px 0;
                        background: var(--gradiente-marca); -webkit-background-clip: text;
                        background-clip: text; color: transparent; }
  .cabecalho-logs .sub { color: var(--fg-dim); font-size: 12.5px; }
  .seletor-logs { display: flex; align-items: end; gap: 10px; }
  .seletor-logs label { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 5px;
                         text-transform: uppercase; letter-spacing: .04em; }
  .seletor-logs select { min-width: 320px; padding: 8px 30px 8px 12px; }

  .painel-logs { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
                 border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
                 max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .conteudo-log { background: rgba(var(--poco),.35); border: 1px solid var(--border); border-radius: 10px;
                   padding: 14px 16px; font-family: 'Consolas', 'Courier New', monospace; font-size: 11.5px;
                   line-height: 1.6; white-space: pre-wrap; word-break: break-word; max-height: 65vh;
                   overflow-y: auto; color: var(--fg); }
  .erro-logs { color: var(--erro); font-size: 12.5px; margin: 10px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-logs">
      <div>
        <h1>Logs</h1>
        <div class="sub">Últimas 1000 linhas de cada log - os do PDA ficam em logs/ na pasta do programa; os da Aplicação Monitoramento vêm direto de C:\\Empresa\\Monitoramento\\log. Cada log do PDA guarda até 200 mil linhas: passando disso, as mais antigas vão zipadas pra logs\\arquivados (os registros de um dia só, como os da Manutenção de Usuários, viram zip depois de 7 dias parados) e cada zip é apagado 30 dias depois de criado.__ARQUIVADOS_LOGS__</div>
      </div>
      <div class="seletor-logs">
        <div>
          <label>Card</label>
          <select id="logs-seletor" onchange="carregarLogSelecionado()">
            __OPCOES_LOGS__
          </select>
        </div>
        <button class="btn-mini" onclick="carregarLogSelecionado()">Atualizar</button>
      </div>
    </div>

    <div class="erro-logs" id="logs-erro"></div>

    <div class="painel-logs">
      <div class="conteudo-log" id="logs-conteudo">Carregando...</div>
    </div>
  </div>

  __FOOTER__

<script>
async function carregarLogSelecionado() {
  const nomeCard = document.getElementById('logs-seletor').value;
  const conteudoEl = document.getElementById('logs-conteudo');
  const erroEl = document.getElementById('logs-erro');
  conteudoEl.innerText = 'Carregando...';
  erroEl.innerText = '';
  try {
    const resp = await fetch('/api/logs?card=' + encodeURIComponent(nomeCard));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar.';
      conteudoEl.innerText = '';
      return;
    }
    if (dados.linhas.length === 0) {
      conteudoEl.innerText = dados.aviso || 'Ainda não há nada registrado nesse log.';
      return;
    }
    conteudoEl.innerText = dados.linhas.join('\\n');
    conteudoEl.scrollTop = conteudoEl.scrollHeight;
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
    conteudoEl.innerText = '';
  }
}

carregarLogSelecionado();
</script>
</body>
</html>
"""
