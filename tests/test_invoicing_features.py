import os
from unittest.mock import MagicMock, patch
import pytest

# Load environment variables just in case
from dotenv import load_dotenv
load_dotenv()

# Pre-import state
from src.agents.state import AgentState

@pytest.fixture(autouse=True)
def mock_llm_setup():
    """Mock ChatGoogleGenerativeAI globally to avoid validation error for missing API Key."""
    with patch('src.agents.agent_1_collector.ChatGoogleGenerativeAI') as mock_collector_llm, \
         patch('src.agents.agent_0_supervisor.ChatGoogleGenerativeAI') as mock_supervisor_llm:
        
        # Set up mock returns
        mock_collector_instance = MagicMock()
        mock_collector_llm.return_value = mock_collector_instance
        
        mock_supervisor_instance = MagicMock()
        mock_supervisor_llm.return_value = mock_supervisor_instance
        
        yield mock_collector_instance, mock_supervisor_instance

# Now import the agents after the patch hook setup
from src.agents.agent_1_collector import OrderCollectorAgent, OrderExtractionModel
from src.agents.agent_0_supervisor import SupervisorAgent, SupervisorOutput
from src.agents.agent_5_invoicing import InvoicingAgent
from src.services.sheets import GoogleSheetsService

def test_collector_invoicing_query_extraction():
    """Test that collector correctly parses invoicing query intent."""
    agent = OrderCollectorAgent()
    state = AgentState(raw_message="Show me the orders pending for invoicing", sender_id="123")
    
    mock_extraction = OrderExtractionModel(
        referenced_order_id=None,
        customer_name=None,
        fabric_type=None,
        embroidery_type=None,
        stitch_count=None,
        quantity=None,
        requested_delivery_date=None,
        mark_as_invoiced=False,
        explain_reasoning=False,
        is_field_override=False,
        is_payment_query=False,
        is_secretary_query=False,
        is_pending_invoicing_query=True,
        is_invoicing_done_update=False,
        invoicing_done_customer=None,
        confirm_duplicate=False
    )
    
    agent.extractor = MagicMock()
    agent.extractor.invoke.return_value = mock_extraction
    
    final_state = agent.process(state)
        
    assert final_state.is_pending_invoicing_query is True
    assert final_state.is_invoicing_done_update is False

def test_collector_invoicing_done_extraction():
    """Test that collector correctly parses invoicing done status updates."""
    agent = OrderCollectorAgent()
    state = AgentState(raw_message="invoicing is done for Ameera", sender_id="123")
    
    mock_extraction = OrderExtractionModel(
        referenced_order_id=None,
        customer_name=None,
        fabric_type=None,
        embroidery_type=None,
        stitch_count=None,
        quantity=None,
        requested_delivery_date=None,
        mark_as_invoiced=False,
        explain_reasoning=False,
        is_field_override=False,
        is_payment_query=False,
        is_secretary_query=False,
        is_pending_invoicing_query=False,
        is_invoicing_done_update=True,
        invoicing_done_customer="Ameera",
        confirm_duplicate=False
    )
    
    agent.extractor = MagicMock()
    agent.extractor.invoke.return_value = mock_extraction
    
    final_state = agent.process(state)
        
    assert final_state.is_invoicing_done_update is True
    assert final_state.invoicing_done_customer == "Ameera"

def test_supervisor_routing_for_invoicing():
    """Test that supervisor routes invoicing intents directly to the invoicing agent."""
    supervisor = SupervisorAgent()
    
    # Query case
    state_query = AgentState(
        raw_message="Show me the orders pending for invoicing",
        is_pending_invoicing_query=True
    )
    
    mock_decision = SupervisorOutput(
        next_step="invoice",
        reasoning="Routing to invoice agent",
        internal_thought="Routing"
    )
    
    supervisor.router = MagicMock()
    supervisor.router.invoke.return_value = mock_decision
    
    final_state = supervisor.process(state_query)
    assert final_state.next_step == "invoice"
    
    # Update case
    state_update = AgentState(
        raw_message="invoicing done for Ameera",
        is_invoicing_done_update=True,
        invoicing_done_customer="Ameera"
    )
    
    final_state = supervisor.process(state_update)
    assert final_state.next_step == "invoice"

    # Termination case (when final_reply is set, it must route to END even if invoicing flag is True)
    state_terminated = AgentState(
        raw_message="invoicing done for Ameera",
        is_invoicing_done_update=True,
        invoicing_done_customer="Ameera",
        final_reply="Invoicing completed, Boss!"
    )
    
    final_state_term = supervisor.process(state_terminated)
    assert final_state_term.next_step == "END"

def test_invoicing_agent_pending_report():
    """Test that InvoicingAgent generates a correctly formatted pending report."""
    agent = InvoicingAgent()
    state = AgentState(
        raw_message="Show me the orders pending for invoicing",
        is_pending_invoicing_query=True
    )
    
    mock_orders = {
        "Ameera": [
            {"order_id": "CJS-7ED337", "fabric_type": "Silk", "embroidery_type": "Logo", "cost": "Rs 1360.0", "completion_date": "2026-05-12"}
        ],
        "Unknown": [
            {"order_id": "CJS-905145", "fabric_type": "Cotton", "embroidery_type": "Flower", "cost": "Rs 0", "completion_date": "2026-05-10"},
            {"order_id": "CJS-869BC6", "fabric_type": "Net", "embroidery_type": "Border", "cost": "Rs 80.18", "completion_date": "2026-05-11"}
        ]
    }
    
    with patch('src.agents.agent_5_invoicing.GoogleSheetsService') as MockServiceClass:
        mock_service = MockServiceClass.return_value
        mock_service.get_orders_pending_invoicing.return_value = mock_orders
        
        final_state = agent.process(state)
        
    assert final_state.final_reply is not None
    # Verify report components
    assert "orders pending for invoicing, Boss!" in final_state.final_reply
    assert "Ameera" in final_state.final_reply
    assert "CJS-7ED337" in final_state.final_reply
    assert "Unknown" in final_state.final_reply
    assert "CJS-905145" in final_state.final_reply
    assert "CJS-869BC6" in final_state.final_reply
    
    # Totals verification: Ameera: 1360, Unknown: 80.18, Grand: 1440.18
    assert "Total for Ameera:* Rs 1360.00" in final_state.final_reply
    assert "Total for Unknown:* Rs 80.18" in final_state.final_reply
    assert "Grand Total:* Rs 1440.18" in final_state.final_reply

def test_invoicing_agent_bulk_update_specific():
    """Test that InvoicingAgent handles bulk completion for a specific customer."""
    agent = InvoicingAgent()
    state = AgentState(
        raw_message="invoicing done for Ameera",
        is_invoicing_done_update=True,
        invoicing_done_customer="Ameera"
    )
    
    with patch('src.agents.agent_5_invoicing.GoogleSheetsService') as MockServiceClass:
        mock_service = MockServiceClass.return_value
        mock_service.mark_invoicing_completed.return_value = 1
        
        final_state = agent.process(state)
        
    mock_service.mark_invoicing_completed.assert_called_once_with("Ameera")
    assert final_state.final_reply is not None
    assert "Invoicing Complete for Ameera!" in final_state.final_reply
    assert "1 pending orders" in final_state.final_reply
    assert "Boss!" in final_state.final_reply

def test_invoicing_agent_bulk_update_all():
    """Test that InvoicingAgent handles bulk completion for all customers."""
    agent = InvoicingAgent()
    state = AgentState(
        raw_message="invoicing is done for all",
        is_invoicing_done_update=True,
        invoicing_done_customer="all"
    )
    
    with patch('src.agents.agent_5_invoicing.GoogleSheetsService') as MockServiceClass:
        mock_service = MockServiceClass.return_value
        mock_service.mark_invoicing_completed.return_value = 5
        
        final_state = agent.process(state)
        
    mock_service.mark_invoicing_completed.assert_called_once_with("all")
    assert final_state.final_reply is not None
    assert "Invoicing Complete!" in final_state.final_reply
    assert "All 5 pending orders" in final_state.final_reply
    assert "Boss!" in final_state.final_reply
