from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class MaintenanceHistory(Base):
    __tablename__ = "maintenance_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False)
    maintenance_date = Column(Date, nullable=False)
    maintenance_type = Column(String(50), nullable=True)  # 'Preventive', 'Corrective', 'Inspection'
    notes = Column(Text, nullable=True)
    performed_by = Column(String(200), nullable=True)
    # Changed from SET NULL to NO ACTION to avoid cascade path conflict in SQL Server
    work_order_id = Column(Integer, ForeignKey("work_orders.id", ondelete="NO ACTION"), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    machine = relationship("Machine", back_populates="maintenance_history")
    work_order = relationship("WorkOrder", foreign_keys=[work_order_id])

    def __repr__(self):
        return f"<MaintenanceHistory(machine_id={self.machine_id}, date='{self.maintenance_date}', type='{self.maintenance_type}')>"


# Additional indexes
Index('idx_machine_maintenance', MaintenanceHistory.machine_id, MaintenanceHistory.maintenance_date.desc())
