from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class WorkflowLogBase(BaseModel):
    workflow_name: str = Field(..., max_length=100, description="Name of the workflow")
    execution_id: Optional[str] = Field(None, max_length=100, description="n8n execution ID")
    status: Optional[Literal["Success", "Failed", "Partial"]] = Field(None, description="Execution status")
    machines_processed: int = Field(0, ge=0, description="Number of machines processed")
    work_orders_created: int = Field(0, ge=0, description="Number of work orders created")
    notifications_sent: int = Field(0, ge=0, description="Number of notifications sent")
    errors: Optional[str] = Field(None, description="Error messages if any")
    execution_time_ms: Optional[int] = Field(None, ge=0, description="Execution time in milliseconds")


class WorkflowLogCreate(WorkflowLogBase):
    """Schema for creating or updating a workflow log"""
    started_at: Optional[datetime] = Field(None, description="Workflow start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Workflow completion timestamp")


class WorkflowLogUpdate(BaseModel):
    """Schema for updating a workflow log"""
    status: Optional[Literal["Success", "Failed", "Partial"]] = None
    machines_processed: Optional[int] = Field(None, ge=0)
    work_orders_created: Optional[int] = Field(None, ge=0)
    notifications_sent: Optional[int] = Field(None, ge=0)
    errors: Optional[str] = None
    execution_time_ms: Optional[int] = Field(None, ge=0)
    completed_at: Optional[datetime] = None


class WorkflowLogResponse(WorkflowLogBase):
    """Schema for workflow log response"""
    id: int
    started_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
