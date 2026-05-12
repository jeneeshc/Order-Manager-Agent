import time
import os
from dotenv import load_dotenv
load_dotenv()
from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState

def main():
    message = "can you add an order? Customer: Ameera, Type: Kurty"

    print("--- STARTING GUARD RAILS TEST ---")
    start_time = time.time()

    # Set hop_count to 5 to trigger the cutoff on the first step
    initial_state = AgentState(raw_message=message, sender_id="1234567890", hop_count=5)
    
    final_output = cjs_bot.invoke(initial_state)

    end_time = time.time()
    
    print("\n--- FINAL OUTPUT ---")
    print(f"Final message: {final_output.get('raw_message')}")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
