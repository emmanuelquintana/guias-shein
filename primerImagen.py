import os
from PIL import Image, ImageFilter
from tkinter import Tk, filedialog

def select_folder():
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    return folder_path

def process_images(input_folder, output_folder):
    for root, _, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(('png', 'jpg', 'jpeg')):
                process_image(input_folder, os.path.join(root, file), output_folder)

def process_image(input_folder, image_path, output_folder):
    with Image.open(image_path) as img:
        # Recortar la imagen desde la marca azul hacia arriba
        crop_area = (0, 0, img.width, int(0.85 * img.height))  # Ajusta este valor según la posición de la marca azul
        img_cropped = img.crop(crop_area)

        # Crear un lienzo en blanco
        canvas = Image.new('RGBA', (940, 1215), (255, 255, 255, 0))

        # Calcular la relación de aspecto y redimensionar la imagen
        img_cropped_ratio = img_cropped.width / img_cropped.height
        canvas_ratio = 940 / 1215

        if img_cropped_ratio > canvas_ratio:
            # La imagen es más ancha en proporción al lienzo
            new_height = 1215
            new_width = int(new_height * img_cropped_ratio)
        else:
            # La imagen es más alta en proporción al lienzo
            new_width = 940
            new_height = int(new_width / img_cropped_ratio)

        img_resized = img_cropped.resize((new_width, new_height), Image.LANCZOS)
        img_resized = img_resized.filter(ImageFilter.SHARPEN)  # Aplicar filtro de nitidez

        # Calcular la posición para centrar la imagen en el lienzo
        x_offset = (940 - new_width) // 2
        y_offset = (1215 - new_height) // 2

        # Pegar la imagen redimensionada en el lienzo
        canvas.paste(img_resized, (x_offset, y_offset), img_resized.convert('RGBA'))

        # Convertir el lienzo a RGB antes de guardarlo
        canvas = canvas.convert('RGB')

        # Guardar la nueva imagen con 72 DPI
        relative_path = os.path.relpath(image_path, input_folder)
        output_path = os.path.join(output_folder, relative_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        canvas.save(output_path, dpi=(72, 72))

if __name__ == "__main__":
    input_folder = select_folder()
    output_folder = os.path.join(input_folder, 'redimensionadas')
    os.makedirs(output_folder, exist_ok=True)
    process_images(input_folder, output_folder)
    print("Imágenes redimensionadas y guardadas en:", output_folder)
