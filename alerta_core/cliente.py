import pandas as pd
from typing import Any, Optional

from .env import load_env, read_env
from core.db_utils import conectar_banco, executar_query, fechar_conexao
from core.config_seguro import obter_valor_config

class Cliente:
    def __init__(self, nome: str, chave_env: Optional[str] = None):
        """
        Inicializa um cliente carregando as variáveis do .env correspondente.

        Parâmetros:
            nome: nome de exibição do cliente (aparece no e-mail/assunto do
                alerta, ex.: 'saas').
            chave_env: nome do arquivo .env a carregar, SE for diferente de
                `nome` (ex.: '.env.saas__cte2_status_inicial' em vez de
                '.env.saas'). Isso existe porque vários alertas diferentes
                podem monitorar o MESMO cliente com queries diferentes -
                sem uma chave própria por alerta, todos aqueles alertas
                acabariam lendo o mesmo .env.<cliente> e mandando a MESMA
                query/mensagem, não importa qual alerta disparou de
                verdade. Se não for informado, usa `nome` (comportamento
                de sempre, pra clientes que só aparecem em um alerta).
        """
        self.nome = nome
        self.db_server: str
        self.db_name: str
        self.db_user: str
        self.db_password: str
        self.query: str
        self.conn: Any
        self.linhas: list[tuple]
        self.colunas: list[str]
        self.tabela: pd.DataFrame
        self.documentacao: str

        env_path = load_env(nome_env=chave_env or nome, stack_level=5, overwrite=True)
        vars_env = read_env(env_path)

        for k, v in vars_env.items():
            setattr(self, k, v)

        # se essa credencial já foi migrada pro config.dat cifrado (ver
        # core/config_seguro.py), usa o valor de lá em vez do que veio do
        # .env em texto puro - senão, mantém o valor do .env normalmente
        # (compatibilidade total: nada quebra pra quem ainda não migrou).
        if hasattr(self, "db_password"):
            chave_config = f"{(chave_env or nome).lower()}::db_password"
            self.db_password = obter_valor_config(chave_config, self.db_password)

        obrigatorias = ['db_server', 'db_name', 'db_user', 'db_password', 'query']
        faltando = [var for var in obrigatorias if not hasattr(self, var)]
        if faltando:
            raise ValueError(f"Cliente {chave_env or nome} sem variáveis obrigatórias: {', '.join(faltando)}")
            
    def get_conn(self):
        """
        Realiza a conexão com banco de dados para a instância de Cliente e grava como atributo.
        Deve ser chamado explicitamente para a instância de Cliente.
        """
        self.conn = conectar_banco(
            self.db_server,
            self.db_name,
            self.db_user,
            self.db_password
        )
        
    def get_tabela(self):
        """
        Gera a tabela DataFrame baseada nos atributos de resultado e coluna da instância de Cliente.
        Deve ser chamado explicitamente para a instância de Cliente.
        """
        if not self.conn:
            # get_conn() já roda antes disso (processar_clientes chama os
            # dois em sequência) - se a conexão falhou, self.conn fica
            # False (não None), então checar isso aqui dá um erro claro em
            # vez de deixar o executar_query() logo abaixo tentar usar uma
            # conexão inválida.
            raise RuntimeError(
                f"Cliente '{self.nome}': sem conexão válida com o banco "
                "(confira db_server/db_name/db_user/db_password no .env)."
            )

        resultado = executar_query(
            conn=self.conn,
            query=self.query,
            fetch=True,
            commit=False,
            params=()
        )
        if not resultado:
            # executar_query() retorna False (não levanta exceção) quando
            # falha - por exemplo quando "query" está vazia. Sem essa
            # checagem, a linha de baixo tentava desempacotar um bool em
            # duas variáveis e quebrava com "cannot unpack non-iterable
            # bool object", uma mensagem sem nenhuma pista do problema real.
            raise RuntimeError(
                f"Cliente '{self.nome}': falha ao executar a query "
                "(confira se o campo 'query' do .env está preenchido e é um SQL válido)."
            )

        self.linhas, self.colunas = resultado
        self.tabela = pd.DataFrame(
            data=self.linhas,
            columns=self.colunas
        )
        
    def fechar_conexao(self):
        fechar_conexao(self.conn)
