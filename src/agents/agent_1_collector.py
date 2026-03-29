import os
from pydantic import BaseModel, Field
from typing import Optional
from src.agents.state import AgentState
from langchain_google_genai import ChatGoogleGenerativeAI
from src.services.sheets import GoogleSheetsService

class OrderExtractionModel(BaseModel):
    """Rigid JSON schema for the LLM to fill out based on Siny's WhatsApp text."""
    fabric_type: Optional[str] = Field(description="The material/fabric mentioned. Leave null if not stated.")
    embroidery_type: Optional[str] = Field(description="The style or type of embroidery (e.g. Logo, Floral, Pattern). Leave null if not stated.")
    stitch_count: Optional[int] = Field(description="The exact numeric total of stitches requested. Leave null if not stated.")
    requested_delivery_date: Optional[str] = Field(description="The day or date requested for delivery. Leave null if not stated.")
    referenced_order_id: Optional[str] = Field(description="If Siny explicitly types a previous Order ID (like CJS-12345), exactly extract it here. Leave null if she does not mention one.")
    is_missing_info: bool = Field(description="True if ANY of fabric_type, embroidery_type, or stitch_count are missing and she DID NOT provide an order ID.")
    missing_fields_prompt: Optional[str] = Field(description="If is_missing_info is True, generate a friendly short text asking Siny for the missing details.")

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
        - Known Fabric: {state.fabric_type or 'None'}
        - Known Embroidery: {state.embroidery_type or 'None'}
        - Known Stitches: {state.stitch_count or 'None'}
        
        Extract any NEW sewing/business details from this Whatsapp message and output the structured JSON.
        If the combination of Known properties AND your New properties still leaves the main 3 fields incomplete, set is_missing_info=true and ask for specifically what is still missing!
        """
        
        # Generative AI reads the human text and extracts the core fields
        extraction: OrderExtractionModel = self.extractor.invoke(prompt)
        
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
        
        # Safely hydrate state if AI explicitly extracted something NEW
        if extraction.fabric_type and not extraction.referenced_order_id:
            state.fabric_type = extraction.fabric_type
        elif extraction.fabric_type and extraction.referenced_order_id:
            pass # Already handled by override logic Above!
        if extraction.embroidery_type and not extraction.referenced_order_id:
            state.embroidery_type = extraction.embroidery_type
        if extraction.stitch_count and not extraction.referenced_order_id:
            state.stitch_count = extraction.stitch_count
            
        if extraction.requested_delivery_date:
            state.requested_delivery_date = extraction.requested_delivery_date
            
        # Decision Logic: Does the bot have enough to confidently do math?
        # A completed order strictly requires Fabric, Embroidery Type, and Stitch Count
        if not state.fabric_type or not state.embroidery_type or not state.stitch_count:
            print(f"[{self.name}] Required parameters missing. Returning to WhatsApp.")
            state.is_missing_info = True
            state.missing_fields_prompt = extraction.missing_fields_prompt or "Can you clarify the remaining missing details for this order?"
        else:
            state.is_missing_info = False
            state.current_agent = "ProductionScheduler"
            
        print(f"[{self.name}] Aggregated Extraction Output -> Stitches: {state.stitch_count}, Fabric: {state.fabric_type}, Style: {state.embroidery_type}")
        
        return state
