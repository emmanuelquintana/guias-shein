import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

# Función para seleccionar y guardar el archivo CSV
def save_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
    return file_path

# Función para agregar productos al DataFrame
def add_product():
    product_name = simpledialog.askstring("Nombre del producto", "Ingrese el nombre del producto:")
    product_sku = simpledialog.askstring("SKU del producto", "Ingrese el SKU del producto:")
    product_price = simpledialog.askfloat("Precio del producto", "Ingrese el precio del producto:")
    product_description = simpledialog.askstring("Descripción del producto", "Ingrese la descripción del producto:")
    
    selected_colors = [color for color, var in color_vars.items() if var.get()]
    selected_sizes = [size for size, var in size_vars.items() if var.get()]

    if not selected_colors or not selected_sizes:
        messagebox.showerror("Error", "Debe seleccionar al menos un color y una talla.")
        return

    for color in selected_colors:
        for size in selected_sizes:
            sku = f"{product_sku}-{color[:2].upper()}-{size}"
            data.append({
                "Type": "variation",
                "SKU": sku,
                "Name": product_name,
                "Description": product_description,
                "Regular price": product_price,
                "Attribute 1 name": "Color",
                "Attribute 1 value(s)": color,
                "Attribute 2 name": "Talla",
                "Attribute 2 value(s)": size
            })
    
    messagebox.showinfo("Éxito", "Producto y variantes añadidos con éxito.")

# Inicializar la lista de datos
data = []

# Crear la ventana principal
root = tk.Tk()
root.title("Agregar Productos y Variantes")

# Crear los campos de colores y tallas
color_options = ["Negro", "Blanco", "Marino", "Rojo", "Azul Rey", "Gris Jaspe", "Gris Oxford", "Naranja", "Rosa", "Fucsia", "Morado", "Cielo"]
size_options = ["CH", "M", "G", "XG"]

color_vars = {color: tk.BooleanVar() for color in color_options}
size_vars = {size: tk.BooleanVar() for size in size_options}

# Crear checkboxes para colores
tk.Label(root, text="Seleccione los colores:").grid(row=0, column=0, sticky="w")
for i, color in enumerate(color_options):
    tk.Checkbutton(root, text=color, variable=color_vars[color]).grid(row=i+1, column=0, sticky="w")

# Crear checkboxes para tallas
tk.Label(root, text="Seleccione las tallas:").grid(row=0, column=1, sticky="w")
for i, size in enumerate(size_options):
    tk.Checkbutton(root, text=size, variable=size_vars[size]).grid(row=i+1, column=1, sticky="w")

# Botón para agregar productos
tk.Button(root, text="Agregar Producto", command=add_product).grid(row=len(color_options)+1, column=0, columnspan=2)

# Botón para guardar el archivo CSV
def save_csv():
    file_path = save_file()
    if file_path:
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False)
        messagebox.showinfo("Éxito", f"Archivo CSV guardado en {file_path}")

tk.Button(root, text="Guardar CSV", command=save_csv).grid(row=len(color_options)+2, column=0, columnspan=2)

root.mainloop()
