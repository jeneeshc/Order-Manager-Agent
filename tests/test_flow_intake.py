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
    assert "order_type_select" in field_names
    assert "template_select" in field_names
    assert "quantity" in field_names
    assert "delivery_date" in field_names
    assert "stitch_count" in field_names
    assert "labor_minutes" in field_names
    assert "photo_picker" in field_names

    photo_picker_component = next(c for c in form_children if c.get("name") == "photo_picker")
    assert photo_picker_component.get("type") == "PhotoPicker"
    assert photo_picker_component.get("photo-source") == "camera_gallery"
    assert photo_picker_component.get("min-uploaded-photos") == 0
    assert photo_picker_component.get("max-uploaded-photos") == 1

    # Verify write-in textboxes are excluded
    assert "new_customer_name" not in field_names
    assert "new_order_type" not in field_names
    assert "new_template_name" not in field_names

    footer = screen["layout"]["children"][1]
    payload = footer["on-click-action"]["payload"]
    assert payload["customer_select"] == "${form.customer_select}"
    assert payload["order_type_select"] == "${form.order_type_select}"
    assert payload["template_select"] == "${form.template_select}"
    assert payload["photo_picker"] == "${form.photo_picker}"

def test_labor_minutes_conversion_and_template_lookup():
    """Verify that labor_minutes (e.g. 360 mins) converts to hours (6.0 hrs) and base stitch count is applied."""
    state = AgentState()
    state.customer_name = "Ammu"
    state.order_type = "Machine Embroidery"
    state.template_name = "Saree Scallop"
    state.labor_minutes = 360.0 # 6 hours
    state.stitch_count = 50000

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

            # Labor: 360 mins / 60 = 6.0 hrs * Rs 100 = Rs 600.0
            # Stitches: (50000 / 1000) * 10 = Rs 500.0
            # Base Cost: 500 + 600 = Rs 1100.0
            # Margin (20%): 220.0
            # GST (18%): (1100 + 220) * 0.18 = 237.6
            # Total: 1100 + 220 + 237.6 = Rs 1557.6
            assert res.labor_hours == 6.0
            assert res.base_cost_rs == 1100.0
            assert res.profit_margin_rs == 220.0
            assert res.total_cost_rs == 1557.6

def test_customer_forwardable_response_omits_internal_costing():
    """Verify that the webhook order confirmation response omits GST, margin, and base cost."""
    from src.api.main import process_webhook_message
    
    mock_payload = {
        "customer_select": "Meera Boutique",
        "order_type_select": "Machine Embroidery",
        "template_select": "Kurti Neck",
        "quantity": "2",
        "delivery_date": "2026-09-25",
        "stitch_count": "30000",
        "labor_minutes": "120",
        "photo_picker": [
            {
                "id": "mock_media_12345",
                "mime_type": "image/jpeg",
                "file_name": "design.jpg"
            }
        ]
    }

    sent_messages = []
    sent_images = []

    with patch('src.api.main.whatsapp_service') as mock_wa, \
         patch('src.api.main.db_service') as mock_db, \
         patch('src.api.main.storage_service') as mock_storage, \
         patch('src.api.main.memory_service') as mock_mem:
        
        mock_wa.download_media.return_value = (b"fake_image_bytes", "image/jpeg")
        mock_wa.send_text_message.side_effect = lambda to, msg: sent_messages.append((to, msg))
        mock_wa.send_image_message.side_effect = lambda to, img, caption: sent_images.append((to, img, caption))
        mock_db.create_customer_if_not_exists.return_value = "CUST-001"
        mock_db.get_template_by_name.return_value = {"labor_minutes": 60, "stitch_count": 20000}
        mock_db.get_config_variables.return_value = {
            "Cost per 1000 Stitches": 10.0,
            "Hourly Labor Rate": 100.0,
            "Profit Margin Percent": 20.0,
            "GST Rate Percent": 18.0
        }
        mock_db.append_order.return_value = "CJS-MOCK01"
        mock_storage.upload_order_image.return_value = {
            "file_id": "order_images/2026_09/CJS-MOCK01.jpg",
            "view_link": "https://storage.googleapis.com/cjs-designs-501004-media/order_images/2026_09/CJS-MOCK01.jpg",
            "public_url": "https://storage.googleapis.com/cjs-designs-501004-media/order_images/2026_09/CJS-MOCK01.jpg"
        }

        process_webhook_message("+919999999999", "[FORM_SUBMITTED]", mock_payload)

        # Verify an image message was sent with caption
        assert len(sent_images) == 1
        to_phone, media_id, caption = sent_images[0]
        assert to_phone == "+919999999999"
        assert media_id == "mock_media_12345"
        
        # Verify customer-forwardable contents matching user's exact template:
        assert "✅ New Order Created: CJS-" in caption
        assert "* Customer: Meera Boutique" in caption
        assert "* Order Type: Machine Embroidery" in caption
        assert "* Template: Kurti Neck" in caption
        assert "* Quantity: 2 pcs" in caption
        assert "* Est. Delivery Date:" in caption
        assert "* Total Amount:" in caption
        assert "* Design Image: https://storage.googleapis.com/cjs-designs-501004-media/order_images/2026_09/CJS-MOCK01.jpg" in caption

        # Verify STRICT omission of internal details:
        assert "* Assigned Machine:" not in caption
        assert "GST" not in caption
        assert "Profit Margin" not in caption
        assert "Base Cost" not in caption
        assert "Google Sheets" not in caption

