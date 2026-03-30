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
| Base billing rate | Rs 8 per 1,000 stitches |
| Custom pricing | Configurable per (embroidery type, fabric) combination in Costing tab |

---

### 5. Functional Requirements

#### FR-1: Order Intake
- Accept order details via WhatsApp text (or forwarded messages)
- **Immediate Acknowledgment:** Instantly notify Boss ("Working on it... 🔄") upon message receipt to manage perceived latency
- Extract: Customer name, Fabric type, Embroidery type, Stitch count, Quantity, Delivery date
- If any required field is missing, ask Siny for clarification and retain partial state
- Detect and warn about duplicate orders (same customer + same specs within 24 hours)

#### FR-2: Production Scheduling
- Read current machine queue from Google Sheets (orders not yet completed)
- Calculate working days needed: `ceil((stitches / 650 SPM / 60) / 6 hours)`
- Assign the machine that becomes free soonest (Ricoma or Aakruthi)
- Skip Sundays and holidays when counting working days

#### FR-3: Cost Estimation
- Look up pricing from the Costing tab (per embroidery-type + fabric combination)
- Fall back to base rate if no exact match: `(stitches / 1000) × Rs 8`
- Set invoice status to "Estimated" upon calculation

#### FR-4: Daily Briefing
- Trigger automatically at **6:00 AM Indian Standard Time (IST)** every working day
- Summarise: orders due today, pending invoices older than 7 days, today's holiday status,
  upcoming holidays in the next 7 days, and any active reminders
- Also available on-demand when Siny asks ("what are my tasks today?")

#### FR-5: Invoice & Payment Tracking
- Track payment status per order: pending → Estimated → invoiced → Completed
- Allow Siny to mark an order as invoiced via WhatsApp ("mark CJS-XXXX as invoiced")
- Notify Siny of order-ready status with payment amount due

#### FR-6: Database Operations (Direct Commands)
Siny can issue natural language commands that execute directly:
- `"mark CJS-XXXX as invoiced"` → updates status in Sheets
- `"change delivery date on CJS-XXXX to 10-April"` → field override
- `"explain reasoning for CJS-XXXX"` → returns agent decision log (Column L)
- `"who owes money?"` → returns pending payment report

#### FR-7: Social Media Content (Planned)
- Triggered when Siny uploads finished product photos
- Generate Instagram-ready caption with order context and hashtags
- Integration with fal.ai for video/image enhancement

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

---

### 7. Google Sheets as Database

Siny's Google Sheet is the sole persistent data store. It contains five named tabs:

| Tab | Purpose |
|---|---|
| **Sheet1** | All orders (master ledger) |
| **Holidays** | Off-days that the scheduler skips |
| **Reminders** | Recurring or date-specific reminders for the daily briefing |
| **Costing** | Custom pricing rules per embroidery/fabric combination |
| **Customers** | Customer ID ↔ Name mapping |
