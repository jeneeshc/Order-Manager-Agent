from src.agents.state import AgentState
from datetime import datetime, timedelta

class ProductionSchedulerAgent:
    def __init__(self):
        self.name = "Production Scheduler Agent"
        self.spm = 650 # Stitches per minute
        self.daily_hours = 6 # 6 hours working
        self.machines = ["Ricoma", "Aakruthi"]

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 2 Logic:
        - Receives the valid stitch count from Agent 1.
        - Math: (Count / SPM) = total minutes required.
        - Divide by (6 hours) to find days required.
        - Apply Calendar: Skip Sundays / Leaves.
        """
        print(f"[{self.name}] Calculating schedule for {state.stitch_count} stitches.")
        
        if not state.stitch_count:
            return state
            
        total_minutes = state.stitch_count / self.spm
        total_hours = total_minutes / 60
        days_required = max(1, round(total_hours / self.daily_hours, 1))
        
        print(f"[{self.name}] Job takes ~{total_hours:.2f} hours. Allocating {days_required} working days.")
        
        # Assign machine (mock logic, alternating or checking queue)
        state.machine_assigned = self.machines[0]
        
        # Calculate Future Date (Mock logic: tomorrow + days required)
        now = datetime.now()
        completion = now + timedelta(days=int(days_required) + 1) # simple logic
        state.estimated_completion_date = completion.strftime("%Y-%m-%d")
        
        state.current_agent = "EstimationAgent"
        return state
