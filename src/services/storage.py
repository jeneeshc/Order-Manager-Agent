import os
import io
import json
import datetime
import pytz
from google.oauth2 import service_account
import google.auth
from google.cloud import storage

IST = pytz.timezone("Asia/Kolkata")
DEFAULT_BUCKET_NAME = "cjs-designs-501004-media"
DEFAULT_PREFIX = "order_images"

class CloudStorageService:
    _cached_client = None

    def __init__(self, bucket_name: str = None):
        self.bucket_name = bucket_name or os.getenv("GCS_MEDIA_BUCKET", DEFAULT_BUCKET_NAME)
        self.prefix = os.getenv("GCS_MEDIA_PREFIX", DEFAULT_PREFIX)
        self.creds_file = r"d:\Projects\CJSDesigns\credentials.json"
        
        if CloudStorageService._cached_client is not None:
            self.client = CloudStorageService._cached_client
        else:
            try:
                creds_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
                if creds_json:
                    info = json.loads(creds_json) if isinstance(creds_json, str) else creds_json
                    creds = service_account.Credentials.from_service_account_info(info)
                    self.client = storage.Client(credentials=creds)
                elif os.path.exists(self.creds_file):
                    self.client = storage.Client.from_service_account_json(self.creds_file)
                else:
                    # Cloud Run Production Context (Inherited service account)
                    self.client = storage.Client()
                CloudStorageService._cached_client = self.client
            except Exception as e:
                print(f"[GCS] Auth failed: {e}")
                self.client = None

    def get_monthly_prefix(self, dt: datetime.datetime = None) -> str:
        """
        Returns monthly folder path in format: order_images/YYYY_MM
        """
        if dt is None:
            dt = datetime.datetime.now(IST)
        month_str = dt.strftime("%Y_%m")
        return f"{self.prefix}/{month_str}"

    def upload_order_image(
        self,
        order_id: str,
        image_bytes: bytes,
        mime_type: str = "image/jpeg",
        filename: str = None,
        dt: datetime.datetime = None
    ) -> dict:
        """
        Uploads an image to Google Cloud Storage organized under order_images/YYYY_MM/{order_id}.{ext}.
        Returns dict with file_id, view_link, and webContentLink.
        """
        if not self.client:
            print("[GCS] Storage client unavailable.")
            return None

        # Determine file extension
        ext = "jpg"
        if "png" in (mime_type or "").lower():
            ext = "png"
        elif "webp" in (mime_type or "").lower():
            ext = "webp"
        elif filename and "." in filename:
            ext = filename.rsplit(".", 1)[-1].lower()

        monthly_prefix = self.get_monthly_prefix(dt)
        blob_name = f"{monthly_prefix}/{order_id}.{ext}"

        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            
            blob.upload_from_string(
                image_bytes,
                content_type=mime_type or "image/jpeg"
            )
            
            public_url = f"https://storage.googleapis.com/{self.bucket_name}/{blob_name}"
            print(f"[GCS] Uploaded order {order_id} image successfully: {public_url}")
            
            return {
                "file_id": blob_name,
                "view_link": public_url,
                "webContentLink": public_url,
                "public_url": public_url
            }
        except Exception as e:
            print(f"[GCS] Failed to upload order image for {order_id}: {e}")
            return None
