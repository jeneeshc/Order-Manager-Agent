import os
from dotenv import load_dotenv
load_dotenv()

from src.workflow.main_graph import cjs_bot
from src.agents.state import AgentState
from unittest.mock import MagicMock, patch

def test_supervisor_multi_intent():
    print("\n--- Testing Supervisor Multi-Intent Orchestration ---")
    
    # Mocking Sheets Service inside the agents
    with patch('src.services.sheets.GoogleSheetsService') as MockSheets:
        mock_db = MockSheets.return_value
        
        # Mock get_order to return nothing (new order)
        mock_db.get_order.return_value = None
        
        # Mock machine availability
        mock_db.get_machine_availability.return_value = {
            "Ricoma-1": MagicMock(),
            "Aakruthi-1": MagicMock()
        }
        
        # Mock holidays
        mock_db.get_holidays.return_value = []
        
        # Mock costing rules
        mock_db.get_costing_rules.return_value = {
            ("standard", "silk"): {"unit_count": 1000, "cost": 10.0}
        }
        
        # Mock secretary data
        mock_db.get_secretary_data.return_value = {
            "today": "2026-03-29",
            "orders_due_today": [{"id": "CJS-101", "customer": "Alice"}],
            "pending_invoices_old": [],
            "holiday_status": None,
            "upcoming_holidays": [],
            "reminders": []
        }

        # Mixed Intent: New Order + Secretary Query
        initial_message = "Hi Siny, create a new order for Bob. 5000 stitches of standard embroidery on Silk. Also, what else is due today?"
        state = AgentState(raw_message=initial_message, sender_id="123")
        
        print(f"Input Message: {initial_message}")
        print("Starting Graph execution...")
        
        final_state_dict = cjs_bot.invoke(state)
        final_state = AgentState(**final_state_dict)
        
        print("\n--- EXECUTION LOGS ---")
        print(final_state.aggregated_reasoning)
        
        print("\n--- FINAL SYNTHESIZED RESPONSE ---")
        print(final_state.raw_message)
        
        # Assertions
        assert final_state.customer_name == "Bob"
        assert final_state.stitch_count == 5000
        assert final_state.total_cost_rs is not None
        assert "Alice" in final_state.raw_message # Should mention the other order due today from mock_data
        
        print("\nMulti-Intent Test Passed!")

if __name__ == "__main__":
    test_supervisor_multi_intent()
