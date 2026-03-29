import os
from dotenv import load_dotenv
load_dotenv()

from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState

def test_collector_directly():
    print("\n--- Testing Collector Directly ---")
    message = "I have a new order. can you add it? Customer: Anna, material: Saree, numbers 5, stitches: 100000"
    state = AgentState(raw_message=message, sender_id="test_user")
    
    agent = OrderCollectorAgent()
    print(f"Input: {message}")
    print("Calling collector.process()...")
    
    final_state = agent.process(state)
    
    print("\n--- RESULTS ---")
    print(f"Customer: {final_state.customer_name}")
    print(f"Material: {final_state.fabric_type}")
    print(f"Stitches: {final_state.stitch_count}")
    print(f"Missing Info? {final_state.is_missing_info}")
    print(f"Prompt: {final_state.missing_fields_prompt}")

if __name__ == "__main__":
    test_collector_directly()
