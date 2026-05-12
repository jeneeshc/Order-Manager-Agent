import os
import requests
from dotenv import load_dotenv

load_dotenv()

WABA_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

url = f"https://graph.facebook.com/v22.0/{WABA_ID}/flows"
headers = {"Authorization": f"Bearer {TOKEN}"}

response = requests.get(url, headers=headers)
print(response.status_code)
print(response.text)
