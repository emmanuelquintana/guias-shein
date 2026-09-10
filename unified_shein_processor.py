import io
import os
import threading
import fitz  # PyMuPDF
from PIL import Image
from docx import Document
from docx.shared import Cm, Inches
from docx.enum.table import WD_ROW_HEIGHT_RULE
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import logging
import platform
import subprocess
import queue
import shutil
import smtplib
from tkinterdnd2 import TkinterDnD, DND_FILES

from gmail_sender import (
    clear_app_password,
    group_email_batches,
    load_app_password,
    send_marketplace_emails,
)

try:
    from docx2pdf import convert
except ImportError:
    convert = None

# ============================================================================
# LOGGING SETUP
# ============================================================================
class QueueHandler(logging.Handler):
    """Log handler sending messages to a queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

# ============================================================================
# UTILITIES
# ============================================================================
def open_folder(path: str):
    """Abre la carpeta en el explorador según el SO."""
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        print(f"Error opening folder: {e}")

def remove_even_pages(pdf_in: str, pdf_out: str):
    """Genera un PDF con solo páginas impares (usado p.ej. en TikTok laser)."""
    try:
        if not os.path.exists(pdf_in):
            return False, f"⚠️ PDF de origen no existe: {pdf_in}"
        src = fitz.open(pdf_in)
        dst = fitz.open()
        for i in range(src.page_count):
            if (i + 1) % 2 == 1:
                dst.insert_pdf(src, from_page=i, to_page=i)
        dst.save(pdf_out)
        dst.close()
        src.close()
        return True, f"✅ PDF (impares extraídos) generado: {os.path.basename(pdf_out)}"
    except Exception as e:
        return False, f"❌ Error al filtrar impares: {e}"

# ============================================================================
# CORE PROCESSING
# ============================================================================
def process_pdf_for_day(pdf_path, brand, directory, today, logger, shortcuts_dict, day_label=""):
    """
    Procesa un único PDF. 
    directory: la carpeta en la que deben guardarse todos los resultados de este día.
    shortcuts_dict: diccionario con rutas 'imprimir' y 'correo' para auto-copia.
    Devuelve: (booleano_exito, cantidad_de_guias_procesadas)
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"❌ Error abriendo PDF ({day_label}): {e}")
        return False, 0

    total = doc.page_count
    logger.info(f"📄 Total páginas [{day_label or 'Único'}]: {total}")

    day_suffix = f" {day_label}" if day_label else ""

    marketplace = "tiktok" if brand == "TikTok" else "shein"

    # --- A) IMPARES -> PDF TÉRMICO ---
    odd_pdf = fitz.open()
    odd_indices = []
    for i in range(total):
        if (i + 1) % 2 == 1:
            odd_pdf.insert_pdf(doc, from_page=i, to_page=i)
            odd_indices.append(i + 1)
    
    odd_name = f"{brand} Guias {marketplace} {today}{day_suffix} - impresora termica.pdf"
    odd_path = os.path.join(directory, odd_name)
    try:
        odd_pdf.save(odd_path)
        shutil.copy2(odd_path, os.path.join(shortcuts_dict["imprimir"], odd_name))
        logger.info(f"✅ Térmico guardado ({odd_name}).")
    except Exception as e:
        logger.error(f"❌ Error guardando térmico: {e}")
    finally:
        odd_pdf.close()

    # --- B) PARES -> DOCX (Imágenes) ---
    even_indices = [i + 1 for i in range(total) if (i + 1) % 2 == 0]
    images = []
    scale = 2  # Zoom para calidad
    
    # Extraer imágenes pares
    for idx in even_indices:
        try:
            page = doc.load_page(idx - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if img.getbbox():
                images.append((idx, img))
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo página {idx}: {e}")

    # Configurar Word
    doc_word = Document()
    for section in doc_word.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.left_margin = Cm(0.5)
        section.right_margin = Cm(0.5)
        section.top_margin = Cm(0.5)
        section.bottom_margin = Cm(0.5)

    section = doc_word.sections[0]
    usable_w_cm = section.page_width.cm - section.left_margin.cm - section.right_margin.cm
    usable_h_cm = section.page_height.cm - section.top_margin.cm - section.bottom_margin.cm

    if brand == "TikTok":
        per_page = 2
        rows, cols = 2, 1
        picture_width = Cm(usable_w_cm * 0.98)
        out_suffix = "tiktok laser"
    else:
        per_page = 4
        rows, cols = 2, 2
        picture_width = Cm(7.0)
        out_suffix = "impresora laser"

    count = 0
    table = None
    temps_to_delete = []
    
    for idx, img in images:
        if count % per_page == 0:
            table = doc_word.add_table(rows=rows, cols=cols)
            table.autofit = False
            table.allow_autofit = False
            
            if brand == "TikTok":
                half_h_cm = usable_h_cm / 2.0
                for r in range(2):
                    table.rows[r].height_rule = WD_ROW_HEIGHT_RULE.EXACTLY
                    table.rows[r].height = Cm(half_h_cm)

        pos = count % per_page
        row_i = pos // cols
        col_i = pos % cols
        cell = table.cell(row_i, col_i)

        temp_png = os.path.join(directory, f"temp_{brand}_{day_label}_{idx}.png")
        img.save(temp_png, quality=100)
        temps_to_delete.append(temp_png)
        
        try:
            run = cell.paragraphs[0].add_run()
            run.add_picture(temp_png, width=picture_width)
            count += 1
            if count % per_page == 0:
                doc_word.add_page_break()
        except Exception as e:
            logger.error(f"❌ Error insertando img {idx} en Word: {e}")

    docx_name = f"{brand} Guias {marketplace} {today}{day_suffix} - {out_suffix}.docx"
    docx_path = os.path.join(directory, docx_name)
    try:
        doc_word.save(docx_path)
        shutil.copy2(docx_path, os.path.join(shortcuts_dict["correo"], docx_name))
        logger.info(f"✅ DOCX láser guardado ({docx_name}).")
    except Exception as e:
        logger.error(f"❌ Error guardando DOCX: {e}")

    # Limpiar PNGs temporales
    for tmp in temps_to_delete:
        try:
            os.remove(tmp)
        except:
            pass

    # --- C) DOCX -> PDF ---
    produced_pdf_path = None
    if convert:
        pdf_name = f"{brand} Guias {marketplace} {today}{day_suffix} - {out_suffix}.pdf"
        produced_pdf_path = os.path.join(directory, pdf_name)
        try:
            logger.info(f"⏳ Convirtiendo a PDF (Tomará un momento)...")
            convert(docx_path, produced_pdf_path)
            shutil.copy2(produced_pdf_path, os.path.join(shortcuts_dict["correo"], pdf_name))
            logger.info("✅ PDF Láser generado.")
        except Exception as e:
            logger.error(f"⚠️ Falló conversión DOCX->PDF: {e}")
    else:
        logger.warning("⚠️ docx2pdf no está instalado. Omitiendo conversión a PDF.")

    # --- D) TikTok Extra: Impares Laser ---
    if brand == "TikTok" and produced_pdf_path:
        laser_odds_pdf_name = f"{brand} Guias {marketplace} {today}{day_suffix} - laser (solo impares).pdf"
        laser_odds_pdf = os.path.join(directory, laser_odds_pdf_name)
        ok, msg = remove_even_pages(produced_pdf_path, laser_odds_pdf)
        if ok:
            shutil.copy2(laser_odds_pdf, os.path.join(shortcuts_dict["correo"], laser_odds_pdf_name))
            logger.info(msg)
        else:
            logger.error(msg)
    
    doc.close()
    return True, len(images)

def run_processing_pipeline(brand, mode, files_dict, logger, clear_shortcuts=False):
    """
    Función envoltorio para gestionar las carpetas y los diferentes modos (Único, Semana, Puente).
    """
    logger.info("==========================================")
    logger.info(f"▶ INICIANDO PROCESO | MODO: {mode}")
    logger.info(f"🔖 Marca: {brand}")
    
    today = datetime.now().strftime("%d-%m-%Y")
    desktop = os.path.expanduser("~/Desktop")
    base_shein = os.path.join(desktop, "guias-shein")
    
    imprimir_dir = os.path.join(base_shein, "imprimir")
    correo_dir = os.path.join(base_shein, "correo")
    
    if clear_shortcuts:
        logger.info("🗑 Vaciando carpetas cortafuegos (imprimir, correo)...")
        for d in [imprimir_dir, correo_dir]:
            if os.path.exists(d):
                for filename in os.listdir(d):
                    file_path = os.path.join(d, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                    except Exception as e:
                        logger.warning(f"⚠️ No se pudo limpiar {file_path}: {e}")
                        
    os.makedirs(imprimir_dir, exist_ok=True)
    os.makedirs(correo_dir, exist_ok=True)
    shortcuts_dict = {"imprimir": imprimir_dir, "correo": correo_dir}
    
    # Crear carpeta principal para el día de hoy
    safe_brand = brand.replace(" ", "_")
    day_folder_root = os.path.join(base_shein, today, safe_brand)
    os.makedirs(day_folder_root, exist_ok=True)
    
    logger.info(f"📂 Guardando maestras en: {day_folder_root}")

    reporte_guias = {}

    if mode == "Día Único":
        pdf_path = files_dict.get("Único")
        if not pdf_path:
            logger.error("❌ Archivo Único no especificado.")
            return False, day_folder_root, {}
        
        success, count = process_pdf_for_day(pdf_path, brand, day_folder_root, today, logger, shortcuts_dict, day_label="")
        if success:
            reporte_guias["Único"] = count

    else:
        # Varios Días
        days_to_process = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sabado", "Domingo"]
            
        for day in days_to_process:
            pdf_path = files_dict.get(day)
            if not pdf_path:
                # Al ser opcionales, si no hay archivo simplemente lo ignoramos
                continue
                
            logger.info(f"\n--- 🗓 Procesando {day} ---")
            day_folder = os.path.join(day_folder_root, day)
            os.makedirs(day_folder, exist_ok=True)
            success, count = process_pdf_for_day(pdf_path, brand, day_folder, today, logger, shortcuts_dict, day_label=day)
            if success:
                reporte_guias[day] = count

    logger.info("✨ PROCESO COMPLETADO EXITOSAMENTE ✨")
    return True, day_folder_root, reporte_guias

# ============================================================================
# EXTRA SERVICE: MERCADO LIBRE - FIRST PAGE AS FULL-PAGE ROTATED IMAGE
# ============================================================================
def process_ml_first_page(file_paths, output_dir, logger, imprimir_dir=None, correo_dir=None):
    """
    Toma la primera hoja de cada PDF, recorta espacio en blanco,
    orienta en portrait y combina todas en UN solo PDF de salida.
    Copia el PDF final a imprimir_dir si se proporciona.
    """
    os.makedirs(output_dir, exist_ok=True)

    if not file_paths:
        return False, output_dir, 0

    out_doc = fitz.open()
    total_processed = 0

    for path in file_paths:
        try:
            source_doc = fitz.open(path)
            if source_doc.page_count == 0:
                logger.warning(f"⚠️ Sin páginas: {os.path.basename(path)}")
                source_doc.close()
                continue

            first_page = source_doc[0]
            scale = 3
            pix = first_page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            source_doc.close()

            # Recortar espacio en blanco alrededor del contenido
            img_gray = img.convert("L")
            mask = img_gray.point(lambda p: 0 if p > 240 else 255)
            bbox = mask.getbbox()
            if bbox:
                pad = 15
                iw, ih = img.size
                bbox = (
                    max(0, bbox[0] - pad),
                    max(0, bbox[1] - pad),
                    min(iw, bbox[2] + pad),
                    min(ih, bbox[3] + pad),
                )
                img = img.crop(bbox)

            # Si el contenido es landscape, rotarlo para que quede portrait
            if img.width > img.height:
                img = img.rotate(-90, expand=True)

            # Página portrait con las dimensiones exactas de la imagen
            dpi = 72 * scale
            page_w_pts = img.width * 72 / dpi
            page_h_pts = img.height * 72 / dpi

            out_page = out_doc.new_page(width=page_w_pts, height=page_h_pts)

            img_bytes = io.BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            out_page.insert_image(out_page.rect, stream=img_bytes.read())

            logger.info(f"✅ Hoja agregada: {os.path.basename(path)}")
            total_processed += 1
        except Exception as e:
            logger.error(f"❌ Error procesando {os.path.basename(path)}: {e}")

    if total_processed == 0:
        out_doc.close()
        return False, output_dir, 0

    # Un solo PDF combinado con timestamp
    timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
    output_name = f"ML_guias_{timestamp}.pdf"
    output_path = os.path.join(output_dir, output_name)
    out_doc.save(output_path)
    out_doc.close()

    # Copiar a carpeta imprimir (igual que las demás marcas)
    if imprimir_dir:
        try:
            os.makedirs(imprimir_dir, exist_ok=True)
            shutil.copy2(output_path, os.path.join(imprimir_dir, output_name))
            logger.info(f"📋 Copiado a imprimir: {output_name}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo copiar a imprimir: {e}")

    if correo_dir:
        try:
            os.makedirs(correo_dir, exist_ok=True)
            shutil.copy2(output_path, os.path.join(correo_dir, output_name))
            logger.info(f"📋 Copiado a correo: {output_name}")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo copiar a correo: {e}")

    logger.info(f"✅ PDF combinado guardado: {output_name} ({total_processed} hoja(s)).")
    return True, output_dir, total_processed

# ============================================================================
# EXTRA SERVICE: AMAZON - UNIR GUIAS Y FACTURAS
# ============================================================================
def process_amazon_service(guias_paths, facturas_paths, logger, imprimir_dir=None, correo_dir=None, day_folder_root=None):
    os.makedirs(day_folder_root, exist_ok=True)
    timestamp = datetime.now().strftime("%d-%m-%Y_%H%M%S")
    
    total_guias = len(guias_paths)
    total_facturas = len(facturas_paths)
    
    success_guias = False
    success_facturas = False
    
    if total_guias > 0:
        logger.info(f"⏳ Uniendo {total_guias} archivo(s) de Guías...")
        guias_name = f"Amazon_Guias_{timestamp}.pdf"
        guias_path = os.path.join(day_folder_root, guias_name)
        out_doc = fitz.open()
        for path in guias_paths:
            try:
                doc = fitz.open(path)
                out_doc.insert_pdf(doc)
                doc.close()
            except Exception as e:
                logger.error(f"❌ Error procesando {os.path.basename(path)}: {e}")
        out_doc.save(guias_path)
        out_doc.close()
        
        if imprimir_dir:
            try:
                os.makedirs(imprimir_dir, exist_ok=True)
                shutil.copy2(guias_path, os.path.join(imprimir_dir, guias_name))
                logger.info(f"📋 Guías copiadas a imprimir: {guias_name}")
                success_guias = True
            except Exception as e:
                logger.warning(f"⚠️ No se pudo copiar a imprimir: {e}")
                
    if total_facturas > 0:
        logger.info(f"⏳ Uniendo {total_facturas} archivo(s) de Facturas...")
        facturas_name = f"Amazon_Facturas_{timestamp}.pdf"
        facturas_path = os.path.join(day_folder_root, facturas_name)
        out_doc = fitz.open()
        for path in facturas_paths:
            try:
                doc = fitz.open(path)
                out_doc.insert_pdf(doc)
                doc.close()
            except Exception as e:
                logger.error(f"❌ Error procesando {os.path.basename(path)}: {e}")
        out_doc.save(facturas_path)
        out_doc.close()
        
        if correo_dir:
            try:
                os.makedirs(correo_dir, exist_ok=True)
                shutil.copy2(facturas_path, os.path.join(correo_dir, facturas_name))
                logger.info(f"📋 Facturas copiadas a correo: {facturas_name}")
                success_facturas = True
            except Exception as e:
                logger.warning(f"⚠️ No se pudo copiar a correo: {e}")
                
    if total_guias == 0 and total_facturas == 0:
        return False, day_folder_root, 0, 0
        
    return True, day_folder_root, total_guias, total_facturas

# ============================================================================
# GUI / APPLICATION
# ============================================================================
class CustomAlert(ctk.CTkToplevel):
    def __init__(self, master, title, message, is_error=False, accent_color="#0066cc"):
        super().__init__(master)
        self.title(" " + title)
        self.geometry("450x250")
        self.resizable(False, False)
        
        self.attributes("-topmost", True)
        self.focus_force()
        self.grab_set()

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        icon = "❌ " if is_error else "✅ "
        lbl_msg = ctk.CTkLabel(frame, text=icon + message, font=ctk.CTkFont(size=14), wraplength=380, justify="left")
        lbl_msg.grid(row=0, column=0, pady=(10, 20), sticky="nsew")
        
        btn_color = "#e11d48" if is_error else accent_color
        btn_ok = ctk.CTkButton(frame, text="Aceptar", command=self.destroy, fg_color=btn_color, height=40, font=ctk.CTkFont(weight="bold"))
        btn_ok.grid(row=1, column=0, pady=(0, 10))


class CustomConfirm(ctk.CTkToplevel):
    def __init__(self, master, title, message, accent_color="#166534"):
        super().__init__(master)
        self.result = False
        self.title(" " + title)
        self.geometry("500x390")
        self.resizable(False, False)
        self.transient(master)
        self.attributes("-topmost", True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        self.bind("<Escape>", lambda _event: self.cancel())

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=0, column=0, sticky="nsew", padx=28, pady=24)
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        heading = ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold"), anchor="w")
        heading.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        body = ctk.CTkLabel(frame, text=message, font=ctk.CTkFont(size=13), wraplength=430, justify="left", anchor="nw")
        body.grid(row=1, column=0, sticky="nsew")

        actions = ctk.CTkFrame(frame, fg_color="transparent")
        actions.grid(row=2, column=0, sticky="e", pady=(20, 0))
        self.btn_cancel = ctk.CTkButton(
            actions,
            text="Cancelar",
            command=self.cancel,
            width=120,
            height=40,
            fg_color="#3a3a3c",
            hover_color="#48484a",
        )
        self.btn_cancel.grid(row=0, column=0, padx=(0, 10))
        btn_confirm = ctk.CTkButton(
            actions,
            text="Enviar",
            command=self.confirm,
            width=120,
            height=40,
            fg_color=accent_color,
            hover_color="#14532d",
            font=ctk.CTkFont(weight="bold"),
        )
        btn_confirm.grid(row=0, column=1)
        self.after(100, self.btn_cancel.focus_set)

    def confirm(self):
        self.result = True
        self.destroy()

    def cancel(self):
        self.destroy()


def ask_custom_confirm(master, title, message):
    dialog = CustomConfirm(master, title, message)
    master.wait_window(dialog)
    return dialog.result


class TkinterDnD_CTk(ctk.CTk, TkinterDnD.DnDWrapper):
    """Mix-in class to enable TkinterDnD within CustomTkinter."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class UnifiedSheinApp(TkinterDnD_CTk):
    GMAIL_SENDER = "quintanatorresjoseemmanuel1dm@gmail.com"
    EMAIL_RECIPIENTS = ("cecilia.unipride@gmail.com", "almacenu4u@gmail.com")

    def __init__(self):
        super().__init__()

        # Configuración de Tkinter Theme (Clean Dark Modern)
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.title("Sistema de Procesamiento Shein")
        self.geometry("900x650")
        self.minsize(800, 600)

        # Variables de estado
        self.log_queue = queue.Queue()
        self.processing = False
        self.result_folder = None
        self.folders_cleared_this_session = False
        self.gmail_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".gmail.json")
        
        self.mode_var = ctk.StringVar(value="Día Único")
        self.brand_var = ctk.StringVar(value="Marcas y Licencias")
        self.files_selected = {}
        self.rotation_files = []
        
        # Variables Amazon
        self.amazon_guias_files = []
        self.amazon_facturas_files = []
        
        # UI Layout principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_main_area()

        # Variables para colores dinámicos
        self.brand_colors = {
            "Marcas y Licencias": {"primary": "#0066cc", "hover": "#0052a3", "accent": "#0066cc"}, # Azul
            "Pure and Simple": {"primary": "#28a745", "hover": "#218838", "accent": "#28a745"}, # Verde
            "TikTok": {"primary": "#ff0050", "hover": "#cc0040", "accent": "#ff0050"}, # Rosa/Rojo TikTok
            "Mercado Libre": {"primary": "#f9d342", "hover": "#e3b517", "accent": "#f9d342"}, # Amarillo Mercado Libre
            "Amazon": {"primary": "#ff9900", "hover": "#cc7a00", "accent": "#ff9900"} # Naranja Amazon
        }
        
        # Inicializar colores dinámicos
        self.on_brand_change(self.brand_var.get())

        # Activar Drag & Drop en la ventana principal
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_file_drop)

        # Iniciar polling del log
        self.after(100, self.poll_log_queue)

    def setup_sidebar(self):
        # Sidebar Frame
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(9, weight=1) # Filler

        # Título
        lbl_title = ctk.CTkLabel(self.sidebar_frame, text="Shein Processor", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_title.grid(row=0, column=0, padx=20, pady=(30, 20))

        # Marca
        lbl_brand = ctk.CTkLabel(self.sidebar_frame, text="Marca", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray70")
        lbl_brand.grid(row=1, column=0, padx=20, pady=(10, 0), sticky="w")
        
        self.brand_menu = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Marcas y Licencias", "Pure and Simple", "TikTok", "Mercado Libre", "Amazon"],
            variable=self.brand_var,
            font=("Roboto", 13),
            command=self.on_brand_change
        )
        self.brand_menu.grid(row=2, column=0, padx=20, pady=(5, 15), sticky="ew")

        # Modo (Tiempo)
        lbl_mode = ctk.CTkLabel(self.sidebar_frame, text="Modo de Operación", font=ctk.CTkFont(size=12, weight="bold"), text_color="gray70")
        lbl_mode.grid(row=3, column=0, padx=20, pady=(10, 0), sticky="w")

        # Usamos SegmentedButton para el modo
        self.mode_selector = ctk.CTkSegmentedButton(
            self.sidebar_frame,
            values=["Día Único", "Varios Días"],
            variable=self.mode_var,
            command=self.on_mode_change
        )
        self.mode_selector.grid(row=4, column=0, padx=20, pady=(5, 30), sticky="ew")

        # Botón de Procesar
        self.btn_process = ctk.CTkButton(
            self.sidebar_frame, 
            text="Procesar Guías", 
            font=ctk.CTkFont(size=15, weight="bold"),
            height=45,
            command=self.start_thread,
            fg_color="#0066cc",
            hover_color="#0052a3"
        )
        self.btn_process.grid(row=5, column=0, padx=20, pady=10, sticky="ew")

        # Botón Abrir Carpeta
        self.btn_open_folder = ctk.CTkButton(
            self.sidebar_frame,
            text="Abrir Carpeta Generada",
            command=self.open_output_folder,
            fg_color="transparent",
            text_color="#0066cc",
            border_width=1,
            border_color="gray50",
            hover_color="#333333",
            state="disabled"
        )
        self.btn_open_folder.grid(row=6, column=0, padx=20, pady=10, sticky="ew")

        self.btn_send_email = ctk.CTkButton(
            self.sidebar_frame,
            text="Enviar correos",
            command=self.start_email_send,
            fg_color="#166534",
            hover_color="#14532d",
            height=42,
            font=ctk.CTkFont(weight="bold"),
        )
        self.btn_send_email.grid(row=7, column=0, padx=20, pady=(10, 4), sticky="ew")

        self.email_recipient_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Destinos: Cecilia + Almacén U4U",
            wraplength=210,
            font=ctk.CTkFont(size=11),
            text_color="gray70",
        )
        self.email_recipient_label.grid(row=8, column=0, padx=20, pady=(0, 12), sticky="ew")

    def setup_main_area(self):
        # Frame derecho principal
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_rowconfigure(4, weight=1) # El log se expande
        self.main_frame.grid_columnconfigure(0, weight=1)

        # 1. Área de selección de archivos
        self.files_container = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1c1c1e")
        self.files_container.grid(row=0, column=0, sticky="ew", pady=(0, 20))
        self.files_container.grid_columnconfigure(0, weight=1)
        
        lbl_files = ctk.CTkLabel(self.files_container, text="Selección de Archivos PDF", font=ctk.CTkFont(size=16, weight="bold"))
        lbl_files.grid(row=0, column=0, pady=(15, 5), padx=20, sticky="w")

        # Sub-frame dinámico para los campos de archivo
        self.dynamic_fields_frame = ctk.CTkFrame(self.files_container, fg_color="transparent")
        self.dynamic_fields_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.dynamic_fields_frame.grid_columnconfigure(1, weight=1)

        self.path_entries = {}
        self.build_file_fields() # Construir inicial (Día Único)

        # 2. Servicio extra: Superponer la primera hoja rotada sobre el PDF
        self.rotate_service_frame = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1c1c1e")
        self.rotate_service_frame.grid(row=1, column=0, sticky="ew", pady=(0, 20))
        self.rotate_service_frame.grid_remove()
        self.rotate_service_frame.grid_columnconfigure(1, weight=1)

        self.rotate_title_label = ctk.CTkLabel(
            self.rotate_service_frame,
            text="Servicio Mercado Libre: Primera hoja rotada (full hoja)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#f9d342"
        )
        self.rotate_title_label.grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        self.rotate_selected_label = ctk.CTkLabel(self.rotate_service_frame, text="0 archivos seleccionados", font=ctk.CTkFont(size=12), text_color="gray70")
        self.rotate_selected_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")

        self.btn_select_rotate_files = ctk.CTkButton(
            self.rotate_service_frame,
            text="Examinar (varios PDFs)",
            width=220,
            command=self.select_multiple_files_for_rotation,
            fg_color="#f9d342",
            hover_color="#e3b517",
            text_color="#000000"
        )
        self.btn_select_rotate_files.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 15), sticky="ew")

        # 3. Servicio Amazon: Unir Guías y Facturas
        self.amazon_service_frame = ctk.CTkFrame(self.main_frame, corner_radius=15, fg_color="#1c1c1e")
        self.amazon_service_frame.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        self.amazon_service_frame.grid_remove()
        self.amazon_service_frame.grid_columnconfigure(1, weight=1)

        self.amazon_title_label = ctk.CTkLabel(
            self.amazon_service_frame,
            text="Servicio Amazon: Unir Guías y Facturas",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ff9900"
        )
        self.amazon_title_label.grid(row=0, column=0, columnspan=3, padx=20, pady=(15, 10), sticky="w")

        self.amazon_guias_label = ctk.CTkLabel(self.amazon_service_frame, text="0 Guías seleccionadas", font=ctk.CTkFont(size=12), text_color="gray70")
        self.amazon_guias_label.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        self.btn_select_amazon_guias = ctk.CTkButton(
            self.amazon_service_frame,
            text="Examinar Guías",
            width=220,
            command=self.select_multiple_guias_amazon,
            fg_color="#ff9900",
            hover_color="#cc7a00",
            text_color="#000000"
        )
        self.btn_select_amazon_guias.grid(row=1, column=1, padx=20, pady=(0, 10), sticky="e")

        self.amazon_facturas_label = ctk.CTkLabel(self.amazon_service_frame, text="0 Facturas seleccionadas", font=ctk.CTkFont(size=12), text_color="gray70")
        self.amazon_facturas_label.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")

        self.btn_select_amazon_facturas = ctk.CTkButton(
            self.amazon_service_frame,
            text="Examinar Facturas",
            width=220,
            command=self.select_multiple_facturas_amazon,
            fg_color="#ff9900",
            hover_color="#cc7a00",
            text_color="#000000"
        )
        self.btn_select_amazon_facturas.grid(row=2, column=1, padx=20, pady=(0, 15), sticky="e")

        # 4. Área de Progreso y Título Logs
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, mode="indeterminate", height=6)
        self.progress_bar.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.progress_bar.set(0) # Visualmente apagado hasta que inicie
        
        lbl_log = ctk.CTkLabel(self.main_frame, text="Consola de Operaciones", font=ctk.CTkFont(size=14, weight="bold"))
        lbl_log.grid(row=3, column=0, sticky="w", padx=20, pady=(0, 5))

        # 5. Log Box
        self.log_box = ctk.CTkTextbox(
            self.main_frame, 
            corner_radius=10,
            fg_color="#0d0d0d", 
            text_color="#e0e0e0",
            font=("Consolas", 12),
            state="disabled"
        )
        self.log_box.grid(row=4, column=0, padx=20, sticky="nsew")
        
        # Etiquetas de color para el log
        self.log_box.tag_config("success", foreground="#a6e3a1") # Soft Green
        self.log_box.tag_config("error", foreground="#f38ba8")   # Red
        self.log_box.tag_config("warning", foreground="#f9e2af") # Yellow
        self.log_box.tag_config("header", foreground="#89b4fa")  # Blue
        self.log_box.tag_config("normal", foreground="#e0e0e0")  # Default

    def build_file_fields(self):
        # Limpiar
        for widget in self.dynamic_fields_frame.winfo_children():
            widget.destroy()
        
        self.files_selected.clear()
        self.path_entries.clear()

        mode = self.mode_var.get()
        if mode == "Día Único":
            keys = ["Único"]
        else:
            keys = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sabado", "Domingo"]

        for i, key in enumerate(keys):
            lbl_text = f"{key} (Opcional):" if mode == "Varios Días" else f"{key}:"
            lbl = ctk.CTkLabel(self.dynamic_fields_frame, text=lbl_text, width=130, anchor="e", font=ctk.CTkFont(weight="bold"))
            lbl.grid(row=i, column=0, padx=(0, 10), pady=10, sticky="e")

            entry = ctk.CTkEntry(self.dynamic_fields_frame, placeholder_text="Seleccione un archivo...", state="disabled", fg_color="#2c2c2e", border_color="#3a3a3c")
            entry.grid(row=i, column=1, padx=(0, 10), pady=10, sticky="ew")
            self.path_entries[key] = entry

            btn = ctk.CTkButton(
                self.dynamic_fields_frame, 
                text="Examinar", 
                width=100, 
                command=lambda k=key: self.select_file(k),
                fg_color="#3a3a3c",
                hover_color="#48484a"
            )
            btn.grid(row=i, column=2, pady=10)

    def on_mode_change(self, value):
        self.build_file_fields()

    def on_brand_change(self, value):
        colors = self.brand_colors.get(value, self.brand_colors["Marcas y Licencias"])
        
        self.btn_process.configure(fg_color=colors["primary"], hover_color=colors["hover"])
        self.mode_selector.configure(selected_color=colors["primary"], selected_hover_color=colors["hover"])
        self.btn_open_folder.configure(text_color=colors["accent"])
        self.progress_bar.configure(progress_color=colors["accent"])

        if value == "Mercado Libre":
            self.files_container.grid_remove()
            if hasattr(self, 'amazon_service_frame'):
                self.amazon_service_frame.grid_remove()
            self.rotate_service_frame.grid()
            self.rotate_title_label.configure(text="Servicio Mercado Libre: Primera hoja rotada (full hoja)", text_color=colors["accent"])
        elif value == "Amazon":
            self.files_container.grid_remove()
            self.rotate_service_frame.grid_remove()
            if hasattr(self, 'amazon_service_frame'):
                self.amazon_service_frame.grid()
        else:
            self.rotate_service_frame.grid_remove()
            if hasattr(self, 'amazon_service_frame'):
                self.amazon_service_frame.grid_remove()
            self.files_container.grid()
        
        # Limpiar seleccion al cambiar marca
        self.files_selected.clear()
        for entry in self.path_entries.values():
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.configure(state="disabled")
            
        if hasattr(self, 'amazon_guias_files'):
            self.amazon_guias_files.clear()
            self.amazon_guias_label.configure(text="0 Guías seleccionadas")
        if hasattr(self, 'amazon_facturas_files'):
            self.amazon_facturas_files.clear()
            self.amazon_facturas_label.configure(text="0 Facturas seleccionadas")
        if hasattr(self, 'rotation_files'):
            self.rotation_files.clear()
            if hasattr(self, 'rotate_selected_label'):
                self.rotate_selected_label.configure(text="0 archivos seleccionados")

    def select_file(self, key):
        path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if path:
            self.assign_file_to_key(key, path)

    def assign_file_to_key(self, key, path):
        """Asigna una ruta de archivo a una caja del formulario"""
        self.files_selected[key] = path
        entry = self.path_entries[key]
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, os.path.basename(path))
        entry.configure(state="disabled")

    def select_multiple_files_for_rotation(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if paths:
            self.rotation_files = list(paths)
            self.rotate_selected_label.configure(text=f"{len(paths)} archivos seleccionados")
            self.log(f"✅ {len(paths)} archivos seleccionados para rotar primera hoja.")
            self.start_rotation_service()

    def select_multiple_guias_amazon(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if paths:
            self.amazon_guias_files = list(paths)
            self.amazon_guias_label.configure(text=f"{len(paths)} Guías seleccionadas")
            self.log(f"✅ {len(paths)} Guías de Amazon seleccionadas.")

    def select_multiple_facturas_amazon(self):
        paths = filedialog.askopenfilenames(filetypes=[("PDF files", "*.pdf")])
        if paths:
            self.amazon_facturas_files = list(paths)
            self.amazon_facturas_label.configure(text=f"{len(paths)} Facturas seleccionadas")
            self.log(f"✅ {len(paths)} Facturas de Amazon seleccionadas.")

    def start_rotation_service(self):
        if self.processing:
            return

        if not self.rotation_files:
            messagebox.showwarning("Faltan Archivos", "Selecciona al menos un PDF para rotar la primera hoja.")
            return

        self.processing = True
        self.btn_process.configure(state="disabled")
        self.btn_open_folder.configure(state="disabled")
        self.mode_selector.configure(state="disabled")
        self.brand_menu.configure(state="disabled")
        self.btn_select_rotate_files.configure(state="disabled")
        self.progress_bar.start()

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        logger = logging.getLogger("AppLogger")
        logger.setLevel(logging.INFO)
        if logger.handlers:
            logger.handlers = []
        queue_h = QueueHandler(self.log_queue)
        queue_h.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(queue_h)

        files_to_process = list(self.rotation_files)
        t = threading.Thread(target=self.run_rotation_service, args=(files_to_process, logger))
        t.daemon = True
        t.start()

    def run_rotation_service(self, files, logger):
        desktop = os.path.expanduser("~/Desktop")
        output_dir = os.path.join(desktop, "mercado-libre", "primeras_hojas_rotadas")
        imprimir_dir = os.path.join(desktop, "guias-shein", "imprimir")
        correo_dir = os.path.join(desktop, "guias-shein", "correo")
        success, folder, processed = process_ml_first_page(
            files, output_dir, logger, imprimir_dir=imprimir_dir, correo_dir=correo_dir
        )
        self.result_folder = folder
        self.after(0, lambda: self.finish_rotation_service(success, processed))

    def finish_rotation_service(self, success, processed):
        self.progress_bar.stop()
        self.processing = False
        self.btn_process.configure(state="normal")
        self.mode_selector.configure(state="normal")
        self.brand_menu.configure(state="normal")
        if hasattr(self, 'btn_select_rotate_files'):
            self.btn_select_rotate_files.configure(state="normal")
        if hasattr(self, 'btn_select_amazon_guias'):
            self.btn_select_amazon_guias.configure(state="normal")
            self.btn_select_amazon_facturas.configure(state="normal")

        if success:
            self.btn_open_folder.configure(state="normal")
            self.log(f"\n✅ Servicio completado: {processed} primera(s) hoja(s) procesada(s).")
            CustomAlert(self, "Mercado Libre completado", f"Se generaron {processed} PDF(s) en:\n{self.result_folder}", is_error=False)
        else:
            CustomAlert(self, "Error de Rotación", "No se pudo procesar ningún archivo. Revisa la consola.", is_error=True)

    def on_file_drop(self, event):
        """Gestor de evento para cuando se sueltan uno o múltiples archivos en la aplicación"""
        files = self.tk.splitlist(event.data)
        if not files: return
        
        mode = self.mode_var.get()
        brand = self.brand_var.get()
        
        if brand == "Amazon" or brand == "Mercado Libre":
            self.log("⚠️ Arrastrar y soltar no soportado en este modo, usa los botones 'Examinar'.")
            return
            
        if mode == "Día Único":
            keys = ["Único"]
        else:
            keys = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sabado", "Domingo"]
            
        pdf_files = [f for f in files if f.lower().endswith('.pdf')]
        
        # Asignamos en orden los archivos caídos a las muescas disponibles
        for i, f in enumerate(pdf_files):
            if i < len(keys):
                self.assign_file_to_key(keys[i], f)
        
        if len(pdf_files) > len(keys):
            self.log(f"⚠️ Soltaste {len(pdf_files)} PDFs pero se necesitan {len(keys)}. Los sobrantes se omitieron.")

    def log(self, msg):
        self.log_box.configure(state="normal")
        tag = "normal"
        if "❌" in msg or "Error" in msg or "Falló" in msg:
            tag = "error"
        elif "✅" in msg or "guardado" in msg or "generado" in msg:
            tag = "success"
        elif "⚠️" in msg:
            tag = "warning"
        elif "▶" in msg or "Iniciando" in msg or "---" in msg or "===" in msg:
            tag = "header"
            
        self.log_box.insert("end", msg + "\n", tag)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def poll_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log(msg)
        except queue.Empty:
            pass
        self.after(100, self.poll_log_queue)

    def open_output_folder(self):
        if self.result_folder and os.path.exists(self.result_folder):
            open_folder(self.result_folder)

    def start_email_send(self):
        if self.processing:
            return

        correo_dir = os.path.join(os.path.expanduser("~/Desktop"), "guias-shein", "correo")
        try:
            password = load_app_password(self.gmail_config_path)
        except Exception:
            messagebox.showerror(
                "Gmail no configurado",
                "No se pudo leer la configuración cifrada de Gmail.",
            )
            return

        if not password:
            messagebox.showerror(
                "Gmail no configurado",
                "No se encontró la configuración cifrada de Gmail.",
            )
            return

        batches = group_email_batches(correo_dir)
        if not batches:
            messagebox.showwarning("Sin archivos", "No hay PDFs de marketplaces en la carpeta 'correo'.")
            return

        summary = "\n".join(
            f"• {marketplace} - {day}: {len(paths)} PDF(s)"
            for (marketplace, day), paths in batches.items()
        )
        if not ask_custom_confirm(
            self,
            "Confirmar envío",
            f"Cada correo se enviará a los mismos 2 destinatarios:\n{self.EMAIL_RECIPIENTS[0]}\n{self.EMAIL_RECIPIENTS[1]}\n\n{summary}\n\n¿Continuar?",
        ):
            return

        self.processing = True
        self.btn_send_email.configure(state="disabled", text="Enviando...")
        self.btn_process.configure(state="disabled")
        self.progress_bar.start()
        self.log("▶ Enviando correos...")
        logger = logging.getLogger("EmailLogger")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(queue_handler)
        threading.Thread(target=self.run_email_send, args=(password, correo_dir, logger), daemon=True).start()

    def run_email_send(self, password, correo_dir, logger):
        try:
            result = send_marketplace_emails(
                self.GMAIL_SENDER,
                password.replace(" ", ""),
                self.EMAIL_RECIPIENTS,
                correo_dir,
                logger,
            )
            self.after(0, lambda: self.finish_email_send(result, None))
        except smtplib.SMTPAuthenticationError:
            clear_app_password(self.gmail_config_path)
            message = "Gmail rechazó la contraseña. Vuelve a pulsar el botón y pega una contraseña de aplicación nueva."
            self.after(0, lambda error=message: self.finish_email_send(None, error))
        except Exception as error:
            message = str(error)
            self.after(0, lambda error=message: self.finish_email_send(None, error))

    def finish_email_send(self, result, error):
        self.processing = False
        self.progress_bar.stop()
        self.btn_send_email.configure(state="normal", text="Enviar correos")
        self.btn_process.configure(state="normal")
        if error:
            self.log(f"❌ Error enviando correo: {error}")
            CustomAlert(self, "Error de correo", error, is_error=True)
            return
        details = "\n".join(f"• {marketplace}: {count} PDF(s)" for marketplace, count in result.items())
        recipients = "\n".join(self.EMAIL_RECIPIENTS)
        self.log(f"✅ Correos enviados a {', '.join(self.EMAIL_RECIPIENTS)}.")
        CustomAlert(self, "Correos enviados", f"Destinatarios:\n{recipients}\n\n{details}")

    def start_thread(self):
        if self.processing: return

        # Validación
        mode = self.mode_var.get()
        brand = self.brand_var.get()
        
        if brand == "Amazon":
            if not self.amazon_guias_files and not self.amazon_facturas_files:
                messagebox.showwarning("Faltan Archivos", "Por favor seleccione Guías o Facturas para procesar.")
                return
        elif brand == "Mercado Libre":
            if not self.rotation_files:
                messagebox.showwarning("Faltan Archivos", "Por favor seleccione archivos para rotar (Mercado Libre).")
                return
        else:
            if len(self.files_selected) == 0:
                messagebox.showwarning("Faltan Archivos", "Por favor seleccione al menos un archivo PDF para procesar.")
                return

        # Marcar que se limpiaran los shortcuts en la sesion a la primera iteracion
        clear_shortcuts = not self.folders_cleared_this_session
        self.folders_cleared_this_session = True

        # UI Lock
        self.processing = True
        self.btn_process.configure(state="disabled", text="Procesando...")
        self.btn_open_folder.configure(state="disabled")
        self.mode_selector.configure(state="disabled")
        self.brand_menu.configure(state="disabled")
        if hasattr(self, 'btn_select_rotate_files'):
            self.btn_select_rotate_files.configure(state="disabled")
        if hasattr(self, 'btn_select_amazon_guias'):
            self.btn_select_amazon_guias.configure(state="disabled")
            self.btn_select_amazon_facturas.configure(state="disabled")
        self.progress_bar.start()

        for btn in self.dynamic_fields_frame.winfo_children():
            if isinstance(btn, ctk.CTkButton):
                btn.configure(state="disabled")

        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        # Setup Thread Logger
        logger = logging.getLogger("AppLogger")
        logger.setLevel(logging.INFO)
        if logger.handlers:
            logger.handlers = []
        queue_h = QueueHandler(self.log_queue)
        queue_h.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(queue_h)

        if brand == "Amazon":
            guias = list(self.amazon_guias_files)
            facturas = list(self.amazon_facturas_files)
            t = threading.Thread(target=self.run_amazon_service, args=(guias, facturas, logger, clear_shortcuts))
            t.daemon = True
            t.start()
        elif brand == "Mercado Libre":
            files = list(self.rotation_files)
            t = threading.Thread(target=self.run_rotation_service, args=(files, logger))
            t.daemon = True
            t.start()
        else:
            files_locked = self.files_selected.copy()
            t = threading.Thread(target=self.run_process_wrapper, args=(brand, mode, files_locked, logger, clear_shortcuts))
            t.daemon = True
            t.start()

    def run_amazon_service(self, guias, facturas, logger, clear_shortcuts):
        desktop = os.path.expanduser("~/Desktop")
        base_shein = os.path.join(desktop, "guias-shein")
        
        imprimir_dir = os.path.join(base_shein, "imprimir")
        correo_dir = os.path.join(base_shein, "correo")
        
        if clear_shortcuts:
            logger.info("🗑 Vaciando carpetas cortafuegos (imprimir, correo)...")
            for d in [imprimir_dir, correo_dir]:
                if os.path.exists(d):
                    for filename in os.listdir(d):
                        file_path = os.path.join(d, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            logger.warning(f"⚠️ No se pudo limpiar {file_path}: {e}")
                            
        os.makedirs(imprimir_dir, exist_ok=True)
        os.makedirs(correo_dir, exist_ok=True)
        
        today = datetime.now().strftime("%d-%m-%Y")
        day_folder_root = os.path.join(base_shein, today, "Amazon")
        
        success, folder, total_guias, total_facturas = process_amazon_service(guias, facturas, logger, imprimir_dir, correo_dir, day_folder_root)
        self.result_folder = folder
        self.after(0, lambda: self.finish_amazon_service(success, total_guias, total_facturas))

    def finish_amazon_service(self, success, total_guias, total_facturas):
        self.progress_bar.stop()
        self.processing = False
        self.btn_process.configure(state="normal", text="Procesar Guías")
        self.mode_selector.configure(state="normal")
        self.brand_menu.configure(state="normal")
        if hasattr(self, 'btn_select_rotate_files'):
            self.btn_select_rotate_files.configure(state="normal")
        if hasattr(self, 'btn_select_amazon_guias'):
            self.btn_select_amazon_guias.configure(state="normal")
            self.btn_select_amazon_facturas.configure(state="normal")

        accent = self.brand_colors.get("Amazon")["accent"]

        if success:
            self.btn_open_folder.configure(state="normal")
            self.log(f"\n✅ Servicio Amazon completado: {total_guias} archivo(s) de Guías y {total_facturas} archivo(s) de Facturas unidos.")
            msg = f"Guías unidas guardadas en:\n{self.result_folder}\ny copiadas a 'imprimir'.\n\nFacturas unidas guardadas en la misma ruta y copiadas a 'correo'."
            CustomAlert(self, "Amazon completado", msg, is_error=False, accent_color=accent)
        else:
            CustomAlert(self, "Error de Amazon", "No se pudo procesar ningún archivo. Revisa la consola.", is_error=True, accent_color=accent)

    def run_process_wrapper(self, brand, mode, files_dict, logger, clear_shortcuts):
        success, folder, report = run_processing_pipeline(brand, mode, files_dict, logger, clear_shortcuts)
        self.result_folder = os.path.join(os.path.expanduser("~/Desktop"), "guias-shein")
        self.after(0, lambda: self.finish_process(success, report))

    def finish_process(self, success, report):
        self.progress_bar.stop()
        self.processing = False
        self.btn_process.configure(state="normal", text="Procesar Guías")
        self.mode_selector.configure(state="normal")
        self.brand_menu.configure(state="normal")
        if hasattr(self, 'btn_select_rotate_files'):
            self.btn_select_rotate_files.configure(state="normal")
        if hasattr(self, 'btn_select_amazon_guias'):
            self.btn_select_amazon_guias.configure(state="normal")
            self.btn_select_amazon_facturas.configure(state="normal")

        for btn in self.dynamic_fields_frame.winfo_children():
            if isinstance(btn, ctk.CTkButton):
                btn.configure(state="normal")

        accent = self.brand_colors.get(self.brand_var.get(), self.brand_colors["Marcas y Licencias"])["accent"]

        if success:
            self.btn_open_folder.configure(state="normal")
            
            # Construir Reporte
            report_str = "\n".join([f"• {dia}: {cnt} guías" for dia, cnt in report.items()])
            total_guias = sum(report.values())
            
            msg = f"Térmica copiadas a: /guias-shein/imprimir\nLáser copiada a: /guias-shein/correo\n\n📊 Total Guías: {total_guias}\n{report_str}"
            self.log(f"\n✅ CONTEO FINAL: {total_guias} Guías procesadas.")
            
            CustomAlert(self, "Proceso Terminado", msg, is_error=False, accent_color=accent)
        else:
            CustomAlert(self, "Error de Procesamiento", "Ocurrió un error. Revisa la consola de operaciones.", is_error=True, accent_color=accent)


if __name__ == "__main__":
    app = UnifiedSheinApp()
    app.mainloop()
