import os
from types import SimpleNamespace

import importlib


def _make_agent():
    return SimpleNamespace(
        name="R-1",
        role="maintenance",
        location="A",
        battery_level=100,
        emotions=SimpleNamespace(stress=0.4, curiosity=0.1, social_need=0.2, satisfaction=0.6),
        traits={"guardrail_reliance": 0.5},
    )


def _make_env(local_events=None, recent_supervisor_text=None):
    class Env:
        def __init__(self):
            self.rooms = ["A", "B", "C"]
            self.recent_supervisor_text = recent_supervisor_text

        def get_local_events_for_agent(self, agent):
            return list(local_events or [])

    return Env()


def test_shape_perception_accurate_mode(monkeypatch):
    monkeypatch.setenv("PERCEPTION_MODE", "accurate")
    # Reload modules to pick up env var where needed
    import loopforge.narrative as narrative
    importlib.reload(narrative)

    agent = _make_agent()
    env = _make_env(local_events=["e1", "e2"], recent_supervisor_text=None)

    p = narrative.build_agent_perception(agent, env, step=1)
    assert p.perception_mode == "accurate"
    # accurate should not truncate events
    assert len(p.local_events) == 2
    # world_summary should contain the location
    assert "you are at A" in p.world_summary


def test_shape_perception_partial_mode(monkeypatch):
    monkeypatch.setenv("PERCEPTION_MODE", "partial")
    import loopforge.narrative as narrative
    importlib.reload(narrative)

    agent = _make_agent()
    env = _make_env(local_events=["e1", "e2", "e3"], recent_supervisor_text=None)

    p = narrative.build_agent_perception(agent, env, step=2)
    assert p.perception_mode == "partial"
    assert len(p.local_events) == 1  # truncated
    # world_summary should be shortened (ends with punctuation or ellipsis)
    assert len(p.world_summary) <= 120


def test_shape_perception_spin_mode_guardrail_tone(monkeypatch):
    monkeypatch.setenv("PERCEPTION_MODE", "spin")
    import loopforge.narrative as narrative
    importlib.reload(narrative)

    agent = _make_agent()
    # Guardrail-heavy supervisor text to bias tone
    env = _make_env(local_events=["e1"], recent_supervisor_text="Protocols need stricter adherence due to risk.")

    p = narrative.build_agent_perception(agent, env, step=3)
    assert p.perception_mode == "spin"
    # Expect a guardrail prefix
    assert p.world_summary.startswith("Management notes increased risk; follow protocols.")
    # Numeric fields untouched
    assert isinstance(p.traits.get("guardrail_reliance", 0.5), float)
