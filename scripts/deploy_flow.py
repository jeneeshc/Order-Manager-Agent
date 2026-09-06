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
            
    # 2. Template Options (strictly existing templates with auto-population of stitches & labor minutes)
    templates_list = sheets.get_description_templates() or []
    template_options = []
    seen_templates = set()
    first_template_stitches = 50000
    first_template_labor_mins = 360

    for t in templates_list:
        tname = t.get("template_name", "").strip()
        if tname and tname not in seen_templates:
            seen_templates.add(tname)
            machine = t.get("machine", "")
            title_str = f"{tname} ({machine})" if machine and machine != "None" else tname
            st = int(t.get("stitch_count") or 0)
            lm = int(t.get("labor_minutes") or 0)
            if not template_options:
                first_template_stitches = st
                first_template_labor_mins = lm
            template_options.append({
                "id": tname,
                "title": title_str[:30],
                "on-select-action": {
                    "name": "update_data",
                    "payload": {
                        "init_stitch_count": st,
                        "init_labor_minutes": lm
                    }
                }
            })
    if not template_options:
        template_options = [{
            "id": "Standard Embroidery",
            "title": "Standard Embroidery",
            "on-select-action": {
                "name": "update_data",
                "payload": {
                    "init_stitch_count": 10000,
                    "init_labor_minutes": 60
                }
            }
        }]

    # 3. Order Types (clean list with on-select auto-population)
    order_types = [
        {
            "id": "Machine Embroidery",
            "title": "Machine Embroidery",
            "on-select-action": {
                "name": "update_data",
                "payload": {
                    "init_stitch_count": first_template_stitches,
                    "init_labor_minutes": first_template_labor_mins
                }
            }
        },
        {
            "id": "Embroidery Designing",
            "title": "Embroidery Designing",
            "on-select-action": {
                "name": "update_data",
                "payload": {
                    "init_stitch_count": 0,
                    "init_labor_minutes": 30
                }
            }
        }
    ]

    return {
        "version": "7.2",
        "screens": [
            {
                "id": "ORDER_SCREEN",
                "title": "CJS Order Manager",
                "data": {
                    "init_customer": {
                        "type": "string",
                        "__example__": "Standard Client"
                    },
                    "init_order_type": {
                        "type": "string",
                        "__example__": "Machine Embroidery"
                    },
                    "init_template": {
                        "type": "string",
                        "__example__": template_options[0]["id"]
                    },
                    "init_quantity": {
                        "type": "number",
                        "__example__": 1
                    },
                    "init_delivery_date": {
                        "type": "string",
                        "__example__": "1788672000000"
                    },
                    "init_stitch_count": {
                        "type": "number",
                        "__example__": first_template_stitches
                    },
                    "init_labor_minutes": {
                        "type": "number",
                        "__example__": first_template_labor_mins
                    },
                    "editing_order_id": {
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
                            "name": "order_form",
                            "init-values": {
                                "customer_select": "${data.init_customer}",
                                "order_type_select": "${data.init_order_type}",
                                "template_select": "${data.init_template}",
                                "quantity": "${data.init_quantity}",
                                "delivery_date": "${data.init_delivery_date}",
                                "stitch_count": "${data.init_stitch_count}",
                                "labor_minutes": "${data.init_labor_minutes}"
                            },
                            "children": [
                                {
                                    "type": "TextHeading",
                                    "text": "Order Details"
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
                                    "label": "Stitch Count",
                                    "input-type": "number",
                                    "required": False
                                },
                                {
                                    "type": "TextInput",
                                    "name": "labor_minutes",
                                    "label": "Labor Minutes",
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
                                    "labor_minutes": "${form.labor_minutes}",
                                    "editing_order_id": "${data.editing_order_id}"
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

