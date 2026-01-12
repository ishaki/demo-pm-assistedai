# AI Decision System Documentation

## Overview

The "Get AI Decision" feature uses Large Language Models (LLMs) to analyze machine maintenance data and automatically recommend actions for preventive maintenance. The system can use different AI providers (OpenAI GPT-4, Claude, or Gemini) to make intelligent decisions about work order management.

## Table of Contents

1. [Complete Workflow](#complete-workflow)
2. [Decision Rules](#decision-rules)
3. [System Components](#system-components)
4. [Data Model](#data-model)
5. [LLM Integration](#llm-integration)
6. [Decision Execution](#decision-execution)
7. [API Endpoints](#api-endpoints)
8. [Example Scenarios](#example-scenarios)
9. [Safety Mechanisms](#safety-mechanisms)

---

## Complete Workflow

### 1. Frontend Trigger

**Location:** `Dyson_WOApp/frontend/src/pages/MachineDetail.jsx:52-65`

When a user clicks the "Get AI Decision" button on the machine detail page:
- The frontend calls `aiService.getDecision(machineId)`
- This makes a POST request to `/api/ai/decision/{machine_id}`
- Shows loading state while waiting for response
- Displays the AI decision in a dialog
- Refreshes machine data to show the new decision

```javascript
const handleGetAIDecision = async () => {
  setAiLoading(true);
  const decision = await aiService.getDecision(id);
  setAiDecision(decision);
  setAiDialogOpen(true);
  await fetchMachineDetails();
};
```

### 2. API Endpoint

**Location:** `Dyson_WOApp/backend/app/routers/ai.py:16-69`

The endpoint receives the request and:
1. Verifies the machine exists using `MachineService`
2. Creates an `AIService` instance
3. Calls `await ai_service.make_decision(machine_id)`
4. Returns the AI decision response or appropriate error

### 3. AI Service Core Logic

**Location:** `Dyson_WOApp/backend/app/services/ai_service.py:25-166`

This is where the main intelligence happens:

#### a) Data Collection

The system gathers comprehensive context:

```python
# Machine Information
machine_data = {
    "machine_id": machine.machine_id,
    "name": machine.name,
    "location": machine.location,
    "pm_frequency": machine.pm_frequency,
    "last_pm_date": str(machine.last_pm_date),
    "next_pm_date": str(machine.next_pm_date),
    "days_until_pm": days_until_pm,  # CRITICAL for decision-making
    "assigned_supplier": machine.assigned_supplier,
    "supplier_email": machine.supplier_email
}
```

**Key Calculation:**
```python
today = datetime.now().date()
days_until_pm = (machine.next_pm_date - today).days
# Negative value = OVERDUE
# Positive value = Days remaining until PM
```

**Maintenance History:**
- Fetches last 10 maintenance records
- Includes date, type, notes, and performer
- Ordered by most recent first

**Existing Work Orders:**
- Checks for work orders in states: Draft, Pending_Approval, Approved
- Critical for preventing duplicate work orders
- Includes WO number, status, priority, creation source

#### b) LLM Provider Call

```python
ai_response = await self.llm_provider.get_decision(
    machine_data,
    maintenance_history_data,
    existing_wo_data
)
```

#### c) Decision Storage

Saves complete audit trail to database:

```python
ai_decision = AIDecision(
    machine_id=machine_id,
    decision=ai_response.decision,
    priority=ai_response.priority,
    confidence=float(ai_response.confidence),
    explanation=ai_response.explanation,
    input_context=json.dumps(input_context, indent=2),
    llm_provider=self.llm_provider.get_provider_name(),
    llm_model=self.llm_provider.get_model_name(),
    raw_response=json.dumps(ai_response.model_dump(), indent=2),
    auto_executed=False,
    requires_review=requires_review
)
```

#### d) Confidence Threshold Check

```python
requires_review = ai_response.confidence < self.settings.CONFIDENCE_THRESHOLD

can_auto_execute = (
    not requires_review and
    ai_response.confidence >= self.settings.CONFIDENCE_THRESHOLD
)
```

---

## Decision Rules

**Location:** `Dyson_WOApp/backend/app/services/llm_providers/base.py:84-131`

The LLM is given strict decision rules in priority order:

### Rule Priority (Apply in Order)

1. **SEND_NOTIFICATION**
   - **Condition:** ANY work order has status "Approved"
   - **Action:** Notify supplier to schedule work immediately
   - **Rationale:** Work order is approved and waiting for supplier action

2. **WAIT**
   - **Condition:** ANY work order has status "Pending_Approval" or "Draft"
   - **Action:** Wait for approval or completion
   - **Rationale:** Work order is already in progress through approval workflow

3. **CREATE_WORK_ORDER**
   - **Condition:** NO work orders exist AND (PM is overdue OR due within 30 days)
   - **Action:** Create new work order
   - **Rationale:** Preventive maintenance is needed and no work order exists

4. **WAIT**
   - **Condition:** PM is not urgent (more than 30 days away) AND no work orders exist
   - **Action:** Wait until closer to due date
   - **Rationale:** Too early to create work order

### Critical Rules

- **Overdue Definition:** `days_until_pm` is NEGATIVE (e.g., -5 means 5 days overdue)
- **Due Soon Definition:** `days_until_pm` is between -999 and 30 (includes overdue!)
- **ALWAYS check existing_work_orders FIRST** before creating a new work order
- **If machine is overdue and has NO work orders,** you MUST choose CREATE_WORK_ORDER
- **"Approved" status means** supplier needs to be notified to start work immediately
- **Do not create duplicate work orders** if one already exists in ANY status

### Priority Rules

```
High Priority:   PM is overdue (days_until_pm < 0) OR due within 7 days
Medium Priority: PM is due within 8-21 days
Low Priority:    PM is due within 22-30 days
```

### Confidence Guidelines

```
0.9 - 1.0:  Very clear decision based on rules (e.g., overdue with no work order)
0.7 - 0.89: Confident but some ambiguity
0.5 - 0.69: Moderate confidence, requires review
< 0.5:      Low confidence, manual review required
```

---

## System Components

### Database Models

#### AIDecision Model
**Location:** `Dyson_WOApp/backend/app/models/ai_decision.py`

```python
class AIDecision(Base):
    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True)
    machine_id = Column(Integer, ForeignKey("machines.id"))
    decision = Column(String(30))  # 'CREATE_WORK_ORDER', 'WAIT', 'SEND_NOTIFICATION'
    priority = Column(String(20))  # 'Low', 'Medium', 'High'
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    explanation = Column(Text)
    input_context = Column(Text)  # JSON snapshot
    llm_provider = Column(String(50))  # 'OpenAI', 'Claude', 'Gemini'
    llm_model = Column(String(100))
    raw_response = Column(Text)
    auto_executed = Column(Boolean, default=False)
    requires_review = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
```

### Schemas

#### AIDecisionResponse
**Location:** `Dyson_WOApp/backend/app/schemas/ai_decision.py`

```python
class AIDecisionBase(BaseModel):
    decision: Literal["CREATE_WORK_ORDER", "WAIT", "SEND_NOTIFICATION"]
    priority: Literal["Low", "Medium", "High"]
    confidence: float  # 0.0 to 1.0
    explanation: str  # Minimum 10 characters
```

### Services

1. **AIService** - Core decision-making logic
2. **MachineService** - Machine data retrieval
3. **WorkOrderService** - Work order creation
4. **NotificationService** - Email notifications

---

## LLM Integration

### Base Provider Architecture

**Location:** `Dyson_WOApp/backend/app/services/llm_providers/base.py`

All LLM providers inherit from `BaseLLMProvider`:

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def get_decision(...) -> AIDecisionResponse:
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        pass
```

### OpenAI Provider Example

**Location:** `Dyson_WOApp/backend/app/services/llm_providers/openai_provider.py`

```python
class OpenAIProvider(BaseLLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.LLM_MODEL or "gpt-4"

    async def get_decision(...) -> AIDecisionResponse:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,  # Lower for consistency
            max_tokens=500
        )
        return AIDecisionResponse(**json.loads(response.choices[0].message.content))
```

### System Prompt

The LLM receives detailed instructions including:
- Decision rules in strict priority order
- Priority assignment guidelines
- Confidence scoring guidelines
- JSON schema requirements

### User Prompt Format

```
**Machine Information:**
- Machine ID: M001
- Name: CNC Machine #1
- Location: Building A - Floor 2
- PM Frequency: 180
- Last PM Date: 2025-12-01
- Next PM Date: 2026-01-01
- Days Until PM: -5 days (OVERDUE)
- Assigned Supplier: Acme Industrial

**Recent Maintenance History (3 records):**
- 2025-12-01: Preventive Maintenance - Completed successfully
- 2025-06-01: Preventive Maintenance - No issues found
- 2024-12-01: Preventive Maintenance - Replaced filters

**Existing Work Orders (0 active):**
No active work orders.

**Your Task:**
Based on the above information, provide your decision in JSON format only.
```

### LLM Response Format

```json
{
  "decision": "CREATE_WORK_ORDER",
  "priority": "High",
  "confidence": 0.95,
  "explanation": "Machine M001 is 5 days overdue for preventive maintenance with no existing work orders. Creating a high-priority work order is urgent to prevent equipment failure."
}
```

---

## Decision Execution

**Location:** `Dyson_WOApp/backend/app/services/ai_service.py:168-335`

### Execute Decision Method

```python
async def execute_decision(
    self,
    ai_decision_id: int,
    force: bool = False
) -> Optional[Dict[str, Any]]:
```

### Execution Flow

1. **Fetch AI Decision** from database
2. **Check if already executed** - prevent duplicate execution
3. **Check confidence threshold** - unless `force=True`
4. **Execute based on decision type**
5. **Mark as executed** - set `auto_executed=True`

### CREATE_WORK_ORDER Execution

**Location:** `ai_service.py:228-256`

```python
async def _create_work_order_from_decision(
    self,
    ai_decision: AIDecision
) -> Dict[str, Any]:

    wo_data = WorkOrderCreate(
        machine_id=ai_decision.machine_id,
        creation_source="AI",
        ai_decision_id=ai_decision.id,
        priority=ai_decision.priority,
        status="Pending_Approval",
        notes=f"AI-generated work order. {ai_decision.explanation}"
    )

    work_order = wo_service.create_work_order(wo_data)

    return {
        "status": "work_order_created",
        "work_order_id": work_order.id,
        "wo_number": work_order.wo_number
    }
```

**Result:**
- Creates work order with status "Pending_Approval"
- Sets priority from AI decision (Low/Medium/High)
- Links to AI decision via `ai_decision_id`
- Includes AI explanation in notes
- Assigns unique WO number (e.g., WO-2026-0015)

### SEND_NOTIFICATION Execution

**Location:** `ai_service.py:258-335`

```python
async def _send_notification_from_decision(
    self,
    ai_decision: AIDecision
) -> Dict[str, Any]:

    # Find approved work order
    work_order = self.db.query(WorkOrder).filter(
        WorkOrder.machine_id == ai_decision.machine_id,
        WorkOrder.status == "Approved"
    ).first()

    # Prepare AI context for email
    ai_context = {
        "explanation": ai_decision.explanation,
        "confidence": ai_decision.confidence
    }

    # Send notification
    success = await notification_service.send_approval_notification(
        machine,
        work_order
    )

    # Mark as sent
    if success:
        wo_service.mark_notification_sent(work_order.id)

    return {
        "status": "notification_sent" if success else "notification_failed",
        "recipient": machine.supplier_email,
        "machine_id": machine.machine_id,
        "wo_number": work_order.wo_number,
        "email_sent": success
    }
```

**Result:**
- Finds approved work order for machine
- Sends email to supplier with work order details
- Includes AI explanation and confidence in email
- Marks work order as "notification_sent"
- Returns success status

### WAIT Execution

```python
if ai_decision.decision == "WAIT":
    logger.info("Decision is WAIT - no action required")
    result = {"status": "wait", "message": "No action required"}
```

**Result:**
- No action taken
- Logs the decision
- Returns wait status

---

## API Endpoints

**Location:** `Dyson_WOApp/backend/app/routers/ai.py`

### 1. Get AI Decision

```
POST /ai/decision/{machine_id}
```

**Description:** Analyze machine and get AI recommendation

**Request:**
```json
{
  "force_decision": false  // Optional
}
```

**Response:**
```json
{
  "id": 123,
  "machine_id": 1,
  "decision": "CREATE_WORK_ORDER",
  "priority": "High",
  "confidence": 0.95,
  "explanation": "Machine M001 is 5 days overdue...",
  "llm_provider": "OpenAI",
  "llm_model": "gpt-4",
  "requires_review": false,
  "auto_executed": false,
  "created_at": "2026-01-12T10:30:00"
}
```

### 2. Execute AI Decision

```
POST /ai/decision/{ai_decision_id}/execute?force=false
```

**Description:** Execute a saved AI decision

**Query Parameters:**
- `force` (boolean): Force execution even if confidence is low

**Response:**
```json
{
  "success": true,
  "ai_decision_id": 123,
  "status": "work_order_created",
  "work_order_id": 456,
  "wo_number": "WO-2026-0015"
}
```

### 3. Get Recent Decisions

```
GET /ai/decisions/recent?limit=20&machine_id=1
```

**Description:** Get recent AI decisions for audit

**Query Parameters:**
- `limit` (1-100): Maximum number of decisions
- `machine_id` (optional): Filter by machine

**Response:**
```json
[
  {
    "id": 123,
    "machine_id": 1,
    "decision": "CREATE_WORK_ORDER",
    "confidence": 0.95,
    "created_at": "2026-01-12T10:30:00",
    ...
  },
  ...
]
```

### 4. Get AI Decision by ID

```
GET /ai/decisions/{ai_decision_id}
```

**Description:** Get specific AI decision details

**Response:** Full AI decision object including input context and raw response

### 5. Get AI Statistics

```
GET /ai/statistics
```

**Description:** Get statistics about AI decisions

**Response:**
```json
{
  "total_decisions": 150,
  "decisions_by_type": {
    "CREATE_WORK_ORDER": 80,
    "WAIT": 50,
    "SEND_NOTIFICATION": 20
  },
  "average_confidence": 0.87,
  "requiring_review": 15,
  "auto_executed": 120,
  "manual_review": 30,
  "provider_distribution": {
    "OpenAI": 100,
    "Claude": 30,
    "Gemini": 20
  }
}
```

---

## Example Scenarios

### Scenario 1: Overdue Machine with No Work Orders

**Input:**
- Machine ID: M001
- Days until PM: -5 (5 days overdue)
- Existing work orders: 0

**Decision Process:**
1. No work orders exist ✓
2. Machine is overdue (days_until_pm < 0) ✓
3. Rule 3 applies: CREATE_WORK_ORDER

**Output:**
```json
{
  "decision": "CREATE_WORK_ORDER",
  "priority": "High",
  "confidence": 0.95,
  "explanation": "Machine M001 is 5 days overdue for preventive maintenance with no existing work orders. Creating a high-priority work order is urgent to prevent equipment failure."
}
```

**Execution:**
- Creates WO-2026-0015 with status "Pending_Approval"
- Priority: High
- Linked to AI decision

### Scenario 2: Machine with Approved Work Order

**Input:**
- Machine ID: M002
- Days until PM: 10 (due in 10 days)
- Existing work orders: 1 (Status: Approved)

**Decision Process:**
1. Work order with status "Approved" exists ✓
2. Rule 1 applies: SEND_NOTIFICATION

**Output:**
```json
{
  "decision": "SEND_NOTIFICATION",
  "priority": "High",
  "confidence": 0.92,
  "explanation": "Work order WO-2026-0010 has been approved. Supplier should be notified to schedule the preventive maintenance for Machine M002, which is due in 10 days."
}
```

**Execution:**
- Sends email to supplier (supplier@example.com)
- Email includes work order details and AI explanation
- Marks work order as notification_sent

### Scenario 3: Machine with Pending Work Order

**Input:**
- Machine ID: M003
- Days until PM: 5 (due in 5 days)
- Existing work orders: 1 (Status: Pending_Approval)

**Decision Process:**
1. Work order with status "Pending_Approval" exists ✓
2. Rule 2 applies: WAIT

**Output:**
```json
{
  "decision": "WAIT",
  "priority": "High",
  "confidence": 0.88,
  "explanation": "Work order WO-2026-0012 is pending approval for Machine M003. Wait for approval before taking further action. PM is due in 5 days, so approval should be expedited."
}
```

**Execution:**
- No action taken
- Decision logged for audit

### Scenario 4: Machine Not Yet Due

**Input:**
- Machine ID: M004
- Days until PM: 45 (due in 45 days)
- Existing work orders: 0

**Decision Process:**
1. No work orders exist ✓
2. PM is more than 30 days away ✓
3. Rule 4 applies: WAIT

**Output:**
```json
{
  "decision": "WAIT",
  "priority": "Low",
  "confidence": 0.90,
  "explanation": "Machine M004's preventive maintenance is due in 45 days. No immediate action required. Create work order when PM is within 30 days."
}
```

**Execution:**
- No action taken
- Will be re-evaluated when closer to due date

### Scenario 5: Low Confidence Decision

**Input:**
- Machine ID: M005
- Days until PM: 15
- Existing work orders: 1 (Status: Draft, created 45 days ago)
- Unusual maintenance history

**Decision Process:**
1. Ambiguous situation - old draft work order
2. Confidence below threshold

**Output:**
```json
{
  "decision": "CREATE_WORK_ORDER",
  "priority": "Medium",
  "confidence": 0.62,
  "explanation": "Machine M005 has a draft work order that's 45 days old, which may be stale. PM is due in 15 days. Recommend creating a new work order, but manual review suggested."
}
```

**Execution:**
- Decision saved with `requires_review=True`
- Cannot auto-execute (confidence 0.62 < threshold 0.7)
- Requires manual approval with `force=True`

---

## Safety Mechanisms

### 1. Confidence Threshold

**Configuration:** `CONFIDENCE_THRESHOLD` in settings (typically 0.7)

```python
requires_review = ai_response.confidence < self.settings.CONFIDENCE_THRESHOLD

can_auto_execute = (
    not requires_review and
    ai_response.confidence >= self.settings.CONFIDENCE_THRESHOLD
)
```

**Behavior:**
- High confidence (≥0.7): Can auto-execute
- Low confidence (<0.7): Requires manual review
- User can override with `force=True`

### 2. Duplicate Prevention

```python
# Check existing work orders before creating new ones
existing_wos = (
    self.db.query(WorkOrder)
    .filter(
        WorkOrder.machine_id == machine_id,
        WorkOrder.status.in_(["Draft", "Pending_Approval", "Approved"])
    )
    .all()
)
```

**Prevents:**
- Creating duplicate work orders
- Overwriting existing workflows
- Conflicting actions

### 3. Execution Tracking

```python
# Check if already executed
if ai_decision.auto_executed:
    logger.warning(f"AI decision {ai_decision_id} was already executed")
    return {"status": "already_executed", "ai_decision_id": ai_decision_id}
```

**Prevents:**
- Double execution of decisions
- Duplicate work orders
- Duplicate notifications

### 4. Complete Audit Trail

Every decision stores:
- **input_context**: Full snapshot of all input data (JSON)
- **llm_provider**: Which AI provider was used
- **llm_model**: Specific model version
- **raw_response**: Complete response from LLM
- **created_at**: Timestamp
- **auto_executed**: Execution status
- **requires_review**: Review flag

**Benefits:**
- Full traceability
- Debugging capability
- Compliance and auditing
- Performance analysis

### 5. Error Handling

```python
try:
    result = await ai_service.make_decision(machine_id)
except ValueError as e:
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
```

**Handles:**
- Machine not found errors
- LLM API failures
- Invalid responses
- Database errors

### 6. Validation

**Schema Validation:**
```python
@validator('decision')
def validate_decision(cls, v):
    valid_decisions = ["CREATE_WORK_ORDER", "WAIT", "SEND_NOTIFICATION"]
    if v not in valid_decisions:
        raise ValueError(f"Decision must be one of: {', '.join(valid_decisions)}")
    return v

@validator('confidence')
def validate_confidence(cls, v):
    if not 0.0 <= v <= 1.0:
        raise ValueError('Confidence must be between 0.0 and 1.0')
    return round(v, 2)
```

**Ensures:**
- Only valid decision types
- Confidence in valid range
- All required fields present
- Proper data types

---

## Configuration

### Environment Variables

```bash
# LLM Provider Selection
LLM_PROVIDER=openai  # Options: openai, claude, gemini

# OpenAI Configuration
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4  # or gpt-3.5-turbo

# Claude Configuration
ANTHROPIC_API_KEY=sk-ant-...
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Gemini Configuration
GOOGLE_API_KEY=AIza...
GEMINI_MODEL=gemini-pro

# Decision Threshold
CONFIDENCE_THRESHOLD=0.7  # 0.0 to 1.0
```

### Provider Selection

**Location:** `Dyson_WOApp/backend/app/services/llm_providers/__init__.py`

```python
def get_llm_provider() -> BaseLLMProvider:
    settings = get_settings()
    provider = settings.LLM_PROVIDER.lower()

    if provider == "openai":
        return OpenAIProvider()
    elif provider == "claude":
        return ClaudeProvider()
    elif provider == "gemini":
        return GeminiProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
```

---

## Key Files Reference

### Backend
- `app/routers/ai.py` - API endpoints
- `app/services/ai_service.py` - Core decision logic
- `app/services/llm_providers/base.py` - LLM provider interface
- `app/services/llm_providers/openai_provider.py` - OpenAI implementation
- `app/services/llm_providers/claude_provider.py` - Claude implementation
- `app/services/llm_providers/gemini_provider.py` - Gemini implementation
- `app/models/ai_decision.py` - Database model
- `app/schemas/ai_decision.py` - API schemas

### Frontend
- `frontend/src/services/aiService.js` - API client
- `frontend/src/pages/MachineDetail.jsx` - UI integration
- `frontend/src/utils/statusUtils.js` - Status formatting

---

## Benefits

1. **Intelligent Automation**: AI analyzes complex scenarios and recommends optimal actions
2. **Consistency**: Standardized decision-making across all machines
3. **Audit Trail**: Complete history of all decisions and reasoning
4. **Flexibility**: Support for multiple LLM providers
5. **Safety**: Confidence thresholds and manual review for uncertain decisions
6. **Transparency**: Clear explanations for all decisions
7. **Efficiency**: Reduces manual work order creation and supplier notifications
8. **Scalability**: Can handle large numbers of machines automatically

---

## Future Enhancements

Potential improvements to consider:

1. **Machine Learning**: Train on historical decisions to improve accuracy
2. **Cost Optimization**: Analyze maintenance costs and optimize scheduling
3. **Predictive Maintenance**: Integrate sensor data to predict failures
4. **Multi-language Support**: Support for international suppliers
5. **A/B Testing**: Compare different LLM providers and models
6. **Dashboard Analytics**: Visualize decision patterns and performance
7. **Custom Rules Engine**: Allow users to define custom decision rules
8. **Integration**: Connect with ERP/CMMS systems

---

**Document Version:** 1.0
**Last Updated:** 2026-01-12
**Author:** System Documentation
