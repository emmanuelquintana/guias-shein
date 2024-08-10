import os
from PIL import Image, ImageFilter, ImageFile
from tkinter import Tk, filedialog

# Aumentar el límite de tamaño de la imagen
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def resize_image(input_path, output_path, target_width, target_height, dpi):
    # Abrir la imagen original
    image = Image.open(input_path)
    
    # Obtener dimensiones originales
    original_width, original_height = image.size
    
    # Calcular la relación de aspecto
    aspect_ratio = original_width / original_height
    
    # Calcular nuevas dimensiones manteniendo la relación de aspecto
    if aspect_ratio > (target_width / target_height):
        new_width = target_width
        new_height = int(target_width / aspect_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * aspect_ratio)
    
    # Redimensionar la imagen
    resized_image = image.resize((new_width, new_height), Image.LANCZOS)
    
    # Crear una nueva imagen con el tamaño objetivo y fondo blanco
    new_image = Image.new("RGB", (target_width, target_height), (255, 255, 255))
    
    # Pegar la imagen redimensionada en el centro
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_image.paste(resized_image, (paste_x, paste_y))
    
    # Guardar la nueva imagen con el DPI especificado
    new_image.save(output_path, dpi=(dpi, dpi))

def resize_super_resolution_images():
    # Crear una ventana Tkinter oculta
    root = Tk()
    root.withdraw()
    
    # Abrir un cuadro de diálogo para seleccionar la carpeta de superresolución
    folder_selected = filedialog.askdirectory(title="Seleccionar carpeta de imágenes de superresolución")
    
    if folder_selected:
        # Crear carpeta de salida
        output_folder = os.path.join(folder_selected, 'resized_images')
        os.makedirs(output_folder, exist_ok=True)
        
        # Dimensiones y DPI deseados
        target_width = 940
        target_height = 1215
        dpi = 72
        
        # Redimensionar imágenes de superresolución
        for subdir, _, files in os.walk(folder_selected):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg','.tiff')):
                    input_path = os.path.join(subdir, filename)
                    # Crear la misma estructura de carpetas en la carpeta de salida
                    relative_path = os.path.relpath(subdir, folder_selected)
                    output_subdir = os.path.join(output_folder, relative_path)
                    os.makedirs(output_subdir, exist_ok=True)
                    output_path = os.path.join(output_subdir, filename)
                    
                    # Redimensionar la imagen
                    resize_image(input_path, output_path, target_width, target_height, dpi)
                    print(f"Imagen redimensionada: {output_path}")

if __name__ == "__main__":
    resize_super_resolution_images()
