import os
import shutil
import datetime
import logging
from win10toast import ToastNotifier

# Configuración de logging
logging.basicConfig(filename="organizador.log", level=logging.INFO, format="%(asctime)s - %(message)s")
notificador = ToastNotifier()

# Función para obtener la semana actual
def obtener_rango_semana():
    hoy = datetime.date.today()
    inicio_semana = hoy - datetime.timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + datetime.timedelta(days=6)
    return inicio_semana, fin_semana

# Función para renombrar archivos en caso de conflicto
def renombrar_si_existe(destino, nombre_archivo):
    base, extension = os.path.splitext(nombre_archivo)
    contador = 1
    nuevo_nombre = nombre_archivo
    while os.path.exists(os.path.join(destino, nuevo_nombre)):
        nuevo_nombre = f"{base} ({contador}){extension}"
        contador += 1
    return nuevo_nombre

# Función para organizar archivos por tipo
def organizar_por_tipo(origen, destino, ignorar_extensiones=[], ignorar_carpetas=[]):
    for root, dirs, files in os.walk(origen):
        # Ignorar carpetas específicas
        if any(ignorar in root for ignorar in ignorar_carpetas):
            continue
        
        for archivo in files:
            archivo_path = os.path.join(root, archivo)
            extension = os.path.splitext(archivo)[-1].lower()
            
            if extension in ignorar_extensiones:
                continue
            
            tipo_carpeta = extension[1:] if extension else "otros"
            destino_tipo = os.path.join(destino, tipo_carpeta)
            os.makedirs(destino_tipo, exist_ok=True)
            
            nuevo_nombre = renombrar_si_existe(destino_tipo, archivo)
            try:
                shutil.move(archivo_path, os.path.join(destino_tipo, nuevo_nombre))
                logging.info(f"Movido: {archivo_path} -> {os.path.join(destino_tipo, nuevo_nombre)}")
            except Exception as e:
                logging.error(f"Error moviendo {archivo_path}: {e}")

# Función para eliminar carpetas vacías
def eliminar_carpetas_vacias(ruta):
    for root, dirs, files in os.walk(ruta, topdown=False):
        for dir_ in dirs:
            dir_path = os.path.join(root, dir_)
            if not os.listdir(dir_path):
                os.rmdir(dir_path)
                logging.info(f"Carpeta vacía eliminada: {dir_path}")

# Organización semanal de descargas
def organizar_descargas():
    inicio_semana, fin_semana = obtener_rango_semana()
    carpeta_descargas = os.path.expanduser("~/Downloads")
    carpeta_destino = os.path.join(carpeta_descargas, f"Semana {inicio_semana} a {fin_semana}")
    ignorar_carpetas = [carpeta_destino]
    
    os.makedirs(carpeta_destino, exist_ok=True)
    organizar_por_tipo(carpeta_descargas, carpeta_destino, ignorar_carpetas=ignorar_carpetas)
    eliminar_carpetas_vacias(carpeta_descargas)
    notificador.show_toast("Organización de Descargas", "Se completó la organización semanal de descargas.", duration=5)

# Organización diaria del escritorio
def organizar_escritorio():
    carpeta_escritorio = os.path.expanduser("~/Desktop")
    carpeta_destino = os.path.join(carpeta_escritorio, "Organizado")
    ignorar_carpetas = [carpeta_destino]
    
    os.makedirs(carpeta_destino, exist_ok=True)
    # Ignorar archivos .exe y accesos directos (.lnk)
    organizar_por_tipo(carpeta_escritorio, carpeta_destino, ignorar_extensiones=[".exe", ".lnk"], ignorar_carpetas=ignorar_carpetas)
    eliminar_carpetas_vacias(carpeta_escritorio)
    notificador.show_toast("Organización del Escritorio", "Se completó la organización diaria del escritorio.", duration=5)

# Ejecución principal
if __name__ == "__main__":
    notificador.show_toast("Organizador de Archivos", "El script de organización ha comenzado.", duration=5)
    organizar_descargas()  # Organización semanal
    organizar_escritorio()  # Organización diaria
    notificador.show_toast("Organizador de Archivos", "El proceso de organización ha finalizado.", duration=5)
