import os
from PIL import Image, ImageFilter, ImageFile
from tkinter import Tk, filedialog

# Aumentar el límite de tamaño de la imagen
Image.MAX_IMAGE_PIXELS = None
ImageFile.LOAD_TRUNCATED_IMAGES = True

def process_image(input_path, output_path, target_width, target_height, dpi):
    with Image.open(input_path) as img:
        # Recortar menos de la imagen para incluir más parte inferior
        crop_area = (0, 0, img.width, int(0.80 * img.height))  # Ajusta este valor según la posición de la marca roja
        img_cropped = img.crop(crop_area)

        # Crear un lienzo en blanco
        canvas = Image.new('RGBA', (target_width, target_height), (255, 255, 255, 0))

        # Calcular la relación de aspecto y redimensionar la imagen
        img_cropped_ratio = img_cropped.width / img_cropped.height
        canvas_ratio = target_width / target_height

        if img_cropped_ratio > canvas_ratio:
            # La imagen es más ancha en proporción al lienzo
            new_height = target_height
            new_width = int(new_height * img_cropped_ratio)
        else:
            # La imagen es más alta en proporción al lienzo
            new_width = target_width
            new_height = int(new_width / img_cropped_ratio)

        img_resized = img_cropped.resize((new_width, new_height), Image.LANCZOS)

        # Calcular la posición para centrar la imagen en el lienzo
        x_offset = (target_width - new_width) // 2
        y_offset = (target_height - new_height) // 2

        # Pegar la imagen redimensionada en el lienzo
        canvas.paste(img_resized, (x_offset, y_offset), img_resized.convert('RGBA'))

        # Convertir el lienzo a RGB antes de guardarlo
        canvas = canvas.convert('RGB')

        # Guardar la nueva imagen con 72 DPI
        canvas.save(output_path, dpi=(dpi, dpi))

def process_resized_images():
    # Crear una ventana Tkinter oculta
    root = Tk()
    root.withdraw()
    
    # Abrir un cuadro de diálogo para seleccionar la carpeta de imágenes redimensionadas
    folder_selected = filedialog.askdirectory(title="Seleccionar carpeta de imágenes redimensionadas")
    
    if folder_selected:
        # Crear carpeta de salida
        output_folder = os.path.join(folder_selected, 'processed_images')
        os.makedirs(output_folder, exist_ok=True)
        
        # Dimensiones y DPI deseados
        target_width = 940
        target_height = 1215
        dpi = 72
        
        # Procesar imágenes redimensionadas
        for subdir, _, files in os.walk(folder_selected):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg','.tiff')):
                    input_path = os.path.join(subdir, filename)
                    # Crear la misma estructura de carpetas en la carpeta de salida
                    relative_path = os.path.relpath(subdir, folder_selected)
                    output_subdir = os.path.join(output_folder, relative_path)
                    os.makedirs(output_subdir, exist_ok=True)
                    output_path = os.path.join(output_subdir, filename)

                    # Procesar la imagen
                    process_image(input_path, output_path, target_width, target_height, dpi)
                    print(f"Imagen procesada: {output_path}")

if __name__ == "__main__":
    process_resized_images()
