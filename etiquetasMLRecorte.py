import os
from tkinter import Tk, filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image

# Función para seleccionar el archivo PDF
def select_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    return file_path

# Función para seleccionar una carpeta
def select_folder():
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    return folder_path

# Función para recortar las etiquetas y guardarlas como imágenes individuales
def crop_and_save_labels(pdf_path, output_folder):
    doc = fitz.open(pdf_path)
    label_count = 0
    label_width = 588
    label_height = 291

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Define las coordenadas para recortar las etiquetas (ajusta según sea necesario)
        rects = [
            fitz.Rect(50, 100, 50 + label_width, 100 + label_height),  # Primera etiqueta
            fitz.Rect(50 + label_width, 100, 50 + 2 * label_width, 100 + label_height),  # Segunda etiqueta
            # Agrega más rectángulos según la cantidad de etiquetas en cada página
        ]
        
        for rect in rects:
            clip = page.get_pixmap(clip=rect, dpi=300)  # Ajustar DPI para mantener la calidad
            output_path = os.path.join(output_folder, f"label_{label_count}.png")
            clip.save(output_path)
            label_count += 1
    
    messagebox.showinfo("Éxito", f"Se guardaron {label_count} etiquetas en {output_folder}.")

def main():
    product_pdf_path = select_file()
    if not product_pdf_path:
        messagebox.showerror("Error", "No se seleccionó ningún archivo.")
        return
    
    output_folder = select_folder()
    if not output_folder:
        messagebox.showerror("Error", "No se seleccionó ninguna carpeta.")
        return
    
    crop_and_save_labels(product_pdf_path, output_folder)

if __name__ == "__main__":
    main()
