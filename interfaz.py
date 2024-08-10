from flask import Flask, render_template
import subprocess

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ejecutar_genera_guias')
def ejecutar_genera_guias():
    try:
        subprocess.Popen(["python", "GeneraGuiasShein.py"])
        return "GeneraGuiasShein.py ejecutado correctamente."
    except Exception as e:
        return f"Error al ejecutar GeneraGuiasShein.py: {str(e)}"

@app.route('/ejecutar_guias')
def ejecutar_guias():
    try:
        subprocess.Popen(["python", "guias.py"])
        return "guias.py ejecutado correctamente."
    except Exception as e:
        return f"Error al ejecutar guias.py: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True)
