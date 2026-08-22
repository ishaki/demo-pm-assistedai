"""
Demo reset and reseed -- the single implementation of the demo data set.

This module owns the constants and the generators that produce the demo estate:
machines with plausible PM windows, their maintenance history, and work orders
spread across every lifecycle status with the AI decisions that raised them.

WHO CALLS IT
  - scripts/seed_data.py        -> seed_machines()
  - scripts/seed_work_orders.py -> seed_work_orders()
  - routers/admin.py            -> reset_and_seed()   (the demo reset page)

The two scripts used to carry their own copy of all of this. They are now thin
CLI wrappers, so the reset page and the command line cannot produce different
data.

scripts/reset_and_seed.sql is a third, deliberately independent implementation
in T-SQL, for running from SSMS with no Python or backend available. It is not
generated from this module and does not import it -- see its header comment.

TRANSACTIONS
  Nothing here commits except reset_and_seed(). The generators flush, so that
  ids are available to the next step, and leave the commit to their caller.
  That is what lets reset_and_seed() delete and reseed inside a single
  transaction: a failure part way through rolls back to the estate you started
  with rather than stranding the demo half-built.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import json
import logging
import random

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AIDecision, Machine, MaintenanceHistory, WorkOrder, WorkflowLog

logger = logging.getLogger(__name__)


# ============================================================================
# Reference data
# ============================================================================

# Supplier names only. Every seeded machine's supplier_email comes from the one
# configured address, the same way the demo estate has always pointed at a
# single mailbox -- carrying a per-supplier email here would imply a variation
# the data has never had.
SUPPLIER_NAMES = [
    "TechServ Inc", "MainCo Solutions", "FixIt Pro", "Industrial Care",
    "MachineGuard", "ProMaintain", "QuickFix Ltd", "ReliaTech",
    "ServiceMax", "EliteMaint",
]

FREQUENCIES = ["Monthly", "Bimonthly", "Yearly"]

# The interval WorkOrderService._calculate_next_pm_date uses.
FREQUENCY_DAYS = {"Monthly": 30, "Bimonthly": 60, "Yearly": 365}

LOCATIONS = ["Zone A", "Zone B", "Zone C", "Zone D", "Zone E"]

MACHINE_TYPES = [
    "CNC Mill", "Lathe", "Press", "Grinder", "Welder",
    "Conveyor", "Robot Arm", "Drill Press", "Band Saw",
    "Plasma Cutter", "Assembly Line", "Packaging Machine",
]

MAINTENANCE_TYPES = ["Preventive", "Corrective", "Inspection"]

MAINTENANCE_NOTES = [
    "Regular maintenance performed. All systems operational.",
    "Routine inspection completed. No issues found.",
    "Preventive maintenance completed successfully.",
    "Parts lubricated and checked. Running smoothly.",
    "Comprehensive service performed. Machine in good condition.",
    "Scheduled maintenance completed. Performance optimal.",
    "Inspection and minor adjustments completed.",
]

APPROVERS = [
    "m.reyes@innoark.com",
    "s.tan@innoark.com",
    "j.okafor@innoark.com",
    "planning@innoark.com",
]

# Explanations are written the way the LLM returns them: a reason grounded in
# the machine's own PM window and history, not a generic template.
AI_EXPLANATIONS = {
    "overdue": [
        "Next PM date passed {days} days ago and no open work order exists. "
        "The machine runs on a {freq} cycle, so the window is already a full "
        "interval behind. Raising a work order at High priority.",
        "PM is {days} days overdue on a {freq} schedule. The last three "
        "history entries were all routine preventive visits with no faults "
        "logged, so this is a lapsed schedule rather than a developing issue.",
        "Overdue by {days} days. {supplier} handled the previous service on "
        "this asset and holds the {freq} contract, so assigning back to them "
        "keeps the service record continuous.",
    ],
    "due_soon": [
        "Next PM falls in {days} days, inside the {window}-day planning "
        "window. Scheduling now gives {supplier} lead time to confirm before "
        "the date arrives.",
        "PM due in {days} days on a {freq} cycle. History shows the previous "
        "visit closed cleanly, so a standard preventive scope is enough.",
        "Due in {days} days. Raising early at Medium priority so the visit can "
        "be batched with the other {location} assets falling due the same week.",
    ],
    "ok": [
        "Next PM is {days} days out, beyond the {window}-day window, but the "
        "last visit logged a corrective repair. Raising a follow-up inspection "
        "at Low priority to confirm the fix held.",
        "Not yet due -- {days} days remain. Raising a Low priority order "
        "against a maintenance note from the previous {freq} visit.",
    ],
}

COMPLETION_NOTES = [
    "PM completed. Filters and belts replaced, no faults found.",
    "PM completed. Lubrication and alignment checked, within tolerance.",
    "PM completed. Worn seal replaced during the visit; asset returned to "
    "service the same day.",
    "PM completed. All checks passed, next cycle confirmed with the supplier.",
]

CANCEL_NOTES = [
    "Cancelled -- machine was taken offline for a line reconfiguration before "
    "the visit; PM will be re-raised once it is back in service.",
    "Cancelled -- duplicate of an order already raised for the same PM window.",
    "Cancelled -- supplier could not meet the window and the schedule was "
    "moved to the next cycle.",
    "Cancelled -- PM was completed during an unrelated corrective visit, so "
    "the scheduled work is no longer needed.",
]


# ============================================================================
# Configuration
# ============================================================================

# Work order statuses, in the order they are created -- which is the order
# wo_number is handed out in, so WO-YYYY-0001 is the first one of the first
# non-empty status.
STATUS_ORDER = ["Draft", "Pending_Approval", "Approved", "Completed", "Cancelled"]

# A machine holds at most one of these. WorkOrderService enforces the same set
# when it refuses to raise a duplicate.
OPEN_STATUSES = ("Draft", "Pending_Approval", "Approved")

DEFAULT_MACHINE_COUNT = 75

# Leave this many of the most-overdue machines with no work order at all.
#
# 0 is what the original seed scripts did, and it costs you a demo: open orders
# are handed out overdue-first, so with 27 of them and 15 overdue machines every
# overdue machine ends up covered. The dashboard then shows Overdue = 0, and a
# live "AI raises a work order" has nothing to act on -- the create endpoint
# answers 409 for every machine that already has an open order.
DEFAULT_RESERVE_OVERDUE_WITHOUT_WO = 5

# Draft is 0 on purpose: nothing in the running application creates a Draft
# work order. ai_service.py passes status="Pending_Approval", and so does the
# n8n Create Work Order node. The only Draft default is the one on
# WorkOrderCreate, which neither caller exercises -- so seeding Drafts invents
# rows in a state the system itself cannot reach. The 6 the original script
# produced are folded into Pending_Approval here.
#
# It does not change how the AI treats them either way: the system prompt in
# llm_providers/base.py says "WAIT: If ANY work order has status
# Pending_Approval or Draft", so both block a new order identically.
DEFAULT_STATUS_COUNTS = {
    "Draft": 0,
    "Pending_Approval": 15,
    "Approved": 12,
    "Completed": 14,
    "Cancelled": 4,
}


@dataclass
class DemoSeedConfig:
    """Everything the demo reset page can vary."""

    admin_email: str
    supplier_email: str
    machine_count: int = DEFAULT_MACHINE_COUNT
    reserve_overdue_without_wo: int = DEFAULT_RESERVE_OVERDUE_WITHOUT_WO
    status_counts: Dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_STATUS_COUNTS)
    )

    @classmethod
    def defaults(cls) -> "DemoSeedConfig":
        """The config the reset page prefills with, emails from settings."""
        settings = get_settings()
        return cls(
            admin_email=settings.DEMO_ADMIN_EMAIL,
            supplier_email=settings.DEMO_SUPPLIER_EMAIL,
        )

    @property
    def open_order_count(self) -> int:
        return sum(self.status_counts.get(s, 0) for s in OPEN_STATUSES)

    @property
    def total_order_count(self) -> int:
        return sum(self.status_counts.get(s, 0) for s in STATUS_ORDER)

    def validate(self) -> None:
        """
        Raise ValueError if the numbers cannot produce a coherent estate.

        The binding constraint is machines, not work orders: every open order
        needs a machine of its own, and the reserved overdue machines are held
        back from that pool.
        """
        if self.machine_count < 1:
            raise ValueError("machine_count must be at least 1")

        if self.reserve_overdue_without_wo < 0:
            raise ValueError("reserve_overdue_without_wo cannot be negative")

        for status, count in self.status_counts.items():
            if status not in STATUS_ORDER:
                raise ValueError(
                    f"Unknown work order status '{status}'. "
                    f"Expected one of: {', '.join(STATUS_ORDER)}"
                )
            if count < 0:
                raise ValueError(f"{status} count cannot be negative")

        available = self.machine_count - self.reserve_overdue_without_wo
        if available < 0:
            raise ValueError(
                f"Holding back {self.reserve_overdue_without_wo} overdue machines "
                f"leaves nothing of {self.machine_count} machines to raise work "
                f"orders against."
            )

        if self.open_order_count > available:
            raise ValueError(
                f"{self.open_order_count} open work orders (Draft + Pending "
                f"Approval + Approved) need one machine each, but only "
                f"{available} of {self.machine_count} machines are available "
                f"after holding back {self.reserve_overdue_without_wo} overdue. "
                f"Lower the open counts, raise the machine count, or reduce the "
                f"overdue reserve."
            )


@dataclass
class DemoResetResult:
    """What a reset actually produced, for the page to report back."""

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


# ============================================================================
# Machines and maintenance history
# ============================================================================

def seed_machines(db: Session, config: DemoSeedConfig) -> List[Machine]:
    """
    Create the machine estate, spread across the three PM buckets.

    The distribution is 20% overdue and 33% due soon, with the remainder OK.
    Both are truncated, so 75 machines gives 15 / 24 / 36 -- the numbers the
    original seed_data.py produced. Machines are numbered in bucket order, so
    MACH-001 upwards are the overdue ones.

    Flushes but does not commit; the returned machines carry their ids.
    """
    today = datetime.now().date()
    now = datetime.now()
    count = config.machine_count

    overdue_count = int(count * 0.20)
    due_soon_count = int(count * 0.33)
    ok_count = count - overdue_count - due_soon_count

    logger.info(
        "Generating %d machines: %d overdue, %d due soon, %d ok",
        count, overdue_count, due_soon_count, ok_count,
    )

    machines: List[Machine] = []

    for index in range(count):
        if index < overdue_count:
            next_pm = today - timedelta(days=random.randint(1, 60))
        elif index < overdue_count + due_soon_count:
            next_pm = today + timedelta(days=random.randint(1, 30))
        else:
            next_pm = today + timedelta(days=random.randint(31, 365))

        frequency = random.choice(FREQUENCIES)
        location = random.choice(LOCATIONS)
        number = index + 1

        machines.append(Machine(
            machine_id=f"MACH-{number:03d}",
            name=f"{random.choice(MACHINE_TYPES)} {number}",
            description=f"Production machine in {location}",
            location=location,
            pm_frequency=frequency,
            last_pm_date=next_pm - timedelta(days=FREQUENCY_DAYS[frequency]),
            next_pm_date=next_pm,
            assigned_supplier=random.choice(SUPPLIER_NAMES),
            supplier_email=config.supplier_email,
            admin_email=config.admin_email,
            status="Active",
            created_at=now,
            updated_at=now,
        ))

    db.add_all(machines)
    db.flush()  # assigns the ids the history rows point at

    history = _build_maintenance_history(machines, today, now)
    db.add_all(history)
    db.flush()

    logger.info(
        "Generated %d machines and %d maintenance history records",
        len(machines), len(history),
    )
    return machines


def _build_maintenance_history(
    machines: List[Machine], today, now
) -> List[MaintenanceHistory]:
    """3 to 8 past visits per machine, reaching back 30 days to 2 years."""
    records: List[MaintenanceHistory] = []

    for machine in machines:
        for _ in range(random.randint(3, 8)):
            records.append(MaintenanceHistory(
                machine_id=machine.id,
                maintenance_date=today - timedelta(days=random.randint(30, 730)),
                maintenance_type=random.choice(MAINTENANCE_TYPES),
                notes=random.choice(MAINTENANCE_NOTES),
                performed_by=random.choice(SUPPLIER_NAMES),
                created_at=now,
            ))

    return records


# ============================================================================
# Work orders and the AI decisions behind them
# ============================================================================

def _pm_bucket(machine: Machine, today, window: int):
    """Classify a machine the way the dashboard does: overdue, due soon, or ok."""
    days = (machine.next_pm_date - today).days
    if days < 0:
        return "overdue", days
    if days <= window:
        return "due_soon", days
    return "ok", days


def _priority_for(bucket: str) -> str:
    """Priority follows urgency, with the occasional bump a planner would make."""
    if bucket == "overdue":
        return random.choices(["High", "Medium"], weights=[85, 15])[0]
    if bucket == "due_soon":
        return random.choices(["Medium", "High", "Low"], weights=[70, 15, 15])[0]
    return random.choices(["Low", "Medium"], weights=[80, 20])[0]


def _next_wo_sequence(db: Session, year: int) -> int:
    """Continue the WO-YYYY-NNNN series rather than colliding with it."""
    prefix = f"WO-{year}-"
    latest = (
        db.query(WorkOrder)
        .filter(WorkOrder.wo_number.like(f"{prefix}%"))
        .order_by(WorkOrder.wo_number.desc())
        .first()
    )
    if not latest:
        return 1
    try:
        return int(latest.wo_number.split("-")[-1]) + 1
    except (ValueError, IndexError):
        return 1


def _build_ai_decision(
    machine: Machine, bucket: str, days: int, priority: str,
    threshold: float, window: int, created_at: datetime,
) -> AIDecision:
    """Build the AIDecision row that an AI-sourced work order hangs off."""
    explanation = random.choice(AI_EXPLANATIONS[bucket]).format(
        days=abs(days),
        freq=machine.pm_frequency.lower(),
        supplier=machine.assigned_supplier,
        location=machine.location,
        window=window,
    )

    # Overdue cases are the clear-cut ones, so they score highest. A handful of
    # decisions land under the threshold to exercise the review path.
    if bucket == "overdue":
        confidence = round(random.uniform(0.88, 0.97), 2)
    elif bucket == "due_soon":
        confidence = round(random.uniform(0.72, 0.91), 2)
    else:
        confidence = round(random.uniform(0.58, 0.76), 2)

    input_context = {
        "machine": {
            "machine_id": machine.machine_id,
            "name": machine.name,
            "location": machine.location,
            "pm_frequency": machine.pm_frequency,
            "last_pm_date": machine.last_pm_date.isoformat() if machine.last_pm_date else None,
            "next_pm_date": machine.next_pm_date.isoformat(),
            "assigned_supplier": machine.assigned_supplier,
            "days_until_pm": days,
        },
        "maintenance_history": f"{len(machine.maintenance_history)} prior records reviewed",
        "existing_work_orders": [],
        "decision_timestamp": created_at.isoformat(),
    }

    return AIDecision(
        machine_id=machine.id,
        decision="CREATE_WORK_ORDER",
        priority=priority,
        confidence=confidence,
        explanation=explanation,
        input_context=json.dumps(input_context, indent=2),
        llm_provider="OpenAI",
        llm_model="gpt-4",
        raw_response=json.dumps(
            {
                "decision": "CREATE_WORK_ORDER",
                "priority": priority,
                "confidence": confidence,
                "explanation": explanation,
            },
            indent=2,
        ),
        auto_executed=confidence >= threshold,
        requires_review=confidence < threshold,
        created_at=created_at,
    )


def seed_work_orders(
    db: Session, config: DemoSeedConfig
) -> Optional[Dict[str, int]]:
    """
    Create work orders across every configured status, plus the AI decisions
    behind the AI-sourced ones.

    Returns the per-status counts actually created, or None if there are no
    machines to raise orders against.

    Flushes but does not commit.
    """
    settings = get_settings()
    threshold = float(settings.CONFIDENCE_THRESHOLD)
    window = int(settings.PM_DUE_DAYS)
    today = datetime.now().date()
    now = datetime.now()
    year = now.year

    machines = db.query(Machine).all()
    if not machines:
        logger.error("No machines found -- seed machines before work orders.")
        return None

    # Overdue first, then due soon: the order the daily PM check would surface
    # them. Slicing off the front of the open pool is what holds the most
    # overdue machines back from getting an order at all.
    ranked = sorted(machines, key=lambda m: (m.next_pm_date, m.id))
    open_pool = list(ranked[config.reserve_overdue_without_wo:])
    history_pool = list(ranked)
    random.shuffle(history_pool)

    seq = _next_wo_sequence(db, year)
    counts: Dict[str, int] = {}

    for status in STATUS_ORDER:
        for _ in range(config.status_counts.get(status, 0)):
            # Open orders take a machine off the pool so no machine ends up
            # with two of them; closed orders may reuse any machine.
            if status in OPEN_STATUSES:
                if not open_pool:
                    logger.warning(
                        "Ran out of machines for open work orders at %s", status
                    )
                    break
                machine = open_pool.pop(0)
            else:
                if not history_pool:
                    history_pool = list(ranked)
                    random.shuffle(history_pool)
                machine = history_pool.pop()

            bucket, days = _pm_bucket(machine, today, window)
            priority = _priority_for(bucket)

            # 70% of orders come from the AI path, the rest are planner-raised.
            from_ai = random.random() < 0.70

            # Age the record so the list is not one flat timestamp. Closed
            # orders reach further back than open ones.
            age_days = (
                random.randint(20, 90)
                if status in ("Completed", "Cancelled")
                else random.randint(0, 14)
            )
            created_at = now - timedelta(days=age_days, hours=random.randint(0, 23))

            ai_decision = None
            if from_ai:
                ai_decision = _build_ai_decision(
                    machine, bucket, days, priority, threshold, window, created_at
                )
                db.add(ai_decision)
                db.flush()  # assign the id the work order refers to

            wo = WorkOrder(
                wo_number=f"WO-{year}-{seq:04d}",
                machine_id=machine.id,
                status=status,
                priority=priority,
                creation_source="AI" if from_ai else "Manual",
                ai_decision_id=ai_decision.id if ai_decision else None,
                created_at=created_at,
                updated_at=created_at,
                notification_sent=False,
            )
            seq += 1

            if from_ai:
                wo.notes = f"AI-generated work order. {ai_decision.explanation}"
            else:
                wo.notes = (
                    f"Raised by planning against the {machine.pm_frequency.lower()} "
                    f"PM schedule for {machine.name} ({machine.location})."
                )

            _apply_status_fields(wo, status, created_at, today)

            db.add(wo)
            counts[status] = counts.get(status, 0) + 1

    db.flush()
    return counts


def _apply_status_fields(
    wo: WorkOrder, status: str, created_at: datetime, today
) -> None:
    """
    Fill in the per-status fields. Anything past approval carries an approver
    and a supplier notification, which is what the real flow records.

    Draft and Pending_Approval are left alone: they are waiting on a human, so
    nothing is scheduled, approved or notified yet.
    """
    if status == "Approved":
        approved_at = created_at + timedelta(days=random.randint(0, 3))
        wo.approved_at = approved_at
        wo.approved_by = random.choice(APPROVERS)
        wo.notification_sent = True
        wo.notification_sent_at = approved_at
        # Half sit in the past so the Complete action is reachable in the UI.
        if random.random() < 0.5:
            wo.scheduled_date = today - timedelta(days=random.randint(1, 10))
        else:
            wo.scheduled_date = today + timedelta(days=random.randint(2, 21))
        wo.updated_at = approved_at

    elif status == "Completed":
        approved_at = created_at + timedelta(days=random.randint(0, 2))
        scheduled = (created_at + timedelta(days=random.randint(3, 12))).date()
        completed = min(scheduled + timedelta(days=random.randint(0, 3)), today)
        wo.approved_at = approved_at
        wo.approved_by = random.choice(APPROVERS)
        wo.scheduled_date = scheduled
        wo.completed_date = completed
        wo.notification_sent = True
        wo.notification_sent_at = approved_at
        wo.notes = f"{wo.notes} {random.choice(COMPLETION_NOTES)}"
        wo.updated_at = datetime.combine(completed, datetime.min.time())

    elif status == "Cancelled":
        wo.notes = f"{wo.notes} {random.choice(CANCEL_NOTES)}"
        wo.updated_at = created_at + timedelta(days=random.randint(1, 8))


# ============================================================================
# Full reset
# ============================================================================

# Children before parents. maintenance_history points at work_orders and
# work_orders points at ai_decisions, both with NO ACTION rather than a
# cascade, so deleting a parent first is refused outright.
_DELETE_ORDER = [MaintenanceHistory, WorkOrder, AIDecision, Machine]

_IDENTITY_TABLES = ["machines", "maintenance_history", "work_orders", "ai_decisions"]


def clear_demo_data(db: Session, clear_workflow_logs: bool = False) -> None:
    """
    Delete the whole demo estate, children first, and restart the identity
    counters.

    DESTRUCTIVE, and does not commit -- the caller owns the transaction.
    """
    for model in _DELETE_ORDER:
        db.query(model).delete(synchronize_session=False)

    if clear_workflow_logs:
        db.query(WorkflowLog).delete(synchronize_session=False)

    db.flush()
    _reseed_identities(db, clear_workflow_logs)


def clear_work_orders(db: Session) -> int:
    """
    Delete work orders and the AI decisions behind them, leaving the machines
    and their history in place.

    This is what scripts/seed_work_orders.py needs: it reseeds orders against an
    estate somebody else created. Work orders reference ai_decisions with NO
    ACTION, so they have to go first or the delete is refused.

    Returns how many orders were removed. Does not commit.
    """
    removed = db.query(WorkOrder).count()
    db.query(WorkOrder).delete(synchronize_session=False)
    db.query(AIDecision).delete(synchronize_session=False)
    db.flush()
    return removed


def reset_and_seed(
    db: Session,
    config: DemoSeedConfig,
    clear_workflow_logs: bool = False,
) -> DemoResetResult:
    """
    Delete the demo estate and build a fresh one, in a single transaction.

    DESTRUCTIVE. Every row in machines, maintenance_history, work_orders and
    ai_decisions is deleted, plus workflow_logs when asked. It commits on
    success; on failure it rolls back and re-raises, leaving the estate exactly
    as it was.

    Creates no schema. The tables must already exist.
    """
    config.validate()

    try:
        clear_demo_data(db, clear_workflow_logs=clear_workflow_logs)

        seed_machines(db, config)
        counts = seed_work_orders(db, config)
        if counts is None:
            raise RuntimeError(
                "Machines were seeded but could not be read back, so no work "
                "orders were created."
            )

        result = _summarise(db, counts, clear_workflow_logs)
        db.commit()

    except Exception:
        db.rollback()
        logger.exception("Demo reset failed and was rolled back")
        raise

    logger.info(
        "Demo reset complete: %d machines, %d work orders, %d AI decisions",
        result.machines, result.work_orders, result.ai_decisions,
    )
    return result


def _reseed_identities(db: Session, include_workflow_logs: bool) -> None:
    """
    Restart the identity counters so a reset looks like a fresh install --
    MACH-001 is row id 1 again.

    DBCC CHECKIDENT is SQL Server only, and cosmetic: machine_id and wo_number
    are numbered by the generators, so the identifiers anyone actually reads
    restart with or without this. A database on another engine skips it rather
    than failing the reset.

    It runs inside reset_and_seed's transaction, which is worth a note because
    the docs describe DBCC CHECKIDENT as non-transactional. If the RESEED
    survived a rollback the counter would sit at 0 while the restored rows still
    held ids 1..N, and the next reset would collide on the primary key. Measured
    against SQL Server 2022: the RESEED *is* rolled back, and the next insert
    continues from the restored maximum. Re-check this before moving it out from
    under the transaction.
    """
    dialect = db.bind.dialect.name
    if dialect != "mssql":
        logger.info(
            "Skipping identity reseed: %s is not SQL Server. Ids will continue "
            "from where they left off.",
            dialect,
        )
        return

    tables = list(_IDENTITY_TABLES)
    if include_workflow_logs:
        tables.append("workflow_logs")

    for table in tables:
        # RESEED 0 makes the next insert 1. Table names come from the module
        # constant above, never from a request.
        db.execute(text(f"DBCC CHECKIDENT ('{table}', RESEED, 0) WITH NO_INFOMSGS"))


def _summarise(
    db: Session, counts: Dict[str, int], workflow_logs_cleared: bool
) -> DemoResetResult:
    """
    Count what the reset produced, so the page can show that it landed.

    The PM status breakdown runs through MachineService rather than a query of
    its own: the point of showing it is that it matches the dashboard, which it
    can only be guaranteed to do if it is the same code.
    """
    from .machine_service import MachineService

    service = MachineService(db)
    machines = db.query(Machine).all()

    pm_status: Dict[str, int] = {}
    for machine in machines:
        status = service.calculate_pm_status(machine.next_pm_date, machine)
        pm_status[status] = pm_status.get(status, 0) + 1

    today = datetime.now().date()
    open_machine_ids = {
        machine_id for (machine_id,) in
        db.query(WorkOrder.machine_id)
        .filter(WorkOrder.status.in_(OPEN_STATUSES))
        .distinct()
    }
    overdue_free = sum(
        1 for m in machines
        if m.next_pm_date < today and m.id not in open_machine_ids
    )

    return DemoResetResult(
        machines=len(machines),
        maintenance_history=db.query(MaintenanceHistory).count(),
        work_orders=db.query(WorkOrder).count(),
        ai_decisions=db.query(AIDecision).count(),
        workflow_logs=db.query(WorkflowLog).count(),
        work_orders_by_status={s: counts.get(s, 0) for s in STATUS_ORDER},
        machines_by_pm_status=pm_status,
        ai_sourced_orders=db.query(WorkOrder)
            .filter(WorkOrder.creation_source == "AI").count(),
        # == True, not .is_(True): SQLAlchemy renders is_() as `IS 1`, which
        # SQL Server rejects outright ("Incorrect syntax near '1'"). IS is only
        # valid against NULL in T-SQL. == True renders `= 1` and works.
        decisions_below_threshold=db.query(AIDecision)
            .filter(AIDecision.requires_review == True).count(),  # noqa: E712
        overdue_machines_without_open_wo=overdue_free,
        workflow_logs_cleared=workflow_logs_cleared,
    )


def current_row_counts(db: Session) -> Dict[str, int]:
    """Row counts for the tables a reset touches, for the page to show first."""
    return {
        "machines": db.query(Machine).count(),
        "maintenance_history": db.query(MaintenanceHistory).count(),
        "work_orders": db.query(WorkOrder).count(),
        "ai_decisions": db.query(AIDecision).count(),
        "workflow_logs": db.query(WorkflowLog).count(),
    }
