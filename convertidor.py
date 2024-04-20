import fitz
from PIL import Image
import tkinter as tk
from tkinter import filedialog
import os
from datetime import datetime

def pdf_to_jpg(pdf_path, output_folder, min_width, min_height):
    # Abre el archivo PDF
    pdf_document = fitz.open(pdf_path)
    
    # Itera sobre cada página del PDF
    for page_number in range(len(pdf_document)):
        # Obtiene la página
        page = pdf_document.load_page(page_number)
        
        # Convierte la página en imagen
        pix = page.get_pixmap()
        
        # Ajusta el tamaño de la imagen si es menor que el mínimo especificado
        if pix.width < min_width or pix.height < min_height:
            scale_factor = max(min_width / pix.width, min_height / pix.height)
            pix = page.get_pixmap(matrix=fitz.Matrix(scale_factor, scale_factor))
        
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Guarda la imagen como JPEG numerado
        output_path = f"{output_folder}/{page_number + 1:04d}.jpg"  # Formato con ceros iniciales
        img.save(output_path, quality=100)  # Ajusta la calidad al 100%
        print(f"Guardado {output_path}")
    
    # Cierra el archivo PDF
    pdf_document.close()

def select_pdf_and_convert():
    # Abre una ventana de diálogo para seleccionar el archivo PDF
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal
    
    file_path = filedialog.askopenfilename(title="Seleccionar archivo PDF", filetypes=[("PDF files", "*.pdf")])
    
    if file_path:
        # Crea el nombre de la carpeta de salida
        output_folder_name = f"GUIAS SHEIN {datetime.now().strftime('%Y-%m-%d')} -IMAGENES"
        
        # Obtiene la ruta completa de la carpeta de salida
        output_folder_path = os.path.join(os.getcwd(), output_folder_name)
        
        # Crea la carpeta de salida si no existe
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)
        
        # Tamaño mínimo requerido para las imágenes
        min_width = 896
        min_height = 1538
        
        # Convierte el PDF a imágenes JPEG numeradas
        pdf_to_jpg(file_path, output_folder_path, min_width, min_height)

if __name__ == "__main__":
    select_pdf_and_convert()
