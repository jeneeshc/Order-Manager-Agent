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

@app.api_route("/trigger-daily-brief", methods=["GET", "POST"])
async def trigger_daily_brief():
    """Manual / GCP Cloud Scheduler endpoint to trigger the morning brief."""
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
                initial_state.hop_count = 0
                initial_state.final_reply = None
                initial_state.is_status_update = False
                initial_state.new_invoice_status = None
                initial_state.is_explanation_request = False
                initial_state.is_payment_query = False
                initial_state.is_secretary_query = False
                initial_state.is_pending_invoicing_query = False
                initial_state.is_invoicing_done_update = False
                initial_state.invoicing_done_customer = None
                initial_state.is_field_override = False
                initial_state.override_field = None
                initial_state.override_value = None
            else:
                print(f"[MEM] Fresh session for {sender_phone}")
                initial_state = AgentState(raw_message=text_body, sender_id=sender_phone)
            
            # 1.5 Handle Form Submission Bypass
            # 1.5 Handle Form Submission Bypass
            if interactive_payload:
                # 1. Customer Name Resolution
                selected_cust = interactive_payload.get("customer_select")
                new_cust = interactive_payload.get("new_customer_name")
                if selected_cust and str(selected_cust).strip().upper() != "NEW":
                    raw_cust_name = selected_cust
                else:
                    raw_cust_name = new_cust or interactive_payload.get("customer_name")
                
                from src.agents.agent_1_collector import sanitize_customer_name
                sanitized_cust_name = sanitize_customer_name(raw_cust_name)
                
                initial_state.customer_name = sanitized_cust_name
                if sanitized_cust_name:
                    cid = db_service.create_customer_if_not_exists(sanitized_cust_name, phone=sender_phone)
                    initial_state.customer_id = cid
                else:
                    initial_state.customer_id = None
                    initial_state.is_missing_info = True
                    initial_state.missing_fields_prompt = "Please provide a valid customer name to complete the order."
                
                # 2. Order Type Resolution
                selected_type = interactive_payload.get("order_type_select")
                new_type = interactive_payload.get("new_order_type")
                if selected_type and str(selected_type).strip().upper() != "NEW":
                    raw_order_type = selected_type
                else:
                    raw_order_type = new_type or interactive_payload.get("new_order_type") or interactive_payload.get("order_type") or "Machine Embroidery"
                initial_state.order_type = str(raw_order_type).strip()

                # 3. Template Name Resolution
                selected_tmpl = interactive_payload.get("template_select")
                new_tmpl = interactive_payload.get("new_template_name")
                if selected_tmpl and str(selected_tmpl).strip().upper() != "NEW":
                    raw_template = selected_tmpl
                else:
                    raw_template = (
                        new_tmpl
                        or interactive_payload.get("new_template_name")
                        or interactive_payload.get("template_name")
                        or interactive_payload.get("embroidery_style")
                        or "General"
                    )
                initial_state.template_name = str(raw_template).strip()
                
                # Maintain legacy fields for compatibility
                initial_state.fabric_type = str(interactive_payload.get("fabric_type") or initial_state.order_type)
                initial_state.embroidery_type = initial_state.template_name
                
                # 4. Quantity
                try:
                    initial_state.quantity = int(interactive_payload.get("quantity") or 1)
                except (ValueError, TypeError):
                    initial_state.quantity = 1

                # 5. Labor Hours
                raw_labor = interactive_payload.get("labor_hours") or interactive_payload.get("hours_required")
                if raw_labor is not None and str(raw_labor).strip():
                    try:
                        initial_state.labor_hours = float(str(raw_labor).strip())
                    except (ValueError, TypeError):
                        tmpl_data = db_service.get_template_by_name(initial_state.template_name)
                        initial_state.labor_hours = tmpl_data.get("default_labor_hours", 1.0) if tmpl_data else 1.0
                else:
                    tmpl_data = db_service.get_template_by_name(initial_state.template_name)
                    initial_state.labor_hours = tmpl_data.get("default_labor_hours", 1.0) if tmpl_data else 1.0

                # Auto-register new template if not already present in Description_Templates
                db_service.create_template_if_not_exists(
                    order_type=initial_state.order_type,
                    template_name=initial_state.template_name,
                    default_labor_hours=initial_state.labor_hours or 1.0
                )

                # 6. Stitch Count
                if initial_state.order_type.lower() in {"embroidery design", "embroidery designing"}:
                    initial_state.stitch_count = 0
                else:
                    raw_stitches = interactive_payload.get("stitch_count")
                    if raw_stitches is not None and str(raw_stitches).strip().isdigit():
                        initial_state.stitch_count = int(str(raw_stitches).strip())
                    else:
                        initial_state.stitch_count = 0
                
                # 7. Delivery Date
                initial_state.requested_delivery_date = str(
                    interactive_payload.get("delivery_date")
                    or interactive_payload.get("expected_delivery_date")
                    or ""
                )
                initial_state.raw_message = "I have filled out the order form."
                print(f"[WEBHOOK] Injected native Flow data into state for {sender_phone} (Customer: {initial_state.customer_name}, Type: {initial_state.order_type}, Template: {initial_state.template_name}, Stitches: {initial_state.stitch_count}, Hours: {initial_state.labor_hours})")

                # FAST-PATH DETERMINISTIC PIPELINE FOR FORM SUBMISSIONS
                # Bypasses multi-agent LLM loops to achieve sub-second response latency
                if initial_state.customer_name and not initial_state.is_missing_info:
                    print(f"[FAST-PATH] Executing deterministic pipeline for form submission (0 LLM overhead)...")
                    from src.agents.agent_2_scheduler import ProductionSchedulerAgent
                    from src.agents.agent_3_estimator import EstimationAgent

                    scheduler = ProductionSchedulerAgent()
                    initial_state = scheduler.process(initial_state)

                    estimator = EstimationAgent()
                    initial_state = estimator.process(initial_state)

                    order_id = db_service.append_order(initial_state)
                    initial_state.order_id = order_id

                    confirm_reply = (
                        f"✅ *New Order Created: {order_id}* 🧵\n\n"
                        f"• *Customer:* {initial_state.customer_name}\n"
                        f"• *Order Type:* {initial_state.order_type}\n"
                        f"• *Template:* {initial_state.template_name}\n"
                        f"• *Quantity:* {initial_state.quantity} pcs\n"
                        f"• *Assigned Machine:* {initial_state.machine_assigned}\n"
                        f"• *Est. Delivery Date:* {initial_state.estimated_completion_date}\n\n"
                        f"💰 *Cost Breakdown:*\n"
                        f"• Base Cost: Rs {initial_state.base_cost_rs or 0}\n"
                        f"• Profit Margin: Rs {initial_state.profit_margin_rs or 0}\n"
                        f"• GST (18%): Rs {initial_state.gst_amount_rs or 0}\n"
                        f"• *Total Amount: Rs {initial_state.total_cost_rs or 0}*\n\n"
                        f"Status: *Estimated* | Saved to Google Sheets! 👍\n"
                        f"Reply *'Hi'* anytime for the main menu."
                    )
                    print(f"[FAST-PATH] Sending instant confirmation to {sender_phone} for {order_id}")
                    whatsapp_service.send_text_message(sender_phone, confirm_reply)
                    memory_service.clear_state(sender_phone)
                    return

            # 2. Execute the LangGraph chain (with Guard Rails)
            final_state_dict = cjs_bot.invoke(initial_state, config={"recursion_limit": 20})
            rebuilt_state = AgentState(**final_state_dict)
            
            if rebuilt_state.send_order_form:
                 # Trigger native WhatsApp Flow
                 flow_id = os.getenv("WHATSAPP_FLOW_ID") or "2592939917793397"
                 msg_text = rebuilt_state.final_reply or "Please fill out the order form below, Boss:"
                 if flow_id:
                     sent = whatsapp_service.send_flow_message(sender_phone, flow_id, message_text=msg_text)
                     if not sent:
                         whatsapp_service.send_text_message(
                             sender_phone,
                             "⚠️ We had trouble opening the interactive form. You can reply directly with:\n"
                             "*Customer Name*, *Order Type*, *Template Name*, *Quantity*, and *Expected Delivery Date*."
                         )
                 else:
                     whatsapp_service.send_text_message(sender_phone, "Error: Flow ID missing from config.")
                 memory_service.save_state(sender_phone, rebuilt_state)
            elif rebuilt_state.is_missing_info:
                 # Bot needs more info (from Collector worker)
                 whatsapp_service.send_text_message(sender_phone, rebuilt_state.missing_fields_prompt)
                 memory_service.save_state(sender_phone, rebuilt_state)
            elif rebuilt_state.active_menu:
                 # Menu navigation or waiting for sub-option / selection
                 reply = rebuilt_state.final_reply or rebuilt_state.raw_message
                 if reply:
                     whatsapp_service.send_text_message(sender_phone, reply)
                 memory_service.save_state(sender_phone, rebuilt_state)
            else:
                 # Finalize any Database changes
                 if rebuilt_state.order_id:
                     if rebuilt_state.is_status_update:
                         db_service.update_order_status(rebuilt_state.order_id, rebuilt_state.new_invoice_status)
                     elif rebuilt_state.is_field_override and rebuilt_state.override_field and rebuilt_state.override_value:
                         db_service.update_order_field(rebuilt_state.order_id, rebuilt_state.override_field, rebuilt_state.override_value)
                     else:
                         db_service.update_order(rebuilt_state)
                 elif not any([
                     rebuilt_state.is_explanation_request,
                     rebuilt_state.is_secretary_query,
                     rebuilt_state.is_payment_query,
                     rebuilt_state.is_pending_invoicing_query,
                     rebuilt_state.is_invoicing_done_update
                 ]):
                     db_service.append_order(rebuilt_state)

                 # 4. Final Reply
                 reply = rebuilt_state.final_reply or rebuilt_state.raw_message
                 print(f"[SEND] Final response for {sender_phone}: {reply[:50] if reply else ''}...")
                 if reply:
                     whatsapp_service.send_text_message(sender_phone, reply)
                 
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
