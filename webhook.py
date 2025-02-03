from flask import Flask, request
import os
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import time

# 🔹 Reemplaza estos valores con tus credenciales o usa variables de entorno en Railway
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_eocUon5DYKr6iDz7wYQKC2jd"  # 🔴 Reemplaza con tu Assistant ID real

# Configurar el cliente de OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Crear la aplicación Flask
app = Flask(__name__)

# Diccionario para almacenar las conversaciones por usuario
THREADS = {}

def responder_con_asistente(user_id, pregunta):
    """
    Envía una pregunta al asistente de OpenAI y obtiene la respuesta.
    """
    try:
        # Si el usuario no tiene un hilo de conversación, crear uno nuevo
        if user_id not in THREADS:
            thread = openai_client.beta.threads.create()
            THREADS[user_id] = thread.id  # Guarda el ID del hilo para este usuario

        thread_id = THREADS[user_id]

        # Agregar el mensaje del usuario al hilo
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=pregunta
        )

        # Ejecutar el asistente en el hilo
        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Esperar a que el asistente procese la respuesta
        while True:
            run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status in ["completed", "failed"]:
                break
            time.sleep(1)  # Espera 1 segundo antes de revisar nuevamente

        if run_status.status == "completed":
            # Obtener la respuesta del asistente
            messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
            respuesta = messages.data[0].content[0].text.value  # Extraer la respuesta del asistente
            return respuesta
        else:
            return "Hubo un error procesando la solicitud."
    
    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """
    Webhook para manejar mensajes de WhatsApp desde Twilio.
    """
    # Obtener el mensaje del usuario y su número de WhatsApp
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "").strip()

    # Responder con el asistente de OpenAI
    respuesta = responder_con_asistente(from_number, incoming_msg)

    # Crear respuesta para Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(respuesta)

    return str(twilio_response)

if __name__ == "__main__":
    # Ejecutar la aplicación Flask
    app.run(host="0.0.0.0", port=5000, debug=True)
