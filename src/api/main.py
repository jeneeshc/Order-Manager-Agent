import os
from fastapi import FastAPI, Request, HTTPException
import uvicorn
from dotenv import load_dotenv

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from src.services.whatsapp import WhatsAppService
from src.services.sheets import GoogleSheetsService
from src.services.memory import MemoryService
from src.services.audio import AudioTranscriptionService

# Load environment configuration
load_dotenv()
app = FastAPI(title="CJS Designs - WhatsApp Agent Webhook")

# Initialize robust service integrations
whatsapp_service = WhatsAppService()
db_service = GoogleSheetsService()
memory_service = MemoryService()
audio_service = AudioTranscriptionService()

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
                        text_body = None
                        
                        # --- Handle Text Messages ---
                        if "text" in msg:
                            text_body = msg["text"]["body"]
                            print(f"\n[WEBHOOK] Incoming text from {sender_phone}: '{text_body}'\n")

                        # --- Handle Voice / Audio Messages ---
                        elif "audio" in msg:
                            media_id = msg["audio"].get("id")
                            mime_type = msg["audio"].get("mime_type", "audio/ogg")
                            print(f"\n[WEBHOOK] Incoming voice note from {sender_phone} (media_id: {media_id})\n")
                            
                            # Step 1: Download from WhatsApp servers
                            audio_bytes, detected_mime = whatsapp_service.download_media(media_id)
                            if detected_mime: mime_type = detected_mime
                            
                            if audio_bytes:
                                # Step 2: Transcribe Malayalam via Gemini
                                whatsapp_service.send_text_message(sender_phone, "🎙️ Voice note received! Transcribing your Malayalam message...")
                                text_body, full_transcript = audio_service.transcribe(audio_bytes, mime_type)
                                
                                if text_body:
                                    # Echo the transcription so Siny can verify it was understood correctly
                                    whatsapp_service.send_text_message(
                                        sender_phone,
                                        f"📝 *Heard:* {text_body}"
                                    )
                                    print(f"[WEBHOOK] Transcribed voice to: '{text_body}'")
                                else:
                                    whatsapp_service.send_text_message(sender_phone, "⚠️ Sorry, I could not understand the voice message. Please try again or type your order.")
                            else:
                                whatsapp_service.send_text_message(sender_phone, "⚠️ Could not download the voice message. Please try again.")
                        
                        if not text_body:
                            continue  # Skip non-text/audio messages (images, stickers, etc.)
                        
                        print(f"[WEBHOOK] Processing message body: '{text_body}'")
                        
                        # ✨ 2. The Core Execution: Invoke Agents ✨
                        # Attempt to restore the user's previous context from memory amnesia 
                        prior_state_dict = memory_service.get_state(sender_phone)
                        
                        if prior_state_dict:
                            print(f"[MEMORY] Resuming context for {sender_phone}...")
                            initial_state = AgentState(**prior_state_dict)
                            initial_state.raw_message = text_body # Specifically inject the newest message
                        else:
                            print(f"[MEMORY] Starting fresh session for {sender_phone}...")
                            initial_state = AgentState(raw_message=text_body, sender_id=sender_phone)
                        
                        # Start Graph cascading sequence
                        final_state_dict = cjs_bot.invoke(initial_state)
                        
                        # ✨ NEW: Intercept Status Overrides BEFORE Normal Logic! ✨
                        if final_state_dict.get("is_status_update"):
                            success = db_service.update_order_status(
                                final_state_dict.get("order_id"), 
                                final_state_dict.get("new_invoice_status")
                            )
                            memory_service.clear_state(sender_phone)
                            
                            if success:
                                msg = f"✅ Success: Order {final_state_dict.get('order_id')} securely marked as {final_state_dict.get('new_invoice_status')} in Siny's Database!"
                            else:
                                msg = f"❌ Error: Could not find order {final_state_dict.get('order_id')} natively in the active database."
                                
                            whatsapp_service.send_text_message(sender_phone, msg)
                            return {"status": "received"}
                        
                        # ✨ NEW: Intercept RAG Explanation Requests! ✨
                        if final_state_dict.get("is_explanation_request"):
                            target_order_id = final_state_dict.get("order_id")
                            memory_service.clear_state(sender_phone)
                            historical = db_service.get_order(target_order_id)
                            
                            if historical and historical.get("reasoning"):
                                raw_log = historical["reasoning"]
                                msg = (
                                    f"📋 *Reasoning Log for Order {target_order_id}*\n"
                                    f"────────────────────────────\n"
                                    f"{raw_log}\n"
                                    f"────────────────────────────\n"
                                    f"📅 Order Date: {historical.get('date', 'Unknown')}\n"
                                    f"🧵 Fabric: {historical.get('fabric_type')} | Style: {historical.get('embroidery_type')}\n"
                                    f"📦 Stitches: {historical.get('stitch_count')} | Machine: {historical.get('machine_assigned')}\n"
                                    f"💰 Cost: {historical.get('cost')} | Status: {historical.get('status')}\n"
                                    f"🗓️ Delivery: {historical.get('completion_date')}"
                                )
                            elif historical:
                                msg = f"⚠️ Order {target_order_id} was found in the database but has no reasoning log recorded in Column K. It may have been created before this feature was enabled."
                            else:
                                msg = f"❌ Could not find order {target_order_id} in the database."
                                
                            whatsapp_service.send_text_message(sender_phone, msg)
                            return {"status": "received"}
                        
                        # ✨ NEW: Intercept Manual Field Override Commands! ✨
                        if final_state_dict.get("is_field_override"):
                            oid = final_state_dict.get("order_id")
                            field = final_state_dict.get("override_field")
                            value = final_state_dict.get("override_value")
                            memory_service.clear_state(sender_phone)
                            
                            success = db_service.update_order_field(oid, field, value)
                            
                            FIELD_LABELS = {
                                "delivery_date": "Override Delivery Date (Col M)",
                                "cost": "Override Cost (Col N)",
                                "machine": "Override Machine (Col O)",
                            }
                            label = FIELD_LABELS.get(field, field)
                            
                            if success:
                                msg = (f"✅ Override applied!\n"
                                       f"• Order: {oid}\n"
                                       f"• Field: {label}\n"
                                       f"• New Value: {value}\n"
                                       f"📝 Reasoning log (Col K) updated with timestamp.")
                            else:
                                msg = f"❌ Override failed: Could not find order {oid} in the database, or the field '{field}' is not recognised."
                                
                            whatsapp_service.send_text_message(sender_phone, msg)
                            return {"status": "received"}
                        
                        # ✨ Intercept Payment Queries (Completed but unpaid orders)! ✨
                        if final_state_dict.get("is_payment_query"):
                            memory_service.clear_state(sender_phone)
                            pending = db_service.get_pending_payments()
                            
                            if not pending:
                                msg = "✅ Great news! There are currently no orders with 'Completed' status pending payment."
                            else:
                                lines = ["💳 *Pending Payments Summary*\n────────────────────────────"]
                                grand_total = 0.0
                                
                                for customer, orders in pending.items():
                                    phone = orders[0].get("phone", "")
                                    lines.append(f"\n👤 *{customer}* ({phone})")
                                    subtotal = 0.0
                                    for o in orders:
                                        cost_str = o.get("cost", "Rs 0")
                                        # Parse numeric value from 'Rs 160.0'
                                        try:
                                            cost_val = float(cost_str.replace("Rs", "").strip())
                                        except:
                                            cost_val = 0.0
                                        subtotal += cost_val
                                        lines.append(
                                            f"  • {o['order_id']} — {o['embroidery_type']} on {o['fabric_type']} — {cost_str} (Due: {o['delivery_date']})"
                                        )
                                    lines.append(f"  *Subtotal: Rs {subtotal:.1f}*")
                                    grand_total += subtotal
                                
                                lines.append(f"\n────────────────────────────")
                                lines.append(f"💰 *Grand Total Pending: Rs {grand_total:.1f}*")
                                msg = "\n".join(lines)
                            
                            whatsapp_service.send_text_message(sender_phone, msg)
                            return {"status": "received"}
                        
                        # 3. Handle End States & Logic Responses
                        if final_state_dict.get("is_missing_info"):
                            # Agent 1 determined it needed more info. Save memory so it doesn't forget!
                            memory_service.save_state(sender_phone, final_state_dict)
                            whatsapp_service.send_text_message(sender_phone, final_state_dict.get("missing_fields_prompt"))
                        else:
                            # Data extraction was perfect. Agent 2 & 3 ran math. 
                            # Clear the conversation state!
                            memory_service.clear_state(sender_phone)
                            
                            rebuilt_state = AgentState(**final_state_dict)
                            order_id = db_service.append_order(rebuilt_state)
                            
                            # Agent replies directly back to phone with estimate
                            quote = (f"✅ Computation Complete!\n"
                                     f"• Cost Estimate: Rs {rebuilt_state.total_cost_rs}\n"
                                     f"• Complete By: {rebuilt_state.estimated_completion_date}\n"
                                     f"• Machine Chosen: {rebuilt_state.machine_assigned}\n"
                                     f"• Invoice Status: {rebuilt_state.invoice_status}\n"
                                     f"• Saved To DB: {order_id}")
                            whatsapp_service.send_text_message(sender_phone, quote)
                                
        except Exception as e:
            print(f"[ERROR] Failed Webhook execution sequence: {e}")
            
    return {"status": "received"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
