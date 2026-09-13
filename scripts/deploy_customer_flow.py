import os
import requests
import json
import time
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

WABA_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
if not TOKEN or TOKEN.startswith("EAAP...") or len(TOKEN) < 50:
    try:
        import subprocess
        TOKEN = subprocess.check_output(
            "gcloud secrets versions access latest --secret=WHATSAPP_ACCESS_TOKEN --project=cjs-designs-501004",
            shell=True, text=True
        ).strip()
    except Exception:
        pass

WABA_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or "1457897545971090"
BASE_URL = "https://graph.facebook.com/v22.0"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def build_customer_flow_json() -> dict:
    """Builds the WhatsApp Flow JSON for Customer Registration."""
    return {
        "version": "7.2",
        "screens": [
            {
                "id": "CUSTOMER_SCREEN",
                "title": "Add New Customer",
                "data": {
                    "init_name": {
                        "type": "string",
                        "__example__": ""
                    },
                    "init_phone": {
                        "type": "string",
                        "__example__": ""
                    },
                    "init_address": {
                        "type": "string",
                        "__example__": ""
                    }
                },
                "terminal": True,
                "layout": {
                    "type": "SingleColumnLayout",
                    "children": [
                        {
                            "type": "Form",
                            "name": "customer_form",
                            "init-values": {
                                "customer_name": "${data.init_name}",
                                "customer_phone": "${data.init_phone}",
                                "customer_address": "${data.init_address}"
                            },
                            "children": [
                                {
                                    "type": "TextHeading",
                                    "text": "Customer Registration"
                                },
                                {
                                    "type": "TextBody",
                                    "text": "Register a new client in CJS Google Sheets database."
                                },
                                {
                                    "type": "TextInput",
                                    "name": "customer_name",
                                    "label": "Customer / Boutique Name",
                                    "input-type": "text",
                                    "required": True
                                },
                                {
                                    "type": "TextInput",
                                    "name": "customer_phone",
                                    "label": "Phone Number",
                                    "input-type": "phone",
                                    "required": False
                                },
                                {
                                    "type": "TextInput",
                                    "name": "customer_address",
                                    "label": "Location / Address",
                                    "input-type": "text",
                                    "required": False
                                }
                            ]
                        },
                        {
                            "type": "Footer",
                            "label": "Save Customer",
                            "on-click-action": {
                                "name": "complete",
                                "payload": {
                                    "flow_type": "customer_registration",
                                    "customer_name": "${form.customer_name}",
                                    "customer_phone": "${form.customer_phone}",
                                    "customer_address": "${form.customer_address}"
                                }
                            }
                        }
                    ]
                }
            }
        ]
    }

def create_flow(name: str) -> str:
    print(f"1. Creating Draft Flow '{name}' on Meta WABA {WABA_ID}...")
    res = requests.post(
        f"{BASE_URL}/{WABA_ID}/flows",
        headers=HEADERS,
        data={
            "name": name,
            "categories": '["OTHER"]'
        }
    )
    if res.status_code != 200:
        print(f"Failed to create flow: {res.text}")
    res.raise_for_status()
    flow_id = res.json()["id"]
    print(f"-> Created Flow ID: {flow_id}")
    return flow_id

def upload_assets(flow_id: str, flow_json: dict):
    print("2. Uploading Customer Flow JSON Assets...")
    files = {
        "file": ("flow.json", json.dumps(flow_json), "application/json")
    }
    data = {
        "name": "flow.json",
        "asset_type": "FLOW_JSON"
    }
    res = requests.post(
        f"{BASE_URL}/{flow_id}/assets",
        headers=HEADERS,
        files=files,
        data=data
    )
    if res.status_code != 200:
        print(f"Upload error: {res.text}")
    res.raise_for_status()
    upload_data = res.json()
    print(f"-> Upload successful. Validation errors: {upload_data.get('validation_errors', [])}")

def publish_flow(flow_id: str):
    print("3. Publishing Customer Flow...")
    res = requests.post(
        f"{BASE_URL}/{flow_id}/publish",
        headers=HEADERS
    )
    if res.status_code != 200:
        print(f"Publish error: {res.text}")
    res.raise_for_status()
    print(f"-> Customer Flow {flow_id} published successfully!")

def deploy_customer_flow() -> str:
    flow_name = f"cjs_customer_intake_{int(time.time())}"
    flow_json = build_customer_flow_json()
    new_id = create_flow(flow_name)
    upload_assets(new_id, flow_json)
    publish_flow(new_id)
    
    # Save to Google Sheets Config tab
    try:
        from src.services.sheets import GoogleSheetsService
        db = GoogleSheetsService()
        db.set_config_variable("WhatsApp Customer Flow ID", new_id)
        print(f"-> Saved Customer Flow ID to Config sheet.")
    except Exception as e:
        print(f"Note: Could not save Customer Flow ID to Config sheet: {e}")

    print(f"\n==========================================")
    print(f"SUCCESS! New Customer Flow ID: {new_id}")
    print(f"==========================================")
    return new_id

if __name__ == "__main__":
    deploy_customer_flow()
