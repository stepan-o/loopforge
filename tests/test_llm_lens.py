from __future__ import annotations

import json
from typing import Dict

from loopforge.reporting import DaySummary, AgentDayStats, EpisodeSummary
from loopforge.llm_lens import (
    LLMPerceptionLensInput,
    LLMPerceptionLensOutput,
    LLMEpisodeLensInput,
    LLMEpisodeLensOutput,
    build_llm_perception_lens_input,
    build_llm_episode_lens_input,
    fake_llm_perception_lens,
    fake_llm_episode_lens,
)


def _mk_day(idx: int, tension: float, stats: Dict[str, AgentDayStats]) -> DaySummary:
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=0,
    )


def _mk_stats(name: str, role: str, g: int, c: int, s: float) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=g, context_count=c, avg_stress=s)


def _mk_episode(tensions: list[float], agents_stats_by_day: list[dict[str, AgentDayStats]]) -> EpisodeSummary:
    days = [_mk_day(i, t, stats) for i, (t, stats) in enumerate(zip(tensions, agents_stats_by_day))]
    from loopforge.reporting import summarize_episode
    return summarize_episode(days)


def test_build_llm_perception_lens_input_basic():
    stats = {"Delta": _mk_stats("Delta", "optimizer", g=7, c=3, s=0.62)}
    ds = _mk_day(0, tension=0.65, stats=stats)

    lens_in = build_llm_perception_lens_input(ds, "Delta")
    assert lens_in is not None
    assert lens_in.agent_name == "Delta"
    assert lens_in.role == "optimizer"
    assert lens_in.avg_stress == 0.62
    assert lens_in.guardrail_count == 7 and lens_in.context_count == 3
    assert lens_in.supervisor_tone_hint == "strict"  # high tension → strict


def test_build_llm_episode_lens_input_copies_trend_and_agents():
    day0 = {"A": _mk_stats("A", "qa", g=5, c=5, s=0.20)}
    day1 = {"A": _mk_stats("A", "qa", g=6, c=4, s=0.30)}
    ep = _mk_episode([0.1, 0.4, 0.5], [day0, day1, day1])

    lens_ep = build_llm_episode_lens_input(ep, characters={})
    assert lens_ep.tension_trend == [0.1, 0.4, 0.5]
    assert isinstance(lens_ep.agent_summaries, list) and lens_ep.agent_summaries
    a0 = lens_ep.agent_summaries[0]
    for key in ("name", "role", "stress_start", "stress_end", "guardrail_ratio"):
        assert key in a0


def test_fake_llm_perception_lens_rules_and_determinism():
    # High stress + high guardrail → burnout risk
    base_in = LLMPerceptionLensInput(
        agent_name="Nova",
        role="qa",
        day_index=0,
        perception_mode="accurate",
        avg_stress=0.5,
        guardrail_count=8,
        context_count=2,
        tension=0.6,
        world_summary="",
        recent_events=[],
        supervisor_tone_hint="steady",
    )
    out1 = fake_llm_perception_lens(base_in)
    out2 = fake_llm_perception_lens(base_in)
    assert out1.risk_assessment == "at risk of burnout"
    assert out1 == out2  # dataclass equality + determinism

    # Low stress + moderate-high guardrail → nudge autonomy
    base_in2 = LLMPerceptionLensInput(
        agent_name="Delta",
        role="optimizer",
        day_index=0,
        perception_mode="accurate",
        avg_stress=0.05,
        guardrail_count=5,
        context_count=5,
        tension=0.2,
        world_summary="",
        recent_events=[],
        supervisor_tone_hint="gentle",
    )
    out3 = fake_llm_perception_lens(base_in2)
    assert out3.risk_assessment == "stable"
    assert "increase autonomy" in out3.suggested_focus


def test_fake_llm_episode_lens_trend_and_text():
    # Rising tension
    ep_in = LLMEpisodeLensInput(
        episode_id="ep-x",
        day_count=3,
        tension_trend=[0.1, 0.4, 0.5],
        agent_summaries=[{"name": "A", "role": "qa", "stress_end": 0.4, "guardrail_ratio": 0.8}],
    )
    ep_out = fake_llm_episode_lens(ep_in)
    assert "runs hot" in ep_out.episode_theme
    assert any("risk" in r or "high stress" in r for r in ep_out.key_risks)

    # Falling tension
    ep_in_fall = LLMEpisodeLensInput(
        episode_id="ep-y",
        day_count=3,
        tension_trend=[0.6, 0.4, 0.2],
        agent_summaries=[],
    )
    ep_out_fall = fake_llm_episode_lens(ep_in_fall)
    assert "eases off" in ep_out_fall.episode_theme

    # Determinism
    ep_out2 = fake_llm_episode_lens(ep_in)
    assert ep_out.episode_theme == ep_out2.episode_theme
    assert ep_out.key_risks == ep_out2.key_risks
    assert ep_out.key_opportunities == ep_out2.key_opportunities
