"""Tela Dash Financeiro.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
Redesenhada na 2.35.0.0: resumo do mês de referência, progresso ao vivo da
rodada, estado de cada produto pelo arquivo do mês, linha do tempo dos meses,
confirmação em modal, log ao vivo (pra quem vê logs) e aviso quando termina.
"""


_DASH_FINANCEIRO_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Atualização Dash Financeiro</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  :root { --ambar-df: #e8a33d; }
  :root[data-tema="claro"] { --ambar-df: #a8670a; }
  .cabecalho-df { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap;
                  gap: 14px; max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .cabecalho-df h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-df .sub { color: var(--fg-dim); font-size: 12.5px; line-height: 1.5; max-width: 640px; }
  .cabecalho-df code { font-size: 11.5px; background: rgba(var(--tinta),.06); padding: 1px 6px; border-radius: 5px; }
  .acoes-df { display: flex; flex-direction: column; align-items: flex-end; gap: 5px; }
  #df-botao-executar { min-width: 210px; }
  #df-botao-executar:disabled { opacity: .55; cursor: default; }
  .dica-botao-df { font-size: 11px; color: var(--fg-dim); text-align: right; max-width: 260px; }
  /* mês a gerar (2.35.1.0) */
  .seletor-mes-df { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
  .seletor-mes-df label { font-size: 11px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em; }
  .seletor-mes-df input { background: rgba(var(--poco),.25); border: 1px solid var(--border); color: var(--fg); border-radius: 8px;
                          padding: 7px 10px; font-size: 13px; font-family: inherit; color-scheme: dark; }
  :root[data-tema="claro"] .seletor-mes-df input { color-scheme: light; }
  .seletor-mes-df input:focus { outline: none; border-color: var(--teal); }
  .seletor-mes-df .passo-mes { background: none; border: 1px solid var(--border); color: var(--fg-dim); border-radius: 8px;
                               width: 32px; height: 32px; cursor: pointer; font-size: 15px; display: grid; place-items: center; padding: 0; }
  .seletor-mes-df .passo-mes:hover:not(:disabled) { color: var(--fg); border-color: var(--teal); }
  .seletor-mes-df .passo-mes:disabled { opacity: .35; cursor: default; }
  .voltar-mes-df { font-size: 11.5px; color: var(--teal); background: none; border: none; cursor: pointer; padding: 0; font-family: inherit; }
  .voltar-mes-df:hover { text-decoration: underline; }
  .tile-df .etq-mes { display: inline-block; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 999px; margin-left: 6px;
                      vertical-align: 3px; background: rgba(232,163,61,.15); color: var(--ambar-df); text-transform: uppercase; letter-spacing: .04em; }

  .erro-df { color: var(--erro); font-size: 12.5px; min-height: 0; max-width: var(--largura-pagina); margin: 0 auto 10px auto; }
  .erro-df:empty { display: none; }

  /* resumo do mês de referência */
  .resumo-df { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px;
               max-width: var(--largura-pagina); margin: 0 auto 10px auto; }
  .tile-df { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; padding: 14px 16px;
             position: relative; overflow: hidden; }
  .tile-df::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--cor-tile, var(--teal)); }
  .tile-df .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .06em; }
  .tile-df .valor { font-size: 24px; font-weight: 800; color: var(--fg); margin-top: 4px; line-height: 1.1; }
  .tile-df .valor small { font-size: 13px; font-weight: 600; color: var(--fg-dim); }
  .tile-df .extra { font-size: 11px; color: var(--fg-dim); margin-top: 4px; }
  .tile-df.clicavel { cursor: pointer; transition: border-color .15s; }
  .tile-df.clicavel:hover { border-color: var(--cor-tile, var(--teal)); }
  .linha-auto-df { max-width: var(--largura-pagina); margin: 0 auto 18px auto; font-size: 11.5px; color: var(--fg-dim);
                   display: flex; gap: 7px; align-items: baseline; }
  .linha-auto-df .ponto { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); display: inline-block; flex: none; }

  .painel-df { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 20px 22px;
               max-width: var(--largura-pagina); margin: 0 auto 20px auto; }
  .painel-df h2 { margin: 0 0 6px 0; font-size: 13px; color: var(--fg-dim); text-transform: uppercase;
                  letter-spacing: .06em; }
  .painel-df .sub-painel { color: var(--fg-dim); font-size: 12px; margin-bottom: 16px; line-height: 1.5; }

  /* progresso da rodada */
  #df-progresso { display: none; border-color: rgba(45,184,207,.45); }
  .topo-progresso-df { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; flex-wrap: wrap; }
  .topo-progresso-df .titulo { font-size: 14px; font-weight: 700; color: var(--fg); }
  .topo-progresso-df .tempo { font-size: 12px; color: var(--fg-dim); font-variant-numeric: tabular-nums; }
  .barra-df { height: 8px; border-radius: 999px; background: rgba(var(--tinta),.08); overflow: hidden; margin: 12px 0; }
  .barra-df > div { height: 100%; background: var(--gradiente-marca); border-radius: 999px; transition: width .6s ease; }
  .passos-df { display: flex; flex-wrap: wrap; gap: 6px; }
  .passo-df { font-size: 11.5px; padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border);
              color: var(--fg-dim); display: inline-flex; align-items: center; gap: 6px; }
  .passo-df.feito { color: var(--ok); border-color: rgba(78,201,176,.4); background: rgba(78,201,176,.08); }
  .passo-df.falhou { color: var(--erro); border-color: rgba(241,76,76,.4); background: rgba(241,76,76,.08); }
  .passo-df.agora { color: var(--teal); border-color: var(--teal); background: rgba(45,184,207,.10); font-weight: 700; }
  .giro-df { width: 10px; height: 10px; border-radius: 50%; border: 2px solid currentColor; border-right-color: transparent;
             display: inline-block; animation: giro-df .8s linear infinite; flex: none; }
  @keyframes giro-df { to { transform: rotate(360deg); } }
  .nota-progresso-df { font-size: 11px; color: var(--fg-dim); margin-top: 10px; }

  /* filtros da grade */
  .topo-grade-df { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
  .filtros-df { display: flex; gap: 6px; flex-wrap: wrap; }
  .filtro-df { font-size: 12px; padding: 5px 12px; border-radius: 999px; border: 1px solid var(--border);
               background: transparent; color: var(--fg-dim); cursor: pointer; }
  .filtro-df:hover { color: var(--fg); }
  .filtro-df.ativo { color: var(--fg); border-color: var(--teal); background: rgba(45,184,207,.12); }
  .filtro-df .n { opacity: .7; margin-left: 3px; }

  .grade-produtos-df { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 14px; }
  .vazio-grade-df { color: var(--fg-dim); font-size: 12.5px; padding: 18px 4px; }
  .cartao-produto-df { background: rgba(var(--tinta),.03); border: 1px solid var(--border); border-radius: 12px;
                        padding: 14px 16px 14px 18px; position: relative; overflow: hidden; display: flex; flex-direction: column; }
  .cartao-produto-df::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--cor-estado); }
  .cartao-produto-df.estado-ok { --cor-estado: var(--ok); }
  .cartao-produto-df.estado-aviso { --cor-estado: #e8a33d; }
  .cartao-produto-df.estado-erro { --cor-estado: var(--erro); }
  .cartao-produto-df.estado-pendente { --cor-estado: #e8a33d; border-style: dashed; }
  .cartao-produto-df.estado-rodando { --cor-estado: var(--teal); border-color: rgba(45,184,207,.5);
                                       box-shadow: 0 0 0 1px rgba(45,184,207,.25), 0 6px 22px rgba(45,184,207,.10); }
  .cartao-produto-df.estado-fila { --cor-estado: rgba(var(--tinta),.25); }
  .topo-cartao-df { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
  .nome-produto { font-size: 15px; font-weight: 800; color: var(--fg); }
  .badge-status-df { display: inline-flex; align-items: center; gap: 5px; padding: 3px 9px; border-radius: 999px; font-size: 10.5px;
                      font-weight: 700; text-transform: uppercase; letter-spacing: .03em; white-space: nowrap; }
  .badge-ok { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-aviso, .badge-pendente { background: rgba(232,163,61,.15); color: var(--ambar-df); }
  .badge-rodando { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-erro { background: rgba(241,76,76,.15); color: var(--erro); }
  .badge-fila { background: rgba(var(--tinta),.07); color: var(--fg-dim); }

  .arquivo-mes-df { font-size: 12px; color: var(--fg); margin-top: 10px; display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
  .arquivo-mes-df .mes { font-weight: 700; }
  .arquivo-mes-df .dim { color: var(--fg-dim); font-size: 11.5px; }
  .ultima-df { font-size: 11.5px; color: var(--fg-dim); margin-top: 4px; line-height: 1.5; }
  .ultima-df b { color: var(--fg); font-weight: 700; }
  .erro-cartao-df { font-size: 11.5px; color: var(--erro); margin-top: 8px; line-height: 1.45; word-break: break-word; }

  /* quantos clientes trouxeram dados, vieram vazios ou falharam */
  .barra-clientes-df { display: flex; height: 6px; border-radius: 999px; overflow: hidden; margin-top: 10px; background: rgba(var(--tinta),.07); }
  .barra-clientes-df span { display: block; height: 100%; }
  .barra-clientes-df .s-ok { background: var(--ok); }
  .barra-clientes-df .s-vazio { background: #e8a33d; }
  .barra-clientes-df .s-erro { background: var(--erro); }
  .legenda-clientes-df { font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; display: flex; gap: 10px; flex-wrap: wrap; }
  .legenda-clientes-df i { display: inline-block; width: 7px; height: 7px; border-radius: 50%; margin-right: 4px; }

  .problemas-df { margin-top: 8px; display: flex; flex-direction: column; gap: 4px; }
  .problema-df { font-size: 11px; line-height: 1.45; padding: 5px 8px; border-radius: 7px; word-break: break-word; }
  .problema-df.erro { background: rgba(241,76,76,.10); color: var(--erro); }
  .problema-df.vazio { background: rgba(232,163,61,.10); color: var(--ambar-df); }

  .rotulo-secao-df { font-size: 10px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em;
                      margin: 12px 0 5px 0; display: flex; justify-content: space-between; }
  .chips-clientes-df { display: flex; flex-wrap: wrap; gap: 4px; }
  .chip-cliente-df { font-size: 10.5px; padding: 2px 7px; border-radius: 999px; color: var(--fg);
                      background: rgba(45,184,207,.10); border: 1px solid rgba(45,184,207,.25); }
  .chip-cliente-df.erro { background: rgba(241,76,76,.10); border-color: rgba(241,76,76,.35); }
  .chip-cliente-df.vazio { background: rgba(232,163,61,.10); border-color: rgba(232,163,61,.35); }
  .chip-mais-df { font-size: 10.5px; padding: 2px 8px; border-radius: 999px; color: var(--teal); background: none;
                  border: 1px dashed rgba(45,184,207,.45); cursor: pointer; }
  .texto-dim-df { font-size: 11px; color: var(--fg-dim); }

  /* linha do tempo: últimos 12 meses */
  .linha-tempo-df { display: grid; grid-template-columns: repeat(12, 1fr); gap: 3px; }
  .mes-df { height: 16px; border-radius: 4px; background: rgba(var(--tinta),.06); border: 1px solid rgba(var(--tinta),.08);
            cursor: pointer; padding: 0; transition: transform .1s; }
  .mes-df:hover { transform: scaleY(1.25); border-color: var(--teal); }
  .mes-df.tem { background: rgba(78,201,176,.55); border-color: transparent; }
  .mes-df.ref { outline: 2px solid var(--teal); outline-offset: 1px; }
  .mes-df.ref:not(.tem) { background: repeating-linear-gradient(45deg, rgba(232,163,61,.35) 0 3px, transparent 3px 6px); }
  .eixo-tempo-df { display: flex; justify-content: space-between; font-size: 9.5px; color: var(--fg-dim); margin-top: 3px; }
  .aviso-consolidado-df { font-size: 10.5px; color: var(--ambar-df); margin-top: 8px; line-height: 1.4; }

  .acoes-cartao-df { display: flex; gap: 6px; margin-top: auto; padding-top: 14px; }
  .btn-cartao-df { flex: 1; font-size: 11.5px; padding: 7px 10px; border-radius: 8px;
                   border: 1px solid var(--border); background: rgba(var(--tinta),.04); color: var(--fg); cursor: pointer; }
  .btn-cartao-df:hover:not(:disabled) { border-color: var(--teal); }
  .btn-cartao-df.principal { border-color: rgba(232,163,61,.55); color: var(--ambar-df); }
  .btn-cartao-df:disabled { opacity: .45; cursor: default; }

  /* log ao vivo */
  .log-df summary { cursor: pointer; list-style: none; display: flex; justify-content: space-between; align-items: center; gap: 10px; }
  .log-df summary::-webkit-details-marker { display: none; }
  .log-df summary h2 { margin: 0; }
  .log-df summary .seta { color: var(--fg-dim); font-size: 12px; transition: transform .2s; }
  .log-df[open] summary .seta { transform: rotate(90deg); }
  .log-df pre { margin: 12px 0 0 0; max-height: 300px; overflow: auto; font-size: 11.5px; line-height: 1.5;
                background: rgba(var(--poco),.25); border: 1px solid var(--border); border-radius: 8px; padding: 10px 12px;
                white-space: pre-wrap; word-break: break-word; color: var(--fg); }
  .log-df .l-erro { color: var(--erro); }
  .log-df .l-aviso { color: var(--ambar-df); }

  /* teste de conexões e busca de empresa */
  #df-painel-teste { display: none; }
  .cabecalho-teste-df { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
  .btn-fechar-df { width: 30px; height: 30px; flex: none; background: none; border: 1px solid var(--border); color: var(--fg-dim);
                   border-radius: 8px; cursor: pointer; display: grid; place-items: center; padding: 0; }
  .btn-fechar-df svg { width: 14px; height: 14px; display: block; }
  .btn-fechar-df:hover { color: var(--fg); border-color: var(--teal); }
  .tabela-df { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
  .tabela-df th { text-align: left; color: var(--fg-dim); font-weight: 600; font-size: 10.5px; text-transform: uppercase;
                  letter-spacing: .04em; padding: 6px 8px; border-bottom: 1px solid var(--border); }
  .tabela-df td { padding: 7px 8px; border-bottom: 1px solid rgba(var(--tinta),.06); vertical-align: top; word-break: break-word; }
  .resultado-ok { color: var(--ok); }
  .resultado-vazio { color: var(--ambar-df); }
  .resultado-erro { color: var(--erro); }
  .rolagem-df { overflow-x: auto; }
  .busca-df { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px; }
  .busca-df input { flex: 1; min-width: 180px; background: rgba(var(--poco),.2); border: 1px solid var(--border);
                    color: var(--fg); border-radius: 8px; padding: 8px 10px; font-size: 13px; }
  .base-busca-df { margin-top: 14px; }
  .base-busca-df .titulo-base { font-size: 12px; font-weight: 700; color: var(--fg); }
  .base-busca-df .clientes-base { font-size: 11px; color: var(--fg-dim); }
  .status-teste-df { font-size: 12px; color: var(--fg-dim); margin-top: 6px; display: flex; align-items: center; gap: 8px; }

  /* modal de confirmação */
  .veu-df { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: none; align-items: center; justify-content: center;
            z-index: 1000; padding: 16px; }
  .veu-df.aberto { display: flex; }
  .modal-df { background: var(--bg); border: 1px solid var(--border); border-radius: 14px; max-width: 460px; width: 100%;
              padding: 22px 22px 18px 22px; box-shadow: 0 20px 60px rgba(0,0,0,.4); }
  .modal-df h3 { margin: 0 0 10px 0; font-size: 16px; color: var(--fg); }
  .modal-df .corpo { font-size: 13px; color: var(--fg-dim); line-height: 1.55; }
  .modal-df .corpo b { color: var(--fg); }
  .modal-df .chips-clientes-df { margin: 10px 0; }
  .botoes-modal-df { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
  .btn-sec-df { background: none; border: 1px solid var(--border); color: var(--fg); border-radius: 8px; padding: 8px 14px;
                cursor: pointer; font-size: 13px; }
  .btn-sec-df:hover { border-color: var(--teal); }

  /* aviso de fim de execução */
  .toast-df { position: fixed; right: 18px; bottom: 18px; z-index: 1001; max-width: 360px; background: var(--bg);
              border: 1px solid var(--border); border-left: 4px solid var(--ok); border-radius: 10px; padding: 12px 14px;
              font-size: 13px; color: var(--fg); box-shadow: 0 10px 30px rgba(0,0,0,.35);
              transform: translateY(20px); opacity: 0; pointer-events: none; transition: all .25s; }
  .toast-df.visivel { transform: none; opacity: 1; pointer-events: auto; }
  .toast-df.com-erro { border-left-color: var(--erro); }
  .toast-df .sub { font-size: 11.5px; color: var(--fg-dim); margin-top: 3px; }

  @media (max-width: 600px) {
    .acoes-df { align-items: stretch; width: 100%; }
    #df-botao-executar { width: 100%; }
    .dica-botao-df { text-align: left; max-width: none; }
    .resumo-df { grid-template-columns: 1fr 1fr; gap: 10px; }
    .tile-df .valor { font-size: 20px; }
  }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-df">
      <div>
        <h1>Atualização Dash Financeiro</h1>
        <div class="sub">
          Contagem mensal de documentos por cliente pro Power BI, um arquivo por mês
          (<code>AAAA-MM.csv</code>) em <code>C:\\Empresa\\Power BI\\Financeiro\\&lt;Produto&gt;\\</code>.
          "Executar" gera só o que falta do mês de referência; "Gerar de novo" refaz um produto.
        </div>
      </div>
      <div class="acoes-df">
        <div class="seletor-mes-df">
          <label for="df-mes">Mês</label>
          <button class="passo-mes" id="df-mes-anterior" onclick="andarMesDf(-1)" title="Mês anterior" aria-label="Mês anterior">&#8249;</button>
          <input type="month" id="df-mes" onchange="mudarMesDf(this.value)">
          <button class="passo-mes" id="df-mes-seguinte" onclick="andarMesDf(1)" title="Mês seguinte" aria-label="Mês seguinte">&#8250;</button>
        </div>
        <button class="btn-accent" id="df-botao-executar" onclick="pedirExecucaoDf()" disabled>Carregando...</button>
        <div class="dica-botao-df" id="df-dica-executar"></div>
      </div>
    </div>

    <div class="erro-df" id="df-erro"></div>

    <div class="resumo-df" id="df-resumo"></div>
    <div class="linha-auto-df" id="df-auto"></div>

    <div class="painel-df" id="df-progresso">
      <div class="topo-progresso-df">
        <div class="titulo" id="df-progresso-titulo">Gerando...</div>
        <div class="tempo" id="df-progresso-tempo"></div>
      </div>
      <div class="barra-df"><div id="df-progresso-barra" style="width:0%"></div></div>
      <div class="passos-df" id="df-progresso-passos"></div>
      <div class="nota-progresso-df">Pode fechar esta página: a geração continua rodando no PDA. A tela atualiza sozinha.</div>
    </div>

    <div class="painel-df">
      <div class="topo-grade-df">
        <h2 style="margin:0">Produtos</h2>
        <div class="filtros-df" id="df-filtros"></div>
      </div>
      <div class="grade-produtos-df" id="df-grade-produtos">
        <div class="vazio-grade-df">Carregando...</div>
      </div>
    </div>

    <div class="painel-df" id="df-painel-teste">
      <div class="cabecalho-teste-df">
        <div>
          <h2 id="df-titulo-teste">Teste de conexões</h2>
          <div class="sub-painel" style="margin-bottom:0">Roda a mesma consulta da geração em cada cliente, sem gravar arquivo nenhum.</div>
        </div>
        <button class="btn-fechar-df" onclick="fecharTesteDf()" title="Fechar" aria-label="Fechar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
        </button>
      </div>
      <div class="status-teste-df" id="df-status-teste"></div>
      <div class="rolagem-df" id="df-resultado-teste"></div>

      <h2 style="margin-top:22px">Procurar empresa nas bases</h2>
      <div class="sub-painel" style="margin-bottom:0">Procura pelo nome ou CNPJ nas tabelas de empresas e grupos de cada base desse produto
        (ex.: achar em qual base e em qual grupo a ClienteA está).</div>
      <div class="busca-df">
        <input type="text" id="df-termo-busca" maxlength="60" placeholder="ex.: ClienteA"
               onkeydown="if (event.key === 'Enter') procurarEmpresaDf()">
        <button class="btn-accent" id="df-botao-busca" onclick="procurarEmpresaDf()">Procurar</button>
      </div>
      <div class="status-teste-df" id="df-status-busca"></div>
      <div id="df-resultado-busca"></div>
    </div>

    <details class="painel-df log-df" id="df-log" style="display:none" ontoggle="if (this.open) carregarLogDf()">
      <summary><h2>Log da atualização</h2><span class="seta">&#9654;</span></summary>
      <pre id="df-log-conteudo">Carregando...</pre>
    </details>
  </div>

  <div class="veu-df" id="df-veu" onclick="if (event.target === this) fecharModalDf(false)">
    <div class="modal-df" role="dialog" aria-modal="true">
      <h3 id="df-modal-titulo"></h3>
      <div class="corpo" id="df-modal-corpo"></div>
      <div class="botoes-modal-df">
        <button class="btn-sec-df" onclick="fecharModalDf(false)">Cancelar</button>
        <button class="btn-accent" id="df-modal-ok" onclick="fecharModalDf(true)">Confirmar</button>
      </div>
    </div>
  </div>

  <div class="toast-df" id="df-toast" onclick="this.classList.remove('visivel')"></div>

  __FOOTER__

<script>
const PODE_VER_LOG_DF = __PODE_VER_LOG_DF__;
let dadosDf = null;            // última resposta do /status
let mesEscolhidoDf = '';       // "AAAA-MM" escolhido na tela; vazio = mês anterior (o padrão do servidor)
let filtroDf = 'todos';
let diferencaRelogioDf = 0;    // relógio do servidor - relógio do navegador (s), pros cronômetros
let rodadaAnteriorDf = null;   // produtos da rodada que estava rodando no último status
const clientesAbertosDf = new Set();
const ESTADOS_DF = {
  ok: { rotulo: 'Gerado', classe: 'badge-ok' },
  aviso: { rotulo: 'Gerado com aviso', classe: 'badge-aviso' },
  erro: { rotulo: 'Erro', classe: 'badge-erro' },
  pendente: { rotulo: 'Pendente', classe: 'badge-pendente' },
  rodando: { rotulo: 'Gerando', classe: 'badge-rodando' },
  fila: { rotulo: 'Na fila', classe: 'badge-fila' },
};

function escaparHtmlDf(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

function formatarMesDf(aaaaMm) {
  // "2026-08" -> "08/2026"
  const partes = String(aaaaMm || '').split('-');
  return partes.length === 2 ? partes[1] + '/' + partes[0] : aaaaMm;
}

function formatarDataDf(aaaaMmDd) {
  const p = String(aaaaMmDd || '').split('-');
  return p.length === 3 ? p[2] + '/' + p[1] : aaaaMmDd;
}

function formatarDuracaoDf(segundos) {
  segundos = Math.max(0, Math.round(segundos || 0));
  const h = Math.floor(segundos / 3600), m = Math.floor((segundos % 3600) / 60), s = segundos % 60;
  if (h) return h + 'h ' + String(m).padStart(2, '0') + 'min';
  if (m) return m + 'min ' + String(s).padStart(2, '0') + 's';
  return s + 's';
}

function formatarTamanhoDf(bytes) {
  if (bytes == null) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' KB';
  return (bytes / 1048576).toLocaleString('pt-BR', { maximumFractionDigits: 1 }) + ' MB';
}

function numeroDf(n) { return Number(n || 0).toLocaleString('pt-BR'); }

function agoraServidorDf() { return Date.now() / 1000 + diferencaRelogioDf; }

// Estado de um produto olhando primeiro o que está rodando, depois o erro da
// última geração e, por fim, se o arquivo do mês de referência existe em disco
function estadoProdutoDf(produto) {
  const st = (dadosDf.status || {})[produto];
  const info = (dadosDf.detalhes || {})[produto] || { meses: [] };
  const prog = dadosDf.progresso || {};
  if (st && st.rodando) return 'rodando';
  if (dadosDf.execucao_ativa && prog.mes === dadosDf.mes_referencia && (prog.produtos || []).includes(produto) && !(prog.concluidos || []).includes(produto)) return 'fila';
  if (st && st.ok === false) return 'erro';
  if ((info.meses || []).includes(dadosDf.mes_referencia)) {
    return problemasDf(st).length ? 'aviso' : 'ok';
  }
  return 'pendente';
}

function problemasDf(st) {
  return ((st && st.por_conexao) || []).filter(c => c.erro || !c.linhas);
}

function pendentesDf() {
  return dadosDf.ordem.filter(p => !((dadosDf.detalhes[p] || {}).meses || []).includes(dadosDf.mes_referencia));
}

function badgeDf(estado) {
  const e = ESTADOS_DF[estado];
  const giro = estado === 'rodando' ? '<span class="giro-df"></span>' : '';
  return `<span class="badge-status-df ${e.classe}">${giro}${e.rotulo}</span>`;
}

function montarResumoDf() {
  const ordem = dadosDf.ordem;
  const estados = ordem.map(estadoProdutoDf);
  const gerados = ordem.length - pendentesDf().length;
  const pendentes = ordem.length - gerados;
  const problemas = estados.filter(e => e === 'erro' || e === 'aviso').length;
  const per = dadosDf.periodo || {};
  const tiles = [
    { rotulo: 'Mês escolhido', valor: formatarMesDf(dadosDf.mes_referencia) + (mesForaDoPadraoDf() ? '<span class="etq-mes">outro mês</span>' : ''),
      extra: `de ${formatarDataDf(per.ini)} a ${formatarDataDf(per.fim)}` + (mesForaDoPadraoDf()
        ? ` · <button class="voltar-mes-df" onclick="event.stopPropagation(); mudarMesDf('')">voltar pro ${formatarMesDf(dadosDf.mes_padrao)}</button>` : ''),
      cor: mesForaDoPadraoDf() ? 'var(--ambar-df)' : 'var(--teal)' },
    { rotulo: 'Gerados', valor: `${gerados}<small> / ${ordem.length}</small>`, extra: pendentes ? 'produtos com o arquivo do mês' : 'tudo em dia', cor: 'var(--ok)', filtro: 'todos' },
    { rotulo: 'Pendentes', valor: pendentes, extra: pendentes ? 'ainda sem o arquivo do mês' : 'nada faltando', cor: pendentes ? '#e8a33d' : 'var(--ok)', filtro: 'pendentes' },
    { rotulo: 'Com problema', valor: problemas, extra: problemas ? 'erro ou cliente de fora' : 'nenhum na última geração', cor: problemas ? 'var(--erro)' : 'var(--ok)', filtro: 'problemas' },
  ];
  document.getElementById('df-resumo').innerHTML = tiles.map(t => `
    <div class="tile-df${t.filtro ? ' clicavel' : ''}" style="--cor-tile:${t.cor}" ${t.filtro ? `onclick="mudarFiltroDf('${t.filtro}')"` : ''}>
      <div class="rotulo">${t.rotulo}</div>
      <div class="valor">${t.valor}</div>
      <div class="extra">${t.extra}</div>
    </div>`).join('');
  const auto = dadosDf.automatico || {};
  document.getElementById('df-auto').innerHTML = auto.proximo
    ? `<span class="ponto"></span> Geração automática todo dia 1 às ${escaparHtmlDf(auto.horario)} · próxima em ${escaparHtmlDf(auto.proximo)}`
    : '';
}

function montarBotaoExecutarDf() {
  const botao = document.getElementById('df-botao-executar');
  const dica = document.getElementById('df-dica-executar');
  const pendentes = pendentesDf();
  const mes = formatarMesDf(dadosDf.mes_referencia);
  if (dadosDf.execucao_ativa) {
    const prog = dadosDf.progresso || {};
    botao.disabled = true;
    botao.innerHTML = `<span class="giro-df" style="margin-right:6px;vertical-align:-1px"></span>Gerando ${(prog.concluidos || []).length}/${(prog.produtos || []).length || '?'}`;
    dica.innerText = 'Aguarde terminar pra disparar outra geração.';
  } else if (!pendentes.length) {
    botao.disabled = true;
    botao.innerText = `Tudo gerado · ${mes}`;
    dica.innerText = 'Pra refazer um produto, use "Gerar de novo" no card dele.';
  } else {
    botao.disabled = false;
    botao.innerText = `Gerar ${mes} · ${pendentes.length} pendente${pendentes.length > 1 ? 's' : ''}`;
    dica.innerText = pendentes.join(' · ');
  }
}

function montarProgressoDf() {
  const painel = document.getElementById('df-progresso');
  const prog = dadosDf.progresso || {};
  if (!dadosDf.execucao_ativa || !(prog.produtos || []).length) { painel.style.display = 'none'; return; }
  painel.style.display = 'block';
  const total = prog.produtos.length, feitos = prog.concluidos.length;
  const atual = prog.produtos.find(p => !prog.concluidos.includes(p));
  document.getElementById('df-progresso-titulo').innerText = atual
    ? `Gerando ${atual} · ${formatarMesDf(prog.mes)} · ${Math.min(feitos + 1, total)} de ${total}` : `Finalizando ${formatarMesDf(prog.mes)} · ${feitos} de ${total}`;
  document.getElementById('df-progresso-barra').style.width = Math.round(feitos / total * 100) + '%';
  document.getElementById('df-progresso-passos').innerHTML = prog.produtos.map(p => {
    if (prog.concluidos.includes(p)) {
      const falhou = prog.mes === dadosDf.mes_referencia && ((dadosDf.status || {})[p] || {}).ok === false;
      return `<span class="passo-df ${falhou ? 'falhou' : 'feito'}">${falhou ? '&#10007;' : '&#10003;'} ${escaparHtmlDf(p)}</span>`;
    }
    if (p === atual) return `<span class="passo-df agora"><span class="giro-df"></span>${escaparHtmlDf(p)}</span>`;
    return `<span class="passo-df">${escaparHtmlDf(p)}</span>`;
  }).join('');
  atualizarCronometrosDf();
}

function atualizarCronometrosDf() {
  if (!dadosDf) return;
  const prog = dadosDf.progresso || {};
  const tempoEl = document.getElementById('df-progresso-tempo');
  if (dadosDf.execucao_ativa && prog.inicio) {
    tempoEl.innerText = formatarDuracaoDf(agoraServidorDf() - prog.inicio) + ' decorridos';
  }
  document.querySelectorAll('[data-desde]').forEach(el => {
    el.innerText = formatarDuracaoDf(agoraServidorDf() - Number(el.dataset.desde));
  });
}

function somarMesesDf(aaaaMm, n) {
  const [ano, mes] = aaaaMm.split('-').map(Number);
  const d = new Date(ano, mes - 1 + n, 1);
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
}

function linhaDoTempoDf(meses) {
  const padrao = dadosDf.mes_padrao || dadosDf.mes_referencia;
  const fim = dadosDf.mes_referencia >= somarMesesDf(padrao, -11) ? padrao : dadosDf.mes_referencia;
  const lista = [];
  for (let i = 11; i >= 0; i--) lista.push(somarMesesDf(fim, -i));
  const conjunto = new Set(meses || []);
  const quadros = lista.map(m => {
    const classes = ['mes-df'];
    if (conjunto.has(m)) classes.push('tem');
    if (m === dadosDf.mes_referencia) classes.push('ref');
    const titulo = formatarMesDf(m) + (conjunto.has(m) ? ' · gerado' : ' · sem arquivo') + ' · clique pra escolher esse mês';
    return `<button type="button" class="${classes.join(' ')}" title="${titulo}" onclick="mudarMesDf('${m}')"></button>`;
  }).join('');
  return `<div class="linha-tempo-df">${quadros}</div>
    <div class="eixo-tempo-df"><span>${formatarMesDf(lista[0])}</span><span>${formatarMesDf(lista[11])}</span></div>`;
}

function cartaoProdutoDf(produto) {
  const estado = estadoProdutoDf(produto);
  const st = (dadosDf.status || {})[produto] || null;
  const info = (dadosDf.detalhes || {})[produto] || { clientes: [], meses: [] };
  const mesRef = formatarMesDf(dadosDf.mes_referencia);
  const prodHtml = escaparHtmlDf(produto);
  const partes = [];

  // arquivo do mês de referência
  if (estado === 'rodando') {
    const desde = ((dadosDf.progresso || {}).inicio_produto || {})[produto];
    partes.push(`<div class="arquivo-mes-df"><span class="mes">${mesRef}</span>
      <span class="dim">consultando os bancos${desde ? ` · há <span data-desde="${desde}"></span>` : ''}</span></div>`);
  } else if (info.arquivo_mes) {
    partes.push(`<div class="arquivo-mes-df"><span class="mes">${mesRef}</span>
      <span class="dim">gerado em ${escaparHtmlDf(info.arquivo_mes.modificado)} · ${formatarTamanhoDf(info.arquivo_mes.tamanho)}</span></div>`);
  } else {
    partes.push(`<div class="arquivo-mes-df"><span class="mes">${mesRef}</span><span class="dim">ainda não gerado</span></div>`);
  }

  // última geração feita nesta sessão do PDA (o "pulado" só diz que o arquivo já existia)
  if (st && !st.rodando && st.ok === false) {
    partes.push(`<div class="erro-cartao-df">${escaparHtmlDf(st.erro || 'Erro desconhecido')}${st.executado_em ? ' · ' + escaparHtmlDf(st.executado_em) : ''}</div>`);
  } else if (st && !st.rodando && st.ok && !st.pulado) {
    const docs = (st.por_conexao || []).reduce((n, c) => n + (c.documentos || 0), 0);
    const pedacos = [`<b>${numeroDf(st.linhas)}</b> linha(s)`];
    if (docs) pedacos.push(`<b>${numeroDf(docs)}</b> documento(s)`);
    if (st.duracao_s != null) pedacos.push('levou ' + formatarDuracaoDf(st.duracao_s));
    partes.push(`<div class="ultima-df">Última geração: ${pedacos.join(' · ')}</div>`);
  }

  // clientes: barra de quem trouxe dados, veio vazio ou falhou
  const porConexao = (st && st.por_conexao) || [];
  if (porConexao.length) {
    const nOk = porConexao.filter(c => !c.erro && c.linhas).length;
    const nVazio = porConexao.filter(c => !c.erro && !c.linhas).length;
    const nErro = porConexao.filter(c => c.erro).length;
    const pct = n => (n / porConexao.length * 100) + '%';
    partes.push(`<div class="barra-clientes-df" title="${nOk} com dados · ${nVazio} sem documentos · ${nErro} com erro">
        <span class="s-ok" style="width:${pct(nOk)}"></span><span class="s-vazio" style="width:${pct(nVazio)}"></span><span class="s-erro" style="width:${pct(nErro)}"></span>
      </div>
      <div class="legenda-clientes-df"><span><i style="background:var(--ok)"></i>${nOk} com dados</span>
        ${nVazio ? `<span><i style="background:#e8a33d"></i>${nVazio} sem documentos</span>` : ''}
        ${nErro ? `<span><i style="background:var(--erro)"></i>${nErro} com erro</span>` : ''}</div>`);
    const problemas = problemasDf(st);
    if (problemas.length) {
      partes.push('<div class="problemas-df">' + problemas.map(c => c.erro
        ? `<div class="problema-df erro"><b>${escaparHtmlDf(c.cliente)}</b> ficou de fora: ${escaparHtmlDf(c.erro)}</div>`
        : `<div class="problema-df vazio"><b>${escaparHtmlDf(c.cliente)}</b> conectou, mas não trouxe nenhum documento no mês</div>`
      ).join('') + '</div>');
    }
  }

  // chips dos clientes cadastrados (recolhidos depois de 8)
  const situacao = {};
  porConexao.forEach(c => { situacao[c.cliente] = c.erro ? 'erro' : (c.linhas ? '' : 'vazio'); });
  const aberto = clientesAbertosDf.has(produto);
  const visiveis = aberto ? info.clientes : info.clientes.slice(0, 8);
  let chips = visiveis.map(c => `<span class="chip-cliente-df ${situacao[c] || ''}">${escaparHtmlDf(c)}</span>`).join('');
  if (info.clientes.length > 8) {
    chips += `<button class="chip-mais-df" data-produto="${prodHtml}" onclick="alternarClientesDf(this.dataset.produto)">${aberto ? 'mostrar menos' : '+' + (info.clientes.length - 8)}</button>`;
  }
  partes.push(`<div class="rotulo-secao-df"><span>Clientes</span><span>${info.clientes.length}</span></div>
    <div class="chips-clientes-df">${chips || '<span class="texto-dim-df">nenhum cadastrado</span>'}</div>`);

  partes.push(`<div class="rotulo-secao-df"><span>Últimos 12 meses</span><span>${info.meses.length} arquivo(s) no total</span></div>${linhaDoTempoDf(info.meses)}`);
  if (info.consolidado_antigo) {
    partes.push('<div class="aviso-consolidado-df">df_consolidado.csv antigo ainda na pasta · não é mais atualizado</div>');
  }

  const bloqueado = dadosDf.execucao_ativa ? 'disabled' : '';
  const rotuloGerar = info.arquivo_mes ? 'Gerar de novo' : `Gerar ${mesRef}`;
  const testavel = (dadosDf.testaveis || []).includes(produto);
  partes.push(`<div class="acoes-cartao-df">
      <button class="btn-cartao-df ${info.arquivo_mes ? '' : 'principal'}" ${bloqueado} data-produto="${prodHtml}" onclick="pedirGerarDeNovoDf(this.dataset.produto)">${rotuloGerar}</button>
      ${testavel ? `<button class="btn-cartao-df" data-produto="${prodHtml}" onclick="testarConexoesDf(this.dataset.produto)">Testar conexões</button>` : ''}
    </div>`);

  return `<div class="cartao-produto-df estado-${estado}">
      <div class="topo-cartao-df"><span class="nome-produto">${prodHtml}</span>${badgeDf(estado)}</div>
      ${partes.join('')}
    </div>`;
}

// "Pendentes" = sem o arquivo do mês (mesma conta do quadro do topo), rodando ou não
function passaNoFiltroDf(produto) {
  if (filtroDf === 'pendentes') return pendentesDf().includes(produto);
  if (filtroDf === 'problemas') return ['erro', 'aviso'].includes(estadoProdutoDf(produto));
  return true;
}

function montarGradeDf() {
  const contagem = { todos: dadosDf.ordem.length, pendentes: pendentesDf().length, problemas: 0 };
  dadosDf.ordem.forEach(p => {
    if (['erro', 'aviso'].includes(estadoProdutoDf(p))) contagem.problemas++;
  });
  const rotulos = { todos: 'Todos', pendentes: 'Pendentes', problemas: 'Com problema' };
  document.getElementById('df-filtros').innerHTML = Object.keys(rotulos).map(f =>
    `<button class="filtro-df ${filtroDf === f ? 'ativo' : ''}" onclick="mudarFiltroDf('${f}')">${rotulos[f]}<span class="n">${contagem[f]}</span></button>`
  ).join('');
  const lista = dadosDf.ordem.filter(passaNoFiltroDf);
  const vazio = { pendentes: 'Nenhum produto pendente no mês de referência.', problemas: 'Nenhum produto com problema na última geração.' };
  document.getElementById('df-grade-produtos').innerHTML = lista.length
    ? lista.map(cartaoProdutoDf).join('')
    : `<div class="vazio-grade-df">${vazio[filtroDf] || 'Nada por aqui.'}</div>`;
}

function mudarFiltroDf(f) { filtroDf = f; if (dadosDf) montarGradeDf(); }

function alternarClientesDf(produto) {
  if (clientesAbertosDf.has(produto)) clientesAbertosDf.delete(produto); else clientesAbertosDf.add(produto);
  montarGradeDf();
}

function mostrarToastDf(titulo, sub, comErro) {
  const el = document.getElementById('df-toast');
  el.className = 'toast-df visivel' + (comErro ? ' com-erro' : '');
  el.innerHTML = `<div><b>${escaparHtmlDf(titulo)}</b></div>${sub ? `<div class="sub">${escaparHtmlDf(sub)}</div>` : ''}`;
  clearTimeout(mostrarToastDf.t);
  mostrarToastDf.t = setTimeout(() => el.classList.remove('visivel'), 12000);
}

// quando uma rodada que estava rodando termina, avisa o resultado (e no título da aba)
function avisarFimDaRodadaDf() {
  const prog = dadosDf.progresso || {};
  if (dadosDf.execucao_ativa) { rodadaAnteriorDf = { produtos: (prog.produtos || []).slice(), mes: prog.mes }; return; }
  if (!rodadaAnteriorDf) return;
  const { produtos: rodada, mes: mesRodada } = rodadaAnteriorDf;
  rodadaAnteriorDf = null;
  if (mesRodada && mesRodada !== dadosDf.mes_referencia) {
    // a tela está em outro mês: o resultado detalhado fica no mês da rodada
    mostrarToastDf(`Geração de ${formatarMesDf(mesRodada)} terminou`, 'Escolha esse mês pra ver o resultado de cada produto.', false);
    return;
  }
  const falhas = rodada.filter(p => ((dadosDf.status || {})[p] || {}).ok === false);
  const avisos = rodada.filter(p => estadoProdutoDf(p) === 'aviso');
  const titulo = falhas.length ? `Geração terminou com ${falhas.length} erro(s)` : 'Geração terminou';
  const sub = falhas.length ? 'Com erro: ' + falhas.join(', ')
    : (avisos.length ? 'Cliente de fora em: ' + avisos.join(', ') : `${rodada.length} produto(s) processado(s) sem erro.`);
  mostrarToastDf(titulo, sub, falhas.length > 0);
  if (document.hidden) document.title = (falhas.length ? '(!) ' : '(ok) ') + 'Atualização Dash Financeiro';
  if (PODE_VER_LOG_DF && document.getElementById('df-log').open) carregarLogDf();
}

function mesForaDoPadraoDf() {
  return !!dadosDf && !!dadosDf.mes_padrao && dadosDf.mes_referencia !== dadosDf.mes_padrao;
}

function montarSeletorMesDf() {
  const campo = document.getElementById('df-mes');
  campo.min = dadosDf.mes_mais_antigo || '2020-01';
  campo.max = dadosDf.mes_padrao || dadosDf.mes_referencia;
  if (document.activeElement !== campo) campo.value = dadosDf.mes_referencia;
  document.getElementById('df-mes-anterior').disabled = dadosDf.mes_referencia <= campo.min;
  document.getElementById('df-mes-seguinte').disabled = dadosDf.mes_referencia >= campo.max;
}

// troca o mês da tela inteira: resumo, cards, botões, teste de conexões e linha do tempo
async function mudarMesDf(mes) {
  if (mes && dadosDf) {
    if (mes > dadosDf.mes_padrao) mes = dadosDf.mes_padrao;
    if (mes < (dadosDf.mes_mais_antigo || '2020-01')) mes = dadosDf.mes_mais_antigo || '2020-01';
  }
  mesEscolhidoDf = (dadosDf && mes === dadosDf.mes_padrao) ? '' : (mes || '');
  fecharTesteDf();
  await carregarStatusDashFinanceiro();
  agendarStatusDf();
}

function andarMesDf(n) {
  if (dadosDf) mudarMesDf(somarMesesDf(dadosDf.mes_referencia, n));
}

function corpoComMesDf(campos) {
  const corpo = new URLSearchParams(campos || {});
  if (mesEscolhidoDf) corpo.set('mes', mesEscolhidoDf);
  return corpo;
}

async function carregarStatusDashFinanceiro() {
  const erroEl = document.getElementById('df-erro');
  try {
    const resp = await fetch('/api/dash-financeiro/status' + (mesEscolhidoDf ? '?mes=' + encodeURIComponent(mesEscolhidoDf) : ''));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (resp.status === 403) { window.location.href = '/'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar o status.';
      if (resp.status === 400 && mesEscolhidoDf) { mesEscolhidoDf = ''; carregarStatusDashFinanceiro(); }  // mês inválido: volta pro padrão
      return;
    }
    erroEl.innerText = '';
    dadosDf = dados;
    montarSeletorMesDf();
    if (dados.agora) diferencaRelogioDf = dados.agora - Date.now() / 1000;
    montarResumoDf();
    montarBotaoExecutarDf();
    montarProgressoDf();
    montarGradeDf();
    avisarFimDaRodadaDf();
    if (PODE_VER_LOG_DF && dados.execucao_ativa && document.getElementById('df-log').open) carregarLogDf();
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
  }
}

// rodando: atualiza a cada 3 s; parado: a cada 20 s; aba escondida: a cada 60 s
let timerStatusDf = null;
function agendarStatusDf() {
  clearTimeout(timerStatusDf);
  const espera = document.hidden ? 60000 : (dadosDf && dadosDf.execucao_ativa ? 3000 : 20000);
  timerStatusDf = setTimeout(async () => { await carregarStatusDashFinanceiro(); agendarStatusDf(); }, espera);
}
document.addEventListener('visibilitychange', async () => {
  if (!document.hidden) {
    document.title = 'Atualização Dash Financeiro';
    await carregarStatusDashFinanceiro();
  }
  agendarStatusDf();
});

let respostaModalDf = null;
function confirmarDf(titulo, corpoHtml, textoBotao) {
  document.getElementById('df-modal-titulo').innerText = titulo;
  document.getElementById('df-modal-corpo').innerHTML = corpoHtml;
  document.getElementById('df-modal-ok').innerText = textoBotao;
  document.getElementById('df-veu').classList.add('aberto');
  document.getElementById('df-modal-ok').focus();
  return new Promise(resolve => { respostaModalDf = resolve; });
}
function fecharModalDf(ok) {
  document.getElementById('df-veu').classList.remove('aberto');
  if (respostaModalDf) { respostaModalDf(ok); respostaModalDf = null; }
}
document.addEventListener('keydown', e => {
  if (e.key === 'Escape' && document.getElementById('df-veu').classList.contains('aberto')) fecharModalDf(false);
});

async function postarDf(url, corpo) {
  const resp = await fetch(url, { method: 'POST', body: corpo });
  if (resp.status === 401) { window.location.href = '/login'; return null; }
  if (resp.status === 403) { window.location.href = '/'; return null; }
  return resp.json();
}

async function pedirExecucaoDf() {
  if (!dadosDf) return;
  const pendentes = pendentesDf();
  const mes = formatarMesDf(dadosDf.mes_referencia);
  const chips = pendentes.map(p => `<span class="chip-cliente-df">${escaparHtmlDf(p)}</span>`).join('');
  const ok = await confirmarDf(`Gerar ${mes}?`,
    `Vai gerar o arquivo de <b>${mes}</b> destes produtos:<div class="chips-clientes-df">${chips}</div>
     Os que já têm o arquivo do mês são pulados. Costuma levar alguns minutos por produto, e dá pra acompanhar aqui.`,
    'Gerar agora');
  if (!ok) return;
  const dados = await postarDf('/api/dash-financeiro/executar', corpoComMesDf());
  if (!dados) return;
  document.getElementById('df-erro').innerText = dados.ok ? '' : (dados.erro || 'Não foi possível iniciar.');
  await carregarStatusDashFinanceiro();
  agendarStatusDf();
}

async function pedirGerarDeNovoDf(produto) {
  if (!dadosDf) return;
  const info = (dadosDf.detalhes || {})[produto] || {};
  const mes = formatarMesDf(dadosDf.mes_referencia);
  const corpo = info.arquivo_mes
    ? `O arquivo <b>${escaparHtmlDf(dadosDf.mes_referencia)}.csv</b> do <b>${escaparHtmlDf(produto)}</b> (gerado em ${escaparHtmlDf(info.arquivo_mes.modificado)}) vai ser <b>substituído</b> por uma consulta nova. Use depois de incluir ou corrigir um cliente.`
    : `Vai gerar o arquivo de <b>${mes}</b> só do <b>${escaparHtmlDf(produto)}</b>.`;
  const ok = await confirmarDf(`${info.arquivo_mes ? 'Gerar de novo' : 'Gerar'} ${produto} · ${mes}?`, corpo,
    info.arquivo_mes ? 'Substituir arquivo' : 'Gerar');
  if (!ok) return;
  const dados = await postarDf('/api/dash-financeiro/gerar-de-novo', corpoComMesDf({ produto }));
  if (!dados) return;
  document.getElementById('df-erro').innerText = dados.ok ? '' : (dados.erro || 'Não foi possível iniciar.');
  await carregarStatusDashFinanceiro();
  agendarStatusDf();
}

async function carregarLogDf() {
  const pre = document.getElementById('df-log-conteudo');
  try {
    const resp = await fetch('/api/logs?card=' + encodeURIComponent('Atualização Dash Financeiro'));
    const dados = await resp.json();
    if (!dados.ok) { pre.innerText = dados.erro || 'Não foi possível ler o log.'; return; }
    const linhas = (dados.linhas || []).slice(-80).map(l => String(l).trimEnd());
    if (!linhas.length) { pre.innerText = dados.aviso || 'Ainda não há nada registrado nesse log.'; return; }
    const noFim = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 20;
    pre.innerHTML = linhas.map(l => {
      const classe = /ERROR|falhou|erro ao/i.test(l) ? 'l-erro' : (/WARNING|não trouxe/i.test(l) ? 'l-aviso' : '');
      return `<span class="${classe}">${escaparHtmlDf(l)}</span>`;
    }).join(String.fromCharCode(10));
    if (noFim) pre.scrollTop = pre.scrollHeight;
  } catch (e) {
    pre.innerText = 'Erro ao ler o log: ' + e;
  }
}

let produtoTesteDf = null;

function fecharTesteDf() {
  document.getElementById('df-painel-teste').style.display = 'none';
  produtoTesteDf = null;
}

async function testarConexoesDf(produto) {
  produtoTesteDf = produto;
  const painel = document.getElementById('df-painel-teste');
  painel.style.display = 'block';
  document.getElementById('df-titulo-teste').innerText = 'Teste de conexões · ' + produto + ' · ' + formatarMesDf(dadosDf ? dadosDf.mes_referencia : '');
  document.getElementById('df-resultado-busca').innerHTML = '';
  document.getElementById('df-status-busca').innerText = '';
  const statusEl = document.getElementById('df-status-teste');
  const resultadoEl = document.getElementById('df-resultado-teste');
  resultadoEl.innerHTML = '';
  statusEl.innerHTML = '<span class="giro-df"></span>Testando cada cliente do ' + escaparHtmlDf(produto) + '... pode levar alguns minutos (consulta o mês inteiro).';
  painel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  try {
    const dados = await postarDf('/api/dash-financeiro/testar-conexoes', corpoComMesDf({ produto }));
    if (!dados) return;
    if (produtoTesteDf !== produto) return;  // clicou em outro produto enquanto esperava
    if (!dados.ok) { statusEl.innerText = dados.erro || 'Não foi possível testar.'; return; }
    const falhas = dados.conexoes.filter(c => c.erro).length;
    const vazios = dados.conexoes.filter(c => !c.erro && !c.linhas).length;
    statusEl.innerText = `${dados.conexoes.length} cliente(s) testado(s) no mês ${formatarMesDf(dados.mes)} · `
      + `${dados.conexoes.length - falhas - vazios} com dados · ${vazios} sem documentos · ${falhas} com erro`;
    resultadoEl.innerHTML = '<table class="tabela-df"><thead><tr><th>Cliente</th><th>Banco</th><th>Resultado</th></tr></thead><tbody>'
      + dados.conexoes.map(c => {
        const resultado = c.erro
          ? `<span class="resultado-erro">&#10007; ${escaparHtmlDf(c.erro)}</span>`
          : (c.linhas
            ? `<span class="resultado-ok">&#10003; ${numeroDf(c.documentos)} documento(s) em ${c.linhas} linha(s)</span>`
            : '<span class="resultado-vazio">&#9888; conectou, mas não trouxe nenhum documento no mês</span>');
        return `<tr><td>${escaparHtmlDf(c.cliente)}</td><td>${escaparHtmlDf(c.database)}</td><td>${resultado}</td></tr>`;
      }).join('') + '</tbody></table>';
  } catch (e) {
    statusEl.innerText = 'Erro ao testar: ' + e;
  }
}

async function procurarEmpresaDf() {
  if (!produtoTesteDf) return;
  const termo = document.getElementById('df-termo-busca').value.trim();
  const statusEl = document.getElementById('df-status-busca');
  const resultadoEl = document.getElementById('df-resultado-busca');
  const botao = document.getElementById('df-botao-busca');
  resultadoEl.innerHTML = '';
  statusEl.innerHTML = '<span class="giro-df"></span>Procurando "' + escaparHtmlDf(termo) + '" nas bases do ' + escaparHtmlDf(produtoTesteDf) + '...';
  botao.disabled = true;
  try {
    const dados = await postarDf('/api/dash-financeiro/procurar-empresa', new URLSearchParams({ produto: produtoTesteDf, termo }));
    if (!dados) return;
    if (!dados.ok) { statusEl.innerText = dados.erro || 'Não foi possível procurar.'; return; }
    const encontrados = dados.bases.reduce((n, b) => n + b.tabelas.reduce((m, t) => m + t.linhas.length, 0), 0);
    statusEl.innerText = `${encontrados} resultado(s) para "${dados.termo}" em ${dados.bases.length} base(s).`;
    resultadoEl.innerHTML = dados.bases.map(b => {
      const cabecalho = `<div class="titulo-base">${escaparHtmlDf(b.database)}</div>
        <div class="clientes-base">usada por: ${b.clientes.map(escaparHtmlDf).join(', ')}</div>`;
      if (b.erro) return `<div class="base-busca-df">${cabecalho}<div class="resultado-erro">&#10007; ${escaparHtmlDf(b.erro)}</div></div>`;
      const tabelas = b.tabelas.filter(t => t.linhas.length);
      if (!tabelas.length) return `<div class="base-busca-df">${cabecalho}<div class="clientes-base">nada encontrado</div></div>`;
      return `<div class="base-busca-df">${cabecalho}` + tabelas.map(t => `
        <div class="rolagem-df"><table class="tabela-df">
          <thead><tr><th colspan="${t.colunas.length}">${escaparHtmlDf(t.tabela)}</th></tr>
                 <tr>${t.colunas.map(c => `<th>${escaparHtmlDf(c)}</th>`).join('')}</tr></thead>
          <tbody>${t.linhas.map(l => `<tr>${l.map(v => `<td>${escaparHtmlDf(v)}</td>`).join('')}</tr>`).join('')}</tbody>
        </table></div>`).join('') + '</div>';
    }).join('');
  } catch (e) {
    statusEl.innerText = 'Erro ao procurar: ' + e;
  } finally {
    botao.disabled = false;
  }
}

if (PODE_VER_LOG_DF) document.getElementById('df-log').style.display = '';
setInterval(atualizarCronometrosDf, 1000);
carregarStatusDashFinanceiro().then(agendarStatusDf);
</script>
</body>
</html>
"""
