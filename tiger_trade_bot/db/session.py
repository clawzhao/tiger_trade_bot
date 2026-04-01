"""
Database session management for Tiger Trade Bot.

Provides:
- engine: SQLAlchemy engine instance configured from DATABASE_URL
- SessionLocal: sessionmaker factory for database sessions
- Base: declarative base for models (re-exported from models)
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL

# Import Base from models to ensure single metadata source
from .models import Base

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

# SessionLocal factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables (for quickstart). For production, use Alembic migrations."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency generator for FastAPI or other ASGI apps."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
