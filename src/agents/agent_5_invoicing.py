from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

class InvoicingAgent:
    def __init__(self):
        self.name = "Invoicing & Arrears Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 5 Logic:
        - Handles pending invoicing query report.
        - Handles invoicing completed updates for specific or all customers.
        - Processes regular invoicing status transitions.
        """
        # 1. Report orders pending for invoicing
        if state.is_pending_invoicing_query:
            print(f"[{self.name}] Generating orders pending for invoicing report.")
            db = GoogleSheetsService()
            pending_orders = db.get_orders_pending_invoicing()
            
            if not pending_orders:
                state.final_reply = "No orders pending for invoicing, Boss! 🎉"
            else:
                report_lines = ["Here are the orders pending for invoicing, Boss! 📋\n"]
                grand_total = 0.0
                
                # Sort customers for deterministic display
                for cname in sorted(pending_orders.keys()):
                    report_lines.append(f"👤 *{cname}*")
                    customer_total = 0.0
                    for o in pending_orders[cname]:
                        # Parse cost (e.g. "Rs 560.0" -> 560.0)
                        cost_str = o["cost"]
                        try:
                            val = float(cost_str.replace("Rs", "").strip())
                        except ValueError:
                            val = 0.0
                        customer_total += val
                        grand_total += val
                        
                        desc = f"{o['fabric_type']} - {o['embroidery_type']}"
                        report_lines.append(f"  • *{o['order_id']}* ({desc}): Rs {val:.2f}")
                    report_lines.append(f"  *Total for {cname}:* Rs {customer_total:.2f}\n")
                
                report_lines.append(f"💵 *Grand Total:* Rs {grand_total:.2f}")
                state.final_reply = "\n".join(report_lines)
            
            state.aggregated_reasoning += f"\n[Invoicing Agent]: Handled orders pending for invoicing query. Drafted report.\n"
            return state

        # 2. Bulk mark invoicing done
        if state.is_invoicing_done_update:
            cust = state.invoicing_done_customer or "all"
            print(f"[{self.name}] Marking invoicing completed for customer: {cust}")
            db = GoogleSheetsService()
            
            updated_count = db.mark_invoicing_completed(cust)
            
            if updated_count == 0:
                if cust.lower() == "all":
                    state.final_reply = "There are no pending orders to mark as completed, Boss! 👍"
                else:
                    state.final_reply = f"No pending orders found for customer *{cust}*, Boss! 👍"
            else:
                if cust.lower() == "all":
                    state.final_reply = f"✅ *Invoicing Complete!*\n\nAll {updated_count} pending orders have been marked as *Completed* and are cleared from invoicing, Boss! 📋"
                else:
                    state.final_reply = f"✅ *Invoicing Complete for {cust}!*\n\n{updated_count} pending orders for *{cust}* have been marked as *Completed* and are cleared from invoicing, Boss! 📋"
            
            state.aggregated_reasoning += f"\n[Invoicing Agent]: Marked {updated_count} orders as Completed for customer '{cust}'.\n"
            return state

        # 3. Regular single order invoicing processing
        if state.invoice_status == "pending" and state.order_id:
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
