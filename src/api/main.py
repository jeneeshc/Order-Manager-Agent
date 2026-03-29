import os
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from dotenv import load_dotenv

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from src.services.whatsapp import WhatsAppService
from src.services.sheets import GoogleSheetsService

# Load environment configuration
load_dotenv()
app = FastAPI(title="CJS Designs - WhatsApp Agent Webhook")

# Initialize robust service integrations
whatsapp_service = WhatsAppService()
db_service = GoogleSheetsService()

@app.get("/")
def health_check():
    return {"status": "ok", "message": "CJS Designs Platform Operational."}

@app.get("/webhook")
def verify_whatsapp_webhook(request: Request):
    """Standard Meta webhook verification."""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_secure_cjs_token")

    if mode and token and mode == "subscribe" and token == VERIFY_TOKEN:
        return int(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """Catch incoming messages, run them through LangGraph, reply to Siny."""
    body = await request.json()
    
    # 1. Drill down into messy WhatsApp JSON to find the actual message text
    if body.get("object") == "whatsapp_business_account":
        try:
            entries = body.get("entry", [])
            for entry in entries:
                changes = entry.get("changes", [])
                for change in changes:
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    
                    for msg in messages:
                        sender_phone = msg.get("from")
                        
                        # Only handle text commands for now
                        if "text" in msg:
                            text_body = msg["text"]["body"]
                            print(f"\n[WEBHOOK] Incoming SMS from {sender_phone}: '{text_body}'\n")
                            
                            # ✨ 2. The Core Execution: Invoke Agents ✨
                            initial_state = AgentState(raw_message=text_body, sender_id=sender_phone)
                            
                            # Start Graph cascading sequence
                            final_state_dict = cjs_bot.invoke(initial_state)
                            
                            # 3. Handle End States & Logic Responses
                            if final_state_dict.get("is_missing_info"):
                                # Agent 1 determined it needed more info
                                whatsapp_service.send_text_message(sender_phone, final_state_dict.get("missing_fields_prompt"))
                            else:
                                # Data extraction was perfect. Agent 2 & 3 ran math. DB saves row.
                                rebuilt_state = AgentState(**final_state_dict)
                                order_id = db_service.append_order(rebuilt_state)
                                
                                # Agent replies directly back to phone with estimate
                                quote = (f"✅ Computation Complete!\n"
                                         f"• Cost Estimate: Rs {rebuilt_state.total_cost_rs}\n"
                                         f"• Complete By: {rebuilt_state.estimated_completion_date}\n"
                                         f"• Machine Chosen: {rebuilt_state.machine_assigned}\n"
                                         f"• Saved To DB: {order_id}")
                                whatsapp_service.send_text_message(sender_phone, quote)
                                
        except Exception as e:
            print(f"[ERROR] Failed Webhook execution sequence: {e}")
            
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
