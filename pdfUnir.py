"""
Script: fusionar_pdfs_gui.py
Descripción: Interfaz gráfica (Tkinter) para arrastrar y soltar PDFs y unirlos sin modificar tamaños.
Requisitos:
  - Python 3.9+
  - pip install pypdf tkinterdnd2
Notas:
  - La unión mantiene cada página tal cual (tamaños/orientación sin cambios).
  - Si no está disponible el arrastre (falta tkinterdnd2), el script sigue funcionando con botón "Agregar".
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Drag & Drop opcional via tkinterdnd2
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES  # pip install tkinterdnd2
    DND_AVAILABLE = True
except Exception:
    TkinterDnD = None
    DND_FILES = None
    DND_AVAILABLE = False

try:
    from pypdf import PdfMerger  # pip install pypdf
except Exception as e:
    raise SystemExit("\n[ERROR] Falta dependencia: pypdf\nInstala con: pip install pypdf\n" + str(e))

APP_TITLE = "Unir PDFs – Arrastrar y Soltar"
DEFAULT_OUTPUT = "fusionado.pdf"

class PDFMergerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("760x520")
        self.root.minsize(680, 480)

        self._build_ui()

    def _build_ui(self):
        # Estilos
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=6)
        style.configure("TFrame", background="#f7f7f7")

        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        # Encabezado
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 8))
        lbl = ttk.Label(
            header,
            text=(
                "Arrastra tus PDFs a la caja de abajo (o usa \"Agregar\"). "
                + ("Soporta arrastrar y soltar." if DND_AVAILABLE else "(Para arrastrar, instala 'tkinterdnd2')")
            ),
            anchor="w",
        )
        lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Zona de lista
        center = ttk.Frame(main)
        center.pack(fill=tk.BOTH, expand=True)

        self.listbox = tk.Listbox(
            center,
            selectmode=tk.EXTENDED,
            activestyle="none",
            font=("Segoe UI", 10),
            bg="white",
            highlightthickness=1,
            relief=tk.SOLID,
        )
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        scroll = ttk.Scrollbar(center, orient=tk.VERTICAL, command=self.listbox.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox.config(yscrollcommand=scroll.set)

        # Habilitar DnD si está disponible
        if DND_AVAILABLE:
            try:
                self.listbox.drop_target_register(DND_FILES)
                self.listbox.dnd_bind("<<Drop>>", self.on_drop)
            except Exception:
                # En algunos entornos podría fallar el binding; ignorar y seguir.
                pass

        # Botones laterales (orden y edición)
        right = ttk.Frame(main)
        right.pack(fill=tk.X, pady=(8, 0))

        btns_left = ttk.Frame(right)
        btns_left.pack(side=tk.LEFT)

        ttk.Button(btns_left, text="Agregar PDFs", command=self.add_files).grid(row=0, column=0, padx=4, pady=4, sticky="ew")
        ttk.Button(btns_left, text="Subir ▲", command=lambda: self.move_selection(-1)).grid(row=0, column=1, padx=4, pady=4, sticky="ew")
        ttk.Button(btns_left, text="Bajar ▼", command=lambda: self.move_selection(1)).grid(row=0, column=2, padx=4, pady=4, sticky="ew")
        ttk.Button(btns_left, text="Quitar", command=self.remove_selected).grid(row=0, column=3, padx=4, pady=4, sticky="ew")
        ttk.Button(btns_left, text="Limpiar", command=self.clear_all).grid(row=0, column=4, padx=4, pady=4, sticky="ew")

        btns_right = ttk.Frame(right)
        btns_right.pack(side=tk.RIGHT)
        ttk.Button(btns_right, text="Unir y Guardar…", command=self.merge_and_save).grid(row=0, column=0, padx=4, pady=4)

        # Barra de estado
        self.status = tk.StringVar(value="Listo")
        statusbar = ttk.Label(main, textvariable=self.status, anchor="w")
        statusbar.pack(fill=tk.X, pady=(8, 0))

        # Atajos
        self.root.bind("<Delete>", lambda e: self.remove_selected())
        self.root.bind("<Control-Return>", lambda e: self.merge_and_save())

    # -------- Utilidades --------
    def _is_pdf(self, path: str) -> bool:
        return path.lower().endswith(".pdf")

    def _sanitize_paths(self, data) -> list[str]:
        """Convierte el payload de DnD en una lista de rutas.
        Usa splitlist para soportar rutas con espacios y llaves en Windows.
        """
        try:
            items = self.root.tk.splitlist(data)
        except Exception:
            items = [data]
        paths: list[str] = []
        for p in items:
            p = p.strip()
            # Filtra carpetas: agrega PDFs dentro si el usuario suelta una carpeta
            if os.path.isdir(p):
                for root, _dirs, files in os.walk(p):
                    for f in files:
                        full = os.path.join(root, f)
                        if self._is_pdf(full):
                            paths.append(full)
            else:
                if self._is_pdf(p):
                    paths.append(p)
        return paths

    def _add_unique(self, paths: list[str]):
        existing = set(self.listbox.get(0, tk.END))
        added = 0
        for p in paths:
            if p not in existing and os.path.exists(p):
                self.listbox.insert(tk.END, p)
                existing.add(p)
                added += 1
        self.status.set(f"Agregados {added} archivo(s). Total: {self.listbox.size()}")

    # -------- Eventos --------
    def on_drop(self, event):
        paths = self._sanitize_paths(event.data)
        if not paths:
            self.status.set("No se detectaron PDFs válidos.")
            return
        self._add_unique(paths)

    def add_files(self):
        files = filedialog.askopenfilenames(
            title="Selecciona PDFs",
            filetypes=[("Archivos PDF", "*.pdf")],
        )
        if not files:
            return
        self._add_unique(list(files))

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        # Eliminar de abajo hacia arriba para no desindexar
        for idx in reversed(sel):
            self.listbox.delete(idx)
        self.status.set(f"Eliminado(s) {len(sel)}. Total: {self.listbox.size()}")

    def clear_all(self):
        self.listbox.delete(0, tk.END)
        self.status.set("Lista vaciada")

    def move_selection(self, direction: int):
        # direction: -1 (subir) o 1 (bajar)
        sel = list(self.listbox.curselection())
        if not sel:
            return
        # Soportar múltiples selecciones: reordenar en bloque
        items = list(self.listbox.get(0, tk.END))
        block = [items[i] for i in sel]
        # Eliminar seleccionados
        for i in reversed(sel):
            del items[i]
        # Calcular nueva posición base
        insert_at = max(0, min(len(items), sel[0] + direction))
        if direction > 0:
            insert_at = min(len(items), sel[-1] + 1 + (direction - 1))
        # Insertar de nuevo el bloque
        for i, val in enumerate(block):
            items.insert(insert_at + i, val)
        # Reescribir listbox
        self.listbox.delete(0, tk.END)
        for it in items:
            self.listbox.insert(tk.END, it)
        # Reseleccionar bloque en nueva posición
        self.listbox.selection_clear(0, tk.END)
        for i in range(insert_at, insert_at + len(block)):
            self.listbox.selection_set(i)
        self.listbox.see(insert_at)

    def merge_and_save(self):
        count = self.listbox.size()
        if count == 0:
            messagebox.showwarning("Sin archivos", "Agrega al menos un PDF.")
            return

        dest = filedialog.asksaveasfilename(
            title="Guardar PDF fusionado",
            defaultextension=".pdf",
            initialfile=DEFAULT_OUTPUT,
            filetypes=[("Archivo PDF", "*.pdf")],
        )
        if not dest:
            return

        self.status.set("Uniendo… por favor espera")
        self.root.update_idletasks()

        merger = PdfMerger()
        added = 0
        skipped: list[str] = []

        for idx in range(count):
            path = self.listbox.get(idx)
            try:
                # PdfMerger.append mantiene tamaños/orientación de las páginas
                merger.append(path)  # no modifica páginas
                added += 1
            except Exception as e:
                # Encriptados o dañados se omiten con aviso
                skipped.append(f"{os.path.basename(path)} – {e}")

        if added == 0:
            messagebox.showerror(
                "No se pudo crear",
                "No se pudo añadir ningún PDF. Revisa si están encriptados o dañados.",
            )
            self.status.set("Error al unir PDFs")
            return

        try:
            # Escribir salida
            with open(dest, "wb") as f:
                merger.write(f)
            merger.close()
        except Exception as e:
            merger.close()
            messagebox.showerror("Error al guardar", str(e))
            self.status.set("Error al guardar")
            return

        msg = [f"Se unieron {added} PDF(s) en:\n{dest}"]
        if skipped:
            msg.append("\nOmitidos:")
            msg.extend(skipped)
        messagebox.showinfo("Listo", "\n".join(msg))
        self.status.set("Completado")


def main():
    # Crear root compatible (con o sin DnD)
    if DND_AVAILABLE and TkinterDnD is not None:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    app = PDFMergerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
