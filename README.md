# CJS Designs - AI WhatsApp Order Agent

An automated, intelligent WhatsApp order management bot for CJS Designs. This agent intercepts WhatsApp texts, extracts business logic using Google Cloud Vertex AI (Gemini), calculates stitching timelines/costs, and directly appends orders into a Google Sheet database entirely autonomously.

## 🚀 Architecture Overview

This project orchestrates five mathematical agents executing sequentially via **LangGraph**:

1. **Order Collector Agent:** Uses Google Gemini 1.5 (via Vertex AI) and Pydantic structured output models to read loose conversational WhatsApp texts and perfectly extract `stitch_count`, `fabric_type`, and `requested_delivery_date`.
2. **Production Scheduler Agent:** Mathematically assigns expected machine timeframe based on a 650 Stitches Per Minute (SPM) theoretical rate over a 6-hour workday limit.
3. **Estimation Agent:** Implements custom design pricing parameters (Rs 8 per 1000 stitches) alongside fabric complexity multipliers to generate an instant upfront invoice quote for Siny.
4. **Social Media Agent:** Connects to `fal.ai` to dynamically generate concept design videos based on the extracted embroidery prompts.
5. **Invoicing Agent:** Compiles the final computed state and securely appends it via Service Accounts into Siny's private Google Sheet Database (`AI_Agent`).

The pipeline triggers a final automated HTTP POST webhook directly back to the customer's cell phone through the **Meta Business WhatsApp API** to formally hand them their real-time, calculated quote.

---

## 🛠️ Technology Stack

* **Routing & APIs:** FastAPI, Uvicorn (ASGI)
* **Orchestration:** LangChain, LangGraph
* **Intelligence:** Google Vertex AI (`gemini-1.5-flash-001`), Pydantic
* **Database Persistence:** Google Sheets V4 API
* **Media Synthesis:** fal.ai Video Models
* **Cloud Infrastructure:** Google Cloud Run (Serverless), Docker, Artifact Registry

---

## 🌍 Cloud Pipeline & CI/CD

This application is fully containerized using a bespoke `Dockerfile` leveraging a heavily optimized `python:3.11-slim` image block.

The platform is mapped explicitly to **Google Cloud Run**. Because it utilizes serverless architecture, the core Python runtime scales down to absolute zero when the business API is idle, ensuring practically $0.00 footprint bills during offline hours. 

### Continuous Deployment (CI/CD)
Google Cloud is permanently attached to this Github Repository via Cloud Build Triggers. Any time a developer runs `git push -u origin main` from their local computer, Google's continuous deployment webhooks will silently pull the updated repository code, re-compile the Docker image in isolated CI workers, and swap the live webhook endpoints transparently within 5 minutes.

### Security Implementation
Critical application parameters, specifically the `.env` local file and `credentials.json` Service Account nodes, are severely strictly ignored in both `.gitignore` and `.gcloudignore` templates. The remote Cloud Run Docker container is programmed dynamically to assume administrative backend permissions natively via internal GCP IAM default mechanisms, avoiding any potential key leakage into open Git trees.

---

## 💻 Environment Variables Requirements

For the server infrastructure to compute algorithms successfully in a local `localhost:8000` or native cloud environment, the following configuration must be supplied directly to the Cloud Run Secrets UI (or injected into a local `.env`):

```env
WHATSAPP_VERIFY_TOKEN=your_secure_hash
WHATSAPP_PHONE_NUMBER_ID=your_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_business_id
WHATSAPP_ACCESS_TOKEN=your_permanent_meta_token
GOOGLE_SHEET_ID=your_spreadsheet_url_id
FAL_KEY=your_media_api_key
```
*(Note: Vertex AI authorization occurs implicitly on Google Container deployments, rendering `GOOGLE_API_KEY` static keys obsolete).*
