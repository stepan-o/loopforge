"""Database setup for Loopforge City using SQLAlchemy 2.0 style.

Provides an engine factory, a scoped Session factory, and Base declarative class.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


def get_engine(echo: bool | None = None):
    settings = get_settings()
    return create_engine(settings.database_url, echo=echo if echo is not None else settings.echo_sql, future=True)


SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)


@contextmanager
def session_scope() -> Iterator["Session"]:
    """Provide a transactional scope around a series of operations.

    Example:
        with session_scope() as session:
            session.add(obj)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
