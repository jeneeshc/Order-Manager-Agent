"""
Memory Persistence Service
File-backed cache to track the progressive state of a WhatsApp user's conversation 
so the LangGraph chain natively remembers prior field extractions even across reloads.
"""
import os
import json
from typing import Dict, Optional

class MemoryService:
    def __init__(self):
        # Local JSON path for persistence
        self.file_path = os.path.join(os.path.dirname(__file__), "active_sessions.json")
        self.active_sessions: Dict[str, dict] = self._load_from_disk()

    def _load_from_disk(self) -> dict:
        """Hydrate memory from a local JSON file if exists."""
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[MemoryService] Load error: {e}. Starting fresh.")
        return {}

    def _save_to_disk(self):
        """Sync the current memory dictionary to slow-storage (disk)."""
        try:
            with open(self.file_path, "w") as f:
                json.dump(self.active_sessions, f, indent=4)
        except Exception as e:
            print(f"[MemoryService] Save error: {e}")

    def get_state(self, sender_phone: str) -> Optional[dict]:
        """Fetch the previous conversation state for this user."""
        return self.active_sessions.get(sender_phone)

    def save_state(self, sender_phone: str, state):
        """Persist the running context of the conversation and sync to disk."""
        # Ensure we save as a dictionary if it's a Pydantic model
        state_dict = state.model_dump() if hasattr(state, "model_dump") else state
        self.active_sessions[sender_phone] = state_dict
        self._save_to_disk()

    def clear_state(self, sender_phone: str):
        """Erase memory after a successful sequence completion to reset the pipeline."""
        if sender_phone in self.active_sessions:
            del self.active_sessions[sender_phone]
            self._save_to_disk()
