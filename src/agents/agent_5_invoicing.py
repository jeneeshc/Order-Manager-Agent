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
        - Proposes a reminder message if payment is pending.
        """
        if state.invoice_status == "pending":
            print(f"[{self.name}] Processing invoice for Order {state.order_id}.")
            print(f"[{self.name}] Amount due: Rs {state.total_cost_rs}")
            
            # Simulated updating to Invoice Ledger
            state.invoice_status = "invoiced"
            
            reminder_text = (f"Hi! Your custom embroidery order is ready. "
                             f"The total due is Rs {state.total_cost_rs}. Let us know when you'd like to pick it up!")
            print(f"[{self.name}] Reminder drafted for Siny to forward: {reminder_text}")
            
        return state
