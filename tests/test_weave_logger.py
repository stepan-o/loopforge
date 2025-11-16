from __future__ import annotations

import json
from pathlib import Path

from loopforge.logging_utils import JsonlWeaveLogger
from loopforge.types import EpisodeTensionSnapshot


def test_jsonl_weave_logger_writes_snapshot(tmp_path: Path):
    path = tmp_path / "weave.jsonl"
    logger = JsonlWeaveLogger(path)

    snap = EpisodeTensionSnapshot(
        episode_index=7,
        num_days=2,
        num_actions=10,
        num_reflections=4,
        incident_rate=0.1,
        belief_rate=0.0,
        guardrail_rate=0.4,
        context_rate=0.6,
        punitive_rate=0.0,
        supportive_rate=0.8,
        apathetic_rate=0.0,
        avg_stress=None,
        avg_satisfaction=None,
        tension_index=0.2,
        notes="stable",
    )

    logger.write_snapshot(snap)

    assert path.exists()
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["episode_index"] == 7
    assert data["num_days"] == 2
    assert isinstance(data["incident_rate"], float)
