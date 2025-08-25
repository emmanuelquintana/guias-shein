from PIL import Image, ImageOps, ImageStat, ImageTk
import os
import tkinter as tk
from tkinter import filedialog, ttk
import logging
from datetime import datetime
import customtkinter as ctk
from pathlib import Path
from itertools import cycle

# ----------------------------
# Configurar logging
# ----------------------------
def configurar_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    nombre_log = f'logs/procesamiento_{datetime.now():%Y%m%d_%H%M%S}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(nombre_log),
            logging.StreamHandler()
        ]
    )

# ----------------------------
# Selección de carpeta
# ----------------------------
def seleccionar_carpeta(titulo):
    root = tk.Tk()
    root.withdraw()
    return filedialog.askdirectory(title=titulo)

# ----------------------------
# Preview y selector de imágenes
# ----------------------------
class ImagenPreview(ctk.CTkFrame):
    def __init__(self, master, ruta, *args, **kw):
        super().__init__(master, *args, **kw)
        self.configure(fg_color=("white","gray20"))
        img = Image.open(ruta)
        img.thumbnail((150,150))
        self.photo = ImageTk.PhotoImage(img)
        cont = ctk.CTkFrame(self, corner_radius=10, fg_color=("white","gray25"))
        cont.pack(padx=5, pady=5, fill="both", expand=True)
        ctk.CTkLabel(cont, image=self.photo, text="").pack(padx=5, pady=5)
        name = Path(ruta).name
        if len(name) > 20:
            name = name[:17] + "..."
        ctk.CTkLabel(cont, text=name, font=("Roboto",12)).pack(pady=2)
        self.var = tk.BooleanVar()
        ctk.CTkCheckBox(cont, variable=self.var, text="").pack(pady=5)

class SelectorImagenes(ctk.CTkToplevel):
    def __init__(self, carpeta):
        super().__init__()
        w,h = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{int(w*0.8)}x{int(h*0.8)}")
        self.minsize(1200,800)
        self.state('zoomed')
        self.title("Selecciona las imágenes")
        self.configure(fg_color=("white","gray17"))
        self.seleccionadas = set()

        frm = ctk.CTkFrame(self, corner_radius=15)
        frm.pack(fill="both", expand=True, padx=30, pady=30)
        ctk.CTkLabel(
            frm,
            text="Selecciona las imágenes que necesitan margen",
            font=("Roboto",28,"bold")
        ).pack(pady=25)

        scroll = ctk.CTkScrollableFrame(frm, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=20)
        scroll.grid_columnconfigure(tuple(range(6)), weight=1)

        self.previews = []
        row = col = 0
        for raiz, _, archivos in os.walk(carpeta):
            if 'Shein' in raiz:
                continue
            for f in archivos:
                if f.lower().endswith(('.png','.jpg','.jpeg','.webp')):
                    ruta = os.path.join(raiz, f)
                    pv = ImagenPreview(scroll, ruta)
                    pv.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
                    self.previews.append((ruta, pv))
                    col += 1
                    if col >= 6:
                        col = 0
                        row += 1

        btns = ctk.CTkFrame(frm, fg_color="transparent")
        btns.pack(pady=25)
        for text, cmd in [
            ("Seleccionar Todo", self._sel_all),
            ("Deseleccionar Todo", self._desel_all),
            ("Confirmar", self._confirm)
        ]:
            b = ctk.CTkButton(
                btns, text=text, command=cmd,
                font=("Roboto",16), corner_radius=10,
                width=180, height=40
            )
            b.pack(side="left", padx=10)

        self.mainloop()

    def _sel_all(self):
        for _, pv in self.previews:
            pv.var.set(True)
    def _desel_all(self):
        for _, pv in self.previews:
            pv.var.set(False)
    def _confirm(self):
        self.seleccionadas = {r for r, pv in self.previews if pv.var.get()}
        self.quit()

def mostrar_selector_imagenes(carpeta):
    dlg = SelectorImagenes(carpeta)
    try:
        dlg.destroy()
    except:
        pass
    return dlg.seleccionadas

# ----------------------------
# Configuraciones de marketplaces
# ----------------------------
class ConfiguracionMarketplace:
    def __init__(self, nombre, ancho, alto, formato, peso_max=None, margen=0.94):
        self.nombre = nombre
        self.ancho = ancho
        self.alto = alto
        self.formato = formato
        self.peso_maximo = peso_max
        self.margen = margen

CONFIGURACIONES = {
    "SHEIN":     ConfiguracionMarketplace("Shein",    1340, 1785, "PNG", margen=0.97),
    "AMAZON":    ConfiguracionMarketplace("Amazon",   1600, 1600, "PNG"),
    "LIVERPOOL": ConfiguracionMarketplace("Liverpool", 940, 1215, "JPEG", 500, margen=0.98),
}

class SelectorMarketplace(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        self.title("Seleccionar Marketplace")
        self.geometry("400x400")
        self.configure(fg_color=("white","gray17"))
        frm = ctk.CTkFrame(self, corner_radius=15)
        frm.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frm, text="Selecciona el Marketplace", font=("Roboto",20,"bold")).pack(pady=20)
        self.elegido = None
        for cfg in CONFIGURACIONES.values():
            ctk.CTkButton(
                frm, text=cfg.nombre,
                command=lambda c=cfg: self._sel(c),
                font=("Roboto",14), corner_radius=10,
                hover_color=("#2CC985","#2FA572"), height=35
            ).pack(fill="x", padx=20, pady=8)
        ttk.Separator(frm, orient='horizontal').pack(fill="x", padx=20, pady=10)
        ctk.CTkButton(
            frm, text="Procesar TODOS",
            command=lambda: self._sel("TODOS"),
            font=("Roboto",14,"bold"), corner_radius=10,
            fg_color="#FF6B6B", hover_color="#FF4949", height=40
        ).pack(fill="x", padx=20, pady=8)
        self.mainloop()

    def _sel(self, c):
        self.elegido = c
        self.quit()

def seleccionar_marketplace():
    dlg = SelectorMarketplace()
    try:
        sel = dlg.elegido
        dlg.destroy()
    except:
        sel = None
    return sel

# ----------------------------
# Ajuste de imagen
# ----------------------------
def ajustar_imagen(ruta, config, aplicar_margen=False):
    img = Image.open(ruta)
    # Convertir transparencia a RGB
    if img.mode in ('RGBA','LA') or (img.mode=='P' and 'transparency' in img.info):
        fondo = Image.new('RGB', img.size, (255,255,255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        fondo.paste(img, mask=img.split()[-1])
        img = fondo

    w_o, h_o = img.size
    w_d, h_d = config.ancho, config.alto

    # SHEIN con margen mínimo en costados
    if config.nombre.upper() == "SHEIN" and aplicar_margen:
        m = 10  # margen lateral en px
        # Cover vertical: ajustar por altura
        factor_h = h_d / h_o
        nw = int(w_o * factor_h)
        nh = h_d
        # Si queda muy ancho, reducir para que entre con margen
        max_w = w_d - 2*m
        if nw > max_w:
            factor_w = max_w / w_o
            nw = int(w_o * factor_w)
            nh = int(h_o * factor_w)
        img_r = img.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (w_d, h_d), (255,255,255))
        x = (w_d - nw) // 2
        y = 0
        canvas.paste(img_r, (x, y))
        return canvas

    # SHEIN sin margen: cover estándar
    if config.nombre.upper() == "SHEIN":
        factor = max(w_d / w_o, h_d / h_o)
        nw = int(w_o * factor)
        nh = int(h_o * factor)
        img_e = img.resize((nw, nh), Image.Resampling.LANCZOS)
        x0 = (nw - w_d) // 2
        y0 = (nh - h_d) // 2
        return img_e.crop((x0, y0, x0 + w_d, y0 + h_d))

    # Otros marketplaces con margen: contain
    if aplicar_margen:
        f = config.margen
        if w_o / h_o > w_d / h_d:
            nw = int(w_d * f)
            nh = int(nw / (w_o / h_o))
        else:
            nh = int(h_d * f)
            nw = int(nh * (w_o / h_o))
        img_r = img.resize((nw, nh), Image.Resampling.LANCZOS)
        canvas = Image.new('RGB', (w_d, h_d), (255,255,255))
        canvas.paste(img_r, ((w_d - nw)//2, (h_d - nh)//2))
        return canvas

    # COVER por defecto
    factor = max(w_d / w_o, h_d / h_o)
    nw = int(w_o * factor)
    nh = int(h_o * factor)
    img_e = img.resize((nw, nh), Image.Resampling.LANCZOS)
    x0 = (nw - w_d) // 2
    y0 = (nh - h_d) // 2
    return img_e.crop((x0, y0, x0 + w_d, y0 + h_d))

# ----------------------------
# Guardar imagen optimizada
# ----------------------------
def guardar_imagen_optimizada(img, ruta_salida, config):
    if config.formato == "JPEG":
        calidad = 95
        while True:
            img.save(ruta_salida, format="JPEG", quality=calidad)
            if config.peso_maximo:
                tam = os.path.getsize(ruta_salida) / 1024
                if tam <= config.peso_maximo:
                    break
                calidad -= 5
                if calidad < 30:
                    logging.warning(f"No se pudo reducir {ruta_salida} < {config.peso_maximo}KB")
                    break
            else:
                break
    else:
        img.save(ruta_salida, format="PNG")

# ----------------------------
# Procesar carpeta
# ----------------------------
def procesar_carpeta(carpeta):
    cfg = seleccionar_marketplace()
    if not cfg:
        logging.error("No se seleccionó marketplace. Saliendo…")
        return
    imgs_margin = mostrar_selector_imagenes(carpeta)

    def _proc(c):
        out_root = os.path.join(carpeta, c.nombre)
        os.makedirs(out_root, exist_ok=True)
        cont = errs = 0
        excl = set(x.nombre for x in CONFIGURACIONES.values())
        for raiz, dirs, archivos in os.walk(carpeta):
            for mkt in excl:
                if mkt in dirs:
                    dirs.remove(mkt)
            rel = os.path.relpath(raiz, carpeta)
            if any(m in rel.split(os.sep) for m in excl):
                continue
            for f in archivos:
                if f.lower().endswith(('.png','.jpg','.jpeg','.webp')):
                    src = os.path.join(raiz, f)
                    dst_dir = os.path.join(out_root, rel)
                    os.makedirs(dst_dir, exist_ok=True)
                    try:
                        aplicar = (src in imgs_margin)
                        img_p = ajustar_imagen(src, c, aplicar_margen=aplicar)
                        name, _ = os.path.splitext(f)
                        ext = '.jpg' if c.formato == "JPEG" else '.png'
                        out = os.path.join(dst_dir, f"procesado_{name}{ext}")
                        guardar_imagen_optimizada(img_p, out, c)
                        cont += 1
                    except Exception as e:
                        logging.error(f"Error procesando {src}: {e}")
                        errs += 1
        logging.info(f"{c.nombre}: procesadas={cont}, errores={errs}")

    if cfg == "TODOS":
        for c in CONFIGURACIONES.values():
            _proc(c)
    else:
        _proc(cfg)

# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    configurar_logging()
    try:
        logging.info("Seleccionando carpeta de entrada…")
        carpeta = seleccionar_carpeta("Selecciona la carpeta con las imágenes")
        if not carpeta:
            logging.error("No se seleccionó carpeta. Saliendo.")
            exit()
        procesar_carpeta(carpeta)
        logging.info("¡Procesamiento completado exitosamente!")
    except Exception as e:
        logging.error(f"Error general en la aplicación: {e}")
