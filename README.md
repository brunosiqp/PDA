# PDA · Painel de Automações

Painel web local para equipes de **Suporte e Monitoramento**: alertas automáticos,
monitores, ferramentas internas e uma comunidade da equipe num lugar só. É um
servidor web Python **puro** (`http.server`, sem framework) embutido numa janela
Tkinter, com jobs agendados rodando em background. Empacotado com PyInstaller,
roda na máquina de quem opera (não é um serviço hospedado).

> **Privacidade e LGPD.** Este repositório é público e é um **espelho sanitizado**
> do código de produção, que fica num repositório privado. Ele **não contém
> nenhum dado sensível**: sem credenciais, tokens ou URLs assinadas; sem dados
> pessoais (nomes, logins, e-mails, fotos, cargos, feedbacks); sem endereços,
> servidores ou caminhos de rede internos; sem CNPJs e sem nomes de clientes.
> Clientes aparecem como pseudônimos (`ClienteA`, `cliente_b`...), pessoas com
> nomes fictícios, e-mails em `@example.com`, IPs na faixa de documentação
> `192.0.2.0/24` e imagens (logos, fotos, prints) como placeholders. Detalhes em
> [Privacidade e LGPD](#privacidade-e-lgpd).

## Funcionalidades

**Monitoramento e alertas**
- Alertas fiscais agendados (biblioteca `schedule`), cada um em sua thread, com
  log, status e aviso no Microsoft Teams quando um job falha seguidas vezes.
- Contingências SEFAZ (SVC-AN / SVC-RS) por estado, com aviso no Teams.
- Central de Monitores: atalhos para os monitores e a infraestrutura de cada
  cliente, editável pela própria tela.
- Monitoramento dos logs do EmailPack, reprocessamento automático de CT-es
  parados, limpeza de arquivos com nome longo, monitoramento de consumo
  indevido e automações de NNU (status 20 → 15), todas começando pausadas e em
  modo simulação.

**Relatórios e dados**
- Relatórios diários enviados ao SharePoint (Microsoft Graph), Dash Financeiro
  mensal para o Power BI e manutenção de alertas, rejeições e relatórios
  direto no banco, com String Connections.
- Indicadores do Movidesk, horas trabalhadas por analista, indicadores mensais
  (efetividade, NOC, satisfação) e calendário de GMUDs.

**Equipe**
- Comunidade (a tela inicial): feed com aniversários, promoções, insígnias,
  férias, publicações com fotos, vídeos, arquivos e votações, palminhas e
  comentários, notificações no topo de todas as telas.
- Perfil com histórico de carreira e insígnias, feedbacks e alinhamentos,
  rankings por produto, Loja de Palminhas e calendário de férias.

**Acesso e segurança**
- Login com permissões por pessoa e por área, troca obrigatória da senha
  inicial, sincronização de usuários com o Movidesk.
- Credenciais sensíveis cifradas (Fernet, `config.dat`), log isolado por
  automação com arquivamento automático em zip.

## Stack

Python 3, `http.server`, Tkinter, `schedule`, `requests`, `pyodbc`, `pandas`,
`xlsxwriter`, `cryptography`, Chart.js (CDN) e PyInstaller para o `.exe`.

## Estrutura

| Caminho | O que é |
|---|---|
| `alertas_gui.py` | App principal: jobs e agendador, montagem das páginas (`_montar_*_html`), rotas HTTP e a janela Tkinter. Versão em `VERSAO_PDA`. |
| `areas/<área>/` | Uma pasta por área, com `logica.py` (regras) e `tela.py` (HTML/CSS/JS). |
| `nucleo/` | Base compartilhada: caminhos, configuração, usuários, sessões e permissões, equipes, fotos, notificações, Movidesk. Não importa o `alertas_gui.py`. |
| `telas/` | HTML/CSS/JS das telas gerais (início, login, alertas, logs, sobre, changelog...) e o CSS comum. Só texto. |
| `core/`, `alerta_core/`, `features/` | Utilitários de banco, e-mail, configuração e criptografia, e as classes dos alertas por cliente. |
| `validar.py`, `validar_execucao.py` | Checklist de validação (ver abaixo). |
| `compilar.bat`, `PainelAlertas.spec`, `requirements.txt` | Build. |

## Rodando

```bash
pip install -r requirements.txt
python alertas_gui.py
```

Sem configuração, o painel sobe normalmente e cada integração mostra na tela o
que está faltando (banco, SMTP, Movidesk, Teams), sem derrubar o app. Na
primeira execução é criado um `usuarios.json` com os usuários de exemplo do
`nucleo/usuarios.py` (senha `troque-esta-senha`); troque as senhas logo depois.

## Configuração

Nenhum valor de ambiente vem no código. Toda credencial segue o padrão
híbrido: o PDA procura primeiro uma seção em `CREDENCIAIS_CENTRALIZADAS.env`
(formato INI) e, sem ela, um `.env.<nome>` legado. Senhas e tokens podem ficar
cifrados no `config.dat` (chave em `chave.key`), cadastrados pela tela
"Configurações Seguras"; veja [CRIPTOGRAFIA.md](CRIPTOGRAFIA.md). O monitor do
EmailPack também lê variáveis de ambiente, descritas em
[`.env.example`](.env.example). Tudo isso fica no `.gitignore`.

## Validação

```bash
python -X utf8 validar.py
```

Confere compilação, sintaxe real de todos os blocos `<script>` (via Node),
rotas duplicadas, placeholders órfãos, ordem de definição das funções da lista
`JOBS`, cores repetidas dos cards e imports dos pacotes locais. Depois **roda o
PDA** numa cópia temporária: monta todas as telas, chama todas as rotas GET com
uma sessão de administrador e valida o JS das telas já montadas (`--rapido`
pula essa parte). Convenções e versionamento em
[docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).

## Privacidade e LGPD

Este repositório é gerado a partir do privado por um sanitizador, que exporta
só o que está versionado, troca dados reais por pseudônimos e **confere o
resultado** antes de publicar (credenciais da máquina, nomes, logins, e-mails,
clientes, IPs, servidores, domínios internos, URLs assinadas e senhas literais).
Se a conferência acha qualquer coisa, nada é publicado.

Regras para quem contribui:

1. **Nunca** commitar credenciais, tokens, chaves, URLs assinadas ou strings de
   conexão. Use os arquivos de configuração locais, ignorados pelo git.
2. **Nunca** commitar dados pessoais: nomes, e-mails, fotos, cargos, feedbacks,
   férias, histórico de carreira, logins ou senhas, nem em comentários,
   exemplos, testes ou mensagens de commit.
3. **Nunca** commitar dados de infraestrutura real (hosts, IPs,
   compartilhamentos de rede, identificadores de tenant, de workflow ou de
   relatório) nem nomes ou CNPJs de clientes: use os pseudônimos.
4. Arquivos de dados de runtime (`usuarios.json`, `feedbacks_usuarios.json`,
   `historico_carreira.json`, `ferias.json`, `mural_*.json`, fotos, anexos e
   similares) ficam fora do repositório. Em desenvolvimento e testes, use
   apenas dados **fictícios** (`exemplo@example.com`, `maria.souza`).
5. Se um dado sensível chegar a ser commitado, trate como vazamento: revogue a
   credencial e reescreva o histórico. Apagar em um commit novo não basta.

## Licença

Ainda não definida. Sem uma licença explícita, todos os direitos permanecem
reservados ao autor.
