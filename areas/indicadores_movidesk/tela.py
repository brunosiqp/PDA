"""Tela Indicadores Movidesk.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_INDICADORES_MOVIDESK_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Indicadores Movidesk</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-im { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1120px; margin: 0 auto 22px auto; }
  .cabecalho-im h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-im .sub { color: var(--fg-dim); font-size: 12.5px; }
  .filtro-im { display: flex; align-items: end; gap: 10px; }
  .filtro-im label { display: block; font-size: 10.5px; color: var(--fg-dim); margin-bottom: 5px;
                      text-transform: uppercase; letter-spacing: .04em; }
  .filtro-im input[type="date"] { padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border);
                                    background: var(--bg-panel-solid); color: var(--fg); font-size: 13px; }

  .grade-im { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 18px;
              max-width: 1120px; margin: 0 auto 20px auto; }
  .cartao-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 20px 22px; }
  .cartao-numero { font-size: 34px; font-weight: 800; background: var(--gradiente-marca);
                    -webkit-background-clip: text; background-clip: text; color: transparent; line-height: 1; }
  .cartao-numero.grande { font-size: 42px; }
  .cartao-rotulo { color: var(--fg-dim); font-size: 12px; margin-top: 8px; text-transform: uppercase;
                    letter-spacing: .04em; }

  .painel-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1120px; margin: 0 auto 20px auto; }
  .painel-im h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .cabecalho-painel-im { display: flex; justify-content: space-between; align-items: center;
                          flex-wrap: wrap; gap: 10px; margin-bottom: 4px; }
  .cabecalho-painel-im h2 { margin: 0; }
  .filtro-solicitante-im { display: flex; align-items: center; gap: 8px; }
  .filtro-solicitante-im label { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                                   letter-spacing: .04em; }
  .filtro-solicitante-im select { min-width: 180px; padding: 6px 30px 6px 10px; font-size: 12.5px; }

  .barra-escalonamento { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
  .barra-escalonamento .rotulo-marcador { width: 220px; flex-shrink: 0; font-size: 12px; color: var(--fg-dim);
                                            text-align: right; text-transform: capitalize;
                                            overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .barra-escalonamento .trilha { flex: 1; background: rgba(var(--tinta),.05); border-radius: 20px;
                                   height: 24px; overflow: hidden; position: relative; }
  .barra-escalonamento .preenchimento { height: 100%; border-radius: 20px;
                                          background: var(--gradiente-marca);
                                          box-shadow: 0 0 14px rgba(45,184,207,.35);
                                          display: flex; align-items: center; justify-content: flex-end;
                                          padding-right: 12px; transition: width .5s ease; min-width: 30px; }
  .barra-escalonamento .preenchimento span { font-size: 11.5px; font-weight: 700; color: #0b0f14; }

  .grade-niveis-escalonamento { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; }
  .cartao-nivel-escalonamento { background: rgba(var(--tinta),.02); border: 1px solid var(--border);
                                  border-top: 3px solid var(--cor-nivel); border-radius: 12px;
                                  padding: 18px 20px; text-align: center; }
  .cartao-nivel-escalonamento .numero-nivel { font-size: 30px; font-weight: 800; color: var(--cor-nivel); line-height: 1; }
  .cartao-nivel-escalonamento .rotulo-nivel { font-size: 11px; color: var(--fg-dim); text-transform: uppercase;
                                                letter-spacing: .04em; margin-top: 8px; }

  .tabela-im-rolagem { overflow-x: auto; border-radius: 10px; }
  table.tabela-im { width: 100%; border-collapse: collapse; min-width: 100%; }
  table.tabela-im th, table.tabela-im td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border);
                                             font-size: 12.5px; white-space: nowrap; overflow: hidden;
                                             text-overflow: ellipsis; max-width: 220px; }
  table.tabela-im th { color: var(--teal); font-weight: 600; text-transform: uppercase; font-size: 10.5px;
                        letter-spacing: .03em; background: rgba(var(--tinta),.03); position: sticky; top: 0; }
  table.tabela-im th.col-destaque, table.tabela-im td.col-destaque {
    max-width: 340px; white-space: normal; text-overflow: clip; line-height: 1.4;
  }
  table.tabela-im tbody tr { transition: background .12s; }
  table.tabela-im tbody tr:hover { background: rgba(var(--tinta),.03); }
  table.tabela-im tbody tr:nth-child(even) { background: rgba(var(--tinta),.015); }
  table.tabela-im tr:last-child td { border-bottom: none; }
  .vazio-im { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .erro-im { color: var(--erro); font-size: 12.5px; }
  .carregando-im { color: var(--fg-dim); font-size: 12.5px; }
  .btn-exportar-im { background: rgba(var(--tinta),.05); border: 1px solid var(--border); color: var(--fg);
                     border-radius: 8px; padding: 6px 12px; font-size: 12px; cursor: pointer; white-space: nowrap; }
  .btn-exportar-im:hover:not(:disabled) { border-color: var(--teal); }
  .btn-exportar-im:disabled { opacity: .55; cursor: default; }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-im">
      <div>
        <h1>Indicadores Movidesk</h1>
        <div class="sub">Escalonamentos, dúvidas e sincronização - direto do Movidesk.</div>
      </div>
      <div class="filtro-im">
        <div>
          <label>A partir de</label>
          <input type="date" id="im-data-inicio">
        </div>
        <div>
          <label>Até</label>
          <input type="date" id="im-data-fim">
        </div>
        <div>
          <label>Equipe</label>
          <select id="im-filtro-equipe">
            <option value="">Todas</option>
            <option value="Suporte">Suporte</option>
            <option value="Monitoramento">Monitoramento</option>
          </select>
        </div>
        <button class="btn-accent" onclick="carregarIndicadoresMovidesk()">Aplicar</button>
      </div>
    </div>

    <div class="grade-im">
      <div class="cartao-im">
        <div class="cartao-numero grande" id="im-numero-duvidas">–</div>
        <div class="cartao-rotulo">Dúvidas abertas no período</div>
      </div>
      <div class="cartao-im">
        <div class="cartao-numero" id="im-numero-escalonamentos">–</div>
        <div class="cartao-rotulo">Escalonamentos no período</div>
      </div>
      <div class="cartao-im">
        <div class="cartao-numero" id="im-numero-marcadores">–</div>
        <div class="cartao-rotulo">Marcadores distintos</div>
      </div>
    </div>

    <div class="painel-im">
      <h2>Top solicitantes (dúvidas processadas)</h2>
      <div id="im-barras-solicitantes"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; margin-bottom:6px">
        <h2 style="margin:0">Chamados por analista (apontamentos)</h2>
        <button class="btn-exportar-im" id="im-botao-exportar" onclick="exportarExcelIndicadoresMes()"
                title="Todos os analistas, no período e na equipe escolhidos acima: tickets por analista, por organização e o detalhe de cada ticket">Exportar Excel (período)</button>
      </div>
      <div class="erro-im" id="im-erro-exportar"></div>
      <div id="im-barras-chamados"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <h2>Escalonamentos por marcador</h2>
      <div id="im-barras-escalonamento"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <div class="cabecalho-painel-im">
        <h2>Dúvidas processadas</h2>
        <div class="filtro-solicitante-im">
          <label for="im-filtro-solicitante">Solicitante</label>
          <select id="im-filtro-solicitante" onchange="aplicarFiltroSolicitante()">
            <option value="">Todos</option>
          </select>
        </div>
      </div>
      <div id="im-tabela-duvidas"><div class="carregando-im">Carregando...</div></div>
    </div>

    <div class="painel-im">
      <h2>Escalonamentos processados por nível</h2>
      <div id="im-niveis-escalonamento"><div class="carregando-im">Carregando...</div></div>
    </div>
  </div>

  __FOOTER__

<script>
(function () {
  document.getElementById('im-data-inicio').value = new Date().toISOString().slice(0, 8) + '01';
  document.getElementById('im-data-fim').value = new Date().toISOString().slice(0, 10);
})();

function formatarNomeColuna(nomeCru) {
  // "TICKET_SUBJECT" / "solicitado_por_nome" -> "Ticket Subject"
  // Mas se já veio bem formatado direto do SQL (com "AS [Nome Bonito]" -
  // sem underscore e não tudo maiúsculo), deixa como está, senão sigla
  // tipo "ID" viraria "Id".
  if (!nomeCru.includes('_') && nomeCru !== nomeCru.toUpperCase()) {
    return nomeCru;
  }
  return nomeCru
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\\b\\w/g, c => c.toUpperCase());
}

function renderizarTabelaDinamica(linhas, elementoDestino) {
  if (!linhas || linhas.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum registro no período.</div>';
    return;
  }
  const colunas = Object.keys(linhas[0]);

  // colunas com texto tipicamente longo (ex.: assunto do ticket) merecem
  // mais espaço e podem quebrar linha - as demais ficam compactas, com
  // reticências e o valor completo disponível ao passar o mouse.
  const comprimentoMedio = {};
  colunas.forEach(c => {
    const total = linhas.slice(0, 30).reduce((soma, l) => soma + String(l[c] ?? '').length, 0);
    comprimentoMedio[c] = total / Math.min(30, linhas.length);
  });
  const colunaDestaque = colunas.reduce((maior, c) =>
    comprimentoMedio[c] > (comprimentoMedio[maior] || 0) ? c : maior, colunas[0]);
  const usaDestaque = comprimentoMedio[colunaDestaque] > 40;

  const cabecalho = colunas.map(c =>
    `<th class="${c === colunaDestaque && usaDestaque ? 'col-destaque' : ''}">${formatarNomeColuna(c)}</th>`
  ).join('');

  const linhasHtml = linhas.slice(0, 200).map(l => {
    const celulas = colunas.map(c => {
      const valor = String(l[c] ?? '');
      const ehDestaque = c === colunaDestaque && usaDestaque;
      const classe = ehDestaque ? 'col-destaque' : '';
      const titulo = valor.length > 24 ? ` title="${valor.replace(/"/g, '&quot;')}"` : '';
      return `<td class="${classe}"${titulo}>${valor}</td>`;
    }).join('');
    return `<tr>${celulas}</tr>`;
  }).join('');

  const avisoLimite = linhas.length > 200
    ? `<div class="vazio-im">Mostrando as primeiras 200 de ${linhas.length} linhas.</div>` : '';
  elementoDestino.innerHTML =
    `<div class="tabela-im-rolagem"><table class="tabela-im"><thead><tr>${cabecalho}</tr></thead><tbody>${linhasHtml}</tbody></table></div>${avisoLimite}`;
}

function renderizarBarrasEscalonamento(escalonamentos, elementoDestino) {
  if (!escalonamentos || escalonamentos.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum escalonamento no período.</div>';
    return;
  }
  const maiorQtd = Math.max(...escalonamentos.map(e => e.qtd));
  // rotulos tipo "[ESC_MONITORAMENTO_PLENO]" ficam mais legiveis sem
  // colchete/prefixo tecnico e com sublinhado virando espaço
  const limparRotulo = (texto) => texto.replace(/^\\[|\\]$/g, '').replace(/_/g, ' ');
  elementoDestino.innerHTML = escalonamentos.map(e => {
    const percentual = Math.max(6, (e.qtd / maiorQtd) * 100);
    const rotulo = limparRotulo(e.marcador);
    return `
      <div class="barra-escalonamento">
        <div class="rotulo-marcador" title="${rotulo.replace(/"/g, '&quot;')}">${rotulo}</div>
        <div class="trilha">
          <div class="preenchimento" style="width:${percentual}%"><span>${e.qtd}</span></div>
        </div>
      </div>
    `;
  }).join('');
}

// Agrupa os MESMOS dados de "escalonamentos por marcador" (ja vem do
// backend numa unica consulta) por nivel de senioridade - os marcadores
// brutos tipo "[ESC_MONITORAMENTO_JUNIOR]"/"[ESC_MONITORAMENTO_PLENO]"/
// "[ESC_MONITORAMENTO_SENIOR]" ja trazem o nivel embutido no proprio
// nome, entao nao precisa de nenhuma consulta nova ao banco - só juntar
// o que já veio, por nível, direto no navegador.
function renderizarNiveisEscalonamento(escalonamentos, elementoDestino) {
  if (!escalonamentos || escalonamentos.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhum escalonamento no período.</div>';
    return;
  }

  const NIVEIS = [
    { chave: 'junior', rotulo: 'Júnior', padrao: /J[ÚU]NIOR/i, cor: '#2db8cf' },
    { chave: 'pleno', rotulo: 'Pleno', padrao: /PLENO/i, cor: '#b0cb1c' },
    { chave: 'senior', rotulo: 'Sênior', padrao: /S[ÊE]NIOR/i, cor: '#b389f9' },
  ];
  const totais = { junior: 0, pleno: 0, senior: 0, outros: 0 };

  for (const e of escalonamentos) {
    const nivelEncontrado = NIVEIS.find(n => n.padrao.test(e.marcador || ''));
    if (nivelEncontrado) {
      totais[nivelEncontrado.chave] += e.qtd;
    } else {
      totais.outros += e.qtd;
    }
  }

  let cartoes = NIVEIS.map(n => `
    <div class="cartao-nivel-escalonamento" style="--cor-nivel:${n.cor}">
      <div class="numero-nivel">${totais[n.chave]}</div>
      <div class="rotulo-nivel">${n.rotulo}</div>
    </div>
  `).join('');

  if (totais.outros > 0) {
    cartoes += `
      <div class="cartao-nivel-escalonamento" style="--cor-nivel:var(--fg-dim)">
        <div class="numero-nivel">${totais.outros}</div>
        <div class="rotulo-nivel">Outros marcadores</div>
      </div>
    `;
  }

  elementoDestino.innerHTML = `<div class="grade-niveis-escalonamento">${cartoes}</div>`;
}

// Conta quantas dúvidas processadas cada pessoa solicitou, a partir da
// lista completa (sem filtro) - o gráfico sempre mostra o ranking geral
// do período, independente do filtro de solicitante da tabela abaixo
// (filtrar pra 1 pessoa só deixaria o ranking sem sentido nenhum).
function contarPorSolicitante(linhas) {
  const contagem = {};
  for (const linha of linhas) {
    const nome = (linha['Solicitado Por'] || '').trim();
    if (!nome) continue;
    contagem[nome] = (contagem[nome] || 0) + 1;
  }
  return Object.entries(contagem)
    .map(([nome, qtd]) => ({ nome, qtd }))
    .sort((a, b) => b.qtd - a.qtd);
}

function renderizarBarrasSolicitantes(linhas, elementoDestino) {
  const ranking = contarPorSolicitante(linhas);
  if (ranking.length === 0) {
    elementoDestino.innerHTML = '<div class="vazio-im">Nenhuma dúvida processada com solicitante identificado no período.</div>';
    return;
  }
  // top 15, senão a barra fica ilegível de tao apertada com muita gente
  const topRanking = ranking.slice(0, 15);
  const maiorQtd = topRanking[0].qtd;
  elementoDestino.innerHTML = topRanking.map(r => {
    const percentual = Math.max(6, (r.qtd / maiorQtd) * 100);
    return `
      <div class="barra-escalonamento">
        <div class="rotulo-marcador" title="${r.nome.replace(/"/g, '&quot;')}">${r.nome}</div>
        <div class="trilha">
          <div class="preenchimento" style="width:${percentual}%"><span>${r.qtd}</span></div>
        </div>
      </div>
    `;
  }).join('');
}

// Guarda a lista completa de dúvidas processadas (sem filtro) - o
// filtro de solicitante é aplicado aqui no navegador mesmo, sem precisar
// consultar o banco de novo a cada troca.
let duvidasProcessadasCompletas = [];

function popularFiltroSolicitante(linhas) {
  const select = document.getElementById('im-filtro-solicitante');
  const valorAtual = select.value;
  const solicitantes = [...new Set(linhas.map(l => l['Solicitado Por']).filter(Boolean))].sort();
  select.innerHTML = '<option value="">Todos</option>' +
    solicitantes.map(s => `<option value="${s}">${s}</option>`).join('');
  // mantém a seleção anterior se o nome ainda existir na lista nova
  if (solicitantes.includes(valorAtual)) select.value = valorAtual;
}

function aplicarFiltroSolicitante() {
  const solicitante = document.getElementById('im-filtro-solicitante').value;
  const filtradas = solicitante
    ? duvidasProcessadasCompletas.filter(l => l['Solicitado Por'] === solicitante)
    : duvidasProcessadasCompletas;
  renderizarTabelaDinamica(filtradas, document.getElementById('im-tabela-duvidas'));
}

async function carregarIndicadoresMovidesk() {
  const dataInicio = document.getElementById('im-data-inicio').value;
  const dataFim = document.getElementById('im-data-fim').value;
  const equipeFiltro = document.getElementById('im-filtro-equipe').value;
  let params = '';
  if (dataInicio) params += (params ? '&' : '?') + 'data_inicio=' + encodeURIComponent(dataInicio);
  if (dataFim) params += (params ? '&' : '?') + 'data_fim=' + encodeURIComponent(dataFim);
  if (equipeFiltro) params += (params ? '&' : '?') + 'equipe=' + encodeURIComponent(equipeFiltro);

  document.getElementById('im-barras-escalonamento').innerHTML = '<div class="carregando-im">Carregando...</div>';
  document.getElementById('im-barras-solicitantes').innerHTML = '<div class="carregando-im">Carregando...</div>';
  document.getElementById('im-barras-chamados').innerHTML = '<div class="carregando-im">Carregando...</div>';
  document.getElementById('im-tabela-duvidas').innerHTML = '<div class="carregando-im">Carregando...</div>';

  try {
    const resp = await fetch('/api/indicadores-movidesk' + params);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();

    if (!dados.ok) {
      // erro geral (nem conseguiu conectar) - aplica em tudo
      const msg = `<div class="erro-im">⚠ ${dados.erro || 'Não foi possível carregar os indicadores.'}</div>`;
      document.getElementById('im-barras-escalonamento').innerHTML = msg;
      document.getElementById('im-barras-chamados').innerHTML = msg;
      document.getElementById('im-tabela-duvidas').innerHTML = msg;
      document.getElementById('im-niveis-escalonamento').innerHTML = msg;
      document.getElementById('im-numero-duvidas').innerText = '–';
      document.getElementById('im-numero-escalonamentos').innerText = '–';
      document.getElementById('im-numero-marcadores').innerText = '–';
      return;
    }

    // cada seção é independente agora - uma tabela com nome errado não
    // impede as outras 3 de mostrarem dado normal
    const du = dados.duvidas_abertas;
    document.getElementById('im-numero-duvidas').innerText = du.ok ? du.valor : '–';

    const esc = dados.escalonamentos;
    if (esc.ok) {
      const totalEscalonamentos = esc.dados.reduce((soma, e) => soma + e.qtd, 0);
      document.getElementById('im-numero-escalonamentos').innerText = totalEscalonamentos;
      document.getElementById('im-numero-marcadores').innerText = esc.dados.length;
      renderizarBarrasEscalonamento(esc.dados, document.getElementById('im-barras-escalonamento'));
      renderizarNiveisEscalonamento(esc.dados, document.getElementById('im-niveis-escalonamento'));
    } else {
      document.getElementById('im-numero-escalonamentos').innerText = '–';
      document.getElementById('im-numero-marcadores').innerText = '–';
      document.getElementById('im-barras-escalonamento').innerHTML = `<div class="erro-im">⚠ ${esc.erro}</div>`;
      document.getElementById('im-niveis-escalonamento').innerHTML = `<div class="erro-im">⚠ ${esc.erro}</div>`;
    }

    const dp = dados.duvidas_processadas;
    if (dp.ok) {
      duvidasProcessadasCompletas = dp.dados;
      popularFiltroSolicitante(dp.dados);
      aplicarFiltroSolicitante();
      renderizarBarrasSolicitantes(dp.dados, document.getElementById('im-barras-solicitantes'));
    } else {
      duvidasProcessadasCompletas = [];
      document.getElementById('im-tabela-duvidas').innerHTML = `<div class="erro-im">⚠ ${dp.erro}</div>`;
      document.getElementById('im-barras-solicitantes').innerHTML = `<div class="erro-im">⚠ ${dp.erro}</div>`;
    }

    const cpa = dados.chamados_por_analista;
    const elChamados = document.getElementById('im-barras-chamados');
    if (cpa && cpa.ok) {
      if (cpa.dados.length === 0) {
        elChamados.innerHTML = '<div class="vazio-im">Nenhum chamado com apontamento no período.</div>';
      } else {
        const topChamados = cpa.dados.slice(0, 15);
        const maiorQtd = topChamados[0].qtd;
        elChamados.innerHTML = topChamados.map(c => {
          const percentual = Math.max(6, (c.qtd / maiorQtd) * 100);
          return `
            <div class="barra-escalonamento">
              <div class="rotulo-marcador" title="${c.analista.replace(/"/g, '&quot;')}">${c.analista}</div>
              <div class="trilha">
                <div class="preenchimento" style="width:${percentual}%"><span>${c.qtd}</span></div>
              </div>
            </div>
          `;
        }).join('');
      }
    } else if (cpa) {
      elChamados.innerHTML = `<div class="erro-im">⚠ ${cpa.erro}</div>`;
    }
  } catch (e) {
    const msg = '<div class="erro-im">⚠ Erro ao carregar: ' + e + '</div>';
    document.getElementById('im-barras-escalonamento').innerHTML = msg;
    document.getElementById('im-barras-solicitantes').innerHTML = msg;
    document.getElementById('im-barras-chamados').innerHTML = msg;
  }
}

carregarIndicadoresMovidesk();

// Excel do período da tela ("A partir de" / "Até"), com o filtro de equipe
async function exportarExcelIndicadoresMes() {
  const botao = document.getElementById('im-botao-exportar');
  const erroEl = document.getElementById('im-erro-exportar');
  const equipe = document.getElementById('im-filtro-equipe').value;
  const dataInicio = document.getElementById('im-data-inicio').value;
  const dataFim = document.getElementById('im-data-fim').value;
  erroEl.innerText = '';
  if (dataInicio && dataFim && dataFim < dataInicio) {
    erroEl.innerText = 'A data "Até" não pode ser antes de "A partir de".';
    return;
  }
  botao.disabled = true;
  const textoOriginal = botao.innerText;
  botao.innerText = 'Gerando...';
  try {
    const params = new URLSearchParams();
    if (dataInicio) params.set('data_inicio', dataInicio);
    if (dataFim) params.set('data_fim', dataFim);
    if (equipe) params.set('equipe', equipe);
    const resp = await fetch('/api/indicadores-movidesk/exportar' + (params.toString() ? '?' + params : ''));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (!resp.ok) {
      const dados = await resp.json().catch(() => ({}));
      erroEl.innerText = dados.erro || 'Não foi possível gerar o Excel.';
      return;
    }
    const nome = (resp.headers.get('Content-Disposition') || '').match(/filename="([^"]+)"/);
    const url = URL.createObjectURL(await resp.blob());
    const link = document.createElement('a');
    link.href = url;
    link.download = nome ? nome[1] : 'indicadores_tickets.xlsx';
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    erroEl.innerText = 'Erro ao exportar: ' + e;
  } finally {
    botao.disabled = false;
    botao.innerText = textoOriginal;
  }
}
</script>
</body>
</html>
"""
