from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional
from ..models.machine import Machine
from ..models.maintenance_history import MaintenanceHistory
from ..schemas.machine import MachineCreate, MachineUpdate
from ..config import get_settings


class MachineService:
    """Service class for machine-related business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def get_all_machines(
        self,
        skip: int = 0,
        limit: int = 100,
        pm_status: Optional[str] = None,
        location: Optional[str] = None
    ) -> List[Machine]:
        """
        Get all machines with optional filtering.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            pm_status: Filter by PM status (overdue, due_soon, ok)
            location: Filter by location

        Returns:
            List of Machine objects
        """
        query = self.db.query(Machine)

        # Filter by location if provided
        if location:
            query = query.filter(Machine.location == location)

        # SQL Server requires ORDER BY when using OFFSET/LIMIT
        query = query.order_by(Machine.id)

        # If pm_status filter is requested, we need to filter after fetching
        # because pm_status is calculated in Python, not stored in database
        if pm_status:
            # Fetch all machines (without limit) to filter by pm_status
            all_machines = query.all()

            # Filter by PM status and collect with days_until_pm for sorting
            filtered_machines = []
            for machine in all_machines:
                machine_pm_status = self.calculate_pm_status(machine.next_pm_date)
                days_until = self.calculate_days_until_pm(machine.next_pm_date)
                if pm_status == "due_soon,overdue":
                    if machine_pm_status in ["due_soon", "overdue"]:
                        filtered_machines.append((machine, days_until))
                elif machine_pm_status == pm_status:
                    filtered_machines.append((machine, days_until))

            # Sort by days_until_pm ascending (overdue machines with negative values appear first)
            filtered_machines.sort(key=lambda x: x[1])

            # Extract machines only and apply skip and limit
            sorted_machines = [machine for machine, _ in filtered_machines]
            return sorted_machines[skip:skip + limit]

        # No pm_status filter, apply skip and limit directly in SQL
        machines = query.offset(skip).limit(limit).all()
        return machines

    def get_machine_by_id(self, machine_id: int) -> Optional[Machine]:
        """
        Get a machine by ID.

        Args:
            machine_id: Machine database ID

        Returns:
            Machine object or None
        """
        return self.db.query(Machine).filter(Machine.id == machine_id).first()

    def get_machine_by_machine_id(self, machine_id: str) -> Optional[Machine]:
        """
        Get a machine by machine_id (e.g., MACH-001).

        Args:
            machine_id: Machine identifier string

        Returns:
            Machine object or None
        """
        return self.db.query(Machine).filter(Machine.machine_id == machine_id).first()

    def create_machine(self, machine_data: MachineCreate) -> Machine:
        """
        Create a new machine.

        Args:
            machine_data: Machine creation data

        Returns:
            Created Machine object
        """
        db_machine = Machine(**machine_data.model_dump())
        self.db.add(db_machine)
        self.db.commit()
        self.db.refresh(db_machine)
        return db_machine

    def update_machine(self, machine_id: int, machine_data: MachineUpdate) -> Optional[Machine]:
        """
        Update an existing machine.

        Args:
            machine_id: Machine database ID
            machine_data: Machine update data

        Returns:
            Updated Machine object or None
        """
        db_machine = self.get_machine_by_id(machine_id)
        if not db_machine:
            return None

        update_data = machine_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_machine, field, value)

        self.db.commit()
        self.db.refresh(db_machine)
        return db_machine

    def delete_machine(self, machine_id: int) -> bool:
        """
        Delete a machine.

        Args:
            machine_id: Machine database ID

        Returns:
            True if deleted, False if not found
        """
        db_machine = self.get_machine_by_id(machine_id)
        if not db_machine:
            return False

        self.db.delete(db_machine)
        self.db.commit()
        return True

    def get_maintenance_history(
        self,
        machine_id: int,
        limit: int = 10
    ) -> List[MaintenanceHistory]:
        """
        Get maintenance history for a machine.

        Args:
            machine_id: Machine database ID
            limit: Maximum number of records to return

        Returns:
            List of MaintenanceHistory objects
        """
        return (
            self.db.query(MaintenanceHistory)
            .filter(MaintenanceHistory.machine_id == machine_id)
            .order_by(MaintenanceHistory.maintenance_date.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def calculate_pm_status(next_pm_date: date) -> str:
        """
        Calculate PM status based on next PM date.

        Args:
            next_pm_date: Next scheduled PM date

        Returns:
            Status string: 'overdue', 'due_soon', or 'ok'
        """
        today = datetime.now().date()
        days_until = (next_pm_date - today).days

        if days_until < 0:
            return "overdue"
        elif days_until <= 30:
            return "due_soon"
        else:
            return "ok"

    @staticmethod
    def calculate_days_until_pm(next_pm_date: date) -> int:
        """
        Calculate days until PM (negative if overdue).

        Args:
            next_pm_date: Next scheduled PM date

        Returns:
            Number of days (negative if overdue)
        """
        today = datetime.now().date()
        return (next_pm_date - today).days

    def enrich_machine_data(self, machine: Machine) -> dict:
        """
        Enrich machine object with calculated PM status and days until PM.

        Args:
            machine: Machine object

        Returns:
            Dictionary with enriched machine data
        """
        pm_status = self.calculate_pm_status(machine.next_pm_date)
        days_until_pm = self.calculate_days_until_pm(machine.next_pm_date)

        return {
            **machine.__dict__,
            "pm_status": pm_status,
            "days_until_pm": days_until_pm
        }

    def get_machines_due_for_pm(self, days_threshold: int = 30) -> List[Machine]:
        """
        Get machines that are due for PM within the threshold.
        Results are ordered by days_until_pm (ascending) so overdue machines appear first.

        Args:
            days_threshold: Number of days to look ahead

        Returns:
            List of machines due for PM, ordered by urgency (overdue first)
        """
        today = datetime.now().date()
        machines = self.db.query(Machine).all()

        due_machines = []
        for machine in machines:
            days_until = self.calculate_days_until_pm(machine.next_pm_date)
            if days_until <= days_threshold:
                due_machines.append((machine, days_until))

        # Sort by days_until_pm ascending (negative values first = overdue machines first)
        due_machines.sort(key=lambda x: x[1])

        # Return only the machine objects, not the tuples
        return [machine for machine, _ in due_machines]
