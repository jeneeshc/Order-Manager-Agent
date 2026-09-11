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
    "2️⃣ *Adjust Existing Order* (Select an active order to edit in WhatsApp Form)\n"
    "3️⃣ *Pending Invoicing* (Completed orders awaiting bill per customer)\n"
    "4️⃣ *Daily Briefing & Tasks* (Today's summary, queues, and reminders)\n"
    "5️⃣ *Active Vendors Directory* (View suppliers and contact details)\n"
    "6️⃣ *Add New Customer Form* (Register a customer in Google Sheets)\n\n"
    "_Reply with the number (1-6) or type a command directly._"
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

import time

def date_to_ms(d_str: str) -> str:
    if not d_str:
        return str(int(time.time() * 1000))
    s = str(d_str).strip()
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            dt = datetime.datetime.strptime(s, fmt)
            return str(int(dt.timestamp() * 1000))
        except ValueError:
            continue
    return str(int(time.time() * 1000))

def sanitize_customer_name(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    name_clean = name.strip()
    if name_clean.isdigit():
        return None
    if name_clean.lower() in {"unknown", "none", "unknown name", "new customer", "unknown customer", "n/a", "null", "undefined", ""}:
        return None
    return name_clean

def render_active_orders_prompt(title: str, db: GoogleSheetsService):
    active_orders = db.get_active_orders_summary(limit=10)
    if not active_orders:
        return None, (
            "Boss, there are no active orders in the queue right now! 📭\n"
            "Reply *'Hi'* to return to the main menu."
        )
    lines = [f"{title}\n"]
    for idx, o in enumerate(active_orders, 1):
        lines.append(
            f"{idx}️⃣ *{o['order_id']}* — {o['customer']} ({o.get('template', 'Order')}, {o.get('quantity', 1)} pcs) | Due: {o.get('delivery_date', '')} | {o.get('machine', '')}"
        )
    lines.append("\n0️⃣ *Back to Main Menu*\n")
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
        clean_words = set(msg_lower.replace("!", "").replace(".", "").replace("?", "").replace(",", "").split())
        greeting_words = {"hi", "hello", "hey", "menu", "start", "help", "hie", "hii", "namaste", "morning", "evening"}
        if (msg_lower in {"hi", "hello", "menu", "help", "start", "hey"}
                or (clean_words & greeting_words and len(clean_words) <= 3)):
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
        # 2. Handling Interactive Input & Selection States
        # -------------------------------------------------------------
        # If user is in an active sub-menu prompt / selection / data entry,
        # prioritize fulfilling that interaction first.
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
                state.final_reply = (
                    "Boss, please provide a valid customer name (e.g. *Priya Boutique* or reply '0' to cancel).\n"
                    "_A number alone or invalid text cannot be registered as a customer name._"
                )
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
            template_name = parts[0].strip() if parts else raw_msg.strip()
            if not template_name or template_name.isdigit():
                state.final_reply = (
                    "Boss, please provide a valid template name (e.g. *Heavy Bridal Blouse* or reply '0' to cancel).\n"
                    "_A number alone cannot be registered as a template name._"
                )
                return state
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
            if not new_type or new_type.isdigit():
                state.final_reply = (
                    "Boss, please provide a valid order type name (e.g. *Cutwork Embroidery* or reply '0' to cancel).\n"
                    "_A number alone cannot be registered as an order type._"
                )
                return state
            state.active_menu = None
            state.final_reply = (
                f"✅ *Order Type Added!*\n\n"
                f"• *Order Type:* {new_type}\n\n"
                f"Registered for CJS Designs. 👍\n"
                f"Reply *'Hi'* for main menu or *'1'* to start a new order."
            )
            return state

        # Sub-menus: Adjustments & Order Editing
        if state.active_menu == "SELECT_ORDER_FOR_EDIT":
            orders = self.db.get_active_orders_summary(limit=10)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                # Find matching order from active_orders
                matched = next((o for o in orders if o["order_id"] == target_id), None)
                if not matched:
                    matched = self.db.get_order(target_id) or {}
                
                cust = matched.get("customer") or matched.get("customer_name") or ""
                otype = matched.get("order_type") or ("Machine Embroidery" if matched.get("machine") in ("Ricoma", "Aakruthi") else "Embroidery designing")
                tmpl = matched.get("template") or matched.get("embroidery_type") or "General"
                qty = int(matched.get("quantity") or 1)
                d_date = matched.get("delivery_date") or ""
                tmpl_data = self.db.get_template_by_name(tmpl) or {}
                stitches = int(matched.get("stitch_count") or tmpl_data.get("stitch_count") or 0)
                stored_labor = float(matched.get("labor_hours") or 0.0)
                if stored_labor > 0:
                    labor_mins = int(round(stored_labor * 60.0)) if stored_labor < 24 else int(stored_labor)
                else:
                    labor_mins = int(tmpl_data.get("labor_minutes") or 60)
                
                state.editing_order_id = target_id
                state.flow_init_data = {
                    "editing_order_id": target_id,
                    "init_customer": cust,
                    "init_order_type": otype,
                    "init_template": tmpl,
                    "init_quantity": qty,
                    "init_delivery_date": date_to_ms(d_date),
                    "init_stitch_count": stitches,
                    "init_labor_minutes": labor_mins
                }
                state.send_order_form = True
                state.active_menu = None
                state.next_step = "END"
                state.final_reply = (
                    f"Opening WhatsApp Form to edit Order *{target_id}* (*{cust}*)... 📋\n"
                    f"Existing order values are pre-filled for your edits."
                )
                return state
            else:
                state.final_reply = f"Boss, please reply with a valid number (1-{len(orders)}) or Order ID from the list above, or '0' for main menu."
                return state

        # Sub-menu: ADJUST (Option 2 adjustments)
        if state.active_menu == "ADJUST":
            if raw_msg in ("1", "21"):
                orders, prompt_text = render_active_orders_prompt("📅 *Select Order to Change Delivery Date:*", self.db)
                if not orders:
                    state.active_menu = None
                    state.final_reply = prompt_text
                    return state
                state.active_menu = "SELECT_ORDER_FOR_DATE"
                state.final_reply = prompt_text
                return state
            elif raw_msg in ("2", "22"):
                orders, prompt_text = render_active_orders_prompt("🧵 *Select Order to Reassign Machine:*", self.db)
                if not orders:
                    state.active_menu = None
                    state.final_reply = prompt_text
                    return state
                state.active_menu = "SELECT_ORDER_FOR_MACHINE"
                state.final_reply = prompt_text
                return state
            elif raw_msg in ("3", "23"):
                orders, prompt_text = render_active_orders_prompt("💰 *Select Order to Override Cost:*", self.db)
                if not orders:
                    state.active_menu = None
                    state.final_reply = prompt_text
                    return state
                state.active_menu = "SELECT_ORDER_FOR_COST"
                state.final_reply = prompt_text
                return state
            elif raw_msg in ("4", "24"):
                orders, prompt_text = render_active_orders_prompt("🔍 *Select Order to Review Reasoning Log:*", self.db)
                if not orders:
                    state.active_menu = None
                    state.final_reply = prompt_text
                    return state
                state.active_menu = "SELECT_ORDER_FOR_EXPLAIN"
                state.final_reply = prompt_text
                return state
            else:
                state.final_reply = "Boss, please select a valid option (1-4) from the Adjust Order menu, or reply '0' for the main menu."
                return state

        if state.active_menu == "SELECT_ORDER_FOR_DATE":
            orders = self.db.get_active_orders_summary(limit=10)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.pending_adjustment_order_id = target_id
                state.pending_adjustment_type = "delivery_date"
                state.active_menu = "INPUT_NEW_DATE"
                state.final_reply = f"Selected order *{target_id}*.\nPlease reply with the new delivery date (e.g. *2026-09-15*):"
                return state
            else:
                state.final_reply = f"Boss, please reply with a valid number (1-{len(orders)}) or Order ID from the list above, or '0' for main menu."
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
            orders = self.db.get_active_orders_summary(limit=10)
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
                state.final_reply = f"Boss, please reply with a valid number (1-{len(orders)}) or Order ID from the list above, or '0' for main menu."
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
            orders = self.db.get_active_orders_summary(limit=10)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                state.pending_adjustment_order_id = target_id
                state.pending_adjustment_type = "cost"
                state.active_menu = "INPUT_NEW_COST"
                state.final_reply = f"Selected order *{target_id}*.\nPlease reply with the new total cost in Rs (e.g. *650*):"
                return state
            else:
                state.final_reply = f"Boss, please reply with a valid number (1-{len(orders)}) or Order ID from the list above, or '0' for main menu."
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
            orders = self.db.get_active_orders_summary(limit=10)
            target_id = resolve_selected_order(raw_msg, orders)
            if target_id:
                order_data = self.db.get_order(target_id)
                reasoning = order_data.get("reasoning", "No detailed reasoning found.") if order_data else "Order not found."
                state.active_menu = None
                state.final_reply = f"🔍 *Audit Reasoning Log — Order {target_id}:*\n\n{reasoning}"
                return state
            else:
                state.final_reply = f"Boss, please reply with a valid number (1-{len(orders)}) or Order ID from the list above, or '0' for main menu."
                return state
        # Fallback guard for any sub-menu: Ensure sub-menu responses NEVER leak into main menu or LLM
        if state.active_menu and state.active_menu != "MAIN":
            state.active_menu = "MAIN"
            state.final_reply = "I didn't recognize that option, Boss. Here is the Main Menu:\n\n" + MAIN_MENU_TEXT
            return state

        # -------------------------------------------------------------
        # 3. Direct Fast-Action Numeric Codes & Top-Level Menus
        # -------------------------------------------------------------
        # Option 1: Open Order Form (only from main menu or top level)
        if ((raw_msg == "1" and state.active_menu in ("MAIN", None))
                or (msg_lower in {"new order", "create order", "order form", "open form"} and state.active_menu in ("MAIN", None))):
            state.editing_order_id = None
            state.flow_init_data = {
                "editing_order_id": "",
                "init_customer": "",
                "init_order_type": "",
                "init_template": "",
                "init_quantity": 1,
                "init_delivery_date": str(int(time.time() * 1000)),
                "init_stitch_count": None,
                "init_labor_minutes": None
            }
            state.send_order_form = True
            state.active_menu = None
            state.next_step = "END"
            state.final_reply = (
                "Opening WhatsApp Order Form for you, Boss! 📋\n"
                "Please select customer, order type, template, quantity, and delivery date."
            )
            return state

        # Option 2: Adjust / Edit Active Orders in WhatsApp Form
        if ((raw_msg == "2" and state.active_menu in ("MAIN", None))
                or (msg_lower in {"adjust order", "edit order", "adjust", "modify order"} and state.active_menu in ("MAIN", None))):
            orders, prompt_text = render_active_orders_prompt(
                "⚙️ *Select Order to Adjust / Edit:*\nBoss, which active order would you like to modify?",
                self.db
            )
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_EDIT"
            state.final_reply = prompt_text
            return state

        # Direct codes 21-24 retained for quick access from main menu
        if raw_msg == "21" and state.active_menu in ("MAIN", None):
            orders, prompt_text = render_active_orders_prompt("📅 *Select Order to Change Delivery Date:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_DATE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "22" and state.active_menu in ("MAIN", None):
            orders, prompt_text = render_active_orders_prompt("🧵 *Select Order to Reassign Machine:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_MACHINE"
            state.final_reply = prompt_text
            return state

        if raw_msg == "23" and state.active_menu in ("MAIN", None):
            orders, prompt_text = render_active_orders_prompt("💰 *Select Order to Override Cost:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_COST"
            state.final_reply = prompt_text
            return state

        if raw_msg == "24" and state.active_menu in ("MAIN", None):
            orders, prompt_text = render_active_orders_prompt("🔍 *Select Order to Review Reasoning Log:*", self.db)
            if not orders:
                state.active_menu = None
                state.final_reply = prompt_text
                return state
            state.active_menu = "SELECT_ORDER_FOR_EXPLAIN"
            state.final_reply = prompt_text
            return state

        # Option 3: Pending Invoicing (Direct report per customer, no sub-menu)
        if (
            (raw_msg in {"3", "31"} and state.active_menu in ("MAIN", None))
            or (("pending invoice" in msg_lower or "pending invoicing" in msg_lower) and state.active_menu in ("MAIN", None))
        ):
            state.is_pending_invoicing_query = True
            state.active_menu = None
            state.next_step = "END"
            pending = self.db.get_orders_pending_invoicing()
            if not pending:
                state.final_reply = "Boss, all completed orders have been invoiced! No pending orders. 🎉"
            else:
                lines = ["📋 *Pending Invoices*\n"]
                for cname, ords in sorted(pending.items()):
                    total_amount = 0.0
                    for o in ords:
                        cost_str = str(o.get("cost", "0")).replace("Rs", "").replace("₹", "").replace(",", "").strip()
                        try:
                            total_amount += float(cost_str)
                        except ValueError:
                            pass
                    amt_display = f"Rs {int(total_amount):,}" if total_amount.is_integer() else f"Rs {total_amount:,.2f}"
                    lines.append(f"• *{cname}* — {amt_display}")
                state.final_reply = "\n".join(lines)
            return state

        if (raw_msg == "34" and state.active_menu in ("MAIN", None)) or ("debtor" in msg_lower and state.active_menu in ("MAIN", None)):
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
        if ((raw_msg == "4" and state.active_menu in ("MAIN", None))
                or (msg_lower in {"briefing", "daily brief", "tasks today", "summary"} and state.active_menu in ("MAIN", None))):
            state.is_secretary_query = True
            state.active_menu = None
            state.next_step = "END"
            state = self.secretary.process(state)
            state.is_secretary_query = True
            state.active_menu = None
            state.next_step = "END"
            return state

        # Option 5: Active Vendors Directory (Direct report, no sub-menu)
        if (
            (raw_msg in {"5", "51"} and state.active_menu in ("MAIN", None))
            or (msg_lower in {"vendor", "vendors", "vendor directory", "active vendors", "suppliers"} and state.active_menu in ("MAIN", None))
        ):
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

        if (raw_msg == "52" and state.active_menu in ("MAIN", None)) or (msg_lower in {"expense", "expenses", "expense ledger"} and state.active_menu in ("MAIN", None)):
            expenses = self.db.get_recent_expenses(limit=5)
            if not expenses:
                state.final_reply = "Boss, no recent expenses found in 'Expense_Ledger'."
            else:
                e_lines = []
                for e in expenses:
                    e_lines.append(f"• *{e.get('date', '')}*: Rs {e.get('amount', 0)} — {e.get('description', '')} ({e.get('category', '')})")
                state.final_reply = "💸 *Recent Expenses (Expense Ledger)*\n\n" + "\n".join(e_lines)
            state.active_menu = None
            state.next_step = "END"
            return state

        # Option 6 / Code 61: Add New Customer Form
        if (
            (raw_msg in {"6", "61"} and state.active_menu in ("MAIN", None))
            or (msg_lower in {"add customer", "new customer", "create customer", "customer form"} and state.active_menu in ("MAIN", None))
        ):
            state.send_customer_form = True
            state.active_menu = "INPUT_NEW_CUSTOMER"
            state.next_step = "END"
            state.final_reply = (
                "👤 *Add New Customer Form*\n"
                "Opening Customer Registration Form for you, Boss! 📋\n"
                "Please fill in the customer name, phone, and address in the form."
            )
            return state

        # Option 7 / Code 71: Add New Template
        if (
            (raw_msg in {"7", "71"} and state.active_menu in ("MAIN", None))
            or (msg_lower in {"add template", "new template", "create template"} and state.active_menu in ("MAIN", None))
        ):
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
        if (
            (raw_msg in {"8", "81"} and state.active_menu in ("MAIN", None))
            or (msg_lower in {"add order type", "new order type"} and state.active_menu in ("MAIN", None))
        ):
            state.active_menu = "INPUT_NEW_ORDER_TYPE"
            state.final_reply = (
                "🧵 *Add New Order Type*\n"
                "Boss, please reply with the new order type name:\n\n"
                "_Example: Cutwork Embroidery or Blouse Neck Embroidery_\n\n"
                "_Reply 0 to cancel._"
            )
            return state

        # Option 9 / Code 91: Sync with Back-end (Refresh WhatsApp Form from Google Sheets)
        sync_triggers = {
            "sync", "sync backend", "sync with backend", "sync back-end",
            "sync with back-end", "refresh form", "sync form", "update form", "sync sheets"
        }
        if (
            (raw_msg in {"9", "91"} and state.active_menu in ("MAIN", None))
            or (msg_lower in sync_triggers and state.active_menu in ("MAIN", None))
        ):
            state.active_menu = None
            state.next_step = "END"
            
            # 1. Invalidate all in-memory caches
            GoogleSheetsService.clear_all_caches()
            
            # 2. Trigger Flow recompilation and deployment to Meta
            try:
                from scripts.deploy_flow import redeploy_order_flow
                new_flow_id = redeploy_order_flow()
                customers = self.db.get_all_customers_list() or []
                templates = self.db.get_description_templates() or []
                
                # Sample 3 customer names for the message
                sample_names = ", ".join(customers[:3]) + (f", +{len(customers)-3} more" if len(customers) > 3 else "")
                
                state.final_reply = (
                    f"✅ *Backend & WhatsApp Synced Successfully!* 🔄\n\n"
                    f"• *Customers Synced:* {len(customers)} clients ({sample_names})\n"
                    f"• *Templates Synced:* {len(templates)} design templates\n"
                    f"• *Active Flow ID:* `{new_flow_id}`\n"
                    f"• *Caches:* Cleared & refreshed from Google Sheets\n\n"
                    f"All WhatsApp order forms are now up-to-date with your latest sheet changes! 👍\n"
                    f"Reply *'1'* anytime to open the updated Order Form."
                )
            except Exception as e:
                print(f"[{self.name}] Sync failed: {e}")
                state.final_reply = (
                    f"⚠️ *Sync Encountered an Error:*\n{e}\n\n"
                    f"In-memory caches were cleared. Please try again in a few moments or reply *'Hi'* for the menu."
                )
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
- If Boss is greeting (saying hi, hello, etc.), output the full Main Menu:
1️⃣ New Order Form
2️⃣ Adjust Existing Order (WhatsApp Form edit)
3️⃣ Pending Invoicing (Completed orders awaiting bill per customer)
4️⃣ Daily Briefing & Tasks
5️⃣ Active Vendors Directory (View suppliers and contact details)
6️⃣ Add New Customer Form (Register a customer in Google Sheets)
- If Boss wants to modify/edit an active order, suggest replying '2' (Adjust Existing Order).
- If Boss is asking about placing an order, suggest replying '1' to open the instant WhatsApp Order Form.
- If Boss is asking about pending invoices or bills, summarize or suggest replying '3'.
- If Boss is asking what to do today or wants a schedule summary, suggest replying '4' for the 5-Pillar Daily Briefing.
- If Boss wants to view vendors or suppliers, suggest replying '5'.
- If Boss wants to register a new customer/client, suggest replying '6' (Add Customer Form).
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
            state.final_reply = MAIN_MENU_TEXT

        return state
