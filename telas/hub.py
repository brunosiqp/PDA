"""Hub principal: mural da equipe (2.35.7.0), seções de cards e o HTML de cada card.

Só texto (HTML/CSS/JS); a lógica fica no alertas_gui.py.
"""


_HUB_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Painel de Automações - Comunidade</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  /* 2.35.7.0: o início virou um mural da equipe (linha do tempo com palminhas) com o
     menu à esquerda: Início, Automações, Gestão de equipe (só admin) e Outros */
  .conteudo.conteudo-mural { max-width: 1420px; }
  .layout-mural { display: grid; grid-template-columns: 236px minmax(0, 1fr); gap: 28px; align-items: start; }

  /* ---------- lateral ---------- */
  .lateral-mural { position: sticky; top: 18px; display: flex; flex-direction: column; gap: 14px; }
  .cartao-eu { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 18px; padding: 20px 16px 16px;
               text-align: center; text-decoration: none; color: inherit; display: block; position: relative; overflow: hidden;
               transition: border-color .15s; }
  .cartao-eu::before { content: ""; position: absolute; inset: 0 0 auto 0; height: 58px;
                       background: linear-gradient(120deg, rgba(45,184,207,.35), rgba(176,203,28,.28)); }
  .cartao-eu:hover { border-color: var(--teal); }
  .cartao-eu .foto-eu { position: relative; width: 78px; height: 78px; margin: 6px auto 10px; }
  .cartao-eu .foto-eu .avatar-mural { width: 78px; height: 78px; font-size: 26px; box-shadow: 0 0 0 4px var(--bg-panel-solid); }
  .cartao-eu .destaque-eu { position: absolute; right: -8px; bottom: -6px; width: 34px; height: 34px;
                            filter: drop-shadow(0 2px 4px rgba(0,0,0,.45)); }
  .cartao-eu .destaque-eu svg { width: 34px; height: 34px; }
  .cartao-eu .nome-eu { font-weight: 800; font-size: 15px; }
  .cartao-eu .cargo-eu { font-size: 12px; color: var(--fg-dim); margin-top: 3px; line-height: 1.4; }
  /* Loja de Palminhas no menu (3.3.7.0) */
  a.item-menu.item-loja { text-decoration: none; color: var(--fg); background: linear-gradient(90deg, rgba(242,183,5,.13), transparent); }
  a.item-menu.item-loja svg { stroke: #f2b705; }
  .selo-novo-loja { margin-left: auto; font-size: 9.5px; font-weight: 900; color: #1a1205; background: #f2b705; border-radius: 99px; padding: 2px 7px; }
  .cartao-eu .ver-perfil { display: inline-block; margin-top: 10px; font-size: 11.5px; color: var(--teal); font-weight: 700; }

  .menu-mural { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 18px; padding: 8px; display: flex; flex-direction: column; gap: 2px; }
  .item-menu { display: flex; align-items: center; gap: 11px; padding: 11px 12px; border-radius: 12px; border: none; background: none;
               color: var(--fg); font: inherit; font-size: 13.5px; font-weight: 600; cursor: pointer; text-align: left; width: 100%;
               transition: background .15s, color .15s; position: relative; }
  .item-menu svg { width: 19px; height: 19px; flex-shrink: 0; stroke: var(--fg-dim); transition: stroke .15s; }
  .item-menu:hover { background: rgba(var(--tinta), .06); }
  .item-menu.ativo { background: linear-gradient(90deg, rgba(45,184,207,.18), rgba(45,184,207,.04)); color: var(--fg); }
  .item-menu.ativo::before { content: ""; position: absolute; left: 0; top: 9px; bottom: 9px; width: 3px; border-radius: 3px; background: var(--teal); }
  .item-menu.ativo svg { stroke: var(--teal); }
  .item-menu.restrito { opacity: .55; cursor: not-allowed; }
  .item-menu.restrito:hover { background: none; }
  .item-menu .selo-restrito { margin-left: auto; font-size: 9.5px; font-weight: 800; letter-spacing: .06em; color: var(--fg-dim);
                              border: 1px solid var(--border); border-radius: 99px; padding: 2px 7px; }
  .item-menu .qtd { margin-left: auto; font-size: 11px; font-weight: 700; color: var(--fg-dim); background: rgba(var(--tinta), .07);
                    border-radius: 99px; padding: 2px 8px; }
  .item-menu .sub-item { display: block; font-size: 10.5px; font-weight: 500; color: var(--fg-dim); margin-top: 1px; }

  .favoritos-lateral { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 18px; padding: 14px 12px 10px; }
  .favoritos-lateral h3, .bloco-lado h3 { font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); margin: 0 4px 8px; font-weight: 700; }
  .atalho { display: flex; align-items: center; gap: 9px; padding: 7px 6px; border-radius: 9px; color: var(--fg); text-decoration: none; font-size: 12.5px; }
  .atalho:hover { background: rgba(var(--tinta), .06); }
  .atalho .ponto-cor { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
  .favoritos-lateral .vazio { font-size: 11.5px; color: var(--fg-dim); margin: 0 4px 4px; line-height: 1.5; }

  /* ---------- seções ---------- */
  .secao-mural { display: none; animation: surgir .35s ease; }
  .secao-mural.ativa { display: block; }
  @keyframes surgir { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
  .topo-secao { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin: 2px 0 20px; flex-wrap: wrap; }
  .topo-secao h1 { font-size: 26px; margin: 0 0 6px; font-weight: 800; letter-spacing: -.01em; }
  .topo-secao .sub { color: var(--fg-dim); font-size: 13.5px; }
  .topo-secao .link-nome-hero { color: inherit; text-decoration: none; border-bottom: 2px solid transparent; }
  .topo-secao .link-nome-hero:hover { border-color: var(--teal); }
  .busca-secao { background: rgba(var(--poco), .2); border: 1px solid var(--border); border-radius: 12px; color: var(--fg);
                 padding: 10px 14px; font: inherit; font-size: 13px; width: 260px; }
  .busca-secao:focus { outline: none; border-color: var(--teal); }

  /* indicadores */
  .indicadores-mural { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 24px; }
  .ind { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 16px 18px; position: relative; overflow: hidden; min-height: 104px; }
  .ind::after { content: ""; position: absolute; right: -30px; top: -30px; width: 100px; height: 100px; border-radius: 50%;
                background: var(--cor-ind, var(--teal)); opacity: .09; }
  .ind .rotulo { font-size: 11px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); font-weight: 700; display: flex; align-items: center; gap: 7px; }
  .ind .rotulo svg { width: 15px; height: 15px; stroke: var(--cor-ind, var(--teal)); }
  .ind .valor { font-size: 28px; font-weight: 800; margin: 8px 0 2px; letter-spacing: -.02em; }
  .ind .valor small { font-size: 13px; font-weight: 600; color: var(--fg-dim); letter-spacing: 0; }
  .ind .detalhe { font-size: 12px; color: var(--fg-dim); }
  .ind .barra { height: 6px; border-radius: 99px; background: rgba(var(--tinta), .08); margin-top: 9px; overflow: hidden; }
  .ind .barra span { display: block; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--teal), var(--lime)); width: 0; transition: width .8s ease; }
  .ind .ins-ind { position: absolute; right: 12px; bottom: 10px; width: 46px; height: 46px; }
  .ind .ins-ind svg { width: 46px; height: 46px; }
  .ind.carregando .valor { color: transparent; background: rgba(var(--tinta), .07); border-radius: 8px; width: 70%; animation: piscar 1.2s infinite; }
  @keyframes piscar { 50% { opacity: .45; } }

  .colunas-inicio { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 24px; align-items: start; }

  /* linha do tempo */
  .cabeca-feed { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; flex-wrap: wrap; }
  .cabeca-feed h2 { font-size: 17px; margin: 0; display: flex; align-items: center; gap: 8px; }
  .filtros-feed { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip-feed { border: 1px solid var(--border); background: transparent; color: var(--fg-dim); border-radius: 99px; padding: 6px 12px;
               font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; transition: all .15s; }
  .chip-feed:hover { color: var(--fg); border-color: rgba(var(--tinta), .3); }
  .chip-feed.ativo { background: var(--teal); border-color: var(--teal); color: #071016; }
  .feed { display: flex; flex-direction: column; gap: 12px; }
  .evento { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 16px 18px 12px;
            display: grid; grid-template-columns: 50px minmax(0, 1fr) auto; gap: 14px; position: relative; animation: surgir .4s ease both; }
  .evento .lado-foto { position: relative; width: 50px; height: 50px; text-decoration: none; }
  .evento .lado-foto .avatar-mural { width: 50px; height: 50px; font-size: 17px; }
  /* insígnia em destaque da pessoa junto da foto (3.0.1.0, no lugar do emoji do tipo) */
  .evento .ins-foto { position: absolute; right: -9px; bottom: -7px; width: 28px; height: 28px; filter: drop-shadow(0 2px 3px rgba(0,0,0,.5)); }
  .evento .ins-foto svg { width: 28px; height: 28px; }
  /* colaboração: as fotos de quem fez juntas, uma por cima da outra */
  .evento .lado-foto.colab .avatar-mural { position: absolute; width: 36px; height: 36px; font-size: 13px; box-shadow: 0 0 0 3px var(--bg-panel-solid); }
  .evento .lado-foto.colab a:nth-child(1) .avatar-mural { left: 0; top: 0; }
  .evento .lado-foto.colab a:nth-child(2) .avatar-mural { left: 20px; top: 16px; }
  .evento .lado-foto.colab .mais-colab { position: absolute; right: -6px; top: -4px; font-size: 10px; font-weight: 800; background: var(--teal);
                                          color: #071016; border-radius: 99px; padding: 1px 6px; }
  .evento.colab-ev { border-color: rgba(192,132,252,.45);
                     background: radial-gradient(circle at 0% 0%, rgba(192,132,252,.12), transparent 50%), var(--bg-panel); }
  .link-ev { display: inline-flex; align-items: center; gap: 6px; margin-top: 9px; font-size: 12px; font-weight: 700; color: var(--teal);
             text-decoration: none; border: 1px solid rgba(45,184,207,.4); border-radius: 99px; padding: 5px 12px; background: rgba(45,184,207,.08); }
  .link-ev:hover { background: rgba(45,184,207,.18); }
  .selo-fixado { display: inline-block; margin-left: 8px; font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase;
                 color: var(--fg-dim); background: rgba(var(--tinta), .07); border-radius: 99px; padding: 1px 8px; vertical-align: 1px; }
  .evento.destacado { box-shadow: 0 0 0 2px var(--teal), 0 0 30px -6px rgba(45,184,207,.6); }
  /* publicações da Comunidade (3.2.6.0) */
  .compor-post { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 14px 16px; margin-bottom: 12px; }
  .compor-post .topo-compor { display: flex; gap: 12px; align-items: flex-start; }
  .compor-post .topo-compor .avatar-mural { width: 40px; height: 40px; font-size: 14px; flex: none; }
  .compor-post textarea { flex: 1; min-width: 0; box-sizing: border-box; resize: vertical; min-height: 44px; max-height: 320px; font: inherit; font-size: 13.5px;
                          background: rgba(var(--poco), .25); color: var(--fg); border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; }
  .compor-post textarea:focus { outline: none; border-color: var(--teal); }
  .previas-post { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 0 52px; }
  .previas-post:empty { display: none; }
  .previa-post { position: relative; border: 1px solid var(--border); border-radius: 10px; background: rgba(var(--tinta), .04); font-size: 12px; }
  .previa-post img { display: block; width: 84px; height: 84px; object-fit: cover; border-radius: 9px; }
  .previa-post.arq { padding: 8px 30px 8px 10px; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .previa-post button { position: absolute; top: 3px; right: 3px; width: 22px; height: 22px; border-radius: 50%; border: none; cursor: pointer;
                        background: rgba(0,0,0,.65); color: #fff; font-size: 13px; line-height: 22px; padding: 0; }
  .acoes-compor { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 10px 0 0 52px; }
  .btn-anexar { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; font-weight: 600; color: var(--fg-dim); cursor: pointer;
                border: 1px solid var(--border); border-radius: 99px; padding: 6px 12px; background: rgba(var(--tinta), .03); }
  .btn-anexar:hover { color: var(--fg); border-color: var(--teal); }
  .check-importante { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 700; color: #e8a33d; cursor: pointer; }
  .check-importante span { font-weight: 400; color: var(--fg-dim); font-size: 11.5px; }
  .btn-publicar { margin-left: auto; background: var(--gradiente-marca); color: #0b0f14; border: none; border-radius: 10px; font-weight: 800;
                  font-size: 13px; padding: 8px 18px; cursor: pointer; }
  .btn-publicar:disabled { opacity: .55; cursor: default; }
  .evento .texto-post { white-space: pre-wrap; word-break: break-word; font-size: 13.5px; color: var(--fg); }
  .evento.post-ev.post-importante { border-color: rgba(232,163,61,.6);
      background: linear-gradient(180deg, rgba(232,163,61,.10), transparent 45%), var(--bg-panel); }
  .selo-importante { display: inline-block; margin-left: 8px; font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase;
                     color: #0b0f14; background: #e8a33d; border-radius: 99px; padding: 1px 8px; vertical-align: 1px; }
  .galeria-post { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; margin-top: 10px; max-width: 520px; }
  .galeria-post.uma { grid-template-columns: minmax(0, 1fr); }
  .galeria-post a, .galeria-post button { display: block; width: 100%; padding: 0; border-radius: 12px; overflow: hidden; border: 1px solid var(--border);
                                           background: rgba(var(--poco), .3); cursor: zoom-in; }
  .galeria-post button:focus-visible { outline: 2px solid var(--teal); outline-offset: 2px; }
  /* foto ampliada da publicação (3.3.0.1): abre na própria página, sem outra aba */
  .fundo-foto-post { position: fixed; inset: 0; z-index: 460; background: rgba(0,0,0,.88); display: flex; align-items: center; justify-content: center;
                     padding: 48px 64px; box-sizing: border-box; animation: aparecer-anuncio .2s ease; }
  .fundo-foto-post img { max-width: 100%; max-height: 100%; object-fit: contain; border-radius: 10px; box-shadow: 0 20px 60px rgba(0,0,0,.6); cursor: default; }
  .fundo-foto-post .btn-foto { position: absolute; border: none; cursor: pointer; color: #fff; background: rgba(255,255,255,.12); border-radius: 50%;
                               width: 44px; height: 44px; font-size: 22px; line-height: 44px; padding: 0; display: flex; align-items: center; justify-content: center; }
  .fundo-foto-post .btn-foto:hover { background: rgba(255,255,255,.24); }
  .fundo-foto-post .fechar-foto { top: 14px; right: 16px; }
  .fundo-foto-post .ant-foto { left: 14px; top: 50%; transform: translateY(-50%); }
  .fundo-foto-post .prox-foto { right: 14px; top: 50%; transform: translateY(-50%); }
  .fundo-foto-post .info-foto { position: absolute; bottom: 14px; left: 50%; transform: translateX(-50%); color: rgba(255,255,255,.8); font-size: 12.5px;
                                max-width: 80%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  @media (max-width: 640px) { .fundo-foto-post { padding: 56px 8px; } }
  .galeria-post img { display: block; width: 100%; height: 180px; object-fit: cover; }
  .galeria-post.uma img { height: auto; max-height: 420px; object-fit: contain; }
  .anexos-post { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }
  /* vídeo na publicação (3.4.2.0) */
  .videos-post { display: flex; flex-direction: column; gap: 8px; margin-top: 10px; max-width: 520px; }
  .videos-post video { width: 100%; max-height: 420px; border-radius: 12px; background: #000; border: 1px solid var(--border); display: block; }
  .previa-post.vid { display: inline-flex; align-items: center; gap: 6px; }
  .previa-post.vid video { width: 96px; height: 64px; object-fit: cover; border-radius: 8px; background: #000; }
  .anexo-post { display: inline-flex; align-items: center; gap: 6px; max-width: 100%; font-size: 12px; font-weight: 600; color: var(--teal); text-decoration: none;
                border: 1px solid rgba(45,184,207,.35); border-radius: 10px; padding: 6px 10px; background: rgba(45,184,207,.06); }
  .anexo-post:hover { background: rgba(45,184,207,.15); }
  .anexo-post .nome-anexo { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
  .anexo-post .tam-anexo { color: var(--fg-dim); font-weight: 400; }
  /* votação (3.3.0.0) */
  /* publicação em grupo (3.4.1.0) */
  .grupo-compor { margin: 10px 0 0 52px; border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; background: rgba(var(--tinta), .02); }
  .grupo-compor .cab-grupo { display: flex; align-items: center; gap: 8px; font-size: 12.5px; margin-bottom: 8px; }
  .grupo-compor .cab-grupo span { color: var(--fg-dim); font-size: 11.5px; flex: 1; }
  .grupo-compor .cab-grupo button { border: none; background: none; color: var(--fg-dim); font-size: 18px; cursor: pointer; line-height: 1; }
  .atalhos-grupo { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
  .atalhos-grupo button { font: inherit; font-size: 11.5px; font-weight: 700; color: var(--fg); background: rgba(var(--tinta), .05); border: 1px solid var(--border);
                          border-radius: 99px; padding: 4px 10px; cursor: pointer; }
  .atalhos-grupo button:hover { border-color: var(--teal); color: var(--teal); }
  .atalhos-grupo input { flex: 1; min-width: 160px; font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25);
                         border: 1px solid var(--border); border-radius: 99px; padding: 5px 12px; }
  .lista-grupo { max-height: 210px; overflow-y: auto; display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 4px; }
  .pessoa-grupo { display: flex; align-items: center; gap: 8px; padding: 5px 8px; border-radius: 9px; cursor: pointer; font-size: 12.5px; min-width: 0; }
  .pessoa-grupo:hover { background: rgba(var(--tinta), .05); }
  .pessoa-grupo.marcada { background: rgba(45,184,207,.12); }
  .pessoa-grupo input { accent-color: var(--teal); }
  .pessoa-grupo .avatar-mural { width: 24px; height: 24px; font-size: 9px; flex: none; }
  .pessoa-grupo .nome-g { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pessoa-grupo small { color: var(--fg-dim); display: block; font-size: 10.5px; }
  .resumo-grupo { font-size: 11.5px; color: var(--fg-dim); margin-top: 8px; }
  .btn-anexar.com-grupo { border-color: var(--teal); color: var(--teal); }
  .link-grupo { font: inherit; color: inherit; background: none; border: none; padding: 0; cursor: pointer; text-align: left; text-decoration: underline dotted rgba(var(--tinta), .35);
                text-underline-offset: 3px; }
  .link-grupo:hover { color: var(--teal); }
  @media (max-width: 640px) { .grupo-compor { margin-left: 0; } }
  .votacao-compor { margin: 10px 0 0 52px; border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; background: rgba(var(--tinta), .02); }
  .votacao-compor .cab-votacao { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; font-size: 13px; }
  .votacao-compor .cab-votacao span { color: var(--fg-dim); font-size: 11.5px; flex: 1; }
  .tirar-votacao { border: none; background: none; color: var(--fg-dim); font-size: 18px; cursor: pointer; line-height: 1; padding: 0 4px; }
  .tirar-votacao:hover { color: var(--erro); }
  .opcao-votacao-compor { display: flex; gap: 6px; margin-bottom: 6px; }
  .opcao-votacao-compor input { flex: 1; min-width: 0; box-sizing: border-box; font: inherit; font-size: 13px; color: var(--fg);
                                background: rgba(var(--poco), .25); border: 1px solid var(--border); border-radius: 9px; padding: 7px 10px; }
  .opcao-votacao-compor input:focus { outline: none; border-color: var(--teal); }
  .opcao-votacao-compor button { border: none; background: none; color: var(--fg-dim); cursor: pointer; font-size: 16px; }
  .config-votacao { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 8px; font-size: 12.5px; color: var(--fg-dim); align-items: center; }
  .config-votacao input[type=datetime-local], .config-votacao select { font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25);
                                     border: 1px solid var(--border); border-radius: 8px; padding: 4px 8px; margin-left: 4px; }
  .votacao-post { margin-top: 12px; max-width: 520px; display: flex; flex-direction: column; gap: 6px; }
  /* votação encerrada (3.3.7.0): faixa de resultado final e a opção vencedora marcada */
  .faixa-encerrada { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 800; color: var(--fg-dim);
                     background: rgba(var(--tinta), .05); border: 1px solid var(--border); border-radius: 10px; padding: 6px 10px; }
  .opcao-voto.vencedora { border-color: var(--lime); }
  .opcao-voto.vencedora .barra-voto { background: rgba(176,203,28,.2); }
  .opcao-voto .trofeu { position: relative; }
  .opcao-voto { position: relative; display: flex; align-items: center; gap: 10px; width: 100%; text-align: left; overflow: hidden; cursor: pointer;
                font: inherit; font-size: 13px; color: var(--fg); border: 1px solid var(--border); border-radius: 10px; padding: 8px 12px;
                background: rgba(var(--tinta), .03); }
  .opcao-voto:hover:not(:disabled) { border-color: var(--teal); }
  .opcao-voto:disabled { cursor: default; }
  .opcao-voto .barra-voto { position: absolute; inset: 0 auto 0 0; background: rgba(45,184,207,.14); transition: width .4s ease; pointer-events: none; }
  .opcao-voto.minha { border-color: var(--teal); }
  .opcao-voto.minha .barra-voto { background: rgba(45,184,207,.26); }
  .opcao-voto .marca { position: relative; width: 16px; height: 16px; border-radius: 50%; border: 2px solid var(--fg-dim); flex: none; }
  .votacao-post.multipla .opcao-voto .marca { border-radius: 4px; }
  .opcao-voto.minha .marca { border-color: var(--teal); background: var(--teal); box-shadow: inset 0 0 0 2px var(--bg-panel-solid, #181f27); }
  .opcao-voto .txt-voto { position: relative; flex: 1; min-width: 0; word-break: break-word; }
  .opcao-voto .pct-voto { position: relative; font-weight: 800; font-size: 12.5px; color: var(--fg-dim); }
  /* votação pública (3.3.6.0): quem votou embaixo de cada opção */
  .quem-voto { display: flex; align-items: center; gap: 6px; margin: -2px 0 2px 12px; background: none; border: none; padding: 2px 4px; font: inherit;
               font-size: 11.5px; color: var(--fg-dim); cursor: pointer; text-align: left; border-radius: 8px; }
  .quem-voto:hover { color: var(--fg); background: rgba(var(--tinta), .05); }
  .quem-voto .pilha { display: inline-flex; }
  .quem-voto .pilha .avatar-mural { width: 20px; height: 20px; font-size: 8.5px; margin-left: -6px; border: 2px solid var(--bg-panel-solid, #181f27); }
  .quem-voto .pilha .avatar-mural:first-child { margin-left: 0; }
  .quem-voto.faltam-voto { margin: 4px 0 0; padding-left: 4px; color: var(--fg-dim); }
  .quem-voto.faltam-voto .pilha .avatar-mural { filter: grayscale(.6); opacity: .85; }
  .grupo-voto-mod { font-size: 12px; font-weight: 800; color: var(--fg-dim); margin: 10px 0 4px; }
  /* aviso fixo de votações abertas (3.3.6.0) */
  .aviso-votacoes { background: var(--bg-panel); border: 1px solid rgba(45,184,207,.45); border-radius: 16px; padding: 12px 14px; margin-bottom: 12px;
                    display: flex; flex-direction: column; gap: 8px; }
  .aviso-votacoes .tit-av { font-size: 12.5px; font-weight: 800; color: var(--teal); }
  .aviso-votacoes .linha-av { display: flex; align-items: center; gap: 10px; font-size: 13px; }
  .aviso-votacoes .linha-av .perg { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .aviso-votacoes .linha-av .perg small { color: var(--fg-dim); }
  .aviso-votacoes button { flex: none; font: inherit; font-size: 12px; font-weight: 700; color: #0b0f14; background: var(--teal); border: none;
                           border-radius: 99px; padding: 5px 12px; cursor: pointer; }
  .confirma-voto-mod .opcao-escolhida { font-size: 15px; font-weight: 800; margin: 6px 0 14px; }
  .confirma-voto-mod .botoes-cv { display: flex; gap: 8px; justify-content: flex-end; }
  .confirma-voto-mod .botoes-cv button { font: inherit; font-size: 13px; font-weight: 700; border-radius: 10px; padding: 8px 14px; cursor: pointer;
                                          border: 1px solid var(--border); background: none; color: var(--fg); }
  .confirma-voto-mod .botoes-cv button.pri { background: var(--teal); border-color: var(--teal); color: #0b0f14; }
  .rodape-votacao { font-size: 11.5px; color: var(--fg-dim); }
  .rodape-votacao b { color: var(--fg); }
  @media (max-width: 640px) { .votacao-compor { margin-left: 0; } }
  .apagar-post { border: none; background: none; color: var(--fg-dim); font: inherit; font-size: 11.5px; cursor: pointer; padding: 2px 4px; }
  .apagar-post:hover { color: var(--erro); }
  .apagar-post.reenviar-teams:hover { color: var(--teal); }
  @media (max-width: 640px) { .previas-post, .acoes-compor { margin-left: 0; } .btn-publicar { margin-left: 0; width: 100%; } }
  /* comentários (3.0.1.0) */
  .btn-comentar { display: inline-flex; align-items: center; gap: 6px; border: 1px solid var(--border); background: rgba(var(--tinta), .03);
                  color: var(--fg); border-radius: 99px; padding: 6px 13px; font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; }
  .btn-comentar:hover { border-color: var(--teal); }
  .rodape-ev .quem-bateu { margin-left: 4px; }
  .comentarios-ev { grid-column: 1 / -1; display: flex; flex-direction: column; gap: 8px; }
  .comentarios-ev:empty { display: none; }
  .comentario { display: flex; gap: 9px; align-items: flex-start; min-width: 0; }
  /* 3.3.9.5: palavra enorme sem espaço ("OOOO...H!") vazava do balão; agora quebra onde precisar */
  .comentario > div { min-width: 0; max-width: 100%; }
  .evento > div, .evento .corpo-ev { min-width: 0; }
  .balao-com, .evento .titulo-ev, .evento .detalhe-ev, .evento .texto-post, .opcao-voto .txt-voto { overflow-wrap: anywhere; word-break: break-word; }
  .comentario .avatar-mural { width: 28px; height: 28px; font-size: 10.5px; margin-top: 2px; }
  .balao-com { background: rgba(var(--tinta), .05); border-radius: 12px; padding: 7px 11px; font-size: 12.8px; line-height: 1.45; min-width: 0; }
  .balao-com b { font-size: 12px; margin-right: 6px; }
  .balao-com b a { color: inherit; text-decoration: none; }
  .meta-com { font-size: 10.5px; color: var(--fg-dim); margin: 2px 0 0 4px; }
  .meta-com button { background: none; border: none; padding: 0; margin-left: 8px; color: var(--fg-dim); font: inherit; font-size: 10.5px; cursor: pointer; }
  .meta-com button:hover { color: var(--erro); }
  .caixa-com { display: none; gap: 8px; align-items: center; }
  .caixa-com.aberta { display: flex; }
  .caixa-com .avatar-mural { width: 28px; height: 28px; font-size: 10.5px; }
  .caixa-com { flex-wrap: wrap; }
  .caixa-com .campo-com { flex: 1; min-width: 0; display: flex; align-items: center; gap: 2px; background: rgba(var(--poco), .2);
                          border: 1px solid var(--border); border-radius: 99px; padding-right: 6px; }
  .caixa-com .campo-com:focus-within { border-color: var(--teal); }
  .caixa-com .campo-com input { border: none !important; background: transparent !important; }
  .caixa-com .btn-extra-com { border: none; background: none; cursor: pointer; font-size: 16px; padding: 4px 5px; border-radius: 99px; line-height: 1; color: inherit; }
  .caixa-com .btn-extra-com:hover { background: rgba(var(--tinta), .08); }
  .previa-com { flex-basis: 100%; display: flex; align-items: center; gap: 8px; margin-left: 36px; font-size: 12px; color: var(--fg-dim); }
  .previa-com[hidden] { display: none; }
  .previa-com img { width: 56px; height: 56px; object-fit: cover; border-radius: 10px; border: 1px solid var(--border); }
  .previa-com button { border: none; background: none; color: var(--fg-dim); cursor: pointer; font-size: 16px; }
  .img-com { display: block; margin-top: 6px; padding: 0; border: none; background: none; cursor: zoom-in; border-radius: 10px; overflow: hidden; }
  .img-com img { display: block; max-width: 240px; max-height: 200px; border-radius: 10px; object-fit: cover; }
  .painel-emoji { position: absolute; z-index: 470; width: 296px; box-sizing: border-box; display: grid; grid-template-columns: repeat(8, 1fr); gap: 2px;
                  background: var(--bg-panel-solid, #181f27); border: 1px solid var(--border); border-radius: 14px; padding: 8px;
                  box-shadow: 0 16px 40px rgba(0,0,0,.45); }
  .painel-emoji button { border: none; background: none; font-size: 20px; padding: 4px 0; border-radius: 8px; cursor: pointer; line-height: 1.2; }
  .painel-emoji button:hover, .painel-emoji button:focus-visible { background: rgba(var(--tinta), .1); outline: none; }
  .publico-post { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 700; color: var(--fg-dim); }
  .publico-post select { font: inherit; font-size: 12.5px; color: var(--fg); background: rgba(var(--poco), .25); border: 1px solid var(--border);
                         border-radius: 99px; padding: 5px 10px; }
  .selo-publico { display: inline-block; margin-left: 8px; font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase;
                  color: #a78bfa; background: rgba(167,139,250,.14); border-radius: 99px; padding: 1px 8px; vertical-align: 1px; }
  .caixa-com input { flex: 1; min-width: 0; background: rgba(var(--poco), .2); border: 1px solid var(--border); border-radius: 99px; color: var(--fg);
                     padding: 8px 14px; font: inherit; font-size: 12.8px; }
  .caixa-com input:focus { outline: none; border-color: var(--teal); }
  .caixa-com .btn-enviar-com { border: none; background: var(--teal); color: #071016; font: inherit; font-weight: 800; font-size: 12px; border-radius: 99px; padding: 8px 14px; cursor: pointer; }
  .caixa-com .btn-enviar-com:disabled { opacity: .5; }
  .evento.tempo-hoje { border-color: rgba(251,146,60,.55);
                       background: radial-gradient(circle at 92% 0%, rgba(251,146,60,.16), transparent 55%), var(--bg-panel); }
  .evento.tempo-hoje .quando-ev { color: #fb923c; font-weight: 700; }
  /* férias (3.2.2.0): saída com mar e areia, volta com folhagem; o emoji balança devagar */
  .evento.ferias-ev.ferias-ida { border-color: rgba(56,189,248,.5);
      background: linear-gradient(180deg, rgba(56,189,248,.12), transparent 55%), radial-gradient(circle at 100% 100%, rgba(250,204,21,.16), transparent 45%), var(--bg-panel); }
  .evento.ferias-ev.ferias-volta { border-color: rgba(52,211,153,.5);
      background: radial-gradient(circle at 95% 0%, rgba(52,211,153,.16), transparent 50%), radial-gradient(circle at 0% 100%, rgba(56,189,248,.10), transparent 45%), var(--bg-panel); }
  .evento.ferias-ev .tipo-ev { color: #38bdf8; }
  .evento.ferias-ev.ferias-volta .tipo-ev { color: #34d399; }
  .onda-ferias { display: inline-block; animation: balanco-ferias 3.2s ease-in-out infinite; transform-origin: 50% 90%; }
  @keyframes balanco-ferias { 0%, 100% { transform: rotate(-6deg); } 50% { transform: rotate(6deg) translateY(-2px); } }
  @media (prefers-reduced-motion: reduce) { .onda-ferias { animation: none; } }
  /* usuário desativado no PDA (3.1.5.0): em vermelho, com a foto apagada */
  .evento.saida-ev { border-color: rgba(241,76,76,.55); background: radial-gradient(circle at 92% 0%, rgba(241,76,76,.14), transparent 55%), var(--bg-panel); }
  .evento.saida-ev .titulo-ev, .evento.saida-ev .titulo-ev a { color: var(--erro); }
  .evento.saida-ev .tipo-ev { color: var(--erro); }
  .evento.saida-ev img, .evento.saida-ev .av { filter: grayscale(1); opacity: .7; }
  .evento.pda-ev { border-color: rgba(45,184,207,.6);
                   background: radial-gradient(circle at 0% 0%, rgba(45,184,207,.18), transparent 50%),
                               radial-gradient(circle at 100% 100%, rgba(176,203,28,.14), transparent 50%), var(--bg-panel); }

  /* parabéns pra quem faz aniversário (3.0.3.0): aparece no primeiro acesso do dia, com balões e confete */
  .festa-niver { position: fixed; inset: 0; z-index: 300; display: flex; align-items: center; justify-content: center; padding: 16px;
                 background: rgba(4,8,12,.62); backdrop-filter: blur(3px); -webkit-backdrop-filter: blur(3px); animation: surgir .35s ease; overflow: hidden; }
  .cartao-niver { position: relative; z-index: 2; max-width: 440px; width: 100%; text-align: center; padding: 34px 28px 26px; border-radius: 22px;
                  background: radial-gradient(circle at 50% 0%, rgba(242,183,5,.22), transparent 60%), var(--bg-panel-solid);
                  border: 1px solid rgba(242,183,5,.55); box-shadow: 0 30px 80px rgba(0,0,0,.55); animation: pular-niver .6s cubic-bezier(.2,1.4,.4,1); }
  @keyframes pular-niver { from { transform: scale(.7); opacity: 0; } to { transform: scale(1); opacity: 1; } }
  .cartao-niver .bolo { font-size: 64px; line-height: 1; animation: balancar 2.2s ease-in-out infinite; }
  .cartao-niver h2 { font-size: 24px; margin: 12px 0 8px; }
  .cartao-niver h2 span { background: linear-gradient(90deg, #f2b705, #fb923c, #e85d75); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .cartao-niver p { color: var(--fg-dim); font-size: 14px; line-height: 1.6; margin: 0 0 20px; }
  .cartao-niver button { border: none; background: linear-gradient(90deg, #f2b705, #fb923c); color: #1a1004; font: inherit; font-weight: 800;
                         font-size: 14px; border-radius: 12px; padding: 11px 26px; cursor: pointer; }
  .confete-niver { position: absolute; top: -20px; width: 9px; height: 15px; border-radius: 2px; z-index: 1; animation: cair-confete linear forwards; }
  @keyframes cair-confete { to { transform: translate(var(--vento), 110vh) rotate(var(--giro)); } }
  .balao-niver { position: absolute; bottom: -140px; z-index: 1; width: 58px; height: 72px; border-radius: 50% 50% 48% 48%;
                 animation: subir-balao ease-in forwards; }
  .balao-niver::after { content: ""; position: absolute; left: 50%; top: 100%; width: 1px; height: 60px; background: rgba(255,255,255,.45); }
  .balao-niver::before { content: ""; position: absolute; left: 22%; top: 16%; width: 12px; height: 20px; border-radius: 50%; background: rgba(255,255,255,.35); }
  @keyframes subir-balao { to { transform: translate(var(--vento), -130vh); } }
  @media (prefers-reduced-motion: reduce) { .confete-niver, .balao-niver { display: none; } }
  .evento .tipo-ev { font-size: 10.5px; font-weight: 800; text-transform: uppercase; letter-spacing: .07em; color: var(--cor-ev); }
  .evento .titulo-ev { font-size: 15px; font-weight: 700; margin: 3px 0 4px; line-height: 1.35; }
  .evento .titulo-ev a { color: inherit; text-decoration: none; }
  .evento .titulo-ev a:hover { color: var(--teal); }
  .evento .detalhe-ev { font-size: 12.5px; color: var(--fg-dim); line-height: 1.5; }
  .evento .quando-ev { font-size: 11.5px; color: var(--fg-dim); white-space: nowrap; }
  .evento .ins-ev { width: 62px; height: 62px; align-self: center; }
  .evento .ins-ev svg { width: 62px; height: 62px; }
  .evento .lado-dir { display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
  .degraus { display: flex; align-items: center; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
  .degraus span { font-size: 12px; padding: 4px 10px; border-radius: 99px; background: rgba(var(--tinta), .06); color: var(--fg-dim); }
  .degraus span.novo { background: rgba(176,203,28,.16); color: var(--lime); font-weight: 700; }
  .degraus i { font-style: normal; color: var(--fg-dim); }
  .rodape-ev { grid-column: 1 / -1; display: flex; align-items: center; gap: 12px; border-top: 1px solid var(--border); padding-top: 10px; margin-top: 2px; }
  .btn-palma { display: inline-flex; align-items: center; gap: 7px; border: 1px solid var(--border); background: rgba(var(--tinta), .03);
               color: var(--fg); border-radius: 99px; padding: 6px 14px 6px 11px; font: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer;
               transition: all .15s; position: relative; }
  .btn-palma .mao { font-size: 16px; display: inline-block; transition: transform .2s; }
  .btn-palma:hover { border-color: #f2b705; }
  .btn-palma:hover .mao { transform: rotate(-12deg) scale(1.15); }
  .btn-palma.bati { background: rgba(242,183,5,.14); border-color: rgba(242,183,5,.6); color: #f2b705; }
  .btn-palma.estourar .mao { animation: estourar .45s ease; }
  .btn-palma:disabled { cursor: default; opacity: .6; }
  @keyframes estourar { 0% { transform: scale(1); } 35% { transform: scale(1.55) rotate(-14deg); } 100% { transform: scale(1); } }
  .palma-voando { position: absolute; left: 12px; top: -4px; pointer-events: none; font-size: 16px; animation: voar .9s ease-out forwards; }
  @keyframes voar { to { transform: translate(var(--dx, 0px), -46px) scale(1.3); opacity: 0; } }
  .quem-bateu { font-size: 12px; color: var(--fg-dim); }
  .quem-bateu b { color: var(--fg); font-weight: 600; }
  /* anúncio de uma vez só (3.2.0.0): foto em GIF, com o Mario */
  .fundo-anuncio { position: fixed; inset: 0; z-index: 450; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; padding: 16px;
                   animation: aparecer-anuncio .25s ease; }
  .cartao-anuncio { box-sizing: border-box; width: min(420px, 100%); background: var(--bg-panel-solid, var(--bg-panel)); border: 1px solid rgba(45,184,207,.45); border-radius: 22px;
                    padding: 22px 24px 20px; text-align: center; box-shadow: 0 24px 70px rgba(0,0,0,.5); position: relative; overflow: hidden; }
  .cartao-anuncio::before { content: ""; position: absolute; inset: 0; pointer-events: none;
                            background: radial-gradient(circle at 50% 0%, rgba(45,184,207,.22), transparent 55%), radial-gradient(circle at 100% 100%, rgba(176,203,28,.14), transparent 50%); }
  .cartao-anuncio > * { position: relative; }
  .selo-anuncio { display: inline-block; font-size: 11px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; color: var(--lime);
                  background: rgba(176,203,28,.14); border: 1px solid rgba(176,203,28,.35); border-radius: 999px; padding: 4px 12px; }
  .palco-anuncio { width: 170px; height: 170px; margin: 14px auto 6px; border-radius: 50%; overflow: hidden; border: 3px solid transparent;
                   background: radial-gradient(circle, #2b3a4a, #121a22) padding-box, var(--gradiente-marca) border-box; box-shadow: 0 10px 30px rgba(45,184,207,.25); }
  .palco-anuncio img { width: 100%; height: 100%; object-fit: cover; object-position: center 20%; display: block; }
  .cartao-anuncio h2 { font-size: 20px; margin: 10px 0 6px; line-height: 1.25; }
  .cartao-anuncio h2 span { background: var(--gradiente-marca); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .cartao-anuncio p { font-size: 13.5px; color: var(--fg-dim); line-height: 1.5; margin: 0 0 16px; }
  .botoes-anuncio { display: flex; flex-direction: column; gap: 8px; }
  .btn-anuncio { display: block; text-decoration: none; background: var(--gradiente-marca); color: #0b0f14; font-weight: 800; font-size: 14px; border-radius: 12px; padding: 11px; }
  .btn-anuncio-sec { background: none; border: none; color: var(--fg-dim); font: inherit; font-size: 13px; cursor: pointer; padding: 6px; }
  .btn-anuncio-sec:hover { color: var(--fg); }
  @keyframes aparecer-anuncio { from { opacity: 0; } to { opacity: 1; } }
  /* lista completa de quem bateu palmas (3.2.0.0) */
  .ver-palmas { background: none; border: none; padding: 0; font: inherit; color: inherit; cursor: pointer; text-align: left; display: inline !important; }
  .ver-palmas:hover { color: var(--fg); text-decoration: underline; text-underline-offset: 3px; }
  .fundo-palmas { position: fixed; inset: 0; z-index: 400; background: rgba(0,0,0,.55); display: flex; align-items: center; justify-content: center; padding: 16px; }
  .cartao-palmas { box-sizing: border-box; width: min(380px, 100%); max-height: min(560px, 90vh); display: flex; flex-direction: column; background: var(--bg-panel-solid, var(--bg-panel));
                   border: 1px solid var(--border); border-radius: 16px; padding: 16px; box-shadow: 0 20px 60px rgba(0,0,0,.45); }
  .topo-palmas-mod { display: flex; align-items: center; justify-content: space-between; gap: 10px; font-size: 15px; }
  .fechar-palmas { background: none; border: none; color: var(--fg-dim); font-size: 15px; cursor: pointer; padding: 4px 6px; border-radius: 8px; }
  .fechar-palmas:hover { color: var(--fg); background: rgba(var(--tinta), .06); }
  .sub-palmas { font-size: 12px; color: var(--fg-dim); margin: 4px 0 10px; }
  .lista-palmas-mod { overflow-y: auto; margin: 0 -6px; padding: 0 6px; }
  .evento.aniversario-hoje { border-color: rgba(242,183,5,.55);
                             background: radial-gradient(circle at 92% 0%, rgba(242,183,5,.16), transparent 55%), var(--bg-panel); }
  .evento.aniversario-hoje .quando-ev { color: #f2b705; font-weight: 700; }
  .evento.aniversario-hoje .confete { font-size: 30px; align-self: center; animation: balancar 2.4s ease-in-out infinite; }
  @keyframes balancar { 50% { transform: rotate(-10deg) scale(1.08); } }
  /* feed em lotes (3.3.8.0): o resto entra ao chegar no fim da página ou no botão */
  /* voltar ao topo (3.3.8.3): aparece depois de rolar mais que uma tela e meia */
  /* 3.3.9.1: pílula com seta e texto; display/padding/margem explícitos porque o estilo global de button deslocava a seta */
  .voltar-topo { position: fixed; right: 24px; bottom: 24px; z-index: 60; box-sizing: border-box; height: 42px; margin: 0; padding: 0 16px 0 13px;
                 border-radius: 99px; border: 1px solid var(--border-forte); background: var(--bg-panel-solid, #181f27); color: var(--teal);
                 font: inherit; font-size: 13px; font-weight: 700; line-height: 1; white-space: nowrap; cursor: pointer;
                 display: inline-flex !important; align-items: center; justify-content: center; gap: 7px;
                 box-shadow: 0 10px 28px rgba(0,0,0,.35); opacity: 0; transform: translateY(12px); transition: opacity .2s, transform .2s, border-color .2s; }
  .voltar-topo[hidden] { display: none !important; }
  .voltar-topo.visivel { opacity: 1; transform: none; }
  .voltar-topo:hover { border-color: var(--teal); }
  .voltar-topo svg { width: 18px; height: 18px; flex: none; display: block; }
  @media (max-width: 640px) { .voltar-topo { right: 14px; bottom: 14px; height: 40px; padding: 0 14px 0 11px; font-size: 12.5px; } }
  /* marco de acessos do PDA (3.4.5.0): dourado, com o número grande e confete */
  .evento.marco-ev { border-color: rgba(242,183,5,.55); position: relative; overflow: hidden;
                     background: radial-gradient(circle at 100% 0%, rgba(242,183,5,.22), transparent 50%), radial-gradient(circle at 0% 100%, rgba(45,184,207,.12), transparent 45%), var(--bg-panel); }
  .evento.marco-ev::before { content: "🎉 ✨ 🎊"; position: absolute; right: 120px; top: 8px; font-size: 14px; letter-spacing: 6px; opacity: .55; pointer-events: none; }
  .evento.marco-ev .titulo-ev { font-size: 17px; }
  .numero-marco { display: flex; flex-direction: column; align-items: center; justify-content: center; min-width: 74px; padding: 8px 10px; border-radius: 16px;
                  font-size: 28px; font-weight: 900; line-height: 1; color: #1a1205; background: linear-gradient(135deg, #ffd34d, #f2b705 55%, #fb923c);
                  box-shadow: 0 8px 24px rgba(242,183,5,.35); animation: brilho-marco 2.6s ease-in-out infinite; }
  .numero-marco small { font-size: 9.5px; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; margin-top: 4px; }
  @keyframes brilho-marco { 0%, 100% { transform: rotate(-3deg) scale(1); } 50% { transform: rotate(3deg) scale(1.05); } }
  @media (prefers-reduced-motion: reduce) { .numero-marco { animation: none; } }
  .mais-feed { display: flex; justify-content: center; padding: 6px 0 2px; }
  .mais-feed button { font: inherit; font-size: 13px; font-weight: 700; color: var(--fg); background: var(--bg-panel); border: 1px solid var(--border);
                      border-radius: 99px; padding: 9px 18px; cursor: pointer; }
  .mais-feed button:hover { border-color: var(--teal); color: var(--teal); }
  .fim-feed { text-align: center; font-size: 12px; color: var(--fg-dim); padding: 4px 0 2px; }
  /* comentários (3.3.8.0): só os mais recentes que cabem no espaço; o resto num clique */
  .ver-mais-com { align-self: flex-start; background: none; border: none; padding: 2px 0 2px 37px; font: inherit; font-size: 12px; font-weight: 700;
                  color: var(--fg-dim); cursor: pointer; }
  .ver-mais-com:hover { color: var(--teal); }
  .feed-vazio { background: var(--bg-panel); border: 1px dashed var(--border); border-radius: 16px; padding: 30px; text-align: center; color: var(--fg-dim); font-size: 13px; line-height: 1.6; }

  /* coluna da direita */
  .lado-inicio { display: flex; flex-direction: column; gap: 14px; position: sticky; top: 18px; }

  /* busca de cards (3.0.8.0; no cabeçalho desde a 3.1.0.0): acha qualquer card do painel sem precisar ir até a seção */
  .busca-global { position: relative; z-index: 60; flex: 1; max-width: 560px; margin: 0 24px; min-width: 0; }
  .busca-global .campo-busca { display: flex; align-items: center; gap: 10px; background: rgba(var(--poco), .25); border: 1px solid var(--border);
                               border-radius: 12px; padding: 0 12px; transition: border-color .15s, box-shadow .15s; }
  .busca-global .campo-busca:focus-within { border-color: var(--teal); box-shadow: 0 0 0 3px rgba(45,184,207,.15); }
  .busca-global svg { width: 18px; height: 18px; stroke: var(--fg-dim); flex-shrink: 0; }
  .busca-global input { flex: 1; min-width: 0; background: none; border: none; color: var(--fg); font: inherit; font-size: 13.5px; padding: 9px 0; outline: none; }
  @media (max-width: 860px) { .busca-global { margin: 0 10px; } .busca-global kbd { display: none; } }
  @media (max-width: 600px) { .busca-global input::placeholder { color: transparent; } }
  .busca-global kbd { font-family: inherit; font-size: 11px; color: var(--fg-dim); border: 1px solid var(--border); border-radius: 6px; padding: 1px 6px; }
  .resultados-busca { position: absolute; left: 0; right: 0; top: calc(100% + 6px); background: var(--bg-panel-solid); border: 1px solid var(--border-forte);
                      border-radius: 14px; box-shadow: 0 18px 40px rgba(0,0,0,.45); max-height: 420px; overflow-y: auto; display: none; padding: 6px; }
  .resultados-busca.aberto { display: block; }
  .resultado-busca { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 10px; text-decoration: none; color: var(--fg); cursor: pointer; }
  .resultado-busca:hover, .resultado-busca.ativo { background: rgba(var(--tinta), .07); }
  .resultado-busca .ic-res { width: 34px; height: 34px; border-radius: 10px; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
  .resultado-busca .ic-res svg { width: 18px; height: 18px; stroke: var(--cor-res, var(--teal)); }
  .resultado-busca .tit-res { font-size: 13.5px; font-weight: 700; }
  .resultado-busca .desc-res { font-size: 11.5px; color: var(--fg-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .resultado-busca .sec-res { margin-left: auto; font-size: 10.5px; font-weight: 700; color: var(--fg-dim); background: rgba(var(--tinta), .06);
                              border-radius: 99px; padding: 2px 8px; white-space: nowrap; }
  .resultado-busca > div { min-width: 0; }
  .nada-busca { padding: 16px; text-align: center; color: var(--fg-dim); font-size: 13px; }

  /* Changelog e Sobre na lateral (3.0.8.0): o rodapé fica longe com o mural comprido */
  .bloco-pda .linha-pda { display: flex; align-items: center; gap: 10px; padding: 9px 6px; border-radius: 10px; text-decoration: none; color: var(--fg); font-size: 13px; font-weight: 600; }
  .bloco-pda .linha-pda:hover { background: rgba(var(--tinta), .05); }
  .bloco-pda .linha-pda .ic { width: 30px; height: 30px; border-radius: 9px; display: flex; align-items: center; justify-content: center; background: rgba(var(--tinta), .06); }
  .bloco-pda .linha-pda .seta { margin-left: auto; color: var(--fg-dim); }
  .bloco-pda .versao-pda { font-size: 11px; font-weight: 800; color: #071016; background: var(--gradiente-marca); border-radius: 99px; padding: 1px 8px; margin-left: 6px; text-transform: none; letter-spacing: 0; }

  /* o perfil já fica no cartão da lateral: no início, o atalho do topo sai (no celular a lateral some, então ele volta) */
  @media (min-width: 861px) { .usuario-area-navbar { display: none; } }
  .bloco-lado { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 14px 14px 10px; }
  .pessoa-linha { display: flex; align-items: center; gap: 10px; padding: 7px 4px; border-radius: 10px; text-decoration: none; color: inherit; }
  .avatar-mural, a .avatar-mural { text-decoration: none; }
  .pessoa-linha:hover { background: rgba(var(--tinta), .05); }
  .pessoa-linha .avatar-mural { width: 34px; height: 34px; font-size: 12.5px; }
  .pessoa-linha .nome { font-size: 13px; font-weight: 600; line-height: 1.25; }
  .pessoa-linha .sub { font-size: 11.5px; color: var(--fg-dim); }
  .pessoa-linha .fim { margin-left: auto; font-size: 11.5px; font-weight: 700; color: var(--fg-dim); white-space: nowrap; display: flex; align-items: center; gap: 6px; }
  .pessoa-linha .fim.hoje { color: #f2b705; }
  .pessoa-linha .fim svg { width: 26px; height: 26px; }
  .bloco-lado .vazio { font-size: 12px; color: var(--fg-dim); padding: 4px 4px 8px; }
  .bloco-campanha { background: linear-gradient(135deg, rgba(45,184,207,.2), rgba(176,203,28,.14)); border: 1px solid rgba(45,184,207,.4);
                    border-radius: 16px; padding: 16px; display: flex; gap: 12px; align-items: center; }
  .bloco-campanha svg { width: 54px; height: 54px; flex-shrink: 0; }
  .bloco-campanha b { font-size: 13.5px; display: block; }
  .bloco-campanha span { font-size: 12px; color: var(--fg-dim); display: block; margin: 3px 0 8px; line-height: 1.45; }
  /* campanha concluída (3.0.1.0): fica na tela até o fim da campanha, com o selo por cima */
  .bloco-campanha { position: relative; overflow: hidden; }
  .bloco-campanha.concluida > *:not(.selo-concluida) { opacity: .35; filter: grayscale(.5); }
  .selo-concluida { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
                    background: rgba(var(--poco), .35); backdrop-filter: blur(1.5px); -webkit-backdrop-filter: blur(1.5px); text-align: center; }
  .selo-concluida b { font-size: 14px; color: var(--lime); letter-spacing: .02em; }
  .selo-concluida span { font-size: 11.5px !important; color: var(--fg) !important; margin: 0 !important; }
  .selo-concluida .check { width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
                           background: var(--lime); color: #0b0f14; font-weight: 900; font-size: 18px; margin-bottom: 4px;
                           box-shadow: 0 0 0 5px rgba(176,203,28,.2); }
  .campanhas-lado { display: flex; flex-direction: column; gap: 8px; }
  .bloco-campanha .prazo-camp { display: inline; font-size: 11.5px; color: var(--lime); font-weight: 800; white-space: nowrap; }
  .campanhas-lado:empty { display: none; }
  /* várias campanhas (3.0.2.0): uma por vez, trocando sozinha, com pontinhos */
  .trilho-camp { overflow: hidden; border-radius: 16px; }
  .faixa-camp { display: flex; transition: transform .45s cubic-bezier(.4,0,.2,1); }
  .faixa-camp > .bloco-campanha { flex: 0 0 100%; min-width: 100%; box-sizing: border-box; }
  .pontos-camp { display: flex; justify-content: center; gap: 7px; }
  .pontos-camp button { width: 7px; height: 7px; padding: 0; border-radius: 50%; border: none; background: rgba(var(--tinta), .2); cursor: pointer; }
  .pontos-camp button.ativo { background: var(--teal); transform: scale(1.3); }
  /* sem campanha (ou todas concluídas): o aviso de que vem campanha nova */
  .bloco-campanha.em-breve { background: repeating-linear-gradient(135deg, rgba(var(--tinta), .03) 0 10px, transparent 10px 20px), var(--bg-panel);
                             border: 1px dashed rgba(var(--tinta), .25); }
  .bloco-campanha.em-breve .icone-em-breve { width: 54px; height: 54px; border-radius: 14px; flex-shrink: 0; display: flex; align-items: center;
                                             justify-content: center; font-size: 26px; background: rgba(var(--tinta), .06); }
  .bloco-campanha.em-breve b { color: var(--fg); }
  .bloco-campanha.em-breve .selo-breve { display: inline-block; font-size: 10px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase;
                                         color: var(--run); margin-top: 2px; }
  /* filtro de equipe da Gestão (3.0.2.0) */
  .filtro-equipe { display: inline-flex; gap: 4px; padding: 4px; border-radius: 99px; background: rgba(var(--tinta), .05); border: 1px solid var(--border); }
  .filtro-equipe button { border: none; background: none; color: var(--fg-dim); font: inherit; font-size: 12.5px; font-weight: 700;
                          padding: 7px 14px; border-radius: 99px; cursor: pointer; }
  .filtro-equipe button:hover { color: var(--fg); }
  .filtro-equipe button.ativo { background: var(--teal); color: #071016; }
  .promo-linha .sub b { color: var(--lime); font-weight: 700; }
  .bloco-campanha button { border: none; background: var(--teal); color: #071016; font: inherit; font-weight: 800; font-size: 12px;
                           border-radius: 9px; padding: 7px 12px; cursor: pointer; }

  /* avatar (foto ou iniciais) */
  .avatar-mural { border-radius: 50%; object-fit: cover; display: flex; align-items: center; justify-content: center;
                  color: #fff; font-weight: 800; flex-shrink: 0; background: var(--cor-av, #2db8cf); }

  /* gestão */
  .fora-hoje { display: flex; gap: 8px; flex-wrap: wrap; margin: -8px 0 24px; align-items: center; }
  .fora-hoje .rot { font-size: 12px; color: var(--fg-dim); font-weight: 700; margin-right: 4px; }
  .chip-pessoa { display: inline-flex; align-items: center; gap: 7px; padding: 4px 10px 4px 4px; border-radius: 99px;
                 background: rgba(var(--tinta), .05); border: 1px solid var(--border); font-size: 12px; text-decoration: none; color: var(--fg); }
  .chip-pessoa .avatar-mural { width: 24px; height: 24px; font-size: 10px; }
  .titulo-grade { font-size: 13px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); margin: 0 0 14px; font-weight: 700; }

  /* ---------- cards (os mesmos de antes) ---------- */
  .grade-hub { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 18px; }
  .card-hub {
    background: var(--bg-panel); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border); border-radius: 16px;
    padding: 22px 22px; cursor: pointer; text-decoration: none; color: inherit; display: block;
    position: relative; transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
  }
  .card-hub:hover { transform: translateY(-4px); border-color: var(--accent-card, var(--teal));
                    box-shadow: 0 18px 40px rgba(0,0,0,.35), 0 0 26px -10px var(--accent-card, var(--teal)); }
  .card-hub .icone { width: 48px; height: 48px; border-radius: 13px; display: flex; align-items: center;
                      justify-content: center; margin-bottom: 15px; box-shadow: inset 0 0 0 1px rgba(var(--tinta),.05); }
  .card-hub .icone svg { width: 24px; height: 24px; stroke: var(--accent-card, var(--accent)); }
  .card-hub h2 { font-size: 15px; margin: 0 0 6px 0; }
  .card-hub p { font-size: 12px; color: var(--fg-dim); margin: 0; line-height: 1.55; }
  .card-hub .tag-em-breve { display: inline-block; margin-top: 12px; font-size: 10px; font-weight: 700;
              letter-spacing: .04em; text-transform: uppercase; color: var(--run); }
  .card-hub .credito-card { display: inline-block; margin-top: 10px; font-size: 10.5px; color: var(--fg-dim); font-style: italic; }
  .card-hub .autor-card { display: inline-flex; align-items: center; gap: 6px; cursor: pointer; border-radius: 999px; padding: 2px 8px 2px 2px;
                          border: 1px solid var(--border); font-style: normal; transition: border-color .15s, color .15s; }
  .card-hub .autor-card:hover { border-color: var(--teal); color: var(--fg); }
  .card-hub .autor-card img { width: 20px; height: 20px; border-radius: 50%; object-fit: cover; }
  .card-hub.bloqueado { cursor: default; opacity: .55; filter: grayscale(.4); }
  .card-hub.bloqueado:hover { transform: none; border-color: var(--border); box-shadow: none; }
  .card-hub.bloqueado .icone svg { stroke: var(--fg-dim); }
  .card-hub.escondido-busca { display: none; }
  .card-hub .tag-live { display: inline-flex; align-items: center; gap: 6px; margin-top: 12px;
              font-size: 10px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
  .tag-live .ponto { width: 7px; height: 7px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
  .tag-live.ok { color: var(--ok); }
  .tag-live.ok .ponto { background: var(--ok); box-shadow: 0 0 6px var(--ok); }
  .tag-live.alerta { color: #ff8080; }
  .tag-live.alerta .ponto { background: #f14c4c; box-shadow: 0 0 8px #f14c4c; animation: pulso-ponto 1.4s infinite; }
  .tag-live.agendada { color: var(--run); }
  .tag-live.agendada .ponto { background: var(--run); box-shadow: 0 0 6px var(--run); }
  .tag-live.desconhecido { color: var(--fg-dim); }
  .tag-live.desconhecido .ponto { background: var(--fg-dim); }
  @keyframes pulso-ponto { 0%, 100% { opacity: 1; } 50% { opacity: .3; } }
  .estrela-hub { position: absolute; top: 12px; right: 12px; width: 30px; height: 30px; border-radius: 50%;
                 display: flex; align-items: center; justify-content: center; cursor: pointer;
                 color: var(--fg-dim); opacity: 0; transition: opacity .15s, color .15s, background .15s, transform .15s; }
  .estrela-hub svg { width: 17px; height: 17px; }
  .estrela-hub:hover { background: rgba(var(--tinta),.08); color: #f2b705; transform: scale(1.1); }
  .estrela-hub:focus-visible { outline: 2px solid var(--teal); opacity: 1; }
  .card-hub:hover .estrela-hub, .card-hub:focus-within .estrela-hub { opacity: .75; }
  .card-hub.favorito .estrela-hub { opacity: 1; color: #f2b705; }
  .card-hub.favorito .estrela-hub svg { fill: #f2b705; }
  @media (hover: none) { .estrela-hub { opacity: .45; } }
  .sem-resultado { color: var(--fg-dim); font-size: 13px; padding: 20px 0; display: none; }

  /* ---------- telas menores ---------- */
  @media (max-width: 1180px) {
    .colunas-inicio { grid-template-columns: minmax(0, 1fr); }
    .lado-inicio { position: static; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); }
    .indicadores-mural { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  }
  @media (max-width: 860px) {
    .layout-mural { grid-template-columns: minmax(0, 1fr); gap: 16px; }
    .lateral-mural { position: static; }
    .cartao-eu, .favoritos-lateral { display: none; }
    .menu-mural { flex-direction: row; overflow-x: auto; }
    .item-menu { white-space: nowrap; width: auto; }
    .item-menu .sub-item { display: none; }
    .item-menu.ativo::before { left: 10px; right: 10px; top: auto; bottom: 2px; width: auto; height: 3px; }
    .busca-secao { width: 100%; }
    .conteudo.conteudo-mural { padding: 18px 14px; }
    main { min-width: 0; }
  }
  @media (max-width: 520px) {
    .indicadores-mural { grid-template-columns: minmax(0, 1fr); }
    .evento { grid-template-columns: 44px minmax(0, 1fr); }
    .evento .lado-dir { grid-column: 2; align-items: flex-start; flex-direction: row; }
  }
</style>
__LOJA_WALLPAPERS__
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-mural">
   <div class="layout-mural">
    <aside class="lateral-mural">
      <a class="cartao-eu" href="/perfil/__LOGIN_HERO__" title="Abrir meu perfil">
        <div class="foto-eu"><span id="avatar-eu"></span><span class="destaque-eu" id="destaque-eu"></span></div>
        <div class="nome-eu">__USUARIO_HERO__</div>
        <div class="cargo-eu" id="cargo-eu">&nbsp;</div>
        <span class="ver-perfil">Ver meu perfil</span>
      </a>
      <nav class="menu-mural" aria-label="Seções da Comunidade">
        <button class="item-menu ativo" data-secao="inicio" onclick="trocarSecao('inicio')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-5h4v5"/></svg>
          <span>Comunidade<span class="sub-item">Feed da equipe</span></span>
        </button>
        <a class="item-menu item-loja" href="/loja">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5 8h14l-1.2 11.2a2 2 0 0 1-2 1.8H8.2a2 2 0 0 1-2-1.8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>
          <span>Loja de Palminhas<span class="sub-item">Troque suas palminhas</span></span><span class="selo-novo-loja">Novo</span>
        </a>
        <button class="item-menu" data-secao="automacoes" onclick="trocarSecao('automacoes')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg>
          <span>Automações<span class="sub-item">Alertas e ferramentas</span></span><span class="qtd" id="qtd-automacoes"></span>
        </button>
        __ITEM_MENU_GESTAO__
        <button class="item-menu" data-secao="operacoes" onclick="trocarSecao('operacoes')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/><path d="M7 7h.01M7 17h.01M11 7h6M11 17h6"/></svg>
          <span>Operações/Serviços<span class="sub-item">GMUDs, máquinas e versões</span></span><span class="qtd" id="qtd-operacoes"></span>
        </button>
        <button class="item-menu" data-secao="outros" onclick="trocarSecao('outros')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>
          <span>Outros<span class="sub-item">Monitores, férias, plantão e mais</span></span><span class="qtd" id="qtd-outros"></span>
        </button>
        <button class="item-menu" data-secao="embreve" onclick="trocarSecao('embreve')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.6 2.6-2.4-.6-.6-2.4z"/></svg>
          <span>Em breve<span class="sub-item">Em construção e beta</span></span><span class="qtd" id="qtd-embreve"></span>
        </button>
      </nav>
      <div class="favoritos-lateral">
        <h3>Favoritos</h3>
        <div id="lista-favoritos"></div>
      </div>
    </aside>

    <main>
      <section class="secao-mural ativa" id="secao-inicio">
        <div class="topo-secao">
          <div>
            <h1>__SAUDACAO_HERO__, <a href="/perfil/__LOGIN_HERO__" class="link-nome-hero">__PRIMEIRO_NOME_HERO__</a></h1>
            <div class="sub" id="sub-inicio">O que está acontecendo na equipe</div>
          </div>
        </div>

        <div class="indicadores-mural">
          <div class="ind carregando" id="ind-horas" style="--cor-ind:#2db8cf">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>Horas no mês</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div><div class="barra"><span></span></div>
          </div>
          <div class="ind carregando" id="ind-tickets" style="--cor-ind:#e8a33d">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4z"/><path d="M14 7v10" stroke-dasharray="2 2"/></svg>Tickets com ação</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div>
          </div>
          <div class="ind" id="ind-casa" style="--cor-ind:#b0cb1c">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>Tempo de casa</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div><span class="ins-ind"></span>
          </div>
          <div class="ind" id="ind-palmas" style="--cor-ind:#f2b705">
            <div class="rotulo"><span style="font-size:14px">👏</span>Palminhas</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div>
          </div>
        </div>

        <div class="colunas-inicio">
          <div>
            <div class="cabeca-feed">
              <h2>Acontecendo na Empresa</h2>
              <div class="filtros-feed" id="filtros-feed">
                <button class="chip-feed ativo" data-tipo="">Tudo</button>
                <button class="chip-feed" data-tipo="aniversario">🎂 Aniversários</button>
                <button class="chip-feed" data-tipo="promocao">🚀 Promoções</button>
                <button class="chip-feed" data-tipo="insignia">🏅 Insígnias</button>
                <button class="chip-feed" data-tipo="chegada">👋 Chegadas</button>
                <button class="chip-feed" data-tipo="tempo">🎊 Tempo de casa</button>
                <button class="chip-feed" data-tipo="colab">🤝 Colaborações</button>
                <button class="chip-feed" data-tipo="ferias">🏖️ Férias</button>
                <button class="chip-feed" data-tipo="post">📝 Publicações</button>
              </div>
            </div>
            <!-- publicar na Comunidade (3.2.6.0): todo mundo desde a 3.4.6.0; o Importante só com admin ou a permissão pode_publicar_comunidade -->
            <div class="compor-post" id="compor-post" hidden>
              <div class="topo-compor"><span id="avatar-compor"></span>
                <textarea id="texto-post" maxlength="3000" rows="2" placeholder="Compartilhe algo com a equipe..."></textarea></div>
              <div class="previas-post" id="previas-post"></div>
              <!-- votação (3.3.0.0): a pergunta é o texto da publicação -->
              <div class="votacao-compor" id="votacao-compor" hidden>
                <div class="cab-votacao"><b>📊 Votação</b><span>a pergunta é o texto da publicação</span>
                  <button type="button" class="tirar-votacao" onclick="alternarVotacaoPost(false)" aria-label="Tirar a votação">×</button></div>
                <div id="opcoes-votacao"></div>
                <button type="button" class="btn-anexar" id="add-opcao-votacao" onclick="adicionarOpcaoVotacao()">+ Opção</button>
                <div class="config-votacao">
                  <label><input type="checkbox" id="votacao-multipla"> Permitir marcar mais de uma</label>
                  <label>Prazo <select id="votacao-prazo" onchange="alternarPrazoVotacao()">
                    <option value="">Sem prazo</option><option value="h1">1 hora</option><option value="h4">4 horas</option>
                    <option value="hoje">Até o fim do dia</option><option value="d1">1 dia</option><option value="d3">3 dias</option>
                    <option value="d7">7 dias</option><option value="data">Escolher data e hora...</option></select></label>
                  <input type="datetime-local" id="votacao-fim" hidden aria-label="Encerra em">
                </div>
              </div>
              <!-- publicação em grupo (3.4.1.0): todos aparecem como autores e recebem as palminhas -->
              <div class="grupo-compor" id="grupo-compor" hidden>
                <div class="cab-grupo"><b>👥 Publicar em grupo</b><span>quem você marcar aparece junto como autor e recebe as palminhas</span>
                  <button type="button" onclick="alternarGrupoPost(false)" aria-label="Tirar o grupo">×</button></div>
                <div class="atalhos-grupo">
                  <button type="button" onclick="marcarEquipeGrupo('Suporte')">+ Suporte</button>
                  <button type="button" onclick="marcarEquipeGrupo('Monitoramento')">+ Monitoramento</button>
                  <button type="button" onclick="marcarEquipeGrupo('Serviços')">+ Serviços</button>
                  <button type="button" onclick="limparGrupo()">Limpar</button>
                  <input type="search" id="busca-grupo" placeholder="Buscar pessoa..." oninput="desenharListaGrupo()">
                </div>
                <div class="lista-grupo" id="lista-grupo"></div>
                <div class="resumo-grupo" id="resumo-grupo"></div>
              </div>
              <div class="acoes-compor">
                <label class="btn-anexar" title="PNG, JPG, GIF ou WebP, até 5 MB cada">📷 Foto ou GIF
                  <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" multiple hidden onchange="adicionarArquivosPost(this, true)"></label>
                <label class="btn-anexar" title="MP4, WebM ou MOV, até 50 MB cada (até 2 por publicação)">🎬 Vídeo
                  <input type="file" accept="video/mp4,video/webm,video/quicktime" multiple hidden onchange="adicionarArquivosPost(this, 'video')"></label>
                <button type="button" class="btn-anexar" onclick="alternarVotacaoPost(true)" title="De 2 a 6 opções, com prazo opcional; os votos são públicos">📊 Votação</button>
                <button type="button" class="btn-anexar" id="btn-grupo-post" onclick="alternarGrupoPost(true)" title="Publicar junto com outras pessoas: todas recebem as palminhas">👥 Em grupo</button>
                <label class="btn-anexar" title="Qualquer arquivo, até 10 MB cada">📎 Arquivo
                  <input type="file" multiple hidden onchange="adicionarArquivosPost(this, false)"></label>
                <label class="publico-post" title="Quem vê a publicação">Para
                  <select id="publico-post"><option value="">🌐 Todos</option><option value="Suporte">Suporte</option>
                    <option value="Monitoramento">Monitoramento</option><option value="Serviços">Serviços</option></select></label>
                <label class="check-importante" title="Avisa no sininho quem vê a publicação e retransmite no Teams"><input type="checkbox" id="importante-post"> 📢 Importante <span>avisa no sininho e no Teams</span></label>
                <button type="button" class="btn-publicar" id="btn-publicar" onclick="publicarPost()">Publicar</button>
              </div>
            </div>
            <div class="aviso-votacoes" id="aviso-votacoes" hidden></div>
            <div class="feed" id="feed"><div class="feed-vazio">Carregando o mural...</div></div>
          </div>
          <aside class="lado-inicio">
            <div class="campanhas-lado" id="bloco-campanha"></div>
            <div class="bloco-lado"><h3>🎂 Aniversariantes</h3><div id="lista-aniversarios"></div></div>
            <div class="bloco-lado" id="bloco-ferias" hidden><h3>🏖️ De férias</h3><div id="lista-ferias"></div></div>
            <div class="bloco-lado"><h3>🚀 Promoções</h3><div id="lista-promocoes"></div></div>
            <div class="bloco-lado bloco-pda"><h3>📦 PDA <span class="versao-pda">v__VERSAO_HUB__</span></h3>
              <a class="linha-pda" href="/changelog"><span class="ic">📜</span>Changelog · o que mudou<span class="seta">→</span></a>
              <a class="linha-pda" href="/sobre"><span class="ic">ℹ️</span>Sobre o PDA<span class="seta">→</span></a>
            </div>
          </aside>
        </div>
      </section>

      <section class="secao-mural" id="secao-automacoes">
        <div class="topo-secao">
          <div><h1>Automações</h1><div class="sub">Alertas, monitoramentos e ferramentas do dia a dia. A estrela fixa o card no começo.</div></div>
          <input class="busca-secao" type="search" placeholder="Buscar automação..." oninput="filtrarCards('automacoes', this.value)">
        </div>
        <div class="grade-hub" data-grade="automacoes">
__CARDS_AUTOMACOES__
        </div>
        <div class="sem-resultado" id="sem-resultado-automacoes">Nenhuma automação com esse nome.</div>
      </section>
__SECAO_GESTAO__
      <section class="secao-mural" id="secao-operacoes">
        <div class="topo-secao">
          <div><h1>Operações/Serviços</h1><div class="sub">GMUDs, indicadores de Serviços, limpeza de máquinas e versões dos produtos.</div></div>
        </div>
        <div class="grade-hub" data-grade="operacoes">
__CARDS_OPERACOES__
        </div>
      </section>
      <section class="secao-mural" id="secao-outros">
        <div class="topo-secao">
          <div><h1>Outros</h1><div class="sub">Central de Monitores, férias, plantão e o que não é automação.</div></div>
        </div>
        <div class="grade-hub" data-grade="outros">
__CARDS_OUTROS__
        </div>
      </section>
      <section class="secao-mural" id="secao-embreve">
        <div class="topo-secao">
          <div><h1>Em breve</h1><div class="sub">O que está em construção e o que já dá pra testar em beta.</div></div>
        </div>
        <div class="grade-hub" data-grade="embreve">
__CARDS_EM_BREVE__
        </div>
      </section>
    </main>
   </div>
  </div>

  <button type="button" class="voltar-topo" id="voltar-topo" onclick="voltarAoTopo()" title="Voltar ao topo" hidden>
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19V5"/><path d="M5 12l7-7 7 7"/></svg>
    <span>Voltar ao topo</span>
  </button>
  __FOOTER__

  <div class="toast" id="toast"></div>
__INSIGNIAS__
<script>
const ADMIN_MURAL = __ADMIN_MURAL__;
let favoritosHub = __FAVORITOS_HUB__;
const SVG_ESTRELA_HUB = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round">'
  + '<path d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/></svg>';
const ordemOriginalHub = {};
document.querySelectorAll('[data-grade]').forEach(g => { ordemOriginalHub[g.dataset.grade] = Array.from(g.querySelectorAll('.card-hub')); });
const CORES_EVENTO = { aniversario: '#f2b705', promocao: '#b0cb1c', insignia: '#2db8cf', chegada: '#f472b6', colab: '#c084fc', tempo: '#fb923c', pda: '#2db8cf', saida: '#f14c4c', ferias: '#38bdf8', post: '#60a5fa', marco: '#f2b705' };
const ROTULOS_EVENTO = { aniversario: 'Aniversário', promocao: 'Promoção', insignia: 'Insígnia', chegada: 'Boas-vindas', colab: 'Colaboração',
                         tempo: 'Tempo de casa', pda: 'Aniversário do PDA', saida: 'Usuário desativado', ferias: 'Férias', post: 'Publicação', marco: 'Marco do PDA' };
const NOMES_MESES_MURAL = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const DIAS_SEMANA_MURAL = ['domingo', 'segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado'];
const MESES_LONGOS_MURAL = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
let muralAtual = null;
let filtroFeed = '';

function esc(t) {
  return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
}

// ---------------- seções ----------------
function trocarSecao(secao, semHash) {
  if (!document.getElementById('secao-' + secao)) secao = 'inicio';
  document.querySelectorAll('.secao-mural').forEach(s => s.classList.toggle('ativa', s.id === 'secao-' + secao));
  document.querySelectorAll('.item-menu').forEach(b => b.classList.toggle('ativo', b.dataset.secao === secao));
  if (!semHash) history.replaceState(null, '', secao === 'inicio' ? location.pathname : '#' + secao);
  if (secao === 'gestao') {
    carregarNumerosMovidesk();
    if (equipeGestao && !window._gestaoFiltrada) { window._gestaoFiltrada = true; filtrarGestao(equipeGestao); }
  }
}

function filtrarCards(grade, texto) {
  const termo = texto.trim().toLowerCase();
  let visiveis = 0;
  ordemOriginalHub[grade].forEach(c => {
    const bate = !termo || c.innerText.toLowerCase().includes(termo);
    c.classList.toggle('escondido-busca', !bate);
    if (bate) visiveis++;
  });
  const aviso = document.getElementById('sem-resultado-' + grade);
  if (aviso) aviso.style.display = visiveis ? 'none' : 'block';
}

// ---------------- favoritos (os mesmos de antes, agora em cada seção) ----------------
function montarGrades() {
  Object.entries(ordemOriginalHub).forEach(([grade, cards]) => {
    const el = document.querySelector('[data-grade="' + grade + '"]');
    const porHref = new Map(cards.map(c => [c.getAttribute('href'), c]));
    const favs = favoritosHub.map(h => porHref.get(h)).filter(Boolean);
    favs.concat(cards.filter(c => !favs.includes(c))).forEach(c => {
      c.classList.toggle('favorito', favs.includes(c));
      el.appendChild(c);
    });
    const qtd = document.getElementById('qtd-' + grade);
    // em "Em breve" conta tudo (lá quase todos são em construção); nas outras, só o que abre
    if (qtd) qtd.textContent = grade === 'embreve' ? cards.length : cards.filter(c => !c.classList.contains('bloqueado')).length;
  });
  document.querySelectorAll('.card-hub .estrela-hub').forEach(e => {
    const texto = e.parentElement.classList.contains('favorito') ? 'Tirar dos favoritos' : 'Favoritar (vai pro começo e pros atalhos)';
    e.title = texto;
    e.setAttribute('aria-label', texto);
  });
  const todos = [].concat(...Object.values(ordemOriginalHub));
  const porHref = new Map(todos.map(c => [c.getAttribute('href'), c]));
  const favs = favoritosHub.map(h => porHref.get(h)).filter(Boolean);
  document.getElementById('lista-favoritos').innerHTML = favs.length ? favs.map(c => {
    const cor = (c.getAttribute('style') || '').split('--accent-card:')[1] || '#2db8cf';
    const alvo = c.getAttribute('target') ? ' target="_blank" rel="noopener noreferrer"' : '';
    return '<a class="atalho" href="' + esc(c.getAttribute('href')) + '"' + alvo + '><span class="ponto-cor" style="background:' + esc(cor.trim()) + '"></span>'
      + esc(c.querySelector('h2').textContent) + '</a>';
  }).join('') : '<p class="vazio">Marque a estrela de um card pra ele aparecer aqui.</p>';
}

[].concat(...Object.values(ordemOriginalHub)).forEach(card => {
  if (card.classList.contains('bloqueado') || !card.getAttribute('href')) return;
  const estrela = document.createElement('span');
  estrela.className = 'estrela-hub';
  estrela.setAttribute('role', 'button');
  estrela.setAttribute('tabindex', '0');
  estrela.innerHTML = SVG_ESTRELA_HUB;
  const alternar = ev => { ev.preventDefault(); ev.stopPropagation(); alternarFavoritoHub(card); };
  estrela.addEventListener('click', alternar);
  estrela.addEventListener('keydown', ev => { if (ev.key === 'Enter' || ev.key === ' ') alternar(ev); });
  card.appendChild(estrela);
});

async function alternarFavoritoHub(card) {
  const href = card.getAttribute('href');
  const anteriores = favoritosHub.slice();
  favoritosHub = favoritosHub.includes(href) ? favoritosHub.filter(h => h !== href) : favoritosHub.concat([href]);
  montarGrades();
  try {
    const resp = await fetch('/api/hub/favoritos', {
      method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
      body: 'cards=' + encodeURIComponent(JSON.stringify(favoritosHub)),
    });
    if (resp.status === 401) { window.location.href = '/login'; return; }
    const dados = await resp.json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
  } catch (e) {
    favoritosHub = anteriores;
    montarGrades();
    mostrarToastHub('Não foi possível salvar os favoritos. Tente de novo.');
  }
}

function mostrarToastHub(texto) {
  const toast = document.getElementById('toast');
  toast.innerText = texto;
  toast.classList.add('mostrar');
  clearTimeout(window._toastTimer);
  window._toastTimer = setTimeout(() => toast.classList.remove('mostrar'), 3500);
}

function abrirEmConstrucao(ev, nome) {
  ev.preventDefault();
  mostrarToastHub(nome + ' está em construção e ainda não está disponível.');
  return false;
}

// ---------------- mural ----------------
function corDoNome(nome) {
  const cores = ['#2db8cf', '#7c9a12', '#c084fc', '#f97316', '#e85d75', '#3b82f6', '#14b8a6', '#d4a017'];
  let h = 0;
  for (const c of String(nome)) h = (h * 31 + c.charCodeAt(0)) % 997;
  return cores[h % cores.length];
}

function iniciais(nome) {
  const partes = String(nome || '?').trim().split(' ').filter(Boolean);
  return ((partes[0] || '?')[0] + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
}

function avatarMural(p) {
  if (p.tem_foto) return '<img class="avatar-mural" src="/foto-usuario/' + encodeURIComponent(p.login) + '" alt="" loading="lazy" decoding="async">';
  return '<span class="avatar-mural" style="--cor-av:' + corDoNome(p.nome) + '">' + esc(iniciais(p.nome)) + '</span>';
}

function quandoTexto(iso, quando) {
  // evento com hora de verdade e de hoje (3.2.4.0): "há 5 min", "há 2 h"
  if (quando && quando.slice(11) !== '00:00:00' && quando.slice(0, 10) === muralAtual.hoje) {
    const min = Math.round((Date.now() - new Date(quando)) / 60000);
    if (min >= 0 && min < 1) return 'agora';
    if (min >= 0 && min < 60) return 'há ' + min + ' min';
    if (min >= 0) return 'há ' + Math.round(min / 60) + ' h';
  }
  const hoje = new Date(muralAtual.hoje + 'T12:00:00');
  const dia = new Date(iso + 'T12:00:00');
  const dias = Math.round((hoje - dia) / 86400000);
  if (dias <= 0) return 'hoje';
  if (dias === 1) return 'ontem';
  if (dias < 7) return 'há ' + dias + ' dias';
  return dia.getDate() + ' ' + NOMES_MESES_MURAL[dia.getMonth()];
}

function textoQuemBateu(ev) {
  if (!ev.palmas) return ev.meu ? 'Ninguém bateu palmas ainda' : 'Seja o primeiro a bater palmas';
  const nomes = ev.quem.slice();
  const resto = ev.palmas - nomes.length;
  const partes = nomes.map((n, i) => '<b>' + esc(i === 0 && n === 'você' ? 'Você' : n) + '</b>');
  if (resto > 0) partes.push('mais ' + resto);
  const lista = partes.length > 1 ? partes.slice(0, -1).join(', ') + ' e ' + partes[partes.length - 1] : partes[0];
  // clicável (3.2.0.0): abre a lista de todo mundo que bateu
  return '<button type="button" class="ver-palmas" onclick="verQuemBateu(this)" title="Ver todo mundo que bateu palmas">'
    + lista + (ev.palmas === 1 ? ' bateu palmas' : ' bateram palmas') + '</button>';
}

function verQuemBateu(botao) {
  const ev = muralAtual.eventos.find(e => e.id === botao.closest('.evento').dataset.id);
  if (!ev) return;
  const todos = ev.quem_todos || [];
  document.querySelectorAll('.fundo-palmas').forEach(f => f.remove());
  const fundo = document.createElement('div');
  fundo.className = 'fundo-palmas';
  fundo.onclick = e => { if (e.target === fundo) fundo.remove(); };
  fundo.innerHTML = '<div class="cartao-palmas" role="dialog" aria-modal="true" aria-label="Quem bateu palmas">'
    + '<div class="topo-palmas-mod"><b>👏 ' + todos.length + (todos.length === 1 ? ' pessoa bateu palmas' : ' pessoas bateram palmas') + '</b>'
    + '<button type="button" class="fechar-palmas" onclick="fecharQuemBateu()" aria-label="Fechar">✕</button></div>'
    + '<div class="sub-palmas">' + esc(ev.titulo) + '</div>'
    + '<div class="lista-palmas-mod">' + todos.map(p => '<a class="pessoa-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
      + '<div><div class="nome">' + esc(p.eu ? p.nome + ' (você)' : p.nome) + '</div><div class="sub">' + esc(p.equipe) + '</div></div></a>').join('') + '</div></div>';
  document.body.appendChild(fundo);
}
function fecharQuemBateu() { document.querySelectorAll('.fundo-palmas').forEach(f => f.remove()); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharQuemBateu(); });

function linkPerfil(login, conteudo) {
  return '<a href="/perfil/' + encodeURIComponent(login) + '">' + conteudo + '</a>';
}

// clicar na foto abre ela grande (3.0.4.0), com o "Ver perfil"; o resto do evento continua levando ao perfil
const pessoasMural = {};
function linkFoto(p, conteudo) {
  pessoasMural[p.login] = Object.assign({}, pessoasMural[p.login] || {}, p);
  return '<a href="/perfil/' + encodeURIComponent(p.login) + '" onclick="event.preventDefault(); abrirFotoPessoa(pessoasMural[' + "'" + esc(p.login) + "'" + '])">' + conteudo + '</a>';
}

// foto(s) do evento: uma pessoa com a insígnia em destaque dela junto; colaboração com as fotos juntas
function htmlFotoEvento(ev) {
  const pessoas = ev.pessoas && ev.pessoas.length ? ev.pessoas : [ev.pessoa];
  if (pessoas.length > 1) {
    return '<div class="lado-foto colab">' + pessoas.slice(0, 2).map(p => linkFoto(p, avatarMural(p))).join('')
      + (pessoas.length > 2 ? '<span class="mais-colab">+' + (pessoas.length - 2) + '</span>' : '') + '</div>';
  }
  const p = pessoas[0];
  pessoasMural[p.login] = Object.assign({}, pessoasMural[p.login] || {}, p);
  return '<a class="lado-foto" href="/perfil/' + encodeURIComponent(p.login) + '" onclick="event.preventDefault(); abrirFotoPessoa(pessoasMural['
    + "'" + esc(p.login) + "'" + '])">' + avatarMural(p)
    + (p.destaque ? '<span class="ins-foto" title="' + esc(p.destaque.nome || '') + '">' + svgInsignia(p.destaque, 28, false) + '</span>' : '') + '</a>';
}

function quandoComentario(texto) {
  const d = new Date((texto || '').replace(' ', 'T'));
  const min = Math.round((Date.now() - d) / 60000);
  if (isNaN(min)) return '';
  if (min < 1) return 'agora';
  if (min < 60) return 'há ' + min + ' min';
  if (min < 1440) return 'há ' + Math.round(min / 60) + ' h';
  return d.getDate() + ' ' + NOMES_MESES_MURAL[d.getMonth()];
}

// Quanto espaço cada comentário ocupa (3.3.8.0): texto curto 1, texto longo até 3, foto/GIF +3. Fechado, o evento mostra
// só os mais recentes que cabem em ESPACO_COMENTARIOS (sempre pelo menos 1) e um "Ver N comentários anteriores".
const ESPACO_COMENTARIOS = 6;
const comentariosAbertos = new Set();
function espacoComentario(c) {
  return Math.min(3, 1 + Math.floor(String(c.texto || '').length / 160)) + (c.imagem ? 3 : 0);
}
function htmlComentarios(ev) {
  const todos = ev.comentarios || [];
  let inicio = 0;
  if (!comentariosAbertos.has(ev.id)) {
    let usado = 0;
    inicio = todos.length;
    while (inicio > 0) {
      const espaco = espacoComentario(todos[inicio - 1]);
      if (inicio < todos.length && usado + espaco > ESPACO_COMENTARIOS) break;
      usado += espaco;
      inicio--;
    }
  }
  const escondidos = inicio;
  return (escondidos ? '<button type="button" class="ver-mais-com" onclick="abrirTodosComentarios(this)">Ver '
      + (escondidos === 1 ? '1 comentário anterior' : escondidos + ' comentários anteriores') + '</button>' : '')
    + todos.slice(inicio).map(c => '<div class="comentario">' + linkFoto(c, avatarMural(c))
    + '<div><div class="balao-com"><b>' + linkPerfil(c.login, esc(c.nome)) + '</b>' + esc(c.texto)
    + (c.imagem ? '<button type="button" class="img-com" onclick="ampliarImagemComentario(this)" aria-label="Ampliar a imagem"><img src="' + esc(c.imagem) + '" alt="Imagem do comentário" loading="lazy"></button>' : '') + '</div>'
    + '<div class="meta-com">' + quandoComentario(c.criado_em)
    + (c.pode_apagar ? '<button onclick="apagarComentario(this, ' + "'" + esc(c.id) + "'" + ')">apagar</button>' : '') + '</div></div></div>').join('');
}

function htmlEvento(ev, i) {
  const p = ev.pessoa;
  const pessoas = ev.pessoas && ev.pessoas.length ? ev.pessoas : [p];
  const titulo = pessoas.length > 1
    ? (ev.tipo === 'post' ? '<button type="button" class="link-grupo" onclick="verGrupoPost(this)" title="Ver quem publicou">' + esc(ev.titulo) + ' 👥</button>' : esc(ev.titulo))
    : linkPerfil(p.login, esc(ev.titulo));
  let extra = '';
  if (ev.tipo === 'promocao') extra = '<div class="degraus"><span>' + esc(ev.de) + '</span><i>→</i><span class="novo">' + esc(ev.para) + '</span></div>';
  if (ev.link) extra += '<a class="link-ev" href="' + esc(ev.link.href) + '">' + esc(ev.link.texto) + ' →</a>';
  if (ev.tipo === 'post') extra += htmlArquivosPost(ev) + htmlVotacaoPost(ev);
  const ins = ev.insignia ? '<span class="ins-ev">' + svgInsignia(ev.insignia, 62, false) + '</span>'
    : (ev.tipo === 'aniversario' && ev.hoje ? '<span class="confete">🎉</span>'
      : (ev.tipo === 'colab' ? '<span class="confete">🤝</span>' : (ev.tipo === 'pda' ? '<span class="confete">🎂</span>'
      : (ev.tipo === 'ferias' ? '<span class="confete onda-ferias">' + (ev.fase === 'volta' ? '🌴' : '🏖️') + '</span>'
      : (ev.tipo === 'marco' ? '<span class="numero-marco">' + (ev.numero >= 1000 ? (ev.numero / 1000) + 'K' : ev.numero) + '<small>acessos</small></span>' : '')))));
  const qtdCom = (ev.comentarios || []).length;
  const fixado = (ev.fixado ? '<span class="selo-fixado">📌 Fixado</span>' : '') + (ev.importante ? '<span class="selo-importante">📢 Importante</span>' : '')
    + (ev.publico ? '<span class="selo-publico" title="Só a equipe ' + esc(ev.publico) + ' (e quem publicou) vê">👥 ' + esc(ev.publico) + '</span>' : '');
  const comentavel = ev.comentavel !== false;  // feedback/alinhamento: sem comentário (3.0.3.0) e sem palminhas (3.0.4.0)
  const interativo = ev.interativo !== false;
  return '<article class="evento' + (ev.tipo === 'aniversario' && ev.hoje ? ' aniversario-hoje' : '') + (ev.tipo === 'colab' ? ' colab-ev' : '')
    + (ev.tipo === 'tempo' && ev.hoje ? ' tempo-hoje' : '') + (ev.tipo === 'pda' ? ' pda-ev' : '') + (ev.tipo === 'saida' ? ' saida-ev' : '') + (ev.tipo === 'ferias' ? ' ferias-ev ferias-' + (ev.fase || 'ida') : '')
    + (ev.tipo === 'post' ? ' post-ev' + (ev.importante ? ' post-importante' : '') : '') + (ev.tipo === 'marco' ? ' marco-ev' : '')
    + '" style="--cor-ev:' + CORES_EVENTO[ev.tipo] + ';animation-delay:' + Math.min(i * 0.05, 0.4) + 's" data-id="' + esc(ev.id) + '">'
    + htmlFotoEvento(ev)
    + '<div><div class="tipo-ev">' + ROTULOS_EVENTO[ev.tipo] + fixado + '</div><div class="titulo-ev">' + titulo + '</div>'
    + (ev.detalhe ? '<div class="detalhe-ev' + (ev.tipo === 'post' ? ' texto-post' : '') + '">' + esc(ev.detalhe) + '</div>' : '') + extra + '</div>'
    + '<div class="lado-dir"><span class="quando-ev">' + quandoTexto(ev.data, ev.quando) + '</span>' + ins
    + (ev.pode_reenviar_teams ? '<button class="apagar-post reenviar-teams" onclick="reenviarTeams(this)" title="Manda o aviso de novo no canal do Teams (palminhas e comentários continuam)">📢 Reenviar ao Teams</button>' : '')
    + (ev.pode_apagar ? '<button class="apagar-post" onclick="apagarPost(this)" title="Apagar a publicação">Apagar</button>' : '') + '</div>'
    + (!interativo ? '' : '<div class="rodape-ev"><button class="btn-palma' + (ev.bati ? ' bati' : '') + '"' + (ev.meu ? ' disabled title="As palminhas são dos colegas"' : '')
    + ' onclick="baterPalma(this)"><span class="mao">👏</span><span class="n">' + (ev.palmas || '') + '</span>Palminhas</button>'
    + (comentavel ? '<button class="btn-comentar" onclick="abrirCaixaComentario(this)">💬 <span class="n-com">' + (qtdCom || '') + '</span> Comentar</button>' : '')
    + '<span class="quem-bateu">' + textoQuemBateu(ev) + '</span></div>')
    + (comentavel ? '<div class="comentarios-ev">' + htmlComentarios(ev) + '</div>'
      + '<div class="caixa-com" style="grid-column:1/-1">' + avatarMural(muralAtual.eu)
      + '<div class="campo-com"><input type="text" maxlength="500" placeholder="Escreva um comentário..." onkeydown="if (event.key === ' + "'Enter'" + ') enviarComentario(this)">'
      + '<button type="button" class="btn-extra-com" onclick="abrirEmojis(this)" title="Emoji" aria-label="Escolher emoji">😊</button>'
      + (ev.tipo === 'post' ? '<label class="btn-extra-com" title="Foto (até 3 MB) ou GIF (até 5 MB)" aria-label="Foto ou GIF">📷<input type="file" accept="image/png,image/jpeg,image/gif,image/webp" hidden onchange="escolherImagemComentario(this)"></label>' : '')
      + '</div><button class="btn-enviar-com" onclick="enviarComentario(this)">Enviar</button>'
      + '<div class="previa-com" hidden></div></div>' : '')
    + '</article>';
}

// ---------------- publicações da Comunidade (3.2.6.0) ----------------
function tamanhoArquivo(b) {
  return b >= 1048576 ? (b / 1048576).toFixed(1).replace('.', ',') + ' MB' : Math.max(1, Math.round(b / 1024)) + ' KB';
}
function htmlArquivosPost(ev) {
  const imgs = (ev.arquivos || []).filter(a => a.imagem), vids = (ev.arquivos || []).filter(a => a.video);
  const outros = (ev.arquivos || []).filter(a => !a.imagem && !a.video);
  let h = '';
  // vídeo (3.4.2.0): só os metadados carregam antes do play, pra não pesar o feed
  if (vids.length) h += '<div class="videos-post">' + vids.map(a => '<video controls playsinline preload="metadata" src="' + esc(a.url) + '" title="' + esc(a.nome) + '"></video>').join('') + '</div>';
  if (imgs.length) h += '<div class="galeria-post' + (imgs.length === 1 ? ' uma' : '') + '">' + imgs.map(a =>
    '<button type="button" onclick="ampliarFotoPost(this)" title="Ampliar ' + esc(a.nome) + '" aria-label="Ampliar a foto ' + esc(a.nome) + '">'
    + '<img src="' + esc(a.url) + '" alt="' + esc(a.nome) + '" loading="lazy"></button>').join('') + '</div>';
  if (outros.length) h += '<div class="anexos-post">' + outros.map(a =>
    '<a class="anexo-post" href="' + esc(a.url) + '" download="' + esc(a.nome) + '">📎 <span class="nome-anexo">' + esc(a.nome)
    + '</span><span class="tam-anexo">' + tamanhoArquivo(a.tamanho || 0) + '</span></a>').join('') + '</div>';
  return h;
}

// ---------------- votação nas publicações (3.3.0.0) ----------------
function htmlVotacaoPost(ev) {
  const v = ev.votacao;
  if (!v) return '';
  // o prazo pode passar com a página aberta (3.3.7.0): a tela fecha sozinha pelo fim_em, sem esperar recarregar
  if (!v.encerrada && votacaoVenceu(v)) v.encerrada = true;
  const jaVotei = (v.meus || []).length > 0;
  const mostrarResultado = jaVotei || v.encerrada;
  const total = (v.opcoes || []).reduce((s, o) => s + o.votos, 0);
  const maior = Math.max(0, ...(v.opcoes || []).map(o => o.votos));
  let fim = '';
  if (v.encerrada) fim = ' · <b>votação encerrada' + (v.fim_em ? ' em ' + esc(prazoVotacaoTexto(v)) : '') + '</b>';
  else if (v.fim) fim = ' · encerra em ' + esc(prazoVotacaoTexto(v));
  return '<div class="votacao-post' + (v.multipla ? ' multipla' : '') + '" data-votacao="' + esc(ev.id) + '">'
    + (v.encerrada ? '<div class="faixa-encerrada">🔒 Votação encerrada · resultado final' + (total ? '' : ' (ninguém votou)') + '</div>' : '')
    + v.opcoes.map(o => {
      const pct = total ? Math.round(o.votos / total * 100) : 0;
      const minha = (v.meus || []).indexOf(o.id) !== -1;
      const venceu = v.encerrada && maior > 0 && o.votos === maior;
      return '<button type="button" class="opcao-voto' + (minha ? ' minha' : '') + (venceu ? ' vencedora' : '') + '"' + (v.encerrada ? ' disabled' : '')
        + ' onclick="votarPost(this, ' + "'" + esc(o.id) + "'" + ')" aria-pressed="' + (minha ? 'true' : 'false') + '">'
        + '<span class="barra-voto" style="width:' + (mostrarResultado ? pct : 0) + '%"></span><span class="marca"></span>'
        + '<span class="txt-voto">' + esc(o.texto) + '</span>' + (venceu ? '<span class="trofeu">🏆</span>' : '')
        + (mostrarResultado ? '<span class="pct-voto">' + pct + '% · ' + o.votos + '</span>' : '') + '</button>'
        + (mostrarResultado ? htmlQuemVotou(o) : '');
    }).join('')
    + (mostrarResultado ? htmlFaltamVotar(v) : '')
    + '<div class="rodape-votacao">' + (v.votantes === 1 ? '1 pessoa votou' : v.votantes + ' pessoas votaram')
    + (v.multipla ? ' · pode marcar mais de uma' : '') + fim
    + (!v.encerrada ? ' · os votos são públicos' + (jaVotei ? ' e dá pra mudar' : '') : '')
    + (!mostrarResultado ? ' · o resultado aparece depois que você votar' : '') + '</div></div>';
}
function votacaoVenceu(v) {
  return !!v.fim_em && Date.now() >= new Date(v.fim_em + ':00').getTime();
}
function prazoVotacaoTexto(v) {
  const s = v.fim || '';
  if (!s) return '';
  const dia = s.slice(8, 10) + '/' + s.slice(5, 7);
  return s.indexOf('T') === -1 ? dia : dia + ' às ' + s.slice(11, 16);  // só data (antes da 3.3.7.0): vale o dia inteiro
}
// a cada 30 s, redesenha a votação cujo prazo acabou de passar (vira "encerrada" com o resultado)
setInterval(() => {
  if (!muralAtual || document.hidden) return;
  (muralAtual.eventos || []).forEach(ev => {
    if (!ev.votacao || ev.votacao.encerrada || !votacaoVenceu(ev.votacao)) return;
    const card = Array.from(document.querySelectorAll('.evento')).find(c => c.dataset.id === ev.id);
    const bloco = card && card.querySelector('.votacao-post');
    if (bloco) bloco.outerHTML = htmlVotacaoPost(ev); else ev.votacao.encerrada = true;
  });
  desenharAvisoVotacoes();
}, 30000);
function alternarPrazoVotacao() {
  const escolha = document.getElementById('votacao-prazo').value;
  const campo = document.getElementById('votacao-fim');
  campo.hidden = escolha !== 'data';
  if (escolha === 'data' && !campo.value) { campo.value = isoLocalVotacao(new Date(Date.now() + 86400000)); campo.focus(); }
}
function isoLocalVotacao(d) {
  const z = n => String(n).padStart(2, '0');
  return d.getFullYear() + '-' + z(d.getMonth() + 1) + '-' + z(d.getDate()) + 'T' + z(d.getHours()) + ':' + z(d.getMinutes());
}
function fimEscolhidoVotacao() {
  const escolha = document.getElementById('votacao-prazo').value;
  const agora = new Date();
  if (!escolha) return '';
  if (escolha === 'data') return document.getElementById('votacao-fim').value || '';
  if (escolha === 'hoje') { const d = new Date(agora); d.setHours(23, 59, 0, 0); return isoLocalVotacao(d); }
  const horas = { h1: 1, h4: 4, d1: 24, d3: 72, d7: 168 }[escolha] || 0;
  return isoLocalVotacao(new Date(agora.getTime() + horas * 3600000));
}
function htmlQuemVotou(o) {
  const quem = o.quem || [];
  if (!quem.length) return '';
  const nomes = quem.slice(0, 2).map(p => p.eu ? 'você' : esc(String(p.nome).split(' ')[0]));
  const resto = quem.length - nomes.length;
  return '<button type="button" class="quem-voto" onclick="verQuemVotou(this, ' + "'" + esc(o.id) + "'" + ')">'
    + '<span class="pilha">' + quem.slice(0, 5).map(avatarMural).join('') + '</span>'
    + '<span>' + nomes.join(', ') + (resto > 0 ? ' e mais ' + resto : '') + '</span></button>';
}
// votação pra uma equipe (3.3.9.4): quem da equipe ainda não votou, junto do resultado
function htmlFaltamVotar(v) {
  const faltam = v.faltam || [];
  if (!faltam.length) return '';
  const nomes = faltam.slice(0, 2).map(p => p.eu ? 'você' : esc(String(p.nome).split(' ')[0]));
  const resto = faltam.length - nomes.length;
  return '<button type="button" class="quem-voto faltam-voto" onclick="verQuemFalta(this)">'
    + '<span class="pilha">' + faltam.slice(0, 5).map(avatarMural).join('') + '</span>'
    + '<span>Ainda não ' + (faltam.length === 1 ? 'votou' : 'votaram') + ' (' + faltam.length + '): ' + nomes.join(', ') + (resto > 0 ? ' e mais ' + resto : '') + '</span></button>';
}
function verQuemFalta(botao) {
  const ev = muralAtual.eventos.find(e => e.id === botao.closest('.evento').dataset.id);
  if (!ev || !ev.votacao) return;
  const faltam = ev.votacao.faltam || [];
  document.querySelectorAll('.fundo-palmas').forEach(f => f.remove());
  const fundo = document.createElement('div');
  fundo.className = 'fundo-palmas';
  fundo.onclick = e => { if (e.target === fundo) fundo.remove(); };
  fundo.innerHTML = '<div class="cartao-palmas" role="dialog" aria-modal="true" aria-label="Quem ainda não votou">'
    + '<div class="topo-palmas-mod"><b>⏳ ' + (faltam.length === 1 ? '1 pessoa ainda não votou' : faltam.length + ' pessoas ainda não votaram') + '</b>'
    + '<button type="button" class="fechar-palmas" onclick="fecharQuemBateu()" aria-label="Fechar">✕</button></div>'
    + '<div class="sub-palmas">' + esc(String(ev.detalhe || '').slice(0, 140)) + '</div>'
    + '<div class="lista-palmas-mod">' + faltam.map(p => '<a class="pessoa-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
      + '<div><div class="nome">' + esc(p.eu ? p.nome + ' (você)' : p.nome) + '</div><div class="sub">' + esc(p.equipe) + '</div></div></a>').join('') + '</div></div>';
  document.body.appendChild(fundo);
}
function verQuemVotou(botao, opcao) {
  const ev = muralAtual.eventos.find(e => e.id === botao.closest('.evento').dataset.id);
  if (!ev || !ev.votacao) return;
  const v = ev.votacao;
  document.querySelectorAll('.fundo-palmas').forEach(f => f.remove());
  const fundo = document.createElement('div');
  fundo.className = 'fundo-palmas';
  fundo.onclick = e => { if (e.target === fundo) fundo.remove(); };
  const linhas = v.opcoes.filter(o => (o.quem || []).length).map(o => '<div class="grupo-voto-mod"' + (o.id === opcao ? ' id="grupo-voto-alvo"' : '') + '>'
    + esc(o.texto) + ' · ' + o.votos + '</div>' + o.quem.map(p => '<a class="pessoa-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
      + '<div><div class="nome">' + esc(p.eu ? p.nome + ' (você)' : p.nome) + '</div><div class="sub">' + esc(p.equipe) + '</div></div></a>').join('')).join('');
  fundo.innerHTML = '<div class="cartao-palmas" role="dialog" aria-modal="true" aria-label="Quem votou">'
    + '<div class="topo-palmas-mod"><b>📊 ' + (v.votantes === 1 ? '1 pessoa votou' : v.votantes + ' pessoas votaram') + '</b>'
    + '<button type="button" class="fechar-palmas" onclick="fecharQuemBateu()" aria-label="Fechar">✕</button></div>'
    + '<div class="sub-palmas">' + esc(String(ev.detalhe || '').slice(0, 140)) + '</div>'
    + '<div class="lista-palmas-mod">' + linhas + '</div></div>';
  document.body.appendChild(fundo);
  const alvo = document.getElementById('grupo-voto-alvo');
  if (alvo) alvo.scrollIntoView({block: 'start'});
}
async function votarPost(botao, opcao) {
  const card = botao.closest('.evento');
  const ev = muralAtual.eventos.find(e => e.id === card.dataset.id);
  if (!ev || !ev.votacao || ev.votacao.encerrada) return;
  const atuais = ev.votacao.meus || [];
  let novas;
  if (ev.votacao.multipla) novas = atuais.indexOf(opcao) !== -1 ? atuais.filter(x => x !== opcao) : atuais.concat([opcao]);
  else novas = (atuais.length === 1 && atuais[0] === opcao) ? [] : [opcao];  // clicar de novo na mesma tira o voto
  await enviarVoto(card, ev, novas);
}
async function enviarVoto(card, ev, novas) {
  card.querySelectorAll('.opcao-voto').forEach(b => { b.disabled = true; });
  try {
    const dados = await (await fetch('/api/mural/votar', { method: 'POST',
      body: new URLSearchParams({ id: ev.id.replace(/^post:/, ''), opcoes: novas.join(',') }) })).json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    ev.votacao = dados.votacao;
  } catch (e) {
    mostrarToastHub(e.message && e.message !== 'erro' ? e.message : 'Não foi possível registrar o voto.');
  }
  const bloco = card.querySelector('.votacao-post');
  if (bloco) bloco.outerHTML = htmlVotacaoPost(ev);
  desenharAvisoVotacoes();
}
// veio do botão de uma opção no cartão do Teams (?votar=o2, 3.3.6.0): pergunta antes de gravar
function confirmarVotoDaUrl(card, ev, opcao) {
  const v = ev.votacao;
  if (!v) return;
  const o = v.opcoes.find(x => x.id === opcao);
  if (!o) return;
  if (v.encerrada) { mostrarToastHub('Essa votação já encerrou.'); return; }
  if ((v.meus || []).indexOf(opcao) !== -1) { mostrarToastHub('Você já votou em "' + o.texto + '".'); return; }
  document.querySelectorAll('.fundo-palmas').forEach(f => f.remove());
  const fundo = document.createElement('div');
  fundo.className = 'fundo-palmas';
  fundo.onclick = e => { if (e.target === fundo) fundo.remove(); };
  const trocar = !v.multipla && (v.meus || []).length;
  fundo.innerHTML = '<div class="cartao-palmas confirma-voto-mod" role="dialog" aria-modal="true" aria-label="Confirmar voto">'
    + '<div class="topo-palmas-mod"><b>📊 Confirmar voto</b><button type="button" class="fechar-palmas" onclick="fecharQuemBateu()" aria-label="Fechar">✕</button></div>'
    + '<div class="sub-palmas">' + esc(String(ev.detalhe || '').slice(0, 200)) + '</div>'
    + '<div class="opcao-escolhida">' + esc(o.texto) + '</div>'
    + (trocar ? '<div class="sub-palmas">Isso troca o voto que você já tinha dado.</div>' : '')
    + '<div class="botoes-cv"><button type="button" onclick="fecharQuemBateu()">Cancelar</button><button type="button" class="pri" id="btn-confirma-voto">Votar</button></div></div>';
  document.body.appendChild(fundo);
  const btn = document.getElementById('btn-confirma-voto');
  btn.focus();
  btn.onclick = async () => {
    fecharQuemBateu();
    await enviarVoto(card, ev, v.multipla ? (v.meus || []).concat([opcao]) : [opcao]);
    if ((ev.votacao.meus || []).indexOf(opcao) !== -1) mostrarToastHub('Voto registrado em "' + o.texto + '".');
  };
}
// aviso fixo no topo do feed (3.3.6.0): votações abertas em que a pessoa ainda não votou
function desenharAvisoVotacoes() {
  const caixa = document.getElementById('aviso-votacoes');
  if (!caixa || !muralAtual) return;
  const abertas = (muralAtual.eventos || []).filter(e => e.votacao && !e.votacao.encerrada && !votacaoVenceu(e.votacao) && !(e.votacao.meus || []).length);
  caixa.hidden = !abertas.length;
  caixa.innerHTML = abertas.length ? '<div class="tit-av">📌 ' + (abertas.length === 1 ? 'Votação aberta esperando seu voto' : abertas.length + ' votações abertas esperando seu voto') + '</div>'
    + abertas.map(e => '<div class="linha-av"><span class="perg">' + esc(String(e.detalhe || 'Votação').split(String.fromCharCode(10))[0].slice(0, 120))
      + ' <small>· ' + esc(((e.pessoas && e.pessoas[0]) || e.pessoa || {}).nome || '') + (e.votacao.fim ? ' · até ' + esc(prazoVotacaoTexto(e.votacao)) : '') + '</small></span>'
      + '<button type="button" onclick="irParaVotacao(' + "'" + esc(e.id) + "'" + ')">Votar</button></div>').join('') : '';
}
function irParaVotacao(id) {
  if (filtroFeed && filtroFeed !== 'post') { const b = document.querySelector('.chip-feed[data-tipo=""]'); if (b) b.click(); }
  garantirEventoNoFeed(id);
  const card = Array.from(document.querySelectorAll('.evento')).find(c => c.dataset.id === id);
  if (!card) return;
  card.classList.add('destacado');
  card.scrollIntoView({behavior: 'smooth', block: 'center'});
  setTimeout(() => card.classList.remove('destacado'), 4000);
}
function alternarVotacaoPost(ligar) {
  const caixa = document.getElementById('votacao-compor');
  caixa.hidden = !ligar;
  if (ligar && !document.querySelectorAll('#opcoes-votacao input').length) { adicionarOpcaoVotacao(); adicionarOpcaoVotacao(); }
  if (ligar) { const primeira = document.querySelector('#opcoes-votacao input'); if (primeira) primeira.focus(); }
  if (!ligar) { document.getElementById('opcoes-votacao').innerHTML = ''; document.getElementById('votacao-multipla').checked = false; document.getElementById('votacao-fim').value = ''; document.getElementById('votacao-prazo').value = ''; alternarPrazoVotacao(); }
  atualizarBotaoOpcaoVotacao();
}
function adicionarOpcaoVotacao() {
  const lista = document.getElementById('opcoes-votacao');
  if (lista.children.length >= 6) return;
  const linha = document.createElement('div');
  linha.className = 'opcao-votacao-compor';
  linha.innerHTML = '<input type="text" maxlength="100" placeholder="Opção ' + (lista.children.length + 1) + '">'
    + '<button type="button" aria-label="Tirar opção" onclick="this.parentNode.remove(); atualizarBotaoOpcaoVotacao()">×</button>';
  lista.appendChild(linha);
  atualizarBotaoOpcaoVotacao();
  linha.querySelector('input').focus();
}
function atualizarBotaoOpcaoVotacao() {
  const n = document.querySelectorAll('#opcoes-votacao .opcao-votacao-compor').length;
  document.getElementById('add-opcao-votacao').hidden = n >= 6;
}
function votacaoDoCompositor() {
  if (document.getElementById('votacao-compor').hidden) return null;
  return {
    opcoes: Array.from(document.querySelectorAll('#opcoes-votacao input')).map(i => i.value.trim()).filter(Boolean),
    multipla: document.getElementById('votacao-multipla').checked,
    fim: fimEscolhidoVotacao()
  };
}

// foto da publicação ampliada na própria página (3.3.0.1): setas (tela ou teclado) passam pelas fotos do mesmo post,
// Esc, o X ou clicar fora fecha
function ampliarFotoPost(botao) {
  const fotos = Array.from(botao.closest('.galeria-post').querySelectorAll('img'));
  let atual = fotos.indexOf(botao.querySelector('img'));
  const voltarFoco = botao;
  const fundo = document.createElement('div');
  fundo.className = 'fundo-foto-post';
  fundo.setAttribute('role', 'dialog');
  fundo.setAttribute('aria-modal', 'true');
  fundo.setAttribute('aria-label', 'Foto ampliada');
  const varias = fotos.length > 1;
  fundo.innerHTML = '<img alt="">'
    + '<button type="button" class="btn-foto fechar-foto" aria-label="Fechar">×</button>'
    + (varias ? '<button type="button" class="btn-foto ant-foto" aria-label="Foto anterior">&#8249;</button>'
      + '<button type="button" class="btn-foto prox-foto" aria-label="Próxima foto">&#8250;</button>' : '')
    + '<div class="info-foto"></div>';
  const img = fundo.querySelector('img');
  const mostrar = () => {
    img.src = fotos[atual].src;
    img.alt = fotos[atual].alt;
    fundo.querySelector('.info-foto').textContent = (varias ? (atual + 1) + ' de ' + fotos.length + ' · ' : '') + fotos[atual].alt;
  };
  const andar = d => { atual = (atual + d + fotos.length) % fotos.length; mostrar(); };
  const fechar = () => { fundo.remove(); document.removeEventListener('keydown', teclas); voltarFoco.focus(); };
  const teclas = e => {
    if (e.key === 'Escape') fechar();
    else if (varias && e.key === 'ArrowRight') andar(1);
    else if (varias && e.key === 'ArrowLeft') andar(-1);
  };
  fundo.addEventListener('click', e => {
    if (e.target.closest('.fechar-foto')) fechar();
    else if (e.target.closest('.ant-foto')) andar(-1);
    else if (e.target.closest('.prox-foto')) andar(1);
    else if (e.target === fundo) fechar();
  });
  document.addEventListener('keydown', teclas);
  document.body.appendChild(fundo);
  mostrar();
  fundo.querySelector('.fechar-foto').focus();
}

// ---------------- emojis e imagem nos comentários (3.3.1.0) ----------------
const EMOJIS_COM = ['😀', '😂', '🤣', '😊', '😍', '🥰', '😎', '🤩', '🥳', '😉', '🙂', '🤔', '😅', '😮', '😢', '😭', '😡', '🙏', '👏', '🙌',
  '👍', '👎', '👌', '💪', '🤝', '👀', '🔥', '✨', '🎉', '🎊', '🎂', '🏆', '🥇', '🚀', '💯', '❤️', '💙', '💚', '💛', '💜',
  '✅', '❌', '⚠️', '☕', '🍕', '🍻', '🏖️', '🌴', '📢', '💡'];
const imagensComentario = {};
function abrirEmojis(botao) {
  const aberto = document.querySelector('.painel-emoji');
  if (aberto) { const mesmo = aberto._botao === botao; aberto.remove(); if (mesmo) return; }
  const painel = document.createElement('div');
  painel.className = 'painel-emoji';
  painel.setAttribute('role', 'dialog');
  painel.setAttribute('aria-label', 'Escolher emoji');
  painel._botao = botao;
  painel.innerHTML = EMOJIS_COM.map(e => '<button type="button">' + e + '</button>').join('');
  const r = botao.getBoundingClientRect();
  painel.style.top = (window.scrollY + r.bottom + 6) + 'px';
  painel.style.left = Math.max(8, Math.min(window.scrollX + r.right - 296, window.scrollX + document.documentElement.clientWidth - 304)) + 'px';
  painel.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    const campo = botao.closest('.caixa-com').querySelector('input[type=text]');
    const ini = campo.selectionStart == null ? campo.value.length : campo.selectionStart;
    const fim = campo.selectionEnd == null ? campo.value.length : campo.selectionEnd;
    campo.value = (campo.value.slice(0, ini) + b.textContent + campo.value.slice(fim)).slice(0, 500);
    campo.focus();
    campo.selectionStart = campo.selectionEnd = ini + b.textContent.length;
  });
  document.body.appendChild(painel);
  painel.querySelector('button').focus();
}
document.addEventListener('click', e => {
  const painel = document.querySelector('.painel-emoji');
  if (painel && !painel.contains(e.target) && e.target !== painel._botao && !(painel._botao && painel._botao.contains(e.target))) painel.remove();
});
document.addEventListener('keydown', e => { if (e.key === 'Escape') { const p = document.querySelector('.painel-emoji'); if (p) { p._botao.focus(); p.remove(); } } });
function escolherImagemComentario(input) {
  const f = input.files && input.files[0];
  input.value = '';
  if (!f) return;
  if (['image/png', 'image/jpeg', 'image/gif', 'image/webp'].indexOf(f.type) === -1) { mostrarToastHub('A imagem precisa ser PNG, JPG, GIF ou WebP.'); return; }
  const limiteMb = f.type === 'image/gif' ? 5 : 3;  // GIF até 5 MB (3.3.2.1)
  if (f.size > limiteMb * 1048576) { mostrarToastHub((f.type === 'image/gif' ? 'O GIF' : 'A imagem') + ' passa de ' + limiteMb + ' MB.'); return; }
  const card = input.closest('.evento');
  const leitor = new FileReader();
  leitor.onload = () => {
    imagensComentario[card.dataset.id] = leitor.result;
    const previa = card.querySelector('.previa-com');
    previa.hidden = false;
    previa.innerHTML = '<img src="' + leitor.result + '" alt=""><span>' + esc(f.name) + '</span>'
      + '<button type="button" onclick="tirarImagemComentario(this)" aria-label="Tirar a imagem">×</button>';
  };
  leitor.readAsDataURL(f);
}
function tirarImagemComentario(botao) {
  const card = botao.closest('.evento');
  delete imagensComentario[card.dataset.id];
  const previa = card.querySelector('.previa-com'); previa.hidden = true; previa.innerHTML = '';
}
function ampliarImagemComentario(botao) {
  // reaproveita o visualizador de fotos das publicações, com uma galeria de uma foto só
  const falso = document.createElement('div');
  falso.className = 'galeria-post';
  falso.style.display = 'none';
  const b = document.createElement('button');
  b.appendChild(botao.querySelector('img').cloneNode());
  falso.appendChild(b);
  document.body.appendChild(falso);
  ampliarFotoPost(b);
  const fechar = () => { if (!document.querySelector('.fundo-foto-post')) { falso.remove(); botao.focus(); clearInterval(vigia); } };
  const vigia = setInterval(fechar, 400);
}

let arquivosPost = [];
function desenharCompositor() {
  const caixa = document.getElementById('compor-post');
  caixa.hidden = !muralAtual.eu.pode_postar;
  // 3.4.6.0: "Importante" (sininho pra todos + Teams) só pra admin ou quem tem a permissão "Publicar como importante"
  const imp = document.querySelector('.check-importante');
  if (imp) imp.hidden = !muralAtual.eu.pode_importante;
  if (!muralAtual.eu.pode_importante) document.getElementById('importante-post').checked = false;
  if (!caixa.hidden) document.getElementById('avatar-compor').innerHTML = avatarMural(muralAtual.eu);
}
function lerArquivoPost(f) {
  return new Promise((ok, falha) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = falha; r.readAsDataURL(f); });
}
async function adicionarArquivosPost(input, soImagem) {
  for (const f of Array.from(input.files || [])) {
    const ehImagem = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'].includes(f.type);
    const ehVideo = ['video/mp4', 'video/webm', 'video/quicktime'].includes(f.type);  // 3.4.2.0
    if (soImagem === true && !ehImagem) { mostrarToastHub(f.name + ' não é PNG, JPG, GIF ou WebP: use 📎 Arquivo'); continue; }
    if (soImagem === 'video' && !ehVideo) { mostrarToastHub(f.name + ' não é MP4, WebM ou MOV'); continue; }
    const tipo = ehImagem ? 'imagem' : (ehVideo ? 'video' : 'arquivo');
    const limite = { imagem: 5, video: 50, arquivo: 10 }[tipo];
    if (f.size > limite * 1048576) { mostrarToastHub(f.name + ' passa de ' + limite + ' MB'); continue; }
    if (arquivosPost.filter(a => (a.tipo || (a.imagem ? 'imagem' : 'arquivo')) === tipo).length >= { imagem: 6, video: 2, arquivo: 4 }[tipo]) {
      mostrarToastHub({ imagem: 'No máximo 6 fotos/GIFs por publicação', video: 'No máximo 2 vídeos por publicação', arquivo: 'No máximo 4 arquivos por publicação' }[tipo]); continue;
    }
    if (arquivosPost.reduce((s, a) => s + a.tamanho, 0) + f.size > 80 * 1048576) { mostrarToastHub('Os arquivos da publicação somam mais de 80 MB'); continue; }
    try { arquivosPost.push({nome: f.name, dados: await lerArquivoPost(f), imagem: ehImagem, video: ehVideo, tipo: tipo, tamanho: f.size}); }
    catch (e) { mostrarToastHub('Não foi possível ler ' + f.name); }
  }
  input.value = '';
  desenharPreviasPost();
}
function desenharPreviasPost() {
  document.getElementById('previas-post').innerHTML = arquivosPost.map((a, i) => a.imagem
    ? '<div class="previa-post"><img src="' + a.dados + '" alt=""><button type="button" onclick="tirarArquivoPost(' + i + ')" aria-label="Tirar">×</button></div>'
    : a.video ? '<div class="previa-post arq vid" title="' + esc(a.nome) + '"><video src="' + a.dados + '" muted preload="metadata"></video>🎬 ' + esc(a.nome) + ' · ' + tamanhoArquivo(a.tamanho)
      + '<button type="button" onclick="tirarArquivoPost(' + i + ')" aria-label="Tirar">×</button></div>'
    : '<div class="previa-post arq" title="' + esc(a.nome) + '">📎 ' + esc(a.nome) + ' · ' + tamanhoArquivo(a.tamanho)
      + '<button type="button" onclick="tirarArquivoPost(' + i + ')" aria-label="Tirar">×</button></div>').join('');
}
function tirarArquivoPost(i) { arquivosPost.splice(i, 1); desenharPreviasPost(); }
// ---------- publicação em grupo (3.4.1.0) ----------
const grupoPost = new Set();
function alternarGrupoPost(ligar) {
  document.getElementById('grupo-compor').hidden = !ligar;
  if (!ligar) grupoPost.clear();
  desenharListaGrupo();
  if (ligar) document.getElementById('busca-grupo').focus();
}
function pessoasGrupoDisponiveis() {
  return (muralAtual.pessoas_grupo || []).filter(p => p.login !== muralAtual.eu.login);
}
function marcarEquipeGrupo(equipe) {
  pessoasGrupoDisponiveis().forEach(p => { if (p.equipe === equipe || p.equipe === 'Suporte e Monitoramento' && (equipe === 'Suporte' || equipe === 'Monitoramento')) grupoPost.add(p.login); });
  desenharListaGrupo();
}
function limparGrupo() { grupoPost.clear(); desenharListaGrupo(); }
function alternarPessoaGrupo(login) {
  if (grupoPost.has(login)) grupoPost.delete(login); else grupoPost.add(login);
  desenharListaGrupo();
}
function desenharListaGrupo() {
  const lista = document.getElementById('lista-grupo');
  if (!lista || !muralAtual) return;
  const termo = semAcento((document.getElementById('busca-grupo') || {}).value || '');
  const pessoas = pessoasGrupoDisponiveis().filter(p => !termo || semAcento(p.nome + ' ' + p.equipe).includes(termo))
    .sort((a, b) => (grupoPost.has(b.login) - grupoPost.has(a.login)) || a.nome.localeCompare(b.nome));
  lista.innerHTML = pessoas.map(p => '<label class="pessoa-grupo' + (grupoPost.has(p.login) ? ' marcada' : '') + '">'
    + '<input type="checkbox"' + (grupoPost.has(p.login) ? ' checked' : '') + ' onchange="alternarPessoaGrupo(' + "'" + esc(p.login) + "'" + ')">'
    + avatarMural(p) + '<span class="nome-g">' + esc(p.nome) + (p.equipe ? '<small>' + esc(p.equipe) + '</small>' : '') + '</span></label>').join('')
    || '<div class="vazio" style="font-size:12px;color:var(--fg-dim)">Ninguém com esse nome.</div>';
  const n = grupoPost.size;
  document.getElementById('resumo-grupo').textContent = n ? 'Você + ' + n + (n === 1 ? ' pessoa' : ' pessoas') + ' publicando juntos.' : 'Marque quem publica com você.';
  const botao = document.getElementById('btn-grupo-post');
  if (botao) { botao.classList.toggle('com-grupo', n > 0); botao.textContent = n ? '👥 Em grupo (' + (n + 1) + ')' : '👥 Em grupo'; }
}
// quem publicou (publicação em grupo): lista completa num clique no título
function verGrupoPost(botao) {
  const ev = muralAtual.eventos.find(e => e.id === botao.closest('.evento').dataset.id);
  if (!ev) return;
  const pessoas = ev.pessoas || [];
  document.querySelectorAll('.fundo-palmas').forEach(f => f.remove());
  const fundo = document.createElement('div');
  fundo.className = 'fundo-palmas';
  fundo.onclick = e => { if (e.target === fundo) fundo.remove(); };
  fundo.innerHTML = '<div class="cartao-palmas" role="dialog" aria-modal="true" aria-label="Quem publicou">'
    + '<div class="topo-palmas-mod"><b>👥 ' + pessoas.length + ' pessoas publicaram</b>'
    + '<button type="button" class="fechar-palmas" onclick="fecharQuemBateu()" aria-label="Fechar">✕</button></div>'
    + '<div class="sub-palmas">Todas recebem as palminhas dessa publicação.</div>'
    + '<div class="lista-palmas-mod">' + pessoas.map(p => '<a class="pessoa-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
      + '<div><div class="nome">' + esc(p.login === muralAtual.eu.login ? p.nome + ' (você)' : p.nome) + '</div><div class="sub">' + esc(p.equipe || '') + '</div></div></a>').join('') + '</div></div>';
  document.body.appendChild(fundo);
}
async function publicarPost() {
  const botao = document.getElementById('btn-publicar');
  const texto = document.getElementById('texto-post').value.trim();
  const importante = document.getElementById('importante-post').checked;
  if (botao.disabled) return;
  if (!texto && !arquivosPost.length) { mostrarToastHub('Escreva alguma coisa ou adicione uma foto ou arquivo.'); return; }
  const votacao = votacaoDoCompositor();
  if (votacao && votacao.opcoes.length < 2) { mostrarToastHub('A votação precisa de pelo menos 2 opções.'); return; }
  if (votacao && !texto) { mostrarToastHub('Escreva a pergunta da votação no texto da publicação.'); return; }
  const publico = document.getElementById('publico-post').value;
  if (importante && !confirm('Publicação importante: ' + (publico ? 'a equipe ' + publico : 'todo mundo') + ' recebe um aviso no sininho e ela vai pro Teams. Publicar?')) return;
  const corpo = new URLSearchParams({texto, importante: importante ? '1' : '0', qtd_arquivos: String(arquivosPost.length), publico});
  arquivosPost.forEach((a, i) => { corpo.append('arquivo_nome_' + i, a.nome); corpo.append('arquivo_' + i, a.dados); });
  if (votacao) corpo.append('votacao', JSON.stringify(votacao));
  if (grupoPost.size) corpo.append('coautores', Array.from(grupoPost).join(','));
  botao.disabled = true;
  botao.textContent = 'Publicando...';
  try {
    const dados = await (await fetch('/api/mural/postar', {method: 'POST', body: corpo})).json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    document.getElementById('texto-post').value = '';
    document.getElementById('importante-post').checked = false;
    arquivosPost = [];
    desenharPreviasPost();
    alternarVotacaoPost(false);
    alternarGrupoPost(false);
    mostrarToastHub(importante ? 'Publicado! Todo mundo foi avisado no sininho.' : 'Publicado na Comunidade!');
    await carregarMural();
  } catch (e) {
    mostrarToastHub(e.message && e.message !== 'erro' ? e.message : 'Não foi possível publicar agora.');
  }
  botao.disabled = false;
  botao.textContent = 'Publicar';
}
// Reenviar ao Teams (3.3.4.2, só admin, só publicação importante): manda o cartão de novo sem mexer em nada
async function reenviarTeams(botao) {
  const id = (botao.closest('.evento').dataset.id || '').replace(/^post:/, '');
  if (!id || !confirm('Mandar esse aviso de novo no canal do Teams?')) return;
  botao.disabled = true;
  const texto = botao.textContent;
  botao.textContent = 'Enviando...';
  try {
    const dados = await (await fetch('/api/mural/post/reenviar-teams', {method: 'POST', body: new URLSearchParams({id})})).json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    mostrarToastHub('Aviso reenviado ao Teams.');
  } catch (e) {
    mostrarToastHub(e.message && e.message !== 'erro' ? 'Não foi pro Teams: ' + e.message : 'Não foi possível reenviar ao Teams.');
  } finally {
    botao.disabled = false;
    botao.textContent = texto;
  }
}

async function apagarPost(botao) {
  const card = botao.closest('.evento');
  const id = (card.dataset.id || '').replace(/^post:/, '');
  if (!id || !confirm('Apagar essa publicação? As fotos, os arquivos, as palminhas e os comentários dela somem junto.')) return;
  try {
    const dados = await (await fetch('/api/mural/post/apagar', {method: 'POST', body: new URLSearchParams({id})})).json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    await carregarMural();
  } catch (e) {
    mostrarToastHub(e.message && e.message !== 'erro' ? e.message : 'Não foi possível apagar.');
  }
}

function abrirCaixaComentario(botao) {
  const caixa = botao.closest('.evento').querySelector('.caixa-com');
  caixa.classList.add('aberta');
  caixa.querySelector('input[type=text]').focus();
}

function abrirTodosComentarios(botao) {
  const card = botao.closest('.evento');
  const ev = muralAtual.eventos.find(e => e.id === card.dataset.id);
  if (!ev) return;
  comentariosAbertos.add(ev.id);
  card.querySelector('.comentarios-ev').innerHTML = htmlComentarios(ev);
}

function atualizarComentarios(card, ev) {
  card.querySelector('.comentarios-ev').innerHTML = htmlComentarios(ev);
  card.querySelector('.n-com').textContent = ev.comentarios.length || '';
}

async function enviarComentario(el) {
  const card = el.closest('.evento');
  const ev = muralAtual.eventos.find(e => e.id === card.dataset.id);
  const campo = card.querySelector('.caixa-com input[type=text]');
  const botao = card.querySelector('.caixa-com .btn-enviar-com');
  const texto = campo.value.trim();
  const imagem = imagensComentario[ev ? ev.id : ''] || '';
  if (!ev || (!texto && !imagem) || botao.disabled) return;
  botao.disabled = true;
  try {
    const resp = await fetch('/api/mural/comentar', {method: 'POST', body: new URLSearchParams({evento: ev.id, texto, imagem})});
    const dados = await resp.json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    ev.comentarios = dados.comentarios;
    comentariosAbertos.add(ev.id);
    campo.value = '';
    delete imagensComentario[ev.id];
    const previa = card.querySelector('.previa-com'); previa.hidden = true; previa.innerHTML = '';
    atualizarComentarios(card, ev);
  } catch (e) {
    mostrarToastHub(e.message && e.message !== 'erro' ? e.message : 'Não foi possível comentar agora.');
  }
  botao.disabled = false;
}

async function apagarComentario(botao, id) {
  const card = botao.closest('.evento');
  const ev = muralAtual.eventos.find(e => e.id === card.dataset.id);
  if (!ev || !confirm('Apagar esse comentário?')) return;
  try {
    const resp = await fetch('/api/mural/comentario/apagar', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                                              body: 'evento=' + encodeURIComponent(ev.id) + '&id=' + encodeURIComponent(id)});
    const dados = await resp.json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    ev.comentarios = dados.comentarios;
    atualizarComentarios(card, ev);
  } catch (e) {
    mostrarToastHub(e.message && e.message !== 'erro' ? e.message : 'Não foi possível apagar.');
  }
}

// veio de uma notificação (/?evento=...): rola até o evento, destaca e abre os comentários
function irParaEventoDaUrl() {
  const alvo = new URLSearchParams(location.search).get('evento');
  if (!alvo) return;
  garantirEventoNoFeed(alvo);
  const card = Array.from(document.querySelectorAll('.evento')).find(c => c.dataset.id === alvo);
  if (!card) { mostrarToastHub('Esse acontecimento já saiu do mural.'); return; }
  card.classList.add('destacado');
  const caixa = card.querySelector('.caixa-com');
  if (caixa) caixa.classList.add('aberta');
  setTimeout(() => card.scrollIntoView({behavior: 'smooth', block: 'center'}), 250);
  setTimeout(() => card.classList.remove('destacado'), 6000);
  const votar = new URLSearchParams(location.search).get('votar');
  const ev = muralAtual.eventos.find(e => e.id === alvo);
  if (votar && ev && ev.votacao) {
    if (caixa) caixa.classList.remove('aberta');
    setTimeout(() => confirmarVotoDaUrl(card, ev, votar), 700);
  }
}

// Feed em lotes (3.3.8.0): abre com FEED_LOTE acontecimentos; o próximo lote entra sozinho quando a pessoa rola até o
// fim do feed (IntersectionObserver no botão) ou no clique em "Ver mais". Cada lote é acrescentado sem redesenhar os
// de cima (caixa de comentário aberta e scroll ficam como estão). Trocar de filtro volta pro primeiro lote.
const FEED_LOTE = 12;
let feedMostrando = FEED_LOTE;
let feedListaAtual = [];
let observadorFeed = null;
function listaDoFeed() {
  // no "Tudo" os aniversários com mais de uma semana ficam de fora (o filtro Aniversários mostra 90 dias, 3.2.2.0)
  // "tambem" (3.3.1.0): o evento aparece em mais de um filtro (a publicação da v3 é colaboração e publicação)
  return muralAtual.eventos.filter(e => filtroFeed ? (e.tipo === filtroFeed || (e.tambem || []).indexOf(filtroFeed) !== -1) : !e.so_filtro);
}
function htmlRodapeFeed() {
  const faltam = feedListaAtual.length - feedMostrando;
  if (faltam > 0) return '<div class="mais-feed" id="mais-feed"><button type="button" onclick="mostrarMaisFeed()">Ver mais acontecimentos (' + faltam + ')</button></div>';
  return feedListaAtual.length > FEED_LOTE ? '<div class="fim-feed">Você viu tudo dos últimos 30 dias ✨</div>' : '';
}
function vigiarFimDoFeed() {
  if (observadorFeed) observadorFeed.disconnect();
  const alvo = document.getElementById('mais-feed');
  if (!alvo || !('IntersectionObserver' in window)) return;
  observadorFeed = new IntersectionObserver(entradas => { if (entradas.some(e => e.isIntersecting)) mostrarMaisFeed(); }, { rootMargin: '0px 0px 200px 0px' });
  observadorFeed.observe(alvo);
}
function desenharFeed() {
  feedListaAtual = listaDoFeed();
  const feed = document.getElementById('feed');
  if (!feedListaAtual.length) {
    feed.innerHTML = '<div class="feed-vazio">' + (filtroFeed ? 'Nada desse tipo nos últimos 30 dias.'
      : 'O mural ainda está quieto. Aniversários, promoções e insígnias aparecem aqui quando as pessoas completam o perfil.') + '</div>';
    return;
  }
  feed.innerHTML = feedListaAtual.slice(0, feedMostrando).map(htmlEvento).join('') + htmlRodapeFeed();
  vigiarFimDoFeed();
}
function mostrarMaisFeed(ate) {
  const antes = feedMostrando;
  feedMostrando = Math.min(feedListaAtual.length, Math.max(ate || 0, feedMostrando + FEED_LOTE));
  if (feedMostrando <= antes) return;
  const rodape = document.getElementById('mais-feed');
  if (rodape) rodape.remove();
  document.getElementById('feed').insertAdjacentHTML('beforeend', feedListaAtual.slice(antes, feedMostrando).map(htmlEvento).join('') + htmlRodapeFeed());
  vigiarFimDoFeed();
}
// notificação, voto pelo Teams ou aviso fixo apontando pra um acontecimento que ainda não entrou no feed: carrega até ele
function garantirEventoNoFeed(id) {
  const i = feedListaAtual.findIndex(e => e.id === id);
  if (i >= feedMostrando) mostrarMaisFeed(i + 1);
}

function desenharLado() {
  const anivs = muralAtual.aniversarios;
  document.getElementById('lista-aniversarios').innerHTML = anivs.length ? anivs.slice(0, 6).map(p =>
    '<a class="pessoa-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
    + '<div><div class="nome">' + esc(p.nome) + '</div><div class="sub">' + esc(p.equipe) + '</div></div>'
    + '<span class="fim' + (p.faltam === 0 ? ' hoje' : '') + '">' + (p.faltam === 0 ? '🎉 hoje' : esc(p.quando)) + '</span></a>').join('')
    : '<div class="vazio">Ninguém faz aniversário nos próximos 30 dias.</div>';
  // De férias (3.1.6.0): direto do Calendário de Férias; sem ninguém fora, o bloco nem aparece
  const ferias = muralAtual.de_ferias || [];
  document.getElementById('bloco-ferias').hidden = !ferias.length;
  document.getElementById('lista-ferias').innerHTML = ferias.map(p =>
    '<a class="pessoa-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
    + '<div><div class="nome">' + esc(p.nome) + '</div><div class="sub">' + { dayoff: 'Day off', atestado: 'Ausente', ferias: 'Férias' }[tipoAusencia(p.tipo)] + (p.equipe ? ' · ' + esc(p.equipe) : '') + '</div></div>'
    + '<span class="fim">' + (p.fim === muralAtual.hoje ? 'volta amanhã' : 'até ' + esc(String(p.fim || '').split('-').reverse().slice(0, 2).join('/'))) + '</span></a>').join('');
  const promos = muralAtual.promocoes || [];
  document.getElementById('lista-promocoes').innerHTML = promos.length ? promos.map(p =>
    '<a class="pessoa-linha promo-linha" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p)
    + '<div><div class="nome">' + esc(p.nome) + '</div><div class="sub">agora <b>' + esc(p.para) + '</b></div></div>'
    + '<span class="fim">' + esc(p.quando) + '</span></a>').join('')
    : '<div class="vazio">As promoções aparecem aqui quando alguém ganha um cargo novo no histórico.</div>';
  desenharCampanhas(muralAtual.campanhas || []);
}

// Campanhas (3.0.2.0): quem concluiu vê o selo por cima até a campanha acabar; sem campanha,
// ou com todas concluídas, entra o "Nova campanha em breve"; com mais de uma página, troca
// sozinha a cada 7 s (para com o mouse em cima) e tem os pontinhos
let paginaCamp = 0, totalCamp = 0, timerCamp = null;
function htmlCampanha(c) {
  const quando = c.concluida_em ? ' em ' + c.concluida_em.split('-').reverse().slice(0, 2).join('/') : '';
  return '<div class="bloco-campanha' + (c.concluida ? ' concluida' : '') + '">' + svgInsignia(c.insignia, 54, false)
    + '<div><b>' + esc(c.nome) + '</b><span>' + esc(c.descricao)
    + (c.fim ? ' <b class="prazo-camp">Até ' + c.fim.split('-').reverse().join('/') + '</b>' : '') + '</span>'
    + (c.concluida ? '' : '<button onclick="' + (c.acao === 'bug' ? 'abrirRequisitosBugHunterIns()' : 'abrirParticipacaoDoPerfilIns()') + '">Quero participar</button>') + '</div>'
    + (c.concluida ? '<div class="selo-concluida"><div class="check">✓</div><b>Campanha concluída</b><span>Insígnia conquistada' + quando + '</span></div>' : '')
    + '</div>';
}
const HTML_CAMPANHA_EM_BREVE = '<div class="bloco-campanha em-breve"><span class="icone-em-breve">📣</span>'
  + '<div><b>Nova campanha em breve</b><span>Fique de olho: a próxima campanha, com insígnia nova, aparece aqui.</span>'
  + '<span class="selo-breve">Em breve</span></div></div>';
function desenharCampanhas(lista) {
  const paginas = lista.map(htmlCampanha);
  if (!lista.length || lista.every(c => c.concluida)) paginas.push(HTML_CAMPANHA_EM_BREVE);
  totalCamp = paginas.length;
  paginaCamp = Math.min(paginaCamp, totalCamp - 1);
  const el = document.getElementById('bloco-campanha');
  el.innerHTML = '<div class="trilho-camp"><div class="faixa-camp" id="faixa-camp">' + paginas.join('') + '</div></div>'
    + (totalCamp > 1 ? '<div class="pontos-camp">' + paginas.map((_, i) => '<button aria-label="Campanha ' + (i + 1) + '" onclick="irParaCampanha(' + i + ', true)"></button>').join('') + '</div>' : '');
  el.onmouseenter = () => clearInterval(timerCamp);
  el.onmouseleave = iniciarRodizioCamp;
  irParaCampanha(paginaCamp, false);
  iniciarRodizioCamp();
}
function irParaCampanha(i, doClique) {
  paginaCamp = i;
  const faixa = document.getElementById('faixa-camp');
  if (faixa) faixa.style.transform = 'translateX(-' + (i * 100) + '%)';
  document.querySelectorAll('.pontos-camp button').forEach((b, j) => b.classList.toggle('ativo', j === i));
  if (doClique) iniciarRodizioCamp();
}
function iniciarRodizioCamp() {
  clearInterval(timerCamp);
  if (totalCamp > 1) timerCamp = setInterval(() => { if (!document.hidden) irParaCampanha((paginaCamp + 1) % totalCamp, false); }, 7000);
}

// Parabéns (3.0.3.0): quem faz aniversário vê, no primeiro acesso do dia, o cartão com balões e confete
function festejarAniversario(forcar) {
  const eu = muralAtual.eu;
  if (!eu.aniversario_hoje && !forcar) return;
  const chave = 'pda-parabens-' + muralAtual.hoje + '-' + eu.login;
  try { if (!forcar && localStorage.getItem(chave)) return; localStorage.setItem(chave, '1'); } catch (e) {}
  const fundo = document.createElement('div');
  fundo.className = 'festa-niver';
  fundo.innerHTML = '<div class="cartao-niver"><div class="bolo">🎂</div><h2>Feliz aniversário, <span>' + esc(eu.nome.split(' ')[0]) + '</span>!</h2>'
    + '<p>Toda a equipe deseja um dia incrível, cheio de coisas boas. Hoje o mural é seu: os colegas já podem deixar palminhas e recados.</p>'
    + '<button>Obrigado, pessoal! 🎉</button></div>';
  const cores = ['#f2b705', '#fb923c', '#e85d75', '#2db8cf', '#b0cb1c', '#c084fc', '#60a5fa'];
  for (let i = 0; i < 90; i++) {
    const c = document.createElement('span');
    c.className = 'confete-niver';
    c.style.left = (Math.random() * 100) + '%';
    c.style.background = cores[i % cores.length];
    c.style.setProperty('--vento', (Math.random() * 160 - 80) + 'px');
    c.style.setProperty('--giro', (Math.random() * 900 - 450) + 'deg');
    c.style.animationDuration = (2.6 + Math.random() * 2.6) + 's';
    c.style.animationDelay = (Math.random() * 1.8) + 's';
    fundo.appendChild(c);
  }
  for (let i = 0; i < 12; i++) {
    const b = document.createElement('span');
    b.className = 'balao-niver';
    b.style.left = (4 + Math.random() * 90) + '%';
    b.style.background = cores[i % cores.length];
    b.style.setProperty('--vento', (Math.random() * 120 - 60) + 'px');
    b.style.animationDuration = (5 + Math.random() * 4) + 's';
    b.style.animationDelay = (Math.random() * 2.5) + 's';
    fundo.appendChild(b);
  }
  const fechar = () => { fundo.remove(); document.removeEventListener('keydown', aoTeclar); };
  const aoTeclar = e => { if (e.key === 'Escape') fechar(); };
  fundo.querySelector('button').onclick = fechar;
  fundo.addEventListener('click', e => { if (e.target === fundo) fechar(); });
  document.addEventListener('keydown', aoTeclar);
  document.body.appendChild(fundo);
}

function desenharEu() {
  const eu = muralAtual.eu;
  document.getElementById('avatar-eu').innerHTML = avatarMural(eu);
  document.getElementById('cargo-eu').textContent = [eu.cargo, eu.equipe].filter(Boolean).join(' · ') || ' ';
  const ins = eu.destaque;
  document.getElementById('destaque-eu').innerHTML = ins ? svgInsignia(ins, 34, false) : '';
  const h = new Date(muralAtual.hoje + 'T12:00:00');
  const n = muralAtual.meus_numeros;
  let sub = DIAS_SEMANA_MURAL[h.getDay()] + ', ' + h.getDate() + ' de ' + MESES_LONGOS_MURAL[h.getMonth()];
  const anivHoje = muralAtual.aniversarios.filter(p => p.faltam === 0).length;
  if (anivHoje) sub += ' · ' + anivHoje + (anivHoje === 1 ? ' aniversariante hoje 🎂' : ' aniversariantes hoje 🎂');
  if (n.ferias) {
    const ini = new Date(n.ferias.inicio + 'T12:00:00'), fim = new Date(n.ferias.fim + 'T12:00:00');
    sub += ' · ' + { dayoff: 'seu day off', atestado: 'sua ausência', ferias: 'suas férias' }[tipoAusencia(n.ferias.tipo)] + ': ' + ini.getDate() + ' ' + NOMES_MESES_MURAL[ini.getMonth()]
      + (n.ferias.inicio === n.ferias.fim ? '' : ' a ' + fim.getDate() + ' ' + NOMES_MESES_MURAL[fim.getMonth()]);
  }
  document.getElementById('sub-inicio').textContent = sub;

  const casa = document.getElementById('ind-casa');
  casa.querySelector('.valor').innerHTML = n.tempo_de_casa ? esc(n.tempo_de_casa) : '<small>sem data</small>';
  casa.querySelector('.detalhe').innerHTML = n.desde ? 'desde ' + n.desde.split('-').reverse().join('/') + ' · ' + n.insignias + (n.insignias === 1 ? ' insígnia' : ' insígnias')
    : '<a href="/perfil/' + encodeURIComponent(eu.login) + '" style="color:var(--teal)">Informe sua entrada no perfil</a>';
  casa.querySelector('.ins-ind').innerHTML = n.insignia_tempo ? svgInsignia(n.insignia_tempo, 46, false) : '';
  const palmas = document.getElementById('ind-palmas');
  palmas.querySelector('.valor').textContent = n.palmas_recebidas;
  palmas.querySelector('.detalhe').textContent = 'recebidas · ' + n.palmas_enviadas + (n.palmas_enviadas === 1 ? ' enviada' : ' enviadas');
  if (window.aplicarWallpaperCartao) aplicarWallpaperCartao(eu.wallpaper || 'padrao');  // Loja de Palminhas (3.3.7.0)
}

async function carregarMural() {
  try {
    const resp = await fetch('/api/mural');
    if (resp.status === 401) { window.location.href = '/login'; return; }
    muralAtual = await resp.json();
    if (!muralAtual.ok) throw new Error(muralAtual.erro || 'erro');
    desenharEu();
    desenharCompositor();
    desenharFeed();
    desenharAvisoVotacoes();
    desenharLado();
    if (!window._eventoUrlFeito) { window._eventoUrlFeito = true; irParaEventoDaUrl(); festejarAniversario(); }
    if (muralAtual.equipe && !equipeGestao) desenharEquipe(muralAtual.equipe);
  } catch (e) {
    document.getElementById('feed').innerHTML = '<div class="feed-vazio">Não foi possível carregar o mural agora. Atualize a página em instantes.</div>';
  }
}

async function baterPalma(botao) {
  const card = botao.closest('.evento');
  const ev = muralAtual.eventos.find(e => e.id === card.dataset.id);
  if (!ev || botao.disabled) return;
  const antes = {palmas: ev.palmas, bati: ev.bati, quem: ev.quem};
  // responde na hora e confirma com o servidor
  ev.bati = !ev.bati;
  ev.palmas += ev.bati ? 1 : -1;
  ev.quem = ev.bati ? ['você'].concat(ev.quem) : ev.quem.filter(q => q !== 'você');
  atualizarCardPalma(card, ev, ev.bati);
  try {
    const resp = await fetch('/api/mural/palma', {method: 'POST', headers: {'Content-Type': 'application/x-www-form-urlencoded'},
                                                   body: 'evento=' + encodeURIComponent(ev.id)});
    const dados = await resp.json();
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    Object.assign(ev, {palmas: dados.palmas, bati: dados.bati, quem: dados.quem, quem_todos: dados.quem_todos || ev.quem_todos});
    atualizarCardPalma(card, ev, false);
  } catch (e) {
    Object.assign(ev, antes);
    atualizarCardPalma(card, ev, false);
    mostrarToastHub(e.message && e.message !== 'erro' ? e.message : 'Não foi possível registrar as palminhas.');
  }
}

function atualizarCardPalma(card, ev, comAnimacao) {
  const botao = card.querySelector('.btn-palma');
  botao.classList.toggle('bati', ev.bati);
  botao.querySelector('.n').textContent = ev.palmas || '';
  card.querySelector('.quem-bateu').innerHTML = textoQuemBateu(ev);
  if (comAnimacao) {
    botao.classList.remove('estourar'); void botao.offsetWidth; botao.classList.add('estourar');
    [-14, 0, 14].forEach((dx, i) => {
      const voa = document.createElement('span');
      voa.className = 'palma-voando'; voa.textContent = '👏';
      voa.style.setProperty('--dx', dx + 'px'); voa.style.animationDelay = (i * 0.08) + 's';
      botao.appendChild(voa);
      setTimeout(() => voa.remove(), 1200);
    });
  }
}

document.getElementById('filtros-feed').addEventListener('click', e => {
  const chip = e.target.closest('.chip-feed');
  if (!chip || !muralAtual) return;
  filtroFeed = chip.dataset.tipo;
  feedMostrando = FEED_LOTE;
  document.querySelectorAll('.chip-feed').forEach(c => c.classList.toggle('ativo', c === chip));
  desenharFeed();
});

// ---------------- números do Movidesk (banco, carregam depois) ----------------
let numerosMovidesk = null;
async function carregarNumerosMovidesk() {
  if (numerosMovidesk) return;
  numerosMovidesk = 'carregando';
  try {
    const resp = await fetch('/api/mural/movidesk');
    const dados = await resp.json();
    numerosMovidesk = dados;
    desenharMovidesk(dados);
  } catch (e) {
    numerosMovidesk = {ok: false, erro: 'sem resposta'};
    desenharMovidesk(numerosMovidesk);
  }
}

function preencherInd(id, valor, detalhe, percentual) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('carregando');
  el.querySelector('.valor').innerHTML = valor;
  el.querySelector('.detalhe').innerHTML = detalhe;
  const barra = el.querySelector('.barra span');
  if (barra) setTimeout(() => { barra.style.width = Math.min(percentual || 0, 100) + '%'; }, 60);
}

function desenharMovidesk(d) {
  const eu = d.ok ? d.eu : null;
  if (!d.ok) {
    preencherInd('ind-horas', '<small>indisponível</small>', 'o banco do Movidesk não respondeu', 0);
    preencherInd('ind-tickets', '<small>indisponível</small>', '&nbsp;', 0);
  } else if (!eu.vinculado) {
    preencherInd('ind-horas', '<small>sem vínculo</small>', eu.erro ? esc(eu.erro) : 'peça pra um admin vincular você ao Movidesk', 0);
    preencherInd('ind-tickets', '<small>sem vínculo</small>', '&nbsp;', 0);
  } else {
    preencherInd('ind-horas', esc(eu.horas) + ' <small>de ' + esc(eu.meta) + '</small>',
                 eu.percentual == null ? 'sem meta no período' : eu.percentual.toLocaleString('pt-BR') + '% da meta até hoje', eu.percentual);
    preencherInd('ind-tickets', String(eu.tickets), 'neste mês', 0);
  }
  if (!document.getElementById('ind-eq-horas') || equipeGestao) return;  // com filtro, quem desenha é filtrarGestao
  desenharMovideskEquipe(d.ok ? d.equipe : null);
}

function desenharMovideskEquipe(eq) {
  if (!eq) {
    preencherInd('ind-eq-horas', '<small>indisponível</small>', 'o banco do Movidesk não respondeu', 0);
    preencherInd('ind-eq-tickets', '<small>indisponível</small>', '&nbsp;', 0);
    return;
  }
  preencherInd('ind-eq-horas', (eq.percentual == null ? '--' : eq.percentual.toLocaleString('pt-BR') + '%'),
               esc(eq.horas) + ' de ' + esc(eq.meta) + ' · ' + eq.abaixo_meta + (eq.abaixo_meta === 1 ? ' pessoa abaixo de ' : ' pessoas abaixo de ') + eq.limite_alerta + '%', eq.percentual);
  preencherInd('ind-eq-tickets', String(eq.tickets), 'com ação neste mês · ' + eq.pessoas + ' pessoas com apontamento', 0);
}

// tipo do Calendário de Férias (3.3.9.3): ele grava "day_off" (com sublinhado) e a Comunidade comparava com "dayoff",
// então todo day off aparecia como férias. Atestado aparece como "ausente" (não expõe o motivo pra todo mundo).
function tipoAusencia(tipo) {
  const t = String(tipo || '').toLowerCase().replace(/[^a-z]/g, '');
  return t === 'dayoff' ? 'dayoff' : (t === 'atestado' || t === 'afastamento' ? 'atestado' : 'ferias');  // afastamento: 3.4.4.0
}

function desenharEquipe(eq) {
  const partes = Object.entries(eq.equipes).map(([n, q]) => q + ' ' + esc(n));
  preencherInd('ind-eq-pessoas', String(eq.ativos), partes.join(' · ') || '&nbsp;', 0);
  preencherInd('ind-eq-fora', String(eq.fora_hoje.length), eq.fora_hoje.length ? 'de férias ou day off hoje' : 'todo mundo trabalhando hoje', 0);
  const fora = document.getElementById('fora-hoje');
  fora.innerHTML = eq.fora_hoje.length ? '<span class="rot">Fora hoje:</span>' + eq.fora_hoje.map(p =>
    '<a class="chip-pessoa" href="/perfil/' + encodeURIComponent(p.login) + '">' + avatarMural(p) + esc(p.nome.split(' ')[0])
    + ' · ' + { dayoff: 'day off', atestado: 'ausente', ferias: 'férias até ' + p.fim.split('-').reverse().slice(0, 2).join('/') }[tipoAusencia(p.tipo)] + '</a>').join('') : '';
}

// Filtro da Gestão (3.0.2.0): Ambos (padrão), Suporte ou Monitoramento; a escolha fica salva no navegador
let equipeGestao = '';
try { equipeGestao = localStorage.getItem('pda-gestao-equipe') || ''; } catch (e) {}
async function filtrarGestao(equipe) {
  equipeGestao = equipe;
  try { localStorage.setItem('pda-gestao-equipe', equipe); } catch (e) {}
  document.querySelectorAll('#filtro-equipe button').forEach(b => b.classList.toggle('ativo', b.dataset.equipe === equipe));
  ['ind-eq-horas', 'ind-eq-tickets', 'ind-eq-pessoas', 'ind-eq-fora'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.classList.add('carregando'); el.querySelector('.valor').innerHTML = '--'; }
  });
  try {
    const resp = await fetch('/api/mural/equipe?equipe=' + encodeURIComponent(equipe));
    const dados = await resp.json();
    if (equipe !== equipeGestao) return;  // clicou em outra enquanto carregava
    if (!dados.ok) throw new Error(dados.erro || 'erro');
    desenharEquipe(dados.geral);
    desenharMovideskEquipe(dados.movidesk && dados.movidesk.ok ? dados.movidesk.equipe : null);
  } catch (e) {
    mostrarToastHub('Não foi possível carregar os números dessa equipe.');
    desenharMovideskEquipe(null);
  }
}

// Busca de cards (3.0.8.0): procura no nome e na descrição de todos os cards (de todas as seções)
const NOMES_SECOES = { automacoes: 'Automações', gestao: 'Gestão de equipe', operacoes: 'Operações/Serviços', outros: 'Outros', embreve: 'Em breve' };
let indiceBusca = -1;
function semAcento(t) { return String(t || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
function buscarCards() {
  const campo = document.getElementById('busca-cards');
  const caixa = document.getElementById('resultados-busca');
  const termo = semAcento(campo.value.trim());
  if (!termo) { caixa.classList.remove('aberto'); caixa.innerHTML = ''; return; }
  const achados = [];
  const jaAchados = new Set();
  Object.entries(ordemOriginalHub).forEach(([grade, cards]) => cards.forEach(c => {
    const titulo = (c.querySelector('h2') || {}).textContent || '';
    const chaveCard = c.getAttribute('href') || titulo;
    if (jaAchados.has(chaveCard)) return;
    const desc = (c.querySelector('p') || {}).textContent || '';
    const alvo = semAcento(titulo + ' ' + desc);
    if (termo.split(' ').every(p => alvo.includes(p))) { jaAchados.add(chaveCard); achados.push({ c, grade, titulo, desc, noTitulo: semAcento(titulo).includes(termo) }); }
  }));
  achados.sort((a, b) => b.noTitulo - a.noTitulo);
  indiceBusca = achados.length ? 0 : -1;
  caixa.innerHTML = achados.length ? achados.slice(0, 8).map((r, i) => {
    const cor = ((r.c.getAttribute('style') || '').split('--accent-card:')[1] || '#2db8cf').trim();
    const icone = r.c.querySelector('.icone svg');
    const href = r.c.getAttribute('href');
    const alvo = r.c.getAttribute('target') ? ' target="_blank" rel="noopener noreferrer"' : '';
    const abre = href ? 'href="' + esc(href) + '"' + alvo : 'onclick="abrirEmConstrucao(event, ' + "'" + esc(r.titulo.replace(/'/g, '')) + "'" + ')"';
    return '<a class="resultado-busca' + (i === 0 ? ' ativo' : '') + '" ' + abre + ' style="--cor-res:' + esc(cor) + '">'
      + '<span class="ic-res" style="background:color-mix(in srgb, ' + esc(cor) + ' 15%, transparent)">' + (icone ? icone.outerHTML : '') + '</span>'
      + '<div><div class="tit-res">' + esc(r.titulo.trim()) + '</div><div class="desc-res">' + esc(r.desc.trim()) + '</div></div>'
      + '<span class="sec-res">' + NOMES_SECOES[r.grade] + '</span></a>';
  }).join('') : '<div class="nada-busca">Nenhum card com "' + esc(campo.value.trim()) + '".</div>';
  caixa.classList.add('aberto');
}
function teclarBusca(ev) {
  const itens = Array.from(document.querySelectorAll('#resultados-busca .resultado-busca'));
  if (ev.key === 'Escape') { ev.target.value = ''; buscarCards(); ev.target.blur(); return; }
  if (!itens.length) return;
  if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
    ev.preventDefault();
    indiceBusca = (indiceBusca + (ev.key === 'ArrowDown' ? 1 : -1) + itens.length) % itens.length;
    itens.forEach((it, i) => it.classList.toggle('ativo', i === indiceBusca));
  } else if (ev.key === 'Enter') {
    ev.preventDefault();
    (itens[indiceBusca] || itens[0]).click();
  }
}
document.addEventListener('click', ev => {
  if (!document.getElementById('busca-global').contains(ev.target)) document.getElementById('resultados-busca').classList.remove('aberto');
});
// "/" em qualquer lugar foca a busca (menos quando já está digitando num campo)
document.addEventListener('keydown', ev => {
  if (ev.key === '/' && !/INPUT|TEXTAREA|SELECT/.test((document.activeElement || {}).tagName || '')) {
    ev.preventDefault(); document.getElementById('busca-cards').focus();
  }
});

window.aoMudarInsigniasIns = carregarMural;
montarGrades();
trocarSecao(location.hash.slice(1) || 'inicio', true);
carregarMural();
carregarNumerosMovidesk();

// Anúncio de uma vez só (3.2.0.0): foto de perfil em GIF, pra quem já tem foto. Espera a comemoração de
// insígnia ou de aniversário fechar, pra não abrir um em cima do outro.
function mostrarAnuncioGif() {
  if (!muralAtual || !muralAtual.eu) { setTimeout(mostrarAnuncioGif, 1500); return; }  // o mural ainda não carregou
  if (muralAtual.eu.anuncio !== 'gif_perfil' || window._anuncioMostrado) return;
  if (document.querySelector('.fundo-ins, .festa-niver, .fundo-palmas')) { setTimeout(mostrarAnuncioGif, 1500); return; }
  window._anuncioMostrado = true;
  const fundo = document.createElement('div');
  fundo.className = 'fundo-anuncio';
  fundo.innerHTML = '<div class="cartao-anuncio" role="dialog" aria-modal="true" aria-label="Novidade: foto em GIF">'
    + '<span class="selo-anuncio">✨ Novidade no PDA</span>'
    + '<div class="palco-anuncio"><img src="/anuncio/mario.gif" alt="Mario dançando"></div>'
    + '<h2>Sua foto de perfil agora pode ser um <span>GIF</span>!</h2>'
    + '<p>Dá pra usar um GIF animado como foto (até 5 MB). Ele aparece mexendo no mural, no seu perfil e em todo lugar que mostra a sua foto.</p>'
    + '<div class="botoes-anuncio"><a class="btn-anuncio" href="/perfil/' + encodeURIComponent(muralAtual.eu.login) + '" onclick="fecharAnuncioGif(false)">Trocar minha foto</a>'
    + '<button type="button" class="btn-anuncio-sec" onclick="fecharAnuncioGif(true)">Agora não</button></div></div>';
  document.body.appendChild(fundo);
}
function fecharAnuncioGif(remover) {
  // o servidor já marca como visto ao entregar o anúncio (3.2.5.1); isso aqui fica de reforço
  try { navigator.sendBeacon('/api/anuncios/visto', new URLSearchParams({ anuncio: 'gif_perfil' })); } catch (e) {
    fetch('/api/anuncios/visto', { method: 'POST', body: new URLSearchParams({ anuncio: 'gif_perfil' }) });
  }
  if (remover) document.querySelectorAll('.fundo-anuncio').forEach(f => f.remove());
}
setTimeout(mostrarAnuncioGif, 2200);

// Laterais que acompanham o scroll (3.2.7.0): antes ficavam presas no topo (sticky top 18px) e, mais altas que a tela
// (muitos favoritos, aniversariantes...), o fim delas só aparecia no fim da página. Agora, mais alta que a tela, a
// lateral desce junto com a página até mostrar o fim e gruda embaixo; subindo, volta até o topo e gruda em cima.
// Sem barra de rolagem extra (a roda do mouse e o teclado continuam rolando a página) e o foco por Tab sempre fica visível.
// voltar ao topo (3.3.8.3): o feed carrega em lotes e fica comprido; o botão aparece depois de 1,5 tela de rolagem
function voltarAoTopo() {
  window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
}
(function () {
  const botao = document.getElementById('voltar-topo');
  if (!botao) return;
  let agendado = false;
  function conferir() {
    agendado = false;
    const mostrar = window.scrollY > window.innerHeight * 1.5;
    // 3.4.0.1: com o rodapé aparecendo, sobe junto pra não ficar em cima do Changelog/Sobre
    const rodape = document.querySelector('.rodape');
    const folga = window.innerWidth <= 640 ? 14 : 24;
    const topoRodape = rodape ? rodape.getBoundingClientRect().top : Infinity;
    botao.style.bottom = (topoRodape < window.innerHeight ? Math.round(window.innerHeight - topoRodape + 12) : folga) + 'px';
    if (mostrar) botao.hidden = false;
    botao.classList.toggle('visivel', mostrar);
    if (!mostrar) setTimeout(() => { if (!botao.classList.contains('visivel')) botao.hidden = true; }, 220);
  }
  const pedir = () => { if (!agendado) { agendado = true; requestAnimationFrame(conferir); } };
  window.addEventListener('scroll', pedir, { passive: true });
  window.addEventListener('resize', pedir);
})();

(function lateraisQueAcompanham() {
  const MARGEM = 18;
  const laterais = [document.querySelector('.lateral-mural'), document.querySelector('.lado-inicio')].filter(Boolean)
    .map(el => ({ el, top: MARGEM }));
  let ultimoScroll = window.scrollY;
  function limites(l) {
    const altura = l.el.offsetHeight, tela = window.innerHeight;
    return { min: Math.min(MARGEM, tela - altura - MARGEM), max: MARGEM };
  }
  function aplicar(l, novoTop) {
    const lim = limites(l);
    l.top = Math.max(lim.min, Math.min(lim.max, novoTop));
    l.el.style.top = l.top + 'px';
  }
  function ativa(l) { return getComputedStyle(l.el).position === 'sticky'; }
  function aoRolar() {
    const delta = window.scrollY - ultimoScroll;
    ultimoScroll = window.scrollY;
    laterais.forEach(l => { if (ativa(l)) aplicar(l, l.top - delta); else l.el.style.top = ''; });
  }
  window.addEventListener('scroll', aoRolar, { passive: true });
  window.addEventListener('resize', () => laterais.forEach(l => ativa(l) ? aplicar(l, l.top) : (l.el.style.top = '')));
  // conteúdo da lateral mudou de altura (mural carregou, favorito novo, campanha trocou): recalcula o limite
  if (window.ResizeObserver) {
    const obs = new ResizeObserver(() => laterais.forEach(l => { if (ativa(l)) aplicar(l, l.top); }));
    laterais.forEach(l => obs.observe(l.el));
  }
  // Tab até um item da lateral que está fora da tela: desliza a lateral até ele aparecer
  laterais.forEach(l => l.el.addEventListener('focusin', e => {
    if (!ativa(l)) return;
    const r = e.target.getBoundingClientRect();
    if (r.bottom > window.innerHeight - MARGEM) aplicar(l, l.top - (r.bottom - window.innerHeight + MARGEM));
    else if (r.top < MARGEM) aplicar(l, l.top + (MARGEM - r.top));
  }));
})();
</script>
<script>verificarCampanhaInsignias('hub');</script>
</body>
</html>
"""


# Cards que antes ficavam direto no template (2.35.7.0: o início monta as seções no alertas_gui.py)
_CARD_ALERTAS_HTML = """<a class="card-hub" href="/alertas" style="--accent-card:#2db8cf">
        <div class="icone" style="background:rgba(45,184,207,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3a5 5 0 0 0-5 5v3.5c0 .7-.3 1.4-.8 1.9L5 15h14l-1.2-1.6c-.5-.5-.8-1.2-.8-1.9V8a5 5 0 0 0-5-5z"/>
            <path d="M9.5 18a2.5 2.5 0 0 0 5 0"/>
          </svg>
        </div>
        <h2>Alertas Suporte (Legacy)</h2>
        <p>Status, agenda e log de execução de todos os alertas operacionais.</p>
      </a>"""

_CARD_CONTINGENCIAS_HTML = """<a class="card-hub" href="/contingencias" style="--accent-card:#f14c4c">
        <div class="icone" style="background:rgba(241,76,76,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3l7 3v6c0 4.5-3 8-7 9-4-1-7-4.5-7-9V6l7-3z"/>
            <path d="M12 8v5"/><path d="M12 16h.01"/>
          </svg>
        </div>
        <h2>Contingências SEFAZ</h2>
        <p>Monitoramento de ativação, agendamento e encerramento da SVC-AN e SVC-RS por estado.</p>
        <span class="tag-live __CLASSE_CONTING__"><span class="ponto"></span>__RESUMO_CONTING__</span>
      </a>"""

_CARD_EMAILPACK_HTML = """<a class="card-hub" href="/emailpack" style="--accent-card:#9b5de5">
        <div class="icone" style="background:rgba(155,93,229,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="5" width="18" height="14" rx="2"/>
            <path d="M3 7l9 6 9-6"/>
          </svg>
        </div>
        <h2>Monitoramento EmailPack</h2>
        <p>Varredura dos logs dos serviços EmailPack por e-mail processado, com aviso automático no Teams.</p>
      </a>"""

_CARD_MEU_PLANTAO_HTML = """<a class="card-hub" href="https://meu-plantao.example.app/login?next=/" target="_blank" rel="noopener noreferrer" style="--accent-card:#6c63ff">
        <div class="icone" style="background:rgba(108,99,255,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>
          </svg>
        </div>
        <h2>Meu Plantão</h2>
        <p>Controle de horas trabalhadas em plantão e lançamento de horas.</p>
        <span class="credito-card autor-card" role="link" tabindex="0" title="Ver o perfil da Debora Sampaio"
              onclick="event.preventDefault(); event.stopPropagation(); location.href='/perfil/debora'"><img src="/foto-usuario/debora" alt="" onerror="this.remove()">por Debora Sampaio</span>
      </a>"""

_CARD_FERIAS_HTML = """<a class="card-hub" href="/ferias" style="--accent-card:#4cc9f0">
        <div class="icone" style="background:rgba(76,201,240,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2"/>
            <path d="M3 9h18M8 2v4M16 2v4"/>
            <path d="M8 14l2 2 4-4"/>
          </svg>
        </div>
        <h2>Calendário de Férias</h2>
        <p>Visualização das férias já agendadas e aprovadas da equipe.</p>
      </a>"""

# Quem não é admin vê o item da Gestão de equipe trancado, como "Restrito" (3.0.7.0); a seção nem entra no HTML dele
_ITEM_MENU_GESTAO_RESTRITO_HTML = """<button class="item-menu restrito" type="button" aria-disabled="true" title="Restrito a administradores"
          onclick="mostrarToastHub('Gestão de equipe é restrita a administradores.')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>
          <span>Gestão de equipe<span class="sub-item">Só administradores</span></span><span class="selo-restrito">Restrito</span>
        </button>"""

# Seção "Gestão de equipe" do início (2.35.7.0): só entra no HTML pra administrador.
_ITEM_MENU_GESTAO_HTML = """<button class="item-menu" data-secao="gestao" onclick="trocarSecao('gestao')">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>
          <span>Gestão de equipe<span class="sub-item">Indicadores e administração</span></span><span class="qtd" id="qtd-gestao"></span>
        </button>"""

_SECAO_GESTAO_HTML = """      <section class="secao-mural" id="secao-gestao">
        <div class="topo-secao">
          <div><h1>Gestão de equipe</h1><div class="sub">Como a equipe está no mês e as ferramentas de administração.</div></div>
          <div class="filtro-equipe" id="filtro-equipe" role="group" aria-label="Equipe dos indicadores">
            <button class="ativo" data-equipe="" onclick="filtrarGestao('')">Ambos</button>
            <button data-equipe="Suporte" onclick="filtrarGestao('Suporte')">Suporte</button>
            <button data-equipe="Monitoramento" onclick="filtrarGestao('Monitoramento')">Monitoramento</button>
          </div>
        </div>
        <div class="indicadores-mural">
          <div class="ind carregando" id="ind-eq-horas" style="--cor-ind:#2db8cf">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>Horas da equipe</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div><div class="barra"><span></span></div>
          </div>
          <div class="ind carregando" id="ind-eq-tickets" style="--cor-ind:#e8a33d">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16v3a2 2 0 0 0 0 4v3H4v-3a2 2 0 0 0 0-4z"/></svg>Tickets da equipe</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div>
          </div>
          <div class="ind carregando" id="ind-eq-pessoas" style="--cor-ind:#b389f9">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/><circle cx="17" cy="9" r="2.4"/></svg>Pessoas ativas</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div>
          </div>
          <div class="ind carregando" id="ind-eq-fora" style="--cor-ind:#4cc9f0">
            <div class="rotulo"><svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="17" rx="2"/><path d="M3 9h18M8 2v4M16 2v4"/></svg>Fora hoje</div>
            <div class="valor">--</div><div class="detalhe">&nbsp;</div>
          </div>
        </div>
        <div class="fora-hoje" id="fora-hoje"></div>
        <h3 class="titulo-grade">Ferramentas de gestão</h3>
        <div class="grade-hub" data-grade="gestao">
__CARDS_GESTAO__
        </div>
      </section>"""



# Cards com acesso restrito - cada um só aparece no HTML pra quem tem a
# permissão correspondente (mesmo critério usado pelas rotas em
# do_GET, ver _tem_acesso_* e checagem de sessao["admin"]). Antes esses
# cards apareciam pra todo mundo e só bloqueavam o acesso no clique;
# agora ficam ocultos de quem não pode acessar, junto com os cards de
# Dados Sensíveis logo abaixo que já seguiam esse padrão.
_CARD_INDICADORES_MOVIDESK_HTML = """<a class="card-hub" href="/indicadores-movidesk" style="--accent-card:#e8a33d">
        <div class="icone" style="background:rgba(232,163,61,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v18h18"/>
            <path d="M7 15l4-5 3 3 5-7"/>
          </svg>
        </div>
        <h2>Indicadores Movidesk</h2>
        <p>Escalonamentos, dúvidas e sincronização - métricas direto do Movidesk.</p>
      </a>"""


_CARD_AUTOMACAO_MOVIDESK_HTML = """<a class="card-hub" href="/automacao-movidesk" style="--accent-card:#b0cb1c">
        <div class="icone" style="background:rgba(176,203,28,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 13v-1a8 8 0 0 1 16 0v1"/>
            <rect x="2.5" y="13" width="4" height="6" rx="1.5"/>
            <rect x="17.5" y="13" width="4" height="6" rx="1.5"/>
            <path d="M19.5 19v1a3 3 0 0 1-3 3h-3"/>
          </svg>
        </div>
        <h2>Automação Movidesk</h2>
        <p>Controle de sincronização - NOC, Satisfação, Uptime, GMUD, Jira e outras automações ainda em construção.</p>
      </a>"""


_CARD_RELATORIOS_CLIENTE_A_HTML = """<a class="card-hub" href="/relatorios-cliente_a" style="--accent-card:#dcdcaa">
        <div class="icone" style="background:rgba(220,220,170,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 20V10"/><path d="M12 20V4"/><path d="M20 20v-7"/><path d="M2 20h20"/>
          </svg>
        </div>
        <h2>Relatórios ClienteA</h2>
        <p>Extração de relatórios de notas e canceladas do cliente ClienteA.</p>
      </a>"""


_CARD_DASH_FINANCEIRO_HTML = """<a class="card-hub" href="/dash-financeiro" style="--accent-card:#22c55e">
        <div class="icone" style="background:rgba(220,220,170,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3v18h18"/>
            <path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>
          </svg>
        </div>
        <h2>Atualização Dash Financeiro</h2>
        <p>Contagem mensal de documentos por cliente (NFe, CTe, NFCe, CFe, NFSe, MDFe, ClienteK, SaaS) pro Power BI.</p>
      </a>"""


_CARD_MANUTENCAO_ALERTAS_HTML = """<a class="card-hub" href="/manutencao-alertas" style="--accent-card:#97a2a8">
        <div class="icone" style="background:rgba(151,162,168,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <ellipse cx="12" cy="5" rx="8" ry="3"/>
            <path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>
            <path d="M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>
          </svg>
        </div>
        <h2>Manutenção de Alertas em Banco</h2>
        <p>Criação e gerenciamento dos alertas automáticos configurados em CONFIGURACOES_ALERTA.</p>
      </a>"""


_CARD_MANUTENCAO_REJEICOES_HTML = """<a class="card-hub" href="/manutencao-rejeicoes" style="--accent-card:#ce9178">
        <div class="icone" style="background:rgba(206,145,120,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M9 9l6 6M15 9l-6 6"/>
          </svg>
        </div>
        <h2>Manutenção Rejeições em Banco</h2>
        <p>Criação e gerenciamento das rejeições automáticas configuradas em CONFIGURACOES_REJEICAO.</p>
      </a>"""


_CARD_MANUTENCAO_RELATORIOS_HTML = """<a class="card-hub" href="/manutencao-relatorios" style="--accent-card:#89b4d8">
        <div class="icone" style="background:rgba(137,180,216,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/>
            <path d="M14 3v6h6M9 13h6M9 17h6M9 9h1"/>
          </svg>
        </div>
        <h2>Manutenção de Relatórios em Banco</h2>
        <p>Criação e gerenciamento dos relatórios automáticos configurados em CONFIGURACOES_RELATORIO.</p>
      </a>"""


_CARD_DASHBOARDS_CLIENTES_HTML = """<a class="card-hub" href="/dashboards-clientes" style="--accent-card:#f5a3d0">
        <div class="icone" style="background:rgba(245,163,208,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="9" rx="1"/>
            <rect x="14" y="3" width="7" height="5" rx="1"/>
            <rect x="14" y="12" width="7" height="9" rx="1"/>
            <rect x="3" y="16" width="7" height="5" rx="1"/>
          </svg>
        </div>
        <h2>Dashboards por Cliente <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>Escolha um cliente e um produto pra ver os indicadores específicos dele.</p>
      </a>"""


_CARD_FEEDBACKS_HTML = """<a class="card-hub" href="/feedbacks" style="--accent-card:#ffb347">
        <div class="icone" style="background:rgba(255,179,71,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            <path d="M8 10h8M8 14h5"/>
          </svg>
        </div>
        <h2>Feedbacks e Alinhamentos</h2>
        <p>Individual, em grupo ou Alinhamento Geral - registro privado, visível só pra quem tem essa permissão.</p>
      </a>"""


_CARD_HORAS_TRABALHADAS_HTML = """<a class="card-hub" href="/horas-trabalhadas" style="--accent-card:#4ec9b0">
        <div class="icone" style="background:rgba(78,201,176,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="9"/>
            <path d="M12 7v5l3 3"/>
          </svg>
        </div>
        <h2>Horas Trabalhadas</h2>
        <p>Apontamentos de horas por analista, direto do banco do Movidesk, filtrável por dia ou mês.</p>
      </a>"""


_CARD_LOGS_HTML = """<a class="card-hub" href="/logs" style="--accent-card:#9cdcfe">
        <div class="icone" style="background:rgba(156,220,254,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16v16H4z"/>
            <path d="M8 9h8M8 13h8M8 17h5"/>
          </svg>
        </div>
        <h2>Logs</h2>
        <p>Log de execução isolado por card - um arquivo por automação, salvos em logs/.</p>
      </a>"""


# Cards de Dados Sensíveis (String Connections + Criptografia de Dados
# Sensíveis) - mesmo padrão acima, só que continuam morando na página 2
# (montada à parte em _montar_hub_html) porque ficam sempre como os
# DOIS ÚLTIMOS cards, pedido explícito.
_CARD_CHECKLISTS_HTML = """<div class="card-hub bloqueado" style="--accent-card:#e0b354">
        <div class="icone" style="background:rgba(224,179,84,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="3" width="14" height="18" rx="2"/>
            <path d="M9 3v2a1 1 0 0 0 1 1h4a1 1 0 0 0 1-1V3"/>
            <path d="M8.5 12l1.5 1.5 3-3M8.5 17l1.5 1.5"/>
          </svg>
        </div>
        <h2>Manutenção de Checklists</h2>
        <p>Criação e gerenciamento de checklists operacionais.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """


# Indicadores Mensais (2.33.7.0, era o card "Considerar/Desconsiderar Pesquisa
# de Satisfação"): Avaliação de Efetividade e NOC Pendente; o considerar/desconsiderar
# tickets vira a terceira aba. Só aparece pra admin com pode_indicadores_mensais.
_CARD_INDICADORES_MENSAIS_HTML = """<a class="card-hub" href="/indicadores-mensais" style="--accent-card:#ff8fa3">
        <div class="icone" style="background:rgba(255,143,163,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="17" rx="2"/>
            <path d="M3 9h18M8 2v4M16 2v4"/>
            <path d="M8 14l2.5 2.5L16 12"/>
          </svg>
        </div>
        <h2>Indicadores Mensais</h2>
        <p>Fechamento do mês no Movidesk: avaliação de efetividade dos tickets e justificativa do NOC fora do prazo.</p>
      </a>"""


# Reprocessamento CTe2 (2.35.4.0): automação do Caio Peixoto trazida pro PDA.
# Só aparece pra quem tem pode_reprocessamento_cte2.
_CARD_REPROCESSAMENTO_CTE2_HTML = """<a class="card-hub" href="/reprocessamento-cte2" style="--accent-card:#60a5fa">
        <div class="icone" style="background:rgba(96,165,250,.13)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>
            <path d="M14 3v5h5"/>
            <path d="M15.5 14a3.5 3.5 0 1 1-1-2.5"/>
            <path d="M15.5 10.5v2h-2"/>
          </svg>
        </div>
        <h2>Reprocessamento CTe2</h2>
        <p>Acha CT-es parados e pede o reprocessamento pela API, com confirmação em dois ciclos.</p>
        <span class="credito-card autor-card" role="link" tabindex="0" title="Ver o perfil do Caio Peixoto"
              onclick="event.preventDefault(); event.stopPropagation(); location.href='/perfil/caio.peixoto'"><img src="/foto-usuario/caio.peixoto" alt="" onerror="this.remove()">por Caio Peixoto</span>
      </a>"""


# Beta desde a 3.2.1.0 (era "em construção"): tratativa guiada dos NNUs do ClienteI, pra todo mundo
_CARD_NNU_ENCHANCED_HTML = """<a class="card-hub" href="/nnu-enchanced" style="--accent-card:#7fd8a6">
        <div class="icone" style="background:rgba(127,216,166,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12a9 9 0 1 1-3.5-7.1"/>
            <path d="M21 3v6h-6"/>
          </svg>
        </div>
        <h2>NNU Enchanced <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>Tratativa guiada dos NNUs do ClienteI (nota offline, prazo de 7 dias, chave e XMLs) e as automações, como o status 20 → 15.</p>
      </a>
      """


# Beta (3.0.7.0, era "em construção" na 3.0.5.0), pra todo mundo: ranks por produto (bronze, prata e
# ouro por pessoa), que vão liberar as insígnias de Rank Ouro (desenhadas, ainda "em breve").
_CARD_RANKS_PRODUTOS_HTML = """<a class="card-hub" href="/ranks-produtos" style="--accent-card:#eab308">
        <div class="icone" style="background:rgba(234,179,8,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 21h8M12 17v4"/>
            <path d="M7 4h10v5a5 5 0 0 1-10 0z"/>
            <path d="M7 6H4.5a2.5 2.5 0 0 0 2.6 3.5M17 6h2.5a2.5 2.5 0 0 1-2.6 3.5"/>
          </svg>
        </div>
        <h2>Rankings</h2>
        <p>Os placares da equipe: ranks bronze, prata, ouro e Master por produto e o leaderboard de palminhas, com insígnias pra quem se destacar.</p>
      </a>
      """


# Em construção (2.35.3.0), só pra administrador: geração de IANs.
_CARD_GERACAO_IANS_HTML = """<div class="card-hub bloqueado" style="--accent-card:#f97316">
        <div class="icone" style="background:rgba(249,115,22,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/>
            <path d="M14 3v5h5"/>
            <path d="M9 13h6M9 17h4"/>
          </svg>
        </div>
        <h2>Geração de IANs</h2>
        <p>Geração das IANs direto pelo painel.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """


_CARD_DIRECIONAMENTO_WEBMONITORS_HTML = """<a class="card-hub" href="/direcionamento-webmonitors" style="--accent-card:#5eead4">
        <div class="icone" style="background:rgba(94,234,212,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="14" rx="2"/>
            <path d="M8 21h8M12 17v4"/>
            <path d="M7 9l3 3-3 3M13 15h4"/>
          </svg>
        </div>
        <h2>Central de Monitores</h2>
        <p>Acesso rápido aos monitores fiscais de cada cliente, organizados por tipo de documento.</p>
        <span class="credito-card autor-card" role="link" tabindex="0" title="Ver o perfil do Wagner Faria"
              onclick="event.preventDefault(); event.stopPropagation(); location.href='/perfil/wagner.faria'"><img src="/foto-usuario/wagner.faria" alt="" onerror="this.remove()">por Wagner Faria</span>
      </a>"""


_CARD_MANUTENCAO_USUARIOS_HTML = """<a class="card-hub" href="/manutencao-usuarios" style="--accent-card:#b389f9">
        <div class="icone" style="background:rgba(179,137,249,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="9" cy="8" r="3"/>
            <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
            <circle cx="17" cy="9" r="2.4"/>
            <path d="M15.5 14.2c2.4.4 4.3 2.3 4.5 4.8"/>
          </svg>
        </div>
        <h2>Usuários</h2>
        <p>Login no PDA, permissões, vínculo com o Movidesk e cadastro/desativação em produção - tudo em um só lugar.</p>
      </a>
      """


_CARDS_DADOS_SENSIVEIS_HTML = """<a class="card-hub" href="/config-seguro" style="--accent-card:#569cd6">
        <div class="icone" style="background:rgba(86,156,214,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="5" y="11" width="14" height="9" rx="2"/>
            <path d="M8 11V7a4 4 0 0 1 8 0v4"/>
          </svg>
        </div>
        <h2>Criptografia de Dados Sensíveis</h2>
        <p>Credenciais sensíveis cifradas com Fernet (config.dat), em vez de texto puro nos .env.</p>
      </a>
      <a class="card-hub" href="/string-connections" style="--accent-card:#c586c0">
        <div class="icone" style="background:rgba(197,134,192,.15)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="7" width="18" height="10" rx="2"/>
            <path d="M7 12h.01M11 12h6"/>
          </svg>
        </div>
        <h2>String Connections</h2>
        <p>Conexões de banco reutilizáveis por cliente e produto, pra usar na Manutenção de Alertas.</p>
      </a>"""


# Busca de cards no cabeçalho do início (3.1.0.0): entra no __BUSCA_NAVBAR__ da navbar só no hub
_BUSCA_NAVBAR_HTML = """
      <div class="busca-global" id="busca-global">
        <div class="campo-busca">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>
          <input type="search" id="busca-cards" placeholder="Buscar um card do painel... (ex.: ClienteA, férias, ranks)" autocomplete="off"
                 aria-label="Buscar card" oninput="buscarCards()" onfocus="buscarCards()" onkeydown="teclarBusca(event)">
          <kbd>/</kbd>
        </div>
        <div class="resultados-busca" id="resultados-busca"></div>
      </div>
"""


# 3.3.1.0 · Serviços ADM: só pra quem tem a permissão pode_servicos_adm (vão pra Gestão de equipe)
_CARD_GMUD_HTML = """<a class="card-hub" href="/calendario-gmud" style="--accent-card:#0ea5e9">
        <div class="icone" style="background:rgba(14,165,233,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="17" rx="2"/>
            <path d="M3 9h18M8 2v4M16 2v4"/>
            <path d="M12 12v3l2 1.5"/>
          </svg>
        </div>
        <h2>Calendário de GMUD's <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>As GMUDs do mês num calendário, as vencidas e próximas a vencer pelo SLA e as próximas a serem executadas.</p>
      </a>"""

_CARD_INDICADORES_SERVICOS_HTML = """<div class="card-hub bloqueado" style="--accent-card:#a3e635">
        <div class="icone" style="background:rgba(163,230,53,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>
          </svg>
        </div>
        <h2>Indicadores Serviços</h2>
        <p>Os números da equipe de Serviços num lugar só.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

# 3.3.1.0 · Em breve pra todo mundo
_CARD_LONGNAMEJANITOR_HTML = """<a class="card-hub" href="/longnamejanitor" style="--accent-card:#e879f9">
        <div class="icone" style="background:rgba(232,121,249,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/>
            <path d="M10 11h4M10 15h4"/>
          </svg>
        </div>
        <h2>LongNameJanitor ClienteQ <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>Limpa as pastas de integração da ClienteQ: nome longo na Processar e os processados do CNPJ, com histórico e modo simulação.</p>
      </a>"""

# 3.3.9.0 · Operações/Serviços, em construção pra todo mundo
_CARD_ABERTURA_GMUD_HTML = """<div class="card-hub bloqueado" style="--accent-card:#f59e0b">
        <div class="icone" style="background:rgba(245,158,11,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="16" height="17" rx="2"/>
            <path d="M8 2v4M16 2v4M4 10h16M12 13v5M9.5 15.5h5"/>
          </svg>
        </div>
        <h2>Abertura de GMUD's</h2>
        <p>Abrir uma GMUD pelo PDA, com os dados que o Movidesk pede, sem sair do painel.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

_CARD_LIMPEZA_MAQUINAS_HTML = """<div class="card-hub bloqueado" style="--accent-card:#fb7185">
        <div class="icone" style="background:rgba(251,113,133,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="12" rx="2"/>
            <path d="M8 20h8M12 16v4"/>
            <path d="M8 10l2 2 4-4"/>
          </svg>
        </div>
        <h2>Limpeza de Máquinas</h2>
        <p>Limpeza das máquinas pelo diretório de cada servidor, com um relatório do que foi feito em cada uma.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

_CARD_VERSOES_RECENTES_HTML = """<div class="card-hub bloqueado" style="--accent-card:#38bdf8">
        <div class="icone" style="background:rgba(56,189,248,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2l3 6 6 .9-4.5 4.3 1 6.3L12 16.8 6.5 19.5l1-6.3L3 8.9 9 8z"/>
          </svg>
        </div>
        <h2>Versões mais recentes</h2>
        <p>As versões mais recentes, atualizadas e testadas pelo Dev, de cada produto.</p>
        <span class="tag-em-breve">Em construção</span>
      </div>
      """

# 3.3.1.0 · só administrador, em beta
# 3.4.3.0 · beta, só administrador: consulta um banco e avisa no Teams quando aparece consumo indevido
_CARD_CONSUMO_INDEVIDO_HTML = """<a class="card-hub" href="/consumo-indevido" style="--accent-card:#f43f5e">
        <div class="icone" style="background:rgba(244,63,94,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>
          </svg>
        </div>
        <h2>Consumo Indevido <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>Monitora o banco atrás de consumo indevido e avisa no Teams assim que aparece um caso novo.</p>
      </a>"""

_CARD_FLUXOGRAMA_HTML = """<a class="card-hub" href="/fluxograma-pda" style="--accent-card:#34d399">
        <div class="icone" style="background:rgba(52,211,153,.12)">
          <svg viewBox="0 0 24 24" fill="none" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="6" height="5" rx="1.5"/><rect x="15" y="3" width="6" height="5" rx="1.5"/><rect x="9" y="16" width="6" height="5" rx="1.5"/>
            <path d="M6 8v3h12V8M12 11v5"/>
          </svg>
        </div>
        <h2>Fluxograma do PDA <span class="tag-em-breve" style="margin-left:4px">Beta</span></h2>
        <p>Mapa interativo de tudo que o PDA faz e com quem conversa: servidor, áreas, dados e sistemas de fora.</p>
      </a>"""
