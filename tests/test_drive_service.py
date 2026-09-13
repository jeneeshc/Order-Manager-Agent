import pytest
from unittest.mock import MagicMock, patch
import datetime
import pytz
from src.services.drive import GoogleDriveService, DEFAULT_ORDERS_FOLDER_ID

IST = pytz.timezone("Asia/Kolkata")

def test_drive_service_init_defaults():
    """Verify GoogleDriveService initializes with expected parent folder and scopes."""
    with patch.object(GoogleDriveService, '__init__', return_value=None):
        svc = GoogleDriveService()
        svc.parent_folder_id = DEFAULT_ORDERS_FOLDER_ID
        svc.scopes = ['https://www.googleapis.com/auth/drive']
        assert svc.parent_folder_id == "1YyowyXwI1xB4fGCG7pmxWtevJlVeSoPA"
        assert 'https://www.googleapis.com/auth/drive' in svc.scopes

def test_get_or_create_monthly_folder_existing():
    """Verify that existing monthly folder is found and returned."""
    with patch.object(GoogleDriveService, '__init__', return_value=None):
        svc = GoogleDriveService()
        svc.parent_folder_id = "test_parent"
        svc.service = MagicMock()

        # Mock finding existing folder
        mock_list = MagicMock()
        mock_list.execute.return_value = {"files": [{"id": "folder_sep_2026", "name": "2026_09"}]}
        svc.service.files().list.return_value = mock_list

        dt = datetime.datetime(2026, 9, 13, 11, 0, tzinfo=IST)
        folder_id = svc.get_or_create_monthly_folder(dt)

        assert folder_id == "folder_sep_2026"
        svc.service.files().create.assert_not_called()

def test_get_or_create_monthly_folder_creates_new():
    """Verify that if monthly folder does not exist, it creates one."""
    with patch.object(GoogleDriveService, '__init__', return_value=None):
        svc = GoogleDriveService()
        svc.parent_folder_id = "test_parent"
        svc.service = MagicMock()

        # Mock no existing folder found
        mock_list = MagicMock()
        mock_list.execute.return_value = {"files": []}
        svc.service.files().list.return_value = mock_list

        # Mock folder creation
        mock_create = MagicMock()
        mock_create.execute.return_value = {"id": "new_folder_created", "name": "2026_09"}
        svc.service.files().create.return_value = mock_create

        dt = datetime.datetime(2026, 9, 13, 11, 0, tzinfo=IST)
        folder_id = svc.get_or_create_monthly_folder(dt)

        assert folder_id == "new_folder_created"
        svc.service.files().create.assert_called_once()
        create_args = svc.service.files().create.call_args[1]
        assert create_args["body"]["name"] == "2026_09"
        assert create_args["body"]["parents"] == ["test_parent"]

def test_upload_order_image_new_file():
    """Verify upload_order_image uploads a new file and returns file_id and view links."""
    with patch.object(GoogleDriveService, '__init__', return_value=None):
        svc = GoogleDriveService()
        svc.parent_folder_id = "test_parent"
        svc.service = MagicMock()
        svc.get_or_create_monthly_folder = MagicMock(return_value="month_folder_123")

        # Mock existing search returns empty
        mock_list = MagicMock()
        mock_list.execute.return_value = {"files": []}
        svc.service.files().list.return_value = mock_list

        # Mock file creation
        mock_create = MagicMock()
        mock_create.execute.return_value = {
            "id": "file_abc_123",
            "name": "CJS-A1B2.jpg",
            "webViewLink": "https://drive.google.com/file/d/file_abc_123/view?usp=sharing",
            "webContentLink": "https://drive.google.com/uc?export=view&id=file_abc_123"
        }
        svc.service.files().create.return_value = mock_create

        mock_perm = MagicMock()
        svc.service.permissions().create.return_value = mock_perm

        res = svc.upload_order_image(
            order_id="CJS-A1B2",
            image_bytes=b"sample_bytes",
            mime_type="image/jpeg",
            filename="my_embroidery.jpg"
        )

        assert res["file_id"] == "file_abc_123"
        assert res["filename"] == "CJS-A1B2.jpg"
        assert "drive.google.com" in res["view_link"]
        assert res["folder_id"] == "month_folder_123"

def test_upload_order_image_existing_file_updates():
    """Verify upload_order_image updates file if an image with the order ID already exists in folder."""
    with patch.object(GoogleDriveService, '__init__', return_value=None):
        svc = GoogleDriveService()
        svc.parent_folder_id = "test_parent"
        svc.service = MagicMock()
        svc.get_or_create_monthly_folder = MagicMock(return_value="month_folder_123")

        # Mock existing search returns file
        mock_list = MagicMock()
        mock_list.execute.return_value = {"files": [{"id": "existing_file_999", "name": "CJS-A1B2.jpg"}]}
        svc.service.files().list.return_value = mock_list

        # Mock file update
        mock_update = MagicMock()
        mock_update.execute.return_value = {
            "id": "existing_file_999",
            "name": "CJS-A1B2.jpg",
            "webViewLink": "https://drive.google.com/file/d/existing_file_999/view?usp=sharing"
        }
        svc.service.files().update.return_value = mock_update

        mock_perm = MagicMock()
        svc.service.permissions().create.return_value = mock_perm

        res = svc.upload_order_image(
            order_id="CJS-A1B2",
            image_bytes=b"updated_sample_bytes",
            mime_type="image/jpeg"
        )

        assert res["file_id"] == "existing_file_999"
        svc.service.files().update.assert_called_once()
