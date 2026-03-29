# Business Requirement Document (BRD)
## CJS Designs - AI-Powered Order Management System

### 1. Executive Summary
CJS Designs, a machine embroidery service managed by the proprietor Siny, requires an automated, multi-agent workflow integrated with WhatsApp. The system aims to streamline the end-to-end order lifecycle—from initial inquiry and estimation to production scheduling, content generation for marketing, and invoicing.

### 2. Business Objectives
- **Automate Order Intake:** Enable seamless order collection via WhatsApp using voice, text, or forwarded messages.
- **Improve Estimation & Quoting:** Automatically calculate stitching costs and timelines based on exact machine specifications and business hours.
- **Streamline Production Planning:** Intelligently schedule orders considering the existing queue, holidays, weekends, and machine capacity.
- **Enhance Marketing:** Automatically generate ready-to-publish Instagram posts and videos for the final products.
- **Efficient Financial Tracking:** Automate the invoicing process and maintain an up-to-date ledger of pending and completed payments.

### 3. Stakeholders
- **Proprietor (Siny):** Primary user interacting with the AI agents via WhatsApp to manage operations.
- **Customers:** End consumers receiving estimates, timelines, and invoices indirectly via Siny.

### 4. Scope
The project scope encompasses developing a cascading multi-agent AI framework with 5 specialized agents. The system will be deployed on Google Cloud Platform (GCP), connect to WhatsApp as the messaging layer, integrate with Model Context Protocol (MCP) to provide structured input forms, utilize Google Sheets for data persistence, and use fal.ai for potential video and image generation.

### 5. Key Requirements
1. **Multimodal Input:** Support voice and text notes via WhatsApp.
2. **Structured Form Input (MCP):** Provide an MCP-based input component via WhatsApp for detailed order capture (fabric type, embroidery type, stitch count, expected delivery date, cost, design photo).
3. **Data Storage:** Real-time synchronization with a Google Sheet table.
4. **Machine & Time Constraints:** 
   - Available Machines: 2 (Ricoma, Aakruthi)
   - Machine Speed: 650 stitches per minute (SPM) each.
   - Working Hours: Approximately 6 hours per day.
5. **Cost Logic:** Billing rate of Rs 8 per 1,000 stitches.
