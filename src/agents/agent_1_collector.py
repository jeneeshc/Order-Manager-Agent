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
    embroidery_type: Optional[str] = Field(None, description="Embroidery style/type.")
    stitch_count: Optional[int] = Field(None, description="Total stitch count (numeric).")
    requested_delivery_date: Optional[str] = Field(None, description="Delivery date/day.")
    referenced_order_id: Optional[str] = Field(None, description="Existing Order ID (e.g., CJS-12345) mentioned.")
    mark_as_invoiced: bool = Field(False, description="True if asked to mark order as invoiced.")
    explain_reasoning: bool = Field(False, description="True if asked to explain logic/math.")
    is_field_override: bool = Field(False, description="True if manually changing a field on an existing order.")
    override_field: Optional[str] = Field(None, description="Field to override ('delivery_date', 'cost', or 'machine').")
    override_value: Optional[str] = Field(None, description="New value for the override.")
    is_payment_query: bool = Field(False, description="True if asking about payments/unpaid orders.")
    is_secretary_query: bool = Field(False, description="True if asking for a daily summary, work update, or tasks for today (secretary function).")
    confirm_duplicate: bool = Field(False, description="True if confirming a duplicate order.")
    is_missing_info: bool = Field(False, description="True if info is missing and not an update/query.")
    missing_fields_prompt: Optional[str] = Field(None, description="Helpful prompt for missing fields.")

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
        
        # Build prompt injecting Memory State if it exists
        prompt = f"""You are Siny's WhatsApp Order Assistant.
        Read this new text message: "{state.raw_message}"
        
        PRIOR KNOWLEDGE EXTRACTED: 
        (If you already have these, do not extract them again. You only need to extract what is in the new message!)
        - Known Customer Name: {state.customer_name or 'None'}
        - Known Fabric: {state.fabric_type or 'None'}
        - Known Embroidery: {state.embroidery_type or 'None'}
        - Known Stitches: {state.stitch_count or 'None'}
        
        TASK:
        Extract any business details from this message.
        If an Order ID (like CJS-12345) is mentioned, exactly extract it into 'referenced_order_id'.
        If they specify a new material, style, or stitch count for an existing order, extract those too.
        If Siny asks for a daily summary, work schedule, status update on her tasks, or anything about "what needs to be done today", set 'is_secretary_query=True'.
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
            return state
            
        # ✨ 0.5 Intercept RAG History Explanations instantly! ✨
        if extraction.explain_reasoning and extraction.referenced_order_id:
            state.is_explanation_request = True
            state.order_id = extraction.referenced_order_id
            return state

        # ✨ 0.6 Intercept Manual Field Override commands! ✨
        if extraction.is_field_override and extraction.referenced_order_id and extraction.override_field and extraction.override_value:
            state.is_field_override = True
            state.order_id = extraction.referenced_order_id
            state.override_field = extraction.override_field
            state.override_value = extraction.override_value
            return state

        # ✨ 0.7 Intercept Payment Query! ✨
        if extraction.is_payment_query:
            state.is_payment_query = True
            return state
            
        # ✨ 0.8 Intercept Secretary Query! ✨
        if extraction.is_secretary_query:
            state.is_secretary_query = True
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
            else:
                print(f"[{self.name}] DB order not found. Falling back to chat extraction exclusively.")
        
        # Hydrate customer_name from extraction
        if extraction.customer_name:
            state.customer_name = extraction.customer_name

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
            
        if extraction.confirm_duplicate:
            state.is_duplicate_confirmed = True

        # Decision Logic: requires Customer Name, Fabric, Embroidery Type, and Stitch Count
        if not state.customer_name or not state.fabric_type or not state.embroidery_type or not state.stitch_count:
            print(f"[{self.name}] Required parameters missing. Returning to WhatsApp.")
            state.is_missing_info = True
            state.missing_fields_prompt = extraction.missing_fields_prompt or "Could you please share the fabric type, embroidery style, stitch count, and your name?"
        else:
            # We have all info — check for duplicates!
            if not state.is_duplicate_confirmed and not extraction.referenced_order_id:
                db = GoogleSheetsService()
                is_duplicate = db.check_duplicate_order(
                    state.customer_name, state.sender_id, state.fabric_type, state.embroidery_type, state.stitch_count
                )
                if is_duplicate:
                    print(f"[{self.name}] Duplicate detected! Prompting Siny for confirmation.")
                    state.is_missing_info = True
                    state.missing_fields_prompt = f"It looks like an identical order was already placed by {state.customer_name} today ({state.stitch_count} stitches of {state.embroidery_type} on {state.fabric_type}). Are you sure you want to duplicate it? Please say 'Yes' to confirm."
                    return state

            # Passes all checks
            state.is_missing_info = False

        # Write Agent 1 Log to Column L (reasoning)
        agent_log = f"\n[Collector Agent]: Customer='{state.customer_name}', Stitches={state.stitch_count}, Fabric={state.fabric_type}, Style={state.embroidery_type}.\n"
        state.aggregated_reasoning = (state.aggregated_reasoning or "") + agent_log

        print(f"[{self.name}] Aggregated Extraction Output -> Customer: {state.customer_name}, Stitches: {state.stitch_count}, Fabric: {state.fabric_type}, Style: {state.embroidery_type}")
        return state
