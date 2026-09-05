import pytest
from unittest.mock import MagicMock, patch
from src.services.sheets import GoogleSheetsService
from src.agents.state import AgentState
from src.agents.agent_3_estimator import EstimationAgent

def test_config_variables_parsing():
    """Test that GoogleSheetsService parses Config tab into key-value map with numerical coercion."""
    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        svc = GoogleSheetsService()
        svc.spreadsheet_id = "dummy_id"
        svc.service = MagicMock()
        
        mock_values = [
            ["Variable Name", "Value", "Last Updated"],
            ["Cost per 1000 Stitches", "10", "2026-09-02T12:00:09.318Z"],
            ["Hourly Labor Rate", "100", "2026-09-02T12:00:09.320Z"],
            ["GST Rate Percent", "18", "2026-09-02T12:00:09.320Z"],
            ["Studio Name", "CJS Designs", "2026-09-02T12:00:09.320Z"]
        ]
        
        mock_get = MagicMock()
        mock_get.execute.return_value = {"values": mock_values}
        svc.service.spreadsheets().values().get.return_value = mock_get
        
        config = svc.get_config_variables()
        assert config["Cost per 1000 Stitches"] == 10
        assert config["Hourly Labor Rate"] == 100
        assert config["GST Rate Percent"] == 18
        assert config["Studio Name"] == "CJS Designs"

def test_estimator_with_dynamic_config_rate():
    """Test that EstimationAgent calculates cost using stitches, labor hours, and GST from Config tab."""
    mock_config = {
        "Cost per 1000 Stitches": 10.0,
        "Hourly Labor Rate": 100.0,
        "GST Rate Percent": 18.0
    }
    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        with patch.object(GoogleSheetsService, 'get_config_variables', return_value=mock_config):
            agent = EstimationAgent()
            
            # Case 1: 50,000 stitches + 2 labor hours
            state = AgentState(
                customer_name="Test Customer",
                fabric_type="Custom Silk",
                embroidery_type="Zari",
                stitch_count=50000,
                labor_hours=2.0
            )
            res = agent.process(state)
            
            # Stitches: (50000 / 1000) * 10 = Rs 500.0
            # Labor: 2.0 * 100 = Rs 200.0
            # Subtotal: Rs 700.0
            # GST: 700.0 * 0.18 = Rs 126.0
            # Total: Rs 826.0
            assert res.base_cost_rs == 700.0
            assert res.gst_amount_rs == 126.0
            assert res.total_cost_rs == 826.0
            assert "Calculated cost using Config parameters" in res.aggregated_reasoning
            assert "GST (18.0%): Rs 126.0" in res.aggregated_reasoning

            # Case 2: Zero / omitted labor hours
            state2 = AgentState(
                customer_name="Test Customer",
                fabric_type="Cotton",
                embroidery_type="Floral",
                stitch_count=20000
            )
            res2 = agent.process(state2)
            # Stitches: (20000 / 1000) * 10 = Rs 200.0
            # Labor: 0.0 * 100 = Rs 0.0
            # Subtotal: Rs 200.0
            # GST: 200.0 * 0.18 = Rs 36.0
            # Total: Rs 236.0
            assert res2.base_cost_rs == 200.0
            assert res2.gst_amount_rs == 36.0
            assert res2.total_cost_rs == 236.0

def test_sales_ledger_parsing():
    """Test that GoogleSheetsService accurately reads and parses the 11-column Sales_Ledger."""
    with patch.object(GoogleSheetsService, '__init__', return_value=None):
        svc = GoogleSheetsService()
        svc.spreadsheet_id = "dummy_id"
        svc.service = MagicMock()
        
        mock_values = [
            ["Date", "Invoice ID", "Customer", "Service Type", "Total Stitches", "Labor Hrs", "Margin %", "Net Price", "GST", "Courier", "Gross Total"],
            ["2026-09-02", "CJS-2026-0001", "Saniya Boutique", "Machine Embroidery", "120000", "10", "25", "2450", "441", "150", "3041"]
        ]
        mock_get = MagicMock()
        mock_get.execute.return_value = {"values": mock_values}
        svc.service.spreadsheets().values().get.return_value = mock_get
        
        sales = svc.get_sales_ledger()
        assert len(sales) == 1
        s = sales[0]
        assert s["invoice_id"] == "CJS-2026-0001"
        assert s["customer"] == "Saniya Boutique"
        assert s["gross_total"] == 3041.0
        assert s["gst"] == 441.0
