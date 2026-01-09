"""
Seed Data Script
Generates 75 test machines with varied PM statuses, maintenance history, and supplier information.

Distribution:
- 15 machines (20%): Overdue (next_pm_date in past, 1-60 days)
- 25 machines (33%): Due soon (next_pm_date within 1-30 days)
- 35 machines (47%): OK (next_pm_date > 30 days)
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, Base
from app.models import Machine, MaintenanceHistory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Test data constants
SUPPLIERS = [
    {"name": "TechServ Inc", "email": "ishak.ahmad@innoark.com"},
    {"name": "MainCo Solutions", "email": "ishak.ahmad@innoark.com"},
    {"name": "FixIt Pro", "email": "ishak.ahmad@innoark.com"},
    {"name": "Industrial Care", "email": "ishak.ahmad@innoark.com"},
    {"name": "MachineGuard", "email": "ishak.ahmad@innoark.com"},
    {"name": "ProMaintain", "email": "ishak.ahmad@innoark.com"},
    {"name": "QuickFix Ltd", "email": "ishak.ahmad@innoark.com"},
    {"name": "ReliaTech", "email": "sishak.ahmad@innoark.com"},
    {"name": "ServiceMax", "email": "ishak.ahmad@innoark.com"},
    {"name": "EliteMaint", "email": "ishak.ahmad@innoark.com"}
]

FREQUENCIES = ["Monthly", "Bimonthly", "Yearly"]
LOCATIONS = ["Zone A", "Zone B", "Zone C", "Zone D", "Zone E"]
MACHINE_TYPES = [
    "CNC Mill", "Lathe", "Press", "Grinder", "Welder",
    "Conveyor", "Robot Arm", "Drill Press", "Band Saw",
    "Plasma Cutter", "Assembly Line", "Packaging Machine"
]
MAINTENANCE_TYPES = ["Preventive", "Corrective", "Inspection"]


def generate_machines(db: SessionLocal, count: int = 75):
    """
    Generate test machines with varied PM statuses.

    Args:
        db: Database session
        count: Total number of machines to generate (default: 75)
    """
    today = datetime.now().date()
    machines_created = []

    logger.info(f"Generating {count} test machines...")

    # Calculate distribution
    overdue_count = int(count * 0.20)  # 20% overdue
    due_soon_count = int(count * 0.33)  # 33% due soon
    ok_count = count - overdue_count - due_soon_count  # Remaining are OK

    logger.info(f"  - {overdue_count} overdue machines")
    logger.info(f"  - {due_soon_count} due soon machines (≤30 days)")
    logger.info(f"  - {ok_count} OK machines (>30 days)")

    machine_counter = 1

    # Generate OVERDUE machines (1-60 days overdue)
    for i in range(overdue_count):
        freq = random.choice(FREQUENCIES)
        days_overdue = random.randint(1, 60)
        next_pm = today - timedelta(days=days_overdue)
        last_pm = next_pm - timedelta(days=get_frequency_days(freq))

        supplier = random.choice(SUPPLIERS)

        machine = Machine(
            machine_id=f"MACH-{machine_counter:03d}",
            name=f"{random.choice(MACHINE_TYPES)} {machine_counter}",
            description=f"Production machine in {random.choice(LOCATIONS)}",
            location=random.choice(LOCATIONS),
            pm_frequency=freq,
            last_pm_date=last_pm,
            next_pm_date=next_pm,
            assigned_supplier=supplier["name"],
            supplier_email=supplier["email"],
            status="Active"
        )
        machines_created.append(machine)
        machine_counter += 1

    # Generate DUE SOON machines (1-30 days)
    for i in range(due_soon_count):
        freq = random.choice(FREQUENCIES)
        days_until = random.randint(1, 30)
        next_pm = today + timedelta(days=days_until)
        last_pm = next_pm - timedelta(days=get_frequency_days(freq))

        supplier = random.choice(SUPPLIERS)

        machine = Machine(
            machine_id=f"MACH-{machine_counter:03d}",
            name=f"{random.choice(MACHINE_TYPES)} {machine_counter}",
            description=f"Production machine in {random.choice(LOCATIONS)}",
            location=random.choice(LOCATIONS),
            pm_frequency=freq,
            last_pm_date=last_pm,
            next_pm_date=next_pm,
            assigned_supplier=supplier["name"],
            supplier_email=supplier["email"],
            status="Active"
        )
        machines_created.append(machine)
        machine_counter += 1

    # Generate OK machines (31-365 days)
    for i in range(ok_count):
        freq = random.choice(FREQUENCIES)
        days_until = random.randint(31, 365)
        next_pm = today + timedelta(days=days_until)
        last_pm = next_pm - timedelta(days=get_frequency_days(freq))

        supplier = random.choice(SUPPLIERS)

        machine = Machine(
            machine_id=f"MACH-{machine_counter:03d}",
            name=f"{random.choice(MACHINE_TYPES)} {machine_counter}",
            description=f"Production machine in {random.choice(LOCATIONS)}",
            location=random.choice(LOCATIONS),
            pm_frequency=freq,
            last_pm_date=last_pm,
            next_pm_date=next_pm,
            assigned_supplier=supplier["name"],
            supplier_email=supplier["email"],
            status="Active"
        )
        machines_created.append(machine)
        machine_counter += 1

    # Add machines to session (using add_all to keep them in session)
    db.add_all(machines_created)
    db.commit()

    # Refresh all machines to get their IDs
    for machine in machines_created:
        db.refresh(machine)

    logger.info(f"✓ Created {len(machines_created)} machines")
    return machines_created


def generate_maintenance_history(db: SessionLocal, machines: list):
    """
    Generate maintenance history for each machine.

    Args:
        db: Database session
        machines: List of Machine objects
    """
    logger.info("Generating maintenance history...")

    today = datetime.now().date()
    history_records = []

    for machine in machines:
        # Generate 3-8 historical maintenance records per machine
        history_count = random.randint(3, 8)

        for j in range(history_count):
            # Generate dates going back 30 days to 2 years
            days_ago = random.randint(30, 730)
            maintenance_date = today - timedelta(days=days_ago)

            supplier = random.choice(SUPPLIERS)

            history = MaintenanceHistory(
                machine_id=machine.id,
                maintenance_date=maintenance_date,
                maintenance_type=random.choice(MAINTENANCE_TYPES),
                notes=random.choice([
                    "Regular maintenance performed. All systems operational.",
                    "Routine inspection completed. No issues found.",
                    "Preventive maintenance completed successfully.",
                    "Parts lubricated and checked. Running smoothly.",
                    "Comprehensive service performed. Machine in good condition.",
                    "Scheduled maintenance completed. Performance optimal.",
                    "Inspection and minor adjustments completed.",
                ]),
                performed_by=supplier["name"]
            )
            history_records.append(history)

    # Add history records to session
    db.add_all(history_records)
    db.commit()

    logger.info(f"✓ Created {len(history_records)} maintenance history records")


def get_frequency_days(frequency: str) -> int:
    """
    Convert PM frequency to approximate days.

    Args:
        frequency: PM frequency string

    Returns:
        Number of days for the frequency
    """
    frequency_map = {
        "Monthly": 30,
        "Bimonthly": 60,
        "Yearly": 365
    }
    return frequency_map.get(frequency, 30)


def seed_database():
    """
    Main function to seed the database with test data.
    """
    logger.info("=" * 60)
    logger.info("Seed Data Generation Script")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # Check if machines already exist
        existing_count = db.query(Machine).count()
        if existing_count > 0:
            logger.warning(f"Database already contains {existing_count} machines.")
            response = input("Do you want to clear existing data and reseed? (yes/no): ")
            if response.lower() != 'yes':
                logger.info("Seed operation cancelled.")
                return False

            # Clear existing data
            logger.info("Clearing existing data...")
            db.query(MaintenanceHistory).delete()
            db.query(Machine).delete()
            db.commit()

            # Reset auto-increment IDs
            logger.info("Resetting ID sequences...")
            try:
                # Reset the auto-increment counter for both tables
                db.execute("DELETE FROM sqlite_sequence WHERE name='machines'")
                db.execute("DELETE FROM sqlite_sequence WHERE name='maintenance_history'")
                db.commit()
                logger.info("✓ ID sequences reset")
            except Exception as e:
                logger.warning(f"Could not reset ID sequences (non-SQLite database?): {e}")

            logger.info("✓ Existing data cleared and IDs reset")

        # Generate machines (already refreshed with IDs)
        machines = generate_machines(db, count=75)

        # Generate maintenance history
        generate_maintenance_history(db, machines)

        logger.info("\n" + "=" * 60)
        logger.info("Seed data generation completed successfully!")
        logger.info("=" * 60)
        logger.info("\nSummary:")
        logger.info(f"  - Total machines: {len(machines)}")
        logger.info(f"  - Unique suppliers: {len(SUPPLIERS)}")
        logger.info(f"  - Locations: {len(LOCATIONS)}")
        logger.info(f"  - PM Frequencies: {', '.join(FREQUENCIES)}")
        logger.info("\nYou can now start the application and view the test data!")

        return True

    except Exception as e:
        logger.error(f"Error during seed operation: {e}")
        db.rollback()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    success = seed_database()
    sys.exit(0 if success else 1)
