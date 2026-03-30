from langgraph.graph import StateGraph, END
from src.agents.state import AgentState
from dotenv import load_dotenv
load_dotenv()

from src.agents.agent_0_supervisor import SupervisorAgent
from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.agent_2_scheduler import ProductionSchedulerAgent
from src.agents.agent_3_estimator import EstimationAgent
from src.agents.agent_4_social_media import SocialMediaAgent
from src.agents.agent_5_invoicing import InvoicingAgent
from src.agents.agent_6_secretary import SecretaryAgent

# Step 1: Initialize Agents
supervisor = SupervisorAgent()
collector = OrderCollectorAgent()
scheduler = ProductionSchedulerAgent()
estimator = EstimationAgent()
social_media = SocialMediaAgent()
invoicing = InvoicingAgent()
secretary = SecretaryAgent()

# Step 2: Define the Graph
builder = StateGraph(AgentState)

# Add Nodes
builder.add_node("supervisor", supervisor.process)
builder.add_node("collector", collector.process)
builder.add_node("scheduler", scheduler.process)
builder.add_node("estimator", estimator.process)
builder.add_node("social", social_media.process)
builder.add_node("invoice", invoicing.process)
builder.add_node("secretary", secretary.process)

# Step 3: Define edges
builder.set_entry_point("supervisor")

# The Supervisor decides who goes next
builder.add_conditional_edges(
    "supervisor",
    lambda state: state.next_step,
    {
        "collector": "collector",
        "scheduler": "scheduler",
        "estimator": "estimator",
        "social": "social",
        "invoice": "invoice",
        "secretary": "secretary",
        "END": END
    }
)

# Every worker returns to the supervisor to check for next steps
builder.add_edge("collector", "supervisor")
builder.add_edge("scheduler", "supervisor")
builder.add_edge("estimator", "supervisor")
builder.add_edge("social", "supervisor")
builder.add_edge("invoice", "supervisor")
builder.add_edge("secretary", "supervisor")

# Compile
cjs_bot = builder.compile()

if __name__ == "__main__":
    # Test Mixed Intent
    test_state = AgentState(raw_message="Hi Boss, update order CJS-12345 to 8000 stitches. Also, what are my tasks for today?")
    print("--- STARTING SUPERVISOR GRAPH ---")
    final_output = cjs_bot.invoke(test_state)
    print("--- FINAL OUTPUT ---")
    print(final_output.get("aggregated_reasoning"))
    print(f"Final Step: {final_output.get('next_step')}")
