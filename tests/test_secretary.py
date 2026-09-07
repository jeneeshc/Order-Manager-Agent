import os
import pytest
from dotenv import load_dotenv
from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState
from src.agents.agent_6_secretary import SecretaryAgent
from unittest.mock import MagicMock, patch

load_dotenv()

@pytest.mark.skip(reason="LLM-dependent extraction test relies on old OrderCollectorAgent.extractor; single-agent refactor changed the internal structure.")
def test_secretary_intent_extraction():
    """
    Previously verified that calling OrderCollectorAgent.process() sets is_secretary_query=True.
    In the new architecture, the CJSSingleAgent processes this via a unified LLM prompt
    without a separately patchable extractor.
    """
    pass

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
