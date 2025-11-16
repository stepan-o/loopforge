from __future__ import annotations

import json
from pathlib import Path

from loopforge.metrics import read_action_logs, compute_incident_rate


def test_compute_incident_rate_basic(tmp_path: Path):
    p = tmp_path / "actions.jsonl"
    rows = [
        {
            "step": 0,
            "agent_name": "A",
            "role": "maintenance",
            "mode": "guardrail",
            "intent": "work",
            "move_to": None,
            "targets": [],
            "riskiness": 0.1,
            "narrative": "",
            "outcome": "incident",
            "raw_action": {},
            "perception": {},
        },
        {
            "step": 1,
            "agent_name": "B",
            "role": "qa",
            "mode": "context",
            "intent": "inspect",
            "move_to": None,
            "targets": [],
            "riskiness": 0.2,
            "narrative": "",
            "outcome": "no_incident",
            "raw_action": {},
            "perception": {},
        },
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    actions = read_action_logs(p)
    res = compute_incident_rate(actions)

    assert res["total_steps"] == 2
    assert res["incidents"] == 1
    assert abs(res["incident_rate"] - 0.5) < 1e-9
