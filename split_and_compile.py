import os
import fitz  # PyMuPDF
from PIL import Image
from docx import Document
from docx.shared import Cm, Inches
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import logging

# Intentar importar docx2pdf para conversión Word->PDF
try:
    from docx2pdf import convert
except ImportError:
    convert = None
    logging.warning("docx2pdf no está instalado. La conversión a PDF se omitirá.")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def ask_brand():
    sel = {}
    sel_root = tk.Toplevel()
    sel_root.title("Seleccione Marca")
    sel_root.geometry("300x140")
    sel_var = tk.StringVar(value="Marcas y Licencias")

    tk.Label(sel_root, text="Seleccione MARCA:").pack(pady=(10,5))
    tk.Radiobutton(sel_root, text="Marcas y Licencias", variable=sel_var, value="Marcas y Licencias")\
        .pack(anchor='w', padx=20)
    tk.Radiobutton(sel_root, text="Pure and Simple",    variable=sel_var, value="Pure and Simple")\
        .pack(anchor='w', padx=20)

    def on_submit():
        sel['brand'] = sel_var.get()
        sel_root.destroy()

    tk.Button(sel_root, text="OK", command=on_submit).pack(pady=(10,10))

    sel_root.update_idletasks()
    sel_root.attributes('-topmost', True)
    sel_root.focus_force()
    sel_root.grab_set()
    sel_root.wait_window()

    return sel.get('brand', '')

def split_and_compile(root):
    logger.info("▶ Iniciando split_and_compile()")

    # 1) Elige MARCA
    brand = ask_brand()
    if not brand:
        logger.error("No se seleccionó ninguna marca. Abortando.")
        root.quit()
        return
    logger.info(f"Marca seleccionada: {brand}")

    # 2) Selecciona PDF
    pdf_path = filedialog.askopenfilename(
        title="Seleccionar archivo PDF",
        filetypes=[("PDF files", "*.pdf")]
    )
    if not pdf_path:
        logger.error("No se seleccionó ningún archivo PDF. Abortando.")
        root.quit()
        return

    # 3) Prepara carpeta de salida
    today = datetime.now().strftime("%d-%m-%Y")
    folder_name = f"Marcas -Shein - {today}"
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    output_folder = os.path.join(desktop, folder_name)
    os.makedirs(output_folder, exist_ok=True)
    logger.info(f"Carpeta de salida: {output_folder}")

    # 4) Abre PDF original
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        logger.error(f"❌ No se pudo abrir el PDF: {e}")
        root.quit()
        return

    total = doc.page_count
    logger.info(f"Documento original: {total} páginas")

    # --- A) IMPARES → PDF térmico ---
    odd_pdf = fitz.open()
    odd_indices = []
    for i in range(total):
        if (i+1) % 2 == 1:
            odd_pdf.insert_pdf(doc, from_page=i, to_page=i)
            odd_indices.append(i+1)

    exp_odds = (total + 1)//2
    if len(odd_indices) != exp_odds:
        logger.warning(f"Mismatch impares: esperadas={exp_odds}, extraídas={len(odd_indices)} ({odd_indices})")
    else:
        logger.info(f"Páginas impares extraídas: {odd_indices}")

    odd_name = f"{brand} Guias shein {today} - impresora termica.pdf"
    odd_path = os.path.join(output_folder, odd_name)
    odd_pdf.save(odd_path)
    logger.info(f"✅ PDF TÉRMICO guardado en: {odd_path}")

    # --- B) PARES → DOCX (4 por hoja) + PDF láser ---
    even_indices = [i+1 for i in range(total) if (i+1)%2==0]
    logger.info(f"Índices pares que deberían procesarse: {even_indices}")

    images = []
    skipped = []
    scale = 2  # factor de zoom para mayor resolución
    for idx in even_indices:
        page = doc.load_page(idx-1)
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        if img.getbbox() is None:
            skipped.append(idx)
            continue
        images.append((idx, img))

    if skipped:
        logger.warning(f"Páginas pares en blanco omitidas: {skipped}")
    if len(images) != len(even_indices) - len(skipped):
        logger.warning(
            f"Después de filtrar blancas: esperadas={len(even_indices)}, "
            f"procesadas={len(images)}"
        )
    else:
        logger.info(f"Imágenes pares procesadas correctamente: {[i for i,_ in images]}")

    # Crear DOCX tamaño Carta
    doc_word = Document()
    for section in doc_word.sections:
        section.page_width = Inches(8.5)
        section.page_height = Inches(11)
        section.left_margin = Cm(0.5)
        section.right_margin = Cm(0.5)
        section.top_margin = Cm(0.5)
        section.bottom_margin = Cm(0.5)

    # Incrustar imágenes 4 por hoja (ligeramente más pequeñas)
    desired_w = Cm(7.0)
    desired_h = Cm(12.0)
    count = 0
    for idx, img in images:
        if count % 4 == 0:
            table = doc_word.add_table(rows=2, cols=2)
            table.autofit = False
            table.allow_autofit = False

        row = (count % 4) // 2
        col = (count % 4) % 2
        cell = table.cell(row, col)
        temp_png = os.path.join(output_folder, f"even_{idx}.png")
        img.save(temp_png, quality=100)
        cell.paragraphs[0].add_run().add_picture(
            temp_png,
            width=desired_w,
            height=desired_h
        )
        logger.info(f"Insertada página par {idx} en tabla posición ({row},{col})")
        count += 1

        if count % 4 == 0:
            doc_word.add_page_break()

    # Guardar DOCX
    docx_name = f"{brand} Guias shein {today} - impresora laser.docx"
    docx_path = os.path.join(output_folder, docx_name)
    doc_word.save(docx_path)
    logger.info(f"✅ DOCX guardado en: {docx_path}")
    
    # 5) Convertir DOCX → PDF láser
    if convert:
        laser_name = f"{brand} Guias shein {today} - impresora laser.pdf"
        laser_path = os.path.join(output_folder, laser_name)
        convert(docx_path, laser_path)
        logger.info(f"✅ PDF LÁSER guardado en: {laser_path}")
    else:
        logger.error("docx2pdf no disponible; se omitió conversión a PDF láser.")

    logger.info("▶ Proceso completado exitosamente.")
    root.quit()

def main():
    root = tk.Tk()
    root.iconify()  # mantiene vivo el loop sin mostrar la ventana principal
    root.after(0, split_and_compile, root)
    root.mainloop()

if __name__ == "__main__":
    main()
