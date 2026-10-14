import os
import sys
import inspect
from dotenv import load_dotenv, dotenv_values

def get_base_path(stack_level: int = 2) -> str:
    """
    Retorna o caminho base do programa, adaptado para execução normal ou empacotada (.exe).
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    frame = inspect.stack()[stack_level]
    return os.path.abspath(os.path.dirname(frame.filename))

def load_env(nome_env: str = "", overwrite: bool = False, stack_level: int = 2) -> str:
    """
    Carrega um arquivo .env no ambiente.
    
    Args:
        nome_env (str, opcional): nome do .env (ex.: 'cliente1' => '.env.cliente1').
        overwrite (bool): se True, sobrescreve variáveis já definidas.
        stack_level (int): nível da stack para encontrar o caminho base.
    
    Returns:
        str: caminho completo do .env carregado.
    """
    base_path = get_base_path(stack_level)
    env_file = f".env.{nome_env.lower()}" if nome_env else ".env"
    env_path = os.path.join(base_path, env_file)

    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=overwrite)
    return env_path

def read_env(env_path: str) -> dict:
    """
    Lê as variáveis do .env (sem carregar no ambiente global).
    
    Args:
        env_path (str): caminho do arquivo .env.
    
    Returns:
        dict: chave-valor das variáveis do .env.
    """
    if os.path.exists(env_path):
        return dotenv_values(env_path)
    return {}
