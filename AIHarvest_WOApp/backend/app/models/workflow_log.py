from sqlalchemy import Column, Integer, String, DateTime, Text, Index
from sqlalchemy.sql import func
from ..database import Base


class WorkflowLog(Base):
    __tablename__ = "workflow_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    workflow_name = Column(String(100), nullable=False)
    execution_id = Column(String(100), nullable=True)  # n8n execution ID
    status = Column(String(20), nullable=True)  # 'Success', 'Failed', 'Partial'
    machines_processed = Column(Integer, nullable=False, default=0)
    work_orders_created = Column(Integer, nullable=False, default=0)
    notifications_sent = Column(Integer, nullable=False, default=0)
    errors = Column(Text, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<WorkflowLog(workflow='{self.workflow_name}', status='{self.status}', started='{self.started_at}')>"


# Additional indexes
Index('idx_workflow_execution', WorkflowLog.workflow_name, WorkflowLog.started_at.desc())
