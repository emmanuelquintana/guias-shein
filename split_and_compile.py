import os
import sys
import threading
import fitz  # PyMuPDF
from PIL import Image
from docx import Document
from docx.shared import Cm, Inches
from docx.enum.table import WD_ROW_HEIGHT_RULE
import customtkinter as ctk
import tkinter as tk  # For Canvas
from tkinter import filedialog, messagebox
from datetime import datetime
import logging
import platform
import subprocess
import queue

# Intentar importar docx2pdf
try:
    from docx2pdf import convert
except ImportError:
    convert = None

# -----------------------------------------------------------------------------
# LOGGING SETUP
# -----------------------------------------------------------------------------
class QueueHandler(logging.Handler):
    """Log handler sending messages to a queue."""
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))

# -----------------------------------------------------------------------------
# LOGIC
# -----------------------------------------------------------------------------
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
    """Genera un PDF con solo páginas impares."""
    try:
        src = fitz.open(pdf_in)
        dst = fitz.open()
        for i in range(src.page_count):
            if (i + 1) % 2 == 1:
                dst.insert_pdf(src, from_page=i, to_page=i)
        dst.save(pdf_out)
        dst.close()
        src.close()
        return True, f"✅ PDF (impares) generado: {os.path.basename(pdf_out)}"
    except Exception as e:
        return False, f"Error al filtrar impares: {e}"

def run_processing(pdf_path, brand, logger):
    """
    Función principal de procesamiento que corre en un hilo separado.
    """
    logger.info("▶ Iniciando procesamiento...")
    logger.info(f"📂 Archivo: {os.path.basename(pdf_path)}")
    logger.info(f"🔖 Modo: {brand}")

    # 1. Preparar carpetas
    today = datetime.now().strftime("%d-%m-%Y")
    timestamp = datetime.now().strftime("%H%M%S")
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    base_folder = os.path.join(desktop, f"Marcas -Shein - {today}")
    run_folder = os.path.join(base_folder, f"{brand} - {timestamp}")
    os.makedirs(run_folder, exist_ok=True)
    
    logger.info(f"📂 Carpeta destino: {run_folder}")

    # 2. Abrir PDF
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"❌ Error abriendo PDF: {e}")
        return False, None

    total = doc.page_count
    logger.info(f"📄 Total páginas: {total}")

    # --- A) IMPARES -> PDF TÉRMICO ---
    odd_pdf = fitz.open()
    odd_indices = []
    for i in range(total):
        if (i + 1) % 2 == 1:
            odd_pdf.insert_pdf(doc, from_page=i, to_page=i)
            odd_indices.append(i + 1)
    
    odd_name = f"{brand} Guias shein {today} - impresora termica.pdf"
    odd_path = os.path.join(run_folder, odd_name)
    try:
        odd_pdf.save(odd_path)
        logger.info(f"✅ térmico guardado.")
    except Exception as e:
        logger.error(f"❌ Error guardando térmico: {e}")
    finally:
        odd_pdf.close()

    # --- B) PARES -> DOCX ---
    even_indices = [i + 1 for i in range(total) if (i + 1) % 2 == 0]
    images = []
    scale = 2  # Zoom
    
    # Procesar imágenes
    for idx in even_indices:
        try:
            page = doc.load_page(idx - 1)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            if img.getbbox():
                images.append((idx, img))
        except Exception as e:
            logger.warning(f"⚠️ Error leyendo página {idx}: {e}")

    # Docx setup
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
        out_suffix = "tiktok"
    else:
        per_page = 4
        rows, cols = 2, 2
        picture_width = Cm(7.0)
        out_suffix = "impresora laser"

    count = 0
    table = None
    
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

        temp_png = os.path.join(run_folder, f"even_{idx}.png")
        img.save(temp_png, quality=100)
        
        try:
            run = cell.paragraphs[0].add_run()
            run.add_picture(temp_png, width=picture_width)
            count += 1
            if count % per_page == 0:
                doc_word.add_page_break()
        except Exception as e:
            logger.error(f"❌ Error insertando img {idx} en Word: {e}")

    docx_name = f"{brand} Guias shein {today} - {out_suffix}.docx"
    docx_path = os.path.join(run_folder, docx_name)
    try:
        doc_word.save(docx_path)
        logger.info(f"✅ DOCX guardado.")
    except Exception as e:
        logger.error(f"❌ Error guardando DOCX: {e}")
        return False, run_folder

    # --- C) DOCX -> PDF ---
    produced_pdf_path = None
    if convert:
        pdf_name = f"{brand} Guias shein {today} - {out_suffix}.pdf"
        produced_pdf_path = os.path.join(run_folder, pdf_name)
        try:
            logger.info("⏳ Convirtiendo DOCX a PDF (esto tarda un poco)...")
            convert(docx_path, produced_pdf_path)
            logger.info("✅ PDF generado.")
        except Exception as e:
            logger.error(f"⚠️ Falló conversión DOCX->PDF: {e}")
    else:
        logger.warning("⚠️ docx2pdf no instalado. Omitiendo conversión.")

    # --- D) TikTok Extra: Impares Laser ---
    if brand == "TikTok" and produced_pdf_path:
        laser_odds_pdf = os.path.join(run_folder, f"{brand} Guias shein {today} - impresora laser (solo impares).pdf")
        ok, msg = remove_even_pages(produced_pdf_path, laser_odds_pdf)
        logger.info(msg)

    doc.close()
    logger.info("✨ PROCESO COMPLETADO ✨")
    return True, run_folder

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # THEME SETUP
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("dark-blue")
        
        # WINDOW CONFIG
        self.title("AutoGuias Pro - Liquid Edition")
        self.geometry("600x680")
        
        # STATE
        self.pdf_path = None
        self.log_queue = queue.Queue()
        self.processing = False

        # --- BACKGROUND (Liquid Simulation) ---
        # We use a standard tkinter Canvas for the background capabilities
        self.bg_canvas = tk.Canvas(self, highlightthickness=0)
        self.bg_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Draw "Liquid" Blobs
        self.draw_liquid_background()
        
        # Bind resize to redraw background (optional, but good for consistency)
        self.bind("<Configure>", self.on_resize)

        # --- GLASS PANE (Main Container) ---
        # "Glass" effect: A frame that is centered but allows the background to peek? 
        # CTkFrame with 'transparent' lets us see the canvas.
        # To make it readable, we can't easily do semi-transparent backgrounds in CTk without hacks.
        # So we will draw a "semi-transparent" rectangle on the canvas ITSELF to act as the glass pane.
        
        self.glass_pane_id = self.bg_canvas.create_rectangle(
            50, 50, 550, 630, 
            fill="#1c1c1e", # Apple Dark Grey
            outline="#4a4a4a",
            width=2
        )
        # Note: stipple="gray50" works for transparency but looks grainy. 
        # Better to just use a nice solid dark grey that contrasts with the colorful neon edges.
        # OR: We use a Frame with specific color.
        
        # Let's use a transparent CTkFrame on top of that canvas rectangle for layout
        self.main_container = ctk.CTkFrame(self, fg_color="#1c1c1e", corner_radius=20, border_width=1, border_color="#505050")
        # To get the "Liquid" feel, maybe we make the container sligthly specialized. 
        # But user wants "Liquid Glass".
        # Let's try to simulate transparency by capturing the background? No, too complex.
        # We will stick to the "Frosted Glass" look -> Dark Surface, Colorful Glow behind.
        
        self.main_container.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.85, relheight=0.85)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(6, weight=1) # Log box expands

        # --- HEADER ---
        self.lbl_title = ctk.CTkLabel(
            self.main_container, 
            text="Procesador de Guías", 
            font=("Roboto Medium", 26),
            text_color="white"
        )
        self.lbl_title.grid(row=0, column=0, pady=(30, 20))

        # --- CONTROLS ---
        # 1. Brand Selector
        self.lbl_brand = ctk.CTkLabel(self.main_container, text="MODO DE OPERACIÓN", font=("Roboto", 11, "bold"), text_color="gray60")
        self.lbl_brand.grid(row=1, column=0, sticky="w", padx=30, pady=(0, 5))

        self.seg_brand = ctk.CTkSegmentedButton(
            self.main_container, 
            values=["Marcas y Licencias", "Pure and Simple", "TikTok"],
            height=32,
            selected_color="#007AFF", # Apple Blue
            selected_hover_color="#0062CC",
            unselected_color="#2c2c2e",
            unselected_hover_color="#3a3a3c",
            text_color="white"
        )
        self.seg_brand.grid(row=2, column=0, sticky="ew", padx=30, pady=(0, 25))
        self.seg_brand.set("Marcas y Licencias")

        # 2. File Selector
        self.lbl_file = ctk.CTkLabel(self.main_container, text="ARCHIVO PDF", font=("Roboto", 11, "bold"), text_color="gray60")
        self.lbl_file.grid(row=3, column=0, sticky="w", padx=30, pady=(0, 5))

        self.file_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.file_frame.grid(row=4, column=0, sticky="ew", padx=30, pady=(0, 25))
        self.file_frame.columnconfigure(0, weight=1)

        self.entry_file = ctk.CTkEntry(
            self.file_frame, 
            placeholder_text="Seleccionar PDF...", 
            height=35,
            corner_radius=8,
            fg_color="#2c2c2e",
            border_color="#3a3a3c",
            text_color="white",
            state="readonly"
        )
        self.entry_file.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.btn_browse = ctk.CTkButton(
            self.file_frame, 
            text="Explorar", 
            width=80, 
            height=35, 
            command=self.browse_file,
            fg_color="#3a3a3c", 
            hover_color="#48484a",
            corner_radius=8
        )
        self.btn_browse.grid(row=0, column=1)

        # 3. Action Button
        self.btn_process = ctk.CTkButton(
            self.main_container, 
            text="Procesar Guías", 
            height=45, 
            corner_radius=22, 
            font=("Roboto Medium", 15),
            fg_color="#007AFF", # Apple Blue
            hover_color="#0056b3",
            command=self.start_thread
        )
        self.btn_process.grid(row=5, column=0, sticky="ew", padx=60, pady=(10, 20))

        # --- LOG CONSOLE ---
        self.log_box = ctk.CTkTextbox(
            self.main_container, 
            corner_radius=10, 
            fg_color="#000000",
            text_color="#00ff00",
            font=("Consolas", 11),
            state="disabled",
            border_width=1,
            border_color="#333333"
        )
        self.log_box.grid(row=6, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        # 4. Open Folder Button (Hidden initially)
        self.btn_open_folder = ctk.CTkButton(
            self.main_container,
            text="Abrir Carpeta",
            command=self.open_result_folder,
            fg_color="transparent",
            text_color="#007AFF",
            hover_color="#2c2c2e",
            state="disabled"
        )
        self.btn_open_folder.grid(row=7, column=0, pady=(0, 15))

        self.result_folder = None
        
        # Start logger poller
        self.after(100, self.poll_log_queue)

    def draw_liquid_background(self):
        """Draws a colorful background on the canvas."""
        self.bg_canvas.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Base: Deep Black/Blue
        self.bg_canvas.create_rectangle(0, 0, w, h, fill="#000000", outline="")

        # Blobs (Simulated Gradient)
        # 1. Purple/Magenta Orb Top-Left
        self.bg_canvas.create_oval(-100, -100, w//1.5, h//2, fill="#4a0072", outline="", tags="blob") # Deep Purple
        
        # 2. Cyan/Blue Orb Bottom-Right
        self.bg_canvas.create_oval(w//2.5, h//2, w+150, h+150, fill="#00477e", outline="", tags="blob") # Deep Blue
        
        # 3. Accent (Pinkish)
        self.bg_canvas.create_oval(w//1.2, -50, w+100, 200, fill="#6a0040", outline="", tags="blob")
        
        # Note: We can't really "blur" these easily in Tkinter Canvas without creating many concentric ovals 
        # or using an image. This "Hard" blob look is "Retro Liquid".
        pass

    def on_resize(self, event):
        # Allow some throttle?
        if event.widget == self:
            self.draw_liquid_background()
            self.glass_pane_id = self.bg_canvas.create_rectangle(
                # We don't really use this rect anymore since we have the CTkFrame on top,
                # but we could use it for a border glow.
                0,0,0,0
            )

    def browse_file(self):
        fname = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if fname:
            self.pdf_path = fname
            self.entry_file.configure(state="normal")
            self.entry_file.delete(0, "end")
            self.entry_file.insert(0, os.path.basename(fname))
            self.entry_file.configure(state="readonly")

    def log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", msg + "\n")
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

    def start_thread(self):
        if self.processing:
            return
        if not self.pdf_path:
            messagebox.showwarning("Falta archivo", "Por favor selecciona un PDF primero.")
            return
        
        brand = self.seg_brand.get()
        self.processing = True
        self.btn_process.configure(state="disabled", text="Procesando...")
        self.btn_open_folder.configure(state="disabled")
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        # Setup Thread Logger
        logger = logging.getLogger("ThreadLogger")
        logger.setLevel(logging.INFO)
        if logger.handlers:
            logger.handlers = []
        queue_h = QueueHandler(self.log_queue)
        queue_h.setFormatter(logging.Formatter('%(message)s'))
        logger.addHandler(queue_h)

        t = threading.Thread(target=self.run_process_wrapper, args=(brand, logger))
        t.daemon = True
        t.start()

    def run_process_wrapper(self, brand, logger):
        success, folder = run_processing(self.pdf_path, brand, logger)
        self.processing = False
        self.result_folder = folder
        self.after(0, lambda: self.finish_ui_update(success))

    def finish_ui_update(self, success):
        self.btn_process.configure(state="normal", text="Procesar Guías")
        if success and self.result_folder:
            self.btn_open_folder.configure(state="normal")
            messagebox.showinfo("Éxito", "Proceso terminado exitosamente.")
        else:
            messagebox.showerror("Error", "Ocurrió un error. Revisa el log.")

    def open_result_folder(self):
        if self.result_folder:
            open_folder(self.result_folder)

if __name__ == "__main__":
    app = App()
    app.mainloop()
