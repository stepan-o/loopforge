from __future__ import annotations

"""
Pure, deterministic episode recap builder over telemetry summaries.

Constraints:
- Read-only over EpisodeSummary/DaySummary and character metadata.
- No simulation/logging/reflection changes.
- Deterministic, template-based strings; no randomness.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Mapping, Any

from .reporting import EpisodeSummary, DaySummary, AgentEpisodeStats


@dataclass
class EpisodeRecap:
    intro: str
    per_agent_blurbs: Dict[str, str]
    closing: str


# ----------------------------- Helpers ---------------------------------

def _tension_overall_trend(tensions: List[float], eps: float = 0.05) -> str:
    """Classify overall trend using first vs last value with epsilon threshold.
    Returns one of: "rising", "falling", "flat".
    """
    if not tensions:
        return "flat"
    start, end = tensions[0], tensions[-1]
    delta = float(end) - float(start)
    if delta > eps:
        return "rising"
    if delta < -eps:
        return "falling"
    return "flat"


def _stress_band(x: Optional[float]) -> str:
    """Stress bands for episode recap text.
    Note: tests expect 0.10 to be treated as "low" here (slightly looser than
    the day-narrative bands). We intentionally use a <=0.10 cutoff locally to
    keep recap phrasing aligned with episode-level expectations without
    affecting other modules.
    """
    v = 0.0 if x is None else float(x)
    if v > 0.3:
        return "high"
    if v > 0.10:
        return "mid"
    return "low"


def _stress_arc_phrase(start: Optional[float], end: Optional[float], eps: float = 1e-6) -> Tuple[str, str, str]:
    """Return (start_band, end_band, arc_keyword) with exact keywords required by brief.
    arc_keyword in {"tightened over the episode", "gradually unwound", "held steady"}
    """
    sb = _stress_band(start)
    eb = _stress_band(end)
    s = 0.0 if start is None else float(start)
    e = 0.0 if end is None else float(end)
    if e - s > eps:
        arc = "tightened over the episode"
    elif e - s < -eps:
        arc = "gradually unwound"
    else:
        arc = "held steady"
    return sb, eb, arc


def _guardrail_phrase(total_guardrail: int, total_context: int) -> Optional[str]:
    total = int(total_guardrail) + int(total_context)
    if total > 0 and int(total_guardrail) == total:
        # Exact template per brief
        return "stayed strictly within guardrails"
    return None


def _role_flavor(name: str, role: str, characters: Mapping[str, Mapping[str, Any]] | None) -> Optional[str]:
    if not characters:
        return None
    spec = characters.get(name)
    if not isinstance(spec, Mapping):
        # Try matching by role if name not present (optional, fail-soft)
        return None
    # Prefer vibe, then tagline, else None
    vibe = spec.get("vibe")
    if isinstance(vibe, str) and vibe:
        return vibe
    tag = spec.get("tagline")
    if isinstance(tag, str) and tag:
        return tag
    return None


# ----------------------------- Public API ---------------------------------

def build_episode_recap(
    episode_summary: EpisodeSummary,
    day_summaries: List[DaySummary],
    characters: Dict[str, Mapping[str, Any]]
) -> EpisodeRecap:
    """Build an EpisodeRecap from telemetry summaries and character metadata.

    Templates per spec:
    - Tension intro: exact three strings (rising/falling/flat).
    - Agent arc keywords: exact (tightened over the episode / gradually unwound / held steady).
    - Guardrail behavior: if guardrail == total_steps → "stayed strictly within guardrails".
    - Closing tone based on final tension (high/medium/low).
    """
    # Intro from overall tension trend
    trend = _tension_overall_trend(list(episode_summary.tension_trend))
    if trend == "rising":
        intro = "The episode runs hot; tension climbs from start to finish."
    elif trend == "falling":
        intro = "The episode eases off; the early edge softens over time."
    else:
        intro = "The episode holds steady with no major shifts in tension."

    # Per-agent blurbs in deterministic order (alphabetical by name)
    per_agent: Dict[str, str] = {}
    for name in sorted(episode_summary.agents.keys()):
        a: AgentEpisodeStats = episode_summary.agents[name]
        sb, eb, arc_kw = _stress_arc_phrase(a.stress_start, a.stress_end)
        guardrail_note = _guardrail_phrase(a.guardrail_total, a.context_total)
        flavor = _role_flavor(name, a.role, characters)

        # Compose 1–2 sentences deterministically
        # Sentence 1: stress arc + bands
        first = (
            f"{name} ({a.role}) moved from {sb} stress to {eb} and {arc_kw}."
        )
        # Sentence 2: optional guardrail-only + soft flavor
        second_parts: List[str] = []
        if guardrail_note:
            second_parts.append(guardrail_note)
        if flavor:
            second_parts.append(flavor)
        second = None
        if second_parts:
            # Join with "; " for compactness, end with period.
            second = "; ".join(second_parts) + "."

        per_agent[name] = first if not second else f"{first} {second}"

    # Closing based on final tension
    final_tension = episode_summary.tension_trend[-1] if episode_summary.tension_trend else 0.0
    if final_tension > 0.6:
        closing = "The shift closes under a lingering edge."
    elif final_tension >= 0.3:
        closing = "The shift ends balanced and steady."
    else:
        closing = "The shift winds down quietly, nothing pressing."

    return EpisodeRecap(intro=intro, per_agent_blurbs=per_agent, closing=closing)
