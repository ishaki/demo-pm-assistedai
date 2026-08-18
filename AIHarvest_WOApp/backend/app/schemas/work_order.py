from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, Literal


class WorkOrderBase(BaseModel):
    machine_id: int = Field(..., description="Machine ID")
    priority: Optional[Literal["Low", "Medium", "High"]] = Field(None, description="Work order priority")
    scheduled_date: Optional[date] = Field(None, description="Scheduled completion date")
    notes: Optional[str] = Field(None, description="Additional notes")


class WorkOrderCreate(WorkOrderBase):
    """Schema for creating a work order"""
    creation_source: Literal["AI", "Manual"] = Field(..., description="Source of work order creation")
    ai_decision_id: Optional[int] = Field(None, description="AI decision ID if created by AI")
    status: Literal["Draft", "Pending_Approval", "Approved", "Completed", "Cancelled"] = Field(
        "Draft", description="Work order status"
    )


class WorkOrderUpdate(BaseModel):
    """Schema for updating a work order"""
    status: Optional[Literal["Draft", "Pending_Approval", "Approved", "Completed", "Cancelled"]] = None
    priority: Optional[Literal["Low", "Medium", "High"]] = None
    scheduled_date: Optional[date] = None
    completed_date: Optional[date] = None
    notes: Optional[str] = None
    approved_by: Optional[str] = Field(None, max_length=200)


class WorkOrderResponse(WorkOrderBase):
    """Schema for work order response"""
    id: int
    wo_number: str
    status: str
    creation_source: str
    ai_decision_id: Optional[int]
    completed_date: Optional[date]
    notification_sent: bool
    notification_sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime]
    approved_by: Optional[str]
    machine_name: Optional[str] = Field(None, description="Machine name from joined machine table")

    class Config:
        from_attributes = True


class WorkOrderApproval(BaseModel):
    """Schema for approving a work order"""
    approved_by: str = Field(..., min_length=1, max_length=200, description="Name of approver")


class WorkOrderCompletion(BaseModel):
    """Schema for completing a work order"""
    completed_date: date = Field(..., description="Date when work was completed")
