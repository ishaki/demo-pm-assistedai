# Product Requirements Document (PRD)

## 1. Product Overview

### 1.1 Purpose
The purpose of this Proof of Concept (POC) is to demonstrate an AI-assisted Preventive Maintenance (PM) solution for asset management. The system will track machines, their maintenance schedules, and maintenance history, automatically identify upcoming PM activities, and use AI to decide whether to create Work Orders (WO) and send notifications.

This POC is designed to work **without integration to an existing Asset Management System**, using a simulated dataset instead.

### 1.2 Goals
- Visualize machine PM schedules and maintenance status
- Automatically detect PM due windows (typically 30 days before due date)
- Use AI to make decisions on:
  - Work Order creation
  - Waiting for approval
  - Sending notifications to suppliers
- Automate daily PM checks via workflow orchestration

### 1.3 Non-Goals
- Full CMMS or ERP replacement
- Predictive maintenance using sensor/IoT data
- Financial or spare-parts management
- Mobile application

---

## 2. Target Users

### 2.1 Primary Users
- Maintenance Planner
- Facility / Asset Manager

### 2.2 Secondary Users
- Supplier / Vendor (email notification only)
- Approver (internal role)

---

## 3. High-Level Architecture

### 3.1 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | ReactJS |
| Backend API | Python (FastAPI) |
| Database | MS SQL Server / Azure SQL Server |
| Workflow Automation | n8n |
| AI Engine | Large Language Model (LLM) via API (OpenAI GPT-4, Claude, or Gemini) |
| Notification | Email (SMTP / n8n Email Node) |
| Deployment | Docker (multi-container orchestration) |

### 3.2 Architectural Principles
- API-first design
- Stateless backend services
- AI-driven decision making
- Workflow orchestration separated from business logic

---

## 4. Functional Requirements

### 4.1 Machine Management

#### FR-1: Machine List
- System shall store a list of machines
- Each machine shall include:
  - Machine ID
  - Name
  - Description
  - Location
  - PM frequency (Monthly / Bimonthly / Yearly)
  - Last PM date
  - Next PM date
  - Assigned supplier

#### FR-2: Maintenance History
- System shall record PM history per machine
- History entries shall include:
  - Maintenance date
  - Maintenance type
  - Notes

---

### 4.2 Work Order Management

#### FR-3: Work Order Creation
- System shall support Work Order (WO) creation
- WO attributes:
  - WO ID
  - Machine ID
  - Status (Draft, Pending Approval, Approved, Completed)
  - Creation source (AI / Manual)
  - AI justification
  - Created date

#### FR-4: Work Order Approval
- WO approval shall be simulated via:
  - Manual approval in the web app OR
  - Approval link via email

---

### 4.3 AI Decision Engine

#### FR-5: AI Decision Making
- AI shall decide actions based on:
  - PM due date
  - Current date
  - Maintenance history
  - Existing WO status

#### FR-6: AI Decision Outputs
AI must return structured JSON only:
```json
{
  "decision": "CREATE_WORK_ORDER | WAIT | SEND_NOTIFICATION",
  "priority": "Low | Medium | High",
  "confidence": 0.0,
  "explanation": "string"
}
```

#### FR-7: AI Guardrails
- AI output must follow strict schema validation
- Decisions with confidence below threshold (e.g. 0.7) shall require manual review

---

### 4.4 Workflow Automation (n8n)

#### FR-8: Daily Scheduler
- Workflow shall run once daily
- Recommended time: 01:00 local time

#### FR-9: PM Due Detection
- Workflow shall identify machines with PM due within 30 days

#### FR-10: Workflow Actions
- Based on AI decision, workflow shall:
  - Create Work Order
  - Wait for approval
  - Send email notification

---

### 4.5 Notification

#### FR-11: Supplier Notification
- Email notification shall be sent when:
  - WO is approved
  - AI recommends notification

Email content shall include:
- Machine details
- PM due date
- WO reference

---

## 5. Frontend Requirements (ReactJS)

### 5.1 Views

#### Machine Dashboard
- Machine list with PM status indicator
  - Green: OK
  - Yellow: Due ≤ 30 days
  - Red: Overdue

#### Machine Detail View
- Machine information
- Maintenance history
- Work Order status

#### Work Order View
- WO list
- Approval action

---

## 6. Backend API Requirements

### 6.1 API Endpoints (Indicative)

| Method | Endpoint | Description |
|---|---|---|
| GET | /machines | List machines |
| GET | /machines/{id} | Machine details |
| GET | /work-orders | List work orders |
| POST | /work-orders | Create work order |
| POST | /ai/decision | Get AI decision |

### 6.2 Security
- No authentication required for POC
- API access restricted by environment

---

## 7. Non-Functional Requirements

### 7.1 Performance
- Daily workflow execution < 5 minutes
- API response time < 500ms (excluding AI latency)

### 7.2 Auditability
- All AI decisions must be stored
- Decision explanation must be viewable

### 7.3 Reliability
- Workflow failures shall be logged
- Partial failures shall not stop daily execution

---

## 8. Assumptions & Constraints

- No integration with real Asset Management System
- AI is advisory but drives decisions
- Email delivery is best-effort
- Single-tenant POC
- POC will use 75 simulated test machines with varied PM statuses
- Docker-based deployment with MS SQL Server, FastAPI backend, React frontend, and n8n workflow
- LLM provider configurable between OpenAI GPT-4, Claude, and Gemini

---

## 9. Success Metrics

- PM due machines correctly identified
- WO created automatically for PM due cases
- AI decisions consistent and explainable
- End-to-end flow runs without manual intervention

---

## 10. Future Enhancements (Out of Scope)

- Integration with real CMMS / ERP
- Mobile app
- Predictive maintenance using IoT
- SLA-based supplier escalation
- Role-based access control

---

## 11. Decisions on Open Questions

- **Confidence threshold for AI auto-action:** 0.7 (decisions with confidence below 0.7 require manual review)
- **Approval SLA duration:** Basic approval flow without SLA tracking
- **Supplier notification frequency:** Once per Work Order

---

**End of PRD**

