from types import SimpleNamespace

from loopforge.narrative import build_agent_perception


class DummyEnv:
    def __init__(self):
        self.events_buffer = []
        self.rooms = ["factory_floor", "control_room"]
        self.recent_supervisor_text = None


def test_build_agent_perception_basic_fields():
    agent = SimpleNamespace(
        name="R-17",
        role="maintenance",
        location="LineA.ControlRoom",
        battery_level=55,
        emotions=SimpleNamespace(stress=0.7, curiosity=0.2, social_need=0.3, satisfaction=0.6),
        traits=SimpleNamespace(risk_aversion=0.6, obedience=0.8, ambition=0.4, empathy=0.5, blame_external=0.2),
    )
    env = DummyEnv()

    p = build_agent_perception(agent, env, step=3)

    assert p.step == 3
    assert p.name == "R-17"
    assert p.role == "maintenance"
    assert p.location == "LineA.ControlRoom"
    assert p.battery_level == 55
    assert isinstance(p.emotions, dict) and p.emotions["stress"] == 0.7
    assert isinstance(p.traits, dict) and p.traits["risk_aversion"] == 0.6
    # summaries should be strings (possibly empty or short deterministic text)
    assert isinstance(p.world_summary, str)
    assert isinstance(p.personal_recent_summary, str)
    # local events list exists
    assert isinstance(p.local_events, list)
