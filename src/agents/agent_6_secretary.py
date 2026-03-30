import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

class SecretaryAgent:
    def __init__(self):
        self.name = "Secretary Agent"
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0.1
        )

    def generate_daily_summary(self, data: dict) -> str:
        """
        Synthesizes a friendly daily report for Siny based on spreadsheet data.
        Addressing Siny: Always use the salutation 'Boss'.
        """
        prompt = f"""
        You are Siny's Business Secretary at CJS Designs.
        Your job is to provide a morning briefing with *updates for TODAY* ({data.get('today')}).
        When addressing your recipient, always call her 'Boss'.
        This message is sent every morning so she knows what to focus on TODAY — never say "tomorrow".
        
        DATA FOR TODAY ({data.get('today')}):
        - Orders Due Today: {data.get('orders_due_today')}
        - Pending Invoices (>7 days old): {data.get('pending_invoices_old')}
        - Holiday Status: {data.get('holiday_status') or 'Work Day'}
        - Upcoming Holidays: {data.get('upcoming_holidays')}
        - Specific Reminders: {data.get('reminders')}
        
        TASK:
        Write a friendly, professional, and concise WhatsApp message to Siny.
        - Start with a warm greeting addressing her as 'Boss'.
        - Summarise what needs to be completed TODAY (not tomorrow).
        - Gently remind her of old pending invoices if any.
        - Mention any holidays (today or upcoming).
        - Include the specific reminders from the Reminders sheet.
        - End with an encouraging note.
        
        Use emojis and *bold* formatting to make it readable on WhatsApp.
        IMPORTANT: This is a briefing for TODAY. Do NOT say "tomorrow" anywhere.
        """
        
        response = self.llm.invoke(prompt)
        
        # Robustly extract text from Gemini's response blocks (handles lists/dicts)
        if isinstance(response.content, list):
            return " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in response.content
            ).strip()
            
        return str(response.content).strip()

    def process(self, state: AgentState) -> AgentState:
        """
        On-demand process: Siny asks "What's my schedule?" or similar.
        Sets state.final_reply so the Supervisor passes it through verbatim
        with no re-synthesis and no format loss.
        """
        print(f"[{self.name}] Generating dynamic work summary on-demand...")
        
        db = GoogleSheetsService()
        data = db.get_secretary_data()
        
        summary = self.generate_daily_summary(data)
        
        # Own the reply format — Supervisor will send this verbatim at END.
        state.final_reply = summary
        state.aggregated_reasoning += f"\n[Secretary Agent]: Generated and stored daily briefing in final_reply.\n"
        
        return state
