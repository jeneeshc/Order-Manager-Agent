import os
import pytest
from dotenv import load_dotenv
load_dotenv()
os.environ.setdefault("GEMINI_API_KEY", "test_key")

from unittest.mock import patch, MagicMock
from src.agents.state import AgentState
from src.agents.single_agent import CJSSingleAgent
from src.services.sheets import GoogleSheetsService

@pytest.fixture
def agent():
    with patch("src.agents.single_agent.ChatGoogleGenerativeAI"), \
         patch("src.agents.agent_6_secretary.ChatGoogleGenerativeAI"):
        return CJSSingleAgent()

def test_single_agent_menu_and_form_launch(agent):
    # Greeting triggers main menu
    state = AgentState(raw_message="hi")
    res = agent.process(state)
    assert res.active_menu == "MAIN"
    assert "🧵 *CJS Designs — Order Manager* 🧵" in res.final_reply

    # Option 1 launches order form
    state1 = AgentState(raw_message="1", active_menu="MAIN")
    res1 = agent.process(state1)
    assert res1.send_order_form is True
    assert "Opening WhatsApp Order Form" in res1.final_reply

def test_single_agent_master_data_customer(agent):
    # Option 6 prompts for customer
    state6 = AgentState(raw_message="6", active_menu="MAIN")
    res6 = agent.process(state6)
    assert res6.active_menu == "INPUT_NEW_CUSTOMER"
    assert "Add New Customer" in res6.final_reply

    # Input customer creates record
    with patch.object(GoogleSheetsService, "create_customer_if_not_exists", return_value="CUST-2001") as mock_c:
        input_state = AgentState(raw_message="Anjali Silks, 9847112233, Kottayam", active_menu="INPUT_NEW_CUSTOMER")
        res_done = agent.process(input_state)
        assert res_done.active_menu is None
        assert "Anjali Silks" in res_done.final_reply
        assert "CUST-2001" in res_done.final_reply
        mock_c.assert_called_once_with("Anjali Silks", phone="9847112233", address="Kottayam")

def test_single_agent_conversational_chat(agent):
    mock_response = MagicMock()
    mock_response.content = "Hello Boss! Yes, we can handle baptism sets on Aakruthi."
    agent.llm.invoke = MagicMock(return_value=mock_response)

    state = AgentState(raw_message="Can we make baptism sets this week?")
    res = agent.process(state)
    assert "Hello Boss!" in res.final_reply
    agent.llm.invoke.assert_called_once()
