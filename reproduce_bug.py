import os
from dotenv import load_dotenv
load_dotenv()

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from unittest.mock import MagicMock, patch

def reproduce():
    print("\n--- Reproducing Reported Bug ---")
    message = "I have a new order. can you add it? Customer: Anna, material: Saree, numbers 5, stitches: 100000"
    state = AgentState(raw_message=message, sender_id="test_user")
    
    # Mocking Sheets to avoid real API hits
    with patch('src.services.sheets.GoogleSheetsService') as MockSheets:
        mock_db = MockSheets.return_value
        mock_db.get_machine_availability.return_value = {"Ricoma-1": MagicMock()}
        mock_db.get_holidays.return_value = []
        mock_db.get_costing_rules.return_value = {}
        mock_db.get_order.return_value = None
        mock_db.check_duplicate_order.return_value = False
        
        print(f"Input: {message}")
        print("Starting Graph execution...")
        
        try:
            final_state_dict = cjs_bot.invoke(state)
            rebuilt_state = AgentState(**final_state_dict)
            
            print("\n--- EXECUTION LOGS ---")
            print(rebuilt_state.aggregated_reasoning)
            
            print("\n--- FINAL RAW MESSAGE (RESPONSE) ---")
            print(rebuilt_state.raw_message)
            
            print(f"Status: {rebuilt_state.next_step}")
        except Exception as e:
            print(f"\n--- FAILED WITH ERROR ---")
            print(e)

if __name__ == "__main__":
    reproduce()
