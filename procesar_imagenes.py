from PIL import Image
import os
import tkinter as tk
from tkinter import filedialog, ttk
import logging
from datetime import datetime
import numpy as np
from PIL import ImageOps, ImageStat
from PIL import ImageTk
import customtkinter as ctk
from pathlib import Path
import threading
from itertools import cycle
import time

# Configurar logging
def configurar_logging():
    # Crear carpeta de logs si no existe
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Configurar el nombre del archivo de log con la fecha
    nombre_log = f'logs/procesamiento_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Configurar el logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(nombre_log),
            logging.StreamHandler()
        ]
    )

def seleccionar_carpeta(titulo):
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal
    carpeta = filedialog.askdirectory(title=titulo)
    return carpeta

def detectar_tipo_imagen(imagen):
    """
    Detecta si la imagen es una prenda completa o un detalle
    Returns: True si es prenda completa, False si es detalle
    """
    # Convertir a escala de grises
    imagen_gris = imagen.convert('L')
    
    # Obtener los bordes de la imagen (donde hay contenido)
    bordes = ImageOps.invert(imagen_gris)
    stat = ImageStat.Stat(bordes)
    
    # Calcular el porcentaje de píxeles no blancos en los bordes
    borde_superior = bordes.crop((0, 0, bordes.width, 10))
    borde_inferior = bordes.crop((0, bordes.height-10, bordes.width, bordes.height))
    borde_izquierdo = bordes.crop((0, 0, 10, bordes.height))
    borde_derecho = bordes.crop((bordes.width-10, 0, bordes.width, bordes.height))
    
    stat_sup = ImageStat.Stat(borde_superior)
    stat_inf = ImageStat.Stat(borde_inferior)
    stat_izq = ImageStat.Stat(borde_izquierdo)
    stat_der = ImageStat.Stat(borde_derecho)
    
    # Si hay contenido significativo en los bordes, probablemente sea una prenda completa
    umbral = 20  # Ajusta este valor según necesites
    bordes_con_contenido = sum([
        stat_sup.mean[0] > umbral,
        stat_inf.mean[0] > umbral,
        stat_izq.mean[0] > umbral,
        stat_der.mean[0] > umbral
    ])
    
    return bordes_con_contenido >= 2  # Si hay contenido en al menos 2 bordes

class ImagenPreview(ctk.CTkFrame):
    def __init__(self, master, imagen_path, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.configure(fg_color=("white", "gray20"))
        
        # Cargar y mostrar miniatura
        self.imagen = Image.open(imagen_path)
        self.imagen.thumbnail((150, 150))
        self.photo = ImageTk.PhotoImage(self.imagen)
        
        # Contenedor principal con efecto glassmorphism
        self.container = ctk.CTkFrame(self, corner_radius=10, fg_color=("white", "gray25"))
        self.container.pack(padx=5, pady=5, fill="both", expand=True)
        
        # Imagen
        self.label_imagen = ctk.CTkLabel(self.container, image=self.photo, text="")
        self.label_imagen.pack(padx=5, pady=5)
        
        # Nombre del archivo
        nombre = Path(imagen_path).name
        if len(nombre) > 20:
            nombre = nombre[:17] + "..."
        self.label_nombre = ctk.CTkLabel(self.container, text=nombre, 
                                       font=("Roboto", 12))
        self.label_nombre.pack(pady=2)
        
        # Checkbox
        self.var = tk.BooleanVar()
        self.checkbox = ctk.CTkCheckBox(self.container, text="", variable=self.var)
        self.checkbox.pack(pady=5)

class SelectorImagenes(ctk.CTkToplevel):
    def __init__(self, carpeta_entrada):
        super().__init__()
        
        # Configurar tamaño inicial más grande
        ancho_pantalla = self.winfo_screenwidth()
        alto_pantalla = self.winfo_screenheight()
        # Usar 80% del tamaño de la pantalla
        ancho_ventana = int(ancho_pantalla * 0.8)
        alto_ventana = int(alto_pantalla * 0.8)
        
        self.title("Selector de Imágenes")
        self.geometry(f"{ancho_ventana}x{alto_ventana}")
        self.minsize(1200, 800)  # Tamaño mínimo de la ventana
        
        # Configurar para que inicie maximizada
        self.state('zoomed')
        
        self.imagenes_seleccionadas = set()
        
        # Configurar el estilo glassmorphism
        self.configure(fg_color=("white", "gray17"))
        
        # Frame principal con más padding
        self.frame_principal = ctk.CTkFrame(self, corner_radius=15)
        self.frame_principal.pack(fill="both", expand=True, padx=30, pady=30)
        
        # Título con animación y tamaño más grande
        self.label_titulo = ctk.CTkLabel(
            self.frame_principal,
            text="Selecciona las imágenes que necesitan margen",
            font=("Roboto", 28, "bold")
        )
        self.label_titulo.pack(pady=25)
        
        # Frame para el grid de imágenes con scroll - más espacio
        self.frame_scroll = ctk.CTkScrollableFrame(
            self.frame_principal,
            fg_color="transparent"
        )
        self.frame_scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Configurar el grid para mostrar más columnas
        self.frame_scroll.grid_columnconfigure(tuple(range(6)), weight=1)
        
        # Grid de imágenes
        self.cargar_imagenes(carpeta_entrada)
        
        # Frame para botones con más espacio
        self.frame_botones = ctk.CTkFrame(
            self.frame_principal,
            fg_color="transparent"
        )
        self.frame_botones.pack(pady=25)
        
        # Botones más grandes
        button_width = 200
        button_height = 40
        
        self.btn_seleccionar = ctk.CTkButton(
            self.frame_botones,
            text="Seleccionar Todo",
            command=self.seleccionar_todo,
            font=("Roboto", 16),
            corner_radius=10,
            hover_color=("gray70", "gray35"),
            width=button_width,
            height=button_height
        )
        self.btn_seleccionar.pack(side="left", padx=15)
        
        self.btn_deseleccionar = ctk.CTkButton(
            self.frame_botones,
            text="Deseleccionar Todo",
            command=self.deseleccionar_todo,
            font=("Roboto", 16),
            corner_radius=10,
            hover_color=("gray70", "gray35"),
            width=button_width,
            height=button_height
        )
        self.btn_deseleccionar.pack(side="left", padx=15)
        
        self.btn_confirmar = ctk.CTkButton(
            self.frame_botones,
            text="Confirmar",
            command=self.confirmar,
            font=("Roboto", 16, "bold"),
            corner_radius=10,
            hover_color=("#2CC985", "#2FA572"),
            width=button_width,
            height=button_height
        )
        self.btn_confirmar.pack(side="left", padx=15)
        
        # Barra de progreso más grande
        self.progreso = ctk.CTkProgressBar(self.frame_principal, height=15)
        self.progreso.pack(fill="x", padx=30, pady=15)
        self.progreso.set(0)
        
        # Iniciar animación de carga
        self.after(100, self.animar_progreso)

    def cargar_imagenes(self, carpeta_entrada):
        self.previews = []
        row = 0
        col = 0
        max_columnas = 6  # Aumentar número de columnas
        
        # Actualizar las extensiones permitidas para incluir webp
        extensiones_permitidas = ('.png', '.jpg', '.jpeg', '.webp')
        
        for raiz, _, archivos in os.walk(carpeta_entrada):
            if 'Shein' not in raiz:
                for archivo in archivos:
                    if archivo.lower().endswith(extensiones_permitidas):
                        ruta_completa = os.path.join(raiz, archivo)
                        preview = ImagenPreview(self.frame_scroll, ruta_completa)
                        preview.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
                        self.previews.append((ruta_completa, preview))
                        
                        col += 1
                        if col >= max_columnas:
                            col = 0
                            row += 1

    def animar_progreso(self):
        progress_values = cycle([i/100 for i in range(0, 101, 2)])
        
        def update_progress():
            self.progreso.set(next(progress_values))
            self.after(50, update_progress)
        
        update_progress()

    def seleccionar_todo(self):
        for _, preview in self.previews:
            preview.var.set(True)

    def deseleccionar_todo(self):
        for _, preview in self.previews:
            preview.var.set(False)

    def confirmar(self):
        self.imagenes_seleccionadas = {
            ruta for ruta, preview in self.previews if preview.var.get()
        }
        self.quit()

def mostrar_selector_imagenes(carpeta_entrada):
    selector = SelectorImagenes(carpeta_entrada)
    selector.mainloop()
    try:
        selector.destroy()
    except:
        pass
    return selector.imagenes_seleccionadas

class ConfiguracionMarketplace:
    def __init__(self, nombre, ancho, alto, formato, peso_maximo=None, margen=0.95):
        self.nombre = nombre
        self.ancho = ancho
        self.alto = alto
        self.formato = formato
        self.peso_maximo = peso_maximo  # en KB
        self.margen = margen

# Definir las configuraciones de cada marketplace
CONFIGURACIONES = {
    "SHEIN": ConfiguracionMarketplace("Shein", 1340, 1785, "PNG", margen=0.98),
    "AMAZON": ConfiguracionMarketplace("Amazon", 1600, 1600, "PNG"),
    "LIVERPOOL": ConfiguracionMarketplace("Liverpool", 940, 1215, "JPEG", 500, margen=0.98)
}

class SelectorMarketplace(ctk.CTkToplevel):
    def __init__(self):
        super().__init__()
        self.title("Seleccionar Marketplace")
        self.geometry("400x400")  # Aumentamos el alto para el nuevo botón
        
        # Configurar el estilo glassmorphism
        self.configure(fg_color=("white", "gray17"))
        
        # Frame principal
        self.frame = ctk.CTkFrame(self, corner_radius=15)
        self.frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        self.label = ctk.CTkLabel(
            self.frame,
            text="Selecciona el Marketplace",
            font=("Roboto", 20, "bold")
        )
        self.label.pack(pady=20)
        
        # Variable para almacenar la selección
        self.seleccion = None
        
        # Crear botones para cada marketplace
        for config in CONFIGURACIONES.values():
            btn = ctk.CTkButton(
                self.frame,
                text=config.nombre,
                command=lambda c=config: self.seleccionar(c),
                font=("Roboto", 14),
                corner_radius=10,
                hover_color=("#2CC985", "#2FA572"),
                height=35
            )
            btn.pack(pady=10, padx=20, fill="x")
        
        # Separador
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=15, padx=20)
        
        # Botón para procesar todos los marketplaces
        btn_todos = ctk.CTkButton(
            self.frame,
            text="Procesar para todos los Marketplaces",
            command=lambda: self.seleccionar("TODOS"),
            font=("Roboto", 14, "bold"),
            corner_radius=10,
            fg_color="#FF6B6B",  # Color distintivo
            hover_color="#FF4949",
            height=45
        )
        btn_todos.pack(pady=15, padx=20, fill="x")
    
    def seleccionar(self, config):
        self.seleccion = config
        self.quit()

def seleccionar_marketplace():
    selector = SelectorMarketplace()
    selector.mainloop()
    try:
        seleccion = selector.seleccion
        selector.destroy()
    except:
        pass
    return seleccion

def ajustar_imagen(ruta_imagen, config, aplicar_margen=False):
    """
    Ajusta una imagen según la configuración del marketplace
    """
    # Abrir la imagen
    imagen = Image.open(ruta_imagen)
    
    # Convertir a RGB si es necesario
    if imagen.mode in ('RGBA', 'LA') or (imagen.mode == 'P' and 'transparency' in imagen.info):
        fondo = Image.new('RGB', imagen.size, (255, 255, 255))
        if imagen.mode == 'P':
            imagen = imagen.convert('RGBA')
        fondo.paste(imagen, mask=imagen.split()[-1])
        imagen = fondo
    
    # Obtener dimensiones
    ancho_original, alto_original = imagen.size
    ancho_destino, alto_destino = config.ancho, config.alto
    
    # Calcular proporciones
    proporcion_original = ancho_original / alto_original
    proporcion_destino = ancho_destino / alto_destino
    
    # Calcular nuevas dimensiones
    if aplicar_margen:
        # Si se aplica margen, usar el 95% del espacio
        factor = config.margen
        if proporcion_original > proporcion_destino:
            nuevo_ancho = int(ancho_destino * factor)
            nuevo_alto = int(nuevo_ancho / proporcion_original)
        else:
            nuevo_alto = int(alto_destino * factor)
            nuevo_ancho = int(nuevo_alto * proporcion_original)
    else:
        # Sin margen, usar el espacio completo
        if proporcion_original > proporcion_destino:
            nuevo_ancho = ancho_destino
            nuevo_alto = int(nuevo_ancho / proporcion_original)
        else:
            nuevo_alto = alto_destino
            nuevo_ancho = int(nuevo_alto * proporcion_original)
    
    # Redimensionar la imagen
    imagen_redimensionada = imagen.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
    
    # Crear imagen final con fondo blanco
    imagen_final = Image.new('RGB', (ancho_destino, alto_destino), (255, 255, 255))
    
    # Calcular posición para centrar
    x = (ancho_destino - nuevo_ancho) // 2
    y = (alto_destino - nuevo_alto) // 2
    
    # Pegar imagen redimensionada
    imagen_final.paste(imagen_redimensionada, (x, y))
    
    return imagen_final

def guardar_imagen_optimizada(imagen, ruta_salida, config):
    """
    Guarda la imagen con la optimización adecuada según el marketplace
    """
    # Determinar parámetros de guardado según el formato
    if config.formato == "JPEG":
        # Empezar con calidad alta
        calidad = 95
        while True:
            # Guardar temporalmente para verificar tamaño
            imagen.save(ruta_salida, format=config.formato, quality=calidad)
            
            # Verificar tamaño si hay límite
            if config.peso_maximo:
                tamano_actual = os.path.getsize(ruta_salida) / 1024  # Convertir a KB
                if tamano_actual <= config.peso_maximo:
                    break
                
                # Reducir calidad si excede el tamaño
                calidad -= 5
                if calidad < 30:  # Establecer un límite mínimo de calidad
                    logging.warning(f"No se pudo reducir el tamaño de {ruta_salida} por debajo de {config.peso_maximo}KB")
                    break
            else:
                break
    else:  # PNG
        imagen.save(ruta_salida, format=config.formato)

def procesar_todos_marketplaces(carpeta_entrada, imagenes_con_margen):
    for config in CONFIGURACIONES.values():
        logging.info(f"\nIniciando procesamiento para {config.nombre}")
        
        # Crear carpeta del marketplace dentro de la carpeta de entrada
        carpeta_salida = os.path.join(carpeta_entrada, config.nombre)
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
            logging.info(f"Creada carpeta de salida: {carpeta_salida}")
        
        # Contador de imágenes procesadas y errores
        imagenes_procesadas = 0
        errores = 0
        
        # Lista de carpetas a excluir (todos los marketplaces)
        carpetas_excluir = set(c.nombre for c in CONFIGURACIONES.values())
        
        # Recorrer todas las subcarpetas y archivos
        for raiz, dirs, archivos in os.walk(carpeta_entrada):
            # Excluir las carpetas de marketplace
            for marketplace in carpetas_excluir:
                if marketplace in dirs:
                    dirs.remove(marketplace)
            
            # Verificar que la ruta no está dentro de ninguna carpeta de marketplace
            ruta_relativa = os.path.relpath(raiz, carpeta_entrada)
            if any(marketplace in ruta_relativa.split(os.sep) for marketplace in carpetas_excluir):
                continue
            
            for archivo in archivos:
                if archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # Construir rutas
                    ruta_completa = os.path.join(raiz, archivo)
                    carpeta_destino = os.path.join(carpeta_salida, ruta_relativa)
                    
                    if not os.path.exists(carpeta_destino):
                        os.makedirs(carpeta_destino)
                    
                    try:
                        logging.info(f"Procesando imagen: {ruta_completa}")
                        imagen_procesada = ajustar_imagen(
                            ruta_completa, 
                            config,
                            aplicar_margen=ruta_completa in imagenes_con_margen
                        )
                        
                        # Definir nombre de archivo de salida
                        nombre_archivo = os.path.splitext(archivo)[0]
                        extension = ".jpg" if config.formato == "JPEG" else ".png"
                        ruta_salida = os.path.join(carpeta_destino, f"procesado_{nombre_archivo}{extension}")
                        
                        # Guardar imagen con optimización
                        guardar_imagen_optimizada(imagen_procesada, ruta_salida, config)
                        
                        logging.info(f"Imagen guardada en: {ruta_salida}")
                        imagenes_procesadas += 1
                        
                    except Exception as e:
                        logging.error(f"Error procesando {ruta_completa}: {str(e)}")
                        errores += 1
        
        # Resumen para este marketplace
        logging.info(f"\nResumen del procesamiento para {config.nombre}:")
        logging.info(f"Total de imágenes procesadas: {imagenes_procesadas}")
        logging.info(f"Total de errores: {errores}")

def procesar_carpeta(carpeta_entrada):
    # Seleccionar marketplace
    config = seleccionar_marketplace()
    if not config:
        logging.error("No se seleccionó ningún marketplace. Saliendo...")
        return
    
    # Obtener selección de imágenes que necesitan margen
    imagenes_con_margen = mostrar_selector_imagenes(carpeta_entrada)
    
    if config == "TODOS":
        # Procesar para todos los marketplaces
        procesar_todos_marketplaces(carpeta_entrada, imagenes_con_margen)
    else:
        # Procesar para un marketplace específico
        # Crear carpeta del marketplace dentro de la carpeta de entrada
        carpeta_salida = os.path.join(carpeta_entrada, config.nombre)
        if not os.path.exists(carpeta_salida):
            os.makedirs(carpeta_salida)
            logging.info(f"Creada carpeta de salida: {carpeta_salida}")
        
        # Contador de imágenes procesadas y errores
        imagenes_procesadas = 0
        errores = 0
        
        logging.info(f"Iniciando procesamiento de imágenes para {config.nombre}")
        
        # Lista de carpetas a excluir (todos los marketplaces)
        carpetas_excluir = set(c.nombre for c in CONFIGURACIONES.values())
        
        # Recorrer todas las subcarpetas y archivos
        for raiz, dirs, archivos in os.walk(carpeta_entrada):
            # Excluir las carpetas de marketplace
            for marketplace in carpetas_excluir:
                if marketplace in dirs:
                    dirs.remove(marketplace)
            
            # Verificar que la ruta no está dentro de ninguna carpeta de marketplace
            ruta_relativa = os.path.relpath(raiz, carpeta_entrada)
            if any(marketplace in ruta_relativa.split(os.sep) for marketplace in carpetas_excluir):
                continue
            
            for archivo in archivos:
                if archivo.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    # Construir rutas
                    ruta_completa = os.path.join(raiz, archivo)
                    carpeta_destino = os.path.join(carpeta_salida, ruta_relativa)
                    
                    if not os.path.exists(carpeta_destino):
                        os.makedirs(carpeta_destino)
                    
                    try:
                        logging.info(f"Procesando imagen: {ruta_completa}")
                        imagen_procesada = ajustar_imagen(
                            ruta_completa, 
                            config,
                            aplicar_margen=ruta_completa in imagenes_con_margen
                        )
                        
                        # Definir nombre de archivo de salida
                        nombre_archivo = os.path.splitext(archivo)[0]
                        extension = ".jpg" if config.formato == "JPEG" else ".png"
                        ruta_salida = os.path.join(carpeta_destino, f"procesado_{nombre_archivo}{extension}")
                        
                        # Guardar imagen con optimización
                        guardar_imagen_optimizada(imagen_procesada, ruta_salida, config)
                        
                        logging.info(f"Imagen guardada en: {ruta_salida}")
                        imagenes_procesadas += 1
                        
                    except Exception as e:
                        logging.error(f"Error procesando {ruta_completa}: {str(e)}")
                        errores += 1
        
        # Resumen final
        logging.info(f"\nResumen del procesamiento para {config.nombre}:")
        logging.info(f"Total de imágenes procesadas: {imagenes_procesadas}")
        logging.info(f"Total de errores: {errores}")

if __name__ == "__main__":
    # Configurar logging
    configurar_logging()
    
    try:
        # Seleccionar carpeta de entrada
        logging.info("Seleccionando carpeta de entrada...")
        CARPETA_ENTRADA = seleccionar_carpeta("Selecciona la carpeta con las imágenes a procesar")
        
        if not CARPETA_ENTRADA:
            logging.error("No se seleccionó ninguna carpeta de entrada. Saliendo...")
            exit()
        
        # Procesar las imágenes
        procesar_carpeta(CARPETA_ENTRADA)
        
        logging.info("Procesamiento completado exitosamente")
        
    except Exception as e:
        logging.error(f"Error general en la aplicación: {str(e)}")