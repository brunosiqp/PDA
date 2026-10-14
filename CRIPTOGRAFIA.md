# Criptografia de configurações sensíveis (Fernet + config.dat)

## O que é isso, resumido

Antes, as senhas de banco e tokens de API ficavam em texto puro, espalhadas
em mais de 30 arquivos `.env.*` na pasta do programa. Agora, essas
credenciais sensíveis ficam cifradas num arquivo só (`config.dat`), usando
o algoritmo Fernet (criptografia simétrica autenticada, da biblioteca
`cryptography`). Só quem tem o arquivo `chave.key` (que fica ao lado do
`config.dat`, na mesma pasta do programa) consegue decifrar o conteúdo.

## Seja realista sobre o que isso protege

Isso é importante entender antes de qualquer outra coisa: **o programa roda
sozinho**, sem ninguém digitando uma senha toda vez que ele liga (via
Task Scheduler, sem supervisão humana). Isso significa que a chave de
criptografia **precisa estar em algum arquivo acessível pro programa
conseguir decifrar sozinho** - não tem como escapar disso sem adicionar
fricção (alguém ter que digitar uma senha mestra toda vez que o programa
reiniciar, o que não é viável pra um serviço automático).

Então, sendo direto:

- **Isso NÃO impede** alguém com acesso total ao servidor (aos arquivos do
  programa) de eventualmente conseguir ler as credenciais - essa pessoa
  também teria acesso ao `chave.key`.
- **Isso PROTEGE de verdade** contra exposição **acidental**: alguém
  abrindo um `.env` sem querer e vendo uma senha, um print de tela
  compartilhado sem perceber o que aparece atrás, um arquivo indo parar
  num lugar que não devia (backup solto, repositório git, pasta
  compartilhada, anexo de e-mail) - nesses casos, sem o `chave.key`
  também estar ali, o conteúdo de `config.dat` é só uma sequência de bytes
  sem sentido nenhum.

Ou seja: é uma camada de proteção contra descuido, não um cofre à prova de
um invasor com acesso completo à máquina. Isso é normal e esperado pra
esse tipo de sistema (qualquer programa que precisa se auto-autenticar sem
supervisão tem essa mesma limitação, incluindo praticamente todo serviço
que roda em segundo plano).

## Os 2 arquivos novos

- **`chave.key`**: a chave de criptografia. Gerada automaticamente na
  primeira vez que alguma coisa é salva em `config.dat` (seja pelo script
  de migração, seja pela tela "Configurações Seguras" do painel). **Nunca
  apague nem compartilhe esse arquivo** - sem ele, o conteúdo de
  `config.dat` fica ilegível pra sempre (não tem "esqueci a senha" em
  criptografia simétrica - se perder a chave, é preciso recadastrar tudo
  do zero).
- **`config.dat`**: o conteúdo cifrado. Um "dicionário" só, com todas as
  credenciais migradas, guardadas como pares `chave -> valor` e cifradas
  inteiras juntas.

Os dois ficam na mesma pasta do `alertas_gui.py`/`.exe`. **Faça backup dos
dois juntos** (nunca de um sem o outro - um `config.dat` sem o `chave.key`
correspondente é inútil, e vice-versa).

## Como migrar as credenciais existentes (primeira vez)

Já preparei um script que lê os `.env.*` que já existem na pasta e cifra
automaticamente os campos sensíveis de cada um. Rode, na pasta do
programa (mesma pasta do `alertas_gui.py`):

```
py migrar_para_config_dat.py
```

Isso vai:
1. Ler cada `.env` e `.env.<nome>` já existente.
2. Identificar o campo sensível de cada um (senha de banco, token, etc.)
3. Cifrar e salvar em `config.dat` (criando `chave.key` se ainda não
   existir).
4. Mostrar um resumo de quantas chaves foram migradas - sem nunca
   exibir os valores em si na tela.

**Isso NÃO apaga nem altera os `.env` originais.** O programa já passa a
preferir os valores cifrados automaticamente depois de rodar o script -
não precisa reiniciar nada além do normal (próxima vez que o serviço
reiniciar/for reiniciado já usa os valores novos).

Depois de confirmar que tudo continua funcionando normalmente com o
`config.dat`, é **opcional** (mas recomendado, se quiser reduzir ainda
mais a exposição) apagar manualmente só a **linha da senha/token** de
dentro de cada `.env` - não o arquivo inteiro, as outras variáveis (como
`db_server`, `query`, etc.) continuam sendo lidas normalmente do `.env`,
só a credencial sensível some de lá. O script de migração não faz essa
parte sozinho de propósito - é uma decisão sua, quando estiver confortável
que está tudo funcionando.

**Seguro rodar o script mais de uma vez**: se uma chave já estiver
migrada, ele só sobrescreve com o valor atual do `.env` correspondente
(não duplica, não dá erro).

## O que já vem migrado nesta versão

O script cobre automaticamente:

- `.env` (raiz) - senha do banco usado pelo alerta "Valor Zerado ClienteC"
- `.env.sharepoint` - senha da conta usada no envio dos relatórios ClienteA
- `.env.cliente_a` - senha do banco de onde vêm os dados do relatório ClienteA
- `.env.monitoramento` - senha do banco de monitoramento (contingências)
- `.env.indicadores_movidesk` - senha do banco de indicadores
- `.env.indicadores_workflow` - senha de banco (não é mais usado pelo
  programa atual, mas migrado por completude, caso volte a ser usado)
- `.env.horas_movidesk` - token da API do Movidesk (Horas Trabalhadas)
- `.env.email` - senha de e-mail (não é usado pelo programa atual, mas
  migrado por completude)
- **Todos os `.env.<cliente>`** dos mais de 30 clientes/alertas
  configurados (campo `db_password` de cada um)

## Como adicionar/atualizar uma credencial nova, daqui pra frente

Duas formas:

### Opção 1 - pela tela do painel (mais simples pro dia a dia)

Acesse **Configurações Seguras** no menu principal (só admin). Lá dá pra:
- Ver a **lista de chaves já migradas** (só os nomes - os valores nunca
  aparecem de volta pela tela, nem pra admin, de propósito).
- **Adicionar ou atualizar** uma chave: informa a chave no formato
  `origem::campo` (ex.: `saas::db_password`) e o valor a cifrar.
- **Remover** uma chave (volta a usar o valor do `.env` correspondente,
  se ele ainda tiver essa variável).

### Opção 2 - direto por código (pra quem for mexer no `alertas_gui.py`)

```python
from core.config_seguro import definir_valor_config_dat, obter_valor_config

# grava/atualiza
definir_valor_config_dat("novo_cliente::db_password", "a-senha-aqui")

# lê (com fallback pro que já vinha de um .env, se ainda não migrado)
senha = obter_valor_config("novo_cliente::db_password", padrao=os.getenv("DB_PASSWORD", ""))
```

## Convenção de nomes de chave

Sempre `origem::campo`, tudo minúsculo na parte da origem:
- `origem` identifica de qual `.env` aquele valor vem - geralmente o nome
  do arquivo sem o `.env.` na frente (ex.: `saas`, `sharepoint`,
  `cliente_e-cte`).
- `campo` é o nome original da variável nesse arquivo (ex.: `db_password`,
  `SHAREPOINT_PASSWORD`, `MOVIDESK_TOKEN`) - mantém a capitalização
  original do `.env` de origem, pra facilitar rastrear de onde veio.

## Como migrar uma credencial NOVA (que ainda não existe nem em `.env`)

Se for configurar um alerta novo com um cliente novo do zero, dá pra
já cadastrar a senha direto em "Configurações Seguras" (Opção 1 acima),
sem nem precisar criar o `.env.<cliente>` com a senha em texto puro -
só as outras variáveis (`db_server`, `db_name`, `db_user`, `query`, etc.)
continuam precisando estar no `.env`, porque só o campo `db_password` é
verificado no `config.dat` hoje.

## Se quiser migrar OUTRAS credenciais no futuro (além da senha)

Hoje só o campo de senha/token de cada configuração é verificado no
`config.dat` (ex.: `db_password`, não `db_user`). Se quiser cifrar campos
adicionais (como `db_user`, por exemplo), o padrão é sempre o mesmo -
teria que:
1. Adicionar uma chamada a `obter_valor_config("origem::campo", padrao)`
   no loader correspondente (ou na classe `Cliente`, pro caso genérico).
2. Migrar o valor existente via `definir_valor_config_dat()` (manual ou
   estendendo o script `migrar_para_config_dat.py`).

Fica à vontade pra pedir ajuda com isso quando quiser expandir.

## O que acontece se `chave.key` for perdido ou corrompido

O programa **não trava**. Ele detecta que não consegue decifrar
`config.dat` (chave errada ou arquivo corrompido), registra um aviso no
log, e cai de volta para os valores dos arquivos `.env` normais - **se
ainda existirem** (por isso a recomendação de não apagar as linhas de
senha dos `.env` imediatamente depois de migrar, só depois de ter
confiança que está tudo funcionando redondo com o `config.dat`).

Se você já tiver apagado as senhas dos `.env` E perder o `chave.key`, vai
precisar recadastrar as credenciais do zero (seja editando os `.env`
de novo, seja pela tela "Configurações Seguras").

## Resumo rápido

| O quê | Onde |
|---|---|
| Rodar a migração pela primeira vez | `py migrar_para_config_dat.py` na pasta do programa |
| Ver quais credenciais já estão cifradas | Menu → Configurações Seguras |
| Adicionar/atualizar uma credencial | Menu → Configurações Seguras, ou `definir_valor_config_dat()` no código |
| Onde fica a chave de criptografia | `chave.key`, ao lado do `config.dat` |
| Fazer backup | Sempre os dois juntos: `chave.key` + `config.dat` |
| O que isso protege de verdade | Exposição acidental, não acesso completo ao servidor |


## Atualização Dash Financeiro - senhas já pré-cadastradas

As 23 credenciais de banco que a Atualização Dash Financeiro precisa
(uma por combinação servidor+banco, entre os 9 produtos: NFe, CTe,
NFCe, CFe, NFSe Out, NFSe In, MDFe, ClienteK, SaaS) **não vêm de nenhum
.env antigo** - essa automação nasceu nova, então não tem texto puro
espalhado em arquivo nenhum pra migrar.

Rode uma vez, na pasta do programa:

```
py cadastrar_senhas_dash_financeiro.py
```

Isso cadastra as 23 chaves de uma vez (extraídas do notebook
Atualizacao_Dash_Financeiro.ipynb que você mandou). Depois de confirmar
que a Atualização Dash Financeiro está funcionando, pode **apagar esse
arquivo** - ele tem as senhas em texto puro dentro dele mesmo, só existe
pra fazer essa carga inicial uma vez. Depois de rodado, as senhas já
estão cifradas em config.dat, que é o que o programa realmente usa.

Se precisar adicionar um banco/cliente novo no futuro (que ainda não
está em nenhuma das 23 chaves), cadastre a senha dele em
Configurações Seguras normalmente, com a chave
`dash_financeiro::<nome_do_banco>` (mesmo padrão das outras).


## Webhook do Teams - Contingências SEFAZ

A URL do Workflow do Teams usada pros avisos de Contingências (agendada /
entrada / saída) também é uma credencial sensível - quem tiver essa URL
consegue postar mensagem no canal. Fica cifrada como
`teams::contingencias_webhook`.

Rode uma vez, na pasta do programa:

```
py cadastrar_webhook_teams_contingencias.py
```

Isso cadastra a URL sem mexer em nenhuma outra chave já existente (senhas
do Dash Financeiro, SharePoint, etc.). Se precisar trocar a URL depois
(recriou o Workflow no Teams, por exemplo), roda o script de novo com a
URL nova, ou usa a tela Configurações Seguras direto no painel.
