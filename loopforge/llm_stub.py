"""Decision logic for agents with optional LLM-backed policy.

Default behavior is deterministic. When USE_LLM_POLICY is true and an
OPENAI_API_KEY is provided, this module will ask an LLM to propose the next
action, falling back to the deterministic policy on any error or parse issue.
"""
from __future__ import annotations

import logging
from typing import Any, Literal

from .config import USE_LLM_POLICY
from .llm_client import chat_json
from .emotions import EmotionState
from .narrative import AgentPerception, AgentActionPlan, build_agent_perception
from pathlib import Path
from .logging_utils import JsonlActionLogger, log_action_step

# Very simple global logger; optional and fail-soft.
_ACTION_LOGGER: JsonlActionLogger | None = JsonlActionLogger(Path("logs/loopforge_actions.jsonl"))

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


# ------------------------------ Narrative plan helpers -----------------------

def decide_mode_from_traits(perception: AgentPerception) -> Literal["guardrail", "context"]:
    """Choose a simple mode from traits (deterministic, safe).

    Heuristic:
    - Strong guardrail reliance OR very high risk aversion ⇒ "guardrail"
    - Clearly low guardrail reliance AND low risk aversion ⇒ "context"
    - Otherwise default to "guardrail" for safety.
    """
    traits = perception.traits or {}
    gr = float(traits.get("guardrail_reliance", 0.5))
    ra = float(traits.get("risk_aversion", 0.5))
    if gr >= 0.7 or ra >= 0.8:
        return "guardrail"
    if gr <= 0.3 and ra <= 0.4:
        return "context"
    return "guardrail"


def decide_robot_action_plan(perception: AgentPerception) -> AgentActionPlan:
    """Deterministic plan based on the same logic as the old stub.

    Phase 3: we compute a mode from traits and stuff it into the plan, but
    we do not expose it in the legacy action dict yet.
    """
    name = perception.name
    role = perception.role
    step = perception.step
    location = perception.location
    battery = perception.battery_level

    action = "idle"
    dest = None

    if battery < 30 or (step % 5 == 0 and battery < 60):
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

    # Simple perceived risk: inversely proportional to battery and directly to stress
    stress = float(perception.emotions.get("stress", 0.2))
    risk = min(1.0, max(0.0, 0.5 * stress + (1.0 - min(1.0, battery / 100.0)) * 0.3))

    narrative = (
        f"I plan to {action} at {dest or location}. Battery={battery}%, stress={stress:.2f}."
    )
    mode = decide_mode_from_traits(perception)
    return AgentActionPlan(intent=action, move_to=dest, targets=[], riskiness=risk, mode=mode, narrative=narrative)


def decide_supervisor_action_plan(step: int, summary: str) -> AgentActionPlan:
    """Deterministic supervisor plan mirroring the previous stub policy."""
    if step % 4 == 0:
        intent = "broadcast"
        dest = None
        narrative = f"I will broadcast an update for t={step}."
    elif "high stress" in summary.lower():
        intent = "coach"
        dest = None
        narrative = "I will coach Sprocket to consider a short recharge."
    else:
        intent = "inspect"
        dest = "control_room"
        narrative = "I will inspect the control room."

    return AgentActionPlan(intent=intent, move_to=dest, targets=[], riskiness=0.2, narrative=narrative)


# ------------------------------ Public API ----------------------------------

def decide_robot_action_plan_and_dict(perception: AgentPerception) -> tuple[AgentActionPlan, dict]:
    """Return both an AgentActionPlan and the legacy action dict for logging.

    Behavior:
    - When USE_LLM_POLICY is False, this wraps decide_robot_action_plan(perception)
      and constructs the legacy action dict from the plan.
    - When USE_LLM_POLICY is True, it queries the LLM for a legacy action dict
      and synthesizes an AgentActionPlan with deterministic risk and mode
      heuristics. On any LLM failure, it falls back to the deterministic plan.
    """
    name = perception.name
    role = perception.role
    step = perception.step
    location = perception.location
    battery_level = int(perception.battery_level or 0)

    if not USE_LLM_POLICY:
        plan = decide_robot_action_plan(perception)
        action_dict = {
            "action_type": plan.intent,
            "destination": plan.move_to,
            "content": None,
            "narrative": plan.narrative,
        }
        return plan, action_dict

    state: dict[str, Any] = {
        "name": name,
        "role": role,
        "step": step,
        "location": location,
        "battery_level": battery_level,
        "emotions": {
            "stress": float(perception.emotions.get("stress", 0.2)),
            "curiosity": float(perception.emotions.get("curiosity", 0.5)),
            "social_need": float(perception.emotions.get("social_need", 0.3)),
            "satisfaction": float(perception.emotions.get("satisfaction", 0.5)),
        },
    }

    system_prompt = (
        "You control a robot in Loopforge City. Return ONLY a JSON object with keys "
        "'action_type' (move|work|talk|recharge|inspect|idle), 'destination' (or null), "
        "and 'content' (short note or null). Keep actions realistic for the rooms."
    )
    schema_hint = '{"action_type": str, "destination": str|null, "content": str|null}'
    user_message = f"Robot state:\n{state}\nDecide the next action. Only return JSON."

    raw = chat_json(system_prompt, [{"role": "user", "content": user_message}], schema_hint)
    if not raw or "action_type" not in raw:
        logger.debug("LLM decision missing/invalid for %s; falling back to deterministic", name)
        plan = decide_robot_action_plan(perception)
        action_dict = {
            "action_type": plan.intent,
            "destination": plan.move_to,
            "content": None,
            "narrative": plan.narrative,
        }
        return plan, action_dict

    action = str(raw.get("action_type", "idle")).lower()
    dest = raw.get("destination")
    content = raw.get("content")

    stress = float(perception.emotions.get("stress", 0.2))
    risk = min(1.0, max(0.0, 0.5 * stress + (1.0 - min(1.0, battery_level / 100.0)) * 0.3))
    mode = decide_mode_from_traits(perception)
    narrative = f"I will {action} at {dest or location}. Battery={battery_level}%, stress={stress:.2f}."
    plan = AgentActionPlan(intent=action, move_to=dest, targets=[], riskiness=risk, mode=mode, narrative=narrative)
    action_dict = {"action_type": action, "destination": dest, "content": content, "narrative": narrative}
    return plan, action_dict

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
        logger.debug("LLM disabled; using narrative plan for %s", name)
        # Build a minimal perception (traits/local events omitted here)
        from .narrative import build_agent_perception
        fake_agent = type("A", (), {
            "name": name,
            "role": role,
            "location": location,
            "battery_level": battery_level,
            "emotions": emotions,
            # default neutral traits-like shim
            "traits": type("T", (), {
                "risk_aversion": 0.5,
                "obedience": 0.5,
                "ambition": 0.5,
                "empathy": 0.5,
                "blame_external": 0.5,
            })(),
        })()
        fake_env = type("E", (), {"rooms": [], "events_buffer": [], "recent_supervisor_text": None})()
        perception = build_agent_perception(fake_agent, fake_env, step)
        plan = decide_robot_action_plan(perception)
        dest = plan.move_to
        return {"action_type": plan.intent, "destination": dest, "content": None, "narrative": plan.narrative}

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
        logger.debug("LLM disabled; using narrative supervisor plan")
        plan = decide_supervisor_action_plan(step, summary)
        result = {
            "actor_type": "supervisor",
            "action_type": plan.intent,
            "destination": plan.move_to,
            "content": None,
        }
        # In simple plan, we can surface narrative via content for broadcasts/coach, else ignore
        if plan.intent in {"broadcast", "coach"}:
            result["content"] = plan.narrative
        # return with narrative key for consumers interested in it
        result["narrative"] = plan.narrative
        return result

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
