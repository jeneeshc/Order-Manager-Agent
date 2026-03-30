import os
import json
from dotenv import load_dotenv
load_dotenv()

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from src.services.memory import MemoryService
from src.services.sheets import GoogleSheetsService
from unittest.mock import MagicMock, patch

def test_full_system_failure():
    print("\n--- Full System Integration Test (Debugging No-Response) ---")
    memory = MemoryService()
    phone = "test_user_failure"
    
    # 1. Simulate the Order Message
    msg1 = "I have a new order. can you add it? Customer: Anna, material: Saree, numbers 5, stitches: 100000"
    print(f"\n[TURN 1] Sending: {msg1}")
    
    with patch('src.services.sheets.GoogleSheetsService') as MockSheets:
        mock_db = MockSheets.return_value
        mock_db.get_machine_availability.return_value = {"Ricoma-1": "Available"}
        mock_db.get_holidays.return_value = []
        mock_db.get_costing_rules.return_value = {}
        mock_db.get_order.return_value = None
        mock_db.check_duplicate_order.return_value = False
        
        # Simulate main.py logic
        state1 = AgentState(raw_message=msg1, sender_id=phone)
        try:
            print("Invoking graph for Turn 1...")
            final_dict1 = cjs_bot.invoke(state1)
            rebuilt1 = AgentState(**final_dict1)
            print("Response 1:", rebuilt1.raw_message)
            memory.save_state(phone, rebuilt1)
        except Exception as e:
            print("TURN 1 CRASHED:", e)
            return

        # 2. Simulate the Secretary Message
        msg2 = "can you tell me if there is anything important tomorrow?"
        print(f"\n[TURN 2] Sending: {msg2}")
        
        # Simulate resume from memory
        prior = memory.get_state(phone)
        state2 = AgentState(**prior)
        state2.raw_message = msg2
        state2.is_missing_info = False
        state2.next_step = "supervisor"
        
        try:
            print("Invoking graph for Turn 2...")
            final_dict2 = cjs_bot.invoke(state2)
            rebuilt2 = AgentState(**final_dict2)
            print("Response 2:", rebuilt2.raw_message)
        except Exception as e:
            print("TURN 2 CRASHED:", e)

if __name__ == "__main__":
    test_full_system_failure()
