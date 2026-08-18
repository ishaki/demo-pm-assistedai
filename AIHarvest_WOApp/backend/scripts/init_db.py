"""
Database Initialization Script
Creates all database tables for the AI-Assisted Preventive Maintenance POC.
Run this script before starting the application for the first time.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import engine, Base, check_db_connection
from app.models import Machine, MaintenanceHistory, WorkOrder, AIDecision, WorkflowLog
from app.config import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_database():
    """
    Initialize the database by creating all tables.
    """
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("Database Initialization Script")
    logger.info("=" * 60)
    logger.info(f"Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'Not configured'}")

    # Check database connection
    logger.info("Checking database connection...")
    if not check_db_connection():
        logger.error("Failed to connect to database. Please check your configuration.")
        logger.error("Ensure MS SQL Server is running and credentials are correct.")
        return False

    logger.info("Database connection successful!")

    # Create all tables
    logger.info("Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tables created successfully!")

        # List created tables
        logger.info("\nCreated tables:")
        for table in Base.metadata.sorted_tables:
            logger.info(f"  - {table.name}")

        logger.info("\n" + "=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        return True

    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        logger.error("Database initialization failed!")
        return False


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
