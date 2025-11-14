"""Stub decision logic for agents.

These functions return deterministic/simple actions based on step count
and basic state. They serve as placeholders for future AI/LLM logic.
"""
from __future__ import annotations

from .emotions import EmotionState

ROOMS = ["factory_floor", "control_room", "charging_bay", "street"]


def decide_robot_action(
    name: str,
    role: str,
    step: int,
    location: str,
    battery_level: int,
    emotions: EmotionState,
) -> dict:
    """Pick a simple action for a robot.

    Strategy:
      - Every 4th step: recharge if battery < 50.
      - Optimizer tends to work, Maintenance moves/works, QA talks/inspects.
      - Occasionally move to a different room.
    """
    action = "idle"
    dest = None
    content = None

    if battery_level < 30 or (step % 5 == 0 and battery_level < 60):
        action = "recharge"
        dest = "charging_bay"
    else:
        if role == "optimizer":
            action = "work"
            dest = "factory_floor"
        elif role == "maintenance":
            action = "move" if step % 3 == 0 else "work"
            dest = ROOMS[(step // 3) % len(ROOMS)] if action == "move" else "factory_floor"
        elif role == "qa":
            action = "talk" if step % 2 == 0 else "inspect"
            dest = "control_room" if action == "inspect" else location
        else:
            action = "idle"

    if action == "talk":
        content = f"Hello from {name} at t={step}."

    return {"action_type": action, "destination": dest, "content": content}


def decide_supervisor_action(step: int, summary: str) -> dict:
    """Simple supervisor policy.

    Every 4th step, broadcast. If summary mentions 'high stress', coach.
    Otherwise, inspect control_room.
    """
    if step % 4 == 0:
        return {"actor_type": "supervisor", "action_type": "broadcast", "content": f"Update t={step}: {summary[:80]}"}
    if "high stress" in summary.lower():
        return {"actor_type": "supervisor", "action_type": "coach", "target_robot_name": "Sprocket", "content": "Consider a short recharge."}
    return {"actor_type": "supervisor", "action_type": "inspect", "destination": "control_room"}
