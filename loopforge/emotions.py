"""Emotion state, traits, and simple update logic for robots.

This module defines:
- EmotionState: core affective dimensions with clamping and simple effects.
- Traits: stable characteristics that can bias decisions and trigger effects.
- Helpers to sync emotions/traits to and from ORM Robots.
- update_emotions: per-step updates based on last action and context flags.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


@dataclass
class EmotionState:
    """Represents core affective dimensions for a robot.

    All values are floats in [0, 1].
    """

    stress: float = 0.2
    curiosity: float = 0.5
    social_need: float = 0.3
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


@dataclass
class Traits:
    """Stable personality-like traits in [0,1].

    Notes:
        - guardrail_reliance: how strongly this agent defaults to "follow the manual"
          vs weighing concrete context. Higher = more likely to pick guardrail mode.
    """

    risk_aversion: float = 0.5
    obedience: float = 0.5
    ambition: float = 0.5
    empathy: float = 0.5
    blame_external: float = 0.5
    guardrail_reliance: float = 0.5

    def clamp(self) -> None:
        self.risk_aversion = _clamp(self.risk_aversion)
        self.obedience = _clamp(self.obedience)
        self.ambition = _clamp(self.ambition)
        self.empathy = _clamp(self.empathy)
        self.blame_external = _clamp(self.blame_external)
        self.guardrail_reliance = _clamp(self.guardrail_reliance)


def update_emotions(agent: Any, last_action: Dict[str, Any], context: Dict[str, Any]) -> None:
    """Lightweight per-step emotion updater.

    Parameters:
        agent: an object with `emotions: EmotionState` attribute.
        last_action: dict with key `action_type` and optional metadata.
        context: dict of flags, e.g. {"near_error": bool, "isolated": bool}
    """
    em = agent.emotions

    # Baseline drift/decay each step
    em.stress -= 0.02  # relax slightly over time
    em.social_need -= 0.01  # social tension eases a bit unless reinforced
    em.curiosity += 0.005  # curiosity slowly rises

    action = (last_action or {}).get("action_type", "idle")
    # Primary action effects (lightweight mapping)
    if action == "work":
        em.stress += 0.08
        em.satisfaction += 0.04
    elif action == "recharge":
        em.stress -= 0.2
        em.satisfaction += 0.08
    elif action == "talk":
        em.social_need -= 0.15
        em.satisfaction += 0.05
    elif action == "move":
        em.curiosity += 0.03
    elif action == "inspect":
        em.curiosity += 0.02

    # Contextual nudges
    if context.get("near_error"):
        em.stress += 0.05
        em.curiosity += 0.01
    if context.get("isolated"):
        em.social_need += 0.05
        em.satisfaction -= 0.02

    em.clamp()


# ORM sync helpers (kept here for reuse without circular deps)

def emotion_from_robot(robot: Any) -> EmotionState:
    return EmotionState(
        stress=float(getattr(robot, "stress", 0.2) or 0.0),
        curiosity=float(getattr(robot, "curiosity", 0.5) or 0.0),
        social_need=float(getattr(robot, "social_need", 0.3) or 0.0),
        satisfaction=float(getattr(robot, "satisfaction", 0.5) or 0.0),
    )


def apply_emotion_to_robot(robot: Any, emotions: EmotionState) -> None:
    robot.stress = float(emotions.stress)
    robot.curiosity = float(emotions.curiosity)
    robot.social_need = float(emotions.social_need)
    robot.satisfaction = float(emotions.satisfaction)


def traits_from_robot(robot: Any) -> Traits:
    """Construct Traits from an ORM Robot's `traits_json`.

    Traits are round-tripped via the Robot.traits_json column. This includes
    `guardrail_reliance` alongside other scalar traits. This helper is the
    canonical sync path from DB → in-memory Traits.
    """
    data = getattr(robot, "traits_json", None) or {}
    return Traits(
        risk_aversion=float(data.get("risk_aversion", 0.5)),
        obedience=float(data.get("obedience", 0.5)),
        ambition=float(data.get("ambition", 0.5)),
        empathy=float(data.get("empathy", 0.5)),
        blame_external=float(data.get("blame_external", 0.5)),
        guardrail_reliance=float(data.get("guardrail_reliance", 0.5)),
    )


def apply_traits_to_robot(robot: Any, traits: Traits) -> None:
    """Persist Traits back to the ORM Robot's `traits_json`.

    Mirrors `traits_from_robot`: clamps values to [0,1] and writes all fields,
    including `guardrail_reliance`. This is the canonical sync path from
    in-memory Traits → DB.
    """
    # Persist as a plain dict; clamp to ensure bounds
    traits.clamp()
    robot.traits_json = {
        "risk_aversion": float(traits.risk_aversion),
        "obedience": float(traits.obedience),
        "ambition": float(traits.ambition),
        "empathy": float(traits.empathy),
        "blame_external": float(traits.blame_external),
        "guardrail_reliance": float(traits.guardrail_reliance),
    }
