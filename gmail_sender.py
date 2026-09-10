import base64
import ctypes
import json
import mimetypes
import re
import smtplib
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from ctypes import wintypes
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465
MAX_MESSAGE_BYTES = 25_000_000
DAY_ORDER = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")
DAY_ALIASES = {day.casefold(): day for day in DAY_ORDER} | {
    "miercoles": "Miércoles",
    "sabado": "Sábado",
}


class DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_byte))]


def _protect(value):
    raw = value.encode("utf-8")
    buffer = ctypes.create_string_buffer(raw)
    source = DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = DataBlob()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)
    ):
        raise ctypes.WinError()
    try:
        return base64.b64encode(ctypes.string_at(target.pbData, target.cbData)).decode("ascii")
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


def _unprotect(value):
    raw = base64.b64decode(value)
    buffer = ctypes.create_string_buffer(raw)
    source = DataBlob(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_byte)))
    target = DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)
    ):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(target.pbData, target.cbData).decode("utf-8")
    finally:
        ctypes.windll.kernel32.LocalFree(target.pbData)


def save_app_password(config_path, app_password):
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _protect(app_password.replace(" ", ""))
    path.write_text(json.dumps({"app_password": encrypted}), encoding="utf-8")


def load_app_password(config_path):
    path = Path(config_path)
    if not path.exists():
        return None
    return _unprotect(json.loads(path.read_text(encoding="utf-8"))["app_password"])


def clear_app_password(config_path):
    try:
        Path(config_path).unlink()
    except FileNotFoundError:
        pass


def _marketplace(filename):
    name = filename.casefold()
    if name.startswith("amazon_"):
        return "Amazon"
    if "tiktok" in name:
        return "TikTok"
    if re.search(r"(^|[_ -])ml[_ -]", name) or "mercado libre" in name:
        return "Mercado Libre"
    if "shein" in name:
        return "Shein"
    return None


def _email_marketplace(filename):
    marketplace = _marketplace(filename)
    if marketplace == "Mercado Libre":
        return None
    if marketplace == "TikTok" and "impares" not in filename.casefold():
        return None
    return marketplace


def group_pdfs_by_marketplace(correo_dir):
    groups = defaultdict(list)
    folder = Path(correo_dir)
    if not folder.exists():
        return {}
    for path in sorted(folder.iterdir()):
        marketplace = _email_marketplace(path.name)
        if path.is_file() and path.suffix.casefold() == ".pdf" and marketplace:
            groups[marketplace].append(path)
    # ponytail: Amazon genera snapshots combinados; enviar sólo el último evita adjuntar reintentos antiguos.
    for marketplace in ("Amazon",):
        if groups[marketplace]:
            groups[marketplace] = [max(groups[marketplace], key=lambda path: path.stat().st_mtime)]
    return dict(groups)


def describe_days(paths, now=None):
    found = set()
    for path in paths:
        for token in re.findall(r"[A-Za-zÁÉÍÓÚáéíóú]+", Path(path).stem):
            day = DAY_ALIASES.get(token.casefold())
            if day:
                found.add(day)
    ordered = [day for day in DAY_ORDER if day in found]
    if not ordered:
        ordered = [DAY_ORDER[(now or datetime.now()).weekday()]]
    if len(ordered) == 1:
        return ordered[0]
    return ", ".join(ordered[:-1]) + " y " + ordered[-1]


def group_email_batches(correo_dir):
    batches = defaultdict(list)
    for marketplace, paths in group_pdfs_by_marketplace(correo_dir).items():
        for path in paths:
            batches[(marketplace, describe_days([path]))].append(path)
    return dict(
        sorted(
            batches.items(),
            key=lambda item: (
                item[0][0],
                DAY_ORDER.index(item[0][1]) if item[0][1] in DAY_ORDER else len(DAY_ORDER),
            ),
        )
    )


def send_marketplace_emails(sender, app_password, recipients, correo_dir, logger=None):
    batches = group_email_batches(correo_dir)
    if not batches:
        raise ValueError("No hay PDFs reconocidos en la carpeta correo.")

    messages = []
    total = len(batches)
    for index, ((marketplace, days), paths) in enumerate(batches.items(), 1):
        if logger:
            logger.info(f"📎 Preparando {index}/{total}: {marketplace} - {days} ({len(paths)} PDF(s))")
        message = EmailMessage()
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message["Subject"] = f"Pedidos - {marketplace} - {days}"
        message.set_content(
            f"Hola,\n\nAdjunto los archivos de pedidos de {marketplace} correspondientes a {days}.\n\nSaludos."
        )
        for path in paths:
            mime_type, _ = mimetypes.guess_type(path.name)
            maintype, subtype = (mime_type or "application/pdf").split("/", 1)
            message.add_attachment(path.read_bytes(), maintype=maintype, subtype=subtype, filename=path.name)
        raw_message = message.as_bytes()
        if len(raw_message) > MAX_MESSAGE_BYTES:
            raise ValueError(f"El correo de {marketplace} supera el límite de 25 MB de Gmail.")
        messages.append((marketplace, days, paths, raw_message))

    if logger:
        logger.info(f"🚀 {total} correo(s) preparados. Enviando hasta 3 en paralelo...")

    def send_one(prepared):
        marketplace, days, paths, raw_message = prepared
        if logger:
            logger.info(f"⏳ Enviando: {marketplace} - {days}")
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=60) as smtp:
            smtp.login(sender, app_password)
            smtp.sendmail(sender, recipients, raw_message)
        if logger:
            logger.info(f"✅ Enviado: {marketplace} - {days} ({len(paths)} PDF(s))")

    errors = []
    with ThreadPoolExecutor(max_workers=min(3, total)) as executor:
        futures = {executor.submit(send_one, message): message[:2] for message in messages}
        for future in as_completed(futures):
            marketplace, days = futures[future]
            try:
                future.result()
            except Exception as error:
                errors.append(f"{marketplace} - {days}: {error}")
                if logger:
                    logger.error(f"❌ Falló: {marketplace} - {days}: {error}")

    if errors:
        raise RuntimeError("No se enviaron todos los correos:\n" + "\n".join(errors))
    return {f"{marketplace} - {days}": len(paths) for (marketplace, days), paths in batches.items()}
