import pytest
import datetime
from unittest.mock import MagicMock, patch
from src.services.db import FirestoreDatabaseService

def test_db_service_get_config_variables():
    svc = FirestoreDatabaseService.__new__(FirestoreDatabaseService)
    svc.db = MagicMock()
    
    mock_doc1 = MagicMock()
    mock_doc1.to_dict.return_value = {"key": "Cost per 1000 Stitches", "value": 10.0}
    mock_doc1.id = "Cost per 1000 Stitches"

    mock_doc2 = MagicMock()
    mock_doc2.to_dict.return_value = {"key": "Hourly Labor Rate", "value": 100.0}
    mock_doc2.id = "Hourly Labor Rate"

    svc.db.collection.return_value.stream.return_value = [mock_doc1, mock_doc2]

    config = svc.get_config_variables()
    assert config["Cost per 1000 Stitches"] == 10.0
    assert config["Hourly Labor Rate"] == 100.0

def test_db_service_get_customers_map():
    svc = FirestoreDatabaseService.__new__(FirestoreDatabaseService)
    svc.db = MagicMock()

    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {"customer_id": "1001", "name": "Adheela"}
    mock_doc.id = "1001"

    svc.db.collection.return_value.stream.return_value = [mock_doc]

    c_map = svc.get_all_customers_map()
    assert c_map["Adheela"] == "1001"
    assert svc.get_customer_id_by_name("adheela") == "1001"

def test_db_service_get_order():
    svc = FirestoreDatabaseService.__new__(FirestoreDatabaseService)
    svc.db = MagicMock()

    mock_doc = MagicMock()
    mock_doc.exists = True
    mock_doc.to_dict.return_value = {
        "order_id": "CJS-BE1653",
        "customer_name": "Adheela",
        "order_type": "Machine Embroidery",
        "template_name": "T Shirt Logo",
        "quantity": 1,
        "machine": "Aakruthi",
        "estimated_delivery_date": "2026-09-14",
        "estimated_cost": "Rs 107.45",
        "payment_status": "Estimated",
        "image_url": "https://storage.googleapis.com/test/img.jpg"
    }
    svc.db.collection.return_value.document.return_value.get.return_value = mock_doc

    order = svc.get_order("CJS-BE1653")
    assert order is not None
    assert order["order_id"] == "CJS-BE1653"
    assert order["customer"] == "Adheela"
    assert order["machine"] == "Aakruthi"
    assert order["cost"] == "Rs 107.45"
    assert order["image_url"] == "https://storage.googleapis.com/test/img.jpg"

def test_db_service_update_order_field():
    svc = FirestoreDatabaseService.__new__(FirestoreDatabaseService)
    svc.db = MagicMock()

    mock_doc_ref = MagicMock()
    svc.db.collection.return_value.document.return_value = mock_doc_ref

    res = svc.update_order_field("CJS-BE1653", "status", "Completed")
    assert res is True
    mock_doc_ref.update.assert_called_once()
    args = mock_doc_ref.update.call_args[0][0]
    assert args["payment_status"] == "Completed"
