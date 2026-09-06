# Solution Requirement Document (SRD)
## CJS Designs — AI-Powered WhatsApp Order Management System

> Updated: September 2026 — reflects the updated system architecture and business logic overhaul.

---

### 1. System Overview

A multi-agent AI system deployed on **Google Cloud Run** that intercepts WhatsApp interactions from **Siny** (sole direct user), coordinates worker agents via **LangGraph**, and maintains real-time bidirectional synchronization with **Google Sheets** (shared with **CJS Accountant**).

The Supervisor agent (Agent 0) acts as the central router and synthesis engine. Siny manages orders, reviews machine schedules, receives cost estimates, and checks daily business updates exclusively through WhatsApp messages and native WhatsApp Flow forms.

---

### 2. Technology Stack

| Layer | Technology | Details |
|---|---|---|
| **Language** | Python 3.11 | Modern async runtime |
| **Web Framework** | FastAPI + Uvicorn | ASGI server, webhook and trigger endpoints |
| **Agent Orchestration** | LangGraph | State-machine graph with Supervisor loopback routing |
| **LLM Framework** | LangChain (`langchain-google-genai`) | Integration layer for Gemini Flash |
| **LLM Model** | `gemini-flash-latest` | High-speed, low-latency reasoning |
| **Structured Output** | Pydantic v2 | Strict schema validation with `with_structured_output()` |
| **Database** | Google Sheets v4 API | `googleapiclient` via Service Account / Cloud IAM |
| **Messaging Channel** | Meta WhatsApp Business Cloud API v22.0 | Two-way webhooks, text, and interactive Flow forms |
| **Scheduled Jobs** | **Google Cloud Scheduler** (GCP) | External cron calling `/trigger-daily-brief` at 6:00 AM IST daily |
| **Session Memory** | `MemoryService` | Persistent key-value store (`phone` &rarr; `AgentState`) |
| **Container & Runtime** | Docker (`python:3.11-slim`) on Google Cloud Run | Serverless, auto-scales on demand, scales to zero when idle |
| **CI/CD** | Cloud Build Triggers | Continuous deployment on `git push` to `main` |

---

### 3. Agent Architecture

#### Orchestration Graph
LangGraph compiles worker agents into a supervisor-controlled state graph:
1. **Entry Point:** Supervisor (Agent 0).
2. **Deterministic Interceptors:** Fast-path menu, code handling, and form submission bypassing LLM inference.
3. **Pipeline Worker Flow (New Order):**
   $$\text{Collector (Agent 1)} \longrightarrow \text{Scheduler (Agent 2)} \longrightarrow \text{Estimator (Agent 3)} \longrightarrow \text{Supervisor (Agent 0)} \longrightarrow \text{END}$$
4. **Self-Contained Workers:**
   - Secretary (Agent 6) for daily briefings and task summaries.
   - Invoicing Worker (Agent 5) for billing summaries and status updates.
   - Supervisor passes `state.final_reply` straight to WhatsApp at `END` (no extra LLM synthesis).

#### Agent Registry

| # | Agent Name | Source File | Model / Engine | Core Responsibility |
|---|---|---|---|---|
| 0 | **Supervisor** | `src/agents/agent_0_supervisor.py` | `gemini-flash-latest` | State routing, guard rails, and final synthesis |
| 1 | **Collector** | `src/agents/agent_1_collector.py` | `gemini-flash-latest` + Pydantic | Form generation, input validation, template extraction |
| 2 | **Scheduler** | `src/agents/agent_2_scheduler.py` | Pure Python (Deterministic) | Machine allocation, running capacity, holiday skipping |
| 3 | **Estimator** | `src/agents/agent_3_estimator.py` | Pure Python (Deterministic) | Strict 4-factor cost estimation |
| 4 | **Social Media** | `src/agents/agent_4_social_media.py` | fal.ai (Planned stub) | Marketing content generation |
| 5 | **Invoicing** | `src/agents/agent_5_invoicing.py` | Pure Python (Deterministic) | Billing summaries (pending invoicing & follow-ups) |
| 6 | **Secretary** | `src/agents/agent_6_secretary.py` | `gemini-flash-latest` | Daily morning briefing and task overview |

---

### 4. Agent Detail Specifications

#### Agent 0 — Supervisor (`agent_0_supervisor.py`)
- **Role:** Central dispatcher and synthesizer.
- **Routing Rules:**
  1. `state.final_reply is not None` &rarr; Route immediately to `END`.
  2. `state.send_order_form == True` &rarr; Route immediately to `END` (triggers WhatsApp Flow).
  3. Form submitted / full order details present &rarr; Route `scheduler` &rarr; `estimator` &rarr; `END`.
  4. `state.is_secretary_query == True` &rarr; Route to `secretary`.
  5. `state.is_pending_invoicing_query` or payment query &rarr; Route to `invoicing`.
  6. Incomplete order details &rarr; Route to `collector`.

---

#### Agent 1 — Order Collector (`agent_1_collector.py`)
- **Extraction Model:** `OrderExtractionModel` (Pydantic v2):
  - `customer_name: Optional[str]` *(Required)*
  - `order_type: Optional[str]` *(Required: 'Machine Embroidery' or 'Embroidery design')*
  - `template_name: Optional[str]` *(Required: from Description_Templates Col C, with dynamic registration)*
  - `quantity: Optional[int] = 1` *(Required)*
  - `requested_delivery_date: Optional[str]` *(Required: YYYY-MM-DD)*
  - `stitch_count: Optional[int] = None` *(Optional; null for Embroidery design)*
  - `labor_hours: Optional[float] = None` *(Optional; pre-populated from Description_Templates Col E, editable)*
- **Removed Fields:** `fabric_type` and `embroidery_type` are completely removed; replaced by `order_type` and `template_name`.
- **Form Dispatcher & Auto-Registration Architecture:**
  - Emits native WhatsApp Flow payload containing:
    - **Customer Name:** Dropdown list of existing customers from `Customers!B:B` plus "+ New Customer" write-in option. When a new customer name is entered, `GoogleSheetsService.create_customer_if_not_exists()` generates a new `Customer ID` and persists the record immediately in the `Customers` tab.
    - **Order Type:** Dropdown from `Description_Templates!A:A` distinct values (`Machine Embroidery`, `Embroidery design`) with write-in capability for new service lines.
    - **Template Name:** Dependent dropdown filtered by chosen Order Type (`Description_Templates!C:C`), with "+ New Template" write-in option. When a new template name is provided, `GoogleSheetsService.create_template_if_not_exists()` registers the template with its allocated machine and default labor hours into `Description_Templates`.
    - **Quantity:** Numeric integer input (default 1).
    - **Expected Delivery Date:** DatePicker.
    - **Stitch Count:** Numeric input (disabled when Order Type is `Embroidery design`).
    - **Labor Hours:** Decimal input pre-populated with default from `Description_Templates` Col E, editable by Siny.
- **Fast Action Codes:**
  - `1`: Launch New Order Form.
  - `2` (`21`-`24`): Order Adjustments (Date, Machine, Cost, Reasoning).
  - `3` (`31`-`34`): Invoicing & Billing Summaries.
  - `4`: Instant Daily Briefing.
  - `5` (`51`-`52`): Vendors and Expenses summary.

---

#### Agent 2 — Production Scheduler (`agent_2_scheduler.py`)
- **Deterministic Math Engine (Zero LLM Latency):**
  - **Inputs:** `order_type`, `template_name`, `stitch_count`, `quantity`, `requested_delivery_date`.
- **Machine Allocation Logic:**
  - Reads `Description_Templates` Column D:
    - If `order_type == "Embroidery design"`: Sets `machine_assigned = "None"`. (No machine capacity consumed; design is executed in software).
    - If `order_type == "Machine Embroidery"`:
      - Looks up template in `Description_Templates`:
        - Large items (e.g. Saree, Kurti, Salwar) &rarr; **Ricoma**
        - Small items (e.g. Logo, Baptism, Badge) &rarr; **Aakruthi**
- **Capacity & Timeline Scheduling:**
  - Constant: `Machine Speed = 650 SPM`, `Daily Working Hours = 6 hours`.
  - Machine running time:
    $$\text{Total Running Hours} = \frac{\text{stitch\_count} \times \text{quantity}}{650 \times 60}$$
    $$\text{Days Needed} = \max\left(1, \left\lceil \frac{\text{Total Running Hours}}{6} \right\rceil\right)$$
  - Reads queue of active orders for the assigned machine from `Orders` tab.
  - Starts iteration from earliest machine free date (or today).
  - Skips **Sundays** and **Holidays** (fetched from `Holidays!A:B`).
  - Calculates `estimated_completion_date`.
  - **Delivery Date Check:** Compares `estimated_completion_date` with `requested_delivery_date`. If achievable, confirms schedule; if completion date exceeds requested date, appends schedule conflict warning with earliest available completion date.

---

#### Agent 3 — Cost Estimator (`agent_3_estimator.py`)
- **Strict 4-Factor Pricing Model:**
  - Sourced dynamically from the `Config` tab:
    - `cost_per_1k = float(config.get("Cost per 1000 Stitches", 10.0))`
    - `hourly_rate = float(config.get("Hourly Labor Rate", 100.0))`
    - `profit_margin_pct = float(config.get("Profit Margin Percent", 20.0))`
    - `gst_rate_pct = float(config.get("GST Rate Percent", 18.0))`
- **Formulas:**
  1. **Stitching Cost:**
     $$\text{stitch\_cost} = \begin{cases} 
     \left(\dfrac{\text{stitch\_count} \times \text{quantity}}{1000}\right) \times \text{cost\_per\_1k}, & \text{if Machine Embroidery} \\ 
     0.0, & \text{if Embroidery design} 
     \end{cases}$$
  2. **Labor Cost:**
     $$\text{labor\_cost} = \text{labor\_hours} \times \text{hourly\_rate}$$
  3. **Base Cost:**
     $$\text{base\_cost} = \text{stitch\_cost} + \text{labor\_cost}$$
  4. **Profit Margin:**
     $$\text{profit\_amount} = \text{base\_cost} \times \left(\frac{\text{profit\_margin\_pct}}{100}\right)$$
  5. **Subtotal:**
     $$\text{subtotal} = \text{base\_cost} + \text{profit\_amount}$$
  6. **GST Amount:**
     $$\text{gst\_amount} = \text{subtotal} \times \left(\frac{\text{gst\_rate\_pct}}{100}\right)$$
  7. **Total Cost:**
     $$\text{total\_cost} = \text{subtotal} + \text{gst\_amount}$$
- **Audit Log:** Writes itemized computation breakdown to Column O (`Reasoning Log`).
- **Initial Status:** Sets `state.invoice_status = "Estimated"`.

---

#### Agent 5 — Invoicing Worker (`agent_5_invoicing.py`)
- **Operational Secretary Summaries (CJS Accountant Delineation):**
  - CJS Accountant generates formal invoices and maintains ledgers.
  - Agent 5 provides Siny with two high-value operational summaries:
    1. **Pending for Invoicing:** Orders in `Orders` tab where production is completed or estimated completion date is reached, but invoice status is not `"invoiced"` or `"Completed"`.
    2. **Pending Invoices Follow-Up:** Orders with status `"invoiced"` where payment is still pending, sorted by age to prioritize customer reminders.
  - Status mutation: Allows Siny to mark orders as `"invoiced"` or `"Completed"` in the `Orders` tab.

---

#### Agent 6 — Business Secretary (`agent_6_secretary.py`)
- **Role:** Generates daily morning briefing and on-demand operational summaries.
- **Five Core Information Pillars:**
  1. **Work Assigned for the Day:** Orders scheduled for production or due today on Ricoma, Aakruthi, and active digital design tasks.
  2. **Pending Orders for Invoicing:** Completed production jobs awaiting billing in CJS Accountant.
  3. **Pending Invoices for Customer Follow-Up:** Unpaid invoices requiring reminders.
  4. **Studio Holidays:** Today's holiday status and upcoming holidays in the next 7 days.
  5. **Scheduled Reminders:** Active entries from the `Reminders` tab.
- **Triggering:**
  - Automated: Triggered at 6:00 AM IST daily by **Google Cloud Scheduler**.
  - On-demand: Triggered whenever Siny asks for daily tasks, schedule, or menu option `4`.

---

### 5. Google Sheets Schema Specifications

#### 5.1 `Orders` Tab (`Orders!A:P`)
| Col | Field Header | Data Type | Notes |
|---|---|---|---|
| A | Order Date | String | `YYYY-MM-DD HH:MM` |
| B | Order ID | String | Unique prefix `CJS-XXXXXX` |
| C | Customer ID | String | FK &rarr; `Customers` |
| D | Customer Name | String | Client name |
| E | Phone | String | Client WhatsApp phone number |
| F | Order Type | String | `Machine Embroidery` / `Embroidery design` |
| G | Template Name | String | Template from `Description_Templates` |
| H | Quantity | Integer | Unit quantity |
| I | Stitch Count | Integer | Total stitches (0 for Embroidery design) |
| J | Labor Hours | Decimal | Siny's prep/design hours |
| K | Machine | String | `Ricoma` / `Aakruthi` / `None` |
| L | Estimated Delivery Date | String | `YYYY-MM-DD` |
| M | Estimated Cost | String | `Rs X.XX` (from 4-factor formula) |
| N | Payment / Invoice Status | String | `pending` / `Estimated` / `invoiced` / `Completed` |
| O | Reasoning Log | String | Multi-agent execution and calculation audit trail |
| P | Overrides | String | Manual override history |

#### 5.2 `Description_Templates` Tab (`Description_Templates!A:E`)
| Col | Field Header | Type | Description |
|---|---|---|---|
| A | Order Type | String | `Machine Embroidery` or `Embroidery design` |
| B | Category | String | Garment, Badge, Digital Art, etc. |
| C | Template Name | String | e.g. `Saree Border`, `Kurti Neck`, `Logo Pocket`, `Baptism Set`, `Vector Digitizing` |
| D | Machine Allocation | String | `Ricoma` (large), `Aakruthi` (small), or `None` (Embroidery design) |
| E | Default Labor Hours | Decimal | Default design/prep hours (e.g. `1.5`, `0.5`, `3.0`) |

#### 5.3 `Config` Tab (`Config!A:C`)
| Col | Variable Name | Type | Value Example |
|---|---|---|---|
| A | `Cost per 1000 Stitches` | Float | `10.0` |
| A | `Hourly Labor Rate` | Float | `100.0` |
| A | `Profit Margin Percent` | Float | `20.0` |
| A | `GST Rate Percent` | Float | `18.0` |
| A | `Machine Speed SPM` | Int | `650` |
| A | `Daily Working Hours` | Float | `6.0` |
| B | Value | Dynamic | Parameter numeric value |
| C | Last Updated | String | ISO timestamp |

---

### 6. API Endpoints & Scheduler Architecture

| Method | Route | Purpose | Caller / Invocation |
|---|---|---|---|
| `GET` | `/` | Health ping | Cloud Run health probes |
| `GET` | `/health` | Diagnostic status | Monitoring |
| `GET` | `/webhook` | Meta verification handshake | Meta Developer Portal |
| `POST` | `/webhook` | Inbound WhatsApp messages & Flow responses | Meta Cloud API |
| `GET` / `POST` | `/trigger-daily-brief` | Executes daily briefing routine and dispatches to Siny | **GCP Cloud Scheduler** |

#### GCP Cloud Scheduler Configuration
```yaml
Name: cjs-daily-briefing-scheduler
Schedule: "30 0 * * *"   # 00:30 UTC = 06:00 AM IST
Timezone: Asia/Kolkata
HTTP Method: POST
Target URL: https://<CLOUD_RUN_SERVICE_URL>/trigger-daily-brief
Auth Header: OIDC token / API Secret key
```

---

### 7. Session Memory & Concurrency

- State maintained via `MemoryService` (`src/services/memory.py`), keyed by sender phone number.
- Reset flags on new turn to allow clean Supervisor routing.
- When an interactive form is dispatched (`send_order_form=True`), session state preserves the ongoing context until the user submits the form payload.
