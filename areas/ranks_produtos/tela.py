"""Tela Rankings (Beta, 3.0.7.0; "Ranks por Produtos" até a 3.1.4.0, quando ganhou o nome novo).

Só texto (HTML/CSS/JS); a lógica fica em logica.py e a montagem no alertas_gui.py.
"""


_RANKS_PRODUTOS_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Rankings</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo.conteudo-ranks { max-width: 1320px; }
  .cab-ranks { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
  .cab-ranks h1 { font-size: 26px; margin: 0 0 6px; font-weight: 800; display: flex; align-items: center; gap: 10px; }
  .cab-ranks .beta { font-size: 11px; font-weight: 800; letter-spacing: .08em; color: var(--run); border: 1px solid currentColor;
                     border-radius: 99px; padding: 2px 9px; }
  .cab-ranks .sub { color: var(--fg-dim); font-size: 13.5px; }
  .filtros-ranks { display: flex; gap: 8px; flex-wrap: wrap; }
  .filtros-ranks input, .filtros-ranks select { background: rgba(var(--poco), .2); border: 1px solid var(--border); border-radius: 10px;
                     color: var(--fg); padding: 9px 12px; font: inherit; font-size: 13px; }
  .filtros-ranks input { width: 220px; }

  .topo-ranks { display: grid; grid-template-columns: 360px minmax(0, 1fr); gap: 18px; margin-bottom: 20px; }
  .cartao-r { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 18px; }
  .cartao-r h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); margin: 0 0 12px; }
  .eu-ranks { display: flex; gap: 14px; align-items: center; }
  .eu-ranks .nome { font-weight: 800; font-size: 15px; }
  .medalhas { display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
  .medalha { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; font-weight: 800; padding: 3px 10px; border-radius: 99px;
             background: rgba(var(--tinta), .06); }
  .medalha.master { color: #d8b4fe; background: rgba(168,85,247,.16); }
  .medalha.ouro { color: #f2b705; background: rgba(242,183,5,.12); }
  .medalha.prata { color: #c3ccd6; background: rgba(195,204,214,.12); }
  .medalha.bronze { color: #e08a4e; background: rgba(224,138,78,.12); }
  .metas-ins { display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end; }
  .meta-ins { position: relative; text-align: center; width: 92px; }
  .meta-ins svg { filter: grayscale(.85) brightness(.75); opacity: .75; }
  .meta-ins.alcancada svg { filter: none; opacity: 1; }
  .meta-ins .rot { font-size: 11px; color: var(--fg-dim); margin-top: 2px; }
  .meta-ins .selo-meta { position: absolute; top: 4px; left: 50%; transform: translateX(-50%); font-size: 9px; font-weight: 800;
                         letter-spacing: .05em; text-transform: uppercase; color: var(--ok); background: var(--bg-panel-solid);
                         border: 1px solid var(--border); border-radius: 99px; padding: 1px 7px; white-space: nowrap; }
  .meta-ins .em-breve-ins { position: absolute; top: 4px; left: 50%; transform: translateX(-50%); font-size: 9px; font-weight: 800;
                            letter-spacing: .05em; text-transform: uppercase; color: var(--run); background: var(--bg-panel-solid);
                            border: 1px solid var(--border); border-radius: 99px; padding: 1px 7px; white-space: nowrap; }
  .aviso-metas { font-size: 12px; color: var(--fg-dim); margin-top: 10px; line-height: 1.5; }

  .abas-ranks { display: flex; gap: 4px; border-bottom: 1px solid var(--border); margin-bottom: 16px; flex-wrap: wrap; }
  .abas-ranks button { border: none; background: none; color: var(--fg-dim); font: inherit; font-weight: 700; font-size: 13.5px;
                       padding: 10px 14px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; border-radius: 0; }
  .abas-ranks button[hidden] { display: none; }  /* o estilo global de botão (inline-block) anulava o hidden */
  .abas-ranks button.ativa { color: var(--fg); border-bottom-color: var(--teal); }
  .aba-ranks { display: none; }
  /* ranking geral ou por equipe (3.2.9.0) */
  .seg-equipe { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin: -4px 0 16px; }
  .seg-equipe .rot { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--fg-dim); margin-right: 4px; }
  .seg-equipe button { font: inherit; font-size: 12.5px; font-weight: 700; color: var(--fg-dim); cursor: pointer; border-radius: 99px;
                       border: 1px solid var(--border); background: rgba(var(--tinta), .03); padding: 5px 13px; }
  .seg-equipe button:hover { color: var(--fg); border-color: rgba(var(--tinta), .3); }
  .seg-equipe button.ativa { background: var(--teal); border-color: var(--teal); color: #071016; }
  .seg-equipe[hidden] { display: none; }
  .titulo-equipe { font-size: 15px; font-weight: 800; margin: 0 0 12px; }
  .titulo-equipe span { font-weight: 600; color: var(--fg-dim); font-size: 13px; margin-left: 6px; }
  .aba-ranks.ativa { display: block; }

  .linha-rank { display: grid; grid-template-columns: 44px 44px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 10px 14px;
                background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; margin-bottom: 8px; }
  .linha-rank.eu { border-color: rgba(45,184,207,.55); }
  .pos { font-size: 18px; font-weight: 900; text-align: center; color: var(--fg-dim); }
  .av-r { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; display: flex; align-items: center; justify-content: center;
          color: #fff; font-weight: 800; font-size: 14px; background: var(--cor-av, #2db8cf); cursor: zoom-in; }
  .linha-rank .nome { font-weight: 700; font-size: 14px; }
  .linha-rank .nome a { color: inherit; text-decoration: none; }
  .linha-rank .sub { font-size: 12px; color: var(--fg-dim); }
  .pontos-prod { display: flex; gap: 4px; flex-wrap: wrap; margin-top: 5px; }
  .pontos-prod span { font-size: 10.5px; font-weight: 700; padding: 1px 7px; border-radius: 6px; background: rgba(var(--tinta), .05); color: var(--fg-dim); }
  .pontos-prod span.master { background: rgba(168,85,247,.18); color: #d8b4fe; }
  .pontos-prod span.ouro { background: rgba(242,183,5,.14); color: #f2b705; }
  .pontos-prod span.prata { background: rgba(195,204,214,.14); color: #c3ccd6; }
  .pontos-prod span.bronze { background: rgba(224,138,78,.14); color: #e08a4e; }

  .tabela-wrap { overflow-x: auto; border: 1px solid var(--border); border-radius: 14px; background: var(--bg-panel); }
  .chip-nivel { display: inline-block; min-width: 64px; font-size: 11.5px; font-weight: 800; padding: 3px 8px; border-radius: 8px; color: var(--fg-dim); }
  .chip-nivel.master { background: rgba(168,85,247,.2); color: #d8b4fe; }
  .chip-nivel.ouro { background: rgba(242,183,5,.16); color: #f2b705; }
  .chip-nivel.prata { background: rgba(195,204,214,.16); color: #c3ccd6; }
  .chip-nivel.bronze { background: rgba(224,138,78,.16); color: #e08a4e; }
  select.sel-nivel { background: rgba(var(--poco), .2); border: 1px solid var(--border); border-radius: 8px; color: var(--fg); font: inherit;
                     font-size: 12px; padding: 4px 6px; }
  select.sel-nivel.master { color: #d8b4fe; border-color: rgba(168,85,247,.6); }
  select.sel-nivel.ouro { color: #f2b705; border-color: rgba(242,183,5,.5); }
  select.sel-nivel.prata { color: #c3ccd6; border-color: rgba(195,204,214,.5); }
  select.sel-nivel.bronze { color: #e08a4e; border-color: rgba(224,138,78,.5); }
  .total-prod { font-size: 11px; color: var(--fg-dim); font-weight: 500; text-transform: none; letter-spacing: 0; display: block; margin-top: 2px; }

  .lista-prod { display: flex; flex-direction: column; gap: 8px; max-width: 640px; }
  .item-prod { display: flex; gap: 8px; align-items: center; background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; padding: 8px 10px; }
  .item-prod input { flex: 1; background: rgba(var(--poco), .2); border: 1px solid var(--border); border-radius: 8px; color: var(--fg); padding: 7px 10px; font: inherit; }
  .btn-r { border: 1px solid var(--border); background: rgba(var(--tinta), .06); color: var(--fg); font: inherit; font-size: 12.5px; font-weight: 700;
           border-radius: 9px; padding: 7px 12px; cursor: pointer; }
  .btn-r.primario { background: var(--teal); border-color: var(--teal); color: #071016; }
  .btn-r.perigo:hover { border-color: var(--erro); color: var(--erro); }
  .alteracao { font-size: 13px; padding: 9px 0; border-bottom: 1px solid var(--border); color: var(--fg); }
  .alteracao .q { color: var(--fg-dim); font-size: 11.5px; }
  .vazio-r { color: var(--fg-dim); font-size: 13px; padding: 20px; text-align: center; }
  /* leaderboard (3.0.8.0 por ouro; 3.0.9.0 pelo Rank Master, com o ouro desempatando): pódio dos 3 primeiros e a lista */
  .podio { display: grid; grid-template-columns: 1fr 1.15fr 1fr; gap: 14px; align-items: end; max-width: 760px; margin: 6px auto 22px; }
  .degrau { text-align: center; }
  .degrau .av-r { width: 64px; height: 64px; font-size: 22px; margin: 0 auto 8px; box-shadow: 0 0 0 3px var(--cor-degrau); }
  .degrau.p1 .av-r { width: 84px; height: 84px; font-size: 28px; }
  .degrau .coroa { font-size: 26px; display: block; margin-bottom: 2px; }
  .degrau .nome-d { font-weight: 800; font-size: 14px; }
  .degrau .ouros-d { font-size: 12.5px; color: #d8b4fe; font-weight: 800; margin-top: 2px; }
  .degrau .bloco-d { margin-top: 10px; border-radius: 14px 14px 0 0; background: linear-gradient(180deg, color-mix(in srgb, var(--cor-degrau) 35%, transparent), rgba(var(--tinta), .03));
                     border: 1px solid color-mix(in srgb, var(--cor-degrau) 45%, transparent); border-bottom: none;
                     display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 900; color: var(--cor-degrau); }
  .degrau.p1 { --cor-degrau: #f2b705; } .degrau.p1 .bloco-d { height: 120px; }
  .degrau.p2 { --cor-degrau: #c3ccd6; } .degrau.p2 .bloco-d { height: 88px; }
  .degrau.p3 { --cor-degrau: #e08a4e; } .degrau.p3 .bloco-d { height: 64px; }
  .degrau.vazio { opacity: .35; }
  .linha-lb { display: grid; grid-template-columns: 44px 40px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 9px 14px;
              background: var(--bg-panel); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 7px; }
  .linha-lb.eu { border-color: rgba(45,184,207,.55); }
  .linha-lb .barra-lb { height: 6px; border-radius: 99px; background: rgba(var(--tinta), .07); margin-top: 6px; overflow: hidden; }
  .linha-lb .barra-lb span { display: block; height: 100%; background: linear-gradient(90deg, #a855f7, #f2b705); border-radius: 99px; }
  .linha-lb .total-ouro { font-size: 15px; font-weight: 900; color: #d8b4fe; white-space: nowrap; }
  .linha-lb .total-ouro small { color: #f2b705; font-size: 12px; margin-left: 8px; }
  .legenda-pontos { font-size: 12px; color: var(--fg-dim); margin: 0 0 10px 4px; }
  /* metas de Rank Master por nível (3.1.0.0): a atual em destaque, as de baixo "superadas" */
  .meta-ins.superada svg { filter: none; opacity: .5; }
  /* leaderboard de palminhas (3.1.3.0): top 10 de quem mais recebeu palminhas no mural */
  .topo-palmas { display: grid; grid-template-columns: 300px minmax(0, 1fr); gap: 18px; margin-bottom: 18px; }
  .minhas-palmas { display: flex; flex-direction: column; justify-content: center; gap: 4px; }
  .minhas-palmas .num { font-size: 40px; font-weight: 900; line-height: 1; color: #fbbf24; }
  .minhas-palmas .num span { font-size: 26px; margin-right: 6px; }
  .minhas-palmas .sub { font-size: 12.5px; color: var(--fg-dim); line-height: 1.45; }
  .degrau .palmas-d { font-size: 12.5px; color: #fbbf24; font-weight: 800; margin-top: 2px; }
  .linha-lb .barra-lb.palmas span { background: linear-gradient(90deg, #f59e0b, #f43f5e); }
  .linha-lb .total-palmas { font-size: 15px; font-weight: 900; color: #fbbf24; white-space: nowrap; }
  @media (max-width: 960px) { .topo-palmas { grid-template-columns: minmax(0, 1fr); } }
  .topo-palmas.sem-metas { grid-template-columns: minmax(0, 360px); }
  .meta-ins .selo-meta.superada { color: var(--fg-dim); }

  /* Atribuir ranks (3.1.0.0, só admin): por pessoa ou por produto, com botões de nível que gravam na hora */
  .modo-atrib { display: inline-flex; gap: 4px; padding: 4px; border-radius: 99px; background: rgba(var(--tinta), .05); border: 1px solid var(--border); margin-bottom: 14px; }
  .modo-atrib button { border: none; background: none; color: var(--fg-dim); font: inherit; font-size: 12.5px; font-weight: 700; padding: 7px 14px; border-radius: 99px; cursor: pointer; }
  .modo-atrib button.ativo { background: var(--teal); color: #071016; }
  .editor-atrib { display: grid; grid-template-columns: 280px minmax(0, 1fr); gap: 16px; align-items: start; }
  .lista-esq { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; padding: 6px; max-height: 620px; overflow-y: auto; position: sticky; top: 80px; }
  .item-esq { display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 10px; cursor: pointer; border: 1px solid transparent; }
  .item-esq:hover { background: rgba(var(--tinta), .05); }
  .item-esq.ativo { background: rgba(45,184,207,.12); border-color: rgba(45,184,207,.45); }
  .item-esq .av-r { width: 30px; height: 30px; font-size: 11px; cursor: pointer; }
  .item-esq .nome-esq { font-size: 13px; font-weight: 700; }
  .item-esq .mini { font-size: 11px; color: var(--fg-dim); }
  .painel-dir { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; }
  .cab-dir { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
  .cab-dir .nome { font-size: 16px; font-weight: 800; }
  .linha-atrib { display: flex; align-items: center; gap: 12px; padding: 9px 0; border-top: 1px solid var(--border); flex-wrap: wrap; }
  .linha-atrib:first-of-type { border-top: none; }
  .linha-atrib .rot-atrib { min-width: 150px; font-weight: 700; font-size: 13.5px; display: flex; align-items: center; gap: 8px; }
  .linha-atrib .rot-atrib .av-r { width: 28px; height: 28px; font-size: 10.5px; }
  .seg { display: inline-flex; border: 1px solid var(--border); border-radius: 10px; overflow: hidden; flex-wrap: wrap; }
  .seg button { border: none; border-right: 1px solid var(--border); background: rgba(var(--tinta), .03); color: var(--fg-dim); font: inherit;
                font-size: 12px; font-weight: 700; padding: 7px 12px; cursor: pointer; border-radius: 0; transition: background .12s, color .12s; }
  .seg button:last-child { border-right: none; }
  .seg button:hover { color: var(--fg); background: rgba(var(--tinta), .08); }
  .seg button.ativo.nada { background: rgba(var(--tinta), .12); color: var(--fg); }
  .seg button.ativo.bronze { background: rgba(224,138,78,.25); color: #f0a36b; }
  .seg button.ativo.prata { background: rgba(195,204,214,.22); color: #e2e8f0; }
  .seg button.ativo.ouro { background: rgba(242,183,5,.25); color: #f7c948; }
  .seg button.ativo.master { background: rgba(168,85,247,.3); color: #e9d5ff; }
  .chips-prod-atrib { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
  .chips-prod-atrib button { border: 1px solid var(--border); background: rgba(var(--tinta), .04); color: var(--fg); font: inherit; font-size: 12.5px;
                             font-weight: 700; padding: 6px 12px; border-radius: 99px; cursor: pointer; }
  .chips-prod-atrib button.ativo { background: var(--teal); border-color: var(--teal); color: #071016; }
  .salvo-atrib { font-size: 11px; color: var(--ok); margin-left: 6px; opacity: 0; transition: opacity .2s; }
  .salvo-atrib.ver { opacity: 1; }

  /* Meus produtos (3.1.0.0): os produtos da pessoa agrupados por nível */
  .grupos-meus { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .grupo-meu { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 14px; padding: 14px; }
  .grupo-meu h4 { margin: 0 0 10px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
  .grupo-meu h4 span { margin-left: auto; font-size: 12px; color: var(--fg-dim); font-weight: 600; }
  .grupo-meu .chips { display: flex; flex-wrap: wrap; gap: 6px; }
  .grupo-meu.master { border-color: rgba(168,85,247,.5); }
  .grupo-meu.ouro { border-color: rgba(242,183,5,.45); }
  @media (max-width: 860px) { .editor-atrib { grid-template-columns: minmax(0, 1fr); } .lista-esq { position: static; max-height: 260px; } }
  .aviso-beta { font-size: 12.5px; color: var(--fg-dim); background: rgba(var(--tinta), .04); border: 1px dashed var(--border); border-radius: 12px;
                padding: 10px 14px; margin-bottom: 18px; }
  @media (max-width: 960px) { .topo-ranks { grid-template-columns: minmax(0, 1fr); } .filtros-ranks input { width: 100%; } }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-ranks">
    <div class="cab-ranks">
      <div>
        <h1>Rankings</h1>
        <div class="sub">Os placares da equipe: o nível de cada pessoa em cada produto (bronze, prata, ouro e, acima de todos, o Master) e quem mais recebeu palminhas.</div>
      </div>
      <div class="filtros-ranks">
        <input type="search" id="busca-r" placeholder="Buscar pessoa..." oninput="desenhar()">
        <input type="hidden" id="equipe-r" value="">
      </div>
    </div>
    <div class="aviso-beta" id="aviso-beta">Quem atribui os níveis dos produtos são os administradores, e cada produto no Master conta pras insígnias de Rank Master. As palminhas vêm do mural do início.</div>

    <div class="topo-ranks">
      <div class="cartao-r"><h3>Você</h3><div id="eu-r"></div></div>
      <div class="cartao-r">
        <h3>Insígnias de Rank Master</h3>
        <div class="metas-ins" id="metas-r"></div>
        <div class="aviso-metas" id="aviso-metas"></div>
      </div>
    </div>

    <div class="abas-ranks" id="abas-r">
      <button class="ativa" data-aba="leaderboard">🏆 Produtos</button>
      <button data-aba="palmas">👏 Palminhas</button>
      <button data-aba="ranking">Ranking geral</button>
      <button data-aba="meus">Meus produtos</button>
      <button data-aba="atribuir" class="so-admin" hidden>✏️ Atribuir ranks</button>
      <button data-aba="produtos" class="so-admin" hidden>Produtos</button>
    </div>
    <!-- 3.2.9.0: ranking geral ou por equipe (vale pra Produtos, Palminhas e o Ranking geral) -->
    <div class="seg-equipe" id="seg-equipe" role="tablist" aria-label="De qual equipe é o ranking">
      <span class="rot">Ranking</span>
      <button data-equipe="" class="ativa" role="tab">🌐 Geral</button>
      <button data-equipe="Suporte" role="tab">Suporte</button>
      <button data-equipe="Monitoramento" role="tab">Monitoramento</button>
      <button data-equipe="Serviços" role="tab">Serviços</button>
    </div>
    <div class="aba-ranks ativa" id="aba-leaderboard"><div class="titulo-equipe" data-titulo="🏆 Produtos"></div><div class="podio" id="podio"></div><div id="lista-leaderboard"><div class="vazio-r">Carregando...</div></div></div>
    <div class="aba-ranks" id="aba-palmas">
      <div class="topo-palmas">
        <div class="cartao-r"><h3>Suas palminhas</h3><div class="minhas-palmas" id="minhas-palmas"></div></div>
        <div class="cartao-r" id="cartao-metas-palmas"><h3>Insígnias de palminhas</h3><div class="metas-ins" id="metas-palmas"></div></div>
      </div>
      <div class="titulo-equipe" data-titulo="👏 Palminhas"></div>
      <div class="podio" id="podio-palmas"></div><div id="lista-palmas"><div class="vazio-r">Carregando...</div></div>
    </div>
    <div class="aba-ranks" id="aba-ranking"><div class="titulo-equipe" data-titulo="Ranking geral de produtos"></div><div id="lista-ranking"><div class="vazio-r">Carregando...</div></div></div>
    <div class="aba-ranks" id="aba-meus"><div class="grupos-meus" id="grupos-meus"></div></div>
    <div class="aba-ranks" id="aba-atribuir">
      <div class="modo-atrib" id="modo-atrib">
        <button class="ativo" data-modo="pessoa">Por pessoa</button>
        <button data-modo="produto">Por produto</button>
      </div>
      <div id="editor-atrib"></div>
    </div>
    <div class="aba-ranks" id="aba-produtos">
      <div class="lista-prod" id="lista-prod"></div>
      <div class="item-prod" style="max-width:640px;margin-top:12px"><input id="novo-prod" maxlength="40" placeholder="Nome do produto novo (ex.: ClienteI)">
        <button class="btn-r primario" onclick="mexerProduto('criar', '', document.getElementById('novo-prod').value)">Adicionar</button></div>
    </div>
  </div>

  __FOOTER__
  <div class="toast" id="toast"></div>
__INSIGNIAS__
<script>
let dadosR = null;
const MEDALHA = { master: '👑', ouro: '🥇', prata: '🥈', bronze: '🥉' };
const NOME_NIVEL = { master: 'Master', ouro: 'Ouro', prata: 'Prata', bronze: 'Bronze' };

function escR(t) {
  return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}
function toastR(texto) {
  const t = document.getElementById('toast');
  t.innerText = texto; t.classList.add('mostrar');
  clearTimeout(window._tR); window._tR = setTimeout(() => t.classList.remove('mostrar'), 3200);
}
function corNome(nome) {
  const cores = ['#2db8cf', '#7c9a12', '#c084fc', '#f97316', '#e85d75', '#3b82f6', '#14b8a6', '#d4a017'];
  let h = 0; for (const c of String(nome)) h = (h * 31 + c.charCodeAt(0)) % 997;
  return cores[h % cores.length];
}
function avatarR(p) {
  const abrir = ' onclick="abrirFotoPessoa(pessoaPorLogin(' + "'" + escR(p.login) + "'" + '))"';
  if (p.tem_foto) return '<img class="av-r" src="/foto-usuario/' + encodeURIComponent(p.login) + '" alt="" loading="lazy" decoding="async"' + abrir + '>';
  const partes = String(p.nome || '?').split(' ').filter(Boolean);
  const ini = ((partes[0] || '?')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
  return '<span class="av-r" style="--cor-av:' + corNome(p.nome) + '"' + abrir + '>' + escR(ini) + '</span>';
}
function pessoaPorLogin(login) {
  const p = dadosR.pessoas.find(x => x.login === login);
  return p ? { login: p.login, nome: p.nome, tem_foto: p.tem_foto, cargo: p.cargo, equipe: p.equipe } : null;
}
function medalhasHtml(c) {
  return '<div class="medalhas"><span class="medalha master">👑 ' + c.master + '</span><span class="medalha ouro">🥇 ' + c.ouro + '</span><span class="medalha prata">🥈 ' + c.prata
    + '</span><span class="medalha bronze">🥉 ' + c.bronze + '</span></div>';
}
function pertence(p, equipe) {
  return !equipe || (p.equipe || '').indexOf(equipe) >= 0;
}
function filtradas() {
  const termo = document.getElementById('busca-r').value.trim().toLowerCase();
  const equipe = document.getElementById('equipe-r').value;
  return dadosR.pessoas.filter(p => pertence(p, equipe) && (!termo || p.nome.toLowerCase().includes(termo)));
}

function desenharTopo() {
  const eu = dadosR.pessoas.find(p => p.login === dadosR.eu);
  document.getElementById('eu-r').innerHTML = eu ? '<div class="eu-ranks">' + avatarR(eu) + '<div><div class="nome">' + escR(eu.nome) + '</div>'
    + medalhasHtml(eu.contagem) + '</div></div>' : '';
  const masters = eu ? eu.contagem.master : 0;
  const atual = Math.max(0, ...dadosR.metas_rank_master.filter(m => masters >= m));
  document.getElementById('metas-r').innerHTML = dadosR.metas_rank_master.map(m =>
    '<div class="meta-ins' + (m === atual ? ' alcancada' : (masters >= m ? ' superada' : '')) + '">'
    + (m === atual ? '<span class="selo-meta">✓ Sua insígnia</span>' : (masters >= m ? '<span class="selo-meta superada">Superada</span>' : ''))
    + svgInsignia({ tipo: 'rank', produtos: m }, 76, false) + '<div class="rot">' + m + (m === 1 ? ' produto' : ' produtos') + '</div></div>').join('');
  const prox = eu && eu.rank_master.proxima;
  document.getElementById('aviso-metas').textContent = (prox ? 'Você tem ' + masters + (masters === 1 ? ' produto' : ' produtos') + ' no Master; a próxima insígnia sai com ' + prox + '.'
    : 'Você já chegou na maior meta!') + ' Os ranks são definidos pelos administradores.';
}

function desenharRanking() {
  const lista = filtradas();
  document.getElementById('lista-ranking').innerHTML = lista.length ? lista.map((p, i) => {
    const pos = dadosR.pessoas.indexOf(p) + 1;
    const total = p.contagem.master + p.contagem.ouro + p.contagem.prata + p.contagem.bronze;
    const chips = dadosR.produtos.filter(pr => p.niveis[pr.id]).map(pr => '<span class="' + p.niveis[pr.id] + '">' + escR(pr.nome) + '</span>').join('');
    return '<div class="linha-rank' + (p.login === dadosR.eu ? ' eu' : '') + '"><div class="pos">' + (total && pos <= 3 ? ['🥇', '🥈', '🥉'][pos - 1] : pos + 'º') + '</div>'
      + avatarR(p) + '<div><div class="nome"><a href="/perfil/' + encodeURIComponent(p.login) + '">' + escR(p.nome) + '</a></div>'
      + '<div class="sub">' + escR([p.cargo, p.equipe].filter(Boolean).join(' · ')) + '</div>'
      + (chips ? '<div class="pontos-prod">' + chips + '</div>' : '<div class="sub">Ainda sem rank em nenhum produto</div>') + '</div>'
      + medalhasHtml(p.contagem) + '</div>';
  }).join('') : '<div class="vazio-r">Ninguém com esse filtro.</div>';
}

// Leaderboard de produtos por pontos (3.2.4.0, pedido do Igor: "todos os produtos devem ter peso, até os de bronze"):
// Master 4 · Ouro 3 · Prata 2 · Bronze 1 (o mesmo "pontos" que a visao calcula). Empate: mais Master, depois mais Ouro,
// depois mais Prata; pontos iguais dividem a posição.
const PESOS_NIVEL = { master: 4, ouro: 3, prata: 2, bronze: 1 };
function pontosR(p) { return p.contagem.master * 4 + p.contagem.ouro * 3 + p.contagem.prata * 2 + p.contagem.bronze; }
function textoPts(n) { return n + (n === 1 ? ' pt' : ' pts'); }
function desenharLeaderboard() {
  const lista = filtradas().filter(p => pontosR(p) > 0)
    .sort((a, b) => pontosR(b) - pontosR(a) || b.contagem.master - a.contagem.master || b.contagem.ouro - a.contagem.ouro
      || b.contagem.prata - a.contagem.prata || a.nome.localeCompare(b.nome));
  let pos = 0, anterior = null;
  lista.forEach((p, i) => { if (pontosR(p) !== anterior) { pos = i + 1; anterior = pontosR(p); } p._pos = pos; });
  const maximo = lista.length ? Math.max(pontosR(lista[0]), 1) : 1;
  const degrau = (p, n) => p
    ? '<div class="degrau p' + n + '">' + (n === 1 ? '<span class="coroa">👑</span>' : '') + avatarR(p) + '<div class="nome-d">' + escR(p.nome.split(' ')[0]) + '</div>'
      + '<div class="ouros-d">' + textoPts(pontosR(p)) + '</div><div class="bloco-d">' + p._pos + 'º</div></div>'
    : '<div class="degrau p' + n + ' vazio"><div class="bloco-d">' + n + 'º</div></div>';
  document.getElementById('podio').innerHTML = lista.length ? degrau(lista[1], 2) + degrau(lista[0], 1) + degrau(lista[2], 3) : '';
  const legenda = '<div class="legenda-pontos">Pontos por produto: 👑 Master 4 · 🥇 Ouro 3 · 🥈 Prata 2 · 🥉 Bronze 1</div>';
  document.getElementById('lista-leaderboard').innerHTML = lista.length ? legenda + lista.map(p => {
    const produtos = ['master', 'ouro', 'prata', 'bronze'].map(n => dadosR.produtos.filter(pr => p.niveis[pr.id] === n)
      .map(pr => MEDALHA[n] + ' ' + pr.nome).join(' · ')).filter(Boolean).join(' · ');
    return '<div class="linha-lb' + (p.login === dadosR.eu ? ' eu' : '') + '"><div class="pos">' + p._pos + 'º</div>' + avatarR(p)
      + '<div><div class="nome"><a href="/perfil/' + encodeURIComponent(p.login) + '" style="color:inherit;text-decoration:none;font-weight:700">' + escR(p.nome) + '</a></div>'
      + '<div class="sub" style="font-size:12px;color:var(--fg-dim)">' + escR(produtos) + '</div>'
      + '<div class="barra-lb"><span style="width:' + Math.round(pontosR(p) / maximo * 100) + '%"></span></div></div>'
      + '<div class="total-ouro">' + textoPts(pontosR(p)) + '<small>' + medalhasCurtas(p.contagem) + '</small></div></div>';
  }).join('') : '<div class="vazio-r">Ninguém com rank ainda. Os administradores definem os ranks na aba Atribuir ranks.</div>';
}
function medalhasCurtas(c) {
  return ['master', 'ouro', 'prata', 'bronze'].filter(n => c[n]).map(n => MEDALHA[n] + ' ' + c[n]).join('  ');
}

// Leaderboard de palminhas (3.1.3.0): top 10 de quem mais recebeu palminhas no mural, com os mesmos filtros de busca e equipe
function rotuloPalmas(n) { return n >= 1000 && n % 1000 === 0 ? (n / 1000) + 'k' : String(n); }
function desenharPalmas() {
  const minhas = dadosR.minhas_palmas || 0;
  const metas = dadosR.metas_palmas || [];
  const atual = Math.max(0, ...metas.filter(m => minhas >= m));
  const prox = metas.find(m => minhas < m);
  // sem metas (insígnias de palminhas desligadas, 3.1.8.0): some o cartão das insígnias e o texto da próxima
  document.getElementById('cartao-metas-palmas').hidden = !metas.length;
  document.querySelector('.topo-palmas').classList.toggle('sem-metas', !metas.length);
  document.getElementById('minhas-palmas').innerHTML = '<div class="num"><span>👏</span>' + minhas + '</div><div class="sub">'
    + (minhas === 1 ? 'palminha recebida' : 'palminhas recebidas') + ' no mural.'
    + (!metas.length ? '' : '<br>' + (prox ? 'A próxima insígnia sai com ' + rotuloPalmas(prox) + ' (' + (prox - minhas === 1 ? 'falta 1' : 'faltam ' + (prox - minhas)) + ').' : 'Você chegou na maior meta!')) + '</div>';
  document.getElementById('metas-palmas').innerHTML = metas.map(m =>
    '<div class="meta-ins' + (m === atual ? ' alcancada' : (minhas >= m ? ' superada' : '')) + '">'
    + (m === atual ? '<span class="selo-meta">✓ Sua insígnia</span>' : (minhas >= m ? '<span class="selo-meta superada">Superada</span>' : ''))
    + svgInsignia({ tipo: 'palmas', palmas: m }, 76, false) + '<div class="rot">' + rotuloPalmas(m) + ' palminhas</div></div>').join('');
  const termo = document.getElementById('busca-r').value.trim().toLowerCase();
  const equipe = document.getElementById('equipe-r').value;
  const todos = (dadosR.palmas || []).filter(p => pertence(p, equipe) && (!termo || p.nome.toLowerCase().includes(termo)));
  let pos = 0, anterior = null;
  todos.forEach((p, i) => { if (p.palmas !== anterior) { pos = i + 1; anterior = p.palmas; } p._pos = pos; });
  const lista = todos.filter(p => p._pos <= 10);  // top 10 (empate na 10ª posição entra junto)
  const maximo = lista.length ? lista[0].palmas : 1;
  const degrau = (p, n) => p
    ? '<div class="degrau p' + n + '">' + (n === 1 ? '<span class="coroa">👏</span>' : '') + avatarR(p) + '<div class="nome-d">' + escR(p.nome.split(' ')[0]) + '</div>'
      + '<div class="palmas-d">👏 ' + p.palmas + '</div><div class="bloco-d">' + p._pos + 'º</div></div>'
    : '<div class="degrau p' + n + ' vazio"><div class="bloco-d">' + n + 'º</div></div>';
  document.getElementById('podio-palmas').innerHTML = lista.length ? degrau(lista[1], 2) + degrau(lista[0], 1) + degrau(lista[2], 3) : '';
  document.getElementById('lista-palmas').innerHTML = lista.length ? lista.map(p =>
    '<div class="linha-lb' + (p.login === dadosR.eu ? ' eu' : '') + '"><div class="pos">' + p._pos + 'º</div>' + avatarR(p)
    + '<div><div class="nome"><a href="/perfil/' + encodeURIComponent(p.login) + '" style="color:inherit;text-decoration:none;font-weight:700">' + escR(p.nome) + '</a></div>'
    + '<div class="sub" style="font-size:12px;color:var(--fg-dim)">' + escR([p.cargo, p.equipe].filter(Boolean).join(' · ')) + '</div>'
    + '<div class="barra-lb palmas"><span style="width:' + Math.round(p.palmas / maximo * 100) + '%"></span></div></div>'
    + '<div class="total-palmas">👏 ' + p.palmas + '</div></div>').join('')
    : '<div class="vazio-r">Ninguém recebeu palminhas ainda. Elas são batidas nos eventos do mural, no início do PDA.</div>';
}

// ---------------- Meus produtos ----------------
function desenharMeus() {
  const eu = dadosR.pessoas.find(p => p.login === dadosR.eu);
  const niveis = eu ? eu.niveis : {};
  const grupos = [['master', '👑 Master'], ['ouro', '🥇 Ouro'], ['prata', '🥈 Prata'], ['bronze', '🥉 Bronze'], ['', 'Sem rank ainda']];
  document.getElementById('grupos-meus').innerHTML = grupos.map(([n, rot]) => {
    const prods = dadosR.produtos.filter(pr => (niveis[pr.id] || '') === n);
    return '<div class="grupo-meu ' + n + '"><h4>' + rot + '<span>' + prods.length + '</span></h4><div class="chips">'
      + (prods.length ? prods.map(pr => '<span class="chip-nivel ' + n + '">' + escR(pr.nome) + '</span>').join('') : '<span style="font-size:12px;color:var(--fg-dim)">Nenhum</span>')
      + '</div></div>';
  }).join('');
}

// ---------------- Atribuir ranks (só admin) ----------------
let modoAtrib = 'pessoa', pessoaAtrib = null, produtoAtrib = null;
function segNivel(login, produto) {
  const p = dadosR.pessoas.find(x => x.login === login);
  const atual = (p && p.niveis[produto]) || '';
  return '<span class="seg" data-login="' + escR(login) + '" data-produto="' + escR(produto) + '">'
    + [['', 'nada', '—'], ['bronze', 'bronze', '🥉 Bronze'], ['prata', 'prata', '🥈 Prata'], ['ouro', 'ouro', '🥇 Ouro'], ['master', 'master', '👑 Master']].map(([v, cls, rot]) =>
      '<button type="button" class="' + cls + (v === atual ? ' ativo' : '') + '" data-nivel="' + v + '">' + rot + '</button>').join('')
    + '</span><span class="salvo-atrib">✓ salvo</span>';
}
function desenharAtribuir() {
  if (!dadosR.pode_editar) return;
  const el = document.getElementById('editor-atrib');
  const lista = filtradas();
  if (modoAtrib === 'pessoa') {
    if (!pessoaAtrib || !lista.some(p => p.login === pessoaAtrib)) pessoaAtrib = lista.length ? lista[0].login : null;
    const p = dadosR.pessoas.find(x => x.login === pessoaAtrib);
    el.innerHTML = '<div class="editor-atrib"><div class="lista-esq">' + lista.map(x =>
      '<div class="item-esq' + (x.login === pessoaAtrib ? ' ativo' : '') + '" data-escolher="' + escR(x.login) + '">' + avatarR(x)
      + '<div><div class="nome-esq">' + escR(x.nome) + '</div><div class="mini">👑 ' + x.contagem.master + ' · 🥇 ' + x.contagem.ouro + ' · 🥈 ' + x.contagem.prata + ' · 🥉 ' + x.contagem.bronze + '</div></div></div>').join('')
      + '</div><div class="painel-dir">' + (p ? '<div class="cab-dir">' + avatarR(p) + '<div><div class="nome">' + escR(p.nome) + '</div>'
        + '<div style="font-size:12px;color:var(--fg-dim)">' + escR([p.cargo, p.equipe].filter(Boolean).join(' · ')) + '</div></div>' + medalhasHtml(p.contagem) + '</div>'
        + dadosR.produtos.map(pr => '<div class="linha-atrib"><div class="rot-atrib">' + escR(pr.nome) + '</div>' + segNivel(p.login, pr.id) + '</div>').join('')
        : '<div class="vazio-r">Ninguém com esse filtro.</div>') + '</div></div>';
  } else {
    if (!produtoAtrib || !dadosR.produtos.some(pr => pr.id === produtoAtrib)) produtoAtrib = dadosR.produtos.length ? dadosR.produtos[0].id : null;
    el.innerHTML = '<div class="chips-prod-atrib">' + dadosR.produtos.map(pr =>
      '<button type="button" class="' + (pr.id === produtoAtrib ? 'ativo' : '') + '" data-produto-escolher="' + escR(pr.id) + '">' + escR(pr.nome) + '</button>').join('') + '</div>'
      + '<div class="painel-dir">' + (produtoAtrib ? lista.map(p => '<div class="linha-atrib"><div class="rot-atrib">' + avatarR(p) + escR(p.nome) + '</div>'
        + segNivel(p.login, produtoAtrib) + '</div>').join('') : '<div class="vazio-r">Cadastre um produto na aba Produtos.</div>') + '</div>';
  }
}
document.getElementById('modo-atrib').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  modoAtrib = b.dataset.modo;
  document.querySelectorAll('#modo-atrib button').forEach(x => x.classList.toggle('ativo', x === b));
  desenharAtribuir();
});
document.getElementById('editor-atrib').addEventListener('click', async e => {
  const escolher = e.target.closest('[data-escolher]');
  if (escolher && !e.target.closest('.av-r')) { pessoaAtrib = escolher.dataset.escolher; desenharAtribuir(); return; }
  const chip = e.target.closest('[data-produto-escolher]');
  if (chip) { produtoAtrib = chip.dataset.produtoEscolher; desenharAtribuir(); return; }
  const botao = e.target.closest('.seg button');
  if (!botao) return;
  const seg = botao.closest('.seg');
  const login = seg.dataset.login, produto = seg.dataset.produto, nivel = botao.dataset.nivel;
  const p = dadosR.pessoas.find(x => x.login === login);
  const antes = p.niveis[produto] || '';
  if (antes === nivel) return;
  // responde na hora e grava em seguida; se falhar, recarrega do servidor
  seg.querySelectorAll('button').forEach(x => x.classList.toggle('ativo', x === botao));
  if (nivel) p.niveis[produto] = nivel; else delete p.niveis[produto];
  try {
    await postar('/api/ranks-produtos/nivel', { usuario: login, produto, nivel });
    const ok = seg.nextElementSibling;
    if (ok) { ok.classList.add('ver'); setTimeout(() => ok.classList.remove('ver'), 1400); }
    clearTimeout(window._recarregaR);
    window._recarregaR = setTimeout(carregar, 900);  // atualiza contagens, leaderboard e metas sem perder a seleção
  } catch (err) {
    toastR(err.message !== 'erro' ? err.message : 'Não foi possível salvar.');
    carregar();
  }
});

function desenharProdutos() {
  document.getElementById('lista-prod').innerHTML = dadosR.produtos.map(pr =>
    '<div class="item-prod"><input value="' + escR(pr.nome) + '" maxlength="40" id="nome-' + escR(pr.id) + '">'
    + '<button class="btn-r" onclick="mexerProduto(' + "'renomear', '" + escR(pr.id) + "'" + ', document.getElementById(' + "'nome-" + escR(pr.id) + "'" + ').value)">Renomear</button>'
    + '<button class="btn-r perigo" onclick="removerProduto(' + "'" + escR(pr.id) + "'" + ')">Remover</button></div>').join('')
    || '<div class="vazio-r">Nenhum produto ainda.</div>';
}

const NOME_EQUIPE_R = { '': 'Geral', 'Suporte': 'Suporte', 'Monitoramento': 'Monitoramento', 'Serviços': 'Serviços' };
function escolherEquipeR(equipe, semDesenhar) {
  if (!(equipe in NOME_EQUIPE_R)) equipe = '';
  document.getElementById('equipe-r').value = equipe;
  document.querySelectorAll('#seg-equipe button').forEach(b => {
    const ativa = b.dataset.equipe === equipe;
    b.classList.toggle('ativa', ativa);
    b.setAttribute('aria-selected', ativa ? 'true' : 'false');
  });
  // "Suporte e Monitoramento" (12x36) entra nos dois rankings
  document.querySelectorAll('.titulo-equipe').forEach(el => {
    el.innerHTML = escR(el.dataset.titulo) + ' · ' + escR(NOME_EQUIPE_R[equipe])
      + (equipe ? '<span>só quem é da equipe ' + escR(equipe) + (equipe !== 'Serviços' ? ' (12x36 conta nas duas)' : '') + '</span>' : '<span>todas as equipes</span>');
  });
  try { localStorage.setItem('pda-ranks-equipe', equipe); } catch (e) { /* só não lembra da escolha */ }
  if (!semDesenhar) desenhar();
}
document.getElementById('seg-equipe').addEventListener('click', e => {
  const b = e.target.closest('button[data-equipe]');
  if (b) escolherEquipeR(b.dataset.equipe);
});
(function () {
  let salva = '';
  try { salva = localStorage.getItem('pda-ranks-equipe') || ''; } catch (e) { /* sem localStorage: Geral */ }
  escolherEquipeR(salva, true);
})();

function desenhar() {
  if (!dadosR) return;
  desenharTopo(); desenharLeaderboard(); desenharPalmas(); desenharRanking(); desenharMeus();
  // 3.1.9.0: a Visão por produto e as Últimas alterações saíram (as alterações ficam no log "Rankings", no card Logs)
  if (dadosR.pode_editar) { desenharAtribuir(); desenharProdutos(); }
}

async function carregar() {
  try {
    const r = await (await fetch('/api/ranks-produtos')).json();
    if (!r.ok) throw new Error(r.erro || 'erro');
    dadosR = r;
    // quem só visualiza fica com Leaderboard, Ranking geral e Meus produtos (3.1.0.0)
    document.querySelectorAll('.so-admin').forEach(b => { b.hidden = !r.pode_editar; });
    desenhar();
  } catch (e) {
    document.getElementById('lista-ranking').innerHTML = '<div class="vazio-r">Não foi possível carregar os ranks agora.</div>';
  }
}

async function postar(url, campos) {
  const resp = await fetch(url, { method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'}, body: new URLSearchParams(campos) });
  const r = await resp.json();
  if (!r.ok) throw new Error(r.erro || 'erro');
  return r;
}

async function mexerProduto(acao, id, nome) {
  try {
    await postar('/api/ranks-produtos/produto', { acao, id, nome });
    if (acao === 'criar') document.getElementById('novo-prod').value = '';
    toastR(acao === 'criar' ? 'Produto adicionado.' : 'Produto atualizado.');
    carregar();
  } catch (e) { toastR(e.message !== 'erro' ? e.message : 'Não foi possível salvar.'); }
}

function removerProduto(id) {
  const pr = dadosR.produtos.find(x => x.id === id);
  if (!confirm('Remover o produto ' + (pr ? pr.nome : id) + '? Os ranks das pessoas nele também saem.')) return;
  mexerProduto('remover', id, '');
}

document.getElementById('abas-r').addEventListener('click', e => {
  const b = e.target.closest('button');
  if (!b) return;
  document.querySelectorAll('#abas-r button').forEach(x => x.classList.toggle('ativa', x === b));
  document.querySelectorAll('.aba-ranks').forEach(a => a.classList.toggle('ativa', a.id === 'aba-' + b.dataset.aba));
  document.getElementById('seg-equipe').hidden = ['meus', 'produtos'].indexOf(b.dataset.aba) !== -1;
});
// /ranks-produtos#palmas abre direto na aba (link do perfil)
const abaInicialR = document.querySelector('#abas-r button[data-aba="' + location.hash.slice(1) + '"]:not(.so-admin)');
if (abaInicialR) abaInicialR.click();
carregar();
</script>
</body>
</html>
"""
