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

def count_tokens(text):
    """Función para contar tokens en un mensaje usando OpenAI."""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.usage.total_tokens
    except Exception as e:
        print(f"Error contando tokens: {str(e)}")
        return 0

def preprocesar_mensaje(mensaje):
    if len(mensaje.strip()) == 0:
        return "Hola, ¿en qué puedo ayudarte?"
    return mensaje

def procesar_y_responder(from_number, incoming_msg):
    """
    Procesa el mensaje usando OpenAI y envía la respuesta a Twilio en segundo plano.
    """
    try:
        # Si el usuario ya tiene un Thread, revisamos cuántos mensajes tiene
        if from_number in THREADS:
            thread_id = THREADS[from_number]
            messages = openai_client.beta.threads.messages.list(thread_id=thread_id).data
            
            # Si el Thread ya tiene más de 10 mensajes, se crea uno nuevo
            if len(messages) >= 10:
                thread = openai_client.beta.threads.create()
                THREADS[from_number] = thread.id
                print(f"[INFO] Nuevo Thread creado para {from_number} debido a límite de mensajes.")
            else:
                print(f"[INFO] Usando Thread existente para {from_number}, Mensajes en el hilo: {len(messages)}")
        else:
            # Si el usuario no tiene un Thread, se crea uno nuevo
            thread = openai_client.beta.threads.create()
            THREADS[from_number] = thread.id
            print(f"[INFO] Nuevo Thread creado para {from_number}")

        thread_id = THREADS[from_number]

        # Contar tokens del mensaje
        tokens_input = count_tokens(incoming_msg)
        print(f"[INFO] Mensaje enviado al asistente ({tokens_input} tokens): {incoming_msg}")

        # Agregar mensaje del usuario al Thread
        openai_client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=incoming_msg
        )

        # Ejecutar el asistente en el Thread
        run = openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )

        # Esperar a que el asistente complete su ejecución
        while True:
            run_status = openai_client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
            if run_status.status in ["completed", "failed"]:
                break
            time.sleep(1)

        if run_status.status == "completed":
            messages = openai_client.beta.threads.messages.list(thread_id=thread_id)
            if messages.data:
                respuesta = messages.data[0].content[0].text.value
            else:
                respuesta = "No se pudo obtener una respuesta del asistente."
        else:
            respuesta = "Hubo un error procesando la solicitud."

        # Enviar la respuesta a Twilio
        from twilio.rest import Client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_='whatsapp:+573186952533',
            to=from_number,
            body=respuesta
        )

        print(f"[INFO] Respuesta enviada a {from_number}: {respuesta}")

    except Exception as e:
        print(f"[ERROR] Procesando mensaje para {from_number}: {str(e)}")
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
