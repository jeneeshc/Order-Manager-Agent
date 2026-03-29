from langgraph.graph import StateGraph, END
from src.agents.state import AgentState

from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.agent_2_scheduler import ProductionSchedulerAgent
from src.agents.agent_3_estimator import EstimationAgent
from src.agents.agent_4_social_media import SocialMediaAgent
from src.agents.agent_5_invoicing import InvoicingAgent

# Step 1: Initialize Agent Wrappers
collector = OrderCollectorAgent()
scheduler = ProductionSchedulerAgent()
estimator = EstimationAgent()
social_media = SocialMediaAgent()
invoicing = InvoicingAgent()

# Step 2: Define the mapping nodes
def call_collector(state: AgentState) -> AgentState:
    return collector.process(state)

def call_scheduler(state: AgentState) -> AgentState:
    return scheduler.process(state)

def call_estimator(state: AgentState) -> AgentState:
    return estimator.process(state)

# Step 3: Define Routing Logic between nodes
def route_after_collector(state: AgentState) -> str:
    # If information is missing during collection (Siny didn't use MCP form fully)
    if state.is_missing_info:
        return "ask_user" # Pauses/Breaks flow to wait for Whatsapp Input
    return "scheduler"    # Proceeds to next node automatically

# Step 4: Build the Graph Architecture
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("collector", call_collector)
workflow.add_node("scheduler", call_scheduler)
workflow.add_node("estimator", call_estimator)
workflow.add_node("social", social_media.process)
workflow.add_node("invoice", invoicing.process)

# Add Edges (Linear Cascading flow based on our architectural diagram)
workflow.set_entry_point("collector")

# Optional: Add condition routing
workflow.add_conditional_edges("collector", route_after_collector, {
    "ask_user": END,
    "scheduler": "scheduler"
})

workflow.add_edge("scheduler", "estimator")
workflow.add_edge("estimator", "social")
workflow.add_edge("social", "invoice")
workflow.add_edge("invoice", END)

# Compile Graph
cjs_bot = workflow.compile()

# Test runner block
if __name__ == "__main__":
    initial_state = AgentState(raw_message="Hi Siny, new design order: 15200 stitches on Cotton padding. Need it by Friday.")
    
    print("--- STARTING CASCADING GRAPH ---")
    final_state = cjs_bot.invoke(initial_state)
    print("--- FINAL COMPILED RUN STATE ---")
    print(final_state.model_dump_json(indent=2))
