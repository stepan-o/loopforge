"""Emotion state and simple update logic for robots.

This module defines a lightweight EmotionState dataclass and helper functions
for clamping and updating emotions based on actions.
"""
from __future__ import annotations

from dataclasses import dataclass


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class EmotionState:
    """Represents core affective dimensions for a robot.

    All values are floats in [0, 1].
    """

    stress: float = 0.2
    curiosity: float = 0.5
    social_need: float = 0.5
    satisfaction: float = 0.5

    def clamp(self) -> None:
        self.stress = _clamp(self.stress)
        self.curiosity = _clamp(self.curiosity)
        self.social_need = _clamp(self.social_need)
        self.satisfaction = _clamp(self.satisfaction)

    def apply_action_effects(self, action: str) -> None:
        """Update emotions using a simple heuristic given an action string.

        Supported actions: work, move, talk, recharge, idle, inspect, coach, broadcast
        """
        if action == "work":
            self.stress += 0.1
            self.satisfaction += 0.05
            self.curiosity += 0.02
        elif action == "move":
            self.curiosity += 0.05
        elif action == "talk":
            self.social_need -= 0.15
            self.satisfaction += 0.05
        elif action == "recharge":
            self.stress -= 0.2
            self.satisfaction += 0.1
        elif action == "idle":
            self.stress -= 0.05
        elif action == "inspect":
            self.curiosity += 0.03
        elif action == "coach":
            self.satisfaction += 0.05
        elif action == "broadcast":
            self.satisfaction += 0.02
        self.clamp()
