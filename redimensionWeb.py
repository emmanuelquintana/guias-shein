import os
from tkinter import Tk, filedialog
from PIL import Image

def resize_and_pad_image(input_path, output_path, size=(2000, 2000)):
    with Image.open(input_path) as img:
        img.thumbnail(size, Image.LANCZOS)
        background = Image.new('RGB', size, (255, 255, 255))
        img_position = (
            (size[0] - img.size[0]) // 2,
            (size[1] - img.size[1]) // 2
        )
        background.paste(img, img_position)
        # Cambiar la extensión a .webp
        output_path = os.path.splitext(output_path)[0] + '.webp'
        background.save(output_path, "WEBP")
        print(f"Imagen redimensionada y guardada en: {output_path}")

def process_folder(input_folder, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    for root, _, files in os.walk(input_folder):
        if root.startswith(output_folder):
            continue
        
        for file in files:
            if file.lower().endswith('.tiff'):
                input_path = os.path.join(root, file)
                relative_path = os.path.relpath(root, input_folder)
                output_dir = os.path.join(output_folder, relative_path)
                
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                output_path = os.path.join(output_dir, file)
                resize_and_pad_image(input_path, output_path)
                print(f"Procesado: {input_path}")

def select_folder():
    root = Tk()
    root.withdraw()  # Hide the root window
    input_folder = filedialog.askdirectory(title="Select Input Folder")
    root.destroy()
    return input_folder

input_folder = select_folder()
if input_folder:
    output_folder = os.path.join(input_folder, "output")
    print(f"Carpeta de entrada seleccionada: {input_folder}")
    print(f"Creando carpeta de salida en: {output_folder}")
    process_folder(input_folder, output_folder)
    print(f"Proceso completado. Las imágenes redimensionadas se guardan en {output_folder}")
else:
    print("No se seleccionó ninguna carpeta.")
