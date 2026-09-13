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
from src.services.db import FirestoreDatabaseService
from src.services.storage import CloudStorageService
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
db_service = FirestoreDatabaseService()
storage_service = CloudStorageService()
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
                initial_state.send_customer_form = False
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
            if interactive_payload:
                # 1.5.A Handle Customer Registration Flow Submission
                if (
                    interactive_payload.get("flow_type") == "customer_registration"
                    or ("customer_name" in interactive_payload and "template_select" not in interactive_payload and "order_type_select" not in interactive_payload)
                ):
                    raw_name = interactive_payload.get("customer_name")
                    phone = interactive_payload.get("customer_phone") or ""
                    address = interactive_payload.get("customer_address") or ""
                    from src.agents.single_agent import sanitize_customer_name
                    clean_name = sanitize_customer_name(raw_name)
                    if clean_name:
                        cid = db_service.create_customer_if_not_exists(clean_name, phone=phone, address=address)
                        confirm_reply = (
                            f"✅ *Customer Added Successfully!*\n\n"
                            f"• *Name:* {clean_name}\n"
                            f"• *Customer ID:* {cid}\n"
                            f"• *Phone:* {phone or 'Not provided'}\n"
                            f"• *Location:* {address or 'Not provided'}\n\n"
                            f"Saved to 'Customers' in Google Sheets. 👍\n"
                            f"Reply *'Hi'* for main menu or *'1'* to start a new order."
                        )
                    else:
                        confirm_reply = "⚠️ Invalid customer name provided. Please reply with a valid name."
                    print(f"[FAST-PATH] Customer registration completed for {clean_name}")
                    whatsapp_service.send_text_message(sender_phone, confirm_reply)
                    memory_service.clear_state(sender_phone)
                    return

                # 1.5.C Handle Standalone WhatsApp Image Upload (e.g. sent directly in chat with Order ID caption)
                if (
                    interactive_payload
                    and "photo_picker" in interactive_payload
                    and "customer_select" not in interactive_payload
                    and "customer_name" not in interactive_payload
                ):
                    raw_photos = interactive_payload.get("photo_picker") or []
                    if raw_photos:
                        photo_id = raw_photos[0].get("id")
                        mime_type = raw_photos[0].get("mime_type", "image/jpeg")
                        import re
                        match = re.search(r'\b(CJS-[A-Za-z0-9]+)\b', text_body, re.I)
                        target_order_id = match.group(1).upper() if match else None

                        if target_order_id:
                            order_data = db_service.get_order(target_order_id)
                            if order_data:
                                img_bytes, downloaded_mime = whatsapp_service.download_media(photo_id)
                                if img_bytes:
                                    storage_res = storage_service.upload_order_image(
                                        order_id=target_order_id,
                                        image_bytes=img_bytes,
                                        mime_type=downloaded_mime or mime_type,
                                        filename=f"{target_order_id}.jpg"
                                    )
                                    if storage_res:
                                        img_url = storage_res.get("public_url") or storage_res.get("view_link")
                                        db_service.update_order_field(target_order_id, "image_url", img_url)
                                        confirm_reply = (
                                            f"✅ Order Updated: {target_order_id}\n\n"
                                            f"* Customer: {order_data.get('customer')}\n"
                                            f"* Order Type: {order_data.get('order_type')}\n"
                                            f"* Template: {order_data.get('template')}\n"
                                            f"* Quantity: {order_data.get('quantity')} pcs\n"
                                            f"* Est. Delivery Date: {order_data.get('delivery_date')}\n"
                                            f"* Total Amount: {order_data.get('cost')}\n"
                                            f"* Design Image: {img_url}"
                                        )
                                        whatsapp_service.send_text_message(sender_phone, confirm_reply)
                                        memory_service.clear_state(sender_phone)
                                        return
                            else:
                                whatsapp_service.send_text_message(
                                    sender_phone,
                                    f"⚠️ Order *{target_order_id}* was not found in Google Sheets. Please check the Order ID."
                                )
                                memory_service.clear_state(sender_phone)
                                return
                        else:
                            whatsapp_service.send_text_message(
                                sender_phone,
                                "📸 *Image Received!*\n"
                                "To attach this image to an existing order, please include the *Order ID* in the caption (e.g. `CJS-ABC123`), or reply *'1'* to create a new order."
                            )
                            memory_service.clear_state(sender_phone)
                            return

                # 1.5.B Handle Order Creation / Edit Flow Submission
                # 1. Customer Name Resolution
                selected_cust = interactive_payload.get("customer_select")
                new_cust = interactive_payload.get("new_customer_name")
                if selected_cust and str(selected_cust).strip().upper() != "NEW":
                    raw_cust_name = selected_cust
                else:
                    raw_cust_name = new_cust or interactive_payload.get("customer_name")
                
                from src.agents.single_agent import sanitize_customer_name
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

                # 5. Labor Minutes & Hours (Converted to Hours for Cost Calculation)
                raw_labor_mins = interactive_payload.get("labor_minutes")
                raw_labor_hrs = interactive_payload.get("labor_hours") or interactive_payload.get("hours_required")
                if raw_labor_mins is not None and str(raw_labor_mins).strip():
                    try:
                        lm = float(str(raw_labor_mins).strip())
                        initial_state.labor_minutes = lm
                        initial_state.labor_hours = round(lm / 60.0, 2)
                    except (ValueError, TypeError):
                        tmpl_data = db_service.get_template_by_name(initial_state.template_name)
                        lm = float(tmpl_data.get("labor_minutes") or tmpl_data.get("default_labor_minutes") or 60.0) if tmpl_data else 60.0
                        initial_state.labor_minutes = lm
                        initial_state.labor_hours = round(lm / 60.0, 2)
                elif raw_labor_hrs is not None and str(raw_labor_hrs).strip():
                    try:
                        val = float(str(raw_labor_hrs).strip())
                        if val > 24: # Likely entered in minutes
                            initial_state.labor_minutes = val
                            initial_state.labor_hours = round(val / 60.0, 2)
                        else:
                            initial_state.labor_hours = val
                            initial_state.labor_minutes = round(val * 60.0, 1)
                    except (ValueError, TypeError):
                        tmpl_data = db_service.get_template_by_name(initial_state.template_name)
                        initial_state.labor_hours = tmpl_data.get("default_labor_hours", 1.0) if tmpl_data else 1.0
                        initial_state.labor_minutes = round(initial_state.labor_hours * 60.0, 1)
                else:
                    tmpl_data = db_service.get_template_by_name(initial_state.template_name)
                    if tmpl_data:
                        lm = float(tmpl_data.get("labor_minutes") or tmpl_data.get("default_labor_minutes") or 60.0)
                        initial_state.labor_minutes = lm
                        initial_state.labor_hours = round(lm / 60.0, 2)
                    else:
                        initial_state.labor_minutes = 60.0
                        initial_state.labor_hours = 1.0

                # 6. Stitch Count
                if initial_state.order_type.lower() in {"embroidery design", "embroidery designing"}:
                    initial_state.stitch_count = 0
                else:
                    raw_stitches = interactive_payload.get("stitch_count")
                    if raw_stitches is not None and str(raw_stitches).strip().isdigit() and int(str(raw_stitches).strip()) > 0:
                        initial_state.stitch_count = int(str(raw_stitches).strip())
                    else:
                        tmpl_data = db_service.get_template_by_name(initial_state.template_name)
                        initial_state.stitch_count = int(tmpl_data.get("stitch_count") or tmpl_data.get("base_stitch_count") or 0) if tmpl_data else 0

                # Auto-register new template if not already present in Description_Templates
                db_service.create_template_if_not_exists(
                    order_type=initial_state.order_type,
                    template_name=initial_state.template_name,
                    default_labor_minutes=initial_state.labor_minutes or 60.0,
                    stitch_count=initial_state.stitch_count or 0
                )
                
                # 7. Delivery Date & Editing Order ID
                initial_state.requested_delivery_date = str(
                    interactive_payload.get("delivery_date")
                    or interactive_payload.get("expected_delivery_date")
                    or ""
                )
                initial_state.editing_order_id = interactive_payload.get("editing_order_id") or None
                initial_state.raw_message = "I have filled out the order form."
                print(f"[WEBHOOK] Injected native Flow data into state for {sender_phone} (Editing: {initial_state.editing_order_id}, Customer: {initial_state.customer_name}, Type: {initial_state.order_type}, Template: {initial_state.template_name}, Stitches: {initial_state.stitch_count}, Hours: {initial_state.labor_hours})")

                # FAST-PATH DETERMINISTIC PIPELINE FOR FORM SUBMISSIONS
                # Bypasses multi-agent LLM loops to achieve sub-second response latency
                if initial_state.customer_name and not initial_state.is_missing_info:
                    print(f"[FAST-PATH] Executing deterministic pipeline for form submission (0 LLM overhead)...")
                    if initial_state.editing_order_id:
                        order_id = initial_state.editing_order_id
                    else:
                        import uuid
                        order_id = getattr(initial_state, "order_id", None) or f"CJS-{str(uuid.uuid4())[:6].upper()}"
                    initial_state.order_id = order_id

                    # 8. Handle optional PhotoPicker upload from camera / WhatsApp gallery
                    raw_photos = interactive_payload.get("photo_picker") or []
                    if isinstance(raw_photos, dict):
                        raw_photos = [raw_photos]
                    if isinstance(raw_photos, list) and len(raw_photos) > 0:
                        photo_info = raw_photos[0]
                        media_id = photo_info.get("id")
                        mime_type = photo_info.get("mime_type", "image/jpeg")
                        file_name = photo_info.get("file_name", f"{order_id}.jpg")
                        if media_id:
                            print(f"[FAST-PATH] Downloading photo {media_id} for order {order_id}...")
                            img_bytes, downloaded_mime = whatsapp_service.download_media(media_id)
                            if img_bytes:
                                print(f"[FAST-PATH] Uploading photo to Cloud Storage under monthly folder...")
                                storage_res = storage_service.upload_order_image(
                                    order_id=order_id,
                                    image_bytes=img_bytes,
                                    mime_type=downloaded_mime or mime_type,
                                    filename=file_name
                                )
                                if storage_res:
                                    initial_state.image_url = storage_res.get("public_url") or storage_res.get("view_link")
                                    initial_state.image_drive_id = storage_res.get("file_id")
                                    initial_state.image_media_id = media_id

                    from src.agents.agent_2_scheduler import ProductionSchedulerAgent
                    from src.agents.agent_3_estimator import EstimationAgent

                    scheduler = ProductionSchedulerAgent()
                    initial_state = scheduler.process(initial_state)

                    estimator = EstimationAgent()
                    initial_state = estimator.process(initial_state)

                    if initial_state.editing_order_id:
                        db_service.update_order_from_form(order_id, initial_state)
                    else:
                        db_service.append_order(initial_state)

                    header = f"✅ Order Updated: {order_id}" if initial_state.editing_order_id else f"✅ New Order Created: {order_id}"
                    delivery_date = initial_state.estimated_completion_date or initial_state.requested_delivery_date or "To be confirmed"
                    total_cost_val = initial_state.total_cost_rs or 0
                    if isinstance(total_cost_val, (int, float)) and float(total_cost_val).is_integer():
                        total_cost_str = f"Rs {int(total_cost_val)}"
                    else:
                        total_cost_str = f"Rs {round(float(total_cost_val), 2)}"

                    # Response formatted with Estimate heading, ready to be forwarded directly to customer:
                    confirm_reply = (
                        f"*Estimate*\n"
                        f"{header}\n\n"
                        f"* Customer: {initial_state.customer_name}\n"
                        f"* Order Type: {initial_state.order_type}\n"
                        f"* Template: {initial_state.template_name}\n"
                        f"* Quantity: {initial_state.quantity} pcs\n"
                        f"* Est. Delivery Date: {delivery_date}\n"
                        f"* Total Amount: {total_cost_str}"
                    )
                    if initial_state.image_url:
                        confirm_reply += f"\n* Design Image: {initial_state.image_url}"

                    print(f"[FAST-PATH] Sending customer-forwardable confirmation to {sender_phone} for {order_id}")
                    # 1. ALWAYS send the text confirmation first so the user reliably gets the estimate instantly
                    whatsapp_service.send_text_message(sender_phone, confirm_reply)

                    # 2. If a valid image URL exists on Cloud Storage, send the image separately
                    if initial_state.image_url and (str(initial_state.image_url).startswith("http://") or str(initial_state.image_url).startswith("https://")):
                        whatsapp_service.send_image_message(
                            sender_phone,
                            initial_state.image_url,
                            caption=f"Design Image for Order {order_id}"
                        )

                    memory_service.clear_state(sender_phone)
                    return

            # 2. Execute the LangGraph chain (with Guard Rails)
            final_state_dict = cjs_bot.invoke(initial_state, config={"recursion_limit": 20})
            rebuilt_state = AgentState(**final_state_dict)
            
            if rebuilt_state.send_order_form:
                 # Trigger native WhatsApp Flow
                 config_vars = db_service.get_config_variables()
                 flow_id = (
                     str(config_vars.get("WhatsApp Flow ID") or config_vars.get("WHATSAPP_FLOW_ID") or "").strip()
                     or os.getenv("WHATSAPP_FLOW_ID")
                     or "2113819249528233"
                 )
                 msg_text = rebuilt_state.final_reply or "Please fill out the order form below, Boss:"
                 header_text = f"Edit Order {rebuilt_state.editing_order_id}" if rebuilt_state.editing_order_id else "Order Creation"
                 if flow_id:
                     sent = whatsapp_service.send_flow_message(
                         sender_phone,
                         flow_id,
                         message_text=msg_text,
                         screen_data=rebuilt_state.flow_init_data,
                         header_text=header_text
                     )
                     if not sent:
                         whatsapp_service.send_text_message(
                             sender_phone,
                             "⚠️ We had trouble opening the interactive form. You can reply directly with:\n"
                             "*Customer Name*, *Order Type*, *Template Name*, *Quantity*, and *Expected Delivery Date*."
                         )
                 else:
                     whatsapp_service.send_text_message(sender_phone, "Error: Flow ID missing from config.")
                 memory_service.save_state(sender_phone, rebuilt_state)
            elif rebuilt_state.send_customer_form:
                  # Trigger native WhatsApp Customer Registration Flow
                  config_vars = db_service.get_config_variables()
                  cust_flow_id = (
                      str(config_vars.get("WhatsApp Customer Flow ID") or config_vars.get("WHATSAPP_CUSTOMER_FLOW_ID") or "").strip()
                      or os.getenv("WHATSAPP_CUSTOMER_FLOW_ID")
                      or "1347920890757319"
                  )
                  msg_text = rebuilt_state.final_reply or "Please fill out the customer registration form below, Boss:"
                  header_text = "New Customer"
                  if cust_flow_id:
                      sent = whatsapp_service.send_flow_message(
                          sender_phone,
                          cust_flow_id,
                          message_text=msg_text,
                          screen_data={"init_name": "", "init_phone": "", "init_address": ""},
                          header_text=header_text,
                          flow_cta="Open Form",
                          initial_screen="CUSTOMER_SCREEN"
                      )
                      if not sent:
                          whatsapp_service.send_text_message(
                              sender_phone,
                              "👤 *Add New Customer*\n"
                              "Boss, please reply with the customer details:\n"
                              "*Format:* Customer Name, Phone (optional), Address (optional)"
                          )
                  else:
                      whatsapp_service.send_text_message(sender_phone, "Error: Customer Flow ID missing from config.")
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
async def handle_webhook(request: Request, background_tasks: BackgroundTasks = None):
    """WhatsApp Webhook message handler (POST)."""
    try:
        data = await request.json()
    except Exception as e:
        print(f"[WEBHOOK ERROR] Failed to parse request JSON: {e}")
        return {"status": "error"}

    try:
        # Process WhatsApp message structure
        if "entry" in data:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    # Log any delivery errors or status changes
                    if "statuses" in value:
                        for status in value["statuses"]:
                            s_status = status.get("status")
                            s_id = status.get("id")
                            s_errors = status.get("errors")
                            if s_errors or s_status in ("failed", "undelivered"):
                                print(f"[WHATSAPP STATUS ERROR] id={s_id}, status={s_status}, errors={s_errors}")

                    if "errors" in value:
                        print(f"[WHATSAPP VALUE ERROR] errors={value['errors']}")

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
                                itype = interactive.get("type")
                                if itype == "nfm_reply":
                                    nfm = interactive.get("nfm_reply", {})
                                    response_json = nfm.get("response_json", "{}")
                                    import json
                                    if isinstance(response_json, dict):
                                        interactive_payload = response_json
                                        text_body = "[FORM_SUBMITTED]"
                                    elif isinstance(response_json, str):
                                        try:
                                            interactive_payload = json.loads(response_json)
                                            text_body = "[FORM_SUBMITTED]"
                                        except Exception as parse_err:
                                            print(f"[WEBHOOK ERROR] Failed to parse nfm_reply response_json: {parse_err}, raw: {response_json}")
                                elif itype == "button_reply":
                                    btn = interactive.get("button_reply", {})
                                    text_body = btn.get("id") or btn.get("title") or ""
                                elif itype == "list_reply":
                                    lst = interactive.get("list_reply", {})
                                    text_body = lst.get("id") or lst.get("title") or ""
                                else:
                                    print(f"[WEBHOOK UNHANDLED INTERACTIVE] type={itype}, data={interactive}")
                            elif msg_type == "button":
                                btn = message.get("button", {})
                                text_body = btn.get("payload") or btn.get("text") or ""
                            elif msg_type == "image":
                                img_obj = message.get("image", {})
                                caption = img_obj.get("caption", "")
                                text_body = caption or "[IMAGE_RECEIVED]"
                                interactive_payload = {
                                    "photo_picker": [{
                                        "id": img_obj.get("id"),
                                        "mime_type": img_obj.get("mime_type", "image/jpeg"),
                                        "file_name": f"{img_obj.get('id')}.jpg"
                                    }]
                                }
                            elif msg_type == "document":
                                doc_obj = message.get("document", {})
                                caption = doc_obj.get("caption", "")
                                text_body = caption or "[DOCUMENT_RECEIVED]"
                                interactive_payload = {
                                    "photo_picker": [{
                                        "id": doc_obj.get("id"),
                                        "mime_type": doc_obj.get("mime_type", "image/jpeg"),
                                        "file_name": doc_obj.get("filename", f"{doc_obj.get('id')}.jpg")
                                    }]
                                }
                            
                            if not text_body:
                                print(f"[WEBHOOK SKIP] Unhandled message format: {message}")
                                continue

                            print(f"[RECV] Message from {sender_phone}: {text_body}")
                            
                            # Process WhatsApp message synchronously to keep Cloud Run CPU at 100%
                            # Deterministic pipeline completes in ~2-3 seconds, well within Meta's 20s SLA
                            process_webhook_message(sender_phone, text_body, interactive_payload)
    except Exception as e:
        print(f"[WEBHOOK CRITICAL ERROR] {e}")
        traceback.print_exc()

    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
