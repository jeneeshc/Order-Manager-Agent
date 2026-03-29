import os
import uvicorn
from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from src.services.whatsapp import WhatsAppService
from src.services.sheets import GoogleSheetsService
from src.services.memory import MemoryService
from src.services.audio import AudioTranscriptionService
from src.agents.agent_6_secretary import SecretaryAgent

# Load environment configuration
load_dotenv()
app = FastAPI(title="CJS Designs - WhatsApp Agent Webhook")

# Initialize robust service integrations
whatsapp_service = WhatsAppService()
db_service = GoogleSheetsService()
memory_service = MemoryService()
audio_service = AudioTranscriptionService()
secretary_service = SecretaryAgent()

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

@app.post("/cron/daily-report")
async def daily_report():
    """Triggered daily at 9:00 AM to send Siny her work summary."""
    print("[CRON] Generating daily report for Siny...")
    data = db_service.get_secretary_data()
    report = secretary_service.generate_daily_summary(data)
    
    # Send to Siny (using the admin number from env)
    admin_phone = os.getenv("ADMIN_PHONE_NUMBER", "918289897413") 
    whatsapp_service.send_text_message(admin_phone, report)
    
    return {"status": "success", "message": "Daily report sent."}

@app.post("/webhook")
async def receive_whatsapp_message(request: Request):
    """Catch incoming messages, run them through LangGraph, reply to Siny."""
    body = await request.json()
    print(f"\n[WEBHOOK] Raw incoming payload: {body}\n")
    
    # 1. Drill down into WhatsApp JSON
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
                        text_body = ""

                        # Handle Text or Audio
                        if msg.get("type") == "text":
                            text_body = msg["text"].get("body")
                        elif "audio" in msg:
                            media_id = msg["audio"].get("id")
                            mime_type = msg["audio"].get("mime_type", "audio/ogg")
                            audio_bytes, detected_mime = whatsapp_service.download_media(media_id)
                            if detected_mime: mime_type = detected_mime
                            if audio_bytes:
                                whatsapp_service.send_text_message(sender_phone, "🎙️ Voice note received! Transcribing...")
                                text_body, _ = audio_service.transcribe(audio_bytes, mime_type)
                                if text_body:
                                    whatsapp_service.send_text_message(sender_phone, f"📝 *Heard:* {text_body}")

                        if not text_body:
                            continue

                        # ✨ 2. The Core Execution: Invoke Supervisor-led Orchestration Flow! ✨
                        prior_state_dict = memory_service.get_state(sender_phone)
                        if prior_state_dict:
                            initial_state = AgentState(**prior_state_dict)
                            initial_state.raw_message = text_body
                            # Reset flags so the Supervisor allows a fresh turn on new messages
                            initial_state.is_missing_info = False
                            initial_state.next_step = "supervisor"
                        else:
                            initial_state = AgentState(raw_message=text_body, sender_id=sender_phone)
                        
                        final_state_dict = cjs_bot.invoke(initial_state)
                        rebuilt_state = AgentState(**final_state_dict)
                        
                        # 3. Decision logic
                        if rebuilt_state.is_missing_info:
                             # Bot needs more info (from Collector worker)
                             whatsapp_service.send_text_message(sender_phone, rebuilt_state.missing_fields_prompt)
                             memory_service.save_state(sender_phone, rebuilt_state)
                        else:
                             # Finalize any Database changes before sending the synthesized response
                             if rebuilt_state.order_id:
                                 if rebuilt_state.is_status_update:
                                     # Update Status (No invoice creation)
                                     db_service.update_order_status(rebuilt_state.order_id, rebuilt_state.new_invoice_status)
                                 else:
                                     # New or Existing order update
                                     db_service.update_order(rebuilt_state)
                             elif not any([rebuilt_state.is_explanation_request, rebuilt_state.is_secretary_query, rebuilt_state.is_payment_query]):
                                 # Completely new order that isn't a query
                                 db_service.append_order(rebuilt_state)

                             # 4. Final Reply: Use the Supervisor's synthesized final response!
                             whatsapp_service.send_text_message(sender_phone, rebuilt_state.raw_message)
                             
                             # Clear state memory as the current task is finished
                             memory_service.clear_state(sender_phone)

        except Exception as e:
            print(f"[ERROR] Failed Webhook execution sequence: {e}")
            # Optional: Notify Siny of failure
            # whatsapp_service.send_text_message(sender_phone, "⚠️ Sorry, I encountered an internal error. Please try again.")
    
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
