from flask import Flask, request
import os
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import openai


# Crear la aplicación Flask
app = Flask(__name__)

# Configura las credenciales desde las variables de entorno
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configura el cliente de Twilio y OpenAI
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
openai.api_key = OPENAI_API_KEY

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """
    Webhook para manejar mensajes de WhatsApp
    """
    # Recibe el mensaje del usuario
    incoming_msg = request.values.get('Body', '').strip()
    from_number = request.values.get('From', '')

    # Responder con ChatGPT
    try:
        # Enviar mensaje a OpenAI (ChatGPT)
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": incoming_msg}]
        )
        reply = response["choices"][0]["message"]["content"]
    except Exception as e:
        reply = f"Hubo un error procesando tu mensaje: {str(e)}"

    # Crear respuesta para Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(reply)

    return str(twilio_response)

if __name__ == "__main__":
    # Ejecutar la aplicación Flask
    app.run(host="0.0.0.0", port=5000, debug=True)
