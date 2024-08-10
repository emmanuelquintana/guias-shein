from bs4 import BeautifulSoup
import requests

# URL de la página web a scrapear
url = 'https://sellerhub.shein.com/#/gsp/order-management/list'

# Realiza la solicitud GET a la página web
response = requests.get(url)

# Imprime el código de estado de la respuesta (200 significa éxito)
print("Código de estado:", response.status_code)

# Imprime el contenido de la respuesta para verificar que se haya obtenido correctamente
print("Contenido de la respuesta:", response.text)

# Parsea el HTML
soup = BeautifulSoup(response.text, 'html.parser')

# Encuentra los elementos relevantes en la página web y extrae los datos
pedidos = soup.find_all('div', class_='order-detail')
for pedido in pedidos:
    codigo_seguimiento = pedido.find('div', string='Código de seguimiento').find_next_sibling('div').get_text()
    # Extrae más datos aquí...
    
    # Imprime los datos en la consola
    print("Código de seguimiento:", codigo_seguimiento)
    # Imprime más datos aquí...
