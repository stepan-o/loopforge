from __future__ import annotations

from loopforge.reporting import summarize_day, summarize_episode, DaySummary
from loopforge.types import ActionLogEntry, AgentReflection


def _mk_entry(step: int, name: str, role: str, mode: str, stress: float = 0.0):
    return ActionLogEntry(
        step=step,
        agent_name=name,
        role=role,
        mode=mode,  # "guardrail" | "context"
        intent="work" if mode == "guardrail" else "inspect",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        raw_action={},
        perception={
            "emotions": {"stress": stress, "curiosity": 0.5, "satisfaction": 0.5},
            "perception_mode": "accurate",
        },
    )


def test_summarize_day_basic():
    # Build a small set of entries for a single day (assume steps_per_day slicing done upstream)
    entries = [
        _mk_entry(0, "Sprocket", "maintenance", "guardrail", stress=0.3),
        _mk_entry(1, "Sprocket", "maintenance", "context", stress=0.4),
        _mk_entry(2, "Nova", "qa", "context", stress=0.6),
    ]

    ds = summarize_day(day_index=0, entries=entries, reflections_by_agent=None)

    assert isinstance(ds, DaySummary)
    assert ds.day_index == 0
    # Agent stats exist for both agents
    assert set(ds.agent_stats.keys()) == {"Sprocket", "Nova"}
    # Counts per agent
    sp = ds.agent_stats["Sprocket"]
    nv = ds.agent_stats["Nova"]
    assert sp.guardrail_count == 1 and sp.context_count == 1
    assert nv.guardrail_count == 0 and nv.context_count == 1
    # Tension must be > 0 due to non-zero stresses
    assert ds.tension_score > 0.0


def test_summarize_episode_aggregates():
    # Construct two day summaries by hand for one agent
    from loopforge.reporting import AgentDayStats

    day0 = DaySummary(
        day_index=0,
        perception_mode="accurate",
        tension_score=0.3,
        agent_stats={
            "Sprocket": AgentDayStats(name="Sprocket", role="maintenance", guardrail_count=2, context_count=1, avg_stress=0.25),
            "Nova": AgentDayStats(name="Nova", role="qa", guardrail_count=0, context_count=3, avg_stress=0.55),
        },
        total_incidents=0,
    )
    day1 = DaySummary(
        day_index=1,
        perception_mode="partial",
        tension_score=0.7,
        agent_stats={
            "Sprocket": AgentDayStats(name="Sprocket", role="maintenance", guardrail_count=3, context_count=0, avg_stress=0.6),
            "Nova": AgentDayStats(name="Nova", role="qa", guardrail_count=1, context_count=2, avg_stress=0.4),
        },
        total_incidents=1,
    )

    ep = summarize_episode([day0, day1])

    # Aggregates per agent
    sp = ep.agents["Sprocket"]
    nv = ep.agents["Nova"]
    assert sp.guardrail_total == 5 and sp.context_total == 1
    assert nv.guardrail_total == 1 and nv.context_total == 5
    # Stress arc captured
    assert sp.stress_start == 0.25 and sp.stress_end == 0.6
    assert nv.stress_start == 0.55 and nv.stress_end == 0.4
    # Tension trend length matches days
    assert ep.tension_trend == [0.3, 0.7]
