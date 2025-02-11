from flask import Flask, request
import os
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI
import threading
import time

# Configuración de variables
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = "asst_eocUon5DYKr6iDz7wYQKC2jd"

openai_client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

THREADS = {}

def preprocesar_mensaje(mensaje):
    if len(mensaje.strip()) == 0:
        return "Hola, ¿en qué puedo ayudarte?"
    return mensaje

def procesar_y_responder(from_number, incoming_msg):
    """
    Procesa el mensaje usando OpenAI y envía la respuesta a Twilio en segundo plano.
    """
    try:
        # Verificar si existe un hilo para el usuario, si no, crearlo
        if from_number not in THREADS:
            thread = openai_client.beta.threads.create()
            THREADS[from_number] = thread.id
        thread_id = THREADS[from_number]

        # Enviar el mensaje al asistente
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=incoming_msg
        )

        # Iniciar la ejecución del asistente
        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Esperar la respuesta del asistente (máximo 15 segundos por Twilio)
        start_time = time.time()
        while time.time() - start_time < 15:
            run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status in ["completed", "failed"]:
                break
            time.sleep(1)

        # Obtener la respuesta
        if run_status.status == "completed":
            messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
            respuesta = messages.data[0].content[0].text.value if messages.data else "No se pudo obtener una respuesta del asistente."
        else:
            respuesta = "Lo siento, no pude procesar tu solicitud en este momento."

        # Enviar la respuesta a Twilio
        try:
            from twilio.rest import Client
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            client.messages.create(
                from_='whatsapp:+573186952533',  # ✅ Tu número en producción
                to=from_number,
                body=respuesta
            )
            print(f"Respuesta enviada a {from_number}: {respuesta}")
        except Exception as twilio_error:
            print(f"Error al enviar mensaje a Twilio: {str(twilio_error)}")

    except Exception as e:
        print(f"Error procesando mensaje para {from_number}: {str(e)}")

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """
    Webhook para manejar mensajes de Twilio.
    """
    incoming_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "").strip()

    print(f"Mensaje recibido de {from_number}: {incoming_msg}")

    incoming_msg = preprocesar_mensaje(incoming_msg)

    # Respuesta inmediata a Twilio
    twilio_response = MessagingResponse()
    twilio_response.message("Estamos procesando tu solicitud, recibirás una respuesta pronto.")
    threading.Thread(target=procesar_y_responder, args=(from_number, incoming_msg)).start()

    return str(twilio_response)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
