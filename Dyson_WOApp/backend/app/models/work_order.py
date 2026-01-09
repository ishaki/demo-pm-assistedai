from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    wo_number = Column(String(50), unique=True, nullable=False, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False)
    status = Column(String(30), nullable=False)  # 'Draft', 'Pending_Approval', 'Approved', 'Completed', 'Cancelled'
    priority = Column(String(20), nullable=True)  # 'Low', 'Medium', 'High'
    creation_source = Column(String(20), nullable=False)  # 'AI', 'Manual'
    # Changed from SET NULL to NO ACTION to avoid cascade path conflict in SQL Server
    ai_decision_id = Column(Integer, ForeignKey("ai_decisions.id", ondelete="NO ACTION"), nullable=True)
    scheduled_date = Column(Date, nullable=True)
    completed_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    notification_sent = Column(Boolean, nullable=False, default=False)
    notification_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    approved_at = Column(DateTime, nullable=True)
    approved_by = Column(String(200), nullable=True)

    # Relationships
    machine = relationship("Machine", back_populates="work_orders")
    ai_decision = relationship("AIDecision", foreign_keys=[ai_decision_id], back_populates="work_order")

    def __repr__(self):
        return f"<WorkOrder(wo_number='{self.wo_number}', status='{self.status}', machine_id={self.machine_id})>"


# Additional indexes
Index('idx_wo_status', WorkOrder.status)
Index('idx_wo_machine', WorkOrder.machine_id)
Index('idx_wo_number', WorkOrder.wo_number)
