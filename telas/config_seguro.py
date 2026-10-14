"""Tela Config Seguro.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_CONFIG_SEGURO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Criptografia de Dados Sensíveis</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-cs { max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .cabecalho-cs h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-cs .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; }

  .painel-cs { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .painel-cs h2 { margin: 0 0 6px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .painel-cs .sub-painel { color: var(--fg-dim); font-size: 12px; margin-bottom: 16px; line-height: 1.5; }

  .linha-chave-cs { display: flex; align-items: center; justify-content: space-between; gap: 10px;
                     padding: 10px 0; border-bottom: 1px solid var(--border); }
  .linha-chave-cs:last-child { border-bottom: none; }
  .linha-chave-cs code { font-size: 12.5px; color: var(--teal); }
  .vazio-cs { color: var(--fg-dim); font-size: 12.5px; padding: 6px 0; }

  .grade-form-cs { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 14px; }
  .grade-form-cs .campo-largo { grid-column: 1 / -1; }
  .dica-cs { color: var(--fg-dim); font-size: 11.5px; margin-top: -8px; margin-bottom: 14px; line-height: 1.5; }
  .erro-cs { color: var(--erro); font-size: 12.5px; min-height: 16px; margin: 6px 0; }
  .sucesso-cs { color: var(--ok); font-size: 12.5px; min-height: 16px; margin: 6px 0; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-cs">
      <h1>Criptografia de Dados Sensíveis</h1>
      <div class="sub">
        Credenciais sensíveis (senhas de banco, tokens) cifradas com Fernet
        num arquivo só (config.dat), em vez de espalhadas em texto puro
        pelos .env. Ver o manual (CRIPTOGRAFIA.md) pra entender o que isso
        protege de verdade e como migrar o resto aos poucos.
      </div>
    </div>

    <div class="painel-cs">
      <h2>Chaves já migradas</h2>
      <div class="sub-painel">Só os nomes aparecem aqui - os valores nunca são exibidos de volta pela interface, nem pra admin.</div>
      <div id="lista-chaves-cs"><div class="vazio-cs">Carregando...</div></div>
    </div>

    <div class="painel-cs">
      <h2>Adicionar / atualizar uma chave</h2>
      <div class="sub-painel">Sobrescreve se a chave já existir.</div>
      <div class="grade-form-cs">
        <div>
          <label>Chave (formato origem::campo)</label>
          <input type="text" id="cs-chave" placeholder="ex.: saas::db_password">
        </div>
        <div>
          <label>Valor</label>
          <input type="password" id="cs-valor" placeholder="valor a cifrar" autocomplete="off">
        </div>
      </div>
      <div class="dica-cs">
        "origem" identifica de qual .env esse valor vem (ex.: "saas",
        "sharepoint", "cliente_e-cte" - use o nome do arquivo .env.&lt;origem&gt;
        sem o ".env." na frente). "campo" é o nome original da variável
        nesse arquivo (ex.: "db_password", "SHAREPOINT_PASSWORD").
      </div>
      <div class="erro-cs" id="cs-erro"></div>
      <div class="sucesso-cs" id="cs-sucesso"></div>
      <button class="btn-accent" onclick="salvarChaveConfigSeguro()">Salvar cifrado</button>
    </div>
  </div>

  __FOOTER__

<script>
async function carregarChavesConfigSeguro() {
  const el = document.getElementById('lista-chaves-cs');
  try {
    const resp = await fetch('/api/config-seguro');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      el.innerHTML = '<div class="vazio-cs">Não foi possível carregar.</div>';
      return;
    }
    if (dados.chaves.length === 0) {
      el.innerHTML = '<div class="vazio-cs">Nenhuma chave migrada ainda.</div>';
      return;
    }
    el.innerHTML = dados.chaves.map(c => `
      <div class="linha-chave-cs">
        <code>${c}</code>
        <button class="btn-mini btn-perigo" onclick="removerChaveConfigSeguro('${c}')">Remover</button>
      </div>
    `).join('');
  } catch (e) {
    el.innerHTML = '<div class="vazio-cs">Erro ao carregar: ' + e + '</div>';
  }
}

async function salvarChaveConfigSeguro() {
  const chave = document.getElementById('cs-chave').value.trim();
  const valor = document.getElementById('cs-valor').value;
  const erroEl = document.getElementById('cs-erro');
  const sucessoEl = document.getElementById('cs-sucesso');
  erroEl.innerText = '';
  sucessoEl.innerText = '';

  const resp = await fetch('/api/config-seguro/definir', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'chave=' + encodeURIComponent(chave) + '&valor=' + encodeURIComponent(valor),
  });
  const dados = await resp.json();
  if (dados.ok) {
    document.getElementById('cs-chave').value = '';
    document.getElementById('cs-valor').value = '';
    sucessoEl.innerText = 'Salvo e cifrado.';
    carregarChavesConfigSeguro();
  } else {
    erroEl.innerText = dados.erro || 'Não foi possível salvar.';
  }
}

async function removerChaveConfigSeguro(chave) {
  if (!confirm('Remover "' + chave + '"? Volta a usar o valor do .env correspondente, se existir.')) return;
  const resp = await fetch('/api/config-seguro/remover', {
    method: 'POST',
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: 'chave=' + encodeURIComponent(chave),
  });
  const dados = await resp.json();
  if (dados.ok) {
    carregarChavesConfigSeguro();
  } else {
    alert(dados.erro || 'Não foi possível remover.');
  }
}

carregarChavesConfigSeguro();
</script>
</body>
</html>
"""
