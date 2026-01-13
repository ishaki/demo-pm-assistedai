from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from ..database import get_db
from ..services.work_order_service import WorkOrderService
from ..schemas.work_order import (
    WorkOrderCreate,
    WorkOrderUpdate,
    WorkOrderResponse,
    WorkOrderApproval,
    WorkOrderCompletion
)

router = APIRouter()


@router.get("/", response_model=List[WorkOrderResponse])
def get_work_orders(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    status: Optional[str] = Query(None, description="Filter by status"),
    machine_id: Optional[int] = Query(None, description="Filter by machine ID"),
    creation_source: Optional[str] = Query(None, description="Filter by creation source (AI/Manual)"),
    db: Session = Depends(get_db)
):
    """
    Get list of work orders with optional filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **status**: Filter by work order status
    - **machine_id**: Filter by machine ID
    - **creation_source**: Filter by creation source (AI or Manual)
    """
    service = WorkOrderService(db)
    work_orders = service.get_all_work_orders(
        skip=skip,
        limit=limit,
        status=status,
        machine_id=machine_id,
        creation_source=creation_source
    )

    return work_orders


@router.get("/{wo_id}", response_model=WorkOrderResponse)
def get_work_order(
    wo_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific work order by ID.

    - **wo_id**: Database ID of the work order
    """
    service = WorkOrderService(db)
    work_order = service.get_work_order_by_id(wo_id)

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {wo_id} not found"
        )

    return work_order


@router.post("/", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
def create_work_order(
    wo_data: WorkOrderCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new work order.

    - **wo_data**: Work order creation payload
    """
    service = WorkOrderService(db)

    # Verify machine exists
    from ..services.machine_service import MachineService
    machine_service = MachineService(db)
    machine = machine_service.get_machine_by_id(wo_data.machine_id)

    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {wo_data.machine_id} not found"
        )

    # Check for existing active work orders for this machine
    from ..models.work_order import WorkOrder
    existing_active_wos = (
        db.query(WorkOrder)
        .filter(
            WorkOrder.machine_id == wo_data.machine_id,
            WorkOrder.status.in_(["Draft", "Pending_Approval", "Approved"])
        )
        .all()
    )

    if existing_active_wos:
        wo_numbers = ", ".join([wo.wo_number for wo in existing_active_wos])
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Active work order(s) already exist for machine ID {wo_data.machine_id}: {wo_numbers}. Please complete or cancel existing work orders before creating a new one."
        )

    work_order = service.create_work_order(wo_data)
    return work_order


@router.put("/{wo_id}", response_model=WorkOrderResponse)
def update_work_order(
    wo_id: int,
    wo_data: WorkOrderUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing work order.

    - **wo_id**: Database ID of the work order
    - **wo_data**: Work order update payload
    """
    service = WorkOrderService(db)
    work_order = service.update_work_order(wo_id, wo_data)

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {wo_id} not found"
        )

    return work_order


@router.post("/{wo_id}/approve", response_model=WorkOrderResponse)
async def approve_work_order(
    wo_id: int,
    approval_data: WorkOrderApproval,
    db: Session = Depends(get_db)
):
    """
    Approve a work order.

    - **wo_id**: Database ID of the work order
    - **approval_data**: Approval information (approved_by)
    """
    service = WorkOrderService(db)

    # Verify WO exists and is in Pending_Approval status
    work_order = service.get_work_order_by_id(wo_id)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {wo_id} not found"
        )

    if work_order.status not in ["Draft", "Pending_Approval"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work order cannot be approved. Current status: {work_order.status}"
        )

    work_order = service.approve_work_order(wo_id, approval_data.approved_by)

    # Send approval notification to supplier
    from ..services.notification_service import NotificationService
    from ..services.machine_service import MachineService

    notification_service = NotificationService()
    machine_service = MachineService(db)
    machine = machine_service.get_machine_by_id(work_order.machine_id)

    if machine:
        email_sent = await notification_service.send_approval_notification(machine, work_order)

        # Update notification tracking if email sent successfully
        if email_sent:
            service.mark_notification_sent(wo_id)
            # Refresh work_order to get updated fields
            db.refresh(work_order)

    return work_order


@router.post("/{wo_id}/complete", response_model=WorkOrderResponse)
async def complete_work_order(
    wo_id: int,
    completion_data: WorkOrderCompletion,
    db: Session = Depends(get_db)
):
    """
    Mark work order as completed.

    - **wo_id**: Database ID of the work order
    - **completion_data**: Completion details including completed_date
    """
    service = WorkOrderService(db)

    # Verify WO exists and is in Approved status
    work_order = service.get_work_order_by_id(wo_id)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {wo_id} not found"
        )

    if work_order.status != "Approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only approved work orders can be completed. Current status: {work_order.status}"
        )

    # Validate completed_date
    today = datetime.now().date()

    # Check if completed_date is not in the future
    if completion_data.completed_date > today:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completion date cannot be in the future"
        )

    # Check if completed_date is not before scheduled_date
    if work_order.scheduled_date and completion_data.completed_date < work_order.scheduled_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Completion date cannot be before scheduled date ({work_order.scheduled_date})"
        )

    work_order = service.complete_work_order(wo_id, completion_data.completed_date)

    # Send completion notification to supplier
    from ..services.notification_service import NotificationService
    from ..services.machine_service import MachineService

    notification_service = NotificationService()
    machine_service = MachineService(db)
    machine = machine_service.get_machine_by_id(work_order.machine_id)

    if machine:
        email_sent = await notification_service.send_completion_notification(machine, work_order)

        # Update notification tracking if email sent successfully
        if email_sent:
            service.mark_notification_sent(wo_id)
            # Refresh work_order to get updated fields
            db.refresh(work_order)

    return work_order


@router.post("/{wo_id}/cancel", response_model=WorkOrderResponse)
def cancel_work_order(
    wo_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancel a work order.

    - **wo_id**: Database ID of the work order
    """
    service = WorkOrderService(db)

    # Verify WO exists
    work_order = service.get_work_order_by_id(wo_id)
    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {wo_id} not found"
        )

    if work_order.status == "Completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed work orders cannot be cancelled"
        )

    work_order = service.cancel_work_order(wo_id)
    return work_order


@router.delete("/{wo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_order(
    wo_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a work order.

    - **wo_id**: Database ID of the work order
    """
    service = WorkOrderService(db)
    work_order = service.get_work_order_by_id(wo_id)

    if not work_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {wo_id} not found"
        )

    service.db.delete(work_order)
    service.db.commit()

    return None
