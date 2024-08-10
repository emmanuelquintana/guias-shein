import os
from PIL import Image, ImageFilter
from tkinter import Tk, filedialog
import cv2
import numpy as np

def super_resolve_image(image_path):
    # Cargar la imagen usando OpenCV
    image = cv2.imread(image_path)
    
    # Aumentar la resolución de la imagen usando un simple escalado bicúbico
    scale_factor = 4  # Factor de escalado para super resolución
    super_resolved_image = cv2.resize(image, (image.shape[1] * scale_factor, image.shape[0] * scale_factor), interpolation=cv2.INTER_CUBIC)
    
    # Convertir de nuevo a formato PIL
    super_resolved_image_pil = Image.fromarray(cv2.cvtColor(super_resolved_image, cv2.COLOR_BGR2RGB))
    return super_resolved_image_pil

def resize_image(input_image, output_path, target_width, target_height, dpi):
    # Obtener dimensiones originales
    original_width, original_height = input_image.size
    
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
    resized_image = input_image.resize((new_width, new_height), Image.LANCZOS)
    
    # Crear una nueva imagen con el tamaño objetivo y fondo blanco
    new_image = Image.new("RGB", (target_width, target_height), (255, 255, 255))
    
    # Pegar la imagen redimensionada en el centro
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_image.paste(resized_image, (paste_x, paste_y))
    
    # Guardar la nueva imagen con el DPI especificado
    new_image.save(output_path, dpi=(dpi, dpi))

def process_image(input_image, output_path, target_width, target_height, dpi):
    # Recortar menos de la imagen para incluir más parte inferior
    crop_area = (0, 0, input_image.width, int(0.75 * input_image.height))  # Ajusta este valor según la posición de la marca roja
    img_cropped = input_image.crop(crop_area)

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

def select_folder_and_process_images():
    # Crear una ventana Tkinter oculta
    root = Tk()
    root.withdraw()
    
    # Abrir un cuadro de diálogo para seleccionar la carpeta de origen
    folder_selected = filedialog.askdirectory(title="Seleccionar carpeta de origen")
    
    if folder_selected:
        # Crear carpetas de salida
        output_folder = os.path.join(folder_selected, 'output_images')
        processed_folder = os.path.join(folder_selected, 'processed_images')
        os.makedirs(output_folder, exist_ok=True)
        os.makedirs(processed_folder, exist_ok=True)
        
        # Dimensiones y DPI deseados
        target_width = 940
        target_height = 1215
        dpi = 72
        
        # Primero, crear imágenes de ultra alta resolución
        for subdir, _, files in os.walk(folder_selected):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    input_path = os.path.join(subdir, filename)
                    # Crear la misma estructura de carpetas en la carpeta de salida
                    relative_path = os.path.relpath(subdir, folder_selected)
                    output_subdir = os.path.join(output_folder, relative_path)
                    os.makedirs(output_subdir, exist_ok=True)
                    output_path = os.path.join(output_subdir, filename)
                    
                    # Crear imagen de ultra alta resolución
                    super_resolved_image = super_resolve_image(input_path)
                    super_resolved_path = output_path.replace('.jpg', '_super_resolved.jpg')
                    super_resolved_image.save(super_resolved_path)
                    print(f"Imagen de ultra alta resolución creada: {super_resolved_path}")
                    
                    # Redimensionar la imagen de alta resolución
                    resize_image(super_resolved_image, output_path, target_width, target_height, dpi)
                    print(f"Imagen redimensionada y mejorada: {output_path}")
        
        # Luego, procesar las imágenes originales (Segundo Script)
        for subdir, _, files in os.walk(folder_selected):
            for filename in files:
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    input_path = os.path.join(subdir, filename)
                    # Crear la misma estructura de carpetas en la carpeta de salida del segundo script
                    relative_path = os.path.relpath(subdir, folder_selected)
                    processed_subdir = os.path.join(processed_folder, relative_path)
                    os.makedirs(processed_subdir, exist_ok=True)
                    processed_path = os.path.join(processed_subdir, filename)

                    # Procesar con recorte y pegar en lienzo blanco
                    process_image(super_resolved_image, processed_path, target_width, target_height, dpi)
                    print(f"Imagen procesada: {processed_path}")

if __name__ == "__main__":
    select_folder_and_process_images()
