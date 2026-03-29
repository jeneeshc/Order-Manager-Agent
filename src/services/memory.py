"""
Memory Persistence Service
In-memory fast cache to track the progressive state of a WhatsApp user's conversation 
so the LangGraph chain natively remembers prior field extractions.
"""
from typing import Dict, Optional

class MemoryService:
    def __init__(self):
        # In-memory dictionary mapping a sender phone number to their active LangGraph AgentState dict
        self.active_sessions: Dict[str, dict] = {}

    def get_state(self, sender_phone: str) -> Optional[dict]:
        """Fetch the previous conversation state for this user."""
        return self.active_sessions.get(sender_phone)

    def save_state(self, sender_phone: str, state_dict: dict):
        """Persist the running context of the conversation."""
        self.active_sessions[sender_phone] = state_dict

    def clear_state(self, sender_phone: str):
        """Erase memory after a successful sequence completion to reset the pipeline."""
        if sender_phone in self.active_sessions:
            del self.active_sessions[sender_phone]
