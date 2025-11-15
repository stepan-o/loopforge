import json
from pathlib import Path
from types import SimpleNamespace

from loopforge.day_runner import run_one_day
from loopforge.reflection import filter_entries_for_day, run_daily_reflections_for_all_agents
from loopforge.logging_utils import JsonlReflectionLogger
from loopforge.types import ActionLogEntry


def test_filter_entries_for_day_basic():
    entries = [
        ActionLogEntry(step=0, agent_name="A", role="r", mode="guardrail", intent="", move_to=None, targets=[], riskiness=0.0, narrative="", raw_action={}, perception={}),
        ActionLogEntry(step=10, agent_name="A", role="r", mode="guardrail", intent="", move_to=None, targets=[], riskiness=0.0, narrative="", raw_action={}, perception={}),
        ActionLogEntry(step=50, agent_name="A", role="r", mode="context", intent="", move_to=None, targets=[], riskiness=0.0, narrative="", raw_action={}, perception={}),
    ]
    # steps_per_day = 50 → day 0: [0,50), day 1: [50,100)
    d0 = filter_entries_for_day(entries, day_index=0, steps_per_day=50)
    d1 = filter_entries_for_day(entries, day_index=1, steps_per_day=50)
    assert len(d0) == 2
    assert len(d1) == 1


def test_run_daily_reflections_for_all_agents_logs(tmp_path: Path):
    # Prepare fake entries all for agent X
    entries = [
        ActionLogEntry(step=i, agent_name="X", role="maintenance", mode="context" if i % 2 else "guardrail", intent="", move_to=None, targets=[], riskiness=0.0, narrative="", raw_action={}, perception={})
        for i in range(5)
    ]
    # Two agents: only X has entries
    agents = [SimpleNamespace(name="X", role="maintenance", traits={"guardrail_reliance": 0.5, "risk_aversion": 0.5}), SimpleNamespace(name="Y", role="qa", traits={})]

    log_path = tmp_path / "refl.jsonl"
    logger = JsonlReflectionLogger(log_path)

    from loopforge.reflection import run_daily_reflections_for_all_agents

    res = run_daily_reflections_for_all_agents(agents, entries, logger, day_index=0)

    # One reflection per agent, even if no entries (Y will be summarized as 0 steps)
    assert len(res) == 2

    # Logger should have 2 lines
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    # Check structure
    row = json.loads(lines[0])
    assert "agent_name" in row and "reflection" in row and "traits_after" in row


def test_run_one_day_reads_logs_and_runs_reflections(tmp_path: Path):
    # Pre-populate an action log with mixed entries for two agents
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
            "riskiness": 0.0,
            "narrative": "",
            "raw_action": {},
            "perception": {},
        },
        {
            "step": 10,
            "agent_name": "B",
            "role": "qa",
            "mode": "context",
            "intent": "inspect",
            "move_to": None,
            "targets": [],
            "riskiness": 0.0,
            "narrative": "",
            "raw_action": {},
            "perception": {},
        },
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # Dummy env with step() we don't validate; run_one_day shouldn't depend on it
    class DummyEnv:
        def __init__(self):
            self.count = 0
        def step(self):
            self.count += 1

    env = DummyEnv()
    agents = [SimpleNamespace(name="A", role="maintenance", traits={}), SimpleNamespace(name="B", role="qa", traits={})]

    from loopforge.day_runner import run_one_day
    from loopforge.logging_utils import JsonlReflectionLogger

    refl_log_path = tmp_path / "reflections.jsonl"
    reflections = run_one_day(
        env,
        agents,
        steps_per_day=50,
        day_index=0,
        reflection_logger=JsonlReflectionLogger(refl_log_path),
        action_log_path=actions_path,
    )

    assert reflections and len(reflections) == 2
    # Reflections log file should have entries
    refl_lines = refl_log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(refl_lines) == 2
