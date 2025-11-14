"""ORM models for Loopforge City.

Defines Robot, Memory, ActionLog, EnvironmentEvent.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import Integer, String, ForeignKey, JSON, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Robot(Base):
    __tablename__ = "robots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    personality_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    location: Mapped[str] = mapped_column(String(64), nullable=False, default="factory_floor")
    battery_level: Mapped[int] = mapped_column(Integer, nullable=False, default=100)

    # emotions
    stress: Mapped[float] = mapped_column(Float, nullable=False, default=0.2)
    curiosity: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    social_need: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    satisfaction: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # relationships
    memories: Mapped[list["Memory"]] = relationship(back_populates="robot", cascade="all, delete-orphan")
    actions: Mapped[list["ActionLog"]] = relationship(back_populates="robot")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_id: Mapped[int] = mapped_column(ForeignKey("robots.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp_step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    importance: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    robot: Mapped[Robot] = relationship(back_populates="memories")


class ActionLog(Base):
    __tablename__ = "action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    robot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("robots.id"), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "robot" or "supervisor"
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_robot_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp_step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    robot: Mapped[Optional[Robot]] = relationship(back_populates="actions")


class EnvironmentEvent(Base):
    __tablename__ = "environment_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    location: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp_step: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
