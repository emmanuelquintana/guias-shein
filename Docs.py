#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from datetime import datetime

# --- Solo para elegir carpeta con Tkinter ---
import tkinter as tk
from tkinter import filedialog, messagebox

ALLOWED_EXTS = {".pdf": "PDF", ".docx": "DOCX", ".xlsx": "XLSX"}

def fixed_drives_windows():
    """Devuelve unidades fijas como ['C:\\', 'D:\\'] en Windows."""
    import ctypes
    drives = []
    bitmask = ctypes.cdll.kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            drive = f"{chr(65 + i)}:\\"
            # DRIVE_FIXED = 3
            dtype = ctypes.windll.kernel32.GetDriveTypeW(drive)
            if dtype == 3:
                drives.append(drive)
    return drives

def choose_target_dir():
    """Abre un diálogo para elegir la carpeta destino (solo Tkinter)."""
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askdirectory(
        title="Elige la carpeta destino para 'Archivos Organizados'"
    )
    root.destroy()
    return path

def ensure_type_dirs(target_root):
    os.makedirs(target_root, exist_ok=True)
    for label in set(ALLOWED_EXTS.values()):
        os.makedirs(os.path.join(target_root, label), exist_ok=True)

def unique_path(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 1
    while True:
        candidate = f"{base} ({i}){ext}"
        if not os.path.exists(candidate):
            return candidate
        i += 1

def within(child, ancestor):
    """True si 'child' está dentro de 'ancestor'."""
    try:
        return os.path.commonpath([os.path.abspath(child), os.path.abspath(ancestor)]) == os.path.abspath(ancestor)
    except Exception:
        return False

def scan_sources():
    """Rutas raíz a escanear."""
    if os.name == "nt":
        drives = fixed_drives_windows()
        if not drives:
            return ["C:\\"]
        return drives
    else:
        return ["/"]

def main():
    print("Selecciona la carpeta donde se creará/usarás 'Archivos Organizados'...")
    base = choose_target_dir()
    if not base:
        home_default = os.path.join(os.path.expanduser("~"))
        base = home_default
        print(f"No se eligió carpeta. Usando HOME: {home_default}")

    target_root = os.path.join(base, "Archivos Organizados")
    ensure_type_dirs(target_root)
    type_dirs = {label: os.path.join(target_root, label) for label in set(ALLOWED_EXTS.values())}

    sources = scan_sources()
    print("Escaneando orígenes:", sources)
    print("Destino:", target_root)

    moved = 0
    errors = 0

    for src_root in sources:
        for root, dirs, files in os.walk(src_root, topdown=True, followlinks=False):
            # Evitar adentrarse en la carpeta destino
            if within(root, target_root):
                dirs[:] = []  # no descender
                continue

            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext in ALLOWED_EXTS:
                    src = os.path.join(root, fname)
                    dest_folder = type_dirs[ALLOWED_EXTS[ext]]
                    dest = unique_path(os.path.join(dest_folder, fname))
                    try:
                        # Segunda barrera: no mover si el archivo ya está dentro del destino
                        if within(src, target_root):
                            continue
                        shutil.move(src, dest)
                        moved += 1
                        print(f"[MOVIDO] {src} -> {dest}")
                    except PermissionError:
                        errors += 1
                        print(f"[PERMISO DENEGADO] {src}")
                    except FileNotFoundError:
                        # archivo desapareció entre escaneo y movimiento
                        print(f"[NO ENCONTRADO] {src}")
                    except OSError as e:
                        errors += 1
                        print(f"[ERROR] {src} -> {e}")

    print("\n--- Resumen ---")
    print(f"Archivos movidos: {moved}")
    print(f"Errores: {errors}")
    print(f"Destino final: {target_root}")
    print("Listo.")

if __name__ == "__main__":
    main()
