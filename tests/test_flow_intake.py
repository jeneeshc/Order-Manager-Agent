import pytest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()

@pytest.fixture(autouse=True)
def mock_llm_setup():
    with patch('src.agents.agent_1_collector.ChatGoogleGenerativeAI') as mock_collector_llm, \
         patch('src.agents.agent_0_supervisor.ChatGoogleGenerativeAI') as mock_supervisor_llm:
        mock_c = MagicMock()
        mock_collector_llm.return_value = mock_c
        mock_s = MagicMock()
        mock_supervisor_llm.return_value = mock_s
        yield mock_c, mock_s

from src.agents.state import AgentState
from src.agents.agent_3_estimator import EstimationAgent
from src.services.sheets import GoogleSheetsService

def test_flow_payload_injection_and_costing():
    """Verify that interactive form payload with hours_required correctly computes costing."""
    interactive_payload = {
        "customer_name": "Meera Boutique",
        "fabric_type": "Silk",
        "garment_type": "Kurti",
        "embroidery_style": "Floral",
        "stitch_count": "45000",
        "hours_required": "2.5",
        "delivery_date": "2026-09-20"
    }

    state = AgentState()
    state.customer_name = interactive_payload["customer_name"]
    state.fabric_type = interactive_payload["fabric_type"]
    state.embroidery_type = f"{interactive_payload['embroidery_style']} {interactive_payload['garment_type']}".strip()
    state.stitch_count = int(interactive_payload["stitch_count"])
    state.labor_hours = float(interactive_payload["hours_required"])
    state.requested_delivery_date = interactive_payload["delivery_date"]

    assert state.stitch_count == 45000
    assert state.labor_hours == 2.5

    mock_config = {
        "Cost per 1000 Stitches": 10.0,
        "Hourly Labor Rate": 100.0,
        "Profit Margin Percent": 20.0,
        "GST Rate Percent": 18.0
    }

    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        with patch.object(GoogleSheetsService, 'get_config_variables', return_value=mock_config):
            estimator = EstimationAgent()
            res = estimator.process(state)

            # Stitches: (45000 / 1000) * 10 = Rs 450.0
            # Labor: 2.5 * 100 = Rs 250.0
            # Base Cost: Rs 700.0
            # Profit Margin (20%): Rs 140.0
            # Subtotal: Rs 840.0
            # GST (18%): 840.0 * 0.18 = Rs 151.2
            # Total Cost: Rs 991.2
            assert res.base_cost_rs == 700.0
            assert res.profit_margin_rs == 140.0
            assert res.gst_amount_rs == 151.2
            assert res.total_cost_rs == 991.2
            assert res.invoice_status == "Estimated"
            assert "Strict 4-Factor Cost Breakdown" in res.aggregated_reasoning

def test_flow_json_structure():
    """Verify that deploy_flow.py's FLOW_JSON has hours_required and correct types."""
    from scripts.deploy_flow import FLOW_JSON

    screen = FLOW_JSON["screens"][0]
    form_children = screen["layout"]["children"][0]["children"]
    field_names = [child.get("name") for child in form_children if "name" in child]

    assert "customer_name" in field_names
    assert "fabric_type" in field_names
    assert "embroidery_style" in field_names
    assert "stitch_count" in field_names
    assert "hours_required" in field_names
    assert "delivery_date" in field_names

    footer = screen["layout"]["children"][1]
    payload = footer["on-click-action"]["payload"]
    assert "hours_required" in payload
    assert payload["hours_required"] == "${form.hours_required}"
