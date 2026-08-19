"""
Work Order Seed Script
Generates work orders across every lifecycle status, plus the AI decisions that
produced the AI-sourced ones, so the Work Orders view and the audit trail have
data to show without calling a live LLM.

Distribution (45 work orders over the seeded machines):
- 6  Draft
- 9  Pending_Approval
- 12 Approved (roughly half already past their scheduled date)
- 14 Completed
- 4  Cancelled

Machines are drawn overdue-first, matching how the daily PM check would pick
them up. A machine holds at most one open work order (Draft / Pending_Approval
/ Approved), which is the invariant WorkOrderService enforces when it refuses to
raise a duplicate; Completed and Cancelled orders are layered on freely as
history.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import json
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Machine, WorkOrder, AIDecision
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Status distribution -- see module docstring
STATUS_PLAN = [
    ("Draft", 6),
    ("Pending_Approval", 9),
    ("Approved", 12),
    ("Completed", 14),
    ("Cancelled", 4),
]

OPEN_STATUSES = ("Draft", "Pending_Approval", "Approved")

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

CANCEL_NOTES = [
    "Cancelled -- machine was taken offline for a line reconfiguration before "
    "the visit; PM will be re-raised once it is back in service.",
    "Cancelled -- duplicate of an order already raised for the same PM window.",
    "Cancelled -- supplier could not meet the window and the schedule was "
    "moved to the next cycle.",
    "Cancelled -- PM was completed during an unrelated corrective visit, so "
    "the scheduled work is no longer needed.",
]

COMPLETION_NOTES = [
    "PM completed. Filters and belts replaced, no faults found.",
    "PM completed. Lubrication and alignment checked, within tolerance.",
    "PM completed. Worn seal replaced during the visit; asset returned to "
    "service the same day.",
    "PM completed. All checks passed, next cycle confirmed with the supplier.",
]


def _pm_bucket(machine, today, window):
    """Classify a machine the way the dashboard does: overdue, due soon, or ok."""
    days = (machine.next_pm_date - today).days
    if days < 0:
        return "overdue", days
    if days <= window:
        return "due_soon", days
    return "ok", days


def _priority_for(bucket):
    """Priority follows urgency, with the occasional bump a planner would make."""
    if bucket == "overdue":
        return random.choices(["High", "Medium"], weights=[85, 15])[0]
    if bucket == "due_soon":
        return random.choices(["Medium", "High", "Low"], weights=[70, 15, 15])[0]
    return random.choices(["Low", "Medium"], weights=[80, 20])[0]


def _next_wo_sequence(db, year):
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


def _build_ai_decision(machine, bucket, days, priority, threshold, window, created_at):
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


def generate_work_orders(db):
    """Generate work orders across every status, with AI decisions behind most."""
    settings = get_settings()
    threshold = float(settings.CONFIDENCE_THRESHOLD)
    window = int(settings.PM_DUE_DAYS)
    today = datetime.now().date()
    now = datetime.now()
    year = now.year

    machines = db.query(Machine).all()
    if not machines:
        logger.error("No machines found. Run scripts/seed_data.py first.")
        return None

    # Overdue first, then due soon -- the order the daily check would surface.
    ranked = sorted(machines, key=lambda m: m.next_pm_date)
    open_pool = list(ranked)
    history_pool = list(ranked)
    random.shuffle(history_pool)

    seq = _next_wo_sequence(db, year)
    created = []
    counts = {}

    for status, count in STATUS_PLAN:
        for _ in range(count):
            # Open orders take a machine off the pool so no machine ends up
            # with two of them; closed orders may reuse any machine.
            if status in OPEN_STATUSES:
                if not open_pool:
                    logger.warning("Ran out of machines for open work orders")
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
            age_days = random.randint(20, 90) if status in ("Completed", "Cancelled") else random.randint(0, 14)
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

            # Per-status fields. Anything past approval carries an approver and
            # a supplier notification, which is what the real flow records.
            if status == "Approved":
                approved_at = created_at + timedelta(days=random.randint(0, 3))
                wo.approved_at = approved_at
                wo.approved_by = random.choice(APPROVERS)
                wo.notification_sent = True
                wo.notification_sent_at = approved_at
                # Half sit in the past so the Complete action is reachable.
                if random.random() < 0.5:
                    wo.scheduled_date = today - timedelta(days=random.randint(1, 10))
                else:
                    wo.scheduled_date = today + timedelta(days=random.randint(2, 21))
                wo.updated_at = approved_at

            elif status == "Completed":
                approved_at = created_at + timedelta(days=random.randint(0, 2))
                scheduled = (created_at + timedelta(days=random.randint(3, 12))).date()
                completed = scheduled + timedelta(days=random.randint(0, 3))
                if completed > today:
                    completed = today
                wo.approved_at = approved_at
                wo.approved_by = random.choice(APPROVERS)
                wo.scheduled_date = scheduled
                wo.completed_date = completed
                wo.notification_sent = True
                wo.notification_sent_at = approved_at
                wo.notes = f"{wo.notes} {random.choice(COMPLETION_NOTES)}"
                wo.updated_at = datetime.combine(completed, datetime.min.time())

            elif status == "Cancelled":
                cancelled_at = created_at + timedelta(days=random.randint(1, 8))
                wo.notes = f"{wo.notes} {random.choice(CANCEL_NOTES)}"
                wo.updated_at = cancelled_at

            elif status == "Pending_Approval":
                # Waiting on a human, so nothing is scheduled or notified yet.
                pass

            db.add(wo)
            created.append(wo)
            counts[status] = counts.get(status, 0) + 1

    db.commit()
    return created, counts


def seed_work_orders():
    """Entry point: clear prior work orders and regenerate the demo set."""
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("Work Order Seed Script")
        logger.info("=" * 60)

        existing = db.query(WorkOrder).count()
        if existing:
            logger.info(f"Clearing {existing} existing work orders and their AI decisions...")
            # Work orders reference ai_decisions with NO ACTION, so they have to
            # go first or the delete is refused.
            db.query(WorkOrder).delete()
            db.query(AIDecision).delete()
            db.commit()
            logger.info("✓ Existing work orders cleared")

        result = generate_work_orders(db)
        if result is None:
            return False
        created, counts = result

        ai_count = sum(1 for wo in created if wo.creation_source == "AI")
        review_count = (
            db.query(AIDecision).filter(AIDecision.requires_review == True).count()  # noqa: E712
        )

        logger.info("\n" + "=" * 60)
        logger.info("Work order generation completed successfully!")
        logger.info("=" * 60)
        logger.info("\nSummary:")
        logger.info(f"  - Total work orders: {len(created)}")
        for status, _ in STATUS_PLAN:
            logger.info(f"      {status:<18} {counts.get(status, 0)}")
        logger.info(f"  - AI-generated: {ai_count}")
        logger.info(f"  - Manual: {len(created) - ai_count}")
        logger.info(f"  - AI decisions below confidence threshold: {review_count}")
        logger.info("\nOpen the Work Orders page to view them.")

        return True

    except Exception as e:
        logger.error(f"Error during work order seed: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = seed_work_orders()
    sys.exit(0 if success else 1)
