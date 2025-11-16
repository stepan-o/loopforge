from __future__ import annotations

import json
from typing import List

from loopforge.weave import (
    compute_episode_tension_snapshot,
    compute_all_episode_snapshots,
)
from loopforge.types import ActionLogEntry, AgentReflection, ReflectionLogEntry


def _action(step: int, name: str, mode: str, outcome: str | None, episode_index: int, day_index: int) -> ActionLogEntry:
    return ActionLogEntry(
        step=step,
        agent_name=name,
        role="maintenance",
        mode=mode,  # "guardrail" | "context"
        intent="work",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        outcome=outcome,
        raw_action={},
        perception={"perception_mode": "accurate"},
        episode_index=episode_index,
        day_index=day_index,
    )


def _reflection(name: str, perceived_intent: str | None, pmode: str, episode_index: int, day_index: int) -> ReflectionLogEntry:
    r = AgentReflection(summary_of_day="", self_assessment="", intended_changes="", tags={})
    r.perception_mode = pmode
    r.supervisor_perceived_intent = perceived_intent
    return ReflectionLogEntry(
        agent_name=name,
        role="maintenance",
        day_index=day_index,
        reflection=r,
        traits_after={"risk_aversion": 0.5},
        perception_mode=pmode,
        supervisor_perceived_intent=perceived_intent,
        episode_index=episode_index,
    )


def test_low_tension_snapshot():
    # Episode 3: low tension — no incidents, mostly context, supportive supervisor, accurate perception
    actions: List[ActionLogEntry] = [
        _action(0, "A", "context", None, episode_index=3, day_index=0),
        _action(1, "A", "context", None, episode_index=3, day_index=0),
        _action(2, "B", "guardrail", None, episode_index=3, day_index=0),
    ]
    reflections: List[ReflectionLogEntry] = [
        _reflection("A", perceived_intent="supportive", pmode="accurate", episode_index=3, day_index=0),
        _reflection("B", perceived_intent="supportive", pmode="accurate", episode_index=3, day_index=0),
    ]

    snap = compute_episode_tension_snapshot(3, actions, reflections)

    assert snap.episode_index == 3
    assert snap.num_actions == 3
    assert snap.num_reflections == 2
    assert 0.0 <= snap.incident_rate <= 0.01  # effectively zero
    assert 0.0 <= snap.belief_rate <= 0.01
    assert snap.context_rate >= snap.guardrail_rate
    assert snap.supportive_rate >= 0.5
    assert 0.0 <= snap.tension_index <= 0.5
    assert isinstance(snap.notes, str)


def test_high_tension_snapshot():
    # Episode 5: high tension — many incidents, guardrail-heavy, punitive supervisor, some spin/partial
    actions = [
        _action(0, "A", "guardrail", "incident", episode_index=5, day_index=0),
        _action(1, "A", "guardrail", "incident", episode_index=5, day_index=0),
        _action(2, "B", "guardrail", None, episode_index=5, day_index=1),
    ]
    # reflections indicate punitive and non-accurate modes
    reflections = [
        _reflection("A", perceived_intent="punitive", pmode="spin", episode_index=5, day_index=0),
        _reflection("B", perceived_intent="punitive", pmode="partial", episode_index=5, day_index=1),
    ]

    snap = compute_episode_tension_snapshot(5, actions, reflections)

    assert snap.episode_index == 5
    assert snap.num_days >= 1
    assert snap.incident_rate >= 0.5
    assert snap.guardrail_rate >= 0.66
    assert snap.punitive_rate >= 0.5
    assert snap.belief_rate > 0.0
    assert 0.3 <= snap.tension_index <= 1.0
    assert "High tension" in snap.notes or "tension" in snap.notes.lower()


def test_compute_all_episode_snapshots_sorts_by_episode():
    actions = [
        _action(0, "A", "context", None, episode_index=5, day_index=0),
        _action(0, "B", "guardrail", None, episode_index=3, day_index=0),
    ]
    reflections = [
        _reflection("A", perceived_intent="supportive", pmode="accurate", episode_index=5, day_index=0),
        _reflection("B", perceived_intent="apathetic", pmode="accurate", episode_index=3, day_index=0),
    ]

    snaps = compute_all_episode_snapshots(actions, reflections)
    assert [s.episode_index for s in snaps] == [3, 5]
