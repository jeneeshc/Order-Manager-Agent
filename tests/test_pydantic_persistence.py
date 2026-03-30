import os
from src.services.memory import MemoryService
from src.agents.state import AgentState

def test_pydantic_persistence():
    print("\n--- Testing Pydantic Persistence ---")
    mem = MemoryService()
    phone = "9998887777"
    
    # Save a Pydantic model
    test_state = AgentState(raw_message="Test message", is_missing_info=True)
    print(f"Saving Pydantic state for {phone}")
    mem.save_state(phone, test_state)
    
    # Create a NEW instance to simulate server restart
    print("Simulating server restart...")
    mem2 = MemoryService()
    loaded_state = mem2.get_state(phone)
    
    print("Loaded State Type:", type(loaded_state))
    print("Loaded State:", loaded_state)
    
    if loaded_state and isinstance(loaded_state, dict) and loaded_state.get("raw_message") == "Test message":
        print("SUCCESS: Pydantic state persisted correctly as dict!")
    else:
        print("FAILED: Pydantic state failed to persist.")
        
    # Cleanup
    mem.clear_state(phone)

if __name__ == "__main__":
    test_pydantic_persistence()
