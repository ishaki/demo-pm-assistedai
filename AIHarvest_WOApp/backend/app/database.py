from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from .config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()

# Create SQLAlchemy engine for MS SQL Server
# pool_pre_ping: Test connections before using them
# pool_size: Number of connections to maintain
# max_overflow: Maximum overflow connections
engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    pool_pre_ping=True,   # Verify connections are alive
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,    # Recycle connections after 1 hour
)

# Create SessionLocal class for database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for declarative models
Base = declarative_base()


def get_db() -> Session:
    """
    Dependency function to get database session.
    Yields a database session and ensures it's closed after use.

    Usage in FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables.
    This should be called on application startup.
    """
    from . import models  # Import all models

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def check_db_connection():
    """
    Check if database connection is working.
    Returns True if connection is successful, False otherwise.
    """
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False
