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
        """
        prompt = f"""
        You are Siny's Business Secretary at CJS Designs. 
        Your job is to provide a morning briefing based on the following data:
        
        DATA FOR TODAY ({data.get('today')}):
        - Orders Due Today: {data.get('orders_due_today')}
        - Pending Invoices (>7 days old): {data.get('pending_invoices_old')}
        - Holiday Status: {data.get('holiday_status') or 'Work Day'}
        - Upcoming Holidays: {data.get('upcoming_holidays')}
        - Specific Reminders: {data.get('reminders')}
        
        TASK:
        Write a friendly, professional, and concise WhatsApp message to Siny.
        - Start with a warm greeting.
        - List what needs to be completed today.
        - Gently remind her of old pending invoices if any.
        - Mention any holidays (today or upcoming).
        - Include the specific reminders from the Reminders sheet.
        - End with an encouraging note.
        
        Use emojis and formatting (bolding) to make it readable.
        """
        
        response = self.llm.invoke(prompt)
        return str(response.content).strip()

    def process(self, state: AgentState) -> AgentState:
        """
        On-demand process: Siny asks "What's my schedule?" or similar.
        """
        print(f"[{self.name}] Generating dynamic work summary on-demand...")
        
        db = GoogleSheetsService()
        data = db.get_secretary_data()
        
        summary = self.generate_daily_summary(data)
        
        # We append the summary to the reasoning or just pass it back?
        # For on-demand, the API will use this result to reply.
        state.aggregated_reasoning += f"\n[Secretary Agent]: Generated daily summary on-demand.\n"
        state.raw_message = summary # Overwriting raw_message to be used as reply in main.py
        
        return state
