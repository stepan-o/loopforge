"""Agent stubs for Loopforge City.

Defines RobotAgent and SupervisorAgent with simple decision policies.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .emotions import EmotionState
from .llm_stub import decide_robot_action, decide_supervisor_action


@dataclass
class RobotAgent:
    """Represents a robot's in-memory state used during a step.

    This is a thin wrapper around DB-backed state for transient logic.
    """

    name: str
    role: str
    location: str
    battery_level: int
    emotions: EmotionState

    def decide(self, step: int) -> dict:
        """Return a dict describing the chosen action.

        Keys: action_type, destination (opt), content (opt)
        """
        return decide_robot_action(self.name, self.role, step, self.location, self.battery_level, self.emotions)


@dataclass
class SupervisorAgent:
    """Supervisor policy stub.

    Currently implements a simple deterministic policy.
    """

    name: str = "Supervisor"

    def decide(self, step: int, summary: str) -> dict:
        """Return an action dict for the supervisor.

        Keys: action_type, target_robot_name (opt), content (opt)
        """
        return decide_supervisor_action(step, summary)
