from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, Literal


class MaintenanceHistoryBase(BaseModel):
    machine_id: int = Field(..., description="Machine ID")
    maintenance_date: date = Field(..., description="Date maintenance was performed")
    maintenance_type: Optional[Literal["Preventive", "Corrective", "Inspection"]] = Field(
        None, description="Type of maintenance"
    )
    notes: Optional[str] = Field(None, description="Maintenance notes")
    performed_by: Optional[str] = Field(None, max_length=200, description="Technician or company")


class MaintenanceHistoryCreate(MaintenanceHistoryBase):
    """Schema for creating maintenance history entry"""
    work_order_id: Optional[int] = Field(None, description="Associated work order ID")


class MaintenanceHistoryResponse(MaintenanceHistoryBase):
    """Schema for maintenance history response"""
    id: int
    work_order_id: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
