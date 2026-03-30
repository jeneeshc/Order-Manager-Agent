# Solution Requirement Document (SRD)
## CJS Designs — AI-Powered WhatsApp Order Management System

> Updated: 30 March 2026 — reflects the live deployed system.

---

### 1. System Overview

A multi-agent AI system deployed on **Google Cloud Run** that intercepts WhatsApp messages
from Boss, orchestrates a network of specialised AI agents via **LangGraph**, and writes
results back to **Google Sheets**. Boss's only interface is WhatsApp.

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
  4. After collector (all info present) → `scheduler` → `estimator` → `END`
  5. Simple query already resolved → `END`
- **At END:** If `state.final_reply` is set → use verbatim. Else → LLM synthesis from reasoning.

#### Agent 1 — Collector (`agent_1_collector.py`)

- **Model:** `gemini-flash-latest`, temperature=0
- **Extraction model:** `OrderExtractionModel` (16 fields, all typed and optional)
- **Intercept chain (strict priority, each returns early):**
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
- **Machine selection:** Reads all non-completed/non-invoiced orders from Sheets; picks earliest free date
- **Holiday skipping:** Reads `Holidays!A:B` tab; also skips Sundays
- **Outputs:** `state.machine_assigned`, `state.estimated_completion_date`

#### Agent 3 — Estimator (`agent_3_estimator.py`)

- **Pure Python (no LLM)**
- **Pricing lookup:** `Costing!A:E` tab, matched by `(embroidery_type.lower(), fabric_type.lower())`
- **Formula (exact match):** `cost = (stitches / unit_count) × cost_per_unit`
- **Formula (fallback):** `cost = (stitches / 1000) × 8.0`
- **Outputs:** `state.total_cost_rs`, `state.invoice_status = "Estimated"`

#### Agent 4 — Social Media (`agent_4_social_media.py`)

- **Status:** Stub — output contract in place, fal.ai integration not yet built
- **Sets:** `state.final_reply` with Instagram caption template
- **Planned:** fal.ai video/image synthesis from product photo uploads

#### Agent 5 — Invoicing (`agent_5_invoicing.py`)

- **Status:** Stub — output contract in place, full payment ledger not yet built
- **Current:** Runs if `invoice_status == "pending"`, sets `state.invoice_status = "invoiced"`, sets `state.final_reply` with pickup reminder
- **Planned:** Multi-customer outstanding receivables report, periodic payment polling

#### Agent 6 — Secretary (`agent_6_secretary.py`)

- **Model:** `gemini-flash-latest`, temperature=0.1
- **Data sources (all from Sheets):**
  - Orders due today (Col I == today)
  - Pending invoices >7 days (not invoiced/completed)
  - Holiday status (today) and upcoming holidays (next 7 days)
  - Reminders from `Reminders!A:C` tab (date-based or "Nth of each month")
- **Prompt rules:** Explicitly says "TODAY not tomorrow"; uses WhatsApp formatting (emojis, `*bold*`)
- **Scheduled:** 6:00 AM IST daily via APScheduler (bypasses LangGraph — calls directly)
- **On-demand:** Triggered by Supervisor when `is_secretary_query=True`
- **Sets:** `state.final_reply = summary`

---

### 5. Google Sheets Schema

#### Sheet1 — Orders

| Col | Field | Type | Notes |
|---|---|---|---|
| A | Order Date | String | `YYYY-MM-DD HH:MM` |
| B | Order ID | String | `CJS-XXXXXX` |
| C | Customer ID | String | FK → Customers tab |
| D | Phone | String | Sender WhatsApp number |
| E | Material | String | Fabric type |
| F | Embroidery Type | String | Style |
| G | Stitch Count | Integer | |
| H | Machine | String | Ricoma / Aakruthi |
| I | Est. Completion | String | `YYYY-MM-DD` |
| J | Cost | String | `Rs X` |
| K | Payment Status | String | pending / Estimated / invoiced / Completed |
| L | Reasoning Log | String | Appended agent audit trail |
| M | Quantity | Integer | |

#### Holidays Tab — A:B

| Col | Field | Format |
|---|---|---|
| A | Date | `DD-Month-YYYY` e.g. `2-April-2026` |
| B | Description | Optional label |

#### Reminders Tab — A:C

| Col | Field | Notes |
|---|---|---|
| B | When | Date string or `"11th of each month"` |
| C | What | Reminder message text |

#### Costing Tab — A:E

| Col | Field | Notes |
|---|---|---|
| A | Embroidery Type | Matched case-insensitively |
| B | Material | Matched case-insensitively |
| C | Unit Label | Display only |
| D | Unit Count | Stitch divisor |
| E | Cost/Unit | Rs |

#### Customers Tab — A:B

| Col | Field |
|---|---|
| A | Customer ID |
| B | Customer Name |

---

### 6. API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health ping (returns version) |
| `GET` | `/health` | Health check |
| `GET` | `/webhook` | Meta webhook subscription verification |
| `POST` | `/webhook` | Incoming WhatsApp message handler |
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
| Admin errors | Error alerts sent only to `ADMIN_PHONE_NUMBER` |

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
