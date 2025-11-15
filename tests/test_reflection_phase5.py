from __future__ import annotations

import json
from types import SimpleNamespace

from loopforge.types import ActionLogEntry, AgentReflection
from loopforge.emotions import Traits
from loopforge.reflection import (
    summarize_agent_day,
    build_agent_reflection,
    apply_reflection_to_traits,
    run_daily_reflection_for_agent,
)


def make_entry(step: int, agent: str, mode: str = "guardrail", outcome: str | None = None) -> ActionLogEntry:
    return ActionLogEntry(
        step=step,
        agent_name=agent,
        role="maintenance",
        mode=mode,
        intent="work",
        move_to=None,
        targets=[],
        riskiness=0.0,
        narrative="",
        outcome=outcome,
        raw_action={"action_type": "work"},
        perception={"name": agent, "traits": {"guardrail_reliance": 0.5}},
    )


def test_summarize_agent_day_counts_phase5_keys():
    entries = [
        make_entry(1, "Sprocket", mode="guardrail"),
        make_entry(2, "Sprocket", mode="context"),
        make_entry(3, "Sprocket", mode="context", outcome="incident"),
        make_entry(4, "Delta", mode="guardrail"),
    ]
    s = summarize_agent_day("Sprocket", entries)
    assert s["total_steps"] == 3
    assert s["guardrail_steps"] == 1
    assert s["context_steps"] == 2
    assert s["incidents"] == 1
    # Back-compat keys still present
    assert s["steps"] == 3
    assert s["incident_count"] == 1


def test_build_agent_reflection_tagging_three_scenarios():
    # A) Mostly guardrail + incident
    s1 = {"total_steps": 5, "guardrail_steps": 4, "context_steps": 1, "incidents": 1}
    r1 = build_agent_reflection("R-17", "maintenance", s1)
    assert isinstance(r1, AgentReflection)
    assert r1.tags.get("regretted_obedience") is True

    # B) Mostly context + incident
    s2 = {"total_steps": 5, "guardrail_steps": 1, "context_steps": 4, "incidents": 1}
    r2 = build_agent_reflection("R-17", "maintenance", s2)
    assert r2.tags.get("regretted_risk") is True

    # C) No incidents + some context
    s3 = {"total_steps": 6, "guardrail_steps": 2, "context_steps": 4, "incidents": 0}
    r3 = build_agent_reflection("R-17", "maintenance", s3)
    assert r3.tags.get("validated_context") is True


def test_apply_reflection_to_traits_pure_and_legacy_paths():
    # Pure: input Traits, expect a new Traits with nudges and clamping
    traits = Traits(risk_aversion=0.5, obedience=0.5, ambition=0.5, empathy=0.5, blame_external=0.5, guardrail_reliance=0.5)
    reflection = AgentReflection(
        summary_of_day="",
        self_assessment="",
        intended_changes="",
        tags={"regretted_risk": True},
    )
    new_traits = apply_reflection_to_traits(traits, reflection)
    assert isinstance(new_traits, Traits)
    assert new_traits.risk_aversion > traits.risk_aversion
    assert new_traits.guardrail_reliance > traits.guardrail_reliance
    assert 0.0 <= new_traits.risk_aversion <= 1.0
    assert 0.0 <= new_traits.guardrail_reliance <= 1.0

    # Legacy: mutate agent-like object with dict traits
    agent = SimpleNamespace(traits={"guardrail_reliance": 1.0, "risk_aversion": 0.0})
    reflection2 = AgentReflection(
        summary_of_day="",
        self_assessment="",
        intended_changes="",
        tags={"regretted_obedience": True, "validated_context": True},
    )
    apply_reflection_to_traits(agent, reflection2)
    # Should decrease guardrail_reliance and clamp within [0,1]
    assert 0.0 <= agent.traits["guardrail_reliance"] <= 1.0


def test_run_daily_reflection_for_agent_wrapper_end_to_end():
    # Use legacy wrapper signature (agent, entries) consistent with existing module
    agent = SimpleNamespace(name="Nova", role="qa", traits={"guardrail_reliance": 0.5, "risk_aversion": 0.5})
    entries = [
        make_entry(1, "Nova", mode="context"),
        make_entry(2, "Nova", mode="context"),
        make_entry(3, "Nova", mode="guardrail"),
    ]
    reflection = run_daily_reflection_for_agent(agent, entries)
    assert isinstance(reflection, AgentReflection)
    # Expect validated_context tag because majority context and no incidents
    assert reflection.tags.get("validated_context") is True
    # Trait drift applied to agent in-place
    assert 0.0 <= agent.traits["guardrail_reliance"] <= 1.0
    assert 0.0 <= agent.traits["risk_aversion"] <= 1.0
