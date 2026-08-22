"""
Schemas for the demo reset page.

The interesting part is DemoResetRequest.check_machine_budget: the counts are
individually plausible but only coherent together, so the cross-field check is
where a bad request is actually caught.
"""

from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Dict

from ..services.demo_seed_service import (
    DEFAULT_MACHINE_COUNT,
    DEFAULT_RESERVE_OVERDUE_WITHOUT_WO,
    DEFAULT_STATUS_COUNTS,
    OPEN_STATUSES,
    STATUS_ORDER,
)

# A cap rather than a limit that means anything: the reset runs synchronously
# through the ORM, and 500 machines is already several thousand inserts and
# tens of seconds. Past that a demo reset wants to be a background job.
MAX_MACHINES = 500
MAX_PER_STATUS = 500


class DemoResetRequest(BaseModel):
    """The form the reset page submits."""

    admin_email: EmailStr = Field(
        ...,
        description="Written to every seeded machine's admin_email -- receives "
                    "the work order approval notice"
    )
    supplier_email: EmailStr = Field(
        ...,
        description="Written to every seeded machine's supplier_email -- "
                    "receives the supplier notification"
    )

    machine_count: int = Field(
        DEFAULT_MACHINE_COUNT, ge=1, le=MAX_MACHINES,
        description="How many machines to create"
    )
    reserve_overdue_without_wo: int = Field(
        DEFAULT_RESERVE_OVERDUE_WITHOUT_WO, ge=0, le=MAX_MACHINES,
        description="Leave this many of the most-overdue machines with no work "
                    "order, so a live 'AI raises a work order' demo has a target"
    )

    draft: int = Field(DEFAULT_STATUS_COUNTS["Draft"], ge=0, le=MAX_PER_STATUS)
    pending_approval: int = Field(
        DEFAULT_STATUS_COUNTS["Pending_Approval"], ge=0, le=MAX_PER_STATUS
    )
    approved: int = Field(DEFAULT_STATUS_COUNTS["Approved"], ge=0, le=MAX_PER_STATUS)
    completed: int = Field(DEFAULT_STATUS_COUNTS["Completed"], ge=0, le=MAX_PER_STATUS)
    cancelled: int = Field(DEFAULT_STATUS_COUNTS["Cancelled"], ge=0, le=MAX_PER_STATUS)

    def status_counts(self) -> Dict[str, int]:
        """Keyed the way the database stores status, in creation order."""
        return {
            "Draft": self.draft,
            "Pending_Approval": self.pending_approval,
            "Approved": self.approved,
            "Completed": self.completed,
            "Cancelled": self.cancelled,
        }

    @model_validator(mode="after")
    def check_machine_budget(self) -> "DemoResetRequest":
        """
        Every open work order needs a machine of its own -- that is the
        invariant WorkOrderService enforces when it refuses a duplicate -- and
        the reserved overdue machines are held back from that pool. Closed
        orders are history and may share a machine freely, so they do not count.

        Rejecting here rather than in the service means the page gets a 422 with
        the real numbers instead of a reset that silently produces fewer orders
        than asked for.
        """
        if self.reserve_overdue_without_wo >= self.machine_count:
            raise ValueError(
                f"Holding back {self.reserve_overdue_without_wo} of "
                f"{self.machine_count} machines leaves none to raise work "
                f"orders against."
            )

        open_orders = self.draft + self.pending_approval + self.approved
        available = self.machine_count - self.reserve_overdue_without_wo

        if open_orders > available:
            raise ValueError(
                f"{open_orders} open work orders (Draft + Pending Approval + "
                f"Approved) need one machine each, but only {available} of "
                f"{self.machine_count} machines are available after holding "
                f"back {self.reserve_overdue_without_wo} overdue."
            )

        return self


class DemoResetDefaults(BaseModel):
    """
    What the page prefills with when the browser has nothing remembered, plus
    what is in the database right now so the operator can see what they are
    about to delete.
    """

    admin_email: str
    supplier_email: str
    machine_count: int
    reserve_overdue_without_wo: int
    status_counts: Dict[str, int]
    current_row_counts: Dict[str, int]
    max_machines: int = MAX_MACHINES
    max_per_status: int = MAX_PER_STATUS
    status_order: list = Field(default_factory=lambda: list(STATUS_ORDER))
    open_statuses: list = Field(default_factory=lambda: list(OPEN_STATUSES))


class DemoResetResponse(BaseModel):
    """What the reset produced. Every number is counted after the commit."""

    machines: int
    maintenance_history: int
    work_orders: int
    ai_decisions: int
    workflow_logs: int
    work_orders_by_status: Dict[str, int]
    machines_by_pm_status: Dict[str, int]
    ai_sourced_orders: int
    decisions_below_threshold: int
    overdue_machines_without_open_wo: int
    workflow_logs_cleared: bool
    elapsed_seconds: float
