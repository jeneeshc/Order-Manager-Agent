import os
from pydantic import BaseModel, Field
from typing import Optional
from src.agents.state import AgentState
from langchain_google_vertexai import ChatVertexAI

# Authenticate GCP natively using the JSON bot file ONLY if we are testing locally!
# In Cloud Run, GCP instances authenticate their Service Accounts implicitly.
creds_path = r"d:\Projects\CJSDesigns\credentials.json"
if os.path.exists(creds_path):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

class OrderExtractionModel(BaseModel):
    """Rigid JSON schema for the LLM to fill out based on Siny's WhatsApp text."""
    fabric_type: Optional[str] = Field(description="The material/fabric mentioned. Leave null if not stated.")
    embroidery_type: Optional[str] = Field(description="The style or type of embroidery (e.g. Logo, Floral, Pattern). Leave null if not stated.")
    stitch_count: Optional[int] = Field(description="The exact numeric total of stitches requested. Leave null if not stated.")
    requested_delivery_date: Optional[str] = Field(description="The day or date requested for delivery. Leave null if not stated.")
    is_missing_info: bool = Field(description="True if ANY of fabric_type, embroidery_type, or stitch_count are missing.")
    missing_fields_prompt: Optional[str] = Field(description="If is_missing_info is True, generate a friendly short text asking Siny for the missing details.")

class OrderCollectorAgent:
    def __init__(self):
        self.name = "Order Collector Agent"
        
        # Initialize natively via Vertex and GCP IAM!
        self.llm = ChatVertexAI(
            model_name="gemini-1.5-flash-001",
            project="ai-agent-462312",
            location="us-central1",
            temperature=0
        )
        
        # Connect the Pydantic structured output constraint
        self.extractor = self.llm.with_structured_output(OrderExtractionModel)

    def process(self, state: AgentState) -> AgentState:
        print(f"[{self.name}] Activating Gemini LLM on: {state.raw_message}")
        
        # Generative AI reads the human text and extracts the core fields
        extraction: OrderExtractionModel = self.extractor.invoke(
            f"Extract the sewing and business details from this Whatsapp message:\n\n{state.raw_message}"
        )
        
        state.fabric_type = extraction.fabric_type
        state.embroidery_type = extraction.embroidery_type
        state.stitch_count = extraction.stitch_count
        state.requested_delivery_date = extraction.requested_delivery_date
        
        # Decision Logic: Does the bot have enough to confidently do math?
        if extraction.is_missing_info or not state.stitch_count:
            print(f"[{self.name}] Required parameters missing. Returning to WhatsApp.")
            state.is_missing_info = True
            state.missing_fields_prompt = extraction.missing_fields_prompt or "Can you provide the exact stitch count and fabric type for this order?"
        else:
            state.is_missing_info = False
            state.current_agent = "ProductionScheduler"
            
        print(f"[{self.name}] Extraction Output -> Stitches: {state.stitch_count}, Fabric: {state.fabric_type}")
        
        return state
