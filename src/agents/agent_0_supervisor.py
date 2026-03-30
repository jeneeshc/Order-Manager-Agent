import os
from pydantic import BaseModel, Field
from typing import Literal
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agents.state import AgentState

class SupervisorOutput(BaseModel):
    """Router decision model for the Supervisor Agent."""
    next_step: Literal["collector", "scheduler", "estimator", "social", "invoice", "secretary", "END"] = Field(..., description="The next agent to call or END if finished.")
    reasoning: str = Field(..., description="Short explanation of why this agent was chosen.")
    internal_thought: str = Field(..., description="What the supervisor is thinking about the overall progress.")

class SupervisorAgent:
    def __init__(self):
        self.name = "Supervisor Agent"
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0
        )
        self.router = self.llm.with_structured_output(SupervisorOutput)

    def process(self, state: AgentState) -> AgentState:
        """
        Orchestration Logic:
        1. Analyzes raw_message and current state.
        2. Decides which specialized agent (worker) needs to run next.
        3. If no further actions are needed, sets next_step="END".
        """
        prompt = f"""
        You are the Head Supervisor for Boss's Embroidery Business (CJS Designs).
        Your job is to coordinate different specialist agents to fulfill a customer's request.
        
        MESSAGE FROM BOSS: "{state.raw_message}"
        
        CURRENT STATE:
        - Customer: {state.customer_name or 'Unknown'}
        - Fabric: {state.fabric_type or 'Unknown'}
        - Embroidery: {state.embroidery_type or 'Unknown'}
        - Stitches: {state.stitch_count or 'Unknown'}
        - Order ID: {state.order_id or 'New Order'}
        - Missing Info? {state.is_missing_info}
        - Estimates Done? {state.total_cost_rs is not None}
        - Secretarial/Task Query? {state.is_secretary_query}
        
        WORKERS AVAILABLE:
        - 'collector': Specialized in extracting names, fabrics, stitches, and detecting intents. Use this if order info is missing or first contact.
        - 'secretary': Specialized in daily task summaries, business briefings, and reminders.
        - 'scheduler': Calculates production dates using machine queues and holidays.
        - 'estimator': Calculates costs and machine assignments.
        - 'social': Prepares media assets and design mockups.
        - 'invoice': Handles payment status, pending dues, and finalizes orders.
        
        DECISION RULES:
        1. CRITICAL: If 'Missing Info? True' (is_missing_info), you MUST route to 'collector' to gather the missing details. If you have already tried 'collector' and 'is_missing_info' remains True, route to 'END' to ask Boss for clarification.
        2. If 'Missing Info? False' or this is a fresh user message, ALWAYS prioritize routing to 'collector' first if an order is involved.
        3. If Boss asks for a daily summary, work schedule, or "what to do today", route to 'secretary'.
        4. Proceed to 'scheduler' and 'estimator' only after 'collector' confirms ALL required info (is_missing_info=False).
        5. If all business logic (scheduling, cost, invoicing) is complete or it's a simple query already answered, route to 'END'.
        """
        
        decision = self.router.invoke(prompt)
        print(f"[{self.name}] Router Decision: {decision.next_step} ({decision.reasoning})")
        
        # If the task is finished, send the final response to Boss.
        if decision.next_step == "END":
            print(f"[{self.name}] Task complete. Preparing final response...")

            if state.final_reply:
                # An agent has already written its formatted reply — pass it through verbatim.
                # No extra LLM call. No format loss. No duplicates.
                state.raw_message = state.final_reply
                print(f"[{self.name}] Using agent's final_reply verbatim (no re-synthesis).")
            else:
                # Multi-step order flow: no single agent owns the reply.
                # Supervisor synthesizes ONE coherent message from all agents' reasoning.
                print(f"[{self.name}] Synthesizing final reply from aggregated reasoning...")
                final_prompt = f"""
                You are Boss's Business Supervisor. The task is complete.
                Based on the following aggregated work from your specialists, write a single final WhatsApp message to Boss.
                
                WORK REASONING:
                {state.aggregated_reasoning}
                
                STATE DETAILS:
                - Order ID: {state.order_id or 'New Order'}
                - Est. Completion: {state.estimated_completion_date or 'N/A'}
                - Total Cost: Rs {state.total_cost_rs or 'N/A'}
                - Material: {state.fabric_type or 'N/A'}
                - Stitches: {state.stitch_count or 'N/A'}
                - Invoicing Status: {state.invoice_status or 'N/A'}
                
                If it was an order, confirm it's saved and give Boss the key details (ID, date, cost).
                If it was a simple info extraction, give her the details.
                
                DO NOT mention "Supervisor" or "Agents" in the final message.
                Be friendly and professional. Use emojis and *bold* formatting for WhatsApp readability.
                """
                final_response = self.llm.invoke(final_prompt)
                state.raw_message = str(final_response.content).strip()

                # Robustly extract text if response is a list of blocks (Gemini format)
                if isinstance(final_response.content, list):
                    state.raw_message = " ".join(
                        block.get("text", "") if isinstance(block, dict) else str(block)
                        for block in final_response.content
                    ).strip()

        # In a supervisor-led loopback, we use next_step to control the graph edge
        state.next_step = decision.next_step
        state.aggregated_reasoning += f"\n[Supervisor]: Decided to route to {decision.next_step} because {decision.reasoning}.\n"
        
        return state
