from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import logging
from ..models.work_order import WorkOrder
from ..models.machine import Machine
from ..models.maintenance_history import MaintenanceHistory
from ..schemas.work_order import WorkOrderCreate, WorkOrderUpdate

logger = logging.getLogger(__name__)


class WorkOrderService:
    """Service class for work order-related business logic"""

    def __init__(self, db: Session):
        self.db = db

    def get_all_work_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        machine_id: Optional[int] = None,
        creation_source: Optional[str] = None
    ) -> List[WorkOrder]:
        """
        Get all work orders with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            machine_id: Filter by machine ID
            creation_source: Filter by creation source (AI/Manual)

        Returns:
            List of WorkOrder objects with machine_name attribute
        """
        query = self.db.query(WorkOrder, Machine.name.label('machine_name')).join(
            Machine, WorkOrder.machine_id == Machine.id
        )

        if status:
            query = query.filter(WorkOrder.status == status)

        if machine_id:
            query = query.filter(WorkOrder.machine_id == machine_id)

        if creation_source:
            query = query.filter(WorkOrder.creation_source == creation_source)

        results = query.order_by(WorkOrder.created_at.desc()).offset(skip).limit(limit).all()

        # Add machine_name attribute to each WorkOrder object
        work_orders = []
        for wo, machine_name in results:
            wo.machine_name = machine_name
            work_orders.append(wo)

        return work_orders

    def get_work_order_by_id(self, wo_id: int) -> Optional[WorkOrder]:
        """
        Get a work order by ID.

        Args:
            wo_id: Work order database ID

        Returns:
            WorkOrder object or None
        """
        return self.db.query(WorkOrder).filter(WorkOrder.id == wo_id).first()

    def get_work_order_by_wo_number(self, wo_number: str) -> Optional[WorkOrder]:
        """
        Get a work order by WO number.

        Args:
            wo_number: Work order number (e.g., WO-2024-001)

        Returns:
            WorkOrder object or None
        """
        return self.db.query(WorkOrder).filter(WorkOrder.wo_number == wo_number).first()

    def create_work_order(self, wo_data: WorkOrderCreate) -> WorkOrder:
        """
        Create a new work order.

        Args:
            wo_data: Work order creation data

        Returns:
            Created WorkOrder object
        """
        # Generate WO number
        wo_number = self._generate_wo_number()

        db_wo = WorkOrder(
            wo_number=wo_number,
            **wo_data.model_dump()
        )

        self.db.add(db_wo)
        self.db.commit()
        self.db.refresh(db_wo)
        return db_wo

    def update_work_order(self, wo_id: int, wo_data: WorkOrderUpdate) -> Optional[WorkOrder]:
        """
        Update an existing work order.

        Args:
            wo_id: Work order database ID
            wo_data: Work order update data

        Returns:
            Updated WorkOrder object or None
        """
        db_wo = self.get_work_order_by_id(wo_id)
        if not db_wo:
            return None

        update_data = wo_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_wo, field, value)

        self.db.commit()
        self.db.refresh(db_wo)
        return db_wo

    def approve_work_order(self, wo_id: int, approved_by: str) -> Optional[WorkOrder]:
        """
        Approve a work order.

        Args:
            wo_id: Work order database ID
            approved_by: Name of approver

        Returns:
            Updated WorkOrder object or None
        """
        db_wo = self.get_work_order_by_id(wo_id)
        if not db_wo:
            return None

        db_wo.status = "Approved"
        db_wo.approved_at = datetime.now()
        db_wo.approved_by = approved_by

        self.db.commit()
        self.db.refresh(db_wo)
        return db_wo

    def complete_work_order(self, wo_id: int) -> Optional[WorkOrder]:
        """
        Mark work order as completed and update machine's PM schedule.

        Args:
            wo_id: Work order database ID

        Returns:
            Updated WorkOrder object or None
        """
        db_wo = self.get_work_order_by_id(wo_id)
        if not db_wo:
            return None

        # Update work order status
        today = datetime.now().date()
        db_wo.status = "Completed"
        db_wo.completed_date = today

        # Update machine's PM schedule
        machine = self.db.query(Machine).filter(Machine.id == db_wo.machine_id).first()
        if machine:
            # Update last PM date to today
            machine.last_pm_date = today

            # Calculate next PM date based on scheduled_date + frequency
            # Use scheduled_date if available, otherwise use today
            base_date = db_wo.scheduled_date if db_wo.scheduled_date else today
            next_pm_date = self._calculate_next_pm_date(base_date, machine.pm_frequency)
            machine.next_pm_date = next_pm_date

            logger.info(
                f"Updated PM schedule for machine {machine.machine_id}: "
                f"last_pm_date={today}, next_pm_date={next_pm_date} "
                f"(calculated from scheduled_date={base_date}), "
                f"frequency={machine.pm_frequency}"
            )

            # Create maintenance history record
            maintenance_record = MaintenanceHistory(
                machine_id=db_wo.machine_id,
                maintenance_date=today,
                maintenance_type="Preventive",
                notes=f"Completed work order {db_wo.wo_number}. {db_wo.notes or ''}".strip(),
                performed_by=machine.assigned_supplier,
                work_order_id=db_wo.id
            )
            self.db.add(maintenance_record)

            logger.info(
                f"Created maintenance history record for machine {machine.machine_id}, "
                f"WO {db_wo.wo_number}"
            )

        self.db.commit()
        self.db.refresh(db_wo)
        return db_wo

    def cancel_work_order(self, wo_id: int) -> Optional[WorkOrder]:
        """
        Cancel a work order.

        Args:
            wo_id: Work order database ID

        Returns:
            Updated WorkOrder object or None
        """
        db_wo = self.get_work_order_by_id(wo_id)
        if not db_wo:
            return None

        db_wo.status = "Cancelled"

        self.db.commit()
        self.db.refresh(db_wo)
        return db_wo

    def mark_notification_sent(self, wo_id: int) -> Optional[WorkOrder]:
        """
        Mark that notification has been sent for a work order.

        Args:
            wo_id: Work order database ID

        Returns:
            Updated WorkOrder object or None
        """
        db_wo = self.get_work_order_by_id(wo_id)
        if not db_wo:
            return None

        db_wo.notification_sent = True
        db_wo.notification_sent_at = datetime.now()

        self.db.commit()
        self.db.refresh(db_wo)
        return db_wo

    def get_active_work_orders_for_machine(self, machine_id: int) -> List[WorkOrder]:
        """
        Get active work orders for a specific machine.

        Args:
            machine_id: Machine database ID

        Returns:
            List of active WorkOrder objects
        """
        return (
            self.db.query(WorkOrder)
            .filter(
                WorkOrder.machine_id == machine_id,
                WorkOrder.status.in_(["Draft", "Pending_Approval", "Approved"])
            )
            .order_by(WorkOrder.created_at.desc())
            .all()
        )

    def _calculate_next_pm_date(self, from_date, pm_frequency: str):
        """
        Calculate the next PM date based on frequency.

        Args:
            from_date: Starting date (usually today/completion date)
            pm_frequency: PM frequency ("Monthly", "Bimonthly", "Yearly")

        Returns:
            Next PM date
        """
        frequency_days = {
            "Monthly": 30,
            "Bimonthly": 60,
            "Quarterly": 90,
            "Yearly": 365
        }

        days_to_add = frequency_days.get(pm_frequency, 30)  # Default to 30 days if unknown

        next_date = from_date + timedelta(days=days_to_add)

        logger.debug(
            f"Calculated next PM date: from_date={from_date}, "
            f"frequency={pm_frequency}, days_to_add={days_to_add}, "
            f"next_date={next_date}"
        )

        return next_date

    def _generate_wo_number(self) -> str:
        """
        Generate a unique work order number.

        Format: WO-YYYY-NNNN

        Returns:
            Generated WO number
        """
        year = datetime.now().year
        prefix = f"WO-{year}-"

        # Get the latest WO number for this year
        latest_wo = (
            self.db.query(WorkOrder)
            .filter(WorkOrder.wo_number.like(f"{prefix}%"))
            .order_by(WorkOrder.wo_number.desc())
            .first()
        )

        if latest_wo:
            # Extract the sequence number and increment
            try:
                seq_num = int(latest_wo.wo_number.split("-")[-1]) + 1
            except (ValueError, IndexError):
                seq_num = 1
        else:
            seq_num = 1

        return f"{prefix}{seq_num:04d}"
