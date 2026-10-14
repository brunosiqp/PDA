"""Tela Horas Trabalhadas.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_HORAS_TRABALHADAS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Horas Trabalhadas</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .cabecalho-ht { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: 1120px; margin: 0 auto 10px auto; }
  .cabecalho-ht h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-ht .sub { color: var(--fg-dim); font-size: 12.5px; }
  .aviso-ht { max-width: 1120px; margin: 0 auto 20px auto; color: var(--fg-dim); font-size: 12px;
              line-height: 1.5; background: rgba(var(--tinta),.03); border: 1px solid var(--border);
              border-radius: 10px; padding: 10px 14px; }

  .filtro-horas-im { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .filtro-horas-im select, .filtro-horas-im input { padding: 6px 10px; font-size: 12.5px; }
  .filtro-horas-im select { min-width: 130px; padding-right: 30px; }

  .painel-im { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px;
               max-width: 1120px; margin: 0 auto 20px auto; }
  .painel-im h2 { margin: 0 0 16px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .cabecalho-painel-im { display: flex; justify-content: space-between; align-items: center;
                          flex-wrap: wrap; gap: 10px; margin-bottom: 4px; }
  .cabecalho-painel-im h2 { margin: 0; }

  .grade-resumo-horas { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
                         gap: 12px; margin-bottom: 20px; }
  .cartao-resumo-horas { background: rgba(var(--tinta),.03); border: 1px solid var(--border);
                          border-radius: 10px; padding: 14px 16px; }
  .nome-analista-horas { font-size: 12.5px; font-weight: 700; color: var(--fg);
                          overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .escala-analista-horas { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                            letter-spacing: .03em; margin: 2px 0 10px 0; }
  .horas-linha-resumo { font-size: 17px; font-weight: 700; color: var(--fg); margin-bottom: 4px; }
  .detalhe-resumo-horas { font-size: 11px; color: var(--fg-dim); margin-top: 6px; }

  .tabela-im-rolagem { overflow-x: auto; border-radius: 10px; }
  table.tabela-im { width: 100%; border-collapse: collapse; min-width: 100%; }
  table.tabela-im th, table.tabela-im td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--border);
                                             font-size: 12.5px; white-space: nowrap; overflow: hidden;
                                             text-overflow: ellipsis; max-width: 220px; }
  table.tabela-im th { color: var(--teal); font-weight: 600; text-transform: uppercase; font-size: 10.5px;
                        letter-spacing: .03em; background: rgba(var(--tinta),.03); position: sticky; top: 0; }
  table.tabela-im tbody tr { transition: background .12s; }
  table.tabela-im tbody tr:hover { background: rgba(var(--tinta),.03); }
  table.tabela-im tbody tr:nth-child(even) { background: rgba(var(--tinta),.015); }
  table.tabela-im tr:last-child td { border-bottom: none; }
  .vazio-im { color: var(--fg-dim); font-size: 12.5px; padding: 10px 0; }
  .erro-im { color: var(--erro); font-size: 12.5px; }
  .carregando-im { color: var(--fg-dim); font-size: 12.5px; }

  .tarja-ausencias-ht { max-width: 1120px; margin: 0 auto 16px auto; background: rgba(76,201,240,.08);
                          border: 1px solid rgba(76,201,240,.3); border-radius: 10px; padding: 12px 16px;
                          display: none; }
  .tarja-ausencias-ht .titulo-tarja-ht { font-size: 11px; font-weight: 700; text-transform: uppercase;
                                           letter-spacing: .04em; color: #4cc9f0; margin-bottom: 8px; }
  .tarja-ausencias-ht .itens-tarja-ht { display: flex; flex-wrap: wrap; gap: 8px; }
  .pilula-ausencia-ht { font-size: 11.5px; padding: 4px 10px; border-radius: 20px; background: rgba(var(--tinta),.05);
                          border: 1px solid var(--border); white-space: nowrap; }
  .pilula-ausencia-ht.feriado { background: rgba(241,76,76,.1); border-color: rgba(241,76,76,.3); color: #ff9d9d; }
  .pilula-ausencia-ht.day_off { background: rgba(var(--tinta),.06); border-color: var(--border-forte); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-ht">
      <div>
        <h1>Horas Trabalhadas</h1>
        <div class="sub">Apontamentos de horas por analista, direto do banco do Movidesk.</div>
      </div>
    </div>
    <div class="aviso-ht">
      Consulta direto na tabela de apontamentos do banco do Movidesk.
      Quem não tem escala configurada no escala.json é considerado 5x2
      por padrão.
    </div>
    <div class="tarja-ausencias-ht" id="tarja-ausencias-ht">
      <div class="titulo-tarja-ht">Feriados, férias e day offs no período (já excluídos da meta)</div>
      <div class="itens-tarja-ht" id="itens-tarja-ht"></div>
    </div>

    <div class="painel-im">
      <div class="cabecalho-painel-im">
        <h2>Horas trabalhadas</h2>
        <div class="filtro-horas-im">
          <select id="horas-modo-filtro" onchange="alternarModoFiltroHoras()">
            <option value="dia">Dia específico</option>
            <option value="mes">Mês inteiro</option>
            <option value="periodo">Período (de - até)</option>
          </select>
          <input type="date" id="horas-filtro-dia">
          <input type="month" id="horas-filtro-mes" style="display:none">
          <span id="horas-filtro-periodo-grupo" style="display:none; gap:8px; align-items:center">
            <input type="date" id="horas-filtro-periodo-inicio">
            <span style="color:var(--fg-dim); font-size:12px">até</span>
            <input type="date" id="horas-filtro-periodo-fim">
          </span>
          <select id="horas-filtro-equipe">
            <option value="">Todas as equipes</option>
            <option value="Suporte">Suporte</option>
            <option value="Monitoramento">Monitoramento</option>
          </select>
          <button class="btn-mini" onclick="carregarHorasTrabalhadas()">Aplicar</button>
          <button class="btn-mini" id="btn-exportar-horas" onclick="exportarHorasTrabalhadas()">Exportar Excel</button>
        </div>
      </div>
      <div id="horas-carregando" class="carregando-im" style="display:none">Consultando o banco do Movidesk...</div>
      <div id="horas-erro" class="erro-im"></div>
      <div id="horas-resumo-cards" class="grade-resumo-horas"></div>
      <div id="horas-tabela-detalhe"></div>
    </div>
  </div>

  __FOOTER__

<script>
(function () {
  document.getElementById('horas-filtro-dia').value = new Date().toISOString().slice(0, 10);
  document.getElementById('horas-filtro-mes').value = new Date().toISOString().slice(0, 7);
  document.getElementById('horas-filtro-periodo-inicio').value = new Date().toISOString().slice(0, 8) + '01';
  document.getElementById('horas-filtro-periodo-fim').value = new Date().toISOString().slice(0, 10);
})();

function alternarModoFiltroHoras() {
  const modo = document.getElementById('horas-modo-filtro').value;
  document.getElementById('horas-filtro-dia').style.display = modo === 'dia' ? '' : 'none';
  document.getElementById('horas-filtro-mes').style.display = modo === 'mes' ? '' : 'none';
  document.getElementById('horas-filtro-periodo-grupo').style.display = modo === 'periodo' ? 'inline-flex' : 'none';
}

function formatarPercentualHoras(p) {
  if (p === null || p === undefined) return '–';
  const cor = p >= 90 ? 'var(--ok)' : (p >= 50 ? 'var(--run)' : 'var(--erro)');
  return `<span style="color:${cor}; font-weight:700">${p.toFixed(1)}%</span>`;
}

function agruparHorasPorAnalista(linhas, metaPeriodoPorAnalista) {
  const grupos = {};
  for (const l of linhas) {
    if (!grupos[l.analista]) {
      grupos[l.analista] = {
        analista: l.analista, escala: l.escala, cadastrado_na_escala: l.cadastrado_na_escala,
        // a meta agora vem pronta do backend, calculada pelo calendário
        // inteiro do período (não soma mais linha por linha aqui) - ver
        // _calcular_meta_periodo no servidor pro motivo
        minutos_trabalhados: 0, minutos_meta: metaPeriodoPorAnalista[l.analista] || 0,
        dias_com_registro: 0, qtd_tickets: 0,
      };
    }
    const g = grupos[l.analista];
    g.minutos_trabalhados += l.minutos_trabalhados;
    g.dias_com_registro += 1;
    g.qtd_tickets += l.qtd_tickets;
  }
  return Object.values(grupos).sort((a, b) => a.analista.localeCompare(b.analista));
}

function minutosParaHoras(min) {
  min = Math.round(min);
  const h = Math.floor(min / 60), m = min % 60;
  return String(h).padStart(2, '0') + ':' + String(m).padStart(2, '0');
}

function obterPeriodoSelecionadoHoras() {
  const modo = document.getElementById('horas-modo-filtro').value;
  let dataInicio, dataFim;
  if (modo === 'dia') {
    const dia = document.getElementById('horas-filtro-dia').value;
    if (!dia) { document.getElementById('horas-erro').innerText = 'Selecione uma data.'; return null; }
    dataInicio = dia; dataFim = dia;
  } else if (modo === 'periodo') {
    dataInicio = document.getElementById('horas-filtro-periodo-inicio').value;
    dataFim = document.getElementById('horas-filtro-periodo-fim').value;
    if (!dataInicio || !dataFim) { document.getElementById('horas-erro').innerText = 'Selecione as duas datas do período.'; return null; }
    if (dataFim < dataInicio) { document.getElementById('horas-erro').innerText = 'A data final não pode ser antes da inicial.'; return null; }
  } else {
    const mes = document.getElementById('horas-filtro-mes').value;
    if (!mes) { document.getElementById('horas-erro').innerText = 'Selecione um mês.'; return null; }
    const [ano, mesNum] = mes.split('-').map(Number);
    dataInicio = mes + '-01';
    const ultimoDia = new Date(ano, mesNum, 0).getDate();
    dataFim = mes + '-' + String(ultimoDia).padStart(2, '0');
  }
  return { dataInicio, dataFim };
}

function renderizarTarjaAusencias(ausencias) {
  const tarja = document.getElementById('tarja-ausencias-ht');
  if (!ausencias.length) { tarja.style.display = 'none'; return; }
  const escapar = (txt) => String(txt).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const rotulosTipo = { feriado: '📅', ferias: '🏖️', day_off: '☕', atestado: '🩺', afastamento: '🩺' };
  document.getElementById('itens-tarja-ht').innerHTML = ausencias.map(a => {
    const periodo = a.inicio === a.fim ? a.inicio : `${a.inicio} a ${a.fim}`;
    // atestado e afastamento (3.4.4.0) aparecem só como ausência: a tela é aberta pra todo mundo
    const rotuloTipo = a.tipo === 'feriado' ? '' : (a.tipo === 'day_off' ? ' (Day Off)' : (a.tipo === 'atestado' || a.tipo === 'afastamento' ? ' (Ausente)' : ' (Férias)'));
    return `<span class="pilula-ausencia-ht ${a.tipo}">${rotulosTipo[a.tipo] || ''} ${escapar(a.nome)}${rotuloTipo} · ${periodo}</span>`;
  }).join('');
  tarja.style.display = 'block';
}

async function carregarHorasTrabalhadas() {
  const periodo = obterPeriodoSelecionadoHoras();
  if (!periodo) return;
  const { dataInicio, dataFim } = periodo;

  document.getElementById('horas-erro').innerText = '';
  document.getElementById('horas-resumo-cards').innerHTML = '';
  document.getElementById('horas-tabela-detalhe').innerHTML = '';
  document.getElementById('tarja-ausencias-ht').style.display = 'none';
  document.getElementById('horas-carregando').style.display = 'block';

  try {
    const equipeFiltro = document.getElementById('horas-filtro-equipe').value;
    let url = `/api/indicadores-movidesk/horas?data_inicio=${dataInicio}&data_fim=${dataFim}`;
    if (equipeFiltro) url += `&equipe=${encodeURIComponent(equipeFiltro)}`;
    const resp = await fetch(url);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    document.getElementById('horas-carregando').style.display = 'none';

    if (!dados.ok) {
      document.getElementById('horas-erro').innerText = '⚠ ' + dados.erro;
      return;
    }

    renderizarTarjaAusencias(dados.ausencias_periodo || []);

    if (dados.linhas.length === 0) {
      document.getElementById('horas-tabela-detalhe').innerHTML = '<div class="vazio-im">Nenhum apontamento de horas encontrado no período.</div>';
      return;
    }

    const resumos = agruparHorasPorAnalista(dados.linhas, dados.meta_periodo_por_analista || {});
    document.getElementById('horas-resumo-cards').innerHTML = resumos.map(r => {
      const percentual = r.minutos_meta > 0 ? (r.minutos_trabalhados / r.minutos_meta * 100) : null;
      const semEscala = !r.cadastrado_na_escala ? '<span title="Não cadastrado no escala.json - considerado 5x2 por padrão" style="color:var(--fg-dim); cursor:help"> ⓘ</span>' : '';
      return `
        <div class="cartao-resumo-horas">
          <div class="nome-analista-horas">${r.analista}${semEscala}</div>
          <div class="escala-analista-horas">${r.escala}</div>
          <div class="horas-linha-resumo">
            <span>${minutosParaHoras(r.minutos_trabalhados)}</span>
            <span style="color:var(--fg-dim)"> / ${minutosParaHoras(r.minutos_meta)}</span>
          </div>
          <div>${formatarPercentualHoras(percentual)}</div>
          <div class="detalhe-resumo-horas">${r.dias_com_registro} dia(s) · ${r.qtd_tickets} chamado(s)</div>
        </div>
      `;
    }).join('');

    const linhasOrdenadas = dados.linhas.slice().sort((a, b) => a.analista.localeCompare(b.analista) || a.data_iso.localeCompare(b.data_iso));
    const corpo = linhasOrdenadas.map(l => `
      <tr>
        <td>${l.analista}</td>
        <td>${l.data}</td>
        <td>${l.escala}</td>
        <td>${l.horas_trabalhadas}</td>
        <td>${l.meta_horas}</td>
        <td>${formatarPercentualHoras(l.percentual)}</td>
        <td>${l.qtd_tickets}</td>
      </tr>
    `).join('');
    document.getElementById('horas-tabela-detalhe').innerHTML = `
      <div class="tabela-im-rolagem">
        <table class="tabela-im">
          <thead><tr><th>Analista</th><th>Data</th><th>Escala</th><th>Horas</th><th>Meta</th><th>%</th><th>Chamados</th></tr></thead>
          <tbody>${corpo}</tbody>
        </table>
      </div>
    `;
  } catch (e) {
    document.getElementById('horas-carregando').style.display = 'none';
    document.getElementById('horas-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

carregarHorasTrabalhadas();

async function exportarHorasTrabalhadas() {
  const periodo = obterPeriodoSelecionadoHoras();
  if (!periodo) return;
  const { dataInicio, dataFim } = periodo;
  const botao = document.getElementById('btn-exportar-horas');
  const textoOriginal = botao.innerText;
  botao.disabled = true;
  botao.innerText = 'Gerando...';
  try {
    const equipeFiltro = document.getElementById('horas-filtro-equipe').value;
    let urlExportar = `/api/horas-trabalhadas/exportar?data_inicio=${dataInicio}&data_fim=${dataFim}`;
    if (equipeFiltro) urlExportar += `&equipe=${encodeURIComponent(equipeFiltro)}`;
    const resp = await fetch(urlExportar);
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (!resp.ok) {
      let msg = 'Erro ao gerar a exportação.';
      try { msg = (await resp.json()).erro || msg; } catch (e) {}
      document.getElementById('horas-erro').innerText = '⚠ ' + msg;
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `horas_trabalhadas_${dataInicio}_a_${dataFim}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    document.getElementById('horas-erro').innerText = 'Erro ao exportar: ' + e;
  } finally {
    botao.disabled = false;
    botao.innerText = textoOriginal;
  }
}
</script>
</body>
</html>
"""
