import os
import io
from tkinter import Tk, filedialog
from PIL import Image, ImageEnhance
from rembg import remove, new_session

# Inicializar el modelo más avanzado
session = new_session("isnet-general-use")

EXTENSIONES_VALIDAS = (".png", ".jpg", ".jpeg", ".webp")

def seleccionar_carpeta():
    root = Tk()
    root.withdraw()
    return filedialog.askdirectory(title="Selecciona la carpeta raíz con imágenes")

def mejorar_contraste(imagen):
    enhancer = ImageEnhance.Contrast(imagen)
    return enhancer.enhance(1.5)

def procesar_imagen(ruta_entrada):
    # Abrir imagen y mejorar contraste
    input_img = Image.open(ruta_entrada).convert("RGB")
    input_img = mejorar_contraste(input_img)

    # Convertir a bytes para rembg
    buffer = io.BytesIO()
    input_img.save(buffer, format="PNG")
    buffer.seek(0)
    output_data = remove(buffer.read(), session=session)

    # Convertir resultado a imagen y componer sobre fondo blanco
    imagen = Image.open(io.BytesIO(output_data)).convert("RGBA")
    fondo = Image.new("RGBA", imagen.size, (255, 255, 255, 255))
    compositada = Image.alpha_composite(fondo, imagen).convert("RGB")
    return compositada

def procesar_directorio(carpeta_entrada):
    carpeta_salida = carpeta_entrada.rstrip("/\\") + "_output"

    for dir_actual, _, archivos in os.walk(carpeta_entrada):
        if carpeta_salida in dir_actual:
            continue  # evitar procesar ya procesadas

        for archivo in archivos:
            if not archivo.lower().endswith(EXTENSIONES_VALIDAS):
                continue

            ruta_entrada = os.path.join(dir_actual, archivo)

            # Crear ruta correspondiente en salida
            ruta_relativa = os.path.relpath(dir_actual, carpeta_entrada)
            dir_salida = os.path.join(carpeta_salida, ruta_relativa)
            os.makedirs(dir_salida, exist_ok=True)

            try:
                imagen_salida = procesar_imagen(ruta_entrada)
                ruta_salida = os.path.join(dir_salida, archivo)
                imagen_salida.save(ruta_salida)
                print(f"✅ Procesado: {ruta_entrada} -> {ruta_salida}")
            except Exception as e:
                print(f"❌ Error al procesar {ruta_entrada}: {e}")

if __name__ == "__main__":
    carpeta = seleccionar_carpeta()
    if carpeta:
        procesar_directorio(carpeta)
        print("🎉 ¡Procesamiento completado! Imágenes con fondo blanco guardadas en '*_output'.")
    else:
        print("⚠️ No se seleccionó ninguna carpeta.")
