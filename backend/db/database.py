"""Database engine and session management."""
from sqlmodel import SQLModel, create_engine, Session
from backend.core.config import settings


# Create database engine
engine = create_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)


def create_db_and_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session
