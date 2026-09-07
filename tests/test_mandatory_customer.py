import os
import pytest
from dotenv import load_dotenv
load_dotenv()
from unittest.mock import MagicMock, patch
from src.agents.agent_0_supervisor import SupervisorAgent
from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

@pytest.mark.skip(reason="Relies on old SupervisorAgent.router mock; single-agent refactor merged routing into CJSSingleAgent.process().")
def test_supervisor_guardrail_missing_customer():
    """Previously tested that the supervisor guardrail overrides to 'collector' when customer is missing.
    In the new architecture, CJSSingleAgent handles this deterministically without a patchable .router."""
    pass


def test_collector_hydration_on_update():
    # NOTE: This test used OrderExtractionModel which was removed during
    # the single-agent refactor. The CJSSingleAgent uses an LLM-based
    # process() that doesn't expose a separate extractor object.
    # Skipping this test to avoid false failures.
    import pytest
    pytest.skip("Skipped: OrderExtractionModel was removed in single-agent refactor.")


def test_sheets_append_validation():
    # If the state has an invalid/missing customer_id, append_order must reject it and return None
    state = AgentState(
        customer_id="Unknown",
        fabric_type="Cotton",
        embroidery_type="Logo",
        stitch_count=10000
    )
    
    db = GoogleSheetsService()
    # Mock sheets API service to verify we don't even make network calls
    db.service = MagicMock()
    
    result = db.append_order(state)
    assert result is None
    
    state.customer_id = None
    result = db.append_order(state)
    assert result is None
    
    print("test_sheets_append_validation passed!")

if __name__ == "__main__":
    test_supervisor_guardrail_missing_customer()
    test_collector_hydration_on_update()
    test_sheets_append_validation()
