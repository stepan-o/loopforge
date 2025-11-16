from __future__ import annotations

from loopforge.reporting import DaySummary, AgentDayStats
from loopforge.narrative_viewer import build_day_narrative


def _mk_stats(name: str, role: str, *, g: int, c: int, s: float) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=g, context_count=c, avg_stress=s)


def _mk_day_summary(tension: float, stats: dict[str, AgentDayStats]) -> DaySummary:
    return DaySummary(day_index=0, perception_mode="accurate", tension_score=tension, agent_stats=stats, total_incidents=0)


def test_build_day_narrative_smoke():
    stats = {
        "Sprocket": _mk_stats("Sprocket", "maintenance", g=3, c=2, s=0.35),
        "Nova": _mk_stats("Nova", "qa", g=1, c=4, s=0.25),
        "Delta": _mk_stats("Delta", "optimizer", g=5, c=0, s=0.15),
    }
    ds = _mk_day_summary(0.44, stats)

    dn = build_day_narrative(ds, 0)

    assert dn.day_index == 0
    assert isinstance(dn.day_intro, str) and dn.day_intro
    assert len(dn.agent_beats) == len(stats)

    for beat in dn.agent_beats:
        assert beat.intro and beat.perception_line and beat.actions_line and beat.closing_line


def test_tension_band_behavior():
    # Very calm
    ds_calm = _mk_day_summary(0.05, {
        "A": _mk_stats("A", "maintenance", g=1, c=0, s=0.05),
    })
    dn_calm = build_day_narrative(ds_calm, 0)
    assert "quiet" in dn_calm.day_intro.lower()

    # High pressure
    ds_high = _mk_day_summary(0.7, {
        "A": _mk_stats("A", "qa", g=0, c=2, s=0.7),
    })
    dn_high = build_day_narrative(ds_high, 0)
    intro = dn_high.day_intro.lower()
    assert ("pressure" in intro) or ("high" in intro)


def test_guardrail_heavy_wording():
    stats = {
        "Rigel": _mk_stats("Rigel", "maintenance", g=10, c=0, s=0.2),
    }
    ds = _mk_day_summary(0.3, stats)
    dn = build_day_narrative(ds, 0)
    beat = dn.agent_beats[0]
    text = (beat.actions_line + " " + beat.perception_line).lower()
    # Ensure rule/manual/policy leaning appears
    assert ("manual" in text) or ("rule" in text) or ("policy" in text)
