import pandas as pd
import tkinter as tk
from tkinter import filedialog

def select_file(prompt):
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(title=prompt, filetypes=[("CSV files", "*.csv")])
    return file_path

# Seleccionar el archivo de Wix
wix_file_path = select_file("Seleccione el archivo CSV exportado de Wix")
wix_df = pd.read_csv(wix_file_path)

# Seleccionar el archivo de ejemplo de WooCommerce
wc_file_path = select_file("Seleccione el archivo CSV exportado de WooCommerce")
wc_df = pd.read_csv(wc_file_path)

# Crear un nuevo DataFrame para almacenar los datos convertidos
wc_columns = wc_df.columns
converted_df = pd.DataFrame(columns=wc_columns)

# Mapeo básico de campos de Wix a WooCommerce
converted_df['Type'] = wix_df.apply(lambda row: 'variable' if row['fieldType'] == 'Product' else 'variation', axis=1)
converted_df['SKU'] = wix_df['sku']
converted_df['Name'] = wix_df['name']
converted_df['Description'] = wix_df['description']
converted_df['Regular price'] = wix_df['price']

# Asegurarse de que los productos y las variantes estén correctamente diferenciados y asociados
converted_df['Parent'] = wix_df.apply(lambda row: row['handleId'] if row['fieldType'] == 'Variant' else '', axis=1)

# Convertir atributos
converted_df['Attribute 1 name'] = wix_df['productOptionName1']
converted_df['Attribute 1 value(s)'] = wix_df['productOptionDescription1']
converted_df['Attribute 2 name'] = wix_df['productOptionName2']
converted_df['Attribute 2 value(s)'] = wix_df['productOptionDescription2']

# Mapear las imágenes
converted_df['Images'] = wix_df['productImageUrl']

# Rellenar otros campos requeridos por WooCommerce con valores predeterminados o vacíos
converted_df['Published'] = '1'
converted_df['Visibility in catalog'] = 'visible'
converted_df['Tax status'] = 'taxable'
converted_df['In stock?'] = '1'

# Guardar el archivo convertido
converted_file_path = filedialog.asksaveasfilename(title="Guardar archivo convertido", defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
converted_df.to_csv(converted_file_path, index=False)

print(f"Archivo convertido guardado en: {converted_file_path}")
