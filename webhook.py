from flask import Flask, request
import os
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import time

# Configuración de variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_eocUon5DYKr6iDz7wYQKC2jd"

openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

# Diccionario para mantener los hilos de conversación por usuario
THREADS = {}

def preprocesar_mensaje(mensaje):
    """
    Preprocesa el mensaje para garantizar que no esté vacío y 
    devuelve un mensaje inicial si el usuario no escribe nada.
    """
    if len(mensaje.strip()) == 0:
        return "Hola, ¿en qué puedo ayudarte?"
    return mensaje

def responder_con_asistente(user_id, pregunta):
    """
    Lógica para manejar la interacción con OpenAI.
    """
    try:
        # Verifica si la pregunta contiene "buscando en mis documentos"
        if "buscando en mis documentos" in pregunta.lower():
            return "Estoy buscando en tus documentos. Por favor, espera un momento."

        # Crea un nuevo hilo si no existe para este usuario
        if user_id not in THREADS:
            thread = openai_client.beta.threads.create()
            THREADS[user_id] = thread.id
            print(f"Nuevo hilo creado para {user_id}: {THREADS[user_id]}")
        else:
            print(f"Hilo existente para {user_id}: {THREADS[user_id]}")

        thread_id = THREADS[user_id]

        # Mide el tiempo para generar la respuesta
        start_time = time.time()
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=pregunta
        )

        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        end_time = time.time()
        print(f"Tiempo para obtener respuesta de OpenAI: {end_time - start_time} segundos")

        # Espera la respuesta del asistente
        while True:
            run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status in ["completed", "failed"]:
                break

        if run_status.status == "completed":
            messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
            if messages.data:
                respuesta = messages.data[0].content[0].text.value
            else:
                respuesta = "No se pudo obtener una respuesta del asistente."
        else:
            respuesta = "Hubo un error procesando la solicitud."

        return respuesta

    except Exception as e:
        print(f"Error en el asistente: {str(e)}")
        return f"Error: {str(e)}"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """
    Webhook para manejar mensajes entrantes de WhatsApp.
    """
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "").strip()

    print(f"Mensaje recibido de {from_number}: {incoming_msg}")

    # Preprocesar mensaje
    incoming_msg = preprocesar_mensaje(incoming_msg)

    # Obtener respuesta del asistente
    respuesta = responder_con_asistente(from_number, incoming_msg)

    print(f"Respuesta generada para {from_number}: {respuesta}")

    # Crear respuesta para Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(respuesta)
    print(str(twilio_response))

    return str(twilio_response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
