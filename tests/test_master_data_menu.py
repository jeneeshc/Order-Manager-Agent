import pytest
from unittest.mock import patch, MagicMock
from src.agents.state import AgentState
from src.agents.agent_1_collector import OrderCollectorAgent
from src.services.sheets import GoogleSheetsService

@pytest.fixture
def collector():
    with patch("src.agents.agent_1_collector.ChatGoogleGenerativeAI"):
        agent = OrderCollectorAgent()
        return agent

def test_menu_option_6_add_customer_flow(collector):
    # Step 1: Boss sends '6' from main menu
    state = AgentState(raw_message="6", active_menu="MAIN")
    res_state = collector.process(state)
    assert res_state.active_menu == "INPUT_NEW_CUSTOMER"
    assert "Add New Customer" in res_state.final_reply

    # Step 2: Boss replies with customer details
    with patch.object(GoogleSheetsService, "create_customer_if_not_exists", return_value="CUST-1099") as mock_create:
        input_state = AgentState(
            raw_message="Kavya Silks, 9876543210, Thrissur",
            active_menu="INPUT_NEW_CUSTOMER"
        )
        final_state = collector.process(input_state)
        assert final_state.active_menu is None
        assert "Kavya Silks" in final_state.final_reply
        assert "CUST-1099" in final_state.final_reply
        mock_create.assert_called_once_with("Kavya Silks", phone="9876543210", address="Thrissur")

def test_menu_option_7_add_template_flow(collector):
    # Step 1: Boss sends '7' from main menu
    state = AgentState(raw_message="7", active_menu="MAIN")
    res_state = collector.process(state)
    assert res_state.active_menu == "INPUT_NEW_TEMPLATE"
    assert "Add New Description Template" in res_state.final_reply

    # Step 2: Boss replies with template details
    with patch.object(GoogleSheetsService, "create_template_if_not_exists", return_value=True) as mock_create:
        input_state = AgentState(
            raw_message="Bridal Peacock Heavy, Ricoma, 3.5, 45000",
            active_menu="INPUT_NEW_TEMPLATE"
        )
        final_state = collector.process(input_state)
        assert final_state.active_menu is None
        assert "Bridal Peacock Heavy" in final_state.final_reply
        assert "Ricoma" in final_state.final_reply
        assert "3.5 hrs" in final_state.final_reply
        mock_create.assert_called_once_with(
            order_type="Machine Embroidery",
            template_name="Bridal Peacock Heavy",
            machine="Ricoma",
            default_labor_hours=3.5
        )

def test_menu_option_8_add_order_type_flow(collector):
    # Step 1: Boss sends '8' from main menu
    state = AgentState(raw_message="8", active_menu="MAIN")
    res_state = collector.process(state)
    assert res_state.active_menu == "INPUT_NEW_ORDER_TYPE"
    assert "Add New Order Type" in res_state.final_reply

    # Step 2: Boss replies with order type name
    input_state = AgentState(
        raw_message="Cutwork Border Embroidery",
        active_menu="INPUT_NEW_ORDER_TYPE"
    )
    final_state = collector.process(input_state)
    assert final_state.active_menu is None
    assert "Cutwork Border Embroidery" in final_state.final_reply
