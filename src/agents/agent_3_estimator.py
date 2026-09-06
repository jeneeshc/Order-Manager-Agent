from src.agents.state import AgentState
from src.services.sheets import GoogleSheetsService

def parse_numeric_rate(val, default: float) -> float:
    """Safely coerces numeric rates, stripping '%', 'Rs', '₹', commas, and whitespace."""
    if val is None:
        return default
    if isinstance(val, (int, float)):
        return float(val)
    try:
        clean = str(val).replace("%", "").replace("Rs", "").replace("₹", "").replace(",", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return default

class EstimationAgent:
    def __init__(self):
        self.name = "Estimation Agent"

    def process(self, state: AgentState) -> AgentState:
        """
        Agent 3 Strict 4-Factor Pricing Logic:
        1. Stitching Cost: (stitch_count * quantity / 1000) * base_rate (0 for Embroidery design)
        2. Labor Cost: labor_hours * hourly_labor_rate
        3. Base Production Cost: Stitching Cost + Labor Cost
        4. Profit Margin: Base Cost * (profit_margin_pct / 100)
        5. Subtotal: Base Cost + Profit Margin
        6. GST: Subtotal * (gst_rate_pct / 100)
        7. Total Order Cost: Subtotal + GST
        """
        print(f"[{self.name}] Connecting to Database to retrieve pricing rates from Config tab...")
        
        db = GoogleSheetsService()
        config = db.get_config_variables()
        
        base_rate = parse_numeric_rate(
            config.get("Cost per 1000 Stitches") or config.get("Cost per 1000 stitches"),
            10.0
        )
        hourly_rate = parse_numeric_rate(
            config.get("Hourly Labor Rate") or config.get("Hourly labor rate") or config.get("Labor Rate"),
            100.0
        )
        profit_margin_pct = parse_numeric_rate(
            config.get("Profit margin") or config.get("Profit Margin Percent") or config.get("Profit Margin") or config.get("Profit margin percent"),
            20.0
        )
        gst_rate = parse_numeric_rate(
            config.get("GST Rate Percent") or config.get("GST Rate") or config.get("GST") or config.get("GST rate percent"),
            18.0
        )
        
        order_type_clean = (state.order_type or "").strip().lower()
        qty = int(state.quantity or 1)
        
        # 1. Stitching Cost
        if order_type_clean == "embroidery design":
            stitch_cost = 0.0
            stitches_display = "0 (Software Design)"
        else:
            stitches = int(state.stitch_count or 0)
            if stitches <= 0 and state.template_name:
                tmpl = db.get_template_by_name(state.template_name)
                if tmpl and (tmpl.get("stitch_count") or tmpl.get("base_stitch_count")):
                    stitches = int(tmpl.get("stitch_count") or tmpl.get("base_stitch_count") or 0)
                    state.stitch_count = stitches
            stitch_cost = round(((stitches * qty) / 1000.0) * base_rate, 2)
            stitches_display = f"{stitches} st x {qty} qty / 1000 x Rs {base_rate}"

        # 2. Labor Cost (Converted from Labor Minutes to Hours)
        labor_hours = float(state.labor_hours or 0.0)
        if getattr(state, "labor_minutes", None) and float(state.labor_minutes) > 0:
            labor_hours = round(float(state.labor_minutes) / 60.0, 2)
            state.labor_hours = labor_hours
        elif labor_hours <= 0 and state.template_name:
            tmpl = db.get_template_by_name(state.template_name)
            if tmpl:
                if tmpl.get("labor_minutes") or tmpl.get("default_labor_minutes"):
                    lm = float(tmpl.get("labor_minutes") or tmpl.get("default_labor_minutes"))
                    labor_hours = round(lm / 60.0, 2)
                    state.labor_minutes = lm
                    state.labor_hours = labor_hours
                elif tmpl.get("default_labor_hours"):
                    labor_hours = float(tmpl["default_labor_hours"])
                    state.labor_hours = labor_hours

        labor_cost = round(labor_hours * hourly_rate, 2)

        # 3. Base Production Cost
        base_cost = round(stitch_cost + labor_cost, 2)

        # 4. Profit Margin
        profit_amount = round(base_cost * (profit_margin_pct / 100.0), 2)

        # 5. Subtotal (Net Price)
        subtotal = round(base_cost + profit_amount, 2)

        # 6. GST
        gst_amount = round(subtotal * (gst_rate / 100.0), 2)

        # 7. Total Cost
        total_cost = round(subtotal + gst_amount, 2)
        
        state.base_cost_rs = base_cost
        state.profit_margin_rs = profit_amount
        state.profit_margin_pct = profit_margin_pct
        state.gst_amount_rs = gst_amount
        state.gst_rate_pct = gst_rate
        state.total_cost_rs = total_cost
        state.invoice_status = "Estimated"
        
        estimator_log = (
            f"\n[Estimator Agent]: Strict 4-Factor Cost Breakdown:\n"
            f"• Stitching Cost: {stitches_display} = Rs {stitch_cost}\n"
            f"• Labor Cost: {labor_hours} hrs x Rs {hourly_rate}/hr = Rs {labor_cost}\n"
            f"• Base Production Cost: Rs {base_cost}\n"
            f"• Profit Margin ({profit_margin_pct}%): Rs {profit_amount}\n"
            f"• Subtotal: Rs {subtotal}\n"
            f"• GST ({gst_rate}%): Rs {gst_amount}\n"
            f"• Total Order Cost: Rs {total_cost}. Status set to 'Estimated'.\n"
        )
             
        state.aggregated_reasoning = (state.aggregated_reasoning or "") + estimator_log
        
        print(f"[{self.name}] Cost Calculated: Rs {state.total_cost_rs} (Stitch: Rs {stitch_cost}, Labor: Rs {labor_cost}, Margin: Rs {profit_amount}, GST: Rs {gst_amount})")
        return state
