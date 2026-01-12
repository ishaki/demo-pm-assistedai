from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pydantic import BaseModel, Field, validator


class AIDecisionResponse(BaseModel):
    """
    Standardized response format for AI decisions.
    All LLM providers must return this format.
    """
    decision: str = Field(..., description="Decision action")
    priority: str = Field(..., description="Priority level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    explanation: str = Field(..., min_length=10, description="Explanation")

    @validator('decision')
    def validate_decision(cls, v):
        valid_decisions = ["CREATE_WORK_ORDER", "WAIT", "SEND_NOTIFICATION"]
        if v not in valid_decisions:
            raise ValueError(f"Decision must be one of: {', '.join(valid_decisions)}")
        return v

    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ["Low", "Medium", "High"]
        if v not in valid_priorities:
            raise ValueError(f"Priority must be one of: {', '.join(valid_priorities)}")
        return v

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return round(v, 2)


class BaseLLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    All LLM provider implementations must inherit from this class.
    """

    @abstractmethod
    async def get_decision(
        self,
        machine_data: Dict[str, Any],
        maintenance_history: List[Dict[str, Any]],
        existing_work_orders: List[Dict[str, Any]]
    ) -> AIDecisionResponse:
        """
        Get AI decision for preventive maintenance work order creation.

        Args:
            machine_data: Dictionary containing machine information
            maintenance_history: List of maintenance history records
            existing_work_orders: List of existing work orders for the machine

        Returns:
            AIDecisionResponse with decision, priority, confidence, and explanation
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the LLM provider.

        Returns:
            Provider name (e.g., "OpenAI", "Claude", "Gemini")
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """
        Get the model name/version being used.

        Returns:
            Model name (e.g., "gpt-4", "claude-3-5-sonnet-20241022")
        """
        pass

    def build_system_prompt(self) -> str:
        """
        Build the system prompt for AI decision making.
        This can be overridden by subclasses if needed.

        Returns:
            System prompt string
        """
        return """You are an AI assistant for preventive maintenance management.
Your task is to analyze machine data and decide the appropriate action for preventive maintenance.

**Decision Rules (Apply in STRICT order):**
1. SEND_NOTIFICATION: If ANY work order has status "Approved" → Notify supplier to schedule work
2. WAIT: If ANY work order has status "Pending_Approval" or "Draft" → Wait for approval/completion
3. CREATE_WORK_ORDER: If NO work orders exist AND (PM is overdue OR due within 30 days) → Create new work order
4. WAIT: If PM is not urgent (more than 30 days away) AND no work orders exist → Wait until closer to due date

**Critical Rules:**
- "Overdue" means days_until_pm is NEGATIVE (e.g., -5 means 5 days overdue)
- "Due within 30 days" means days_until_pm is between -999 and 30 (includes overdue!)
- ALWAYS check existing_work_orders FIRST before creating a new work order
- If machine is overdue and has NO work orders, you MUST choose CREATE_WORK_ORDER
- "Approved" status means supplier needs to be notified to start work immediately
- Do not create duplicate work orders if one already exists in ANY status

**Priority Rules:**
- High: PM is overdue (days_until_pm < 0) OR due within 7 days
- Medium: PM is due within 8-21 days
- Low: PM is due within 22-30 days

**Confidence Guidelines:**
- 0.9-1.0: Very clear decision based on rules (e.g., overdue with no work order)
- 0.7-0.89: Confident but some ambiguity
- 0.5-0.69: Moderate confidence, requires review
- Below 0.5: Low confidence, manual review required

**IMPORTANT:**
- Return ONLY valid JSON matching this exact schema
- Do not include any explanatory text outside the JSON
- Ensure confidence is a decimal between 0.0 and 1.0
- Provide clear, concise explanation

**Response Schema:**
{
  "decision": "CREATE_WORK_ORDER | WAIT | SEND_NOTIFICATION",
  "priority": "Low | Medium | High",
  "confidence": 0.0,
  "explanation": "string"
}"""

    def build_user_prompt(
        self,
        machine_data: Dict[str, Any],
        maintenance_history: List[Dict[str, Any]],
        existing_work_orders: List[Dict[str, Any]]
    ) -> str:
        """
        Build the user prompt with machine data.

        Args:
            machine_data: Machine information
            maintenance_history: Maintenance history
            existing_work_orders: Existing work orders

        Returns:
            Formatted user prompt
        """
        days_until_pm = machine_data.get('days_until_pm', 0)
        pm_status = "OVERDUE" if days_until_pm < 0 else "DUE SOON" if days_until_pm <= 30 else "OK"

        return f"""
**Machine Information:**
- Machine ID: {machine_data.get('machine_id')}
- Name: {machine_data.get('name')}
- Location: {machine_data.get('location')}
- PM Frequency: {machine_data.get('pm_frequency')}
- Last PM Date: {machine_data.get('last_pm_date')}
- Next PM Date: {machine_data.get('next_pm_date')}
- Days Until PM: {days_until_pm} days ({pm_status})
- Assigned Supplier: {machine_data.get('assigned_supplier')}

**Recent Maintenance History ({len(maintenance_history)} records):**
{self._format_maintenance_history(maintenance_history)}

**Existing Work Orders ({len(existing_work_orders)} active):**
{self._format_work_orders(existing_work_orders)}

**Your Task:**
Based on the above information, provide your decision in JSON format only.
"""

    def _format_maintenance_history(self, history: List[Dict[str, Any]]) -> str:
        """Format maintenance history for prompt"""
        if not history:
            return "No recent maintenance history available."

        formatted = []
        for h in history[:5]:  # Show only last 5
            formatted.append(
                f"- {h.get('maintenance_date')}: {h.get('maintenance_type')} - {h.get('notes', 'N/A')}"
            )
        return "\n".join(formatted)

    def _format_work_orders(self, work_orders: List[Dict[str, Any]]) -> str:
        """Format work orders for prompt"""
        if not work_orders:
            return "No active work orders."

        formatted = []
        approved_count = 0
        pending_count = 0

        for wo in work_orders:
            status = wo.get('status')
            formatted.append(
                f"- WO {wo.get('wo_number')}: Status={status}, Priority={wo.get('priority')}, Created={wo.get('created_at')}"
            )
            if status == "Approved":
                approved_count += 1
            elif status in ["Pending_Approval", "Draft"]:
                pending_count += 1

        summary = f"Total: {len(work_orders)} work order(s) - {approved_count} Approved, {pending_count} Pending/Draft\n"
        return summary + "\n".join(formatted)
