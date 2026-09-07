import pytest
from unittest.mock import patch, MagicMock
from src.agents.state import AgentState
from src.agents.single_agent import CJSSingleAgent
from src.services.sheets import GoogleSheetsService

def test_sync_menu_option_9():
    """Verify that replying '9' triggers cache invalidation, redeploys flow, and replies with confirmation."""
    mock_db = MagicMock(spec=GoogleSheetsService)
    mock_db.get_all_customers_list.return_value = ["Anna Maria", "Joy Alukkas", "Carpet", "Steffy"]
    mock_db.get_description_templates.return_value = [
        {"template_name": "Baptism", "machine": "Aakruthi"},
        {"template_name": "Kurti Neck", "machine": "Ricoma"}
    ]

    with patch('src.services.sheets.GoogleSheetsService.clear_all_caches') as mock_clear_caches, \
         patch('scripts.deploy_flow.redeploy_order_flow', return_value="1761036464934039") as mock_redeploy:
        
        agent = CJSSingleAgent(sheets_service=mock_db)
        state = AgentState(raw_message="9")
        res = agent.process(state)

        mock_clear_caches.assert_called_once()
        mock_redeploy.assert_called_once()
        assert res.next_step == "END"
        assert "Backend & WhatsApp Synced Successfully!" in res.final_reply
        assert "4 clients" in res.final_reply
        assert "Anna Maria, Joy Alukkas, Carpet, +1 more" in res.final_reply
        assert "2 design templates" in res.final_reply
        assert "1761036464934039" in res.final_reply

def test_sync_menu_text_synonyms():
    """Verify that synonyms like 'sync backend' or 'refresh form' also trigger option 9."""
    mock_db = MagicMock(spec=GoogleSheetsService)
    mock_db.get_all_customers_list.return_value = ["Ammu"]
    mock_db.get_description_templates.return_value = []

    for synonym in ["sync", "sync backend", "sync with backend", "refresh form", "sync form"]:
        with patch('src.services.sheets.GoogleSheetsService.clear_all_caches') as mock_clear_caches, \
             patch('scripts.deploy_flow.redeploy_order_flow', return_value="123456789") as mock_redeploy:
            
            agent = CJSSingleAgent(sheets_service=mock_db)
            state = AgentState(raw_message=synonym)
            res = agent.process(state)

            mock_clear_caches.assert_called_once()
            mock_redeploy.assert_called_once()
            assert "Backend & WhatsApp Synced Successfully!" in res.final_reply

def test_sync_menu_error_handling():
    """Verify that when deploy_flow fails, it informs Boss without crashing."""
    mock_db = MagicMock(spec=GoogleSheetsService)

    with patch('src.services.sheets.GoogleSheetsService.clear_all_caches'), \
         patch('scripts.deploy_flow.redeploy_order_flow', side_effect=RuntimeError("Meta Graph API timeout")):
        
        agent = CJSSingleAgent(sheets_service=mock_db)
        state = AgentState(raw_message="9")
        res = agent.process(state)

        assert res.next_step == "END"
        assert "⚠️ *Sync Encountered an Error:*" in res.final_reply
        assert "Meta Graph API timeout" in res.final_reply
