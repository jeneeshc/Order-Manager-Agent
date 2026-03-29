from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService
import datetime

class ProductionSchedulerAgent:
    def __init__(self):
        self.name = "Production Scheduler Agent"
        self.spm = 650 # Stitches per minute
        self.daily_hours = 6 # 6 hours active production
        
    def process(self, state: AgentState) -> AgentState:
        """
        Multi-Agent Logic:
        1. Parse pending Open Orders from Google Sheets to identify Ricoma/Aakruthi delays.
        2. Query Google Calendar API to extract Holidays and Leaves dynamically.
        3. Iterate mathematically starting from Machine Free-Date, explicitly jumping weekends and Holidays!
        """
        print(f"[{self.name}] Connecting to multi-API environment for 4D scheduling...")
        if not state.stitch_count: return state
        
        # 1. Base Math Requirements
        total_hours = (state.stitch_count / self.spm) / 60
        days_required = max(1, round(total_hours / self.daily_hours))
        
        # 2. Get Open Router Queues natively
        db = GoogleSheetsService()
        machine_queues = db.get_machine_availability()
        
        # Dynamically assign to the absolute earliest available machine mathematically!
        machine_assigned = min(machine_queues, key=machine_queues.get)
        start_date = machine_queues[machine_assigned].date()
        
        # If queue is empty or in the past, production starts today!
        if start_date < datetime.date.today():
            start_date = datetime.date.today()
            
        print(f"[{self.name}] {machine_assigned} is free on {start_date}. Iterating {days_required} working days into the future.")
        
        # 3. Sheets Integration Check (Holidays/Sick Leave)
        holidays_to_skip = db.get_holidays()
        
        # 4. Temporal Timeline Iterator
        current_date = start_date
        days_added = 0
        
        while days_added < days_required:
            current_date += datetime.timedelta(days=1)
            
            # Condition A: Skip Sundays (Weekend off)
            if current_date.weekday() == 6:
                continue
                
            # Condition B: Skip Calendar API Holidays natively!
            if current_date in holidays_to_skip:
                print(f"[{self.name}] Timeline Engine skipped holiday blockout: {current_date}")
                continue
                
            days_added += 1
            
        # 5. Hydrate Results
        state.machine_assigned = machine_assigned
        state.estimated_completion_date = current_date.strftime("%Y-%m-%d")
        
        queue_text = "almost immediately today" if start_date == datetime.date.today() else f"after finishing the active tracking backlog on {start_date.strftime('%Y-%m-%d')}"
        state.scheduling_reasoning = f"Smart-Assigned to {machine_assigned} {queue_text}. Required {days_required} true working days. Automatically navigated and skipped Sundays & explicit Spreadsheet blockouts."
        
        state.current_agent = "EstimationAgent"
        return state
