"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings


# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create Base class for models
class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


def get_db():
    """
    Database dependency for FastAPI routes.
    
    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database tables.
    
    This function creates all tables defined in the models.
    """
    from models.user import User  # noqa: F401
    from models.credit_settings import CreditSettings  # noqa: F401
    from models.credit_transaction import CreditTransaction  # noqa: F401
    
    Base.metadata.create_all(bind=engine)

