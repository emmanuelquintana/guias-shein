import os
import fitz  # PyMuPDF
from PIL import Image
from docx import Document
from docx.shared import Cm, Inches
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from datetime import datetime
import logging
import threading
import sys

# Intentar importar docx2pdf para conversión Word->PDF
try:
    from docx2pdf import convert
except ImportError:
    convert = None
    print("docx2pdf no está instalado. La conversión a PDF se omitirá.")

# Configurar logging básico (para consola/archivo si se necesita)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuración de CustomTkinter
ctk.set_appearance_mode("System")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class TextHandler(logging.Handler):
    """Handler para redirigir logs a un widget de texto."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert("end", msg + "\n")
            self.text_widget.see("end")
            self.text_widget.configure(state="disabled")
        self.text_widget.after(0, append)

class SheinSplitApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana principal
        self.title("Procesador Guías Shein")
        self.geometry("800x650")

        # Variables de estado
        self.brand_var = ctk.StringVar(value="Marcas y Licencias")
        self.is_weekend_var = ctk.BooleanVar(value=False)
        self.is_puente_var = ctk.BooleanVar(value=False)
        self.files_selected = {}
        self.output_folder = None

        # Grid layout 
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Crear paneles
        self.create_sidebar()
        self.create_main_area()
        self.create_log_area()

        # Configurar logging a la UI
        text_handler = TextHandler(self.log_textbox)
        text_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(text_handler)

    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="SheinTools", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.brand_label = ctk.CTkLabel(self.sidebar_frame, text="Marca:", anchor="w")
        self.brand_label.grid(row=1, column=0, padx=20, pady=(10, 0))

        self.brand_option = ctk.CTkSegmentedButton(self.sidebar_frame, values=["Marcas y Licencias", "Pure and Simple"],
                                                   variable=self.brand_var)
        self.brand_option.grid(row=2, column=0, padx=20, pady=(5, 10))
        
        self.weekend_switch = ctk.CTkSwitch(self.sidebar_frame, text="Modo Fin de Semana", 
                                            variable=self.is_weekend_var, command=self.on_weekend_toggle)
        self.weekend_switch.grid(row=3, column=0, padx=20, pady=10)

        self.puente_switch = ctk.CTkSwitch(self.sidebar_frame, text="Es Puente?", 
                                           variable=self.is_puente_var, command=self.update_file_buttons)
        self.puente_switch.grid(row=4, column=0, padx=20, pady=10)
        self.puente_switch.configure(state="disabled")

        # Botón de Procesar
        self.process_btn = ctk.CTkButton(self.sidebar_frame, text="PROCESAR", command=self.start_thread,
                                         fg_color="#2CC985", hover_color="#229A65")
        self.process_btn.grid(row=5, column=0, padx=20, pady=20)

        # Botón de Abrir Carpeta
        self.open_folder_btn = ctk.CTkButton(self.sidebar_frame, text="Abrir Carpeta", command=self.open_output_folder,
                                             fg_color="#3B8ED0", hover_color="#36719F", state="disabled")
        self.open_folder_btn.grid(row=6, column=0, padx=20, pady=(0, 20))

    def create_main_area(self):
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        self.files_label = ctk.CTkLabel(self.main_frame, text="Selección de Archivos", font=ctk.CTkFont(size=16, weight="bold"))
        self.files_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        self.file_buttons_frame = ctk.CTkFrame(self.main_frame)
        self.file_buttons_frame.grid(row=1, column=0, sticky="ew")
        self.file_buttons_frame.grid_columnconfigure(0, weight=1) # Label
        self.file_buttons_frame.grid_columnconfigure(1, weight=0) # Button

        self.update_file_buttons()

    def create_log_area(self):
        # Área de logs en la parte inferior o integrada
        self.log_textbox = ctk.CTkTextbox(self.main_frame, width=400, height=300)
        self.log_textbox.grid(row=2, column=0, padx=0, pady=(20, 0), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        # Configurar expansión del log
        self.main_frame.grid_rowconfigure(2, weight=1)

    def update_file_buttons(self):
        # Limpiar frame anterior
        for widget in self.file_buttons_frame.winfo_children():
            widget.destroy()

        self.files_selected = {} # Reiniciar selección al cambiar modo
        
        # Diccionario de widgets para acceso posterior
        self.path_labels = {}

        if self.is_weekend_var.get():
            days = ["Viernes", "Sabado", "Domingo"]
            if self.is_puente_var.get():
                days.append("Lunes")
            for i, day in enumerate(days):
                lbl_title = ctk.CTkLabel(self.file_buttons_frame, text=f"{day}:", width=60, anchor="e")
                lbl_title.grid(row=i, column=0, padx=10, pady=5, sticky="e")
                
                path_lbl = ctk.CTkEntry(self.file_buttons_frame, placeholder_text="No seleccionado", state="disabled")
                path_lbl.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                self.path_labels[day] = path_lbl
                
                btn = ctk.CTkButton(self.file_buttons_frame, text="Seleccionar", width=100, 
                                    command=lambda d=day: self.select_file(d))
                btn.grid(row=i, column=2, padx=10, pady=5)
                
            self.file_buttons_frame.grid_columnconfigure(1, weight=1)
        else:
            lbl_title = ctk.CTkLabel(self.file_buttons_frame, text="Archivo PDF:", width=80, anchor="e")
            lbl_title.grid(row=0, column=0, padx=10, pady=5, sticky="e")

            path_lbl = ctk.CTkEntry(self.file_buttons_frame, placeholder_text="No seleccionado", state="disabled")
            path_lbl.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
            self.path_labels["Single"] = path_lbl

            btn = ctk.CTkButton(self.file_buttons_frame, text="Seleccionar", width=100,
                                command=lambda: self.select_file("Single"))
            btn.grid(row=0, column=2, padx=10, pady=5)
            
            self.file_buttons_frame.grid_columnconfigure(1, weight=1)

    def on_weekend_toggle(self):
        if self.is_weekend_var.get():
            self.puente_switch.configure(state="normal")
        else:
            self.is_puente_var.set(False)
            self.puente_switch.configure(state="disabled")
        self.update_file_buttons()

    def select_file(self, key):
        file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file_path:
            self.files_selected[key] = file_path
            # Actualizar visualmente (necesitamos habilitar temporalmente el Entry)
            entry = self.path_labels[key]
            entry.configure(state="normal")
            entry.delete(0, "end")
            entry.insert(0, os.path.basename(file_path))
            entry.configure(state="disabled")

    def open_output_folder(self):
        if self.output_folder and os.path.exists(self.output_folder):
            os.startfile(self.output_folder)

    def start_thread(self):
        # Validaciones
        brand = self.brand_var.get()
        if not brand:
            messagebox.showerror("Error", "Selecciona una marca.")
            return

        weekend = self.is_weekend_var.get()
        puente = self.is_puente_var.get()
        if weekend:
            required_count = 4 if puente else 3
            if len(self.files_selected) < required_count:
                messagebox.showerror("Error", f"Debes seleccionar los {required_count} archivos para fin de semana.")
                return
        else:
            if "Single" not in self.files_selected:
                messagebox.showerror("Error", "Debes seleccionar un archivo PDF.")
                return

        # Deshabilitar botón
        self.process_btn.configure(state="disabled", text="Procesando...")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        self.log_textbox.configure(state="disabled")

        # Iniciar thread
        t = threading.Thread(target=self.run_process, args=(brand, weekend, puente, self.files_selected.copy()))
        t.start()

    def run_process(self, brand, weekend, puente, files):
        try:
            logger.info(f"Iniciando proceso para: {brand}")
            output_folder, today = self.ensure_output_folder(brand)
            logger.info(f"Carpeta de salida: {output_folder}")
            
            # Guardar referencia y habilitar botón (thread-safe)
            self.output_folder = output_folder
            self.after(0, lambda: self.open_folder_btn.configure(state="normal"))

            if weekend:
                days = ["Viernes", "Sabado", "Domingo"]
                if puente:
                    days.append("Lunes")
                    
                for d in days:
                    if d not in files:
                        logger.error(f"Falta archivo para {d}")
                        continue
                    
                    day_dir = os.path.join(output_folder, d)
                    os.makedirs(day_dir, exist_ok=True)
                    logger.info(f"--- Procesando {d} ---")
                    self.process_pdf_for_day(files[d], brand, day_dir, today, day_label=d)
            else:
                logger.info("--- Procesando PDF único ---")
                self.process_pdf_for_day(files["Single"], brand, output_folder, today, day_label=None)

            logger.info("✅ PROCESO COMPLETADO EXITOSAMENTE")
            messagebox.showinfo("Éxito", "Proceso completado correctamente.")

        except Exception as e:
            logger.error(f"❌ Error crítico: {e}")
            messagebox.showerror("Error", f"Ocurrió un error: {e}")

        finally:
            self.process_btn.configure(state="normal", text="PROCESAR")

    # --- LÓGICA DE NEGOCIO (Adaptada del script original) ---

    def ensure_output_folder(self, brand):
        today = datetime.now().strftime("%d-%m-%Y")
        safe_brand = brand.replace(" ", "_")
        folder_name = f"{safe_brand} -Shein - {today}"
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        output_folder = os.path.join(desktop, folder_name)
        os.makedirs(output_folder, exist_ok=True)
        return output_folder, today

    def process_pdf_for_day(self, pdf_path, brand, output_folder, today, day_label=None):
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"No se pudo abrir el PDF ({day_label or 'Único'}): {e}")
            return

        total = doc.page_count
        logger.info(f"Documento original: {total} páginas")

        # --- A) IMPARES → PDF térmico ---
        odd_pdf = fitz.open()
        odd_indices = []
        for i in range(total):
            if (i + 1) % 2 == 1:
                odd_pdf.insert_pdf(doc, from_page=i, to_page=i)
                odd_indices.append(i + 1)

        exp_odds = (total + 1) // 2
        if len(odd_indices) != exp_odds:
            logger.warning(f"Mismatch impares: esperadas={exp_odds}, extraídas={len(odd_indices)}")
        
        day_chunk = f" - {day_label}" if day_label else ""
        odd_name = f"{brand} Guias shein {today}{day_chunk} - impresora termica.pdf"
        odd_path = os.path.join(output_folder, odd_name)
        odd_pdf.save(odd_path)
        odd_pdf.close()
        logger.info(f"PDF TÉRMICO guardado: {odd_name}")

        # --- B) PARES → DOCX (4 por hoja) + PDF láser ---
        even_indices = [i + 1 for i in range(total) if (i + 1) % 2 == 0]
        
        images = []
        skipped = []
        scale = 2  # factor de zoom
        
        # Procesamiento de imágenes (puede tardar, bueno reportar progreso si fuera más granular)
        for idx in even_indices:
            page = doc.load_page(idx - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if img.getbbox() is None:
                skipped.append(idx)
                continue
            images.append((idx, img))

        if skipped:
            logger.warning(f"Páginas en blanco omitidas: {skipped}")

        # Crear DOCX
        doc_word = Document()
        for section in doc_word.sections:
            section.page_width = Inches(8.5)
            section.page_height = Inches(11)
            section.left_margin = Cm(0.5)
            section.right_margin = Cm(0.5)
            section.top_margin = Cm(0.5)
            section.bottom_margin = Cm(0.5)

        desired_w = Cm(7.0)
        desired_h = Cm(12.0)
        count = 0
        table = None

        for idx, img in images:
            if count % 4 == 0:
                table = doc_word.add_table(rows=2, cols=2)
                table.autofit = False
                table.allow_autofit = False

            row = (count % 4) // 2
            col = (count % 4) % 2
            cell = table.cell(row, col)

            temp_png = os.path.join(output_folder, f"{(day_label or 'unico').lower()}_even_{idx}.png")
            img.save(temp_png, quality=100)
            
            p = cell.paragraphs[0]
            r = p.add_run()
            r.add_picture(temp_png, width=desired_w, height=desired_h)
            
            count += 1
            if count % 4 == 0:
                doc_word.add_page_break()
            
            # Limpiar temp inmediatamente para no llenar disco? O al final?
            # El script original no los borraba, los dejo por ahora o los borro?
            # Mejor borrarlos para limpiar garbage.
            try:
                os.remove(temp_png)
            except:
                pass

        docx_name = f"{brand} Guias shein {today}{day_chunk} - impresora laser.docx"
        docx_path = os.path.join(output_folder, docx_name)
        doc_word.save(docx_path)
        logger.info(f"DOCX guardado: {docx_name}")

        if convert:
            try:
                laser_name = f"{brand} Guias shein {today}{day_chunk} - impresora laser.pdf"
                laser_path = os.path.join(output_folder, laser_name)
                convert(docx_path, laser_path)
                logger.info(f"PDF LÁSER generado: {laser_name}")
            except Exception as e:
                logger.error(f"Error conversión PDF: {e}")
        else:
            logger.warning("docx2pdf no disponible; omitiendo PDF láser")

        doc.close()


if __name__ == "__main__":
    app = SheinSplitApp()
    app.mainloop()

