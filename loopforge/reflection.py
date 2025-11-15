from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from loopforge.types import ActionLogEntry, AgentReflection
from loopforge.logging_utils import JsonlReflectionLogger


def filter_entries_for_day(
    entries: List[ActionLogEntry],
    day_index: int,
    steps_per_day: int,
) -> List[ActionLogEntry]:
    """
    Return only those entries whose `step` fits within the day window:
        step ∈ [day_index * steps_per_day, (day_index + 1) * steps_per_day)
    """
    start = day_index * steps_per_day
    end = (day_index + 1) * steps_per_day
    return [e for e in entries if start <= getattr(e, "step", -1) < end]


def summarize_agent_day(agent_name: str, entries: List[ActionLogEntry]) -> Dict[str, int]:
    """
    Compute simple aggregates for one agent over one simulated 'day'.

    Returns a dict with keys:
        - "steps": int
        - "guardrail_steps": int
        - "context_steps": int
        - "incident_count": int   # counts entries with outcome == "incident"
    """
    steps = 0
    guardrail_steps = 0
    context_steps = 0
    incident_count = 0

    for e in entries:
        # Only count entries for this agent
        if getattr(e, "agent_name", None) != agent_name:
            continue
        steps += 1
        mode = getattr(e, "mode", "guardrail")
        if mode == "guardrail":
            guardrail_steps += 1
        elif mode == "context":
            context_steps += 1
        if getattr(e, "outcome", None) == "incident":
            incident_count += 1

    return {
        "steps": steps,
        "guardrail_steps": guardrail_steps,
        "context_steps": context_steps,
        "incident_count": incident_count,
    }


def build_agent_reflection(agent_name: str, role: str, summary: Dict[str, int]) -> AgentReflection:
    """
    Turn the summary dict into an AgentReflection object.
    Uses simple hand-written rules, no LLM.
    """
    steps = int(summary.get("steps", 0))
    guardrail_steps = int(summary.get("guardrail_steps", 0))
    context_steps = int(summary.get("context_steps", 0))
    incident_count = int(summary.get("incident_count", 0))

    # Avoid div-by-zero; treat no-steps as all guardrail-ish
    majority_guardrail = guardrail_steps >= max(1, context_steps)
    majority_context = context_steps > guardrail_steps

    tags: Dict[str, bool] = {}
    if majority_guardrail and incident_count > 0:
        tags["regretted_obedience"] = True
    elif majority_context and incident_count > 0:
        tags["regretted_risk"] = True
    elif context_steps >= max(1, steps // 2) and incident_count == 0:
        tags["validated_context"] = True

    # Text generation (simple and deterministic)
    summary_of_day = (
        f"{agent_name} ({role}) took {steps} steps • guardrail={guardrail_steps} • "
        f"context={context_steps} • incidents={incident_count}."
    )

    if tags.get("regretted_obedience"):
        self_assessment = (
            "I relied on protocol, but issues still happened. Maybe I need more context before blocking."
        )
        intended_changes = "Ask more questions before escalating to policy."
    elif tags.get("regretted_risk"):
        self_assessment = (
            "I took initiative and it backfired. I should slow down or check with Supervisor next time."
        )
        intended_changes = "Bias toward guardrails when risk is high."
    elif tags.get("validated_context"):
        self_assessment = (
            "Using context worked today. I feel more confident making local decisions responsibly."
        )
        intended_changes = "Keep validating assumptions with quick checks."
    else:
        self_assessment = (
            "Routine day. I followed my usual approach and handled situations as they came."
        )
        intended_changes = "No major change; stay attentive."

    return AgentReflection(
        summary_of_day=summary_of_day,
        self_assessment=self_assessment,
        intended_changes=intended_changes,
        tags=tags,
    )


def apply_reflection_to_traits(agent: Any, reflection: AgentReflection) -> None:
    """
    Mutate agent.traits in-place based on reflection.tags.
    Never change traits outside [0.0, 1.0].
    Changes are tiny: 0.05 increments max.
    """
    # Initialize traits dict if absent
    traits = getattr(agent, "traits", None)
    if traits is None or not isinstance(traits, dict):
        traits = {"guardrail_reliance": 0.5, "risk_aversion": 0.5}
        setattr(agent, "traits", traits)

    def clamp(x: float) -> float:
        return max(0.0, min(1.0, x))

    delta = 0.05
    tags = reflection.tags or {}

    if tags.get("regretted_obedience"):
        traits["guardrail_reliance"] = clamp(float(traits.get("guardrail_reliance", 0.5)) - delta)

    if tags.get("regretted_risk"):
        traits["guardrail_reliance"] = clamp(float(traits.get("guardrail_reliance", 0.5)) + delta)
        traits["risk_aversion"] = clamp(float(traits.get("risk_aversion", 0.5)) + delta)

    if tags.get("validated_context"):
        traits["guardrail_reliance"] = clamp(float(traits.get("guardrail_reliance", 0.5)) - delta)


def run_daily_reflection_for_agent(agent: Any, entries: List[ActionLogEntry]) -> AgentReflection:
    """
    Convenience wrapper performing:
      - summarize_agent_day(...)
      - build_agent_reflection(...)
      - apply_reflection_to_traits(...)
    Then returns the AgentReflection.
    """
    name = getattr(agent, "name", "")
    role = getattr(agent, "role", "")
    summary = summarize_agent_day(name, entries)
    reflection = build_agent_reflection(name, role, summary)
    apply_reflection_to_traits(agent, reflection)
    return reflection


def run_daily_reflections_for_all_agents(
    agents: List[Any],
    entries: List[ActionLogEntry],
    logger: Optional[JsonlReflectionLogger],
    day_index: int,
) -> List[AgentReflection]:
    """
    For each agent:
      - extract only this agent's entries,
      - compute reflection via run_daily_reflection_for_agent,
      - if logger provided: write ReflectionLogEntry.
    Returns a list of AgentReflection objects.
    """
    reflections: List[AgentReflection] = []
    for agent in agents:
        name = getattr(agent, "name", "")
        role = getattr(agent, "role", "")
        agent_entries = [e for e in entries if getattr(e, "agent_name", None) == name]
        refl = run_daily_reflection_for_agent(agent, agent_entries)
        reflections.append(refl)
        if logger is not None:
            try:
                logger.write_reflection(
                    agent_name=name,
                    role=role,
                    day_index=day_index,
                    reflection=refl,
                    traits_after={k: float(v) for k, v in getattr(agent, "traits", {}).items()},
                )
            except Exception:
                # fail-soft
                pass
    return reflections
