"""
Legacy alias for CJSSingleAgent.
Maintains backward compatibility for tests and existing imports.
"""
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from src.services.sheets import GoogleSheetsService
from src.agents.single_agent import CJSSingleAgent as SupervisorAgent

class SupervisorOutput(BaseModel):
    next_step: str = "END"
    reasoning: str = ""
    internal_thought: str = ""

__all__ = ["SupervisorAgent", "ChatGoogleGenerativeAI", "SupervisorOutput", "GoogleSheetsService"]
