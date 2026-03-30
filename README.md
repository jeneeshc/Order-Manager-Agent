# CJS Designs — AI WhatsApp Order Management Agent

> **Reference document — last updated 30 March 2026**
> This README is the single source of truth for the entire CJS Designs multi-agent system.
> It covers business context, architecture, every agent's logic, routing conditions, data flow,
> Google Sheets schema, development conventions, environment setup, and deployment.

---

## Table of Contents

1. [Business Context](#1-business-context)
2. [System Architecture](#2-system-architecture)
3. [Message Flow — End to End](#3-message-flow--end-to-end)
4. [AgentState — The Shared Data Contract](#4-agentstate--the-shared-data-contract)
5. [Agent 0 — Supervisor](#5-agent-0--supervisor)
6. [Agent 1 — Order Collector](#6-agent-1--order-collector)
7. [Agent 2 — Production Scheduler](#7-agent-2--production-scheduler)
8. [Agent 3 — Estimator](#8-agent-3--estimator)
9. [Agent 4 — Social Media (Stub)](#9-agent-4--social-media-stub)
10. [Agent 5 — Invoicing (Stub)](#10-agent-5--invoicing-stub)
11. [Agent 6 — Secretary](#11-agent-6--secretary)
12. [The `final_reply` Output Contract](#12-the-final_reply-output-contract)
13. [Supervisor Routing Rules](#13-supervisor-routing-rules)
14. [Google Sheets Schema](#14-google-sheets-schema)
15. [Daily Briefing Scheduler](#15-daily-briefing-scheduler)
16. [Memory & Session Persistence](#16-memory--session-persistence)
17. [WhatsApp Webhook Handler](#17-whatsapp-webhook-handler)
18. [Adding a New Agent](#18-adding-a-new-agent)
19. [Technology Stack](#19-technology-stack)
20. [Environment Variables](#20-environment-variables)
21. [Project Structure](#21-project-structure)
22. [Local Development](#22-local-development)
23. [Deployment (Google Cloud Run)](#23-deployment-google-cloud-run)

---

## 1. Business Context

**CJS Designs** is a machine embroidery business operated by **Siny** (proprietor).
Customers contact Siny via WhatsApp with order requests — fabric type, embroidery style,
stitch count, and delivery expectations. Previously, Siny manually calculated costs,
scheduled machine time, and tracked payments via spreadsheets.

This system automates the entire lifecycle via AI agents that Siny controls entirely through
natural WhatsApp messages — no app, no portal, no training required.

### Business Constants

| Parameter | Value |
|---|---|
| Machines available | 2: **Ricoma**, **Aakruthi** |
| Machine speed | 650 stitches/minute (SPM) each |
| Working hours/day | 6 hours |
| Base billing rate | Rs 8 per 1,000 stitches |
| Off days | Sundays + public holidays (read from Sheets) |
| Admin WhatsApp | Siny's number (`ADMIN_PHONE_NUMBER` env var) |

---

## 2. System Architecture

### High-Level Flow

```
Siny (WhatsApp) ──► Meta Webhook ──► FastAPI (Cloud Run)
                                           │
                                    ┌──────▼──────┐
                                    │  Supervisor   │ ◄── LangGraph router
                                    │  (Agent 0)    │
                                    └──────┬────────┘
                                           │ routes to one of:
                   ┌───────────────────────┼────────────────────────┐
                   ▼           ▼           ▼           ▼            ▼
             Collector    Scheduler   Estimator    Secretary    Invoicing
            (Agent 1)    (Agent 2)   (Agent 3)    (Agent 6)   (Agent 5)
                   │           │           │           │            │
                   └───────────┴───────────┴───────────┴────────────┘
                                           │
                                    ┌──────▼────────┐
                                    │  Supervisor END │
                                    │  → WhatsApp     │
                                    └─────────────────┘
```

Every worker agent loops **back to the Supervisor** after completing its step.
The Supervisor decides whether more agents need to run, or whether the task is `END`.

### LangGraph Graph Definition (`src/workflow/main_graph.py`)

```
Entry point: supervisor
Conditional edges from supervisor → collector | scheduler | estimator | social | invoice | secretary | END
All workers have a fixed return edge → supervisor
```

### Orchestration Model

This is a **Supervisor-led, loopback multi-agent graph** (not a sequential pipeline).
The Supervisor can choose any agent at any step — it is not forced into a fixed order.
In practice for a new order, the typical path is:

```
supervisor → collector → supervisor → scheduler → supervisor → estimator → supervisor → END
```

---

## 3. Message Flow — End to End

### Incoming WhatsApp Message

```
1. Meta sends POST to /webhook
2. FastAPI extracts sender_phone + text_body
3. **Immediate Acknowledgement:** If sender is Siny, FastAPI instantly sends "Working on it, Boss... 🔄"
4. MemoryService.get_state(sender_phone) → loads prior session if multi-turn
5. AgentState created (fresh or resumed)
6. cjs_bot.invoke(state) → LangGraph graph runs
7. Decision logic on rebuilt_state:
   a. is_missing_info=True  → send missing_fields_prompt, save state to memory
   b. is_missing_info=False → finalize DB writes + send final reply, clear memory
```

### Database Write Logic (`src/api/main.py`)

```python
if rebuilt_state.is_missing_info:
    whatsapp.send(missing_fields_prompt)
    memory.save_state(sender_phone, rebuilt_state)
else:
    if rebuilt_state.order_id:
        if rebuilt_state.is_status_update:
            db.update_order_status(order_id, new_invoice_status)
        else:
            db.update_order(rebuilt_state)
    elif not any([is_explanation_request, is_secretary_query, is_payment_query]):
        db.append_order(rebuilt_state)          # New order → new row
    whatsapp.send(rebuilt_state.raw_message)    # Always set by Supervisor at END
    memory.clear_state(sender_phone)
```

### Multi-Turn Conversation (Memory)

When `is_missing_info=True`, the state is persisted via `MemoryService`. On the next
message from the same phone number, the prior state is **resumed** with these resets:

```python
initial_state.raw_message = text_body       # New message replaces old
initial_state.is_missing_info = False       # Force Supervisor to re-evaluate
initial_state.next_step = "supervisor"
```

---

## 4. AgentState — The Shared Data Contract

All agents communicate exclusively through `AgentState` (a Pydantic model in `src/agents/state.py`).
No agent calls another agent directly.

```python
class AgentState(BaseModel):
    # Identity
    sender_id: str                          # WhatsApp phone number

    # Input
    raw_message: str                        # Current WhatsApp message text

    # Order fields (hydrated by Collector)
    customer_name: Optional[str]
    customer_id: Optional[str]              # ID from Customers sheet
    fabric_type: Optional[str]
    embroidery_type: Optional[str]
    stitch_count: Optional[int]
    quantity: Optional[int]
    requested_delivery_date: Optional[str]
    order_id: Optional[str]                 # CJS-XXXXXX (existing or new)

    # Scheduler output
    estimated_completion_date: Optional[str]
    machine_assigned: Optional[str]         # "Ricoma" or "Aakruthi"

    # Estimator output
    total_cost_rs: Optional[float]

    # Invoicing
    invoice_status: str                     # "pending" | "Estimated" | "invoiced" | "Completed"
    media_assets: List[str]

    # Audit log (readable by Supervisor at END for synthesis)
    aggregated_reasoning: str

    # Routing
    next_step: str                          # Supervisor writes this; graph reads it
    current_agent: str

    # Intent flags (set by Collector early-return intercepts)
    is_missing_info: bool
    missing_fields_prompt: Optional[str]
    is_status_update: bool                  # "mark CJS-XXXX as invoiced"
    new_invoice_status: Optional[str]
    is_explanation_request: bool            # "explain reasoning for CJS-XXXX"
    is_payment_query: bool                  # "who owes me money?"
    is_secretary_query: bool                # "what are my tasks today?"
    is_duplicate_confirmed: bool            # "yes, create duplicate"
    is_field_override: bool                 # "change delivery date on CJS-XXXX"
    override_field: Optional[str]
    override_value: Optional[str]

    # OUTPUT CONTRACT (see Section 12)
    final_reply: Optional[str]              # Agent sets this to own the WhatsApp reply
    worker_feedback: str
```

---

## 5. Agent 0 — Supervisor

**File:** `src/agents/agent_0_supervisor.py`
**Model:** `gemini-flash-latest`, temperature=0 (deterministic routing)
**Role:** Orchestrator — never does business logic, only decides who runs next.

### Routing Decision

The Supervisor uses **structured output** (Pydantic `SupervisorOutput`) so the LLM is
forced to return a valid `next_step` from a fixed `Literal` set:

```python
next_step: Literal["collector", "scheduler", "estimator", "social", "invoice", "secretary", "END"]
```

### Routing Prompt Rules (injected into every Supervisor call)

| Condition | Action |
|---|---|
| `is_missing_info=True` | Route to `collector` again |
| `is_missing_info=True` AND collector already tried | Route to `END` (ask Siny for info) |
| Fresh message involving an order | Route to `collector` first |
| Siny asks for daily summary / schedule / tasks | Route to `secretary` |
| Final Reply Ready? (`state.final_reply` is set) | **Route to `END` immediately** |
| Collector done, all info present | Route to `scheduler` |
| Scheduler done | Route to `estimator` |
| All steps complete, or simple query already answered | Route to `END` |

### At END — Final Reply Logic

```python
if state.final_reply:
    # Agent already wrote a formatted message — send it verbatim (no extra LLM call)
    state.raw_message = state.final_reply
else:
    # Multi-step order flow — Supervisor synthesizes ONE message from aggregated_reasoning
    state.raw_message = llm.invoke(final_prompt)
```

---

## 6. Agent 1 — Order Collector

**File:** `src/agents/agent_1_collector.py`
**Model:** `gemini-flash-latest`, temperature=0
**Role:** Parse intent, extract order fields, detect duplicate orders.

### Structured Extraction Model

The Collector uses `with_structured_output(OrderExtractionModel)` — a Pydantic model
that forces the LLM to return valid typed fields:

| Field | Type | Description |
|---|---|---|
| `customer_name` | str | Customer name from message |
| `fabric_type` | str | Material (saree, uniform, cap, etc.) |
| `embroidery_type` | str | Style (applique, flat, 3D puff, etc.) |
| `stitch_count` | int | Total stitches (numeric) |
| `quantity` | int | Number of items |
| `requested_delivery_date` | str | Delivery date |
| `referenced_order_id` | str | Existing CJS-XXXXXX if mentioned |
| `mark_as_invoiced` | bool | "mark CJS-XXXX as invoiced" |
| `explain_reasoning` | bool | "explain reasoning for CJS-XXXX" |
| `is_field_override` | bool | "change X on order CJS-XXXX" |
| `override_field` | str | Field name to override |
| `override_value` | str | New value |
| `is_payment_query` | bool | "who owes money?" / "pending payments?" |
| `is_secretary_query` | bool | "what are my tasks today?" |
| `confirm_duplicate` | bool | "yes, go ahead" after duplicate warning |
| `is_missing_info` | bool | True if required fields are absent |
| `missing_fields_prompt` | str | Friendly ask for missing info |

### Intercept Chain (Early Returns)

The Collector processes in strict priority order; each intercept returns immediately,
bypassing the rest of the extraction logic:

```
0.  mark_as_invoiced + order_id  → state.is_status_update=True, state.final_reply="✅ Marked Invoiced"
0.5 explain_reasoning + order_id → state.is_explanation_request=True, state.final_reply="🔍 See Column L"
0.6 is_field_override + all fields → state.is_field_override=True, state.final_reply="✅ Field Updated"
0.7 is_payment_query              → state.is_payment_query=True (Supervisor routes to END or invoice)
0.8 is_secretary_query            → state.is_secretary_query=True (Supervisor routes to secretary)
```

### Order Hydration from Sheets

If `referenced_order_id` is extracted, the Collector fetches the existing order from
Google Sheets and hydrates state fields unless the new message overrides them:

```python
state.fabric_type      = extraction.fabric_type      or db_order["fabric_type"]
state.embroidery_type  = extraction.embroidery_type  or db_order["embroidery_type"]
state.stitch_count     = extraction.stitch_count     or db_order["stitch_count"]
```

### Missing Info Logic

Required fields for a new order: `customer_name`, `fabric_type`, `embroidery_type`, `stitch_count`.
If any are absent → `is_missing_info=True`, `missing_fields_prompt` is set by the LLM.

### Duplicate Detection

After all fields are confirmed and it's a new order (no `referenced_order_id`):

```python
db.check_duplicate_order(customer_name, sender_id, fabric_type, embroidery_type, stitch_count)
# Checks last 24 hours for identical combination
# If found → is_missing_info=True with a confirmation prompt
# User must reply "yes" → confirm_duplicate=True → bypass check
```

---

## 7. Agent 2 — Production Scheduler

**File:** `src/agents/agent_2_scheduler.py`
**Role:** Calculate estimated completion date using machine queues and holidays.

### Algorithm

```
1. total_hours   = stitch_count / 650 SPM / 60
2. days_required = max(1, round(total_hours / 6))
3. machine_assigned = min(machine_queues, key=availability_datetime)
   → Picks whichever of Ricoma/Aakruthi is free soonest
4. start_date = machine queue date (or today if past/empty)
5. Iterate forward days_required WORKING days:
   - Skip Sundays (weekday() == 6)
   - Skip dates in Holidays tab
6. estimated_completion_date = final date
```

### Machine Queue Calculation (`GoogleSheetsService.get_machine_availability`)

Scans all orders in Sheet1, filters out `completed` and `invoiced` statuses, and finds
the latest `estimated_completion_date` per machine. This gives the real queue tail.

### Output written to state

```python
state.machine_assigned          = "Ricoma" | "Aakruthi"
state.estimated_completion_date = "YYYY-MM-DD"
state.aggregated_reasoning     += "[Scheduler Agent]: ..."
```

---

## 8. Agent 3 — Estimator

**File:** `src/agents/agent_3_estimator.py`
**Role:** Calculate cost using the Costing tab in Google Sheets.

### Pricing Logic

```
1. Lookup (embroidery_type, fabric_type) tuple in Costing sheet (Cols A-E)
   - Col A: Embroidery type
   - Col B: Fabric/material
   - Col C: Unit label
   - Col D: Unit count (stitches per unit)
   - Col E: Cost per unit (Rs)

2. If exact match found:
   total_cost = (stitch_count / unit_count) × cost_per_unit

3. If no match (fallback):
   total_cost = (stitch_count / 1000) × 8.0   ← base rate Rs 8 per 1000 stitches

4. invoice_status = "Estimated"
```

### Output written to state

```python
state.total_cost_rs     = float (rounded to 2 decimal places)
state.invoice_status    = "Estimated"
state.aggregated_reasoning += "[Estimator Agent]: ..."
```

---

## 9. Agent 4 — Social Media (Stub)

**File:** `src/agents/agent_4_social_media.py`
**Status:** Stub — core output contract implemented, full fal.ai integration pending.

**Trigger:** When an order reaches "Produced" state and Boss uploads product photos.

**Planned full logic:**
1. Read order context from state (embroidery type, fabric, stitch count)
2. Call fal.ai to generate a video/image from uploaded product photos
3. Draft an Instagram-ready caption with hashtags

**Current behaviour:**
- Generates a hardcoded caption template
- Sets `state.final_reply = caption` ← output contract already in place
- Writes to `state.aggregated_reasoning`

---

## 10. Agent 5 — Invoicing (Stub)

**File:** `src/agents/agent_5_invoicing.py`
**Status:** Stub — core output contract implemented, full ledger integration pending.

**Trigger:** Order lifecycle approaches completion / Boss requests payment reminders.

**Planned full logic:**
1. Scan all orders with `invoice_status == "Completed"` grouped by customer
2. Calculate total outstanding dues per customer
3. Generate per-customer WhatsApp reminder messages
4. Update payment status in Sheet on confirmation

**Current behaviour:**
- Runs if `invoice_status == "pending"`
- Sets `state.invoice_status = "invoiced"`
- Sets `state.final_reply` with a WhatsApp-formatted pickup/payment reminder:
  ```
  ✅ Order Ready for Pickup!
  Order CJS-XXXX is complete 🎉
  💰 Amount Due: Rs X
  ```

---

## 11. Agent 6 — Secretary

**File:** `src/agents/agent_6_secretary.py`
**Model:** `gemini-flash-latest`, temperature=0.1
**Trigger:** Siny asks "what are my tasks today?", "what's my schedule?", etc.
**Also triggered:** Automatically every morning at 6:00 AM IST (see Section 15).

### Data gathered from Google Sheets

| Data | Source |
|---|---|
| Orders due today | Sheet1 Col I (estimated completion) == today |
| Pending invoices >7 days old | Sheet1 orders not invoiced/completed, order date < 7 days ago |
| Holiday status | Holidays tab — is today a holiday? |
| Upcoming holidays | Holidays tab — next 7 days |
| Reminders | Reminders tab — Col B: when, Col C: what |

### Prompt Rules

- Explicitly told: "This message is for TODAY — never say tomorrow"
- Uses emojis and `*bold*` for WhatsApp formatting
- Mentions orders due, old pending invoices, holidays, and specific reminders

### Output contract

```python
state.final_reply = summary      # Supervisor sends verbatim — no re-synthesis
state.aggregated_reasoning += "..."
```

---

## 12. The `final_reply` Output Contract

This is the **mandatory pattern** every agent must follow. See `docs/AGENT_DEVELOPMENT.md`
for the full guide.

### Two patterns

**Pattern A — Self-contained query (agent owns the reply):**
```python
state.final_reply = "your formatted WhatsApp message"
# Supervisor at END: sends this verbatim, no extra LLM call
```

**Pattern B — Intermediate pipeline step:**
```python
state.aggregated_reasoning += "[AgentName]: what was done"
# Do NOT set state.final_reply
# Supervisor at END: synthesizes one message from all agents' reasoning
```

### Which agents use which pattern

| Agent | Pattern | Reason |
|---|---|---|
| Supervisor | N/A | Sets `state.raw_message` directly at END |
| Collector (overrides/explain) | A | Self-contained confirmation |
| Collector (new order / updates) | B | Feeds scheduler and estimator |
| Scheduler | B | Intermediate — feeds estimator |
| Estimator | B | Intermediate — feeds supervisor synthesis |
| Social Media | A | Caption is a self-contained deliverable |
| Invoicing | A | Payment reminder is self-contained |
| Secretary | A | Daily brief is self-contained |

### Rules

- **Never set `state.raw_message` inside an agent** — that field belongs to the Supervisor only.
- If multiple agents set `final_reply`, the last one in the graph wins.
- Agents that are purely intermediate (Scheduler, Estimator) must never set `final_reply`.

---

## 13. Supervisor Routing Rules

The Supervisor's routing prompt encodes these decision rules:

```
RULE 1: is_missing_info=True → route to collector.
        If already tried collector and still missing → route to END.

RULE 2: Fresh message with order content → always route to collector first.

RULE 3: is_secretary_query=True → route to secretary.

RULE 4: state.final_reply is set (Final Reply Ready) → route to END immediately.

RULE 5: collector done, is_missing_info=False → route to scheduler.
        scheduler done → route to estimator.
        All steps done → route to END.

RULE 6: Simple query already answered (payment, override, explanation) → route to END.
```

---

## 14. Google Sheets Schema

### Sheet1 — Orders

| Col | Field | Notes |
|---|---|---|
| A | Order Date | `YYYY-MM-DD HH:MM` |
| B | Order ID | `CJS-XXXXXX` (UUID prefix) |
| C | Customer ID | From Customers sheet |
| D | Phone | Sender's WhatsApp number |
| E | Material / Fabric | |
| F | Embroidery Type | |
| G | Stitch Count | Numeric |
| H | Machine Assigned | Ricoma / Aakruthi |
| I | Est. Completion Date | `YYYY-MM-DD` |
| J | Estimated Cost | `Rs X` |
| K | Payment Status | pending / Estimated / invoiced / Completed |
| L | Reasoning Log | Aggregated agent reasoning (audit trail) |
| M | Quantity | Number of items |

### Holidays Tab — Columns A:B

| Col | Field | Format |
|---|---|---|
| A | Date | `DD-Month-YYYY` (e.g. `2-April-2026`) |
| B | Description | Optional label |

### Reminders Tab — Columns A:C

| Col | Field | Notes |
|---|---|---|
| A | (unused) | |
| B | When | Date or "11th of each month" |
| C | What | Reminder text |

### Costing Tab — Columns A:E

| Col | Field | Notes |
|---|---|---|
| A | Embroidery Type | Matched case-insensitively |
| B | Material | Matched case-insensitively |
| C | Unit label | (display only) |
| D | Unit Count | Divisor (stitches per unit) |
| E | Cost per Unit | Rs |

### Customers Tab — Columns A:B

| Col | Field | Notes |
|---|---|---|
| A | Customer ID | e.g. CUST-001 |
| B | Customer Name | Matched case-insensitively for lookup |

---

## 15. Daily Briefing Scheduler

The `SecretaryAgent.generate_daily_summary()` is automatically triggered at **6:00 AM IST
(Asia/Kolkata)** every day using APScheduler embedded in the FastAPI startup event.

```python
# src/api/main.py
scheduler = AsyncIOScheduler(timezone=IST)
scheduler.add_job(
    send_daily_briefing,
    CronTrigger(hour=6, minute=0, timezone=IST),
    id="daily_briefing",
    replace_existing=True
)
scheduler.start()   # called in @app.on_event("startup")
```

`send_daily_briefing()` calls the secretary **directly** — it bypasses LangGraph entirely
and uses `WhatsAppService.send_text_message(ADMIN_PHONE_NUMBER, summary)`.

A manual trigger is available at `GET /trigger-daily-brief` for testing.

> **Cloud Run note:** The scheduler lives in-process. On a single-instance deployment it
> fires reliably once per day. If multiple instances are running, consider using
> Cloud Scheduler to call `/trigger-daily-brief` instead.

---

## 16. Memory & Session Persistence

**File:** `src/services/memory.py`

Used for multi-turn conversations where Siny provides order info across multiple messages.

```
Key scheme: sender_phone number
Value: serialized AgentState dict
```

On resume, only three fields are reset to force fresh Supervisor evaluation:
```python
state.raw_message    = new_text_body
state.is_missing_info = False
state.next_step      = "supervisor"
```

State is cleared after a successful complete response (`memory.clear_state()`).

---

## 17. WhatsApp Webhook Handler

**File:** `src/api/main.py`

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/webhook` | Meta webhook verification (subscribe handshake) |
| `POST` | `/webhook` | Incoming WhatsApp messages (sends immediate acknowledgment) |
| `GET` | `/` | Health ping with version |
| `GET` | `/health` | Health check |
| `GET` | `/trigger-daily-brief` | Manual secretary briefing trigger |

### Error Handling

If the agent pipeline throws an exception, the admin phone (`ADMIN_PHONE_NUMBER`) receives
a formatted error notification:
```
⚠️ Internal Error: <exception message>
Check logs for details.
```

### Version

Current: `v1.2.7`

---

## 18. Adding a New Agent

See `docs/AGENT_DEVELOPMENT.md` for the detailed guide. Summary:

**Step 1** — Copy `src/agents/agent_template.py`, rename class and `self.name`.

**Step 2** — Implement `process(state: AgentState) -> AgentState`.
- If self-contained: set `state.final_reply`
- If intermediate: only append to `state.aggregated_reasoning`
- Never touch `state.raw_message`

**Step 3** — Register in `src/workflow/main_graph.py`:
```python
from src.agents.agent_N_yourname import YourNameAgent
yourname = YourNameAgent()
builder.add_node("yourname", yourname.process)
# In conditional edges:  "yourname": "yourname"
builder.add_edge("yourname", "supervisor")
```

**Step 4** — Register in `src/agents/agent_0_supervisor.py`:
```python
# In SupervisorOutput:
next_step: Literal[..., "yourname", "END"]

# In routing prompt:
- 'yourname': Specialized in [describe trigger condition].
```

---

## 19. Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Web Framework | FastAPI + Uvicorn (ASGI) |
| Agent Orchestration | LangGraph (state-machine graph with loopback) |
| LLM Framework | LangChain + `langchain-google-genai` |
| LLM Model | `gemini-flash-latest` (Google Gemini) |
| Structured Output | Pydantic v2 (`with_structured_output`) |
| Database | Google Sheets v4 API (`googleapiclient`) |
| Auth | GCP Service Account (local) / IAM Default (Cloud Run) |
| WhatsApp | Meta Business WhatsApp Cloud API v22.0 |
| Scheduler | APScheduler (`AsyncIOScheduler`) |
| Media Generation | fal.ai (planned — agent stub exists) |
| Container | Docker (`python:3.11-slim`) |
| Cloud | Google Cloud Run (serverless) |
| CI/CD | Cloud Build Triggers (auto-deploy on `git push`) |

---

## 20. Environment Variables

```env
# WhatsApp / Meta
WHATSAPP_VERIFY_TOKEN=         # Webhook verification secret
WHATSAPP_PHONE_NUMBER_ID=      # Meta phone number ID
WHATSAPP_ACCESS_TOKEN=         # Permanent Meta access token

# Google
GOOGLE_SHEET_ID=               # Spreadsheet ID from the URL
GEMINI_API_KEY=                # Google Gemini API key

# App
ADMIN_PHONE_NUMBER=            # Siny's WhatsApp number (for daily brief + error alerts)
FAL_KEY=                       # fal.ai API key (for future social media agent)
```

> **Local dev:** Put these in `.env` at project root (already in `.gitignore`).
>
> **Cloud Run:** Inject via Cloud Run Secrets or environment variable configuration.
> `credentials.json` is in `.gcloudignore` — Cloud Run uses implicit IAM auth.

---

## 21. Project Structure

```
CJS Designs/
├── src/
│   ├── agents/
│   │   ├── state.py                  ← AgentState Pydantic model (shared contract)
│   │   ├── agent_template.py         ← Copy this for any new agent
│   │   ├── agent_0_supervisor.py     ← Router + final reply synthesis
│   │   ├── agent_1_collector.py      ← Intent + order field extraction
│   │   ├── agent_2_scheduler.py      ← Production date calculation
│   │   ├── agent_3_estimator.py      ← Cost calculation
│   │   ├── agent_4_social_media.py   ← Instagram caption (stub)
│   │   ├── agent_5_invoicing.py      ← Payment reminder (stub)
│   │   └── agent_6_secretary.py      ← Daily briefing
│   ├── services/
│   │   ├── sheets.py                 ← Google Sheets read/write
│   │   ├── whatsapp.py               ← Meta WhatsApp API send/receive
│   │   └── memory.py                 ← Session persistence (multi-turn)
│   ├── workflow/
│   │   └── main_graph.py             ← LangGraph definition
│   └── api/
│       └── main.py                   ← FastAPI app, webhook handler, scheduler
├── docs/
│   ├── AGENT_DEVELOPMENT.md          ← Agent development guide & conventions
│   ├── Architecture.md               ← Mermaid architecture diagram
│   ├── BRD.md                        ← Business requirements
│   └── SRD.md                        ← System requirements
├── tests/                            ← All test & debug scripts
├── Dockerfile
├── requirements.txt
├── credentials.json                  ← GCP service account (gitignored)
├── .env                              ← Local env vars (gitignored)
├── .gitignore
└── .gcloudignore
```

---

## 22. Local Development

```bash
# 1. Create and activate venv
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
# Copy .env.example → .env and fill in values

# 4. Run the server
uvicorn src.api.main:app --reload --port 8000

# 5. Expose to internet (for WhatsApp webhook)
ngrok.exe http 8000
# Copy the https:// URL and set as WhatsApp webhook in Meta dashboard

# 6. Run tests
python tests/test_full_system.py
python tests/test_secretary.py
```

### Triggering the daily brief manually during development

```bash
curl http://localhost:8000/trigger-daily-brief
```

---

## 23. Deployment (Google Cloud Run)

```bash
# Build and push Docker image
gcloud builds submit --tag gcr.io/YOUR_PROJECT/cjs-agent

# Deploy to Cloud Run
gcloud run deploy cjs-agent \
  --image gcr.io/YOUR_PROJECT/cjs-agent \
  --platform managed \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars "WHATSAPP_VERIFY_TOKEN=...,WHATSAPP_ACCESS_TOKEN=...,..."
```

**CI/CD:** Cloud Build Trigger is connected to the GitHub repository.
Any `git push` to `main` automatically:
1. Pulls latest repo code
2. Rebuilds Docker image
3. Deploys new revision to Cloud Run
4. Swaps webhook endpoint (zero downtime, ~5 min total)

The Cloud Run container inherits GCP IAM permissions automatically — no `credentials.json`
needed in production. `GEMINI_API_KEY` and other secrets should be stored in
**GCP Secret Manager** and injected as environment variables in the Cloud Run service config.
