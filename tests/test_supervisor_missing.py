import os
from dotenv import load_dotenv
load_dotenv()

from src.agents.agent_0_supervisor import SupervisorAgent
from src.agents.state import AgentState

def test_supervisor_on_missing_info():
    print("\n--- Testing Supervisor Decision on Missing Info ---")
    state = AgentState(
        raw_message="I have a new order for Anna, Saree, 100k stitches.",
        customer_name="Anna",
        fabric_type="Saree",
        stitch_count=100000,
        is_missing_info=True # EMBROIDERY TYPE IS MISSING
    )
    
    supervisor = SupervisorAgent()
    print("Calling supervisor.process()...")
    
    final_state = supervisor.process(state)
    
    print("\n--- RESULTS ---")
    print(f"Next Step: {final_state.next_step}")
    print(f"Aggregated Reasoning: {final_state.aggregated_reasoning}")

if __name__ == "__main__":
    test_supervisor_on_missing_info()
