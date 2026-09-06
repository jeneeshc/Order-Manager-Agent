from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService
import datetime
import math

class ProductionSchedulerAgent:
    def __init__(self):
        self.name = "Production Scheduler Agent"
        self.spm = 650         # Stitches per minute
        self.daily_hours = 6.0  # 6 hours active production per working day
        
    def process(self, state: AgentState) -> AgentState:
        """
        Multi-Agent Logic:
        1. Check Order Type: If 'Embroidery design', no machine or stitch count required.
        2. If 'Machine Embroidery', route machine deterministically via Description_Templates Col D
           (Ricoma for large items like Saree/Kurti, Aakruthi for small items like Logo/Baptism).
        3. Calculate working days needed from machine running time: ceil((stitches * qty / 650 / 60) / 6h).
        4. Advance timeline from machine free date, skipping Sundays and Google Sheet Holidays.
        5. Verify availability against requested delivery date.
        """
        print(f"[{self.name}] Initiating capacity and machine availability analysis...")
        db = GoogleSheetsService()
        
        # 1. Embroidery Design (Software design only, consumes zero machine running time)
        order_type_clean = (state.order_type or "").strip().lower()
        if order_type_clean == "embroidery design":
            state.machine_assigned = "None"
            today = datetime.date.today()
            
            # Default completion to requested delivery date or tomorrow
            if state.requested_delivery_date:
                state.estimated_completion_date = state.requested_delivery_date
            else:
                next_day = today + datetime.timedelta(days=1)
                state.estimated_completion_date = next_day.strftime("%Y-%m-%d")
                
            scheduler_log = (
                f"\n[Scheduler Agent]: Order Type is 'Embroidery design' (Software Digitizing). "
                f"No machine time required. Siny's labor time: {state.labor_hours or 0} hrs. "
                f"Completion target set to {state.estimated_completion_date}.\n"
            )
            state.aggregated_reasoning = (state.aggregated_reasoning or "") + scheduler_log
            print(f"[{self.name}] Completed Embroidery Design scheduling (No machine required).")
            return state

        # 2. Machine Embroidery Allocation
        template_info = None
        if state.template_name:
            template_info = db.get_template_by_name(state.template_name)

        if isinstance(template_info, dict) and template_info.get("machine") and str(template_info["machine"]).lower() != "none":
            machine_assigned = str(template_info["machine"])
            print(f"[{self.name}] Deterministically matched machine from template: '{machine_assigned}'")
        else:
            # Heuristic keyword fallback for machine routing
            text_to_check = f"{state.template_name or ''} {state.embroidery_type or ''}".lower()
            large_keywords = ["saree", "kurti", "kurty", "gown", "salwar", "lehenga", "suit", "bedsheet"]
            if any(kw in text_to_check for kw in large_keywords):
                machine_assigned = "Ricoma"
            else:
                machine_assigned = "Aakruthi"
            print(f"[{self.name}] Allocated machine by template classification: '{machine_assigned}'")

        # 3. Machine Running Time Calculation
        stitches = int(state.stitch_count or 0)
        quantity = int(state.quantity or 1)
        total_stitches = stitches * quantity
        
        if total_stitches > 0:
            total_machine_hours = (total_stitches / self.spm) / 60.0
            days_required = max(1, math.ceil(total_machine_hours / self.daily_hours))
        else:
            total_machine_hours = 0.0
            days_required = 1

        # 4. Read Queue Availability for Target Machine
        machine_queues = db.get_machine_availability()
        start_dt = machine_queues.get(machine_assigned, datetime.datetime.now())
        start_date = start_dt.date() if isinstance(start_dt, datetime.datetime) else start_dt
        today = datetime.date.today()
        
        if start_date < today:
            start_date = today

        print(f"[{self.name}] {machine_assigned} available on {start_date}. Iterating {days_required} working days...")

        # 5. Temporal Timeline Iterator (Skipping Sundays & Holidays)
        holidays_to_skip = db.get_holidays()
        current_date = start_date
        days_added = 0
        
        while days_added < days_required:
            current_date += datetime.timedelta(days=1)
            # Skip Sundays
            if current_date.weekday() == 6:
                continue
            # Skip Holidays
            if current_date in holidays_to_skip:
                print(f"[{self.name}] Skipped studio holiday: {current_date}")
                continue
            days_added += 1

        state.machine_assigned = machine_assigned
        state.estimated_completion_date = current_date.strftime("%Y-%m-%d")

        # 6. Check Delivery Date Availability
        conflict_warning = ""
        if state.requested_delivery_date:
            try:
                req_dt = datetime.datetime.strptime(state.requested_delivery_date.strip(), "%Y-%m-%d").date()
                if current_date > req_dt:
                    conflict_warning = (
                        f" ⚠️ *Schedule Alert:* Customer requested {state.requested_delivery_date}, "
                        f"but earliest completion on {machine_assigned} is {state.estimated_completion_date}."
                    )
            except ValueError:
                pass

        skipped_holidays = [h.strftime('%Y-%m-%d') for h in holidays_to_skip if start_date <= h <= current_date]
        queue_text = "immediately (no backlog)" if start_date == today else f"after backlog clears on {start_date.strftime('%Y-%m-%d')}"
        
        scheduler_log = (
            f"\n[Scheduler Agent]: Machine Queue Analysis -> Assigned '{machine_assigned}' ({queue_text}). "
            f"Calculated {days_required} working day(s) needed for {total_stitches} total stitches "
            f"({stitches} st x {quantity} qty at {self.spm} SPM / {self.daily_hours}h daily). "
            f"Estimated completion date: {current_date.strftime('%Y-%m-%d')}."
            f"{conflict_warning} "
            f"Skipped holidays: {', '.join(skipped_holidays) if skipped_holidays else 'None'}.\n"
        )
        state.aggregated_reasoning = (state.aggregated_reasoning or "") + scheduler_log

        print(f"[{self.name}] Scheduled on {machine_assigned} for completion on {state.estimated_completion_date}")
        return state
