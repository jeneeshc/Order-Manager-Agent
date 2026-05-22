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
        state.hop_count += 1
        
        prompt = f"""
        You are the Head Supervisor for Siny's Embroidery Business (CJS Designs).
        Your job is to coordinate different specialist agents to fulfill a request.
        Addressing the user: Always use the salutation 'Boss' in your final response.
        
        MESSAGE: "{state.raw_message}"
        
        CURRENT STATE:
        - Customer: {state.customer_name or 'Unknown'}
        - Fabric: {state.fabric_type or 'Unknown'}
        - Embroidery: {state.embroidery_type or 'Unknown'}
        - Stitches: {state.stitch_count or 'Unknown'}
        - Order ID: {state.order_id or 'New Order'}
        - Est. Completion: {state.estimated_completion_date or 'Unknown'}
        - Missing Info? {state.is_missing_info}
        - Estimates Done? {state.total_cost_rs is not None}
        - Secretarial/Task Query? {state.is_secretary_query}
        - Final Reply Ready? {'Yes' if state.final_reply else 'No'}
        
        WORKERS AVAILABLE:
        - 'collector': Specialized in extracting names, fabrics, stitches, and detecting intents. Use this if order info is missing or first contact.
        - 'secretary': Specialized in daily task summaries, business briefings, and reminders.
        - 'scheduler': Calculates production dates using machine queues and holidays.
        - 'estimator': Calculates costs and machine assignments.
        - 'social': Prepares media assets and design mockups.
        - 'invoice': Handles payment status, pending dues, report of orders pending for invoicing, and bulk invoicing updates.
        
        DECISION RULES:
        1. CRITICAL: If 'Missing Info? True' (is_missing_info), you MUST route to 'END' immediately. This allows the system to send the missing information prompt to Siny. Do NOT route to collector again if information is already flagged as missing.
        2. If 'Missing Info? False' AND this is an order request AND ANY of Customer, Fabric, Embroidery, or Stitches is 'Unknown', you MUST route to 'collector' to extract the remaining information.
        3. If all required order info is present (Customer, Fabric, Embroidery, Stitches are NOT 'Unknown') and scheduling hasn't been done (Est. Completion is 'Unknown'), route to 'scheduler'.
        4. If scheduling is done but costs aren't calculated, route to 'estimator'.
        5. If Siny asks for a daily summary, work schedule, or "what to do today", route to 'secretary'.
        6. If Siny asks for details of orders pending for invoicing, or states that invoicing is done (for a customer or all customers), route to 'invoice'.
        7. If all business logic (scheduling, cost, invoicing) is complete or it's a simple query already answered, route to 'END'.
        8. CRITICAL: If 'Final Reply Ready? Yes', you MUST route to 'END' immediately to deliver the message to Siny.
        """
        
        from src.agents.agent_0_supervisor import SupervisorOutput
        
        if state.hop_count >= 6:
            print(f"[{self.name}] Safety cutoff reached! Forcing END.")
            state.final_reply = "⚠️ *System Safety Check Triggered*\n\nThe request took too many steps to process. I aborted it to save your resources. Please check the logs or try rephrasing your request."
            decision = SupervisorOutput(next_step="END", reasoning="Hop count limit exceeded.", internal_thought="Aborting infinite loop.")
        else:
            decision = self.router.invoke(prompt)
            if decision is None:
                print(f"[{self.name}] Router LLM returned None. Defaulting to 'END' to prevent crash.")
                decision = SupervisorOutput(next_step="END", reasoning="Safety filter blocked or parsing failed.", internal_thought="Error")
        
        next_step = decision.next_step
        reasoning = decision.reasoning

        # Force routing to invoice agent if invoicing queries/updates are detected
        if (state.is_pending_invoicing_query or state.is_invoicing_done_update) and not state.final_reply:
            next_step = "invoice"
            reasoning = "Message is an invoicing query or status update, routing to Invoicing Agent."
        
        # Programmatic Guardrails to enforce mandatory fields on order creation
        is_order_creation = not any([
            state.is_status_update,
            state.is_explanation_request,
            state.is_field_override,
            state.is_payment_query,
            state.is_secretary_query,
            state.is_pending_invoicing_query,
            state.is_invoicing_done_update
        ])

        if is_order_creation and next_step in {"scheduler", "estimator", "END"} and not state.is_missing_info:
            missing_fields = []
            if not state.customer_name or state.customer_name.strip().lower() in {"unknown", "none", ""}:
                missing_fields.append("customer name")
            if not state.fabric_type or state.fabric_type.strip().lower() in {"unknown", "none", ""}:
                missing_fields.append("fabric type")
            if not state.embroidery_type or state.embroidery_type.strip().lower() in {"unknown", "none", ""}:
                missing_fields.append("embroidery style")
            if not state.stitch_count or (isinstance(state.stitch_count, int) and state.stitch_count <= 0):
                missing_fields.append("stitch count")
                
            if missing_fields:
                print(f"[{self.name}] Guardrail Triggered! Missing mandatory fields: {missing_fields}. Overriding next_step to 'collector'.")
                next_step = "collector"
                reasoning = f"Guardrail overridden to collector due to missing required fields: {', '.join(missing_fields)}"

        # If a final reply has already been formulated by a worker agent, force termination
        if state.final_reply:
            next_step = "END"
            reasoning = "Final reply is ready, routing to END."

        print(f"[{self.name}] Supervisor Routing Decision: {next_step} (original: {decision.next_step}, reasoning: {reasoning})")
        
        # If the task is finished, send the final response to Siny.
        if next_step == "END":
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
                You are Siny's Business Supervisor. The task is complete.
                When addressing the user, always use the salutation 'Boss'.
                Based on the following aggregated work from your specialists, write a single final WhatsApp message.
                
                WORK REASONING:
                {state.aggregated_reasoning[-1000:] if len(state.aggregated_reasoning) > 1000 else state.aggregated_reasoning}
                
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
        state.next_step = next_step
        state.aggregated_reasoning += f"\n[Supervisor]: Decided to route to {next_step} because {reasoning}.\n"
        
        return state
