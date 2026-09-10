import gradio as gr
import vtracer
import os
import tempfile
import requests

def vectorize_local(image_path, color_mode, mode, color_precision, max_iterations):
    if image_path is None:
        return None
    output_path = tempfile.mktemp(suffix=".svg")
    c_mode = 'color' if color_mode == 'Color' else 'bw'
    v_mode = 'spline' if mode == 'Curvas (Spline)' else 'polygon'
    
    try:
        vtracer.convert_image_to_svg_py(
            image_path,
            output_path,
            colormode=c_mode,
            hierarchical='stacked',
            mode=v_mode,
            filter_speckle=4,
            color_precision=int(color_precision),
            layer_difference=16,
            corner_threshold=60,
            length_threshold=4.0,
            max_iterations=int(max_iterations),
            splice_threshold=45,
            path_precision=8
        )
        return output_path, "✅ Trazado local completado (Modo offline)"
    except Exception as e:
        return None, f"❌ Error local: {e}"

def vectorize_vectorizer_ai(image_path, api_key):
    if not api_key:
        return None, "❌ Por favor, introduce tu API Key de Vectorizer.ai"
    if image_path is None:
        return None, "❌ Por favor, sube una imagen."
        
    output_path = tempfile.mktemp(suffix=".svg")
    
    try:
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://vectorizer.ai/api/v1/vectorize',
                files={'image': f},
                data={'mode': 'test'}, # Test mode for debugging if needed
                auth=('api_key', api_key)
            )
            
        if response.status_code == 200:
            with open(output_path, 'wb') as out_f:
                out_f.write(response.content)
            return output_path, "✅ ¡Vectorización con IA (Vectorizer.ai) completada con éxito!"
        else:
            return None, f"❌ Error de la API: {response.status_code} - {response.text}"
    except Exception as e:
        return None, f"❌ Error de conexión: {e}"

def vectorize_image(engine, image_path, color_mode, mode, color_precision, max_iterations, api_key):
    if engine == "Inteligencia Artificial (Vectorizer.ai) - Requiere API Key":
        return vectorize_vectorizer_ai(image_path, api_key)
    else:
        return vectorize_local(image_path, color_mode, mode, color_precision, max_iterations)

def toggle_api_key(engine):
    if engine == "Inteligencia Artificial (Vectorizer.ai) - Requiere API Key":
        return gr.update(visible=True), gr.update(visible=False)
    else:
        return gr.update(visible=False), gr.update(visible=True)

# Gradio Interface
with gr.Blocks(title="Vectorizador Pro") as demo:
    gr.Markdown("# 🎨 Vectorizador Pro (Local + IA)")
    gr.Markdown("Elige entre el **Motor Local (Gratis/Offline)** para trazado normal, o el **Motor de IA Avanzado** para resultados perfectos y nítidos en logos y textos.")
    
    with gr.Row():
        with gr.Column():
            input_image = gr.Image(type="filepath", label="Imagen Original")
            
            engine = gr.Radio(
                ["Trazado Local (Gratis / Offline)", "Inteligencia Artificial (Vectorizer.ai) - Requiere API Key"],
                value="Trazado Local (Gratis / Offline)",
                label="Motor de Vectorización"
            )
            
            # API Key settings for AI Engine
            with gr.Column(visible=False) as api_settings:
                gr.Markdown("ℹ️ *Vectorizer.ai usa modelos matemáticos profundos para adivinar fuentes y formas perfectas. Para usarlo aquí, necesitas pegar tu API Key.*")
                api_key = gr.Textbox(label="Vectorizer.ai API Key", type="password", placeholder="Pega aquí tu clave (Ej: vk_...)")
                
            # Local settings
            with gr.Accordion("Opciones (Motor Local)", open=False, visible=True) as local_settings:
                color_mode = gr.Radio(["Color", "Blanco y Negro"], value="Color", label="Modo de Color")
                mode = gr.Radio(["Curvas (Spline)", "Polígonos (Angular)"], value="Curvas (Spline)", label="Estilo de Trazado")
                color_precision = gr.Slider(minimum=1, maximum=10, value=6, step=1, label="Precisión de Color (Menor = Más colores)")
                max_iterations = gr.Slider(minimum=1, maximum=20, value=10, step=1, label="Iteraciones de Suavizado")
                
            btn = gr.Button("¡Vectorizar Imagen!", variant="primary")
            
        with gr.Column():
            status_text = gr.Markdown("Esperando imagen...")
            output_file = gr.File(label="Archivo SVG Generado")
            
    engine.change(
        fn=toggle_api_key,
        inputs=[engine],
        outputs=[api_settings, local_settings]
    )
            
    btn.click(
        fn=vectorize_image, 
        inputs=[engine, input_image, color_mode, mode, color_precision, max_iterations, api_key], 
        outputs=[output_file, status_text]
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)
