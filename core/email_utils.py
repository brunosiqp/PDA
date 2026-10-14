# encoding: utf-8

import logging
import os
import re
import smtplib
import tempfile
import unicodedata
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


def _montar_nome_arquivo(nome_base: str, extensao: str, fallback: str = "anexo") -> str:
    """Normaliza nome de arquivo para uso seguro em headers de e-mail."""
    nome_base = str(nome_base or "").replace("\r", " ").replace("\n", " ").strip()
    extensao = str(extensao or "").strip()
    if extensao and not extensao.startswith("."):
        extensao = f".{extensao}"

    nome_base = (
        unicodedata.normalize("NFKD", nome_base)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    nome_base = re.sub(r'[\\/:*?"<>|]+', "_", nome_base)
    nome_base = re.sub(r"\s+", " ", nome_base).strip(" .")

    if not nome_base:
        nome_base = fallback

    return f"{nome_base}{extensao}"


def _normalizar_destinatarios(destinatario: str | Iterable[str]) -> list[str]:
    if isinstance(destinatario, str):
        destinatarios = [destinatario]
    else:
        destinatarios = list(destinatario)

    destinatarios = [email.strip() for email in destinatarios if isinstance(email, str) and email.strip()]
    if not destinatarios:
        raise ValueError("Informe ao menos um destinatario valido.")

    invalidos = [email for email in destinatarios if "@" not in email or email.startswith("@")]
    if invalidos:
        raise ValueError(f"Destinatarios invalidos: {', '.join(invalidos)}")

    return destinatarios


def _validar_smtp_info(smtp_info: dict[str, Any]) -> None:
    if not isinstance(smtp_info, dict):
        raise ValueError("smtp_info deve ser um dicionario.")

    obrigatorios = ("smtp_server", "smtp_port", "email_from", "email_password")
    ausentes = [campo for campo in obrigatorios if not smtp_info.get(campo)]
    if ausentes:
        raise ValueError(f"Campos obrigatorios ausentes em smtp_info: {', '.join(ausentes)}")


def _mime_subtype(tipo_arquivo: str) -> str:
    return {
        ".csv": "csv",
        ".txt": "plain",
        ".xlsx": "vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".zip": "zip",
    }.get(tipo_arquivo.lower(), "octet-stream")


def _anexar_arquivo(msg: MIMEMultipart, caminho_arquivo: str, nome_anexo: str | None = None) -> None:
    path = Path(caminho_arquivo)
    if not path.is_file():
        raise FileNotFoundError(f"Arquivo {caminho_arquivo} nao encontrado.")

    with path.open("rb") as arquivo:
        parte = MIMEBase("application", "octet-stream")
        parte.set_payload(arquivo.read())

    encoders.encode_base64(parte)
    filename = nome_anexo or path.name.replace("\r", "").replace("\n", "").strip() or "anexo"
    parte.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(parte)


def _criar_anexo_temporario(
    anexo_temp: Any,
    nome_arquivo_temp: str,
    tipo_arquivo_temp: str,
) -> tuple[str, str, bool]:
    tipo_arquivo_temp = tipo_arquivo_temp if tipo_arquivo_temp.startswith(".") else f".{tipo_arquivo_temp}"

    if tipo_arquivo_temp == ".zip":
        if isinstance(anexo_temp, str) and os.path.exists(anexo_temp):
            return anexo_temp, _montar_nome_arquivo(nome_arquivo_temp, tipo_arquivo_temp), False
        raise ValueError("Para tipo .zip, anexo_temp deve ser o caminho do arquivo.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=tipo_arquivo_temp) as temp_file:
        temp_file_path = temp_file.name

    try:
        if tipo_arquivo_temp == ".xlsx":
            if not hasattr(anexo_temp, "to_excel"):
                raise ValueError("Para tipo .xlsx, anexo_temp deve possuir metodo to_excel.")
            anexo_temp.to_excel(temp_file_path, index=False)

        elif tipo_arquivo_temp == ".csv":
            if not hasattr(anexo_temp, "to_csv"):
                raise ValueError("Para tipo .csv, anexo_temp deve possuir metodo to_csv.")
            anexo_temp.to_csv(
                temp_file_path,
                index=False,
                encoding="utf-8-sig",
                sep=";",
                decimal=",",
            )

        elif tipo_arquivo_temp == ".txt":
            with open(temp_file_path, "wb") as temp_file:
                conteudo = anexo_temp.encode("utf-8") if isinstance(anexo_temp, str) else anexo_temp
                temp_file.write(conteudo)

        else:
            conteudo = anexo_temp.encode("utf-8") if isinstance(anexo_temp, str) else anexo_temp
            with open(temp_file_path, "wb") as temp_file:
                temp_file.write(conteudo)

    except Exception:
        try:
            os.unlink(temp_file_path)
        except OSError:
            logger.debug("Nao foi possivel remover arquivo temporario: %s", temp_file_path)
        raise

    return temp_file_path, _montar_nome_arquivo(nome_arquivo_temp, tipo_arquivo_temp), True


def enviar_email(
    destinatario: str | Iterable[str],
    assunto: str,
    corpo: str,
    smtp_info: dict,
    anexos: list | None = None,
    anexo_temp: Any | None = None,
    nome_arquivo_temp: str = "notas",
    tipo_arquivo_temp: str = ".txt",
    retorn_erro: bool = False,
    raise_on_error: bool = False,
) -> bool:
    """
    Envia um e-mail utilizando o servidor SMTP especificado.

    Mantem o comportamento antigo de retornar False em erro. Use
    raise_on_error=True para levantar excecoes.
    """
    temp_files_to_remove: list[str] = []

    try:
        _validar_smtp_info(smtp_info)
        destinatarios_envio = _normalizar_destinatarios(destinatario)

        msg = MIMEMultipart()
        msg["From"] = smtp_info["email_from"]
        msg["To"] = ", ".join(destinatarios_envio)
        msg["Subject"] = str(assunto or "")
        msg.attach(MIMEText(str(corpo or ""), "html", "utf-8"))

        if anexo_temp is not None:
            temp_file_path, nome_anexo_temp, deve_remover = _criar_anexo_temporario(
                anexo_temp,
                nome_arquivo_temp,
                tipo_arquivo_temp,
            )
            if deve_remover:
                temp_files_to_remove.append(temp_file_path)

            with open(temp_file_path, "rb") as temp_file:
                parte = MIMEBase("application", _mime_subtype(tipo_arquivo_temp))
                parte.set_payload(temp_file.read())

            encoders.encode_base64(parte)
            parte.add_header("Content-Disposition", "attachment", filename=nome_anexo_temp)
            msg.attach(parte)

        if anexos is not None:
            for caminho_arquivo in anexos:
                try:
                    _anexar_arquivo(msg, caminho_arquivo)
                except FileNotFoundError as exc:
                    logger.warning("%s Anexo nao adicionado.", exc)
                    if raise_on_error:
                        raise

        with smtplib.SMTP(smtp_info["smtp_server"], int(smtp_info["smtp_port"])) as server:
            server.starttls()
            server.login(smtp_info["email_from"], smtp_info["email_password"])
            server.sendmail(smtp_info["email_from"], destinatarios_envio, msg.as_string())

        return True

    except Exception as exc:
        if retorn_erro:
            logger.exception("Erro ao enviar e-mail: %s", exc)
        else:
            logger.debug("Erro ao enviar e-mail: %s", exc)
        if raise_on_error:
            raise
        return False

    finally:
        for temp_file_path in temp_files_to_remove:
            try:
                os.unlink(temp_file_path)
            except OSError as exc:
                logger.debug("Nao foi possivel remover arquivo temporario %s: %s", temp_file_path, exc)
