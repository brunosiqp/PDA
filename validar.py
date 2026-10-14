"""Checklist de validação do PDA (ver HANDOFF_PDA.md) - rodar antes de toda entrega.

Uso: python validar.py [pasta do projeto]
Lê o alertas_gui.py e os pacotes separados dele desde 26/09/2026: telas/, areas/ e nucleo/.
Sai com código 1 se algum item falhar. Precisa do Node no PATH pro item 2.
Os itens 8, 9 e 10 rodam o PDA numa cópia temporária (~30 s); "--rapido" pula esses três.
"""
import ast
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
from collections import Counter

PASTA = next((a for a in sys.argv[1:] if not a.startswith("--")), None) or os.path.dirname(os.path.abspath(__file__))
ARQUIVO = os.path.join(PASTA, "alertas_gui.py")
PACOTES = ("telas", "areas", "nucleo")  # separados do alertas_gui.py
ARQUIVOS_TELAS = sorted(p for pac in PACOTES
                        for p in glob.glob(os.path.join(PASTA, pac, "**", "*.py"), recursive=True))
# Rotas que aparecem 2x de propósito (uma nas rotas GET, outra nas POST)
ROTAS_DUPLICADAS_OK = {"/login", "/alterar-senha"}

src = open(ARQUIVO, encoding="utf-8").read()
fontes = {ARQUIVO: src}
fontes.update({p: open(p, encoding="utf-8").read() for p in ARQUIVOS_TELAS})
tudo = "\n".join(fontes.values())  # alertas_gui.py + pacotes, pros itens que olham texto
falhas = []


def item(titulo, ok, detalhe=""):
    print(f"[{'OK' if ok else 'FALHOU'}] {titulo}" + (f"\n       {detalhe}" if detalhe else ""))
    if not ok:
        falhas.append(titulo)


def rel(caminho):
    return os.path.relpath(caminho, PASTA)


# 1. Compila? (via compile pra não gerar __pycache__; warnings de escape inválido também contam)
erros, avisos_txt = [], []
for caminho, texto in fontes.items():
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        try:
            compile(texto, caminho, "exec")
        except SyntaxError as e:
            erros.append(f"{rel(caminho)} linha {e.lineno}: {e.msg}")
    avisos_txt += [f"{rel(caminho)} linha {a.lineno}: {a.message}" for a in avisos]
item(f"1. Compila ({len(fontes)} arquivos)", not erros, "; ".join(erros))
if avisos_txt:
    print("       avisos: " + "; ".join(avisos_txt))

# 2. Todo bloco <script> é JS válido? (Node de verdade, não regex)
node = shutil.which("node")
if not node:
    item("2. Blocos <script> são JS válido", False, "node não encontrado no PATH")
else:
    ruins, total = [], 0
    with tempfile.TemporaryDirectory() as tmp:
        for caminho, texto in fontes.items():
            for i, s in enumerate(re.findall(r"<script>(.*?)</script>", texto, re.S)):
                total += 1
                js = os.path.join(tmp, f"check_{total}.js")
                with open(js, "w", encoding="utf-8") as f:
                    f.write(s)
                r = subprocess.run([node, "--check", js], capture_output=True, text=True, encoding="utf-8")
                if r.returncode != 0:
                    linha_py = texto[: texto.find(s)].count("\n") + 1
                    ultima = [l for l in r.stderr.strip().splitlines() if l.strip()]
                    ruins.append(f"{rel(caminho)} perto da linha {linha_py}: {ultima[-1] if ultima else '?'}")
    item(f"2. Blocos <script> são JS válido ({total} blocos)", not ruins, "\n       ".join(ruins))

# 3. Rotas duplicadas? (as rotas moram no alertas_gui.py)
rotas = re.findall(r'(?:elif|if) caminho == "([^"]+)"', src)
dup = {k: v for k, v in Counter(rotas).items() if v > 1 and k not in ROTAS_DUPLICADAS_OK}
item(f"3. Sem rotas duplicadas ({len(rotas)} rotas)", not dup, str(dup) if dup else "")

# 4. Placeholder __X__ sem .replace() correspondente? (placeholder fica em telas/, o .replace no alertas_gui.py)
placeholders = set(re.findall(r"__[A-Z][A-Z0-9_]*__", tudo))
orfaos = sorted(p for p in placeholders if f'.replace("{p}"' not in tudo and f".replace('{p}'" not in tudo)
item(f"4. Sem placeholders órfãos ({len(placeholders)} placeholders)", not orfaos, ", ".join(orfaos))

# 5. Toda função em JOBS[].executar= está definida ANTES da lista JOBS?
linhas = src.split("\n")
try:
    linha_jobs = next(i for i, l in enumerate(linhas) if l.startswith("JOBS: List[Job] = ["))
    fim_jobs = next(i for i in range(linha_jobs, len(linhas)) if linhas[i].startswith("]"))
    bloco = "\n".join(l for l in linhas[linha_jobs : fim_jobs + 1] if not l.lstrip().startswith("#"))
    defs = {}
    for no in ast.parse(src).body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            defs.setdefault(no.name, no.lineno - 1)
        elif isinstance(no, ast.ImportFrom):  # função que mora numa área (ex.: areas/jobs_proprios) e é importada
            for a in no.names:
                defs.setdefault(a.asname or a.name, no.lineno - 1)
    # executar=<func> e também helpers chamados na lista (ex.: job_alerta(...)) - todos avaliados na carga
    nomes = set(re.findall(r"executar\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", bloco))
    nomes |= {n for n in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", bloco) if n in defs}
    problemas = [f"{n} ({'linha ' + str(defs[n] + 1) if n in defs else 'não definida'})"
                 for n in sorted(nomes) if defs.get(n, 10**9) > linha_jobs]
    item(f"5. Funções usadas em JOBS definidas antes da linha {linha_jobs + 1} ({', '.join(sorted(nomes))})",
         not problemas, ", ".join(problemas))
except StopIteration:
    item("5. Funções de JOBS definidas antes da lista", False, "não achei 'JOBS: List[Job] = ['")

# 6. Cores --accent-card repetidas entre cards do hub
cores = Counter(c.lower() for c in re.findall(r"--accent-card:(#[0-9a-fA-F]+)", tudo))
rep = {k: v for k, v in cores.items() if v > 1}
item(f"6. Sem --accent-card repetido ({len(cores)} cores)", not rep, str(rep) if rep else "")

# 7. Todo "from <pacote local>.<módulo> import ..." aponta pra um nome que existe no arquivo?
#    (py_compile não pega: nome errado só estoura ao abrir o PDA). Vale pro alertas_gui.py e
#    pros próprios pacotes (ex.: areas/ importando de nucleo/).
def _nos_do_nivel_do_modulo(corpo):
    """Nós do nível do módulo, entrando em try/except, if e with (ex.: o plano B do
    nucleo/config.py define as funções dentro de um try/except ImportError)."""
    for no in corpo:
        yield no
        if isinstance(no, (ast.Try, ast.If, ast.With)):
            filhos = list(no.body) + list(getattr(no, "orelse", [])) + list(getattr(no, "finalbody", []))
            for h in getattr(no, "handlers", []):
                filhos += h.body
            yield from _nos_do_nivel_do_modulo(filhos)


def nomes_do_modulo(caminho):
    nomes_mod = set()
    for no in _nos_do_nivel_do_modulo(ast.parse(fontes[caminho]).body):
        if isinstance(no, ast.Assign):
            for t in no.targets:
                nomes_mod |= {x.id for x in ast.walk(t) if isinstance(x, ast.Name)}
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name):
            nomes_mod.add(no.target.id)
        elif isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            nomes_mod.add(no.name)
        elif isinstance(no, (ast.Import, ast.ImportFrom)):
            nomes_mod |= {(a.asname or a.name).split(".")[0] for a in no.names}
    return nomes_mod


problemas_import, qtd_nomes = [], 0
for origem, texto in fontes.items():
    for no in ast.walk(ast.parse(texto)):
        if isinstance(no, ast.ImportFrom) and (no.module or "").split(".")[0] in PACOTES:
            destino = os.path.join(PASTA, *no.module.split(".")) + ".py"
            for a in no.names:
                qtd_nomes += 1
                if destino not in fontes:
                    problemas_import.append(f"{rel(origem)}: {no.module} não existe")
                elif a.name not in nomes_do_modulo(destino):
                    problemas_import.append(f"{rel(origem)}: {a.name} não está em {rel(destino)}")
item(f"7. Imports dos pacotes locais batem ({qtd_nomes} nomes)", not problemas_import,
     "; ".join(sorted(set(problemas_import))))

# 8 e 9. Roda o PDA de verdade numa cópia temporária só com código (sem credenciais nem dados):
#        monta todas as telas e chama todas as rotas GET com sessão de admin (ver validar_execucao.py).
#        Pega o que compilar não pega: nome inexistente, import errado, placeholder que sobrou no
#        HTML, rota que devolve 500. Leva ~1 min; "--rapido" pula esses dois.
if "--rapido" in sys.argv:
    print("[--] 8, 9 e 10. Execução das telas e rotas pulada (--rapido)")
else:
    with tempfile.TemporaryDirectory() as copia:
        for nome in ("alertas_gui.py",) + PACOTES + ("core", "alerta_core", "features"):
            origem = os.path.join(PASTA, nome)
            if os.path.isdir(origem):
                shutil.copytree(origem, os.path.join(copia, nome), ignore=shutil.ignore_patterns("__pycache__"))
            elif os.path.isfile(origem):
                shutil.copy(origem, copia)
        saida_json = os.path.join(copia, "_resultado_validacao.json")
        r = subprocess.run([sys.executable, "-X", "utf8", os.path.join(PASTA, "validar_execucao.py"), copia, saida_json],
                           capture_output=True, text=True, encoding="utf-8", timeout=600)
        res = json.load(open(saida_json, encoding="utf-8")) if os.path.exists(saida_json) else {}
    if not res.get("importou"):
        detalhe = res.get("erro_import") or (r.stderr or r.stdout)[-1500:]
        item("8. Todas as telas montam", False, "o PDA nem importou:\n" + detalhe)
        item("9. Rotas GET respondem sem erro", False, "pulado (o PDA não importou)")
    else:
        telas_ruins = [f"{n}: {s}" for n, s in res["telas"].items() if s != "ok"]
        item(f"8. Todas as telas montam ({len(res['telas'])} telas)", not telas_ruins, "\n       ".join(telas_ruins))
        rotas_ruins = [f"{rota}: {s}" for rota, s in res["rotas"].items() if s != "ok"]
        item(f"9. Rotas GET respondem sem erro ({len(res['rotas'])} rotas)", not rotas_ruins and not res["excecoes"],
             "\n       ".join(rotas_ruins + [f"exceção no log: {e}" for e in res["excecoes"]]))
        # 10. o JS das telas JÁ MONTADAS (o que o navegador recebe) é válido? O item 2 olha
        #     o texto do .py, onde uma barra-n escrita num template é válida; no HTML final
        #     ela pode virar quebra de linha dentro de uma string JS e parar o script da tela.
        if node:
            js_ruins, total_js = [], 0
            with tempfile.TemporaryDirectory() as tmp:
                for nome_tela, scripts in res.get("scripts", {}).items():
                    for i, js in enumerate(scripts):
                        total_js += 1
                        caminho_js = os.path.join(tmp, f"{nome_tela}_{i}.js")
                        with open(caminho_js, "w", encoding="utf-8") as f:
                            f.write(js)
                        rj = subprocess.run([node, "--check", caminho_js], capture_output=True, text=True, encoding="utf-8")
                        if rj.returncode != 0:
                            linhas_erro = [l for l in rj.stderr.strip().splitlines() if l.strip()]
                            trecho = linhas_erro[1].strip() if len(linhas_erro) > 1 else ""
                            erro_js = next((l.strip() for l in linhas_erro if "Error" in l), linhas_erro[-1] if linhas_erro else "?")
                            js_ruins.append(f"{nome_tela}: {erro_js} · perto de: {trecho[:90]}")
            item(f"10. JS das telas montadas é válido ({total_js} blocos)", not js_ruins, "\n       ".join(js_ruins))

versao = re.search(r'^VERSAO_PDA = "([^"]+)"', src, re.M)
print(f"\nVERSAO_PDA = {versao.group(1) if versao else '?'}")
print("TUDO OK" if not falhas else f"{len(falhas)} item(ns) falharam")
sys.exit(1 if falhas else 0)
