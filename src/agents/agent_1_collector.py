import os
from pydantic import BaseModel, Field
from typing import Optional
from src.agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from src.services.sheets import GoogleSheetsService

class OrderExtractionModel(BaseModel):
    """Rigid JSON schema for the LLM to fill out based on Siny's WhatsApp text."""
    customer_name: Optional[str] = Field(description="The name of the customer placing the order. Leave null if not mentioned.")
    fabric_type: Optional[str] = Field(description="The material/fabric mentioned. Leave null if not stated.")
    embroidery_type: Optional[str] = Field(description="The style or type of embroidery (e.g. Logo, Floral, Pattern). Leave null if not stated.")
    stitch_count: Optional[int] = Field(description="The exact numeric total of stitches requested. Leave null if not stated.")
    requested_delivery_date: Optional[str] = Field(description="The day or date requested for delivery. Leave null if not stated.")
    referenced_order_id: Optional[str] = Field(description="If Siny explicitly types a previous Order ID (like CJS-12345), exactly extract it here. Leave null if she does not mention one.")
    mark_as_invoiced: bool = Field(description="True ONLY if the user explicitly commanded to mark an existing order ID as invoiced or finalized.")
    explain_reasoning: bool = Field(description="True ONLY if Siny explicitly asks to explain the reasoning, logic, or math behind a previously generated Order ID.")
    is_field_override: bool = Field(description="True ONLY if the user wants to manually change/override a specific field (delivery date, cost, or machine) on an existing order.")
    override_field: Optional[str] = Field(description="If is_field_override is True, which field to change: 'delivery_date', 'cost', or 'machine'. Leave null otherwise.")
    override_value: Optional[str] = Field(description="If is_field_override is True, the new value Siny wants to set. Leave null otherwise.")
    is_payment_query: bool = Field(description="True ONLY if Siny is asking about pending payments, unpaid orders, or items awaiting payment.")
    confirm_duplicate: bool = Field(description="True ONLY if the user explicitly says 'Yes' or confirms they want to proceed with a duplicate order that was previously warned about.")
    is_missing_info: bool = Field(description="True if ANY of customer_name, fabric_type, embroidery_type, or stitch_count are missing AND she DID NOT provide an order ID AND mark_as_invoiced, is_payment_query, explain_reasoning, and is_field_override are all False.")
    missing_fields_prompt: Optional[str] = Field(description="If is_missing_info is True, generate a friendly short text asking Siny for the missing details including customer name if not provided.")

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
        Read this new text message from the customer: "{state.raw_message}"
        
        PRIOR KNOWLEDGE EXTRACTED: 
        (If the customer already provided these earlier, do not extract them again. You only need to extract what the customer just said in the new message!)
        - Known Customer Name: {state.customer_name or 'None'}
        - Known Fabric: {state.fabric_type or 'None'}
        - Known Embroidery: {state.embroidery_type or 'None'}
        - Known Stitches: {state.stitch_count or 'None'}
        - Is Waiting For Duplicate Confirmation? {state.missing_fields_prompt.startswith('It looks like') if state.missing_fields_prompt else 'False'}
        
        Last Question Asked to User: {state.missing_fields_prompt or 'None'}
        
        Extract any NEW sewing/business details from this Whatsapp message and output the structured JSON.
        If the combination of Known properties AND your New properties still leaves the main 4 fields (customer_name, fabric_type, embroidery_type, stitch_count) incomplete, set is_missing_info=true and ask for specifically what is still missing!
        If they are replying 'yes' to a duplicate check, output confirm_duplicate=true.
        """
        
        # Generative AI reads the human text and extracts the core fields
        extraction: OrderExtractionModel = self.extractor.invoke(prompt)
        
        # ✨ 0. Intercept explicit Database Mutation Overrides instantly! ✨
        if extraction.mark_as_invoiced and extraction.referenced_order_id:
            print(f"[{self.name}] Intercepted Database Mutation Command for {extraction.referenced_order_id}")
            state.is_status_update = True
            state.new_invoice_status = "Invoiced"
            state.order_id = extraction.referenced_order_id
            state.current_agent = "End" # Force Graph to skip Schedulers and Estimators!
            return state
            
        # ✨ 0.5 Intercept RAG History Explanations instantly! ✨
        if extraction.explain_reasoning and extraction.referenced_order_id:
            print(f"[{self.name}] Intercepted Database Explanation Request for {extraction.referenced_order_id}")
            state.is_explanation_request = True
            state.order_id = extraction.referenced_order_id
            state.current_agent = "End"
            return state

        # ✨ 0.6 Intercept Manual Field Override commands! ✨
        if extraction.is_field_override and extraction.referenced_order_id and extraction.override_field and extraction.override_value:
            print(f"[{self.name}] Intercepted Field Override: '{extraction.override_field}' -> '{extraction.override_value}' on {extraction.referenced_order_id}")
            state.is_field_override = True
            state.order_id = extraction.referenced_order_id
            state.override_field = extraction.override_field
            state.override_value = extraction.override_value
            state.current_agent = "End"
            return state

        # ✨ 0.7 Intercept Payment Query! ✨
        if extraction.is_payment_query:
            print(f"[{self.name}] Intercepted Payment Query — routing to invoicing lookup.")
            state.is_payment_query = True
            state.current_agent = "End"
            return state
        
        # Hydrate from Google Sheets if an Order ID was parsed!
        if extraction.referenced_order_id:
            print(f"[{self.name}] Connecting to Database to hydrate context for {extraction.referenced_order_id}...")
            db = GoogleSheetsService()
            historical_db_order = db.get_order(extraction.referenced_order_id)
            
            if historical_db_order:
                # Inject DB parameters unless the AI successfully extracted a NEW override from the chat!
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
            state.current_agent = "ProductionScheduler"

        # Write Agent 1 Log to Column L (reasoning)
        agent_log = f"\n[Collector Agent]: Customer='{state.customer_name}', Stitches={state.stitch_count}, Fabric={state.fabric_type}, Style={state.embroidery_type}.\n"
        state.aggregated_reasoning = (state.aggregated_reasoning or "") + agent_log

        print(f"[{self.name}] Aggregated Extraction Output -> Customer: {state.customer_name}, Stitches: {state.stitch_count}, Fabric: {state.fabric_type}, Style: {state.embroidery_type}")
        return state
