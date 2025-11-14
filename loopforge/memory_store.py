"""Memory store abstraction for robots.

Provides helper functions to add and retrieve memories from the database.
"""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Memory, Robot


class MemoryStore:
    """Simple helper to manage Memory rows."""

    def add_memory(
        self,
        session: Session,
        robot: Robot,
        timestamp_step: int,
        text: str,
        importance: int = 1,
        tags: Optional[dict] = None,
    ) -> Memory:
        mem = Memory(
            robot_id=robot.id,
            timestamp_step=timestamp_step,
            text=text,
            importance=importance,
            tags=tags,
        )
        session.add(mem)
        return mem

    def get_recent_memories(
        self, session: Session, robot: Robot, limit: int = 10
    ) -> Iterable[Memory]:
        stmt = (
            select(Memory)
            .where(Memory.robot_id == robot.id)
            .order_by(Memory.timestamp_step.desc())
            .limit(limit)
        )
        return session.scalars(stmt).all()
