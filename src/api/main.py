import os
import json
import pytz
import uvicorn
import traceback
from fastapi import FastAPI, Request, Query, Response, BackgroundTasks
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import threading

# Internal imports
from src.services.whatsapp import WhatsAppService
from src.services.memory import MemoryService
from src.services.sheets import GoogleSheetsService
from src.agents.state import AgentState
from src.agents.agent_6_secretary import SecretaryAgent
from src.workflow.main_graph import cjs_bot

# Load environment variables
load_dotenv()

app = FastAPI()

# Configuration
VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN")
ADMIN_PHONE_NUMBER = os.environ.get("ADMIN_PHONE_NUMBER")
VERSION = "1.2.6"
IST = pytz.timezone("Asia/Kolkata")

# Initialize services
whatsapp_service = WhatsAppService()
memory_service = MemoryService()
db_service = GoogleSheetsService()
secretary_agent = SecretaryAgent()

# Scheduler (fires at 6:00 AM IST daily)
# Scheduler (fires at 6:00 AM IST daily)
scheduler = AsyncIOScheduler(timezone=IST)

async def send_daily_briefing():
    """Triggered at 6:00 AM IST — generates and sends the morning brief to Boss."""
    print("[Scheduler] Triggering daily briefing at 6:00 AM IST...")
    try:
        data = db_service.get_secretary_data()
        summary = secretary_agent.generate_daily_summary(data)
        if ADMIN_PHONE_NUMBER and summary:
            whatsapp_service.send_text_message(ADMIN_PHONE_NUMBER, summary)
            print(f"[Scheduler] Daily briefing sent to {ADMIN_PHONE_NUMBER}.")
        else:
            print("[Scheduler] Skipped: ADMIN_PHONE_NUMBER not set or summary empty.")
    except Exception as e:
        print(f"[Scheduler] Daily briefing failed: {e}")
        print(traceback.format_exc())

@app.on_event("startup")
async def startup_event():
    print(f"--- CJS Agent Server Started (v{VERSION}) ---")
    print(f"Gemini API Key: {'Set' if os.environ.get('GEMINI_API_KEY') else 'MISSING'}")
    print(f"Sheet ID: {'Set' if os.environ.get('GOOGLE_SHEET_ID') else 'MISSING'}")
    print(f"Admin Phone: {ADMIN_PHONE_NUMBER}")
    
    # Schedule daily briefing at 6:00 AM IST (Asia/Kolkata)
    scheduler.add_job(
        send_daily_briefing,
        CronTrigger(hour=6, minute=0, timezone=IST),
        id="daily_briefing",
        replace_existing=True
    )
    scheduler.start()
    print("[Scheduler] Daily briefing scheduled at 06:00 AM IST (Asia/Kolkata) every day.")

@app.get("/")
async def root():
    return {"status": "online", "agent": "CJS Designs", "version": VERSION}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": "2026-03-30", "version": VERSION}

@app.get("/trigger-daily-brief")
async def trigger_daily_brief():
    """Manual / Cloud Scheduler endpoint to trigger the morning brief."""
    await send_daily_briefing()
    return {"status": "sent", "recipient": ADMIN_PHONE_NUMBER}

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

# Global locks dictionary for synchronizing per-user webhook processing
user_locks = {}
user_locks_lock = threading.Lock()

def get_user_lock(phone: str) -> threading.Lock:
    with user_locks_lock:
        if phone not in user_locks:
            user_locks[phone] = threading.Lock()
        return user_locks[phone]

def process_webhook_message(sender_phone: str, text_body: str, interactive_payload: dict = None):
    """Processes the incoming WhatsApp message in the background."""
    lock = get_user_lock(sender_phone)
    with lock:
        try:
            # 0. Truncate user input to prevent token overload
            text_body = text_body[:1500]
            
            # 1. Load context from Persistence
            prior_state_dict = memory_service.get_state(sender_phone)
            
            if prior_state_dict:
                print(f"[MEM] Resuming session for {sender_phone}")
                initial_state = AgentState(**prior_state_dict)
                # Reset flags to force the Supervisor to re-evaluate the new message
                initial_state.raw_message = text_body
                initial_state.is_missing_info = False
                initial_state.send_order_form = False
                initial_state.next_step = "supervisor"
            else:
                print(f"[MEM] Fresh session for {sender_phone}")
                initial_state = AgentState(raw_message=text_body, sender_id=sender_phone)
            
            # 1.5 Handle Form Submission Bypass
            if interactive_payload:
                raw_cust_name = interactive_payload.get("customer_name")
                from src.agents.agent_1_collector import sanitize_customer_name
                sanitized_cust_name = sanitize_customer_name(raw_cust_name)
                
                initial_state.customer_name = sanitized_cust_name
                if sanitized_cust_name:
                    cid = db_service.create_customer_if_not_exists(sanitized_cust_name)
                    initial_state.customer_id = cid
                else:
                    initial_state.customer_id = None
                    initial_state.is_missing_info = True
                    initial_state.missing_fields_prompt = "Please provide a valid customer name to complete the order."
                
                initial_state.fabric_type = interactive_payload.get("fabric_type")
                # Combine garment type into embroidery type to match existing state logic
                garment = interactive_payload.get("garment_type", "")
                embroidery = interactive_payload.get("embroidery_style", "")
                initial_state.embroidery_type = f"{embroidery} {garment}".strip()
                initial_state.stitch_count = int(interactive_payload.get("stitch_count", 0))
                initial_state.requested_delivery_date = str(interactive_payload.get("delivery_date"))
                initial_state.raw_message = "I have filled out the order form."
                print(f"[WEBHOOK] Injected native Flow data into state for {sender_phone}")
            
            # 2. Execute the LangGraph chain (with Guard Rails)
            final_state_dict = cjs_bot.invoke(initial_state, config={"recursion_limit": 20})
            rebuilt_state = AgentState(**final_state_dict)
            
            # 3. Decision logic
            if rebuilt_state.send_order_form:
                 # Trigger native WhatsApp Flow
                 flow_id = os.getenv("WHATSAPP_FLOW_ID")
                 if flow_id:
                     whatsapp_service.send_flow_message(sender_phone, flow_id)
                 else:
                     whatsapp_service.send_text_message(sender_phone, "Error: Flow ID missing from config.")
                 memory_service.save_state(sender_phone, rebuilt_state)
            elif rebuilt_state.is_missing_info:
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
                 print(f"[SEND] Final response for {sender_phone}: {rebuilt_state.raw_message[:50]}...")
                 whatsapp_service.send_text_message(sender_phone, rebuilt_state.raw_message)
                 
                 # Clear state as the task is finished
                 memory_service.clear_state(sender_phone)

        except Exception as e:
            error_trace = traceback.format_exc()
            print(f"[ERROR] Failed Webhook execution sequence: {e}")
            print(error_trace)
            
            # NOTIFY the user about the failure (Helpful for debugging)
            error_msg = f"⚠️ *Internal Error:* {str(e)}\n\nCheck logs for details."
            whatsapp_service.send_text_message(sender_phone, error_msg)

@app.post("/webhook")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
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
                        msg_type = message.get("type")
                        
                        interactive_payload = None
                        text_body = ""

                        if msg_type == "text":
                            text_body = message.get("text", {}).get("body", "")
                        elif msg_type == "interactive":
                            interactive = message.get("interactive", {})
                            if interactive.get("type") == "nfm_reply":
                                response_json = interactive.get("nfm_reply", {}).get("response_json", "{}")
                                import json
                                try:
                                    interactive_payload = json.loads(response_json)
                                    text_body = "[FORM_SUBMITTED]"
                                except json.JSONDecodeError:
                                    pass
                        
                        if not text_body:
                            continue

                        print(f"[RECV] Message from {sender_phone}: {text_body}")
                        
                        # ✨ Immediate Acknowledgment to Siny to manage perceived latency ✨
                        whatsapp_service.send_text_message(sender_phone, "Working on your request, Boss... 🔄")
                        
                        # Add WhatsApp message processing to background tasks
                        background_tasks.add_task(process_webhook_message, sender_phone, text_body, interactive_payload)
    
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
