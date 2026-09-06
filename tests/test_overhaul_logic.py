import pytest
from unittest.mock import MagicMock, patch
from src.agents.state import AgentState
from src.agents.agent_2_scheduler import ProductionSchedulerAgent
from src.agents.agent_3_estimator import EstimationAgent

def test_estimator_machine_embroidery_4_factor():
    """Verify strict 4-factor formula for Machine Embroidery."""
    estimator = EstimationAgent()
    state = AgentState(
        order_type="Machine Embroidery",
        template_name="Saree Border",
        stitch_count=10000,
        quantity=2,
        labor_hours=2.0
    )

    mock_config = {
        "Cost per 1000 Stitches": 10.0,
        "Hourly Labor Rate": 100.0,
        "Profit Margin Percent": 20.0,
        "GST Rate Percent": 18.0
    }

    with patch("src.agents.agent_3_estimator.GoogleSheetsService") as mock_db_cls:
        mock_db = MagicMock()
        mock_db.get_config_variables.return_value = mock_config
        mock_db_cls.return_value = mock_db

        result_state = estimator.process(state)

        # Expected Math:
        # Total stitches = 10000 * 2 = 20000
        # Stitch cost = (20000 / 1000) * 10.0 = 200.0
        # Labor cost = 2.0 * 100.0 = 200.0
        # Base cost = 200.0 + 200.0 = 400.0
        # Profit margin (20%) = 400.0 * 0.20 = 80.0
        # Subtotal = 400.0 + 80.0 = 480.0
        # GST (18%) = 480.0 * 0.18 = 86.4
        # Total cost = 480.0 + 86.4 = 566.4
        assert result_state.base_cost_rs == 400.0
        assert result_state.profit_margin_rs == 80.0
        assert result_state.gst_amount_rs == 86.4
        assert result_state.total_cost_rs == 566.4
        assert result_state.invoice_status == "Estimated"
        assert "Strict 4-Factor Cost Breakdown" in result_state.aggregated_reasoning

def test_estimator_embroidery_design_zero_stitches():
    """Verify Embroidery design has 0 stitch cost and uses only labor hours in 4-factor formula."""
    estimator = EstimationAgent()
    state = AgentState(
        order_type="Embroidery design",
        template_name="Vector Digitizing",
        stitch_count=0,
        quantity=1,
        labor_hours=3.0
    )

    mock_config = {
        "Cost per 1000 Stitches": 10.0,
        "Hourly Labor Rate": 100.0,
        "Profit Margin Percent": 20.0,
        "GST Rate Percent": 18.0
    }

    with patch("src.agents.agent_3_estimator.GoogleSheetsService") as mock_db_cls:
        mock_db = MagicMock()
        mock_db.get_config_variables.return_value = mock_config
        mock_db_cls.return_value = mock_db

        result_state = estimator.process(state)

        # Expected Math:
        # Stitch cost = 0.0
        # Labor cost = 3.0 * 100.0 = 300.0
        # Base cost = 300.0
        # Profit margin (20%) = 60.0
        # Subtotal = 360.0
        # GST (18%) = 64.8
        # Total cost = 424.8
        assert result_state.base_cost_rs == 300.0
        assert result_state.profit_margin_rs == 60.0
        assert result_state.gst_amount_rs == 64.8
        assert result_state.total_cost_rs == 424.8

def test_scheduler_embroidery_design_no_machine():
    """Verify Embroidery design consumes zero machine capacity and sets machine_assigned to None."""
    scheduler = ProductionSchedulerAgent()
    state = AgentState(
        order_type="Embroidery design",
        template_name="Logo Digitizing",
        requested_delivery_date="2026-09-15"
    )

    with patch("src.agents.agent_2_scheduler.GoogleSheetsService") as mock_db_cls:
        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        result_state = scheduler.process(state)

        assert result_state.machine_assigned == "None"
        assert result_state.estimated_completion_date == "2026-09-15"
        assert "Embroidery design" in result_state.aggregated_reasoning

def test_scheduler_machine_allocation_ricoma():
    """Verify large template allocates to Ricoma."""
    scheduler = ProductionSchedulerAgent()
    state = AgentState(
        order_type="Machine Embroidery",
        template_name="Saree Border",
        stitch_count=39000,
        quantity=1
    )

    with patch("src.agents.agent_2_scheduler.GoogleSheetsService") as mock_db_cls:
        mock_db = MagicMock()
        mock_db.get_template_by_name.return_value = {
            "template_name": "Saree Border",
            "machine": "Ricoma",
            "default_labor_hours": 1.5
        }
        mock_db.get_machine_availability.return_value = {}
        mock_db.get_holidays.return_value = []
        mock_db_cls.return_value = mock_db

        result_state = scheduler.process(state)

        assert result_state.machine_assigned == "Ricoma"
        assert result_state.estimated_completion_date is not None

def test_scheduler_machine_allocation_aakruthi():
    """Verify small template allocates to Aakruthi."""
    scheduler = ProductionSchedulerAgent()
    state = AgentState(
        order_type="Machine Embroidery",
        template_name="Logo Pocket",
        stitch_count=5000,
        quantity=1
    )

    with patch("src.agents.agent_2_scheduler.GoogleSheetsService") as mock_db_cls:
        mock_db = MagicMock()
        mock_db.get_template_by_name.return_value = {
            "template_name": "Logo Pocket",
            "machine": "Aakruthi",
            "default_labor_hours": 0.5
        }
        mock_db.get_machine_availability.return_value = {}
        mock_db.get_holidays.return_value = []
        mock_db_cls.return_value = mock_db

        result_state = scheduler.process(state)

        assert result_state.machine_assigned == "Aakruthi"
        assert result_state.estimated_completion_date is not None
