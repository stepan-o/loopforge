from __future__ import annotations

import json
from pathlib import Path

from loopforge.metrics import read_action_logs, read_reflection_logs, compute_belief_vs_truth_drift


def test_compute_belief_vs_truth_drift_from_logs(tmp_path: Path):
    # Actions: one accurate, one spin
    actions_path = tmp_path / "actions.jsonl"
    a_rows = [
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
            "raw_action": {},
            "perception": {"name": "A", "perception_mode": "accurate"},
        },
        {
            "step": 1,
            "agent_name": "A",
            "role": "maintenance",
            "mode": "context",
            "intent": "inspect",
            "move_to": None,
            "targets": [],
            "riskiness": 0.2,
            "narrative": "",
            "raw_action": {},
            "perception": {"name": "A", "perception_mode": "spin"},
        },
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in a_rows) + "\n", encoding="utf-8")

    # Reflections: one accurate, one partial
    refl_path = tmp_path / "reflections.jsonl"
    r_rows = [
        {
            "agent_name": "A",
            "role": "maintenance",
            "day_index": 0,
            "reflection": {
                "summary_of_day": "",
                "self_assessment": "",
                "intended_changes": "",
                "tags": {},
                "perception_mode": "accurate",
                "supervisor_perceived_intent": None,
            },
            "traits_after": {"risk_aversion": 0.5},
            "perception_mode": "accurate",
            "supervisor_perceived_intent": None,
            "episode_index": 0,
        },
        {
            "agent_name": "A",
            "role": "maintenance",
            "day_index": 1,
            "reflection": {
                "summary_of_day": "",
                "self_assessment": "",
                "intended_changes": "",
                "tags": {},
                "perception_mode": "partial",
                "supervisor_perceived_intent": None,
            },
            "traits_after": {"risk_aversion": 0.5},
            "perception_mode": "partial",
            "supervisor_perceived_intent": None,
            "episode_index": 0,
        },
    ]
    refl_path.write_text("\n".join(json.dumps(r) for r in r_rows) + "\n", encoding="utf-8")

    actions = read_action_logs(actions_path)
    reflections = read_reflection_logs(refl_path)

    res = compute_belief_vs_truth_drift(actions, reflections)
    # total events = 2 actions + 2 reflections = 4
    # belief events: 1 action (spin) + 1 reflection (partial) = 2
    assert res["total_events"] == 4
    assert res["belief_events"] == 2
    assert abs(res["belief_rate"] - 0.5) < 1e-9
