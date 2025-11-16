from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from loopforge.day_runner import run_episode


def test_run_episode_writes_indices_in_reflection_and_supervisor(tmp_path: Path):
    # Prepare a tiny action log with a couple of entries covering two agents
    actions_path = tmp_path / "actions.jsonl"
    rows = [
        {
            "step": 0,
            "agent_name": "A",
            "role": "maintenance",
            "mode": "guardrail",
            "intent": "work",
            "move_to": None,
            "targets": [],
            "riskiness": 0.2,
            "narrative": "",
            "raw_action": {},
            "perception": {},
        },
        {
            "step": 3,
            "agent_name": "B",
            "role": "qa",
            "mode": "context",
            "intent": "inspect",
            "move_to": None,
            "targets": [],
            "riskiness": 0.4,
            "narrative": "",
            "raw_action": {},
            "perception": {},
        },
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # Dummy env with no-op step
    class DummyEnv:
        def step(self):
            pass

    env = DummyEnv()
    agents = [SimpleNamespace(name="A", role="maintenance", traits={}), SimpleNamespace(name="B", role="qa", traits={})]

    reflection_log_path = tmp_path / "reflections.jsonl"
    supervisor_log_path = tmp_path / "supervisor.jsonl"

    run_episode(
        env=env,
        agents=agents,
        num_days=2,
        steps_per_day=3,
        persist_to_db=False,
        episode_index=7,
        action_log_path=actions_path,
        reflection_log_path=reflection_log_path,
        supervisor_log_path=supervisor_log_path,
    )

    # Check reflection log contains episode/day fields
    assert reflection_log_path.exists()
    refl_lines = [json.loads(l) for l in reflection_log_path.read_text(encoding="utf-8").strip().splitlines()]
    assert any(row.get("episode_index") == 7 for row in refl_lines)
    assert any(row.get("day_index") in {0, 1} for row in refl_lines)

    # Check supervisor log exists and contains episode_index
    assert supervisor_log_path.exists()
    sup_lines = [json.loads(l) for l in supervisor_log_path.read_text(encoding="utf-8").strip().splitlines()]
    assert sup_lines, "Supervisor log should have at least one message"
    assert any(row.get("episode_index") == 7 for row in sup_lines)
    assert any(row.get("day_index") in {0, 1} for row in sup_lines)
