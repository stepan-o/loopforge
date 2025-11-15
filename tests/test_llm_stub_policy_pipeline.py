from types import SimpleNamespace

from loopforge import llm_stub


class DummyEnv:
    def __init__(self):
        self.events_buffer = []
        self.rooms = ["factory_floor", "control_room"]
        self.recent_supervisor_text = None


def test_decide_robot_action_returns_legacy_shape_no_mode(monkeypatch):
    # Force LLM path off to use deterministic plan
    monkeypatch.setattr(llm_stub, "USE_LLM_POLICY", False, raising=True)

    agent = SimpleNamespace(
        name="R-17",
        role="maintenance",
        location="factory_floor",
        battery_level=80,
        # emotions object with required attributes
        emotions=SimpleNamespace(stress=0.2, curiosity=0.5, social_need=0.3, satisfaction=0.6),
    )
    env = DummyEnv()

    # Note: this signature mirrors how llm_stub.decide_robot_action is used internally
    action = llm_stub.decide_robot_action(
        name=agent.name,
        role=agent.role,
        step=1,
        location=agent.location,
        battery_level=agent.battery_level,
        emotions=agent.emotions,
    )

    assert isinstance(action, dict)
    # Legacy keys should exist
    assert "action_type" in action
    assert "destination" in action
    # Phase 2 requirement: do NOT expose mode yet
    assert "mode" not in action
