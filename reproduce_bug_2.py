import os
from dotenv import load_dotenv
load_dotenv()

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from unittest.mock import MagicMock, patch

def reproduce_two_step():
    print("\n--- Reproducing Two-Step Order Bug ---")
    
    # STEP 1: First message (missing info)
    msg1 = "I have a new order. can you add it? Customer: Anna, material: Saree, numbers 5, stitches: 100000"
    state1 = AgentState(raw_message=msg1, sender_id="test_user")
    
    with patch('src.services.sheets.GoogleSheetsService') as MockSheets:
        mock_db = MockSheets.return_value
        mock_db.get_machine_availability.return_value = {"Ricoma-1": MagicMock()}
        mock_db.get_holidays.return_value = []
        mock_db.get_costing_rules.return_value = {}
        mock_db.get_order.return_value = None
        mock_db.check_duplicate_order.return_value = False
        
        print("\n[STEP 1] Input:", msg1)
        final_state1_dict = cjs_bot.invoke(state1)
        state1_rebuilt = AgentState(**final_state1_dict)
        print("Bot Response 1:", state1_rebuilt.raw_message)
        print("Missing Info?", state1_rebuilt.is_missing_info)
        
        # STEP 2: Second message (providing missing info)
        msg2 = "Fabric type: Cotton, embroidery style: floral, Stitch count: 200000, customer name: Anna"
        # Simulate memory service behavior in main.py fix:
        state2 = AgentState(**final_state1_dict)
        state2.raw_message = msg2
        state2.is_missing_info = False
        state2.next_step = "supervisor"
        
        print("\n[STEP 2] Input:", msg2)
        try:
            final_state2_dict = cjs_bot.invoke(state2)
            state2_rebuilt = AgentState(**final_state2_dict)
            print("\n--- FINAL EXECUTION LOGS ---")
            print(state2_rebuilt.aggregated_reasoning)
            print("\n--- FINAL BOT REPLY ---")
            print(state2_rebuilt.raw_message)
        except Exception as e:
            print("FAILED WITH ERROR:", e)

if __name__ == "__main__":
    reproduce_two_step()
