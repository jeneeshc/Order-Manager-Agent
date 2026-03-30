import os
from dotenv import load_dotenv
load_dotenv()

from src.agents.agent_0_supervisor import SupervisorAgent
from src.agents.state import AgentState

def test_supervisor_missing_info_routing():
    print("\n--- Testing Supervisor Routing for Missing Info ---")
    
    # State simulated: Collector just ran and found missing info
    state = AgentState(
        raw_message="New order for Anna",
        is_missing_info=True,
        missing_fields_prompt="Please provide the embroidery type.",
        customer_name="Anna"
    )
    
    agent = SupervisorAgent()
    print("Calling supervisor.process() with is_missing_info=True...")
    
    final_state = agent.process(state)
    
    print("\n--- RESULTS ---")
    print(f"Next Step: {final_state.next_step}")
    print(f"Reasoning: {final_state.aggregated_reasoning.split('[Supervisor]:')[-1].strip()}")
    
    assert final_state.next_step == "END", f"Expected END but got {final_state.next_step}"
    print("✅ TEST PASSED: Routed to END as expected.")

if __name__ == "__main__":
    test_supervisor_missing_info_routing()
