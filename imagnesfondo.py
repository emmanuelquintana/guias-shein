from PIL import Image, ImageOps
import os
import tkinter as tk
from tkinter import filedialog
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def remove_background(image):
    image = image.convert("RGBA")
    datas = image.getdata()
    new_data = []
    for item in datas:
        if item[0] > 200 and item[1] > 200 and item[2] > 200:  # Ajuste para colores claros (fondo blanco)
            new_data.append((255, 255, 255, 0))  # Transparente
        else:
            new_data.append(item)
    image.putdata(new_data)
    return image

def process_image(image_path, background_path, output_path):
    try:
        logging.info(f"Procesando imagen: {image_path}")
        
        # Abrir la imagen principal y eliminar el fondo
        img = Image.open(image_path)
        img_no_bg = remove_background(img)
        
        # Abrir la imagen de fondo
        background = Image.open(background_path).convert("RGBA")
        
        # Redimensionar la imagen sin fondo si es necesario para ajustarse a la imagen de fondo
        img_no_bg = ImageOps.fit(img_no_bg, background.size, method=Image.LANCZOS, centering=(0.5, 0.5))
        
        # Crear la imagen final componiendo el fondo con la imagen sin su fondo anterior
        composite = Image.alpha_composite(background, img_no_bg)
        
        # Guardar la imagen resultante en formato webp
        composite.save(output_path, 'webp')
        logging.info(f"Imagen guardada: {output_path}")
    
    except Exception as e:
        logging.error(f"Error al procesar la imagen {image_path}: {e}")

def process_images(input_folder, background_path):
    output_folder = os.path.join(input_folder, "output")
    os.makedirs(output_folder, exist_ok=True)

    for root, dirs, files in os.walk(input_folder):
        for filename in files:
            if filename.endswith((".png", ".jpg", ".jpeg", ".webp")):
                image_path = os.path.join(root, filename)
                
                # Crear la estructura de carpetas de salida
                relative_path = os.path.relpath(root, input_folder)
                output_dir = os.path.join(output_folder, relative_path)
                os.makedirs(output_dir, exist_ok=True)

                output_path = os.path.join(output_dir, os.path.splitext(filename)[0] + '.webp')
                process_image(image_path, background_path, output_path)

    logging.info("Procesamiento completo.")

def select_folder():
    root = tk.Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory()
    return folder_selected

def select_file():
    root = tk.Tk()
    root.withdraw()
    file_selected = filedialog.askopenfilename()
    return file_selected

def main():
    input_folder = select_folder()
    background_path = select_file()

    if input_folder and background_path:
        process_images(input_folder, background_path)
    else:
        logging.warning("No se seleccionaron todas las carpetas o archivos necesarios.")

if __name__ == "__main__":
    main()
