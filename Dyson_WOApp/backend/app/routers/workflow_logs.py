from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..services.workflow_log_service import WorkflowLogService
from ..schemas.workflow_log import (
    WorkflowLogCreate,
    WorkflowLogUpdate,
    WorkflowLogResponse
)

router = APIRouter()


@router.get("/", response_model=List[WorkflowLogResponse])
def get_workflow_logs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records"),
    workflow_name: Optional[str] = Query(None, description="Filter by workflow name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    db: Session = Depends(get_db)
):
    """
    Get list of workflow logs with optional filtering.

    - **skip**: Number of records to skip (pagination)
    - **limit**: Maximum number of records to return
    - **workflow_name**: Filter by workflow name
    - **status**: Filter by execution status (Success, Failed, Partial)
    """
    service = WorkflowLogService(db)
    logs = service.get_all_workflow_logs(
        skip=skip,
        limit=limit,
        workflow_name=workflow_name,
        status=status
    )

    return logs


@router.get("/{log_id}", response_model=WorkflowLogResponse)
def get_workflow_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """
    Get a specific workflow log by ID.

    - **log_id**: Database ID of the workflow log
    """
    service = WorkflowLogService(db)
    log = service.get_workflow_log_by_id(log_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow log with ID {log_id} not found"
        )

    return log


@router.get("/execution/{execution_id}", response_model=WorkflowLogResponse)
def get_workflow_log_by_execution(
    execution_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a workflow log by n8n execution ID.

    - **execution_id**: n8n execution ID
    """
    service = WorkflowLogService(db)
    log = service.get_workflow_log_by_execution_id(execution_id)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow log with execution_id {execution_id} not found"
        )

    return log


@router.post("/", response_model=WorkflowLogResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_workflow_log(
    log_data: WorkflowLogCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new workflow log or update existing one (upsert operation).

    If execution_id is provided and a log with that execution_id exists,
    the existing log will be updated. Otherwise, a new log will be created.

    - **log_data**: Workflow log creation/update payload

    This endpoint is designed to be called by n8n workflows to log their execution.
    """
    service = WorkflowLogService(db)
    log = service.upsert_workflow_log(log_data)

    return log


@router.put("/{log_id}", response_model=WorkflowLogResponse)
def update_workflow_log(
    log_id: int,
    log_data: WorkflowLogUpdate,
    db: Session = Depends(get_db)
):
    """
    Update an existing workflow log.

    - **log_id**: Database ID of the workflow log
    - **log_data**: Workflow log update payload
    """
    service = WorkflowLogService(db)
    log = service.update_workflow_log(log_id, log_data)

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow log with ID {log_id} not found"
        )

    return log


@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow_log(
    log_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete a workflow log.

    - **log_id**: Database ID of the workflow log
    """
    service = WorkflowLogService(db)
    deleted = service.delete_workflow_log(log_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow log with ID {log_id} not found"
        )

    return None
