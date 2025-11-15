import json
import importlib
from pathlib import Path
from types import SimpleNamespace

from loopforge.types import ActionLogEntry
from loopforge.logging_utils import JsonlReflectionLogger


def test_reflection_carries_perception_mode_and_logged(tmp_path, monkeypatch):
    # Ensure environment variable drives the mode
    monkeypatch.setenv("PERCEPTION_MODE", "partial")

    # Reload reflection module if needed (get_perception_mode reads env at call time)
    import loopforge.reflection as reflection
    importlib.reload(reflection)

    entries = [
        ActionLogEntry(
            step=0,
            agent_name="X",
            role="maintenance",
            mode="guardrail",
            intent="",
            move_to=None,
            targets=[],
            riskiness=0.0,
            narrative="",
            raw_action={},
            perception={},
        )
    ]
    agents = [SimpleNamespace(name="X", role="maintenance", traits={})]

    log_path = tmp_path / "reflections.jsonl"
    logger = JsonlReflectionLogger(log_path)

    res = reflection.run_daily_reflections_for_all_agents(
        agents=agents,
        entries=entries,
        logger=logger,
        day_index=0,
    )

    assert res and res[0].perception_mode == "partial"

    # Check log line contains perception_mode
    line = log_path.read_text(encoding="utf-8").strip().splitlines()[0]
    data = json.loads(line)
    assert data.get("perception_mode") == "partial"
    assert data["reflection"].get("perception_mode") == "partial"
