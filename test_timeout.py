import time
import os
from dotenv import load_dotenv
load_dotenv()
from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState

def main():
    message = """can you add an order?
Customer: Ameera
Type: Kurty
Count: 3
Stitch: 170000
Expected delivery date: 12May2026
Fabric type: Cotton, Style: Floral"""

    print("--- STARTING TIMEOUT TEST ---")
    start_time = time.time()

    initial_state = AgentState(raw_message=message, sender_id="1234567890")
    
    # We added recursion_limit in main.py, but not in the graph compiler directly. 
    # The API calls invoke with config={"recursion_limit": 8}. We should replicate that here.
    final_output = cjs_bot.invoke(initial_state, config={"recursion_limit": 20})

    end_time = time.time()
    
    print("\n--- FINAL OUTPUT ---")
    print(f"Final message: {final_output.get('raw_message')}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
