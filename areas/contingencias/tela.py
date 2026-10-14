"""Tela Contingencias.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_CONTINGENCIAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Monitoramento de Contingências</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-conting {
    background: linear-gradient(135deg, rgba(241,76,76,.10), rgba(241,76,76,0) 60%);
    border: 1px solid rgba(241,76,76,.25); border-radius: 16px;
    padding: 22px 26px; margin-bottom: 22px;
    display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
  }
  .cabecalho-conting h1 { margin: 0 0 4px 0; font-size: 20px; color: #ff8080; }
  .cabecalho-conting .sub-conting { color: var(--fg-dim); font-size: 12px; max-width: 620px; line-height: 1.5; }
  .cabecalho-conting .ultima { color: var(--fg-dim); font-size: 11px; margin-top: 8px; font-family: Consolas, monospace; }
  .aviso-scraping { background: rgba(220,220,170,.08); border: 1px solid rgba(220,220,170,.25);
                     border-radius: 10px; padding: 12px 16px; font-size: 11.5px; color: var(--run);
                     margin-bottom: 22px; line-height: 1.6; }
  .resumo-conting { display: flex; gap: 12px; margin-bottom: 24px; flex-wrap: wrap; }
  .cartao-conting { background: var(--bg-panel); backdrop-filter: blur(10px); border: 1px solid var(--border);
                     border-radius: 12px; padding: 14px 20px; min-width: 130px; }
  .cartao-conting .num { font-size: 24px; font-weight: 700; font-family: Consolas, monospace; }
  .cartao-conting .rot { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em; }

  .area-mapa { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 22px; align-items: start; }
  @media (max-width: 860px) { .area-mapa { grid-template-columns: 1fr; } }

  .painel-mapa { background: var(--bg-panel); backdrop-filter: blur(10px); border: 1px solid var(--border);
                 border-radius: 16px; padding: 24px; overflow-x: auto; }
  .painel-mapa h2 { margin: 0 0 4px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                     letter-spacing: .05em; font-weight: 600; text-align: center; }
  .painel-mapa .legenda-inline { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; justify-content: center; }
  .painel-mapa .legenda-inline .item-legenda { display: flex; align-items: center; gap: 7px; font-size: 11.5px; color: var(--fg-dim); }
  .item-legenda .amostra { width: 13px; height: 13px; border-radius: 4px; flex-shrink: 0; }
  .amostra.normal { background: rgba(78,201,176,.25); border: 1px solid var(--ok); }
  .amostra.contingencia { background: rgba(241,76,76,.3); border: 1px solid #f14c4c; }
  .amostra.agendada { background: rgba(220,220,170,.3); border: 1px solid var(--run); }
  .amostra.desconhecido { background: rgba(var(--tinta),.06); border: 1px solid var(--border-forte); }

  .mapa-escala-container { width: 100%; max-width: 680px; margin: 0 auto; position: relative;
                            overflow: hidden; }
  .mapa-wrapper { position: relative; width: 560px; height: 552px; transform-origin: top left; }
  .silhueta-brasil { position: absolute; inset: 0; width: 100%; height: 100%; }
  .silhueta-brasil path {
    fill: url(#gradiente-silhueta); stroke: rgba(45,184,207,.55); stroke-width: 2;
  }
  .mapa-brasil { display: grid; grid-template-columns: repeat(9, 40px); grid-auto-rows: 40px; gap: 6px;
                 position: absolute; left: 92px; top: 46px; }
  .uf-tile {
    border-radius: 9px; display: flex; align-items: center; justify-content: center;
    font-size: 11.5px; font-weight: 700; font-family: Consolas, monospace;
    background: rgba(20,26,32,.85); border: 1px solid var(--border-forte); color: var(--fg-dim);
    transition: transform .15s ease, box-shadow .15s ease; cursor: default;
  }
  .uf-tile:hover { transform: scale(1.18); z-index: 2; border-color: var(--teal); }
  .uf-tile.normal { background: rgba(78,201,176,.28); border-color: rgba(78,201,176,.6); color: #eafff9; }
  .uf-tile.desconhecido { background: rgba(20,26,32,.85); border-color: var(--border-forte); color: var(--fg-dim); }
  .uf-tile.agendada { background: rgba(220,220,170,.3); border-color: var(--run); color: #fff8e0; }
  .uf-tile.contingencia {
    background: rgba(241,76,76,.35); border-color: #f14c4c; color: #fff;
    animation: pulso-vermelho 1.6s ease-in-out infinite;
  }
  @keyframes pulso-vermelho {
    0%, 100% { box-shadow: 0 0 6px rgba(241,76,76,.35); }
    50% { box-shadow: 0 0 18px rgba(241,76,76,.85); }
  }

  .coluna-lateral { display: flex; flex-direction: column; gap: 18px; }
  .mini-painel { background: var(--bg-panel); backdrop-filter: blur(10px); border: 1px solid var(--border);
                 border-radius: 14px; padding: 18px 20px; }
  .mini-painel h3 { margin: 0 0 12px 0; font-size: 12.5px; color: #ff8080; text-transform: uppercase;
                     letter-spacing: .04em; font-weight: 700; }
  .mini-painel h3.neutro { color: var(--teal); }
  .lista-afetados .uf-linha { font-size: 12.5px; padding: 8px 10px; border-radius: 8px;
                               background: rgba(241,76,76,.08); border: 1px solid rgba(241,76,76,.2);
                               margin-bottom: 6px; }
  .uf-linha .uf-linha-topo { display: flex; justify-content: space-between; }
  .uf-linha .uf-linha-data { color: var(--fg-dim); font-size: 11px; margin-top: 3px; font-family: Consolas, monospace; }
  .uf-linha.agendada { background: rgba(220,220,170,.08); border-color: rgba(220,220,170,.25); }
  .sem-afetados { color: var(--fg-dim); font-size: 12.5px; }

  .mini-painel p { color: var(--fg-dim); font-size: 12px; line-height: 1.6; margin: 0 0 12px 0; }
  .links-oficiais { display: flex; flex-direction: column; gap: 8px; }
  .links-oficiais a { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--teal);
                       text-decoration: none; padding: 8px 10px; border-radius: 8px;
                       background: rgba(45,184,207,.08); border: 1px solid rgba(45,184,207,.2); }
  .links-oficiais a:hover { background: rgba(45,184,207,.15); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-conting">
      <div>
        <h1>Monitoramento de Contingências · SVC-AN / SVC-RS</h1>
        <div class="sub-conting">
          Acompanha a disponibilidade dos autorizadores de NF-e por UF e sinaliza
          quando um estado provavelmente está operando via contingência.
        </div>
        <div class="ultima" id="ultima-verificacao">carregando...</div>
      </div>
      <button class="btn-accent" id="botao-atualizar-contingencias" onclick="atualizarAgora()">Atualizar agora</button>
    </div>

    <div class="aviso-scraping" id="aviso-erro" style="display:none"></div>

    <div class="resumo-conting" id="resumo-conting"></div>

    <div class="area-mapa">
      <div class="painel-mapa">
        <h2>Disponibilidade por UF</h2>
        <div class="legenda-inline">
          <div class="item-legenda"><div class="amostra normal"></div> Normal</div>
          <div class="item-legenda"><div class="amostra contingencia"></div> Contingência ativa</div>
          <div class="item-legenda"><div class="amostra agendada"></div> Contingência agendada</div>
          <div class="item-legenda"><div class="amostra desconhecido"></div> Não verificado</div>
        </div>
          <div class="mapa-escala-container" id="mapa-escala-container">
            <div class="mapa-wrapper" id="mapa-wrapper-escalavel">
              <svg class="silhueta-brasil" viewBox="0 0 560 552" preserveAspectRatio="xMidYMid meet">
                <defs>
                  <linearGradient id="gradiente-silhueta" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#2db8cf" stop-opacity="0.28"/>
                    <stop offset="100%" stop-color="#b0cb1c" stop-opacity="0.20"/>
                  </linearGradient>
                </defs>
                        <path d="M 193.7,20.0 L 186.4,29.0 L 146.3,36.4 L 151.4,59.5 L 158.2,61.7 L 134.5,74.7 L 123.2,74.7 L 108.0,58.4 L 78.7,65.1 L 71.9,88.8 L 78.1,104.6 L 74.7,127.7 L 42.6,143.0 L 20.0,184.7 L 29.0,210.6 L 41.4,219.7 L 56.7,220.2 L 65.1,232.1 L 89.4,233.2 L 122.1,219.1 L 134.5,243.9 L 189.2,265.9 L 196.5,280.6 L 192.6,281.1 L 196.0,297.5 L 218.0,302.6 L 219.1,311.0 L 227.5,312.1 L 223.0,315.0 L 227.5,325.1 L 221.9,337.0 L 224.2,370.8 L 250.1,382.6 L 254.1,378.1 L 253.5,395.6 L 267.0,400.7 L 267.0,415.9 L 274.4,426.6 L 272.7,437.9 L 258.0,445.2 L 229.2,480.2 L 271.5,510.7 L 279.4,532.1 L 315.5,498.8 L 343.7,459.3 L 347.7,425.5 L 356.7,415.9 L 400.7,395.1 L 434.0,393.4 L 453.7,371.4 L 472.9,326.2 L 479.1,284.5 L 497.1,271.5 L 509.5,252.4 L 507.9,245.0 L 534.9,217.4 L 540.0,197.1 L 537.2,173.4 L 528.7,156.5 L 496.6,147.5 L 470.6,124.3 L 415.4,115.3 L 403.5,103.5 L 342.0,83.2 L 343.2,66.2 L 330.2,52.1 L 324.6,34.7 L 310.5,42.0 L 298.6,62.9 L 271.0,52.7 L 218.0,69.6 L 210.6,53.3 L 212.3,30.7 L 207.2,22.3 Z"/>
              </svg>
              <div class="mapa-brasil" id="mapa-brasil"></div>
            </div>
          </div>
      </div>

      <div class="coluna-lateral">
        <div class="mini-painel lista-afetados">
          <h3>Contingência ativa agora</h3>
          <div id="lista-afetados"><div class="sem-afetados">Nenhuma no momento.</div></div>
        </div>

        <div class="mini-painel">
          <h3 class="neutro">Contingências agendadas</h3>
          <div id="lista-agendadas"><div class="sem-afetados">Nenhuma no momento.</div></div>
          <div class="links-oficiais" style="margin-top:14px">
            <a href="https://www.sefaz.rs.gov.br/NFE/NFE-SVC.aspx" target="_blank" rel="noopener">
              Fonte oficial: situação SVC-RS ↗
            </a>
            <a href="https://www.nfe.fazenda.gov.br/portal/principal.aspx" target="_blank" rel="noopener">
              Fonte oficial: Portal Nacional NF-e (SVC-AN) ↗
            </a>
          </div>
        </div>
      </div>
    </div>
  </div>

  __FOOTER__

<script>
const GRADE_UF = __GRADE_UF_JSON__;
const NOME_UF = __NOME_UF_JSON__;
const SVC_POR_UF = __SVC_POR_UF_JSON__;

function montarMapa() {
  const mapa = document.getElementById('mapa-brasil');
  mapa.innerHTML = '';
  for (const uf in GRADE_UF) {
    const [col, lin] = GRADE_UF[uf];
    const tile = document.createElement('div');
    tile.className = 'uf-tile desconhecido';
    tile.id = 'uf-' + uf;
    tile.style.gridColumn = (col + 1);
    tile.style.gridRow = (lin + 1);
    tile.innerText = uf;
    tile.title = NOME_UF[uf] + ' (contingência: ' + SVC_POR_UF[uf] + ')';
    mapa.appendChild(tile);
  }
}

let ultimaAssinaturaConting = '';

async function carregarContingencias() {
  try {
    const resp = await fetch('/api/contingencias');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();

    const avisoEl = document.getElementById('aviso-erro');
    if (dados.ultimo_erro) {
      avisoEl.style.display = 'block';
      avisoEl.innerText = '⚠ Não foi possível confirmar a última consulta ao portal da NF-e: ' + dados.ultimo_erro;
    } else {
      avisoEl.style.display = 'none';
    }

    document.getElementById('ultima-verificacao').innerText =
      dados.ultima_verificacao ? ('Última verificação: ' + dados.ultima_verificacao) : 'Ainda não verificado';

    // Se nada mudou desde o ultimo poll, nao mexe em NADA no DOM - evita
    // reiniciar a animacao de pulso dos tiles em contingencia (senao ela
    // "piscaria" de novo a cada 5s mesmo sem mudanca real) e economiza
    // trabalho de layout do navegador.
    const assinaturaAtual = JSON.stringify(dados.ufs) + JSON.stringify(dados.detalhes || {});
    if (assinaturaAtual === ultimaAssinaturaConting) return;
    ultimaAssinaturaConting = assinaturaAtual;

    let normal = 0, contingencia = 0, agendada = 0, desconhecido = 0;
    const afetados = [];
    const agendadas = [];
    const detalhes = dados.detalhes || {};
    for (const uf in dados.ufs) {
      const status = dados.ufs[uf];
      const tile = document.getElementById('uf-' + uf);
      if (tile && tile.dataset.status !== status) {
        tile.className = 'uf-tile ' + status;
        tile.dataset.status = status;
      }
      if (status === 'normal') normal++;
      else if (status === 'contingencia') { contingencia++; afetados.push(uf); }
      else if (status === 'agendada') { agendada++; agendadas.push(uf); }
      else desconhecido++;
    }

    document.getElementById('resumo-conting').innerHTML = `
      <div class="cartao-conting"><div class="num" style="color:var(--ok)">${normal}</div><div class="rot">Normal</div></div>
      <div class="cartao-conting"><div class="num" style="color:#f14c4c">${contingencia}</div><div class="rot">Contingência</div></div>
      <div class="cartao-conting"><div class="num" style="color:var(--run)">${agendada}</div><div class="rot">Agendada</div></div>
      <div class="cartao-conting"><div class="num" style="color:var(--fg-dim)">${desconhecido}</div><div class="rot">Não verificado</div></div>
    `;

    const listaEl = document.getElementById('lista-afetados');
    if (afetados.length === 0) {
      listaEl.innerHTML = '<div class="sem-afetados">Nenhuma no momento.</div>';
    } else {
      listaEl.innerHTML = afetados.map(uf => {
        const d = detalhes[uf];
        const linhaData = d ? `<div class="uf-linha-data">Desde ${d.inicio}${d.fim ? ' até ' + d.fim : ''}</div>` : '';
        return `<div class="uf-linha">
          <div class="uf-linha-topo"><span>${NOME_UF[uf]} (${uf})</span><span>${SVC_POR_UF[uf]}</span></div>
          ${linhaData}
        </div>`;
      }).join('');
    }

    const listaAgendadasEl = document.getElementById('lista-agendadas');
    if (agendadas.length === 0) {
      listaAgendadasEl.innerHTML = '<div class="sem-afetados">Nenhuma no momento.</div>';
    } else {
      listaAgendadasEl.innerHTML = agendadas.map(uf => `
        <div class="uf-linha agendada">
          <div class="uf-linha-topo"><span>${NOME_UF[uf]} (${uf})</span><span>${SVC_POR_UF[uf]}</span></div>
        </div>
      `).join('');
    }
  } catch (e) {
    document.getElementById('ultima-verificacao').innerText = 'Erro ao atualizar: ' + e;
  }
}

async function atualizarAgora() {
  const botao = document.getElementById('botao-atualizar-contingencias');
  if (botao.disabled) return;  // trava no proprio clique - ignora cliques repetidos na hora, antes ate do fetch responder
  botao.disabled = true;
  const textoOriginal = botao.innerText;
  botao.innerText = 'Atualizando...';
  try {
    const resp = await fetch('/api/contingencias/atualizar', { method: 'POST' });
    const dados = await resp.json();
    if (!dados.ok) {
      const avisoEl = document.getElementById('aviso-erro');
      avisoEl.innerText = dados.erro || 'Não foi possível atualizar.';
      avisoEl.style.display = 'block';
      setTimeout(() => { avisoEl.style.display = 'none'; }, 4000);
    }
    setTimeout(carregarContingencias, 1500);
  } finally {
    setTimeout(() => { botao.disabled = false; botao.innerText = textoOriginal; }, 1500);
  }
}

// Escala o mapa (SVG + blocos, como uma unidade só) pra caber na largura
// disponível, mantendo mapa e blocos sempre alinhados entre si em
// qualquer tamanho de tela - sem isso, o SVG (que escala sozinho via
// viewBox) e os blocos (posicionados em pixel fixo) se descolavam um do
// outro em telas estreitas, cortando o mapa pela metade no celular.
function ajustarEscalaMapa() {
  const contêiner = document.getElementById('mapa-escala-container');
  const wrapper = document.getElementById('mapa-wrapper-escalavel');
  if (!contêiner || !wrapper) return;
  const larguraBase = 560, alturaBase = 552;
  const larguraDisponivel = contêiner.clientWidth || larguraBase;
  // permite crescer um pouco além do tamanho "natural" (até 1.25x, ~700px)
  // pra dar mais espaço de respiro aos blocos de status, mas continua
  // encolhendo normalmente em telas estreitas.
  const escala = Math.min(1.25, larguraDisponivel / larguraBase);
  wrapper.style.transform = `scale(${escala})`;
  contêiner.style.height = (alturaBase * escala) + 'px';
}
window.addEventListener('resize', ajustarEscalaMapa);
if (window.ResizeObserver) {
  const observador = new ResizeObserver(ajustarEscalaMapa);
  window.addEventListener('load', () => {
    const el = document.getElementById('mapa-escala-container');
    if (el) observador.observe(el);
  });
}

montarMapa();
ajustarEscalaMapa();
carregarContingencias();
setInterval(carregarContingencias, 5000);
</script>
</body>
</html>
"""
