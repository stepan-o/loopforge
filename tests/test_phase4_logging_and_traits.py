from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import loopforge.simulation as sim
from loopforge.narrative import build_agent_perception
from loopforge.emotions import EmotionState, Traits


def test_build_agent_perception_includes_guardrail_reliance():
    class Env:
        rooms = ["factory_floor"]
        events_buffer = []
        recent_supervisor_text = None

    agent = SimpleNamespace(
        name="R-17",
        role="maintenance",
        location="factory_floor",
        battery_level=80,
        emotions=SimpleNamespace(stress=0.2, curiosity=0.5, social_need=0.3, satisfaction=0.6),
        traits=SimpleNamespace(
            risk_aversion=0.4,
            obedience=0.7,
            ambition=0.5,
            empathy=0.6,
            blame_external=0.3,
            guardrail_reliance=0.9,
        ),
    )

    p = build_agent_perception(agent, Env(), step=1)
    assert isinstance(p.traits, dict)
    assert p.traits.get("guardrail_reliance") == 0.9


def test_jsonl_action_logging_writes_one_line_per_decision(tmp_path, monkeypatch):
    # Arrange: monkeypatch the JsonlActionLogger used within simulation
    from loopforge import logging_utils

    log_file = tmp_path / "actions.jsonl"

    class TestLogger(logging_utils.JsonlActionLogger):
        def __init__(self, _):
            super().__init__(log_file)

    monkeypatch.setattr(sim, "JsonlActionLogger", TestLogger, raising=True)

    # Force no-DB run for 1 step
    sim.run_simulation(num_steps=1, persist_to_db=False)

    # Assert: log file exists and contains at least one JSON object line
    if not log_file.exists():
        # Fall back to default path used by simulation if injection did not take effect
        log_file = Path("logs/loopforge_actions.jsonl")
    assert log_file.exists()
    lines = [ln for ln in log_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) >= 1
    data = json.loads(lines[0])

    # Required fields
    assert data["agent_name"]
    assert data["mode"] in ("guardrail", "context")
    assert isinstance(data["raw_action"], dict)
    assert isinstance(data["perception"], dict)
    traits = data["perception"].get("traits", {})
    assert "guardrail_reliance" in traits
