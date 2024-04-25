from concurrent.futures import ThreadPoolExecutor
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random

def visita(veces, tiempo_min, tiempo_max):
    # Inicializar el navegador
    browser = webdriver.Chrome()
    try:
        # Navegar a la página web de Google
        browser.get("https://www.google.com/")

        # Buscar el campo de búsqueda y enviar la palabra clave
        search_bar = WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.NAME, "q")))
        search_bar.send_keys("AUTOCLAVE CRISTOFOLI")

        # Enviar la tecla "Enter"
        search_bar.send_keys(Keys.RETURN)

        # Esperar a que la página cargue y obtener el primer resultado
        first_result= WebDriverWait(browser, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href='https://www.equiposonrie.com/product-page/autoclave-cristofoli-vitale-21-class-cd']")))
        first_result.click()

        # Esperar a que la página de equiposonrie.com cargue
        WebDriverWait(browser, 10).until(EC.title_contains("equiposonrie"))

        # Permanecer en la página durante un tiempo aleatorio entre tiempo_min y tiempo_max
        tiempo_aleatorio = random.randint(tiempo_min, tiempo_max)
        print(f"Permaneciendo en la página durante {tiempo_aleatorio} segundos")
        time.sleep(tiempo_aleatorio)

    except Exception as e:
        print(e)
    finally:
        browser.quit()

    # Llamar a la función visita de nuevo si queda más de una vez por ejecutar
    if veces > 1:
        visita(veces-1, tiempo_min, tiempo_max)

# Cantidad de veces que se repetirá la visita
veces = int(input("Ingrese la cantidad de veces que desea visitar el sitio web: "))

# Cantidad de visitas a realizar en paralelo
cantidad = int(input("Ingrese la cantidad de visitas a realizar en paralelo: "))

# Tiempo mínimo y máximo para permanecer en la página
tiempo_min = int(input("Ingrese el tiempo mínimo en segundos para permanecer en la página: "))
tiempo_max = int(input("Ingrese el tiempo máximo en segundos para permanecer en la página: "))

scroll = 4

with ThreadPoolExecutor(max_workers=cantidad) as executor:
    # Ejecutar las visitas en paralelo
    executor.map(visita, [veces] * cantidad, [tiempo_min] * cantidad, [tiempo_max] * cantidad)
