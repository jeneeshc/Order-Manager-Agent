import pytest
from unittest.mock import MagicMock, patch
from src.services.sheets import GoogleSheetsService
from src.agents.state import AgentState

def test_append_order_writes_image_url_to_column_q():
    """Verify that append_order includes image_url in Column Q of Orders tab."""
    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        svc = GoogleSheetsService()
        svc.spreadsheet_id = "dummy_sheet"
        svc.service = MagicMock()
        svc.ensure_orders_image_header = MagicMock()

        mock_append = MagicMock()
        mock_append.execute.return_value = {"updates": {"updatedRows": 1}}
        svc.service.spreadsheets().values().append.return_value = mock_append

        state = AgentState(
            order_id="CJS-TEST99",
            customer_id="CUST-101",
            customer_name="Anita Boutique",
            order_type="Machine Embroidery",
            template_name="Zari Work",
            quantity=1,
            labor_hours=1.5,
            stitch_count=25000,
            image_url="https://drive.google.com/file/d/xyz123/view"
        )

        order_id = svc.append_order(state)
        assert order_id == "CJS-TEST99"

        call_args = svc.service.spreadsheets().values().append.call_args[1]
        assert call_args["range"] == "'Orders'!A:Q"
        values = call_args["body"]["values"][0]
        # Column Q is index 16
        assert len(values) == 17
        assert values[1] == "CJS-TEST99"
        assert values[16] == "https://drive.google.com/file/d/xyz123/view"

def test_update_order_from_form_preserves_existing_image_if_not_updated():
    """Verify update_order_from_form keeps existing Column Q image_url if state has no new image."""
    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        svc = GoogleSheetsService()
        svc.spreadsheet_id = "dummy_sheet"
        svc.service = MagicMock()
        svc.ensure_orders_image_header = MagicMock()

        # Mock finding order row at index 2 (row 3)
        mock_get_b = MagicMock()
        mock_get_b.execute.return_value = {"values": [["Order ID"], ["CJS-OLD01"], ["CJS-TARGET"]]}
        
        # Mock reading Col O:Q of target row (row 3)
        mock_get_oq = MagicMock()
        mock_get_oq.execute.return_value = {"values": [["Existing reasoning", "", "https://drive.google.com/existing_image"]]}

        def side_effect_get(spreadsheetId, range):
            mock_req = MagicMock()
            if "B:B" in range:
                mock_req.execute.return_value = {"values": [["Order ID"], ["CJS-OLD01"], ["CJS-TARGET"]]}
            elif "O3:Q3" in range:
                mock_req.execute.return_value = {"values": [["Existing reasoning", "", "https://drive.google.com/existing_image"]]}
            return mock_req

        svc.service.spreadsheets().values().get.side_effect = side_effect_get

        mock_update = MagicMock()
        svc.service.spreadsheets().values().update.return_value = mock_update

        # State without image_url
        state = AgentState(
            customer_id="CUST-101",
            customer_name="Anita Boutique",
            order_type="Machine Embroidery",
            template_name="Zari Work",
            quantity=2,
            labor_hours=2.0,
            image_url=None
        )

        res = svc.update_order_from_form("CJS-TARGET", state)
        assert res is True

        update_call = svc.service.spreadsheets().values().update.call_args[1]
        assert update_call["range"] == "'Orders'!C3:Q3"
        updated_row = update_call["body"]["values"][0]
        # Column Q in C:Q slice is index 14 (C=0, D=1, ... Q=14)
        assert updated_row[14] == "https://drive.google.com/existing_image"

def test_get_order_returns_image_url():
    """Verify get_order reads Orders!A:Q and returns image_url."""
    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        svc = GoogleSheetsService()
        svc.spreadsheet_id = "dummy_sheet"
        svc.service = MagicMock()
        svc.get_all_customers_map = MagicMock(return_value={"CUST-101": "Anita Boutique"})

        mock_get = MagicMock()
        mock_get.execute.return_value = {
            "values": [
                ["Header1"],
                [
                    "2026-09-13 10:00", "CJS-IMG01", "CUST-101", "Anita Boutique", "+919999999999",
                    "Machine Embroidery", "Zari Work", "1", "20000", "1.5",
                    "Ricoma", "2026-09-20", "Rs 500", "Estimated", "Reasoning log",
                    "", "https://drive.google.com/file/d/img_order_1/view"
                ]
            ]
        }
        svc.service.spreadsheets().values().get.return_value = mock_get

        order = svc.get_order("CJS-IMG01")
        assert order is not None
        assert order["order_id"] == "CJS-IMG01"
        assert order["image_url"] == "https://drive.google.com/file/d/img_order_1/view"
