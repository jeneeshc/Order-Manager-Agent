import os
from src.services.memory import MemoryService

def test_memory_persistence():
    print("\n--- Testing Memory Persistence ---")
    mem = MemoryService()
    phone = "1234567890"
    
    # Save something
    test_state = {"raw_message": "Hello", "is_missing_info": True}
    print(f"Saving state for {phone}")
    mem.save_state(phone, test_state)
    
    # Create a NEW instance to simulate server restart
    print("Simulating server restart (new MemoryService instance)...")
    mem2 = MemoryService()
    loaded_state = mem2.get_state(phone)
    
    print("Loaded State:", loaded_state)
    
    if loaded_state == test_state:
        print("SUCCESS: Memory persisted to disk!")
    else:
        print("FAILED: Memory was lost.")
        
    # Cleanup
    mem.clear_state(phone)

if __name__ == "__main__":
    test_memory_persistence()
