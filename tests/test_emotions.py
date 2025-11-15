from __future__ import annotations

from loopforge.emotions import EmotionState, update_emotions


class FakeAgent:
    def __init__(self, em: EmotionState | None = None):
        self.emotions = em or EmotionState()


def test_update_emotions_work_and_context_near_error():
    agent = FakeAgent(EmotionState(stress=0.2, curiosity=0.5, social_need=0.3, satisfaction=0.5))
    ctx = {"near_error": True, "isolated": False}

    update_emotions(agent, {"action_type": "work"}, ctx)

    # Baseline + work + near_error should push stress up and curiosity up
    assert agent.emotions.stress >= 0.2
    assert agent.emotions.curiosity >= 0.5
    # social_need decays a bit by baseline
    assert agent.emotions.social_need <= 0.3
    # values are clamped within [0,1]
    for v in (
        agent.emotions.stress,
        agent.emotions.curiosity,
        agent.emotions.social_need,
        agent.emotions.satisfaction,
    ):
        assert 0.0 <= v <= 1.0


def test_update_emotions_recharge_and_isolated():
    agent = FakeAgent(EmotionState(stress=0.9, curiosity=0.1, social_need=0.0, satisfaction=0.2))
    ctx = {"near_error": False, "isolated": True}

    update_emotions(agent, {"action_type": "recharge"}, ctx)

    # Recharge should reduce stress and increase satisfaction
    assert agent.emotions.stress < 0.9
    assert agent.emotions.satisfaction > 0.2
    # isolated nudges social_need up
    assert agent.emotions.social_need >= 0.0
    # still clamped to [0,1]
    for v in (
        agent.emotions.stress,
        agent.emotions.curiosity,
        agent.emotions.social_need,
        agent.emotions.satisfaction,
    ):
        assert 0.0 <= v <= 1.0
