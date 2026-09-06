import os
from pydantic import BaseModel, Field
from typing import Optional
from src.agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from src.services.sheets import GoogleSheetsService

class OrderExtractionModel(BaseModel):
    """Structured extraction of order details from WhatsApp messages."""
    customer_name: Optional[str] = Field(None, description="Customer name.")
    order_type: Optional[str] = Field(None, description="Order type: 'Machine Embroidery' or 'Embroidery design'.")
    template_name: Optional[str] = Field(None, description="Template name (e.g. Saree Border, Kurti Neck, Logo, Baptism, Vector Digitizing).")
    fabric_type: Optional[str] = Field(None, description="Legacy fabric/material type if mentioned.")
    embroidery_type: Optional[str] = Field(None, description="Legacy embroidery style if mentioned.")
    stitch_count: Optional[int] = Field(None, description="Total stitch count (numeric, not needed for Embroidery design).")
    labor_hours: Optional[float] = Field(None, description="Labor hours or hours required to complete the work (numeric).")
    quantity: Optional[int] = Field(1, description="Total number of items (numeric, default 1).")
    requested_delivery_date: Optional[str] = Field(None, description="Delivery date/day.")
    referenced_order_id: Optional[str] = Field(None, description="Existing Order ID (e.g., CJS-12345) mentioned.")
    mark_as_invoiced: bool = Field(False, description="True if asked to mark order as invoiced.")
    mark_as_completed: bool = Field(False, description="True if asked to mark a specific order as complete/completed.")
    explain_reasoning: bool = Field(False, description="True if asked to explain logic/math.")
    is_field_override: bool = Field(False, description="True if manually changing a field on an existing order.")
    override_field: Optional[str] = Field(None, description="Field to override ('delivery_date', 'cost', or 'machine').")
    override_value: Optional[str] = Field(None, description="New value for the override.")
    is_payment_query: bool = Field(False, description="True if asking about payments/unpaid orders.")
    is_secretary_query: bool = Field(False, description="True if asking for a daily summary, work update, or tasks for today (secretary function).")
    is_pending_invoicing_query: bool = Field(False, description="True if asking for details/report of orders pending for invoicing.")
    is_invoicing_done_update: bool = Field(False, description="True if indicating that invoicing/billing is done/completed (either for a particular customer or for all customers).")
    invoicing_done_customer: Optional[str] = Field(None, description="The customer name for whom invoicing is done, or 'all' if for all customers.")
    confirm_duplicate: bool = Field(False, description="True ONLY if the bot previously warned about a similar order and the user explicitly replied 'create new' or 'yes'. False for all fresh orders.")
    is_missing_info: bool = Field(False, description="True if info is missing and not an update/query.")
    missing_fields_prompt: Optional[str] = Field(None, description="Helpful prompt for missing fields.")

def sanitize_customer_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name_clean = name.strip()
    if name_clean.lower() in {"unknown", "none", "unknown name", "new customer", "unknown customer", "n/a", "null", "undefined", ""}:
        return None
    return name_clean

MAIN_MENU_TEXT = (
    "🧵 *CJS Designs — Order Manager* 🧵\n"
    "Hello Boss! How can I assist you today? Please reply with a number:\n\n"
    "1️⃣ *New Order Form* (Customer, Order Type & Template dropdowns)\n"
    "2️⃣ *Adjust Existing Order* (Change Date, Machine, Cost, or Reasoning)\n"
    "3️⃣ *Invoicing & Billing* (Pending Invoices, Mark Invoiced/Paid, Debtors)\n"
    "4️⃣ *Daily Briefing & Tasks* (Today's summary, queues, and reminders)\n"
    "5️⃣ *Vendors & Expenses* (View suppliers or recent cash outflows)\n\n"
    "_Reply with the number (e.g. 1, 2) or type a command directly._"
)

ADJUST_MENU_TEXT = (
    "⚙️ *Order Adjustments Menu*\n"
    "Boss, which adjustment would you like to make?\n\n"
    "1️⃣ *Change Delivery Date* (Code: 21)\n"
    "2️⃣ *Reassign Machine* — Ricoma ↔ Aakruthi (Code: 22)\n"
    "3️⃣ *Override Cost* — Manual quote / discount (Code: 23)\n"
    "4️⃣ *Explain Reasoning* — Audit schedule & pricing math (Code: 24)\n"
    "0️⃣ *Back to Main Menu*\n\n"
    "_Reply with a number (e.g., 1 or 21)_"
)

INVOICING_MENU_TEXT = (
    "📋 *Invoicing & Billing Menu*\n"
    "Boss, what financial action would you like to take?\n\n"
    "1️⃣ *Pending Invoicing Report* — Completed orders awaiting bill (Code: 31)\n"
    "2️⃣ *Mark Order as Invoiced* (Code: 32)\n"
    "3️⃣ *Mark Order as Paid / Completed* (Code: 33)\n"
    "4️⃣ *Debtors & Pending Dues* — Who owes us money? (Code: 34)\n"
    "0️⃣ *Back to Main Menu*\n\n"
    "_Reply with a number (e.g., 1 or 31)_"
)

VENDORS_MENU_TEXT = (
    "🏢 *Vendors & Expenses Menu*\n"
    "Boss, please select an option:\n\n"
    "1️⃣ *Active Vendors Directory* (Code: 51)\n"
    "2️⃣ *Recent Expenses* — Latest purchase records (Code: 52)\n"
    "0️⃣ *Back to Main Menu*\n\n"
    "_Reply with a number (e.g., 1 or 51)_"
)

def render_active_orders_prompt(title: str, db: GoogleSheetsService):
    active_orders = db.get_active_orders_summary(limit=5)
    if not active_orders:
        return None, (
            "Boss, there are no active orders in the queue right now! 📭\n"
            "Reply *'Hi'* to return to the main menu."
        )
    lines = [f"{title}\n"]
    for idx, o in enumerate(active_orders, 1):
        lines.append(
            f"{idx}️⃣ *{o['order_id']}* — {o['customer']} ({o['fabric']}, {o['embroidery']}) | Due: {o['delivery_date']} | Machine: {o['machine']}"
        )
    lines.append("0️⃣ *Back to Main Menu*\n")
    lines.append(f"_Reply with the number (1-{len(active_orders)}) or type the Order ID._")
    return active_orders, "\n".join(lines)

def resolve_selected_order(raw_msg: str, active_orders: list) -> Optional[str]:
    msg = raw_msg.strip()
    if msg.isdigit():
        idx = int(msg)
        if 1 <= idx <= len(active_orders):
            return active_orders[idx - 1]["order_id"]
    if msg.upper().startswith("CJS-"):
        return msg.upper()
    return None

class OrderCollectorAgent:
    def __init__(self):
        self.name = "Order Collector Agent"
        
        # Initialize cleanly via API Studio explicitly pointing to the GEMINI_API_KEY constant!
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0
        )
        
        # Connect the Pydantic structured output constraint
        self.extractor = self.llm.with_structured_output(OrderExtractionModel)

    def process(self, state: AgentState) -> AgentState:
        raw_msg = (state.raw_message or "").strip()
        msg_lower = raw_msg.lower()

        # 0. Global Cancellation & Exit
        if msg_lower in {"cancel", "exit", "stop"}:
            state.active_menu = None
            state.pending_adjustment_type = None
            state.pending_adjustment_order_id = None
            state.final_reply = "Operation cancelled, Boss. Reply *'Hi'* anytime to see the menu. 👍"
            return state

        # 0.1 Greetings / Main Menu Trigger
        if msg_lower in {"hi", "hello", "menu", "help", "start", "hey"}:
            state.active_menu = "MAIN"
            state.pending_adjustment_type = None
            state.pending_adjustment_order_id = None
            state.final_reply = MAIN_MENU_TEXT
            return state

        # 0.2 Return to Main Menu (0 pressed from any sub-state)
        if raw_msg == "0" and state.active_menu:
            state.active_menu = "MAIN"
            state.pending_adjustment_type = None
            state.pending_adjustment_order_id = None
            state.final_reply = MAIN_MENU_TEXT
            return state

        db = GoogleSheetsService()

        # 0.3 Direct Fast-Action Codes (Can be invoked from anywhere)
        if raw_msg == "21" or (state.active_menu == "ADJUST" and raw_msg == "1"):
            orders, prompt_text = render_active_orders_prompt("📅 *Select Order to Change Delivery Date:*", db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_DATE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "22" or (state.active_menu == "ADJUST" and raw_msg == "2"):
            orders, prompt_text = render_active_orders_prompt("🧵 *Select Order to Reassign Machine:*", db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_MACHINE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "23" or (state.active_menu == "ADJUST" and raw_msg == "3"):
            orders, prompt_text = render_active_orders_prompt("💰 *Select Order to Override Cost:*", db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_COST"
            state.final_reply = prompt_text
            return state

        if raw_msg == "24" or (state.active_menu == "ADJUST" and raw_msg == "4"):
            orders, prompt_text = render_active_orders_prompt("🔍 *Select Order to Review Reasoning Log:*", db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_EXPLAIN"
            state.final_reply = prompt_text
            return state

        if raw_msg == "31" or (state.active_menu == "INVOICING" and raw_msg == "1"):
            state.is_pending_invoicing_query = True
            state.active_menu = None
            return state

        if raw_msg == "32" or (state.active_menu == "INVOICING" and raw_msg == "2"):
            orders, prompt_text = render_active_orders_prompt("📋 *Select Order to Mark as Invoiced:*", db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_TO_INVOICE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "33" or (state.active_menu == "INVOICING" and raw_msg == "3"):
            orders, prompt_text = render_active_orders_prompt("✅ *Select Order to Mark as Completed / Paid:*", db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_TO_COMPLETE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "34" or (state.active_menu == "INVOICING" and raw_msg == "4"):
            state.is_payment_query = True
            state.active_menu = None
            return state

        if raw_msg == "51" or (state.active_menu == "VENDORS" and raw_msg == "1"):
            vendors = db.get_all_vendors()
            if not vendors:
                state.final_reply = "Boss, no vendors are currently registered in 'Vendors' tab."
            else:
                v_lines = []
                for v in vendors:
                    v_lines.append(f"• *{v.get('name', 'Unknown')}* ({v.get('category', 'General')}) — Ph: {v.get('phone', 'N/A')}")
                state.final_reply = "🧵 *Active Vendors Directory*\n\n" + "\n".join(v_lines)
            state.active_menu = None
            return state

        if raw_msg == "52" or (state.active_menu == "VENDORS" and raw_msg == "2"):
            expenses = db.get_recent_expenses(limit=5)
            if not expenses:
                state.final_reply = "Boss, no recent expenses found in 'Expense_Ledger'."
            else:
                e_lines = []
                for e in expenses:
                    e_lines.append(f"• *{e.get('date', '')}*: Rs {e.get('amount', 0)} — {e.get('description', '')} ({e.get('category', '')})")
                state.final_reply = "💸 *Recent Expenses (Expense Ledger)*\n\n" + "\n".join(e_lines)
            state.active_menu = None
            return state

        # 0.4 Handling Main Menu numeric choices & direct intents
        if state.active_menu == "MAIN" or (not state.active_menu and raw_msg in {"1", "2", "3", "4", "5"}) or msg_lower in {"new order", "create order", "order form", "open form"}:
            if raw_msg == "1" or msg_lower in {"1", "new order", "create order", "order form", "open form"}:
                state.send_order_form = True
                state.active_menu = None
                state.final_reply = (
                    "Opening WhatsApp Order Form for you, Boss! 📋\n"
                    "Please fill in customer name, order type, template, and quantity."
                )
                return state
            elif raw_msg == "2":
                state.active_menu = "ADJUST"
                state.final_reply = ADJUST_MENU_TEXT
                return state
            elif raw_msg == "3":
                state.active_menu = "INVOICING"
                state.final_reply = INVOICING_MENU_TEXT
                return state
            elif raw_msg == "4":
                state.is_secretary_query = True
                state.active_menu = None
                return state
            elif raw_msg == "5":
                state.active_menu = "VENDORS"
                state.final_reply = VENDORS_MENU_TEXT
                return state

        # 0.5 Handling Selection States (Order selection & input prompts)
        if state.active_menu == "SELECT_ORDER_FOR_DATE":
            orders = db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.pending_adjustment_order_id = target_id
                state.pending_adjustment_type = "delivery_date"
                state.active_menu = "INPUT_NEW_DATE"
                state.final_reply = f"Selected order *{target_id}*.\nPlease reply with the new delivery date (e.g. *2026-09-15* or *Friday*):"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "INPUT_NEW_DATE":
            new_date = raw_msg
            target_oid = state.pending_adjustment_order_id
            state.is_field_override = True
            state.order_id = target_oid
            state.override_field = "delivery_date"
            state.override_value = new_date
            state.active_menu = None
            state.pending_adjustment_order_id = None
            state.pending_adjustment_type = None
            state.final_reply = f"✅ *Field Updated!*\nOrder *{target_oid}* — *Delivery Date* has been updated to *{new_date}*. 📅"
            return state

        if state.active_menu == "SELECT_ORDER_FOR_MACHINE":
            orders = db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.pending_adjustment_order_id = target_id
                state.pending_adjustment_type = "machine"
                state.active_menu = "SELECT_MACHINE_CHOICE"
                state.final_reply = (
                    f"Selected order *{target_id}*.\n"
                    f"Which machine would you like to assign?\n\n"
                    f"1️⃣ *Ricoma*\n"
                    f"2️⃣ *Aakruthi*\n"
                    f"0️⃣ *Cancel*\n\n"
                    f"_Reply 1 or 2._"
                )
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "SELECT_MACHINE_CHOICE":
            if raw_msg == "1":
                machine = "Ricoma"
            elif raw_msg == "2":
                machine = "Aakruthi"
            elif msg_lower in ("ricoma", "aakruthi"):
                machine = raw_msg.title()
            else:
                state.final_reply = "Please reply with *1* for Ricoma or *2* for Aakruthi (or '0' to cancel)."
                return state
            target_oid = state.pending_adjustment_order_id
            state.is_field_override = True
            state.order_id = target_oid
            state.override_field = "machine"
            state.override_value = machine
            state.active_menu = None
            state.pending_adjustment_order_id = None
            state.pending_adjustment_type = None
            state.final_reply = f"✅ *Machine Reassigned!*\nOrder *{target_oid}* has been reassigned to *{machine}*. 🧵"
            return state

        if state.active_menu == "SELECT_ORDER_FOR_COST":
            orders = db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.pending_adjustment_order_id = target_id
                state.pending_adjustment_type = "cost"
                state.active_menu = "INPUT_NEW_COST"
                state.final_reply = f"Selected order *{target_id}*.\nPlease reply with the new total cost in Rs (e.g. *650*):"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "INPUT_NEW_COST":
            cost_str = "".join(c for c in raw_msg if c.isdigit() or c == '.')
            if not cost_str:
                cost_str = raw_msg
            target_oid = state.pending_adjustment_order_id
            state.is_field_override = True
            state.order_id = target_oid
            state.override_field = "cost"
            state.override_value = f"Rs {cost_str}"
            state.active_menu = None
            state.pending_adjustment_order_id = None
            state.pending_adjustment_type = None
            state.final_reply = f"✅ *Cost Updated!*\nOrder *{target_oid}* — *Cost* has been updated to *Rs {cost_str}*. 💰"
            return state

        if state.active_menu == "SELECT_ORDER_FOR_EXPLAIN":
            orders = db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.is_explanation_request = True
                state.order_id = target_id
                state.active_menu = None
                state.pending_adjustment_order_id = None
                state.final_reply = (
                    f"🔍 *Order Reasoning — {target_id}*\n\n"
                    f"I've retrieved the full agent decision log for this order. "
                    f"You can review the scheduling, costing, and machine assignment reasoning in your Orders sheet, Column L."
                )
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "SELECT_ORDER_TO_INVOICE":
            orders = db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.is_status_update = True
                state.new_invoice_status = "Invoiced"
                state.order_id = target_id
                state.active_menu = None
                state.final_reply = f"✅ *Status Updated!*\nOrder *{target_id}* has been marked as *Invoiced*. 📋"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "SELECT_ORDER_TO_COMPLETE":
            orders = db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.is_status_update = True
                state.new_invoice_status = "Completed"
                state.order_id = target_id
                state.active_menu = None
                state.final_reply = f"✅ *Status Updated!*\nOrder *{target_id}* has been marked as *Completed*. 📋"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        # Clear active menu if unrecognized text was sent (e.g. Boss typed a freeform order or intent)
        state.active_menu = None
        state.pending_adjustment_type = None
        state.pending_adjustment_order_id = None

        print(f"[{self.name}] Activating Gemini LLM on: {state.raw_message}")
        
        # Build prompt focused strictly on extraction results
        prompt = f"""Extract order details from this WhatsApp message: "{state.raw_message}"
        
        PRIOR KNOWLEDGE EXTRACTED: 
        (If you already have these, do not extract them again!)
        - Known Customer Name: {state.customer_name or 'None'}
        - Known Fabric: {state.fabric_type or 'None'}
        - Known Embroidery: {state.embroidery_type or 'None'}
        - Known Stitches: {state.stitch_count or 'None'}
        
        INSTRUCTIONS:
        1. Extract: name, material/fabric, embroidery style, and stitch count.
        2. If "Numbers 10" or "Qty 5" is mentioned, extract that into 'quantity'.
        3. If a specific Order ID (CJS-XXXXXX) is mentioned, set 'referenced_order_id'.
        4. If the message is about daily summary or today's tasks, set 'is_secretary_query=True'.
        5. If the message is asking for details or a report of orders pending for invoicing, set 'is_pending_invoicing_query=True'.
        6. If the message indicates that invoicing is done (e.g. "invoicing is done for Anna", "invoicing done all", "invoiced Anna"), set 'is_invoicing_done_update=True' and set 'invoicing_done_customer' to the customer name (e.g., "Anna") or 'all' if for all customers.
        7. If the message asks to mark a specific order as complete or says a specific order is complete/completed (e.g., "mark CJS-7ED337 as complete", "CJS-7ED337 is complete"), set 'mark_as_completed=True' and set 'referenced_order_id' to that order ID.
        8. If hours or duration required is mentioned (e.g., "2 hours", "3 hrs labor"), extract that into 'labor_hours'.
        9. Provide a helpful 'missing_fields_prompt' if key info is still absent.
        """
        
        # Generative AI reads the human text and extracts the core fields
        raw_extraction = self.extractor.invoke(prompt)
        
        # Robustly ensure we have an OrderExtractionModel instance
        if raw_extraction is None:
            print(f"[{self.name}] LLM returned None!", flush=True)
            extraction = OrderExtractionModel()
        elif isinstance(raw_extraction, OrderExtractionModel):
            extraction = raw_extraction
        else:
            # If it's a dict or other object, convert to model
            print(f"[{self.name}] Converting dict to model...", flush=True)
            try:
                extraction = OrderExtractionModel(**dict(raw_extraction))
            except Exception as e:
                print(f"[{self.name}] Conversion failed: {e}", flush=True)
                extraction = OrderExtractionModel()
        
        # ✨ 0. Intercept explicit Database Mutation Overrides instantly! ✨
        if extraction.mark_as_invoiced and extraction.referenced_order_id:
            state.is_status_update = True
            state.new_invoice_status = "Invoiced"
            state.order_id = extraction.referenced_order_id
            state.final_reply = (
                f"✅ *Status Updated!*\n"
                f"Order *{extraction.referenced_order_id}* has been marked as *Invoiced*. 📋"
            )
            return state

        # ✨ 0.1 Intercept explicit mark as completed overrides instantly! ✨
        if extraction.mark_as_completed and extraction.referenced_order_id:
            state.is_status_update = True
            state.new_invoice_status = "Completed"
            state.order_id = extraction.referenced_order_id
            state.final_reply = (
                f"✅ *Status Updated!*\n"
                f"Order *{extraction.referenced_order_id}* has been marked as *Completed*. 📋"
            )
            return state
            
        # ✨ 0.5 Intercept RAG History Explanations instantly! ✨
        if extraction.explain_reasoning and extraction.referenced_order_id:
            state.is_explanation_request = True
            state.order_id = extraction.referenced_order_id
            state.final_reply = (
                f"🔍 *Order Reasoning — {extraction.referenced_order_id}*\n\n"
                f"I've retrieved the full agent decision log for this order. "
                f"You can review the scheduling, costing, and machine assignment reasoning in your Orders sheet, Column L."
            )
            return state

        # ✨ 0.6 Intercept Manual Field Override commands! ✨
        if extraction.is_field_override and extraction.referenced_order_id and extraction.override_field and extraction.override_value:
            state.is_field_override = True
            state.order_id = extraction.referenced_order_id
            state.override_field = extraction.override_field
            state.override_value = extraction.override_value
            state.final_reply = (
                f"✅ *Field Updated!*\n"
                f"Order *{extraction.referenced_order_id}* — "
                f"*{extraction.override_field.replace('_', ' ').title()}* has been updated to *{extraction.override_value}*. ✏️"
            )
            return state

        # ✨ 0.7 Intercept Payment Query! ✨
        if extraction.is_payment_query:
            state.is_payment_query = True
            if not (extraction.customer_name or extraction.fabric_type or extraction.embroidery_type or extraction.stitch_count):
                return state
            
        # ✨ 0.8 Intercept Secretary Query! ✨
        if extraction.is_secretary_query:
            state.is_secretary_query = True
            if not (extraction.customer_name or extraction.fabric_type or extraction.embroidery_type or extraction.stitch_count):
                return state

        # ✨ 0.9 Intercept Pending Invoicing Query! ✨
        if extraction.is_pending_invoicing_query:
            state.is_pending_invoicing_query = True
            return state

        # ✨ 0.95 Intercept Invoicing Done Update! ✨
        if extraction.is_invoicing_done_update:
            state.is_invoicing_done_update = True
            state.invoicing_done_customer = extraction.invoicing_done_customer
            return state
        
        # Hydrate from Google Sheets if an Order ID was parsed!
        if extraction.referenced_order_id:
            print(f"[{self.name}] Connecting to Database to hydrate context for {extraction.referenced_order_id}...")
            db = GoogleSheetsService()
            historical_db_order = db.get_order(extraction.referenced_order_id)
            
            if historical_db_order:
                # Inject DB parameters unless the AI successfully extracted a NEW override from the chat!
                state.order_id = extraction.referenced_order_id
                state.fabric_type = extraction.fabric_type or historical_db_order.get("fabric_type")
                state.embroidery_type = extraction.embroidery_type or historical_db_order.get("embroidery_type")
                state.stitch_count = extraction.stitch_count or historical_db_order.get("stitch_count")
                
                # Hydrate customer details from historical order
                hist_cid = historical_db_order.get("customer_id")
                if hist_cid:
                    state.customer_id = hist_cid
                    cust_map = db.get_all_customers_map()
                    state.customer_name = cust_map.get(hist_cid, state.customer_name)
            else:
                print(f"[{self.name}] DB order not found. Falling back to chat extraction exclusively.")
        
        # Hydrate customer_name from extraction and look up ID
        sanitized_name = sanitize_customer_name(extraction.customer_name or state.customer_name)
        if sanitized_name:
            state.customer_name = sanitized_name
            db = GoogleSheetsService()
            cid = db.create_customer_if_not_exists(sanitized_name)
            if cid:
                print(f"[{self.name}] Linked/Registered Customer '{sanitized_name}' to ID: {cid}")
                state.customer_id = cid
            else:
                print(f"[{self.name}] Failed to resolve Customer ID for '{sanitized_name}'.")
                state.customer_id = None
        else:
            state.customer_name = None
            state.customer_id = None

        # Safely hydrate state if AI explicitly extracted something NEW
        if extraction.order_type:
            state.order_type = extraction.order_type
        if extraction.template_name:
            state.template_name = extraction.template_name
        if extraction.fabric_type:
            state.fabric_type = extraction.fabric_type
            if not state.order_type:
                state.order_type = "Machine Embroidery"
        if extraction.embroidery_type:
            state.embroidery_type = extraction.embroidery_type
            if not state.template_name:
                state.template_name = extraction.embroidery_type
        if extraction.stitch_count is not None:
            state.stitch_count = extraction.stitch_count

        if extraction.requested_delivery_date:
            state.requested_delivery_date = extraction.requested_delivery_date
            
        if extraction.quantity:
            state.quantity = extraction.quantity
            
        if extraction.labor_hours is not None:
            state.labor_hours = extraction.labor_hours
        elif state.template_name and not state.labor_hours:
            # Pre-populate default labor hours from Description_Templates
            db = GoogleSheetsService()
            tmpl = db.get_template_by_name(state.template_name)
            if tmpl and tmpl.get("default_labor_hours"):
                state.labor_hours = float(tmpl["default_labor_hours"])

        if extraction.confirm_duplicate:
            state.is_duplicate_confirmed = True

        # Decision Logic: requires Customer Name, Order Type, and Template Name
        missing_items = []
        if not state.customer_name: missing_items.append("customer name")
        if not state.order_type and not state.fabric_type: missing_items.append("order type")
        if not state.template_name and not state.embroidery_type: missing_items.append("template name")

        if missing_items:
            print(f"[{self.name}] Required parameters missing: {missing_items}. Returning to WhatsApp.")
            state.is_missing_info = True
            
            if len(missing_items) >= 2:
                print(f"[{self.name}] Multiple parameters missing. Triggering native WhatsApp Flow Form.")
                state.send_order_form = True
                state.missing_fields_prompt = "Triggering order form..."
            else:
                missing_str = missing_items[0]
                state.missing_fields_prompt = f"Please provide the {missing_str} to complete the order."
        else:
            # We have all required info — check for duplicates!
            if not state.is_duplicate_confirmed and not extraction.referenced_order_id:
                db = GoogleSheetsService()
                similar_order = db.find_similar_order(
                    state.customer_id or state.customer_name, state.fabric_type or state.order_type, state.embroidery_type or state.template_name, state.stitch_count or 0
                )
                if similar_order:
                    print(f"[{self.name}] Similar order detected! Prompting Boss for update vs create new choice.")
                    state.is_missing_info = True
                    o_id = similar_order.get("order_id", "Unknown")
                    o_date = similar_order.get("date", "recently")
                    o_stitch = similar_order.get("stitches", state.stitch_count)
                    o_style = similar_order.get("style", state.template_name or state.embroidery_type)
                    
                    state.missing_fields_prompt = f"I found a ~90% similar order for {state.customer_name} from {o_date}: Order *{o_id}* ({o_stitch} stitches of {o_style}).\n\nWould you like to update this existing order (reply *'update {o_id}'*), or create a brand new one (reply *'create new'*)"
                    return state

            # Passes all checks
            state.is_missing_info = False

        # Write Agent 1 Log to Column O (reasoning)
        agent_log = f"\n[Collector Agent]: Customer='{state.customer_name}', Order Type='{state.order_type}', Template='{state.template_name}', Qty={state.quantity}, Stitches={state.stitch_count}, LaborHrs={state.labor_hours}.\n"
        state.aggregated_reasoning = (state.aggregated_reasoning or "") + agent_log

        print(f"[{self.name}] Aggregated Extraction Output -> Customer: {state.customer_name}, Order Type: {state.order_type}, Template: {state.template_name}, Qty: {state.quantity}, Stitches: {state.stitch_count}")
        return state
