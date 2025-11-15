from __future__ import annotations

from loopforge.supervisor_bias import infer_supervisor_intent
from loopforge.types import SupervisorMessage


def _msg(intent: str) -> SupervisorMessage:
    return SupervisorMessage(
        agent_name="R-1",
        role="maintenance",
        day_index=0,
        intent=intent,  # "tighten_guardrails" | "encourage_context" | "neutral_update"
        body="test",
        tags={},
    )


def test_infer_none_when_no_message():
    assert infer_supervisor_intent(None, traits={}) is None


def test_guardrails_high_blame_is_punitive():
    msg = _msg("tighten_guardrails")
    snap = infer_supervisor_intent(msg, traits={"blame_external": 0.9, "obedience": 0.2})
    assert snap is not None
    assert snap.true_intent == "tighten_guardrails"
    assert snap.perceived_intent == "punitive"
    assert snap.confidence > 0.7
    assert isinstance(snap.notes, str) and snap.notes


def test_guardrails_high_obedience_low_blame_is_protective():
    msg = _msg("tighten_guardrails")
    snap = infer_supervisor_intent(msg, traits={"blame_external": 0.2, "obedience": 0.85})
    assert snap is not None
    assert snap.perceived_intent in {"protective", "strict"}  # allow fallback if thresholds adjust


def test_encourage_context_high_risk_averse_is_reckless():
    msg = _msg("encourage_context")
    snap = infer_supervisor_intent(msg, traits={"risk_aversion": 0.8, "obedience": 0.5})
    assert snap is not None
    assert snap.perceived_intent == "reckless"


def test_neutral_low_satisfaction_is_apathetic():
    msg = _msg("neutral_update")
    snap = infer_supervisor_intent(msg, traits={}, satisfaction=0.1)
    assert snap is not None
    assert snap.perceived_intent == "apathetic"
