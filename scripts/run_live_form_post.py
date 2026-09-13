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
                                            "customer_select": "Ammu",
                                            "order_type_select": "Machine Embroidery",
                                            "template_select": "Shirt Logo",
                                            "quantity": 1,
                                            "delivery_date": "2026-09-15",
                                            "stitch_count": 3000,
                                            "labor_minutes": 10,
                                            "photo_picker": []
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

print("Sending simulated form submission to live Cloud Run...")
r = requests.post("https://cjs-agent-225021995719.us-central1.run.app/webhook", json=payload, timeout=20)
print("Response:", r.status_code, r.text)
