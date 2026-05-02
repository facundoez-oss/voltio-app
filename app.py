from flask import Flask, request, jsonify, send_from_directory
import openai
import os

app = Flask(__name__, static_folder='static')
openai.api_key = os.environ.get("OPENAI_API_KEY")

CAMPOS_NUEVO = ['fecha', 'cliente', 'direccion', 'ubicacion', 'caja', 'caracteristicas', 'localizacion', 'incidencia', 'observaciones', 'recomendaciones']
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
        'fecha': 'Fecha', 'cliente': 'Cliente', 'direccion': 'Dirección', 'ubicacion': 'Ubicación',
        'caja': 'Caja', 'caracteristicas': 'Características', 'localizacion': 'Localización',
        'incidencia': 'Incidencia', 'observaciones': 'Observaciones',
        'recomendaciones': 'Recomendaciones', 'nro_tarea': 'Nro. tarea',
        'tareas_pendientes': 'Tareas pendientes'
    }
    lista = ', '.join([labels[c] for c in campos])

    if tipo == 'nuevo':
        descripcion_campos = """- fecha: fecha del trabajo en formato DD/MM/YYYY (ejemplo: 12/04/2026)
- cliente: SOLO nombre y apellido de la persona (ejemplo: "Julio Pérez", "María González"). IMPORTANTE: si el electricista dice frases como "fui a lo de Julio", "estuve en lo de Pérez", "trabajé donde Martínez", extraé SOLO el nombre/apellido (Julio, Pérez, Martínez). NO incluyas palabras como "fui", "fiel", "lo de", "a lo de", etc. Si no se menciona claramente un nombre de persona, dejá null.
- direccion: dirección física del lugar donde se hizo el trabajo (calle, número, barrio, ejemplo: "Bulevar España 2340", "Av. Italia 1500")
- ubicacion: lugar dentro de la propiedad donde se hizo la tarea o donde está la falla (ejemplos: "garage", "cuarto principal", "taller", "cocina", "sótano")
- caja: tipo de tablero o caja eléctrica
- caracteristicas: detalle del equipo o componentes que hay (o que se van a instalar) en esa localización. NO son características técnicas como voltaje o trifásico. Son los componentes físicos. Ejemplos: "1 plaqueta de llave para 3 módulos, 1 módulo Schuko, 1 módulo universal", "casquete con lámpara LED 12W", "interruptor doble + toma corriente"
- localizacion: el punto exacto dentro de la ubicación donde está la falla o donde se trabaja. Especifica QUÉ es y DÓNDE está dentro de la ubicación. Ejemplos: "casquete centro techo", "caja de interruptor de luz pared norte", "torre este pared norte", "armario centro pared oeste", "toma corriente parte inferior pared sur"
- incidencia: lo que el cliente reporta o solicita (el desperfecto que dice que tiene o la instalación que pide). Es lo que dice el cliente, NO el diagnóstico técnico del electricista. Ejemplos: "no funciona la luz", "no anda el toma corriente", "instalación de tablero nuevo", "adicionar tomas en el living"
- observaciones: detalle de lo que el electricista hizo en esa asistencia/visita específica. Es el trabajo concreto realizado ese día. Ejemplos: "desmonte, relevamiento, localización de falla en toma corriente", "acopio de materiales y costos del material retirado", "desconexión, recambio de módulo, colocación de plaqueta, armado, conectado, probado funcionando correctamente"
- recomendaciones: sugerencias para el futuro"""
    else:
        descripcion_campos = """- nro_tarea: número de tarea o parte (si dice "Parte 342" el valor es 342)
- fecha: fecha del trabajo en formato DD/MM/YYYY (ejemplo: 12/04/2026)
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
@app.route('/corregir-campo', methods=['POST'])
def corregir_campo():
    try:
        data = request.json
        campo = data.get('campo', '')
        valor_actual = data.get('valor_actual', '')
        texto = data.get('texto', '')
        labels = {
            'fecha': 'fecha del trabajo en formato DD/MM/YYYY',
            'cliente': 'nombre y apellido de la persona (solo el nombre, sin frases tipo "fui a lo de")',
            'direccion': 'dirección física del lugar (calle y número)',
            'ubicacion': 'lugar dentro de la propiedad donde se hace la tarea o está la falla (garage, taller, cuarto, etc)',
            'caja': 'tipo de tablero o caja eléctrica',
            'caracteristicas': 'detalle de los componentes o equipo que hay en la localización (ej: 1 plaqueta llave 3 módulos, 1 módulo Schuko)',
            'localizacion': 'punto exacto dentro de la ubicación, qué es y dónde está (ej: casquete centro techo, torre este pared norte)',
            'incidencia': 'lo que el cliente reporta o solicita (no el diagnóstico técnico)',
            'observaciones': 'lo que hizo el electricista en esa asistencia específica',
            'recomendaciones': 'sugerencias para el futuro',
            'nro_tarea': 'número de tarea o parte',
            'tareas_pendientes': 'trabajos que quedaron pendientes'
        }

        descripcion = labels.get(campo, campo)

        prompt = f"""Sos un asistente para un electricista. Tu tarea es corregir el valor de un campo específico.

Campo a corregir: "{descripcion}"
Valor actual del campo: "{valor_actual}"
Lo que dijo el electricista para corregirlo: "{texto}"

Reglas importantes:
- Si el electricista dice que una letra va con otra (ej: "va con z no con s"), corregí ESA letra en la palabra correspondiente
- Si menciona varias correcciones en una sola frase, aplicá TODAS las correcciones juntas al valor final
- Devolvé SOLO el valor final corregido y completo, sin explicaciones
- No inventes información, solo corregí lo que pidió

Ejemplos:
- Valor actual: "Fabricio Greco", dice "Fabricio va con z y Greco con doble c" → devolvés: "Fabrizio Grecco"
- Valor actual: "21 de abril", dice "es el 22 no el 21" → devolvés: "22/04/2026"
- Valor actual: "", dice "es Rivera 1250" → devolvés: "Rivera 1250"

Devolvé SOLO el valor corregido:"""

        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100
        )
        valor_corregido = response.choices[0].message.content.strip()
        return jsonify({"valor": valor_corregido})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)