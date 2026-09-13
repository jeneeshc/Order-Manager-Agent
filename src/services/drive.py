import os
import io
import json
import datetime
import pytz
from google.oauth2 import service_account
import google.auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

IST = pytz.timezone("Asia/Kolkata")
DEFAULT_ORDERS_FOLDER_ID = "1YyowyXwI1xB4fGCG7pmxWtevJlVeSoPA"

class GoogleDriveService:
    _cached_service = None

    def __init__(self):
        self.parent_folder_id = os.getenv("GOOGLE_DRIVE_ORDERS_FOLDER_ID", DEFAULT_ORDERS_FOLDER_ID)
        self.creds_file = r"d:\Projects\CJSDesigns\credentials.json"
        self.scopes = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets'
        ]
        
        if GoogleDriveService._cached_service is not None:
            self.service = GoogleDriveService._cached_service
            return

        try:
            creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
            if creds_json:
                info = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
                self.creds = service_account.Credentials.from_service_account_info(info, scopes=self.scopes)
            elif os.path.exists(self.creds_file):
                self.creds = service_account.Credentials.from_service_account_file(self.creds_file, scopes=self.scopes)
            else:
                self.creds, _ = google.auth.default(scopes=self.scopes)
                
            self.service = build('drive', 'v3', credentials=self.creds, cache_discovery=False)
            GoogleDriveService._cached_service = self.service
        except Exception as e:
            print(f"[DriveAPI] Auth failed. Check credentials: {e}")
            self.service = None

    def get_or_create_monthly_folder(self, dt: datetime.datetime = None) -> str:
        """
        Ensures a monthly subfolder with format YYYY_MM (e.g. 2026_09) exists
        under the parent folder. Returns the folder ID.
        """
        if not self.service:
            print("[DriveAPI] Drive service unavailable.")
            return None

        if dt is None:
            dt = datetime.datetime.now(IST)
        folder_name = dt.strftime("%Y_%m")

        try:
            # Check if monthly folder already exists
            query = (
                f"'{self.parent_folder_id}' in parents "
                f"and name = '{folder_name}' "
                f"and mimeType = 'application/vnd.google-apps.folder' "
                f"and trashed = false"
            )
            results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()

            files = results.get('files', [])
            if files:
                folder_id = files[0]['id']
                print(f"[DriveAPI] Found existing monthly folder '{folder_name}': {folder_id}")
                return folder_id

            # Create new monthly folder
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [self.parent_folder_id]
            }
            folder = self.service.files().create(
                body=folder_metadata,
                fields='id, name',
                supportsAllDrives=True
            ).execute()
            folder_id = folder.get('id')
            print(f"[DriveAPI] Created new monthly folder '{folder_name}': {folder_id}")
            return folder_id

        except Exception as e:
            print(f"[DriveAPI] Failed to get/create monthly folder '{folder_name}': {e}")
            return None

    def upload_order_image(
        self,
        order_id: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        filename: str = None
    ) -> dict:
        """
        Uploads an image to Google Drive under the current month's folder (YYYY_MM)
        named with the Order ID.
        Returns a dict with file_id, view_link, and content_link.
        """
        if not self.service:
            print("[DriveAPI] Service unavailable. Skipping image upload.")
            return None

        if not image_bytes or not order_id:
            print("[DriveAPI] Invalid image_bytes or order_id.")
            return None

        folder_id = self.get_or_create_monthly_folder()
        if not folder_id:
            print("[DriveAPI] Could not obtain monthly folder ID.")
            return None

        # Determine extension
        ext = ".jpg"
        if "png" in (mime_type or "").lower() or (filename and filename.lower().endswith(".png")):
            ext = ".png"
        elif "webp" in (mime_type or "").lower() or (filename and filename.lower().endswith(".webp")):
            ext = ".webp"
        target_filename = f"{order_id}{ext}"

        media = MediaIoBaseUpload(io.BytesIO(image_bytes), mimetype=mime_type or "image/jpeg", resumable=True)

        try:
            # Check if file already exists in target folder (e.g. for order edit replacement)
            query = (
                f"'{folder_id}' in parents "
                f"and name = '{target_filename}' "
                f"and trashed = false"
            )
            existing_results = self.service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            existing_files = existing_results.get('files', [])

            if existing_files:
                file_id = existing_files[0]['id']
                updated_file = self.service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields='id, name, webViewLink, webContentLink',
                    supportsAllDrives=True
                ).execute()
                print(f"[DriveAPI] Updated existing file for {order_id} ({file_id})")
                file_data = updated_file
            else:
                file_metadata = {
                    'name': target_filename,
                    'parents': [folder_id]
                }
                new_file = self.service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, name, webViewLink, webContentLink',
                    supportsAllDrives=True
                ).execute()
                file_id = new_file.get('id')
                print(f"[DriveAPI] Uploaded new file for {order_id}: {target_filename} ({file_id})")
                file_data = new_file

            # Ensure file is viewable with link
            try:
                self.service.permissions().create(
                    fileId=file_id,
                    body={'type': 'anyone', 'role': 'reader'},
                    supportsAllDrives=True
                ).execute()
            except Exception as pe:
                print(f"[DriveAPI] Note on permission sharing for {file_id}: {pe}")

            view_link = file_data.get('webViewLink') or f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
            content_link = file_data.get('webContentLink') or f"https://drive.google.com/uc?export=view&id={file_id}"

            return {
                "file_id": file_id,
                "filename": target_filename,
                "view_link": view_link,
                "content_link": content_link,
                "folder_id": folder_id
            }

        except Exception as e:
            print(f"[DriveAPI] Failed to upload order image for {order_id}: {e}")
            return None
