# Guia de desenvolvimento

Arquitetura, convenções e checklist de validação do PDA. Nada aqui descreve
infraestrutura, pessoas ou dados reais de nenhuma organização.

## Arquitetura

Um servidor web Python **puro** (`http.server`, sem framework) embutido numa
janela Tkinter, mais monitores/alertas agendados em background. Quase tudo vive
em um único arquivo, `alertas_gui.py` (~19 mil linhas):

- HTML/CSS/JS de cada página como strings Python (`_X_HTML_TEMPLATE`), com
  placeholders `__PLACEHOLDER__` trocados via `.replace()`;
- rotas HTTP em `if/elif caminho == "/rota"` dentro de `do_GET`/`do_POST`;
- lógica de negócio, jobs agendados (lista `JOBS`) e a janela Tkinter.

Empacotado com PyInstaller, roda na máquina de quem opera (não é um serviço
hospedado).

### Módulos locais que não estão neste repositório

O arquivo importa pacotes locais (`core.*`, `alerta_core.*`, `features.*`) que
**ainda não foram migrados** para este repositório. Sem eles o app não sobe;
o que dá para fazer aqui é ler, revisar e validar estaticamente o código.

## Configuração e segredos

Nenhum segredo, endereço interno ou dado pessoal pode entrar no código nem no
histórico do git. Toda configuração específica de ambiente vem de:

1. **variáveis de ambiente** (ver `.env.example`);
2. **arquivos de configuração locais** (`.env*`, `config.dat`, `chave.key`),
   todos no `.gitignore`.

Padrão híbrido para credenciais: tenta primeiro o arquivo central por seção e
cai no `.env` legado individual se a seção não existir. Config ausente nunca
derruba o app: mostra erro claro na tela.

## Pseudônimos de cliente

Nomes reais de cliente e fornecedor não entram no código. Convenção: `ClienteA`
/ `cliente_a` / `CLIENTE_A` (por caixa, do A ao I) e `FornecedorA`. Ao criar
algo novo que dependa de um cliente, escolha o próximo pseudônimo livre e use
`_alias_real()` só onde o nome real é necessário de fato (chave de config,
pasta, arquivo de log, nome do alerta). O mapa pseudônimo → real fica no
`aliases_privados.json`, **fora do git**. Nunca escreva o nome real em código,
comentário, teste ou mensagem de commit.

## Versionamento

SemVer em `VERSAO_PDA` (topo do arquivo, seção de versão):

- **MAJOR**: só sobe por decisão explícita do mantenedor;
- **MINOR**: funcionalidade nova ou reformulação visual relevante;
- **PATCH**: ajuste pequeno ou correção de bug.

Atualização manual a cada entrega.

## Convenções de código

- Sem framework web: rotas na mão.
- Cores: `--teal` `#2db8cf`, `--lime` `#b0cb1c`, `--erro` `#f14c4c`, fundo
  escuro (`#0b0f14`/`#181f27`); gradiente de marca teal → lime. Cada card do hub
  tem uma cor (`--accent-card`) que não se repete.
- Bolinha (`·`), nunca travessão (`—`/`–`), como separador visual.
- Imagens inline em `data:image/...;base64,...` (sem assets externos).
- Texto de interface em português informal; comentários em português
  explicando o **porquê**, não o quê.
- Comparação de equipe sempre via `_pertence_a_equipe()` (Python) /
  `pertenceAEquipeMU()` (JS), nunca `==`.
- Gates de acesso por card: funções `_tem_acesso_X(sessao)`.

## Gotcha: `JOBS` é avaliada na carga do módulo

Toda função passada em `executar=` precisa estar **definida antes** da lista
`JOBS`, senão dá `NameError` na inicialização. Isso não aparece no `py_compile`,
só em runtime. Se a implementação real mora mais abaixo, crie um wrapper fino
antes de `JOBS` que só chama a função por nome. O checklist abaixo já verifica
isso.

## Checklist de validação (antes de considerar qualquer mudança pronta)

```bash
python scripts/validar_pda.py
```

O script confere:

1. `py_compile` do `alertas_gui.py`;
2. todo bloco `<script>` é JS válido (parse real com Node; sem Node no PATH usa
   o runtime do VS Code via `ELECTRON_RUN_AS_NODE`);
3. nenhuma rota HTTP duplicada;
4. nenhum placeholder `__X__` sem `.replace()` correspondente;
5. toda função de `JOBS[].executar=` definida antes da lista.

"Compila" não é "funciona". Para lógica nova, extraia a função com `ast` /
`exec()` num namespace mockado e teste cenários reais (sucesso, erro, casos de
borda). Vários bugs só apareceram assim.

Arquivo grande: navegue com `grep`/leitura por intervalo de linhas e valide a
cada edição, sem acumular várias mudanças. Já houve corrupção na junção de blocos
grandes de texto.

## Dados de runtime (nunca versionar)

O app grava arquivos locais como `usuarios.json`, `feedbacks_usuarios.json`,
`historico_carreira.json`, `ferias.json`, conexões e controle de e-mails
enviados. Contêm dados pessoais e ficam no `.gitignore`. Em desenvolvimento,
use apenas dados fictícios.

## Pendências conhecidas

- Migrar `core/`, `alerta_core/` e `features/` para este repositório (já
  sanitizados) para o app voltar a rodar a partir do clone.
- Remover código morto da antiga tela de Usuários (`_montar_usuarios_html` e
  `_USUARIOS_HTML_TEMPLATE`): as rotas de API dela continuam em uso pela tela
  de Manutenção de Usuários, só o HTML/template ficou inalcançável.
- Integrações externas (banco, Microsoft Graph, Movidesk) foram escritas e
  testadas com conexões simuladas; teste em ambiente real antes de confiar.
