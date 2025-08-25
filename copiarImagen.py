import os
import shutil
from tkinter import Tk
from tkinter.filedialog import askdirectory

def copiar_imagenes(origen, destino):
    # Asegurarse de que la carpeta destino exista
    if not os.path.exists(destino):
        os.makedirs(destino)

    for root, dirs, files in os.walk(origen):
        for file in files:
            # Comprobar que el archivo tenga extensión .jpg (case insensitive)
            if file.lower().endswith('.jpg'):
                ruta_origen = os.path.join(root, file)
                nombre_destino = file
                ruta_destino = os.path.join(destino, nombre_destino)
                contador = 1

                # Si el archivo ya existe en destino, agregar un sufijo numérico al nombre
                while os.path.exists(ruta_destino):
                    nombre_sin_ext, ext = os.path.splitext(file)
                    nombre_destino = f"{nombre_sin_ext}_{contador}{ext}"
                    ruta_destino = os.path.join(destino, nombre_destino)
                    contador += 1

                try:
                    # Intentar copiar el archivo preservando metadatos
                    shutil.copy2(ruta_origen, ruta_destino)
                    print(f"Copiado: {ruta_origen} a {ruta_destino}")
                except Exception as e:
                    # Capturar y mostrar el error sin detener la ejecución
                    print(f"Error copiando {ruta_origen} a {ruta_destino}: {e}")

if __name__ == "__main__":
    # Ocultar la ventana principal de Tkinter
    root = Tk()
    root.withdraw()

    # Seleccionar carpeta de origen
    directorio_origen = askdirectory(title="Selecciona la carpeta de origen")
    if not directorio_origen:
        print("No se seleccionó carpeta de origen.")
        exit()

    # Seleccionar carpeta de destino
    directorio_destino = askdirectory(title="Selecciona la carpeta de destino")
    if not directorio_destino:
        print("No se seleccionó carpeta de destino.")
        exit()

    copiar_imagenes(directorio_origen, directorio_destino)
