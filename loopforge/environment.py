"""Environment model for Loopforge City.

Tracks rooms, time steps, and environment events.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .models import EnvironmentEvent


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
