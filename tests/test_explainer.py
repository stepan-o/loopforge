from __future__ import annotations

from pathlib import Path
import json

from typer.testing import CliRunner

from loopforge.reporting import DaySummary, AgentDayStats, EpisodeSummary
from loopforge.explainer_context import build_episode_context, build_agent_focus_context
from loopforge.explainer import explain_agent_episode
from scripts.run_simulation import app as cli_app


def test_explainer_low_low_arc():
    # Low -> Low trajectory should use the special steady-low phrasing
    agent_ctx = {
        "agent_name": "Nova",
        "agent": {
            "role": "qa",
            "vibe": None,
            "tagline": None,
            "stress_start": 0.06,
            "stress_end": 0.00,
            "stress_arc": "falling",  # even if arc would be 'falling', special case should override wording
            "guardrail_total": 1,
            "context_total": 1,
            "guardrail_ratio": 0.5,
        },
        "episode_meta": {"tension_direction": "flat"},
        "per_day": [],
    }
    text = explain_agent_episode(agent_ctx)
    low = text.lower()
    assert "held steady" in low and "low" in low
    assert "gradually unwound" not in low
    assert "moderate" not in low


def test_explainer_near_zero_end():
    # End stress near zero should append the phrase "almost zero" inline (no standalone sentence)
    agent_ctx = {
        "agent_name": "Sprocket",
        "agent": {
            "role": "maintenance",
            "vibe": None,
            "tagline": None,
            "stress_start": 0.20,
            "stress_end": 0.02,  # < 0.03 threshold
            "stress_arc": "falling",
            "guardrail_total": 3,
            "context_total": 2,
            "guardrail_ratio": 3 / 5,
        },
        "episode_meta": {"tension_direction": "falling"},
        "per_day": [],
    }
    text = explain_agent_episode(agent_ctx)
    low = text.lower()
    assert ", down to almost zero." in low
    # Ensure no standalone sentence form
    assert "Down to almost zero." not in text


def test_explainer_role_flavor():
    # Known roles include their flavor line; unknown roles do not
    known_ctx = {
        "agent_name": "Delta",
        "agent": {
            "role": "qa",
            "vibe": None,
            "tagline": None,
            "stress_start": 0.10,
            "stress_end": 0.12,
            "stress_arc": "rising",
            "guardrail_total": 2,
            "context_total": 1,
            "guardrail_ratio": 2 / 3,
        },
        "episode_meta": {"tension_direction": "rising"},
        "per_day": [],
    }
    txt_known = explain_agent_episode(known_ctx)
    assert "As a qa, they are ever vigilant for faults and inconsistencies." in txt_known

    unknown_ctx = {
        "agent_name": "Ghost",
        "agent": {
            "role": "unknown",
            "vibe": None,
            "tagline": None,
            "stress_start": 0.05,
            "stress_end": 0.05,
            "stress_arc": "flat",
            "guardrail_total": 0,
            "context_total": 0,
            "guardrail_ratio": 0.0,
        },
        "episode_meta": {"tension_direction": "flat"},
        "per_day": [],
    }
    txt_unknown = explain_agent_episode(unknown_ctx)
    assert "As a unknown," not in txt_unknown


def _mk_day(idx: int, tension: float, stats: dict[str, AgentDayStats]) -> DaySummary:
    return DaySummary(
        day_index=idx,
        perception_mode="accurate",
        tension_score=tension,
        agent_stats=stats,
        total_incidents=0,
    )


def _mk_stats(name: str, role: str, g: int, c: int, s: float) -> AgentDayStats:
    return AgentDayStats(name=name, role=role, guardrail_count=g, context_count=c, avg_stress=s)


def _mk_episode(tensions: list[float], agents_stats_by_day: list[dict[str, AgentDayStats]]) -> EpisodeSummary:
    days = [_mk_day(i, t, stats) for i, (t, stats) in enumerate(zip(tensions, agents_stats_by_day))]
    # Aggregate like summarize_episode would for AgentEpisodeStats via reporting.summarize_episode
    from loopforge.reporting import summarize_episode
    ep = summarize_episode(days)
    return ep


def test_build_episode_and_agent_context_basic():
    # Two-day episode with one agent
    day0 = {"Delta": _mk_stats("Delta", "optimizer", g=2, c=1, s=0.05)}
    day1 = {"Delta": _mk_stats("Delta", "optimizer", g=3, c=0, s=0.20)}
    ep = _mk_episode([0.2, 0.4], [day0, day1])

    episode_ctx = build_episode_context(ep, ep.days, characters={})
    assert episode_ctx["episode_meta"]["tension_values"] == [0.2, 0.4]
    assert episode_ctx["episode_meta"]["tension_direction"] == "rising"

    delta_ctx = build_agent_focus_context(ep, ep.days, characters={}, agent_name="Delta")
    assert delta_ctx["agent_name"] == "Delta"
    assert isinstance(delta_ctx["agent"], dict)
    # stress arc rising because 0.05 -> 0.20 (> 0.05)
    assert delta_ctx["agent"]["stress_arc"] == "rising"
    # ratio guardrail over total (5/6)
    assert abs(delta_ctx["agent"]["guardrail_ratio"] - (5/6)) < 1e-6
    # per-day rollup has two days
    assert len(delta_ctx["per_day"]) == 2


def test_explainer_rule_phrases_and_determinism():
    # Hand-crafted context dicts
    agent_ctx = {
        "agent_name": "Delta",
        "agent": {
            "role": "optimizer",
            "vibe": "quietly obsessive optimizer energy",
            "tagline": None,
            "stress_start": 0.05,
            "stress_end": 0.35,
            "stress_arc": "rising",
            "guardrail_total": 2,
            "context_total": 5,
            "guardrail_ratio": 2 / 7,
        },
        "episode_meta": {"tension_direction": "rising"},
        "per_day": [],
    }

    text1 = explain_agent_episode(agent_ctx)
    text2 = explain_agent_episode(agent_ctx)

    assert "rising factory tension" in text1
    assert "quietly obsessive optimizer energy" in text1
    assert "tightened over the episode" in text1
    assert "leaned more on context than policy" in text1
    assert "rose in step" in text1 or "in step" in text1
    assert text1 == text2  # deterministic

    # Guardrail-only
    agent_ctx2 = {
        "agent_name": "Nova",
        "agent": {
            "role": "qa",
            "vibe": None,
            "tagline": None,
            "stress_start": 0.40,
            "stress_end": 0.10,
            "stress_arc": "falling",
            "guardrail_total": 10,
            "context_total": 0,
            "guardrail_ratio": 1.0,
        },
        "episode_meta": {"tension_direction": "falling"},
        "per_day": [],
    }
    txt_guard = explain_agent_episode(agent_ctx2)
    assert "stayed strictly within guardrails" in txt_guard
    assert "managed to relax as the factory itself eased off" in txt_guard


def test_cli_smoke_explain_episode(tmp_path: Path):
    # Build a tiny action log for one day with two agents
    actions_path = tmp_path / "actions.jsonl"
    rows = [
        {
            "step": i,
            "agent_name": "Delta" if i % 2 == 0 else "Nova",
            "role": "optimizer" if i % 2 == 0 else "qa",
            "mode": "guardrail" if i % 3 == 0 else "context",
            "intent": "work" if i % 3 == 0 else "inspect",
            "move_to": None,
            "targets": [],
            "riskiness": 0.2,
            "narrative": "",
            "raw_action": {},
            "perception": {"emotions": {"stress": 0.1 + 0.01 * i}, "perception_mode": "accurate"},
        }
        for i in range(10)
    ]
    actions_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli_app,
        [
            "explain-episode",
            "--action-log-path",
            str(actions_path),
            "--steps-per-day",
            "10",
            "--days",
            "1",
            "--agent",
            "Delta",
        ],
    )
    assert result.exit_code == 0
    out = result.stdout
    assert "EPISODE EXPLAINER" in out
    assert "Agent: Delta" in out
    assert out.strip().endswith(".")
