from src.agents.state import AgentState

class EstimationAgent:
    def __init__(self):
        self.name = "Estimation Agent"
        self.rate_per_1k = 8.0  # Rs 8 per 1000 stitches

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 3 Logic:
        - Re-confirm stitch count.
        - Calculate cost = (Stitch Count / 1000) * 8.0.
        - Add padding for complex fabrics (e.g. Leather/Silk) or special threads.
        - Finalize Quote for Siny.
        """
        if not state.stitch_count:
            return state
            
        print(f"[{self.name}] Calculating estimate for {state.stitch_count} stitches.")
        
        base_cost = (state.stitch_count / 1000.0) * self.rate_per_1k
        
        # Example variable pricing based on Fabric Type 
        multiplier = 1.0
        if state.fabric_type:
            if state.fabric_type.lower() in ['silk', 'leather', 'velvet']:
                multiplier = 1.2  # 20% surcharge for difficult fabrics
                
        state.total_cost_rs = round(base_cost * multiplier, 2)
        
        print(f"[{self.name}] Final Cost Estimate: Rs {state.total_cost_rs}")
        state.current_agent = "SocialMediaAgent" # or End, Social media triggers upon completion
        
        return state
