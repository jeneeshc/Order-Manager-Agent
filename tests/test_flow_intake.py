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
    """Verify that interactive form payload with hours and stitches computes 4-factor costing."""
    state = AgentState()
    state.customer_name = "Meera Boutique"
    state.order_type = "Machine Embroidery"
    state.template_name = "Kurti Neck"
    state.stitch_count = 45000
    state.quantity = 1
    state.labor_hours = 2.5
    state.requested_delivery_date = "2026-09-20"

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
    """Verify that deploy_flow.py's FLOW_JSON has dropdowns and write-in fields."""
    from scripts.deploy_flow import build_flow_json

    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        with patch.object(GoogleSheetsService, 'get_all_customers_list', return_value=["Ammu", "Anna"]):
            with patch.object(GoogleSheetsService, 'get_description_templates', return_value=[{"template_name": "Baptism", "machine": "Aakruthi"}]):
                flow_json = build_flow_json()

    screen = flow_json["screens"][0]
    form_children = screen["layout"]["children"][0]["children"]
    field_names = [child.get("name") for child in form_children if "name" in child]

    assert "customer_select" in field_names
    assert "new_customer_name" in field_names
    assert "order_type_select" in field_names
    assert "new_order_type" in field_names
    assert "template_select" in field_names
    assert "new_template_name" in field_names
    assert "quantity" in field_names
    assert "delivery_date" in field_names
    assert "stitch_count" in field_names
    assert "labor_hours" in field_names

    footer = screen["layout"]["children"][1]
    payload = footer["on-click-action"]["payload"]
    assert payload["customer_select"] == "${form.customer_select}"
    assert payload["new_customer_name"] == "${form.new_customer_name}"
    assert payload["order_type_select"] == "${form.order_type_select}"
    assert payload["template_select"] == "${form.template_select}"
    assert payload["quantity"] == "${form.quantity}"
    assert payload["delivery_date"] == "${form.delivery_date}"
