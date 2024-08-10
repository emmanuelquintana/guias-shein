import pywhatkit
import datetime

# Definir la función para enviar el mensaje
def enviar_mensaje_whatsapp(numero, mensaje, hora, minuto):
    pywhatkit.sendwhatmsg(numero, mensaje, hora, minuto)

# Obtener la hora actual
hora_actual = datetime.datetime.now().hour
minuto_actual = datetime.datetime.now().minute

# Definir el mensaje y el número de teléfono
mensaje = "¡Hola! Ceci Buenos dias , ya te pase shein."
numero_whatsapp = "+5215528495314"  # Reemplaza esto con el número de teléfono al que quieres enviar el mensaje

# Calcular la hora de envío (8:00 AM)
hora_envio = 8
minuto_envio = 1

# Calcular la diferencia de tiempo para enviar el mensaje
if hora_actual < hora_envio or (hora_actual == hora_envio and minuto_actual < minuto_envio):
    # Si es antes de las 8:00 AM, enviar el mensaje para hoy
    enviar_mensaje_whatsapp(numero_whatsapp, mensaje, hora_envio, minuto_envio)
else:
    # Si es después de las 8:00 AM, enviar el mensaje para mañana
    enviar_mensaje_whatsapp(numero_whatsapp, mensaje, hora_envio, minuto_envio)
