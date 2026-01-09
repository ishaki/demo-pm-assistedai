from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Numeric, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class AIDecision(Base):
    __tablename__ = "ai_decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False)
    decision = Column(String(30), nullable=False)  # 'CREATE_WORK_ORDER', 'WAIT', 'SEND_NOTIFICATION'
    priority = Column(String(20), nullable=True)  # 'Low', 'Medium', 'High'
    confidence = Column(Numeric(3, 2), nullable=False)  # 0.00 to 1.00
    explanation = Column(Text, nullable=False)
    input_context = Column(Text, nullable=True)  # JSON snapshot of input data
    llm_provider = Column(String(50), nullable=True)  # 'OpenAI', 'Claude', 'Gemini'
    llm_model = Column(String(100), nullable=True)  # Model version used
    raw_response = Column(Text, nullable=True)  # Full LLM response for audit
    auto_executed = Column(Boolean, nullable=False, default=False)
    requires_review = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    machine = relationship("Machine", back_populates="ai_decisions")
    work_order = relationship("WorkOrder", foreign_keys="WorkOrder.ai_decision_id", back_populates="ai_decision", uselist=False)

    def __repr__(self):
        return f"<AIDecision(machine_id={self.machine_id}, decision='{self.decision}', confidence={self.confidence})>"


# Additional indexes
Index('idx_ai_machine', AIDecision.machine_id, AIDecision.created_at.desc())
Index('idx_ai_decision', AIDecision.decision, AIDecision.created_at.desc())
