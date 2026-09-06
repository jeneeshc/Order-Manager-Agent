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
BASE_URL = "https://graph.facebook.com/v22.0"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}

def build_flow_json() -> dict:
    """Builds the WhatsApp Flow JSON dynamically from Google Sheets data."""
    from src.services.sheets import GoogleSheetsService
    sheets = GoogleSheetsService()
    
    # 1. Customer Options (strictly existing customers)
    customers_list = sheets.get_all_customers_list() or []
    customer_options = []
    for c in customers_list:
        clean = str(c).strip()
        if clean:
            customer_options.append({"id": clean, "title": clean[:30]})
    if not customer_options:
        customer_options = [{"id": "Standard Client", "title": "Standard Client"}]
            
    # 2. Order Types (clean list)
    order_types = [
        {"id": "Machine Embroidery", "title": "Machine Embroidery"},
        {"id": "Embroidery Designing", "title": "Embroidery Designing"}
    ]
    
    # 3. Template Options (strictly existing templates)
    templates_list = sheets.get_description_templates() or []
    template_options = []
    seen_templates = set()
    for t in templates_list:
        tname = t.get("template_name", "").strip()
        if tname and tname not in seen_templates:
            seen_templates.add(tname)
            machine = t.get("machine", "")
            title_str = f"{tname} ({machine})" if machine and machine != "None" else tname
            template_options.append({"id": tname, "title": title_str[:30]})
    if not template_options:
        template_options = [{"id": "Standard Embroidery", "title": "Standard Embroidery"}]

    return {
        "version": "7.2",
        "screens": [
            {
                "id": "ORDER_SCREEN",
                "title": "CJS Order Intake",
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
                                    "text": "New Order Intake"
                                },
                                {
                                    "type": "Dropdown",
                                    "name": "customer_select",
                                    "label": "Customer Name",
                                    "required": True,
                                    "data-source": customer_options
                                },
                                {
                                    "type": "Dropdown",
                                    "name": "order_type_select",
                                    "label": "Order Type",
                                    "required": True,
                                    "data-source": order_types
                                },
                                {
                                    "type": "Dropdown",
                                    "name": "template_select",
                                    "label": "Template / Design Name",
                                    "required": True,
                                    "data-source": template_options
                                },
                                {
                                    "type": "TextInput",
                                    "name": "quantity",
                                    "label": "Quantity (Units / Pieces)",
                                    "input-type": "number",
                                    "required": True
                                },
                                {
                                    "type": "DatePicker",
                                    "name": "delivery_date",
                                    "label": "Expected Delivery Date",
                                    "required": True
                                },
                                {
                                    "type": "TextInput",
                                    "name": "stitch_count",
                                    "label": "Stitch Count (Optional)",
                                    "input-type": "number",
                                    "required": False
                                },
                                {
                                    "type": "TextInput",
                                    "name": "labor_hours",
                                    "label": "Labor Hours (Optional Override)",
                                    "input-type": "number",
                                    "required": False
                                }
                            ]
                        },
                        {
                            "type": "Footer",
                            "label": "Submit Order",
                            "on-click-action": {
                                "name": "complete",
                                "payload": {
                                    "customer_select": "${form.customer_select}",
                                    "order_type_select": "${form.order_type_select}",
                                    "template_select": "${form.template_select}",
                                    "quantity": "${form.quantity}",
                                    "delivery_date": "${form.delivery_date}",
                                    "stitch_count": "${form.stitch_count}",
                                    "labor_hours": "${form.labor_hours}"
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
    print("2. Uploading Flow JSON Assets...")
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
    print("3. Publishing Flow...")
    res = requests.post(
        f"{BASE_URL}/{flow_id}/publish",
        headers=HEADERS
    )
    if res.status_code != 200:
        print(f"Publish error: {res.text}")
    res.raise_for_status()
    print(f"-> Flow {flow_id} published successfully!")

def update_env_flow_id(new_flow_id: str):
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        with open(env_path, "w") as f:
            updated = False
            for line in lines:
                if line.startswith("WHATSAPP_FLOW_ID="):
                    f.write(f'WHATSAPP_FLOW_ID="{new_flow_id}"\n')
                    updated = True
                else:
                    f.write(line)
            if not updated:
                f.write(f'WHATSAPP_FLOW_ID="{new_flow_id}"\n')
        print(f"-> Updated .env with WHATSAPP_FLOW_ID={new_flow_id}")

def redeploy_order_flow() -> str:
    """Builds and publishes an updated Flow to Meta Graph API, updating local .env and returning the new flow_id."""
    flow_name = f"cjs_order_intake_{int(time.time())}"
    flow_json = build_flow_json()
    new_id = create_flow(flow_name)
    upload_assets(new_id, flow_json)
    publish_flow(new_id)
    update_env_flow_id(new_id)
    os.environ["WHATSAPP_FLOW_ID"] = new_id
    print(f"\n==========================================")
    print(f"SUCCESS! New Flow ID: {new_id}")
    print(f"==========================================")
    return new_id

if __name__ == "__main__":
    redeploy_order_flow()

