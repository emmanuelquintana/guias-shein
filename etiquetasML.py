import os
import re
from tkinter import Tk, filedialog, simpledialog, messagebox, ttk, StringVar, IntVar
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
import io

# Función para seleccionar el archivo PDF
def select_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    return file_path

# Función para seleccionar una carpeta
def select_folder():
    root = Tk()
    root.withdraw()
    folder_path = filedialog.askdirectory()
    return folder_path

# Función para recortar las etiquetas y guardarlas como imágenes individuales
def crop_and_save_labels(pdf_path, output_folder):
    pdf_reader = PdfReader(pdf_path)
    label_count = 0
    colors = set()
    sizes = set()
    
    for page_num, page in enumerate(pdf_reader.pages):
        if '/Annots' in page:
            for annot in page['/Annots']:
                annot_obj = annot.get_object()
                if annot_obj['/Subtype'] == '/Widget':
                    rect = annot_obj['/Rect']
                    x1, y1, x2, y2 = [int(val) for val in rect]
                    
                    pdf_writer = PdfWriter()
                    new_page = page
                    new_page.cropbox.lower_left = (x1, y1)
                    new_page.cropbox.upper_right = (x2, y2)
                    pdf_writer.add_page(new_page)
                    
                    output_pdf = io.BytesIO()
                    pdf_writer.write(output_pdf)
                    
                    output_pdf.seek(0)
                    with open(os.path.join(output_folder, f"label_{label_count}.pdf"), 'wb') as output:
                        output.write(output_pdf.read())
                    
                    # Convertir PDF a imagen
                    pdf_image = Image.open(io.BytesIO(output_pdf.getvalue()))
                    pdf_image.save(os.path.join(output_folder, f"label_{label_count}.png"), "PNG")
                    os.remove(os.path.join(output_folder, f"label_{label_count}.pdf"))
                    label_count += 1
                    
                    # Obtener color y talla del texto de la etiqueta
                    text = page.extract_text()
                    color, size = extract_color_and_size_from_text(text)
                    colors.add(color)
                    sizes.add(size)
    
    return colors, sizes

# Función para extraer color y talla del texto de la etiqueta
def extract_color_and_size_from_text(text):
    colors = ['Blanco', 'Negro', 'Azul marino', 'Azul rey', 'Rosa pastel', 'Bugambilia', 'Jade']
    sizes = ['CH', 'M', 'G', 'XG']
    color = 'Desconocido'
    size = 'Desconocido'
    
    for c in colors:
        if re.search(r'\b' + re.escape(c) + r'\b', text, re.IGNORECASE):
            color = c
            break
    
    for s in sizes:
        if re.search(r'\b' + re.escape(s) + r'\b', text, re.IGNORECASE):
            size = s
            break
    
    return color, size

# Función para mostrar una ventana de selección de color y talla
def select_color_and_size(colors, sizes):
    selection = {}

    def on_submit():
        selection['color'] = color_var.get()
        selection['size'] = size_var.get()
        selection['quantity'] = quantity_var.get()
        root.quit()

    root = Tk()
    root.title("Seleccione Color, Talla y Cantidad")

    ttk.Label(root, text="Color:").grid(column=0, row=0, padx=10, pady=10)
    color_var = StringVar(value="Seleccione" if not colors else next(iter(colors)))
    color_menu = ttk.Combobox(root, textvariable=color_var, values=list(colors))
    color_menu.grid(column=1, row=0, padx=10, pady=10)

    ttk.Label(root, text="Talla:").grid(column=0, row=1, padx=10, pady=10)
    size_var = StringVar(value="M")
    size_menu = ttk.Combobox(root, textvariable=size_var, values=list(sizes))
    size_menu.grid(column=1, row=1, padx=10, pady=10)

    ttk.Label(root, text="Cantidad:").grid(column=0, row=2, padx=10, pady=10)
    quantity_var = IntVar(value=1)
    quantity_entry = ttk.Entry(root, textvariable=quantity_var)
    quantity_entry.grid(column=1, row=2, padx=10, pady=10)

    submit_button = ttk.Button(root, text="Enviar", command=on_submit)
    submit_button.grid(column=0, row=3, columnspan=2, padx=10, pady=10)

    root.mainloop()

    return selection

# Función para generar el documento Avery 5160 con las etiquetas seleccionadas
def generate_avery_5160(labels, output_path):
    label_sheet = Image.open("Avery5160EasyPeelAddressLabels.pdf")
    label_width, label_height = 816, 1056  # Tamaño de cada etiqueta en píxeles
    x_start, y_start = 54, 72  # Coordenadas iniciales
    x_gap, y_gap = 48, 0  # Espacios entre etiquetas

    for i, label in enumerate(labels):
        label_image = Image.open(label)
        x = x_start + (i % 3) * (label_width + x_gap)
        y = y_start + (i // 3) * (label_height + y_gap)
        label_sheet.paste(label_image, (x, y))

    label_sheet.save(output_path)

# Función principal
def main():
    product_pdf_path = select_file()
    if not product_pdf_path:
        messagebox.showerror("Error", "No se seleccionó ningún archivo.")
        return
    
    output_folder = select_folder()
    if not output_folder:
        messagebox.showerror("Error", "No se seleccionó ninguna carpeta.")
        return
    
    colors, sizes = crop_and_save_labels(product_pdf_path, output_folder)
    if not colors:
        messagebox.showerror("Error", "No se detectaron colores en las etiquetas.")
        return
    
    labels = []
    while True:
        selection = select_color_and_size(colors, sizes)
        color = selection['color']
        size = selection['size']
        quantity = selection['quantity']
        
        if not color or not size or not quantity:
            break
        
        for i in range(quantity):
            label_path = filedialog.askopenfilename(initialdir=output_folder, filetypes=[("Image files", "*.png")])
            if not label_path:
                continue
            labels.append(label_path)
    
    output_pdf_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF files", "*.pdf")])
    if not output_pdf_path:
        messagebox.showerror("Error", "No se seleccionó el destino para guardar el documento.")
        return
    
    generate_avery_5160(labels, output_pdf_path)
    messagebox.showinfo("Éxito", f"Documento Avery 5160 generado con éxito en {output_pdf_path}.")

if __name__ == "__main__":
    main()
