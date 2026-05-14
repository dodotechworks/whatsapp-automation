import requests
import os
from dotenv import load_dotenv

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

def send_whatsapp_message(phone, message):

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {
            "body": message
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    return response.json()

def send_button_message(phone, body_text, buttons):

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    button_items = []

    for button in buttons:
        button_items.append({
            "type": "reply",
            "reply": {
                "id": button["id"],
                "title": button["title"]
            }
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": button_items
            }
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    return response.json()

def send_service_list_message(phone, body_text, services):

    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    rows = []

    for service in services:
        rows.append({
            "id": f"service_{service.id}",
            "title": service.title[:24],
            "description": service.description[:72] if service.description else ""
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": body_text
            },
            "action": {
                "button": "Choose Service",
                "sections": [
                    {
                        "title": "Available Services",
                        "rows": rows
                    }
                ]
            }
        }
    }

    response = requests.post(
        url,
        headers=headers,
        json=payload
    )

    return response.json()