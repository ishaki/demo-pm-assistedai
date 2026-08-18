from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any, Optional
import json
import logging

from ..models.machine import Machine
from ..models.maintenance_history import MaintenanceHistory
from ..models.work_order import WorkOrder
from ..models.ai_decision import AIDecision
from ..services.llm_providers import get_llm_provider
from ..config import get_settings

logger = logging.getLogger(__name__)


class AIService:
    """Service class for AI decision-making logic"""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.llm_provider = get_llm_provider()

    async def make_decision(self, machine_id: int) -> Dict[str, Any]:
        """
        Make an AI decision for a machine's preventive maintenance.

        Args:
            machine_id: Machine database ID

        Returns:
            Dictionary containing AI decision and execution status
        """
        logger.info(f"Making AI decision for machine ID: {machine_id}")

        # Fetch machine data
        machine = self.db.query(Machine).filter(Machine.id == machine_id).first()

        if not machine:
            raise ValueError(f"Machine with ID {machine_id} not found")

        # Calculate days until PM
        today = datetime.now().date()
        days_until_pm = (machine.next_pm_date - today).days

        # Fetch maintenance history (last 10 entries)
        history = (
            self.db.query(MaintenanceHistory)
            .filter(MaintenanceHistory.machine_id == machine_id)
            .order_by(MaintenanceHistory.maintenance_date.desc())
            .limit(10)
            .all()
        )

        # Check existing work orders
        existing_wos = (
            self.db.query(WorkOrder)
            .filter(
                WorkOrder.machine_id == machine_id,
                WorkOrder.status.in_(["Draft", "Pending_Approval", "Approved"])
            )
            .all()
        )

        # Prepare context for LLM
        machine_data = {
            "machine_id": machine.machine_id,
            "name": machine.name,
            "location": machine.location,
            "pm_frequency": machine.pm_frequency,
            "last_pm_date": str(machine.last_pm_date) if machine.last_pm_date else None,
            "next_pm_date": str(machine.next_pm_date),
            "days_until_pm": days_until_pm,
            "assigned_supplier": machine.assigned_supplier,
            "supplier_email": machine.supplier_email
        }

        maintenance_history_data = [
            {
                "maintenance_date": str(h.maintenance_date),
                "maintenance_type": h.maintenance_type,
                "notes": h.notes,
                "performed_by": h.performed_by
            }
            for h in history
        ]

        existing_wo_data = [
            {
                "wo_number": wo.wo_number,
                "status": wo.status,
                "priority": wo.priority,
                "creation_source": wo.creation_source,
                "created_at": str(wo.created_at)
            }
            for wo in existing_wos
        ]

        # Get AI decision from LLM provider
        logger.info(f"Calling {self.llm_provider.get_provider_name()} for decision")

        ai_response = await self.llm_provider.get_decision(
            machine_data,
            maintenance_history_data,
            existing_wo_data
        )

        logger.info(
            f"AI Decision received: {ai_response.decision} "
            f"(confidence: {ai_response.confidence})"
        )

        # Prepare input context for audit
        input_context = {
            "machine": machine_data,
            "maintenance_history": maintenance_history_data,
            "existing_work_orders": existing_wo_data,
            "decision_timestamp": datetime.now().isoformat()
        }

        # Determine if decision requires review
        requires_review = ai_response.confidence < self.settings.CONFIDENCE_THRESHOLD

        # Store decision in database
        ai_decision = AIDecision(
            machine_id=machine_id,
            decision=ai_response.decision,
            priority=ai_response.priority,
            confidence=float(ai_response.confidence),
            explanation=ai_response.explanation,
            input_context=json.dumps(input_context, indent=2),
            llm_provider=self.llm_provider.get_provider_name(),
            llm_model=self.llm_provider.get_model_name(),
            raw_response=json.dumps(ai_response.model_dump(), indent=2),
            auto_executed=False,  # Will be updated if action is executed
            requires_review=requires_review
        )

        self.db.add(ai_decision)
        self.db.commit()
        self.db.refresh(ai_decision)

        logger.info(f"AI decision saved with ID: {ai_decision.id}")

        # Determine if action should be auto-executed
        can_auto_execute = (
            not requires_review and
            ai_response.confidence >= self.settings.CONFIDENCE_THRESHOLD
        )

        result = {
            "ai_decision": ai_decision,
            "can_auto_execute": can_auto_execute,
            "requires_review": requires_review,
            "confidence_threshold": self.settings.CONFIDENCE_THRESHOLD,
            "machine_data": machine_data
        }

        if requires_review:
            logger.warning(
                f"Decision requires manual review - confidence {ai_response.confidence} "
                f"is below threshold {self.settings.CONFIDENCE_THRESHOLD}"
            )

        return result

    async def execute_decision(
        self,
        ai_decision_id: int,
        force: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Execute an AI decision (create work order, send notification, etc.).

        Args:
            ai_decision_id: AI decision database ID
            force: Force execution even if confidence is low

        Returns:
            Dictionary with execution results or None if decision is WAIT
        """
        logger.info(f"Executing AI decision ID: {ai_decision_id}")

        # Fetch AI decision
        ai_decision = (
            self.db.query(AIDecision)
            .filter(AIDecision.id == ai_decision_id)
            .first()
        )

        if not ai_decision:
            raise ValueError(f"AI decision with ID {ai_decision_id} not found")

        # Check if already executed
        if ai_decision.auto_executed:
            logger.warning(f"AI decision {ai_decision_id} was already executed")
            return {"status": "already_executed", "ai_decision_id": ai_decision_id}

        # Check confidence threshold
        if not force and ai_decision.requires_review:
            raise ValueError(
                f"AI decision requires manual review (confidence: {ai_decision.confidence}). "
                f"Use force=True to execute anyway."
            )

        result = {}

        # Execute based on decision type
        if ai_decision.decision == "CREATE_WORK_ORDER":
            result = await self._create_work_order_from_decision(ai_decision)

        elif ai_decision.decision == "SEND_NOTIFICATION":
            result = await self._send_notification_from_decision(ai_decision)

        elif ai_decision.decision == "WAIT":
            logger.info("Decision is WAIT - no action required")
            result = {"status": "wait", "message": "No action required"}

        # Mark decision as executed
        ai_decision.auto_executed = True
        self.db.commit()

        logger.info(f"AI decision {ai_decision_id} executed successfully")

        return result

    async def _create_work_order_from_decision(
        self,
        ai_decision: AIDecision
    ) -> Dict[str, Any]:
        """Create a work order based on AI decision"""
        from .work_order_service import WorkOrderService
        from ..schemas.work_order import WorkOrderCreate

        wo_service = WorkOrderService(self.db)

        # Create work order
        wo_data = WorkOrderCreate(
            machine_id=ai_decision.machine_id,
            creation_source="AI",
            ai_decision_id=ai_decision.id,
            priority=ai_decision.priority,
            status="Pending_Approval",
            notes=f"AI-generated work order. {ai_decision.explanation}"
        )

        work_order = wo_service.create_work_order(wo_data)

        logger.info(f"Created work order {work_order.wo_number} from AI decision")

        return {
            "status": "work_order_created",
            "work_order_id": work_order.id,
            "wo_number": work_order.wo_number
        }

    async def _send_notification_from_decision(
        self,
        ai_decision: AIDecision
    ) -> Dict[str, Any]:
        """Send notification based on AI decision"""
        from .notification_service import NotificationService

        machine = self.db.query(Machine).filter(
            Machine.id == ai_decision.machine_id
        ).first()

        if not machine:
            logger.error(f"Machine not found for AI decision {ai_decision.id}")
            return {
                "status": "error",
                "message": "Machine not found"
            }

        # Find the approved work order for this machine
        work_order = self.db.query(WorkOrder).filter(
            WorkOrder.machine_id == ai_decision.machine_id,
            WorkOrder.status == "Approved"
        ).first()

        if not work_order:
            logger.warning(
                f"No approved work order found for machine {machine.machine_id}. "
                "Creating notification anyway."
            )
            # If no approved WO, try to find any active WO
            work_order = self.db.query(WorkOrder).filter(
                WorkOrder.machine_id == ai_decision.machine_id,
                WorkOrder.status.in_(["Pending_Approval", "Draft"])
            ).first()

        if not work_order:
            logger.error(f"No work order found for machine {machine.machine_id}")
            return {
                "status": "error",
                "message": "No work order found to notify about"
            }

        # Send notification using NotificationService
        notification_service = NotificationService()

        # Prepare AI context for email
        ai_context = {
            "explanation": ai_decision.explanation,
            "confidence": ai_decision.confidence
        }

        if work_order.status == "Approved":
            success = await notification_service.send_approval_notification(machine, work_order)
        else:
            success = await notification_service.send_work_order_notification(
                machine,
                work_order,
                additional_context=ai_context
            )

        # Update notification tracking if email sent successfully
        if success:
            from .work_order_service import WorkOrderService
            wo_service = WorkOrderService(self.db)
            wo_service.mark_notification_sent(work_order.id)

        logger.info(
            f"Notification {'sent' if success else 'failed'} to {machine.supplier_email} "
            f"for machine {machine.machine_id}, WO {work_order.wo_number}"
        )

        return {
            "status": "notification_sent" if success else "notification_failed",
            "recipient": machine.supplier_email,
            "machine_id": machine.machine_id,
            "wo_number": work_order.wo_number,
            "email_sent": success
        }

    def get_recent_decisions(
        self,
        limit: int = 20,
        machine_id: Optional[int] = None
    ) -> list:
        """
        Get recent AI decisions for audit.

        Args:
            limit: Maximum number of decisions to return
            machine_id: Optional filter by machine ID

        Returns:
            List of AIDecision objects
        """
        query = self.db.query(AIDecision)

        if machine_id:
            query = query.filter(AIDecision.machine_id == machine_id)

        decisions = query.order_by(AIDecision.created_at.desc()).limit(limit).all()

        return decisions
