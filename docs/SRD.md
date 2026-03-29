# Solution Requirement Document (SRD)
## CJS Designs - AI-Powered Order Management System

### 1. System Overview
The proposed solution is a multi-agent orchestrated architecture deployed on Google Cloud Platform (GCP). It leverages WhatsApp as the primary user interface for Siny, backed by a series of intelligent AI agents that handle specialized sub-tasks in a cascading workflow. Data persistence is handled via Google Sheets.

### 2. Technology Stack
- **Cloud Infrastructure:** Google Cloud Platform (GCP) (e.g., Cloud Run for hosting the agents, Secret Manager for API keys).
- **User Interface:** WhatsApp Business API (via Meta, Twilio, or equivalent provider).
- **Core Agent Framework:** LangChain, CrewAI, or Microsoft AutoGen (Python) to orchestrate the multi-agent workflow.
- **Database / Ledger:** Google Sheets via Google Sheets API.
- **AI Models & Vendors:** 
  - **LLM:** Fast reasoning models (e.g., Gemini Flash or Pro) for parsing and executing agent roles.
  - **Voice-to-Text:** Whisper API or equivalent for transcribing Siny's voice messages.
  - **Media & Video Generation:** fal.ai models (e.g., fast video generators, image-to-video tools) based on finalized order photos.
- **Tooling Interface:** Model Context Protocol (MCP) concepts for passing structured forms to external AI tools to ensure rigorous data format collection within chat.

### 3. Cascading Agent Workflow
#### Agent 1: Order Collector
- **Trigger:** New voice/text/forwarded message on WhatsApp.
- **Function:** Parses the message. If details are missing, it asks Siny for clarifications. It presents an MCP tool/form for structured input (Fabric, Embroidery type, Stitch count, Delivery date, Cost, Photos).
- **Output:** Confirms validated details with Siny and pushes the data to Google Sheets.

#### Agent 2: Production Scheduler
- **Trigger:** New order logged in Google Sheets.
- **Function:** Reads existing orders, checks Siny's schedule (leaves, holidays, weekends). Calculates required time using machine constants (Ricoma, Aakruthi @ 650 SPM, 6 hrs/day). 
- **Output:** Identifies available capacity and updates the order workflow with a proposed completion date.

#### Agent 3: Estimation Agent
- **Trigger:** Stitch count derived by Agent 1 and Timeline calculated by Agent 2.
- **Function:** Applies the pricing algorithm (Rs 8 per 1,000 stitches).
- **Output:** Generates a formatted quote summary comprising cost metrics and delivery timeline, which Siny can organically forward to the customer.

#### Agent 4: Social Media & Content Agent
- **Trigger:** Siny uploads final product photos/videos.
- **Function:** Extrapolates contextual product details (embroidery type, threads used) from the original order in the database. Leverages fal.ai for dynamic video/image synthesis if required.
- **Output:** Drafts compelling, Instagram-ready post captions with appropriate tags and generates compiled media ready for posting.

#### Agent 5: Invoicing Agent
- **Trigger:** Order lifecycle approaches completion.
- **Function:** Calculates total amounts due. Periodically polls the Google Sheet to find outstanding receivables. 
- **Output:** Formats pending item reminders for Siny and securely tracks invoice fulfillment via Google Sheets.

### 4. Integration & Security
- Cloud functions and API Gateways secured on GCP.
- Strict token handling using GCP Secret Manager.
- Secure Google Service Accounts for Google Sheets API communication.
