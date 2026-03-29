import os
import json
import uvicorn
import traceback
from fastapi import FastAPI, Request, Query, Response
from dotenv import load_dotenv

# Internal imports
from src.services.whatsapp import WhatsAppService
from src.services.memory import MemoryService
from src.services.sheets import GoogleSheetsService
from src.agents.state import AgentState
from src.workflow.main_graph import cjs_bot

# Load environment variables
load_dotenv()

app = FastAPI()

# Configuration
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
ADMIN_PHONE_NUMBER = os.environ.get("ADMIN_PHONE_NUMBER")
VERSION = "1.2.5"

# Initialize services
whatsapp_service = WhatsAppService()
memory_service = MemoryService()
db_service = GoogleSheetsService()

@app.on_event("startup")
async def startup_event():
    print(f"--- CJS Agent Server Started (v{VERSION}) ---")
    print(f"Gemini API Key: {'Set' if os.environ.get('GEMINI_API_KEY') else 'MISSING'}")
    print(f"Sheet ID: {'Set' if os.environ.get('GOOGLE_SHEET_ID') else 'MISSING'}")
    print(f"Admin Phone: {ADMIN_PHONE_NUMBER}")

@app.get("/")
async def root():
    return {"status": "online", "agent": "CJS Designs", "version": VERSION}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2026-03-29", "version": VERSION}

@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge"),
):
    """WhatsApp Webhook verification (GET)."""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("WEBHOOK_VERIFIED")
        return Response(content=challenge, media_type="text/plain")
    return Response(content="Forbidden", status_code=403)

@app.post("/webhook")
async def handle_webhook(request: Request):
    """WhatsApp Webhook message handler (POST)."""
    data = await request.json()
    
    # Process WhatsApp message structure
    if "entry" in data:
        for entry in data["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" in value:
                    for message in value["messages"]:
                        sender_phone = message.get("from")
                        text_body = message.get("text", {}).get("body", "")
                        
                        if not text_body:
                            continue

                        print(f"[RECV] Message from {sender_phone}: {text_body}")
                        
                        try:
                            # 1. Load context from Persistence
                            prior_state_dict = memory_service.get_state(sender_phone)
                            
                            if prior_state_dict:
                                print(f"[MEM] Resuming session for {sender_phone}")
                                initial_state = AgentState(**prior_state_dict)
                                # Reset flags to force the Supervisor to re-evaluate the new message
                                initial_state.raw_message = text_body
                                initial_state.is_missing_info = False
                                initial_state.next_step = "supervisor"
                            else:
                                print(f"[MEM] Fresh session for {sender_phone}")
                                initial_state = AgentState(raw_message=text_body, sender_id=sender_phone)
                            
                            # 2. Execute the LangGraph chain
                            final_state_dict = cjs_bot.invoke(initial_state)
                            rebuilt_state = AgentState(**final_state_dict)
                            
                            # 3. Decision logic
                            if rebuilt_state.is_missing_info:
                                 # Bot needs more info (from Collector worker)
                                 whatsapp_service.send_text_message(sender_phone, rebuilt_state.missing_fields_prompt)
                                 memory_service.save_state(sender_phone, rebuilt_state)
                            else:
                                 # Finalize any Database changes
                                 if rebuilt_state.order_id:
                                     if rebuilt_state.is_status_update:
                                         db_service.update_order_status(rebuilt_state.order_id, rebuilt_state.new_invoice_status)
                                     else:
                                         db_service.update_order(rebuilt_state)
                                 elif not any([rebuilt_state.is_explanation_request, rebuilt_state.is_secretary_query, rebuilt_state.is_payment_query]):
                                     db_service.append_order(rebuilt_state)

                                 # 4. Final Reply
                                 whatsapp_service.send_text_message(sender_phone, rebuilt_state.raw_message)
                                 
                                 # Clear state as the task is finished
                                 memory_service.clear_state(sender_phone)

                        except Exception as e:
                            error_trace = traceback.format_exc()
                            print(f"[ERROR] Failed Webhook execution sequence: {e}")
                            print(error_trace)
                            
                            # NOTIFY the user about the failure (Helpful for debugging)
                            if sender_phone == ADMIN_PHONE_NUMBER:
                                 error_msg = f"⚠️ *Internal Error:* {str(e)}\n\nCheck logs for details."
                                 whatsapp_service.send_text_message(sender_phone, error_msg)
    
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
