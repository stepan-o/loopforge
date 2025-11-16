from __future__ import annotations

"""
Rule-based, deterministic explainer built on top of explainer_context structures.

Inputs are JSON-serializable dicts produced by explainer_context.
No simulation/logging is touched. All phrasing is template-based.
"""

from typing import Any, Dict


# Shared stress band thresholds from narrative viewer
# low < 0.08, mid 0.08–0.3, high > 0.3

def _stress_band(x: float | None) -> str:
    v = 0.0 if x is None else float(x)
    if v > 0.3:
        return "high"
    if v >= 0.08:
        return "moderate"
    return "low"


def explain_agent_episode(agent_context: Dict[str, Any]) -> str:
    """Produce a short, deterministic paragraph explaining an agent's episode.

    agent_context structure is defined in build_agent_focus_context(...) and includes:
      - agent_name
      - agent: {role, vibe?, tagline?, stress_start, stress_end, stress_arc, guardrail_total, context_total, guardrail_ratio}
      - episode_meta: {tension_direction}
      - per_day: list of daily stats (unused for text for now)
    """
    name = str(agent_context.get("agent_name", "")).strip()
    agent = agent_context.get("agent", {}) or {}
    role = str(agent.get("role", "")).strip()
    vibe = agent.get("vibe")
    tagline = agent.get("tagline")
    stress_start = agent.get("stress_start")
    stress_end = agent.get("stress_end")
    stress_arc = agent.get("stress_arc")  # rising | falling | flat
    g_total = int(agent.get("guardrail_total", 0) or 0)
    c_total = int(agent.get("context_total", 0) or 0)
    ratio = float(agent.get("guardrail_ratio", 0.0) or 0.0)

    epi = agent_context.get("episode_meta", {}) or {}
    tension_dir = str(epi.get("tension_direction", "flat"))  # rising | falling | flat

    # Opening sentence with tension profile + optional vibe
    if tension_dir == "rising":
        tension_word = "rising"
    elif tension_dir == "falling":
        tension_word = "easing"
    else:
        tension_word = "steady"
    parts: list[str] = []
    first = f"{name} ({role}) spent this episode working under a {tension_word} factory tension profile."
    parts.append(first)
    if isinstance(vibe, str) and vibe:
        parts.append(f"Their baseline: {vibe}.")
    elif isinstance(tagline, str) and tagline:
        # fall back to tagline if vibe unavailable
        parts.append(f"Baseline note: {tagline}.")

    # Stress arc sentence using shared bands
    sb = _stress_band(stress_start)
    eb = _stress_band(stress_end)
    if stress_arc == "rising":
        parts.append(f"Their stress tightened over the episode, moving from {sb} to {eb}.")
    elif stress_arc == "falling":
        parts.append(f"Their stress gradually unwound, moving from {sb} to {eb}.")
    else:
        parts.append(f"Their stress held steady at {eb}.")

    # Guardrail behavior sentence
    total = g_total + c_total
    if total == 0:
        parts.append("They barely registered in the action logs this time.")
    else:
        if ratio > 0.9:
            parts.append("They stayed strictly within guardrails, rarely acting on raw context.")
        elif ratio < 0.5:
            parts.append("They leaned more on context than policy, taking initiative beyond the written rules.")
        else:
            parts.append("They split their decisions between policy and context without a clear bias.")

    # Alignment sentence (optional)
    if stress_arc == "rising" and tension_dir == "rising":
        parts.append("Their internal stress rose in step with the overall factory tension.")
    elif stress_arc == "falling" and tension_dir == "falling":
        parts.append("They managed to relax as the factory itself eased off.")
    elif stress_arc in {"rising", "falling"}:
        parts.append("Their internal arc didn’t fully match the factory’s overall mood.")

    return " " .join(parts)
