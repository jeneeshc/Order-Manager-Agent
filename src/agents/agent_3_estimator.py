from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

class EstimationAgent:
    def __init__(self):
        self.name = "Estimation Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 3 Logic:
        - Re-confirm stitch count natively.
        - Cross-Pollinate Embroidery & Material matching exactly against Siny's Costing Tuple DB.
        - Calculate cost = (Stitch Count / Unit Count) * Cost in Rupees.
        """
        if not state.stitch_count: return state
            
        print(f"[{self.name}] Connecting to Database for Dynamic Costing Combinatorics...")
        
        db = GoogleSheetsService()
        pricing_rules = db.get_costing_rules()
        
        target_emb = str(state.embroidery_type).strip().lower() if state.embroidery_type else ""
        target_mat = str(state.fabric_type).strip().lower() if state.fabric_type else ""
        
        # 1. Exact Combinatorial Match inside the 5-Column Database!
        matched_rule = pricing_rules.get((target_emb, target_mat))
        
        if matched_rule:
             print(f"[{self.name}] Natively Matched precise (Embroidery, Material) Tuple from cloud: {matched_rule}")
             u_count = matched_rule["unit_count"]
             u_cost = matched_rule["cost"]
             state.total_cost_rs = round((state.stitch_count / u_count) * u_cost, 2)
             estimator_log = (
                 f"\n[Estimator Agent]: Pricing Lookup -> Matched exact combination "
                 f"('{state.embroidery_type}', '{state.fabric_type}') in Costing sheet. "
                 f"Rule: {state.stitch_count} stitches / {u_count} units x Rs {u_cost} = Rs {state.total_cost_rs}. "
                 f"Payment status set to 'Estimated'.\n"
             )
        else:
             print(f"[{self.name}] Combinatorial pair ({target_emb}, {target_mat}) NOT natively mapped. Engaging Base fallback formula!")
             state.total_cost_rs = round((state.stitch_count / 1000.0) * 8.0, 2)
             estimator_log = (
                 f"\n[Estimator Agent]: Pricing Lookup -> No exact match found for "
                 f"('{state.embroidery_type}', '{state.fabric_type}') in Costing sheet. "
                 f"Applied default fallback rate: {state.stitch_count} stitches / 1000 x Rs 8.0 = Rs {state.total_cost_rs}. "
                 f"Payment status set to 'Estimated'.\n"
             )
             
        state.aggregated_reasoning += estimator_log
        state.invoice_status = "Estimated"
        
        print(f"[{self.name}] Final Calculated Cost: Rs {state.total_cost_rs}")
        state.current_agent = "SocialMediaAgent"
        
        return state
