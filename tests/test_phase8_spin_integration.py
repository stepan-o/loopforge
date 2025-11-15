import json
from pathlib import Path
from types import SimpleNamespace
import importlib

from loopforge.day_runner import run_one_day_with_supervisor
from loopforge.logging_utils import JsonlReflectionLogger


def test_integration_spin_mode_reflection_log_contains_mode(tmp_path, monkeypatch):
    # Set spin mode
    monkeypatch.setenv("PERCEPTION_MODE", "spin")

    # Prepare minimal action log to produce entries for an agent
    actions_path = tmp_path / "actions.jsonl"
    rows = [
        {
            "step": 0,
            "agent_name": "S",
            "role": "maintenance",
            "mode": "guardrail",
            "intent": "work",
            "move_to": None,
            "targets": [],
            "riskiness": 0.1,
            "narrative": "",
            "raw_action": {},
            "perception": {},
        }
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    class DummyEnv:
        def step(self):
            pass

    env = DummyEnv()
    agents = [SimpleNamespace(name="S", role="maintenance", traits={})]

    reflection_path = tmp_path / "reflections.jsonl"

    # Run orchestrator; we pass reflection_log_path so reflections are written
    run_one_day_with_supervisor(
        env=env,
        agents=agents,
        steps_per_day=50,
        day_index=0,
        action_log_path=actions_path,
        reflection_log_path=reflection_path,
    )

    # Verify reflection log contains perception_mode == spin
    assert reflection_path.exists()
    lines = [json.loads(line) for line in reflection_path.read_text(encoding="utf-8").strip().splitlines() if line.strip()]
    assert lines, "No reflection lines written"
    assert any(row.get("perception_mode") == "spin" for row in lines)
    assert any(row.get("reflection", {}).get("perception_mode") == "spin" for row in lines)
