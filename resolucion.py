import os
from tkinter import Tk, filedialog
from PIL import Image, ImageFile
import cv2
import numpy as np

# Aumentar el límite de tamaño de la imagen
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def super_resolve_image(image_path):
    # Cargar la imagen usando OpenCV
    image = cv2.imread(image_path)
    
    # Aumentar la resolución de la imagen usando un simple escalado bicúbico
    scale_factor = 4  # Factor de escalado para super resolución
    super_resolved_image = cv2.resize(image, (image.shape[1] * scale_factor, image.shape[0] * scale_factor), interpolation=cv2.INTER_CUBIC)
    
    # Convertir de nuevo a formato PIL
    super_resolved_image_pil = Image.fromarray(cv2.cvtColor(super_resolved_image, cv2.COLOR_BGR2RGB))
    return super_resolved_image_pil

def generate_super_resolution_images():
    # Crear una ventana Tkinter oculta
    root = Tk()
    root.withdraw()
    
    # Abrir un cuadro de diálogo para seleccionar la carpeta de origen
    folder_selected = filedialog.askdirectory(title="Seleccionar carpeta de origen")
    
    if folder_selected:
        # Crear carpeta de salida
        output_folder = os.path.join(folder_selected, 'super_resolution_images')
        os.makedirs(output_folder, exist_ok=True)
        
        # Generar imágenes de superresolución
        for subdir, _, files in os.walk(folder_selected):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    input_path = os.path.join(subdir, filename)
                    # Crear la misma estructura de carpetas en la carpeta de salida
                    relative_path = os.path.relpath(subdir, folder_selected)
                    output_subdir = os.path.join(output_folder, relative_path)
                    os.makedirs(output_subdir, exist_ok=True)
                    output_path = os.path.join(output_subdir, filename)
                    
                    # Crear imagen de superresolución
                    super_resolved_image = super_resolve_image(input_path)
                    tiff_path = output_path.replace('.jpg', '.tiff').replace('.jpeg', '.tiff').replace('.png', '.tiff')
                    super_resolved_image.save(tiff_path, format='TIFF')
                    print(f"Imagen de superresolución creada: {tiff_path}")

if __name__ == "__main__":
    generate_super_resolution_images()
