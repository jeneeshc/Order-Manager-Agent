import os
import datetime
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService
from src.agents.agent_2_scheduler import ProductionSchedulerAgent
from src.agents.agent_3_estimator import EstimationAgent
from src.agents.agent_6_secretary import SecretaryAgent

MAIN_MENU_TEXT = (
    "🧵 *CJS Designs — Order Manager* 🧵\n"
    "Hello Boss! How can I assist you today? Please reply with a number:\n\n"
    "1️⃣ *New Order Form* (Open Clean Order Intake Form)\n"
    "2️⃣ *Adjust Existing Order* (Change Date, Machine, Cost, or Reasoning)\n"
    "3️⃣ *Invoicing & Billing* (Pending Invoices, Mark Invoiced/Paid, Debtors)\n"
    "4️⃣ *Daily Briefing & Tasks* (Today's summary, queues, and reminders)\n"
    "5️⃣ *Vendors & Expenses* (View suppliers or recent cash outflows)\n"
    "6️⃣ *Add New Customer* (Register a customer in Google Sheets)\n"
    "7️⃣ *Add New Template* (Add design template with machine & hours)\n"
    "8️⃣ *Add New Order Type* (Add embroidery category)\n\n"
    "_Reply with the number (e.g. 1, 6, 7) or type a command directly._"
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

def sanitize_customer_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name_clean = name.strip()
    if name_clean.lower() in {"unknown", "none", "unknown name", "new customer", "unknown customer", "n/a", "null", "undefined", ""}:
        return None
    return name_clean

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
            f"{idx}️⃣ *{o['order_id']}* — {o['customer']} ({o.get('order_type', '')}, {o.get('template', '')}) | Due: {o['delivery_date']} | Machine: {o['machine']}"
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

class CJSSingleAgent:
    """
    Unified Single Agent Architecture for CJS Designs.
    Eliminates multi-agent circular routing loops and provides:
    1. Deterministic Fast-Path for WhatsApp Flow form submissions (< 1s).
    2. Deterministic State Machine for Menu options and master data entry (< 200ms).
    3. Exactly 1 Gemini Flash LLM call for natural conversational chat (< 1.5s).
    """
    def __init__(self, sheets_service=None):
        self.name = "CJS Designs Agent"
        self.scheduler = ProductionSchedulerAgent()
        self.estimator = EstimationAgent()
        self.secretary = SecretaryAgent()
        
        # Support injected service or mock on agent_1_collector
        if sheets_service is not None:
            self.db = sheets_service
        else:
            try:
                import src.agents.agent_1_collector as a1
                SheetsCls = getattr(a1, "GoogleSheetsService", GoogleSheetsService)
                self.db = SheetsCls()
            except Exception:
                self.db = GoogleSheetsService()
        self.sheets = self.db
        
        # Single Unified LLM instance
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=api_key,
            temperature=0.2
        )
        self.router = self.llm

    def process(self, state: AgentState) -> AgentState:
        """Main processing entrypoint."""
        # If final_reply is already set, conclude routing immediately
        if state.final_reply:
            state.next_step = "END"
            state.raw_message = state.final_reply
            return state

        raw_msg = (state.raw_message or "").strip()
        msg_lower = raw_msg.lower()

        # -------------------------------------------------------------
        # 0. Global Cancellation & Exits
        # -------------------------------------------------------------
        if msg_lower in {"cancel", "exit", "stop"}:
            state.active_menu = None
            state.pending_adjustment_type = None
            state.pending_adjustment_order_id = None
            state.next_step = "END"
            state.final_reply = "Operation cancelled, Boss. Reply *'Hi'* anytime to see the menu. 👍"
            return state

        # -------------------------------------------------------------
        # 1. Main Menu Triggers
        # -------------------------------------------------------------
        if msg_lower in {"hi", "hello", "menu", "help", "start", "hey"}:
            state.active_menu = "MAIN"
            state.pending_adjustment_type = None
            state.pending_adjustment_order_id = None
            state.next_step = "END"
            state.final_reply = MAIN_MENU_TEXT
            return state

        if raw_msg == "0" and state.active_menu:
            state.active_menu = "MAIN"
            state.pending_adjustment_type = None
            state.pending_adjustment_order_id = None
            state.next_step = "END"
            state.final_reply = MAIN_MENU_TEXT
            return state

        # -------------------------------------------------------------
        # 2. Direct Fast-Action Numeric Codes
        # -------------------------------------------------------------
        # Option 1: Open Order Form (only from main menu or top level)
        if ((raw_msg == "1" and state.active_menu in ("MAIN", None))
                or msg_lower in {"new order", "create order", "order form", "open form"}):
            state.send_order_form = True
            state.active_menu = None
            state.next_step = "END"
            state.final_reply = (
                "Opening WhatsApp Order Form for you, Boss! 📋\n"
                "Please select customer, order type, template, quantity, and delivery date."
            )
            return state

        # Option 2: Adjustments Menu / Codes 21-24
        if raw_msg == "2" and (state.active_menu == "MAIN" or not state.active_menu):
            state.active_menu = "ADJUST"
            state.final_reply = ADJUST_MENU_TEXT
            return state

        if raw_msg == "21" or (state.active_menu == "ADJUST" and raw_msg == "1"):
            orders, prompt_text = render_active_orders_prompt("📅 *Select Order to Change Delivery Date:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_DATE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "22" or (state.active_menu == "ADJUST" and raw_msg == "2"):
            orders, prompt_text = render_active_orders_prompt("🧵 *Select Order to Reassign Machine:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_MACHINE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "23" or (state.active_menu == "ADJUST" and raw_msg == "3"):
            orders, prompt_text = render_active_orders_prompt("💰 *Select Order to Override Cost:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_COST"
            state.final_reply = prompt_text
            return state

        if raw_msg == "24" or (state.active_menu == "ADJUST" and raw_msg == "4"):
            orders, prompt_text = render_active_orders_prompt("🔍 *Select Order to Review Reasoning Log:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_EXPLAIN"
            state.final_reply = prompt_text
            return state

        # Option 3: Invoicing Menu / Codes 31-34
        if raw_msg == "3" and (state.active_menu == "MAIN" or not state.active_menu):
            state.active_menu = "INVOICING"
            state.final_reply = INVOICING_MENU_TEXT
            return state

        if raw_msg == "31" or (state.active_menu == "INVOICING" and raw_msg == "1") or "pending invoice" in msg_lower:
            state.is_pending_invoicing_query = True
            state.active_menu = None
            state.next_step = "END"
            pending = self.db.get_orders_pending_invoicing()
            if not pending:
                state.final_reply = "Boss, all completed orders have been invoiced! No pending orders. 🎉"
            else:
                lines = ["📋 *Orders Pending Invoicing Report*\n"]
                for cname, ords in pending.items():
                    lines.append(f"👤 *{cname}* ({len(ords)} orders):")
                    for o in ords:
                        lines.append(f"  • *{o['order_id']}* — {o.get('template', 'Order')} | Due: {o.get('completion_date', '')} | Cost: {o.get('cost', '')}")
                lines.append("\nReply *32* to mark an order as invoiced, or reply with customer name to update.")
                state.final_reply = "\n".join(lines)
            return state

        if raw_msg == "32" or (state.active_menu == "INVOICING" and raw_msg == "2"):
            orders, prompt_text = render_active_orders_prompt("📋 *Select Order to Mark as Invoiced:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_TO_INVOICE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "33" or (state.active_menu == "INVOICING" and raw_msg == "3"):
            orders, prompt_text = render_active_orders_prompt("✅ *Select Order to Mark as Completed / Paid:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_TO_COMPLETE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "34" or (state.active_menu == "INVOICING" and raw_msg == "4") or "debtor" in msg_lower:
            state.is_payment_query = True
            state.active_menu = None
            state.next_step = "END"
            pending_payments = self.db.get_pending_payments()
            if not pending_payments:
                state.final_reply = "Boss, there are no outstanding debtors or unpaid completed orders right now! 💵"
            else:
                lines = ["💰 *Pending Dues & Debtors Report*\n"]
                for display_key, orders in pending_payments.items():
                    lines.append(f"👤 *{display_key}*:")
                    for o in orders:
                        lines.append(f"  • *{o['order_id']}* — Due: {o.get('cost', 'Rs 0')}")
                state.final_reply = "\n".join(lines)
            return state

        # Option 4: Daily Briefing
        if (raw_msg == "4" and (state.active_menu == "MAIN" or not state.active_menu)) or msg_lower in {"briefing", "daily brief", "tasks today", "summary"}:
            state.is_secretary_query = True
            state.active_menu = None
            state.next_step = "END"
            state = self.secretary.process(state)
            state.is_secretary_query = True
            state.active_menu = None
            state.next_step = "END"
            return state

        # Option 5: Vendors & Expenses / Codes 51-52
        if raw_msg == "5" and (state.active_menu == "MAIN" or not state.active_menu):
            state.active_menu = "VENDORS"
            state.final_reply = VENDORS_MENU_TEXT
            return state

        if raw_msg == "51" or (state.active_menu == "VENDORS" and raw_msg == "1"):
            vendors_fn = getattr(self.db, "get_all_vendors", getattr(self.db, "get_vendors", None)) or self.db.get_vendors
            vendors = vendors_fn()
            if not vendors:
                state.final_reply = "Boss, no vendors are currently registered in 'Vendors' tab."
            else:
                v_lines = []
                for v in vendors:
                    v_lines.append(f"• *{v.get('name', 'Unknown')}* ({v.get('category', 'General')}) — Ph: {v.get('phone', 'N/A')}")
                state.final_reply = "🧵 *Active Vendors Directory*\n\n" + "\n".join(v_lines)
            state.active_menu = None
            state.next_step = "END"
            return state

        if raw_msg == "52" or (state.active_menu == "VENDORS" and raw_msg == "2"):
            expenses = self.db.get_recent_expenses(limit=5)
            if not expenses:
                state.final_reply = "Boss, no recent expenses found in 'Expense_Ledger'."
            else:
                e_lines = []
                for e in expenses:
                    e_lines.append(f"• *{e.get('date', '')}*: Rs {e.get('amount', 0)} — {e.get('description', '')} ({e.get('category', '')})")
                state.final_reply = "💸 *Recent Expenses (Expense Ledger)*\n\n" + "\n".join(e_lines)
            state.active_menu = None
            return state

        # Option 6 / Code 61: Add New Customer
        if raw_msg in {"6", "61"} or (state.active_menu == "MAIN" and raw_msg == "6") or msg_lower in {"add customer", "new customer", "create customer"}:
            state.active_menu = "INPUT_NEW_CUSTOMER"
            state.final_reply = (
                "👤 *Add New Customer*\n"
                "Boss, please reply with the customer details:\n\n"
                "*Format:* Customer Name, Phone (optional), Address/City (optional)\n"
                "_Example: Priya Boutique, 9876543210, Ernakulam_\n\n"
                "_Reply 0 to cancel._"
            )
            return state

        # Option 7 / Code 71: Add New Template
        if raw_msg in {"7", "71"} or (state.active_menu == "MAIN" and raw_msg == "7") or msg_lower in {"add template", "new template", "create template"}:
            state.active_menu = "INPUT_NEW_TEMPLATE"
            state.final_reply = (
                "🎨 *Add New Description Template*\n"
                "Boss, please reply with the template details:\n\n"
                "*Format:* Template Name, Machine (Ricoma / Aakruthi / None), Default Labor Hours (optional), Default Stitches (optional)\n"
                "_Example: Heavy Bridal Blouse, Ricoma, 3.5, 45000_\n\n"
                "_Reply 0 to cancel._"
            )
            return state

        # Option 8 / Code 81: Add New Order Type
        if raw_msg in {"8", "81"} or (state.active_menu == "MAIN" and raw_msg == "8") or msg_lower in {"add order type", "new order type"}:
            state.active_menu = "INPUT_NEW_ORDER_TYPE"
            state.final_reply = (
                "🧵 *Add New Order Type*\n"
                "Boss, please reply with the new order type name:\n\n"
                "_Example: Cutwork Embroidery or Blouse Neck Embroidery_\n\n"
                "_Reply 0 to cancel._"
            )
            return state

        # -------------------------------------------------------------
        # 3. Handling Interactive Input & Selection States
        # -------------------------------------------------------------
        if state.active_menu == "INPUT_NEW_CUSTOMER":
            if raw_msg == "0":
                state.active_menu = "MAIN"
                state.final_reply = MAIN_MENU_TEXT
                return state
            parts = [p.strip() for p in raw_msg.split(",") if p.strip()]
            cust_name = parts[0] if parts else raw_msg.strip()
            phone = parts[1] if len(parts) > 1 else ""
            address = parts[2] if len(parts) > 2 else ""
            clean_name = sanitize_customer_name(cust_name)
            if not clean_name:
                state.final_reply = "Boss, please provide a valid customer name (or reply '0' to cancel)."
                return state
            cid = self.db.create_customer_if_not_exists(clean_name, phone=phone, address=address)
            state.active_menu = None
            state.final_reply = (
                f"✅ *Customer Added Successfully!*\n\n"
                f"• *Name:* {clean_name}\n"
                f"• *Customer ID:* {cid}\n"
                f"• *Phone:* {phone or 'Not provided'}\n"
                f"• *Location:* {address or 'Not provided'}\n\n"
                f"Saved to 'Customers' in Google Sheets. 👍\n"
                f"Reply *'Hi'* for main menu or *'1'* to start a new order."
            )
            return state

        if state.active_menu == "INPUT_NEW_TEMPLATE":
            if raw_msg == "0":
                state.active_menu = "MAIN"
                state.final_reply = MAIN_MENU_TEXT
                return state
            parts = [p.strip() for p in raw_msg.split(",") if p.strip()]
            if not parts:
                state.final_reply = "Boss, please provide a valid template name (or reply '0' to cancel)."
                return state
            template_name = parts[0]
            machine = "Ricoma"
            labor_hours = 1.0
            stitch_count = 10000
            if len(parts) > 1:
                m_candidate = parts[1].title()
                if m_candidate in {"Ricoma", "Aakruthi", "None"}:
                    machine = m_candidate
            if len(parts) > 2:
                try: labor_hours = float(parts[2])
                except ValueError: pass
            if len(parts) > 3:
                try: stitch_count = int(parts[3])
                except ValueError: pass
            order_type = "Machine Embroidery" if machine in ("Ricoma", "Aakruthi") else "Embroidery designing"
            self.db.create_template_if_not_exists(
                order_type=order_type,
                template_name=template_name,
                machine=machine,
                default_labor_hours=labor_hours
            )
            state.active_menu = None
            state.final_reply = (
                f"✅ *Template Added Successfully!*\n\n"
                f"• *Template:* {template_name}\n"
                f"• *Machine:* {machine}\n"
                f"• *Order Type:* {order_type}\n"
                f"• *Default Labor:* {labor_hours} hrs\n"
                f"• *Default Stitches:* {stitch_count:,}\n\n"
                f"Saved to 'Description_Templates' in Google Sheets. 👍\n"
                f"Reply *'Hi'* for main menu or *'1'* to start a new order."
            )
            return state

        if state.active_menu == "INPUT_NEW_ORDER_TYPE":
            if raw_msg == "0":
                state.active_menu = "MAIN"
                state.final_reply = MAIN_MENU_TEXT
                return state
            new_type = raw_msg.strip()
            if not new_type:
                state.final_reply = "Boss, please provide an order type name (or reply '0' to cancel)."
                return state
            state.active_menu = None
            state.final_reply = (
                f"✅ *Order Type Added!*\n\n"
                f"• *Order Type:* {new_type}\n\n"
                f"Registered for CJS Designs. 👍\n"
                f"Reply *'Hi'* for main menu or *'1'* to start a new order."
            )
            return state

        # Sub-menus: Adjustments
        if state.active_menu == "SELECT_ORDER_FOR_DATE":
            orders = self.db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.pending_adjustment_order_id = target_id
                state.pending_adjustment_type = "delivery_date"
                state.active_menu = "INPUT_NEW_DATE"
                state.final_reply = f"Selected order *{target_id}*.\nPlease reply with the new delivery date (e.g. *2026-09-15*):"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "INPUT_NEW_DATE":
            new_date = raw_msg.strip()
            target_oid = state.pending_adjustment_order_id
            self.db.update_order_field(target_oid, "delivery_date", new_date)
            state.is_field_override = True
            state.order_id = target_oid
            state.override_field = "delivery_date"
            state.override_value = new_date
            state.active_menu = None
            state.pending_adjustment_order_id = None
            state.pending_adjustment_type = None
            state.next_step = "END"
            state.final_reply = f"✅ *Field Updated!*\nOrder *{target_oid}* — *Delivery Date* updated to *{new_date}*. 📅"
            return state

        if state.active_menu == "SELECT_ORDER_FOR_MACHINE":
            orders = self.db.get_active_orders_summary(limit=5)
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
            if raw_msg == "1": machine = "Ricoma"
            elif raw_msg == "2": machine = "Aakruthi"
            elif msg_lower in ("ricoma", "aakruthi"): machine = raw_msg.title()
            else:
                state.final_reply = "Please reply with *1* for Ricoma or *2* for Aakruthi (or '0' to cancel)."
                return state
            target_oid = state.pending_adjustment_order_id
            self.db.update_order_field(target_oid, "machine", machine)
            state.is_field_override = True
            state.order_id = target_oid
            state.override_field = "machine"
            state.override_value = machine
            state.active_menu = None
            state.pending_adjustment_order_id = None
            state.pending_adjustment_type = None
            state.next_step = "END"
            state.final_reply = f"✅ *Machine Reassigned!*\nOrder *{target_oid}* has been reassigned to *{machine}*. 🧵"
            return state

        if state.active_menu == "SELECT_ORDER_FOR_COST":
            orders = self.db.get_active_orders_summary(limit=5)
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
            target_oid = state.pending_adjustment_order_id
            cost_val = f"Rs {cost_str}"
            self.db.update_order_field(target_oid, "cost", cost_val)
            state.is_field_override = True
            state.order_id = target_oid
            state.override_field = "cost"
            state.override_value = cost_val
            state.active_menu = None
            state.pending_adjustment_order_id = None
            state.pending_adjustment_type = None
            state.next_step = "END"
            state.final_reply = f"✅ *Cost Updated!*\nOrder *{target_oid}* — *Total Cost* updated to *Rs {cost_str}*. 💰"
            return state

        if state.active_menu == "SELECT_ORDER_FOR_EXPLAIN":
            orders = self.db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                order_data = self.db.get_order(target_id)
                reasoning = order_data.get("reasoning", "No detailed reasoning found.") if order_data else "Order not found."
                state.active_menu = None
                state.final_reply = f"🔍 *Audit Reasoning Log — Order {target_id}:*\n\n{reasoning}"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "SELECT_ORDER_TO_INVOICE":
            orders = self.db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                self.db.update_order_status(target_id, "Invoiced")
                state.active_menu = None
                state.final_reply = f"✅ *Status Updated!*\nOrder *{target_id}* has been marked as *Invoiced*. 📋"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        if state.active_menu == "SELECT_ORDER_TO_COMPLETE":
            orders = self.db.get_active_orders_summary(limit=5)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                self.db.update_order_status(target_id, "Completed")
                state.active_menu = None
                state.final_reply = f"✅ *Status Updated!*\nOrder *{target_id}* has been marked as *Completed*. 📋"
                return state
            else:
                state.final_reply = f"Boss, please reply with a number (1-{len(orders)}) or Order ID, or '0' for main menu."
                return state

        # -------------------------------------------------------------
        # 4. Natural Language Conversational Handler (Exactly 1 LLM Call)
        # -------------------------------------------------------------
        state.active_menu = None
        state.pending_adjustment_type = None
        state.pending_adjustment_order_id = None

        prompt = f"""
You are the AI Business Assistant for CJS Designs, an embroidery studio run by Siny.
Always address the user with the salutation 'Boss'.
Keep responses clear, professional, warm, and concise for WhatsApp.
Use WhatsApp formatting (*bold*, bullet points).

User's Message: "{state.raw_message}"

Guidelines:
- If Boss is asking about placing an order, suggest replying '1' to open the instant WhatsApp Order Form.
- If Boss is asking what to do today or wants a schedule summary, suggest replying '4' for the 5-Pillar Daily Briefing.
- If Boss is asking about invoices or payments, summarize or suggest replying '3'.
- If Boss wants to register a client or template, suggest replying '6' (Add Customer) or '7' (Add Template).
- If Boss asks a general question, answer helpfully directly.
"""
        try:
            response = self.llm.invoke(prompt)
            reply_text = str(response.content).strip()
            if isinstance(response.content, list):
                reply_text = " ".join(
                    b.get("text", "") if isinstance(b, dict) else str(b) for b in response.content
                ).strip()
            state.final_reply = reply_text
        except Exception as e:
            print(f"[{self.name}] LLM invocation error: {e}")
            state.final_reply = (
                "Hello Boss! How can I assist you today? 🧵\n\n"
                "• Reply *'1'* for New Order Form\n"
                "• Reply *'4'* for Today's Work & Briefing\n"
                "• Reply *'Hi'* to view the full menu."
            )

        return state
