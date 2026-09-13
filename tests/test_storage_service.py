import pytest
import datetime
from unittest.mock import MagicMock, patch
from src.services.storage import CloudStorageService

def test_get_monthly_prefix_custom_date():
    service = CloudStorageService(bucket_name="test-bucket")
    dt = datetime.datetime(2026, 9, 13, 10, 0, 0)
    prefix = service.get_monthly_prefix(dt)
    assert prefix == "order_images/2026_09"

def test_get_monthly_prefix_default():
    service = CloudStorageService(bucket_name="test-bucket")
    prefix = service.get_monthly_prefix()
    assert prefix.startswith("order_images/")
    assert len(prefix.split("/")[-1]) == 7  # YYYY_MM

def test_upload_order_image_success():
    service = CloudStorageService(bucket_name="test-bucket")
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    service.client = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    dt = datetime.datetime(2026, 9, 13)
    res = service.upload_order_image(
        order_id="CJS-12345",
        image_bytes=b"fake_image_bytes",
        mime_type="image/jpeg",
        dt=dt
    )

    assert res is not None
    assert res["file_id"] == "order_images/2026_09/CJS-12345.jpg"
    assert res["public_url"] == "https://storage.googleapis.com/test-bucket/order_images/2026_09/CJS-12345.jpg"
    mock_blob.upload_from_string.assert_called_once_with(
        b"fake_image_bytes",
        content_type="image/jpeg"
    )

def test_upload_order_image_png_extension():
    service = CloudStorageService(bucket_name="test-bucket")
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    service.client = mock_client
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob

    dt = datetime.datetime(2026, 9, 13)
    res = service.upload_order_image(
        order_id="CJS-67890",
        image_bytes=b"png_bytes",
        mime_type="image/png",
        dt=dt
    )

    assert res is not None
    assert res["file_id"] == "order_images/2026_09/CJS-67890.png"
    assert res["public_url"] == "https://storage.googleapis.com/test-bucket/order_images/2026_09/CJS-67890.png"
