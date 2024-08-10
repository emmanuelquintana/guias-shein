import os
import shutil
from tkinter import Tk, filedialog

# Función para abrir la ventana de selección de carpeta
def seleccionar_carpeta():
    root = Tk()
    root.withdraw()  # Ocultar la ventana principal de Tkinter
    carpeta_seleccionada = filedialog.askdirectory()
    return carpeta_seleccionada

# Función para organizar los archivos
def organizar_archivos(carpeta):
    # Definir las extensiones de archivo para cada categoría
    tipos_de_archivos = {
        'Editables': ['.psd', '.ai', '.eps'],
        'Fuentes': ['.otf'],
        'Imagenes': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff'],
        'Videos': ['.mp4', '.mov', '.avi', '.mkv'],
        'Musica': ['.mp3', '.wav', '.aac'],
        'PDF': ['.pdf'],
        'Documentos': ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx'],
        'Otros': []  # Esta categoría manejará archivos no especificados
    }
    
    # Crear las subcarpetas si no existen
    for categoria in tipos_de_archivos:
        carpeta_destino = os.path.join(carpeta, categoria)
        if not os.path.exists(carpeta_destino):
            os.makedirs(carpeta_destino)
    
    # Recorrer la carpeta y sus subcarpetas
    for root, dirs, files in os.walk(carpeta, topdown=False):
        for archivo in files:
            ruta_archivo = os.path.join(root, archivo)
            extension = os.path.splitext(archivo)[1].lower()
            movido = False
            for categoria, extensiones in tipos_de_archivos.items():
                if extension in extensiones:
                    carpeta_destino = os.path.join(carpeta, categoria)
                    nombre_archivo_destino = os.path.join(carpeta_destino, archivo)
                    contador = 1
                    while os.path.exists(nombre_archivo_destino):
                        nombre_archivo_destino = os.path.join(carpeta_destino, f"{os.path.splitext(archivo)[0]}_{contador}{extension}")
                        contador += 1
                    shutil.move(ruta_archivo, nombre_archivo_destino)
                    movido = True
                    break
            if not movido:
                carpeta_destino = os.path.join(carpeta, 'Otros')
                nombre_archivo_destino = os.path.join(carpeta_destino, archivo)
                contador = 1
                while os.path.exists(nombre_archivo_destino):
                    nombre_archivo_destino = os.path.join(carpeta_destino, f"{os.path.splitext(archivo)[0]}_{contador}{extension}")
                    contador += 1
                shutil.move(ruta_archivo, nombre_archivo_destino)
    
    # Eliminar las carpetas vacías
    for root, dirs, files in os.walk(carpeta, topdown=False):
        for nombre in dirs:
            ruta_directorio = os.path.join(root, nombre)
            try:
                os.rmdir(ruta_directorio)
            except OSError:
                pass

# Ejecutar las funciones
carpeta = seleccionar_carpeta()
if carpeta:
    organizar_archivos(carpeta)
