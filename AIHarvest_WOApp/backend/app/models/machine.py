from sqlalchemy import Column, Integer, String, Date, DateTime, Text, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    machine_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    location = Column(String(200), nullable=True)
    pm_frequency = Column(String(20), nullable=False)  # 'Monthly', 'Bimonthly', 'Yearly'
    last_pm_date = Column(Date, nullable=True)
    next_pm_date = Column(Date, nullable=False, index=True)
    assigned_supplier = Column(String(200), nullable=True)
    supplier_email = Column(String(200), nullable=True)
    status = Column(String(20), nullable=False, default="Active")  # 'Active', 'Inactive'
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    maintenance_history = relationship("MaintenanceHistory", back_populates="machine", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="machine", cascade="all, delete-orphan")
    ai_decisions = relationship("AIDecision", back_populates="machine", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Machine(machine_id='{self.machine_id}', name='{self.name}', next_pm='{self.next_pm_date}')>"


# Additional indexes
Index('idx_next_pm_date', Machine.next_pm_date)
Index('idx_machine_id', Machine.machine_id)
