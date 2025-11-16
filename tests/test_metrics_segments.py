from __future__ import annotations

import json
from pathlib import Path

from loopforge.metrics import read_action_logs, segment_by_episode, segment_by_day


essential = {
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
}


def test_segmenters_group_by_episode_and_day(tmp_path: Path):
    p = tmp_path / "actions.jsonl"
    rows = [
        dict(essential, step=0, episode_index=7, day_index=0),
        dict(essential, step=1, episode_index=7, day_index=1),
        dict(essential, step=2, episode_index=None, day_index=None),
        dict(essential, step=3, episode_index=8, day_index=0),
    ]
    p.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    actions = read_action_logs(p)

    ep = segment_by_episode(actions)
    # Expect keys: 7, 8, -1 (for None)
    assert set(ep.keys()) == {7, 8, -1}
    assert len(ep[7]) == 2  # steps 0 and 1 are episode 7

    dy = segment_by_day(actions)
    # Expect day buckets 0, 1, -1
    assert set(dy.keys()) == {0, 1, -1}
    assert len(dy[0]) >= 1
