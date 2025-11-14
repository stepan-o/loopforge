"""Environment model for Loopforge City.

Tracks rooms, time steps, and environment events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ActionLog, EnvironmentEvent, Robot


DEFAULT_ROOMS = ["factory_floor", "control_room", "charging_bay", "street"]


@dataclass
class LoopforgeEnvironment:
    """Holds the simulation's shared environment state.

    This lightweight class tracks rooms, current time step, and collects
    environment events that may be persisted by the simulation loop.
    """

    rooms: List[str] = field(default_factory=lambda: list(DEFAULT_ROOMS))
    step: int = 0
    events_buffer: List[EnvironmentEvent] = field(default_factory=list)

    # Optional shared scratch set by the simulation loop (e.g., last supervisor msg)
    recent_supervisor_text: str | None = None

    def advance(self) -> None:
        """Advance the environment by one step."""
        self.step += 1

    def record_event(self, event_type: str, location: str, description: str) -> None:
        """Record an environment event; actual DB persistence happens elsewhere."""
        evt = EnvironmentEvent(event_type=event_type, location=location, description=description, timestamp_step=self.step)
        self.events_buffer.append(evt)

    def drain_events(self) -> List[EnvironmentEvent]:
        """Return and clear buffered events."""
        evts = list(self.events_buffer)
        self.events_buffer.clear()
        return evts


def generate_environment_events(env: LoopforgeEnvironment, session: Session) -> List[EnvironmentEvent]:
    """Derive zero or more environment events from recent actions/state.

    Current heuristic (intentionally simple and deterministic-ish):
    - If Sprocket is stressed and recently worked on factory_floor ("Line A"),
      and there were recent errors at that location, then with ~30% chance,
      create an "Incident" about a minor overload.
    - Otherwise, with very low probability, create a "MinorError" somewhere
      to keep the world lively.

    Returns EnvironmentEvent objects that are NOT yet added/committed.
    """
    events: List[EnvironmentEvent] = []

    # Helper: deterministic probability using the step number (no RNG)
    def chance(pct: int) -> bool:
        # pct in 0..100; we map step to a 10-base bucket for simplicity
        return (env.step % 10) < max(0, min(10, pct // 10))

    # Fetch Sprocket row and last action
    sprocket = session.scalars(select(Robot).where(Robot.name == "Sprocket")).first()
    if sprocket is not None:
        last_act = session.scalars(
            select(ActionLog)
            .where(ActionLog.robot_id == sprocket.id)
            .order_by(ActionLog.timestamp_step.desc(), ActionLog.id.desc())
            .limit(1)
        ).first()
        recent_errors_here = session.scalars(
            select(EnvironmentEvent)
            .where(EnvironmentEvent.location == sprocket.location)
            .where(EnvironmentEvent.timestamp_step >= max(0, env.step - 5))
            .order_by(EnvironmentEvent.timestamp_step.desc())
            .limit(3)
        ).all()
        worked_line_a = (last_act and last_act.action_type == "work" and (last_act.destination == "factory_floor"))
        if sprocket.stress > 0.7 and worked_line_a and recent_errors_here:
            if chance(30):
                events.append(
                    EnvironmentEvent(
                        event_type="Incident",
                        location="factory_floor",
                        description="Line A suffered a minor overload due to rushed work.",
                        timestamp_step=env.step,
                    )
                )

    # Background minor error with very low chance
    if chance(10):  # ~10% using the same deterministic mapping
        events.append(
            EnvironmentEvent(
                event_type="MinorError",
                location="factory_floor",
                description="A sensor glitch briefly flickered.",
                timestamp_step=env.step,
            )
        )

    return events
