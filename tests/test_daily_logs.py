from __future__ import annotations

from loopforge.reporting import DaySummary, AgentDayStats
from loopforge.daily_logs import build_daily_log, DailyLog


def _mk_stats(name: str, role: str, g: int, c: int, s: float) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=g, context_count=c, avg_stress=s)


def _mk_day(idx: int, tension: float, stats: dict[str, AgentDayStats]) -> DaySummary:
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=0,
    )


# ---------------- Intro tests ----------------

def test_intro_rising_falling_flat_and_day0():
    # Day 0 → flat intro regardless
    ds0 = _mk_day(0, 0.2, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    log0: DailyLog = build_daily_log(ds0, day_index=0, previous_day_summary=None)
    assert log0.intro == "The floor holds steady with no major shift at the start."

    # Rising: prev 0.20 → cur 0.28 (+0.08)
    prev = _mk_day(0, 0.20, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    cur = _mk_day(1, 0.28, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    log_rise = build_daily_log(cur, day_index=1, previous_day_summary=prev)
    assert log_rise.intro == "The floor starts tight and the early pulse runs hot."

    # Falling: prev 0.40 → cur 0.30 (-0.10)
    prev2 = _mk_day(0, 0.40, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    cur2 = _mk_day(1, 0.30, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    log_fall = build_daily_log(cur2, day_index=1, previous_day_summary=prev2)
    assert log_fall.intro == "The floor begins calm and keeps easing off."

    # Flat: prev 0.20 → cur 0.22 (|Δ|=0.02)
    prev3 = _mk_day(0, 0.20, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    cur3 = _mk_day(1, 0.22, {"A": _mk_stats("A", "qa", 1, 1, 0.1)})
    log_flat = build_daily_log(cur3, day_index=1, previous_day_summary=prev3)
    assert log_flat.intro == "The floor holds steady with no major shift at the start."


# ---------------- Agent beats ----------------

ess_role_optimizer = "always chasing efficiency"
ess_role_qa = "ever watchful for cracks in the system"
ess_role_maint = "hands always in the guts of the place"

def test_agent_beats_bands_flavor_guardrail_and_determinism():
    stats = {
        "Delta": _mk_stats("Delta", "optimizer", g=5, c=0, s=0.12),  # role flavor + guardrail-only
        "Nova": _mk_stats("Nova", "qa", g=0, c=4, s=0.05),           # context leaning + low stress
        "Sprocket": _mk_stats("Sprocket", "maintenance", g=2, c=2, s=0.32),  # high stress
    }
    ds = _mk_day(0, 0.3, stats)
    log1 = build_daily_log(ds, 0)
    log2 = build_daily_log(ds, 0)

    # Determinism: same inputs → identical structure
    assert log1.agent_beats == log2.agent_beats

    # Check per-agent lines presence
    delta_lines = " ".join(log1.agent_beats["Delta"]).lower()
    assert ess_role_optimizer in delta_lines
    assert "leans heavily on protocol" in delta_lines

    nova_lines = " ".join(log1.agent_beats["Nova"]).lower()
    assert ess_role_qa in nova_lines
    assert "acts on local judgment" in nova_lines
    # Low stress should mention relaxed/starts relaxed
    assert ("starts relaxed" in nova_lines) or ("relaxed and light" in nova_lines)

    sprocket_lines = " ".join(log1.agent_beats["Sprocket"]).lower()
    assert ess_role_maint in sprocket_lines
    assert ("wound a little tight" in sprocket_lines) or ("carrying some weight" in sprocket_lines)


# ---------------- General beats ----------------

def test_general_beats_supervisor_and_skew_and_drift():
    day_prev = _mk_day(0, 0.2, {
        "A": _mk_stats("A", "qa", g=1, c=4, s=0.10),
        "B": _mk_stats("B", "optimizer", g=1, c=4, s=0.10),
    })
    # Higher tension, protocol skew, higher stress
    day_cur = _mk_day(1, 0.65, {
        "A": _mk_stats("A", "qa", g=8, c=2, s=0.25),
        "B": _mk_stats("B", "optimizer", g=9, c=1, s=0.35),
    })

    log_cur = build_daily_log(day_cur, 1, previous_day_summary=day_prev)

    gen = " ".join(log_cur.general_beats)
    # Supervisor presence via high tension
    assert "Supervisor checked in often." in log_cur.general_beats
    # Protocol skew
    assert any("skewed toward protocol" in line for line in log_cur.general_beats)
    # Stress drift up
    assert any("tightened a notch" in line for line in log_cur.general_beats)


# ---------------- Closing line ----------------

def test_closing_by_tension_band():
    # Low
    ds_low = _mk_day(0, 0.05, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.02)})
    log_low = build_daily_log(ds_low, 0)
    assert log_low.closing == "The floor winds down quietly."

    # Mid
    ds_mid = _mk_day(0, 0.20, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.10)})
    log_mid = build_daily_log(ds_mid, 0)
    assert log_mid.closing == "The day ends balanced and steady."

    # High
    ds_high = _mk_day(0, 0.65, {"A": _mk_stats("A", "qa", g=1, c=1, s=0.31)})
    log_high = build_daily_log(ds_high, 0)
    assert log_high.closing == "The day closes with a lingering edge."


# ---------------- Determinism ----------------

def test_determinism_same_day_same_log():
    ds = _mk_day(2, 0.44, {
        "Sprocket": _mk_stats("Sprocket", "maintenance", g=3, c=2, s=0.35),
        "Nova": _mk_stats("Nova", "qa", g=1, c=4, s=0.25),
    })
    prev = _mk_day(1, 0.40, {
        "Sprocket": _mk_stats("Sprocket", "maintenance", g=1, c=4, s=0.10),
        "Nova": _mk_stats("Nova", "qa", g=2, c=3, s=0.35),
    })

    log_a = build_daily_log(ds, 2, previous_day_summary=prev)
    log_b = build_daily_log(ds, 2, previous_day_summary=prev)

    assert log_a.intro == log_b.intro
    assert log_a.agent_beats == log_b.agent_beats
    assert log_a.general_beats == log_b.general_beats
    assert log_a.closing == log_b.closing
