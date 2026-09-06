# System Architecture
## CJS Designs — AI-Powered WhatsApp Order Management System

> Updated: September 2026 — reflects the updated system architecture and business logic overhaul.

## High-Level Architecture Diagram

```mermaid
graph TD
    %% External Interfaces
    Siny((Siny\nProprietor)) <-->|WhatsApp\nText / Menus / Flows| WA[Meta WhatsApp\nCloud API v22.0]

    %% GCP Cloud Scheduler
    GCPCron[GCP Cloud Scheduler\n6:00 AM IST daily\n00:30 UTC] -->|POST /trigger-daily-brief| API

    %% GCP Infrastructure
    subgraph GCP [Google Cloud Platform — Cloud Run]
        WA <-->|POST /webhook| API[FastAPI Webhook &\nFlows Controller]
        API -.->|Immediate Ack 🔄| WA
        API -.->|Interactive Form / Flow| WA
        API -->|invoke| Graph

        subgraph Graph [LangGraph — Supervisor-Led Loopback Graph]
            SUP[Supervisor\nAgent 0\nRouter & Synthesizer]

            SUP -->|route| COL[Collector\nAgent 1\nForm & Template Extraction]
            SUP -->|route| SCH[Scheduler\nAgent 2\nCapacity & Machine Routing]
            SUP -->|route| EST[Estimator\nAgent 3\n4-Factor Costing]
            SUP -->|route| SOC[Social Media\nAgent 4\nMarketing Caption]
            SUP -->|route| INV[Invoicing\nAgent 5\nBilling Summaries]
            SUP -->|route| SEC[Secretary\nAgent 6\nDaily Briefing]

            COL -->|return| SUP
            SCH -->|return| SUP
            EST -->|return| SUP
            SOC -->|return| SUP
            INV -->|return| SUP
            SEC -->|return| SUP
        end

        API -->|send reply| WA
        API -->|trigger brief| SEC
    end

    %% External Applications & Services
    CJSAcc[CJS Accountant\nAccounting & Invoicing App]
    GSheets[(Google Sheets Shared DB\nOrders / Description_Templates\nConfig / Customers / Holidays\nReminders / Sales_Ledger / Expenses)]
    Memory[(MemoryService\nSession Persistence)]

    CJSAcc <-->|invoices, payments & ledgers| GSheets
    COL <-->|read Description_Templates & Customers| GSheets
    SCH <-->|read Description_Templates, Orders & Holidays| GSheets
    EST <-->|read Config| GSheets
    INV <-->|read Orders & Sales_Ledger| GSheets
    SEC <-->|read Orders, Holidays, Reminders| GSheets
    API <-->|read/write Orders| GSheets
    API <-->|get/set/clear| Memory

    %% Styling
    classDef external fill:#f9f,stroke:#333,stroke-width:2px
    classDef gcp fill:#e1f5fe,stroke:#03a9f4,stroke-width:2px
    classDef agent fill:#e8f5e9,stroke:#4caf50,stroke-width:2px
    classDef db fill:#fff3e0,stroke:#ff9800,stroke-width:2px

    class Siny,WA external
    class API,GCPCron gcp
    class SUP,COL,SCH,EST,SOC,INV,SEC agent
    class GSheets,Memory db
```

## Key Architectural Decisions

### 1. Supervisor-Led Loopback
The graph uses a dynamic loopback topology where every worker agent reports back to the Supervisor (Agent 0). The Supervisor dynamically evaluates `AgentState` to determine next steps, allowing:
- Deterministic fast-path bypass for menus and WhatsApp form submissions.
- Seamless multi-agent chaining (`Collector` &rarr; `Scheduler` &rarr; `Estimator` &rarr; `Supervisor` &rarr; `END`).
- Instant termination whenever a worker sets `state.final_reply`.

### 2. Form-Based Order Intake
Freeform message parsing for critical fields is replaced with structured **WhatsApp Flows**:
- Dropdowns for `Order Type` (from `Description_Templates` Col A) and `Template Name` (Col C).
- Numerical controls for `Quantity`, `Stitch Count` (optional), and `Labor Hours` (pre-populated default from Col E).
- Target `Expected Delivery Date` picker.

### 3. Machine Allocation & Capacity Scheduling
- Machine routing is deterministic via `Description_Templates` Col D (`Ricoma` for large garments, `Aakruthi` for small badges/logos, `None` for software-only `Embroidery design`).
- Machine running time (`stitches / 650 SPM / 60`) governs machine daily capacity and availability against the requested delivery date, skipping Sundays and studio holidays.
- Labor hours are decoupled from machine availability, measuring human design effort and driving labor cost.

### 4. Strict 4-Factor Costing
Dynamic formula reading rates from `Config`:
$$\text{Total Cost} = (\text{Stitch Cost} + \text{Labor Cost} + \text{Profit Margin}) + \text{GST}$$

### 5. Daily Briefing via GCP Cloud Scheduler
Because Google Cloud Run scales to zero during inactivity, in-process schedulers (like APScheduler) cannot guarantee morning execution. Briefings are triggered by an external **GCP Cloud Scheduler** cron job at 6:00 AM IST daily calling `POST /trigger-daily-brief`.

### 6. CJS Accountant Delineation
The AI Agent operates strictly as an executive operational assistant. Tax invoicing, payment receipts, and formal ledger mutations are managed by **CJS Accountant**; the AI Agent provides Siny with operational summaries (pending invoicing, customer payment follow-ups).
