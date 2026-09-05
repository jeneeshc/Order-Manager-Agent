# Solution Requirement Document (SRD)
## CJS Designs — AI-Powered WhatsApp Order Management System

> Updated: 30 March 2026 — reflects the live deployed system.

---

### 1. System Overview

A multi-agent AI system deployed on **Google Cloud Run** that intercepts WhatsApp messages
from Siny, orchestrates a network of specialised AI agents via **LangGraph**, and writes
results back to **Google Sheets**. Siny's only interface is WhatsApp.

The Supervisor agent (Agent 0) acts as the LangGraph router — it analyses each message and
state, decides which worker agent runs next, and synthesises the final WhatsApp reply.

---

### 2. Technology Stack

| Layer | Technology | Details |
|---|---|---|
| Language | Python 3.11 | |
| Web framework | FastAPI + Uvicorn | ASGI, Cloud Run entrypoint |
| Agent orchestration | LangGraph | Supervisor-led loopback state-machine graph |
| LLM framework | LangChain (`langchain-google-genai`) | |
| LLM model | `gemini-flash-latest` | Google Gemini, used by all LLM agents |
| Structured output | Pydantic v2 | `with_structured_output()` for deterministic extraction |
| Database | Google Sheets v4 API | `googleapiclient` via service account / IAM |
| WhatsApp | Meta Business Cloud API v22.0 | Webhook POST handler |
| Scheduler | APScheduler (`AsyncIOScheduler`) | In-process cron, 6:00 AM IST daily |
| Session memory | MemoryService | Key-value store (phone → AgentState) |
| Container | Docker (`python:3.11-slim`) | |
| Cloud | Google Cloud Run | Serverless, scales to zero |
| CI/CD | Cloud Build Triggers | Auto-deploy on `git push` to `main` |
| Media (planned) | fal.ai | Social media image/video generation |

---

### 3. Agent Architecture

#### Orchestration Model

LangGraph compiles the agents into a **loopback graph**:
- Entry point: Supervisor
- Every worker has a fixed edge back to Supervisor
- Supervisor uses `SupervisorOutput` (structured LLM output) to set `next_step`
- Graph terminates when Supervisor sets `next_step = "END"`

#### Agent Registry

| # | Agent | File | Model | Role |
|---|---|---|---|---|
| 0 | Supervisor | `agent_0_supervisor.py` | Gemini Flash, temp=0 | Router + final synthesiser |
| 1 | Collector | `agent_1_collector.py` | Gemini Flash, temp=0 | Intent + field extraction |
| 2 | Scheduler | `agent_2_scheduler.py` | — (pure math) | Production date + machine assignment |
| 3 | Estimator | `agent_3_estimator.py` | — (pure math) | Cost calculation |
| 4 | Social Media | `agent_4_social_media.py` | — (stub) | Instagram caption (fal.ai pending) |
| 5 | Invoicing | `agent_5_invoicing.py` | — (stub) | Payment reminders (full ledger pending) |
| 6 | Secretary | `agent_6_secretary.py` | Gemini Flash, temp=0.1 | Daily briefing |

#### `final_reply` Output Contract

Every agent must follow one of two patterns:

**Pattern A — Self-contained query:**
```python
state.final_reply = "formatted WhatsApp message"
# Supervisor sends this verbatim at END — no re-synthesis, no extra LLM call
```

**Pattern B — Intermediate pipeline step:**
```python
state.aggregated_reasoning += "[AgentName]: what was done"
# Supervisor synthesises a single reply from all reasoning at END
```

Agents **must never** set `state.raw_message` directly — that is Supervisor-only.
See `docs/AGENT_DEVELOPMENT.md` for the complete guide and template.

---

### 4. Agent Detail Specifications

#### Agent 0 — Supervisor (`agent_0_supervisor.py`)

- **Model:** `gemini-flash-latest`, temperature=0
- **Structured output:** `SupervisorOutput` with `next_step: Literal[...]` and `reasoning: str`
- **Routing rules (enforced via prompt):**
  1. `is_missing_info=True` → route to `collector`
  2. Fresh order message → route to `collector` first
  3. `is_secretary_query=True` → route to `secretary`
  4. **`state.final_reply` is set → route to `END` immediately (priority)**
  5. After collector (all info present) → `scheduler` → `estimator` → `END`
  6. Simple query already resolved → `END`
- **At END:** If `state.final_reply` is set → use verbatim. Else → LLM synthesis from reasoning.

#### Agent 1 — Collector (`agent_1_collector.py`)

- **Model:** `gemini-flash-latest`, temperature=0
- **Extraction model:** `OrderExtractionModel` (typed Pydantic model)
- **Deterministic Menu & Form Interceptor (Priority 0 — Zero LLM Latency):**
  1. If message is greeting (`"hi"`, `"hello"`, `"menu"`, `"help"`, `"0"`) → sets `final_reply` to Main Menu (`1` to `5`); sets `state.active_menu = "MAIN"`.
  2. If `state.active_menu == "MAIN"`:
     - `"1"`: Sets `state.send_order_form = True` to launch native WhatsApp Flow form with dropdowns (Cotton/Silk/Net/Velvet, Floral/Neckline/Border, etc.) and DatePicker.
     - `"2"`: Sets `final_reply` to Sub-Menu 2 (Adjust Order); sets `state.active_menu = "ADJUST"`.
     - `"3"`: Sets `final_reply` to Sub-Menu 3 (Invoicing & Billing); sets `state.active_menu = "INVOICING"`.
     - `"4"`: Sets `is_secretary_query = True` for instant daily tasks brief.
     - `"5"`: Sets `final_reply` to Sub-Menu 5 (Vendors & Expenses); sets `state.active_menu = "VENDORS"`.
  3. Direct Sub-Menu Codes:
     - `"21"`, `"22"`, `"23"`, `"24"`: Adjust delivery date, machine, cost, or reasoning log. Presents dynamic choices of active orders.
     - `"31"`, `"32"`, `"33"`, `"34"`: Pending report, mark invoiced, mark completed, or overdue accounts report.
     - `"51"`, `"52"`: View vendors directory or recent expenses.
- **LLM Intercept chain (Freeform text fallback):**
  1. `mark_as_invoiced` + order ID → status update + `final_reply`
  2. `explain_reasoning` + order ID → explanation request + `final_reply`
  3. `is_field_override` + all fields → field override + `final_reply`
  4. `is_payment_query` → payment query flag
  5. `is_secretary_query` → secretary flag
- **Order hydration:** If `referenced_order_id` present, fetches from Sheets and merges with new extractions
- **Missing info:** Required fields: `customer_name`, `fabric_type`, `embroidery_type`, `stitch_count`
- **Duplicate detection:** Checks last 24 hours for identical (customer, phone, fabric, style, stitches) before allowing new order

#### Agent 2 — Scheduler (`agent_2_scheduler.py`)

- **Pure Python (no LLM)**
- **Machine speed:** 650 SPM
- **Working hours/day:** 6
- **Formula:** `days = max(1, round((stitches / 650 / 60) / 6))`
- **Machine selection:** Reads all non-completed/non-invoiced orders from `'Orders'!A:K`; picks earliest free date
- **Holiday skipping:** Reads `'Holidays'!A:B` tab; also skips Sundays
- **Outputs:** `state.machine_assigned`, `state.estimated_completion_date`

#### Agent 3 — Estimator (`agent_3_estimator.py`)

- **Pure Python (no LLM)**
- **Cost calculation:** Direct dynamic multi-factor formula sourced from `'Config'!A:C`:
  - `base_rate = [Cost per 1000 Stitches]` (default: 10.0)
  - `hourly_rate = [Hourly Labor Rate]` (default: 100.0)
  - `gst_rate = [GST Rate Percent]` (default: 18.0)
- **Formula:**
  - $\text{stitch\_cost} = (\text{stitches} / 1000) \times \text{base\_rate}$
  - $\text{labor\_cost} = \text{labor\_hours} \times \text{hourly\_rate}$
  - $\text{subtotal} = \text{stitch\_cost} + \text{labor\_cost}$
  - $\text{gst\_amount} = \text{subtotal} \times (\text{gst\_rate} / 100)$
  - $\text{total\_cost} = \text{subtotal} + \text{gst\_amount}$
- **Outputs:** `state.total_cost_rs`, `state.base_cost_rs`, `state.gst_amount_rs`, `state.invoice_status = "Estimated"`

#### Agent 4 — Social Media (`agent_4_social_media.py`)

- **Status:** Stub — output contract in place, fal.ai integration not yet built
- **Sets:** `state.final_reply` with Instagram caption template
- **Planned:** fal.ai video/image synthesis from product photo uploads

#### Agent 5 — Invoicing (`agent_5_invoicing.py`)

- **Role:** Payment reminders, pending invoicing queries, and synchronizing with `Sales_Ledger`
- **Current:** Runs if `invoice_status == "pending"`, sets `state.invoice_status = "invoiced"`, sets `state.final_reply` with pickup reminder
- **Ledger Integration:** Syncs with `'Sales_Ledger'!A:K` (shared with CJS Accountant) for invoice records, gross totals, and GST calculation.

#### Agent 6 — Secretary (`agent_6_secretary.py`)

- **Model:** `gemini-flash-latest`, temperature=0.1
- **Data sources (from Google Sheets):**
  - Orders due today (Col I == today in `Orders`)
  - Pending invoices >7 days (not invoiced/completed in `Orders`)
  - Holiday status (today) and upcoming holidays (next 7 days from `Holidays`)
  - Reminders from `'Reminders'!A:C` tab (date-based or "Nth of each month")
  - Optional financial context from `'Sales_Ledger'` / `'Expense_Ledger'`
- **Prompt rules:** Explicitly says "TODAY not tomorrow"; uses WhatsApp formatting (emojis, `*bold*`)
- **Scheduled:** 6:00 AM IST daily via APScheduler (bypasses LangGraph — calls directly)
- **On-demand:** Triggered by Supervisor when `is_secretary_query=True`
- **Sets:** `state.final_reply = summary`

---

### 5. Google Sheets Schema (Shared with CJS Accountant)

#### 1. Orders Tab — `Orders!A:O`

| Col | Field | Type | Notes |
|---|---|---|---|
| A | Order Date | String | `YYYY-MM-DD HH:MM` |
| B | Order ID | String | `CJS-XXXXXX` |
| C | Customer ID | String | FK → Customers tab |
| D | Phone | String | Sender WhatsApp number |
| E | Material | String | Fabric type |
| F | Embroidery Type | String | Style |
| G | Stitch Count | Integer | Total stitches |
| H | Machine | String | Ricoma / Aakruthi |
| I | Estimated Delivery Date | String | `YYYY-MM-DD` |
| J | Estimated Cost | String | `Rs X` |
| K | Payment Status | String | pending / Estimated / invoiced / Completed |
| L | Reasoning Log | String | Appended agent audit trail |
| M | Override Delivery Date | String | Manual override date |
| N | Override Cost (Rs) | String | Manual override cost |
| O | Override Machine | String | Manual override machine |

#### 2. Config Tab — `Config!A:C`

| Col | Field | Example | Notes |
|---|---|---|---|
| A | Variable Name | `Cost per 1000 Stitches` | Dynamic system configuration parameter |
| B | Value | `10` | Parameter value (numeric or string) |
| C | Last Updated | `2026-09-02T12:00:09.318Z` | ISO Timestamp |

#### 3. Sales_Ledger Tab — `Sales_Ledger!A:K`

| Col | Field | Format / Example | Notes |
|---|---|---|---|
| A | Date | `YYYY-MM-DD` | Invoice / Transaction Date |
| B | Invoice ID | `CJS-2026-0001` | Formatted invoice sequence |
| C | Customer | `Saniya Boutique` | Customer Name |
| D | Service Type | `Machine Embroidery` | Service Category |
| E | Total Stitches | `120000` | Stitch count |
| F | Labor Hrs | `10` | Hours expended |
| G | Margin % | `25` | Markup percentage |
| H | Net Price | `2450` | Base revenue (excl. tax) |
| I | GST | `441` | GST tax component |
| J | Courier | `150` | Shipping / courier cost |
| K | Gross Total | `3041` | Net + GST + Courier |

#### 4. Expense_Ledger Tab — `Expense_Ledger!A:E`

| Col | Field | Example |
|---|---|---|
| A | Date | `YYYY-MM-DD` |
| B | Expense Category | `Cost of Thread` |
| C | Description | `Naren - Thread buying` |
| D | Amount | `840` |
| E | Payment Method | `UPI` / `Cash` / `Bank` |

#### 5. Asset_Ledger Tab — `Asset_Ledger!A:E`

| Col | Field | Example |
|---|---|---|
| A | Asset Name | `Barudan 2-Head Commercial Embroidery Machine` |
| B | Purchase Date | `2025-01-10` |
| C | Purchase Price | `650000` |
| D | Useful Life (Months) | `60` |
| E | Monthly Depreciation | `10833.33` |

#### 6. Capital_Ledger Tab — `Capital_Ledger!A:D`

| Col | Field | Example |
|---|---|---|
| A | Date | `2025-01-05` |
| B | Transaction Type | `Investment` / `Loan` |
| C | Description | `Initial Owner Equity Contribution` |
| D | Amount | `500000` |

#### 7. Vendors Tab — `Vendors!A:F`

| Col | Field | Notes |
|---|---|---|
| A | Vendor ID | `VND-001` |
| B | Name | Vendor / Firm Name |
| C | Category | Category (e.g. `Thread purchase`) |
| D | Contact Person | Name of contact person |
| E | Phone | Phone number |
| F | Address | Location / Address |

#### 8. Customers Tab — `Customers!A:D`

| Col | Field | Notes |
|---|---|---|
| A | Customer ID | Unique numeric ID (`1001`, `1002`) |
| B | Name | Customer full name |
| C | Phone | WhatsApp / contact phone |
| D | Address | Customer delivery address |

#### 9. Holidays Tab — `Holidays!A:B`

| Col | Field | Format |
|---|---|---|
| A | Date | `DD-Month-YYYY` e.g. `2-April-2026` |
| B | Description | Event description |

#### 10. Reminders Tab — `Reminders!A:C`

| Col | Field | Notes |
|---|---|---|
| A | No | Numeric index |
| B | When | Date string or `"11th of each month"` |
| C | What to remind | Reminder message text |

---

### 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health ping (returns version) |
| `GET` | `/health` | Health check |
| `GET` | `/webhook` | Meta webhook subscription verification |
| `POST` | `/webhook` | Incoming WhatsApp message handler (sends immediate "Working on it... 🔄" acknowledgment) |
| `GET` | `/trigger-daily-brief` | Manually trigger the morning briefing |

---

### 7. Session Memory

`MemoryService` (`src/services/memory.py`) maintains multi-turn conversation state
keyed by sender phone number. On resume:

```python
state.raw_message     = new_message        # Replace with incoming text
state.is_missing_info = False              # Force fresh Supervisor evaluation
state.next_step       = "supervisor"
```

State is cleared on successful completion (`memory.clear_state()`).

---

### 8. Security

| Concern | Implementation |
|---|---|
| Credentials | `credentials.json` in `.gitignore` and `.gcloudignore` |
| Cloud Run auth | Implicit IAM — no credentials file needed in production |
| API keys | Stored in GCP Secret Manager, injected as env vars |
| WhatsApp webhook | Verified by `WHATSAPP_VERIFY_TOKEN` on GET handshake |
| Admin errors | Error alerts sent only to `Siny's number` / `ADMIN_PHONE_NUMBER` |

---

### 9. Deployment

**Container:** `python:3.11-slim` via Dockerfile
**Runtime:** Cloud Run (serverless, scales to zero)
**CI/CD:** Cloud Build Trigger → auto-build and deploy on `git push` to `main`
**Region:** Recommended `asia-south1` (Mumbai) for lowest latency from India

---

### 10. Development Conventions

- All new agents must follow the `final_reply` contract (see `docs/AGENT_DEVELOPMENT.md`)
- Use `src/agents/agent_template.py` as the starting point for any new agent
- Register new agents in three places: `main_graph.py`, `SupervisorOutput` Literal, Supervisor routing prompt
- Never set `state.raw_message` inside an agent — Supervisor-only
- Always append to `state.aggregated_reasoning` for audit trail, regardless of pattern A or B
