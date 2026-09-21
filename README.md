# PDA · Painel de Automações

Painel web local para equipes de **Suporte e Monitoramento**: reúne alertas
automáticos, monitores e ferramentas internas em um só lugar. É um servidor web
Python **puro** (sem framework, apenas `http.server`) embutido em uma janela
Tkinter, com jobs agendados rodando em background. Empacotado com PyInstaller,
roda na máquina de quem opera (não é um serviço hospedado).

> **Privacidade e LGPD.** Este repositório é público e **não contém nenhum dado
> sensível** da **Inventti**, a empresa onde o PDA é utilizado, nem de seus
> clientes ou colaboradores: sem credenciais, tokens ou URLs assinadas, sem dados
> pessoais (nomes, e-mails, fotos, histórico de RH), sem endereços, servidores ou
> caminhos de rede internos, sem CNPJs e sem nomes de clientes (todos aparecem
> como pseudônimos: `ClienteA`, `cliente_b`...). Tudo o que é específico de um ambiente vem de
> variáveis de ambiente e de arquivos locais que ficam fora do git. Detalhes em
> [Privacidade e LGPD](#privacidade-e-lgpd).

## Funcionalidades

- **Hub de automações** com cards e controle de acesso por permissão.
- **Alertas e jobs agendados** (biblioteca `schedule`), cada um em sua própria
  thread, com log e acompanhamento de status.
- **Monitoramento de contingências SEFAZ** (SVC-AN / SVC-RS) por estado, com
  aviso automático no Microsoft Teams (Workflow).
- **Monitoramento de logs do EmailPack** por e-mail processado, com deduplicação
  e aviso no Teams.
- **Manutenção de usuários**: cadastro, desativação e edição em vários bancos e
  no Movidesk, com diagnóstico multi-banco.
- **Perfil e feedbacks**: indicadores, horas trabalhadas, linha do tempo de
  cargo e feedbacks privados entre administradores.
- **Horas trabalhadas** (apontamentos do Movidesk vs. meta, escala, feriados e
  férias).
- **Manutenção de alertas, rejeições e relatórios** em banco.
- **Dashboards por cliente** (Beta): dashboard nativo com Chart.js ou relatório
  Power BI incorporado por iframe.
- **E-mails automáticos** com identidade visual própria (boas-vindas, marcos de
  45/90 dias de empresa, feedback registrado).
- **Credenciais cifradas** ("Configurações Seguras") e gestão de permissões
  granulares.

## Stack

Python 3, `http.server`, Tkinter, `schedule`, `requests`, `pyodbc`, `pandas`,
`xlsxwriter`, Chart.js (CDN) e PyInstaller para o `.exe`.

## Estado do repositório

O `alertas_gui.py` importa pacotes locais (`core.*`, `alerta_core.*`,
`features.*`) que **ainda não foram migrados** para cá; enquanto isso, o app não
sobe a partir do clone. O que já dá para fazer aqui é ler, revisar e validar o
código (veja [Validação](#validação)). A migração desses módulos, já
sanitizados, está listada em [docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).

## Configuração

Não há nenhum valor de ambiente embutido no código. Defina as variáveis
descritas em [`.env.example`](.env.example) no ambiente do processo. Principais:

| Variável | Para quê |
|---|---|
| `PDA_ADMIN_SENHA_INICIAL` | Senha do usuário `admin` criado na primeira execução. Vazia: uma senha aleatória é sorteada e registrada uma vez no log. |
| `PDA_SENHA_PADRAO_NOVOS_USUARIOS` | Senha inicial dos cadastros novos. Obrigatória para cadastrar usuários e enviar boas-vindas. |
| `PDA_DESTINATARIOS_TEMPO_EMPRESA`, `PDA_DESTINATARIOS_FEEDBACK_EXTRAS` | Destinatários de e-mail, separados por vírgula. Vazio: ninguém é notificado. |
| `PDA_LINK_WEB`, `PDA_NOME_AMIGAVEL_WEB` | Endereço exibido nos e-mails e nome amigável do servidor. |
| `EMAILPACK_*`, `PDA_FTP_UNC`, `PDA_*_PASTA` | Servidores e pastas de rede dos monitores. |

### Nomes de clientes (pseudônimos)

O código só usa pseudônimos (`ClienteA`, `cliente_b`, `FornecedorA`...). Quem
opera o PDA cria, **fora do git**, um `aliases_privados.json` ao lado do programa
(ou aponta `PDA_ALIASES_PRIVADOS`) com o mapa pseudônimo → nome real; veja
[`aliases_privados.example.json`](aliases_privados.example.json). O mapa é aplicado só onde o
nome vira chave de verdade (seções e chaves de configuração, pastas e logs,
nomes dos alertas, permissões antigas do `usuarios.json`). Sem o arquivo, tudo
funciona com os pseudônimos, o que basta para desenvolver e testar. Os CNPJs
usados por consultas vêm de variáveis de ambiente (`PDA_CNPJ_*`).

Segredos (senhas de banco, SMTP, webhook do Teams) ficam em arquivos `.env*`,
`config.dat` e `chave.key` locais, **todos no `.gitignore`**.

## Validação

```bash
python scripts/validar_pda.py
```

Confere compilação, sintaxe real de todos os blocos `<script>` (via Node), rotas
duplicadas, placeholders órfãos e a ordem de definição das funções da lista
`JOBS`. Convenções, versionamento e o checklist completo estão em
[docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).

## Privacidade e LGPD

O projeto segue a LGPD **sempre**. Regras para quem contribui:

1. **Nunca** commitar credenciais, tokens, chaves, URLs assinadas ou strings de
   conexão. Use variáveis de ambiente ou os arquivos locais ignorados pelo git.
2. **Nunca** commitar dados pessoais: nomes, e-mails, fotos, cargos, feedbacks,
   férias, histórico de carreira, logins ou senhas, nem em comentários,
   exemplos, testes ou mensagens de commit.
3. **Nunca** commitar dados de infraestrutura real: hosts, IPs, compartilhamentos
   de rede, identificadores de tenant ou de relatório, nem nomes ou CNPJs de
   clientes: use os pseudônimos e o `aliases_privados.json` (fora do git).
4. Arquivos de dados de runtime (`usuarios.json`, `feedbacks_usuarios.json`,
   `historico_carreira.json`, `ferias.json` e similares) ficam fora do
   repositório. Em desenvolvimento e testes, use apenas dados **fictícios**
   (`exemplo@example.com`, `maria.souza`).
5. Se um dado sensível chegar a ser commitado, trate como vazamento: revogue a
   credencial e reescreva o histórico. Apagar em um commit novo não basta.

## Licença

Ainda não definida. Sem uma licença explícita, todos os direitos permanecem
reservados ao autor.
