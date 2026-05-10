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
        """Sends a freeform text message back to the customer/Boss."""
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
    def send_flow_message(self, recipient_number: str, flow_id: str, message_text: str = "Please fill out the form below to proceed:"):
        """Sends an interactive WhatsApp Flow message."""
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_number,
            "type": "interactive",
            "interactive": {
                "type": "flow",
                "header": {
                    "type": "text",
                    "text": "Order Creation"
                },
                "body": {
                    "text": message_text
                },
                "footer": {
                    "text": "CJS Designs"
                },
                "action": {
                    "name": "flow",
                    "parameters": {
                        "flow_message_version": "3",
                        "flow_token": "CJS_ORDER_FLOW",
                        "flow_id": flow_id,
                        "flow_cta": "Open Form",
                        "flow_action": "navigate",
                        "flow_action_payload": {
                            "screen": "ORDER_SCREEN"
                        }
                    }
                }
            }
        }
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            print(f"[WhatsApp] Sent flow message to {recipient_number}: {response.status_code}")
            return True
        except Exception as e:
            print(f"[WhatsApp] Failed to send flow message: {e}")
            if hasattr(e, 'response') and e.response:
                print(f"[WhatsApp] Error detail: {e.response.text}")
            return False
    def download_media(self, media_id: str):
        """
        Resolves and downloads a WhatsApp media file (e.g. voice note) by its media_id.
        Returns (bytes, mime_type) tuple, or (None, None) on failure.

        Step 1: GET /{media_id} → returns a JSON with a 'url' field
        Step 2: GET that url → returns raw audio bytes
        """
        try:
            headers = {"Authorization": f"Bearer {self.token}"}
            
            # Step 1: Resolve media URL
            meta_url = f"https://graph.facebook.com/v22.0/{media_id}"
            meta_resp = requests.get(meta_url, headers=headers)
            meta_resp.raise_for_status()
            media_info = meta_resp.json()
            
            download_url = media_info.get("url")
            mime_type = media_info.get("mime_type", "audio/ogg")
            
            if not download_url:
                print(f"[WhatsApp] No download URL returned for media_id {media_id}")
                return None, None

            # Step 2: Download the actual audio bytes
            audio_resp = requests.get(download_url, headers=headers)
            audio_resp.raise_for_status()
            
            print(f"[WhatsApp] Downloaded {len(audio_resp.content)} bytes of audio ({mime_type})")
            return audio_resp.content, mime_type

        except Exception as e:
            print(f"[WhatsApp] Media download failed for {media_id}: {e}")
            return None, None
