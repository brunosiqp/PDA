"""Fotos de perfil - lógica (fotos por login em fotos_usuarios/, usadas na navbar, no perfil e nos e-mails).

Separado do alertas_gui.py em 26/09/2026. As rotas web e o agendamento continuam no alertas_gui.py
e usam o que está aqui.
"""
import base64
import logging
import os
import re
from typing import Optional

from nucleo.caminhos import base_path_app as _base_path_app
from nucleo.usuarios import USUARIOS_WEB
from telas.imagens import _AVATAR_IGOR_BASE64_MIGRACAO
from telas.imagens import _AVATAR_DEBORA_BASE64_MIGRACAO

logger = logging.getLogger("alertas")  # mesmo logger configurado no alertas_gui.py


# GIF desde a 3.1.9.0 (animado continua animado: a tela manda o arquivo inteiro, sem passar pelo recorte)
_EXTENSOES_FOTO_PERMITIDAS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
_TAMANHO_MAXIMO_FOTO_BYTES = 3 * 1024 * 1024  # 3MB decodificado (foto parada: o recorte já sai com no máximo 1024 px)
_TAMANHO_MAXIMO_GIF_BYTES = 5 * 1024 * 1024   # GIF animado até 5MB (3.3.2.1); as telas carregam os avatares sob demanda


def _pasta_fotos_usuarios() -> str:
    caminho = os.path.join(_base_path_app(), "fotos_usuarios")
    os.makedirs(caminho, exist_ok=True)
    return caminho


def _caminho_foto_usuario(usuario: str) -> Optional[str]:
    """Devolve o caminho da foto desse usuário se existir (tentando cada
    extensão suportada), ou None se a pessoa nunca subiu uma foto."""
    pasta = _pasta_fotos_usuarios()
    nome_seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", usuario)
    for ext in _EXTENSOES_FOTO_PERMITIDAS.values():
        candidato = os.path.join(pasta, nome_seguro + ext)
        if os.path.exists(candidato):
            return candidato
    return None


def _salvar_foto_usuario(usuario: str, data_url: str) -> Optional[str]:
    """Recebe uma data URL (ex: 'data:image/jpeg;base64,/9j/...'), valida
    tipo e tamanho, e salva em disco. Devolve uma mensagem de erro (str) se
    algo deu errado, ou None se salvou com sucesso."""
    m = re.match(r"^data:(image/[\w.+-]+);base64,(.+)$", data_url, re.DOTALL)
    if not m:
        return "formato de imagem inválido"
    tipo_mime, base64_dados = m.group(1), m.group(2)
    if tipo_mime not in _EXTENSOES_FOTO_PERMITIDAS:
        return f"tipo de imagem não suportado ({tipo_mime}) - use JPEG, PNG, WEBP ou GIF"

    try:
        bytes_imagem = base64.b64decode(base64_dados, validate=True)
    except Exception:
        return "não foi possível decodificar a imagem"

    limite = _TAMANHO_MAXIMO_GIF_BYTES if tipo_mime == "image/gif" else _TAMANHO_MAXIMO_FOTO_BYTES
    if len(bytes_imagem) > limite:
        return f"imagem muito grande (máximo {limite // (1024*1024)}MB{' pra GIF' if tipo_mime == 'image/gif' else ''})"
    if len(bytes_imagem) == 0:
        return "imagem vazia"
    if tipo_mime == "image/gif" and not bytes_imagem.startswith((b"GIF87a", b"GIF89a")):
        return "esse arquivo não é um GIF de verdade"

    # remove qualquer foto anterior (pode ter sido salva com outra extensão)
    pasta = _pasta_fotos_usuarios()
    nome_seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", usuario)
    for ext in _EXTENSOES_FOTO_PERMITIDAS.values():
        antiga = os.path.join(pasta, nome_seguro + ext)
        if os.path.exists(antiga):
            try:
                os.remove(antiga)
            except Exception:
                pass

    extensao = _EXTENSOES_FOTO_PERMITIDAS[tipo_mime]
    caminho_novo = os.path.join(pasta, nome_seguro + extensao)
    try:
        with open(caminho_novo, "wb") as f:
            f.write(bytes_imagem)
    except Exception as e:
        logger.exception("Falha ao salvar foto de %s", usuario)
        return f"falha ao salvar: {e}"
    return None


def _migrar_fotos_iniciais_perfil() -> None:
    """Roda uma vez na inicializacao do app - se o Igor ou a Debora
    ainda nao tiverem uma foto de perfil salva como arquivo, extrai a
    que ja estava embutida nos templates e salva de verdade. Nao
    sobrescreve quem ja tem foto (subida manualmente ou de uma
    migracao anterior)."""
    mapeamento = {"igor": _AVATAR_IGOR_BASE64_MIGRACAO, "debora": _AVATAR_DEBORA_BASE64_MIGRACAO}
    for login, base64_dados in mapeamento.items():
        if login not in USUARIOS_WEB:
            continue
        if _caminho_foto_usuario(login) is not None:
            continue
        try:
            erro = _salvar_foto_usuario(login, f"data:image/jpeg;base64,{base64_dados}")
            if erro:
                logger.warning("Não foi possível migrar a foto inicial de '%s': %s", login, erro)
            else:
                logger.info("Foto inicial de '%s' migrada com sucesso pro novo sistema de arquivo.", login)
        except Exception:
            logger.exception("Falha ao migrar foto inicial de '%s'", login)
