from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

class EstimationAgent:
    def __init__(self):
        self.name = "Estimation Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 3 Logic:
        - Re-confirm stitch count natively.
        - Dynamically fetch 'Cost per 1000 Stitches', 'Hourly Labor Rate', and 'GST Rate Percent' from Config tab.
        - Calculate:
            stitch_cost = (stitch_count / 1000) * cost_per_1000_stitches
            labor_cost = labor_hours * hourly_labor_rate
            base_cost = stitch_cost + labor_cost
            gst_amount = base_cost * (gst_rate_percent / 100)
            total_cost = base_cost + gst_amount
        """
        if not state.stitch_count: return state
            
        print(f"[{self.name}] Connecting to Database to retrieve rates from Config tab...")
        
        db = GoogleSheetsService()
        config = db.get_config_variables()
        base_rate = float(config.get("Cost per 1000 Stitches", 10.0))
        hourly_rate = float(config.get("Hourly Labor Rate", 100.0))
        gst_rate = float(config.get("GST Rate Percent", 18.0))
        
        stitch_cost = round((state.stitch_count / 1000.0) * base_rate, 2)
        labor_hours = float(state.labor_hours or 0.0)
        labor_cost = round(labor_hours * hourly_rate, 2)
        
        base_cost = round(stitch_cost + labor_cost, 2)
        gst_amount = round(base_cost * (gst_rate / 100.0), 2)
        total_cost = round(base_cost + gst_amount, 2)
        
        state.base_cost_rs = base_cost
        state.gst_amount_rs = gst_amount
        state.total_cost_rs = total_cost
        
        estimator_log = (
            f"\n[Estimator Agent]: Calculated cost using Config parameters:\n"
            f"• Stitching: {state.stitch_count} stitches / 1000 x Rs {base_rate} = Rs {stitch_cost}\n"
            f"• Labor: {labor_hours} hrs x Rs {hourly_rate}/hr = Rs {labor_cost}\n"
            f"• Subtotal: Rs {base_cost}\n"
            f"• GST ({gst_rate}%): Rs {gst_amount}\n"
            f"• Total Order Cost: Rs {total_cost}. Payment status set to 'Estimated'.\n"
        )
             
        state.aggregated_reasoning += estimator_log
        state.invoice_status = "Estimated"
        
        print(f"[{self.name}] Final Calculated Cost: Rs {state.total_cost_rs} (Stitches: Rs {stitch_cost}, Labor: Rs {labor_cost}, GST: Rs {gst_amount})")
        
        return state
