"""Caminhos do PDA."""
import os
import sys


def base_path_app() -> str:
    """Resolve a pasta onde o programa está (funciona tanto rodando como
    .py quanto como .exe empacotado). Usado pra achar o .env, o
    usuarios.json, etc. - tudo sempre ao lado do executável/script.

    Este arquivo fica em <pasta do PDA>/nucleo/, então sobe UM nível a
    partir dele (antes a função morava no alertas_gui.py, na raiz)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
