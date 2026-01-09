from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import logging
from ..models.workflow_log import WorkflowLog
from ..schemas.workflow_log import WorkflowLogCreate, WorkflowLogUpdate

logger = logging.getLogger(__name__)


class WorkflowLogService:
    """Service class for workflow log-related business logic"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_workflow_logs(
        self,
        skip: int = 0,
        limit: int = 100,
        workflow_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[WorkflowLog]:
        """
        Get all workflow logs with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            workflow_name: Filter by workflow name
            status: Filter by status

        Returns:
            List of WorkflowLog objects
        """
        query = self.db.query(WorkflowLog)

        if workflow_name:
            query = query.filter(WorkflowLog.workflow_name == workflow_name)

        if status:
            query = query.filter(WorkflowLog.status == status)

        # Order by most recent first
        query = query.order_by(WorkflowLog.started_at.desc())

        return query.offset(skip).limit(limit).all()

    def get_workflow_log_by_id(self, log_id: int) -> Optional[WorkflowLog]:
        """
        Get a specific workflow log by ID.

        Args:
            log_id: Workflow log ID

        Returns:
            WorkflowLog object or None
        """
        return self.db.query(WorkflowLog).filter(WorkflowLog.id == log_id).first()

    def get_workflow_log_by_execution_id(self, execution_id: str) -> Optional[WorkflowLog]:
        """
        Get a workflow log by execution ID.

        Args:
            execution_id: n8n execution ID

        Returns:
            WorkflowLog object or None
        """
        return self.db.query(WorkflowLog).filter(WorkflowLog.execution_id == execution_id).first()

    def create_workflow_log(self, log_data: WorkflowLogCreate) -> WorkflowLog:
        """
        Create a new workflow log.

        Args:
            log_data: WorkflowLogCreate schema

        Returns:
            Created WorkflowLog object
        """
        log_dict = log_data.model_dump()

        # Set started_at to now if not provided
        if not log_dict.get('started_at'):
            log_dict['started_at'] = datetime.utcnow()

        workflow_log = WorkflowLog(**log_dict)

        self.db.add(workflow_log)
        self.db.commit()
        self.db.refresh(workflow_log)

        logger.info(f"Created workflow log: {workflow_log.workflow_name} (ID: {workflow_log.id})")
        return workflow_log

    def update_workflow_log(self, log_id: int, log_data: WorkflowLogUpdate) -> Optional[WorkflowLog]:
        """
        Update an existing workflow log.

        Args:
            log_id: Workflow log ID
            log_data: WorkflowLogUpdate schema

        Returns:
            Updated WorkflowLog object or None if not found
        """
        workflow_log = self.get_workflow_log_by_id(log_id)

        if not workflow_log:
            logger.warning(f"Workflow log with ID {log_id} not found")
            return None

        # Update only provided fields
        update_data = log_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workflow_log, field, value)

        self.db.commit()
        self.db.refresh(workflow_log)

        logger.info(f"Updated workflow log ID: {log_id}")
        return workflow_log

    def upsert_workflow_log(self, log_data: WorkflowLogCreate) -> WorkflowLog:
        """
        Create a new workflow log or update existing one based on execution_id.
        If execution_id is provided and exists, update that record.
        Otherwise, create a new record.

        Args:
            log_data: WorkflowLogCreate schema

        Returns:
            Created or updated WorkflowLog object
        """
        existing_log = None

        # Try to find existing log by execution_id
        if log_data.execution_id:
            existing_log = self.get_workflow_log_by_execution_id(log_data.execution_id)

        if existing_log:
            # Update existing log
            logger.info(f"Updating existing workflow log for execution_id: {log_data.execution_id}")

            # Convert to update schema
            update_data = WorkflowLogUpdate(
                status=log_data.status,
                machines_processed=log_data.machines_processed,
                work_orders_created=log_data.work_orders_created,
                notifications_sent=log_data.notifications_sent,
                errors=log_data.errors,
                execution_time_ms=log_data.execution_time_ms,
                completed_at=log_data.completed_at
            )

            return self.update_workflow_log(existing_log.id, update_data)
        else:
            # Create new log
            logger.info(f"Creating new workflow log for: {log_data.workflow_name}")
            return self.create_workflow_log(log_data)

    def delete_workflow_log(self, log_id: int) -> bool:
        """
        Delete a workflow log.

        Args:
            log_id: Workflow log ID

        Returns:
            True if deleted, False if not found
        """
        workflow_log = self.get_workflow_log_by_id(log_id)

        if not workflow_log:
            logger.warning(f"Workflow log with ID {log_id} not found")
            return False

        self.db.delete(workflow_log)
        self.db.commit()

        logger.info(f"Deleted workflow log ID: {log_id}")
        return True
