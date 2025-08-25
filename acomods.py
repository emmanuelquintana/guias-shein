#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import shutil
from pathlib import Path
import threading

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText

# Extensiones de imagen comunes (ajusta si necesitas)
IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp",
    ".tif", ".tiff", ".gif",
    ".heic", ".heif",
    ".raw", ".arw", ".cr2", ".nef", ".dng"
}

def is_image(path: Path) -> bool:
    return path.suffix.lower() in IMAGE_EXTS

def bytes_from_mb(mb: float) -> int:
    return int(float(mb) * 1024 * 1024)

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Copiar imágenes > N MB (manteniendo estructura)")
        self.geometry("740x520")
        self.resizable(True, True)

        self.src_var = tk.StringVar()
        self.dst_var = tk.StringVar()
        self.min_mb_var = tk.StringVar(value="2")

        self._build_ui()
        self.worker_thread = None
        self.stop_flag = False

    def _build_ui(self):
        pad = {"padx": 10, "pady": 8}

        # Carpeta Origen
        frm1 = ttk.Frame(self)
        frm1.pack(fill="x", **pad)
        ttk.Label(frm1, text="Carpeta origen:").pack(side="left")
        self.src_entry = ttk.Entry(frm1, textvariable=self.src_var)
        self.src_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(frm1, text="Elegir...", command=self.choose_src).pack(side="left")

        # Carpeta Destino
        frm2 = ttk.Frame(self)
        frm2.pack(fill="x", **pad)
        ttk.Label(frm2, text="Carpeta destino:").pack(side="left")
        self.dst_entry = ttk.Entry(frm2, textvariable=self.dst_var)
        self.dst_entry.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(frm2, text="Elegir...", command=self.choose_dst).pack(side="left")

        # Tamaño mínimo
        frm3 = ttk.Frame(self)
        frm3.pack(fill="x", **pad)
        ttk.Label(frm3, text="Tamaño mínimo (MB):").pack(side="left")
        self.min_entry = ttk.Entry(frm3, width=8, textvariable=self.min_mb_var)
        self.min_entry.pack(side="left", padx=8)
        ttk.Label(frm3, text=f"Extensiones: {', '.join(sorted(IMAGE_EXTS))}").pack(side="left", padx=8)

        # Botones
        frm4 = ttk.Frame(self)
        frm4.pack(fill="x", **pad)
        self.run_btn = ttk.Button(frm4, text="Iniciar copia", command=self.start_copy)
        self.run_btn.pack(side="left")
        self.stop_btn = ttk.Button(frm4, text="Detener", command=self.stop_copy, state="disabled")
        self.stop_btn.pack(side="left", padx=8)

        # Log / progreso
        self.log = ScrolledText(self, height=18, state="disabled")
        self.log.pack(fill="both", expand=True, padx=10, pady=(0,10))

        # Barra de progreso
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=10, pady=(0,10))

    def choose_src(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta de ORIGEN")
        if path:
            self.src_var.set(path)

    def choose_dst(self):
        path = filedialog.askdirectory(title="Selecciona la carpeta de DESTINO")
        if path:
            self.dst_var.set(path)

    def log_print(self, msg: str):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")
        self.update_idletasks()

    def start_copy(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        min_mb = self.min_mb_var.get().strip()

        # Validaciones básicas
        if not src or not Path(src).is_dir():
            messagebox.showerror("Error", "Selecciona una carpeta de ORIGEN válida.")
            return
        if not dst:
            messagebox.showerror("Error", "Selecciona una carpeta de DESTINO.")
            return
        try:
            min_mb_val = float(min_mb)
            if min_mb_val <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", "El tamaño mínimo debe ser un número mayor que 0.")
            return

        # Evitar destino dentro de origen (recursión/duplicados)
        try:
            src_res = Path(src).resolve()
            dst_res = Path(dst).resolve()
            if str(dst_res).startswith(str(src_res)):
                messagebox.showerror(
                    "Error",
                    "La carpeta DESTINO no debe estar dentro de la carpeta ORIGEN."
                )
                return
        except Exception:
            pass

        # Preparar UI
        self.stop_flag = False
        self.run_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.progress.config(value=0, maximum=100)

        # Hilo de trabajo
        args = (Path(src), Path(dst), float(min_mb))
        self.worker_thread = threading.Thread(target=self.copy_worker, args=args, daemon=True)
        self.worker_thread.start()
        self.after(200, self.check_thread_done)

    def stop_copy(self):
        self.stop_flag = True
        self.log_print("[INFO] Señal de detener enviada. Terminando lo antes posible...")

    def check_thread_done(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.after(200, self.check_thread_done)
        else:
            self.run_btn.config(state="normal")
            self.stop_btn.config(state="disabled")

    def copy_worker(self, src_root: Path, dst_root: Path, min_mb: float):
        threshold = bytes_from_mb(min_mb)

        # Conteos
        total_files = 0
        total_images = 0
        copied = 0
        skipped_non_image = 0
        skipped_small = 0
        errors = 0

        # Primero contamos para la barra de progreso (opcional)
        all_paths = []
        for root, _, files in os.walk(src_root):
            for name in files:
                all_paths.append(Path(root) / name)

        total_files = len(all_paths)
        self._set_progress(0, max(1, total_files))

        processed = 0
        dst_root.mkdir(parents=True, exist_ok=True)

        for src_file in all_paths:
            if self.stop_flag:
                self.log_print("[CANCELADO] Proceso detenido por el usuario.")
                break

            processed += 1

            if not is_image(src_file):
                skipped_non_image += 1
                self._tick_progress(processed, total_files)
                continue

            total_images += 1
            try:
                size = src_file.stat().st_size
            except OSError:
                errors += 1
                self.log_print(f"[ERROR] No se pudo leer el tamaño: {src_file}")
                self._tick_progress(processed, total_files)
                continue

            if size <= threshold:
                skipped_small += 1
                self._tick_progress(processed, total_files)
                continue

            rel_path = src_file.relative_to(src_root)
            dst_file = dst_root / rel_path
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                if dst_file.exists():
                    try:
                        if dst_file.stat().st_size == size:
                            # mismo tamaño -> lo damos por copiado
                            self._tick_progress(processed, total_files)
                            continue
                    except OSError:
                        pass

                shutil.copy2(src_file, dst_file)
                copied += 1
                self.log_print(f"[COPIADO] {src_file} -> {dst_file} ({size/1024/1024:.2f} MB)")
            except Exception as e:
                errors += 1
                self.log_print(f"[ERROR] Al copiar {src_file} -> {dst_file}: {e}")

            self._tick_progress(processed, total_files)

        # Resumen
        self.log_print("\n=== Resumen ===")
        self.log_print(f"Archivos totales       : {total_files}")
        self.log_print(f"Imágenes analizadas    : {total_images}")
        self.log_print(f"Imágenes copiadas      : {copied}")
        self.log_print(f"No imágenes            : {skipped_non_image}")
        self.log_print(f"Imágenes <= {min_mb} MB: {skipped_small}")
        self.log_print(f"Errores                : {errors}")
        self.log_print(f"Destino                : {dst_root.resolve()}")

    def _set_progress(self, value, maximum):
        self.progress.config(maximum=maximum, value=value)
        self.update_idletasks()

    def _tick_progress(self, processed, total):
        self.progress.config(value=processed, maximum=max(1, total))
        # No forzamos update cada vez para no saturar, pero mantenemos fluido:
        if processed % 20 == 0:
            self.update_idletasks()

if __name__ == "__main__":
    app = App()
    app.mainloop()
