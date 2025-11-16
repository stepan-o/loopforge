from __future__ import annotations

import json
from pathlib import Path

from loopforge.metrics import read_action_logs, compute_mode_distribution


essential_row = {
    "step": 0,
    "agent_name": "A",
    "role": "maintenance",
    "intent": "work",
    "move_to": None,
    "targets": [],
    "riskiness": 0.0,
    "narrative": "",
    "raw_action": {},
    "perception": {},
}


def test_compute_mode_distribution_counts_and_dist(tmp_path: Path):
    p = tmp_path / "actions.jsonl"
    rows = []
    # 3 guardrail, 2 context, 1 unknown
    for i in range(3):
        r = dict(essential_row)
        r["step"] = i
        r["mode"] = "guardrail"
        rows.append(r)
    for i in range(2):
        r = dict(essential_row)
        r["step"] = 10 + i
        r["mode"] = "context"
        rows.append(r)
    r = dict(essential_row)
    r["step"] = 20
    r["mode"] = "unknown"  # explicit unknown bucket
    rows.append(r)

    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    actions = read_action_logs(p)
    res = compute_mode_distribution(actions)

    counts = res["counts"]
    total = res["total"]
    dist = res["distribution"]

    assert total == 6
    assert counts.get("guardrail") == 3
    assert counts.get("context") == 2
    assert counts.get("unknown") == 1
    # distribution sums to ~1.0
    s = sum(dist.values())
    assert abs(s - 1.0) < 1e-9
