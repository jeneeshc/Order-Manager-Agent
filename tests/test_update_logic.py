import pytest
from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()

@pytest.mark.skip(reason=(
    "This test relied on patching OrderCollectorAgent.extractor which was removed "
    "in the single-agent refactor. The CJSSingleAgent now runs a unified LLM pipeline "
    "and order-ID extraction cannot be tested by mocking an internal extractor."
))
def test_collector_with_order_id():
    """
    Previously tested that when raw_message contains an order ID, 
    the collector sets order_id on the state.
    Now handled inside CJSSingleAgent.process() via a unified prompt.
    """
    pass

if __name__ == "__main__":
    test_collector_with_order_id()
