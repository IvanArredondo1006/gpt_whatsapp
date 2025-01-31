from flask import Flask, request
import os
from twilio.twiml.messaging_response import MessagingResponse
from openai import OpenAI

# Crear la aplicación Flask
app = Flask(__name__)

# Configurar las credenciales desde las variables de entorno
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configura el cliente de OpenAI
openai_client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    """
    Webhook para manejar mensajes de WhatsApp
    """
    # Recibe el mensaje del usuario
    incoming_msg = request.values.get("Body", "").strip()

    # Responder con ChatGPT
    try:
        # Enviar mensaje a OpenAI (ChatGPT)
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",  # Cambia a "gpt-3.5-turbo" si es necesario
            messages=[{"role": "user", "content": incoming_msg}]
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = f"Hubo un error procesando tu mensaje: {str(e)}"

    # Crear respuesta para Twilio
    twilio_response = MessagingResponse()
    twilio_response.message(reply)

    return str(twilio_response)

if __name__ == "__main__":
    # Ejecutar la aplicación Flask
    app.run(host="0.0.0.0", port=5000, debug=True)
