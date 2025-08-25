from PIL import Image
import os

def ajustar_imagen(ruta_imagen, ancho_lienzo=1340, alto_lienzo=1785):
    # Abrir la imagen
    imagen = Image.open(ruta_imagen)
    
    # Calcular la relación de aspecto del lienzo
    relacion_lienzo = ancho_lienzo / alto_lienzo
    
    # Obtener dimensiones originales
    ancho_orig, alto_orig = imagen.size
    relacion_imagen = ancho_orig / alto_orig
    
    # Calcular nuevas dimensiones manteniendo la relación de aspecto
    if relacion_imagen > relacion_lienzo:
        # Si la imagen es más ancha proporcionalmente
        nuevo_alto = alto_lienzo
        nuevo_ancho = int(alto_lienzo * relacion_imagen)
    else:
        # Si la imagen es más alta proporcionalmente
        nuevo_ancho = ancho_lienzo
        nuevo_alto = int(ancho_lienzo / relacion_imagen)
    
    # Redimensionar la imagen
    imagen_redimensionada = imagen.resize((nuevo_ancho, nuevo_alto), Image.Resampling.LANCZOS)
    
    # Crear nuevo lienzo blanco
    lienzo = Image.new('RGB', (ancho_lienzo, alto_lienzo), 'white')
    
    # Calcular posición para centrar la imagen
    x = (ancho_lienzo - nuevo_ancho) // 2
    y = (alto_lienzo - nuevo_alto) // 2
    
    # Pegar la imagen redimensionada en el lienzo
    lienzo.paste(imagen_redimensionada, (x, y))
    
    return lienzo

def procesar_carpeta(carpeta_entrada, carpeta_salida):
    # Crear carpeta de salida si no existe
    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)
    
    # Recorrer todas las subcarpetas y archivos
    for raiz, dirs, archivos in os.walk(carpeta_entrada):
        for archivo in archivos:
            if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Construir rutas
                ruta_completa = os.path.join(raiz, archivo)
                
                # Crear la misma estructura de carpetas en el destino
                ruta_relativa = os.path.relpath(raiz, carpeta_entrada)
                carpeta_destino = os.path.join(carpeta_salida, ruta_relativa)
                
                if not os.path.exists(carpeta_destino):
                    os.makedirs(carpeta_destino)
                
                # Procesar imagen
                try:
                    imagen_procesada = ajustar_imagen(ruta_completa)
                    
                    # Guardar imagen procesada
                    ruta_salida = os.path.join(carpeta_destino, f"procesado_{archivo}")
                    imagen_procesada.save(ruta_salida, quality=95)
                    print(f"Procesada: {ruta_completa}")
                except Exception as e:
                    print(f"Error procesando {ruta_completa}: {str(e)}")

if __name__ == "__main__":
    # Definir carpetas de entrada y salida
    CARPETA_ENTRADA = "ruta/a/tus/imagenes"  # Cambia esto a tu carpeta de entrada
    CARPETA_SALIDA = "ruta/a/imagenes/procesadas"  # Cambia esto a tu carpeta de salida
    
    procesar_carpeta(CARPETA_ENTRADA, CARPETA_SALIDA)