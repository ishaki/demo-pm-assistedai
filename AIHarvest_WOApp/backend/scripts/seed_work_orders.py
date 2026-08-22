"""
Work Order Seed Script -- work orders and the AI decisions behind them.

Generates work orders across every lifecycle status, plus the AI decisions that
produced the AI-sourced ones, so the Work Orders view and the audit trail have
data to show without calling a live LLM.

Default distribution (45 work orders over the seeded machines):
- 0  Draft             (nothing in the running app creates one -- see
                        DEFAULT_STATUS_COUNTS in demo_seed_service.py)
- 15 Pending_Approval
- 12 Approved          (roughly half already past their scheduled date)
- 14 Completed
- 4  Cancelled

Machines are drawn overdue-first, matching how the daily PM check would pick
them up, and a machine holds at most one open work order (Draft /
Pending_Approval / Approved) -- the invariant WorkOrderService enforces when it
refuses to raise a duplicate. Completed and Cancelled orders are layered on
freely as history.

Requires machines to exist: run scripts/seed_data.py first.

The generators live in app/services/demo_seed_service.py, which the demo reset
page also calls -- so the page and the command line cannot drift apart.

Usage:
    python scripts/seed_work_orders.py
    python scripts/seed_work_orders.py --reserve-overdue 0
    python scripts/seed_work_orders.py --approved 20 --completed 30
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import AIDecision, Machine, WorkOrder
from app.services.demo_seed_service import (
    DEFAULT_RESERVE_OVERDUE_WITHOUT_WO,
    DEFAULT_STATUS_COUNTS,
    STATUS_ORDER,
    DemoSeedConfig,
    clear_work_orders,
    seed_work_orders as generate_work_orders,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    for status in STATUS_ORDER:
        flag = "--" + status.lower().replace("_", "-")
        parser.add_argument(
            flag, type=int, default=DEFAULT_STATUS_COUNTS[status],
            metavar="N", dest=status.lower(),
            help=f"{status} work orders (default: {DEFAULT_STATUS_COUNTS[status]})",
        )
    parser.add_argument(
        "--reserve-overdue", type=int,
        default=DEFAULT_RESERVE_OVERDUE_WITHOUT_WO, metavar="N",
        help=(
            "Leave this many of the most-overdue machines with no work order, "
            "so a live 'AI raises a work order' demo has a target "
            f"(default: {DEFAULT_RESERVE_OVERDUE_WITHOUT_WO})"
        ),
    )
    return parser.parse_args()


def build_config(args) -> DemoSeedConfig:
    """
    Config for the generator. machine_count is read from the database rather
    than taken from a flag -- this script does not create machines, so the
    estate that is already there is the only honest number to validate against.
    """
    config = DemoSeedConfig.defaults()
    config.reserve_overdue_without_wo = args.reserve_overdue
    config.status_counts = {s: getattr(args, s.lower()) for s in STATUS_ORDER}
    return config


def seed_work_orders(args) -> bool:
    """Clear prior work orders and regenerate the demo set."""
    db = SessionLocal()

    try:
        logger.info("=" * 60)
        logger.info("Work Order Seed Script")
        logger.info("=" * 60)

        machine_count = db.query(Machine).count()
        if not machine_count:
            logger.error("No machines found. Run scripts/seed_data.py first.")
            return False

        config = build_config(args)
        config.machine_count = machine_count
        config.validate()

        removed = clear_work_orders(db)
        if removed:
            logger.info(
                f"Cleared {removed} existing work orders and their AI decisions"
            )

        counts = generate_work_orders(db, config)
        if counts is None:
            return False

        db.commit()

        total = sum(counts.values())
        ai_count = db.query(WorkOrder).filter(
            WorkOrder.creation_source == "AI"
        ).count()
        # == True rather than .is_(True): SQLAlchemy renders is_() as `IS 1`,
        # which SQL Server rejects -- IS is only valid against NULL in T-SQL.
        review_count = db.query(AIDecision).filter(
            AIDecision.requires_review == True  # noqa: E712
        ).count()

        logger.info("\n" + "=" * 60)
        logger.info("Work order generation completed successfully!")
        logger.info("=" * 60)
        logger.info("\nSummary:")
        logger.info(f"  - Total work orders: {total}")
        for status in STATUS_ORDER:
            logger.info(f"      {status:<18} {counts.get(status, 0)}")
        logger.info(f"  - AI-generated: {ai_count}")
        logger.info(f"  - Manual: {total - ai_count}")
        logger.info(f"  - AI decisions below confidence threshold: {review_count}")
        logger.info(
            f"  - Overdue machines held back without an order: "
            f"{config.reserve_overdue_without_wo}"
        )
        logger.info("\nOpen the Work Orders page to view them.")

        return True

    except ValueError as e:
        # Config that cannot produce a coherent estate -- usually more open
        # orders than there are machines to hang them on.
        logger.error(str(e))
        db.rollback()
        return False

    except Exception as e:
        logger.error(f"Error during work order seed: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = seed_work_orders(parse_args())
    sys.exit(0 if success else 1)
