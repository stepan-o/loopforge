"""Narrative layer primitives for Loopforge City.

This module defines the perception → plan seam and constructs perceptions
using the shared types in `loopforge.types`. Simulation mechanics remain
unchanged; this is a structural module consumed by policy code.
"""
from __future__ import annotations

from typing import Any, List

# Import and re-expose shared types to keep imports stable for existing tests
from loopforge.types import AgentPerception, AgentActionPlan

__all__ = ["AgentPerception", "AgentActionPlan", "build_agent_perception"]


def build_agent_perception(agent: Any, env: Any, step: int) -> AgentPerception:
    """Construct the AgentPerception for a single agent at a given step.

    This is the only place that should assemble an AgentPerception from
    environment / agent state. Future phases may introduce biases or
    omissions; for now this is a straightforward snapshot.
    """
    name = getattr(agent, "name", "")
    role = getattr(agent, "role", "")
    location = getattr(agent, "location", "")

    # Battery level can be int 0..100 in current code; map to float or leave as-is
    battery_level = getattr(agent, "battery_level", None)

    # Emotions/traits may be dataclasses; serialize to simple dicts
    emotions = {}
    try:
        emotions = {
            "stress": float(getattr(getattr(agent, "emotions", object()), "stress", 0.0)),
            "curiosity": float(getattr(getattr(agent, "emotions", object()), "curiosity", 0.0)),
            "social_need": float(getattr(getattr(agent, "emotions", object()), "social_need", 0.0)),
            "satisfaction": float(getattr(getattr(agent, "emotions", object()), "satisfaction", 0.0)),
        }
    except Exception:
        emotions = dict(getattr(agent, "emotions", {}) or {})

    traits = {}
    try:
        traits = {
            "risk_aversion": float(getattr(getattr(agent, "traits", object()), "risk_aversion", 0.5)),
            "obedience": float(getattr(getattr(agent, "traits", object()), "obedience", 0.5)),
            "ambition": float(getattr(getattr(agent, "traits", object()), "ambition", 0.5)),
            "empathy": float(getattr(getattr(agent, "traits", object()), "empathy", 0.5)),
            "blame_external": float(getattr(getattr(agent, "traits", object()), "blame_external", 0.5)),
        }
    except Exception:
        traits = dict(getattr(agent, "traits", {}) or {})

    # Deterministic, compact summaries to aid logs/tests (non-empty)
    world_summary = (
        f"t={step} • rooms={len(getattr(env, 'rooms', []) or [])} • you are at {location}"
    )
    # Pull a couple of emotion signals if available
    s = emotions.get("stress", 0.0)
    sat = emotions.get("satisfaction", 0.0)
    personal_recent_summary = f"You feel stress={s:.2f}, satisfaction={sat:.2f}."

    # Local events via optional env helper
    local_events: List[str] = []
    get_local_events_for_agent = getattr(env, "get_local_events_for_agent", None)
    if callable(get_local_events_for_agent):
        try:
            local_events = list(get_local_events_for_agent(agent))
        except Exception:
            local_events = []

    recent_supervisor_text = getattr(
        agent,
        "recent_supervisor_text",
        getattr(env, "recent_supervisor_text", None),
    )

    return AgentPerception(
        step=int(step),
        name=str(name),
        role=str(role),
        location=str(location),
        battery_level=battery_level,  # leave as provided (Optional[float] in types)
        emotions=dict(emotions),
        traits=dict(traits),
        world_summary=world_summary,
        personal_recent_summary=personal_recent_summary,
        local_events=list(local_events),
        recent_supervisor_text=recent_supervisor_text,
        extra={},
    )
