import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd

# Traducción de colores
color_dict = {
    "01": "Negro",
    "02": "Rojo",
    "03": "Blanco",
    "04": "Azul Marino",
    "07": "Gris",
    "09": "Naranja"
}

class ProductEntryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Entrada de Productos")
        
        # Variables
        self.sku = tk.StringVar()
        self.nombre = tk.StringVar()
        self.descripcion_corta = tk.StringVar()
        self.peso = tk.DoubleVar()
        self.longitud = tk.DoubleVar()
        self.anchura = tk.DoubleVar()
        self.altura = tk.DoubleVar()
        self.categorias = tk.StringVar()
        self.tallas = tk.StringVar()
        self.colores = tk.StringVar()
        
        # Crear interfaz
        self.create_widgets()
        
    def create_widgets(self):
        # SKU
        ttk.Label(self.root, text="SKU:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.sku).grid(row=0, column=1)
        
        # Nombre
        ttk.Label(self.root, text="Nombre:").grid(row=1, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.nombre).grid(row=1, column=1)
        
        # Descripción Corta
        ttk.Label(self.root, text="Descripción Corta:").grid(row=2, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.descripcion_corta).grid(row=2, column=1)
        
        # Peso
        ttk.Label(self.root, text="Peso (kg):").grid(row=3, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.peso).grid(row=3, column=1)
        
        # Longitud
        ttk.Label(self.root, text="Longitud (cm):").grid(row=4, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.longitud).grid(row=4, column=1)
        
        # Anchura
        ttk.Label(self.root, text="Anchura (cm):").grid(row=5, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.anchura).grid(row=5, column=1)
        
        # Altura
        ttk.Label(self.root, text="Altura (cm):").grid(row=6, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.altura).grid(row=6, column=1)
        
        # Categorías
        ttk.Label(self.root, text="Categorías:").grid(row=7, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.categorias).grid(row=7, column=1)
        
        # Tallas
        ttk.Label(self.root, text="Tallas (separadas por coma):").grid(row=8, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.tallas).grid(row=8, column=1)
        
        # Colores
        ttk.Label(self.root, text="Colores (códigos separados por coma):").grid(row=9, column=0, sticky=tk.W)
        ttk.Entry(self.root, textvariable=self.colores).grid(row=9, column=1)
        
        # Guardar
        ttk.Button(self.root, text="Guardar Producto", command=self.save_product).grid(row=10, column=1, sticky=tk.W)
    
    def save_product(self):
        sku = self.sku.get()
        nombre = self.nombre.get()
        descripcion_corta = self.descripcion_corta.get()
        peso = self.peso.get()
        longitud = self.longitud.get()
        anchura = self.anchura.get()
        altura = self.altura.get()
        categorias = self.categorias.get()
        tallas = self.tallas.get().split(',')
        colores = self.colores.get().split(',')
        
        data = []
        for talla in tallas:
            for color_code in colores:
                color_nombre = color_dict.get(color_code.strip(), "Desconocido")
                sku_variation = f"{sku}-{color_code.strip()}-{talla.strip()}"
                data.append([None, "variation", sku_variation, nombre, 1, 0, "visible", descripcion_corta, "", 
                             None, None, "", "", 1, 0, None, "", 0, peso, longitud, anchura, altura, 1, "", 
                             None, None, categorias, "", "", "", None, None, "", "", "", "", "", "", 0, "", 
                             "Talla", talla.strip(), 1, 1, "Color", color_nombre, 1, 1])
        
        columns = ['ID', 'Tipo', 'SKU', 'Nombre', 'Publicado', '¿Está destacado?',
                   'Visibilidad en el catálogo', 'Descripción corta', 'Descripción',
                   'Día en que empieza el precio rebajado', 'Día en que termina el precio rebajado', 'Estado del impuesto',
                   'Clase de impuesto', '¿Existencias?', 'Inventario', 'Cantidad de bajo inventario',
                   '¿Permitir reservas de productos agotados?', '¿Vendido individualmente?', 'Peso (kg)', 'Longitud (cm)',
                   'Anchura (cm)', 'Altura (cm)', '¿Permitir valoraciones de clientes?', 'Nota de compra',
                   'Precio rebajado', 'Precio normal', 'Categorías', 'Etiquetas', 'Clase de envío', 'Imágenes',
                   'Límite de descargas', 'Días de caducidad de la descarga', 'Superior', 'Productos agrupados',
                   'Ventas dirigidas', 'Ventas cruzadas', 'URL externa', 'Texto del botón', 'Posición',
                   'Woo Variation Gallery Images', 'Nombre del atributo 1', 'Valor(es) del atributo 1', 'Atributo visible 1',
                   'Atributo global 1', 'Nombre del atributo 2', 'Valor(es) del atributo 2', 'Atributo visible 2',
                   'Atributo global 2']
        
        df = pd.DataFrame(data, columns=columns)
        
        # Guardar en CSV
        df.to_csv("productos.csv", index=False)
        messagebox.showinfo("Guardar Producto", "Producto guardado exitosamente en productos.csv")

# Crear la aplicación
root = tk.Tk()
app = ProductEntryApp(root)
root.mainloop()

