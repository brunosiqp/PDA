"""Tela Manutencao Usuarios.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
Redesenhada na 2.35.1.0: antes eram três abas separadas (Cadastrar, Desativar,
Editar). Agora a lista de pessoas é a tela, com números e filtros no topo;
clicar numa pessoa abre uma gaveta com abas (Dados, Acesso, Movidesk, Sistemas,
Desativar), e "Novo usuário"/"Desativar por login" abrem a gaveta do fluxo de
banco + Movidesk (prévia e confirmação). Mesmas rotas e mesmas regras de antes.
"""


_MANUTENCAO_USUARIOS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Manutenção de Usuários</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  :root { --ambar-mu: #e8a33d; }
  :root[data-tema="claro"] { --ambar-mu: #a8670a; }

  .cabecalho-mu { display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 14px;
                  max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .cabecalho-mu h1 { font-size: 20px; margin: 0 0 4px 0;
                      background: var(--gradiente-marca); -webkit-background-clip: text;
                      background-clip: text; color: transparent; }
  .cabecalho-mu .sub { color: var(--fg-dim); font-size: 12.5px; max-width: 560px; line-height: 1.5; }
  .acoes-topo-mu { display: flex; gap: 8px; flex-wrap: wrap; }
  .btn-sec-mu { background: rgba(var(--tinta),.04); border: 1px solid var(--border); color: var(--fg); border-radius: 9px;
                padding: 9px 14px; font-size: 12.5px; cursor: pointer; display: inline-flex; align-items: center; gap: 7px;
                font-family: inherit; white-space: nowrap; text-decoration: none; }
  .btn-sec-mu:hover:not(:disabled) { border-color: var(--teal); }
  .btn-sec-mu:disabled { opacity: .55; cursor: default; }
  .btn-sec-mu svg, .btn-accent svg { width: 15px; height: 15px; flex: none; }
  .btn-accent { display: inline-flex; align-items: center; justify-content: center; gap: 7px; }
  .btn-accent:disabled { opacity: .55; cursor: default; }
  .btn-perigo-mu { background: rgba(241,76,76,.10); border: 1px solid rgba(241,76,76,.45); color: var(--erro); border-radius: 9px;
                   padding: 9px 14px; font-size: 12.5px; cursor: pointer; font-weight: 700; font-family: inherit; }
  .btn-perigo-mu:hover:not(:disabled) { background: rgba(241,76,76,.18); }
  .btn-perigo-mu:disabled { opacity: .5; cursor: default; }

  .aviso-sync-mu { max-width: var(--largura-pagina); margin: -6px auto 16px auto; font-size: 12px; color: var(--fg-dim);
                   background: rgba(45,184,207,.07); border: 1px solid rgba(45,184,207,.25); border-radius: 10px; padding: 9px 14px;
                   display: flex; align-items: center; gap: 8px; line-height: 1.5; }
  .aviso-sync-mu:empty { display: none; }

  /* números do topo (clicáveis: aplicam o filtro) */
  .numeros-mu { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px;
                max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .numero-mu { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; padding: 13px 16px;
               cursor: pointer; text-align: left; font-family: inherit; color: var(--fg); position: relative; overflow: hidden;
               transition: border-color .15s, transform .15s; }
  .numero-mu::before { content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--cor-n, var(--teal)); }
  .numero-mu:hover { border-color: var(--cor-n, var(--teal)); transform: translateY(-1px); }
  .numero-mu.ativo { border-color: var(--cor-n, var(--teal)); background: rgba(45,184,207,.07); }
  .numero-mu .rotulo { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .06em; }
  .numero-mu .valor { font-size: 24px; font-weight: 800; margin-top: 3px; line-height: 1.1; }

  .painel-mu { background: var(--bg-panel); backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
               border: 1px solid var(--border); border-radius: 14px; padding: 18px 20px;
               max-width: var(--largura-pagina); margin: 0 auto 20px auto; }

  /* barra de busca e filtros */
  .barra-mu { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; margin-bottom: 14px; }
  .busca-mu { flex: 1 1 240px; position: relative; }
  .busca-mu svg { position: absolute; left: 11px; top: 50%; transform: translateY(-50%); width: 15px; height: 15px; color: var(--fg-dim); }
  .busca-mu input { width: 100%; padding: 9px 12px 9px 34px; border-radius: 9px; border: 1px solid var(--border);
                    background: rgba(var(--poco),.25); color: var(--fg); font-size: 13px; font-family: inherit; }
  .busca-mu input:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.14); }
  .segmento-mu { display: inline-flex; border: 1px solid var(--border); border-radius: 9px; overflow: hidden; }
  .segmento-mu button { background: none; border: none; color: var(--fg-dim); padding: 8px 12px; font-size: 12px; cursor: pointer; font-family: inherit; }
  .segmento-mu button + button { border-left: 1px solid var(--border); }
  .segmento-mu button:hover { color: var(--fg); }
  .segmento-mu button.ativo { background: rgba(45,184,207,.14); color: var(--fg); font-weight: 700; }

  /* lista de pessoas */
  .lista-mu { display: flex; flex-direction: column; }
  .pessoa-mu { display: grid; grid-template-columns: 40px minmax(0, 1.6fr) minmax(0, 1fr) minmax(0, 1.2fr) 150px 18px; gap: 14px;
               align-items: center; padding: 11px 12px; border-radius: 10px; cursor: pointer; border: 1px solid transparent;
               background: none; text-align: left; color: var(--fg); font-family: inherit; width: 100%; }
  .pessoa-mu + .pessoa-mu { border-top-color: rgba(var(--tinta),.05); }
  .pessoa-mu:hover, .pessoa-mu:focus-visible { background: rgba(45,184,207,.06); border-color: rgba(45,184,207,.25); outline: none; }
  .pessoa-mu.inativa { opacity: .55; }
  .pessoa-mu .nome { font-size: 13.5px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pessoa-mu .det { font-size: 11.5px; color: var(--fg-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }
  .pessoa-mu .col { font-size: 12px; min-width: 0; }
  .pessoa-mu .col .det { margin-top: 2px; }
  .pessoa-mu .seta { color: var(--fg-dim); font-size: 16px; }
  .etqs-mu { display: flex; gap: 5px; flex-wrap: wrap; justify-content: flex-end; }
  .etq-mu { font-size: 10.5px; font-weight: 700; padding: 3px 9px; border-radius: 999px; white-space: nowrap; letter-spacing: .02em; }
  .etq-mu.admin { background: rgba(176,203,28,.14); color: var(--lime); }
  .etq-mu.ativo { background: rgba(78,201,176,.14); color: var(--ok); }
  .etq-mu.inativo { background: rgba(241,76,76,.12); color: var(--erro); }
  .etq-mu.neutra { background: rgba(var(--tinta),.07); color: var(--fg-dim); }
  .vinculo-mu { display: inline-flex; align-items: center; gap: 5px; }
  .vinculo-mu .ponto { width: 7px; height: 7px; border-radius: 50%; background: var(--ok); flex: none; }
  .vinculo-mu.sem .ponto { background: var(--ambar-mu); }
  .vinculo-mu.sem { color: var(--ambar-mu); }
  .vazio-mu { color: var(--fg-dim); font-size: 12.5px; padding: 18px 6px; text-align: center; }

  .avatar-mu { width: 40px; height: 40px; border-radius: 50%; flex-shrink: 0; object-fit: cover; }
  .iniciais-mu { width: 40px; height: 40px; border-radius: 50%; background: var(--gradiente-marca); display: flex; align-items: center;
                 justify-content: center; font-weight: 800; color: #08090c; font-size: 14px; flex-shrink: 0; }
  .grande .avatar-mu, .grande .iniciais-mu { width: 56px; height: 56px; font-size: 18px; }

  /* gavetas */
  .fundo-mu { position: fixed; inset: 0; background: rgba(0,0,0,.55); backdrop-filter: blur(2px); z-index: 70;
              opacity: 0; pointer-events: none; transition: opacity .2s; }
  .fundo-mu.aberto { opacity: 1; pointer-events: auto; }
  .gaveta-mu { position: fixed; top: 0; right: 0; bottom: 0; width: min(680px, 100%); z-index: 71; display: flex; flex-direction: column;
               background: var(--bg-panel-solid); border-left: 1px solid var(--border-forte); box-shadow: -20px 0 50px rgba(0,0,0,.4);
               transform: translateX(100%); transition: transform .25s ease; }
  .gaveta-mu.aberta { transform: translateX(0); }
  .cab-gaveta-mu { padding: 18px 22px 0 22px; border-bottom: 1px solid var(--border); }
  .topo-cab-mu { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; padding-bottom: 14px; }
  .cab-gaveta-mu h2 { margin: 0; font-size: 17px; color: var(--fg); }
  .cab-gaveta-mu .sub { font-size: 12px; color: var(--fg-dim); margin-top: 3px; line-height: 1.5; }
  .pessoa-cab-mu { display: flex; gap: 14px; align-items: center; min-width: 0; }
  .pessoa-cab-mu .etqs-mu { justify-content: flex-start; margin-top: 6px; }
  .fechar-mu { background: none; border: 1px solid var(--border); color: var(--fg-dim); width: 32px; height: 32px; border-radius: 8px;
               cursor: pointer; flex-shrink: 0; display: grid; place-items: center; padding: 0; }
  .fechar-mu svg { width: 14px; height: 14px; display: block; }
  .fechar-mu:hover { color: var(--fg); border-color: var(--teal); }
  .abas-mu { display: flex; gap: 2px; overflow-x: auto; margin: 0 -4px; }
  .abas-mu button { background: none; border: none; border-bottom: 2px solid transparent; color: var(--fg-dim); padding: 10px 12px;
                    font-size: 12.5px; cursor: pointer; white-space: nowrap; font-family: inherit; }
  .abas-mu button:hover { color: var(--fg); }
  .abas-mu button.ativa { color: var(--fg); border-bottom-color: var(--teal); font-weight: 700; }
  .abas-mu button.perigo.ativa { border-bottom-color: var(--erro); color: var(--erro); }
  .corpo-gaveta-mu { flex: 1; overflow-y: auto; padding: 4px 22px 24px 22px; }
  .aba-mu { display: none; }
  .aba-mu.ativa { display: block; }
  .rodape-gaveta-mu { padding: 14px 22px; border-top: 1px solid var(--border); display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
  .rodape-gaveta-mu .espaco { flex: 1; }

  .secao-mu { padding-top: 18px; }
  .secao-mu + .secao-mu { margin-top: 6px; border-top: 1px dashed rgba(var(--tinta),.09); }
  .titulo-secao-mu { display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--fg); margin-bottom: 4px; }
  .titulo-secao-mu .num { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; font-size: 10.5px; font-weight: 800;
                          background: rgba(45,184,207,.15); color: var(--teal); flex-shrink: 0; }
  .ajuda-mu { font-size: 11.5px; color: var(--fg-dim); line-height: 1.5; margin: 2px 0 10px 0; }

  .campos-mu { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 14px; }
  .campos-mu.tres { grid-template-columns: 1fr 1fr 1fr; }
  .campos-mu .inteiro { grid-column: 1 / -1; }
  .rotulo-mu { display: block; font-size: 11px; color: var(--fg-dim); margin: 10px 0 5px 0; }
  .gaveta-mu input[type="text"], .gaveta-mu input[type="email"], .gaveta-mu input[type="time"], .gaveta-mu input[type="date"],
  .gaveta-mu input[type="password"], .gaveta-mu select {
    width: 100%; padding: 9px 11px; border-radius: 8px; border: 1px solid var(--border); background: rgba(var(--poco),.28);
    color: var(--fg); font-size: 13px; font-family: inherit; }
  .gaveta-mu input:focus, .gaveta-mu select:focus { outline: none; border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .acoes-secao-mu { display: flex; gap: 8px; align-items: center; margin-top: 14px; flex-wrap: wrap; }
  .erro-mu { color: var(--erro); font-size: 12px; }
  .status-mu { font-size: 12px; color: var(--fg-dim); }
  .status-mu.ok { color: var(--ok); }
  .erro-mu:empty, .status-mu:empty { display: none; }

  /* escolha em cartões (área, papel, equipe, status) */
  .opcoes-mu { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 8px; }
  .opcao-mu { text-align: left; background: rgba(var(--tinta),.03); border: 1px solid var(--border); border-radius: 10px;
              padding: 10px 12px; cursor: pointer; color: var(--fg); font-family: inherit; }
  .opcao-mu:hover { border-color: var(--teal); }
  .opcao-mu.ativa { border-color: var(--teal); background: rgba(45,184,207,.10); box-shadow: inset 0 0 0 1px var(--teal); }
  .opcao-mu .t { font-size: 12.5px; font-weight: 700; }
  .opcao-mu .d { font-size: 10.5px; color: var(--fg-dim); margin-top: 2px; line-height: 1.4; }

  /* interruptores (permissões, opções do cadastro) */
  .interruptor-mu { display: flex; align-items: flex-start; gap: 12px; padding: 11px 12px; border: 1px solid var(--border); border-radius: 10px;
                    cursor: pointer; background: rgba(var(--tinta),.02); }
  .interruptor-mu:hover { border-color: rgba(45,184,207,.45); }
  .interruptor-mu input { position: absolute; opacity: 0; pointer-events: none; }
  .interruptor-mu .trilho { width: 34px; height: 20px; border-radius: 999px; background: rgba(var(--tinta),.15); position: relative;
                            flex: none; margin-top: 1px; transition: background .15s; }
  .interruptor-mu .trilho::after { content: ''; position: absolute; top: 3px; left: 3px; width: 14px; height: 14px; border-radius: 50%;
                                   background: #fff; transition: transform .15s; box-shadow: 0 1px 3px rgba(0,0,0,.3); }
  .interruptor-mu input:checked + .trilho { background: var(--teal); }
  .interruptor-mu input:checked + .trilho::after { transform: translateX(14px); }
  .interruptor-mu input:focus-visible + .trilho { box-shadow: 0 0 0 3px rgba(45,184,207,.3); }
  .interruptor-mu.travado { cursor: default; opacity: .7; }
  .interruptor-mu .t { font-size: 12.5px; font-weight: 700; color: var(--fg); }
  .interruptor-mu .d { font-size: 11px; color: var(--fg-dim); margin-top: 2px; line-height: 1.4; }
  .interruptor-mu .nota { font-size: 10px; font-weight: 700; color: var(--ambar-mu); text-transform: uppercase; letter-spacing: .04em; margin-left: 6px; }
  .interruptor-mu.admin { border-color: rgba(176,203,28,.35); background: rgba(176,203,28,.05); }
  .grade-permissoes-mu { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }

  .dias-semana-mu { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 2px; }
  .dia-check-mu { display: flex; align-items: center; justify-content: center; min-width: 46px; font-size: 12px; color: var(--fg-dim);
                  border: 1px solid var(--border); border-radius: 8px; padding: 7px 9px; cursor: pointer; user-select: none; }
  .dia-check-mu input { position: absolute; opacity: 0; pointer-events: none; }
  .dia-check-mu:has(input:checked) { border-color: var(--teal); color: var(--fg); background: rgba(45,184,207,.12); font-weight: 700; }

  .caixa-aviso-mu { font-size: 12px; line-height: 1.55; border-radius: 10px; padding: 10px 14px; margin-top: 14px; }
  .caixa-aviso-mu.perigo { background: rgba(241,76,76,.07); border: 1px solid rgba(241,76,76,.3); color: var(--fg); }
  .caixa-aviso-mu.perigo b { color: var(--erro); }
  .caixa-aviso-mu.info { background: rgba(var(--tinta),.04); border: 1px solid var(--border); color: var(--fg-dim); }
  details.avancado-mu { margin-top: 18px; border: 1px solid rgba(241,76,76,.25); border-radius: 10px; padding: 0 14px; }
  details.avancado-mu summary { cursor: pointer; padding: 11px 0; font-size: 12.5px; font-weight: 700; color: var(--erro); }
  details.avancado-mu[open] { padding-bottom: 14px; }

  /* prévia/resultado e diagnóstico */
  table.tabela-mu { width: 100%; border-collapse: collapse; margin-top: 8px; }
  table.tabela-mu th, table.tabela-mu td { text-align: left; padding: 7px 8px; border-bottom: 1px solid rgba(var(--tinta),.07); font-size: 12px; vertical-align: top; }
  table.tabela-mu th { color: var(--fg-dim); font-weight: 600; font-size: 10.5px; text-transform: uppercase; letter-spacing: .04em; }
  .rolagem-mu { overflow-x: auto; }
  .badge-status-mu { display: inline-block; padding: 2px 9px; border-radius: 20px; font-size: 11px; font-weight: 600; white-space: nowrap; }
  .badge-status-mu.success { background: rgba(78,201,176,.15); color: var(--ok); }
  .badge-status-mu.skipped { background: rgba(220,220,170,.15); color: var(--run); }
  .badge-status-mu.error { background: rgba(241,76,76,.15); color: var(--erro); }
  .resumo-final-mu { margin-top: 12px; font-size: 12.5px; color: var(--fg-dim); }
  .resumo-final-mu b { color: var(--fg); }
  .linha-resumo-mu { display: flex; justify-content: space-between; gap: 12px; padding: 7px 0; font-size: 12.5px; border-bottom: 1px dashed var(--border); }
  .linha-resumo-mu span:first-child { color: var(--fg-dim); }
  .contagem-alvos-mu { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 4px; }
  .contagem-alvos-mu span { font-size: 11.5px; padding: 3px 10px; border-radius: 999px; background: rgba(45,184,207,.10); color: var(--fg); }
  .giro-mu { width: 12px; height: 12px; border-radius: 50%; border: 2px solid currentColor; border-right-color: transparent;
             display: inline-block; animation: giro-mu .8s linear infinite; flex: none; vertical-align: -2px; }
  @keyframes giro-mu { to { transform: rotate(360deg); } }

  /* modal de confirmação e toast */
  .veu-modal-mu { position: fixed; inset: 0; background: rgba(0,0,0,.55); display: none; align-items: center; justify-content: center;
                  z-index: 90; padding: 16px; }
  .veu-modal-mu.aberto { display: flex; }
  .modal-mu { background: var(--bg-panel-solid); border: 1px solid var(--border-forte); border-radius: 14px; max-width: 460px; width: 100%;
              padding: 22px; box-shadow: 0 20px 60px rgba(0,0,0,.45); }
  .modal-mu h3 { margin: 0 0 10px 0; font-size: 16px; color: var(--fg); }
  .modal-mu .corpo { font-size: 13px; color: var(--fg-dim); line-height: 1.55; }
  .modal-mu .corpo b { color: var(--fg); }
  .botoes-modal-mu { display: flex; justify-content: flex-end; gap: 8px; margin-top: 18px; }
  .toast-mu { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px); opacity: 0; z-index: 95;
              background: var(--bg-panel-solid); border: 1px solid var(--border-forte); color: var(--fg); padding: 10px 18px; border-radius: 10px;
              font-size: 13px; transition: opacity .2s, transform .2s; pointer-events: none; max-width: calc(100% - 32px); }
  .toast-mu.mostrar { opacity: 1; transform: translateX(-50%) translateY(0); }

  @media (max-width: 760px) {
    .pessoa-mu { grid-template-columns: 40px minmax(0, 1fr) auto; }
    .pessoa-mu .col, .pessoa-mu .seta { display: none; }
    .campos-mu, .campos-mu.tres, .grade-permissoes-mu { grid-template-columns: 1fr; }
    .acoes-topo-mu { width: 100%; }
    .acoes-topo-mu > * { flex: 1; justify-content: center; }
    .segmento-mu { flex: 1 1 100%; }
    .segmento-mu button { flex: 1; }
  }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="cabecalho-mu">
      <div>
        <h1>Manutenção de Usuários</h1>
        <div class="sub">Login no PDA, vínculo com o Movidesk e acesso nos bancos dos clientes. Clique em uma pessoa pra ver e editar tudo dela.</div>
      </div>
      <div class="acoes-topo-mu">
        <button class="btn-sec-mu" id="btn-atualizar-lista-movidesk-mu" onclick="atualizarListaMovideskMU()"
                title="Busca de verdade na API do Movidesk e sincroniza a tabela (insere, atualiza, reativa e inativa)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 1-15.5 6.2M3 12A9 9 0 0 1 18.5 5.8"/><path d="M21 4v5h-5M3 20v-5h5"/></svg>
          Sincronizar Movidesk
        </button>
        <button class="btn-sec-mu" onclick="abrirCadExcMU('exc')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M5.6 5.6l12.8 12.8"/></svg>
          Desativar por login
        </button>
        <button class="btn-accent" onclick="abrirCadExcMU('cad')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>
          Novo usuário
        </button>
      </div>
    </div>

    <div class="aviso-sync-mu" id="vinc-status-lista-mu"></div>

    <div class="numeros-mu" id="numeros-mu"></div>

    <div class="painel-mu">
      <div class="barra-mu">
        <div class="busca-mu">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>
          <input type="text" id="filtro-nome-mu" placeholder="Buscar por nome, login, cargo ou e-mail..." oninput="filtrarListaEditarMU()">
        </div>
        <div class="segmento-mu" id="filtro-equipe-mu"></div>
        <div class="segmento-mu" id="filtro-status-mu"></div>
      </div>
      <div class="lista-mu" id="corpo-lista-editar-mu"><div class="vazio-mu">Carregando...</div></div>
      <div class="status-mu" style="margin-top:10px; text-align:right"><span id="contagem-lista-mu">0</span> pessoa(s) na lista</div>
    </div>
  </div>

  <div class="fundo-mu" id="fundo-mu" onclick="fecharGavetasMU()"></div>

  <!-- Gaveta de uma pessoa: tudo dela em abas -->
  <aside class="gaveta-mu" id="gaveta-pessoa-mu" aria-hidden="true">
    <div class="cab-gaveta-mu">
      <div class="topo-cab-mu">
        <div class="pessoa-cab-mu grande" id="perfil-cabecalho-mu"></div>
        <div style="display:flex; gap:8px; align-items:center">
          <a class="btn-sec-mu" id="link-ver-perfil-mu" href="#" target="_blank" rel="noopener">Ver perfil</a>
          <button class="fechar-mu" onclick="fecharGavetasMU()" title="Fechar (Esc)" aria-label="Fechar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </button>
        </div>
      </div>
      <div class="abas-mu" id="abas-pessoa-mu">
        <button data-aba="dados" class="ativa" onclick="mudarAbaPessoaMU('dados')">Dados</button>
        <button data-aba="acesso" onclick="mudarAbaPessoaMU('acesso')">Acesso e senha</button>
        <button data-aba="movidesk" onclick="mudarAbaPessoaMU('movidesk')">Movidesk e escala</button>
        <button data-aba="sistemas" onclick="mudarAbaPessoaMU('sistemas')">Status nos sistemas</button>
        <button data-aba="desativar" class="perigo" onclick="mudarAbaPessoaMU('desativar'); atualizarSoPdaMU()">Desativar</button>
      </div>
    </div>

    <div class="corpo-gaveta-mu">
      <!-- Dados -->
      <div class="aba-mu ativa" data-aba="dados">
        <div class="secao-mu">
          <div class="titulo-secao-mu">Identificação</div>
          <div class="campos-mu">
            <div class="inteiro"><label class="rotulo-mu">Nome</label><input type="text" id="ed-nome" maxlength="60"></div>
            <div><label class="rotulo-mu">E-mail</label><input type="email" id="ed-email" placeholder="contato31@example.com"></div>
            <div><label class="rotulo-mu">Gênero <span title="Usado nos textos do painel (Bem-vindo/Bem-vinda)">&#9432;</span></label>
              <select id="ed-genero"><option value="">Não informado</option><option value="F">Feminino</option><option value="M">Masculino</option></select></div>
            <div><label class="rotulo-mu">Início na empresa (opcional)</label><input type="date" id="ed-data-inicio"></div>
          </div>
          <div class="ajuda-mu" style="margin-top:6px">A data de início dispara os e-mails automáticos de 45 e 90 dias de empresa.</div>
        </div>
        <div class="secao-mu">
          <div class="titulo-secao-mu">Equipe</div>
          <input type="hidden" id="ed-atribuicao">
          <div class="opcoes-mu" id="opcoes-atribuicao-mu"></div>
        </div>
        <div class="secao-mu">
          <div class="titulo-secao-mu">Papel e login no PDA</div>
          <input type="hidden" id="ed-papel"><input type="hidden" id="ed-status">
          <div class="opcoes-mu" id="opcoes-papel-mu"></div>
          <div class="opcoes-mu" id="opcoes-status-mu" style="margin-top:8px"></div>
          <div class="ajuda-mu" style="margin-top:8px">Mudar o papel só vale no próximo login da pessoa.</div>
        </div>
        <div class="acoes-secao-mu">
          <button class="btn-accent" id="btn-salvar-dados-mu" onclick="salvarDadosGeraisMU()">Salvar dados</button>
          <span class="erro-mu" id="ed-erro-geral-mu"></span><span class="status-mu ok" id="ed-status-geral-mu"></span>
        </div>

        <div class="secao-mu">
          <div class="titulo-secao-mu">E-mail de boas-vindas</div>
          <div class="ajuda-mu">Vai pro e-mail acima, com a senha ATUAL da pessoa no PDA, o link do painel e o aviso da VPN. Salve o e-mail antes, se acabou de preencher.</div>
          <div class="acoes-secao-mu" style="margin-top:4px">
            <button class="btn-sec-mu" onclick="enviarBoasVindasTesteMU()">&#9993; Enviar boas-vindas</button>
            <span class="erro-mu" id="ed-erro-boasvindas-mu"></span><span class="status-mu ok" id="ed-status-boasvindas-mu"></span>
          </div>
        </div>

        <details class="avancado-mu">
          <summary>Renomear login</summary>
          <div class="ajuda-mu">Troca o login em TUDO (permissões, feedbacks, histórico de carreira). A sessão aberta da pessoa é encerrada e ela entra com o login novo. Use pra igualar o usuário do PDA com o dos webmonitors.</div>
          <div style="display:flex; gap:8px; flex-wrap:wrap">
            <input type="text" id="ed-usuario-novo" placeholder="Novo login, ex.: ana.silva" style="flex:1; min-width:180px">
            <button class="btn-perigo-mu" onclick="renomearUsuarioMU()">Renomear</button>
          </div>
          <div style="margin-top:8px"><span class="erro-mu" id="ed-erro-renomear-mu"></span><span class="status-mu ok" id="ed-status-renomear-mu"></span></div>
        </details>
      </div>

      <!-- Acesso e senha -->
      <div class="aba-mu" data-aba="acesso">
        <div class="secao-mu">
          <div class="titulo-secao-mu">Permissões</div>
          <div class="ajuda-mu">Administrador libera sozinho as áreas comuns. As marcadas "à parte" precisam ser ligadas uma a uma, mesmo pra administrador.</div>
          <label class="interruptor-mu admin">
            <input type="checkbox" id="perm-admin" onchange="aoMarcarAdminMU()"><span class="trilho"></span>
            <span><span class="t">Administrador</span><span class="d" style="display:block">Vê e mexe em quase tudo do painel. Mesmo campo do Papel na aba Dados.</span></span>
          </label>
          <div class="grade-permissoes-mu" id="grade-permissoes-mu"></div>
          <div class="acoes-secao-mu">
            <button class="btn-accent" onclick="salvarPermissoesMU()">Salvar permissões</button>
            <span class="erro-mu" id="perm-erro-mu"></span><span class="status-mu ok" id="perm-status-mu"></span>
          </div>
        </div>
        <div class="secao-mu">
          <div class="titulo-secao-mu">Trocar senha do PDA</div>
          <div class="campos-mu">
            <div><label class="rotulo-mu">Nova senha</label><input type="password" id="ed-nova-senha" placeholder="mínimo 4 caracteres" autocomplete="new-password"></div>
            <div><label class="rotulo-mu">Confirmar</label><input type="password" id="ed-confirma-senha" autocomplete="new-password"></div>
          </div>
          <div class="acoes-secao-mu">
            <button class="btn-sec-mu" onclick="salvarSenhaEdicaoMU()">Trocar senha</button>
            <span class="erro-mu" id="ed-erro-senha-mu"></span><span class="status-mu ok" id="ed-status-senha-mu"></span>
          </div>
        </div>
      </div>

      <!-- Movidesk e escala -->
      <div class="aba-mu" data-aba="movidesk">
        <div class="secao-mu">
          <div class="titulo-secao-mu">Vínculo com o Movidesk</div>
          <div class="ajuda-mu">Liga este login a uma pessoa da tabela "usuarios" do Movidesk. Sem vínculo, a meta de horas não é calculada direito e o cargo não sincroniza.</div>
          <input type="text" id="vinc-busca-movidesk" placeholder="Filtrar a lista por nome ou cargo..." oninput="montarOpcoesMovideskMU()">
          <select id="vinc-select-movidesk" onchange="aoTrocarUsuarioVinculadoMU()" style="margin-top:8px">
            <option value="">Sem vínculo</option>
          </select>
        </div>
        <div id="vinc-campos-movidesk-mu" style="display:none">
          <div class="secao-mu">
            <div class="titulo-secao-mu">Dados de horas</div>
            <div class="ajuda-mu" id="aviso-servicos-mu" hidden>Equipe Serviços: não entra no cálculo de horas nem na escala do PDA (Horas Trabalhadas, perfil e números da equipe).</div>
            <div class="campos-mu">
              <div><label class="rotulo-mu">Cargo</label><input type="text" id="vinc-cargo"></div>
              <div><label class="rotulo-mu">E-mail no Movidesk</label><input type="email" id="vinc-email"></div>
            </div>
            <div class="campos-mu tres">
              <div><label class="rotulo-mu">Escala</label>
                <select id="vinc-escala">
                  <option value="">Sem escala definida</option><option value="5x2">5x2</option><option value="6x1">6x1</option>
                  <option value="12x36">12x36</option><option value="ESTAGIO">Estágio</option><option value="ESCALA_ARA">Escala ARA</option>
                </select></div>
              <div><label class="rotulo-mu">Hora início</label><input type="time" id="vinc-horainicio"></div>
              <div><label class="rotulo-mu">Hora fim</label><input type="time" id="vinc-horafim"></div>
            </div>
            <label class="rotulo-mu">Dias trabalhados</label>
            <div class="dias-semana-mu">
              <label class="dia-check-mu"><input type="checkbox" value="Monday">Seg</label>
              <label class="dia-check-mu"><input type="checkbox" value="Tuesday">Ter</label>
              <label class="dia-check-mu"><input type="checkbox" value="Wednesday">Qua</label>
              <label class="dia-check-mu"><input type="checkbox" value="Thursday">Qui</label>
              <label class="dia-check-mu"><input type="checkbox" value="Friday">Sex</label>
              <label class="dia-check-mu"><input type="checkbox" value="Saturday">Sáb</label>
              <label class="dia-check-mu"><input type="checkbox" value="Sunday">Dom</label>
            </div>
          </div>
        </div>
        <div class="acoes-secao-mu">
          <button class="btn-accent" onclick="salvarVinculoMovideskMU()">Salvar vínculo</button>
          <span class="erro-mu" id="vinc-erro-mu"></span><span class="status-mu ok" id="vinc-status-mu"></span>
        </div>
      </div>

      <!-- Status nos sistemas -->
      <div class="aba-mu" data-aba="sistemas">
        <div class="secao-mu">
          <div class="titulo-secao-mu">Onde essa pessoa existe</div>
          <div class="ajuda-mu">Só consulta, não grava nada: cruza o Movidesk com todos os bancos de cliente pelo login (normalmente o e-mail).</div>
          <div style="display:flex; gap:8px; flex-wrap:wrap">
            <input type="text" id="diag-login" placeholder="contato31@example.com" style="flex:1; min-width:200px"
                   onkeydown="if (event.key === 'Enter') verificarDiagnosticoMU()">
            <button class="btn-accent" id="btn-diag-verificar" onclick="verificarDiagnosticoMU()">Verificar</button>
          </div>
          <div style="margin-top:8px"><span class="erro-mu" id="diag-erro-mu"></span><span class="status-mu" id="diag-status-mu"></span></div>
          <div id="diag-resultado-mu" style="margin-top:10px"></div>
        </div>
      </div>

      <!-- Desativar -->
      <div class="aba-mu" data-aba="desativar">
        <div class="secao-mu">
          <div class="titulo-secao-mu" style="color:var(--erro)">Desativar em todos os sistemas</div>
          <div class="ajuda-mu">Desativa a pessoa no banco de cada cliente, no Movidesk e no login do PDA, com o mesmo fluxo de sempre: prévia dos alvos, confirmação e resultado alvo por alvo.</div>
          <div class="caixa-aviso-mu perigo"><b>Produção de verdade:</b> roda UPDATE nos bancos dos clientes e chama a API do Movidesk. Não dá pra desfazer automaticamente.</div>
          <div class="acoes-secao-mu">
            <button class="btn-perigo-mu" onclick="irParaDesativarComDadosMU()">Continuar pra desativação</button>
          </div>
        </div>
        <div class="secao-mu">
          <div class="titulo-secao-mu">Só no PDA</div>
          <div class="ajuda-mu" id="so-pda-texto-mu">Bloqueia só o login do PDA: não mexe nos bancos dos clientes nem no Movidesk. A pessoa sai na hora (as sessões abertas caem), sai dos Rankings e todo mundo é avisado no sininho. Dá pra reativar aqui mesmo.</div>
          <div class="acoes-secao-mu">
            <button class="btn-perigo-mu" id="btn-so-pda-mu" onclick="alternarSoPdaMU()">Desativar só no PDA</button>
          </div>
        </div>
      </div>
    </div>
  </aside>

  <!-- Gaveta de cadastro / desativação (banco + Movidesk + PDA) -->
  <aside class="gaveta-mu" id="gaveta-cadexc-mu" aria-hidden="true">
    <div class="cab-gaveta-mu">
      <div class="topo-cab-mu">
        <div>
          <h2 id="titulo-form-cadexc">Novo usuário</h2>
          <div class="sub" id="sub-form-cadexc"></div>
        </div>
        <button class="fechar-mu" onclick="fecharGavetasMU()" title="Fechar (Esc)" aria-label="Fechar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
        </button>
      </div>
    </div>
    <div class="corpo-gaveta-mu">
      <div class="caixa-aviso-mu perigo">
        <b>Atenção:</b> roda direto nos bancos de PRODUÇÃO dos clientes (INSERT/UPDATE de verdade) e na API do Movidesk.
        Gere a prévia, revise os alvos e só então confirme. Toda execução fica no log de auditoria (logs/manutencao_usuarios_*.jsonl).
      </div>

      <div class="secao-mu">
        <div class="titulo-secao-mu"><span class="num">1</span> Pessoa</div>
        <div class="campos-mu">
          <div><label class="rotulo-mu">Nome</label><input type="text" id="mu-nome" maxlength="40" placeholder="Ex.: Ana Silva" oninput="invalidarPreviaMU()"></div>
          <div><label class="rotulo-mu">Login (bancos e Movidesk)</label><input type="text" id="mu-login" maxlength="255" placeholder="contato31@example.com" oninput="invalidarPreviaMU()"></div>
        </div>
        <div class="ajuda-mu" id="mu-dica-senha" style="margin-top:8px">
          Senha inicial nos bancos e no Movidesk: '__SENHA_PADRAO__'. O perfil no Movidesk segue a área escolhida abaixo.
        </div>
      </div>

      <div class="secao-mu">
        <div class="titulo-secao-mu"><span class="num">2</span> Área <span class="ajuda-mu" style="margin:0 0 0 auto; font-weight:400">define em quais bancos roda</span></div>
        <div class="opcoes-mu" id="opcoes-area-mu">
          <button type="button" class="opcao-mu ativa" data-area="suporte" onclick="escolherAreaMU('suporte')"><div class="t">Suporte</div><div class="d">bancos do Suporte</div></button>
          <button type="button" class="opcao-mu" data-area="monitoramento" onclick="escolherAreaMU('monitoramento')"><div class="t">Monitoramento</div><div class="d">bancos do Monitoramento</div></button>
          <button type="button" class="opcao-mu" data-area="todos" onclick="escolherAreaMU('todos')"><div class="t">Todas</div><div class="d">os dois conjuntos</div></button>
        </div>
      </div>

      <div class="secao-mu">
        <div class="titulo-secao-mu"><span class="num">3</span> Login no PDA</div>
        <label class="interruptor-mu">
          <input type="checkbox" id="mu-incluir-pda" onchange="atualizarCamposCondicionaisMU(); invalidarPreviaMU()"><span class="trilho"></span>
          <span><span class="t" id="mu-texto-incluir-pda">Também criar o login no PDA</span>
            <span class="d" style="display:block" id="mu-dica-incluir-pda">Sem nenhuma permissão extra (nem admin). Ajuste depois na pessoa.</span></span>
        </label>
        <div id="mu-campos-pda" style="display:none">
          <div class="campos-mu">
            <div><label class="rotulo-mu">Usuário do PDA</label><input type="text" id="mu-usuario-pda" placeholder="Ex.: ana.silva" oninput="invalidarPreviaMU()"></div>
            <div id="mu-bloco-senha-pda"><label class="rotulo-mu">Senha do PDA</label><input type="text" id="mu-senha-pda" placeholder="mínimo 4 caracteres"></div>
            <div id="mu-bloco-genero-pda"><label class="rotulo-mu">Gênero</label>
              <select id="mu-genero-pda"><option value="">Não informado</option><option value="F">Feminino</option><option value="M">Masculino</option></select></div>
          </div>
        </div>
        <label class="interruptor-mu" id="mu-campo-boas-vindas" style="margin-top:8px">
          <input type="checkbox" id="mu-enviar-boas-vindas"><span class="trilho"></span>
          <span><span class="t">Enviar e-mail de boas-vindas</span>
            <span class="d" style="display:block">Pro endereço do Login, com o acesso, o link do PDA e o aviso da VPN.</span></span>
        </label>
      </div>

      <div class="secao-mu">
        <div class="titulo-secao-mu"><span class="num">4</span> <span id="mu-titulo-workspace">Prévia</span></div>
        <div id="mu-workspace"><div class="ajuda-mu">Preencha os dados e gere a prévia pra ver em quais bancos vai rodar.</div></div>
      </div>
    </div>
    <div class="rodape-gaveta-mu">
      <span class="erro-mu" id="mu-erro"></span>
      <span class="status-mu" id="mu-status"></span>
      <span class="espaco"></span>
      <button class="btn-sec-mu" id="btn-mu-previa" onclick="gerarPreviaManutencaoUsuarios()">Gerar prévia</button>
      <button class="btn-accent" id="btn-mu-executar" onclick="confirmarExecucaoManutencaoUsuarios()" disabled>Confirmar e executar</button>
    </div>
  </aside>

  <div class="veu-modal-mu" id="veu-modal-mu" onclick="if (event.target === this) fecharModalMU(false)">
    <div class="modal-mu" role="dialog" aria-modal="true">
      <h3 id="modal-titulo-mu"></h3>
      <div class="corpo" id="modal-corpo-mu"></div>
      <div class="botoes-modal-mu">
        <button class="btn-sec-mu" onclick="fecharModalMU(false)">Cancelar</button>
        <button class="btn-accent" id="modal-ok-mu" onclick="fecharModalMU(true)">Confirmar</button>
      </div>
    </div>
  </div>
  <div class="toast-mu" id="toast-mu"></div>

  __FOOTER__

<script>
let previaAlvosManutencaoUsuarios = [];
let usuariosCarregadosMU = [];
let usuariosMovideskCarregadosMU = [];
let usuarioAtualEditarMU = null;
let acaoCadExcMU = 'cad';
let areaMU = 'suporte';
const filtrosMU = { equipe: '', status: 'ativos', recorte: '' };
const CARIMBO_FOTOS_MU = Date.now();  // uma vez por carregamento: não rebaixa as fotos a cada tecla da busca

// -- Permissões especiais: mesmas rotas /api/usuarios/* de sempre ------------
const ENDPOINTS_PERMISSOES_MU = {
  pode_manutencao_alertas: '/api/usuarios/permissao-manutencao',
  pode_relatorios_cliente_a: '/api/usuarios/permissao-cliente_a',
  pode_dash_financeiro: '/api/usuarios/permissao-dash-financeiro',
  pode_manutencao_rejeicoes: '/api/usuarios/permissao-manutencao-rejeicoes',
  pode_manutencao_relatorios: '/api/usuarios/permissao-manutencao-relatorios',
  pode_dados_sensiveis: '/api/usuarios/permissao-string-connections',
  pode_manutencao_usuarios: '/api/usuarios/permissao-manutencao-usuarios',
  pode_feedbacks: '/api/usuarios/permissao-feedbacks',
  pode_ver_logs: '/api/usuarios/permissao-logs',
  pode_indicadores_mensais: '/api/usuarios/permissao-indicadores-mensais',
  pode_editar_central: '/api/usuarios/permissao-editar-central',
  pode_publicar_comunidade: '/api/usuarios/permissao-publicar-comunidade',
  pode_servicos_adm: '/api/usuarios/permissao-servicos-adm',
};
const PERMISSOES_NAO_AUTOMATICAS_MU = new Set(['pode_dados_sensiveis', 'pode_manutencao_usuarios', 'pode_feedbacks', 'pode_indicadores_mensais', 'pode_reprocessamento_cte2', 'pode_editar_central', 'pode_servicos_adm']);
const PERMISSOES_UI_MU = [
  { chave: 'pode_manutencao_alertas', t: 'Manutenção de Alertas', d: 'criar e editar alertas em banco' },
  { chave: 'pode_manutencao_rejeicoes', t: 'Manutenção de Rejeições', d: 'regras de rejeição em banco' },
  { chave: 'pode_manutencao_relatorios', t: 'Manutenção de Relatórios', d: 'relatórios em banco' },
  { chave: 'pode_relatorios_cliente_a', t: 'Relatórios ClienteA', d: 'gerar e enviar os relatórios' },
  { chave: 'pode_dash_financeiro', t: 'Dash Financeiro', d: 'gerar os arquivos do Power BI' },
  { chave: 'pode_ver_logs', t: 'Leitura de Logs', d: 'ver os logs das automações' },
  { chave: 'pode_publicar_comunidade', t: 'Publicar como importante', d: 'publicar na Comunidade todo mundo pode; esta marca o post como Importante (sininho pra todos e Teams)' },
  { chave: 'pode_dados_sensiveis', t: 'Dados Sensíveis', d: 'String Connections e criptografia', nota: 'à parte' },
  { chave: 'pode_feedbacks', t: 'Feedbacks e Alinhamentos', d: 'precisa de Administrador', nota: 'à parte' },
  { chave: 'pode_indicadores_mensais', t: 'Indicadores Mensais', d: 'precisa de Administrador', nota: 'à parte' },
  { chave: 'pode_editar_central', t: 'Editar a Central de Monitores', d: 'clientes, logos, monitores e infra · precisa de Administrador', nota: 'à parte' },
  { chave: 'pode_servicos_adm', t: 'Serviços ADM', d: "Calendário de GMUD's e Indicadores Serviços", nota: 'à parte' },
  { chave: 'pode_manutencao_usuarios', t: 'Manutenção de Usuários', d: 'esta tela · precisa de Administrador', nota: 'à parte' },
];
const EQUIPES_MU = [
  { valor: 'Suporte', t: 'Suporte', d: 'só Suporte' },
  { valor: 'Monitoramento', t: 'Monitoramento', d: 'só Monitoramento' },
  { valor: 'Suporte e Monitoramento', t: 'Suporte e Monitoramento', d: 'escala 12x36, entra nas duas' },
  { valor: 'Serviços', t: 'Serviços', d: 'à parte · fora do cálculo de horas e da escala' },
];

function escaparHtmlMU(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

function iniciaisMU(nome) {
  const partes = (nome || '?').trim().split(' ').filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function avatarMU(u) {
  if (u.tem_foto) {
    return `<img class="avatar-mu" loading="lazy" src="/foto-usuario/${encodeURIComponent(u.usuario)}?t=${CARIMBO_FOTOS_MU}" alt="">`;
  }
  return `<div class="iniciais-mu">${escaparHtmlMU(iniciaisMU(u.nome || u.usuario))}</div>`;
}

function mostrarToastMU(texto) {
  const el = document.getElementById('toast-mu');
  el.innerText = texto;
  el.classList.add('mostrar');
  clearTimeout(mostrarToastMU.t);
  mostrarToastMU.t = setTimeout(() => el.classList.remove('mostrar'), 3500);
}

let respostaModalMU = null;
function confirmarMU(titulo, corpoHtml, textoBotao) {
  document.getElementById('modal-titulo-mu').innerText = titulo;
  document.getElementById('modal-corpo-mu').innerHTML = corpoHtml;
  document.getElementById('modal-ok-mu').innerText = textoBotao || 'Confirmar';
  document.getElementById('veu-modal-mu').classList.add('aberto');
  document.getElementById('modal-ok-mu').focus();
  return new Promise(resolve => { respostaModalMU = resolve; });
}
function fecharModalMU(ok) {
  document.getElementById('veu-modal-mu').classList.remove('aberto');
  if (respostaModalMU) { respostaModalMU(ok); respostaModalMU = null; }
}

async function postarMU(url, corpo) {
  const resp = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: corpo });
  if (resp.status === 401) { window.location.href = '/login'; throw new Error('sessão expirada'); }
  return { resp, dados: await resp.json().catch(() => ({})) };
}

// -- Carga inicial ------------------------------------------------------------
async function carregarListasBaseMU() {
  try {
    const [respUsuarios, respMovidesk] = await Promise.all([fetch('/api/usuarios'), fetch('/api/usuarios-movidesk')]);
    if (respUsuarios.status === 401) { window.location.href = '/login'; return; }
    const dadosUsuarios = await respUsuarios.json();
    usuariosCarregadosMU = dadosUsuarios.usuarios || [];
    const dadosMovidesk = await respMovidesk.json().catch(() => ({}));
    if (dadosMovidesk.ok) usuariosMovideskCarregadosMU = dadosMovidesk.registros;
    montarOpcoesMovideskMU();
    filtrarListaEditarMU();
  } catch (e) {
    document.getElementById('corpo-lista-editar-mu').innerHTML = '<div class="vazio-mu">Não foi possível carregar os usuários: ' + escaparHtmlMU(e) + '</div>';
  }
}

async function recarregarUsuariosMU() {
  try {
    const dados = await (await fetch('/api/usuarios')).json();
    usuariosCarregadosMU = dados.usuarios || usuariosCarregadosMU;
    filtrarListaEditarMU();
  } catch (e) { /* a lista atualiza no próximo carregamento */ }
}

// -- Sincronizar com o Movidesk (não muda o vínculo de ninguém, só traz gente nova)
async function atualizarListaMovideskMU() {
  const statusEl = document.getElementById('vinc-status-lista-mu');
  const botao = document.getElementById('btn-atualizar-lista-movidesk-mu');
  if (botao) botao.disabled = true;
  statusEl.innerHTML = '<span class="giro-mu"></span> Sincronizando com a API do Movidesk (pode levar até 1 minuto)...';
  try {
    const { dados: sync } = await postarMU('/api/usuarios-movidesk/sincronizar', '');
    if (!sync.ok) { statusEl.innerText = sync.erro || 'Não foi possível sincronizar com o Movidesk.'; return; }
    const dados = await (await fetch('/api/usuarios-movidesk')).json();
    if (!dados.ok) { statusEl.innerText = dados.erro || 'Não foi possível atualizar a lista.'; return; }
    usuariosMovideskCarregadosMU = dados.registros;
    montarOpcoesMovideskMU();
    await recarregarUsuariosMU();  // cargo novo do Movidesk no cadastro do PDA (2.34.4.0)
    const textoCargos = sync.cargos_gravados === false
      ? ' Atenção: os cargos não foram gravados no PDA (veja o log).'
      : ` ${sync.cargos_pda || 0} cargo(s) atualizado(s) no PDA` +
        (sync.sem_vinculo_pda ? ` (${sync.sem_vinculo_pda} login(s) sem vínculo ficam sem cargo).` : '.');
    statusEl.innerText = `Sincronizado com o Movidesk: ${sync.novos} novo(s), ${sync.atualizados} atualizado(s), ` +
      `${sync.reativados} reativado(s), ${sync.inativados} inativado(s). ${usuariosMovideskCarregadosMU.length} pessoa(s) disponível(is).` + textoCargos;
  } catch (e) {
    statusEl.innerText = 'Erro ao sincronizar: ' + e;
  } finally {
    if (botao) botao.disabled = false;
  }
}

// -- Lista, números e filtros ------------------------------------------------
function pertenceAEquipeMU(atribuicao, equipeFiltro) {
  // mesma regra de _pertence_a_equipe() no backend: 12x36 entra nas duas
  if (!equipeFiltro) return true;
  const valor = atribuicao || 'Suporte';
  if (valor === 'Suporte e Monitoramento') return equipeFiltro !== 'Serviços';
  return valor === equipeFiltro;
}

function nomeVinculoMU(u) {
  if (!u.usuario_movidesk_id) return null;
  const m = usuariosMovideskCarregadosMU.find(x => String(x.id) === String(u.usuario_movidesk_id));
  return m ? m.nome : 'ID ' + u.usuario_movidesk_id;
}

function montarNumerosMU() {
  const todos = usuariosCarregadosMU;
  const ativos = todos.filter(u => u.ativo !== false);
  const numeros = [
    { id: 'ativos', rotulo: 'Ativos', valor: ativos.length, cor: 'var(--ok)', acao: () => { filtrosMU.status = 'ativos'; filtrosMU.recorte = ''; } },
    { id: 'admin', rotulo: 'Administradores', valor: ativos.filter(u => u.admin).length, cor: 'var(--lime)', acao: () => { filtrosMU.status = 'ativos'; filtrosMU.recorte = 'admin'; } },
    { id: 'semvinculo', rotulo: 'Sem vínculo Movidesk', valor: ativos.filter(u => !u.usuario_movidesk_id).length, cor: 'var(--ambar-mu)', acao: () => { filtrosMU.status = 'ativos'; filtrosMU.recorte = 'semvinculo'; } },
    { id: 'inativos', rotulo: 'Desativados', valor: todos.length - ativos.length, cor: 'var(--erro)', acao: () => { filtrosMU.status = 'inativos'; filtrosMU.recorte = ''; } },
  ];
  montarNumerosMU.acoes = Object.fromEntries(numeros.map(n => [n.id, n.acao]));
  const ativoAgora = filtrosMU.recorte || (filtrosMU.status === 'inativos' ? 'inativos' : (filtrosMU.status === 'ativos' ? 'ativos' : ''));
  document.getElementById('numeros-mu').innerHTML = numeros.map(n => `
    <button class="numero-mu ${n.id === ativoAgora ? 'ativo' : ''}" style="--cor-n:${n.cor}" onclick="aplicarNumeroMU('${n.id}')">
      <div class="rotulo">${n.rotulo}</div><div class="valor">${n.valor}</div>
    </button>`).join('');
}

function aplicarNumeroMU(id) {
  const ativoAgora = filtrosMU.recorte || (filtrosMU.status === 'inativos' ? 'inativos' : '');
  if (id !== 'ativos' && ativoAgora === id) { filtrosMU.status = 'ativos'; filtrosMU.recorte = ''; }  // clicar de novo tira o recorte
  else montarNumerosMU.acoes[id]();
  filtrarListaEditarMU();
}

function montarSegmentosMU() {
  const equipes = [['', 'Todas'], ['Suporte', 'Suporte'], ['Monitoramento', 'Monitoramento'], ['Serviços', 'Serviços']];
  document.getElementById('filtro-equipe-mu').innerHTML = equipes.map(([v, r]) =>
    `<button class="${filtrosMU.equipe === v ? 'ativo' : ''}" onclick="filtrosMU.equipe='${v}'; filtrarListaEditarMU()">${r}</button>`).join('');
  const status = [['ativos', 'Ativos'], ['inativos', 'Desativados'], ['', 'Todos']];
  document.getElementById('filtro-status-mu').innerHTML = status.map(([v, r]) =>
    `<button class="${filtrosMU.status === v ? 'ativo' : ''}" onclick="filtrosMU.status='${v}'; filtrosMU.recorte=''; filtrarListaEditarMU()">${r}</button>`).join('');
}

function filtrarListaEditarMU() {
  const termo = (document.getElementById('filtro-nome-mu').value || '').trim().toLowerCase();
  const filtrados = usuariosCarregadosMU.filter(u => {
    const ativo = u.ativo !== false;
    if (filtrosMU.status === 'ativos' && !ativo) return false;
    if (filtrosMU.status === 'inativos' && ativo) return false;
    if (filtrosMU.recorte === 'admin' && !u.admin) return false;
    if (filtrosMU.recorte === 'semvinculo' && u.usuario_movidesk_id) return false;
    if (!pertenceAEquipeMU(u.atribuicao, filtrosMU.equipe)) return false;
    if (!termo) return true;
    return [u.nome, u.usuario, u.cargo, u.email].some(c => (c || '').toLowerCase().includes(termo));
  });
  filtrados.sort((a, b) => (a.nome || a.usuario).localeCompare(b.nome || b.usuario));

  montarNumerosMU();
  montarSegmentosMU();
  document.getElementById('contagem-lista-mu').innerText = filtrados.length;
  const corpo = document.getElementById('corpo-lista-editar-mu');
  if (!filtrados.length) {
    corpo.innerHTML = '<div class="vazio-mu">Ninguém encontrado com esse filtro.</div>';
    return;
  }
  corpo.innerHTML = filtrados.map(u => {
    const ativo = u.ativo !== false;
    const vinculo = nomeVinculoMU(u);
    return `
      <button class="pessoa-mu ${ativo ? '' : 'inativa'}" data-usuario="${escaparHtmlMU(u.usuario)}" onclick="abrirPerfilEdicaoMU(this.dataset.usuario)">
        ${avatarMU(u)}
        <div style="min-width:0"><div class="nome">${escaparHtmlMU(u.nome || u.usuario)}</div>
          <div class="det">${escaparHtmlMU(u.usuario)}${u.cargo ? ' · ' + escaparHtmlMU(u.cargo) : ''}</div></div>
        <div class="col"><div>${escaparHtmlMU(u.atribuicao || 'Suporte')}</div></div>
        <div class="col">${vinculo
          ? `<span class="vinculo-mu"><span class="ponto"></span>${escaparHtmlMU(vinculo)}</span>`
          : '<span class="vinculo-mu sem"><span class="ponto"></span>Sem vínculo Movidesk</span>'}</div>
        <div class="etqs-mu">${u.admin ? '<span class="etq-mu admin">Admin</span>' : ''}
          <span class="etq-mu ${ativo ? 'ativo' : 'inativo'}">${ativo ? 'Ativo' : 'Desativado'}</span></div>
        <span class="seta">&#8250;</span>
      </button>`;
  }).join('');
}

// -- Gavetas -------------------------------------------------------------------
function abrirGavetaMU(id) {
  document.getElementById('fundo-mu').classList.add('aberto');
  ['gaveta-pessoa-mu', 'gaveta-cadexc-mu'].forEach(g => {
    const el = document.getElementById(g);
    el.classList.toggle('aberta', g === id);
    el.setAttribute('aria-hidden', g === id ? 'false' : 'true');
  });
  document.body.style.overflow = 'hidden';
}

function fecharGavetasMU() {
  document.getElementById('fundo-mu').classList.remove('aberto');
  document.querySelectorAll('.gaveta-mu').forEach(g => { g.classList.remove('aberta'); g.setAttribute('aria-hidden', 'true'); });
  document.body.style.overflow = '';
  usuarioAtualEditarMU = null;
}

document.addEventListener('keydown', e => {
  if (e.key !== 'Escape') return;
  if (document.getElementById('veu-modal-mu').classList.contains('aberto')) fecharModalMU(false);
  else fecharGavetasMU();
});

function mudarAbaPessoaMU(aba) {
  document.querySelectorAll('#abas-pessoa-mu button').forEach(b => b.classList.toggle('ativa', b.dataset.aba === aba));
  document.querySelectorAll('#gaveta-pessoa-mu .aba-mu').forEach(p => p.classList.toggle('ativa', p.dataset.aba === aba));
}

// cartões de escolha (equipe, papel, status) gravam num input escondido com o mesmo id de antes
function montarOpcoesMU(idContainer, idCampo, opcoes, aoMudar) {
  const valor = document.getElementById(idCampo).value;
  document.getElementById(idContainer).innerHTML = opcoes.map(o =>
    `<button type="button" class="opcao-mu ${o.valor === valor ? 'ativa' : ''}" data-valor="${escaparHtmlMU(o.valor)}"
       onclick="escolherOpcaoMU('${idContainer}', '${idCampo}', this.dataset.valor)"><div class="t">${o.t}</div><div class="d">${o.d}</div></button>`
  ).join('');
  montarOpcoesMU.aoMudar = montarOpcoesMU.aoMudar || {};
  if (aoMudar) montarOpcoesMU.aoMudar[idCampo] = aoMudar;
}
function escolherOpcaoMU(idContainer, idCampo, valor) {
  document.getElementById(idCampo).value = valor;
  document.querySelectorAll('#' + idContainer + ' .opcao-mu').forEach(b => b.classList.toggle('ativa', b.dataset.valor === valor));
  const fn = (montarOpcoesMU.aoMudar || {})[idCampo];
  if (fn) fn();
}
function avisoServicosMU() {
  const aviso = document.getElementById('aviso-servicos-mu');
  if (aviso) aviso.hidden = document.getElementById('ed-atribuicao').value !== 'Serviços';
}
function desenharOpcoesPessoaMU() {
  montarOpcoesMU('opcoes-atribuicao-mu', 'ed-atribuicao', EQUIPES_MU, avisoServicosMU);
  avisoServicosMU();
  montarOpcoesMU('opcoes-papel-mu', 'ed-papel', [
    { valor: 'view', t: 'Visualização', d: 'só as áreas liberadas' },
    { valor: 'admin', t: 'Administrador', d: 'libera as áreas comuns' },
  ], atualizarTravasPermissoesMU);
  montarOpcoesMU('opcoes-status-mu', 'ed-status', [
    { valor: 'true', t: 'Login ativo', d: 'entra no PDA normalmente' },
    { valor: 'false', t: 'Login desativado', d: 'não consegue entrar no PDA' },
  ]);
}

function montarCabecalhoPessoaMU(u) {
  const ativo = u.ativo !== false;
  document.getElementById('perfil-cabecalho-mu').innerHTML = `
    ${avatarMU(u)}
    <div style="min-width:0">
      <h2 style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis">${escaparHtmlMU(u.nome || u.usuario)}</h2>
      <div class="sub">${escaparHtmlMU(u.usuario)}${u.cargo ? ' · ' + escaparHtmlMU(u.cargo) : ''} · ${escaparHtmlMU(u.atribuicao || 'Suporte')}</div>
      <div class="etqs-mu">${u.admin ? '<span class="etq-mu admin">Administrador</span>' : '<span class="etq-mu neutra">Visualização</span>'}
        <span class="etq-mu ${ativo ? 'ativo' : 'inativo'}">${ativo ? 'Ativo' : 'Desativado'}</span>
        ${u.usuario_movidesk_id ? '<span class="etq-mu neutra">Movidesk vinculado</span>' : ''}</div>
    </div>`;
}

function limparMensagensMU(ids) { ids.forEach(id => { document.getElementById(id).innerText = ''; }); }

// -- Abrir uma pessoa: popula todas as abas de uma vez ------------------------
async function abrirPerfilEdicaoMU(usuario) {
  const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
  if (!u) return;
  usuarioAtualEditarMU = usuario;
  montarCabecalhoPessoaMU(u);
  document.getElementById('link-ver-perfil-mu').href = '/perfil/' + encodeURIComponent(u.usuario);
  mudarAbaPessoaMU('dados');

  document.getElementById('ed-nome').value = u.nome || u.usuario;
  document.getElementById('ed-genero').value = u.genero || '';
  document.getElementById('ed-email').value = u.email || '';
  document.getElementById('ed-data-inicio').value = u.data_inicio || '';
  document.getElementById('ed-papel').value = u.admin ? 'admin' : 'view';
  document.getElementById('ed-atribuicao').value = u.atribuicao || 'Suporte';
  document.getElementById('ed-status').value = u.ativo !== false ? 'true' : 'false';
  document.getElementById('ed-usuario-novo').value = '';
  document.querySelector('details.avancado-mu').open = false;
  document.getElementById('ed-nova-senha').value = '';
  document.getElementById('ed-confirma-senha').value = '';
  limparMensagensMU(['ed-erro-geral-mu', 'ed-status-geral-mu', 'ed-erro-boasvindas-mu', 'ed-status-boasvindas-mu',
    'ed-erro-renomear-mu', 'ed-status-renomear-mu', 'ed-erro-senha-mu', 'ed-status-senha-mu', 'perm-erro-mu', 'perm-status-mu',
    'vinc-erro-mu', 'vinc-status-mu', 'diag-erro-mu', 'diag-status-mu']);
  desenharOpcoesPessoaMU();

  for (const chave of Object.keys(ENDPOINTS_PERMISSOES_MU)) {
    // 3.3.2.1: permissão sem caixinha na tela (ex.: a do CTe2, que saiu na 3.3.1.0) é pulada; antes o erro aqui
    // parava a função e a gaveta da pessoa não abria
    const checkbox = document.getElementById('perm-' + chave);
    if (checkbox) checkbox.checked = !!u[chave];
  }
  atualizarTravasPermissoesMU();

  document.getElementById('vinc-busca-movidesk').value = '';
  montarOpcoesMovideskMU(u.usuario_movidesk_id || '');
  document.getElementById('vinc-campos-movidesk-mu').style.display = 'none';

  const campoDiagLogin = document.getElementById('diag-login');
  campoDiagLogin.value = u.email || '';
  document.getElementById('diag-resultado-mu').innerHTML = '';

  abrirGavetaMU('gaveta-pessoa-mu');
  if (u.usuario_movidesk_id) carregarDadosMovideskParaVinculoMU(u.usuario_movidesk_id);
}

// a flag Administrador das permissões e o Papel dos dados são o mesmo campo
function aoMarcarAdminMU() {
  document.getElementById('ed-papel').value = document.getElementById('perm-admin').checked ? 'admin' : 'view';
  desenharOpcoesPessoaMU();
  atualizarTravasPermissoesMU();
}

function atualizarTravasPermissoesMU() {
  const ehAdmin = document.getElementById('ed-papel').value === 'admin';
  document.getElementById('perm-admin').checked = ehAdmin;
  for (const chave of Object.keys(ENDPOINTS_PERMISSOES_MU)) {
    const checkbox = document.getElementById('perm-' + chave);
    if (!checkbox) continue;
    const travar = ehAdmin && !PERMISSOES_NAO_AUTOMATICAS_MU.has(chave);
    checkbox.disabled = travar;
    if (travar) checkbox.checked = true;
    checkbox.closest('.interruptor-mu').classList.toggle('travado', travar);
    checkbox.closest('.interruptor-mu').title = travar ? 'Automática pra administrador' : '';
  }
}

function desenharPermissoesMU() {
  document.getElementById('grade-permissoes-mu').innerHTML = PERMISSOES_UI_MU.map(p => `
    <label class="interruptor-mu">
      <input type="checkbox" id="perm-${p.chave}"><span class="trilho"></span>
      <span><span class="t">${p.t}</span>${p.nota ? `<span class="nota">${p.nota}</span>` : ''}<span class="d" style="display:block">${p.d}</span></span>
    </label>`).join('');
}

// -- Dados gerais (nome, e-mail, data, gênero, papel, equipe, status) ----------
async function salvarDadosGeraisMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('ed-erro-geral-mu');
  const statusEl = document.getElementById('ed-status-geral-mu');
  const botao = document.getElementById('btn-salvar-dados-mu');
  erroEl.innerText = ''; statusEl.innerText = '';
  const novoNome = document.getElementById('ed-nome').value.trim();
  if (!novoNome) { erroEl.innerText = 'O nome não pode ficar em branco.'; return; }
  const u = 'usuario=' + encodeURIComponent(usuario);
  const passos = [
    ['/api/usuarios/alterar-nome', u + '&nome=' + encodeURIComponent(novoNome), 'nome'],
    ['/api/usuarios/alterar-email', u + '&email=' + encodeURIComponent(document.getElementById('ed-email').value.trim()), 'e-mail'],
    ['/api/usuarios/alterar-data-inicio', u + '&data_inicio=' + encodeURIComponent(document.getElementById('ed-data-inicio').value), 'data de início'],
    ['/api/usuarios/alterar-genero', u + '&genero=' + encodeURIComponent(document.getElementById('ed-genero').value), 'gênero'],
    ['/api/usuarios/admin', u + '&admin=' + (document.getElementById('ed-papel').value === 'admin' ? 'true' : 'false'), 'papel'],
    ['/api/usuarios/alterar-atribuicao', u + '&atribuicao=' + encodeURIComponent(document.getElementById('ed-atribuicao').value), 'equipe'],
    ['/api/usuarios/alterar-status', u + '&ativo=' + document.getElementById('ed-status').value, 'status'],
  ];
  botao.disabled = true;
  try {
    for (const [url, corpo, nome] of passos) {
      const { dados } = await postarMU(url, corpo);
      if (!dados.ok) { erroEl.innerText = dados.erro || ('Não foi possível salvar o ' + nome + '.'); return; }
    }
    statusEl.innerText = 'Salvo.';
    mostrarToastMU('Dados de ' + novoNome + ' salvos.');
    await recarregarUsuariosMU();
    const atualizado = usuariosCarregadosMU.find(x => x.usuario === usuario);
    if (atualizado) montarCabecalhoPessoaMU(atualizado);
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  } finally {
    botao.disabled = false;
  }
}

// desativar (ou reativar) só o login do PDA, sem passar pelo fluxo dos bancos e do Movidesk (3.3.1.0)
function atualizarSoPdaMU() {
  const u = usuariosCarregadosMU.find(x => x.usuario === usuarioAtualEditarMU);
  const botao = document.getElementById('btn-so-pda-mu');
  if (!u || !botao) return;
  const ativo = u.ativo !== false;
  botao.textContent = ativo ? 'Desativar só no PDA' : 'Reativar no PDA';
  botao.className = ativo ? 'btn-perigo-mu' : 'btn-accent';
}
async function alternarSoPdaMU() {
  const u = usuariosCarregadosMU.find(x => x.usuario === usuarioAtualEditarMU);
  if (!u) return;
  const ativar = u.ativo === false;
  const nome = u.nome || u.usuario;
  if (!confirm(ativar ? 'Reativar o login de ' + nome + ' no PDA?' : 'Desativar ' + nome + ' só no PDA? Os bancos dos clientes e o Movidesk não mudam.')) return;
  try {
    const { dados } = await postarMU('/api/usuarios/alterar-status', 'usuario=' + encodeURIComponent(u.usuario) + '&ativo=' + (ativar ? 'true' : 'false'));
    if (!dados.ok) { mostrarToastMU(dados.erro || 'Não foi possível mudar o status.'); return; }
    mostrarToastMU(ativar ? nome + ' reativado(a) no PDA.' : nome + ' desativado(a) no PDA.');
    await recarregarUsuariosMU();
    const atualizado = usuariosCarregadosMU.find(x => x.usuario === u.usuario);
    if (atualizado) {
      document.getElementById('ed-status').value = atualizado.ativo !== false ? 'true' : 'false';
      desenharOpcoesPessoaMU();
      montarCabecalhoPessoaMU(atualizado);
    }
    atualizarSoPdaMU();
  } catch (e) {
    mostrarToastMU('Erro: ' + e);
  }
}

async function salvarSenhaEdicaoMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('ed-erro-senha-mu');
  const statusEl = document.getElementById('ed-status-senha-mu');
  erroEl.innerText = ''; statusEl.innerText = '';
  const nova = document.getElementById('ed-nova-senha').value;
  const confirma = document.getElementById('ed-confirma-senha').value;
  if (!nova || nova.length < 4) { erroEl.innerText = 'A senha precisa ter ao menos 4 caracteres.'; return; }
  if (nova !== confirma) { erroEl.innerText = 'As senhas não coincidem.'; return; }
  try {
    const { dados } = await postarMU('/api/usuarios/senha', 'usuario=' + encodeURIComponent(usuario) + '&nova_senha=' + encodeURIComponent(nova));
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível salvar.'; return; }
    statusEl.innerText = 'Senha atualizada.';
    document.getElementById('ed-nova-senha').value = '';
    document.getElementById('ed-confirma-senha').value = '';
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  }
}

// envia de verdade pro e-mail cadastrado, com a senha REAL da pessoa
async function enviarBoasVindasTesteMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('ed-erro-boasvindas-mu');
  const statusEl = document.getElementById('ed-status-boasvindas-mu');
  erroEl.innerText = '';
  statusEl.innerText = 'Enviando...';
  try {
    const { dados } = await postarMU('/api/usuarios/enviar-boas-vindas', 'usuario=' + encodeURIComponent(usuario));
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível enviar.'; statusEl.innerText = ''; return; }
    statusEl.innerText = `Enviado pra ${dados.email}.`;
  } catch (e) {
    erroEl.innerText = 'Erro ao enviar: ' + e;
    statusEl.innerText = '';
  }
}

// troca a chave do login em tudo (feedbacks, histórico, sessão): operação rara, com confirmação
async function renomearUsuarioMU() {
  const usuarioAtual = usuarioAtualEditarMU;
  if (!usuarioAtual) return;
  const usuarioNovo = document.getElementById('ed-usuario-novo').value.trim();
  const erroEl = document.getElementById('ed-erro-renomear-mu');
  const statusEl = document.getElementById('ed-status-renomear-mu');
  erroEl.innerText = '';
  if (!usuarioNovo) { erroEl.innerText = 'Informe o novo login.'; return; }
  const ok = await confirmarMU('Renomear login?',
    `De <b>${escaparHtmlMU(usuarioAtual)}</b> pra <b>${escaparHtmlMU(usuarioNovo)}</b>. Troca o login em permissões, feedbacks e histórico de carreira, e encerra a sessão aberta da pessoa.`,
    'Renomear');
  if (!ok) return;
  statusEl.innerText = 'Renomeando...';
  try {
    const { dados } = await postarMU('/api/usuarios/renomear',
      'usuario_atual=' + encodeURIComponent(usuarioAtual) + '&usuario_novo=' + encodeURIComponent(usuarioNovo));
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível renomear.'; statusEl.innerText = ''; return; }
    await recarregarUsuariosMU();
    mostrarToastMU(`Login renomeado pra '${dados.usuario_novo}'.`);
    abrirPerfilEdicaoMU(dados.usuario_novo);
  } catch (e) {
    erroEl.innerText = 'Erro ao renomear: ' + e;
    statusEl.innerText = '';
  }
}

// uma permissão por vez, conferindo a resposta, e relendo do servidor no fim (2.33.6.0)
async function salvarPermissoesMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const erroEl = document.getElementById('perm-erro-mu');
  const statusEl = document.getElementById('perm-status-mu');
  erroEl.innerText = '';
  statusEl.innerText = 'Salvando...';
  const falhas = [];
  async function enviar(url, corpo, nome) {
    try {
      const { resp, dados } = await postarMU(url, corpo);
      if (!resp.ok || !dados.ok) falhas.push(nome + ': ' + (dados.erro || ('HTTP ' + resp.status)));
    } catch (e) {
      falhas.push(nome + ': ' + e);
    }
  }
  const titulo = chave => (PERMISSOES_UI_MU.find(p => p.chave === chave) || { t: chave }).t;
  const querAdmin = document.getElementById('perm-admin').checked;
  await enviar('/api/usuarios/admin', 'usuario=' + encodeURIComponent(usuario) + '&admin=' + (querAdmin ? 'true' : 'false'), 'Administrador');
  for (const [chave, url] of Object.entries(ENDPOINTS_PERMISSOES_MU)) {
    const checkbox = document.getElementById('perm-' + chave);
    if (!checkbox || checkbox.disabled) continue;  // sem caixinha na tela, ou automática pra admin
    await enviar(url, 'usuario=' + encodeURIComponent(usuario) + '&permitido=' + (checkbox.checked ? 'true' : 'false'), titulo(chave));
  }
  try {
    const dadosUsuarios = await (await fetch('/api/usuarios')).json();
    usuariosCarregadosMU = dadosUsuarios.usuarios || usuariosCarregadosMU;
    const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
    if (u) {
      if (!!u.admin !== querAdmin) falhas.push('Administrador não ficou gravado');
      for (const chave of Object.keys(ENDPOINTS_PERMISSOES_MU)) {
        const checkbox = document.getElementById('perm-' + chave);
        if (checkbox && !checkbox.disabled && !!u[chave] !== checkbox.checked) falhas.push(titulo(chave) + ' não ficou gravada');
      }
      filtrarListaEditarMU();
      montarCabecalhoPessoaMU(u);
    }
  } catch (e) { /* as respostas acima já dizem se gravou */ }
  if (falhas.length) {
    erroEl.innerText = 'Não salvou tudo: ' + falhas.join(' · ');
    statusEl.innerText = '';
  } else {
    statusEl.innerText = 'Salvas. Valem depois que a pessoa sair e entrar de novo.';
    mostrarToastMU('Permissões salvas.');
  }
}

// -- Vínculo Movidesk --------------------------------------------------------------
function montarOpcoesMovideskMU(selecionar) {
  const select = document.getElementById('vinc-select-movidesk');
  const atual = selecionar !== undefined ? String(selecionar) : select.value;
  const filtro = (document.getElementById('vinc-busca-movidesk').value || '').trim().toLowerCase();
  const lista = usuariosMovideskCarregadosMU.filter(m => !filtro || String(m.id) === atual
    || (m.nome || '').toLowerCase().includes(filtro) || (m.cargo || '').toLowerCase().includes(filtro));
  select.innerHTML = '<option value="">Sem vínculo</option>' +
    lista.map(m => `<option value="${escaparHtmlMU(m.id)}">${escaparHtmlMU(m.nome)}${m.cargo ? ' · ' + escaparHtmlMU(m.cargo) : ''}</option>`).join('');
  select.value = atual;
}

function aoTrocarUsuarioVinculadoMU() {
  const id = document.getElementById('vinc-select-movidesk').value;
  if (id) carregarDadosMovideskParaVinculoMU(id);
  else document.getElementById('vinc-campos-movidesk-mu').style.display = 'none';
}

async function carregarDadosMovideskParaVinculoMU(id) {
  const erroEl = document.getElementById('vinc-erro-mu');
  erroEl.innerText = '';
  try {
    const dados = await (await fetch('/api/usuarios-movidesk/' + encodeURIComponent(id))).json();
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível carregar os dados desse usuário.';
      document.getElementById('vinc-campos-movidesk-mu').style.display = 'none';
      return;
    }
    const r = dados.registro;
    document.getElementById('vinc-cargo').value = r.cargo || '';
    document.getElementById('vinc-email').value = r.email || '';
    document.getElementById('vinc-escala').value = r.escala || '';
    document.getElementById('vinc-horainicio').value = r.horainicio || '';
    document.getElementById('vinc-horafim').value = r.horafim || '';
    const diasMarcados = (r.diastrabalhados || '').split(',').map(d => d.trim()).filter(Boolean);
    document.querySelectorAll('#vinc-campos-movidesk-mu .dia-check-mu input').forEach(chk => { chk.checked = diasMarcados.includes(chk.value); });
    document.getElementById('vinc-campos-movidesk-mu').style.display = 'block';
    if (r.email) document.getElementById('diag-login').value = r.email;
  } catch (e) {
    erroEl.innerText = 'Erro ao carregar: ' + e;
  }
}

async function salvarVinculoMovideskMU() {
  const erroEl = document.getElementById('vinc-erro-mu');
  const statusEl = document.getElementById('vinc-status-mu');
  erroEl.innerText = ''; statusEl.innerText = '';
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const idSelecionado = document.getElementById('vinc-select-movidesk').value;
  try {
    const { dados: dadosVinculo } = await postarMU('/api/usuarios/vincular-movidesk',
      'usuario=' + encodeURIComponent(usuario) + '&id_movidesk=' + encodeURIComponent(idSelecionado));
    if (!dadosVinculo.ok) { erroEl.innerText = dadosVinculo.erro || 'Não foi possível salvar o vínculo.'; return; }
    if (idSelecionado) {
      const diasMarcados = Array.from(document.querySelectorAll('#vinc-campos-movidesk-mu .dia-check-mu input:checked')).map(c => c.value);
      const { dados: dadosSalvar } = await postarMU('/api/usuarios-movidesk/atualizar',
        'id=' + encodeURIComponent(idSelecionado) +
        '&cargo=' + encodeURIComponent(document.getElementById('vinc-cargo').value) +
        '&email=' + encodeURIComponent(document.getElementById('vinc-email').value) +
        '&escala=' + encodeURIComponent(document.getElementById('vinc-escala').value) +
        '&horainicio=' + encodeURIComponent(document.getElementById('vinc-horainicio').value) +
        '&horafim=' + encodeURIComponent(document.getElementById('vinc-horafim').value) +
        '&diasTrabalhados=' + encodeURIComponent(diasMarcados.join(',')));
      if (!dadosSalvar.ok) { erroEl.innerText = dadosSalvar.erro || 'Vínculo salvo, mas não foi possível salvar os dados de horas.'; return; }
      const email = document.getElementById('vinc-email').value;
      if (email) document.getElementById('diag-login').value = email;
    }
    statusEl.innerText = 'Vínculo e dados atualizados.';
    mostrarToastMU('Vínculo com o Movidesk salvo.');
    await recarregarUsuariosMU();
    const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
    if (u) montarCabecalhoPessoaMU(u);
  } catch (e) {
    erroEl.innerText = 'Erro ao salvar: ' + e;
  }
}

// -- Diagnóstico: SÓ CONSULTA (Movidesk + todos os bancos de cliente) ---------------
function renderizarResultadoDiagnosticoMU(dados, login) {
  const rotulos = { success: 'Encontrado', skipped: 'Não encontrado', error: 'Erro' };
  let blocoMovidesk;
  if (dados.erro_movidesk) {
    blocoMovidesk = `<div class="linha-resumo-mu"><span>Movidesk</span><span class="erro-mu">${escaparHtmlMU(dados.erro_movidesk)}</span></div>`;
  } else if (dados.movidesk) {
    const m = dados.movidesk;
    blocoMovidesk = `
      <div class="linha-resumo-mu"><span>Movidesk</span><span><span class="badge-status-mu success">Encontrado</span></span></div>
      <div class="linha-resumo-mu"><span>Nome</span><span>${escaparHtmlMU(m.businessName || '-')}</span></div>
      <div class="linha-resumo-mu"><span>Ativo</span><span>${m.isActive ? 'Sim' : 'Não'}</span></div>
      <div class="linha-resumo-mu"><span>Perfil de acesso</span><span>${escaparHtmlMU(m.accessProfile || '-')}</span></div>`;
  } else {
    blocoMovidesk = '<div class="linha-resumo-mu"><span>Movidesk</span><span><span class="badge-status-mu skipped">Não encontrado</span></span></div>';
  }
  const linhasBancos = dados.resultados_bancos.map(r => `
    <tr><td>${escaparHtmlMU(r.area)}</td><td>${escaparHtmlMU(r.tenant)}</td><td>${escaparHtmlMU(r.produto)}</td><td>${escaparHtmlMU(r.database)}</td>
      <td><span class="badge-status-mu ${r.status}">${rotulos[r.status] || escaparHtmlMU(r.status)}</span></td><td>${escaparHtmlMU(r.message)}</td></tr>`).join('');
  const totalEncontrado = dados.resultados_bancos.filter(r => r.status === 'success').length;
  const totalErro = dados.resultados_bancos.filter(r => r.status === 'error').length;
  document.getElementById('diag-resultado-mu').innerHTML = `
    <div class="linha-resumo-mu"><span>Login verificado</span><span>${escaparHtmlMU(login)}</span></div>
    ${blocoMovidesk}
    <div class="resumo-final-mu">Encontrado em <b>${totalEncontrado}</b> de ${dados.resultados_bancos.length} banco(s)${totalErro ? ` (${totalErro} não puderam ser checados)` : ''}.</div>
    <div class="rolagem-mu"><table class="tabela-mu">
      <thead><tr><th>Área</th><th>Tenant</th><th>Produto</th><th>Banco</th><th>Status</th><th>Detalhe</th></tr></thead>
      <tbody>${linhasBancos}</tbody></table></div>`;
}

async function verificarDiagnosticoMU() {
  const login = document.getElementById('diag-login').value.trim();
  const erroEl = document.getElementById('diag-erro-mu');
  const statusEl = document.getElementById('diag-status-mu');
  erroEl.innerText = '';
  if (!login) { erroEl.innerText = 'Informe o login pra verificar.'; return; }
  const botao = document.getElementById('btn-diag-verificar');
  botao.disabled = true;
  statusEl.innerHTML = '<span class="giro-mu"></span> Verificando em todos os bancos... pode levar um tempo.';
  document.getElementById('diag-resultado-mu').innerHTML = '';
  try {
    const { dados } = await postarMU('/api/manutencao-usuarios/diagnostico', 'login=' + encodeURIComponent(login));
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível verificar.'; statusEl.innerText = ''; return; }
    renderizarResultadoDiagnosticoMU(dados, login);
    statusEl.innerText = '';
  } catch (e) {
    erroEl.innerText = 'Erro ao verificar: ' + e;
    statusEl.innerText = '';
  } finally {
    botao.disabled = false;
  }
}

// -- Cadastrar / Desativar (banco + Movidesk + login PDA opcional) -------------------
function abrirCadExcMU(acao, preenchido) {
  acaoCadExcMU = acao;
  const cad = acao === 'cad';
  document.getElementById('titulo-form-cadexc').innerText = cad ? 'Novo usuário' : 'Desativar usuário';
  document.getElementById('sub-form-cadexc').innerText = cad
    ? 'Cria a pessoa nos bancos da área escolhida e no Movidesk, e se quiser também o login no PDA.'
    : 'Desativa a pessoa nos bancos da área escolhida e no Movidesk, e se quiser também o login no PDA.';
  document.getElementById('btn-mu-executar').className = cad ? 'btn-accent' : 'btn-perigo-mu';
  document.getElementById('btn-mu-executar').innerText = cad ? 'Confirmar e cadastrar' : 'Confirmar e desativar';
  document.getElementById('mu-nome').value = (preenchido && preenchido.nome) || '';
  document.getElementById('mu-login').value = (preenchido && preenchido.login) || '';
  document.getElementById('mu-incluir-pda').checked = !!(preenchido && preenchido.usuarioPda);
  document.getElementById('mu-usuario-pda').value = (preenchido && preenchido.usuarioPda) || '';
  document.getElementById('mu-senha-pda').value = '';
  document.getElementById('mu-genero-pda').value = '';
  document.getElementById('mu-enviar-boas-vindas').checked = false;
  escolherAreaMU((preenchido && preenchido.area) || 'suporte');
  atualizarCamposCondicionaisMU();
  invalidarPreviaMU();
  document.getElementById('mu-erro').innerText = '';
  document.getElementById('mu-status').innerText = (preenchido && preenchido.aviso) || '';
  abrirGavetaMU('gaveta-cadexc-mu');
  setTimeout(() => document.getElementById(preenchido && preenchido.nome ? 'mu-login' : 'mu-nome').focus(), 260);
}

function escolherAreaMU(area) {
  areaMU = area;
  document.querySelectorAll('#opcoes-area-mu .opcao-mu').forEach(b => b.classList.toggle('ativa', b.dataset.area === area));
  invalidarPreviaMU();
}

// qualquer mudança nos dados invalida a prévia: confirmar exige uma prévia do que está na tela
function invalidarPreviaMU() {
  if (!previaAlvosManutencaoUsuarios.length) return;
  previaAlvosManutencaoUsuarios = [];
  document.getElementById('btn-mu-executar').disabled = true;
  document.getElementById('mu-titulo-workspace').innerText = 'Prévia';
  document.getElementById('mu-workspace').innerHTML = '<div class="ajuda-mu">Os dados mudaram: gere a prévia de novo.</div>';
}

function lerFormularioManutencaoUsuarios() {
  const acao = acaoCadExcMU;
  return {
    acao, area: areaMU,
    nome: document.getElementById('mu-nome').value.trim(),
    login: document.getElementById('mu-login').value.trim(),
    incluirPda: document.getElementById('mu-incluir-pda').checked,
    usuarioPda: document.getElementById('mu-usuario-pda').value.trim(),
    senhaPda: document.getElementById('mu-senha-pda').value,
    generoPda: document.getElementById('mu-genero-pda').value,
    enviarBoasVindas: acao === 'cad' && document.getElementById('mu-enviar-boas-vindas').checked,
  };
}

function atualizarCamposCondicionaisMU() {
  const cad = acaoCadExcMU === 'cad';
  const incluirPda = document.getElementById('mu-incluir-pda').checked;
  document.getElementById('mu-campos-pda').style.display = incluirPda ? 'block' : 'none';
  document.getElementById('mu-bloco-senha-pda').style.display = cad ? '' : 'none';
  document.getElementById('mu-bloco-genero-pda').style.display = cad ? '' : 'none';
  document.getElementById('mu-texto-incluir-pda').innerText = cad ? 'Também criar o login no PDA' : 'Também desativar o login no PDA';
  document.getElementById('mu-dica-incluir-pda').innerText = cad
    ? 'Sem nenhuma permissão extra (nem admin). Ajuste depois na pessoa.'
    : 'O login do PDA fica desativado (não é apagado).';
  document.getElementById('mu-dica-senha').style.display = cad ? '' : 'none';
  document.getElementById('mu-campo-boas-vindas').style.display = cad ? 'flex' : 'none';
  if (!cad) document.getElementById('mu-enviar-boas-vindas').checked = false;
}

function corpoCadExcMU(f, comSenha) {
  return 'action=' + encodeURIComponent(f.acao) + '&area=' + encodeURIComponent(f.area) +
    '&nome=' + encodeURIComponent(f.nome) + '&login=' + encodeURIComponent(f.login) +
    '&incluir_pda=' + (f.incluirPda ? 'true' : 'false') + '&usuario_pda=' + encodeURIComponent(f.usuarioPda) +
    (comSenha ? '&senha_pda=' + encodeURIComponent(f.senhaPda) + '&genero_pda=' + encodeURIComponent(f.generoPda) : '') +
    '&enviar_boas_vindas=' + (f.enviarBoasVindas ? 'true' : 'false');
}

function renderizarTabelaAlvosManutencaoUsuarios(alvos) {
  if (alvos.length === 0) return '<div class="ajuda-mu">Nenhum alvo encontrado pra essa área.</div>';
  const porProduto = {};
  alvos.forEach(a => { porProduto[a.produto] = (porProduto[a.produto] || 0) + 1; });
  const resumo = Object.entries(porProduto).map(([p, n]) => `<span>${escaparHtmlMU(p)} · ${n}</span>`).join('');
  const linhas = alvos.map(a => `<tr><td>${escaparHtmlMU(a.area)}</td><td>${escaparHtmlMU(a.tenant)}</td><td>${escaparHtmlMU(a.produto)}</td><td>${escaparHtmlMU(a.database)}</td></tr>`).join('');
  return `<div class="contagem-alvos-mu">${resumo}</div>
    <div class="rolagem-mu"><table class="tabela-mu"><thead><tr><th>Área</th><th>Tenant</th><th>Produto</th><th>Banco</th></tr></thead>
    <tbody>${linhas}</tbody></table></div>`;
}

async function gerarPreviaManutencaoUsuarios() {
  const f = lerFormularioManutencaoUsuarios();
  const erroEl = document.getElementById('mu-erro');
  const statusEl = document.getElementById('mu-status');
  erroEl.innerText = '';
  document.getElementById('btn-mu-executar').disabled = true;
  previaAlvosManutencaoUsuarios = [];
  const botao = document.getElementById('btn-mu-previa');
  botao.disabled = true;
  statusEl.innerHTML = '<span class="giro-mu"></span> Montando a prévia...';
  try {
    const { dados } = await postarMU('/api/manutencao-usuarios/previa', corpoCadExcMU(f, false));
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível gerar a prévia.'; statusEl.innerText = ''; return; }
    previaAlvosManutencaoUsuarios = dados.targets;
    document.getElementById('mu-titulo-workspace').innerText = `Prévia · ${dados.targets.length} alvo(s)`;
    document.getElementById('mu-workspace').innerHTML = renderizarTabelaAlvosManutencaoUsuarios(dados.targets);
    document.getElementById('btn-mu-executar').disabled = dados.targets.length === 0;
    statusEl.innerText = `${dados.targets.length} alvo(s), Movidesk incluso. Revise antes de confirmar.`;
    document.getElementById('mu-workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (e) {
    erroEl.innerText = 'Erro ao gerar prévia: ' + e;
    statusEl.innerText = '';
  } finally {
    botao.disabled = false;
  }
}

async function confirmarExecucaoManutencaoUsuarios() {
  if (previaAlvosManutencaoUsuarios.length === 0) {
    document.getElementById('mu-erro').innerText = 'Gere a prévia antes de executar.';
    return;
  }
  const f = lerFormularioManutencaoUsuarios();
  const cad = f.acao === 'cad';
  const ok = await confirmarMU(cad ? 'Cadastrar usuário?' : 'Desativar usuário?',
    `Vai ${cad ? 'cadastrar' : 'desativar'} <b>${escaparHtmlMU(f.login)}</b> em <b>${previaAlvosManutencaoUsuarios.length} alvo(s)</b>` +
    `${f.incluirPda ? ` e ${cad ? 'criar' : 'desativar'} o login <b>${escaparHtmlMU(f.usuarioPda)}</b> no PDA` : ''}.<br><br>` +
    'Grava de verdade nos bancos de produção e na API do Movidesk, e não pode ser desfeito automaticamente.',
    cad ? 'Cadastrar' : 'Desativar');
  if (!ok) { document.getElementById('mu-status').innerText = 'Execução cancelada.'; return; }

  const erroEl = document.getElementById('mu-erro');
  const statusEl = document.getElementById('mu-status');
  const botaoExecutar = document.getElementById('btn-mu-executar');
  const botaoPrevia = document.getElementById('btn-mu-previa');
  erroEl.innerText = '';
  botaoExecutar.disabled = true;
  botaoPrevia.disabled = true;
  statusEl.innerHTML = '<span class="giro-mu"></span> Executando... uma conexão por alvo, em sequência.';
  document.getElementById('mu-titulo-workspace').innerText = 'Executando...';
  try {
    const { dados } = await postarMU('/api/manutencao-usuarios/executar', corpoCadExcMU(f, true));
    if (!dados.ok) {
      erroEl.innerText = dados.erro || 'Não foi possível executar.';
      statusEl.innerText = '';
      return;
    }
    renderizarResultadoManutencaoUsuarios(dados);
    statusEl.innerText = 'Execução finalizada.';
    previaAlvosManutencaoUsuarios = [];
    mostrarToastMU(cad ? 'Cadastro finalizado. Confira o resultado.' : 'Desativação finalizada. Confira o resultado.');
    recarregarUsuariosMU();
  } catch (e) {
    erroEl.innerText = 'Erro ao executar: ' + e;
    statusEl.innerText = '';
  } finally {
    botaoPrevia.disabled = false;
  }
}

function renderizarResultadoManutencaoUsuarios(dados) {
  document.getElementById('mu-titulo-workspace').innerText = 'Resultado';
  const rotulos = { success: 'OK', skipped: 'AVISO', error: 'ERRO' };
  const linhas = dados.resultados.map(r => `
    <tr><td>${escaparHtmlMU(r.area)}</td><td>${escaparHtmlMU(r.tenant)}</td><td>${escaparHtmlMU(r.produto)}</td><td>${escaparHtmlMU(r.database)}</td>
      <td><span class="badge-status-mu ${r.status}">${rotulos[r.status] || escaparHtmlMU(r.status)}</span></td><td>${escaparHtmlMU(r.message)}</td></tr>`).join('');
  document.getElementById('mu-workspace').innerHTML = `
    <div class="resumo-final-mu" style="margin-top:0">
      <b>${dados.sucesso}</b> sucesso(s) · <b>${dados.ignorados}</b> ignorado(s) · <b>${dados.erros}</b> erro(s) · log <b>${escaparHtmlMU(dados.log)}</b>
    </div>
    <div class="rolagem-mu"><table class="tabela-mu">
      <thead><tr><th>Área</th><th>Tenant</th><th>Produto</th><th>Banco</th><th>Status</th><th>Mensagem</th></tr></thead>
      <tbody>${linhas}</tbody></table></div>`;
}

// da aba Desativar da pessoa pra gaveta de desativação, já com os dados dela
function irParaDesativarComDadosMU() {
  const usuario = usuarioAtualEditarMU;
  if (!usuario) return;
  const u = usuariosCarregadosMU.find(x => x.usuario === usuario);
  if (!u) return;
  const loginSugerido = document.getElementById('vinc-email').value || document.getElementById('diag-login').value || u.email || '';
  const area = u.atribuicao === 'Monitoramento' ? 'monitoramento' : (u.atribuicao === 'Suporte e Monitoramento' ? 'todos' : 'suporte');
  abrirCadExcMU('exc', {
    nome: u.nome || u.usuario, login: loginSugerido, usuarioPda: u.usuario, area,
    aviso: loginSugerido
      ? `Dados de ${u.nome || u.usuario} preenchidos pelo perfil: confira a área e o login.`
      : 'Não achamos um e-mail dessa pessoa: preencha o login antes da prévia.',
  });
}

desenharPermissoesMU();
atualizarCamposCondicionaisMU();
carregarListasBaseMU();
</script>
</body>
</html>
"""
