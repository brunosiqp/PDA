import time
import html
from datetime import datetime

from .cliente import Cliente
from .env import load_env, read_env
from core.email_utils import enviar_email
try:
    from core.config_central import obter_secao as obter_secao_central
except ImportError:
    def obter_secao_central(nome_secao: str) -> dict:
        return {}

class Alerta:
    def __init__(
            self,
            nome: str,
            clientes: "list[str | tuple[str, str]]",
            descricao: str = 'Sem descrição adicional.',
            tipo_arquivo_temp: str = '.xlsx',
    ):
        """
        Inicializa uma instância de alerta.

        Parâmetros:
            nome (str): Nome do alerta (ex: "Alerta Fila Processamento").
            clientes: Lista de clientes. Cada item pode ser:
                - uma string simples (ex.: "cliente_d") - usa esse nome tanto
                  pra exibição quanto pra achar o arquivo .env.cliente_d; OU
                - uma tupla (nome_exibicao, chave_env) (ex.:
                  ("saas", "saas__cte2_status_inicial")) - usada quando o
                  MESMO cliente aparece em mais de um alerta com queries
                  diferentes, pra cada alerta ler seu próprio .env sem
                  colidir com o de outro alerta que usa o mesmo cliente.
        """
        self.nome = nome
        self.clientes = []
        avisos_pulados = []
        for c in clientes:
            nome_exibicao, chave_env = c if isinstance(c, tuple) else (c, c)
            try:
                self.clientes.append(Cliente(*c) if isinstance(c, tuple) else Cliente(c))
            except Exception as e:
                # um cliente com .env faltando/incompleto NÃO deve impedir
                # os outros clientes deste MESMO alerta de serem checados -
                # ex.: "Manifestações" tem 3 clientes (cliente_ag/cliente_e/saas2);
                # se só o .env do cliente_ag estiver faltando, cliente_e e saas2
                # ainda devem ser verificados normalmente.
                aviso = f"Cliente '{nome_exibicao}' (chave .env: '{chave_env}') não pôde ser carregado: {e}"
                print(f"[AVISO] {aviso} - pulando só esse cliente.")
                avisos_pulados.append(aviso)

        if not self.clientes and avisos_pulados:
            # se TODOS os clientes falharam, isso não pode virar um
            # "sucesso silencioso" - continua levantando erro de verdade,
            # igual sempre fez, pra aparecer no log como falha visível.
            raise ValueError(
                f"Nenhum cliente pôde ser carregado pro alerta '{nome}': " + " | ".join(avisos_pulados)
            )

        self.descricao = descricao
        self.tipo_arquivo_temp = tipo_arquivo_temp

        self.corpo_template = (
            "Olá,\n\n"
            "O alerta '{nome_alerta}' detectou {total} registros para o cliente '{cliente}' e produto '{produto}'.\n"
            "Limite configurado: {limite}\n\n"
            "Descrição dos registros: {descricao}\n\n"
            "Query utilizada:\n{query}\n\n"
            "{documentacao}\n\n"
            "Este e-mail é gerado automaticamente, favor não responder."   
        )

        self.corpo_template_html = ("""
        <html>
            <body>
                <p>Olá,</p>
                    <br>
                <p>
                    O alerta '<b>{nome_alerta}</b>' detectou <b>{total}</b> registros para o cliente '<b>{cliente}</b>' e produto '<b>{produto}</b>'.
                    <br>
                    Limite configurado: <b>{limite}</b>
                </p>
                    <br>
                <p>
                    Descrição dos registros:
                    <br>
                    {descricao}
                </p>
                    <br>
                <p>
                    Query utilizada:
                    <br>
                    <pre>{query}</pre>
                </p>
                    <br>
                <p>
                    {documentacao}
                </p>
                    <br>
                <p>
                    Este e-mail é gerado automaticamente, favor não responder.
                </p>
            </body>
        </html>
        """
        )
        
        self.assunto_template = (
            "ALERTA - [{nome_alerta}] - {cliente} - {produto} - {data} - {tabela} - ({total}|{limite})"
        )

    def processar_clientes(self):
        """
        Processa todos os clientes associados ao alerta.

        Para cada cliente:
            - Estabelece conexão com o banco de dados.
            - Executa a query configurada e armazena o resultado em um DataFrame.
            - Fecha a conexão ao final do processamento.

        Ao final, armazena os objetos de conexão e DataFrames em dicionários de acesso rápido:
            - self.conn_clientes: {nome_cliente: conexão}
            - self.tabela_clientes: {nome_cliente: DataFrame}

        Um cliente que falhar (conexão ruim, query inválida, etc.) é
        removido de self.clientes daqui pra frente - os outros clientes
        continuam sendo processados normalmente. Se TODOS os clientes
        falharem, levanta uma exceção de verdade (não fica um "sucesso"
        que na prática não processou nada).
        """
        clientes_processados = []
        avisos_falha = []
        for cliente in self.clientes:
            try:
                cliente.get_conn()
                cliente.get_tabela()
                clientes_processados.append(cliente)
            except Exception as e:
                aviso = f"Erro ao processar {cliente.nome}: {e}"
                print(aviso)
                avisos_falha.append(aviso)
            finally:
                try:
                    cliente.fechar_conexao()
                except Exception:
                    pass  # fechar conexão nunca deve mascarar o erro real de processamento

        if not clientes_processados and avisos_falha:
            raise RuntimeError(
                f"Nenhum cliente pôde ser processado no alerta '{self.nome}': " + " | ".join(avisos_falha)
            )

        self.clientes = clientes_processados
        self.conn_clientes = {cliente.nome: cliente.conn for cliente in self.clientes}
        self.tabela_clientes = {cliente.nome: cliente.tabela for cliente in self.clientes}
        
    def verifica_limite(self):
        """
        Coleta e armazena o limite de registros para cada cliente.

        Para cada cliente:
            - Busca o atributo 'limite' carregado do .env.
            - Caso não exista, define o limite padrão como 1 (ou seja, qualquer registro já dispara o alerta).

        O resultado é armazenado em self.limite_clientes, um dicionário no formato:
            {nome_cliente: limite}

        Uso:
            - Deve ser chamado antes de ativar o alerta para garantir que os limites estejam definidos.
        """
        self.limite_clientes = {cliente.nome: int(getattr(cliente, 'limite', 1)) for cliente in self.clientes}
                    
    def ativar_alerta(self):
        """
        Avalia se o alerta deve ser disparado para cada cliente.

        Para cada cliente:
            - Calcula o total de registros relevantes (soma de coluna específica ou número de linhas).
            - Compara o total com o limite definido.
            - Se o total for maior ou igual ao limite, envia o e-mail de alerta.
            - Caso contrário, exibe mensagem informando que não há pendências suficientes.

        Observação:
            - O método chama automaticamente verifica_limite() antes de iniciar as verificações.
        """
        self.verifica_limite()
        
        for cliente in self.clientes:
            limite = self.limite_clientes.get(cliente.nome, 1)
            coluna = getattr(cliente, 'coluna_contagem', None)
            if coluna is not None:
                if coluna in cliente.tabela.columns:
                    total = cliente.tabela[coluna].sum()
                else:
                    print(f"Coluna '{coluna}' não encontrada para {cliente.nome}.")
                    continue
            else:
                total = len(cliente.tabela)
                
            if total >= limite:
                self.enviar_alerta_email(cliente=cliente, total=total, limite=limite, df=cliente.tabela)
            else:
                print(f"Não existem pendências suficientes [{total}|{limite} - {cliente.nome} - {getattr(cliente, 'produto', 'N/A')}]. {datetime.now()}")
                
    def config_email(self):
        """
        Carrega e retorna as configurações de e-mail.

        CREDENCIAIS_CENTRALIZADAS.env primeiro (seção [infra_email]), cai
        pro .env.email tradicional se essa seção não existir (ver
        core/config_central.py).

        Retorna:
            dict: Um dicionário contendo:
                - 'smtp_info': informações do servidor SMTP (servidor, porta, usuário, senha)
                - 'email_to': destinatário do e-mail
        """
        vars_email = obter_secao_central("infra_email")
        if not vars_email:
            env_email = load_env(nome_env='email', stack_level=5, overwrite=True)
            vars_email = read_env(env_email)
        smtp_info = {
            'smtp_server': vars_email['smtp_server'],
            'smtp_port': vars_email['smtp_port'],
            'email_from': vars_email['email_from'],
            'email_password': vars_email['email_password']
        }
        email_to = vars_email['email_to']
        return {
            'smtp_info': smtp_info,
            'email_to': email_to
        }

    def enviar_alerta_email(self, cliente, total, limite, df):
        """
        Envia um e-mail de alerta para o destinatário configurado.

        Parâmetros:
            cliente (Cliente): Objeto Cliente com os dados do alerta.
            total (int): Total de registros encontrados.
            limite (int): Limite configurado para disparo do alerta.
            df (pd.DataFrame): DataFrame com os dados a serem anexados ao e-mail.

        O método tenta enviar o e-mail até 10 vezes em caso de falha.
        """
        print(f"[DEBUG] Iniciando envio de e-mail para {cliente.nome}...")
        
        try:
            vars_email = self.config_email()
            print(f"[DEBUG] Configurações de e-mail carregadas: {vars_email.get('email_to')}")
        except Exception as e:
            print(f"[ERRO] Falha ao carregar configurações de e-mail: {e}")
            return
        
        documentacao_html = f'<a href="{cliente.documentacao}">Acessar Documentação</a>'
        query_html = html.escape(cliente.query)
        corpo = self.corpo_template_html.format(
            nome_alerta=self.nome,
            cliente=cliente.nome,
            produto=getattr(cliente, 'produto', 'produto não referenciado'),
            total=total,
            limite=limite,
            documentacao=documentacao_html,
            descricao=self.descricao,
            query=query_html
        )
        
        assunto = self.assunto_template.format(
            nome_alerta=self.nome,
            cliente=cliente.nome,
            produto=getattr(cliente, 'produto', 'produto não referenciado'),
            total=total,
            limite=limite,
            tabela=getattr(cliente, 'nome_tabela', 'tabela não referenciada'),
            data=datetime.now().strftime("%d/%m/%Y")
        )
        
        print(f"[DEBUG] Assunto: {assunto}")
        print(f"[DEBUG] DataFrame com {len(df)} linhas")
        
        ultimo_erro = None
        for i in range(10):
            try:
                print(f"[DEBUG] Tentativa {i+1}/10 de envio de e-mail...")
                resultado = enviar_email(
                    destinatario=vars_email['email_to'],
                    assunto=assunto,
                    corpo=corpo,
                    smtp_info=vars_email['smtp_info'],
                    anexo_temp=df,
                    nome_arquivo_temp=self.nome,
                    tipo_arquivo_temp=self.tipo_arquivo_temp,
                    retorn_erro=True
                )
                print(f"[DEBUG] Resultado da tentativa {i+1}: {resultado}")
                
                if resultado:
                    print(f"Email enviado com sucesso [{total}|{limite} - {cliente.nome} - {getattr(cliente, 'produto', 'produto não referenciado')}]. {datetime.now()}")
                    return
            except Exception as e:
                print(f"[DEBUG] Exceção na tentativa {i+1}: {e}")
                ultimo_erro = e
            
            time.sleep(5)
        
        # Exibir erro apenas após as 10 tentativas falharem
        print(f"Falha ao enviar e-mail após 10 tentativas. Erro: {ultimo_erro}. {datetime.now()}")
