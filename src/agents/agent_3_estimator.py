from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

class EstimationAgent:
    def __init__(self):
        self.name = "Estimation Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 3 Logic:
        - Re-confirm stitch count.
        - Dynamically scan 'Costing' tab in Siny's Google Sheet for Base Rate and Multipliers.
        - Calculate cost = (Stitch Count / 1000) * Live Rate * Multiplier.
        """
        if not state.stitch_count: return state
            
        print(f"[{self.name}] Connecting to Database for Dynamic Pricing Matrix...")
        
        db = GoogleSheetsService()
        pricing_rules = db.get_costing_rules()
        
        # Determine Base Rate with generic graceful Fallback 
        base_rate = pricing_rules.get("base rate", 8.0) # Rs per 1000 natively
        base_cost = (state.stitch_count / 1000.0) * base_rate
        
        # Dynamic Fabric Multiplier matching from Costing Tab!
        multiplier = 1.0
        if state.fabric_type:
            fab = state.fabric_type.lower()
            if fab in pricing_rules:
                multiplier = pricing_rules[fab]
                print(f"[{self.name}] Matched {fab} exactly in Pricing DB. Multiplier: {multiplier}")
            elif fab in ['silk', 'leather', 'velvet'] and not pricing_rules:
                multiplier = 1.2
                
        state.total_cost_rs = round(base_cost * multiplier, 2)
        state.invoice_status = "Estimated"
        
        print(f"[{self.name}] Final Cost Estimate: Rs {state.total_cost_rs} (Base: {base_rate}, Mult: {multiplier})")
        state.current_agent = "SocialMediaAgent"
        
        return state
