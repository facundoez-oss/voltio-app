from flask import Flask, request, jsonify, send_from_directory
import openai
import os

app = Flask(__name__, static_folder='static')
openai.api_key = os.environ.get("OPENAI_API_KEY")

CAMPOS_NUEVO = ['fecha', 'cliente', 'ubicacion', 'caja', 'caracteristicas', 'localizacion', 'incidencia', 'observaciones', 'recomendaciones']
CAMPOS_EXISTENTE = ['nro_tarea', 'fecha', 'observaciones', 'recomendaciones', 'tareas_pendientes']

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/interpretar', methods=['POST'])
def interpretar():
    data = request.json
    texto = data.get('texto', '')
    tipo = data.get('tipo', 'nuevo')

    campos = CAMPOS_NUEVO if tipo == 'nuevo' else CAMPOS_EXISTENTE
    labels = {
        'fecha': 'Fecha', 'cliente': 'Cliente', 'ubicacion': 'Ubicación',
        'caja': 'Caja', 'caracteristicas': 'Características', 'localizacion': 'Localización',
        'incidencia': 'Incidencia', 'observaciones': 'Observaciones',
        'recomendaciones': 'Recomendaciones', 'nro_tarea': 'Nro. tarea',
        'tareas_pendientes': 'Tareas pendientes'
    }
    lista = ', '.join([labels[c] for c in campos])

    if tipo == 'nuevo':
        descripcion_campos = """- fecha: fecha del trabajo
- cliente: nombre del cliente
- ubicacion: dirección o lugar donde se hizo el trabajo
- caja: tipo de tablero o caja eléctrica
- caracteristicas: características técnicas del sistema eléctrico (monofásico, trifásico, voltaje, potencia, etc)
- localizacion: lugar dentro de la propiedad donde está la caja (garage, planta baja, primer piso, etc)
- incidencia: problema o falla que se encontró
- observaciones: lo que se hizo para solucionar el problema
- recomendaciones: sugerencias para el futuro"""
    else:
        descripcion_campos = """- nro_tarea: número de tarea o parte (si dice "Parte 342" el valor es 342)
- fecha: fecha del trabajo
- observaciones: lo que se realizó o completó en el trabajo
- recomendaciones: sugerencias para el futuro o próximos pasos a largo plazo
- tareas_pendientes: trabajos que quedaron sin terminar o que hay que hacer próximamente"""

    prompt = f"""Sos un asistente para un electricista. Extraé los campos de este texto.
Tipo de parte: {'PARTE NUEVO' if tipo == 'nuevo' else 'PARTE EXISTENTE'}.

Campos a extraer con su significado:
{descripcion_campos}

Texto del electricista:
"{texto}"

Respondé SOLO con un objeto JSON válido. Sin backticks, sin texto adicional.
Si un campo no se menciona, dejá el valor como null.
Formato: {{"fecha":"...","cliente":"...",...}}"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024
        )
        resultado = response.choices[0].message.content
        resultado = resultado.replace("```json", "").replace("```", "").strip()
        import json
        data_parsed = json.loads(resultado)
        return jsonify(data_parsed)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/transcribir', methods=['POST'])
def transcribir():
    try:
        audio = request.files.get('audio')
        if not audio:
            return jsonify({"error": "No se recibió audio"}), 400

        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio.read(), "audio/webm"),
            language="es"
        )
        return jsonify({"texto": transcript.text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)