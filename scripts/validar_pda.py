"""Checklist de validação do PDA (ver docs/DESENVOLVIMENTO.md).

Uso: python scripts/validar_pda.py [alertas_gui.py] [caminho-do-node]

Sem o 2º argumento, procura o Node na variável NODE, no PATH e, por último,
no runtime embutido do VS Code (ELECTRON_RUN_AS_NODE). Sem Node nenhum, a
checagem de JS falha de propósito (não dá pra dizer "OK" sem executar o parser).
"""
import os, re, shutil, subprocess, sys, tempfile
from collections import Counter

alvo = sys.argv[1] if len(sys.argv) > 1 else 'alertas_gui.py'


def _achar_node():
    for candidato in (sys.argv[2] if len(sys.argv) > 2 else None, os.environ.get('NODE'), shutil.which('node')):
        if candidato and os.path.exists(candidato):
            return candidato
    vscode = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'Microsoft VS Code', 'Code.exe')
    return vscode if os.path.exists(vscode) else None


node = _achar_node()
src = open(alvo, encoding='utf-8').read()
linhas = src.split('\n')
falhas = 0


def resultado(nome, ok, detalhe=''):
    global falhas
    if not ok:
        falhas += 1
    print(f"[{'OK' if ok else 'FALHA'}] {nome}" + (f' · {detalhe}' if detalhe else ''))


# 1. Compila?
try:
    compile(src, alvo, 'exec')
    resultado('py_compile', True)
except SyntaxError as e:
    resultado('py_compile', False, str(e))

# 2. Blocos <script> são JS válido? (vm.Script só faz o parse, não executa)
scripts = re.findall(r'<script>(.*?)</script>', src, re.S)
if node:
    tmp = tempfile.mkdtemp()
    ruins = []
    for i, s in enumerate(scripts):
        p = os.path.join(tmp, f'check_{i}.js')
        open(p, 'w', encoding='utf-8').write(s)
        chk = ("const vm=require('vm'),fs=require('fs');"
               f"try{{new vm.Script(fs.readFileSync({p!r},'utf8'),{{filename:{p!r}}})}}"
               "catch(e){console.log(e.message);process.exit(1)}")
        env = dict(os.environ, ELECTRON_RUN_AS_NODE='1')
        r = subprocess.run([node, '-e', chk], capture_output=True, text=True, env=env)
        if r.returncode != 0:
            ruins.append((i, (r.stdout + r.stderr).strip()[:200]))
    resultado(f'{len(scripts)} blocos <script> (parse JS)', not ruins, str(ruins) if ruins else '')
else:
    resultado('blocos <script>', False, 'node não informado')

# 3. Rotas duplicadas?
rotas = re.findall(r'elif caminho == "([^"]+)"', src)
dup = {k: v for k, v in Counter(rotas).items() if v > 1}
resultado(f'rotas duplicadas ({len(rotas)} rotas)', not dup, str(dup) if dup else '')

# 4. Placeholder __X__ sem .replace() correspondente?
placeholders = set(re.findall(r'__[A-Z][A-Z0-9_]*__', src))
orfaos = sorted(p for p in placeholders if f'.replace("{p}"' not in src)
resultado(f'placeholders ({len(placeholders)})', not orfaos, str(orfaos) if orfaos else '')

# 5. Funções de JOBS[].executar= definidas antes da lista JOBS?
linha_jobs = next(i for i, l in enumerate(linhas) if l.startswith('JOBS: List[Job] = ['))
fim = next(i for i in range(linha_jobs, len(linhas)) if linhas[i].startswith(']'))
bloco = '\n'.join(linhas[linha_jobs:fim + 1])
nomes = sorted(set(re.findall(r'executar\s*=\s*([A-Za-z_]\w*)', bloco)))
defs = {}
for i, l in enumerate(linhas):
    m = re.match(r'(?:async\s+)?def\s+(\w+)\s*\(', l)
    if m and m.group(1) not in defs:
        defs[m.group(1)] = i
problemas = [(n, defs.get(n)) for n in nomes if n not in defs or defs[n] > linha_jobs]
resultado(f'JOBS (linha {linha_jobs + 1}): {len(nomes)} executores definidos antes', not problemas, str(problemas) if problemas else '')

print('\nTOTAL DE FALHAS:', falhas)
sys.exit(1 if falhas else 0)
