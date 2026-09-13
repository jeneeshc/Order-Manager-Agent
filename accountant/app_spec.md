# CJS Designs Accounting Application - Product Specification (v1.0)

## 1. System Architecture & Platform Specifications
* **Frontend Interface:** Progressive Web App (PWA). Built using responsive web technologies (HTML/CSS/JS or lightweight frameworks like React/Vue/Svelte) to render seamlessly on laptop screens and mobile devices (specifically optimized for iPhone).
* **Deployment:** Web-hosted, including a Web App Manifest to enable the "Add to Home Screen" function. This provides a native-like app icon and full-screen mobile experience without App Store or Google Play deployment.
* **Backend Database:** Google Sheets API. The application will perform CRUD (Create, Read, Update, Delete) operations directly to a designated Google Spreadsheet.
* **Data Override Strategy:** Google Sheets acts as the single source of truth. The application pushes data via API, but the user retains the ability to open the sheet directly to correct errors, update master data (fixed assets, loans), run custom pivot tables, or download backups.
* **Authentication:** Single-user access secured via a simple PIN or Google Account OAuth tied to the owner's specific account.

## 2. Services & Pricing Engine
The application calculates order pricing dynamically based on user inputs.

### Service Categories
* **Machine Embroidery:** Pricing based on both stitch count and labor hours.
* **Machine Embroidery Design Making:** Pricing based on labor hours only (stitch count defaults to 0).

### Global Variables (Stored in 'Config' Sheet)
* **Cost per 1000 Stitches:** ₹8 (includes raw material and machine running cost)
* **Hourly Labor Rate:** ₹100
* **GST Rate:** 18%

### Calculation Logic
* `Stitch Cost = (Stitch Count / 1000) * 8`
* `Labor Cost = Labor Hours * 100`
* `Base Cost = Stitch Cost + Labor Cost`
* `Selling Price (Pre-Tax) = Base Cost * (1 + (Profit Margin % / 100))`
* `Final Invoice Total = (Selling Price (Pre-Tax) * 1.18) + Courier Charge (Optional)`

## 3. Invoicing Module
* **Document Generation:** Generates a clean, printable PDF or web-based HTML invoice.
* **Branding:** Prominently features the "CJS Designs" logo and tagline at the header.
* **Customer-Facing Output:** Displays Customer Name, Date, Service Description, Selling Price (Pre-Tax), GST (18%), optional Courier Charge, and Final Total.
* **Confidentiality:** Internal metrics (Stitch Count, Profit Margin, Base Cost, Labor Hours) are strictly hidden from the customer-facing invoice.
* **Ledger Integration:** Upon generating/saving, the invoice data automatically appends a new row to the `Sales_Ledger` tab in Google Sheets.

## 4. Expense & Asset Management
### Expense Logging
* **Interface:** A quick-entry form for out-of-pocket costs and recurring bills.
* **Predefined Categories:**
    * Machine Maintenance
    * Electricity
    * Cost of Thread
    * Stabilizer / Backing
    * Facility / Rent
    * Miscellaneous / Other
* **Inventory Philosophy:** Raw materials are treated as direct operational expenses at the time of purchase (no complex physical inventory decrementing).

### Capital & Asset Tracking
* **Capital Registry:** Tracks initial investments, owner equity, and active loans.
* **Fixed Asset Tracker:** Logs high-value equipment (e.g., multi-head embroidery machines, computers).
* **Automated Depreciation:** System calculates standard monthly depreciation (e.g., straight-line) for active assets and automatically injects these figures into the monthly expense ledger to ensure accurate P&L.

## 5. Main Dashboard & KPIs
The home screen answers: *Are we making money? How busy is the machine? Where is the money going?*

### The Financial Pulse (Top KPI Tiles - Current Month)
* **Total Revenue:** Total billed from all invoices this month.
* **Total Expenses:** Sum of all logged operational costs, base costs, and automated depreciation.
* **Net Profit:** Revenue minus Total Expenses.
* **Net Profit Margin:** Net Profit ÷ Revenue.

### Production Metrics
* **Total Stitches Billed:** Helps forecast thread and maintenance needs.
* **Labor Hours Logged:** Total hours billed to clients.
* **Average Order Value (AOV):** Total Revenue / Number of Invoices.

### Visual Charts
* **Revenue vs. Expenses (6-Month Bar Chart):** Trend line to monitor cost creep vs. revenue.
* **Expense Distribution (Donut Chart):** Breakdown of expenses by category (e.g., Thread, Rent, Electricity).

### Quick Actions & Recent Activity
* **Primary Buttons:** Large, thumb-friendly buttons for `[ + New Invoice ]` and `[ + Log Expense ]`.
* **Recent Invoices:** A simple list of the last 5 invoices (Date, Client, Amount).

## 6. Google Sheets Database Schema
The designated Google Spreadsheet requires the following structured tabs:

| Sheet Name | Purpose | Required Column Headers |
| :--- | :--- | :--- |
| **Config** | Stores global variables | Variable Name, Value, Last Updated |
| **Sales_Ledger** | Records generated invoices | Date, Invoice ID, Customer, Service Type, Total Stitches, Labor Hrs, Margin %, Net Price, GST, Courier, Gross Total |
| **Expense_Ledger** | Records operational costs | Date, Expense Category, Description, Amount, Payment Method |
| **Asset_Ledger** | Tracks fixed assets | Asset Name, Purchase Date, Purchase Price, Useful Life (Months), Monthly Depreciation |
| **Capital_Ledger**| Tracks investments/loans | Date, Transaction Type (Investment/Loan), Description, Amount |
