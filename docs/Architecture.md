# System Architecture

> Updated: 30 March 2026 — reflects live production implementation.

## High-Level Architecture Diagram

```mermaid
graph TD
    %% External Interfaces
    Siny((Siny\nProprietor)) <-->|WhatsApp\nText / Voice / Flows| WA[Meta WhatsApp\nCloud API v22.0]

    %% GCP Infrastructure
    subgraph GCP [Google Cloud Platform — Cloud Run]
        WA <-->|POST /webhook| API[FastAPI Webhook &\nFlows Controller]
        API -.->|Immediate Ack| WA
        API -.->|Interactive Form / Flow| WA
        API -->|invoke| Graph

        subgraph Graph [LangGraph — Supervisor-Led Loopback Graph]
            SUP[Supervisor\nAgent 0\nRouter & Synthesizer]

            SUP -->|route| COL[Collector\nAgent 1\nIntent + Extraction]
            SUP -->|route| SCH[Scheduler\nAgent 2\nProduction Date]
            SUP -->|route| EST[Estimator\nAgent 3\nCosting]
            SUP -->|route| SOC[Social Media\nAgent 4\nInstagram Caption]
            SUP -->|route| INV[Invoicing\nAgent 5\nPayment Reminder]
            SUP -->|route| SEC[Secretary\nAgent 6\nDaily Briefing]

            COL -->|return| SUP
            SCH -->|return| SUP
            EST -->|return| SUP
            SOC -->|return| SUP
            INV -->|return| SUP
            SEC -->|return| SUP
        end

        API -->|send reply| WA
        SCHED[APScheduler\n6:00 AM IST daily] -->|direct call| SEC
        SCHED -->|send brief| WA
    end

    %% External Applications & Services
    CJSAcc[CJS Accountant\nWeb / Accounting App]
    GSheets[(Google Sheets Shared DB\nOrders / Customers / Config\nSales_Ledger / Expense_Ledger\nVendors / Holidays\nReminders / Assets)]
    Memory[(MemoryService\nSession Persistence)]

    CJSAcc <-->|read/write ledgers & config| GSheets
    COL <-->|read/write Orders & Customers| GSheets
    SCH <-->|read Orders & Holidays| GSheets
    EST <-->|read Config| GSheets
    INV <-->|sync Sales_Ledger & Orders| GSheets
    SEC <-->|read Orders, Holidays, Reminders| GSheets
    API <-->|read/write| GSheets
    API <-->|get/set/clear| Memory

    %% Styling
    classDef external fill:#f9f,stroke:#333,stroke-width:2px
    classDef gcp fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
    classDef agent fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef db fill:#fff3e0,stroke:#ff9800,stroke-width:2px

    class Siny,WA external
    class API,SCHED gcp
    class SUP,COL,SCH,EST,SOC,INV,SEC agent
    class GSheets,Memory db
```

## Key Architectural Decisions

### Supervisor-Led Loopback (not a sequential pipeline)

The graph has **no fixed sequence**. Every worker agent returns to the Supervisor after
each step. The Supervisor decides the next agent dynamically based on the current
`AgentState`. This allows:
- Re-routing if info is still missing after Collector runs
- Skipping agents that are not relevant to the current query
- Handling mixed-intent messages (e.g., "add this order AND tell me my tasks today")
- **Instant Response Routing:** If an agent sets `final_reply`, the Supervisor priorities routing to `END` immediately to deliver the message.

### `final_reply` Output Contract

All agents follow one of two patterns when writing output:

| Pattern | When | How |
|---|---|---|
| **A — Agent owns reply** | Self-contained query (Secretary, Invoicing, Social, Collector overrides) | Set `state.final_reply` |
| **B — Intermediate step** | Feeds data to next agent (Collector→order, Scheduler, Estimator) | Append to `state.aggregated_reasoning` only |

At `END`, the Supervisor checks:
- `final_reply` is set → sends verbatim (zero extra LLM call)
- `final_reply` is None → synthesizes one message from `aggregated_reasoning`

### Daily Briefing (Scheduled)

`APScheduler` inside the FastAPI process fires `SecretaryAgent.generate_daily_summary()`
at **6:00 AM IST** and sends the result directly to Siny via WhatsApp — bypassing the
LangGraph entirely. Also available via `GET /trigger-daily-brief`.
