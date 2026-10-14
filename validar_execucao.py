"""Parte do validar.py que RODA o PDA (itens 8 e 9). Não chamar direto.

Uso interno: python validar_execucao.py <pasta_copia> <saida.json>
A pasta é uma cópia temporária só com código (sem .env, config.dat, chave.key nem
JSONs de dados), então nenhuma rota consegue falar com banco/Teams/e-mail de verdade.

8. Monta todas as telas (_montar_*_html, achadas sozinhas) com uma sessão de admin:
   pega nome inexistente, import errado e placeholder __X__ que sobrou no HTML final.
   Também devolve os <script> de cada tela montada, que o validar.py passa no Node (item 10).
9. Sobe o servidor web e chama todas as rotas GET com essa sessão: pega rota que
   devolve 500, cai sem resposta ou gera exceção Python no log (502/503 da rota
   avisando que o banco não respondeu é esperado, já que a cópia não tem credenciais).
"""
import inspect
import io
import json
import logging
import os
import re
import sys
import threading
import traceback
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer

pasta, saida = sys.argv[1], sys.argv[2]
os.chdir(pasta)
sys.path.insert(0, pasta)

# exceções de programação (não de rede/banco, que são esperadas sem credenciais)
PADRAO_EXC = re.compile(r"\b(NameError|AttributeError|ImportError|ModuleNotFoundError|UnboundLocalError|TypeError|KeyError|IndexError)\b[^\n]*")
# rotas GET que não devem ser chamadas pelo teste (encerram a sessão)
NAO_CHAMAR = {"/logout"}
excecoes = []


class Captura(logging.Handler):
    def emit(self, record):
        texto = record.getMessage() + ("\n" + "".join(traceback.format_exception(*record.exc_info)) if record.exc_info else "")
        excecoes.extend(m.group(0)[:200] for m in PADRAO_EXC.finditer(texto))


stderr_real, sys.stderr = sys.stderr, io.StringIO()
stdout_real, sys.stdout = sys.stdout, io.StringIO()  # avisos de .env faltando etc.
resultado = {"importou": False, "telas": {}, "rotas": {}, "excecoes": [], "scripts": {}}
try:
    import alertas_gui as g
    resultado["importou"] = True
except BaseException:
    resultado["erro_import"] = traceback.format_exc()[-1500:]
    sys.stdout, sys.stderr = stdout_real, stderr_real
    json.dump(resultado, open(saida, "w", encoding="utf-8"))
    sys.exit(0)
logging.getLogger("alertas").addHandler(Captura())

codigo = open("alertas_gui.py", encoding="utf-8").read()
permissoes = sorted(set(re.findall(r'"pode_([a-z_]+)"', codigo)))
usuario = next(iter(g.USUARIOS_WEB))
sessao = {"usuario": usuario, "nome": "Validação", "admin": True, "genero": "", "atribuicao": "Suporte e Monitoramento",
          "expira": datetime.now() + timedelta(hours=1), **{f"pode_{p}": True for p in permissoes}}

# ---- 8. telas ----
for nome in sorted(n for n in dir(g) if re.fullmatch(r"_montar_\w+_html", n)):
    funcao = getattr(g, nome)
    args, faltando = [], []
    for p in inspect.signature(funcao).parameters.values():
        if p.name == "sessao":
            args.append(dict(sessao))
        elif "usuario" in p.name:
            args.append(usuario)
        elif p.default is not inspect.Parameter.empty:
            break  # daqui pra frente fica tudo no padrão
        elif p.annotation is bool or p.name.startswith("com_"):
            args.append(False)
        else:
            faltando.append(p.name)
    if faltando:
        resultado["telas"][nome] = f"não sei chamar (parâmetro {', '.join(faltando)})"
        continue
    try:
        html = funcao(*args)
        sobras = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]*__", html)))
        # placeholder que o próprio JS da página troca na hora (ex.: __LOGO__ da Central de Monitores)
        sobras = [s for s in sobras if f"'{s}'" not in html and f'"{s}"' not in html]
        # o ícone da aba nunca é trocado pelo JS: entre aspas (href="__FAVICON__") também é falha
        if "__FAVICON__" in html and "__FAVICON__" not in sobras:
            sobras.append("__FAVICON__")
        if not isinstance(html, str) or len(html) < 200:
            resultado["telas"][nome] = "devolveu vazio"
        elif sobras:
            resultado["telas"][nome] = "placeholder sem trocar: " + ", ".join(sobras)
        else:
            resultado["telas"][nome] = "ok"
        # JS como o navegador recebe (depois do Python montar a página): pega escape
        # que é válido no .py mas quebra no HTML final, ex.: uma barra-n que vira
        # quebra de linha de verdade dentro de uma string JS (item 10 do validar.py)
        resultado["scripts"][nome] = re.findall(r"<script>(.*?)</script>", html, re.S)
    except Exception as e:
        resultado["telas"][nome] = f"{type(e).__name__}: {e}"

# ---- 9. rotas GET ----
# desde a 2.35.7.0 as rotas ficam em _rotas_get/_rotas_post (do_GET/do_POST só embrulham com a rede de segurança)
inicio_get = codigo.index("def _rotas_get")
fim_get = codigo.index("def _rotas_post") if codigo.index("def _rotas_post") > inicio_get else len(codigo)
rotas_get = sorted(set(re.findall(r'caminho == "([^"]+)"', codigo[inicio_get:fim_get])) - NAO_CHAMAR)
rotas_get.append(f"/perfil/{usuario}")  # exemplo de rota por prefixo
token = "validacao"
g.SESSIONS[token] = sessao
servidor = ThreadingHTTPServer(("127.0.0.1", 0), g._PainelHTTPHandler)
threading.Thread(target=servidor.serve_forever, daemon=True).start()
porta = servidor.server_address[1]


def chamar(rota):
    # exceções no log entram no relatório geral (as rotas rodam em paralelo, não dá pra atribuir a uma só)
    req =urllib.request.Request(f"http://127.0.0.1:{porta}{rota}", headers={"Cookie": f"session={token}"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            status = r.status
    except urllib.error.HTTPError as e:
        status = e.code
    except Exception as e:
        return rota, f"sem resposta ({type(e).__name__})"
    # 502/503 = a própria rota avisando que o banco/serviço não respondeu, esperado na cópia sem
    # credenciais; 500 (ou cair sem resposta) é erro de programação
    if status == 500:
        return rota, f"HTTP {status}"
    return rota, "ok"


with ThreadPoolExecutor(max_workers=12) as ex:
    resultado["rotas"] = dict(ex.map(chamar, rotas_get))
servidor.shutdown()
resultado["excecoes"] = sorted(set(excecoes + [m.group(0)[:200] for m in PADRAO_EXC.finditer(sys.stderr.getvalue())]))
sys.stdout, sys.stderr = stdout_real, stderr_real
json.dump(resultado, open(saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
