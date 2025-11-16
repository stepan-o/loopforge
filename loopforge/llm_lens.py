from __future__ import annotations

"""
LLM-ready Narrative Lens scaffolding (pure, deterministic, no side effects).

This module defines the typed contract for future LLM-style narrative
interpretation and provides deterministic "fake LLM" helpers that operate on
telemetry-derived summaries only. Nothing here talks to external services.

Constraints:
- Pure dataclasses and pure builder functions
- Deterministic rule-based fake outputs (no randomness)
- No simulation/logging/perception changes
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional

from .reporting import DaySummary, EpisodeSummary
from .characters import CHARACTERS


# ------------------------------- Types ---------------------------------

@dataclass
class LLMPerceptionLensInput:
    agent_name: str
    role: str
    day_index: int
    perception_mode: str  # accurate | partial | spin
    avg_stress: float
    guardrail_count: int
    context_count: int
    tension: float
    world_summary: str
    recent_events: List[str]
    supervisor_tone_hint: str  # "gentle" | "steady" | "strict"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMPerceptionLensOutput:
    agent_name: str
    emotional_read: str         # 1–2 sentences
    risk_assessment: str        # e.g. "stable", "at risk of burnout"
    suggested_focus: str        # e.g. "reduce guardrail reliance", "increase autonomy"
    supervisor_comment_prompt: str  # seed line Supervisor could say
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMEpisodeLensInput:
    episode_id: str
    day_count: int
    tension_trend: List[float]
    agent_summaries: List[Dict[str, Any]]  # derived from EpisodeSummary/Character Sheets


@dataclass
class LLMEpisodeLensOutput:
    episode_id: str
    episode_theme: str         # e.g. "cooling factory after a hot start"
    key_risks: List[str]
    key_opportunities: List[str]
    supervisor_script_seed: str  # 1–2 lines Supervisor could broadcast next episode
    meta: Dict[str, Any] = field(default_factory=dict)


# ------------------------ Builder helpers ------------------------------

def _tone_from_tension(t: float) -> str:
    if t >= 0.6:
        return "strict"
    if t >= 0.3:
        return "steady"
    return "gentle"


def build_llm_perception_lens_input(day_summary: DaySummary, agent_name: str) -> Optional[LLMPerceptionLensInput]:
    """Construct an LLMPerceptionLensInput from a DaySummary slice for one agent.

    - Pulls avg_stress, guardrail/context counts from DaySummary.agent_stats
    - Uses DaySummary.tension_score for supervisor_tone_hint mapping
    - Uses DaySummary.perception_mode
    - world_summary/recent_events are placeholders (kept deterministic)
    """
    stats = day_summary.agent_stats.get(agent_name)
    if stats is None:
        return None

    # Per-template fields
    s = float(getattr(stats, "avg_stress", 0.0) or 0.0)
    g = int(getattr(stats, "guardrail_count", 0) or 0)
    c = int(getattr(stats, "context_count", 0) or 0)
    t = float(getattr(day_summary, "tension_score", 0.0) or 0.0)
    pm = str(getattr(day_summary, "perception_mode", "accurate") or "accurate")

    # Minimal free-text fields (pure, deterministic placeholders)
    world_summary = f"day={day_summary.day_index} • mode={pm} • tension={t:.2f}"
    recent_events: List[str] = []

    return LLMPerceptionLensInput(
        agent_name=agent_name,
        role=stats.role,
        day_index=day_summary.day_index,
        perception_mode=pm,
        avg_stress=s,
        guardrail_count=g,
        context_count=c,
        tension=t,
        world_summary=world_summary,
        recent_events=recent_events,
        supervisor_tone_hint=_tone_from_tension(t),
        extra={},
    )


def _guardrail_ratio(g: int, c: int) -> float:
    total = int(g) + int(c)
    if total <= 0:
        return 0.0
    return float(int(g)) / float(total)


def build_llm_episode_lens_input(
    episode_summary: EpisodeSummary,
    characters: Mapping[str, Mapping[str, Any]] | None = None,
    *,
    episode_id: str = "ep-0",
) -> LLMEpisodeLensInput:
    """Build the episode-level lens input from EpisodeSummary + characters.

    The episode_id is a deterministic external label; default to "ep-0".
    """
    chars = characters or CHARACTERS

    agent_summaries: List[Dict[str, Any]] = []
    for name in sorted(episode_summary.agents.keys()):
        a = episode_summary.agents[name]
        spec = chars.get(name, {}) if isinstance(chars, Mapping) else {}
        vibe = spec.get("vibe") if isinstance(spec, Mapping) else None
        role = a.role
        g = int(a.guardrail_total)
        c = int(a.context_total)
        agent_summaries.append(
            {
                "name": name,
                "role": role,
                "stress_start": a.stress_start,
                "stress_end": a.stress_end,
                "guardrail_ratio": _guardrail_ratio(g, c),
                "vibe": vibe if isinstance(vibe, str) else None,
            }
        )

    return LLMEpisodeLensInput(
        episode_id=episode_id,
        day_count=len(episode_summary.days),
        tension_trend=list(episode_summary.tension_trend),
        agent_summaries=agent_summaries,
    )


# ---------------------- Deterministic fake LLMs ------------------------

def fake_llm_perception_lens(input: LLMPerceptionLensInput) -> LLMPerceptionLensOutput:
    """Rule-based, deterministic transformation.

    Heuristics:
    - emotional_read driven by avg_stress and guardrail ratio.
    - risk_assessment contains "at risk of burnout" if stress high (>0.3) and ratio high (>0.7).
      else "stable" for low stress (<0.08), else "watchful".
    - suggested_focus nudges autonomy if guardrail heavy with moderate/low stress; otherwise balance.
    - supervisor_comment_prompt reflects supervisor_tone_hint.
    """
    g = int(input.guardrail_count)
    c = int(input.context_count)
    ratio = _guardrail_ratio(g, c)
    s = float(input.avg_stress)

    # Emotional read
    if s > 0.6 and ratio > 0.7:
        emotional_read = "tense and tightly constrained"
    elif s > 0.3 and ratio > 0.7:
        emotional_read = "under pressure and bound by protocol"
    elif s < 0.08 and ratio < 0.5:
        emotional_read = "calm and willing to exercise local judgment"
    else:
        emotional_read = "focused under routine load"

    # Risk assessment
    if s > 0.3 and ratio > 0.7:
        risk_assessment = "at risk of burnout"
    elif s < 0.08:
        risk_assessment = "stable"
    else:
        risk_assessment = "watchful"

    # Suggested focus
    # Nudge autonomy if guardrail-heavy or if stress is low and guardrails are moderate-heavy
    if (ratio > 0.7 and s >= 0.08) or (s < 0.08 and ratio >= 0.5):
        suggested_focus = "increase autonomy where safe"
    elif ratio < 0.3 and s > 0.3:
        suggested_focus = "lean on guardrails during high-pressure work"
    else:
        suggested_focus = "balance policy with context"

    # Supervisor prompt
    tone = input.supervisor_tone_hint
    if tone == "strict":
        supervisor_comment_prompt = "Hold steady on safety protocols; take a breath before escalating."
    elif tone == "steady":
        supervisor_comment_prompt = "Maintain pace; check assumptions before committing changes."
    else:
        supervisor_comment_prompt = "Good cadence—continue to validate with quick checks."

    return LLMPerceptionLensOutput(
        agent_name=input.agent_name,
        emotional_read=emotional_read,
        risk_assessment=risk_assessment,
        suggested_focus=suggested_focus,
        supervisor_comment_prompt=supervisor_comment_prompt,
        meta={
            "guardrail_ratio": ratio,
            "rules": "deterministic_fake_llm_v1",
        },
    )


def fake_llm_episode_lens(input: LLMEpisodeLensInput) -> LLMEpisodeLensOutput:
    """Deterministic episode-level lens.

    - episode_theme from first→last tension comparison with 0.05 epsilon.
    - key_risks/opportunities from agent summaries thresholds.
    - supervisor_script_seed mirrors the overall theme.
    """
    tensions = list(input.tension_trend)
    start = tensions[0] if tensions else 0.0
    end = tensions[-1] if tensions else 0.0
    delta = end - start
    eps = 0.05
    if delta > eps:
        episode_theme = "The episode runs hot; tension climbs overall."
        theme_tag = "rising"
    elif delta < -eps:
        episode_theme = "The episode eases off after an early edge."
        theme_tag = "falling"
    else:
        episode_theme = "The episode holds a steady tone."
        theme_tag = "flat"

    # Risks/opportunities
    risks: List[str] = []
    opps: List[str] = []
    for a in input.agent_summaries:
        ratio = float(a.get("guardrail_ratio", 0.0) or 0.0)
        s_end = float(a.get("stress_end", 0.0) or 0.0)
        role = str(a.get("role", ""))
        name = str(a.get("name", ""))
        if s_end > 0.3 and ratio > 0.7:
            risks.append(f"{name}: high stress within strict guardrails")
        if ratio < 0.3 and s_end < 0.3:
            opps.append(f"{name}: room to grant autonomy")
        if role == "qa" and s_end > 0.3:
            risks.append(f"{name}: QA pressure may increase incident scrutiny")

    if not risks:
        risks.append("general: watch for localized overloads on busy lines")
    if not opps:
        opps.append("general: encourage quick checks before escalation")

    # Supervisor seed
    if theme_tag == "rising":
        supervisor_script_seed = (
            "Tension is up. Slow the pace by half a beat and consult before major actions."
        )
    elif theme_tag == "falling":
        supervisor_script_seed = (
            "We’re cooling. Hold the gains and keep communication predictable."
        )
    else:
        supervisor_script_seed = (
            "Steady shift. Maintain rhythm and continue validating assumptions."
        )

    return LLMEpisodeLensOutput(
        episode_id=input.episode_id,
        episode_theme=episode_theme,
        key_risks=risks,
        key_opportunities=opps,
        supervisor_script_seed=supervisor_script_seed,
        meta={"rules": "deterministic_fake_llm_v1"},
    )
