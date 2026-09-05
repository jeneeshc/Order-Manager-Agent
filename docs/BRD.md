# Business Requirement Document (BRD)
## CJS Designs — AI-Powered WhatsApp Order Management System

> Updated: 30 March 2026 — reflects the live deployed system.

---

### 1. Executive Summary

CJS Designs is a machine embroidery business operated by **Siny** (proprietor).
The system automates the complete order lifecycle — from WhatsApp message intake
through production scheduling, cost estimation, invoicing, and daily business briefings —
using a multi-agent AI framework. Siny interacts exclusively via WhatsApp; no separate
application, portal, or training is required.

---

### 2. Business Objectives

| Objective | Status |
|---|---|
| Automate order intake from WhatsApp text/voice | ✅ Live |
| Calculate stitching costs and machine timelines automatically | ✅ Live |
| Schedule production across two machines with holiday/weekend awareness | ✅ Live |
| Provide a daily morning briefing with tasks, deadlines, and reminders | ✅ Live |
| Track pending invoices and aging payments | ✅ Live (stub — full ledger pending) |
| Generate Instagram-ready content for completed orders | 🚧 Stub (fal.ai integration pending) |
| Maintain a persistent customer and order database | ✅ Live (Google Sheets) |

---

### 3. Stakeholders

| Stakeholder | Role |
|---|---|
| **Siny** | Proprietor — primary user, interacts via WhatsApp |
| **Customers** | End consumers — receive estimates/confirmation indirectly through Siny |

---

### 4. Business Constants

| Parameter | Value |
|---|---|
| Machines | 2: Ricoma, Aakruthi |
| Machine speed | 650 stitches/minute (SPM) |
| Working hours/day | 6 hours |
| Off days | Sundays + holidays (configurable in Holidays sheet tab) |
| Base billing rate | Dynamic from Config tab (default: Rs 10 per 1,000 stitches) |
| Hourly labor rate | Dynamic from Config tab (default: Rs 100/hr) |
| GST rate | Dynamic from Config tab (default: 18%) |

---

### 5. Functional Requirements

#### FR-1: Order Intake
- Accept order details via WhatsApp text, forwarded messages, or WhatsApp Flow form
- **Immediate Acknowledgment:** Instantly notify Boss ("Working on it... 🔄") upon message receipt to manage perceived latency
- Extract / Accept: Customer name, Fabric type, Embroidery type, Stitch count, Hours required (labor), Quantity, Delivery date
- If any required field is missing, ask Siny for clarification and retain partial state
- Detect and warn about duplicate orders (same customer + same specs within 24 hours)

#### FR-2: Production Scheduling
- Read current machine queue from Google Sheets (`Orders` tab) (orders not yet completed)
- Calculate working days needed: `ceil((stitches / 650 SPM / 60) / 6 hours)`
- Assign the machine that becomes free soonest (Ricoma or Aakruthi)
- Skip Sundays and holidays when counting working days

#### FR-3: Cost Estimation
- Dynamically calculate order cost using parameters from the `Config` tab:
  - $\text{Stitching Cost} = \left(\frac{\text{Stitch Count}}{1000}\right) \times \text{Cost per 1000 Stitches}$ (e.g. Rs 10 / 1k st)
  - $\text{Labor Cost} = \text{Hours Required} \times \text{Hourly Labor Rate}$ (e.g. Rs 100 / hr)
  - $\text{Subtotal} = \text{Stitching Cost} + \text{Labor Cost}$
  - $\text{GST Amount} = \text{Subtotal} \times \left(\frac{\text{GST Rate Percent}}{100}\right)$ (e.g. 18%)
  - $\text{Total Cost} = \text{Subtotal} + \text{GST Amount}$
- Set invoice status to "Estimated" upon calculation and record full itemized math in Column L (Reasoning Log)

#### FR-4: Daily Briefing
- Trigger automatically at **6:00 AM Indian Standard Time (IST)** every working day
- Summarise: orders due today, pending invoices older than 7 days, today's holiday status,
  upcoming holidays in the next 7 days, and any active reminders
- Also available on-demand when Siny asks ("what are my tasks today?")

#### FR-5: Invoice & Payment Tracking
- Track payment status per order: pending → Estimated → invoiced → Completed
- Allow Siny to mark an order as invoiced via WhatsApp ("mark CJS-XXXX as invoiced")
- Synchronize completed and invoiced orders with the shared `Sales_Ledger`
- Notify Siny of order-ready status with payment amount due

#### FR-6: Override Capabilities
- Siny can manually override AI decisions at any point via WhatsApp:
  - "change delivery date to 2026-04-10" → writes to Column M
  - "change cost to 500" → writes to Column N
  - "change machine to Ricoma" → writes to Column O
- All overrides are logged in the order's reasoning history (Column L) with timestamps

#### FR-7: Decision Explanations
- On request ("why did you schedule it on 2026-04-10?"), retrieve the reasoning from Column L
- Summarise in plain language: machine availability, holiday clashes, costing breakdown

#### FR-8: Social Media Marketing (Planned)
- Generate social media promotion assets for completed orders using fal.ai
- Create high-quality product images and video reels showcasing the embroidery work
- Suggest engaging captions and hashtags tailored for Instagram/WhatsApp Business

#### FR-9: Guided Hierarchical Menu & Form-Driven Operations
- **Main Menu Trigger:** Responds to `"Hi"`, `"Hello"`, `"Menu"`, or `"Help"` with a structured, numbered main menu:
  - `1`: New Order Form (Launches interactive WhatsApp Flow form with Fabric/Style dropdowns, Stitch count, and Hours required)
  - `2`: Adjust Existing Order (Opens Sub-Menu 2)
  - `3`: Invoicing & Billing (Opens Sub-Menu 3)
  - `4`: Daily Tasks & Morning Briefing
  - `5`: Vendors & Expenses (Opens Sub-Menu 5)
- **Sub-Menus:** Provides structured numeric sub-options (`21`, `22`, `23`, `31`, `32`, `33`, `34`, `51`, `52`) and `0` to return to the Main Menu.
- **Form-Based & Dropdown Inputs:** Minimizes manual typing and enforces standardization by using WhatsApp Flows (with dropdowns for Fabric Type, Embroidery Style, Stitch Count, Hours Required, and DatePicker) and dynamic numbered lists of active orders for adjustments and billing.

---

### 6. Non-Functional Requirements

| Requirement | Implementation |
|---|---|
| **Availability** | Google Cloud Run — scales to zero when idle, auto-scales on demand |
| **Security** | `.env` and `credentials.json` excluded from git; Cloud Run uses IAM default auth |
| **Reliability** | Memory service retains partial state across multi-turn conversations |
| **Observability** | Each agent appends to `aggregated_reasoning` (audit log written to Column L) |
| **Extensibility** | Standardised agent template + `final_reply` contract for new agents |
| **CI/CD** | Cloud Build Trigger auto-deploys on `git push` to `main` |
| **Schema Integrity** | Strict preservation of column ordering and headers across all shared tabs |

---

### 7. Google Sheets as Database (Shared with CJS Accountant)

Siny's Google Sheet serves as the shared persistent data store for both the AI Order Manager Agent and CJS Accountant. It contains ten named tabs:

| Tab | Purpose | Application Usage |
|---|---|---|
| **Orders** | Master orders queue and tracking ledger | AI Agent & Production |
| **Reminders** | Recurring or date-specific reminders for the daily briefing | AI Agent (Secretary) |
| **Customers** | Customer ID ↔ Name, Phone, and Address master directory | Shared (AI Agent + CJS Accountant) |
| **Holidays** | Off-days that the scheduler skips | AI Agent (Scheduler + Secretary) |
| **Config** | Global studio parameters (rate per 1k stitches, labor, GST rate) | Shared (AI Agent + CJS Accountant) |
| **Sales_Ledger** | Official accounting sales invoices and tax breakdown | Shared (AI Agent Invoicing + CJS Accountant) |
| **Expense_Ledger** | Operating expenses by category and payment method | Shared (CJS Accountant + AI Agent queries) |
| **Asset_Ledger** | Capital machinery registry and monthly depreciation | Shared (CJS Accountant) |
| **Capital_Ledger** | Owner equity, loans, and infusions | Shared (CJS Accountant) |
| **Vendors** | Suppliers directory (threads, backings, contact person) | Shared (CJS Accountant + AI Agent queries) |

