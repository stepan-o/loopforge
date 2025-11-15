"""Narrative layer primitives for Loopforge City.

This module introduces a thin perception→plan seam between the environment
and agent policies. It does NOT change simulation mechanics; it just provides
structured objects we can later feed to an LLM for more narrative behavior.

Phase 1 scope:
- AgentPerception: what the environment tells an agent they "see" this step.
- AgentActionPlan: what the agent intends to do, plus a short narrative.
- build_agent_perception: helper to construct perceptions from current state.

Future phases (not implemented here):
- AgentReflection for day/episode-end reflections driving trait evolution.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class AgentPerception:
    """A structured snapshot of what the agent perceives this step.

    Note: Numeric internal state (emotions/traits) is included here in a
    structured form, but in narrative prompts the agent will receive a
    textual rendering of these. Keeping both allows deterministic tests
    and future prompt building without DB access here.
    """

    step: int
    name: str
    role: str
    location: str
    battery_level: int

    emotions: Dict[str, float]
    traits: Dict[str, float]

    world_summary: str
    personal_recent_summary: str
    local_events: List[str] = field(default_factory=list)
    recent_supervisor_text: Optional[str] = None

    # Raw context not directly "shown" to the agent; policies may use it.
    raw_context: Dict[str, Any] | None = None


@dataclass
class AgentActionPlan:
    """Canonical, structured description of what the agent intends to do.

    The environment/simulation will translate this back into concrete state
    updates using existing mechanics (locations, batteries, logs, etc.).
    """

    intent: str  # e.g. "work", "inspect", "talk", "recharge", "move", "idle"
    move_to: Optional[str]
    targets: List[str] = field(default_factory=list)
    riskiness: float = 0.0  # 0..1 simple perceived risk indicator

    # Free-form narrative describing the immediate plan in natural language
    narrative: str = ""


def build_agent_perception(agent: Any, env: Any, step: int) -> AgentPerception:
    """Construct an AgentPerception from a RobotAgent and LoopforgeEnvironment.

    This helper is intentionally light and deterministic. It composes small
    human-readable summaries without calling any LLMs. The `env` object is
    expected to provide `step`, optional `recent_supervisor_text`, and an
    `events_buffer` list of EnvironmentEvent-like objects with `location`
    and `description` attributes.
    """
    # Emotions/traits are simple dataclasses with floats in [0,1]
    emotions = {
        "stress": float(getattr(agent.emotions, "stress", 0.0)),
        "curiosity": float(getattr(agent.emotions, "curiosity", 0.0)),
        "social_need": float(getattr(agent.emotions, "social_need", 0.0)),
        "satisfaction": float(getattr(agent.emotions, "satisfaction", 0.0)),
    }
    traits = {
        "risk_aversion": float(getattr(agent.traits, "risk_aversion", 0.5)),
        "obedience": float(getattr(agent.traits, "obedience", 0.5)),
        "ambition": float(getattr(agent.traits, "ambition", 0.5)),
        "empathy": float(getattr(agent.traits, "empathy", 0.5)),
        "blame_external": float(getattr(agent.traits, "blame_external", 0.5)),
    }

    # Local events: take buffered events at the same location this step
    local_events: List[str] = []
    try:
        for evt in getattr(env, "events_buffer", []) or []:
            if getattr(evt, "location", None) == agent.location:
                desc = getattr(evt, "description", "")
                if desc:
                    local_events.append(str(desc))
    except Exception:
        # Be resilient to any mismatches; this is best-effort context.
        local_events = []

    # Deterministic mini-summaries; keep them short for logs/tests
    world_summary = (
        f"t={step} • rooms={len(getattr(env, 'rooms', []) or [])} • you are at {agent.location}"
    )
    personal_recent_summary = (
        f"You feel stress={emotions['stress']:.2f}, satisfaction={emotions['satisfaction']:.2f}."
    )

    return AgentPerception(
        step=step,
        name=str(getattr(agent, "name", "")),
        role=str(getattr(agent, "role", "")),
        location=str(getattr(agent, "location", "")),
        battery_level=int(getattr(agent, "battery_level", 0)),
        emotions=emotions,
        traits=traits,
        world_summary=world_summary,
        personal_recent_summary=personal_recent_summary,
        local_events=local_events,
        recent_supervisor_text=getattr(env, "recent_supervisor_text", None),
        raw_context={"rooms": list(getattr(env, "rooms", []) or [])},
    )


# NOTE: Future Phase hook (not implemented):
# @dataclass
# class AgentReflection: ...  # day/episode-end self-assessment and learning
