from __future__ import annotations

"""
Daily Narrative Logs — compact, deterministic day summaries built from telemetry.

Constraints:
- Pure, deterministic, read-only over DaySummary/AgentDayStats and (optionally) previous DaySummary
- No simulation, logging, or schema changes
- Zero randomness; template-based strings only
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Mapping, Any

from .reporting import DaySummary, AgentDayStats


# ----------------------- Public types -----------------------

@dataclass
class DailyLog:
    day_index: int
    intro: str
    agent_beats: Dict[str, List[str]] = field(default_factory=dict)  # agent -> list of 1–3 short lines
    general_beats: List[str] = field(default_factory=list)
    closing: str = ""


# ----------------------- Helpers ----------------------------

# Role flavor hooks (deterministic)
_ROLE_FLAVOR: Dict[str, str] = {
    "optimizer": "always chasing efficiency",
    "qa": "ever watchful for cracks in the system",
    "maintenance": "hands always in the guts of the place",
}


def _stress_band(x: float) -> str:
    # Bands per spec: low < 0.08, mid 0.08–0.3, high > 0.3
    if x > 0.3:
        return "high"
    if x >= 0.08:
        return "mid"
    return "low"


def _tension_intro(t_today: float, prev: Optional[float], day_index: int) -> str:
    # Day 0 → flat intro per spec
    if day_index == 0 or prev is None:
        return "The floor holds steady with no major shift at the start."
    delta = float(t_today) - float(prev)
    if delta > 0.05:
        return "The floor starts tight and the early pulse runs hot."
    if delta < -0.05:
        return "The floor begins calm and keeps easing off."
    return "The floor holds steady with no major shift at the start."


def _agent_beats_for(stats: AgentDayStats, prev: Optional[AgentDayStats]) -> List[str]:
    lines: List[str] = []

    s = float(getattr(stats, "avg_stress", 0.0) or 0.0)
    g = int(getattr(stats, "guardrail_count", 0) or 0)
    c = int(getattr(stats, "context_count", 0) or 0)
    role_key = (getattr(stats, "role", "") or "").lower().strip()

    # Line 1: stress band + role flavor
    band = _stress_band(s)
    if band == "high":
        first = "Starts the day wound a little tight."
    elif band == "mid":
        first = "Starts steady but alert."
    else:
        first = "Starts relaxed and light."
    flavor = _ROLE_FLAVOR.get(role_key)
    if flavor:
        # Append with an em-dash for compact flavor
        if first.endswith("."):
            first = first[:-1] + f" — {flavor}."
        else:
            first = first + f" — {flavor}."
    lines.append(first)

    # Line 2: guardrail/context leaning
    if c == 0 and g > 0:
        second = "Leans heavily on protocol."
    elif g == 0 and c > 0:
        second = "Acts on local judgment."
    else:
        second = "Splits decisions between protocol and context."
    lines.append(second)

    # Optional Line 3: deltas vs previous day (if provided)
    if prev is not None:
        prev_s = float(getattr(prev, "avg_stress", 0.0) or 0.0)
        prev_g = int(getattr(prev, "guardrail_count", 0) or 0)
        prev_c = int(getattr(prev, "context_count", 0) or 0)
        # Stress drift
        if s - prev_s > 0.05:
            delta_line = "Stress rose compared to yesterday."
        elif prev_s - s > 0.05:
            delta_line = "Stress eased compared to yesterday."
        else:
            delta_line = None
        # Guardrail/context drift (use ratio; avoid div-by-zero)
        total = g + c
        prev_total = prev_g + prev_c
        ratio = (g / total) if total > 0 else 0.0
        prev_ratio = (prev_g / prev_total) if prev_total > 0 else 0.0
        drift_line = None
        if ratio - prev_ratio > 0.2:
            drift_line = "Shifted toward protocol."
        elif prev_ratio - ratio > 0.2:
            drift_line = "Shifted toward context."
        # Choose at most one delta line to keep log compact
        chosen = delta_line or drift_line
        if chosen:
            lines.append(chosen)

    # Cap at 3 lines
    return lines[:3]


def _general_beats(day: DaySummary, prev: Optional[DaySummary]) -> List[str]:
    beats: List[str] = []
    t = float(getattr(day, "tension_score", 0.0) or 0.0)

    # Supervisor presence proxy via tension bands
    if t > 0.6:
        beats.append("Supervisor checked in often.")
    elif t >= 0.3:
        beats.append("Supervisor kept a steady watch.")
    else:
        beats.append("Supervisor stayed mostly quiet.")

    # Protocol vs context skew
    total_g = sum(int(s.guardrail_count or 0) for s in day.agent_stats.values())
    total_c = sum(int(s.context_count or 0) for s in day.agent_stats.values())
    if total_g + total_c > 0:
        if total_g >= int(0.6 * (total_g + total_c)):
            beats.append("Work skewed toward protocol.")
        elif total_c >= int(0.6 * (total_g + total_c)):
            beats.append("Initiative showed in context calls.")

    # Overall stress drift vs previous day (if available)
    if prev is not None and prev.agent_stats:
        from statistics import mean

        cur_mean = mean([float(s.avg_stress or 0.0) for s in day.agent_stats.values()]) if day.agent_stats else 0.0
        prev_mean = mean([float(s.avg_stress or 0.0) for s in prev.agent_stats.values()]) if prev.agent_stats else 0.0
        if cur_mean - prev_mean > 0.05:
            beats.append("Overall stress tightened a notch.")
        elif prev_mean - cur_mean > 0.05:
            beats.append("Overall stress eased a notch.")

    return beats[:3]


def _closing_by_tension(t: float) -> str:
    if t < 0.08:
        return "The floor winds down quietly."
    if t <= 0.30:
        return "The day ends balanced and steady."
    return "The day closes with a lingering edge."


# ----------------------- Public builder ---------------------

def build_daily_log(
    day_summary: DaySummary,
    day_index: int,
    previous_day_summary: Optional[DaySummary] = None,
    characters: Optional[Mapping[str, Mapping[str, Any]]] = None,  # reserved; not required for current rules
) -> DailyLog:
    """Build a compact DailyLog from telemetry-backed DaySummary.

    - Intro: tension delta vs previous (±0.05), Day 0 → flat intro.
    - Agent beats: 1–3 short lines per agent (stress band + role flavor, guardrail/context leaning, optional deltas vs prev).
    - General beats: 1–3 lines (supervisor presence proxy, protocol/context skew, overall stress drift).
    - Closing: based on day tension band per spec.
    """
    t_today = float(getattr(day_summary, "tension_score", 0.0) or 0.0)
    t_prev = float(getattr(previous_day_summary, "tension_score", 0.0) or 0.0) if previous_day_summary is not None else None
    intro = _tension_intro(t_today, t_prev, day_index)

    # Build per-agent beats (deterministic order by agent name)
    beats: Dict[str, List[str]] = {}
    prev_map: Dict[str, AgentDayStats] = previous_day_summary.agent_stats if previous_day_summary is not None else {}
    for name in sorted(day_summary.agent_stats.keys()):
        cur = day_summary.agent_stats[name]
        prev = prev_map.get(name) if isinstance(prev_map, dict) else None
        beats[name] = _agent_beats_for(cur, prev)

    general = _general_beats(day_summary, previous_day_summary)
    closing = _closing_by_tension(t_today)

    return DailyLog(
        day_index=day_index,
        intro=intro,
        agent_beats=beats,
        general_beats=general,
        closing=closing,
    )
