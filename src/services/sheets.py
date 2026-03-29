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
            state.invoice_status
        ]]
        
        body = {'values': values}
        
        try:
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="Sheet1!A:J",
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
                range="Sheet1!A:J"
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
