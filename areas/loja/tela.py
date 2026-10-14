"""Tela da Loja de Palminhas (3.3.7.0, /loja). Só texto; a regra fica em logica.py e os desenhos em telas/loja_wallpapers.py."""

_LOJA_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Loja de Palminhas</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo.conteudo-loja { max-width: 1180px; }
  .cab-loja { display: flex; gap: 18px; align-items: stretch; flex-wrap: wrap; margin-bottom: 18px; }
  .cab-loja .tit { flex: 1; min-width: 280px; }
  .cab-loja h1 { font-size: 26px; margin: 0 0 4px; font-weight: 800; background: linear-gradient(90deg, #f2b705, #fb923c); -webkit-background-clip: text; background-clip: text; color: transparent; }
  .cab-loja .sub { color: var(--fg-dim); font-size: 13.5px; max-width: 560px; line-height: 1.5; }
  .cofre { min-width: 280px; flex: 0 1 360px; box-sizing: border-box; border-radius: 16px; padding: 14px 18px; border: 1px solid rgba(242,183,5,.35);
    background: radial-gradient(circle at 100% 0%, rgba(242,183,5,.22), transparent 55%), var(--bg-panel); }
  .cofre .rot { font-size: 11px; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; color: var(--fg-dim); }
  .cofre .val { font-size: 32px; font-weight: 900; line-height: 1.15; }
  .cofre .det { font-size: 12px; color: var(--fg-dim); }
  .cofre .rank { margin-top: 8px; font-size: 11.5px; color: var(--fg); display: flex; gap: 6px; align-items: flex-start; border-top: 1px solid var(--border); padding-top: 8px; }
  .abas-loja { display: flex; gap: 6px; flex-wrap: wrap; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
  .abas-loja button { font: inherit; font-size: 13.5px; font-weight: 800; border: 0; background: none; color: var(--fg-dim); padding: 10px 14px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; }
  .abas-loja button.ativo { color: var(--fg); border-color: #f2b705; }
  .abas-loja button.eventos { color: #a77ff0; } .abas-loja button.eventos.ativo { color: var(--fg); border-color: #b47cff; }
  .vitrine-lj { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 16px; }
  .item-lj { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; overflow: hidden; display: flex; flex-direction: column; transition: transform .15s, border-color .15s; }
  .item-lj:hover { transform: translateY(-3px); border-color: var(--border-forte); }
  .item-lj .prev, .ev-lj .prev { position: relative; }
  .item-lj .prev { height: 120px; } .ev-lj .prev { height: 150px; }
  .item-lj .prev > .lj-wp, .ev-lj .prev > .lj-wp { position: absolute; inset: 0; }
  .item-lj .info, .ev-lj .info { padding: 12px 14px 14px; display: flex; flex-direction: column; gap: 3px; flex: 1; }
  .item-lj .tipo { font-size: 10.5px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--fg-dim); }
  .item-lj .nome { font-size: 16px; font-weight: 900; }
  .item-lj .desc, .ev-lj .desc { font-size: 12.5px; color: var(--fg-dim); flex: 1; line-height: 1.45; }
  .rodape-lj { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
  .preco-lj { font-weight: 900; font-size: 15px; } .preco-lj.gratis { color: var(--lime); font-size: 13px; }
  .falta-lj { font-size: 11.5px; color: var(--fg-dim); }
  .selo-lj { position: absolute; top: 9px; left: 9px; z-index: 3; font-size: 10.5px; font-weight: 900; border-radius: 99px; padding: 2px 9px; }
  .selo-lj.meu { background: var(--lime); color: #0b0f14; } .selo-lj.evento { background: #b47cff; color: #1a0d2b; }
  .banner-eventos { position: relative; overflow: hidden; border-radius: 16px; padding: 18px 22px; margin-bottom: 16px; border: 1px solid rgba(180,124,255,.35);
    background: radial-gradient(circle at 90% 0%, rgba(242,183,5,.18), transparent 45%), linear-gradient(120deg, rgba(91,52,120,.35), rgba(26,17,36,.2)), var(--bg-panel); }
  .banner-eventos h3 { margin: 0 0 4px; font-size: 18px; } .banner-eventos p { margin: 0; font-size: 13px; color: var(--fg-dim); max-width: 680px; line-height: 1.5; }
  .eventos-lj { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
  .ev-lj { background: var(--bg-panel); border: 1px solid rgba(180,124,255,.28); border-radius: 18px; overflow: hidden; display: flex; flex-direction: column; }
  .ev-lj .evento { font-size: 11px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: #a77ff0; }
  .ev-lj .nome { font-size: 18px; font-weight: 900; }
  .ev-lj .status { margin-top: 10px; display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
  .pill-lj { font-size: 11.5px; font-weight: 800; border-radius: 99px; padding: 3px 10px; background: rgba(var(--tinta), .07); color: var(--fg-dim); }
  .pill-lj.ok { background: rgba(176,203,28,.16); color: var(--lime); } .pill-lj.vivo { background: rgba(255,122,26,.16); color: #ff9a3d; } .pill-lj.breve { background: rgba(180,124,255,.18); color: #a77ff0; }
  .doces-lj { display: flex; gap: 3px; } .doces-lj i { width: 18px; height: 12px; border-radius: 4px; background: rgba(var(--tinta), .1); } .doces-lj i.ok { background: linear-gradient(90deg, #ff7a1a, #9b5de5); }
  .ev-lj.bloqueado .prev::after { content: "🔒"; position: absolute; inset: 0; display: grid; place-items: center; font-size: 28px; background: rgba(5,8,12,.5); z-index: 2; }
  .ev-lj.proximo { border-style: dashed; opacity: .75; } .ev-lj.proximo .prev { display: grid; place-items: center; font-size: 34px; letter-spacing: 6px; background: repeating-linear-gradient(-45deg, rgba(var(--tinta), .04) 0 10px, transparent 10px 20px); }
  .vazio-lj { color: var(--fg-dim); font-size: 13px; padding: 16px 0; }
  .ganhar-lj { margin-top: 22px; display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }
  .ganhar-lj div { font-size: 12.5px; color: var(--fg-dim); border: 1px dashed var(--border-forte); border-radius: 12px; padding: 11px 13px; line-height: 1.45; }
  .ganhar-lj b { color: var(--fg); display: block; margin-bottom: 2px; }
  .conta-lj { margin: 12px 0; border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; font-size: 13.5px; }
  .conta-lj div { display: flex; justify-content: space-between; padding: 3px 0; } .conta-lj .tot { border-top: 1px solid var(--border); margin-top: 4px; padding-top: 7px; font-weight: 900; }
  .erro-lj { color: var(--erro); font-size: 12.5px; margin-bottom: 10px; }
</style>
__LOJA_WALLPAPERS__
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-loja" id="app-loja">
    <div class="cab-loja">
      <div class="tit"><h1>Loja de Palminhas</h1>
        <div class="sub">Cada palminha que você recebe na Comunidade vira moeda aqui. Troque por wallpapers pro seu perfil e pro seu cartão da Comunidade.</div></div>
      <div class="cofre"><div class="rot">Seu saldo na Loja</div><div class="val" id="saldo-lj">👏 ...</div><div class="det" id="det-lj"></div>
        <div class="rank">🏆 <span id="rank-lj">Gastar não tira nada do seu ranking de palminhas.</span></div></div>
    </div>
    <div class="abas-loja" role="tablist">
      <button type="button" data-aba="vitrine" class="ativo">🛍️ Vitrine</button>
      <button type="button" data-aba="eventos" class="eventos">✨ Eventos</button>
      <button type="button" data-aba="meus">Meus itens</button>
    </div>
    <div id="conteudo-loja"><div class="vazio-lj">Carregando a Loja...</div></div>
    <div class="ganhar-lj">
      <div><b>👏 Como ganhar palminhas</b>Quando os colegas batem palma nos seus acontecimentos da Comunidade: aniversário, tempo de casa, insígnia, promoção, publicação.</div>
      <div><b>🏆 O ranking não muda</b>O leaderboard conta todas as palminhas que você recebeu. Gastar na Loja só mexe no saldo daqui.</div>
      <div><b>✨ Eventos</b>Alguns itens não estão à venda: vêm de eventos (Halloween, GPTW...) e ficam com quem conquistou.</div>
    </div>
  </div>
  __FOOTER__
<script>
(function () {
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = n => String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  const dm = s => String(s || '').split('-').reverse().slice(0, 2).join('/');
  let L = null;
  let aba = new URLSearchParams(location.search).get('aba') || (location.hash || '').slice(1) || 'vitrine';
  if (['vitrine', 'eventos', 'meus'].indexOf(aba) === -1) aba = 'vitrine';

  function botaoItem(it) {
    if (it.usando) return '<button type="button" class="btn-lj uso">Em uso</button>';
    if (it.tem) return '<button type="button" class="btn-lj sec" data-usar="' + esc(it.id) + '">Usar</button>';
    if (it.aba !== 'vitrine') return '';
    if (L.saldo < it.preco) return '<span class="falta-lj">faltam ' + fmt(it.preco - L.saldo) + ' 👏</span>';
    return '<button type="button" class="btn-lj" data-comprar="' + esc(it.id) + '">Trocar</button>';
  }
  function cardItem(it) {
    const selo = it.tem ? '<span class="selo-lj meu">✓ Seu</span>' : (it.aba === 'eventos' ? '<span class="selo-lj evento">✨ Evento</span>' : '');
    const preco = it.tem || it.aba === 'eventos' ? '<span></span>' : (it.preco === 0 ? '<span class="preco-lj gratis">Grátis</span>' : '<span class="preco-lj">👏 ' + fmt(it.preco) + '</span>');
    return '<div class="item-lj"><div class="prev">' + selo + wallpaperLoja(it.id, it.id === 'iw26' ? 'limpo' : 'card') + '</div>'
      + '<div class="info"><span class="tipo">' + esc(it.tipo) + '</span><span class="nome">' + esc(it.nome) + '</span><span class="desc">' + esc(it.desc) + '</span>'
      + '<div class="rodape-lj">' + preco + botaoItem(it) + '</div></div></div>';
  }
  function cardEvento(it) {
    let status;
    if (it.estado === 'meu') status = '<span class="pill-lj ok">✓ Conquistado</span>' + botaoItem(it);
    else if (it.estado === 'breve') status = '<span class="pill-lj breve">Em breve</span><span class="falta-lj">Torcendo pela Empresa 🤞</span>';
    else if (it.estado === 'antes') status = '<span class="pill-lj">Começa em ' + dm(it.inicio) + '</span><span class="falta-lj">Os doces aparecem no dia</span>';
    else if (it.estado === 'encerrado') status = '<span class="pill-lj">Encerrado em ' + dm(it.fim) + '</span><span class="falta-lj">Não dá mais pra conseguir</span>';
    else {
      const n = L.doces.achados, t = L.doces.total;
      status = '<span class="pill-lj vivo">Acontecendo · até ' + dm(it.fim) + '</span><span class="doces-lj">'
        + Array.from({ length: t }, (_, i) => '<i class="' + (i < n ? 'ok' : '') + '"></i>').join('') + '</span><span class="falta-lj">' + n + ' de ' + t + ' doces</span>';
    }
    const periodo = it.inicio ? dm(it.inicio) + ' a ' + dm(it.fim) : 'quando sair o resultado';
    return '<div class="ev-lj' + (it.estado === 'breve' ? ' bloqueado' : '') + '"><div class="prev">' + wallpaperLoja(it.id, 'card') + '</div><div class="info">'
      + '<span class="evento">✨ ' + esc(it.evento) + ' · ' + periodo + '</span><span class="nome">' + esc(it.nome) + '</span><span class="desc">' + esc(it.desc) + '</span>'
      + '<div class="status">' + status + '</div></div></div>';
  }
  function desenhar() {
    document.getElementById('saldo-lj').textContent = '👏 ' + fmt(L.saldo);
    document.getElementById('det-lj').innerHTML = '<b>' + fmt(L.recebidas) + '</b> recebidas no total · <b>' + fmt(L.gastas) + '</b> gastas na Loja';
    document.getElementById('rank-lj').innerHTML = 'Gastar não tira nada do seu ranking: no leaderboard de palminhas você continua com <b>' + fmt(L.recebidas) + '</b>.';
    document.querySelectorAll('.abas-loja button').forEach(b => b.classList.toggle('ativo', b.dataset.aba === aba));
    const c = document.getElementById('conteudo-loja');
    if (aba === 'vitrine') c.innerHTML = '<div class="vitrine-lj">' + L.itens.filter(i => i.aba === 'vitrine').map(cardItem).join('') + '</div>';
    else if (aba === 'eventos') c.innerHTML = '<div class="banner-eventos"><h3>✨ Eventos</h3><p>Itens que só aparecem em datas especiais. <b>Não estão à venda</b>: você conquista participando (como a Caça aos Doces) ou ganha junto com a empresa (como o GPTW). Depois que o evento acaba, quem conquistou fica com o item pra sempre.</p></div>'
      + '<div class="eventos-lj">' + L.itens.filter(i => i.aba === 'eventos').map(cardEvento).join('')
      + '<div class="ev-lj proximo"><div class="prev">🎄🎂⚽</div><div class="info"><span class="evento">✨ Próximos eventos</span><span class="nome">Em breve</span><span class="desc">Natal, aniversário do PDA e o que mais vier. Cada evento traz um item novo.</span></div></div></div>';
    else c.innerHTML = '<div class="vitrine-lj">' + L.itens.filter(i => i.tem).map(cardItem).join('') + '</div>';
  }
  async function carregar() {
    try {
      const r = await fetch('/api/loja');
      if (r.status === 401) { location.href = '/login'; return; }
      L = await r.json();
      if (!L.ok) throw new Error(L.erro || 'erro');
      desenhar();
    } catch (e) {
      document.getElementById('conteudo-loja').innerHTML = '<div class="vazio-lj">Não foi possível abrir a Loja agora. Atualize a página em instantes.</div>';
    }
  }
  async function postar(url, campos) {
    const r = await fetch(url, { method: 'POST', body: new URLSearchParams(campos) });
    return r.json();
  }
  function abrirCompra(id) {
    const it = L.itens.find(i => i.id === id);
    if (!it) return;
    const t = document.createElement('template');
    t.innerHTML = '<div class="lj-fundo"><div class="lj-modal" role="dialog" aria-modal="true" aria-label="Trocar palminhas"><div class="prev">' + wallpaperLoja(id, 'card') + '</div><div class="corpo"><h4>Trocar por "' + esc(it.nome) + '"?</h4>'
      + '<div class="conta-lj"><div><span>Seu saldo na Loja</span><b>👏 ' + fmt(L.saldo) + '</b></div><div><span>Preço</span><b>− ' + fmt(it.preco) + '</b></div><div class="tot"><span>Fica com</span><span>👏 ' + fmt(L.saldo - it.preco) + '</span></div></div>'
      + '<p class="nota-lj">O item fica seu pra sempre. <b>Seu ranking de palminhas não muda</b>: lá continuam contando as ' + fmt(L.recebidas) + ' que você recebeu.</p>'
      + '<div class="erro-lj" hidden></div>'
      + '<div class="acoes-lj"><button type="button" class="btn-lj sec" data-fechar>Agora não</button><button type="button" class="btn-lj sec" data-so>Só trocar</button><button type="button" class="btn-lj" data-usarja>Trocar e usar</button></div></div></div></div>';
    const f = t.content.firstChild;
    document.body.appendChild(f);
    f.addEventListener('click', async ev => {
      if (ev.target === f || ev.target.hasAttribute('data-fechar')) { f.remove(); return; }
      const usarJa = ev.target.hasAttribute('data-usarja');
      if (!usarJa && !ev.target.hasAttribute('data-so')) return;
      f.querySelectorAll('button').forEach(b => { b.disabled = true; });
      const r = await postar('/api/loja/comprar', { id: id, usar: usarJa ? '1' : '' });
      if (!r.ok) {
        const e = f.querySelector('.erro-lj'); e.hidden = false; e.textContent = r.erro || 'Não deu pra trocar.';
        f.querySelectorAll('button').forEach(b => { b.disabled = false; });
        return;
      }
      L = r; f.remove(); desenhar();
    });
  }
  document.addEventListener('click', async ev => {
    const b = ev.target.closest('[data-comprar],[data-usar],.abas-loja button');
    if (!b) return;
    if (b.dataset.comprar) abrirCompra(b.dataset.comprar);
    else if (b.dataset.usar) {
      b.disabled = true;
      const r = await postar('/api/loja/usar', { id: b.dataset.usar });
      if (r.ok) { L = r; desenhar(); } else { b.disabled = false; alert(r.erro || 'Não deu pra trocar.'); }
    } else if (b.dataset.aba) { aba = b.dataset.aba; history.replaceState(null, '', '/loja?aba=' + aba); desenhar(); }
  });
  carregar();
})();
</script>
</body>
</html>
"""
