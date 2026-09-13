import os
import sys
import re
import datetime
import dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import firestore

# Ensure utf-8 output on Windows terminal
sys.stdout.reconfigure(encoding='utf-8')

dotenv.load_dotenv(r"d:\Projects\CJSDesigns\.env")

PROJECT_ID = "cjs-designs-501004"
SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SHEETS_CREDS_FILE = r"d:\Projects\CJSDesigns\credentials.json"
FIRESTORE_CREDS_FILE = r"d:\Projects\CJSDesigns\service-account-key.json"

print(f"Connecting to Google Sheets ID: {SHEET_ID}")
print(f"Connecting to Firestore Project: {PROJECT_ID}")

# 1. Sheets Client (Uses credentials.json which has Sheets access)
sheets_creds = service_account.Credentials.from_service_account_file(
    SHEETS_CREDS_FILE,
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
sheets_service = build('sheets', 'v4', credentials=sheets_creds)

# 2. Firestore Client (Uses service-account-key.json which has Firestore access)
if os.path.exists(FIRESTORE_CREDS_FILE):
    db = firestore.Client.from_service_account_json(FIRESTORE_CREDS_FILE, project=PROJECT_ID)
else:
    db = firestore.Client(project=PROJECT_ID)

def clean_number(val, default=0.0):
    if val is None:
        return default
    s = str(val).replace("₹", "").replace(",", "").replace("Rs", "").replace("rs", "").strip()
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return default

def clean_int(val, default=0):
    if val is None:
        return default
    s = re.sub(r'[^\d]', '', str(val))
    try:
        return int(s)
    except ValueError:
        return default

def get_tab_rows(tab_name):
    try:
        res = sheets_service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"'{tab_name}'!A:Z"
        ).execute()
        rows = res.get('values', [])
        if len(rows) <= 1:
            return []
        headers = [h.strip() for h in rows[0]]
        items = []
        for r in rows[1:]:
            item = {}
            for idx, h in enumerate(headers):
                item[h] = r[idx] if idx < len(r) else ""
            item["_raw_row"] = r
            items.append(item)
        return items
    except Exception as e:
        print(f"Warning: Failed to fetch tab {tab_name}: {e}")
        return []

def migrate_all():
    print("=" * 60)
    print("STARTING GOOGLE SHEETS -> FIRESTORE MIGRATION")
    print("=" * 60)

    summary = {}

    # 1. Config
    print("\n1. Migrating Config...")
    config_rows = get_tab_rows("Config")
    count = 0
    for r in config_rows:
        var_name = r.get("Variable Name", "").strip()
        val_str = r.get("Value", "").strip()
        last_updated = r.get("Last Updated", "").strip()
        if not var_name:
            continue
        # Convert numeric values if applicable
        val = clean_number(val_str, default=val_str)
        doc_ref = db.collection("config").document(var_name)
        doc_ref.set({
            "key": var_name,
            "value": val,
            "last_updated": last_updated or datetime.datetime.now().isoformat()
        })
        count += 1
    summary["config"] = count
    print(f"-> Migrated {count} config variables.")

    # 2. Customers
    print("\n2. Migrating Customers...")
    cust_rows = get_tab_rows("Customers")
    count = 0
    for r in cust_rows:
        cid = str(r.get("Customer ID", "")).strip()
        name = r.get("Name", "").strip()
        phone = str(r.get("Phone", "")).strip()
        address = r.get("Address", "").strip()
        if not cid and not name:
            continue
        doc_id = cid or f"CUST-{count+1}"
        db.collection("customers").document(doc_id).set({
            "customer_id": doc_id,
            "name": name,
            "phone": phone,
            "address": address
        })
        count += 1
    summary["customers"] = count
    print(f"-> Migrated {count} customers.")

    # 3. Vendors
    print("\n3. Migrating Vendors...")
    vendor_rows = get_tab_rows("Vendors")
    count = 0
    for r in vendor_rows:
        vid = str(r.get("Vendor ID", "")).strip()
        name = r.get("Name", "").strip()
        cat = r.get("Category", "").strip()
        contact = r.get("Contact Person", "").strip()
        phone = str(r.get("Phone", "")).strip()
        address = r.get("Address", "").strip()
        if not vid and not name:
            continue
        doc_id = vid or f"VND-{count+1}"
        db.collection("vendors").document(doc_id).set({
            "vendor_id": doc_id,
            "name": name,
            "category": cat,
            "contact_person": contact,
            "phone": phone,
            "address": address
        })
        count += 1
    summary["vendors"] = count
    print(f"-> Migrated {count} vendors.")

    # 4. Description Templates
    print("\n4. Migrating Description Templates...")
    tmpl_rows = get_tab_rows("Description_Templates")
    count = 0
    for r in tmpl_rows:
        tname = r.get("Template Name", "").strip()
        scat = r.get("Service Category", "").strip()
        desc = r.get("Description", "").strip()
        machine = r.get("Machine", "").strip() or "None"
        labor_min = clean_number(r.get("Labor Minutes"), 60.0)
        stitch_count = clean_int(r.get("Stitch Count"), 0)
        if not tname:
            continue
        doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', tname)
        db.collection("description_templates").document(doc_id).set({
            "template_name": tname,
            "service_category": scat,
            "description": desc,
            "machine": machine,
            "labor_minutes": labor_min,
            "labor_hours": round(labor_min / 60.0, 2),
            "stitch_count": stitch_count
        })
        count += 1
    summary["description_templates"] = count
    print(f"-> Migrated {count} templates.")

    # 5. Holidays
    print("\n5. Migrating Holidays...")
    holiday_rows = get_tab_rows("Holidays")
    count = 0
    for r in holiday_rows:
        date_str = r.get("Date", "").strip()
        event = r.get("Event", "").strip()
        if not date_str:
            continue
        doc_id = re.sub(r'[^a-zA-Z0-9_-]', '_', date_str)
        db.collection("holidays").document(doc_id).set({
            "date": date_str,
            "event": event
        })
        count += 1
    summary["holidays"] = count
    print(f"-> Migrated {count} holidays.")

    # 6. Reminders
    print("\n6. Migrating Reminders...")
    rem_rows = get_tab_rows("Reminders")
    count = 0
    for r in rem_rows:
        no = r.get("No", "").strip()
        when = r.get("When", "").strip()
        what = r.get("What to remind", "").strip()
        if not what:
            continue
        doc_id = f"rem_{no or count+1}"
        db.collection("reminders").document(doc_id).set({
            "no": clean_int(no, count + 1),
            "when": when,
            "what_to_remind": what
        })
        count += 1
    summary["reminders"] = count
    print(f"-> Migrated {count} reminders.")

    # 7. Orders
    print("\n7. Migrating Orders...")
    order_rows = get_tab_rows("Orders")
    count = 0
    for r in order_rows:
        raw = r.get("_raw_row", [])
        oid = raw[1] if len(raw) > 1 else ""
        if not oid or not str(oid).strip().startswith("CJS-"):
            continue
        oid = str(oid).strip()
        data = {
            "order_date": raw[0] if len(raw) > 0 else "",
            "order_id": oid,
            "customer_id": raw[2] if len(raw) > 2 else "",
            "customer_name": raw[3] if len(raw) > 3 else "",
            "phone": raw[4] if len(raw) > 4 else "",
            "order_type": raw[5] if len(raw) > 5 else "",
            "template_name": raw[6] if len(raw) > 6 else "",
            "quantity": clean_int(raw[7] if len(raw) > 7 else 1, 1),
            "stitch_count": clean_int(raw[8] if len(raw) > 8 else 0, 0),
            "labor_hours": clean_number(raw[9] if len(raw) > 9 else 0.0, 0.0),
            "machine": raw[10] if len(raw) > 10 else "None",
            "estimated_delivery_date": raw[11] if len(raw) > 11 else "",
            "estimated_cost": raw[12] if len(raw) > 12 else "",
            "payment_status": raw[13] if len(raw) > 13 else "Estimated",
            "reasoning": raw[14] if len(raw) > 14 else "",
            "overrides": raw[15] if len(raw) > 15 else "",
            "image_url": raw[16] if len(raw) > 16 else "",
            "created_at": datetime.datetime.now().isoformat()
        }
        db.collection("orders").document(oid).set(data)
        count += 1
    summary["orders"] = count
    print(f"-> Migrated {count} orders.")

    # 8. Expense Ledger
    print("\n8. Migrating Expense Ledger...")
    exp_rows = get_tab_rows("Expense_Ledger")
    count = 0
    for idx, r in enumerate(exp_rows):
        dt_val = r.get("Date", "").strip()
        cat = r.get("Expense Category", "").strip()
        desc = r.get("Description", "").strip()
        amt = clean_number(r.get("Amount"))
        pm = r.get("Payment Method", "").strip()
        if not desc and amt == 0:
            continue
        doc_id = f"exp_{idx+1}"
        db.collection("expense_ledger").document(doc_id).set({
            "id": doc_id,
            "date": dt_val,
            "category": cat,
            "description": desc,
            "amount": amt,
            "payment_method": pm
        })
        count += 1
    summary["expense_ledger"] = count
    print(f"-> Migrated {count} expense records.")

    # 9. Asset Ledger
    print("\n9. Migrating Asset Ledger...")
    asset_rows = get_tab_rows("Asset_Ledger")
    count = 0
    for idx, r in enumerate(asset_rows):
        name = r.get("Asset Name", "").strip()
        pdate = r.get("Purchase Date", "").strip()
        price = clean_number(r.get("Purchase Price"))
        life = clean_int(r.get("Useful Life (Months)"))
        dep = clean_number(r.get("Monthly Depreciation"))
        if not name:
            continue
        doc_id = f"asset_{idx+1}"
        db.collection("asset_ledger").document(doc_id).set({
            "id": doc_id,
            "name": name,
            "purchase_date": pdate,
            "purchase_price": price,
            "useful_life_months": life,
            "monthly_depreciation": dep
        })
        count += 1
    summary["asset_ledger"] = count
    print(f"-> Migrated {count} asset records.")

    # 10. Capital Ledger
    print("\n10. Migrating Capital Ledger...")
    cap_rows = get_tab_rows("Capital_Ledger")
    count = 0
    for idx, r in enumerate(cap_rows):
        dt_val = r.get("Date", "").strip()
        ttype = r.get("Transaction Type", "").strip()
        desc = r.get("Description", "").strip()
        amt = clean_number(r.get("Amount"))
        if not desc and amt == 0:
            continue
        doc_id = f"cap_{idx+1}"
        db.collection("capital_ledger").document(doc_id).set({
            "id": doc_id,
            "date": dt_val,
            "transaction_type": ttype,
            "description": desc,
            "amount": amt
        })
        count += 1
    summary["capital_ledger"] = count
    print(f"-> Migrated {count} capital records.")

    # 11. Sales Ledger
    print("\n11. Migrating Sales Ledger...")
    sales_rows = get_tab_rows("Sales_Ledger")
    count = 0
    for idx, r in enumerate(sales_rows):
        inv_id = r.get("Invoice ID", "").strip()
        if not inv_id:
            continue
        doc_id = inv_id or f"sale_{idx+1}"
        db.collection("sales_ledger").document(doc_id).set({
            "date": r.get("Date", ""),
            "invoice_id": inv_id,
            "customer": r.get("Customer", ""),
            "service_type": r.get("Service Type", ""),
            "total_stitches": clean_int(r.get("Total Stitches")),
            "labor_hrs": clean_number(r.get("Labor Hrs")),
            "margin_pct": clean_number(r.get("Margin %")),
            "net_price": clean_number(r.get("Net Price")),
            "gst": clean_number(r.get("GST")),
            "courier": clean_number(r.get("Courier")),
            "gross_total": clean_number(r.get("Gross Total"))
        })
        count += 1
    summary["sales_ledger"] = count
    print(f"-> Migrated {count} sales ledger records.")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE! SUMMARY:")
    print("=" * 60)
    for col, cnt in summary.items():
        print(f"  • {col.ljust(25)}: {cnt} records")
    print("=" * 60)

if __name__ == "__main__":
    migrate_all()
