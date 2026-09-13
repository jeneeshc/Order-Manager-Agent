import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("WHATSAPP_ACCESS_TOKEN")
waba = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID") or "1457897545971090"
from scripts.deploy_flow import build_flow_json

flow_json = build_flow_json()
picker = flow_json['screens'][0]['layout']['children'][0]['children'][-1]
print("Current picker config:", picker)

# Test creating draft flow
headers = {"Authorization": f"Bearer {token}"}
res = requests.post(f"https://graph.facebook.com/v22.0/{waba}/flows", headers=headers, data={"name": "test_photo_picker_val", "categories": '["OTHER"]'})
fid = res.json().get("id")
print("Draft Flow ID:", fid)

if fid:
    up = requests.post(
        f"https://graph.facebook.com/v22.0/{fid}/assets",
        headers=headers,
        files={"file": ("flow.json", json.dumps(flow_json), "application/json")},
        data={"name": "flow.json", "asset_type": "FLOW_JSON"}
    )
    print("Upload result:", up.json())
    # Delete test flow
    del_res = requests.delete(f"https://graph.facebook.com/v22.0/{fid}", headers=headers)
    print("Cleanup test flow:", del_res.status_code)
