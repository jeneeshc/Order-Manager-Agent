import os
from dotenv import load_dotenv
load_dotenv()
from unittest.mock import MagicMock, patch
from src.agents.agent_0_supervisor import SupervisorAgent
from src.agents.agent_1_collector import OrderCollectorAgent, OrderExtractionModel
from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

def test_supervisor_guardrail_missing_customer():
    # If the LLM router suggests routing to scheduler but customer name is missing,
    # the programmatic guardrail must override next_step to 'collector'.
    state = AgentState(
        raw_message="New order on Cotton, 10000 stitches.",
        fabric_type="Cotton",
        stitch_count=10000,
        embroidery_type="Logo",
        customer_name=None,      # MISSING customer_name
        is_missing_info=False
    )
    
    agent = SupervisorAgent()
    
    # Mock LLM router behavior to return next_step="scheduler" (bypassing collector)
    mock_decision = MagicMock()
    mock_decision.next_step = "scheduler"
    mock_decision.reasoning = "All details are extracted."
    
    with patch.object(agent, 'router') as mock_router:
        mock_router.invoke.return_value = mock_decision
        final_state = agent.process(state)
        
    assert final_state.next_step == "collector"
    assert "Guardrail overridden to collector" in final_state.aggregated_reasoning
    print("test_supervisor_guardrail_missing_customer passed!")


def test_collector_hydration_on_update():
    agent = OrderCollectorAgent()
    state = AgentState(
        raw_message="Update order CJS-12345: change to velvet.",
        sender_id="123"
    )
    
    # Mock extraction model returning reference
    mock_extraction = OrderExtractionModel(
        referenced_order_id="CJS-12345",
        customer_name=None,
        fabric_type="velvet",
        embroidery_type=None,
        stitch_count=None,
        quantity=None,
        requested_delivery_date=None,
        mark_as_invoiced=False,
        explain_reasoning=False,
        is_field_override=False,
        is_payment_query=False,
        is_secretary_query=False,
        confirm_duplicate=False
    )
    
    mock_db = MagicMock()
    mock_db.get_order.return_value = {
        "customer_id": "1005",
        "fabric_type": "Cotton",
        "embroidery_type": "Logo",
        "stitch_count": 5000
    }
    mock_db.get_all_customers_map.return_value = {"1005": "Anna"}
    mock_db.create_customer_if_not_exists.return_value = "1005"
    
    with patch.object(agent, 'extractor') as mock_extractor, \
         patch('src.agents.agent_1_collector.GoogleSheetsService', return_value=mock_db):
        mock_extractor.invoke.return_value = mock_extraction
        final_state = agent.process(state)
        
    assert final_state.order_id == "CJS-12345"
    assert final_state.customer_id == "1005"
    assert final_state.customer_name == "Anna"
    assert final_state.fabric_type == "velvet"  # updated
    assert final_state.stitch_count == 5000      # hydrated
    print("test_collector_hydration_on_update passed!")


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
