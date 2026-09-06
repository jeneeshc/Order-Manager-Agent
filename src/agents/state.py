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
    customer_name: Optional[str] = None
    customer_id: Optional[str] = None
    order_type: Optional[str] = None       # "Machine Embroidery" or "Embroidery design"
    template_name: Optional[str] = None    # e.g. "Saree Border", "Logo", etc.
    fabric_type: Optional[str] = None      # Legacy fallback
    embroidery_type: Optional[str] = None  # Legacy fallback
    stitch_count: Optional[int] = None
    quantity: Optional[int] = Field(default=1)
    labor_hours: Optional[float] = Field(default=0.0)
    labor_minutes: Optional[float] = Field(default=0.0)
    requested_delivery_date: Optional[str] = None
    order_id: Optional[str] = None
    
    # Agent 2 updates these: Scheduling
    estimated_completion_date: Optional[str] = None
    machine_assigned: Optional[str] = None  # Ricoma, Aakruthi, or None
    aggregated_reasoning: str = Field(default="")
    
    # Agent 3 updates these: Costing (Strict 4-Factor Formula)
    base_cost_rs: Optional[float] = None
    profit_margin_rs: Optional[float] = None
    profit_margin_pct: Optional[float] = None
    gst_amount_rs: Optional[float] = None
    gst_rate_pct: Optional[float] = None
    total_cost_rs: Optional[float] = None
    
    # Agent 4 & 5 updates these: Media & Invoicing
    media_assets: List[str] = Field(default_factory=list)
    invoice_status: str = Field(default="pending")
    
    # System routing & logging
    current_agent: str = Field(default="OrderCollector")
    is_missing_info: bool = Field(default=False)
    missing_fields_prompt: Optional[str] = None
    hop_count: int = Field(default=0)
    
    # State overrides for Native Database Mutations & RAG Audits
    is_status_update: bool = Field(default=False)
    new_invoice_status: Optional[str] = None
    is_explanation_request: bool = Field(default=False)
    is_payment_query: bool = Field(default=False)
    is_duplicate_confirmed: bool = Field(default=False)
    is_secretary_query: bool = Field(default=False)
    send_order_form: bool = Field(default=False)    
    is_pending_invoicing_query: bool = Field(default=False)
    is_invoicing_done_update: bool = Field(default=False)
    invoicing_done_customer: Optional[str] = None
    # supervisor-led orchestration fields
    next_step: str = Field(default="supervisor")
    worker_feedback: str = Field(default="")

    # Hierarchical Menu & Form-Driven Workflow State
    active_menu: Optional[str] = Field(default=None)  # "MAIN", "ADJUST", "INVOICING", "VENDORS", etc.
    pending_adjustment_type: Optional[str] = None     # "delivery_date", "machine", "cost"
    pending_adjustment_order_id: Optional[str] = None # Currently targeted Order ID for adjustment
    editing_order_id: Optional[str] = None            # Set when launching form to edit an existing order
    flow_init_data: Optional[dict] = None             # Pre-populated payload data for WhatsApp Flow

    # -------------------------------------------------------------------------
    # FINAL REPLY CONTRACT  (see docs/AGENT_DEVELOPMENT.md for full details)
    # -------------------------------------------------------------------------
    # Every agent MUST follow one of two patterns:
    #
    #   PATTERN A — Self-contained query (agent owns the WhatsApp reply):
    #     Set state.final_reply = "your formatted message"
    #     Supervisor passes it straight to WhatsApp — verbatim, zero extra LLM call.
    #
    #   PATTERN B — Intermediate pipeline step (feeds another agent):
    #     Do NOT set final_reply. Append to state.aggregated_reasoning only.
    #     Supervisor synthesizes a single reply from all agents' reasoning at END.
    #
    # NEVER set state.raw_message directly inside an agent. That is Supervisor-only.
    # -------------------------------------------------------------------------
    final_reply: Optional[str] = None

    # Manual Field Override state
    is_field_override: bool = Field(default=False)
    override_field: Optional[str] = None   # "delivery_date" | "cost" | "machine"
    override_value: Optional[str] = None   # The new value Boss specified
