from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Literal


class AIDecisionBase(BaseModel):
    decision: Literal["CREATE_WORK_ORDER", "WAIT", "SEND_NOTIFICATION"] = Field(
        ..., description="AI decision action"
    )
    priority: Literal["Low", "Medium", "High"] = Field(..., description="Priority level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    explanation: str = Field(..., min_length=10, description="Explanation for the decision")

    @validator('confidence')
    def validate_confidence(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError('Confidence must be between 0.0 and 1.0')
        return round(v, 2)


class AIDecisionCreate(AIDecisionBase):
    """Schema for creating an AI decision record"""
    machine_id: int = Field(..., description="Machine ID")
    input_context: Optional[str] = Field(None, description="JSON snapshot of input data")
    llm_provider: Optional[str] = Field(None, max_length=50, description="LLM provider used")
    llm_model: Optional[str] = Field(None, max_length=100, description="LLM model version")
    raw_response: Optional[str] = Field(None, description="Full LLM response for audit")
    auto_executed: bool = Field(False, description="Whether action was auto-executed")
    requires_review: bool = Field(False, description="Whether decision requires manual review")


class AIDecisionResponse(AIDecisionCreate):
    """Schema for AI decision response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AIDecisionRequest(BaseModel):
    """Schema for requesting an AI decision (optional parameters)"""
    force_decision: bool = Field(False, description="Force new decision even if recent one exists")
