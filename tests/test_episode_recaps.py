from __future__ import annotations

from loopforge.reporting import EpisodeSummary, DaySummary, AgentEpisodeStats
from loopforge.episode_recaps import build_episode_recap


def _mk_day(idx: int, tension: float) -> DaySummary:
    from loopforge.reporting import AgentDayStats
    return DaySummary(day_index=idx, perception_mode="accurate", tension_score=tension, agent_stats={}, total_incidents=0)


def _mk_ep(ten: list[float], agents: dict[str, AgentEpisodeStats]) -> EpisodeSummary:
    days = [_mk_day(i, t) for i, t in enumerate(ten)]
    return EpisodeSummary(days=days, agents=agents, tension_trend=ten)


def _agent(name: str, role: str, g: int, c: int, s0: float | None, s1: float | None) -> AgentEpisodeStats:
    return AgentEpisodeStats(
        name=name,
        role=role,
        guardrail_total=g,
        context_total=c,
        trait_deltas={},
        stress_start=s0,
        stress_end=s1,
        representative_reflection=None,
        visual="",
        vibe="",
        tagline="",
    )


def test_tension_trend_intro_and_closing_rising_falling_flat():
    # Rising trend
    ep_rise = _mk_ep([0.1, 0.4, 0.7], {"A": _agent("A", "qa", 1, 2, 0.1, 0.2)})
    recap_rise = build_episode_recap(ep_rise, ep_rise.days, characters={})
    assert recap_rise.intro == "The episode runs hot; tension climbs from start to finish."
    assert recap_rise.closing == "The shift closes under a lingering edge."

    # Falling trend
    ep_fall = _mk_ep([0.7, 0.5, 0.2], {"A": _agent("A", "qa", 1, 2, 0.3, 0.1)})
    recap_fall = build_episode_recap(ep_fall, ep_fall.days, characters={})
    assert recap_fall.intro == "The episode eases off; the early edge softens over time."
    assert recap_fall.closing == "The shift winds down quietly, nothing pressing."

    # Flat trend
    ep_flat = _mk_ep([0.25, 0.26, 0.24], {"A": _agent("A", "qa", 1, 2, 0.2, 0.2)})
    recap_flat = build_episode_recap(ep_flat, ep_flat.days, characters={})
    assert recap_flat.intro == "The episode holds steady with no major shifts in tension."
    # ending 0.24 -> medium/low boundary (<0.3 → low)
    assert recap_flat.closing == "The shift winds down quietly, nothing pressing."


def test_per_agent_blurbs_arc_and_guardrail_and_role_flavor():
    # Guardrail-only for B should include the exact phrase
    agents = {
        "A": _agent("A", "maintenance", g=2, c=8, s0=0.05, s1=0.35),  # low -> high (tightened)
        "B": _agent("B", "qa", g=10, c=0, s0=0.40, s1=0.10),         # high -> low (unwound), guardrail-only
    }
    ep = _mk_ep([0.2, 0.4], agents)

    # character metadata to add flavor for role by name
    characters = {
        "A": {"vibe": "hands always in the guts of the place"},
        "B": {"vibe": "ever watchful for cracks in the system"},
    }

    recap = build_episode_recap(ep, ep.days, characters=characters)

    a_txt = recap.per_agent_blurbs["A"]
    assert "low stress" in a_txt and "high" in a_txt  # bands
    assert "tightened over the episode" in a_txt
    assert "hands always in the guts of the place" in a_txt

    b_txt = recap.per_agent_blurbs["B"]
    assert "high stress" in b_txt and "low" in b_txt
    assert "gradually unwound" in b_txt
    assert "stayed strictly within guardrails" in b_txt
    assert "ever watchful for cracks in the system" in b_txt


def test_determinism_same_inputs_same_output():
    agents = {"X": _agent("X", "qa", g=3, c=1, s0=0.10, s1=0.10)}
    ep = _mk_ep([0.3, 0.3], agents)
    chars = {"X": {"vibe": "ever watchful for cracks in the system"}}

    r1 = build_episode_recap(ep, ep.days, characters=chars)
    r2 = build_episode_recap(ep, ep.days, characters=chars)

    assert r1.intro == r2.intro
    assert r1.closing == r2.closing
    assert r1.per_agent_blurbs == r2.per_agent_blurbs
