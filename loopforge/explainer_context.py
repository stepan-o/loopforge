from __future__ import annotations

"""
Pure, deterministic context builders for developer explainers.

Constraints:
- Read-only over EpisodeSummary/DaySummary and characters metadata.
- No simulation/logging/reflection changes.
- JSON-serializable dicts suitable for CLI printing or future UI.
"""

from typing import Any, Dict, List, Mapping, Optional

from .reporting import EpisodeSummary, DaySummary


def _tension_direction(values: List[float], eps: float = 0.05) -> str:
    """Classify overall tension trend (first vs last) with epsilon threshold.
    Returns one of: "rising", "falling", "flat".
    """
    if not values:
        return "flat"
    start, end = float(values[0]), float(values[-1])
    delta = end - start
    if delta > eps:
        return "rising"
    if delta < -eps:
        return "falling"
    return "flat"


def _stress_arc(start: Optional[float], end: Optional[float], eps: float = 0.05) -> str:
    """Return stress arc label using thresholds from brief.
    rising if end - start > 0.05, falling if start - end > 0.05, else flat.
    """
    s = 0.0 if start is None else float(start)
    e = 0.0 if end is None else float(end)
    if e - s > eps:
        return "rising"
    if s - e > eps:
        return "falling"
    return "flat"


def _guardrail_ratio(g: int, c: int) -> float:
    total = int(g) + int(c)
    if total <= 0:
        return 0.0
    return float(int(g)) / float(total)


def build_episode_context(
    episode_summary: EpisodeSummary,
    day_summaries: List[DaySummary],
    characters: Dict[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build a JSON-serializable context dict for the whole episode.

    Structure:
    {
      "episode_meta": {"days": int, "tension_values": [...], "tension_direction": "rising|falling|flat"},
      "agents": {
        name: {
          "role": str,
          "vibe": Optional[str],
          "tagline": Optional[str],
          "stress_start": float|None,
          "stress_end": float|None,
          "stress_arc": "rising|falling|flat",
          "guardrail_total": int,
          "context_total": int,
          "guardrail_ratio": float,
        },
        ...
      }
    }
    """
    tension_values = list(episode_summary.tension_trend)
    ctx: Dict[str, Any] = {
        "episode_meta": {
            "days": len(day_summaries),
            "tension_values": tension_values,
            "tension_direction": _tension_direction(tension_values),
        },
        "agents": {},
    }

    for name, a in sorted(episode_summary.agents.items()):
        spec = characters.get(name, {}) if isinstance(characters, dict) else {}
        vibe = spec.get("vibe") if isinstance(spec, Mapping) else None
        tagline = spec.get("tagline") if isinstance(spec, Mapping) else None
        arc = _stress_arc(a.stress_start, a.stress_end)
        g = int(a.guardrail_total)
        c = int(a.context_total)
        ctx["agents"][name] = {
            "role": a.role,
            "vibe": vibe if isinstance(vibe, str) else None,
            "tagline": tagline if isinstance(tagline, str) else None,
            "stress_start": a.stress_start,
            "stress_end": a.stress_end,
            "stress_arc": arc,
            "guardrail_total": g,
            "context_total": c,
            "guardrail_ratio": _guardrail_ratio(g, c),
        }

    return ctx


def build_agent_focus_context(
    episode_summary: EpisodeSummary,
    day_summaries: List[DaySummary],
    characters: Dict[str, Mapping[str, Any]],
    agent_name: str,
) -> Dict[str, Any]:
    """Build a per-agent focused context using episode context + per-day rollups.

    Structure:
    {
      "agent_name": str,
      "agent": { ...same shape as episode_context["agents"][name]... },
      "episode_meta": { ... },
      "per_day": [ {"day_index": int, "avg_stress": float, "guardrail_count": int, "context_count": int}, ... ],
    }
    """
    ep_ctx = build_episode_context(episode_summary, day_summaries, characters)
    agent_block = ep_ctx["agents"].get(agent_name, None)
    # Build per-day stats for this agent
    per_day: List[Dict[str, Any]] = []
    for d in day_summaries:
        s = d.agent_stats.get(agent_name)
        if s is None:
            continue
        per_day.append(
            {
                "day_index": int(getattr(d, "day_index", len(per_day))),
                "avg_stress": float(getattr(s, "avg_stress", 0.0) or 0.0),
                "guardrail_count": int(getattr(s, "guardrail_count", 0) or 0),
                "context_count": int(getattr(s, "context_count", 0) or 0),
            }
        )

    return {
        "agent_name": agent_name,
        "agent": agent_block,
        "episode_meta": ep_ctx["episode_meta"],
        "per_day": per_day,
    }
