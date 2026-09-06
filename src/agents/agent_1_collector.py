"""
Legacy alias for CJSSingleAgent.
Maintains backward compatibility for tests and existing imports.
"""
from langchain_google_genai import ChatGoogleGenerativeAI
from src.services.sheets import GoogleSheetsService
from src.agents.single_agent import (
    CJSSingleAgent as OrderCollectorAgent,
    sanitize_customer_name,
    MAIN_MENU_TEXT,
    ADJUST_MENU_TEXT,
    INVOICING_MENU_TEXT,
    VENDORS_MENU_TEXT,
    render_active_orders_prompt,
    resolve_selected_order
)

__all__ = [
    "OrderCollectorAgent",
    "sanitize_customer_name",
    "MAIN_MENU_TEXT",
    "ADJUST_MENU_TEXT",
    "INVOICING_MENU_TEXT",
    "VENDORS_MENU_TEXT",
    "render_active_orders_prompt",
    "resolve_selected_order"
]
