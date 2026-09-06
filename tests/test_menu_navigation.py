import os
from unittest.mock import MagicMock, patch
import pytest
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(autouse=True)
def mock_llm_setup():
    """Mock ChatGoogleGenerativeAI globally to avoid validation error for missing API Key in test environment."""
    with patch('src.agents.agent_1_collector.ChatGoogleGenerativeAI') as mock_collector_llm, \
         patch('src.agents.agent_0_supervisor.ChatGoogleGenerativeAI') as mock_supervisor_llm:
        
        mock_collector_instance = MagicMock()
        mock_collector_llm.return_value = mock_collector_instance
        
        mock_supervisor_instance = MagicMock()
        mock_supervisor_llm.return_value = mock_supervisor_instance
        
        yield mock_collector_instance, mock_supervisor_instance

from src.agents.state import AgentState
from src.agents.agent_1_collector import OrderCollectorAgent, MAIN_MENU_TEXT, ADJUST_MENU_TEXT, INVOICING_MENU_TEXT, VENDORS_MENU_TEXT
from src.agents.agent_0_supervisor import SupervisorAgent

@pytest.fixture
def mock_sheets_service():
    with patch("src.agents.agent_1_collector.GoogleSheetsService") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance
        
        # Default mock returns
        mock_instance.get_active_orders_summary.return_value = [
            {
                "order_id": "CJS-869BC6",
                "customer": "Shwetha",
                "fabric": "Silk",
                "embroidery": "Floral",
                "machine": "Ricoma",
                "delivery_date": "2026-09-08",
                "cost": "Rs 800"
            },
            {
                "order_id": "CJS-A12B34",
                "customer": "Priya",
                "fabric": "Cotton",
                "embroidery": "Neckline",
                "machine": "Aakruthi",
                "delivery_date": "2026-09-10",
                "cost": "Rs 500"
            }
        ]
        mock_instance.get_all_vendors.return_value = [
            {"vendor_id": "V-001", "name": "Coats India", "category": "Thread", "phone": "9845012345"},
            {"vendor_id": "V-002", "name": "Surat Fabrics", "category": "Raw Material", "phone": "9712345678"}
        ]
        mock_instance.get_recent_expenses.return_value = [
            {"date": "2026-09-02", "category": "Maintenance", "description": "Bobbin case", "amount": 450.0},
            {"date": "2026-09-01", "category": "Raw Material", "description": "Zari threads", "amount": 3200.0}
        ]
        yield mock_instance

def test_greeting_triggers_main_menu(mock_sheets_service):
    collector = OrderCollectorAgent()
    
    for word in ["hi", "Hi", "HELLO", "menu", "help", "Start"]:
        state = AgentState(raw_message=word)
        result = collector.process(state)
        
        assert result.active_menu == "MAIN"
        assert result.final_reply is not None
        assert "CJS Designs — Order Manager" in result.final_reply
        assert "1️⃣ *New Order Form*" in result.final_reply
        assert "2️⃣ *Adjust Existing Order*" in result.final_reply
        assert "3️⃣ *Invoicing & Billing*" in result.final_reply
        assert "4️⃣ *Daily Briefing & Tasks*" in result.final_reply
        assert "5️⃣ *Vendors & Expenses*" in result.final_reply

def test_main_menu_option_1_launches_order_form(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="1", active_menu="MAIN")
    result = collector.process(state)
    
    assert result.send_order_form is True
    assert result.active_menu is None
    assert "WhatsApp Order Form" in result.final_reply

def test_main_menu_option_2_adjust_submenu(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="2", active_menu="MAIN")
    result = collector.process(state)
    
    assert result.active_menu == "SELECT_ORDER_FOR_EDIT"
    assert "Select Order to Adjust / Edit" in result.final_reply
    assert "CJS-869BC6" in result.final_reply
    assert "Shwetha" in result.final_reply

def test_order_edit_form_selection(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="1", active_menu="SELECT_ORDER_FOR_EDIT")
    result = collector.process(state)
    
    assert result.send_order_form is True
    assert result.editing_order_id == "CJS-869BC6"
    assert result.flow_init_data is not None
    assert result.flow_init_data["editing_order_id"] == "CJS-869BC6"
    assert result.flow_init_data["init_customer"] == "Shwetha"
    assert "Opening WhatsApp Form to edit Order *CJS-869BC6*" in result.final_reply

def test_main_menu_option_3_invoicing_submenu(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="3", active_menu="MAIN")
    result = collector.process(state)
    
    assert result.active_menu == "INVOICING"
    assert "Invoicing & Billing Menu" in result.final_reply
    assert "Pending Invoicing Report" in result.final_reply
    assert "Mark Order as Invoiced" in result.final_reply

def test_main_menu_option_4_secretary_briefing(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="4", active_menu="MAIN")
    result = collector.process(state)
    
    assert result.is_secretary_query is True
    assert result.active_menu is None

def test_main_menu_option_5_vendors_submenu(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="5", active_menu="MAIN")
    result = collector.process(state)
    
    assert result.active_menu == "VENDORS"
    assert "Vendors & Expenses Menu" in result.final_reply
    assert "Active Vendors Directory" in result.final_reply
    assert "Recent Expenses" in result.final_reply

def test_delivery_date_adjustment_flow(mock_sheets_service):
    collector = OrderCollectorAgent()
    
    # Step 1: Select 1 from ADJUST menu (or send 21)
    state = AgentState(raw_message="1", active_menu="ADJUST")
    result1 = collector.process(state)
    assert result1.active_menu == "SELECT_ORDER_FOR_DATE"
    assert "CJS-869BC6" in result1.final_reply
    assert "CJS-A12B34" in result1.final_reply
    
    # Step 2: Choose Order #1
    state2 = AgentState(raw_message="1", active_menu="SELECT_ORDER_FOR_DATE")
    result2 = collector.process(state2)
    assert result2.active_menu == "INPUT_NEW_DATE"
    assert result2.pending_adjustment_order_id == "CJS-869BC6"
    assert result2.pending_adjustment_type == "delivery_date"
    assert "Selected order *CJS-869BC6*" in result2.final_reply
    
    # Step 3: Input new date
    state3 = AgentState(
        raw_message="2026-09-15",
        active_menu="INPUT_NEW_DATE",
        pending_adjustment_order_id="CJS-869BC6",
        pending_adjustment_type="delivery_date"
    )
    result3 = collector.process(state3)
    assert result3.is_field_override is True
    assert result3.order_id == "CJS-869BC6"
    assert result3.override_field == "delivery_date"
    assert result3.override_value == "2026-09-15"
    assert result3.active_menu is None
    assert "Field Updated!" in result3.final_reply

def test_machine_reassign_flow(mock_sheets_service):
    collector = OrderCollectorAgent()
    
    # Direct code 22
    state = AgentState(raw_message="22")
    result1 = collector.process(state)
    assert result1.active_menu == "SELECT_ORDER_FOR_MACHINE"
    
    # Select Order #2
    state2 = AgentState(raw_message="2", active_menu="SELECT_ORDER_FOR_MACHINE")
    result2 = collector.process(state2)
    assert result2.active_menu == "SELECT_MACHINE_CHOICE"
    assert result2.pending_adjustment_order_id == "CJS-A12B34"
    assert "Which machine would you like to assign?" in result2.final_reply
    
    # Select Ricoma (Option 1)
    state3 = AgentState(
        raw_message="1",
        active_menu="SELECT_MACHINE_CHOICE",
        pending_adjustment_order_id="CJS-A12B34",
        pending_adjustment_type="machine"
    )
    result3 = collector.process(state3)
    assert result3.is_field_override is True
    assert result3.order_id == "CJS-A12B34"
    assert result3.override_field == "machine"
    assert result3.override_value == "Ricoma"
    assert result3.active_menu is None
    assert "Machine Reassigned!" in result3.final_reply

def test_cost_override_flow(mock_sheets_service):
    collector = OrderCollectorAgent()
    
    # Direct code 23
    state = AgentState(raw_message="23")
    result1 = collector.process(state)
    assert result1.active_menu == "SELECT_ORDER_FOR_COST"
    
    # Select Order #1
    state2 = AgentState(raw_message="1", active_menu="SELECT_ORDER_FOR_COST")
    result2 = collector.process(state2)
    assert result2.active_menu == "INPUT_NEW_COST"
    assert result2.pending_adjustment_order_id == "CJS-869BC6"
    
    # Enter Rs 950
    state3 = AgentState(
        raw_message="950",
        active_menu="INPUT_NEW_COST",
        pending_adjustment_order_id="CJS-869BC6",
        pending_adjustment_type="cost"
    )
    result3 = collector.process(state3)
    assert result3.is_field_override is True
    assert result3.order_id == "CJS-869BC6"
    assert result3.override_field == "cost"
    assert result3.override_value == "Rs 950"
    assert result3.active_menu is None
    assert "Cost Updated!" in result3.final_reply

def test_direct_code_31_pending_invoicing(mock_sheets_service):
    mock_sheets_service.get_orders_pending_invoicing.return_value = {
        "Priya": [{"order_id": "CJS-101", "cost": "Rs 1,500.0"}],
        "Ammu": [{"order_id": "CJS-102", "cost": "Rs 2,000"}, {"order_id": "CJS-103", "cost": "Rs 500"}]
    }
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="31")
    result = collector.process(state)
    
    assert result.is_pending_invoicing_query is True
    assert result.active_menu is None
    assert "Pending Invoices" in result.final_reply
    assert "• *Ammu* — Rs 2,500" in result.final_reply
    assert "• *Priya* — Rs 1,500" in result.final_reply

def test_direct_code_34_debtors(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="34")
    result = collector.process(state)
    
    assert result.is_payment_query is True
    assert result.active_menu is None

def test_direct_code_51_vendors_directory(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="51")
    result = collector.process(state)
    
    assert "Active Vendors Directory" in result.final_reply
    assert "Coats India" in result.final_reply
    assert "Surat Fabrics" in result.final_reply
    assert result.active_menu is None

def test_direct_code_52_recent_expenses(mock_sheets_service):
    collector = OrderCollectorAgent()
    state = AgentState(raw_message="52")
    result = collector.process(state)
    
    assert "Recent Expenses (Expense Ledger)" in result.final_reply
    assert "Bobbin case" in result.final_reply
    assert "Zari threads" in result.final_reply
    assert result.active_menu is None

def test_menu_cancellation_and_back(mock_sheets_service):
    collector = OrderCollectorAgent()
    
    # Cancel resets everything
    state1 = AgentState(raw_message="cancel", active_menu="ADJUST")
    res1 = collector.process(state1)
    assert res1.active_menu is None
    assert "Operation cancelled" in res1.final_reply
    
    # '0' returns to main menu
    state2 = AgentState(raw_message="0", active_menu="ADJUST")
    res2 = collector.process(state2)
    assert res2.active_menu == "MAIN"
    assert "CJS Designs — Order Manager" in res2.final_reply

def test_supervisor_routes_menu_to_end_without_guardrail():
    from src.agents.agent_0_supervisor import SupervisorOutput
    supervisor = SupervisorAgent()
    supervisor.router = MagicMock()
    supervisor.router.invoke.return_value = SupervisorOutput(
        next_step="collector", reasoning="Test", internal_thought="Test"
    )
    
    # Case 1: State has active_menu and final_reply -> Should force next_step = "END"
    state = AgentState(
        raw_message="Hi",
        active_menu="MAIN",
        final_reply=MAIN_MENU_TEXT
    )
    result = supervisor.process(state)
    assert result.next_step == "END"
    assert result.raw_message == MAIN_MENU_TEXT
    
    # Case 2: State has send_order_form=True -> Should force next_step = "END"
    state2 = AgentState(
        raw_message="1",
        send_order_form=True,
        final_reply="Opening WhatsApp Order Form for you, Boss! 📋"
    )
    result2 = supervisor.process(state2)
    assert result2.next_step == "END"
