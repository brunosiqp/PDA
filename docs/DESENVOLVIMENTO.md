# Guia de desenvolvimento

Arquitetura, convenções e checklist de validação do PDA. Nada aqui descreve
infraestrutura, pessoas ou dados reais de nenhuma organização.

## Arquitetura

Um servidor web Python **puro** (`http.server`, sem framework) embutido numa
janela Tkinter, mais monitores e alertas agendados em background. Empacotado
com PyInstaller, roda na máquina de quem opera.

- **`alertas_gui.py`**: jobs e agendador (lista `JOBS`), montagem das páginas
  (`_montar_*_html`), rotas HTTP (`_rotas_get` / `_rotas_post` dentro do
  `_PainelHTTPHandler`) e a janela Tkinter.
- **`areas/<área>/`**: cada área numa pasta, com `logica.py` (regras, banco,
  arquivos) e `tela.py` (HTML/CSS/JS como texto). Área nova = pasta nova aqui,
  nunca código de área direto no `alertas_gui.py`.
- **`nucleo/`**: base compartilhada (caminhos, configuração, usuários, sessões e
  permissões, equipes, fotos, notificações, Movidesk).
- **`telas/`**: telas gerais e o CSS comum (`comum.py`: paleta, navbar,
  rodapé). Só texto, sem lógica.

### Regras da separação por área

1. Nada em `areas/` ou `nucleo/` importa o `alertas_gui.py` (ele roda como
   `__main__`; importar recarregaria o arquivo inteiro). O que for
   compartilhado vai para o `nucleo/`.
2. Variável que o resto do PDA altera (ex.: trava de execução) não é importada
   e reatribuída de fora: a área expõe funções (`tentar_iniciar_execucao()`).
3. O inverso também quebra: a área reatribuir (`global X; X = ...`) um nome que
   o `alertas_gui.py` importou deixa o `alertas_gui` com o objeto velho.
4. Loggers: `logging.getLogger("alertas.<nome>")` devolve o mesmo objeto
   configurado no `alertas_gui.py`.
5. CSS não é compartilhado entre páginas: cada template tem o seu `<style>`.
   Ao copiar um elemento de uma página para outra, confira se a classe existe
   no template de destino.

## Convenções de código

- Sem framework web: rotas em `if/elif caminho == "/rota"`; rotas de arquivo
  binário com `caminho.startswith("/prefixo/")`. Exceção numa rota vai para o
  log principal e a tela recebe um 500 em JSON.
- Ações de escrita (INSERT/UPDATE/DELETE, envio de e-mail) sempre em `POST`.
- HTML/CSS/JS como strings Python com placeholders `__PLACEHOLDER__` trocados
  via `.replace()`. Dentro de template Python, quebra de linha numa string JS
  se escreve `\\n`.
- Configuração: `_obter_config_hibrido(secao, arquivo_legado, chaves)` tenta a
  seção do `CREDENCIAIS_CENTRALIZADAS.env` e cai no `.env` legado. Config
  ausente nunca derruba o app: mostra erro claro na tela.
- Comparação de equipe sempre via `_pertence_a_equipe()`, nunca `==`.
- Gates de acesso por card: funções `_tem_acesso_X(sessao)`.
- Cores: `--teal` `#2db8cf`, `--lime` `#b0cb1c`, `--erro` `#f14c4c`; gradiente
  de marca teal → lime. Cada card do início tem uma cor (`--accent-card`) que
  não se repete.
- **Modo claro**: o escuro é o padrão. CSS novo usa as variáveis (`--bg`,
  `--bg-panel`, `--fg`, `--fg-dim`, `--border`...), `rgba(var(--tinta), A)`
  para véus claros e `rgba(var(--poco), A)` para fundo de campo.
- Bolinha (`·`), nunca travessão, como separador visual.
- Imagens no app em `data:image/...;base64,...`; em e-mail, sempre anexadas por
  Content-ID (o Outlook desktop não mostra data URI).
- Texto de interface em português informal; comentários em português
  explicando o **porquê**, não o quê.

## Gotcha: `JOBS` é avaliada na carga do módulo

Toda função passada em `executar=` precisa estar **definida antes** da lista
`JOBS`, senão dá `NameError` na inicialização (não aparece no `py_compile`). Se
a implementação mora mais abaixo, crie um wrapper fino antes de `JOBS` que só
chama a função por nome. O `validar.py` confere isso.

## Versionamento

`VERSAO_PDA` tem quatro níveis, `MAJOR.MINOR.FUNCIONALIDADE.AJUSTE`:

| Nível | Quando sobe |
|---|---|
| **MAJOR** | Marco de produto ou arquitetura, por decisão dos mantenedores. |
| **MINOR** | Fecha um ciclo de entregas numa entrada do changelog. Sobe por decisão dos mantenedores ou quando a FUNCIONALIDADE passaria de 9. |
| **FUNCIONALIDADE** | Funcionalidade nova ou mudança visual relevante (zera o AJUSTE). De 0 a 9. |
| **AJUSTE** | Correção ou ajuste pequeno. De 0 a 9. |

Um ajuste depois de `x.y.5.9` vira `x.y.6.0`, e uma funcionalidade depois de
`x.y.9.z` vira `x.(y+1).0.0`. O changelog fica na própria aplicação
(`/changelog`), organizado por era (uma por MAJOR).

## Checklist de validação

```bash
python -X utf8 validar.py
```

1. compila todos os `.py`;
2. todo bloco `<script>` é JS válido (parse real com Node);
3. nenhuma rota HTTP duplicada;
4. nenhum placeholder `__X__` sem `.replace()`;
5. toda função de `JOBS[].executar=` definida antes da lista;
6. nenhuma cor `--accent-card` repetida;
7. imports dos pacotes locais batem;
8. todas as telas `_montar_*_html` montam (rodando o PDA numa cópia temporária);
9. todas as rotas GET respondem sem erro com sessão de administrador (502/503
   é a rota avisando que o banco não respondeu, esperado sem credenciais);
10. o JS das telas já montadas é válido.

"Compila" não é "funciona". Para lógica nova, extraia a função num namespace
mockado e teste cenários reais (sucesso, erro, casos de borda); para DOM, use
`jsdom`. Vários bugs só apareceram assim.

## Dados de runtime (nunca versionar)

O app grava `usuarios.json`, `feedbacks_usuarios.json`,
`historico_carreira.json`, `ferias.json`, `mural_*.json`, `notificacoes.json`,
fotos, anexos, logs e o estado das automações. Contêm dados pessoais e ficam no
`.gitignore`. Em desenvolvimento, use apenas dados fictícios.

## Pendências conhecidas

- Integrações externas (bancos, Microsoft Graph, Movidesk, Teams) foram
  escritas e testadas com conexões simuladas; teste em ambiente real antes de
  confiar.
- A antiga tela de Usuários (`_montar_usuarios_html`) ficou como código morto:
  as rotas de API dela continuam em uso pela Manutenção de Usuários.
