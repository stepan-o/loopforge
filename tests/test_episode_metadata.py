from __future__ import annotations

import json
from pathlib import Path

from loopforge.types import ActionLogEntry, AgentReflection, ReflectionLogEntry
from loopforge.logging_utils import JsonlActionLogger, JsonlReflectionLogger


def test_action_log_entry_roundtrip_with_episode_day(tmp_path: Path):
    entry = ActionLogEntry(
        step=5,
        agent_name="R-99",
        role="maintenance",
        mode="guardrail",
        intent="inspect",
        move_to=None,
        targets=[],
        riskiness=0.1,
        narrative="n",
        outcome=None,
        raw_action={},
        perception={"name": "R-99"},
        episode_index=7,
        day_index=1,
    )
    data = entry.to_dict()
    assert data["episode_index"] == 7
    assert data["day_index"] == 1

    # Round-trip via from_dict
    rt = ActionLogEntry.from_dict(data)
    assert rt.episode_index == 7
    assert rt.day_index == 1

    # And writing via JSONL logger should include the fields
    log_path = tmp_path / "actions.jsonl"
    logger = JsonlActionLogger(log_path)
    logger.write_entry(entry)
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[0]
    parsed = json.loads(line)
    assert parsed["episode_index"] == 7
    assert parsed["day_index"] == 1


def test_reflection_log_entry_writes_episode_day(tmp_path: Path):
    refl = AgentReflection(summary_of_day="", self_assessment="", intended_changes="", tags={})
    # also set fields used by logger to mirror build path
    refl.perception_mode = "accurate"
    # Optional perceived intent left None

    log_path = tmp_path / "refl.jsonl"
    logger = JsonlReflectionLogger(log_path)
    entry = ReflectionLogEntry(
        agent_name="R-01",
        role="qa",
        day_index=0,
        reflection=refl,
        traits_after={"risk_aversion": 0.5},
        perception_mode=refl.perception_mode,
        supervisor_perceived_intent=None,
        episode_index=42,
    )

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.to_dict()) + "\n")

    line = log_path.read_text(encoding="utf-8").strip().splitlines()[0]
    data = json.loads(line)
    assert data.get("day_index") == 0
    assert data.get("episode_index") == 42
