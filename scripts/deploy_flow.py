import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

WABA_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
BASE_URL = "https://graph.facebook.com/v22.0"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

FLOW_JSON = {
    "version": "7.2",
    "screens": [
        {
            "id": "ORDER_SCREEN",
            "title": "CJS Order Details",
            "data": {},
            "terminal": True,
            "layout": {
                "type": "SingleColumnLayout",
                "children": [
                    {
                        "type": "Form",
                        "name": "order_form",
                        "children": [
                            {
                                "type": "TextHeading",
                                "text": "New Embroidery Order"
                            },
                            {
                                "type": "TextInput",
                                "name": "customer_name",
                                "label": "Customer Name",
                                "required": True
                            },
                            {
                                "type": "Dropdown",
                                "name": "fabric_type",
                                "label": "Fabric Type",
                                "required": True,
                                "data-source": [
                                    {"id": "Cotton", "title": "Cotton"},
                                    {"id": "Silk", "title": "Silk"},
                                    {"id": "Net", "title": "Net"},
                                    {"id": "Velvet", "title": "Velvet"},
                                    {"id": "Other", "title": "Other"}
                                ]
                            },
                            {
                                "type": "TextInput",
                                "name": "garment_type",
                                "label": "Garment (e.g. Kurty, Saree)",
                                "required": True
                            },
                            {
                                "type": "Dropdown",
                                "name": "embroidery_style",
                                "label": "Embroidery Style",
                                "required": True,
                                "data-source": [
                                    {"id": "Floral", "title": "Floral"},
                                    {"id": "Name", "title": "Name"},
                                    {"id": "Geometric", "title": "Geometric"},
                                    {"id": "Outline", "title": "Outline"},
                                    {"id": "Other", "title": "Other"}
                                ]
                            },
                            {
                                "type": "TextInput",
                                "name": "stitch_count",
                                "label": "Stitch Count",
                                "input-type": "number",
                                "required": True
                            },
                            {
                                "type": "TextInput",
                                "name": "hours_required",
                                "label": "Hours Required (Labor)",
                                "input-type": "number",
                                "required": True
                            },
                            {
                                "type": "DatePicker",
                                "name": "delivery_date",
                                "label": "Expected Delivery Date",
                                "required": True
                            }
                        ]
                    },
                    {
                        "type": "Footer",
                        "label": "Submit Order",
                        "on-click-action": {
                            "name": "complete",
                            "payload": {
                                "customer_name": "${form.customer_name}",
                                "fabric_type": "${form.fabric_type}",
                                "garment_type": "${form.garment_type}",
                                "embroidery_style": "${form.embroidery_style}",
                                "stitch_count": "${form.stitch_count}",
                                "hours_required": "${form.hours_required}",
                                "delivery_date": "${form.delivery_date}"
                            }
                        }
                    }
                ]
            }
        }
    ]
}

def create_flow():
    print("1. Creating Draft Flow...")
    res = requests.post(
        f"{BASE_URL}/{WABA_ID}/flows",
        headers=HEADERS,
        data={
            "name": "cjs_order_form",
            "categories": '["OTHER"]'
        }
    )
    if res.status_code != 200:
        # Flow might already exist with this name, try appending timestamp
        import time
        res = requests.post(
            f"{BASE_URL}/{WABA_ID}/flows",
            headers=HEADERS,
            data={
                "name": f"cjs_order_form_{int(time.time())}",
                "categories": '["OTHER"]'
            }
        )
    res.raise_for_status()
    flow_id = res.json()["id"]
    print(f"-> Created Flow ID: {flow_id}")
    return flow_id

def upload_assets(flow_id: str):
    print("2. Uploading Flow JSON Assets...")
    
    # We need to send multipart/form-data
    files = {
        "file": ("flow.json", json.dumps(FLOW_JSON), "application/json")
    }
    data = {
        "name": "flow.json",
        "asset_type": "FLOW_JSON"
    }
    # Uploading assets is slightly different
    # POST /{flow_id}/assets
    res = requests.post(
        f"{BASE_URL}/{flow_id}/assets",
        headers=HEADERS,
        files=files,
        data=data
    )
    
    if res.status_code != 200:
        print(res.text)
    res.raise_for_status()
    print("-> Upload successful.")

def publish_flow(flow_id: str):
    print("3. Publishing Flow...")
    res = requests.post(
        f"{BASE_URL}/{flow_id}/publish",
        headers=HEADERS
    )
    if res.status_code != 200:
        print(res.text)
    res.raise_for_status()
    print("-> Flow published successfully!")

if __name__ == "__main__":
    try:
        flow_id = create_flow()
        upload_assets(flow_id)
        publish_flow(flow_id)
        print(f"\nSUCCESS! Save this FLOW_ID to your .env file: \nFLOW_ID={flow_id}")
    except Exception as e:
        print(f"Failed: {e}")
