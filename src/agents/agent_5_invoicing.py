from src.agents.state import AgentState

class InvoicingAgent:
    def __init__(self):
        self.name = "Invoicing & Arrears Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 5 Logic:
        - Triggered on delivery/completion.
        - Calculates total pending dues for the current customer mapping.
        - Updates the final status to 'invoiced' in the Google Sheet.
        - Sets state.final_reply with a formatted WhatsApp payment reminder.
        """
        if state.invoice_status == "pending":
            print(f"[{self.name}] Processing invoice for Order {state.order_id}.")
            print(f"[{self.name}] Amount due: Rs {state.total_cost_rs}")
            
            # Simulated updating to Invoice Ledger
            state.invoice_status = "invoiced"
            
            reminder_text = (
                f"✅ *Order Ready for Pickup!*\n\n"
                f"Hi! Your custom embroidery order *{state.order_id}* is complete. 🎉\n"
                f"💰 *Amount Due:* Rs {state.total_cost_rs}\n\n"
                f"Please let us know when you'd like to pick it up!"
            )
            print(f"[{self.name}] Reminder drafted: {reminder_text}")
            
            # Own the reply format — Supervisor sends this verbatim at END.
            state.final_reply = reminder_text
            state.aggregated_reasoning += f"\n[Invoicing Agent]: Order {state.order_id} invoiced. Amount: Rs {state.total_cost_rs}. Reminder stored in final_reply.\n"
            
        return state
