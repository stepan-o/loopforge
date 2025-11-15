from __future__ import annotations

from loopforge.agents import RobotAgent, default_triggers_for
from loopforge.emotions import EmotionState, Traits


class FakeEnv:
    def __init__(self, msg: str | None = None):
        self.recent_supervisor_text = msg
        self.rooms = ["factory_floor", "control_room"]
        self.events_buffer = []
        self.step = 1


def test_sprocket_crash_mode_trigger():
    # High stress and recent supervisor says "hurry" should trigger Crash Mode
    agent = RobotAgent(
        name="Sprocket",
        role="maintenance",
        location="factory_floor",
        battery_level=80,
        emotions=EmotionState(stress=0.85, curiosity=0.4, social_need=0.3, satisfaction=0.5),
        traits=Traits(risk_aversion=0.5, obedience=0.5, ambition=0.5, empathy=0.5, blame_external=0.2),
        triggers=default_triggers_for("Sprocket"),
    )
    env = FakeEnv(msg="Please hurry on Line A")

    before_risk = agent.traits.risk_aversion
    before_stress = agent.emotions.stress
    agent.run_triggers(env)

    assert agent.traits.risk_aversion <= before_risk - 0.099  # allow for clamping rounding
    assert agent.emotions.stress >= before_stress  # slight bump
    assert 0.0 <= agent.traits.risk_aversion <= 1.0
    assert 0.0 <= agent.emotions.stress <= 1.0


def test_nova_quiet_resentment_trigger():
    # Stress high and satisfaction low should reduce obedience and increase blame_external
    agent = RobotAgent(
        name="Nova",
        role="qa",
        location="control_room",
        battery_level=90,
        emotions=EmotionState(stress=0.7, curiosity=0.5, social_need=0.3, satisfaction=0.25),
        traits=Traits(risk_aversion=0.5, obedience=0.6, ambition=0.4, empathy=0.8, blame_external=0.4),
        triggers=default_triggers_for("Nova"),
    )
    env = FakeEnv()

    before_obed = agent.traits.obedience
    before_blame = agent.traits.blame_external

    agent.run_triggers(env)

    assert agent.traits.obedience < before_obed
    assert agent.traits.blame_external > before_blame
    assert 0.0 <= agent.traits.obedience <= 1.0
    assert 0.0 <= agent.traits.blame_external <= 1.0
