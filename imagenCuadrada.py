import os
from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

def hacer_cuadradas_y_guardar_con_estructura(input_folder):
    output_base = os.path.join(input_folder, 'output')
    procesadas = 0

    for root, dirs, files in os.walk(input_folder):
        # Saltar la carpeta de salida
        if output_base in root:
            continue

        # Ruta relativa para reproducir la estructura
        relative_path = os.path.relpath(root, input_folder)
        output_folder = os.path.join(output_base, relative_path)
        os.makedirs(output_folder, exist_ok=True)

        for filename in files:
            if not filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                continue

            input_path = os.path.join(root, filename)
            output_path = os.path.join(output_folder, filename)

            try:
                with Image.open(input_path) as im:
                    width, height = im.size
                    if width == height:
                        im.save(output_path)
                        continue

                    max_dim = max(width, height)
                    new_im = Image.new("RGB", (max_dim, max_dim), (255, 255, 255))  # fondo blanco
                    offset = ((max_dim - width) // 2, (max_dim - height) // 2)
                    new_im.paste(im, offset)
                    new_im.save(output_path)
                    procesadas += 1
            except Exception as e:
                print(f"Error con {filename}: {e}")

    return procesadas

def seleccionar_y_procesar():
    folder = filedialog.askdirectory(title="Selecciona la carpeta principal de imágenes")
    if not folder:
        return

    count = hacer_cuadradas_y_guardar_con_estructura(folder)
    messagebox.showinfo("Proceso completado", f"Imágenes cuadradas: {count}")

# Interfaz gráfica
root = tk.Tk()
root.withdraw()  # Oculta ventana principal
seleccionar_y_procesar()
