# CJS Designs — Agent Development Guide

This document is the authoritative reference for building any new agent in the CJS multi-agent system.
Follow these conventions exactly so that output handling, WhatsApp message quality, and the
Supervisor routing contract remain consistent across the entire system.

---

## Core Architecture

```
WhatsApp Message
      │
      ▼
 Supervisor (router) ──► Worker Agents (1 or more)
      │                        │
      │◄───────────────────────┘
      │
      ▼ (at END)
 state.final_reply set?
      ├─ YES → send it verbatim (zero extra LLM call, exact formatting)
      └─ NO  → Supervisor synthesizes from aggregated_reasoning (multi-step order flows)
      │
      ▼
 WhatsApp Reply (one message, always from Supervisor)
```

---

## The `final_reply` Contract

`AgentState.final_reply` is the single field that determines how the Supervisor sends the
final WhatsApp message to Siny.

### Rule

| Your agent's query type | Do you set `final_reply`? |
|---|---|
| **Self-contained** — the agent produces a complete, user-facing response on its own | ✅ Yes — set `state.final_reply` |
| **Intermediate / pipeline** — your agent feeds data to another agent downstream | ❌ No — write to `state.aggregated_reasoning` only |

### Why this matters

- If you set `final_reply`, the Supervisor passes it to WhatsApp **verbatim** — your formatting,
  your emojis, your tone. Zero risk of the LLM re-wording or flattening it.
- If you don't set `final_reply`, the Supervisor synthesizes from all agents' `aggregated_reasoning`
  — ideal for multi-step order flows (Collector → Scheduler → Estimator → Invoice).
- **Never set `state.raw_message` directly.** Only the Supervisor touches `raw_message`.

---

## Agent Template

Copy this skeleton when creating a new agent:

```python
# src/agents/agent_N_yourname.py

import os
from langchain_google_genai import ChatGoogleGenerativeAI
from src.agents.state import AgentState

class YourNameAgent:
    def __init__(self):
        self.name = "Your Agent Name"
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-flash-latest",
            google_api_key=os.environ.get("GEMINI_API_KEY"),
            temperature=0.1
        )

    def process(self, state: AgentState) -> AgentState:
        """
        [One-line description of what this agent does.]

        OUTPUT CONTRACT:
        - Sets state.final_reply if this agent owns the user-facing response.
        - Appends to state.aggregated_reasoning for audit / pipeline context.
        - Never sets state.raw_message directly.
        """
        print(f"[{self.name}] Starting...")

        # --- Your agent logic here ---

        # Build the user-facing WhatsApp message.
        # Use emojis and *bold* formatting for WhatsApp readability.
        reply = (
            f"✅ *Your formatted result here*\n\n"
            f"Details...\n"
        )

        # DECISION: does this agent own the full response?
        # If YES (self-contained query): set final_reply
        state.final_reply = reply

        # If NO (intermediate in a pipeline): comment the line above
        # and only append to aggregated_reasoning below.

        # Always write an audit log entry.
        state.aggregated_reasoning += f"\n[{self.name}]: <short summary of what was done>.\n"

        return state
```

---

## Registering a New Agent

After creating your agent file, register it in **three places**:

### 1. `src/workflow/main_graph.py`

```python
from src.agents.agent_N_yourname import YourNameAgent

yourname = YourNameAgent()
builder.add_node("yourname", yourname.process)

# In conditional edges map:
"yourname": "yourname",

# Return edge back to supervisor:
builder.add_edge("yourname", "supervisor")
```

### 2. `src/agents/agent_0_supervisor.py` — routing prompt

Add your agent to the `WORKERS AVAILABLE` section in the Supervisor's routing prompt:

```
- 'yourname': Specialized in [describe what triggers this agent].
```

### 3. `src/agents/agent_0_supervisor.py` — `SupervisorOutput` Literal

```python
next_step: Literal[
    "collector", "scheduler", "estimator", "social", "invoice", "secretary",
    "yourname",   # ← add here
    "END"
]
```

---

## Existing Agent Reference

| Agent | File | Sets `final_reply`? | Trigger |
|---|---|---|---|
| Supervisor | `agent_0_supervisor.py` | N/A — orchestrator | Always first |
| Collector | `agent_1_collector.py` | ✅ for overrides/explanations; ❌ for orders | Any message |
| Scheduler | `agent_2_scheduler.py` | ❌ intermediate | After collector |
| Estimator | `agent_3_estimator.py` | ❌ intermediate | After scheduler |
| Social Media | `agent_4_social_media.py` | ✅ (stub — to be fully developed) | Order produced |
| Invoicing | `agent_5_invoicing.py` | ✅ (stub — to be fully developed) | Order delivery |
| Secretary | `agent_6_secretary.py` | ✅ | Daily brief / schedule query |

---

## WhatsApp Formatting Guide

Always format `final_reply` for WhatsApp:

| Element | Syntax | Example |
|---|---|---|
| Bold | `*text*` | `*Order ID:* CJS-4F51AD` |
| Newline | `\n` | Line breaks between sections |
| Section header | emoji + bold | `📦 *Order Details*` |
| List items | `- item` or `• item` | `- Status: Pending` |

**Avoid:** Markdown headers (`#`, `##`), HTML tags, triple backticks — WhatsApp doesn't render them.
