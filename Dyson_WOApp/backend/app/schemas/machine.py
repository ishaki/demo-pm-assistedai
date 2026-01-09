from pydantic import BaseModel, Field, validator
from datetime import date, datetime
from typing import Optional, List, Literal


class MachineBase(BaseModel):
    machine_id: str = Field(..., min_length=1, max_length=50, description="Unique machine identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Machine name")
    description: Optional[str] = Field(None, description="Machine description")
    location: Optional[str] = Field(None, max_length=200, description="Physical location")
    pm_frequency: Literal["Monthly", "Bimonthly", "Yearly"] = Field(..., description="PM frequency")
    next_pm_date: date = Field(..., description="Next scheduled PM date")
    assigned_supplier: Optional[str] = Field(None, max_length=200, description="Assigned supplier name")
    supplier_email: Optional[str] = Field(None, max_length=200, description="Supplier email address")


class MachineCreate(MachineBase):
    """Schema for creating a new machine"""
    last_pm_date: Optional[date] = Field(None, description="Last PM completion date")
    status: Literal["Active", "Inactive"] = Field("Active", description="Machine status")


class MachineUpdate(BaseModel):
    """Schema for updating an existing machine"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    pm_frequency: Optional[Literal["Monthly", "Bimonthly", "Yearly"]] = None
    last_pm_date: Optional[date] = None
    next_pm_date: Optional[date] = None
    assigned_supplier: Optional[str] = Field(None, max_length=200)
    supplier_email: Optional[str] = Field(None, max_length=200)
    status: Optional[Literal["Active", "Inactive"]] = None


class MachineResponse(MachineBase):
    """Schema for machine response"""
    id: int
    last_pm_date: Optional[date]
    status: str
    created_at: datetime
    updated_at: datetime
    pm_status: str = Field(..., description="PM status: overdue, due_soon, or ok")
    days_until_pm: int = Field(..., description="Days until PM (negative if overdue)")

    class Config:
        from_attributes = True


class MaintenanceHistorySimple(BaseModel):
    """Simplified maintenance history for inclusion in machine response"""
    id: int
    maintenance_date: date
    maintenance_type: Optional[str]
    notes: Optional[str]
    performed_by: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WorkOrderSimple(BaseModel):
    """Simplified work order for inclusion in machine response"""
    id: int
    wo_number: str
    status: str
    priority: Optional[str]
    creation_source: str
    created_at: datetime

    class Config:
        from_attributes = True


class MachineWithHistory(MachineResponse):
    """Machine response with maintenance history and work orders"""
    maintenance_history: List[MaintenanceHistorySimple] = []
    work_orders: List[WorkOrderSimple] = []

    class Config:
        from_attributes = True
