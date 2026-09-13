import requests
import json

payload = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "918289897413",
                                "type": "interactive",
                                "interactive": {
                                    "type": "nfm_reply",
                                    "nfm_reply": {
                                        "response_json": json.dumps({
                                            "customer_select": "Joy Alukkas",
                                            "order_type_select": "Machine Embroidery",
                                            "template_select": "Baptism",
                                            "quantity": 1,
                                            "delivery_date": "2026-09-17",
                                            "stitch_count": 15000,
                                            "labor_minutes": 20,
                                            "photo_picker": [
                                                {
                                                    "id": "2515108385668095",
                                                    "mime_type": "image/jpeg",
                                                    "file_name": "test_design.jpg"
                                                }
                                            ]
                                        })
                                    }
                                }
                            }
                        ]
                    }
                }
            ]
        }
    ]
}

print("Sending simulated form submission WITH PHOTO to live Cloud Run...")
r = requests.post("https://cjs-agent-225021995719.us-central1.run.app/webhook", json=payload, timeout=25)
print("Response:", r.status_code, r.text)
