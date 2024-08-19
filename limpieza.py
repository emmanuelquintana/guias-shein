import os
import shutil
from datetime import datetime
import tkinter as tk
from tkinter import filedialog
import logging

# Configurar el logging
logging.basicConfig(filename='archivo_log.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def seleccionar_carpeta():
    # Abrir una ventana para seleccionar la carpeta de origen
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal de Tkinter
    return filedialog.askdirectory(title="Seleccionar carpeta de origen")

# Obtener la fecha actual en formato "YYYY-MM-DD"
fecha_actual = datetime.now().strftime('%Y-%m-%d')

# Definir el nombre de la carpeta de destino
carpeta_destino = f"EN USO {fecha_actual}"

# Seleccionar la carpeta de origen
directorio_origen = seleccionar_carpeta()

if not directorio_origen:
    logging.error("No se seleccionó ninguna carpeta. El script ha sido cancelado.")
    print("No se seleccionó ninguna carpeta. El script ha sido cancelado.")
    exit()

logging.info(f"Carpeta de origen seleccionada: {directorio_origen}")

# Crear la carpeta de destino si no existe
if not os.path.exists(carpeta_destino):
    os.makedirs(carpeta_destino)
    logging.info(f"Carpeta de destino creada: {carpeta_destino}")

# Recorrer todos los archivos y carpetas en el directorio de origen
for item in os.listdir(directorio_origen):
    item_path = os.path.join(directorio_origen, item)

    # Si es un archivo DOCX o PDF, lo movemos
    if os.path.isfile(item_path) and (item.endswith('.docx') or item.endswith('.pdf')):
        shutil.move(item_path, carpeta_destino)
        logging.info(f"Archivo movido: {item_path}")

    # Si es una carpeta que comienza con "GUIAS SHEIN", la movemos
    elif os.path.isdir(item_path) and item.startswith("GUIAS SHEIN"):
        shutil.move(item_path, carpeta_destino)
        logging.info(f"Carpeta movida: {item_path}")

print(f"Archivos y carpetas movidos a la carpeta {carpeta_destino}")
logging.info(f"Archivos y carpetas movidos a la carpeta {carpeta_destino}")
