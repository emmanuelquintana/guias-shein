#!/usr/bin/env python3
"""
organizar_formatos_v3.py
GUI para elegir carpeta, mueve vídeos / ISO / RAR-ZIP a 'resultados/'.
Ignora 'Youtube' y 'Games'. Continúa aun si algún archivo da error.
"""

import os
import shutil
from pathlib import Path

# ---------- GUI para escoger carpeta ---------------------------------
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox
except ImportError:
    raise SystemExit("✖ tkinter no está disponible; instala Python con soporte GUI.")

root = tk.Tk()
root.withdraw()

selected = filedialog.askdirectory(
    title="Selecciona la carpeta o disco que deseas ordenar"
)
if not selected:
    messagebox.showinfo("Operación cancelada", "No se seleccionó carpeta.")
    raise SystemExit

BASE_DIR = Path(selected)
# ---------------------------------------------------------------------

EXCLUDE_DIRS = {"Youtube", "Games","SteamLibrary", "Sesion de fotos"}

VIDEO_EXTS = {"mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "mpeg", "mpg", "m4v"}
ISO_EXTS = {"iso"}
COMPRESSED_EXTS = {"rar", "zip"}

RESULTS_DIR = BASE_DIR / "resultados"
SUBFOLDERS = {
    "videos": VIDEO_EXTS,
    "iso": ISO_EXTS,
    "rar_zip": COMPRESSED_EXTS,
}

# 🆕  ───────────────────────────────────────────────────────────────────
moved_count = 0
skipped_files = []
# ──────────────────────────────────────────────────────────────────────


def ensure_dirs():
    for sub in SUBFOLDERS:
        (RESULTS_DIR / sub).mkdir(parents=True, exist_ok=True)


def belongs_to_category(ext: str):
    if ext in VIDEO_EXTS:
        return "videos"
    if ext in ISO_EXTS:
        return "iso"
    if ext in COMPRESSED_EXTS:
        return "rar_zip"
    return None


def handle_file(src_path: Path):
    global moved_count  # 🆕
    category = belongs_to_category(src_path.suffix.lower().lstrip("."))
    if not category:
        return

    dst_dir = RESULTS_DIR / category
    dst_path = dst_dir / src_path.name

    if dst_path.exists():
        stem, ext = src_path.stem, src_path.suffix
        counter = 1
        while True:
            candidate = dst_dir / f"{stem}({counter}){ext}"
            if not candidate.exists():
                dst_path = candidate
                break
            counter += 1

    # 🆕 intenta mover y captura cualquier fallo (permisos, archivo en uso, etc.)
    try:
        shutil.move(src_path, dst_path)
        moved_count += 1
        print(f"✔ MOVED: {src_path}  →  {dst_path}")
    except Exception as e:
        skipped_files.append(src_path)
        print(f"⛔ SKIP : {src_path}  ({e})")


def walk_and_collect():
    for root_dir, dirs, files in os.walk(BASE_DIR):
        current = Path(root_dir).name
        if current in EXCLUDE_DIRS:
            dirs[:] = []
            continue

        for fname in files:
            handle_file(Path(root_dir) / fname)


def main():
    ensure_dirs()
    walk_and_collect()

    # 🆕 guardar log de saltados
    if skipped_files:
        skip_log = RESULTS_DIR / "skipped.txt"
        skip_log.write_text("\n".join(map(str, skipped_files)), encoding="utf-8")

    total_skipped = len(skipped_files)
    messagebox.showinfo(
        "Proceso completado",
        (
            f"🎉 ¡Orden terminado!\n"
            f"Archivos movidos   : {moved_count}\n"
            f"Archivos saltados : {total_skipped}\n\n"
            f"{'Se generó skipped.txt con el detalle.' if total_skipped else ''}"
        ),
    )


if __name__ == "__main__":
    main()
