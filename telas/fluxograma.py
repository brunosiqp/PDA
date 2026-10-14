"""Tela Fluxograma do PDA (beta, 3.3.1.0): mapa interativo de tudo que o PDA faz e com quem conversa.

Só texto (HTML/CSS/JS); a rota e o acesso (só administrador) ficam no alertas_gui.py. Os nós e as ligações estão
no próprio JS (NOS e LIGACOES): peça nova no PDA = um nó e as ligações dele aqui.
"""


_FLUXOGRAMA_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Fluxograma do PDA</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo-fluxo { max-width: 1560px; margin: 0 auto; }
  .cab-fluxo { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
  .cab-fluxo h1 { font-size: 22px; margin: 0 0 4px; background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .cab-fluxo .sub { color: var(--fg-dim); font-size: 13px; max-width: 760px; line-height: 1.5; }
  .selo-beta { display: inline-block; font-size: 10.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; vertical-align: 4px;
               color: #071016; background: var(--teal); border-radius: 99px; padding: 2px 9px; margin-left: 8px; -webkit-text-fill-color: #071016; }
  .barra-fluxo { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 12px; }
  .barra-fluxo input { font: inherit; font-size: 13px; color: var(--fg); background: rgba(var(--poco), .25); border: 1px solid var(--border);
                       border-radius: 10px; padding: 7px 12px; width: 240px; }
  .barra-fluxo input:focus { outline: none; border-color: var(--teal); }
  .chip-tipo { display: inline-flex; align-items: center; gap: 6px; font: inherit; font-size: 12px; font-weight: 700; cursor: pointer; color: var(--fg-dim);
               border: 1px solid var(--border); border-radius: 99px; padding: 5px 11px; background: rgba(var(--tinta), .03); }
  .chip-tipo i { width: 18px; height: 3px; border-radius: 2px; background: var(--cor); display: inline-block; }
  .chip-tipo.desligado { opacity: .38; text-decoration: line-through; }
  .chip-tipo:hover { color: var(--fg); }
  #chips-tipo { display: inline-flex; flex-wrap: wrap; gap: 8px; align-items: center; }
  .zoom-fluxo { margin-left: auto; display: inline-flex; gap: 6px; align-items: center; }
  .zoom-fluxo button { display: inline-flex; align-items: center; justify-content: center; box-sizing: border-box;
                       width: 34px; height: 34px; padding: 0; margin: 0; line-height: 1; vertical-align: middle;
                       border-radius: 9px; border: 1px solid var(--border); background: rgba(var(--tinta), .04); color: var(--fg); cursor: pointer; }
  .zoom-fluxo button svg { width: 16px; height: 16px; display: block; fill: none; stroke: currentColor; stroke-width: 2;
                           stroke-linecap: round; stroke-linejoin: round; }
  .zoom-fluxo button:hover { border-color: var(--teal); color: var(--teal); }
  .palco-fluxo { position: relative; display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 14px; }
  .tela-fluxo { position: relative; border: 1px solid var(--border); border-radius: 18px; overflow: hidden; height: 76vh; min-height: 560px;
                background: radial-gradient(circle at 20% 10%, rgba(45,184,207,.10), transparent 40%),
                            radial-gradient(circle at 85% 90%, rgba(176,203,28,.08), transparent 40%), var(--bg-panel);
                cursor: grab; touch-action: none; }
  .tela-fluxo.arrastando { cursor: grabbing; }
  .tela-fluxo svg { width: 100%; height: 100%; display: block; user-select: none; }
  .grade-fundo { stroke: rgba(var(--tinta), .045); stroke-width: 1; }
  .faixa-camada { fill: rgba(var(--tinta), .022); stroke: rgba(var(--tinta), .06); }
  .titulo-camada { fill: var(--fg-dim); font-size: 12px; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
  .ligacao { fill: none; stroke-width: 1.7; opacity: .5; transition: opacity .2s, stroke-width .2s; }
  .ligacao.fluxo { stroke-dasharray: 5 9; animation: correr 1.4s linear infinite; }
  @keyframes correr { to { stroke-dashoffset: -28; } }
  @media (prefers-reduced-motion: reduce) { .ligacao.fluxo { animation: none; } }
  .no { cursor: pointer; }
  .no rect.caixa { fill: var(--bg-panel-solid, #181f27); stroke: var(--cor); stroke-width: 1.4; transition: stroke-width .2s, filter .2s; }
  .no rect.faixa { fill: var(--cor); }
  .no text.nome { fill: var(--fg); font-size: 13px; font-weight: 700; }
  .no text.detalhe { fill: var(--fg-dim); font-size: 10.5px; }
  .no text.icone { font-size: 16px; }
  .no:hover rect.caixa, .no.escolhido rect.caixa { stroke-width: 2.6; filter: drop-shadow(0 0 10px var(--cor)); }
  svg.focando .no:not(.ligado) { opacity: .16; }
  svg.focando .ligacao:not(.ligado) { opacity: .04; }
  svg.focando .ligacao.ligado { opacity: 1; stroke-width: 2.6; }
  svg.focando .rotulo-lig:not(.ligado) { opacity: 0; }
  .rotulo-lig { font-size: 10px; font-weight: 700; fill: var(--fg); paint-order: stroke; stroke: var(--bg-panel-solid, #181f27); stroke-width: 4px;
                opacity: 0; transition: opacity .2s; pointer-events: none; }
  svg.focando .rotulo-lig.ligado { opacity: 1; }
  .no.oculto, .ligacao.oculto, .rotulo-lig.oculto { display: none; }
  /* painel de detalhes */
  .painel-fluxo { border: 1px solid var(--border); border-radius: 18px; background: var(--bg-panel); padding: 18px; height: 76vh; min-height: 560px;
                  overflow-y: auto; box-sizing: border-box; }
  .painel-fluxo .vazio { color: var(--fg-dim); font-size: 13px; line-height: 1.6; }
  .painel-fluxo .vazio b { color: var(--fg); }
  .painel-fluxo h2 { font-size: 18px; margin: 4px 0 2px; display: flex; align-items: center; gap: 8px; }
  .painel-fluxo .camada { font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--cor); }
  .painel-fluxo p { font-size: 13px; line-height: 1.6; color: var(--fg); margin: 10px 0; }
  .painel-fluxo h3 { font-size: 11px; letter-spacing: .08em; text-transform: uppercase; color: var(--fg-dim); margin: 16px 0 8px; }
  .lig-item { display: flex; gap: 8px; align-items: flex-start; font-size: 12.5px; padding: 7px 9px; border-radius: 10px; cursor: pointer;
              border: 1px solid transparent; }
  .lig-item:hover { border-color: var(--border); background: rgba(var(--tinta), .03); }
  .lig-item .seta { font-weight: 800; color: var(--cor); flex: none; width: 14px; }
  .lig-item .tipo { font-size: 10px; font-weight: 800; text-transform: uppercase; letter-spacing: .05em; color: var(--cor); }
  .lig-item .oque { color: var(--fg-dim); font-size: 11.5px; }
  .numeros-fluxo { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-top: 16px; }
  .numeros-fluxo div { border: 1px solid var(--border); border-radius: 12px; padding: 10px; text-align: center; }
  .numeros-fluxo b { display: block; font-size: 20px; }
  .numeros-fluxo span { font-size: 11px; color: var(--fg-dim); }
  .dica-fluxo { font-size: 11.5px; color: var(--fg-dim); margin-top: 10px; }
  @media (max-width: 1100px) { .palco-fluxo { grid-template-columns: minmax(0, 1fr); } .painel-fluxo { height: auto; min-height: 0; } }
  /* tela cheia (3.3.4.0): a barra e o mapa ocupam a tela toda; .cheia é o reserva pra navegador sem a Fullscreen API */
  #area-fluxo:fullscreen, #area-fluxo.cheia { background: var(--bg); padding: 14px 16px; box-sizing: border-box; display: flex; flex-direction: column; }
  #area-fluxo.cheia { position: fixed; inset: 0; z-index: 9999; }
  #area-fluxo:fullscreen .palco-fluxo, #area-fluxo.cheia .palco-fluxo { flex: 1; min-height: 0; }
  #area-fluxo:fullscreen .tela-fluxo, #area-fluxo.cheia .tela-fluxo,
  #area-fluxo:fullscreen .painel-fluxo, #area-fluxo.cheia .painel-fluxo { height: 100%; min-height: 0; }
  #area-fluxo:fullscreen .barra-fluxo, #area-fluxo.cheia .barra-fluxo { margin-bottom: 10px; }
  .zoom-fluxo button.ativo { border-color: var(--teal); color: var(--teal); }
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-fluxo">
    <div class="cab-fluxo">
      <div>
        <h1>Fluxograma do PDA <span class="selo-beta">Beta</span></h1>
        <div class="sub">Tudo que o PDA faz e com quem conversa: quem usa, o servidor e as rotinas, cada área, os dados que ele guarda e os sistemas de fora. Passe o mouse ou clique numa peça pra ver as ligações dela.</div>
      </div>
    </div>
    <div id="area-fluxo">
    <div class="barra-fluxo">
      <input type="search" id="busca-fluxo" placeholder="Buscar peça (ex.: Movidesk, Teams)" oninput="buscar(this.value)">
      <span id="chips-tipo"></span>
      <span class="zoom-fluxo">
        <button type="button" onclick="zoom(1.2)" aria-label="Aproximar" title="Aproximar"><svg viewBox="0 0 24 24"><path d="M12 5v14M5 12h14"/></svg></button>
        <button type="button" onclick="zoom(1 / 1.2)" aria-label="Afastar" title="Afastar"><svg viewBox="0 0 24 24"><path d="M5 12h14"/></svg></button>
        <button type="button" onclick="ajustar()" aria-label="Ver o mapa inteiro" title="Ver o mapa inteiro"><svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="6"/><path d="M20 20l-4.2-4.2M8.5 11h5"/></svg></button>
        <button type="button" id="btn-tela-cheia" onclick="alternarTelaCheia()" aria-label="Tela cheia" title="Tela cheia (F)"><svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg></button>
      </span>
    </div>
    <div class="palco-fluxo">
      <div class="tela-fluxo" id="tela-fluxo"><svg id="svg-fluxo" xmlns="http://www.w3.org/2000/svg"></svg></div>
      <aside class="painel-fluxo" id="painel-fluxo"></aside>
    </div>
    </div>
  </div>
  __FOOTER__
<script>
const TIPOS = {
  http:    { nome: 'Navegador / HTTP', cor: '#2db8cf' },
  sql:     { nome: 'Banco SQL', cor: '#f59e0b' },
  api:     { nome: 'API externa', cor: '#a78bfa' },
  webhook: { nome: 'Teams (Workflow)', cor: '#6366f1' },
  email:   { nome: 'E-mail (SMTP)', cor: '#f472b6' },
  arquivo: { nome: 'Arquivo local', cor: '#b0cb1c' },
  interno: { nome: 'Dentro do PDA', cor: '#64748b' },
};
const CAMADAS = [
  { id: 'pessoas', nome: 'Quem usa', cor: '#2db8cf' },
  { id: 'pda', nome: 'PDA', cor: '#22c55e' },
  { id: 'areas', nome: 'Áreas', cor: '#eab308' },
  { id: 'dados', nome: 'Dados do PDA', cor: '#b0cb1c' },
  { id: 'fora', nome: 'Sistemas de fora', cor: '#a78bfa' },
];
const NOS = [
  { id: 'equipe', camada: 'pessoas', icone: '👥', nome: 'Equipe no navegador', detalhe: 'Suporte, Monitoramento, Serviços',
    texto: 'Todo mundo usa o PDA pelo navegador (pda.local ou 192.0.2.198:8765), com login e permissões por pessoa. A Central de Monitores abre até sem login.' },
  { id: 'admin', camada: 'pessoas', icone: '🛡️', nome: 'Administradores', detalhe: 'Igor, Debora e gestão',
    texto: 'Administradores enxergam a Gestão de equipe, cadastram usuários e permissões, atribuem ranks e publicam na Comunidade.' },
  { id: 'janela', camada: 'pessoas', icone: '🖥️', nome: 'Janela do PDA', detalhe: 'PainelAlertas.exe (Tkinter)',
    texto: 'O programa roda na máquina do servidor: a janela Tkinter sobe o servidor web, o agendador e as rotinas em segundo plano. Compilado com PyInstaller.' },
  { id: 'web', camada: 'pda', icone: '🌐', nome: 'Servidor web', detalhe: 'http.server · portas 8765 e 80',
    texto: 'Servidor HTTP feito à mão (sem framework): monta cada tela, responde as rotas /api e entrega fotos, anexos e arquivos. Sessão por cookie, 90 min sem uso desconecta.' },
  { id: 'agendador', camada: 'pda', icone: '⏰', nome: 'Agendador de jobs', detalhe: '12 alertas + rotinas diárias',
    texto: 'Roda os alertas nos horários de cada um (fila de e-mail, NFSe, CTe, Manifestações...), os e-mails de 45/90 dias, a limpeza de logs e o Relatório ClienteA. Falha repetida avisa no Teams.' },
  { id: 'rotinas', camada: 'pda', icone: '🔁', nome: 'Rotinas contínuas', detalhe: 'Contingências, EmailPack, CTe2',
    texto: 'Threads que ficam rodando: monitor de Contingências SEFAZ, varredura do EmailPack e o ciclo do Reprocessamento CTe2 (60 s).' },
  { id: 'comunidade', camada: 'areas', icone: '💬', nome: 'Comunidade', detalhe: 'feed, publicações, votação',
    texto: 'O feed da equipe: aniversários, promoções, insígnias, férias, publicações com fotos e votação, palminhas, comentários e o sininho.' },
  { id: 'rankings', camada: 'areas', icone: '🏆', nome: 'Rankings e insígnias', detalhe: 'produtos, palminhas, perfil',
    texto: 'Nível de cada pessoa por produto, leaderboard geral e por equipe, palminhas e as insígnias do perfil.' },
  { id: 'horas', camada: 'areas', icone: '⏱️', nome: 'Horas e indicadores', detalhe: 'Horas, Indicadores, Mensais',
    texto: 'Horas trabalhadas x meta pela escala, Indicadores Movidesk e o fechamento mensal (efetividade, NOC e satisfação).' },
  { id: 'gestao', camada: 'areas', icone: '🧑‍💼', nome: 'Gestão e usuários', detalhe: 'Usuários, Feedbacks, Férias',
    texto: 'Cadastro e permissões, feedbacks e alinhamentos por equipe, calendário de férias e a sincronização com o Movidesk.' },
  { id: 'alertas', camada: 'areas', icone: '🔔', nome: 'Alertas e manutenções', detalhe: 'alertas, rejeições, relatórios',
    texto: 'Os alertas por cliente e as manutenções em banco (alertas, rejeições e relatórios), além da Validação FTP.' },
  { id: 'relatorios', camada: 'areas', icone: '📊', nome: 'Relatórios e Dash', detalhe: 'ClienteA, Dash Financeiro',
    texto: 'Relatórios ClienteA em Excel enviados pro SharePoint e o Dash Financeiro: um CSV por mês por produto pro Power BI.' },
  { id: 'cte2', camada: 'areas', icone: '♻️', nome: 'Reprocessamento CTe2', detalhe: 'automação do Caio',
    texto: 'Acha os CT-e parados na INTERF_CTE e pede o reprocessamento na API do CTe2. Falhou uma vez, a chave fica bloqueada até alguém liberar.' },
  { id: 'central', camada: 'areas', icone: '🛰️', nome: 'Central de Monitores', detalhe: 'links por cliente, editável',
    texto: 'Os monitores e a infraestrutura de cada cliente, com produtos por servidor. Aberta sem login; administradores com permissão editam pela própria tela.' },
  { id: 'contingencias', camada: 'areas', icone: '🚦', nome: 'Contingências SEFAZ', detalhe: 'SVC-AN e SVC-RS',
    texto: 'Lê as páginas públicas da SEFAZ e avisa no Teams quando uma UF entra ou sai de contingência.' },
  { id: 'json', camada: 'dados', icone: '🗂️', nome: 'Arquivos JSON', detalhe: 'usuarios, mural, ranks, férias...',
    texto: 'Tudo que o PDA guarda fica em arquivos ao lado do programa: usuários e permissões, mural, palminhas, comentários, publicações, ranks, férias, notificações e a Central. Fora do git.' },
  { id: 'segredos', camada: 'dados', icone: '🔐', nome: 'Credenciais', detalhe: 'config.dat cifrado + .env central',
    texto: 'Senhas e chaves cifradas no config.dat (chave.key) e as conexões no CREDENCIAIS_CENTRALIZADAS.env. A tela nunca mostra o valor de volta.' },
  { id: 'arquivos', camada: 'dados', icone: '📁', nome: 'Fotos, anexos e logs', detalhe: 'fotos_usuarios, anexos, logs/',
    texto: 'Fotos de perfil, anexos de feedback e de publicações, CSVs do Dash e os logs de cada área (apagados depois de 30 dias).' },
  { id: 'bancos', camada: 'fora', icone: '🗄️', nome: 'Bancos dos clientes', detalhe: 'SQL Server de cada produto',
    texto: 'Os bancos SQL Server dos produtos de cada cliente: consultados pelos alertas, pelas manutenções, pelo Dash, pelos relatórios e pelo cadastro de usuários.' },
  { id: 'bdmovidesk', camada: 'fora', icone: '🧮', nome: 'Banco do Movidesk', detalhe: 'apontamentos, tickets, NOC',
    texto: 'A base com os dados do Movidesk (apontamentos, tickets, NOC, satisfação e a tabela usuarios): horas, indicadores e fechamento do mês.' },
  { id: 'apimovidesk', camada: 'fora', icone: '🎧', nome: 'API do Movidesk', detalhe: 'pessoas e agentes',
    texto: 'Cadastro e desativação de pessoas e a sincronização dos agentes ativos com a tabela usuarios.' },
  { id: 'teams', camada: 'fora', icone: '💠', nome: 'Microsoft Teams', detalhe: 'Workflows do Power Automate',
    texto: 'Cartões nos canais: falha de job, Contingências, EmailPack e as publicações importantes da Comunidade.' },
  { id: 'smtp', camada: 'fora', icone: '✉️', nome: 'Servidor de e-mail', detalhe: 'mailserver.example-cloud',
    texto: 'Alertas por e-mail, boas-vindas, 45/90 dias de empresa, feedbacks e a insígnia Beta, com as fotos por CID.' },
  { id: 'sharepoint', camada: 'fora', icone: '☁️', nome: 'SharePoint', detalhe: 'Microsoft Graph',
    texto: 'Pasta dos Relatórios ClienteA, organizada por ano, mês e dia.' },
  { id: 'apicte2', camada: 'fora', icone: '🚚', nome: 'API do CTe2', detalhe: 'saas.example.app/cte2',
    texto: 'Recebe o pedido de reprocessamento de cada chave, com a x-api-key.' },
  { id: 'sefaz', camada: 'fora', icone: '🏛️', nome: 'Portais da SEFAZ', detalhe: 'nfe.fazenda e sefaz.rs',
    texto: 'Páginas públicas com a situação das contingências por UF.' },
  { id: 'servidores', camada: 'fora', icone: '🖧', nome: 'Servidores e monitores', detalhe: 'EmailPack, webmonitors',
    texto: 'Logs dos serviços EmailPack nos servidores e os webmonitors de cada cliente abertos pela Central.' },
  { id: 'powerbi', camada: 'fora', icone: '📈', nome: 'Power BI', detalhe: 'relatórios e Dash',
    texto: 'Lê os CSVs do Dash Financeiro e mostra os relatórios embutidos em Dashboards por Cliente.' },
];
const LIGACOES = [
  ['equipe', 'web', 'http', 'usa as telas'], ['admin', 'web', 'http', 'administra'], ['janela', 'web', 'interno', 'sobe o servidor'],
  ['janela', 'agendador', 'interno', 'liga'], ['janela', 'rotinas', 'interno', 'liga'],
  ['web', 'comunidade', 'interno', 'telas e /api'], ['web', 'rankings', 'interno', 'telas e /api'], ['web', 'horas', 'interno', 'telas e /api'],
  ['web', 'gestao', 'interno', 'telas e /api'], ['web', 'alertas', 'interno', 'telas e /api'], ['web', 'relatorios', 'interno', 'telas e /api'],
  ['web', 'cte2', 'interno', 'card'], ['web', 'central', 'interno', 'página pública'], ['web', 'contingencias', 'interno', 'card'],
  ['agendador', 'alertas', 'interno', 'roda os alertas'], ['agendador', 'relatorios', 'interno', 'ClienteA diário · Dash dia 1'],
  ['agendador', 'gestao', 'interno', 'e-mails de 45/90 dias'], ['rotinas', 'contingencias', 'interno', 'monitor'], ['rotinas', 'cte2', 'interno', 'ciclo de 60 s'],
  ['comunidade', 'json', 'arquivo', 'mural, palminhas, posts'], ['comunidade', 'arquivos', 'arquivo', 'fotos e anexos'], ['comunidade', 'teams', 'webhook', 'publicação importante'],
  ['rankings', 'json', 'arquivo', 'ranks e insígnias'], ['gestao', 'json', 'arquivo', 'usuários, feedbacks, férias'], ['gestao', 'arquivos', 'arquivo', 'fotos e anexos'],
  ['gestao', 'apimovidesk', 'api', 'cadastro e sincronização'], ['gestao', 'bancos', 'sql', 'cadastro de usuários'], ['gestao', 'smtp', 'email', 'boas-vindas e feedback'],
  ['gestao', 'bdmovidesk', 'sql', 'tabela usuarios'],
  ['horas', 'bdmovidesk', 'sql', 'apontamentos e tickets'],
  ['alertas', 'bancos', 'sql', 'consultas dos alertas'], ['alertas', 'smtp', 'email', 'alerta por e-mail'], ['alertas', 'teams', 'webhook', 'falha de job'],
  ['relatorios', 'bancos', 'sql', 'dados do mês'], ['relatorios', 'sharepoint', 'api', 'Excel da ClienteA'], ['relatorios', 'arquivos', 'arquivo', 'CSV por mês'],
  ['arquivos', 'powerbi', 'arquivo', 'CSV do Dash'],
  ['cte2', 'bancos', 'sql', 'INTERF_CTE'], ['cte2', 'apicte2', 'api', 'reprocessar chave'], ['cte2', 'json', 'arquivo', 'controle e bloqueios'],
  ['central', 'json', 'arquivo', 'clientes e links'], ['central', 'servidores', 'http', 'abre os webmonitors'],
  ['contingencias', 'sefaz', 'http', 'lê as páginas'], ['contingencias', 'teams', 'webhook', 'entrou/saiu de contingência'],
  ['rotinas', 'servidores', 'arquivo', 'logs do EmailPack'], ['rotinas', 'teams', 'webhook', 'aviso do EmailPack'],
  ['agendador', 'segredos', 'arquivo', 'conexões'], ['web', 'segredos', 'arquivo', 'credenciais'], ['web', 'json', 'arquivo', 'sessões e permissões'],
];

const LARG = 1500, ALT = 1000, NO_L = 210, NO_A = 56;
const svgNS = 'http://www.w3.org/2000/svg';
const svg = document.getElementById('svg-fluxo');
let vista = { x: 0, y: 0, w: LARG, h: ALT };
const tiposLigados = new Set(Object.keys(TIPOS));
let escolhido = null;
const pos = {};

function el(nome, attrs, pai) {
  const e = document.createElementNS(svgNS, nome);
  Object.entries(attrs || {}).forEach(([k, v]) => e.setAttribute(k, v));
  if (pai) pai.appendChild(e);
  return e;
}
function corCamada(id) { return (CAMADAS.find(c => c.id === id) || {}).cor || '#64748b'; }

function posicionar() {
  const larguraColuna = LARG / CAMADAS.length;
  CAMADAS.forEach((c, i) => {
    const nos = NOS.filter(n => n.camada === c.id);
    const passo = Math.min(108, (ALT - 120) / Math.max(nos.length, 1));
    const total = passo * (nos.length - 1);
    nos.forEach((n, j) => {
      pos[n.id] = { x: larguraColuna * i + (larguraColuna - NO_L) / 2, y: 90 + (ALT - 120 - total) / 2 + passo * j - NO_A / 2 };
    });
  });
}

function caminho(a, b) {
  const pa = pos[a], pb = pos[b];
  const vaiPraDireita = pb.x > pa.x + 10;
  const x1 = vaiPraDireita ? pa.x + NO_L : pa.x + NO_L / 2, y1 = vaiPraDireita ? pa.y + NO_A / 2 : pa.y + (pb.y > pa.y ? NO_A : 0);
  const x2 = vaiPraDireita ? pb.x : pb.x + NO_L / 2, y2 = vaiPraDireita ? pb.y + NO_A / 2 : pb.y + (pb.y > pa.y ? 0 : NO_A);
  if (!vaiPraDireita) {
    const meio = (x1 + x2) / 2 + 120;
    return { d: 'M' + x1 + ',' + y1 + ' C' + meio + ',' + y1 + ' ' + meio + ',' + y2 + ' ' + x2 + ',' + y2, mx: meio - 30, my: (y1 + y2) / 2 };
  }
  const dx = Math.max(60, (x2 - x1) * 0.5);
  return { d: 'M' + x1 + ',' + y1 + ' C' + (x1 + dx) + ',' + y1 + ' ' + (x2 - dx) + ',' + y2 + ' ' + x2 + ',' + y2, mx: (x1 + x2) / 2, my: (y1 + y2) / 2 };
}

function desenhar() {
  svg.innerHTML = '';
  const defs = el('defs', {}, svg);
  Object.entries(TIPOS).forEach(([id, t]) => {
    const m = el('marker', { id: 'seta-' + id, viewBox: '0 0 10 10', refX: 9, refY: 5, markerWidth: 7, markerHeight: 7, orient: 'auto-start-reverse' }, defs);
    el('path', { d: 'M0,0 L10,5 L0,10 z', fill: t.cor }, m);
  });
  const fundo = el('g', {}, svg);
  for (let x = 0; x <= LARG; x += 50) el('line', { x1: x, y1: 0, x2: x, y2: ALT, class: 'grade-fundo' }, fundo);
  for (let y = 0; y <= ALT; y += 50) el('line', { x1: 0, y1: y, x2: LARG, y2: y, class: 'grade-fundo' }, fundo);
  const larguraColuna = LARG / CAMADAS.length;
  CAMADAS.forEach((c, i) => {
    el('rect', { x: larguraColuna * i + 10, y: 20, width: larguraColuna - 20, height: ALT - 40, rx: 22, class: 'faixa-camada' }, fundo);
    const t = el('text', { x: larguraColuna * i + larguraColuna / 2, y: 54, 'text-anchor': 'middle', class: 'titulo-camada' }, fundo);
    t.textContent = c.nome;
  });
  const gLig = el('g', {}, svg), gRot = el('g', {}, svg), gNos = el('g', {}, svg);
  LIGACOES.forEach(([a, b, tipo, oque], i) => {
    const c = caminho(a, b);
    el('path', { d: c.d, class: 'ligacao fluxo', stroke: TIPOS[tipo].cor, 'marker-end': 'url(#seta-' + tipo + ')',
                 'data-a': a, 'data-b': b, 'data-tipo': tipo, 'data-i': i }, gLig);
    const r = el('text', { x: c.mx, y: c.my - 4, 'text-anchor': 'middle', class: 'rotulo-lig', 'data-a': a, 'data-b': b, 'data-tipo': tipo }, gRot);
    r.textContent = oque;
  });
  NOS.forEach(n => {
    const p = pos[n.id];
    const g = el('g', { class: 'no', transform: 'translate(' + p.x + ',' + p.y + ')', 'data-id': n.id, tabindex: 0, role: 'button',
                        'aria-label': n.nome + ': ' + n.detalhe, style: '--cor:' + corCamada(n.camada) }, gNos);
    el('rect', { class: 'caixa', width: NO_L, height: NO_A, rx: 14 }, g);
    el('rect', { class: 'faixa', width: 5, height: NO_A - 20, x: 0, y: 10, rx: 2.5 }, g);
    const ic = el('text', { class: 'icone', x: 16, y: 35 }, g); ic.textContent = n.icone;
    const nm = el('text', { class: 'nome', x: 44, y: 25 }, g); nm.textContent = n.nome;
    const dt = el('text', { class: 'detalhe', x: 44, y: 41 }, g); dt.textContent = n.detalhe;
    g.addEventListener('mouseenter', () => { if (!escolhido) focar(n.id); });
    g.addEventListener('mouseleave', () => { if (!escolhido) focar(null); });
    g.addEventListener('click', ev => { ev.stopPropagation(); escolher(escolhido === n.id ? null : n.id); });
    g.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); escolher(escolhido === n.id ? null : n.id); } });
  });
  aplicarFiltros();
  aplicarVista();
}

function vizinhos(id) {
  const lig = LIGACOES.filter(([a, b, t]) => (a === id || b === id) && tiposLigados.has(t));
  return new Set([id].concat(lig.map(([a, b]) => a === id ? b : a)));
}
function focar(id) {
  svg.classList.toggle('focando', !!id);
  const viz = id ? vizinhos(id) : new Set();
  svg.querySelectorAll('.no').forEach(g => g.classList.toggle('ligado', viz.has(g.dataset.id)));
  svg.querySelectorAll('.ligacao, .rotulo-lig').forEach(l => l.classList.toggle('ligado', !!id && (l.dataset.a === id || l.dataset.b === id)));
}
function escolher(id) {
  escolhido = id;
  svg.querySelectorAll('.no').forEach(g => g.classList.toggle('escolhido', g.dataset.id === id));
  focar(id);
  painel(id);
}
function painel(id) {
  const alvo = document.getElementById('painel-fluxo');
  if (!id) {
    const externos = NOS.filter(n => n.camada === 'fora').length;
    alvo.innerHTML = '<div class="vazio"><b>Como ler o mapa</b><br>Cada coluna é uma camada: quem usa, o PDA, as áreas, os dados que ele guarda e os sistemas de fora. '
      + 'As linhas animadas são as conversas, coloridas pelo tipo (filtre pelos botões lá em cima).<br><br>Passe o mouse numa peça pra destacar com quem ela fala, ou clique pra fixar e ver os detalhes aqui. '
      + 'Arraste pra mover e use a roda do mouse (ou + e −) pro zoom.</div>'
      + '<div class="numeros-fluxo"><div><b>' + NOS.length + '</b><span>peças</span></div><div><b>' + LIGACOES.length + '</b><span>ligações</span></div><div><b>' + externos + '</b><span>sistemas de fora</span></div></div>';
    return;
  }
  const n = NOS.find(x => x.id === id);
  const camada = CAMADAS.find(c => c.id === n.camada);
  const saem = LIGACOES.filter(l => l[0] === id), chegam = LIGACOES.filter(l => l[1] === id);
  const item = (outro, tipo, oque, seta) => {
    const o = NOS.find(x => x.id === outro);
    return '<div class="lig-item" style="--cor:' + TIPOS[tipo].cor + '" onclick="escolher(' + "'" + outro + "'" + ')"><span class="seta">' + seta + '</span>'
      + '<div><div>' + o.icone + ' ' + o.nome + ' <span class="tipo">' + TIPOS[tipo].nome + '</span></div><div class="oque">' + oque + '</div></div></div>';
  };
  alvo.innerHTML = '<div class="camada" style="--cor:' + camada.cor + '">' + camada.nome + '</div>'
    + '<h2>' + n.icone + ' ' + n.nome + '</h2><div style="font-size:12px;color:var(--fg-dim)">' + n.detalhe + '</div>'
    + '<p>' + n.texto + '</p>'
    + (saem.length ? '<h3>Fala com (' + saem.length + ')</h3>' + saem.map(l => item(l[1], l[2], l[3], '→')).join('') : '')
    + (chegam.length ? '<h3>Recebe de (' + chegam.length + ')</h3>' + chegam.map(l => item(l[0], l[2], l[3], '←')).join('') : '')
    + '<div class="dica-fluxo">Clique de novo na peça, ou no fundo, pra soltar.</div>';
}
function aplicarFiltros() {
  svg.querySelectorAll('.ligacao, .rotulo-lig').forEach(l => l.classList.toggle('oculto', !tiposLigados.has(l.dataset.tipo)));
  if (escolhido) focar(escolhido);
}
function desenharChips() {
  document.getElementById('chips-tipo').innerHTML = Object.entries(TIPOS).map(([id, t]) =>
    '<button class="chip-tipo' + (tiposLigados.has(id) ? '' : ' desligado') + '" style="--cor:' + t.cor + '" onclick="alternarTipo(' + "'" + id + "'" + ')"><i></i>' + t.nome + '</button>').join(' ');
}
function alternarTipo(id) { tiposLigados.has(id) ? tiposLigados.delete(id) : tiposLigados.add(id); desenharChips(); aplicarFiltros(); }
function buscar(texto) {
  const t = texto.trim().toLowerCase();
  svg.querySelectorAll('.no').forEach(g => {
    const n = NOS.find(x => x.id === g.dataset.id);
    g.classList.toggle('oculto', !!t && !(n.nome + ' ' + n.detalhe + ' ' + n.texto).toLowerCase().includes(t));
  });
}
// zoom e arrastar (viewBox)
function aplicarVista() { svg.setAttribute('viewBox', vista.x + ' ' + vista.y + ' ' + vista.w + ' ' + vista.h); }
function zoom(fator, cx, cy) {
  const nw = Math.min(LARG * 2, Math.max(LARG / 4, vista.w / fator));
  const nh = nw * (vista.h / vista.w);
  cx = cx == null ? vista.x + vista.w / 2 : cx; cy = cy == null ? vista.y + vista.h / 2 : cy;
  vista = { x: cx - (cx - vista.x) * (nw / vista.w), y: cy - (cy - vista.y) * (nh / vista.h), w: nw, h: nh };
  aplicarVista();
}
function ajustar() { vista = { x: 0, y: 0, w: LARG, h: ALT }; aplicarVista(); }
const tela = document.getElementById('tela-fluxo');
let arraste = null;
tela.addEventListener('wheel', ev => {
  ev.preventDefault();
  const r = svg.getBoundingClientRect();
  zoom(ev.deltaY < 0 ? 1.12 : 1 / 1.12, vista.x + (ev.clientX - r.left) / r.width * vista.w, vista.y + (ev.clientY - r.top) / r.height * vista.h);
}, { passive: false });
tela.addEventListener('pointerdown', ev => {
  if (ev.target.closest('.no')) return;
  arraste = { x: ev.clientX, y: ev.clientY, vx: vista.x, vy: vista.y, moveu: false };
  tela.classList.add('arrastando');
});
window.addEventListener('pointermove', ev => {
  if (!arraste) return;
  const r = svg.getBoundingClientRect();
  if (Math.abs(ev.clientX - arraste.x) + Math.abs(ev.clientY - arraste.y) > 3) arraste.moveu = true;
  vista.x = arraste.vx - (ev.clientX - arraste.x) / r.width * vista.w;
  vista.y = arraste.vy - (ev.clientY - arraste.y) / r.height * vista.h;
  aplicarVista();
});
window.addEventListener('pointerup', () => {
  if (arraste && !arraste.moveu) escolher(null);  // clique no fundo solta a peça
  arraste = null; tela.classList.remove('arrastando');
});
document.addEventListener('keydown', ev => { if (ev.key === 'Escape') escolher(null); });

// tela cheia (3.3.4.0): Fullscreen API na barra + mapa; sem ela (ou se o navegador recusar), cobre a janela com .cheia
const SVG_ENTRAR_CHEIA = '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>';
const SVG_SAIR_CHEIA = '<svg viewBox="0 0 24 24"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg>';
function emTelaCheia() { const a = document.getElementById('area-fluxo'); return document.fullscreenElement === a || a.classList.contains('cheia'); }
function marcarTelaCheia() {
  const b = document.getElementById('btn-tela-cheia');
  const cheia = emTelaCheia();
  b.innerHTML = cheia ? SVG_SAIR_CHEIA : SVG_ENTRAR_CHEIA;
  b.classList.toggle('ativo', cheia);
  b.title = cheia ? 'Sair da tela cheia (Esc)' : 'Tela cheia (F)';
  b.setAttribute('aria-label', cheia ? 'Sair da tela cheia' : 'Tela cheia');
  document.body.style.overflow = document.getElementById('area-fluxo').classList.contains('cheia') ? 'hidden' : '';
  ajustar();
}
function alternarTelaCheia() {
  const a = document.getElementById('area-fluxo');
  if (a.classList.contains('cheia')) { a.classList.remove('cheia'); marcarTelaCheia(); return; }
  if (document.fullscreenElement) { document.exitFullscreen(); return; }
  const reserva = () => { a.classList.add('cheia'); marcarTelaCheia(); };
  if (!a.requestFullscreen) { reserva(); return; }
  // alguns navegadores embutidos deixam o pedido pendente sem responder: sem tela cheia em 700 ms, cobre a janela
  let respondeu = false;
  a.requestFullscreen().then(() => { respondeu = true; }, () => { respondeu = true; reserva(); });
  setTimeout(() => { if (!respondeu && !document.fullscreenElement && !a.classList.contains('cheia')) reserva(); }, 700);
}
document.addEventListener('fullscreenchange', marcarTelaCheia);
document.addEventListener('keydown', ev => {
  const a = document.getElementById('area-fluxo');
  if (ev.key === 'Escape' && a.classList.contains('cheia')) { a.classList.remove('cheia'); marcarTelaCheia(); return; }
  const digitando = ev.target && (ev.target.tagName === 'INPUT' || ev.target.tagName === 'TEXTAREA');
  if (!digitando && !ev.ctrlKey && !ev.metaKey && !ev.altKey && (ev.key === 'f' || ev.key === 'F')) { ev.preventDefault(); alternarTelaCheia(); }
});

posicionar();
desenharChips();
desenhar();
painel(null);
</script>
</body>
</html>
"""
