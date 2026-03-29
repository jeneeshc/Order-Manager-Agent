import os
import uuid
import datetime
import google.auth
from google.oauth2 import service_account
from googleapiclient.discovery import build

class GoogleSheetsService:
    """Wrapper for writing outputs directly to Siny's spreadsheet."""
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
        
        # We assume Sheet1 has standardized headers
        values = [[
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            order_id,
            state.sender_id,
            state.fabric_type or "Unknown",
            state.embroidery_type or "Unknown",
            state.stitch_count or 0,
            state.machine_assigned or "Pending",
            state.estimated_completion_date or "Unknown",
            f"Rs {state.total_cost_rs or 0}",
            state.invoice_status or "Estimated",
            state.scheduling_reasoning or "No logic recorded"
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

    def get_order(self, order_id: str) -> dict:
        """
        Scans Sheet1 for a specific Order ID and securely returns 
        the historical properties associated with it.
        """
        if not self.service or not order_id: return None
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range="A:J"
            ).execute()
            
            rows = result.get('values', [])
            for row in rows:
                if len(row) > 1 and row[1] == order_id:
                    print(f"[SheetsAPI] Found historical order: {order_id}")
                    return {
                        "date": row[0] if len(row) > 0 else None,
                        "fabric_type": row[3] if len(row) > 3 else None,
                        "embroidery_type": row[4] if len(row) > 4 else None,
                        "stitch_count": int(row[5]) if len(row) > 5 and str(row[5]).isdigit() else None,
                        "machine_assigned": row[6] if len(row) > 6 else None,
                        "completion_date": row[7] if len(row) > 7 else None,
                        "cost": row[8] if len(row) > 8 else None,
                        "status": row[9] if len(row) > 9 else None
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
        availability = { "Ricoma": datetime.datetime.now(), "Aakruthi": datetime.datetime.now() }
        if not self.service: 
            return availability
            
        try:
            result = self.service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range="A:K").execute()
            rows = result.get('values', [])
            
            for row in rows:
                if len(row) > 7:
                    machine = str(row[6]).strip()
                    end_str = str(row[7]).strip()
                    
                    # Ignore completed orders
                    if len(row) > 9 and "completed" in str(row[9]).lower(): continue
                    
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
        Reads explicitly marked off-days from the 'Holidays' tab in Siny's Google Sheet.
        Expects Column A to contain dates formatted strictly as YYYY-MM-DD.
        """
        holidays = []
        if not self.service: return holidays
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, 
                range="Holidays!A:A"
            ).execute()
            
            rows = result.get('values', [])
            for row in rows:
                if row:
                    try:
                        dt = datetime.datetime.strptime(row[0].strip(), "%Y-%m-%d").date()
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
        Extracts variable pricing properties explicitly from Siny's 'Costing' tab.
        Assumes Column A = Rule Name (e.g. 'Base Rate', 'Velvet'), Column B = Numeric Rate/Multiplier.
        """
        rules = {}
        if not self.service: return rules
        
        try:
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id, range="Costing!A:B"
            ).execute()
            rows = result.get('values', [])
            
            for row in rows:
                if len(row) > 1:
                    key = str(row[0]).strip().lower()
                    try:
                        val = float(row[1])
                        rules[key] = val
                    except ValueError:
                        pass
                        
            print(f"[SheetsAPI] Extracted {len(rules)} explicit pricing rules from 'Costing' tab.")
            return rules
        except Exception as e:
            print(f"[SheetsAPI] Warning: 'Costing' tab execution failed: {e}")
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
                
            # Step 2: Push the new Status explicitly forcing Column J
            body = {'values': [[new_status]]}
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"J{target_row_num}",
                valueInputOption="USER_ENTERED",
                body=body
            ).execute()
            
            print(f"[SheetsAPI] Success executing Row Mutation: {order_id} updated to {new_status}")
            return True
            
        except Exception as e:
            print(f"[SheetsAPI] Critical Row Mutation Failure: {e}")
            return False
