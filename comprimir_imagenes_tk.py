import os
import io
import shutil
import threading
from pathlib import Path
from typing import Tuple, Optional

from PIL import Image, ImageOps

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# ---------------------------------------------
# Utilidades
# ---------------------------------------------

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".bmp"}


def is_image_file(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def ensure_dir(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def bytes_to_mb(n: int) -> float:
    return n / (1024 * 1024)


def try_save_to_bytes(img: Image.Image, fmt: str, **save_kwargs) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, **save_kwargs)
    return buf.getvalue()


def orient_image(img: Image.Image) -> Image.Image:
    # Respeta orientación EXIF (no cambia dimensiones “visuales” finales)
    return ImageOps.exif_transpose(img)


def flatten_alpha_to_bg(img: Image.Image, bg_rgb=(255, 255, 255)) -> Image.Image:
    """Aplana transparencia sobre un color de fondo."""
    if img.mode in ("RGBA", "LA") or "transparency" in img.info:
        base = Image.new("RGB", img.size, bg_rgb)
        rgba = img.convert("RGBA")
        base.paste(rgba, mask=rgba.getchannel("A"))
        return base
    return img.convert("RGB")


# ---------------------------------------------
# Compresiones
# ---------------------------------------------

def jpeg_binary_search_under_size(
    img: Image.Image,
    max_bytes: int,
    min_q: int,
    max_q: int,
    exif_bytes: Optional[bytes] = None,
    subsampling: int = 0,     # 0 = 4:4:4, 2 = 4:2:0
    progressive: bool = True,
    optimize: bool = True,
) -> Tuple[bytes, int]:
    """
    Búsqueda binaria de calidad JPEG para estar debajo de max_bytes.
    Devuelve (data, calidad_usada). Lanza ValueError si no logra quedar bajo el límite.
    """
    work = img.convert("RGB")
    best_data = None
    best_q = None
    lo, hi = min_q, max_q
    while lo <= hi:
        mid = (lo + hi) // 2
        data = try_save_to_bytes(
            work,
            "JPEG",
            quality=mid,
            optimize=optimize,
            progressive=progressive,
            subsampling=subsampling,
            exif=exif_bytes if exif_bytes else None,
        )
        if len(data) <= max_bytes:
            best_data = data
            best_q = mid
            lo = mid + 1
        else:
            hi = mid - 1

    if best_data is None:
        raise ValueError("No fue posible comprimir JPEG debajo del límite.")
    return best_data, best_q


def jpeg_force_under_limit(
    img: Image.Image,
    max_bytes: int,
    exif_bytes: Optional[bytes] = None
) -> Tuple[bytes, str]:
    """
    Intenta varias estrategias para GARANTIZAR <= max_bytes manteniendo dimensiones:
      1) subsampling 4:4:4, progressive
      2) subsampling 4:2:0, progressive
      3) subsampling 4:2:0, baseline (no progressive)
      4) último intento: baseline sin optimize
    Devuelve (data, descripcion_estrategia).
    Puede fallar en casos extremos (imágenes gigantescas).
    """
    tries = [
        dict(subsampling=0, progressive=True,  optimize=True,  min_q=10, max_q=95, tag="JPEG 4:4:4 prog"),
        dict(subsampling=2, progressive=True,  optimize=True,  min_q=10, max_q=95, tag="JPEG 4:2:0 prog"),
        dict(subsampling=2, progressive=False, optimize=True,  min_q=5,  max_q=95, tag="JPEG 4:2:0 base"),
        dict(subsampling=2, progressive=False, optimize=False, min_q=1,  max_q=90, tag="JPEG 4:2:0 base (no opt)"),
    ]
    err = None
    for t in tries:
        try:
            data, q = jpeg_binary_search_under_size(
                img, max_bytes,
                min_q=t["min_q"], max_q=t["max_q"],
                exif_bytes=exif_bytes,
                subsampling=t["subsampling"],
                progressive=t["progressive"],
                optimize=t["optimize"]
            )
            return data, f'{t["tag"]} Q={q}'
        except Exception as e:
            err = e
            continue
    raise ValueError(f"No fue posible quedar <= límite incluso con ajustes agresivos: {err}")


def png_optimize(img: Image.Image) -> bytes:
    return try_save_to_bytes(img, "PNG", optimize=True, compress_level=9)


def webp_try(
    img: Image.Image,
    max_bytes: int,
    lossless: bool,
    q_lo: int = 80,
    q_hi: int = 95,
) -> Tuple[Optional[bytes], Optional[int], bool]:
    if lossless:
        data = try_save_to_bytes(img, "WEBP", lossless=True, method=6)
        return (data, None, True) if len(data) <= max_bytes else (None, None, True)

    # Búsqueda binaria de calidad alta
    lo, hi = q_lo, q_hi
    best = None
    best_q = None
    while lo <= hi:
        mid = (lo + hi) // 2
        data = try_save_to_bytes(img, "WEBP", quality=mid, method=6)
        if len(data) <= max_bytes:
            best = data
            best_q = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return (best, best_q, False)


# ---------------------------------------------
# Lógica principal de compresión
# ---------------------------------------------

def compress_keep_dimensions(
    src_file: Path,
    dst_file: Path,
    max_bytes: int,
    allow_webp_lossless: bool,
    allow_webp_visual: bool,
    allow_png_to_jpg: bool,
    png_jpg_bg: str,  # "Blanco" | "Negro"
) -> Tuple[bool, str, Optional[Path]]:
    """
    Comprime/convierte manteniendo dimensiones.
    Intenta que SIEMPRE quede <= max_bytes.
    Retorna (ok, mensaje, ruta_final).
    """
    try:
        with Image.open(src_file) as im0:
            im = orient_image(im0)
            orig_fmt = (im0.format or src_file.suffix.replace(".", "")).upper()
            exif_bytes = im0.info.get("exif", None)

            bg_rgb = (255, 255, 255) if png_jpg_bg.lower().startswith("b") else (0, 0, 0)

            # Si ya pesa <= max_bytes, solo copiar
            orig_size = src_file.stat().st_size
            if orig_size <= max_bytes:
                ensure_dir(dst_file)
                shutil.copy2(src_file, dst_file)
                return True, f"Copiado sin cambios ({bytes_to_mb(orig_size):.2f} MB).", dst_file

            if orig_fmt in {"JPG", "JPEG"}:
                # Recomprensión JPEG con intentos agresivos si hace falta
                data, desc = jpeg_force_under_limit(im, max_bytes, exif_bytes=exif_bytes)
                final = dst_file.with_suffix(".jpg")
                ensure_dir(final)
                with open(final, "wb") as f:
                    f.write(data)
                return True, f"{desc}.", final

            elif orig_fmt == "PNG":
                # 1) PNG sin pérdida
                data_png = png_optimize(im)
                if len(data_png) <= max_bytes:
                    ensure_dir(dst_file)
                    with open(dst_file, "wb") as f:
                        f.write(data_png)
                    return True, "PNG optimizado (sin pérdida).", dst_file

                # 2) Si se permite, convertir a JPG y forzar <= límite
                if allow_png_to_jpg:
                    jpg_img = flatten_alpha_to_bg(im, bg_rgb=bg_rgb)
                    data, desc = jpeg_force_under_limit(jpg_img, max_bytes, exif_bytes=None)
                    final = dst_file.with_suffix(".jpg")
                    ensure_dir(final)
                    with open(final, "wb") as f:
                        f.write(data)
                    return True, f"PNG→JPG {desc}.", final

                # 3) WebP como alternativa si está permitido
                if allow_webp_lossless:
                    data, _, _ = webp_try(im, max_bytes, lossless=True)
                    if data:
                        final = dst_file.with_suffix(".webp")
                        ensure_dir(final)
                        with open(final, "wb") as f:
                            f.write(data)
                        return True, "Convertido a WebP (sin pérdida).", final

                if allow_webp_visual:
                    data, q, _ = webp_try(im, max_bytes, lossless=False, q_lo=70, q_hi=95)
                    if data:
                        final = dst_file.with_suffix(".webp")
                        ensure_dir(final)
                        with open(final, "wb") as f:
                            f.write(data)
                        return True, f"Convertido a WebP (Q={q}).", final

                # Si llega aquí y no se permite JPG, no hay forma sin pérdida seguro
                return False, "PNG optimizado aún > límite y PNG→JPG desactivado.", None

            else:
                # WEBP/TIFF/BMP/etc. Intentar JPEG agresivo (si no hay alfa) y luego WebP
                has_alpha = ("A" in im.getbands()) or (im.mode in ("LA", "RGBA", "P"))
                if not has_alpha:
                    try:
                        data, desc = jpeg_force_under_limit(im, max_bytes, exif_bytes=exif_bytes)
                        final = dst_file.with_suffix(".jpg")
                        ensure_dir(final)
                        with open(final, "wb") as f:
                            f.write(data)
                        return True, f"Convertido a {desc}.", final
                    except Exception:
                        pass

                # WebP (intento visual)
                data, q, _ = webp_try(im, max_bytes, lossless=False, q_lo=70, q_hi=95)
                if data:
                    final = dst_file.with_suffix(".webp")
                    ensure_dir(final)
                    with open(final, "wb") as f:
                        f.write(data)
                    return True, f"Convertido a WebP (Q={q}).", final

                # Último recurso: aplanar y forzar JPEG
                jpg_img = flatten_alpha_to_bg(im, bg_rgb=(255, 255, 255))
                data, desc = jpeg_force_under_limit(jpg_img, max_bytes, exif_bytes=None)
                final = dst_file.with_suffix(".jpg")
                ensure_dir(final)
                with open(final, "wb") as f:
                    f.write(data)
                return True, f"Con alfa → JPG {desc}.", final

    except Exception as e:
        return False, f"ERROR: {e}", None


# ---------------------------------------------
# Interfaz Tk
# ---------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Comprimir imágenes ≤ X MB (misma resolución)")
        self.geometry("820x600")

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.max_mb_var = tk.DoubleVar(value=2.0)

        # Opciones
        self.webp_lossless_var = tk.BooleanVar(value=False)   # por defecto off
        self.webp_visual_var = tk.BooleanVar(value=True)      # por defecto on
        self.png_to_jpg_var = tk.BooleanVar(value=True)       # NUEVO: PNG→JPG
        self.png_bg_var = tk.StringVar(value="Blanco")        # Blanco/Negro

        self.create_widgets()

        self.total_files = 0
        self.processed = 0
        self._thread = None

    def create_widgets(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill="both", expand=True)

        # Origen
        row = ttk.Frame(frm); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Carpeta origen:").pack(side="left")
        ttk.Entry(row, textvariable=self.src_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Seleccionar...", command=self.select_src).pack(side="left")

        # Destino
        row = ttk.Frame(frm); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Carpeta destino:").pack(side="left")
        ttk.Entry(row, textvariable=self.dst_var).pack(side="left", fill="x", expand=True, padx=6)
        ttk.Button(row, text="Seleccionar...", command=self.select_dst).pack(side="left")

        # Opciones tamaño
        row = ttk.Frame(frm); row.pack(fill="x", pady=6)
        ttk.Label(row, text="Tamaño máximo (MB):").pack(side="left")
        ttk.Entry(row, width=7, textvariable=self.max_mb_var).pack(side="left", padx=6)

        # Opciones de formato
        row = ttk.Frame(frm); row.pack(fill="x", pady=6)
        ttk.Checkbutton(row, text="Permitir WebP sin pérdida", variable=self.webp_lossless_var).pack(side="left", padx=(0,10))
        ttk.Checkbutton(row, text="Permitir WebP visual (Q alto)", variable=self.webp_visual_var).pack(side="left", padx=(0,10))
        ttk.Checkbutton(row, text="Permitir PNG → JPG", variable=self.png_to_jpg_var).pack(side="left", padx=(0,10))

        # Fondo para PNG→JPG
        row = ttk.Frame(frm); row.pack(fill="x", pady=4)
        ttk.Label(row, text="Fondo PNG→JPG:").pack(side="left")
        ttk.Combobox(row, textvariable=self.png_bg_var, values=["Blanco", "Negro"], width=10, state="readonly").pack(side="left", padx=6)

        # Progreso
        self.pb = ttk.Progressbar(frm, orient="horizontal", mode="determinate")
        self.pb.pack(fill="x", pady=8)

        # Botones acción
        row = ttk.Frame(frm); row.pack(fill="x", pady=4)
        ttk.Button(row, text="Procesar", command=self.start).pack(side="left")
        ttk.Button(row, text="Cancelar", command=self.cancel).pack(side="left", padx=8)

        # Log
        ttk.Label(frm, text="Registro:").pack(anchor="w")
        self.log = scrolledtext.ScrolledText(frm, height=18)
        self.log.pack(fill="both", expand=True)

    def select_src(self):
        d = filedialog.askdirectory(title="Selecciona carpeta origen")
        if d:
            self.src_var.set(d)

    def select_dst(self):
        d = filedialog.askdirectory(title="Selecciona carpeta destino")
        if d:
            self.dst_var.set(d)

    def start(self):
        src = Path(self.src_var.get().strip())
        dst = Path(self.dst_var.get().strip())
        if not src.is_dir():
            messagebox.showerror("Error", "Selecciona una carpeta ORIGEN válida.")
            return
        if not dst.exists():
            try:
                dst.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo crear la carpeta destino:\n{e}")
                return
        if src.resolve() == dst.resolve():
            messagebox.showerror("Error", "Origen y destino no pueden ser la misma carpeta.")
            return

        # Contar imágenes (para progressbar)
        imgs = [p for p in src.rglob("*") if p.is_file() and is_image_file(p)]
        self.total_files = len(imgs)
        self.processed = 0
        self.pb["maximum"] = max(1, self.total_files)
        self.pb["value"] = 0
        self.log.delete("1.0", "end")
        self.log.insert("end", f"Encontrados {self.total_files} archivos de imagen.\n")
        self.log.see("end")

        # Lanzar hilo
        self._thread = threading.Thread(target=self.worker, daemon=True)
        self._thread.start()

    def cancel(self):
        if self._thread and self._thread.is_alive():
            messagebox.showinfo("Cancelación", "Se intentará cancelar. Espera a que termine el archivo actual.")
        self._thread = None

    def worker(self):
        try:
            src = Path(self.src_var.get().strip())
            dst = Path(self.dst_var.get().strip())
            max_bytes = int(self.max_mb_var.get() * 1024 * 1024)
            allow_webp_lossless = self.webp_lossless_var.get()
            allow_webp_visual = self.webp_visual_var.get()
            allow_png_to_jpg = self.png_to_jpg_var.get()
            png_jpg_bg = self.png_bg_var.get()

            for p in src.rglob("*"):
                if self._thread is None:
                    break
                if not p.is_file() or not is_image_file(p):
                    continue

                rel = p.relative_to(src)
                dst_path_same_ext = dst / rel  # se ajustará extensión si cambia

                ok, msg, out_path = compress_keep_dimensions(
                    p,
                    dst_path_same_ext,
                    max_bytes,
                    allow_webp_lossless,
                    allow_webp_visual,
                    allow_png_to_jpg,
                    png_jpg_bg,
                )
                self.processed += 1
                self.pb["value"] = self.processed
                out_name = out_path.name if out_path else "—"
                self.log.insert("end", f"[{self.processed}/{self.total_files}] {rel} → {out_name} | {msg}\n")
                self.log.see("end")
                self.update_idletasks()

            self.log.insert("end", "Proceso terminado.\n")
            self.log.see("end")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ---------------------------------------------
# Main
# ---------------------------------------------

if __name__ == "__main__":
    Image.MAX_IMAGE_PIXELS = None  # permitir imágenes grandes
    app = App()
    app.mainloop()
