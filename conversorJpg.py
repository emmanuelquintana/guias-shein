import os
from tkinter import Tk, filedialog
from PIL import Image

def select_folder():
    """Abre un cuadro de diálogo para seleccionar una carpeta."""
    root = Tk()
    root.withdraw()
    folder_selected = filedialog.askdirectory(title="Selecciona la carpeta con archivos WEBP")
    return folder_selected

def convert_webp_to_jpg(input_folder):
    """Convierte todos los archivos .webp en una carpeta a .jpg y los guarda en una carpeta de salida."""
    if not os.path.exists(input_folder):
        print("La carpeta seleccionada no existe.")
        return

    output_folder = os.path.join(input_folder, "output_jpg")
    os.makedirs(output_folder, exist_ok=True)

    for file_name in os.listdir(input_folder):
        if file_name.lower().endswith(".webp"):
            input_path = os.path.join(input_folder, file_name)
            output_path = os.path.join(output_folder, os.path.splitext(file_name)[0] + ".jpg")

            try:
                with Image.open(input_path) as img:
                    rgb_image = img.convert("RGB")  # Convertir a formato RGB
                    rgb_image.save(output_path, "JPEG")
                    print(f"Convertido: {file_name} -> {os.path.basename(output_path)}")
            except Exception as e:
                print(f"Error al convertir {file_name}: {e}")

    print(f"Conversión completa. Archivos guardados en: {output_folder}")

if __name__ == "__main__":
    folder = select_folder()
    if folder:
        convert_webp_to_jpg(folder)
    else:
        print("No se seleccionó ninguna carpeta.")
