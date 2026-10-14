"""Tela Perfil.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
2.35.5.0: insígnias (painel e mini-insígnias no cabeçalho, desenhadas por telas/insignias.py),
data de início e histórico na empresa editáveis pela própria pessoa.
"""


_PERFIL_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Perfil</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  body { position: relative; }
  body::before {
    content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background: radial-gradient(ellipse 900px 500px at 20% 0%, rgba(45,184,207,.06), transparent 60%),
                radial-gradient(ellipse 800px 500px at 85% 100%, rgba(176,203,28,.05), transparent 60%);
  }
  .conteudo { position: relative; z-index: 1; max-width: 720px; }

  .cabecalho-perfil { display: flex; align-items: center; gap: 22px; margin-bottom: 24px; flex-wrap: wrap; }
  .foto-perfil-wrap { position: relative; width: 96px; height: 96px; flex-shrink: 0; }
  .foto-perfil { width: 96px; height: 96px; border-radius: 50%; object-fit: cover;
                  border: 3px solid var(--border-forte); background: rgba(var(--tinta),.04);
                  display: flex; align-items: center; justify-content: center; font-size: 30px; font-weight: 800;
                  color: #08090c; }
  .botao-trocar-foto { position: absolute; bottom: -2px; right: -2px; width: 30px; height: 30px; border-radius: 50%;
                        background: var(--gradiente-marca); border: 2px solid var(--bg); cursor: pointer;
                        display: flex; align-items: center; justify-content: center; }
  .botao-trocar-foto svg { width: 15px; height: 15px; color: #08090c; }
  .info-cabecalho-perfil h1 { margin: 0 0 6px 0; font-size: 22px; font-weight: 800;
                                background: var(--gradiente-marca); -webkit-background-clip: text;
                                background-clip: text; color: transparent; }
  .cargo-perfil { font-size: 13px; color: var(--fg-dim); margin-bottom: 10px; }
  .badges-perfil { display: flex; gap: 8px; flex-wrap: wrap; }
  .badge-perfil { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 6px;
                   background: rgba(var(--tinta),.06); color: var(--fg-dim); }
  .badge-perfil.atribuicao-suporte { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-perfil.atribuicao-monitoramento { background: rgba(176,203,28,.15); color: var(--lime); }
  .badge-perfil.atribuicao-servicos { background: rgba(167,139,250,.16); color: #a78bfa; }
  /* usuário desativado no PDA (3.1.5.0): em vermelho, com o aviso do que isso costuma querer dizer */
  .badge-perfil.desativado { background: rgba(241,76,76,.15); color: var(--erro); }
  .aviso-desativado { margin-top: 10px; font-size: 12.5px; color: var(--erro); background: rgba(241,76,76,.08); border: 1px solid rgba(241,76,76,.35);
                      border-radius: 10px; padding: 8px 12px; max-width: 460px; line-height: 1.45; }
  .badge-perfil.atribuicao-ambas { background: linear-gradient(135deg, rgba(45,184,207,.18), rgba(176,203,28,.18)); color: var(--fg); }

  .painel-perfil { background: var(--bg-panel); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
                    border: 1px solid var(--border); border-radius: 14px; padding: 22px 24px; margin-bottom: 18px; }
  .painel-perfil h2 { margin: 0 0 16px 0; font-size: 12.5px; color: var(--fg-dim); text-transform: uppercase;
                       letter-spacing: .06em; font-weight: 700; }
  .cabecalho-com-acao { display: flex; align-items: center; justify-content: space-between; }
  .btn-editar-historico { background: rgba(var(--tinta),.05); border: 1px solid var(--border); border-radius: 7px;
      width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; cursor: pointer;
      color: var(--fg-dim); transition: all .15s; flex-shrink: 0; font-size: 12px; line-height: 1; }
  .btn-editar-historico:hover, .btn-editar-historico.ativo { color: var(--teal); border-color: var(--teal);
      background: rgba(45,184,207,.1); }
  /* fora do modo de edição, some com os botões de remover e o formulário
     de adicionar - fica só a timeline limpa (pedido: "bem bonito
     visualmente" quando não tá editando) */
  #painel-historico-carreira:not(.modo-edicao) .btn-remover-timeline,
  #painel-historico-carreira:not(.modo-edicao) .btn-editar-timeline,
  #painel-historico-carreira:not(.modo-edicao) .form-add-timeline { display: none; }

  /* ---------- insígnias (2.35.5.0) ---------- */
  .destaque-foto-ins { position: absolute; left: -16px; bottom: -14px; z-index: 2; pointer-events: auto; cursor: pointer;
                       filter: drop-shadow(0 4px 8px rgba(0,0,0,.45)); transition: transform .15s; background: none; border: none; padding: 0; }
  .destaque-foto-ins:hover { transform: scale(1.08) rotate(-4deg); }
  .btn-destacar-ins { margin-top: 8px; background: none; border: 1px solid var(--border); color: var(--fg-dim); border-radius: 999px; padding: 3px 10px;
                      font-size: 10.5px; font-weight: 700; cursor: pointer; font-family: inherit; }
  .btn-destacar-ins:hover { color: var(--lime); border-color: rgba(176,203,28,.55); }
  .card-insignia.em-destaque { box-shadow: 0 0 0 2px rgba(176,203,28,.55); }
  .selo-destaque-ins { position: absolute; top: 9px; left: 9px; font-size: 9.5px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase;
                       color: var(--lime); background: rgba(176,203,28,.14); padding: 2px 7px; border-radius: 999px; }
  .btn-participar-ins { margin-top: 10px; align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; border: none; border-radius: 9px;
                        background: var(--gradiente-marca); color: #0b0f14; font-weight: 800; font-size: 12px; padding: 8px 14px; cursor: pointer; font-family: inherit; }
  .minis-insignias { display: flex; gap: 2px; margin-top: 10px; flex-wrap: wrap; }
  .minis-insignias button { background: none; border: none; padding: 0; cursor: pointer; transition: transform .15s; }
  .minis-insignias button:hover { transform: translateY(-2px) scale(1.06); }
  .desde-perfil { font-size: 12.5px; color: var(--fg-dim); margin-top: 9px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .desde-perfil b { color: var(--fg); }
  .btn-lapis-perfil { background: none; border: 1px solid var(--border); color: var(--fg-dim); border-radius: 7px; padding: 2px 8px; font-size: 11.5px;
                      cursor: pointer; font-family: inherit; }
  .btn-lapis-perfil:hover { color: var(--teal); border-color: var(--teal); }
  .btn-lapis-perfil.destaque { color: var(--teal); border-color: rgba(45,184,207,.55); background: rgba(45,184,207,.08); }
  .form-desde-perfil { display: inline-flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .form-desde-perfil input { background: rgba(var(--poco),.28); border: 1px solid var(--border); color: var(--fg); border-radius: 7px;
                             padding: 5px 8px; font-size: 12.5px; font-family: inherit; color-scheme: dark; }
  :root[data-tema="claro"] .form-desde-perfil input { color-scheme: light; }
  .contagem-insignias { font-size: 12px; color: var(--fg-dim); font-weight: 400; text-transform: none; letter-spacing: 0; }
  .contagem-insignias b { color: var(--fg); }
  .grade-insignias-perfil { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; }
  .card-insignia { border: 1px solid var(--border); border-radius: 14px; padding: 14px 10px 12px; text-align: center; position: relative;
                   background: rgba(var(--tinta),.02); display: flex; flex-direction: column; align-items: center; }
  .card-insignia.ganha { border-color: rgba(45,184,207,.45); background: radial-gradient(90% 70% at 50% 0%, rgba(45,184,207,.13), transparent 70%); }
  .card-insignia.ganha.fundador { border-color: rgba(179,137,249,.5); background: radial-gradient(90% 70% at 50% 0%, rgba(179,137,249,.15), transparent 70%); }
  .card-insignia.ganha.contribuidor { border-color: rgba(155,93,229,.45); background: radial-gradient(90% 70% at 50% 0%, rgba(76,201,240,.13), transparent 70%); }
  .card-insignia .nome-ins { font-size: 12.5px; font-weight: 800; color: var(--fg); margin-top: 6px; }
  .card-insignia .desc-ins { font-size: 10.5px; color: var(--fg-dim); margin-top: 3px; line-height: 1.4; }
  .clicavel-foto { cursor: zoom-in; }
  .painel-concessoes { border-color: rgba(176,203,28,.4); }
  .linha-conc { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-top: 1px solid var(--border); }
  .linha-conc:first-of-type { border-top: none; }
  .linha-conc .info-conc { flex: 1; }
  .linha-conc .info-conc b { display: block; font-size: 14px; }
  .estado-conc { font-size: 12px; color: var(--fg-dim); }
  .estado-conc.ok { color: var(--ok); }
  .btn-mini.primario-conc { background: var(--teal); color: #071016; border-color: var(--teal); font-weight: 800; }
  .card-insignia .quando-ins { display: inline-block; margin-top: 8px; font-size: 10px; font-weight: 700; color: var(--ok); background: rgba(78,201,176,.12);
                               padding: 2px 8px; border-radius: 999px; }
  .card-insignia.trancada .quando-ins { color: var(--fg-dim); background: rgba(var(--tinta),.06); }
  .card-insignia .cad-ins { position: absolute; top: 10px; right: 10px; color: var(--fg-dim); opacity: .7; }
  .card-insignia .cad-ins svg { width: 13px; height: 13px; display: block; }
  .card-insignia.com-requisitos { grid-column: span 2; align-items: stretch; text-align: left; flex-direction: row; gap: 14px; padding: 14px; }
  .card-insignia.com-requisitos .lado-ins { display: flex; flex-direction: column; align-items: center; text-align: center; flex: none; width: 120px; }
  .requisitos-ins { flex: 1; display: flex; flex-direction: column; gap: 6px; justify-content: center; min-width: 0; }
  .requisitos-ins .titulo-req { font-size: 11px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em; margin-bottom: 2px; }
  .req-ins { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--fg); padding: 7px 9px; border-radius: 9px;
             border: 1px solid var(--border); background: rgba(var(--tinta),.02); }
  .req-ins .bola { width: 20px; height: 20px; border-radius: 50%; display: grid; place-items: center; flex: none; font-size: 11px; font-weight: 800;
                   background: rgba(var(--tinta),.08); color: var(--fg-dim); }
  .req-ins.feito { color: var(--fg-dim); }
  .req-ins.feito .bola { background: rgba(78,201,176,.18); color: var(--ok); }
  .req-ins button { margin-left: auto; background: none; border: 1px solid rgba(45,184,207,.5); color: var(--teal); border-radius: 7px; padding: 3px 9px;
                    font-size: 11px; font-weight: 700; cursor: pointer; font-family: inherit; white-space: nowrap; }
  .req-ins button:hover { background: rgba(45,184,207,.1); }
  .progresso-ins { width: 100%; height: 5px; border-radius: 999px; background: rgba(var(--tinta),.08); overflow: hidden; margin-top: 8px; }
  .progresso-ins div { height: 100%; background: var(--gradiente-marca); border-radius: 999px; }
  @media (max-width: 560px) { .card-insignia.com-requisitos { grid-column: span 1; flex-direction: column; align-items: center; } .card-insignia.com-requisitos .lado-ins { width: auto; } }

  /* Feedback interno - painel com destaque visual diferente (borda
     tracejada âmbar) pra deixar bem claro que é algo restrito/privado,
     que a própria pessoa nunca vê */
  .painel-feedback { border: 1px dashed rgba(220,220,170,.4) !important; background: rgba(220,220,170,.03) !important; }
  .aviso-feedback { font-size: 10.5px; color: var(--run); margin-bottom: 14px; display: flex; align-items: center; gap: 6px; }
  .item-feedback { background: rgba(var(--tinta),.02); border: 1px solid var(--border); border-radius: 8px;
      padding: 12px 14px; margin-bottom: 10px; }
  .item-feedback:last-child { margin-bottom: 0; }
  .cabecalho-item-feedback { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
  .autor-feedback { font-size: 12px; font-weight: 700; color: var(--fg); }
  .data-feedback { font-size: 10.5px; color: var(--fg-dim); }
  .texto-feedback { font-size: 12.5px; color: var(--fg); line-height: 1.5; white-space: pre-wrap; }
  .form-add-feedback { margin-top: 14px; padding-top: 14px; border-top: 1px dashed var(--border); }
  .form-add-feedback textarea { width: 100%; min-height: 70px; padding: 9px 10px; border-radius: 7px;
      border: 1px solid var(--border); background: rgba(var(--poco),.28); color: var(--fg); font-size: 12.5px;
      font-family: inherit; resize: vertical; }
  .form-add-feedback textarea:focus { outline: none; border-color: var(--teal); }
  .form-add-feedback input[type="text"] { width: 100%; padding: 9px 10px; border-radius: 7px;
      border: 1px solid var(--border); background: rgba(var(--poco),.28); color: var(--fg); font-size: 12.5px;
      font-family: inherit; }
  .badge-tipo-feedback { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .03em;
      padding: 2px 7px; border-radius: 5px; margin-right: 6px; }
  .badge-tipo-feedback.tipo-feedback { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-tipo-feedback.tipo-alinhamento { background: rgba(176,203,28,.15); color: var(--lime); }
  .seletor-tipo-feedback { display: flex; gap: 14px; margin: 4px 0 12px 0; }
  .opcao-tipo-feedback { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--fg-dim);
      text-transform: none; letter-spacing: normal; cursor: pointer; }
  .opcao-tipo-feedback input { margin: 0; }
  .link-canva-feedback { display: inline-block; margin-top: 8px; font-size: 11.5px; color: var(--teal);
      text-decoration: none; }
  .link-canva-feedback:hover { text-decoration: underline; }
  .acoes-item-feedback { display: flex; gap: 14px; margin-top: 6px; }
  .btn-remover-feedback { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 11px;
      margin-top: 0; padding: 0; opacity: .6; transition: opacity .15s, color .15s; }
  .btn-remover-feedback:hover { opacity: 1; color: var(--erro); }
  .btn-remover-feedback:first-child:hover { color: var(--teal); }
  .editado-feedback { font-style: italic; opacity: .7; }
  .nota-feedback { color: var(--run); font-size: 12px; margin-left: 6px; letter-spacing: 1px; }
  .rotulo-nota-feedback { display: block; font-size: 10px; color: var(--fg-dim); text-transform: uppercase;
      letter-spacing: .04em; margin-bottom: 6px; }
  .seletor-estrelas { display: flex; gap: 4px; margin-bottom: 12px; }
  .estrela-selecionavel { font-size: 20px; color: var(--fg-dim); cursor: pointer; transition: color .1s, transform .1s; user-select: none; }
  .estrela-selecionavel:hover { transform: scale(1.15); }
  .estrela-selecionavel.preenchida { color: var(--run); }

  .grade-metricas-perfil { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 16px; }
  .metrica-perfil { text-align: center; }
  .metrica-perfil .valor-metrica { font-size: 24px; font-weight: 800; color: var(--teal); }
  .metrica-perfil .rotulo-metrica { font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase;
                                      letter-spacing: .04em; margin-top: 4px; }
  .obs-metricas-perfil { font-size: 10.5px; color: var(--fg-dim); text-align: center; margin-top: 14px;
                          font-style: italic; opacity: .8; }

  .barra-progresso-perfil { height: 8px; border-radius: 5px; background: rgba(var(--tinta),.06); margin-top: 14px;
                              overflow: hidden; }
  .barra-progresso-perfil .preenchimento { height: 100%; background: var(--gradiente-marca); border-radius: 5px;
                                             transition: width .4s ease; }
  .comparacao-mes-anterior-perfil { margin-top: 16px; padding-top: 16px; border-top: 1px dashed var(--border); }
  .titulo-comparacao-perfil { font-size: 11.5px; color: var(--fg-dim); text-transform: uppercase;
                                letter-spacing: .05em; margin-bottom: 12px; font-weight: 700; }

  .linha-periodo-perfil { display: flex; justify-content: space-between; align-items: center; gap: 10px;
                            background: rgba(var(--tinta),.02); border: 1px solid var(--border); border-radius: 8px;
                            padding: 10px 14px; margin-bottom: 8px; font-size: 12.5px; }
  .linha-periodo-perfil:last-child { margin-bottom: 0; }
  .badge-tipo-perfil { font-size: 9.5px; font-weight: 700; text-transform: uppercase; padding: 2px 7px;
                        border-radius: 5px; background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-tipo-perfil.day-off { background: rgba(var(--tinta),.06); color: var(--fg-dim);
                                 border: 1px dashed var(--border-forte); }
  .vazio-perfil { color: var(--fg-dim); font-size: 12.5px; }

  .aviso-privado-perfil { background: rgba(var(--tinta),.03); border: 1px solid var(--border); border-radius: 12px;
                            padding: 18px 20px; font-size: 12.5px; color: var(--fg-dim); text-align: center; }
  .erro-perfil { color: var(--erro); font-size: 12.5px; min-height: 16px; margin-bottom: 10px; }
  input[type="file"] { display: none; }

  /* Histórico de carreira - timeline estilo LinkedIn */
  .timeline-carreira { position: relative; padding-left: 28px; }
  .item-timeline-carreira { position: relative; padding-bottom: 22px; }
  .item-timeline-carreira:last-child { padding-bottom: 0; }
  .item-timeline-carreira::before {
    /* linha vertical conectando os pontos */
    content: ''; position: absolute; left: -20px; top: 20px; bottom: -2px; width: 2px;
    background: linear-gradient(to bottom, var(--border-forte), var(--border));
  }
  .item-timeline-carreira:last-child::before { display: none; }
  .ponto-timeline {
    position: absolute; left: -26px; top: 2px; width: 14px; height: 14px; border-radius: 50%;
    background: var(--bg); border: 2.5px solid var(--fg-dim); z-index: 1;
  }
  .ponto-timeline.area-suporte { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.15); }
  .ponto-timeline.area-monitoramento { border-color: var(--lime); box-shadow: 0 0 0 3px rgba(176,203,28,.15); }
  .ponto-timeline.atual {
    border-color: var(--teal); background: var(--gradiente-marca);
    box-shadow: 0 0 0 4px rgba(45,184,207,.22), 0 0 14px rgba(45,184,207,.5);
  }
  .cargo-timeline { font-size: 14.5px; font-weight: 700; color: var(--fg); display: flex; align-items: center;
                      gap: 8px; flex-wrap: wrap; }
  .badge-atual-timeline { font-size: 9px; font-weight: 800; text-transform: uppercase; letter-spacing: .04em;
                             padding: 2px 8px; border-radius: 20px; background: var(--gradiente-marca); color: #08090c; }
  .badge-area-timeline { font-size: 9.5px; font-weight: 700; text-transform: uppercase; padding: 2px 8px;
                           border-radius: 5px; margin-left: 2px; }
  .badge-area-timeline.suporte { background: rgba(45,184,207,.15); color: var(--teal); }
  .badge-area-timeline.monitoramento { background: rgba(176,203,28,.15); color: var(--lime); }
  .periodo-timeline { font-size: 11.5px; color: var(--fg-dim); margin-top: 3px; }
  .duracao-timeline { color: var(--fg-dim); opacity: .75; }
  .btn-remover-timeline { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 11px;
                             margin-left: 8px; opacity: .5; transition: opacity .15s, color .15s; }
  .btn-remover-timeline:hover { opacity: 1; color: var(--erro); }
  /* editar um cargo já lançado (3.1.1.0): o lápis carrega o item no formulário de baixo */
  .btn-editar-timeline { background: none; border: none; color: var(--fg-dim); cursor: pointer; font-size: 12px;
                         margin-left: 8px; opacity: .5; transition: opacity .15s, color .15s; padding: 0; }
  .btn-editar-timeline:hover { opacity: 1; color: var(--teal); }
  .item-timeline-carreira.em-edicao .cargo-timeline { color: var(--teal); }
  .form-add-timeline .titulo-form-timeline { font-size: 11px; font-weight: 800; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em; }
  .form-add-timeline.editando { border-top-color: rgba(45,184,207,.55); }
  .form-add-timeline.editando .titulo-form-timeline { color: var(--teal); }
  .acoes-form-timeline { display: flex; gap: 8px; flex-wrap: wrap; }
  .form-add-timeline { margin-top: 18px; padding-top: 16px; border-top: 1px dashed var(--border);
                          display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  .form-add-timeline input, .form-add-timeline select { padding: 8px 10px; border-radius: 7px;
      border: 1px solid var(--border); background: rgba(var(--poco),.28); color: var(--fg); font-size: 12.5px;
      font-family: inherit; }
  .form-add-timeline label { font-size: 10px; color: var(--fg-dim); text-transform: uppercase;
      letter-spacing: .04em; display: block; margin-bottom: 4px; }
  .form-add-timeline .campo-largura-total { grid-column: 1 / -1; }
  .form-add-timeline .campo-checkbox-atual { display: flex; align-items: center; gap: 6px; font-size: 12px;
      color: var(--fg-dim); grid-column: 1 / -1; }
</style>
__LOJA_WALLPAPERS__
</head>
<body>
__NAVBAR__
  <div class="conteudo">
    <div class="erro-perfil" id="perfil-erro"></div>
    <div id="perfil-corpo"><div class="vazio-perfil">Carregando...</div></div>
  </div>

  <input type="file" id="perfil-input-foto" accept="image/jpeg,image/png,image/webp,image/gif">
  __INSIGNIAS__

  __FOOTER__

<script>
function escaparHtml(txt) {
  return String(txt ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

const USUARIO_PERFIL = "__USUARIO_PERFIL__";

function iniciaisPerfil(nome) {
  const partes = nome.trim().split(/\\s+/).filter(Boolean);
  if (partes.length === 0) return '?';
  if (partes.length === 1) return partes[0].slice(0, 2).toUpperCase();
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase();
}

function htmlFotoOuIniciais(dados) {
  // clicar abre a foto grande (3.0.4.0)
  if (dados.tem_foto) {
    return `<img class="foto-perfil clicavel-foto" onclick="ampliarFotoPerfil()" title="Ver foto" src="/foto-usuario/${encodeURIComponent(dados.usuario)}?t=${Date.now()}" alt="${escaparHtml(dados.nome)}">`;
  }
  return `<div class="foto-perfil clicavel-foto" onclick="ampliarFotoPerfil()">${iniciaisPerfil(dados.nome)}</div>`;
}

function ampliarFotoPerfil() {
  const d = dadosPerfilAtual;
  if (!d || typeof abrirFotoPessoa !== 'function') return;
  abrirFotoPessoa({ login: d.usuario, nome: d.nome, tem_foto: d.tem_foto, cargo: d.cargo, equipe: d.atribuicao,
                    destaque: (d.insignias || []).find(i => i.destaque) || null }, true);
}

const MESES_ABREV_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];

function formatarMesAnoTimeline(aaaaMm) {
  const [ano, mes] = aaaaMm.split('-').map(Number);
  return `${MESES_ABREV_PT[mes - 1]}/${ano}`;
}

function formatarDuracaoTimeline(inicio, fim) {
  const [anoIni, mesIni] = inicio.split('-').map(Number);
  const hoje = new Date();
  const [anoFim, mesFim] = fim ? fim.split('-').map(Number) : [hoje.getFullYear(), hoje.getMonth() + 1];
  let totalMeses = (anoFim - anoIni) * 12 + (mesFim - mesIni) + 1;
  if (totalMeses < 1) totalMeses = 1;
  const anos = Math.floor(totalMeses / 12);
  const meses = totalMeses % 12;
  const partes = [];
  if (anos > 0) partes.push(`${anos} ano${anos > 1 ? 's' : ''}`);
  if (meses > 0 || anos === 0) partes.push(`${meses} ${meses === 1 ? 'mês' : 'meses'}`);
  return partes.join(' e ');
}

const TEXTO_DESATIVADO_PERFIL = 'Esse usuário foi desativado no PDA. Isso geralmente indica que a pessoa não faz mais parte da Empresa ou da equipe de sustentação.';

function rotuloAreaTimeline(area) {
  if (area === 'suporte') return 'Suporte';
  if (area === 'monitoramento') return 'Monitoramento';
  return '';
}

function montarHtmlTimelineCarreira(historico, sessaoAdmin) {
  const itens = historico.length === 0
    ? '<div class="vazio-perfil">Nenhum histórico de carreira registrado ainda.</div>'
    : `<div class="timeline-carreira">${historico.map((h, i) => {
        const ehAtual = !h.fim;
        const classeArea = h.area ? `area-${h.area}` : '';
        const rotuloArea = rotuloAreaTimeline(h.area);
        const periodoTexto = ehAtual
          ? `${formatarMesAnoTimeline(h.inicio)} - o momento`
          : `${formatarMesAnoTimeline(h.inicio)} - ${formatarMesAnoTimeline(h.fim)}`;
        const botaoRemover = sessaoAdmin
          ? `<button class="btn-editar-timeline" onclick="editarHistoricoCarreira(${h.id})" title="Editar">✎</button>` +
            `<button class="btn-remover-timeline" onclick="removerHistoricoCarreira(${h.id})" title="Remover">✕</button>`
          : '';
        return `
          <div class="item-timeline-carreira" data-id-historico="${h.id}">
            <div class="ponto-timeline ${classeArea} ${ehAtual ? 'atual' : ''}"></div>
            <div class="cargo-timeline">
              ${escaparHtml(h.cargo)}
              ${ehAtual ? '<span class="badge-atual-timeline">Atual</span>' : ''}
              ${rotuloArea ? `<span class="badge-area-timeline ${h.area}">${rotuloArea}</span>` : ''}
              ${botaoRemover}
            </div>
            <div class="periodo-timeline">${periodoTexto} <span class="duracao-timeline">· ${formatarDuracaoTimeline(h.inicio, h.fim)}</span></div>
          </div>
        `;
      }).join('')}</div>`;

  if (!sessaoAdmin) return itens;

  historicoCarreiraAtual = historico;
  return itens + `
    <div class="form-add-timeline" id="form-historico-carreira">
      <div class="campo-largura-total titulo-form-timeline" id="th-titulo">Adicionar cargo</div>
      <div class="campo-largura-total">
        <label>Cargo</label>
        <input type="text" id="th-cargo" maxlength="60" placeholder="Ex.: Analista Pleno">
      </div>
      <div>
        <label>Área</label>
        <select id="th-area">
          <option value="">Sem área</option>
          <option value="suporte">Suporte</option>
          <option value="monitoramento">Monitoramento</option>
        </select>
      </div>
      <div>
        <label>Início</label>
        <input type="month" id="th-inicio">
      </div>
      <div class="campo-checkbox-atual">
        <input type="checkbox" id="th-atual" checked onchange="document.getElementById('th-fim').disabled = this.checked; document.getElementById('th-fim').value = '';">
        <label for="th-atual" style="text-transform:none; font-size:12px; margin:0">Esse é o cargo atual (sem data de fim)</label>
      </div>
      <div class="campo-largura-total">
        <label>Fim</label>
        <input type="month" id="th-fim" disabled>
      </div>
      <div class="campo-largura-total erro-perfil" id="th-erro"></div>
      <div class="campo-largura-total acoes-form-timeline">
        <button class="btn-mini" id="th-salvar" onclick="adicionarHistoricoCarreira()">+ Adicionar ao histórico</button>
        <button class="btn-mini" id="th-cancelar" onclick="cancelarEdicaoHistorico()" hidden>Cancelar</button>
      </div>
    </div>
  `;
}

function renderizarEstrelas(nota) {
  if (!nota) return '';
  let estrelas = '';
  for (let i = 1; i <= 5; i++) estrelas += i <= nota ? '★' : '☆';
  return `<span class="nota-feedback">${estrelas}</span>`;
}


// editar um cargo já lançado (3.1.1.0): o mesmo formulário de adicionar, com o id do item em edição
let historicoCarreiraAtual = [];
let idHistoricoEmEdicao = null;

function editarHistoricoCarreira(id) {
  const h = historicoCarreiraAtual.find(x => x.id === id);
  if (!h) return;
  idHistoricoEmEdicao = id;
  document.getElementById('th-cargo').value = h.cargo || '';
  document.getElementById('th-area').value = h.area || '';
  document.getElementById('th-inicio').value = h.inicio || '';
  const atual = !h.fim;
  document.getElementById('th-atual').checked = atual;
  const fimEl = document.getElementById('th-fim');
  fimEl.disabled = atual;
  fimEl.value = h.fim || '';
  document.getElementById('th-erro').innerText = '';
  document.getElementById('th-titulo').innerText = 'Editando · ' + (h.cargo || '');
  document.getElementById('th-salvar').innerText = 'Salvar alteração';
  document.getElementById('th-cancelar').hidden = false;
  const form = document.getElementById('form-historico-carreira');
  form.classList.add('editando');
  document.querySelectorAll('.item-timeline-carreira').forEach(el =>
    el.classList.toggle('em-edicao', el.dataset.idHistorico === String(id)));
  form.scrollIntoView({behavior: 'smooth', block: 'center'});
  document.getElementById('th-cargo').focus();
}

function cancelarEdicaoHistorico() {
  idHistoricoEmEdicao = null;
  ['th-cargo', 'th-inicio', 'th-fim'].forEach(i => { document.getElementById(i).value = ''; });
  document.getElementById('th-area').value = '';
  document.getElementById('th-atual').checked = true;
  document.getElementById('th-fim').disabled = true;
  document.getElementById('th-erro').innerText = '';
  document.getElementById('th-titulo').innerText = 'Adicionar cargo';
  document.getElementById('th-salvar').innerText = '+ Adicionar ao histórico';
  document.getElementById('th-cancelar').hidden = true;
  document.getElementById('form-historico-carreira').classList.remove('editando');
  document.querySelectorAll('.item-timeline-carreira.em-edicao').forEach(el => el.classList.remove('em-edicao'));
}

async function adicionarHistoricoCarreira() {
  const cargo = document.getElementById('th-cargo').value.trim();
  const area = document.getElementById('th-area').value;
  const inicio = document.getElementById('th-inicio').value;
  const ehAtual = document.getElementById('th-atual').checked;
  const fim = ehAtual ? '' : document.getElementById('th-fim').value;
  const erroEl = document.getElementById('th-erro');
  erroEl.innerText = '';

  if (!cargo) { erroEl.innerText = 'Informe o cargo.'; return; }
  if (!inicio) { erroEl.innerText = 'Informe o mês/ano de início.'; return; }
  if (!ehAtual && !fim) { erroEl.innerText = 'Informe o mês/ano de fim, ou marque "cargo atual".'; return; }

  try {
    const editando = idHistoricoEmEdicao !== null;
    const resp = await fetch(editando ? '/api/historico-carreira/editar' : '/api/historico-carreira/criar', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: (editando ? 'id=' + encodeURIComponent(idHistoricoEmEdicao) + '&' : '') +
            'usuario=' + encodeURIComponent(USUARIO_PERFIL) + '&cargo=' + encodeURIComponent(cargo) +
            '&area=' + encodeURIComponent(area) + '&inicio=' + encodeURIComponent(inicio) +
            '&fim=' + encodeURIComponent(fim),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || (editando ? 'Não foi possível salvar.' : 'Não foi possível adicionar.'); return; }
    idHistoricoEmEdicao = null;
    await carregarPerfil();
    // continua no modo de edição depois de recarregar, pra ajustar outro item se precisar
    const painel = document.getElementById('painel-historico-carreira');
    if (painel && !painel.classList.contains('modo-edicao')) alternarEdicaoHistorico();
  } catch (e) {
    erroEl.innerText = 'Erro: ' + e;
  }
}

async function removerHistoricoCarreira(id) {
  if (!confirm('Remover essa entrada do histórico de carreira?')) return;
  try {
    const resp = await fetch('/api/historico-carreira/excluir', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'id=' + encodeURIComponent(id),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) { alert(dados.erro || 'Não foi possível remover.'); return; }
    carregarPerfil();
  } catch (e) {
    alert('Erro: ' + e);
  }
}

function alternarEdicaoHistorico() {
  const painel = document.getElementById('painel-historico-carreira');
  const botao = painel.querySelector('.btn-editar-historico');
  painel.classList.toggle('modo-edicao');
  if (botao) botao.classList.toggle('ativo');
}

// ---------------- insígnias (2.35.5.0) ----------------
let dadosPerfilAtual = null;
const ICONE_CADEADO_PERFIL = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';

function dataBrPerfil(iso) {
  const p = String(iso || '').split('-');
  return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : '';
}

function tempoDesdePerfil(iso) {
  const inicio = new Date(iso + 'T00:00:00');
  const hoje = new Date();
  let meses = (hoje.getFullYear() - inicio.getFullYear()) * 12 + (hoje.getMonth() - inicio.getMonth());
  if (hoje.getDate() < inicio.getDate()) meses--;
  if (meses < 1) return 'menos de 1 mês';
  const anos = Math.floor(meses / 12), resto = meses % 12;
  const partes = [];
  if (anos) partes.push(anos + (anos === 1 ? ' ano' : ' anos'));
  if (resto) partes.push(resto + (resto === 1 ? ' mês' : ' meses'));
  return partes.join(' e ');
}

function htmlDesdePerfil(dados) {
  if (!dados.pode_editar_perfil) return '';
  if (!dados.data_inicio) {
    return `<button class="btn-lapis-perfil destaque" onclick="editarDesdePerfil()">+ Informar quando entrou na empresa</button>`;
  }
  return `Na empresa desde <b>${dataBrPerfil(dados.data_inicio)}</b> · ${tempoDesdePerfil(dados.data_inicio)}
    <button class="btn-lapis-perfil" onclick="editarDesdePerfil()" title="Alterar a data de início">✏️ alterar</button>
    ${dados.aniversario ? `<span>· 🎂 aniversário em <b>${aniversarioPerfil(dados.aniversario)}</b></span>` : ''}`;
}

function editarDesdePerfil() {
  const alvo = document.getElementById('desde-perfil');
  if (!alvo || !dadosPerfilAtual) return;
  const hoje = new Date();
  const max = hoje.getFullYear() + '-' + String(hoje.getMonth() + 1).padStart(2, '0') + '-' + String(hoje.getDate()).padStart(2, '0');
  alvo.innerHTML = `<span class="form-desde-perfil">Entrei na empresa em
      <input type="date" id="desde-input" max="${max}" min="1980-01-01" value="${escaparHtml(dadosPerfilAtual.data_inicio || '')}">
      <button class="btn-lapis-perfil destaque" onclick="salvarDesdePerfil()">Salvar</button>
      <button class="btn-lapis-perfil" onclick="document.getElementById('desde-perfil').innerHTML = htmlDesdePerfil(dadosPerfilAtual)">Cancelar</button>
      <span class="erro-perfil" id="desde-erro" style="margin:0"></span></span>`;
  document.getElementById('desde-input').focus();
}

async function salvarDesdePerfil() {
  const valor = document.getElementById('desde-input').value;
  const erroEl = document.getElementById('desde-erro');
  if (!valor) { erroEl.innerText = 'Escolha a data.'; return; }
  try {
    const resp = await fetch('/api/usuarios/alterar-data-inicio', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(USUARIO_PERFIL) + '&data_inicio=' + encodeURIComponent(valor),
    });
    const dados = await resp.json();
    if (!dados.ok) { erroEl.innerText = dados.erro || 'Não foi possível salvar.'; return; }
    carregarPerfil();
  } catch (e) {
    erroEl.innerText = 'Erro: ' + e;
  }
}

const MESES_PERFIL = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
function aniversarioPerfil(mmdd) {
  const [m, d] = String(mmdd || '').split('-').map(Number);
  return m && d ? d + ' de ' + MESES_PERFIL[m - 1] : '';
}

function htmlDestaqueFoto(dados) {
  const destaque = (dados.insignias || []).find(i => i.destaque);
  if (!destaque) return '';
  return `<button class="destaque-foto-ins" title="${escaparHtml(destaque.nome)} · em destaque" onclick="irParaInsignias()">${svgInsignia(destaque, 46, false)}</button>`;
}

async function destacarNoPerfil(id) {
  try {
    const dados = await (await fetch('/api/insignias/destaque', { method: 'POST', body: new URLSearchParams({ id }) })).json();
    if (!dados.ok) { document.getElementById('perfil-erro').innerText = dados.erro || 'Não foi possível destacar.'; return; }
    carregarPerfil();
  } catch (e) {
    document.getElementById('perfil-erro').innerText = 'Erro: ' + e;
  }
}

function htmlMinisInsignias(dados) {
  const ganhas = (dados.insignias || []).filter(i => i.desbloqueada);
  if (!ganhas.length) return '';
  return '<div class="minis-insignias">' + ganhas.map(i =>
    `<button title="${escaparHtml(i.nome)}" onclick="irParaInsignias()">${svgInsignia(i, 34, false)}</button>`).join('') + '</div>';
}

function irParaInsignias() {
  const painel = document.getElementById('insignias');
  if (painel) painel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function htmlRequisitosBeta(ins) {
  const feitos = ins.requisitos.filter(r => r.feito).length;
  const podeParticipar = dadosPerfilAtual && dadosPerfilAtual.proprio_perfil;
  const prazo = ins.fim_campanha ? ' · até ' + ins.fim_campanha.split('-').reverse().join('/') : '';
  return `<div class="requisitos-ins"><div class="titulo-req">Pra desbloquear · ${feitos} de ${ins.requisitos.length}${prazo}</div>` +
    ins.requisitos.map(r => `<div class="req-ins ${r.feito ? 'feito' : ''}"><span class="bola">${r.feito ? '&#10003;' : '&#8226;'}</span>
      <span>${escaparHtml(r.nome)}</span></div>`).join('') +
    `<div class="progresso-ins"><div style="width:${Math.round(feitos / ins.requisitos.length * 100)}%"></div></div>` +
    (podeParticipar ? `<button class="btn-participar-ins" onclick="abrirParticipacaoDoPerfilIns()">&#9733; Participar da campanha</button>` : '') + `</div>`;
}

function htmlCardInsignia(ins) {
  const tipoClasse = ins.tipo === 'fundador' || ins.tipo === 'contribuidor' ? ins.tipo : '';
  if (ins.desbloqueada) {
    let quando = ins.quando ? 'Conquistada em ' + dataBrPerfil(ins.quando) : 'Exclusiva';
    if (ins.id === 'beta_user' && ins.quando) quando = 'Desbloqueada em ' + dataBrPerfil(ins.quando);
    let desc = escaparHtml(ins.descricao);
    if (ins.tipo === 'rank' && ins.proximo) {  // Rank Master por nível (3.1.0.0)
      desc += ` · próxima com ${ins.proximo.produtos} produtos (${ins.proximo.faltam === 1 ? 'falta 1' : 'faltam ' + ins.proximo.faltam})`;
    }
    if (ins.tipo === 'palmas' && ins.proximo) {  // palminhas por nível (3.1.3.0)
      desc += ` · próxima com ${ins.proximo.palmas} (${ins.proximo.faltam === 1 ? 'falta 1' : 'faltam ' + ins.proximo.faltam})`;
    }
    if (ins.tipo === 'tempo' && ins.proximo) {
      desc += ins.proximo.nivel_nome === ins.nivel_nome
        ? (ins.proximo.meses ? ` · ${ins.proximo.meses} meses em ${dataBrPerfil(ins.proximo.data)}` : ` · ${ins.proximo.anos} anos em ${dataBrPerfil(ins.proximo.data)}`)
        : ` · ${escaparHtml(ins.proximo.nivel_nome)} em ${dataBrPerfil(ins.proximo.data)}`;
    }
    const podeDestacar = dadosPerfilAtual && dadosPerfilAtual.proprio_perfil;
    const botaoDestaque = !podeDestacar ? ''
      : (ins.destaque ? `<button class="btn-destacar-ins" onclick="destacarNoPerfil('')" title="Tirar do destaque">tirar do destaque</button>`
                      : `<button class="btn-destacar-ins" onclick="destacarNoPerfil('${escaparHtml(ins.id)}')">&#9733; Destacar junto da foto</button>`);
    return `<div class="card-insignia ganha ${tipoClasse} ${ins.destaque ? 'em-destaque' : ''}">${ins.destaque ? '<span class="selo-destaque-ins">em destaque</span>' : ''}${svgInsignia(ins, 84, true)}
      <div class="nome-ins">${escaparHtml(ins.nome)}</div><div class="desc-ins">${desc}</div><span class="quando-ins">${escaparHtml(quando)}</span>${botaoDestaque}</div>`;
  }
  if (ins.tipo === 'rank') {  // Rank Master ainda não alcançada (3.0.9.0: liberada pelos produtos no Master do Ranks por Produtos)
    const faltam = ins.produtos - (ins.masters || 0);
    return `<div class="card-insignia trancada"><span class="cad-ins">${ICONE_CADEADO_PERFIL}</span>
      <div class="insignia-bloqueada">${svgInsignia(ins, 84, false)}</div>
      <div class="nome-ins">${escaparHtml(ins.nome)}</div><div class="desc-ins">${escaparHtml(ins.descricao)} · ${faltam === 1 ? 'falta 1' : 'faltam ' + faltam}</div>
      <a class="quando-ins" href="/ranks-produtos" style="text-decoration:none">Ver rankings</a></div>`;
  }
  if (ins.tipo === 'palmas') {  // primeira meta de palminhas ainda não alcançada (3.1.3.0)
    const faltam = ins.palmas - (ins.recebidas || 0);
    return `<div class="card-insignia trancada"><span class="cad-ins">${ICONE_CADEADO_PERFIL}</span>
      <div class="insignia-bloqueada">${svgInsignia(ins, 84, false)}</div>
      <div class="nome-ins">${escaparHtml(ins.nome)}</div><div class="desc-ins">${escaparHtml(ins.descricao)} · ${faltam === 1 ? 'falta 1' : 'faltam ' + faltam}</div>
      <a class="quando-ins" href="/ranks-produtos#palmas" style="text-decoration:none">Ver leaderboard</a></div>`;
  }
  if (ins.id === 'bug_hunter') {
    return `<div class="card-insignia trancada"><span class="cad-ins">${ICONE_CADEADO_PERFIL}</span>
      <div class="insignia-bloqueada">${svgInsignia(ins, 84, false)}</div>
      <div class="nome-ins">Bug Hunter</div><div class="desc-ins">${escaparHtml(ins.descricao)}</div>
      <button class="btn-destacar-ins" onclick="abrirRequisitosBugHunterIns()">Como participar</button></div>`;
  }
  if (ins.id === 'beta_user' && ins.encerrada) {  // campanha terminou (3.1.2.0): não dá mais pra conquistar
    return `<div class="card-insignia trancada"><span class="cad-ins">${ICONE_CADEADO_PERFIL}</span>
      <div class="insignia-bloqueada">${svgInsignia(ins, 84, false)}</div>
      <div class="nome-ins">${escaparHtml(ins.nome)}</div><div class="desc-ins">${escaparHtml(ins.descricao)}</div></div>`;
  }
  if (ins.id === 'beta_user') {
    return `<div class="card-insignia trancada com-requisitos"><span class="cad-ins">${ICONE_CADEADO_PERFIL}</span>
      <div class="lado-ins"><div class="insignia-bloqueada">${svgInsignia(ins, 84, false)}</div><div class="nome-ins">${escaparHtml(ins.nome)}</div>
        <div class="desc-ins">Da fase beta do PDA</div></div>${htmlRequisitosBeta(ins)}</div>`;
  }
  // tempo de casa ainda sem 1 ano completo (ou sem data de início)
  let desc = 'Complete 1 ano de empresa';
  if (ins.sem_data_inicio) desc = 'Informe quando entrou na empresa';
  else if (ins.proximo) desc = `Em ${dataBrPerfil(ins.proximo.data)} (faltam ${ins.proximo.dias} dias)`;
  return `<div class="card-insignia trancada"><span class="cad-ins">${ICONE_CADEADO_PERFIL}</span>
    <div class="insignia-bloqueada">${svgInsignia(ins, 84, false)}</div>
    <div class="nome-ins">Tempo de casa</div><div class="desc-ins">${escaparHtml(desc)}</div><span class="quando-ins">Bloqueada</span></div>`;
}

// Conceder insígnias (3.0.5.0): só o Igor e a Debora veem; Bug Hunter e PDA Contributor
function htmlPainelConcessoes(dados) {
  if (!dados.pode_conceder || !(dados.concessoes || []).length) return '';
  const linhas = dados.concessoes.map(c => {
    const estado = c.fixa ? '<span class="estado-conc">Tem pela lista fixa</span>'
      : (c.tem ? `<span class="estado-conc ok">Concedida${c.quando ? ' em ' + dataBrPerfil(c.quando) : ''}</span>` : '<span class="estado-conc">Ainda não tem</span>');
    const botao = c.fixa ? ''
      : `<button class="btn-mini ${c.tem ? '' : 'primario-conc'}" onclick="concederInsigniaPerfil('${escaparHtml(c.id)}', ${!c.tem})">${c.tem ? 'Retirar' : 'Conceder'}</button>`;
    return `<div class="linha-conc">${svgInsignia({ tipo: c.id === 'bug_hunter' ? 'bug' : 'contribuidor' }, 40, false)}
      <div class="info-conc"><b>${escaparHtml(c.nome)}</b>${estado}</div>${botao}</div>`;
  }).join('');
  return `<div class="painel-perfil painel-concessoes">
    <h2>Conceder insígnias <span class="contagem-insignias">só Igor e Debora veem isto</span></h2>${linhas}
    <div class="erro-perfil" id="erro-concessao"></div></div>`;
}

async function concederInsigniaPerfil(id, dar) {
  const d = dadosPerfilAtual;
  const nome = (d.concessoes.find(c => c.id === id) || {}).nome || id;
  if (!confirm((dar ? 'Conceder a insígnia ' : 'Retirar a insígnia ') + nome + (dar ? ' pra ' : ' de ') + d.nome + '?')) return;
  try {
    const resp = await fetch('/api/insignias/conceder', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(d.usuario) + '&id=' + encodeURIComponent(id) + '&dar=' + (dar ? 'true' : 'false')});
    const r = await resp.json();
    if (!r.ok) throw new Error(r.erro || 'erro');
    carregarPerfil();
  } catch (e) {
    const el = document.getElementById('erro-concessao');
    if (el) el.textContent = e.message && e.message !== 'erro' ? e.message : 'Não foi possível salvar agora.';
  }
}

function htmlPainelInsignias(dados) {
  const lista = dados.insignias || [];
  const ganhas = lista.filter(i => i.desbloqueada).length;
  if (!lista.length) {
    return '<div class="painel-perfil" id="insignias"><h2>Insígnias</h2><div class="vazio-perfil">Nenhuma insígnia ainda.</div></div>';
  }
  return `<div class="painel-perfil" id="insignias">
    <h2 class="cabecalho-com-acao"><span>Insígnias</span><span class="contagem-insignias"><b>${ganhas}</b> ${ganhas === 1 ? 'desbloqueada' : 'desbloqueadas'}</span></h2>
    <div class="grade-insignias-perfil">${lista.map(htmlCardInsignia).join('')}</div>
  </div>`;
}

function abrirEdicaoHistoricoPerfil() {
  const painel = document.getElementById('painel-historico-carreira');
  if (!painel) return;
  if (!painel.classList.contains('modo-edicao')) alternarEdicaoHistorico();
  painel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  setTimeout(() => { const campo = document.getElementById('th-cargo'); if (campo) campo.focus(); }, 400);
}

function renderizarPerfil(dados) {
  dadosPerfilAtual = dados;
  const corpo = document.getElementById('perfil-corpo');

  if (!dados.pode_ver_completo) {
    // perfil público (3.0.4.0): o básico, insígnias e histórico na empresa, só leitura;
    // indicadores pessoais, férias e feedbacks ficam com a própria pessoa e a gestão
    const classeEquipe = dados.atribuicao === 'Monitoramento' ? 'atribuicao-monitoramento'
      : dados.atribuicao === 'Suporte e Monitoramento' ? 'atribuicao-ambas'
      : dados.atribuicao === 'Serviços' ? 'atribuicao-servicos' : 'atribuicao-suporte';
    const desde = dados.data_inicio
      ? `Na empresa desde <b>${dataBrPerfil(dados.data_inicio)}</b> · ${tempoDesdePerfil(dados.data_inicio)}`
        + (dados.aniversario ? ` <span>· 🎂 aniversário em <b>${aniversarioPerfil(dados.aniversario)}</b></span>` : '')
      : (dados.aniversario ? `🎂 Aniversário em <b>${aniversarioPerfil(dados.aniversario)}</b>` : '');
    corpo.innerHTML = `
      <div class="cabecalho-perfil">
        <div class="foto-perfil-wrap">${htmlFotoOuIniciais(dados)}${htmlDestaqueFoto(dados)}</div>
        <div class="info-cabecalho-perfil">
          <h1>${escaparHtml(dados.nome)}</h1>
          ${dados.cargo ? `<div class="cargo-perfil">${escaparHtml(dados.cargo)}</div>` : ''}
          ${dados.atribuicao || dados.ativo === false ? `<div class="badges-perfil">${dados.atribuicao ? `<span class="badge-perfil ${classeEquipe}">${escaparHtml(dados.atribuicao)}</span>` : ''}${dados.ativo === false ? '<span class="badge-perfil desativado">Usuário desativado no PDA</span>' : ''}</div>` : ''}
          ${desde ? `<div class="desde-perfil">${desde}</div>` : ''}
          ${dados.ativo === false ? `<div class="aviso-desativado">${TEXTO_DESATIVADO_PERFIL}</div>` : ''}
          ${htmlMinisInsignias(dados)}
        </div>
      </div>
      ${htmlPainelInsignias(dados)}
      <div class="painel-perfil">
        <h2>Histórico na empresa</h2>
        ${montarHtmlTimelineCarreira(dados.historico_carreira || [], false)}
      </div>
      <div class="aviso-privado-perfil">Você está vendo o perfil público. Indicadores pessoais, férias e feedbacks ficam só com a própria pessoa e a gestão.</div>
    `;
    return;
  }

  const classeAtribuicao = dados.atribuicao === 'Monitoramento' ? 'atribuicao-monitoramento'
    : dados.atribuicao === 'Suporte e Monitoramento' ? 'atribuicao-ambas'
    : dados.atribuicao === 'Serviços' ? 'atribuicao-servicos' : 'atribuicao-suporte';
  const percentual = dados.percentual_horas_mes;
  const larguraBarra = percentual === null ? 0 : Math.min(percentual, 100);

  let blocoHoras;
  if (!dados.vinculado_movidesk) {
    blocoHoras = '<div class="vazio-perfil">Ainda não vinculado a um usuário do Movidesk (fale com um admin em "Editar usuário" → Horas/Vínculo) - sem isso não dá pra calcular horas trabalhadas nem tickets.</div>';
  } else if (dados.erro_horas) {
    blocoHoras = `<div class="vazio-perfil">Não foi possível calcular agora: ${escaparHtml(dados.erro_horas)}</div>`;
  } else {
    blocoHoras = `
      <div class="grade-metricas-perfil">
        <div class="metrica-perfil">
          <div class="valor-metrica">${percentual === null ? '–' : percentual + '%'}</div>
          <div class="rotulo-metrica">Do mês concluído</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.horas_trabalhadas_mes || '–'}</div>
          <div class="rotulo-metrica">Horas trabalhadas</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.meta_horas_mes || '–'}</div>
          <div class="rotulo-metrica">Meta do mês</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.tickets_mes ?? '–'}</div>
          <div class="rotulo-metrica">Tickets com ação</div>
        </div>
      </div>
      <div class="barra-progresso-perfil"><div class="preenchimento" style="width:${larguraBarra}%"></div></div>
      <button class="btn-mini" id="btn-comparar-mes-anterior" onclick="compararMesAnterior()" style="margin-top:14px">Comparar com mês anterior</button>
      <button class="btn-mini" id="btn-exportar-horas-perfil" onclick="exportarHorasPerfil()" style="margin-top:14px">Exportar Excel (mês atual)</button>
      <div id="comparacao-mes-anterior"></div>
    `;
  }

  // Indicadores gerais - DIFERENTE do bloco acima (que é sempre só do mês
  // atual), esse aqui olha o histórico INTEIRO da pessoa, sem filtro de
  // período (pedido explícito do Igor).
  let blocoIndicadoresGerais;
  if (!dados.vinculado_movidesk) {
    blocoIndicadoresGerais = '<div class="vazio-perfil">Ainda não vinculado a um usuário do Movidesk.</div>';
  } else if (dados.erro_indicadores_gerais) {
    blocoIndicadoresGerais = `<div class="vazio-perfil">Não foi possível calcular agora: ${escaparHtml(dados.erro_indicadores_gerais)}</div>`;
  } else {
    blocoIndicadoresGerais = `
      <div class="grade-metricas-perfil">
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.tickets_acao_total ?? '–'}</div>
          <div class="rotulo-metrica">Tickets com ação (desde sempre)</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.total_horas_trabalhadas || '–'}</div>
          <div class="rotulo-metrica">Horas totais trabalhadas</div>
        </div>
        <div class="metrica-perfil">
          <div class="valor-metrica">${dados.primeira_atividade || '–'}</div>
          <div class="rotulo-metrica">${dados.primeira_atividade_e_data_inicio_manual ? 'Data Início' : 'Primeira atividade registrada'}</div>
        </div>
      </div>
      <div class="obs-metricas-perfil">Valores antigos podem variar e estar incompletos.</div>
    `;
  }

  const listaPeriodos = dados.periodos_futuros.length === 0
    ? '<div class="vazio-perfil">Nenhuma férias ou day off agendado.</div>'
    : dados.periodos_futuros.map(p => {
        const ehDayOff = p.tipo === 'day_off';
        const rotulo = { day_off: 'Day Off', atestado: 'Atestado', afastamento: 'Afastamento' }[p.tipo] || 'Férias';
        return `
          <div class="linha-periodo-perfil">
            <span>${p.inicio} até ${p.fim}</span>
            <span class="badge-tipo-perfil ${ehDayOff ? 'day-off' : ''}">${rotulo}</span>
          </div>
        `;
      }).join('');

  const blocoHistoricoCarreira = montarHtmlTimelineCarreira(dados.historico_carreira || [], !!dados.pode_editar_perfil);

  corpo.innerHTML = `
    <div class="cabecalho-perfil">
      <div class="foto-perfil-wrap">
        ${htmlFotoOuIniciais(dados)}
        ${htmlDestaqueFoto(dados)}
        <div class="botao-trocar-foto" onclick="document.getElementById('perfil-input-foto').click()" title="Trocar foto · JPG, PNG, WEBP ou GIF animado">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/>
            <circle cx="12" cy="13" r="4"/>
          </svg>
        </div>
      </div>
      <div class="info-cabecalho-perfil">
        <h1>${escaparHtml(dados.nome)}</h1>
        ${dados.cargo ? `<div class="cargo-perfil">${escaparHtml(dados.cargo)}</div>` : ''}
        <div class="badges-perfil">
          <span class="badge-perfil ${classeAtribuicao}">${escaparHtml(dados.atribuicao)}</span>
          <span class="badge-perfil">${dados.admin ? 'Administrador' : 'Visualização'}</span>
          ${!dados.ativo ? '<span class="badge-perfil desativado">Usuário desativado no PDA</span>' : ''}
        </div>
        <div class="desde-perfil" id="desde-perfil">${htmlDesdePerfil(dados)}</div>
        ${!dados.ativo ? `<div class="aviso-desativado">${TEXTO_DESATIVADO_PERFIL}</div>` : ''}
        ${htmlMinisInsignias(dados)}
      </div>
    </div>

    ${htmlPainelInsignias(dados)}
    ${htmlPainelConcessoes(dados)}

    <div class="painel-perfil">
      <h2>Horas trabalhadas neste mês</h2>
      ${blocoHoras}
    </div>

    <div class="painel-perfil">
      <h2>Indicadores gerais</h2>
      ${blocoIndicadoresGerais}
    </div>

    <div class="painel-perfil">
      <h2>Férias &amp; Day Off agendados</h2>
      ${listaPeriodos}
    </div>

    <div class="painel-perfil" id="painel-historico-carreira">
      <h2 class="cabecalho-com-acao">
        <span>Histórico na Empresa</span>
        ${dados.pode_editar_perfil ? '<button class="btn-editar-historico" onclick="alternarEdicaoHistorico()" title="Editar histórico">✏️</button>' : ''}
      </h2>
      ${blocoHistoricoCarreira}
    </div>

    ${dados.pode_ver_feedback ? `
    <div class="painel-perfil painel-feedback">
      <h2>Feedback (privado)</h2>
      <div class="aviso-feedback">🔒 Visível só pra quem tem a permissão de Feedbacks e Alinhamentos - a própria pessoa nunca vê isso.</div>
      <div id="perfil-lista-feedbacks"><div class="data-feedback">Carregando...</div></div>
      <a class="link-canva-feedback" href="/feedbacks?usuario=${encodeURIComponent(dados.usuario)}">Abrir na tela de Feedbacks (editar, remover, novo) →</a>
    </div>
    ` : ''}
  `;
}

// Feedbacks e alinhamentos que a pessoa recebeu (individual ou num grupo), direto no
// perfil (2.34.7.1; antes era só um link pra tela de Feedbacks). Mesma rota e mesma
// permissão da tela de Feedbacks; editar/remover continua lá.
async function carregarFeedbacksPerfil() {
  const destino = document.getElementById('perfil-lista-feedbacks');
  if (!destino) return;
  try {
    const resp = await fetch('/api/feedbacks/listar?usuario=' + encodeURIComponent(USUARIO_PERFIL));
    const dados = await resp.json();
    if (!dados.ok) { destino.innerHTML = '<div class="data-feedback">' + escaparHtml(dados.erro || 'Não foi possível carregar.') + '</div>'; return; }
    if (!dados.registros.length) { destino.innerHTML = '<div class="data-feedback">Nenhum feedback ou alinhamento registrado pra essa pessoa.</div>'; return; }
    destino.innerHTML = dados.registros.map(f => {
      const tipo = f.tipo || 'Feedback';
      const grupo = f.escopo === 'grupo' ? ' <span class="data-feedback">(em grupo: ' + escaparHtml(f.descricao_alvo) + ')</span>' : '';
      const canva = f.link_canva ? '<a class="link-canva-feedback" target="_blank" rel="noopener" href="' + escaparHtml(f.link_canva) + '">🔗 Ver slide no Canva</a> ' : '';
      const anexo = f.anexo ? '<a class="link-canva-feedback" href="/feedback-anexo/' + f.id + '">📎 ' + escaparHtml(f.anexo_nome_original || 'Baixar anexo') + '</a>' : '';
      const editado = f.editado_em ? '<span class="editado-feedback"> (editado)</span>' : '';
      return '<div class="item-feedback">' +
        '<div class="cabecalho-item-feedback">' +
          '<span class="autor-feedback"><span class="badge-tipo-feedback ' + (tipo === 'Alinhamento' ? 'tipo-alinhamento' : 'tipo-feedback') + '">' + escaparHtml(tipo) + '</span>' +
            escaparHtml(f.autor_nome || '') + grupo + renderizarEstrelas(f.nota) + '</span>' +
          '<span class="data-feedback">' + escaparHtml(f.criado_em || '') + editado + (f.equipe ? ' · ' + escaparHtml(f.equipe) : '') + '</span>' +
        '</div>' +
        '<div class="texto-feedback">' + escaparHtml(f.texto || '') + '</div>' + canva + anexo +
      '</div>';
    }).join('');
  } catch (e) {
    destino.innerHTML = '<div class="data-feedback">Erro ao carregar os feedbacks: ' + escaparHtml(String(e)) + '</div>';
  }
}

// capa com o wallpaper da Loja de Palminhas (3.3.7.0) toda vez que o perfil é desenhado
if (typeof renderizarPerfil === 'function' && window.aplicarCapaPerfil) {
  const renderizarPerfilSemCapa = renderizarPerfil;
  renderizarPerfil = function (dados) { renderizarPerfilSemCapa(dados); try { aplicarCapaPerfil(dados); } catch (e) { /* capa é enfeite */ } };
}

async function carregarPerfil() {
  try {
    const resp = await fetch('/api/perfil/' + encodeURIComponent(USUARIO_PERFIL));
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('perfil-erro').innerText = dados.erro || 'Não foi possível carregar o perfil.';
      return;
    }
    document.getElementById('perfil-erro').innerText = '';
    renderizarPerfil(dados);
    if (dados.pode_ver_feedback) carregarFeedbacksPerfil();
    if (dados.proprio_perfil) verificarCampanhaInsignias('perfil');
    if (window.location.hash === '#insignias' && !carregarPerfil.rolou) { carregarPerfil.rolou = true; setTimeout(irParaInsignias, 150); }
  } catch (e) {
    document.getElementById('perfil-erro').innerText = 'Erro ao carregar: ' + e;
  }
}

async function exportarHorasPerfil() {
  const botao = document.getElementById('btn-exportar-horas-perfil');
  const textoOriginal = botao.innerText;
  botao.disabled = true;
  botao.innerText = 'Gerando...';
  try {
    const resp = await fetch('/api/perfil/' + encodeURIComponent(USUARIO_PERFIL) + '/exportar-horas');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    if (!resp.ok) {
      let msg = 'Erro ao gerar a exportação.';
      try { msg = (await resp.json()).erro || msg; } catch (e) {}
      document.getElementById('perfil-erro').innerText = msg;
      return;
    }
    const blob = await resp.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `horas_${USUARIO_PERFIL}.xlsx`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (e) {
    document.getElementById('perfil-erro').innerText = 'Erro ao exportar: ' + e;
  } finally {
    botao.disabled = false;
    botao.innerText = textoOriginal;
  }
}

async function compararMesAnterior() {
  const botao = document.getElementById('btn-comparar-mes-anterior');
  const container = document.getElementById('comparacao-mes-anterior');
  botao.disabled = true;
  botao.innerText = 'Carregando...';
  try {
    const resp = await fetch('/api/perfil/' + encodeURIComponent(USUARIO_PERFIL) + '/mes-anterior');
    const dados = await resp.json();
    if (!dados.ok) {
      container.innerHTML = `<div class="vazio-perfil">${escaparHtml(dados.erro || 'Não foi possível comparar.')}</div>`;
      botao.style.display = 'none';
      return;
    }
    if (!dados.vinculado_movidesk || dados.erro_horas || dados.percentual_horas_mes === null) {
      container.innerHTML = `<div class="vazio-perfil">Sem dados de ${escaparHtml(dados.nome_mes)} pra comparar.</div>`;
      botao.style.display = 'none';
      return;
    }
    container.innerHTML = `
      <div class="comparacao-mes-anterior-perfil">
        <div class="titulo-comparacao-perfil">${escaparHtml(dados.nome_mes)}</div>
        <div class="grade-metricas-perfil">
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.percentual_horas_mes}%</div>
            <div class="rotulo-metrica">Do mês concluído</div>
          </div>
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.horas_trabalhadas_mes || '–'}</div>
            <div class="rotulo-metrica">Horas trabalhadas</div>
          </div>
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.meta_horas_mes || '–'}</div>
            <div class="rotulo-metrica">Meta do mês</div>
          </div>
          <div class="metrica-perfil">
            <div class="valor-metrica">${dados.tickets_mes ?? '–'}</div>
            <div class="rotulo-metrica">Tickets com ação</div>
          </div>
        </div>
      </div>
    `;
    botao.style.display = 'none';
  } catch (e) {
    container.innerHTML = `<div class="vazio-perfil">Erro ao comparar: ${escaparHtml(String(e))}</div>`;
    botao.disabled = false;
    botao.innerText = 'Comparar com mês anterior';
  }
}

// trocar foto: abre o ajuste (zoom e enquadramento, telas/insignias.py) e manda a foto já recortada (2.35.6.0)
document.getElementById('perfil-input-foto').addEventListener('change', (ev) => {
  const arquivo = ev.target.files[0];
  ev.target.value = '';
  if (!arquivo) return;
  abrirRecorteFotoIns(arquivo, async (dataUrl) => {
    const resp = await fetch('/api/usuarios/upload-foto', {
      method: 'POST',
      headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'usuario=' + encodeURIComponent(USUARIO_PERFIL) + '&foto=' + encodeURIComponent(dataUrl),
    });
    const dados = await resp.json();
    if (!dados.ok) {
      document.getElementById('perfil-erro').innerText = dados.erro || 'Não foi possível trocar a foto.';
      return;
    }
    // 3.2.3.0: a foto da navbar (e qualquer outra dessa pessoa na tela) troca na hora, sem esperar recarregar
    const versaoFoto = Date.now();
    document.querySelectorAll('img[src*="/foto-usuario/' + encodeURIComponent(USUARIO_PERFIL) + '"]').forEach(img => {
      img.src = '/foto-usuario/' + encodeURIComponent(USUARIO_PERFIL) + '?t=' + versaoFoto;
    });
    carregarPerfil();
  }, (mensagem) => { document.getElementById('perfil-erro').innerText = mensagem; });
});

window.aoMudarInsigniasIns = carregarPerfil;  // participar da campanha ou destacar: recarrega o perfil
carregarPerfil();
</script>
</body>
</html>
"""
