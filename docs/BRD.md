# Business Requirement Document (BRD)
## CJS Designs — AI-Powered WhatsApp Order Management System

> Updated: September 2026 — reflects the updated system architecture and business logic overhaul.

---

### 1. Executive Summary

CJS Designs is an embroidery and custom design business operated by **Siny** (proprietor).
The system functions as an AI-powered Executive Secretary to assist Siny in managing the complete operational lifecycle:
- Creating and tracking new orders via interactive WhatsApp forms.
- Checking machine availability and scheduling production based on expected delivery dates.
- Providing deterministic, multi-factor cost estimations.
- Delivering daily morning briefings with daily work allocations, pending orders awaiting invoicing, pending invoices requiring customer follow-up, upcoming studio holidays, and reminders.
- Interacting seamlessly with a centralized Google Sheet shared with **CJS Accountant** (a dedicated accounting application).

Siny interacts exclusively via WhatsApp; no separate portal, mobile app, or manual data entry is required.

---

### 2. Business Objectives

| Objective | Description |
|---|---|
| **Automate Order Intake** | Capture standardized order details using WhatsApp interactive forms (dropdowns/fields) directly from Siny. |
| **Intelligent Machine Allocation** | Route orders automatically to the appropriate machine based on design category/size templates, or treat as pure software design when no machine is needed. |
| **Accurate Capacity & Delivery Scheduling** | Track machine running hours vs. working day capacity to verify machine availability against the customer's expected delivery date, skipping Sundays and studio holidays. |
| **Strict 4-Factor Cost Estimation** | Calculate precise order estimates dynamically using Config parameters (Stitch count, Labor hours, Profit margin, and GST). |
| **Automated Daily Briefing** | Run a reliable scheduled morning briefing at 6:00 AM IST via GCP Cloud Scheduler summarizing daily work, pending invoicing, invoice follow-ups, and holidays. |
| **Operational Billing Summaries** | Provide Siny with actionable operational summaries for billing and payment follow-ups, delegating full ledger entry and tax invoicing to CJS Accountant. |
| **Persistent Shared Data Store** | Maintain real-time synchronization with Google Sheets shared between the AI Order Manager Agent and CJS Accountant. |

---

### 3. Stakeholders

| Stakeholder | Role | Interaction Model |
|---|---|---|
| **Siny** | Proprietor / Business Operator | Sole direct user of the AI Agent. Interacts exclusively via WhatsApp text, menus, and forms. |
| **Customers** | End Clients / Boutiques | Interact solely with Siny; receive quotes, delivery commitments, and invoices generated through Siny. |
| **CJS Accountant** | Dedicated Accounting Application | Downstream accounting system sharing the same Google Sheet database for invoice generation, payments, and financial ledgers. |

---

### 4. Business Constants & Configuration

System constants and rates are dynamically maintained in the **`Config`** and **`Description_Templates`** tabs of the shared Google Sheet:

#### 4.1 Global Config (`Config` Tab)
| Parameter Name | Description | Default / Example Value |
|---|---|---|
| `Cost per 1000 Stitches` | Base stitching rate per 1,000 stitches | Rs 10.0 |
| `Hourly Labor Rate` | Siny's hourly labor cost for software design / prep | Rs 100.0 |
| `Profit Margin Percent` | Business markup applied on base production cost | 20% |
| `GST Rate Percent` | Applicable Goods and Services Tax percentage | 18% |
| `Machine Speed (SPM)` | Stitches per minute for embroidery machines | 650 SPM |
| `Daily Working Hours` | Maximum active machine running time per working day | 6 hours / day |
| `Off Days` | Non-working days | Sundays + dates in `Holidays` tab |

#### 4.2 Machine & Template Allocation (`Description_Templates` Tab)
Embroidery orders are allocated to specific hardware or classified as software design based on template configurations:
- **Large Items** (e.g., Saree, Kurti, Salwar, Gown): Allocated to **Ricoma** (multi-needle / wide frame).
- **Small Items** (e.g., Logo, Baptism set, Badge, Monogram, Name patch): Allocated to **Aakruthi** (single/compact frame).
- **Embroidery Design**: Software-only digitizing and design creation. Requires **no machine** and **no stitch count**; tracked purely by labor hours.
- **Default Labor Hours**: Each template provides a pre-populated default labor duration in Column E (editable during order intake).

---

### 5. Functional Requirements

#### FR-1: Order Intake, Streamlined Dropdowns & Master Data Management
- **Streamlined Form-Based Intake:** To prevent mobile form clutter, ambiguity, and latency, order intake is conducted via a clean WhatsApp Flow form containing only essential dropdowns and inputs:
  1. **Customer Name** *(Required, Dropdown)*: Pre-populated with active registered customers from the `Customers` tab.
  2. **Order Type** *(Required, Dropdown)*: Pre-populated with core service types (`Machine Embroidery`, `Embroidery Designing`).
  3. **Template Name** *(Required, Dropdown)*: Pre-populated with active templates from `Description_Templates` (showing template name and assigned machine).
  4. **Quantity** *(Required, Integer)*: Number of units (default: 1).
  5. **Expected Delivery Date** *(Required, DatePicker)*: Customer's target delivery date.
  6. **Stitch Count** *(Optional, Integer)*: Stitch count if known upfront.
  7. **Labor Hours** *(Optional, Decimal)*: Custom labor hours override (defaults to template's standard duration).

- **Dedicated Master Data Management via Main Menu:**
  To keep the intake form fast and uncluttered, adding new master records is handled via conversational menu actions:
  - **6️⃣ Add New Customer (Code 6 / 61):** Prompts Siny for customer name, phone, and location, then saves the new client to the `Customers` tab with a generated `Customer ID`.
  - **7️⃣ Add New Template (Code 7 / 71):** Prompts Siny for template name, machine (`Ricoma`, `Aakruthi`, `None`), default labor hours, and default stitches, saving to `Description_Templates`.
  - **8️⃣ Add New Order Type (Code 8 / 81):** Prompts Siny for new service categories and registers them in configuration.
- **Immediate Acknowledgment:** Instantly acknowledges message receipt to eliminate perceived latency.
- **Duplicate Protection:** Warns if an identical order (same customer, template, and delivery date) was created within the last 24 hours.

#### FR-2: Production Scheduling & Capacity Validation
- **Machine Running Hours vs. Labor Hours:**
  - **Machine Running Time:** Decides machine capacity and backlog. Calculated as:
    $$\text{Machine Hours} = \frac{\text{Stitch Count} \times \text{Quantity}}{650 \text{ SPM} \times 60 \text{ min}}$$
    $$\text{Working Days Required} = \left\lceil \frac{\text{Machine Hours}}{6 \text{ hours/day}} \right\rceil$$
  - **Labor Hours:** Represents Siny's human effort spent on design/digitizing; does **not** block the embroidery machines. Used for costing.
- **Machine Assignment Rules:**
  - Sourced directly from `Description_Templates` Column D based on the selected Template Name.
  - If Order Type is `Embroidery design`: Assigned machine is `None` (no machine scheduled).
  - If Order Type is `Machine Embroidery`: Assigned to `Ricoma` or `Aakruthi` as specified by the template.
- **Timeline & Delivery Date Check:**
  - Evaluates the current queue of the assigned machine from the `Orders` sheet tab (orders not yet completed).
  - Starting from the earliest date the machine becomes available (or today), projects forward by `Working Days Required`, skipping **Sundays** and **Holidays** listed in the `Holidays` tab.
  - Compares the calculated completion date against the customer's **Expected Delivery Date**:
    - If achievable: Confirms the schedule.
    - If expected delivery date falls before achievable completion date: Flags a schedule conflict warning to Siny with the earliest possible completion date.

#### FR-3: Strict 4-Factor Cost Estimation
All order cost calculations strictly adhere to the following dynamic multi-factor formula, reading rates from the `Config` tab:

1. **Stitching Cost:**
   $$\text{Stitching Cost} = \begin{cases} 
   \left(\dfrac{\text{Stitch Count} \times \text{Quantity}}{1000}\right) \times \text{Cost per 1000 Stitches}, & \text{if Machine Embroidery} \\ 
   0, & \text{if Embroidery design} 
   \end{cases}$$

2. **Labor Cost:**
   $$\text{Labor Cost} = \text{Labor Hours} \times \text{Hourly Labor Rate}$$

3. **Base Production Cost:**
   $$\text{Base Cost} = \text{Stitching Cost} + \text{Labor Cost}$$

4. **Profit Margin:**
   $$\text{Profit Amount} = \text{Base Cost} \times \left(\frac{\text{Profit Margin Percent}}{100}\right)$$

5. **Subtotal (Net Price):**
   $$\text{Subtotal} = \text{Base Cost} + \text{Profit Amount}$$

6. **GST (Tax Component):**
   $$\text{GST Amount} = \text{Subtotal} \times \left(\frac{\text{GST Rate Percent}}{100}\right)$$

7. **Total Estimated Cost:**
   $$\text{Total Cost} = \text{Subtotal} + \text{GST Amount}$$

- Set initial order status to `"Estimated"` and append the itemized mathematical breakdown to Column L (Reasoning Log).

#### FR-4: Automated Daily Briefing (Cloud Scheduler)
- **Scheduling Architecture:** Google Cloud Run scales to zero when idle; therefore, daily briefing execution is triggered via an external **GCP Cloud Scheduler** cron job at **6:00 AM IST (00:30 UTC)** daily, sending an authenticated HTTP request to `/trigger-daily-brief`.
- **Briefing Scope:**
  1. **Work Assigned for the Day:** Orders scheduled for production or due today on Ricoma and Aakruthi, plus active software design tasks.
  2. **Pending Orders for Invoicing:** Completed production orders awaiting invoice creation in CJS Accountant.
  3. **Pending Invoices for Customer Follow-Ups:** Invoiced orders with pending/unpaid balances (>7 days old) requiring customer payment follow-ups.
  4. **Holiday Status:** Alerts if today is a studio holiday, along with upcoming holidays in the next 7 days.
  5. **Reminders:** Scheduled notes and tasks from the `Reminders` tab.
- **On-Demand Access:** Siny can request the briefing at any time via WhatsApp ("What are my tasks today?", "Daily summary").

#### FR-5: Invoicing & Payment Tracking (Secretary Summary)
- **Application Boundary:** Formal invoice creation, PDF generation, tax ledgers (`Sales_Ledger`), and payment reconciliation are handled by the **CJS Accountant** application.
- **AI Agent Role:** Functions strictly as Siny's executive assistant providing operational summaries:
  - List orders whose production is completed but not yet billed ("Pending Invoicing").
  - List customers with overdue balances for payment follow-up.
  - Allow Siny to record quick status transitions (e.g. marking an order as `"invoiced"` or `"Completed"` in the `Orders` tab).
- **Status Progression:** `pending` $\rightarrow$ `Estimated` $\rightarrow$ `invoiced` $\rightarrow$ `Completed`.

#### FR-6: Manual Overrides
- Siny retains full authority to override AI calculations and schedules via WhatsApp text:
  - Change delivery date &rarr; updates Column M (`Override Delivery Date`).
  - Change cost &rarr; updates Column N (`Override Cost`).
  - Change assigned machine &rarr; updates Column O (`Override Machine`).
  - Change labor hours &rarr; triggers cost recalculation.
- All manual overrides are timestamped and logged in Column L (`Reasoning Log`).

#### FR-7: Decision Auditing & Reasoning Explanations
- When asked ("Why was Ricoma chosen?", "Why is the delivery date 2026-09-15?", "Break down the cost"), the agent retrieves the audit trail from Column L and explains the machine allocation, holiday skips, backlog queue, and 4-factor costing math in clear language.

#### FR-8: Guided Menu & Form Navigation
- Responds to `"Hi"`, `"Hello"`, `"Menu"`, or `"Help"` with a structured main menu:
  - `1`: **New Order Form** (Triggers WhatsApp Flow with Order Type, Template dropdown, Quantity, Delivery Date, Stitch count, editable Labor hours).
  - `2`: **Adjust Existing Order** (Delivery Date, Machine re-assignment, Cost override, or Reasoning log).
  - `3`: **Invoicing & Billing Summary** (Pending for invoicing, pending payment follow-ups, mark invoiced/paid).
  - `4`: **Daily Tasks & Briefing** (Today's machine schedule, tasks, holidays, and reminders).
  - `5`: **Vendors & Expenses Summary** (Directory and recent expense logs).
- Quick exit (`"0"` or `"Cancel"`) from any sub-state.

---

### 6. Non-Functional Requirements

| Requirement | Implementation Specification |
|---|---|
| **Availability & Scalability** | Hosted on **Google Cloud Run** with min instances = 0; scales automatically on incoming webhooks. |
| **Reliable Scheduled Tasks** | Daily briefing triggered by **GCP Cloud Scheduler**; resilient against container scale-to-zero. |
| **Data Integrity & Consistency** | Strict preservation of shared Google Sheet tab structures, column mappings, and data types shared with CJS Accountant. |
| **Security & Privacy** | WhatsApp webhook handshake authentication via verify token; service credentials managed securely; no git exposure. |
| **Auditability** | Full reasoning and calculation trail preserved in Column L of each order. |
| **Latency Management** | Immediate WhatsApp acknowledgment message ("Working on it... 🔄") dispatched prior to LLM/Sheet operations. |

---

### 7. Google Sheets Database Schema

The Google Sheet is shared between the **AI Order Manager Agent** and **CJS Accountant**.

#### 7.1 `Orders` Tab (`Orders!A:P`)
Master order queue and lifecycle ledger:

| Col | Header Name | Type | Notes |
|---|---|---|---|
| A | Order Date | String | `YYYY-MM-DD HH:MM` |
| B | Order ID | String | Unique identifier (e.g. `CJS-260901`) |
| C | Customer ID | String | FK &rarr; `Customers` tab |
| D | Customer Name | String | Denormalized customer name |
| E | Phone | String | WhatsApp phone number |
| F | Order Type | String | `Machine Embroidery` / `Embroidery design` |
| G | Template Name | String | Selected template from `Description_Templates` |
| H | Quantity | Integer | Unit quantity |
| I | Stitch Count | Integer | Total stitches (0 for Embroidery design) |
| J | Labor Hours | Decimal | Siny's prep/design hours |
| K | Machine | String | `Ricoma` / `Aakruthi` / `None` |
| L | Estimated Delivery Date | String | `YYYY-MM-DD` |
| M | Estimated Cost | String | `Rs X.XX` (Total cost from 4-factor formula) |
| N | Payment / Invoice Status| String | `pending` / `Estimated` / `invoiced` / `Completed` |
| O | Reasoning Log | String | Multi-agent execution and calculation audit log |
| P | Overrides | String | JSON / text log of manual overrides (Date, Cost, Machine) |

#### 7.2 `Description_Templates` Tab (`Description_Templates!A:E`)
Catalog of embroidery types, machine routing, and default labor times:

| Col | Header Name | Type | Description / Examples |
|---|---|---|---|
| A | Order Type | String | `Machine Embroidery` or `Embroidery design` |
| B | Category | String | Subcategory (e.g., `Garment`, `Badge`, `Digital Art`) |
| C | Template Name | String | Specific template (e.g., `Saree Border`, `Kurti Neck`, `Logo Pocket`, `Baptism Set`, `Vector Digitizing`) |
| D | Machine Allocation | String | `Ricoma` (large items), `Aakruthi` (small items), or `None` (Embroidery design) |
| E | Default Labor Hours | Decimal | Default preparation/software design hours (e.g., `1.5`, `0.5`, `3.0`) |

#### 7.3 `Config` Tab (`Config!A:C`)
Global pricing, production, and tax parameters:

| Col | Header Name | Example Variable | Example Value |
|---|---|---|---|
| A | Variable Name | `Cost per 1000 Stitches` | `10.0` |
| | | `Hourly Labor Rate` | `100.0` |
| | | `Profit Margin Percent` | `20.0` |
| | | `GST Rate Percent` | `18.0` |
| | | `Machine Speed SPM` | `650` |
| | | `Daily Working Hours` | `6.0` |
| B | Value | Parameter value | Numeric / string |
| C | Last Updated | Timestamp | ISO-8601 string |

#### 7.4 Supporting Tabs (Shared with CJS Accountant)
- **`Customers` (`Customers!A:D`):** Customer directory (`Customer ID`, `Name`, `Phone`, `Address`).
- **`Holidays` (`Holidays!A:B`):** Studio non-working days (`Date`, `Description`).
- **`Reminders` (`Reminders!A:C`):** Scheduled business reminders (`No`, `When`, `What to remind`).
- **`Sales_Ledger` (`Sales_Ledger!A:K`):** Formal invoices ledger maintained by CJS Accountant; read by Agent for billing follow-up summaries.
- **`Expense_Ledger` (`Expense_Ledger!A:E`):** Operating expense ledger; queried for vendor expense summaries.
- **`Vendors` (`Vendors!A:F`):** Supplier directory.
