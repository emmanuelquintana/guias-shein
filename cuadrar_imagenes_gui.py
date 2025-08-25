#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cuadrar imágenes verticales añadiendo espacio a los lados (sin recortar),
ancladas al fondo (de abajo hacia arriba). Preserva nombres y estructura
de carpetas, evita re-procesar la carpeta de salida y ofrece GUI con botón
para iniciar.

Requisitos: Pillow (pip install pillow)
"""

import os
from pathlib import Path
from typing import List, Optional, Tuple

# --- PIL / Pillow ---
from PIL import Image, ImageOps, ImageColor
try:
    # Para Pillow >=10
    from PIL.Image import Resampling
    RZ = Resampling.LANCZOS
except Exception:
    RZ = Image.LANCZOS

# --- Tkinter GUI ---
import tkinter as tk
from tkinter import filedialog, messagebox

# -------------------- Config por defecto --------------------
# Si quieres que el resultado quede EXACTAMENTE en 2000x2000, deja RESIZE_TO_SQUARE = True.
# Si quieres mantener la ALTURA ORIGINAL y SOLO agregar laterales, pon RESIZE_TO_SQUARE = False.
DEFAULT_TARGET_SIZE = 2000
RESIZE_TO_SQUARE = True       # <- cámbialo a False si NO quieres redimensionar al final
DEFAULT_BG_COLOR = "#FFFFFF"  # Fondo blanco
# ------------------------------------------------------------

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


# -------------------- Utilidades de imagen --------------------
def exif_orient(img: Image.Image) -> Image.Image:
    """Aplica orientación EXIF si existe."""
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def parse_color(s: str):
    """Convierte texto a color RGBA; fallback a blanco."""
    try:
        return ImageColor.getcolor(s, "RGBA")
    except Exception:
        return (255, 255, 255, 255)


def ensure_rgb(img: Image.Image, bg=(255, 255, 255, 255)) -> Image.Image:
    """Convierte a RGB mezclando alpha con fondo sólido si hace falta (útil para JPG)."""
    if img.mode in ("RGBA", "LA"):
        bg_img = Image.new("RGBA", img.size, bg)
        bg_img.paste(img, (0, 0), img)
        return bg_img.convert("RGB")
    if img.mode == "P":
        return img.convert("RGB")
    return img


def pad_to_square(img: Image.Image, anchor_bottom=True, background=(255, 255, 255, 255)) -> Image.Image:
    """
    Devuelve una imagen cuadrada agregando padding.
    - Vertical (alto >= ancho): lienzo h x h, padding a los lados, y=0 (anclado abajo).
    - Horizontal (ancho > alto): lienzo w x w, padding arriba; pega imagen al fondo (y=w-h).
    - Cuadrada: igual.
    """
    img = exif_orient(img)
    w, h = img.size

    if h >= w:
        side = h
        canvas = Image.new("RGBA", (side, side), background)
        x = (side - w) // 2
        y = 0 if anchor_bottom else (side - h) // 2
        canvas.paste(img, (x, y))
        return canvas
    else:
        side = w
        canvas = Image.new("RGBA", (side, side), background)
        x = 0 if not anchor_bottom else 0
        y = (side - h) if anchor_bottom else (side - h) // 2
        canvas.paste(img, (x, y))
        return canvas


def process_image(
    in_path: Path,
    out_path: Path,
    target_size: Optional[int],
    do_resize: bool,
    anchor_bottom: bool,
    bg_color_str: str,
):
    """Padding a cuadrado y, opcionalmente, redimensiona a target_size x target_size."""
    background = parse_color(bg_color_str)
    try:
        img = Image.open(in_path)
    except Exception as e:
        print(f"[ERROR] No se pudo abrir {in_path}: {e}")
        return

    squared = pad_to_square(img, anchor_bottom=anchor_bottom, background=background)

    if do_resize and target_size and target_size > 0:
        squared = squared.resize((target_size, target_size), RZ)

    ext = in_path.suffix.lower()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if ext in {".jpg", ".jpeg"}:
        final = ensure_rgb(squared, background)
        final.save(out_path.with_suffix(".jpg"), format="JPEG", quality=95, optimize=True, subsampling=0)
    elif ext in {".png", ".webp", ".bmp", ".tif", ".tiff"}:
        # Si se quiere fondo sólido en PNG, convertir a RGB para ahorrar espacio
        if ext == ".png" and background[3] == 255:
            final = ensure_rgb(squared, background)
            final.save(out_path.with_suffix(".png"), format="PNG", optimize=True)
        else:
            squared.save(out_path.with_suffix(ext), optimize=True)
    else:
        # Fallback a PNG
        squared.save(out_path.with_suffix(".png"), format="PNG", optimize=True)


def walk_images(input_dir: Path) -> List[Path]:
    """Recorre recursivamente la carpeta y devuelve imágenes soportadas."""
    files: List[Path] = []
    for root, _, filenames in os.walk(input_dir):
        for name in filenames:
            if Path(name).suffix.lower() in SUPPORTED_EXTS:
                files.append(Path(root) / name)
    return files


def is_relative_to(child: Path, parent: Path) -> bool:
    """Compatibilidad con Python<3.9 para Path.is_relative_to."""
    try:
        child.relative_to(parent)
        return True
    except Exception:
        return False


# -------------------- GUI --------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cuadrar imágenes (padding lateral)")
        self.geometry("720x380")
        self.minsize(680, 360)

        self.input_dir = tk.StringVar()
        self.output_dir = tk.StringVar()
        self.bg_color = tk.StringVar(value=DEFAULT_BG_COLOR)
        self.target_size = tk.IntVar(value=DEFAULT_TARGET_SIZE)
        self.resize_flag = tk.BooleanVar(value=RESIZE_TO_SQUARE)
        self.anchor_bottom = tk.BooleanVar(value=True)

        self.selected_files: List[str] = []

        self._build()

    def _build(self):
        pad = {"padx": 10, "pady": 6}

        # Rutas
        frm_paths = tk.LabelFrame(self, text="Rutas")
        frm_paths.pack(fill="x", **pad)

        row = tk.Frame(frm_paths); row.pack(fill="x", **pad)
        tk.Label(row, text="Carpeta de entrada:").pack(side="left")
        tk.Entry(row, textvariable=self.input_dir, width=60).pack(side="left", padx=6, fill="x", expand=True)
        tk.Button(row, text="Seleccionar carpeta", command=self.choose_input_dir).pack(side="left", padx=4)
        tk.Button(row, text="Elegir archivos", command=self.choose_files).pack(side="left", padx=4)

        row2 = tk.Frame(frm_paths); row2.pack(fill="x", **pad)
        tk.Label(row2, text="Carpeta de salida:").pack(side="left")
        tk.Entry(row2, textvariable=self.output_dir, width=60).pack(side="left", padx=6, fill="x", expand=True)
        tk.Button(row2, text="Seleccionar", command=self.choose_output_dir).pack(side="left", padx=4)

        # Opciones
        frm_opts = tk.LabelFrame(self, text="Opciones")
        frm_opts.pack(fill="x", **pad)

        row3 = tk.Frame(frm_opts); row3.pack(fill="x", **pad)
        tk.Label(row3, text="Color de fondo:").pack(side="left")
        tk.Entry(row3, textvariable=self.bg_color, width=10).pack(side="left", padx=6)
        tk.Label(row3, text="(p. ej. #FFFFFF o 'white')").pack(side="left")

        row4 = tk.Frame(frm_opts); row4.pack(fill="x", **pad)
        tk.Checkbutton(row4, text="Resultado EXACTO 2000×2000 (redimensionar después del padding)",
                       variable=self.resize_flag).pack(side="left")

        row5 = tk.Frame(frm_opts); row5.pack(fill="x", **pad)
        tk.Label(row5, text="Tamaño final:").pack(side="left")
        tk.Entry(row5, textvariable=self.target_size, width=7).pack(side="left", padx=6)
        tk.Label(row5, text="px").pack(side="left")
        tk.Checkbutton(row5, text="Anclar al fondo (de abajo hacia arriba)",
                       variable=self.anchor_bottom).pack(side="left", padx=16)

        # Progreso + botón grande INICIAR
        frm_act = tk.Frame(self); frm_act.pack(fill="x", **pad)
        self.lbl = tk.Label(frm_act, text="Listo")
        self.lbl.pack(anchor="w")
        self.pb = tk.Scale(frm_act, from_=0, to=100, orient="horizontal", showvalue=False, length=680)
        self.pb.pack(fill="x", pady=6)

        btn = tk.Button(self, text="INICIAR", command=self.process, bg="#1e90ff", fg="white", height=2)
        btn.pack(fill="x", padx=10, pady=10)

    # --- callbacks ---
    def choose_input_dir(self):
        p = filedialog.askdirectory(title="Seleccionar carpeta de entrada")
        if p:
            self.input_dir.set(p)
            self.output_dir.set(os.path.join(p, "_cuadradas"))

    def choose_files(self):
        files = filedialog.askopenfilenames(
            title="Seleccionar imágenes",
            filetypes=[("Imágenes", "*.jpg;*.jpeg;*.png;*.webp;*.bmp;*.tif;*.tiff"),
                       ("Todos", "*.*")]
        )
        if files:
            self.selected_files = list(files)
            base = os.path.commonpath(self.selected_files)
            if os.path.isfile(base):
                base = os.path.dirname(base)
            self.input_dir.set(base)
            self.output_dir.set(os.path.join(base, "_cuadradas"))

    def choose_output_dir(self):
        p = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if p:
            self.output_dir.set(p)

    def process(self):
        inp = self.input_dir.get().strip()
        out = self.output_dir.get().strip()
        if not inp and not self.selected_files:
            messagebox.showerror("Error", "Selecciona una carpeta de entrada o archivos sueltos.")
            return
        if not out:
            messagebox.showerror("Error", "Selecciona la carpeta de salida.")
            return

        input_dir = Path(inp) if inp else None
        output_dir = Path(out)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Construir lista de archivos
        if self.selected_files:
            files = [Path(p) for p in self.selected_files]
        else:
            files = walk_images(input_dir)

        # Evitar procesar archivos dentro de la carpeta de salida
        filtered = []
        for f in files:
            if f.suffix.lower() not in SUPPORTED_EXTS:
                continue
            try:
                if is_relative_to(f.resolve(), output_dir.resolve()):
                    continue
            except Exception:
                pass
            filtered.append(f)

        total = len(filtered)
        if total == 0:
            messagebox.showinfo("Info", "No se encontraron imágenes para procesar.")
            return

        self.lbl.config(text=f"Procesando 0 / {total}…")
        self.pb.config(to=total)
        self.pb.set(0)
        self.update_idletasks()

        for i, in_file in enumerate(filtered, 1):
            # Mantener subcarpetas relativas
            if input_dir and is_relative_to(in_file.resolve(), input_dir.resolve()):
                rel = in_file.resolve().relative_to(input_dir.resolve())
                out_file = output_dir / rel
            else:
                out_file = output_dir / in_file.name

            try:
                process_image(
                    in_file,
                    out_file,
                    target_size=self.target_size.get(),
                    do_resize=self.resize_flag.get(),
                    anchor_bottom=self.anchor_bottom.get(),
                    bg_color_str=self.bg_color.get().strip() or DEFAULT_BG_COLOR,
                )
            except Exception as e:
                print(f"[ERROR] {in_file} -> {e}")

            self.lbl.config(text=f"Procesando {i} / {total}…")
            self.pb.set(i)
            self.update_idletasks()

        self.lbl.config(text=f"Listo: {total} imágenes procesadas en {output_dir}")
        messagebox.showinfo("Completado", f"Se procesaron {total} imágenes.\nSalida: {output_dir}")


# -------------------- Main --------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
