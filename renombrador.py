#!/usr/bin/env python3
"""
Renombra una carpeta y todos los archivos que contiene.

1. Abre un cuadro de diálogo para que el usuario elija la carpeta.
2. Solicita por teclado el nuevo nombre base.
3. Cambia el nombre de la carpeta al texto indicado.
4. Cambia el nombre de cada archivo de la carpeta a:
      <texto> (1).<extensión>, <texto> (2).<extensión>, …

Requisitos:
- Python 3.8 o superior.
- Tkinter (viene incluido en la instalación oficial de Python para Windows/macOS).
"""

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox

def main() -> None:
    # Iniciar interfaz oculta (solo para los diálogos)
    root = tk.Tk()
    root.withdraw()

    # 1) Elegir carpeta
    carpeta_origen = filedialog.askdirectory(
        title="Selecciona la carpeta que quieres renombrar")
    if not carpeta_origen:
        messagebox.showinfo("Operación cancelada", "No se seleccionó ninguna carpeta.")
        sys.exit()

    carpeta_path = Path(carpeta_origen)
    parent = carpeta_path.parent

    # 2) Pedir texto
    nuevo_nombre = simpledialog.askstring(
        "Nuevo nombre",
        "Escribe el nuevo nombre para la carpeta y sus archivos:",
        parent=root)

    if not nuevo_nombre:
        messagebox.showinfo("Operación cancelada", "No se introdujo ningún texto.")
        sys.exit()

    # 3) Renombrar la carpeta
    nueva_carpeta_path = parent / nuevo_nombre
    try:
        carpeta_path.rename(nueva_carpeta_path)
    except FileExistsError:
        messagebox.showerror(
            "Error",
            f"Ya existe una carpeta llamada «{nuevo_nombre}». "
            "Mueve o renombra esa carpeta primero."
        )
        sys.exit()

    # 4) Renombrar archivos dentro de la nueva carpeta
    archivos = sorted(
        [f for f in nueva_carpeta_path.iterdir() if f.is_file()],
        key=lambda p: p.stat().st_mtime  # opcional: por fecha de modificación
    )

    for idx, archivo in enumerate(archivos, start=1):
        sufijo = f" ({idx})"
        ext = archivo.suffix  # incluye el punto, p. ej. ".jpg"
        nuevo_archivo = nueva_carpeta_path / f"{nuevo_nombre}{sufijo}{ext}"

        # Si el nombre destino existe, se añade un guion bajo para evitar colisiones
        contador_colision = 1
        while nuevo_archivo.exists():
            nuevo_archivo = nueva_carpeta_path / f"{nuevo_nombre}{sufijo}_{contador_colision}{ext}"
            contador_colision += 1

        archivo.rename(nuevo_archivo)

    messagebox.showinfo(
        "Proceso completado",
        f"Carpeta y archivos renombrados correctamente a «{nuevo_nombre}»."
    )

if __name__ == "__main__":
    main()
