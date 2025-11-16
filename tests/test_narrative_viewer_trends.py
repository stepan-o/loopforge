from __future__ import annotations

from loopforge.reporting import DaySummary, AgentDayStats
from loopforge.narrative_viewer import build_day_narrative


def _mk_stats(name: str, role: str, *, g: int, c: int, s: float) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=g, context_count=c, avg_stress=s)


def _mk_day_summary(day_index: int, tension: float, stats: dict[str, AgentDayStats]) -> DaySummary:
    return DaySummary(
        day_index=day_index,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=0,
    )


def test_day_outro_trend_variants():
    # Rising: prev 0.20 -> cur 0.26 (delta +0.06)
    prev = _mk_day_summary(0, 0.20, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.2)})
    cur = _mk_day_summary(1, 0.26, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.2)})
    dn_rise = build_day_narrative(cur, 1, previous_day_summary=prev)
    assert "tighter" in dn_rise.day_outro.lower() or "leftover static" in dn_rise.day_outro.lower()

    # Falling: prev 0.40 -> cur 0.30 (delta -0.10)
    prev2 = _mk_day_summary(0, 0.40, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.2)})
    cur2 = _mk_day_summary(1, 0.30, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.2)})
    dn_fall = build_day_narrative(cur2, 1, previous_day_summary=prev2)
    assert "winds down lighter" in dn_fall.day_outro.lower() or "exhales" in dn_fall.day_outro.lower()

    # Flat: prev 0.20 -> cur 0.22 (|delta| = 0.02)
    prev3 = _mk_day_summary(0, 0.20, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.2)})
    cur3 = _mk_day_summary(1, 0.22, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.2)})
    dn_flat = build_day_narrative(cur3, 1, previous_day_summary=prev3)
    assert "settles into its usual idle" in dn_flat.day_outro.lower()


def test_agent_closing_stress_bands():
    # Low (<0.08)
    ds_low = _mk_day_summary(0, 0.2, {"X": _mk_stats("X", "qa", g=0, c=1, s=0.05)})
    dn_low = build_day_narrative(ds_low, 0)
    assert dn_low.agent_beats[0].closing_line == "Ends the day calm, nothing sticking."

    # Mid (0.08–0.3)
    ds_mid = _mk_day_summary(0, 0.2, {"Y": _mk_stats("Y", "qa", g=0, c=1, s=0.10)})
    dn_mid = build_day_narrative(ds_mid, 0)
    assert dn_mid.agent_beats[0].closing_line == "Ends the day balanced, tension kept in check."

    # High (>0.3)
    ds_high = _mk_day_summary(0, 0.2, {"Z": _mk_stats("Z", "qa", g=0, c=1, s=0.31)})
    dn_high2 = build_day_narrative(ds_high, 0)
    assert dn_high2.agent_beats[0].closing_line == "Ends the day carrying some weight."


ess_role_optimizer = "always chasing efficiency"
ess_role_qa = "ever watchful for cracks in the system"
ess_role_maint = "hands always in the guts of the place"


def test_role_flavor_in_intro():
    stats = {
        "Delta": _mk_stats("Delta", "optimizer", g=2, c=3, s=0.12),
        "Nova": _mk_stats("Nova", "qa", g=1, c=4, s=0.20),
        "Sprocket": _mk_stats("Sprocket", "maintenance", g=3, c=2, s=0.35),
        "Ghost": _mk_stats("Ghost", "unknown", g=1, c=1, s=0.05),
    }
    ds = _mk_day_summary(0, 0.3, stats)
    dn = build_day_narrative(ds, 0)
    beats = {b.name: b for b in dn.agent_beats}
    assert ess_role_optimizer in beats["Delta"].intro
    assert ess_role_qa in beats["Nova"].intro
    assert ess_role_maint in beats["Sprocket"].intro
    # Unknown role should not get flavor
    assert " — " not in beats["Ghost"].intro
