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
