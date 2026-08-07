"""
Database session factory and base model for SQLAlchemy.

Usage:
    from database import Base, get_db, engine

    # In a model module:
    class MyModel(Base):
        __tablename__ = "my_table"
        ...

    # In a FastAPI route (via dependency injection):
    def my_route(db: Session = Depends(get_db)):
        ...
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Fall back to an in-memory SQLite database when DATABASE_URL is not set so
# that the module can be imported without a running PostgreSQL instance.
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://stockiq:stockiq@localhost:5432/stockiq",
)

engine = create_engine(
    DATABASE_URL,
    # pool_pre_ping checks connection liveness before handing it to a request,
    # which prevents "server closed the connection unexpectedly" errors after
    # a long period of inactivity.
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base class shared by all ORM models."""
    pass


def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy database session and
    guarantees the session is closed after the request completes.

    Yields:
        Session: An active SQLAlchemy ORM session.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
