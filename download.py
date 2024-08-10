import requests
from bs4 import BeautifulSoup
import os

# Función para descargar un recurso dado su URL
def descargar_recurso(url, directorio):
    nombre_archivo = os.path.join(directorio, url.split("/")[-1])
    with open(nombre_archivo, 'wb') as archivo:
        response = requests.get(url)
        archivo.write(response.content)

# Función para extraer enlaces de recursos multimedia de una página web
def extraer_enlaces_multimedia(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    enlaces_multimedia = []
    for elemento in soup.find_all('a'):
        href = elemento.get('href')
        if href and '/cdn2/' in href:
            enlaces_multimedia.append(href)
    return enlaces_multimedia

# URL de la página web
url_pagina = 'https://onlyfans.com/lady_dusha666'

# Directorio donde se guardarán los archivos multimedia
directorio_destino = r'H:\Backup octubre 2023\Doocs\Lady dusha'

# Crear el directorio si no existe
os.makedirs(directorio_destino, exist_ok=True)

# Extraer enlaces de recursos multimedia de la página web
enlaces_multimedia = extraer_enlaces_multimedia(url_pagina)

# Descargar cada recurso multimedia
for enlace in enlaces_multimedia:
    descargar_recurso(enlace, directorio_destino)
