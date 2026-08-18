from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..services.machine_service import MachineService
from ..schemas.machine import (
    MachineCreate,
    MachineUpdate,
    MachineResponse,
    MachineWithHistory,
    MaintenanceHistorySimple,
    WorkOrderSimple
)

router = APIRouter()


def enrich_machine_response(machine, service: MachineService) -> dict:
    """Helper function to enrich machine data with PM status"""
    return service.enrich_machine_data(machine)


@router.get("/", response_model=List[MachineResponse])
def get_machines(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    pm_status: Optional[str] = Query(
        None,
        description="Filter by PM status: scheduled, overdue, due_soon, ok, or due_soon,overdue"
    ),
    location: Optional[str] = Query(None, description="Filter by location"),
    exclude_scheduled: bool = Query(
        False,
        description="Exclude machines with approved work orders that have scheduled dates"
    ),
    db: Session = Depends(get_db)
):
    """
    Get list of machines with optional filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **pm_status**: Filter by PM status (scheduled, overdue, due_soon, ok)
    - **location**: Filter by machine location
    - **exclude_scheduled**: Exclude machines with scheduled approved work orders (default: false)
    """
    service = MachineService(db)
    machines = service.get_all_machines(
        skip=skip,
        limit=limit,
        pm_status=pm_status,
        location=location,
        exclude_scheduled=exclude_scheduled
    )

    # Enrich each machine with PM status
    enriched_machines = [enrich_machine_response(m, service) for m in machines]

    return enriched_machines


@router.get("/{machine_id}", response_model=MachineWithHistory)
def get_machine(
    machine_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific machine by ID with maintenance history and work orders.

    - **machine_id**: Database ID of the machine
    """
    service = MachineService(db)
    machine = service.get_machine_by_id(machine_id)

    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found"
        )

    # Enrich machine data
    enriched_data = enrich_machine_response(machine, service)

    # Get maintenance history
    maintenance_history = service.get_maintenance_history(machine_id, limit=20)

    # Convert to response format
    enriched_data["maintenance_history"] = [
        MaintenanceHistorySimple.model_validate(h) for h in maintenance_history
    ]

    enriched_data["work_orders"] = [
        WorkOrderSimple.model_validate(wo) for wo in machine.work_orders
    ]

    return enriched_data


@router.post("/", response_model=MachineResponse, status_code=status.HTTP_201_CREATED)
def create_machine(
    machine_data: MachineCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new machine.

    - **machine_data**: Machine creation payload
    """
    service = MachineService(db)

    # Check if machine_id already exists
    existing = service.get_machine_by_machine_id(machine_data.machine_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Machine with machine_id '{machine_data.machine_id}' already exists"
        )

    machine = service.create_machine(machine_data)
    return enrich_machine_response(machine, service)


@router.put("/{machine_id}", response_model=MachineResponse)
def update_machine(
    machine_id: int,
    machine_data: MachineUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing machine.

    - **machine_id**: Database ID of the machine
    - **machine_data**: Machine update payload
    """
    service = MachineService(db)
    machine = service.update_machine(machine_id, machine_data)

    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found"
        )

    return enrich_machine_response(machine, service)


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(
    machine_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a machine.

    - **machine_id**: Database ID of the machine
    """
    service = MachineService(db)
    deleted = service.delete_machine(machine_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found"
        )

    return None


@router.get("/{machine_id}/maintenance-history", response_model=List[MaintenanceHistorySimple])
def get_machine_maintenance_history(
    machine_id: int,
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    db: Session = Depends(get_db)
):
    """
    Get maintenance history for a specific machine.

    - **machine_id**: Database ID of the machine
    - **limit**: Maximum number of history records to return
    """
    service = MachineService(db)

    # Verify machine exists
    machine = service.get_machine_by_id(machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found"
        )

    history = service.get_maintenance_history(machine_id, limit=limit)
    return [MaintenanceHistorySimple.model_validate(h) for h in history]
