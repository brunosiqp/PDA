"""Tela NNU Enchanced (Beta, 3.2.1.0): tratativa guiada dos NNUs do ClienteI.

Segue o escopo que o Igor passou (05/10/2026), que cobre ~95% dos casos:
1. Existe nota posterior emitida offline?
   - Não: a nota online está no prazo de 7 dias pra gerar o NNU? No prazo, aguardar; fora, IND_STATUS_PROC = 10.
   - Sim: consultar no Monitor (CNPJ, série e número) e comparar a chave da offline com a do select do NNU;
     chaves diferentes = fazer a troca de chave.
2. As duas notas estão autorizadas e são a mesma transação (valor total e itens)? Qualquer diferença entre os
   XMLs = o NNU não processa e o IND_STATUS_PROC vai pra 10.
3. Duas rejeições depois de processar vão pro time ClienteI: 203 (emissor não habilitado) e certificado expirado
   (70018/30042).
Tudo roda no navegador (leitura da chave, prazo, comparação dos XMLs, mensagem pro time ClienteI); nada consulta nem
grava em banco. Só texto (HTML/CSS/JS); a montagem fica no alertas_gui.py.
"""


_NNU_ENCHANCED_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>NNU Enchanced</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" type="image/png" href="__FAVICON__">
<style>
__NAVBAR_CSS__
  .conteudo.conteudo-nnu { max-width: 1180px; }
  .cab-nnu h1 { font-size: 26px; margin: 0 0 6px; font-weight: 800; display: flex; align-items: center; gap: 10px; }
  .cab-nnu .beta { font-size: 11px; font-weight: 800; letter-spacing: .08em; color: var(--lime); border: 1px solid currentColor; border-radius: 6px; padding: 2px 7px; }
  .cab-nnu .sub { color: var(--fg-dim); font-size: 13.5px; line-height: 1.5; max-width: 820px; }
  .grade-nnu { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(0, 1fr); gap: 18px; margin-top: 20px; align-items: start; }
  @media (max-width: 980px) { .grade-nnu { grid-template-columns: minmax(0, 1fr); } }
  /* 3.3.1.0: os resultados possíveis à vista desde o começo; o atual acende conforme a tratativa anda */
  .saidas-nnu { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 10px; margin-top: 16px; }
  .saida-nnu { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; background: rgba(var(--tinta), .02); opacity: .62;
               transition: opacity .2s, transform .2s, box-shadow .2s; border-top: 3px solid var(--cor); }
  .saida-nnu b { display: block; font-size: 12.5px; color: var(--cor); margin-bottom: 2px; }
  .saida-nnu span { font-size: 11.5px; color: var(--fg-dim); line-height: 1.4; }
  .saida-nnu.atual { opacity: 1; transform: translateY(-2px); box-shadow: 0 8px 24px -10px var(--cor); background: color-mix(in srgb, var(--cor) 10%, transparent); }
  @media (max-width: 760px) { .saidas-nnu { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
  .lado-nnu { position: sticky; top: 18px; }
  @media (max-width: 980px) { .lado-nnu { position: static; } }
  .lembretes-nnu { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
  .lembretes-nnu li { display: flex; gap: 9px; font-size: 12.5px; line-height: 1.45; color: var(--fg-dim); }
  .lembretes-nnu li span:first-child { flex: none; width: 20px; text-align: center; }
  .cartao-nnu { background: var(--bg-panel); border: 1px solid var(--border); border-radius: 16px; padding: 18px 20px; margin-bottom: 18px; }
  .cartao-nnu h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .07em; color: var(--fg-dim); margin: 0 0 12px; font-weight: 800; }
  .campo-nnu { width: 100%; box-sizing: border-box; background: rgba(var(--poco), .28); border: 1px solid var(--border); color: var(--fg);
               border-radius: 10px; padding: 10px 12px; font: inherit; font-size: 13.5px; }
  .campo-nnu.mono { font-family: Consolas, 'Cascadia Mono', monospace; letter-spacing: .02em; }
  textarea.campo-nnu { min-height: 110px; resize: vertical; font-family: Consolas, 'Cascadia Mono', monospace; font-size: 12px; }
  .rot-nnu { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--fg-dim); margin: 10px 0 5px; }
  .dica-nnu { font-size: 12px; color: var(--fg-dim); margin-top: 6px; line-height: 1.45; }
  .erro-nnu { color: var(--erro); font-size: 12.5px; margin-top: 6px; }
  .ok-nnu { color: var(--lime); font-size: 12.5px; margin-top: 6px; }
  .partes-chave { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 8px; margin-top: 10px; }
  .parte { background: rgba(var(--tinta), .04); border: 1px solid var(--border); border-radius: 10px; padding: 8px 10px; }
  .parte span { display: block; font-size: 10.5px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: .05em; }
  .parte b { font-size: 13.5px; font-family: Consolas, 'Cascadia Mono', monospace; }
  .parte button { margin-left: 6px; background: none; border: none; color: var(--teal); cursor: pointer; font-size: 11px; padding: 0; }
  /* passos do fluxo */
  .passo { border-left: 3px solid var(--border); padding: 4px 0 4px 16px; margin: 0 0 16px 6px; position: relative; }
  .passo::before { content: attr(data-n); position: absolute; left: -15px; top: 2px; width: 26px; height: 26px; border-radius: 50%; background: var(--bg-panel);
                   border: 2px solid var(--border); display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 800; color: var(--fg-dim); }
  .passo.ativo { border-left-color: var(--teal); }
  .passo.ativo::before { border-color: var(--teal); color: var(--teal); }
  .passo.feito { border-left-color: var(--lime); }
  .passo.feito::before { content: "✓"; border-color: var(--lime); color: var(--lime); }
  .passo h3 { font-size: 15px; margin: 2px 0 8px 8px; }
  .passo .corpo { margin-left: 8px; }
  .escolha { display: flex; gap: 8px; flex-wrap: wrap; }
  .escolha button { border: 1px solid var(--border); background: rgba(var(--tinta), .04); color: var(--fg); font: inherit; font-size: 13px; font-weight: 700;
                    border-radius: 10px; padding: 8px 16px; cursor: pointer; }
  .escolha button.sel { background: var(--teal); border-color: var(--teal); color: #071016; }
  .linha2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
  @media (max-width: 620px) { .linha2 { grid-template-columns: 1fr; } }
  /* veredito */
  .veredito { border-radius: 14px; padding: 16px 18px; border: 1px solid var(--border); background: rgba(var(--tinta), .04); }
  .veredito .tit { font-size: 17px; font-weight: 800; margin-bottom: 6px; }
  .veredito .txt { font-size: 13.5px; color: var(--fg-dim); line-height: 1.5; }
  .veredito.aguardar { border-color: rgba(232,163,61,.5); background: rgba(232,163,61,.08); } .veredito.aguardar .tit { color: #e8a33d; }
  .veredito.status10 { border-color: rgba(241,76,76,.5); background: rgba(241,76,76,.08); } .veredito.status10 .tit { color: var(--erro); }
  .veredito.processar { border-color: rgba(176,203,28,.5); background: rgba(176,203,28,.08); } .veredito.processar .tit { color: var(--lime); }
  .veredito.troca { border-color: rgba(45,184,207,.5); background: rgba(45,184,207,.08); } .veredito.troca .tit { color: var(--teal); }
  .acao-veredito { margin-top: 10px; display: flex; gap: 8px; flex-wrap: wrap; }
  .btn-nnu { border: none; background: var(--teal); color: #071016; font: inherit; font-weight: 800; font-size: 12.5px; border-radius: 9px; padding: 8px 14px; cursor: pointer; }
  .btn-nnu.sec { background: rgba(var(--tinta), .07); color: var(--fg); border: 1px solid var(--border); }
  /* comparação dos XMLs */
  table.dif { width: 100%; border-collapse: collapse; font-size: 12.5px; margin-top: 10px; }
  table.dif th, table.dif td { text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--border); vertical-align: top; }
  table.dif th { color: var(--fg-dim); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }
  table.dif td.dif-sim { color: var(--erro); font-weight: 700; }
  table.dif td.dif-nao { color: var(--lime); }
  .rejeicao { border: 1px solid var(--border); border-radius: 12px; padding: 10px 12px; margin-bottom: 10px; font-size: 12.5px; line-height: 1.45; }
  .rejeicao b { display: block; margin-bottom: 3px; }
  .rejeicao code { font-size: 11.5px; color: var(--fg-dim); }
  .mensagem-cliente_i { white-space: pre-wrap; font-family: Consolas, 'Cascadia Mono', monospace; font-size: 12px; background: rgba(var(--poco), .3);
                   border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; margin-top: 8px; }
  .toast-nnu { position: fixed; bottom: 22px; left: 50%; transform: translateX(-50%) translateY(20px); opacity: 0; background: var(--bg-panel); border: 1px solid var(--border);
               border-radius: 10px; padding: 10px 16px; font-size: 13px; transition: all .2s; pointer-events: none; z-index: 50; }
  .toast-nnu.mostrar { opacity: 1; transform: translateX(-50%) translateY(0); }
  /* abas (3.4.9.0): a tratativa guiada e cada automação de NNU */
  .abas-nnu { display: flex; gap: 6px; flex-wrap: wrap; margin: 18px 0 18px; border-bottom: 1px solid var(--border); }
  .aba-nnu { font: inherit; font-size: 13.5px; font-weight: 700; color: var(--fg-dim); background: none; border: 0; border-bottom: 2px solid transparent;
             padding: 9px 14px; margin-bottom: -1px; cursor: pointer; display: inline-flex; align-items: center; gap: 8px; border-radius: 10px 10px 0 0; }
  .aba-nnu:hover { color: var(--fg); background: rgba(var(--tinta), .04); }
  .aba-nnu.ativa { color: var(--fg); border-bottom-color: var(--teal); }
  .aba-nnu .tipo-aba { font-size: 10px; font-weight: 800; letter-spacing: .05em; text-transform: uppercase; color: var(--fg-dim);
                       border: 1px solid var(--border); border-radius: 99px; padding: 1px 7px; }
  .aba-nnu.ativa .tipo-aba { color: var(--teal); border-color: rgba(45,184,207,.5); }
  .sub-aba-nnu { color: var(--fg-dim); font-size: 13.5px; line-height: 1.5; max-width: 820px; margin-bottom: 4px; }
__NNU_AUTOMACAO_CSS__
</style>
</head>
<body>
__NAVBAR__
  <div class="conteudo conteudo-nnu">
    <div class="cab-nnu">
      <h1>NNU Enchanced <span class="beta">BETA</span></h1>
      <div class="sub">Tudo dos NNUs do ClienteI num lugar só: a tratativa guiada e as automações.</div>
    </div>

    <div class="abas-nnu" role="tablist">
      <button class="aba-nnu" role="tab" data-aba="tratativa" onclick="trocarAbaNnu('tratativa')">🧭 Tratativa guiada <span class="tipo-aba">Guia</span></button>
      <button class="aba-nnu" role="tab" data-aba="status-20-15" onclick="trocarAbaNnu('status-20-15')">🔁 Status 20 → 15 <span class="tipo-aba">Automação</span></button>
    </div>

    <div class="painel-aba-nnu" id="aba-nnu-tratativa">
    <div class="cab-nnu">
      <div class="sub-aba-nnu">Confere a nota posterior offline, o prazo de 7 dias, a chave e os XMLs, e diz o que fazer.
        Cobre a lógica de ~95% dos casos; situações pontuais continuam indo pro time ClienteI. Nada aqui consulta ou grava em banco.</div>
      <div class="saidas-nnu" aria-label="Resultados possíveis">
        <div class="saida-nnu" data-saida="aguardar" style="--cor:#e8a33d"><b>⏳ Aguardar</b><span>Sem nota offline e ainda dentro dos 7 dias.</span></div>
        <div class="saida-nnu" data-saida="troca" style="--cor:#2db8cf"><b>🔁 Troca de chave</b><span>A chave da offline não bate com a do select.</span></div>
        <div class="saida-nnu" data-saida="processar" style="--cor:#b0cb1c"><b>✅ Pode processar</b><span>As duas autorizadas e a mesma transação.</span></div>
        <div class="saida-nnu" data-saida="status10" style="--cor:#f14c4c"><b>⛔ IND_STATUS_PROC 10</b><span>Fora do prazo, notas diferentes ou não autorizadas.</span></div>
      </div>
    </div>

    <div class="grade-nnu">
      <div>
        <div class="cartao-nnu">
          <h2>Chave da nota online (do select do NNU)</h2>
          <input class="campo-nnu mono" id="chave-online" maxlength="60" placeholder="Cole a chave de 44 dígitos" oninput="atualizarTudo()">
          <div id="leitura-online"></div>
        </div>

        <div class="cartao-nnu">
          <h2>Tratativa</h2>
          <div class="passo" data-n="1" id="p1">
            <h3>Existe uma nota posterior emitida de forma offline?</h3>
            <div class="corpo">
              <div class="escolha" data-campo="temOffline">
                <button type="button" data-v="sim">Sim, existe</button>
                <button type="button" data-v="nao">Não existe</button>
              </div>
            </div>
          </div>

          <div class="passo" data-n="2" id="p-prazo" hidden>
            <h3>A nota online está dentro do prazo de 7 dias pra geração do NNU?</h3>
            <div class="corpo">
              <label class="rot-nnu" for="data-emissao">Data de emissão da nota online</label>
              <input type="date" class="campo-nnu" id="data-emissao" style="max-width:220px" oninput="atualizarTudo()">
              <div id="info-prazo"></div>
            </div>
          </div>

          <div class="passo" data-n="2" id="p-chave" hidden>
            <h3>Consulte a nota offline no Monitor e compare a chave</h3>
            <div class="corpo">
              <div class="dica-nnu" id="dica-monitor">Consulte no Monitor pelo CNPJ, série e número da nota (aparecem acima quando a chave online é colada).</div>
              <label class="rot-nnu" for="chave-offline">Chave da nota offline (do Monitor)</label>
              <input class="campo-nnu mono" id="chave-offline" maxlength="60" placeholder="Cole a chave de 44 dígitos da nota offline" oninput="atualizarTudo()">
              <div id="info-chave"></div>
            </div>
          </div>

          <div class="passo" data-n="3" id="p-xml" hidden>
            <h3>As duas notas estão autorizadas e são a mesma transação?</h3>
            <div class="corpo">
              <div class="dica-nnu">Cole os dois XMLs pra comparar sozinho (valor total, itens, autorização). Qualquer diferença mínima e o NNU não processa.</div>
              <div class="linha2">
                <div><label class="rot-nnu" for="xml-online">XML da nota online</label><textarea class="campo-nnu" id="xml-online" placeholder="&lt;nfeProc ...&gt;" oninput="atualizarTudo()"></textarea></div>
                <div><label class="rot-nnu" for="xml-offline">XML da nota offline</label><textarea class="campo-nnu" id="xml-offline" placeholder="&lt;nfeProc ...&gt;" oninput="atualizarTudo()"></textarea></div>
              </div>
              <div id="info-xml"></div>
              <div id="manual-xml">
                <div class="dica-nnu" style="margin-top:12px">Sem os XMLs? Responda conferindo no Monitor:</div>
                <label class="rot-nnu">As duas notas estão autorizadas?</label>
                <div class="escolha" data-campo="autorizadas"><button type="button" data-v="sim">Sim, as duas</button><button type="button" data-v="nao">Não</button></div>
                <label class="rot-nnu">Mesmo valor total e mesmos itens?</label>
                <div class="escolha" data-campo="mesmaTransacao"><button type="button" data-v="sim">Sim, idênticas</button><button type="button" data-v="nao">Tem diferença</button></div>
              </div>
            </div>
          </div>

          <div class="veredito" id="veredito"><div class="tit">Comece pela pergunta 1</div><div class="txt">Cole a chave da nota online e responda os passos.</div></div>
          <div class="acao-veredito">
            <button type="button" class="btn-nnu" onclick="copiarResumo()">Copiar resumo da tratativa</button>
            <button type="button" class="btn-nnu sec" onclick="recomecar()">Recomeçar</button>
          </div>
        </div>
      </div>

      <div class="lado-nnu">
        <div class="cartao-nnu">
          <h2>Deu rejeição ao processar o NNU?</h2>
          <div class="dica-nnu" style="margin:-4px 0 10px">Estas duas vão pro time ClienteI. Cole a mensagem abaixo que o PDA reconhece e monta o texto pra repassar:</div>
          <div class="rejeicao"><b>Emissor não habilitado (203)</b><code>Inutilização não homologada. 203 - Rejeicao: Emissor nao habilitado para emissao da NF-e</code></div>
          <div class="rejeicao"><b>Certificado expirado (70018 / 30042)</b><code>Erro ao solicitar inutilização. Exceção: Código: 70018. Descrição: Certificado inválido. Código: 30042. Descrição: O certificado está expirado...</code></div>
          <label class="rot-nnu" for="texto-rejeicao">Cole a rejeição que apareceu</label>
          <textarea class="campo-nnu" id="texto-rejeicao" style="min-height:80px" placeholder="Cole aqui a mensagem do processamento do NNU" oninput="analisarRejeicao()"></textarea>
          <div id="info-rejeicao"></div>
        </div>
        <div class="cartao-nnu">
          <h2>Lembretes</h2>
          <ul class="lembretes-nnu">
            <li><span>📅</span><span>Prazo do NNU: 7 dias contados da emissão da nota online.</span></li>
            <li><span>🔑</span><span>Chave da offline diferente da do select = troca de chave antes de seguir.</span></li>
            <li><span>🧾</span><span>Valor total e itens precisam ser idênticos nos dois XMLs.</span></li>
            <li><span>⛔</span><span>Fora do prazo, notas diferentes ou não autorizadas: IND_STATUS_PROC = 10.</span></li>
            <li><span>💬</span><span>Outras situações são pontuais: na dúvida, pergunte pro time ClienteI.</span></li>
          </ul>
        </div>
      </div>
    </div>
    </div>

    <div class="painel-aba-nnu" id="aba-nnu-status-20-15" hidden>
__NNU_AUTOMACAO_STATUS__
    </div>
  </div>
  <div class="toast-nnu" id="toast-nnu"></div>
  __FOOTER__
<script>
const UFS_NNU = {11: 'RO', 12: 'AC', 13: 'AM', 14: 'RR', 15: 'PA', 16: 'AP', 17: 'TO', 21: 'MA', 22: 'PI', 23: 'CE', 24: 'RN', 25: 'PB', 26: 'PE', 27: 'AL',
                 28: 'SE', 29: 'BA', 31: 'MG', 32: 'ES', 33: 'RJ', 35: 'SP', 41: 'PR', 42: 'SC', 43: 'RS', 50: 'MS', 51: 'MT', 52: 'GO', 53: 'DF'};
const TP_EMIS_NNU = {1: 'Normal', 2: 'Contingência FS-IA', 4: 'Contingência EPEC', 5: 'Contingência FS-DA', 6: 'Contingência SVC-AN', 7: 'Contingência SVC-RS', 9: 'Contingência off-line (NFC-e)'};
const estadoNNU = { temOffline: '', autorizadas: '', mesmaTransacao: '' };

function escN(t) { return String(t == null ? '' : t).replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c])); }
function toastN(t) { const el = document.getElementById('toast-nnu'); el.textContent = t; el.classList.add('mostrar'); clearTimeout(window._tN); window._tN = setTimeout(() => el.classList.remove('mostrar'), 2500); }
function copiarN(texto, aviso) {
  const ok = () => toastN(aviso || 'Copiado.');
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(texto).then(ok, () => copiarN2(texto, ok)); } else { copiarN2(texto, ok); }
}
function copiarN2(texto, ok) {
  const ta = document.createElement('textarea'); ta.value = texto; ta.style.position = 'fixed'; ta.style.opacity = '0';
  document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); ok(); } catch (e) { toastN('Selecione e copie com Ctrl+C.'); } ta.remove();
}

// chave de acesso: 44 dígitos = cUF(2) AAMM(4) CNPJ(14) modelo(2) série(3) número(9) tpEmis(1) código(8) DV(1)
function lerChave(bruta) {
  const chave = String(bruta || '').replace(/[^0-9]/g, '');
  if (!chave) return null;
  if (chave.length !== 44) return { erro: 'A chave tem ' + chave.length + ' dígitos; precisa ter 44.' };
  let soma = 0, peso = 2;
  for (let i = 42; i >= 0; i--) { soma += Number(chave[i]) * peso; peso = peso === 9 ? 2 : peso + 1; }
  const resto = soma % 11, dv = resto < 2 ? 0 : 11 - resto;
  const c = { chave, uf: UFS_NNU[Number(chave.slice(0, 2))] || chave.slice(0, 2), aamm: chave.slice(4, 6) + '/20' + chave.slice(2, 4),
              cnpj: chave.slice(6, 20), modelo: chave.slice(20, 22), serie: String(Number(chave.slice(22, 25))), numero: String(Number(chave.slice(25, 34))),
              tpEmis: Number(chave.slice(34, 35)), dvOk: dv === Number(chave[43]) };
  c.cnpjFmt = c.cnpj.replace(/^(..)(...)(...)(....)(..)$/, '$1.$2.$3/$4-$5');
  return c;
}
function htmlChave(c, rotulo) {
  if (!c) return '';
  if (c.erro) return '<div class="erro-nnu">' + escN(c.erro) + '</div>';
  const parte = (nome, valor, copiar) => '<div class="parte"><span>' + nome + '</span><b>' + escN(valor) + '</b>'
    + (copiar ? '<button type="button" onclick="copiarN(' + "'" + escN(copiar) + "'" + ', ' + "'" + nome + ' copiado.' + "'" + ')">copiar</button>' : '') + '</div>';
  return (c.dvOk ? '' : '<div class="erro-nnu">Dígito verificador não confere: confira se a chave foi colada inteira.</div>')
    + '<div class="partes-chave">' + parte('CNPJ', c.cnpjFmt, c.cnpj) + parte('Série', c.serie, c.serie) + parte('Número', c.numero, c.numero)
    + parte('Modelo', c.modelo === '65' ? '65 · NFC-e' : (c.modelo === '55' ? '55 · NF-e' : c.modelo)) + parte('UF', c.uf) + parte('Emissão', c.aamm)
    + parte('Tipo de emissão', TP_EMIS_NNU[c.tpEmis] || c.tpEmis) + '</div>';
}

// XML: lê sem depender do namespace (nfeProc ou NFe solto)
function lerXml(texto) {
  texto = String(texto || '').trim();
  if (!texto) return null;
  const doc = new DOMParser().parseFromString(texto, 'text/xml');
  if (doc.getElementsByTagName('parsererror').length) return { erro: 'Não deu pra ler esse XML.' };
  const um = (raiz, tag) => { const el = raiz.getElementsByTagNameNS('*', tag)[0]; return el ? el.textContent.trim() : ''; };
  const inf = doc.getElementsByTagNameNS('*', 'infNFe')[0];
  if (!inf) return { erro: 'Esse XML não tem infNFe.' };
  const itens = Array.from(doc.getElementsByTagNameNS('*', 'det')).map(det => {
    const prod = det.getElementsByTagNameNS('*', 'prod')[0] || det;
    return { n: det.getAttribute('nItem') || '', cProd: um(prod, 'cProd'), xProd: um(prod, 'xProd'), qCom: um(prod, 'qCom'), vUnCom: um(prod, 'vUnCom'), vProd: um(prod, 'vProd') };
  });
  const tot = doc.getElementsByTagNameNS('*', 'ICMSTot')[0] || doc;
  return { chave: (inf.getAttribute('Id') || '').replace(/^NFe/, ''), vNF: um(tot, 'vNF'), vProd: um(tot, 'vProd'), vDesc: um(tot, 'vDesc'),
           cStat: um(doc.getElementsByTagNameNS('*', 'protNFe')[0] || doc.createElement('x'), 'cStat'), itens };
}
function numIgual(a, b) { return a === b || (a !== '' && b !== '' && Math.abs(Number(a) - Number(b)) < 0.000001); }
function compararXmls(on, off) {
  const linhas = [];
  const add = (campo, a, b, igual) => linhas.push({ campo, a, b, dif: !igual });
  add('Valor total (vNF)', on.vNF, off.vNF, numIgual(on.vNF, off.vNF));
  add('Valor dos produtos', on.vProd, off.vProd, numIgual(on.vProd, off.vProd));
  add('Desconto', on.vDesc || '0', off.vDesc || '0', numIgual(on.vDesc || '0', off.vDesc || '0'));
  add('Quantidade de itens', String(on.itens.length), String(off.itens.length), on.itens.length === off.itens.length);
  const n = Math.max(on.itens.length, off.itens.length);
  for (let i = 0; i < n; i++) {
    const a = on.itens[i] || {}, b = off.itens[i] || {};
    ['cProd', 'qCom', 'vUnCom', 'vProd'].forEach(k => {
      const igual = k === 'cProd' ? (a[k] || '') === (b[k] || '') : numIgual(a[k] || '', b[k] || '');
      if (!igual) add('Item ' + (i + 1) + ' · ' + ({cProd: 'código', qCom: 'quantidade', vUnCom: 'valor unitário', vProd: 'valor'}[k]), a[k] || '·', b[k] || '·', false);
    });
  }
  return linhas;
}

function marcarEscolhas() {
  document.querySelectorAll('.escolha').forEach(g => g.querySelectorAll('button').forEach(b => b.classList.toggle('sel', estadoNNU[g.dataset.campo] === b.dataset.v)));
}
document.querySelectorAll('.escolha').forEach(g => g.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return;
  estadoNNU[g.dataset.campo] = estadoNNU[g.dataset.campo] === b.dataset.v ? '' : b.dataset.v;
  atualizarTudo();
}));

function diasEntre(a, b) { return Math.round((b - a) / 86400000); }
function dataBr(d) { return String(d.getDate()).padStart(2, '0') + '/' + String(d.getMonth() + 1).padStart(2, '0') + '/' + d.getFullYear(); }

let resumoAtual = '';
function atualizarTudo() {
  marcarEscolhas();
  const on = lerChave(document.getElementById('chave-online').value);
  document.getElementById('leitura-online').innerHTML = htmlChave(on);
  const s = estadoNNU, linhasResumo = [];
  if (on && !on.erro) linhasResumo.push('Nota online: ' + on.chave + ' (CNPJ ' + on.cnpjFmt + ', série ' + on.serie + ', número ' + on.numero + ')');
  document.getElementById('p1').classList.toggle('ativo', !s.temOffline);
  document.getElementById('p1').classList.toggle('feito', !!s.temOffline);
  document.getElementById('p-prazo').hidden = s.temOffline !== 'nao';
  document.getElementById('p-chave').hidden = s.temOffline !== 'sim';
  let veredito = null;

  if (s.temOffline === 'nao') {
    linhasResumo.push('Não existe nota posterior offline.');
    const valor = document.getElementById('data-emissao').value;
    const info = document.getElementById('info-prazo');
    document.getElementById('p-prazo').classList.toggle('ativo', !valor);
    document.getElementById('p-prazo').classList.toggle('feito', !!valor);
    if (valor) {
      const emissao = new Date(valor + 'T00:00:00'), limite = new Date(emissao); limite.setDate(limite.getDate() + 7);
      const hoje = new Date(); hoje.setHours(0, 0, 0, 0);
      const passados = diasEntre(emissao, hoje), restam = diasEntre(hoje, limite);
      info.innerHTML = '<div class="dica-nnu">Emitida há ' + passados + (passados === 1 ? ' dia' : ' dias') + ' · prazo até ' + dataBr(limite) + '.</div>';
      linhasResumo.push('Emissão da nota online: ' + dataBr(emissao) + ' (prazo do NNU até ' + dataBr(limite) + ').');
      veredito = restam >= 0
        ? { cls: 'aguardar', tit: 'Aguardar', txt: 'A nota ainda está no prazo de 7 dias pra gerar o NNU (' + (restam === 0 ? 'vence hoje' : (restam === 1 ? 'falta 1 dia' : 'faltam ' + restam + ' dias')) + ', até ' + dataBr(limite) + '). Nada a fazer agora.' }
        : { cls: 'status10', tit: 'Alterar o IND_STATUS_PROC para 10', txt: 'O prazo de 7 dias pra gerar o NNU acabou em ' + dataBr(limite) + ' e não existe nota posterior offline.' };
    } else { info.innerHTML = ''; }
  }

  if (s.temOffline === 'sim') {
    linhasResumo.push('Existe nota posterior offline.');
    const off = lerChave(document.getElementById('chave-offline').value);
    const info = document.getElementById('info-chave');
    document.getElementById('dica-monitor').innerHTML = on && !on.erro
      ? 'Consulte no Monitor: <b>CNPJ ' + escN(on.cnpjFmt) + '</b> · <b>série ' + escN(on.serie) + '</b> · <b>número ' + escN(on.numero) + '</b>.'
      : 'Consulte no Monitor pelo CNPJ, série e número da nota (aparecem acima quando a chave online é colada).';
    let trocaChave = false, chaveOk = false;
    if (off && !off.erro) {
      chaveOk = true;
      const avisos = [];
      if (!off.dvOk) avisos.push('<div class="erro-nnu">Dígito verificador da chave offline não confere.</div>');
      if (on && !on.erro) {
        if (on.cnpj !== off.cnpj || on.serie !== off.serie || on.numero !== off.numero) avisos.push('<div class="erro-nnu">Atenção: CNPJ, série ou número da offline não batem com a nota online. Confira se é a nota certa.</div>');
        trocaChave = on.chave !== off.chave;
        avisos.push(trocaChave ? '<div class="erro-nnu"><b>Chaves diferentes:</b> vai precisar fazer a troca de chave.</div>' : '<div class="ok-nnu">As chaves são iguais: não precisa trocar.</div>');
      }
      if (off.tpEmis !== 9) avisos.push('<div class="dica-nnu">O tipo de emissão dessa chave é "' + escN(TP_EMIS_NNU[off.tpEmis] || off.tpEmis) + '" (offline costuma ser 9).</div>');
      info.innerHTML = htmlChave(off) + avisos.join('');
      linhasResumo.push('Nota offline (Monitor): ' + off.chave + (trocaChave ? ' · chave diferente da do select: fazer troca de chave' : ' · mesma chave do select'));
    } else { info.innerHTML = off && off.erro ? '<div class="erro-nnu">' + escN(off.erro) + '</div>' : ''; }
    document.getElementById('p-chave').classList.toggle('ativo', !chaveOk);
    document.getElementById('p-chave').classList.toggle('feito', chaveOk);
    document.getElementById('p-xml').hidden = !chaveOk;

    if (chaveOk) {
      // XMLs colados: decide sozinho; sem eles, vale o que foi respondido à mão
      const xOn = lerXml(document.getElementById('xml-online').value), xOff = lerXml(document.getElementById('xml-offline').value);
      const infoXml = document.getElementById('info-xml');
      let autorizadas = s.autorizadas, mesma = s.mesmaTransacao;
      document.getElementById('manual-xml').hidden = !!(xOn && xOff && !xOn.erro && !xOff.erro);
      if (xOn && xOff && !xOn.erro && !xOff.erro) {
        const linhas = compararXmls(xOn, xOff), difs = linhas.filter(l => l.dif);
        const autOn = xOn.cStat === '100', autOff = xOff.cStat === '100';
        autorizadas = autOn && autOff ? 'sim' : 'nao';
        mesma = difs.length ? 'nao' : 'sim';
        infoXml.innerHTML = '<div class="' + (autorizadas === 'sim' ? 'ok-nnu' : 'erro-nnu') + '">Autorização: online ' + (xOn.cStat ? 'cStat ' + escN(xOn.cStat) : 'sem protocolo')
          + ' · offline ' + (xOff.cStat ? 'cStat ' + escN(xOff.cStat) : 'sem protocolo') + (autorizadas === 'sim' ? ' (as duas autorizadas)' : ' (precisa ser 100 nas duas)') + '</div>'
          + '<table class="dif"><thead><tr><th>Campo</th><th>Online</th><th>Offline</th><th></th></tr></thead><tbody>'
          + linhas.map(l => '<tr><td>' + escN(l.campo) + '</td><td>' + escN(l.a) + '</td><td>' + escN(l.b) + '</td><td class="' + (l.dif ? 'dif-sim">diferente' : 'dif-nao">igual') + '</td></tr>').join('')
          + '</tbody></table>' + (difs.length ? '<div class="erro-nnu">' + difs.length + (difs.length === 1 ? ' diferença encontrada.' : ' diferenças encontradas.') + '</div>' : '<div class="ok-nnu">Valor total e itens idênticos.</div>');
        linhasResumo.push('XMLs comparados: ' + (autorizadas === 'sim' ? 'as duas autorizadas' : 'nem as duas autorizadas') + '; ' + (difs.length ? difs.length + ' diferença(s): ' + difs.map(d => d.campo + ' (' + d.a + ' x ' + d.b + ')').join('; ') : 'valor total e itens idênticos') + '.');
      } else {
        infoXml.innerHTML = (xOn && xOn.erro ? '<div class="erro-nnu">XML online: ' + escN(xOn.erro) + '</div>' : '') + (xOff && xOff.erro ? '<div class="erro-nnu">XML offline: ' + escN(xOff.erro) + '</div>' : '');
        if (autorizadas) linhasResumo.push('Autorização conferida no Monitor: ' + (autorizadas === 'sim' ? 'as duas autorizadas' : 'nem as duas autorizadas') + '.');
        if (mesma) linhasResumo.push('Valor total e itens: ' + (mesma === 'sim' ? 'idênticos' : 'com diferença') + '.');
      }
      const respondido = autorizadas && mesma;
      document.getElementById('p-xml').classList.toggle('ativo', !respondido);
      document.getElementById('p-xml').classList.toggle('feito', !!respondido);
      if (autorizadas === 'nao' || mesma === 'nao') {
        veredito = { cls: 'status10', tit: 'Alterar o IND_STATUS_PROC para 10', txt: (autorizadas === 'nao' ? 'As duas notas precisam estar autorizadas. ' : '')
          + (mesma === 'nao' ? 'As notas não são a mesma transação (valor total ou itens diferentes): com qualquer diferença entre os XMLs o NNU não processa.' : '') };
      } else if (respondido) {
        veredito = trocaChave
          ? { cls: 'troca', tit: 'Fazer a troca de chave e processar o NNU', txt: 'As duas notas estão autorizadas e são a mesma transação, mas a chave da offline é diferente da do select: troque a chave e siga com o processamento.' }
          : { cls: 'processar', tit: 'Pode processar o NNU', txt: 'As duas notas estão autorizadas, são a mesma transação e a chave bate com a do select.' };
      } else if (trocaChave) {
        veredito = { cls: 'troca', tit: 'Troca de chave necessária', txt: 'Antes de seguir, confira se as duas notas estão autorizadas e se são a mesma transação (passo 3).' };
      }
    }
  }

  const v = document.getElementById('veredito');
  if (veredito) { v.className = 'veredito ' + veredito.cls; v.innerHTML = '<div class="tit">' + escN(veredito.tit) + '</div><div class="txt">' + escN(veredito.txt) + '</div>'; linhasResumo.push('Resultado: ' + veredito.tit + '.'); }
  else { v.className = 'veredito'; v.innerHTML = '<div class="tit">' + (s.temOffline ? 'Continue nos passos acima' : 'Comece pela pergunta 1') + '</div><div class="txt">Cole a chave da nota online e responda os passos.</div>'; }
  resumoAtual = linhasResumo.join('\\n');
}

function copiarResumo() {
  if (!resumoAtual) { toastN('Preencha a tratativa primeiro.'); return; }
  copiarN('Tratativa NNU (PDA · NNU Enchanced)\\n' + resumoAtual, 'Resumo copiado pro ticket.');
}
function recomecar() {
  ['chave-online', 'chave-offline', 'data-emissao', 'xml-online', 'xml-offline'].forEach(id => { document.getElementById(id).value = ''; });
  Object.keys(estadoNNU).forEach(k => { estadoNNU[k] = ''; });
  atualizarTudo();
}

// rejeições depois do processamento que vão pro time ClienteI
function analisarRejeicao() {
  const texto = document.getElementById('texto-rejeicao').value.trim();
  const info = document.getElementById('info-rejeicao');
  if (!texto) { info.innerHTML = ''; return; }
  const on = lerChave(document.getElementById('chave-online').value);
  const nota = on && !on.erro ? ' da nota ' + on.chave + ' (CNPJ ' + on.cnpjFmt + ', série ' + on.serie + ', número ' + on.numero + ')' : '';
  let tipo = '';
  if (/(^|[^0-9])203([^0-9]|$)/.test(texto) && /habilitad/i.test(texto)) tipo = 'emissor';
  else if (/70018|30042/.test(texto) || /certificado.*(expirad|inv[aá]lid)/i.test(texto)) tipo = 'certificado';
  if (!tipo) {
    info.innerHTML = '<div class="dica-nnu">Não é nenhuma das duas rejeições conhecidas. Se for um caso pontual, vale perguntar pro time ClienteI.</div>';
    return;
  }
  const validade = (texto.match(/Validade\\s+([0-9/: ]+?)\\s+at[eé]\\s+([0-9/]+)/i) || []);
  const msg = tipo === 'emissor'
    ? 'Olá, time ClienteI! O processamento do NNU' + nota + ' voltou com a rejeição 203 - Emissor não habilitado para emissão da NF-e (inutilização não homologada). Podem verificar a habilitação do emissor na SEFAZ?'
    : 'Olá, time ClienteI! O processamento do NNU' + nota + ' falhou na inutilização porque o certificado digital está expirado (códigos 70018/30042' + (validade[2] ? ', validade até ' + validade[2] : '') + '). Podem providenciar a renovação do certificado com o cliente?';
  info.innerHTML = '<div class="ok-nnu">' + (tipo === 'emissor' ? 'Rejeição 203: emissor não habilitado.' : 'Certificado expirado (70018/30042).') + ' Vai pro time ClienteI.</div>'
    + '<div class="mensagem-cliente_i" id="msg-cliente_i">' + escN(msg) + '</div>'
    + '<div class="acao-veredito"><button type="button" class="btn-nnu" onclick="copiarN(document.getElementById(' + "'msg-cliente_i'" + ').textContent, ' + "'Mensagem copiada.'" + ')">Copiar mensagem pro time ClienteI</button></div>';
}

atualizarTudo();
// 3.3.1.0: acende na faixa de cima o resultado em que a tratativa chegou (a classe do veredito diz qual é)
(function () {
  const v = document.getElementById('veredito');
  const acender = () => document.querySelectorAll('.saida-nnu').forEach(s => s.classList.toggle('atual', v.classList.contains(s.dataset.saida)));
  new MutationObserver(acender).observe(v, { attributes: true, attributeFilter: ['class'] });
  acender();
})();

// abas (3.4.9.0): a escolhida vai pro endereço (#status-20-15) e fica lembrada
const ABAS_NNU = ['tratativa', 'status-20-15'];
function trocarAbaNnu(aba) {
  if (!ABAS_NNU.includes(aba)) aba = 'tratativa';
  ABAS_NNU.forEach(a => { document.getElementById('aba-nnu-' + a).hidden = a !== aba; });
  document.querySelectorAll('.aba-nnu').forEach(b => { b.classList.toggle('ativa', b.dataset.aba === aba); b.setAttribute('aria-selected', b.dataset.aba === aba); });
  try { history.replaceState(null, '', aba === 'tratativa' ? location.pathname : '#' + aba); localStorage.setItem('pda-nnu-aba', aba); } catch (e) {}
  if (aba !== 'tratativa' && window.recarregarNnuStatus) window.recarregarNnuStatus();
}
(function () {
  let aba = (location.hash || '').slice(1);
  if (!ABAS_NNU.includes(aba)) { try { aba = localStorage.getItem('pda-nnu-aba') || 'tratativa'; } catch (e) { aba = 'tratativa'; } }
  trocarAbaNnu(aba);
})();
</script>
__NNU_AUTOMACAO_JS__
</body>
</html>
"""
