import os
import logging
from PIL import Image, ImageOps

import tkinter as tk
from tkinter import filedialog
from tkinterdnd2 import TkinterDnD, DND_FILES

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Función para eliminar el fondo blanco, recortar y ajustar la imagen en el lienzo
def procesar_imagen(imagen_path, output_path):
    try:
        # Abrir imagen y convertir a RGBA (incluye transparencia)
        img = Image.open(imagen_path).convert("RGBA")

        # Obtener los datos de la imagen y detectar los límites del área no blanca
        bg = Image.new("RGBA", img.size, (255, 255, 255, 0))
        diff = Image.chops.difference(img, bg)
        bbox = diff.getbbox()  # Obtener el recorte de la parte no blanca

        if bbox:
            # Recortar la imagen para eliminar el aire sobrante
            img = img.crop(bbox)

        # Crear lienzo con las dimensiones especificadas
        lienzo = Image.new("RGBA", (1340, 1785), (255, 255, 255, 0))

        # Ajustar imagen al lienzo sin perder proporción
        img.thumbnail((1340, 1785), Image.Resampling.LANCZOS)
        img = ImageOps.contain(img, (1340, 1785))

        # Pegar imagen en el centro del lienzo
        posicion = ((1340 - img.width) // 2, (1785 - img.height) // 2)
        lienzo.paste(img, posicion, img)

        # Si el formato de salida es JPEG, convertir la imagen a RGB
        if output_path.lower().endswith(".jpg") or output_path.lower().endswith(".jpeg"):
            lienzo = lienzo.convert("RGB")

        # Guardar la imagen final
        lienzo.save(output_path)
        logging.info(f"Procesada: {output_path}")
    except Exception as e:
        logging.error(f"Error al procesar {imagen_path}: {e}")

# Función para procesar todas las imágenes en una carpeta
def procesar_carpeta(input_folder, output_folder):
    for root, dirs, files in os.walk(input_folder):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                imagen_path = os.path.join(root, file)
                # Crear la misma estructura de carpetas
                output_path = os.path.join(output_folder, os.path.relpath(root, input_folder), file)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                procesar_imagen(imagen_path, output_path)

# Interfaz gráfica
def seleccionar_carpeta():
    carpeta = filedialog.askdirectory()
    if carpeta:
        output_folder = os.path.join(carpeta, "imagenes shein")
        os.makedirs(output_folder, exist_ok=True)
        procesar_carpeta(carpeta, output_folder)
        logging.info("Procesamiento de carpeta completo.")

def arrastrar_imagen(event):
    imagen_path = event.data
    if os.path.isfile(imagen_path) and imagen_path.lower().endswith(('.png', '.jpg', '.jpeg')):
        output_folder = os.path.join(os.path.dirname(imagen_path), "imagenes shein")
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, os.path.basename(imagen_path))
        procesar_imagen(imagen_path, output_path)

# Crear ventana Tkinter
root = TkinterDnD.Tk()  # Ventana con funcionalidad de arrastrar
root.title("Procesador de Imágenes Shein")

# Botón para seleccionar carpeta
boton_carpeta = tk.Button(root, text="Seleccionar Carpeta", command=seleccionar_carpeta)
boton_carpeta.pack(pady=20)

# Área para arrastrar imágenes
root.drop_target_register(DND_FILES)
root.dnd_bind('<<Drop>>', arrastrar_imagen)

root.geometry("300x150")
root.mainloop()
