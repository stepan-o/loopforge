import json
from pathlib import Path
from types import SimpleNamespace

from loopforge.supervisor import build_supervisor_messages_for_day, set_supervisor_messages_on_env
from loopforge.narrative import build_agent_perception
from loopforge.logging_utils import JsonlSupervisorLogger
from loopforge.types import AgentReflection, SupervisorMessage


def test_build_supervisor_messages_for_day_regretted_risk():
    ref = AgentReflection(
        summary_of_day="",
        self_assessment="",
        intended_changes="",
        tags={"regretted_risk": True},
    )
    # Attach agent metadata dynamically for the test
    setattr(ref, "agent_name", "R-17")
    setattr(ref, "role", "maintenance")

    messages = build_supervisor_messages_for_day([ref], day_index=1)
    assert len(messages) == 1
    msg = messages[0]
    assert msg.intent == "tighten_guardrails"
    assert "risk" in msg.body.lower()


def test_build_supervisor_messages_for_day_encourage_context():
    ref = AgentReflection(
        summary_of_day="",
        self_assessment="",
        intended_changes="",
        tags={"regretted_obedience": True},
    )
    setattr(ref, "agent_name", "R-17")
    setattr(ref, "role", "maintenance")
    msgs = build_supervisor_messages_for_day([ref], day_index=0)
    assert msgs and msgs[0].intent == "encourage_context"

    ref2 = AgentReflection(
        summary_of_day="",
        self_assessment="",
        intended_changes="",
        tags={"validated_context": True},
    )
    setattr(ref2, "agent_name", "R-18")
    setattr(ref2, "role", "qa")
    msgs2 = build_supervisor_messages_for_day([ref2], day_index=0)
    assert msgs2 and msgs2[0].intent == "encourage_context"


def test_build_supervisor_messages_for_day_neutral():
    ref = AgentReflection(summary_of_day="", self_assessment="", intended_changes="", tags={})
    setattr(ref, "agent_name", "R-17")
    setattr(ref, "role", "maintenance")
    msgs = build_supervisor_messages_for_day([ref], day_index=2)
    assert msgs and msgs[0].intent == "neutral_update"


def test_supervisor_message_shows_in_perception_recent_supervisor_text():
    env = SimpleNamespace()
    agent = SimpleNamespace(name="R-17", role="maintenance", location="A", traits={}, emotions={})

    msg = SupervisorMessage(
        agent_name="R-17",
        role="maintenance",
        day_index=0,
        intent="tighten_guardrails",
        body="Follow protocols more strictly.",
        tags={},
    )

    set_supervisor_messages_on_env(env, [msg])

    perception = build_agent_perception(agent, env, step=0)
    assert perception.recent_supervisor_text == "Follow protocols more strictly."


def test_jsonl_supervisor_logger_writes_line(tmp_path: Path):
    log_path = tmp_path / "supervisor.jsonl"
    logger = JsonlSupervisorLogger(log_path)

    msg = SupervisorMessage(
        agent_name="R-17",
        role="maintenance",
        day_index=2,
        intent="encourage_context",
        body="You can use more judgment.",
        tags={"encouraging_context": True},
    )

    logger.write_message(msg)

    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["agent_name"] == "R-17"
    assert data["intent"] == "encourage_context"
