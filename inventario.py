import pandas as pd

# Cargar los archivos CSV en DataFrames
df_a = pd.read_csv('archivo_a.csv')
df_b = pd.read_csv('archivo_b.csv')

# Combinar los DataFrames utilizando las columnas 'Variant SKU' y 'seller-sku'
df_merged = pd.merge(df_a, df_b, left_on='Variant SKU', right_on='seller-sku', how='left')

# Crear un registro de productos no encontrados en el archivo A
productos_no_encontrados = []

# Actualizar las cantidades y manejar productos no encontrados
for index, row in df_merged.iterrows():
    if pd.notna(row['Quantity Available']):
        sku = row['Variant SKU']
        old_qty = df_a.loc[df_a['Variant SKU'] == sku, 'Variant Inventory Qty'].values[0]
        new_qty = row['Quantity Available']
        if old_qty != new_qty:
            df_a.loc[df_a['Variant SKU'] == sku, 'Variant Inventory Qty'] = new_qty
            print(f"Inventario actualizado para SKU {sku}: {old_qty} -> {new_qty}")
    elif pd.notna(row['seller-sku']):
        productos_no_encontrados.append(row['seller-sku'])

# Guardar el DataFrame actualizado en un nuevo archivo CSV (archivo_c.csv)
df_a.to_csv('shopify.csv', index=False)

# Imprimir los productos no encontrados en el archivo A
if productos_no_encontrados:
    print("\nProductos no encontrados en el archivo A:")
    for producto in productos_no_encontrados:
        print(producto)
else:
    print("\nTodos los productos fueron procesados exitosamente.")

print("\nProceso completado. Archivo C generado.")