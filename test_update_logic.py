from src.agents.agent_1_collector import OrderCollectorAgent
from src.agents.state import AgentState
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()

# Mock the database service to return a dummy order for "CJS-12345"
mock_db = MagicMock()
mock_db.get_order.return_value = {
    "fabric_type": "Cotton",
    "embroidery_type": "Logo",
    "stitch_count": 5000,
    "customer_name": "Test Customer"
}

def test_collector_with_order_id():
    agent = OrderCollectorAgent()
    state = AgentState(raw_message="Update order CJS-12345: change to velvet and 6000 stitches.", sender_id="123")
    
    # Patch GoogleSheetsService inside the agent's process method
    with patch('src.agents.agent_1_collector.GoogleSheetsService', return_value=mock_db):
        final_state = agent.process(state)
        
    print(f"DEBUG: order_id={final_state.order_id}")
    print(f"DEBUG: fabric_type={final_state.fabric_type}")
    print(f"DEBUG: embroidery_type={final_state.embroidery_type}")
    print(f"DEBUG: stitch_count={final_state.stitch_count}")
    print(f"DEBUG: is_missing_info={final_state.is_missing_info}")
    print(f"DEBUG: missing_fields_prompt={final_state.missing_fields_prompt}")
    
    assert final_state.order_id == "CJS-12345"
    assert final_state.fabric_type == "velvet"
    assert final_state.stitch_count == 6000
    print("Test Passed!")

if __name__ == "__main__":
    test_collector_with_order_id()
