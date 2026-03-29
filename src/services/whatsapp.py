import os
import requests

class WhatsAppService:
    def __init__(self):
        self.phone_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        self.token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        self.base_url = f"https://graph.facebook.com/v22.0/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def send_text_message(self, recipient_number: str, message: str):
        """Sends a freeform text message back to the customer/Siny."""
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": "text",
            "text": {
                "body": message
            }
        }
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            print(f"[WhatsApp] Sent message to {recipient_number}: {response.status_code}")
            return True
        except Exception as e:
            print(f"[WhatsApp] Failed to send message: {e}")
            return False
