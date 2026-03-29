import os
from pydantic import BaseModel, Field
from typing import Optional, List

# Define the state that goes linearly through the graph
class AgentState(BaseModel):
    # Customer Details
    sender_id: str = Field(default="")
    
    # NLP Context / Audio Text
    raw_message: str = Field(default="")
    
    # Agent 1 updates these: Order context
    fabric_type: Optional[str] = None
    embroidery_type: Optional[str] = None
    stitch_count: Optional[int] = None
    requested_delivery_date: Optional[str] = None
    order_id: Optional[str] = None
    
    # Agent 2 updates these: Scheduling
    estimated_completion_date: Optional[str] = None
    machine_assigned: Optional[str] = None  # Ricoma or Aakruthi
    
    # Agent 3 updates these: Costing
    total_cost_rs: Optional[float] = None
    
    # Agent 4 & 5 updates these: Media & Invoicing
    media_assets: List[str] = Field(default_factory=list)
    invoice_status: str = Field(default="pending")
    
    # System routing & logging
    current_agent: str = Field(default="OrderCollector")
    is_missing_info: bool = Field(default=False)
    missing_fields_prompt: Optional[str] = None
    
    # State overrides for Native Database Mutations
    is_status_update: bool = Field(default=False)
    new_invoice_status: Optional[str] = None
