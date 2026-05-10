import os
import uuid
import datetime
import pytz
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

IST = pytz.timezone("Asia/Kolkata")

class GoogleSheetsService:
    """Wrapper for writing outputs directly to Boss's spreadsheet."""
    def __init__(self):
        self.spreadsheet_id = os.getenv("GOOGLE_SHEET_ID")
        self.creds_file = r"d:\Projects\CJSDesigns\credentials.json"
        
        try:
            self.scopes = ['https://www.googleapis.com/auth/spreadsheets']
            if os.path.exists(self.creds_file):
                # Local Development Context
                self.creds = service_account.Credentials.from_service_account_file(self.creds_file, scopes=self.scopes)
            else:
                # Cloud Run Production Context (Implicit Auth)
                self.creds, _ = google.auth.default(scopes=self.scopes)
                
            self.service = build('sheets', 'v4', credentials=self.creds)
        except Exception as e:
            print(f"[SheetsAPI] Auth failed. Check credentials: {e}")
            self.service = None

    def append_order(self, state) -> str:
        """
        Appends the order details from the AgentState into the Google Sheet.
        Returns the generated Order ID if successful.
        """
        if not self.service: return None
        
        # Generate a unique tracking ID
        order_id = f"CJS-{str(uuid.uuid4())[:6].upper()}"
        
        # New column order (A-M) matching workflow progression
        values = [[
            datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M"),  # A: Order Date
            order_id,                                               # B: Order ID
            state.customer_id or "Unknown",                        # C: Customer ID
            state.sender_id,                                        # D: Phone
            state.fabric_type or "Unknown",                        # E: Material
            state.embroidery_type or "Unknown",                    # F: Embroidery Type
            int(state.stitch_count) if state.stitch_count and str(state.stitch_count).isdigit() else 0, # G: Stitch Count
            state.machine_assigned or "Pending",                   # H: Machine
            state.estimated_completion_date or "Unknown",          # I: Estimated Delivery Date
            f"Rs {state.total_cost_rs or 0}",                      # J: Estimated Cost
            state.invoice_status or "Estimated",                   # K: Payment Status
            state.aggregated_reasoning or "No logic recorded",     # L: Reasoning
            state.quantity or 1                                    # M: Quantity
        ]]
        
        body = {'values': values}
        
        try:
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="A:K",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            print(f"[SheetsAPI] Appended Order {order_id} successfully.")
            return order_id
            
        except Exception as e:
            print(f"[SheetsAPI] Append failed: {e}")
            return None

    def update_order(self, state) -> bool:
        """
        Locates an existing order by ID and updates its core fields.
        Preserves original Order Date, ID, Customer ID, and Phone.
        Appends new reasoning to the reasoning log.
        """
        if not self.service or not state.order_id: return False
        
        try:
            # Step 1: Find the row index
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="B:B"
            ).execute()
            rows = result.get('values', [])
            target_row = None
            for i, row in enumerate(rows):
                if row and row[0] == state.order_id:
                    target_row = i + 1
                    break
            
            if not target_row:
                print(f"[SheetsAPI] Update failed: {state.order_id} not found.")
                return False
                
            # Step 2: Read existing reasoning to append
            k_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=f"L{target_row}"
            ).execute()
            existing_reasoning = ""
            k_vals = k_result.get('values', [])
            if k_vals and k_vals[0]:
                existing_reasoning = k_vals[0][0]
                
            # Step 3: Prepare updated values for columns E through L
            # E: Material, F: Style, G: Stitches, H: Machine, I: Date, J: Cost, K: Status, L: Reasoning
            updated_values = [[
                state.fabric_type or "Unknown",
                state.embroidery_type or "Unknown",
                state.stitch_count or 0,
                state.machine_assigned or "Pending",
                state.estimated_completion_date or "Unknown",
                f"Rs {state.total_cost_rs or 0}",
                state.invoice_status or "Estimated",
                existing_reasoning + "\n[Update Session]: " + (state.aggregated_reasoning or ""),
                state.quantity or 1 # M: Quantity
            ]]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"E{target_row}:M{target_row}",
                valueInputOption="USER_ENTERED",
                body={'values': updated_values}
            ).execute()
            
            print(f"[SheetsAPI] Updated Order {state.order_id} successfully.")
            return True
            
        except Exception as e:
            print(f"[SheetsAPI] Update failed: {e}")
            return False

    def get_order(self, order_id: str) -> dict:
        """
        Scans Sheet1 for a specific Order ID and securely returns 
        the historical properties associated with it.
        """
        if not self.service or not order_id: return None
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="A:K"
            ).execute()
            
            rows = result.get('values', [])
            for row in rows:
                if len(row) > 1 and row[1] == order_id:
                    print(f"[SheetsAPI] Found historical order: {order_id}")
                    return {
                        "date":             row[0]  if len(row) > 0  else None,
                        "customer_id":      row[2]  if len(row) > 2  else None,
                        "phone":            row[3]  if len(row) > 3  else None,
                        "fabric_type":      row[4]  if len(row) > 4  else None,
                        "embroidery_type":  row[5]  if len(row) > 5  else None,
                        "stitch_count":     int(row[6]) if len(row) > 6 and str(row[6]).isdigit() else None,
                        "machine_assigned": row[7]  if len(row) > 7  else None,
                        "completion_date":  row[8]  if len(row) > 8  else None,
                        "cost":             row[9]  if len(row) > 9  else None,
                        "status":           row[10] if len(row) > 10 else None,
                        "reasoning":        row[11] if len(row) > 11 else "No historical agent reasoning log found in Column L.",
                        "quantity":         int(row[12]) if len(row) > 12 and str(row[12]).isdigit() else None
                    }
            print(f"[SheetsAPI] Order {order_id} not found in database.")
            return None
        except Exception as e:
            print(f"[SheetsAPI] Fetch failed: {e}")
            return None

    def get_machine_availability(self) -> dict:
        """
        Calculates when 'Ricoma' and 'Aakruthi' physically become free by mathematically 
        parsing all open, incomplete backlogged orders natively from the Google Sheet.
        """
        availability = { "Ricoma": datetime.datetime.now(IST).replace(tzinfo=None), "Aakruthi": datetime.datetime.now(IST).replace(tzinfo=None) }
        if not self.service: 
            return availability
            
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range="A:K").execute()
            rows = result.get('values', [])
            
            for row in rows:
                if len(row) > 7:
                    machine = str(row[7]).strip()   # H: Machine
                    end_str = str(row[8]).strip()   # I: Estimated Delivery Date
                    status  = str(row[10]).strip().lower() if len(row) > 10 else ""  # K: Payment Status
                    
                    if "completed" in status or "invoiced" in status: continue
                    
                    if machine in availability and end_str:
                        try:
                            end_dt = datetime.datetime.strptime(end_str, "%Y-%m-%d")
                            if end_dt > availability[machine]:
                                availability[machine] = end_dt
                        except ValueError:
                            pass
            return availability
        except Exception as e:
            print(f"[SheetsAPI] Warning: Failed to parse queues natively: {e}")
            return availability

    def get_holidays(self) -> list:
        """
        Reads explicitly marked off-days from the 'Holidays' tab in Boss's Google Sheet.
        Explicitly bypasses Header A1 and parses strict 2-April-2026 formats natively.
        """
        holidays = []
        if not self.service: return holidays
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, 
                range="Holidays!A:B"
            ).execute()
            
            rows = result.get('values', [])
            for index, row in enumerate(rows):
                if index == 0: continue # Safely skip header row
                
                if len(row) > 0:
                    date_str = str(row[0]).strip()
                    try:
                        # Map native Boss format: 2-April-2026
                        dt = datetime.datetime.strptime(date_str, "%d-%B-%Y").date()
                        holidays.append(dt)
                    except ValueError:
                        # ISO 8601 fallback safety
                        try:
                            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                            holidays.append(dt)
                        except ValueError:
                            pass
                            
            print(f"[SheetsAPI] Extracted {len(holidays)} explicit holidays from 'Holidays' tab.")
            return holidays
            
        except Exception as e:
            print(f"[SheetsAPI] Warning: 'Holidays' tab not found or unreadable: {e}")
            return holidays

    def get_costing_rules(self) -> dict:
        """
        Extracts variable combinatorial pricing natively from Boss's 'Costing' tab.
        Strict 5-Column Requirement: [Embroidery(A), Material(B), Unit(C), UnitCount(D), Cost(E)]
        """
        rules = {}
        if not self.service: return rules
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Costing!A:E"
            ).execute()
            rows = result.get('values', [])
            
            for index, row in enumerate(rows):
                if index == 0: continue # Pass header strictly
                
                if len(row) >= 5:
                    embroidery = str(row[0]).strip().lower()
                    material = str(row[1]).strip().lower()
                    try:
                        unit_count = float(row[3])
                        cost = float(row[4])
                        # Bind combinatorial tuple!
                        rules[(embroidery, material)] = {
                            "unit_count": unit_count,
                            "cost": cost
                        }
                    except ValueError:
                        pass
                        
            print(f"[SheetsAPI] Extracted {len(rules)} combinatoric pricing pairs from 'Costing' tab.")
            return rules
        except Exception as e:
            print(f"[SheetsAPI] Warning: 'Costing' tab 5-Column execution failed: {e}")
            return rules

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        Natively locates the precise row mathematical index of the referenced Order ID 
        and physically overwrites the specific Column J value natively.
        """
        if not self.service or not order_id: return False
        
        try:
            # Step 1: Query the entire Column B explicitly to find the Row Index
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="B:B"
            ).execute()
            
            rows = result.get('values', [])
            target_row_num = None
            
            for index, row in enumerate(rows):
                if row and row[0] == order_id:
                    target_row_num = index + 1 # Google Sheets is mathematically 1-indexed natively
                    break
                    
            if not target_row_num:
                print(f"[SheetsAPI] Could not mutate status: {order_id} strictly missing from database.")
                return False
                
            # Step 2: Push the new Status to col K (index 11, 1-based)
            body = {'values': [[new_status]]}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"K{target_row_num}",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            print(f"[SheetsAPI] Success executing Row Mutation: {order_id} updated to {new_status}")
            return True
            
        except Exception as e:
            print(f"[SheetsAPI] Critical Row Mutation Failure: {e}")
            return False

    def update_order_field(self, order_id: str, field: str, new_value: str) -> bool:
        """
        Allows Boss to manually override an AI-generated field on an existing order.
        Writes to override columns L (delivery_date), M (cost), or N (machine).
        Also appends a timestamped note to Column K (reasoning log).
        
        Column mapping:
          L = Override Delivery Date
          M = Override Cost (Rs)
          N = Override Machine
        """
        if not self.service or not order_id: return False

        FIELD_MAP = {
            "delivery_date": "M",   # Col M: Override Delivery Date
            "cost": "N",            # Col N: Override Cost
            "machine": "O",         # Col O: Override Machine
        }
        
        target_col = FIELD_MAP.get(field.lower().replace(" ", "_"))
        if not target_col:
            print(f"[SheetsAPI] Unknown override field '{field}'. Must be one of: {list(FIELD_MAP.keys())}")
            return False

        try:
            # Step 1: Find row index by Order ID in Column B
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="B:B"
            ).execute()
            rows = result.get('values', [])
            target_row = None
            for i, row in enumerate(rows):
                if row and row[0] == order_id:
                    target_row = i + 1
                    break

            if not target_row:
                print(f"[SheetsAPI] Override failed: {order_id} not found.")
                return False

            # Step 2: Read existing Col L (reasoning) to append, not overwrite
            k_result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range=f"L{target_row}"
            ).execute()
            existing_k = ""
            k_vals = k_result.get('values', [])
            if k_vals and k_vals[0]:
                existing_k = k_vals[0][0]

            # Step 3: Write override value to correct column (M/N/O)
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{target_col}{target_row}",
                valueInputOption="USER_ENTERED",
                body={'values': [[new_value]]}
            ).execute()

            # Step 4: Append override audit note to Col L (reasoning)
            timestamp = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
            override_note = f"\n[Override - {timestamp}]: Boss manually changed '{field}' to '{new_value}'."
            updated_k = existing_k + override_note
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"L{target_row}",
                valueInputOption="USER_ENTERED",
                body={'values': [[updated_k]]}
            ).execute()

            print(f"[SheetsAPI] Override success: {order_id} col {target_col} = '{new_value}'")
            return True

        except Exception as e:
            print(f"[SheetsAPI] Override field update failed: {e}")
            return False

    def get_pending_payments(self) -> dict:
        """
        Scans all orders and returns those with Payment Status == 'Completed',
        grouped by Customer Name.
        Returns a dict: {"CUST-ID - Name": [order_dict, ...]}
        """
        if not self.service: return {}
        
        try:
            # Get lookup mapping first
            customer_map = self.get_all_customers_map()
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="A:O"
            ).execute()
            rows = result.get('values', [])
            pending = {}  # { "CUST-001 - Name": [orders] }
            
            for i, row in enumerate(rows):
                if i == 0: continue  # skip header
                if len(row) < 11: continue
                
                status = str(row[10]).strip().lower()  # K: Payment Status
                if status != "completed": continue
                
                cid = row[2].strip() if len(row) > 2 else "Unknown"
                cname = customer_map.get(cid, "Unknown Name")
                display_key = f"{cid} - {cname}"
                
                order = {
                    "order_id":        row[1]  if len(row) > 1  else "Unknown",
                    "customer_id":     cid,
                    "phone":           row[3]  if len(row) > 3  else "",
                    "embroidery_type": row[5]  if len(row) > 5  else "Unknown",
                    "fabric_type":     row[4]  if len(row) > 4  else "Unknown",
                    "cost":            row[9]  if len(row) > 9  else "Rs 0",
                    "delivery_date":   row[8]  if len(row) > 8  else "Unknown",
                }
                
                if display_key not in pending:
                    pending[display_key] = []
                pending[display_key].append(order)
            
            total_count = sum(len(v) for v in pending.values())
            print(f"[SheetsAPI] Found {total_count} completed-unpaid orders across {len(pending)} customers.")
            return pending
            
        except Exception as e:
            print(f"[SheetsAPI] get_pending_payments failed: {e}")
            return {}

    def get_customer_id_by_name(self, name: str) -> str:
        """
        Scans the 'Customers' sheet (Col A=ID, B=Name). 
        Returns the Customer ID if found via fuzzy match (case/space-insensitive).
        Returns None if not found.
        """
        if not self.service or not name: return None
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Customers!A:B"
            ).execute()
            rows = result.get('values', [])
            
            target = name.strip().lower()
            for i, row in enumerate(rows):
                if i == 0 or len(row) < 2: continue # skip header
                
                sheet_name = str(row[1]).strip().lower()
                if sheet_name == target:
                    return str(row[0]).strip()
            
            return None
            
        except Exception as e:
            print(f"[SheetsAPI] get_customer_id_by_name failed: {e}")
            return None
            
    def get_all_customers_map(self) -> dict:
        """
        Returns a dictionary mapping Customer ID -> Name from the 'Customers' sheet.
        """
        mapping = {}
        if not self.service: return mapping
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Customers!A:B"
            ).execute()
            rows = result.get('values', [])
            
            for i, row in enumerate(rows):
                if i == 0 or len(row) < 2: continue
                cid = str(row[0]).strip()
                cname = str(row[1]).strip()
                if cid and cname:
                    mapping[cid] = cname
            
            return mapping
        except Exception as e:
            print(f"[SheetsAPI] get_all_customers_map failed: {e}")
            return mapping

    def check_duplicate_order(self, customer_id: str, phone: str, fabric_type: str, embroidery_type: str, stitch_count: int) -> bool:
        """
        Scans recent orders (last 24 hours) for an identical match based on:
        Customer ID, Phone, Fabric, Embroidery Type, and Stitch Count.
        Returns True if a probable duplicate is found.
        """
        if not self.service or not customer_id: return False
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="A:O"
            ).execute()
            rows = result.get('values', [])
            
            cutoff = datetime.datetime.now(IST).replace(tzinfo=None) - datetime.timedelta(hours=24)
            
            for i, row in enumerate(rows):
                if i == 0 or len(row) < 7: continue  # skip header or short rows
                
                # A: Order Date
                date_str = str(row[0]).strip()
                try:
                    order_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
                    if order_dt < cutoff:
                        continue # Skip old orders
                except ValueError:
                    pass
                
                # Compare fields safely with null-handling
                r_customer = str(row[2]).strip().lower() if len(row) > 2 else ""
                r_phone    = str(row[3]).strip() if len(row) > 3 else ""
                r_fabric   = str(row[4]).strip().lower() if len(row) > 4 else ""
                r_style    = str(row[5]).strip().lower() if len(row) > 5 else ""
                r_stitch   = str(row[6]).strip() if len(row) > 6 else ""
                
                c_id = str(customer_id).strip().lower() if customer_id else ""
                c_phone = str(phone).strip() if phone else ""
                c_fabric = str(fabric_type).strip().lower() if fabric_type else ""
                c_style = str(embroidery_type).strip().lower() if embroidery_type else ""
                c_stitch = str(stitch_count).strip() if stitch_count else ""
                
                if (r_customer == c_id and
                    r_phone    == c_phone and
                    r_fabric   == c_fabric and
                    r_style    == c_style and
                    r_stitch   == c_stitch):
                    print(f"[SheetsAPI] Duplicate detected from {order_dt} for {customer_id}")
                    return True
                    
            return False
            
        except Exception as e:
            print(f"[SheetsAPI] Duplicate check failed: {e}")
            return False

    def get_secretary_data(self) -> dict:
        """
        Gathers data for the Secretary Agent's daily report.
        Aggregation includes:
        - Orders to be completed Today (Col I == Today)
        - Pending invoices > 7 days (Col K != 'Invoiced' and Col A < 7 days ago)
        - Holiday state (Today and Upcoming next 7 days)
        - General Reminders from 'Reminders' tab
        """
        if not self.service: return {}
        
        today = datetime.datetime.now(IST).date()
        today_str = today.strftime("%Y-%m-%d")
        seven_days_ago = today - datetime.timedelta(days=7)
        
        data = {
            "today": today_str,
            "orders_due_today": [],
            "pending_invoices_old": [],
            "holiday_status": None,
            "upcoming_holidays": [],
            "reminders": []
        }
        
        try:
            # 1. Fetch Orders (Sheet1)
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="A:K"
            ).execute()
            rows = result.get('values', [])
            
            for i, row in enumerate(rows):
                if i == 0: continue
                
                # A: Order Date, B: ID, I: Completion, K: Status
                order_date_str = row[0].split(" ")[0] if len(row) > 0 else ""
                order_id = row[1] if len(row) > 1 else "Unknown"
                completion_date = row[8] if len(row) > 8 else ""
                status = row[10].strip().lower() if len(row) > 10 else ""
                
                # Orders due today
                if completion_date == today_str:
                    data["orders_due_today"].append({
                        "id": order_id,
                        "customer": row[2] if len(row) > 2 else "Unknown",
                        "fabric": row[4] if len(row) > 4 else "Unknown",
                        "cost": row[9] if len(row) > 9 else "Unknown"
                    })
                
                # Pending invoices > 7 days
                if status != "invoiced" and status != "completed" and order_date_str:
                    try:
                        order_dt = datetime.datetime.strptime(order_date_str, "%Y-%m-%d").date()
                        if order_dt < seven_days_ago:
                            data["pending_invoices_old"].append({
                                "id": order_id,
                                "date": order_date_str,
                                "cost": row[9] if len(row) > 9 else "Unknown"
                            })
                    except ValueError:
                        pass
            
            # 2. Fetch Holiday Status
            holidays = self.get_holidays()
            next_seven = today + datetime.timedelta(days=7)
            
            if today in holidays:
                data["holiday_status"] = "TODAY IS A HOLIDAY!"
                
            for h in holidays:
                if today < h <= next_seven:
                    data["upcoming_holidays"].append(h.strftime("%d-%B-%Y"))
            
            # 3. Fetch Reminders
            reminders = self.get_reminders()
            for r in reminders:
                when = r.get("when", "").lower()
                what = r.get("what", "")
                
                # Handle "11th of each month"
                if "of each month" in when:
                    num_str = "".join(filter(str.isdigit, when))
                    if num_str and str(today.day) == num_str:
                        data["reminders"].append(what)
                
                # Handle Today if specified exactly or just a date
                elif when == today_str or when == today.strftime("%d-%B-%y"):
                    data["reminders"].append(what)
            
            return data
            
        except Exception as e:
            print(f"[SheetsAPI] Secretary Data fetch failed: {e}")
            return data

    def get_reminders(self) -> list:
        """Reads from a dedicated 'Reminders' tab."""
        reminders = []
        if not self.service: return reminders
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Reminders!A:C"
            ).execute()
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if i == 0 or len(row) < 3: continue
                reminders.append({"when": str(row[1]).strip(), "what": str(row[2]).strip()})
            return reminders
        except Exception as e:
            print(f"[SheetsAPI] Warning: 'Reminders' tab execution failure: {e}")
            return reminders
