"""
CJS Designs — New Agent Template
=================================
INSTRUCTIONS:
  1. Copy this file to src/agents/agent_N_yourname.py
  2. Rename the class and self.name
  3. Fill in your process() logic
  4. Follow the OUTPUT CONTRACT below
  5. Register the agent in main_graph.py and agent_0_supervisor.py
     (see docs/AGENT_DEVELOPMENT.md for the exact steps)

OUTPUT CONTRACT (mandatory, applies to ALL agents):
  - Set state.final_reply  if this agent owns the user-facing WhatsApp reply.
  - Append to state.aggregated_reasoning  always (for pipeline audit / Supervisor synthesis).
  - Never touch state.raw_message — only the Supervisor sets that at END.
"""

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agents.state import AgentState


class TemplateAgent:
    def __init__(self):
        self.name = "Template Agent"   # ← rename this
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0.1
        )

    def process(self, state: AgentState) -> AgentState:
        """
        [Replace with a one-line description of what this agent does.]

        OUTPUT CONTRACT:
        - Sets state.final_reply  → agent owns the full user-facing response (self-contained queries).
        - Skips state.final_reply → agent is an intermediate pipeline step (feeds aggregated_reasoning).
        - Never sets state.raw_message directly.
        """
        print(f"[{self.name}] Starting...")

        # ------------------------------------------------------------------
        # YOUR AGENT LOGIC GOES HERE
        # ------------------------------------------------------------------

        # Example: generate a user-facing WhatsApp message.
        # Use emojis and *bold* for WhatsApp readability (see docs/AGENT_DEVELOPMENT.md).
        reply = (
            f"✅ *Result Heading*\n\n"
            f"Your formatted details here.\n"
            f"💡 *Next step:* ...\n"
        )

        # ------------------------------------------------------------------
        # OUTPUT CONTRACT
        # ------------------------------------------------------------------

        # OPTION A: Self-contained query — this agent owns the final reply.
        # The Supervisor will pass state.final_reply to WhatsApp verbatim (no re-synthesis).
        state.final_reply = reply

        # OPTION B: Intermediate pipeline step — comment out the line above.
        # The Supervisor will synthesize the final reply from aggregated_reasoning at END.
        # (Uncomment the next line and remove state.final_reply = reply above)
        # pass

        # Always write an audit log entry regardless of OPTION A or B.
        state.aggregated_reasoning += f"\n[{self.name}]: <short summary of what was computed/done>.\n"

        return state
