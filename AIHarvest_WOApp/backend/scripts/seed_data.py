"""
Seed Data Script -- machines and their maintenance history.

Generates the machine estate: 75 machines by default, spread across the three
PM buckets, each with 3 to 8 historical maintenance records.

Distribution (truncated, so 75 gives 15 / 24 / 36):
- 20% overdue   (next_pm_date 1-60 days in the past)
- 33% due soon  (next_pm_date 1-30 days out)
- the rest OK   (next_pm_date 31-365 days out)

Run scripts/seed_work_orders.py afterwards to raise work orders against them.

The generators live in app/services/demo_seed_service.py, which the demo reset
page also calls -- so the page and the command line cannot drift apart. This
script is the CLI around them: it handles the confirmation prompt, the clear,
and the summary.

Usage:
    python scripts/seed_data.py                 # 75 machines
    python scripts/seed_data.py --count 120
    python scripts/seed_data.py --yes           # skip the confirmation
"""

import argparse
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.models import Machine
from app.services.demo_seed_service import (
    DEFAULT_MACHINE_COUNT,
    LOCATIONS,
    SUPPLIER_NAMES,
    FREQUENCIES,
    DemoSeedConfig,
    clear_demo_data,
    seed_machines,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count", type=int, default=DEFAULT_MACHINE_COUNT,
        help=f"How many machines to create (default: {DEFAULT_MACHINE_COUNT})",
    )
    parser.add_argument(
        "--yes", action="store_true",
        help="Clear existing data without asking",
    )
    return parser.parse_args()


def seed_database(count: int = DEFAULT_MACHINE_COUNT, assume_yes: bool = False) -> bool:
    """
    Clear the estate and generate a fresh set of machines.

    Everything runs in one transaction, so a failure part way through leaves the
    database as it was.
    """
    logger.info("=" * 60)
    logger.info("Seed Data Generation Script")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        existing_count = db.query(Machine).count()
        if existing_count > 0:
            logger.warning(f"Database already contains {existing_count} machines.")
            if not assume_yes:
                response = input(
                    "Clear existing machines, history, work orders and AI "
                    "decisions, then reseed? (yes/no): "
                )
                if response.lower() != "yes":
                    logger.info("Seed operation cancelled.")
                    return False

        # Work orders and AI decisions go too. They hang off machines that are
        # about to disappear, so keeping them would leave the estate incoherent
        # -- and scripts/seed_work_orders.py is the next step anyway.
        #
        # workflow_logs is left alone, which is what this script has always
        # done. The reset page clears it; the command line does not.
        logger.info("Clearing existing data...")
        clear_demo_data(db, clear_workflow_logs=False)

        config = DemoSeedConfig.defaults()
        config.machine_count = count

        machines = seed_machines(db, config)
        db.commit()

        logger.info("\n" + "=" * 60)
        logger.info("Seed data generation completed successfully!")
        logger.info("=" * 60)
        logger.info("\nSummary:")
        logger.info(f"  - Total machines: {len(machines)}")
        logger.info(f"  - Suppliers: {len(SUPPLIER_NAMES)}")
        logger.info(f"  - Locations: {len(LOCATIONS)}")
        logger.info(f"  - PM Frequencies: {', '.join(FREQUENCIES)}")
        logger.info(f"  - Admin email:    {config.admin_email}")
        logger.info(f"  - Supplier email: {config.supplier_email}")
        logger.info("\nNext: python scripts/seed_work_orders.py")

        return True

    except Exception as e:
        logger.error(f"Error during seed operation: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    args = parse_args()
    success = seed_database(count=args.count, assume_yes=args.yes)
    sys.exit(0 if success else 1)
