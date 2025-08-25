import time
import requests
import sys
import webbrowser
from urllib.parse import urlparse
from plyer import notification

# ----- CONFIGURACIÓN FIJA -----
URL_BASE = 'https://coleccionalfaromeo.com.mx/'
EXPECTED_PATHS = ('/lander', '/lander/')
CHECK_INTERVAL_SECONDS = 60
REQUEST_TIMEOUT = 10
OPEN_BROWSER_ON_CHANGE = True   # True si quieres abrir navegador cuando cambie
ONCE_AND_EXIT = False           # True si quieres que detenga tras primera alerta
# -------------------------------

def get_path_from_url(u: str) -> str:
    try:
        parsed = urlparse(u)
        return parsed.path or '/'
    except Exception:
        return u

def notify_desktop(title: str, message: str):
    try:
        notification.notify(
            title=title,
            message=message,
            timeout=10
        )
    except Exception as e:
        print(f"[WARN] No se pudo mostrar notificación: {e}", file=sys.stderr)

def check_redirect() -> (bool, str):
    try:
        resp = requests.get(URL_BASE, allow_redirects=True, timeout=REQUEST_TIMEOUT)
        final_url = resp.url
        path = get_path_from_url(final_url)
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        if path not in EXPECTED_PATHS:
            print(f"[{timestamp}] ALERTA: ruta final '{path}' fuera de lo esperado {EXPECTED_PATHS}. URL final: {final_url}")
            return True, final_url
        else:
            print(f"[{timestamp}] OK: ruta final = '{path}', sigue redirigiendo a /lander.")
            return False, final_url
    except requests.exceptions.RequestException as e:
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] ERROR al consultar {URL_BASE}: {e}", file=sys.stderr)
        return False, None

def main():
    print("Iniciando monitor de redirección (modo fijo, sin argumentos)...")
    print(f"URL base: {URL_BASE}")
    print(f"Rutas esperadas: {EXPECTED_PATHS}")
    print(f"Intervalo: {CHECK_INTERVAL_SECONDS}s, Timeout HTTP: {REQUEST_TIMEOUT}s")
    print(f"Abrir navegador si cambia: {'Sí' if OPEN_BROWSER_ON_CHANGE else 'No'}")
    print(f"Detener tras primera alerta: {'Sí' if ONCE_AND_EXIT else 'No'}")
    print("Ctrl+C para detener manualmente.")
    estado_alertado = False

    try:
        while True:
            changed, final_url = check_redirect()
            if changed:
                if not estado_alertado:
                    notify_desktop(
                        title="Cambio en redirección detectado",
                        message=f"No redirige a /lander. URL final: {final_url or URL_BASE}"
                    )
                    if OPEN_BROWSER_ON_CHANGE:
                        target = final_url or URL_BASE
                        try:
                            webbrowser.open(target)
                            print(f"Abriendo navegador en: {target}")
                        except Exception as e:
                            print(f"[WARN] No se pudo abrir navegador: {e}", file=sys.stderr)
                    estado_alertado = True
                    if ONCE_AND_EXIT:
                        print("Deteniendo monitor tras detección (ONCE).")
                        break
            else:
                if estado_alertado:
                    print("La redirección volvió a /lander; se resetea estado de alerta.")
                estado_alertado = False
            time.sleep(CHECK_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nMonitor detenido por el usuario.")
    except Exception as ex:
        print(f"Error inesperado: {ex}", file=sys.stderr)

if __name__ == '__main__':
    main()
