from __future__ import annotations

from loopforge.narrative import build_agent_perception, AgentActionPlan
from loopforge.emotions import EmotionState, Traits
from loopforge.llm_stub import decide_robot_action_plan


class FakeEnv:
    def __init__(self):
        self.rooms = ["factory_floor", "control_room"]
        self.step = 1
        self.recent_supervisor_text = None
        self.events_buffer = []


class FakeAgent:
    def __init__(self):
        self.name = "Sprocket"
        self.role = "maintenance"
        self.location = "factory_floor"
        self.battery_level = 100
        self.emotions = EmotionState(stress=0.2, curiosity=0.5, social_need=0.3, satisfaction=0.5)
        self.traits = Traits(risk_aversion=0.4, obedience=0.6, ambition=0.5, empathy=0.7, blame_external=0.2)


def test_build_agent_perception_basic():
    env = FakeEnv()
    agent = FakeAgent()

    p = build_agent_perception(agent, env, step=1)

    assert p.name == agent.name
    assert p.role == agent.role
    assert p.location == agent.location
    assert p.step == 1
    assert set(p.emotions.keys()) == {"stress", "curiosity", "social_need", "satisfaction"}
    # Traits should at least include the canonical five; additional keys (like guardrail_reliance) are allowed
    keys = set(p.traits.keys())
    assert {"risk_aversion", "obedience", "ambition", "empathy", "blame_external"}.issubset(keys)
    assert "guardrail_reliance" in keys
    assert isinstance(p.world_summary, str) and p.world_summary
    assert isinstance(p.personal_recent_summary, str) and p.personal_recent_summary
    assert isinstance(p.local_events, list)


def test_decide_robot_action_plan_from_perception():
    env = FakeEnv()
    agent = FakeAgent()

    p = build_agent_perception(agent, env, step=2)
    plan = decide_robot_action_plan(p)

    assert isinstance(plan, AgentActionPlan)
    assert plan.intent in {"move", "work", "talk", "recharge", "inspect", "idle"}
    assert 0.0 <= plan.riskiness <= 1.0
    assert isinstance(plan.narrative, str) and plan.narrative
