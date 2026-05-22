import os
from pydantic import BaseModel, Field
from typing import Optional
from src.agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from src.services.sheets import GoogleSheetsService

class OrderExtractionModel(BaseModel):
    """Structured extraction of order details from WhatsApp messages."""
    customer_name: Optional[str] = Field(None, description="Customer name.")
    fabric_type: Optional[str] = Field(None, description="Material/fabric type.")
    embroidery_type: Optional[str] = Field(None, description="Embroidery style/type. Do NOT include garment type (e.g., Kurty).")
    stitch_count: Optional[int] = Field(None, description="Total stitch count (numeric).")
    quantity: Optional[int] = Field(None, description="Total number of items (numeric).")
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
        8. Provide a helpful 'missing_fields_prompt' if key info is still absent.
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
        if extraction.fabric_type and not extraction.referenced_order_id:
            state.fabric_type = extraction.fabric_type
        elif extraction.fabric_type and extraction.referenced_order_id:
            pass
        if extraction.embroidery_type and not extraction.referenced_order_id:
            state.embroidery_type = extraction.embroidery_type
        if extraction.stitch_count and not extraction.referenced_order_id:
            state.stitch_count = extraction.stitch_count

        if extraction.requested_delivery_date:
            state.requested_delivery_date = extraction.requested_delivery_date
            
        if extraction.quantity:
            state.quantity = extraction.quantity
            
        if extraction.confirm_duplicate:
            state.is_duplicate_confirmed = True

        # Decision Logic: requires Customer Name, Fabric, Embroidery Type, and Stitch Count
        if not state.customer_name or not state.fabric_type or not state.embroidery_type or not state.stitch_count:
            print(f"[{self.name}] Required parameters missing. Returning to WhatsApp.")
            state.is_missing_info = True
            
            missing_items = []
            if not state.customer_name: missing_items.append("customer name")
            if not state.fabric_type: missing_items.append("fabric type")
            if not state.embroidery_type: missing_items.append("embroidery style")
            if not state.stitch_count: missing_items.append("stitch count")
            
            if len(missing_items) == 4:
                print(f"[{self.name}] All parameters missing. Triggering native WhatsApp Flow Form.")
                state.send_order_form = True
                state.missing_fields_prompt = "Triggering form..."
            else:
                if len(missing_items) == 1:
                    missing_str = missing_items[0]
                elif len(missing_items) == 2:
                    missing_str = f"{missing_items[0]} and {missing_items[1]}"
                else:
                    missing_str = ", ".join(missing_items[:-1]) + f", and {missing_items[-1]}"
                
                state.missing_fields_prompt = f"Please provide the {missing_str} to complete the order."
        else:
            # We have all info — check for duplicates!
            if not state.is_duplicate_confirmed and not extraction.referenced_order_id:
                db = GoogleSheetsService()
                similar_order = db.find_similar_order(
                    state.customer_id or state.customer_name, state.fabric_type, state.embroidery_type, state.stitch_count
                )
                if similar_order:
                    print(f"[{self.name}] Similar order detected! Prompting Boss for update vs create new choice.")
                    state.is_missing_info = True
                    o_id = similar_order.get("order_id", "Unknown")
                    o_date = similar_order.get("date", "recently")
                    o_stitch = similar_order.get("stitches", state.stitch_count)
                    o_style = similar_order.get("style", state.embroidery_type)
                    o_fabric = similar_order.get("fabric", state.fabric_type)
                    
                    state.missing_fields_prompt = f"I found a ~90% similar order for {state.customer_name} from {o_date}: Order *{o_id}* ({o_stitch} stitches of {o_style} on {o_fabric}).\n\nWould you like to update this existing order (reply *'update {o_id}'*), or create a brand new one (reply *'create new'*)"
                    return state

            # Passes all checks
            state.is_missing_info = False

        # Write Agent 1 Log to Column L (reasoning)
        agent_log = f"\n[Collector Agent]: Customer='{state.customer_name}', Stitches={state.stitch_count}, Fabric={state.fabric_type}, Style={state.embroidery_type}.\n"
        state.aggregated_reasoning = (state.aggregated_reasoning or "") + agent_log

        print(f"[{self.name}] Aggregated Extraction Output -> Customer: {state.customer_name}, Stitches: {state.stitch_count}, Fabric: {state.fabric_type}, Style: {state.embroidery_type}")
        return state
