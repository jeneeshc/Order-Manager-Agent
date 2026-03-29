from dotenv import load_dotenv
load_dotenv()

import os
print("Using GEMINI_API_KEY:", os.environ.get("GEMINI_API_KEY"))

from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState

print("Instantiating Agent...")
agent = OrderCollectorAgent()

state = AgentState(
    raw_message="Can you get me an estimate for 16,000 stitches on a velvet gown?",
    client_name="Test User",
    sender_phone="918289897413"
)

try:
    print("Testing local Gemini connection...")
    new_state = agent.process(state)
    print(f"SUCCESS! Extracted: {new_state.stitch_count} stitches, {new_state.fabric_type} fabric.")
except Exception as e:
    print(f"CRASH: {e}")
