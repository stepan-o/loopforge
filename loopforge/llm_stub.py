"""Decision logic for agents with optional LLM-backed policy.

Default behavior is deterministic. When USE_LLM_POLICY is true and an
OPENAI_API_KEY is provided, this module will ask an LLM to propose the next
action, falling back to the deterministic policy on any error or parse issue.
"""
from __future__ import annotations

import logging
from typing import Any

from .config import USE_LLM_POLICY
from .llm_client import chat_json
from .emotions import EmotionState

logger = logging.getLogger(__name__)

ROOMS = ["factory_floor", "control_room", "charging_bay", "street"]


# ------------------------- Deterministic policies ----------------------------

def _deterministic_robot_policy(
    name: str,
    role: str,
    step: int,
    location: str,
    battery_level: int,
    emotions: EmotionState,
) -> dict:
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


def _deterministic_supervisor_policy(step: int, summary: str) -> dict:
    if step % 4 == 0:
        return {
            "actor_type": "supervisor",
            "action_type": "broadcast",
            "content": f"Update t={step}: {summary[:80]}",
        }
    if "high stress" in summary.lower():
        return {
            "actor_type": "supervisor",
            "action_type": "coach",
            "target_robot_name": "Sprocket",
            "content": "Consider a short recharge.",
        }
    return {"actor_type": "supervisor", "action_type": "inspect", "destination": "control_room"}


# ------------------------------ Public API ----------------------------------

def decide_robot_action(
    name: str,
    role: str,
    step: int,
    location: str,
    battery_level: int,
    emotions: EmotionState,
) -> dict:
    """Return an action dict: {action_type, destination?, content?}.

    Contract must remain stable for the simulation loop. This function will use
    the LLM when enabled; otherwise it returns the deterministic choice.
    """
    if not USE_LLM_POLICY:
        logger.debug("LLM disabled; using deterministic robot policy for %s", name)
        return _deterministic_robot_policy(name, role, step, location, battery_level, emotions)

    # Build compact state for the LLM
    state: dict[str, Any] = {
        "name": name,
        "role": role,
        "step": step,
        "location": location,
        "battery_level": battery_level,
        "emotions": {
            "stress": emotions.stress,
            "curiosity": emotions.curiosity,
            "social_need": emotions.social_need,
            "satisfaction": emotions.satisfaction,
        },
    }

    system_prompt = (
        "You control a robot in Loopforge City. Return ONLY a JSON object with keys "
        "'action_type' (move|work|talk|recharge|inspect|idle), 'destination' (or null), "
        "and 'content' (short note or null). Keep actions realistic for the rooms."
    )
    schema_hint = "{""action_type"": str, ""destination"": str|null, ""content"": str|null}"
    user_message = f"Robot state:\n{state}\nDecide the next action. Only return JSON."

    raw = chat_json(system_prompt, [{"role": "user", "content": user_message}], schema_hint)
    if not raw or "action_type" not in raw:
        logger.debug("LLM decision missing/invalid for %s; falling back to deterministic", name)
        return _deterministic_robot_policy(name, role, step, location, battery_level, emotions)

    # Normalize output
    action = str(raw.get("action_type", "idle")).lower()
    dest = raw.get("destination")
    content = raw.get("content")
    logger.debug("LLM decision for %s: %s dest=%s", name, action, dest)
    return {"action_type": action, "destination": dest, "content": content}


def decide_supervisor_action(step: int, summary: str) -> dict:
    """Return supervisor action dict {action_type, destination?, target_robot_name?, content?}."""
    if not USE_LLM_POLICY:
        logger.debug("LLM disabled; using deterministic supervisor policy")
        return _deterministic_supervisor_policy(step, summary)

    system_prompt = (
        "You are the Supervisor in Loopforge City. Return ONLY a JSON object with keys "
        "'action_type' (broadcast|inspect|coach|idle), 'target_robot_name' (or null), "
        "'destination' (or null), and 'content' (short message)."
    )
    schema_hint = (
        '{"action_type": str, "target_robot_name": str|null, "destination": str|null, "content": str|null}'
    )
    user_message = (
        "Current step: "
        + str(step)
        + "\nWorld summary:\n"
        + summary
        + "\nDecide the Supervisor action. Only return JSON."
    )

    raw = chat_json(system_prompt, [{"role": "user", "content": user_message}], schema_hint)
    if not raw or "action_type" not in raw:
        logger.debug("LLM supervisor decision invalid; falling back to deterministic")
        return _deterministic_supervisor_policy(step, summary)

    action = str(raw.get("action_type", "inspect")).lower()
    target = raw.get("target_robot_name")
    dest = raw.get("destination")
    content = raw.get("content") or ""
    logger.debug("LLM supervisor action: %s target=%s dest=%s", action, target, dest)
    return {
        "actor_type": "supervisor",
        "action_type": action,
        "target_robot_name": target,
        "destination": dest,
        "content": content,
    }
