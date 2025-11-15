import json
import os
from pathlib import Path
from types import SimpleNamespace

from loopforge.day_runner import run_one_day_with_supervisor


def test_run_one_day_with_supervisor_writes_log_and_returns_messages(tmp_path: Path, monkeypatch):
    # Prepare an action log with entries that will yield a non-neutral tone.
    # We want majority context with incidents to trigger regretted_risk → tighten_guardrails.
    actions_path = tmp_path / "actions.jsonl"
    rows = [
        {
            "step": 0,
            "agent_name": "A",
            "role": "maintenance",
            "mode": "context",
            "intent": "work",
            "move_to": None,
            "targets": [],
            "riskiness": 0.7,
            "narrative": "",
            "outcome": "incident",
            "raw_action": {},
            "perception": {},
        },
        {
            "step": 10,
            "agent_name": "A",
            "role": "maintenance",
            "mode": "context",
            "intent": "inspect",
            "move_to": None,
            "targets": [],
            "riskiness": 0.4,
            "narrative": "",
            "outcome": "incident",
            "raw_action": {},
            "perception": {},
        },
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    # Dummy env with no-op step and mailbox
    class DummyEnv:
        def __init__(self):
            self.count = 0
        def step(self):
            self.count += 1

    env = DummyEnv()
    agents = [SimpleNamespace(name="A", role="maintenance", traits={})]

    sup_log_path = tmp_path / "supervisor.jsonl"

    messages = run_one_day_with_supervisor(
        env=env,
        agents=agents,
        steps_per_day=50,
        day_index=0,
        action_log_path=actions_path,
        supervisor_log_path=sup_log_path,
    )

    # Should return at least one message
    assert messages and messages[0].body
    # Log file created with one line per message
    assert sup_log_path.exists()
    lines = sup_log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    data = json.loads(lines[0])
    assert data["agent_name"] == "A"
    assert data["intent"] in {"tighten_guardrails", "encourage_context", "neutral_update"}
    assert isinstance(data["body"], str) and data["body"].strip()


def test_run_one_day_with_supervisor_env_var_overrides_path(tmp_path: Path, monkeypatch):
    # Prepare minimal action log for a neutral message
    actions_path = tmp_path / "actions.jsonl"
    row = {
        "step": 0,
        "agent_name": "B",
        "role": "qa",
        "mode": "guardrail",
        "intent": "work",
        "move_to": None,
        "targets": [],
        "riskiness": 0.0,
        "narrative": "",
        "raw_action": {},
        "perception": {},
    }
    actions_path.write_text(json.dumps(row) + "\n", encoding="utf-8")

    class DummyEnv:
        def step(self):
            pass

    env = DummyEnv()
    agents = [SimpleNamespace(name="B", role="qa", traits={})]

    # Set env var to override supervisor log path
    env_path = tmp_path / "env_override_supervisor.jsonl"
    monkeypatch.setenv("SUPERVISOR_LOG_PATH", str(env_path))

    fallback_path = tmp_path / "should_not_be_used.jsonl"
    run_one_day_with_supervisor(
        env=env,
        agents=agents,
        steps_per_day=50,
        day_index=0,
        action_log_path=actions_path,
        supervisor_log_path=fallback_path,
    )

    assert env_path.exists()
    # Ensure fallback was not used
    assert not fallback_path.exists()
