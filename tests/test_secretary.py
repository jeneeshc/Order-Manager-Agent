import os
from dotenv import load_dotenv
from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState
from src.agents.agent_6_secretary import SecretaryAgent
from unittest.mock import MagicMock, patch

load_dotenv()

def test_secretary_intent_extraction():
    print("\n--- Testing Secretary Intent Extraction ---")
    agent = OrderCollectorAgent()
    state = AgentState(raw_message="What are my tasks for today? Please give me a summary.", sender_id="123")
    
    # We don't need to mock sheets here yet because extraction happens first
    final_state = agent.process(state)
    
    print(f"DEBUG: raw_message={state.raw_message}")
    print(f"DEBUG: is_secretary_query={final_state.is_secretary_query}")
    print(f"DEBUG: is_missing_info={final_state.is_missing_info}")
    print(f"DEBUG: customer_name={final_state.customer_name}")
    assert final_state.is_secretary_query is True
    print("Intent Extraction Passed!")

def test_secretary_report_generation():
    print("\n--- Testing Secretary Report Generation ---")
    secretary = SecretaryAgent()
    
    # Mock data as if it came from sheets.py
    mock_data = {
        "today": "2026-03-29",
        "orders_due_today": [
            {"id": "CJS-101", "customer": "Alice", "fabric": "Silk", "cost": "1500", "machine": "Ricoma"},
            {"id": "CJS-102", "customer": "Bob", "fabric": "Cotton", "cost": "800", "machine": "Aakruthi"}
        ],
        "pending_invoices_old": [
            {"id": "CJS-090", "customer": "Charlie", "date": "2026-03-10", "completion_date": "2026-03-12", "cost": "3000"},
            {"id": "CJS-091", "customer": "Diana", "date": "2026-03-11", "completion_date": "", "cost": "1200"}
        ],
        "holiday_status": None,
        "upcoming_holidays": ["02-April-2026"],
        "reminders": ["Submit GST (Monthly Requirement)"]
    }
    
    report = secretary.generate_daily_summary(mock_data)
    print("Generated Report:\n")
    print(report)
    print("\nReport Generation Passed!")

if __name__ == "__main__":
    test_secretary_intent_extraction()
    test_secretary_report_generation()
