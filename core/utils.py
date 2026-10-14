import os
import urllib.request
import sys
import inspect
from typing import Any, Optional
from dotenv import load_dotenv, dotenv_values


def limpa_tela():
    _ = os.system('cls' if os.name == 'nt' else 'clear')


def menu(opcoes: dict[str, Any], mensagem: str = None):
    if mensagem:
        print(mensagem)
    while True:
        escolha = input('>> ')
        if escolha in opcoes:
            if opcoes[escolha] == 'Outro':
                return input(': ')
            if callable(opcoes[escolha]):
                return opcoes[escolha]()
            return opcoes[escolha]
        else:
            print(f"Escolha inválida ({escolha}). Por favor, informe novamente.")


def verificar_conexao() -> bool:
    try:
        urllib.request.urlopen('https://www.google.com', timeout=5)
        return True
    except:
        return False


def get_base_path(stack_level: int) -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    frame = inspect.stack()[stack_level]
    return os.path.abspath(os.path.dirname(frame.filename))


def carregar_arquivo_env(stack_level: int = 3, spec_env: str = None, overwrite: bool = False) -> None:
    base_path = get_base_path(stack_level)
    env_file = f".env.{spec_env}" if spec_env else ".env"
    env_path = os.path.join(base_path, env_file)

    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path, override=overwrite)
        return env_path

    embedded_path = os.path.join(sys._MEIPASS, f".env.{spec_env}") if getattr(sys, 'frozen', False) else None
    if embedded_path and os.path.exists(embedded_path):
        load_dotenv(dotenv_path=embedded_path)
        return embedded_path

    return None


# Alias: core/__init__.py importa "load_env", mas a funcao aqui se chama
# "carregar_arquivo_env" (usada por features/operations.py do ValidacaoFTP
# com esse nome). Alias evita quebrar um dos dois lados.
load_env = carregar_arquivo_env


def read_env(env_path: str) -> dict:
    if os.path.exists(env_path):
        return dotenv_values(env_path)
    return {}


class EnvManager:
    def __init__(self, stack_level: int = 1):
        self.base_path = self.get_base_path(stack_level)
        self.env_path = None

    @staticmethod
    def get_base_path(stack_level: int) -> str:
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        frame = inspect.stack()[stack_level]
        caller_path = os.path.abspath(os.path.dirname(frame.filename))
        return caller_path

    def carregar(self, nome_env: Optional[str] = None, overwrite: bool = False) -> None:
        if nome_env:
            env_path = os.path.join(self.base_path, f".env.{nome_env}")
        else:
            env_path = os.path.join(self.base_path, ".env")
        self.env_path = env_path

        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path, override=overwrite)
            return None

        embedded_path = os.path.join(sys._MEIPASS, f".env.{nome_env}") if getattr(sys, 'frozen', False) else None
        if embedded_path and os.path.exists(embedded_path):
            load_dotenv(dotenv_path=embedded_path)
            return None
        return None

    def ler_env(self) -> dict:
        if self.env_path and os.path.exists(self.env_path):
            return dotenv_values(self.env_path)
        return {}

    def listar_envs(self) -> list:
        return [f for f in os.listdir(self.base_path) if f.startswith('.env')]
