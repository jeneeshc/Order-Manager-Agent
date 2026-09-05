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

        # Enforce that customer_id is mandatory and valid
        if not state.customer_id or str(state.customer_id).strip().lower() in {"unknown", "none", "unknown name", "new customer", "unknown customer", "n/a", "null", "undefined", ""}:
            print(f"[SheetsAPI] Append failed: Invalid or missing customer_id '{state.customer_id}'. Customer name is mandatory.")
            return None
        
        # Generate a unique tracking ID
        order_id = f"CJS-{str(uuid.uuid4())[:6].upper()}"
        
        # Standard column order (A-L) for Orders tab
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
            state.aggregated_reasoning or "No logic recorded"      # L: Reasoning
        ]]
        
        body = {'values': values}
        
        try:
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="'Orders'!A:L",
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
                spreadsheetId=self.spreadsheet_id, range="'Orders'!B:B"
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
                spreadsheetId=self.spreadsheet_id, range=f"'Orders'!L{target_row}"
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
                existing_reasoning + "\n[Update Session]: " + (state.aggregated_reasoning or "")
            ]]
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Orders'!E{target_row}:L{target_row}",
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
        Scans the 'Orders' tab for a specific Order ID and securely returns 
        the historical properties associated with it.
        """
        if not self.service or not order_id: return None
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Orders'!A:O"
            ).execute()
            
            rows = result.get('values', [])
            for row in rows:
                if len(row) > 1 and row[1] == order_id:
                    print(f"[SheetsAPI] Found historical order: {order_id}")
                    return {
                        "date":                   row[0]  if len(row) > 0  else None,
                        "order_id":               row[1]  if len(row) > 1  else None,
                        "customer_id":            row[2]  if len(row) > 2  else None,
                        "phone":                  row[3]  if len(row) > 3  else None,
                        "fabric_type":            row[4]  if len(row) > 4  else None,
                        "embroidery_type":        row[5]  if len(row) > 5  else None,
                        "stitch_count":           int(row[6]) if len(row) > 6 and str(row[6]).isdigit() else None,
                        "machine_assigned":       row[7]  if len(row) > 7  else None,
                        "completion_date":        row[8]  if len(row) > 8  else None,
                        "cost":                   row[9]  if len(row) > 9  else None,
                        "status":                 row[10] if len(row) > 10 else None,
                        "reasoning":              row[11] if len(row) > 11 else "No historical agent reasoning log found in Column L.",
                        "override_delivery_date": row[12] if len(row) > 12 else None,
                        "override_cost":          row[13] if len(row) > 13 else None,
                        "override_machine":       row[14] if len(row) > 14 else None,
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
            result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range="'Orders'!A:K").execute()
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


    def update_order_status(self, order_id: str, new_status: str) -> bool:
        """
        Natively locates the precise row mathematical index of the referenced Order ID 
        and physically overwrites the specific Column J value natively.
        """
        if not self.service or not order_id: return False
        
        try:
            # Step 1: Query the entire Column B explicitly to find the Row Index
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="'Orders'!B:B"
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
                range=f"'Orders'!K{target_row_num}",
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
                spreadsheetId=self.spreadsheet_id, range="'Orders'!B:B"
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
                spreadsheetId=self.spreadsheet_id, range=f"'Orders'!L{target_row}"
            ).execute()
            existing_k = ""
            k_vals = k_result.get('values', [])
            if k_vals and k_vals[0]:
                existing_k = k_vals[0][0]

            # Step 3: Write override value to correct column (M/N/O)
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Orders'!{target_col}{target_row}",
                valueInputOption="USER_ENTERED",
                body={'values': [[new_value]]}
            ).execute()

            # Step 4: Append override audit note to Col L (reasoning)
            timestamp = datetime.datetime.now(IST).strftime("%Y-%m-%d %H:%M")
            override_note = f"\n[Override - {timestamp}]: Boss manually changed '{field}' to '{new_value}'."
            updated_k = existing_k + override_note
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"'Orders'!L{target_row}",
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
                spreadsheetId=self.spreadsheet_id, range="'Orders'!A:O"
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
                spreadsheetId=self.spreadsheet_id, range="Customers!A:D"
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

    def create_customer_if_not_exists(self, name: str, phone: str = "", address: str = "") -> str:
        """
        Looks up customer by name (fuzzy match). 
        If found, returns the existing Customer ID.
        If not found, generates a new numeric Customer ID (e.g. max + 1, starting at 1001),
        appends a new row to the 'Customers' sheet (Cols A:D), and returns the new ID.
        """
        if not self.service or not name:
            return None
            
        name = name.strip()
        # Verify name is valid (not a placeholder like Unknown)
        name_lower = name.lower()
        if name_lower in {"unknown", "none", "unknown name", "new customer", "unknown customer", "n/a", "null", "undefined", ""}:
            return None
            
        # 1. Look up existing customer
        existing_id = self.get_customer_id_by_name(name)
        if existing_id:
            return existing_id
            
        try:
            # 2. Get all customers to find the max ID
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Customers!A:D"
            ).execute()
            rows = result.get('values', [])
            
            max_id = 1000  # Default starting number minus 1
            for i, row in enumerate(rows):
                if i == 0 or not row: continue  # Skip header
                cid_str = str(row[0]).strip()
                if cid_str.isdigit():
                    max_id = max(max_id, int(cid_str))
            
            new_id = str(max_id + 1)
            
            # 3. Append the new customer row preserving exact A:D structure (ID, Name, Phone, Address)
            body = {'values': [[new_id, name, phone or "", address or ""]]}
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Customers!A:D",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            print(f"[SheetsAPI] Created new customer: ID={new_id}, Name='{name}'")
            return new_id
            
        except Exception as e:
            print(f"[SheetsAPI] create_customer_if_not_exists failed: {e}")
            return None
            
    def get_all_customers_map(self) -> dict:
        """
        Returns a dictionary mapping Customer ID -> Name from the 'Customers' sheet.
        """
        mapping = {}
        if not self.service: return mapping
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Customers!A:D"
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

    def find_similar_order(self, customer_id: str, fabric_type: str, embroidery_type: str, stitch_count: int) -> dict | None:
        """
        Scans recent orders (last 7 days) for a ~90% similar match based on:
        Customer ID, Fabric, Embroidery Type, and Stitch Count (10% variance allowed).
        Does NOT check phone number.
        Returns a dictionary of the most similar order's details if found, else None.
        """
        if not self.service or not customer_id: return None
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="'Orders'!A:O"
            ).execute()
            rows = result.get('values', [])
            
            cutoff = datetime.datetime.now(IST).replace(tzinfo=None) - datetime.timedelta(days=7)
            
            c_id = str(customer_id).strip().lower()
            c_fabric = str(fabric_type).strip().lower() if fabric_type else ""
            c_style = str(embroidery_type).strip().lower() if embroidery_type else ""
            
            try:
                c_stitch = int(stitch_count) if stitch_count else 0
            except ValueError:
                c_stitch = 0
            
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
                
                r_id = str(row[1]).strip() if len(row) > 1 else ""
                r_customer = str(row[2]).strip().lower() if len(row) > 2 else ""
                r_fabric   = str(row[4]).strip().lower() if len(row) > 4 else ""
                r_style    = str(row[5]).strip().lower() if len(row) > 5 else ""
                
                try:
                    r_stitch = int(str(row[6]).strip()) if len(row) > 6 else 0
                except ValueError:
                    r_stitch = 0
                
                # Calculate Similarity
                # Customer ID must match exactly
                if r_customer != c_id:
                    continue
                    
                # Fabric and Style must match
                if r_fabric != c_fabric or r_style != c_style:
                    continue
                
                # Stitch count variance (10%)
                if c_stitch > 0:
                    variance = abs(r_stitch - c_stitch) / float(c_stitch)
                else:
                    variance = 0 if r_stitch == 0 else 1.0
                    
                print(f"[DEBUG SheetsAPI] Comparing with order {r_id}: r_customer={r_customer}, r_fabric={r_fabric}, r_style={r_style}, r_stitch={r_stitch}. Variance={variance}")
                    
                if variance <= 0.10:
                    print(f"[SheetsAPI] ~90% Similar order detected from {order_dt} for {customer_id} (Variance: {variance*100:.1f}%)")
                    return {
                        "order_id": r_id,
                        "date": date_str,
                        "fabric": str(row[4]).strip() if len(row) > 4 else "Unknown",
                        "style": str(row[5]).strip() if len(row) > 5 else "Unknown",
                        "stitches": r_stitch
                    }
                    
            return None
            
        except Exception as e:
            print(f"[SheetsAPI] Similar order check failed: {e}")
            return None

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
            customer_map = self.get_all_customers_map()
            
            # 1. Fetch Orders
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="'Orders'!A:K"
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
                    cust_id = row[2].strip() if len(row) > 2 else "Unknown"
                    cust_name = customer_map.get(cust_id, cust_id)
                    data["orders_due_today"].append({
                        "id": order_id,
                        "customer": cust_name,
                        "fabric": row[4] if len(row) > 4 else "Unknown",
                        "cost": row[9] if len(row) > 9 else "Unknown",
                        "machine": row[7] if len(row) > 7 else "Unknown"
                    })
                
                # Pending invoices > 7 days
                if status != "invoiced" and status != "completed" and order_date_str:
                    try:
                        order_dt = datetime.datetime.strptime(order_date_str, "%Y-%m-%d").date()
                        if order_dt < seven_days_ago:
                            cust_id = row[2].strip() if len(row) > 2 else "Unknown"
                            cust_name = customer_map.get(cust_id, cust_id)
                            data["pending_invoices_old"].append({
                                "id": order_id,
                                "customer": cust_name,
                                "date": order_date_str,
                                "completion_date": completion_date,
                                "cost": row[9] if len(row) > 9 else "Unknown"
                            })
                    except ValueError:
                        pass
            
            # 2. Fetch Holiday Status
            holidays = self.get_holidays()
            next_seven = today + datetime.timedelta(days=7)
            
            if today in holidays or today.weekday() in (5, 6):
                if today.weekday() in (5, 6):
                    data["holiday_status"] = "TODAY IS A HOLIDAY! (Weekend)"
                else:
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

    def get_orders_pending_invoicing(self) -> dict:
        """
        Scans all orders and returns those with status not in ('invoiced', 'completed'),
        grouped by Customer Name.
        Returns a dict: {"Customer Name": [order_dict, ...]}
        """
        if not self.service: return {}
        try:
            customer_map = self.get_all_customers_map()
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="'Orders'!A:K"
            ).execute()
            rows = result.get('values', [])
            pending = {}
            for i, row in enumerate(rows):
                if i == 0: continue # skip header
                if len(row) < 2: continue
                
                status = str(row[10]).strip().lower() if len(row) > 10 else ""
                if status in ("invoiced", "completed"): continue
                
                order_id = row[1]
                cid = row[2].strip() if len(row) > 2 else "Unknown"
                cname = customer_map.get(cid, cid)
                
                order = {
                    "order_id": order_id,
                    "customer_id": cid,
                    "customer_name": cname,
                    "fabric_type": row[4] if len(row) > 4 else "Unknown",
                    "embroidery_type": row[5] if len(row) > 5 else "Unknown",
                    "cost": row[9] if len(row) > 9 else "Rs 0",
                    "completion_date": row[8] if len(row) > 8 else "Unknown",
                }
                if cname not in pending:
                    pending[cname] = []
                pending[cname].append(order)
            return pending
        except Exception as e:
            print(f"[SheetsAPI] get_orders_pending_invoicing failed: {e}")
            return {}

    def mark_invoicing_completed(self, customer_name_or_all: str) -> int:
        """
        Updates status to 'Completed' for all orders pending invoicing under the specified customer (or 'all').
        Returns the number of orders updated.
        """
        if not self.service or not customer_name_or_all: return 0
        
        try:
            customer_map = self.get_all_customers_map()
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="'Orders'!B:K"
            ).execute()
            rows = result.get('values', [])
            
            target_all = customer_name_or_all.strip().lower() == "all"
            target_cid = None
            target_cname = None
            
            if not target_all:
                target_cid = self.get_customer_id_by_name(customer_name_or_all)
                target_cname = customer_name_or_all.strip().lower()
                
            updated_count = 0
            for i, row in enumerate(rows):
                row_num = i + 1
                if i == 0: continue # skip header
                if len(row) < 1: continue
                
                order_id = row[0] # Column B
                cid = row[1].strip() if len(row) > 1 else "" # Column C
                status = row[9].strip().lower() if len(row) > 9 else "" # Column K
                
                if status in ("invoiced", "completed"): continue
                
                cname = customer_map.get(cid, "").strip().lower()
                
                match = False
                if target_all:
                    match = True
                else:
                    if (target_cid and cid == target_cid) or (target_cname and cname == target_cname):
                        match = True
                        
                if match:
                    body = {'values': [["Completed"]]}
                    self.service.spreadsheets().values().update(
                        spreadsheetId=self.spreadsheet_id,
                        range=f"'Orders'!K{row_num}",
                        valueInputOption="USER_ENTERED",
                        body=body
                    ).execute()
                    updated_count += 1
                    
            print(f"[SheetsAPI] Updated {updated_count} orders to Completed for customer '{customer_name_or_all}'")
            return updated_count
            
        except Exception as e:
            print(f"[SheetsAPI] mark_invoicing_completed failed: {e}")
            return 0

    # -------------------------------------------------------------------------
    # NEW TABS INTEGRATION: Config, Sales_Ledger, Expense_Ledger, Vendors
    # (Maintains 100% strict column invariance for CJS Accountant)
    # -------------------------------------------------------------------------

    def get_config_variables(self) -> dict:
        """
        Fetches system variables from the 'Config' tab (Col A=Variable Name, Col B=Value, Col C=Last Updated).
        Returns a dictionary mapping Variable Name -> Value (coerced to float/int if numeric, else string).
        Example: {"Cost per 1000 Stitches": 10.0, "Hourly Labor Rate": 100.0, "GST Rate Percent": 18.0, "Studio Name": "CJS Designs"}
        """
        config = {}
        if not self.service: return config
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Config'!A:B"
            ).execute()
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if i == 0 or len(row) < 2: continue
                var_name = str(row[0]).strip()
                var_val_str = str(row[1]).strip()
                try:
                    var_val = float(var_val_str)
                    if var_val.is_integer():
                        var_val = int(var_val)
                except ValueError:
                    var_val = var_val_str
                config[var_name] = var_val
            print(f"[SheetsAPI] Loaded {len(config)} variables from 'Config' tab.")
            return config
        except Exception as e:
            print(f"[SheetsAPI] get_config_variables failed: {e}")
            return config

    def get_sales_ledger(self, limit: int = 50) -> list:
        """
        Reads records from 'Sales_Ledger'!A:K.
        Columns: Date, Invoice ID, Customer, Service Type, Total Stitches, Labor Hrs, Margin %, Net Price, GST, Courier, Gross Total.
        """
        sales = []
        if not self.service: return sales
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Sales_Ledger'!A:K"
            ).execute()
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if i == 0 or not row: continue
                sales.append({
                    "date": row[0] if len(row) > 0 else "",
                    "invoice_id": row[1] if len(row) > 1 else "",
                    "customer": row[2] if len(row) > 2 else "",
                    "service_type": row[3] if len(row) > 3 else "",
                    "total_stitches": int(row[4]) if len(row) > 4 and str(row[4]).isdigit() else 0,
                    "labor_hrs": float(row[5]) if len(row) > 5 and str(row[5]).replace(".", "", 1).isdigit() else 0.0,
                    "margin_pct": float(row[6]) if len(row) > 6 and str(row[6]).replace(".", "", 1).isdigit() else 0.0,
                    "net_price": float(row[7]) if len(row) > 7 and str(row[7]).replace(".", "", 1).isdigit() else 0.0,
                    "gst": float(row[8]) if len(row) > 8 and str(row[8]).replace(".", "", 1).isdigit() else 0.0,
                    "courier": float(row[9]) if len(row) > 9 and str(row[9]).replace(".", "", 1).isdigit() else 0.0,
                    "gross_total": float(row[10]) if len(row) > 10 and str(row[10]).replace(".", "", 1).isdigit() else 0.0,
                })
            return sales[-limit:]
        except Exception as e:
            print(f"[SheetsAPI] get_sales_ledger failed: {e}")
            return sales

    def record_sale_in_ledger(self, date_str: str, invoice_id: str, customer_name: str, service_type: str, total_stitches: int, labor_hrs: float, margin_pct: float, net_price: float, gst: float, courier: float, gross_total: float) -> bool:
        """
        Appends an invoice record into 'Sales_Ledger'!A:K.
        Guarantees exact preservation of CJS Accountant column ordering:
        A: Date, B: Invoice ID, C: Customer, D: Service Type, E: Total Stitches,
        F: Labor Hrs, G: Margin %, H: Net Price, I: GST, J: Courier, K: Gross Total.
        """
        if not self.service: return False
        try:
            values = [[
                date_str,
                invoice_id,
                customer_name,
                service_type,
                str(total_stitches),
                str(labor_hrs),
                str(margin_pct),
                str(net_price),
                str(gst),
                str(courier),
                str(gross_total)
            ]]
            body = {'values': values}
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="'Sales_Ledger'!A:K",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            print(f"[SheetsAPI] Appended invoice {invoice_id} to 'Sales_Ledger'.")
            return True
        except Exception as e:
            print(f"[SheetsAPI] record_sale_in_ledger failed: {e}")
            return False

    def get_vendors(self) -> list:
        """
        Reads supplier/vendor records from 'Vendors'!A:F.
        Columns: Vendor ID, Name, Category, Contact Person, Phone, Address.
        """
        vendors = []
        if not self.service: return vendors
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Vendors'!A:F"
            ).execute()
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if i == 0 or not row: continue
                vendors.append({
                    "vendor_id": row[0] if len(row) > 0 else "",
                    "name": row[1] if len(row) > 1 else "",
                    "category": row[2] if len(row) > 2 else "",
                    "contact_person": row[3] if len(row) > 3 else "",
                    "phone": row[4] if len(row) > 4 else "",
                    "address": row[5] if len(row) > 5 else "",
                })
            return vendors
        except Exception as e:
            print(f"[SheetsAPI] get_vendors failed: {e}")
            return vendors

    def get_recent_expenses(self, limit: int = 50) -> list:
        """
        Reads expense records from 'Expense_Ledger'!A:E.
        Columns: Date, Expense Category, Description, Amount, Payment Method.
        """
        expenses = []
        if not self.service: return expenses
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Expense_Ledger'!A:E"
            ).execute()
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if i == 0 or not row: continue
                expenses.append({
                    "date": row[0] if len(row) > 0 else "",
                    "category": row[1] if len(row) > 1 else "",
                    "description": row[2] if len(row) > 2 else "",
                    "amount": float(row[3]) if len(row) > 3 and str(row[3]).replace(".", "", 1).isdigit() else row[3] if len(row) > 3 else 0.0,
                    "payment_method": row[4] if len(row) > 4 else "",
                })
            return expenses[-limit:]
        except Exception as e:
            print(f"[SheetsAPI] get_recent_expenses failed: {e}")
            return expenses

    def get_active_orders_summary(self, limit: int = 5) -> list:
        """
        Fetches the most recent active/in-progress orders (not completed/invoiced)
        from 'Orders'!A:O to present as quick-select options for Boss.
        """
        active_orders = []
        if not self.service: return active_orders
        try:
            customer_map = self.get_all_customers_map()
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="'Orders'!A:O"
            ).execute()
            rows = result.get('values', [])
            for i, row in enumerate(rows):
                if i == 0 or len(row) < 2: continue
                status = str(row[10]).strip().lower() if len(row) > 10 else ""
                if status in ("completed", "invoiced"): continue
                
                oid = row[1].strip()
                cid = row[2].strip() if len(row) > 2 else "Unknown"
                cname = customer_map.get(cid, cid)
                fabric = row[4] if len(row) > 4 else "Unknown"
                embroidery = row[5] if len(row) > 5 else "Unknown"
                machine = row[7] if len(row) > 7 else "Pending"
                delivery = row[8] if len(row) > 8 else "Unknown"
                cost = row[9] if len(row) > 9 else "Rs 0"
                
                active_orders.append({
                    "order_id": oid,
                    "customer": cname,
                    "fabric": fabric,
                    "embroidery": embroidery,
                    "machine": machine,
                    "delivery_date": delivery,
                    "cost": cost
                })
            # Return most recent ones
            return active_orders[-limit:]
        except Exception as e:
            print(f"[SheetsAPI] get_active_orders_summary failed: {e}")
            return active_orders
