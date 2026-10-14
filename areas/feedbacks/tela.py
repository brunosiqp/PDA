"""Tela Feedbacks.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py e em areas/feedbacks/logica.py.
2.34.9.0: tela redesenhada - a lista é o foco e o formulário abre numa gaveta lateral,
em etapas (o quê, pra quem, quem fez, quem é avisado, conteúdo). Mesmas rotas e regras.
Sem barra invertida no JS deste template (vira escape do Python).
"""


_FEEDBACKS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Feedbacks e Alinhamentos</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  /* ---------- topo ---------- */
  .topo-fb { display: flex; justify-content: space-between; align-items: flex-end; gap: 14px; flex-wrap: wrap;
             max-width: var(--largura-pagina); margin: 0 auto 18px auto; }
  .topo-fb h1 { font-size: 20px; margin: 0 0 4px 0; background: var(--gradiente-marca);
                -webkit-background-clip: text; background-clip: text; color: transparent; }
  .topo-fb .sub { color: var(--fg-dim); font-size: 12.5px; }
  .btn-novo-fb { padding: 10px 18px; border-radius: 10px; font-size: 13px; }

  /* ---------- barra de filtros ---------- */
  .nota-equipes-fb { max-width: var(--largura-pagina); margin: -6px auto 14px auto; font-size: 12px; color: var(--fg-dim);
                     display: flex; align-items: center; gap: 7px; flex-wrap: wrap; }
  .nota-equipes-fb:empty { display: none; }
  .nota-equipes-fb b { color: var(--fg); }
  .aviso-equipe-fb { font-size: 11.5px; color: var(--fg-dim); background: rgba(232,163,61,.08); border: 1px solid rgba(232,163,61,.3);
                     border-radius: 9px; padding: 8px 12px; margin-top: 10px; line-height: 1.5; }
  .barra-fb { max-width: var(--largura-pagina); margin: 0 auto 16px auto; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;
              background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; padding: 12px 14px; }
  .busca-fb { flex: 1 1 240px; display: flex; align-items: center; gap: 8px; background: rgba(var(--poco),.25);
              border: 1px solid var(--border); border-radius: 9px; padding: 0 10px; }
  .busca-fb input { flex: 1; border: none; background: none; color: var(--fg); font-size: 13px; padding: 9px 0; font-family: inherit; }
  .busca-fb input:focus { outline: none; }
  .busca-fb:focus-within { border-color: var(--teal); }
  .busca-fb svg { width: 15px; height: 15px; color: var(--fg-dim); flex-shrink: 0; }
  .campo-fb { background: rgba(var(--poco),.25); border: 1px solid var(--border); color: var(--fg); border-radius: 9px;
              padding: 9px 10px; font-size: 12.5px; font-family: inherit; }
  .campo-fb:focus { outline: none; border-color: var(--teal); }
  .abas-fb { display: inline-flex; background: rgba(var(--poco),.25); border: 1px solid var(--border); border-radius: 9px; padding: 3px; }
  .abas-fb button { background: none; border: none; color: var(--fg-dim); font-size: 12px; font-weight: 600; padding: 6px 12px;
                    border-radius: 7px; cursor: pointer; font-family: inherit; display: flex; gap: 6px; align-items: center; }
  .abas-fb button.ativa { background: rgba(var(--tinta),.09); color: var(--fg); }
  .abas-fb .qtd { font-size: 10.5px; color: var(--fg-dim); font-weight: 700; }

  /* ---------- lista ---------- */
  .lista-fb { max-width: var(--largura-pagina); margin: 0 auto; display: flex; flex-direction: column; gap: 12px; }
  .card-fb { background: var(--bg-panel); border: 1px solid var(--border); border-left: 3px solid var(--cor-tipo, var(--teal));
             border-radius: 12px; padding: 16px 18px; transition: border-color .15s; }
  .card-fb.alinhamento { --cor-tipo: var(--lime); }
  /* veio do mural do início (/feedbacks?registro=ID, 3.0.1.0): o registro fica em destaque */
  .card-fb.destacado-fb { border-color: var(--teal); box-shadow: 0 0 0 2px rgba(45,184,207,.55), 0 0 28px -6px rgba(45,184,207,.6); }
  .card-fb:hover { border-color: rgba(45,184,207,.35); border-left-color: var(--cor-tipo, var(--teal)); }
  .card-fb .linha1 { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; flex-wrap: wrap; }
  .card-fb .para { font-size: 14px; font-weight: 700; color: var(--fg); line-height: 1.4; }
  .card-fb .para a { color: var(--fg); text-decoration: none; border-bottom: 1px dashed rgba(var(--tinta),.3); }
  .card-fb .para a:hover { color: var(--teal); border-bottom-color: var(--teal); }
  .card-fb .por { font-size: 12px; color: var(--fg-dim); margin-top: 3px; }
  .card-fb .por b { color: var(--fg); font-weight: 600; }
  .card-fb .data { font-size: 11px; color: var(--fg-dim); white-space: nowrap; }
  .etiquetas-fb { display: flex; gap: 6px; flex-wrap: wrap; margin: 10px 0 0 0; align-items: center; }
  .etq-fb { font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 6px; letter-spacing: .02em; }
  .etq-fb.tipo { background: rgba(45,184,207,.14); color: var(--teal); text-transform: uppercase; }
  .card-fb.alinhamento .etq-fb.tipo { background: rgba(176,203,28,.14); color: var(--lime); }
  .etq-fb.neutra { background: rgba(var(--tinta),.06); color: var(--fg-dim); }
  .etq-fb.equipe { background: rgba(45,184,207,.08); color: var(--fg); border: 1px solid rgba(45,184,207,.2); }
  .estrelas-fb { color: var(--run); font-size: 13px; letter-spacing: 1px; }
  .texto-fb { font-size: 13px; color: var(--fg); line-height: 1.65; white-space: pre-wrap; margin-top: 12px; word-break: break-word; }
  .texto-fb.recolhido { display: -webkit-box; -webkit-line-clamp: 4; -webkit-box-orient: vertical; overflow: hidden; }
  .ver-mais-fb { background: none; border: none; color: var(--teal); font-size: 12px; padding: 4px 0 0 0; cursor: pointer; font-family: inherit; }
  .rodape-card-fb { display: flex; justify-content: space-between; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 12px;
                    padding-top: 10px; border-top: 1px solid rgba(var(--tinta),.06); }
  .anexos-fb { display: flex; gap: 8px; flex-wrap: wrap; }
  .anexo-link-fb { font-size: 12px; color: var(--teal); text-decoration: none; padding: 4px 9px; border-radius: 7px;
                   background: rgba(45,184,207,.08); border: 1px solid rgba(45,184,207,.2); }
  .anexo-link-fb:hover { border-color: var(--teal); }
  .acoes-fb { display: flex; gap: 6px; margin-left: auto; }
  .acao-fb { background: none; border: 1px solid var(--border); color: var(--fg-dim); border-radius: 7px; padding: 5px 11px;
             font-size: 11.5px; cursor: pointer; font-family: inherit; }
  .acao-fb:hover { color: var(--fg); border-color: var(--teal); }
  .acao-fb.perigo:hover { color: var(--erro); border-color: var(--erro); }
  .editado-fb { font-style: italic; }
  .vazio-fb { text-align: center; color: var(--fg-dim); font-size: 13px; padding: 46px 10px; background: var(--bg-panel);
              border: 1px dashed var(--border); border-radius: 14px; }
  .vazio-fb .grande { font-size: 15px; color: var(--fg); font-weight: 700; margin-bottom: 6px; }

  /* ---------- gaveta do formulário ---------- */
  .fundo-fb { position: fixed; inset: 0; background: rgba(0,0,0,.55); backdrop-filter: blur(2px); z-index: 70;
              opacity: 0; pointer-events: none; transition: opacity .2s; }
  .fundo-fb.aberto { opacity: 1; pointer-events: auto; }
  .gaveta-fb { position: fixed; top: 0; right: 0; bottom: 0; width: min(560px, 100%); z-index: 71; display: flex; flex-direction: column;
               background: var(--bg-panel-solid); border-left: 1px solid var(--border-forte); box-shadow: -20px 0 50px rgba(0,0,0,.4);
               transform: translateX(100%); transition: transform .25s ease; }
  .gaveta-fb.aberta { transform: translateX(0); }
  .cab-gaveta-fb { padding: 18px 22px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; gap: 10px; }
  .cab-gaveta-fb h2 { margin: 0; font-size: 16px; color: var(--fg); }
  .cab-gaveta-fb .sub { font-size: 11.5px; color: var(--fg-dim); margin-top: 2px; }
  /* X desenhado em SVG e centralizado pela grade: o caractere ✕ ficava torto pela métrica da fonte */
  .fechar-fb { background: none; border: 1px solid var(--border); color: var(--fg-dim); width: 32px; height: 32px; border-radius: 8px;
               cursor: pointer; flex-shrink: 0; display: grid; place-items: center; padding: 0; }
  .fechar-fb svg { width: 14px; height: 14px; display: block; }
  .fechar-fb:hover { color: var(--fg); border-color: var(--teal); }
  .corpo-gaveta-fb { flex: 1; overflow-y: auto; padding: 6px 22px 22px 22px; }
  .rodape-gaveta-fb { padding: 14px 22px; border-top: 1px solid var(--border); display: flex; gap: 10px; align-items: center; }
  .rodape-gaveta-fb .msg { flex: 1; font-size: 12px; color: var(--erro); }
  .aviso-edicao-fb { font-size: 11.5px; color: var(--fg-dim); background: rgba(var(--tinta),.04); border: 1px solid var(--border);
                     border-radius: 9px; padding: 9px 12px; margin-top: 14px; display: none; line-height: 1.5; }

  .etapa-fb { padding-top: 18px; }
  .etapa-fb + .etapa-fb { margin-top: 4px; border-top: 1px dashed rgba(var(--tinta),.08); }
  .etapa-fb .titulo-etapa { display: flex; align-items: center; gap: 8px; font-size: 12.5px; font-weight: 700; color: var(--fg); margin-bottom: 10px; }
  .etapa-fb .num { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; font-size: 10.5px; font-weight: 800;
                   background: rgba(45,184,207,.15); color: var(--teal); flex-shrink: 0; }
  .etapa-fb .ajuda { font-size: 11px; color: var(--fg-dim); font-weight: 400; margin-left: auto; }
  .rotulo-fb { display: block; font-size: 11px; color: var(--fg-dim); margin: 12px 0 6px 0; }

  .seg-fb { display: flex; background: rgba(var(--poco),.25); border: 1px solid var(--border); border-radius: 10px; padding: 3px; gap: 3px; }
  .seg-fb button { flex: 1; background: none; border: none; color: var(--fg-dim); font-size: 12.5px; font-weight: 600; padding: 8px 10px;
                   border-radius: 8px; cursor: pointer; font-family: inherit; }
  .seg-fb button:hover { color: var(--fg); }
  .seg-fb button.ativo { background: var(--teal); color: #0b0f14; }

  .seletor-pessoas-fb { border: 1px solid var(--border); border-radius: 10px; background: rgba(var(--poco),.15); padding: 10px; }
  .seletor-pessoas-fb .ferramentas { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
  .seletor-pessoas-fb .filtro { flex: 1 1 140px; background: rgba(var(--poco),.25); border: 1px solid var(--border); color: var(--fg);
                                border-radius: 7px; padding: 6px 9px; font-size: 12px; font-family: inherit; }
  .seletor-pessoas-fb .filtro:focus { outline: none; border-color: var(--teal); }
  .mini-fb { background: none; border: 1px solid var(--border); color: var(--fg-dim); border-radius: 7px; padding: 5px 9px; font-size: 11px;
             cursor: pointer; font-family: inherit; }
  .mini-fb:hover { color: var(--fg); border-color: var(--teal); }
  .chips-pessoas-fb { display: flex; flex-wrap: wrap; gap: 6px; max-height: 150px; overflow-y: auto; }
  .chip-pessoa-fb { background: rgba(var(--tinta),.04); border: 1px solid var(--border); color: var(--fg); border-radius: 999px;
                    padding: 5px 11px; font-size: 12px; cursor: pointer; font-family: inherit; display: inline-flex; align-items: center; gap: 6px; }
  .chip-pessoa-fb:hover { border-color: var(--teal); }
  .chip-pessoa-fb.marcado { background: rgba(45,184,207,.16); border-color: var(--teal); color: var(--fg); }
  .chip-pessoa-fb.marcado::before { content: "✓"; color: var(--teal); font-weight: 800; }
  .chip-pessoa-fb.bloqueado { opacity: .35; cursor: not-allowed; }
  .resumo-selecao-fb { font-size: 11px; color: var(--fg-dim); margin-top: 6px; }
  .aviso-geral-fb { font-size: 12px; color: var(--fg-dim); background: rgba(176,203,28,.07); border: 1px solid rgba(176,203,28,.25);
                    border-radius: 9px; padding: 10px 12px; }

  .equipes-fb { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 8px; }
  .equipe-opcao-fb { text-align: left; background: rgba(var(--tinta),.03); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px;
                     cursor: pointer; color: var(--fg); font-family: inherit; }
  .equipe-opcao-fb:hover { border-color: var(--teal); }
  .equipe-opcao-fb.ativo { border-color: var(--teal); background: rgba(45,184,207,.10); box-shadow: inset 0 0 0 1px var(--teal); }
  .equipe-opcao-fb .nome { font-size: 12.5px; font-weight: 700; }
  .equipe-opcao-fb .pessoas { font-size: 10.5px; color: var(--fg-dim); margin-top: 3px; line-height: 1.45; }
  .equipe-opcao-fb .pessoas.membros { color: var(--teal); }

  .corpo-gaveta-fb textarea, .corpo-gaveta-fb input[type="text"] { width: 100%; padding: 10px 12px; border-radius: 9px; border: 1px solid var(--border);
      background: rgba(var(--poco),.25); color: var(--fg); font-size: 13px; font-family: inherit; }
  .corpo-gaveta-fb textarea { min-height: 120px; resize: vertical; line-height: 1.55; }
  .corpo-gaveta-fb textarea:focus, .corpo-gaveta-fb input[type="text"]:focus { outline: none; border-color: var(--teal); }
  .contador-fb { text-align: right; font-size: 10.5px; color: var(--fg-dim); margin-top: 4px; }
  .seletor-estrelas { display: flex; gap: 4px; align-items: center; }
  .estrela-selecionavel { font-size: 22px; color: var(--fg-dim); cursor: pointer; transition: color .1s, transform .1s; user-select: none;
                          background: none; border: none; padding: 0 2px; font-family: inherit; }
  .estrela-selecionavel:hover { transform: scale(1.15); }
  .estrela-selecionavel.preenchida { color: var(--run); }
  .limpar-nota-fb { margin-left: 8px; }

  /* anexo: input escondido (continua acessível pelo teclado) + área de clicar/arrastar */
  .input-anexo-oculto { position: absolute; width: 1px; height: 1px; opacity: 0; overflow: hidden; }
  .zona-anexo-fb { display: flex; align-items: center; gap: 12px; padding: 14px 16px; cursor: pointer;
                   border: 1.5px dashed var(--border); border-radius: 10px; background: rgba(var(--poco),.15); font-size: 12.5px; color: var(--fg);
                   transition: border-color .15s, background .15s; }
  .zona-anexo-fb:hover, .zona-anexo-fb.arrastando { border-color: var(--teal); background: rgba(45,184,207,.06); }
  .input-anexo-oculto:focus-visible + .zona-anexo-fb { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.16); }
  .icone-anexo { width: 34px; height: 34px; border-radius: 9px; display: grid; place-items: center; background: rgba(45,184,207,.12);
                 color: var(--teal); font-size: 16px; flex-shrink: 0; }
  .zona-anexo-fb strong { color: var(--teal); font-weight: 600; }
  .zona-anexo-fb small { display: block; color: var(--fg-dim); font-size: 11px; margin-top: 2px; }
  .anexo-escolhido-fb { display: none; align-items: center; gap: 12px; padding: 10px 14px; border-radius: 10px;
                        border: 1px solid var(--border); background: rgba(var(--tinta),.03); }
  .anexo-escolhido-fb.visivel { display: flex; }
  .anexo-escolhido-fb.grande { border-color: rgba(241,76,76,.5); background: rgba(241,76,76,.06); }
  .anexo-escolhido-fb .icone-anexo { background: rgba(176,203,28,.14); color: var(--lime); width: 30px; height: 30px; font-size: 14px; }
  .anexo-escolhido-fb.grande .icone-anexo { background: rgba(241,76,76,.14); color: var(--erro); }
  .anexo-escolhido-fb .info-anexo { flex: 1; min-width: 0; }
  .anexo-escolhido-fb .nome-anexo { font-size: 12.5px; color: var(--fg); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .anexo-escolhido-fb .meta-anexo { font-size: 11px; color: var(--fg-dim); }
  .anexo-escolhido-fb.grande .meta-anexo { color: var(--erro); }
  .anexo-fixo-fb { font-size: 12px; color: var(--fg-dim); }

  .toast-fb { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%) translateY(20px); opacity: 0; z-index: 80;
              background: var(--bg-panel-solid); border: 1px solid var(--border-forte); color: var(--fg); padding: 10px 18px; border-radius: 10px;
              font-size: 13px; transition: opacity .2s, transform .2s; pointer-events: none; }
  .toast-fb.mostrar { opacity: 1; transform: translateX(-50%) translateY(0); }

  @media (max-width: 640px) {
    .barra-fb .campo-fb, .abas-fb { flex: 1 1 100%; }
    .abas-fb button { flex: 1; justify-content: center; }
    .acoes-fb { margin-left: 0; }
  }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="topo-fb">
      <div>
        <h1>Feedbacks e Alinhamentos</h1>
        <div class="sub">Registro privado, visível só pra quem tem essa permissão.</div>
      </div>
      <button class="btn-accent btn-novo-fb" onclick="abrirFormFB()">+ Novo registro</button>
    </div>

    <div class="barra-fb">
      <label class="busca-fb">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input type="text" id="fb-filtro-busca" placeholder="Buscar por pessoa, autor ou texto..." oninput="agendarCargaFB()">
      </label>
      <div class="abas-fb" id="fb-abas-tipo">
        <button class="ativa" data-tipo="" onclick="trocarAbaTipoFB('')">Todos <span class="qtd" id="fb-qtd-todos">0</span></button>
        <button data-tipo="Feedback" onclick="trocarAbaTipoFB('Feedback')">Feedbacks <span class="qtd" id="fb-qtd-feedback">0</span></button>
        <button data-tipo="Alinhamento" onclick="trocarAbaTipoFB('Alinhamento')">Alinhamentos <span class="qtd" id="fb-qtd-alinhamento">0</span></button>
      </div>
      <select class="campo-fb" id="fb-filtro-pessoa" onchange="carregarListaFB()"><option value="">Todas as pessoas</option></select>
      <select class="campo-fb" id="fb-filtro-equipe" onchange="carregarListaFB()"><option value="">Todas as equipes</option></select>
    </div>

    <div class="nota-equipes-fb" id="fb-nota-equipes"></div>
    <div class="lista-fb" id="fb-lista"><div class="vazio-fb">Carregando...</div></div>
  </div>

  <div class="fundo-fb" id="fb-fundo" onclick="fecharFormFB()"></div>
  <aside class="gaveta-fb" id="fb-gaveta" aria-hidden="true">
    <div class="cab-gaveta-fb">
      <div>
        <h2 id="fb-titulo-form">Novo registro</h2>
        <div class="sub" id="fb-sub-form">Preencha as etapas e salve. O aviso por e-mail sai na hora.</div>
      </div>
      <button class="fechar-fb" onclick="fecharFormFB()" title="Fechar (Esc)" aria-label="Fechar">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
      </button>
    </div>
    <div class="corpo-gaveta-fb">
      <div class="aviso-edicao-fb" id="fb-aviso-edicao">
        A edição não manda e-mail de novo (o aviso sai só quando o registro é criado) e o anexo não muda.
      </div>

      <div class="etapa-fb">
        <div class="titulo-etapa"><span class="num">1</span> O que é</div>
        <div class="seg-fb" id="fb-seg-tipo">
          <button type="button" data-valor="Feedback" class="ativo" onclick="escolherTipoFB('Feedback')">Feedback</button>
          <button type="button" data-valor="Alinhamento" onclick="escolherTipoFB('Alinhamento')">Alinhamento</button>
        </div>
      </div>

      <div class="etapa-fb">
        <div class="titulo-etapa"><span class="num">2</span> Pra quem</div>
        <div class="seg-fb" id="fb-seg-escopo">
          <button type="button" data-valor="individual" class="ativo" onclick="escolherEscopoFB('individual')">Uma pessoa</button>
          <button type="button" data-valor="grupo" onclick="escolherEscopoFB('grupo')">Grupo</button>
          <button type="button" data-valor="geral" onclick="escolherEscopoFB('geral')">Toda a equipe</button>
        </div>
        <div id="fb-bloco-alvo" style="margin-top:10px"></div>
      </div>

      <div class="etapa-fb">
        <div class="titulo-etapa"><span class="num">3</span> Quem fez <span class="ajuda">pode ser mais de uma pessoa</span></div>
        <div id="fb-bloco-autores"></div>
      </div>

      <div class="etapa-fb">
        <div class="titulo-etapa"><span class="num">4</span> Quem é avisado por e-mail</div>
        <div class="equipes-fb" id="fb-equipes"></div>
        <div class="aviso-equipe-fb" id="fb-aviso-equipe" style="display:none"></div>
      </div>

      <div class="etapa-fb">
        <div class="titulo-etapa"><span class="num">5</span> Conteúdo</div>
        <textarea id="fb-texto" maxlength="2000" placeholder="Escreva o feedback ou alinhamento..." oninput="atualizarContadorFB()"></textarea>
        <div class="contador-fb" id="fb-contador">0 / 2000</div>
        <span class="rotulo-fb">Nota geral (opcional)</span>
        <div class="seletor-estrelas" id="fb-seletor-estrelas"></div>
        <span class="rotulo-fb">Link do Canva (opcional)</span>
        <input type="text" id="fb-link-canva" placeholder="https://www.canva.com/design/...">
        <span class="rotulo-fb">Anexo (opcional)</span>
        <div id="fb-bloco-anexo">
          <input type="file" id="fb-anexo-input" class="input-anexo-oculto" onchange="mostrarNomeAnexoFB()">
          <label for="fb-anexo-input" class="zona-anexo-fb" id="fb-zona-anexo">
            <span class="icone-anexo">📎</span>
            <span><strong>Clique pra escolher</strong> ou arraste o arquivo aqui<small>Qualquer tipo de arquivo, até 10MB</small></span>
          </label>
          <div class="anexo-escolhido-fb" id="fb-anexo-escolhido">
            <span class="icone-anexo" id="fb-anexo-icone">📄</span>
            <div class="info-anexo">
              <div class="nome-anexo" id="fb-anexo-nome"></div>
              <div class="meta-anexo" id="fb-anexo-meta"></div>
            </div>
            <button type="button" class="mini-fb" onclick="document.getElementById('fb-anexo-input').click()">Trocar</button>
            <button type="button" class="mini-fb" onclick="removerAnexoFB()">Remover</button>
          </div>
        </div>
        <div class="anexo-fixo-fb" id="fb-anexo-fixo" style="display:none"></div>
      </div>
    </div>
    <div class="rodape-gaveta-fb">
      <div class="msg" id="fb-erro"></div>
      <button class="mini-fb" style="padding:9px 14px; font-size:12.5px" onclick="fecharFormFB()">Cancelar</button>
      <button class="btn-accent" id="fb-btn-salvar" style="padding:9px 18px" onclick="salvarFeedbackFB()">Salvar</button>
    </div>
  </aside>

  <div class="toast-fb" id="fb-toast"></div>

  __FOOTER__

<script>
const EQUIPES_FB = __EQUIPES_FEEDBACK__;          // [{nome, pessoas: [nomes]}] - só nomes, sem e-mail
const USUARIO_LOGADO_FB = __USUARIO_LOGADO_FB__;
const TAMANHO_MAXIMO_ANEXO_FB = 10 * 1024 * 1024; // mesmo limite do backend
let usuariosFB = [];
let registrosFB = [];
let abaTipoFB = '';
let formFB = null;   // estado do formulário aberto

function escaparHtmlFB(txt) {
  return String(txt == null ? '' : txt).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function nomeDeFB(login) {
  const u = usuariosFB.find(x => x.usuario === login);
  return u ? (u.nome || u.usuario) : login;
}

function juntarNomesFB(nomes) {
  if (nomes.length <= 1) return nomes.join('');
  return nomes.slice(0, -1).join(', ') + ' e ' + nomes[nomes.length - 1];
}

function mostrarToastFB(msg) {
  const t = document.getElementById('fb-toast');
  t.innerText = msg;
  t.classList.add('mostrar');
  clearTimeout(window._toastFB);
  window._toastFB = setTimeout(() => t.classList.remove('mostrar'), 2800);
}

// login de teste ("teste", "teste123"...) e desativados não aparecem pra escolher
function pessoaVisivelFB(u) {
  if (u.ativo === false) return false;
  return !/^teste/i.test(u.usuario || '') && !/^teste/i.test(u.nome || '');
}

async function inicializarFB() {
  try {
    const resp = await fetch('/api/usuarios');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    usuariosFB = (dados.usuarios || []).filter(pessoaVisivelFB);
    usuariosFB.sort((a, b) => (a.nome || a.usuario).localeCompare(b.nome || b.usuario));
  } catch (e) {
    console.warn('Erro ao carregar usuários pra Feedbacks:', e);
  }
  document.getElementById('fb-filtro-pessoa').innerHTML = '<option value="">Todas as pessoas</option>' +
    usuariosFB.map(u => '<option value="' + escaparHtmlFB(u.usuario) + '">' + escaparHtmlFB(u.nome || u.usuario) + '</option>').join('');
  document.getElementById('fb-filtro-equipe').innerHTML = '<option value="">Todas as equipes</option>' +
    EQUIPES_FB.map(e => '<option value="' + escaparHtmlFB(e.nome) + '">' + escaparHtmlFB(e.nome) + '</option>').join('');
  // veio do Perfil (/feedbacks?usuario=X): já filtra
  const usuarioUrl = new URLSearchParams(window.location.search).get('usuario');
  if (usuarioUrl) document.getElementById('fb-filtro-pessoa').value = usuarioUrl;
  carregarListaFB();
}

// ---------------- lista ----------------
function agendarCargaFB() {
  clearTimeout(window._cargaFB);
  window._cargaFB = setTimeout(carregarListaFB, 250);
}

async function carregarListaFB() {
  const parametros = new URLSearchParams();
  const busca = document.getElementById('fb-filtro-busca').value.trim();
  const pessoa = document.getElementById('fb-filtro-pessoa').value;
  const equipe = document.getElementById('fb-filtro-equipe').value;
  if (busca) parametros.set('busca', busca);
  if (pessoa) parametros.set('usuario', pessoa);
  if (equipe) parametros.set('equipe', equipe);
  try {
    const resp = await fetch('/api/feedbacks/listar' + (parametros.toString() ? '?' + parametros : ''));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { document.getElementById('fb-lista').innerHTML = '<div class="vazio-fb">' + escaparHtmlFB(dados.erro || 'Erro ao carregar.') + '</div>'; return; }
    registrosFB = dados.registros || [];
    respostaTodasFB = !!dados.ve_todas_equipes;
    if (Array.isArray(dados.equipes_visiveis)) atualizarEquipesVisiveisFB(dados.equipes_visiveis);
    desenharListaFB();
    irParaRegistroDaUrlFB();
  } catch (e) {
    document.getElementById('fb-lista').innerHTML = '<div class="vazio-fb">Erro ao carregar: ' + escaparHtmlFB(e.message) + '</div>';
  }
}

// Cada equipe só vê os próprios registros (2.35.2.0): a nota diz quais a pessoa vê
// e o filtro de equipe só oferece essas
let equipesVisiveisFB = null;
let respostaTodasFB = false;  // a gerência vê todas as equipes (2.35.5.1)
function atualizarEquipesVisiveisFB(equipes) {
  equipesVisiveisFB = equipes;
  const todas = equipes.length && equipes.length === EQUIPES_FB.length;
  document.getElementById('fb-nota-equipes').innerHTML = !equipes.length
    ? '&#128274; Você não recebe e-mails de nenhuma equipe: aparecem só os registros que você fez.'
    : (todas && respostaTodasFB
      ? '&#128275; Você vê os registros de <b>todas as equipes</b>.'
      : '&#128274; Você vê os registros de <b>' + escaparHtmlFB(juntarNomesFB(equipes)) + '</b> (as equipes que você recebe por e-mail) e os que você registrou.');
  const filtro = document.getElementById('fb-filtro-equipe');
  const atual = filtro.value;
  filtro.innerHTML = '<option value="">Todas as minhas equipes</option>' +
    equipes.map(e => '<option value="' + escaparHtmlFB(e) + '">' + escaparHtmlFB(e) + '</option>').join('');
  filtro.value = equipes.includes(atual) ? atual : '';
}

function trocarAbaTipoFB(tipo) {
  abaTipoFB = tipo;
  document.querySelectorAll('#fb-abas-tipo button').forEach(b => b.classList.toggle('ativa', b.dataset.tipo === tipo));
  desenharListaFB();
}

function dataLegivelFB(texto) {
  const m = /^([0-9]{4})-([0-9]{2})-([0-9]{2}) ([0-9]{2}):([0-9]{2})/.exec(texto || '');
  return m ? m[3] + '/' + m[2] + '/' + m[1] + ' ' + m[4] + ':' + m[5] : (texto || '');
}

function linkPessoaFB(login) {
  return '<a href="/perfil/' + encodeURIComponent(login) + '">' + escaparHtmlFB(nomeDeFB(login)) + '</a>';
}

function paraQuemFB(f) {
  if (f.escopo === 'geral') return 'Toda a equipe';
  if (f.escopo === 'grupo' && Array.isArray(f.usuarios) && f.usuarios.length) {
    const links = f.usuarios.map(linkPessoaFB);
    return links.length === 1 ? links[0] : links.slice(0, -1).join(', ') + ' e ' + links[links.length - 1];
  }
  if (f.usuario) return linkPessoaFB(f.usuario);
  return escaparHtmlFB(f.descricao_alvo || '-');
}

function desenharListaFB() {
  const lista = document.getElementById('fb-lista');
  const contar = t => registrosFB.filter(r => (r.tipo || 'Feedback') === t).length;
  document.getElementById('fb-qtd-todos').innerText = registrosFB.length;
  document.getElementById('fb-qtd-feedback').innerText = contar('Feedback');
  document.getElementById('fb-qtd-alinhamento').innerText = contar('Alinhamento');
  const visiveis = abaTipoFB ? registrosFB.filter(r => (r.tipo || 'Feedback') === abaTipoFB) : registrosFB;
  if (!visiveis.length) {
    const filtrando = document.getElementById('fb-filtro-busca').value || document.getElementById('fb-filtro-pessoa').value
      || document.getElementById('fb-filtro-equipe').value || abaTipoFB;
    lista.innerHTML = filtrando
      ? '<div class="vazio-fb"><div class="grande">Nada encontrado</div>Nenhum registro bate com os filtros.</div>'
      : '<div class="vazio-fb"><div class="grande">Nenhum registro ainda</div>Clique em "+ Novo registro" pra começar.</div>';
    return;
  }
  lista.innerHTML = visiveis.map(f => {
    const tipo = f.tipo || 'Feedback';
    const escopo = { individual: 'Individual', grupo: 'Grupo', geral: 'Geral' }[f.escopo] || 'Individual';
    const autores = (f.autores && f.autores.length ? f.autores : [f.autor]).filter(Boolean);
    const nota = f.nota ? '<span class="estrelas-fb" title="Nota ' + f.nota + ' de 5">' + '★'.repeat(f.nota) + '☆'.repeat(5 - f.nota) + '</span>' : '';
    const longo = (f.texto || '').length > 320 || (f.texto || '').split(String.fromCharCode(10)).length > 5;  // 10 = quebra de linha
    const anexos = [
      f.link_canva ? '<a class="anexo-link-fb" target="_blank" rel="noopener" href="' + escaparHtmlFB(f.link_canva) + '">🔗 Slide no Canva</a>' : '',
      f.anexo ? '<a class="anexo-link-fb" href="/feedback-anexo/' + f.id + '">📎 ' + escaparHtmlFB(f.anexo_nome_original || 'Anexo') + '</a>' : '',
    ].join('');
    return '<div class="card-fb ' + (tipo === 'Alinhamento' ? 'alinhamento' : '') + '" id="fb-card-' + f.id + '">' +
      '<div class="linha1"><div>' +
        '<div class="para">' + paraQuemFB(f) + '</div>' +
        '<div class="por">por <b>' + escaparHtmlFB(juntarNomesFB(autores.map(nomeDeFB))) + '</b></div>' +
      '</div><div class="data">' + escaparHtmlFB(dataLegivelFB(f.criado_em)) +
        (f.editado_em ? ' <span class="editado-fb" title="Editado por ' + escaparHtmlFB(nomeDeFB(f.editado_por || '')) + ' em ' + escaparHtmlFB(dataLegivelFB(f.editado_em)) + '">· editado</span>' : '') +
      '</div></div>' +
      '<div class="etiquetas-fb"><span class="etq-fb tipo">' + escaparHtmlFB(tipo) + '</span><span class="etq-fb neutra">' + escopo + '</span>' +
        '<span class="etq-fb equipe" title="Equipe avisada por e-mail">✉ ' + escaparHtmlFB(f.equipe || '') + '</span>' + nota + '</div>' +
      '<div class="texto-fb' + (longo ? ' recolhido' : '') + '" id="fb-texto-' + f.id + '">' + escaparHtmlFB(f.texto || '') + '</div>' +
      (longo ? '<button class="ver-mais-fb" onclick="alternarTextoFB(' + f.id + ', this)">Ver tudo</button>' : '') +
      '<div class="rodape-card-fb"><div class="anexos-fb">' + anexos + '</div><div class="acoes-fb">' +
        '<button class="acao-fb" onclick="abrirFormFB(' + f.id + ')">Editar</button>' +
        '<button class="acao-fb perigo" onclick="removerFeedbackFB(' + f.id + ')">Remover</button>' +
      '</div></div></div>';
  }).join('');
}

// /feedbacks?registro=ID (link "Ver alinhamento" do mural): rola até o registro, destaca e abre o texto todo
let registroUrlFeitoFB = false;
function irParaRegistroDaUrlFB() {
  if (registroUrlFeitoFB) return;
  registroUrlFeitoFB = true;
  const id = new URLSearchParams(window.location.search).get('registro');
  if (!id) return;
  const card = document.getElementById('fb-card-' + id);
  if (!card) { mostrarToastFB('Esse registro não está na sua lista (pode ter sido removido).'); return; }
  const texto = document.getElementById('fb-texto-' + id);
  if (texto && texto.classList.contains('recolhido')) {
    texto.classList.remove('recolhido');
    const botao = card.querySelector('.ver-mais-fb');
    if (botao) botao.innerText = 'Ver menos';
  }
  card.classList.add('destacado-fb');
  setTimeout(() => card.scrollIntoView({behavior: 'smooth', block: 'center'}), 200);
}

function alternarTextoFB(id, botao) {
  const el = document.getElementById('fb-texto-' + id);
  const recolhido = el.classList.toggle('recolhido');
  botao.innerText = recolhido ? 'Ver tudo' : 'Ver menos';
}

async function removerFeedbackFB(id) {
  const f = registrosFB.find(r => r.id === id);
  const descricao = f ? (f.tipo || 'Feedback').toLowerCase() + ' pra ' + (f.descricao_alvo || '') : 'esse registro';
  if (!confirm('Remover ' + descricao + '? Não dá pra desfazer.')) return;
  try {
    const resp = await fetch('/api/feedback-usuario/excluir', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: 'id=' + encodeURIComponent(id),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { alert(dados.erro || 'Não foi possível remover.'); return; }
    mostrarToastFB('Registro removido.');
    carregarListaFB();
  } catch (e) {
    alert('Erro: ' + e.message);
  }
}

// ---------------- formulário (gaveta) ----------------
function abrirFormFB(id) {
  const f = id ? registrosFB.find(r => r.id === id) : null;
  formFB = {
    id: f ? f.id : null,
    tipo: f ? (f.tipo || 'Feedback') : 'Feedback',
    escopo: f ? (f.escopo || 'individual') : 'individual',
    individual: f && f.escopo === 'individual' ? (f.usuario || '') : '',
    grupo: new Set(f && f.escopo === 'grupo' ? (f.usuarios || []) : []),
    autores: new Set(f ? ((f.autores && f.autores.length) ? f.autores : [f.autor]) : [USUARIO_LOGADO_FB]),
    equipe: f && f.equipe ? f.equipe : equipePadraoFB(),
    nota: f ? (f.nota || 0) : 0,
    equipeManual: !!f,  // equipe escolhida à mão (ou registro já salvo): não troca sozinha
    filtroAlvo: '', filtroAutores: '',
    alterado: false,
  };
  document.getElementById('fb-titulo-form').innerText = f ? 'Editar registro' : 'Novo registro';
  document.getElementById('fb-sub-form').innerText = f
    ? 'Criado em ' + dataLegivelFB(f.criado_em) + '. Ajuste o que precisar e salve.'
    : 'Preencha as etapas e salve. O aviso por e-mail sai na hora.';
  document.getElementById('fb-aviso-edicao').style.display = f ? 'block' : 'none';
  document.getElementById('fb-btn-salvar').innerText = f ? 'Salvar alterações' : 'Salvar e avisar';
  document.getElementById('fb-texto').value = f ? (f.texto || '') : '';
  document.getElementById('fb-link-canva').value = f ? (f.link_canva || '') : '';
  document.getElementById('fb-anexo-input').value = '';
  document.getElementById('fb-bloco-anexo').style.display = f ? 'none' : '';
  const fixo = document.getElementById('fb-anexo-fixo');
  fixo.style.display = f ? 'block' : 'none';
  fixo.innerText = f ? (f.anexo ? '📎 ' + (f.anexo_nome_original || 'Anexo') + ' (o anexo não muda na edição)' : 'Sem anexo (anexo só na criação).') : '';
  document.getElementById('fb-erro').innerText = '';
  escolherTipoFB(formFB.tipo, true);
  escolherEscopoFB(formFB.escopo, true);
  desenharAutoresFB();
  desenharEquipesFB();
  desenharEstrelasFB();
  atualizarContadorFB();
  mostrarNomeAnexoFB();
  formFB.alterado = false;
  document.getElementById('fb-fundo').classList.add('aberto');
  const gaveta = document.getElementById('fb-gaveta');
  gaveta.classList.add('aberta');
  gaveta.setAttribute('aria-hidden', 'false');
  setTimeout(() => document.getElementById('fb-texto').focus({ preventScroll: true }), 260);
}

function fecharFormFB(forcar) {
  if (!formFB) return;
  if (!forcar && formFB.alterado && !confirm('Fechar sem salvar? O que foi preenchido vai ser perdido.')) return;
  formFB = null;
  document.getElementById('fb-fundo').classList.remove('aberto');
  const gaveta = document.getElementById('fb-gaveta');
  gaveta.classList.remove('aberta');
  gaveta.setAttribute('aria-hidden', 'true');
}

document.addEventListener('keydown', e => { if (e.key === 'Escape' && formFB) fecharFormFB(); });
document.getElementById('fb-gaveta').addEventListener('input', () => { if (formFB) formFB.alterado = true; });

function marcarSegmentoFB(id, valor) {
  document.querySelectorAll('#' + id + ' button').forEach(b => b.classList.toggle('ativo', b.dataset.valor === valor));
}

function escolherTipoFB(tipo, inicial) {
  formFB.tipo = tipo;
  if (!inicial) formFB.alterado = true;
  marcarSegmentoFB('fb-seg-tipo', tipo);
}

function escolherEscopoFB(escopo, inicial) {
  formFB.escopo = escopo;
  if (!inicial) formFB.alterado = true;
  marcarSegmentoFB('fb-seg-escopo', escopo);
  desenharAlvoFB();
}

// seletor de pessoas em chips (um só ou vários), com filtro por nome
function htmlSeletorPessoasFB(qual, marcados, multi, ferramentasExtra) {
  const filtro = (qual === 'alvo' ? formFB.filtroAlvo : formFB.filtroAutores).toLowerCase();
  const bloqueados = qual === 'alvo' ? formFB.autores : new Set(formFB.escopo === 'individual' ? [formFB.individual] : [...formFB.grupo]);
  const chips = usuariosFB
    .filter(u => !filtro || (u.nome || u.usuario).toLowerCase().includes(filtro) || u.usuario.toLowerCase().includes(filtro))
    .map(u => {
      const marcado = marcados.has(u.usuario);
      const bloqueado = !marcado && bloqueados.has(u.usuario);
      return '<button type="button" class="chip-pessoa-fb' + (marcado ? ' marcado' : '') + (bloqueado ? ' bloqueado' : '') + '"' +
        (bloqueado ? ' disabled title="' + (qual === 'alvo' ? 'É autor deste registro' : 'Está recebendo este registro') + '"' : '') +
        ' onclick="alternarPessoaFB(' + "'" + qual + "', '" + escaparHtmlFB(u.usuario) + "'" + ')">' + escaparHtmlFB(u.nome || u.usuario) + '</button>';
    }).join('') || '<span class="resumo-selecao-fb">Ninguém com esse nome.</span>';
  const resumo = marcados.size
    ? (multi ? marcados.size + ' selecionada(s): ' : 'Selecionada: ') + escaparHtmlFB(juntarNomesFB([...marcados].map(nomeDeFB)))
    : (multi ? 'Ninguém selecionado ainda.' : 'Escolha uma pessoa.');
  return '<div class="seletor-pessoas-fb"><div class="ferramentas">' +
      '<input class="filtro" placeholder="Filtrar por nome..." value="' + escaparHtmlFB(qual === 'alvo' ? formFB.filtroAlvo : formFB.filtroAutores) + '"' +
      ' oninput="filtrarPessoasFB(' + "'" + qual + "'" + ', this.value)">' + (ferramentasExtra || '') +
    '</div><div class="chips-pessoas-fb">' + chips + '</div></div>' +
    '<div class="resumo-selecao-fb">' + resumo + '</div>';
}

function desenharAlvoFB() {
  const bloco = document.getElementById('fb-bloco-alvo');
  if (formFB.escopo === 'geral') {
    bloco.innerHTML = '<div class="aviso-geral-fb">Alinhamento pra toda a equipe: não fica ligado a uma pessoa e aparece só na lista geral.</div>';
    return;
  }
  if (formFB.escopo === 'individual') {
    bloco.innerHTML = htmlSeletorPessoasFB('alvo', new Set(formFB.individual ? [formFB.individual] : []), false, '');
    return;
  }
  const atalhos = '<button type="button" class="mini-fb" onclick="marcarGrupoPorEquipeFB(' + "'Suporte'" + ')">+ Suporte</button>' +
    '<button type="button" class="mini-fb" onclick="marcarGrupoPorEquipeFB(' + "'Monitoramento'" + ')">+ Monitoramento</button>' +
    EQUIPES_FB.filter(e => (e.membros || []).length).map(e =>
      '<button type="button" class="mini-fb" onclick="marcarGrupoPorEquipeFB(' + "'" + escaparHtmlFB(e.nome) + "'" + ')">+ ' + escaparHtmlFB(e.nome) + '</button>').join('') +
    '<button type="button" class="mini-fb" onclick="marcarGrupoPorEquipeFB(null)">Limpar</button>';
  bloco.innerHTML = htmlSeletorPessoasFB('alvo', formFB.grupo, true, atalhos);
}

function desenharAutoresFB() {
  document.getElementById('fb-bloco-autores').innerHTML = htmlSeletorPessoasFB('autores', formFB.autores, true, '');
}

function filtrarPessoasFB(qual, valor) {
  if (qual === 'alvo') formFB.filtroAlvo = valor; else formFB.filtroAutores = valor;
  const desenhar = qual === 'alvo' ? desenharAlvoFB : desenharAutoresFB;
  desenhar();
  const campo = document.querySelector((qual === 'alvo' ? '#fb-bloco-alvo' : '#fb-bloco-autores') + ' .filtro');
  campo.focus();
  campo.setSelectionRange(valor.length, valor.length);
}

function alternarPessoaFB(qual, login) {
  formFB.alterado = true;
  if (qual === 'autores') {
    if (formFB.autores.has(login)) formFB.autores.delete(login); else formFB.autores.add(login);
  } else if (formFB.escopo === 'individual') {
    formFB.individual = formFB.individual === login ? '' : login;
  } else {
    if (formFB.grupo.has(login)) formFB.grupo.delete(login); else formFB.grupo.add(login);
  }
  if (qual === 'alvo') sugerirEquipeFB();
  desenharAlvoFB();
  desenharAutoresFB();
}

// Quem recebe é todo de uma equipe com membros fixos (ex.: Serviços)? Já marca essa
// equipe pro aviso por e-mail, enquanto ninguém escolheu a equipe à mão
function sugerirEquipeFB() {
  if (formFB.equipeManual) return;
  const alvos = formFB.escopo === 'individual' ? (formFB.individual ? [formFB.individual] : []) : [...formFB.grupo];
  const equipe = alvos.length ? EQUIPES_FB.find(e => (e.membros || []).length && alvos.every(a => e.membros.includes(a))) : null;
  const nova = equipe ? equipe.nome : equipePadraoFB();
  if (nova !== formFB.equipe) { formFB.equipe = nova; desenharEquipesFB(); }
}

// "+ Suporte"/"+ Monitoramento" marcam a equipe inteira (12x36 entra nas duas); autores ficam de fora
function marcarGrupoPorEquipeFB(equipe) {
  formFB.alterado = true;
  const fixa = EQUIPES_FB.find(e => e.nome === equipe && (e.membros || []).length);
  if (equipe === null) { formFB.grupo.clear(); }
  else if (fixa) {
    fixa.membros.forEach(login => {
      if (usuariosFB.some(u => u.usuario === login) && !formFB.autores.has(login)) formFB.grupo.add(login);
    });
    // 3.2.5.0: quem tem essa equipe no cadastro (ex.: Serviços) entra junto
    usuariosFB.forEach(u => { if (u.atribuicao === equipe && !formFB.autores.has(u.usuario)) formFB.grupo.add(u.usuario); });
  } else {
    usuariosFB.forEach(u => {
      const atribuicao = u.atribuicao || 'Suporte';
      if ((atribuicao === equipe || atribuicao === 'Suporte e Monitoramento') && !formFB.autores.has(u.usuario)) formFB.grupo.add(u.usuario);
    });
  }
  sugerirEquipeFB();
  desenharAlvoFB();
  desenharAutoresFB();
}

function desenharEquipesFB() {
  document.getElementById('fb-equipes').innerHTML = EQUIPES_FB.map(e =>
    '<button type="button" class="equipe-opcao-fb' + (e.nome === formFB.equipe ? ' ativo' : '') + '" onclick="escolherEquipeFB(' + "'" + escaparHtmlFB(e.nome) + "'" + ')">' +
      '<div class="nome">' + escaparHtmlFB(e.nome) + '</div><div class="pessoas">' + escaparHtmlFB(e.pessoas.join(', ')) + '</div>' +
      ((e.membros || []).length ? '<div class="pessoas membros">Equipe: ' + escaparHtmlFB(juntarNomesFB(e.membros.map(nomeDeFB))) + '</div>' : '') +
      '</button>'
  ).join('');
  avisarEquipeForaFB();
}

// equipe que o formulário já traz marcada: a primeira que a pessoa recebe (antes era sempre Monitoramento)
function equipePadraoFB() {
  if (equipesVisiveisFB && equipesVisiveisFB.length) return equipesVisiveisFB[0];
  return EQUIPES_FB[0] ? EQUIPES_FB[0].nome : '';
}

function avisarEquipeForaFB() {
  const aviso = document.getElementById('fb-aviso-equipe');
  const fora = equipesVisiveisFB && formFB.equipe && !equipesVisiveisFB.includes(formFB.equipe);
  aviso.style.display = fora ? 'block' : 'none';
  if (fora) aviso.innerText = 'Você não recebe os e-mails de ' + formFB.equipe + ': o registro fica visível pra essa equipe e, além dela, só pra você (que registrou) e pros autores.';
}

function escolherEquipeFB(nome) {
  formFB.equipe = nome;
  formFB.equipeManual = true;
  formFB.alterado = true;
  desenharEquipesFB();
}

function desenharEstrelasFB() {
  let html = '';
  for (let v = 1; v <= 5; v++) {
    html += '<button type="button" class="estrela-selecionavel' + (v <= formFB.nota ? ' preenchida' : '') + '" onclick="escolherNotaFB(' + v + ')" title="' + v + ' de 5">' + (v <= formFB.nota ? '★' : '☆') + '</button>';
  }
  if (formFB.nota) html += '<button type="button" class="mini-fb limpar-nota-fb" onclick="escolherNotaFB(0)">Sem nota</button>';
  document.getElementById('fb-seletor-estrelas').innerHTML = html;
}

function escolherNotaFB(valor) {
  formFB.nota = formFB.nota === valor ? 0 : valor;
  formFB.alterado = true;
  desenharEstrelasFB();
}

function atualizarContadorFB() {
  document.getElementById('fb-contador').innerText = document.getElementById('fb-texto').value.length + ' / 2000';
}

// ---------------- anexo ----------------
function tamanhoLegivelFB(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1).replace('.', ',') + ' MB';
}

function mostrarNomeAnexoFB() {
  const arquivo = document.getElementById('fb-anexo-input').files[0];
  const zona = document.getElementById('fb-zona-anexo');
  const cartao = document.getElementById('fb-anexo-escolhido');
  if (!arquivo) { zona.style.display = ''; cartao.classList.remove('visivel', 'grande'); return; }
  const grande = arquivo.size > TAMANHO_MAXIMO_ANEXO_FB;
  zona.style.display = 'none';
  cartao.classList.add('visivel');
  cartao.classList.toggle('grande', grande);
  document.getElementById('fb-anexo-icone').textContent = grande ? '⚠' : '📄';
  document.getElementById('fb-anexo-nome').textContent = arquivo.name;
  document.getElementById('fb-anexo-nome').title = arquivo.name;
  document.getElementById('fb-anexo-meta').textContent = tamanhoLegivelFB(arquivo.size) +
    (grande ? ' · maior que o limite de 10MB, escolha outro arquivo' : ' · vai junto com o registro');
  if (formFB) formFB.alterado = true;
}

function removerAnexoFB() {
  document.getElementById('fb-anexo-input').value = '';
  mostrarNomeAnexoFB();
}

(function () {
  const zona = document.getElementById('fb-zona-anexo');
  ['dragenter', 'dragover'].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add('arrastando'); }));
  ['dragleave', 'drop'].forEach(ev => zona.addEventListener(ev, () => zona.classList.remove('arrastando')));
  zona.addEventListener('drop', e => {
    e.preventDefault();
    const arquivos = e.dataTransfer && e.dataTransfer.files;
    if (!arquivos || !arquivos.length) return;
    const transferencia = new DataTransfer();
    transferencia.items.add(arquivos[0]);   // um arquivo por registro
    document.getElementById('fb-anexo-input').files = transferencia.files;
    mostrarNomeAnexoFB();
  });
})();

function lerArquivoComoDataURL(arquivo) {
  return new Promise((resolve, reject) => {
    const leitor = new FileReader();
    leitor.onload = () => resolve(leitor.result);
    leitor.onerror = () => reject(leitor.error);
    leitor.readAsDataURL(arquivo);
  });
}

// ---------------- salvar ----------------
async function salvarFeedbackFB() {
  const erroEl = document.getElementById('fb-erro');
  erroEl.innerText = '';
  const texto = document.getElementById('fb-texto').value.trim();
  const linkCanva = document.getElementById('fb-link-canva').value.trim();
  const autores = [...formFB.autores];
  if (formFB.escopo === 'individual' && !formFB.individual) { erroEl.innerText = 'Etapa 2: escolha a pessoa.'; return; }
  if (formFB.escopo === 'grupo' && !formFB.grupo.size) { erroEl.innerText = 'Etapa 2: escolha ao menos uma pessoa pro grupo.'; return; }
  if (!autores.length) { erroEl.innerText = 'Etapa 3: marque ao menos um autor.'; return; }
  if (!texto) { erroEl.innerText = 'Etapa 5: escreva o texto.'; document.getElementById('fb-texto').focus(); return; }
  if (linkCanva && !(linkCanva.startsWith('http://') || linkCanva.startsWith('https://'))) { erroEl.innerText = 'O link do Canva precisa começar com http:// ou https://'; return; }

  const campos = new URLSearchParams({
    escopo: formFB.escopo, texto: texto, nota: formFB.nota || '', tipo: formFB.tipo, link_canva: linkCanva,
    autores: autores.join(','), equipe: formFB.equipe,
  });
  if (formFB.id !== null) campos.set('id', formFB.id);
  if (formFB.escopo === 'individual') campos.set('usuario', formFB.individual);
  if (formFB.escopo === 'grupo') campos.set('usuarios', [...formFB.grupo].join(','));
  const editando = formFB.id !== null;
  if (!editando) {
    const arquivo = document.getElementById('fb-anexo-input').files[0];
    if (arquivo) {
      if (arquivo.size > TAMANHO_MAXIMO_ANEXO_FB) { erroEl.innerText = 'O anexo passa de 10MB. Escolha outro arquivo.'; return; }
      try {
        campos.set('anexo_data_url', await lerArquivoComoDataURL(arquivo));
        campos.set('anexo_nome', arquivo.name);
      } catch (e) { erroEl.innerText = 'Erro ao ler o arquivo: ' + e.message; return; }
    }
  }
  const botao = document.getElementById('fb-btn-salvar');
  botao.disabled = true;
  try {
    const resp = await fetch(editando ? '/api/feedback-usuario/editar' : '/api/feedback-usuario/criar', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: campos.toString(),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível salvar.'; return; }
    fecharFormFB(true);
    mostrarToastFB(dados.aviso || (editando ? 'Alterações salvas.' : 'Registro salvo e equipe avisada por e-mail.'));
    carregarListaFB();
  } catch (e) {
    erroEl.innerText = 'Erro: ' + e.message;
  } finally {
    botao.disabled = false;
  }
}

inicializarFB();
</script>
</body>
</html>
"""
