from __future__ import annotations

import json
from pathlib import Path

from loopforge.day_runner import compute_day_summary
from loopforge.reporting import summarize_day, DaySummary
from loopforge.types import ActionLogEntry, AgentReflection


def _mk_entry(step: int, name: str, role: str, mode: str, *, stress: float = 0.0, outcome: str | None = None):
    """Helper to build an ActionLogEntry with minimal perception snapshot."""
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
        outcome=outcome,
    )


def test_compute_day_summary_slices_by_step(tmp_path: Path):
    # Build a JSONL action log with 20 steps: 0..9 (day 0) and 10..19 (day 1)
    actions_path = tmp_path / "actions.jsonl"
    rows: list[dict] = []
    # Day 0 entries for A only
    for i in range(10):
        mode = "guardrail" if i % 2 == 0 else "context"
        row = _mk_entry(i, "A", "maintenance", mode, stress=0.2 + 0.01 * i).to_dict()
        rows.append(row)
    # Day 1 entries for B only
    for i in range(10, 20):
        mode = "context" if i % 2 == 0 else "guardrail"
        row = _mk_entry(i, "B", "qa", mode, stress=0.6 - 0.01 * (i - 10)).to_dict()
        rows.append(row)
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # Slice day 0
    ds0: DaySummary = compute_day_summary(
        day_index=0,
        action_log_path=actions_path,
        steps_per_day=10,
    )
    assert isinstance(ds0, DaySummary)
    assert ds0.day_index == 0
    # Only agent A should appear on day 0
    assert set(ds0.agent_stats.keys()) == {"A"}
    a0 = ds0.agent_stats["A"]
    assert a0.guardrail_count + a0.context_count == 10

    # Slice day 1
    ds1: DaySummary = compute_day_summary(
        day_index=1,
        action_log_path=actions_path,
        steps_per_day=10,
    )
    assert ds1.day_index == 1
    # Only agent B should appear on day 1
    assert set(ds1.agent_stats.keys()) == {"B"}
    b1 = ds1.agent_stats["B"]
    assert b1.guardrail_count + b1.context_count == 10


def test_summarize_day_uses_telemetry_not_reflections():
    # Two entries for one agent with stress and one incident
    entries = [
        _mk_entry(0, "Sprocket", "maintenance", "guardrail", stress=0.3),
        _mk_entry(1, "Sprocket", "maintenance", "context", stress=0.5, outcome="incident"),
    ]
    # Reflection contains misleading numeric text; it must not affect counts
    fake_reflection = AgentReflection(
        summary_of_day="Sprocket took 180 steps • guardrail=170 • context=10 • incidents=42.",
        self_assessment="",
        intended_changes="",
        tags={},
    )
    ds = summarize_day(day_index=0, entries=entries, reflections_by_agent={"Sprocket": fake_reflection})

    sp = ds.agent_stats["Sprocket"]
    # Counts must come from entries only
    assert sp.guardrail_count == 1
    assert sp.context_count == 1
    assert ds.total_incidents == 1
    # Average stress must be telemetry average
    assert abs(sp.avg_stress - ((0.3 + 0.5) / 2)) < 1e-6
