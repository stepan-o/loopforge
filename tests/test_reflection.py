from types import SimpleNamespace

from loopforge.reflection import (
    summarize_agent_day,
    build_agent_reflection,
    apply_reflection_to_traits,
    run_daily_reflection_for_agent,
)
from loopforge.types import ActionLogEntry


def _entry(step, name, mode="guardrail", outcome=None):
    return ActionLogEntry(
        step=step,
        agent_name=name,
        role="maintenance",
        mode=mode,
        intent="work",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        outcome=outcome,
        raw_action={},
        perception={},
    )


def test_summarize_agent_day_counts():
    entries = [
        _entry(1, "R-17", mode="guardrail"),
        _entry(2, "R-17", mode="context"),
        _entry(3, "R-17", mode="context", outcome="incident"),
        _entry(4, "Other", mode="guardrail"),
    ]
    s = summarize_agent_day("R-17", entries)
    assert s["steps"] == 3
    assert s["guardrail_steps"] == 1
    assert s["context_steps"] == 2
    assert s["incident_count"] == 1


def test_build_agent_reflection_tags():
    # Mostly guardrail + incident
    s1 = {"steps": 5, "guardrail_steps": 4, "context_steps": 1, "incident_count": 1}
    r1 = build_agent_reflection("R-17", "maintenance", s1)
    assert r1.tags.get("regretted_obedience") is True

    # Mostly context + incident
    s2 = {"steps": 5, "guardrail_steps": 1, "context_steps": 4, "incident_count": 1}
    r2 = build_agent_reflection("R-17", "maintenance", s2)
    assert r2.tags.get("regretted_risk") is True

    # Mostly context + no incident
    s3 = {"steps": 6, "guardrail_steps": 2, "context_steps": 4, "incident_count": 0}
    r3 = build_agent_reflection("R-17", "maintenance", s3)
    assert r3.tags.get("validated_context") is True


def test_apply_reflection_to_traits_clamped():
    agent = SimpleNamespace(traits={"guardrail_reliance": 0.8, "risk_aversion": 0.5})

    # Regretted obedience: guardrail_reliance down
    r1 = SimpleNamespace(tags={"regretted_obedience": True})
    apply_reflection_to_traits(agent, r1)
    assert agent.traits["guardrail_reliance"] <= 0.75

    # Regretted risk: guardrail_reliance and risk_aversion up
    r2 = SimpleNamespace(tags={"regretted_risk": True})
    apply_reflection_to_traits(agent, r2)
    assert agent.traits["guardrail_reliance"] >= 0.75
    assert agent.traits["risk_aversion"] >= 0.55

    # Validated context: guardrail_reliance down
    r3 = SimpleNamespace(tags={"validated_context": True})
    apply_reflection_to_traits(agent, r3)
    assert 0.0 <= agent.traits["guardrail_reliance"] <= 1.0
    assert 0.0 <= agent.traits["risk_aversion"] <= 1.0


def test_run_daily_reflection_for_agent_e2e():
    agent = SimpleNamespace(name="R-17", role="maintenance", traits={"guardrail_reliance": 0.5, "risk_aversion": 0.5})
    entries = [
        _entry(1, "R-17", mode="context"),
        _entry(2, "R-17", mode="context"),
        _entry(3, "R-17", mode="guardrail"),
    ]

    reflection = run_daily_reflection_for_agent(agent, entries)
    assert hasattr(reflection, "summary_of_day")
    assert "R-17" in reflection.summary_of_day
    # Trait moved (likely down for guardrail_reliance if validated_context)
    assert 0.0 <= agent.traits["guardrail_reliance"] <= 1.0
    assert 0.0 <= agent.traits["risk_aversion"] <= 1.0
