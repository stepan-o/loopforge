from __future__ import annotations

"""
Read-only Narrative Viewer for day-level story snippets built from telemetry summaries.

Constraints:
- Pure functions over DaySummary/AgentDayStats (from loopforge.reporting)
- Deterministic, template-based text (no randomness)
- Does not touch simulation, logging, or loopforge.narrative (perception seam)
"""

from dataclasses import dataclass
from typing import List, Dict, Optional

from .reporting import DaySummary, AgentDayStats


@dataclass
class AgentDayBeat:
    name: str
    role: str
    intro: str            # how they start the day
    perception_line: str  # how they feel / what they notice
    actions_line: str     # what they mostly did (flavored)
    closing_line: str     # end-of-day micro reflection


@dataclass
class DayNarrative:
    day_index: int
    day_intro: str        # one-line establishing shot
    agent_beats: List[AgentDayBeat]
    supervisor_line: str  # one line about supervisor tone/behavior
    day_outro: str        # short closing line


# ----------------- Public API -----------------

# Light, static role flavor hooks (deterministic, template-only)
ROLE_FLAVOR: Dict[str, str] = {
    "optimizer": "always chasing efficiency",
    "qa": "ever watchful for cracks in the system",
    "maintenance": "hands always in the guts of the place",
}

def build_day_narrative(
    day_summary: DaySummary,
    day_index: int,
    previous_day_summary: Optional[DaySummary] = None,
) -> DayNarrative:
    """Build a DayNarrative from a DaySummary.

    Numeric inputs are taken exclusively from telemetry-backed DaySummary fields.
    """
    tension_today = float(getattr(day_summary, "tension_score", 0.0) or 0.0)
    day_intro = _describe_tension(tension_today)

    # Build per-agent beats
    beats: List[AgentDayBeat] = []
    for name, stats in sorted(day_summary.agent_stats.items()):
        role = stats.role
        beats.append(
            AgentDayBeat(
                name=name,
                role=role,
                intro=_describe_agent_intro(name, role, stats),
                perception_line=_describe_agent_perception(stats),
                actions_line=_describe_agent_actions(role, stats),
                closing_line=_describe_agent_closing(stats),
            )
        )

    supervisor_line = _describe_supervisor(day_summary)

    # Day outro considers trend vs previous day if provided
    tension_prev = None
    if previous_day_summary is not None:
        try:
            tension_prev = float(getattr(previous_day_summary, "tension_score", 0.0) or 0.0)
        except Exception:
            tension_prev = None
    day_outro = _describe_day_outro(tension_today, tension_prev)

    return DayNarrative(
        day_index=day_index,
        day_intro=day_intro,
        agent_beats=beats,
        supervisor_line=supervisor_line,
        day_outro=day_outro,
    )


# ----------------- Module-private helpers -----------------

def _describe_tension(tension: float) -> str:
    if tension < 0.1:
        return "The factory hums quietly; nothing feels urgent."
    if tension < 0.3:
        return "The factory feels focused but calm."
    if tension < 0.6:
        return "The floor is steady with a subtle edge."
    return "Everyone comes online into a high-pressure shift."


def _describe_agent_intro(name: str, role: str, stats: AgentDayStats) -> str:
    s = float(getattr(stats, "avg_stress", 0.0) or 0.0)
    # Shared bands: low < 0.08, mid 0.08–0.3, high > 0.3
    if s > 0.3:
        base = f"{name} starts the shift wound a little tight."
    elif s >= 0.08:
        base = f"{name} comes online steady but alert."
    else:
        base = f"{name} drifts into the shift almost relaxed."

    # Append light character flavor based on role, if known
    flavor = ROLE_FLAVOR.get((role or "").lower().strip())
    if flavor:
        # Convert final period to an em-dash clause for smoother reading
        if base.endswith("."):
            base = base[:-1] + f" — {flavor}."
        else:
            base = base + f" — {flavor}."
    return base


def _describe_agent_perception(stats: AgentDayStats) -> str:
    s = float(getattr(stats, "avg_stress", 0.0) or 0.0)
    # Guardrail/context ratio hint
    g = int(getattr(stats, "guardrail_count", 0) or 0)
    c = int(getattr(stats, "context_count", 0) or 0)
    if c == 0 and g > 0:
        leaning = "leans heavily on the rulebook"
    elif g == 0 and c > 0:
        leaning = "relies on local judgment"
    else:
        leaning = "balances procedure and judgment"
    tone = "feels strained" if s >= 0.6 else ("feels a mild pull" if s >= 0.3 else "seems unbothered")
    return f"{stats.name} {tone} and {leaning}."


def _describe_agent_actions(role: str, stats: AgentDayStats) -> str:
    g = int(getattr(stats, "guardrail_count", 0) or 0)
    c = int(getattr(stats, "context_count", 0) or 0)

    role_hint = role.lower().strip()
    if role_hint in {"maintenance", "maintainer"}:
        base = "keeps the floor running"
    elif role_hint in {"optimizer", "line_operator", "operator"}:
        base = "pushes the line for output"
    elif role_hint in {"qa", "quality", "inspector"}:
        base = "inspects and checks rather than changing things"
    else:
        base = "handles their usual tasks"

    if c == 0 and g > 0:
        rules = "by the manual"
    elif g == 0 and c > 0:
        rules = "on situational judgment"
    else:
        rules = "mixing policy with on-the-spot calls"

    return f"Mostly {base}, {rules}."


def _describe_agent_closing(stats: AgentDayStats) -> str:
    s = float(getattr(stats, "avg_stress", 0.0) or 0.0)
    # Shared bands: low < 0.08, mid 0.08–0.3, high > 0.3
    if s > 0.3:
        return "Ends the day carrying some weight."
    if s >= 0.08:
        return "Ends the day balanced, tension kept in check."
    return "Ends the day calm, nothing sticking."


def _describe_supervisor(day_summary: DaySummary) -> str:
    # If we had explicit supervisor signals, we could branch here; for now use tension.
    t = float(getattr(day_summary, "tension_score", 0.0) or 0.0)
    if t < 0.1:
        return "Supervisor signs off quietly; just another routine shift."
    if t < 0.3:
        return "Supervisor keeps a steady watch but rarely intervenes."
    if t < 0.6:
        return "Supervisor checks in periodically—gentle reminders over the intercom."
    return "Supervisor’s presence is felt in frequent reminders and broadcasts."


def _describe_day_outro(tension_today: float, tension_prev: Optional[float]) -> str:
    """Trend-aware day outro.

    - If previous day is provided, compute trend with epsilon=0.05 thresholds.
    - Else, fall back to intro-matched current-tension summary.
    """
    if tension_prev is not None:
        delta = tension_today - float(tension_prev)
        if delta > 0.05:
            return "The shift closes on a slightly tighter note; the floor hums with leftover static."
        if delta < -0.05:
            return "The shift winds down lighter than it began; the floor exhales a little."
        return "Shift complete; the floor settles into its usual idle."

    # Day 0 fallback: map to current tension only
    if tension_today > 0.6:
        return "The day ends with tension still clinging to the walls."
    if tension_today < 0.1:
        return "The factory powers down in calm silence."
    return "Shift complete; the floor eases back to idle."