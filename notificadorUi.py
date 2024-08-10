import tkinter as tk
from tkinter import messagebox
import pywhatkit
import datetime

def enviar_mensaje():
    mensaje = mensaje_entry.get()
    numero_whatsapp = numero_entry.get()
    hora_envio = hora_entry.get()
    minuto_envio = minuto_entry.get()

    try:
        hora_envio = int(hora_envio)
        minuto_envio = int(minuto_envio)

        if 0 <= hora_envio <= 23 and 0 <= minuto_envio <= 59:
            hora_actual = datetime.datetime.now().hour
            minuto_actual = datetime.datetime.now().minute

            if hora_actual < hora_envio or (hora_actual == hora_envio and minuto_actual < minuto_envio):
                pywhatkit.sendwhatmsg(numero_whatsapp, mensaje, hora_envio, minuto_envio)
            else:
                pywhatkit.sendwhatmsg(numero_whatsapp, mensaje, hora_envio, minuto_envio, wait_time=60)
        else:
            messagebox.showerror("Error", "Por favor, introduce una hora y minutos válidos (0-23 para la hora y 0-59 para los minutos).")
    except ValueError:
        messagebox.showerror("Error", "Por favor, introduce valores numéricos para la hora y minutos.")

# Crear la ventana principal
root = tk.Tk()
root.title("Envío de Mensaje por WhatsApp")

# Crear los widgets de la interfaz
mensaje_label = tk.Label(root, text="Mensaje:")
mensaje_label.grid(row=0, column=0, padx=5, pady=5, sticky="e")
mensaje_entry = tk.Entry(root, width=50)
mensaje_entry.grid(row=0, column=1, columnspan=2, padx=5, pady=5)

numero_label = tk.Label(root, text="Número de Teléfono:")
numero_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
numero_entry = tk.Entry(root, width=20)
numero_entry.grid(row=1, column=1, padx=5, pady=5)

hora_label = tk.Label(root, text="Hora de Envío (0-23):")
hora_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
hora_entry = tk.Entry(root, width=5)
hora_entry.grid(row=2, column=1, padx=5, pady=5)

minuto_label = tk.Label(root, text="Minuto de Envío (0-59):")
minuto_label.grid(row=2, column=2, padx=5, pady=5, sticky="e")
minuto_entry = tk.Entry(root, width=5)
minuto_entry.grid(row=2, column=3, padx=5, pady=5)

enviar_button = tk.Button(root, text="Enviar Mensaje", command=enviar_mensaje)
enviar_button.grid(row=3, column=0, columnspan=4, padx=5, pady=5)

# Ejecutar la aplicación
root.mainloop()
