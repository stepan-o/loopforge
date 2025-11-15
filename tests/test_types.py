import math

from loopforge.types import AgentPerception, AgentActionPlan, AgentReflection


def test_agent_perception_roundtrip_dict():
    data = {
        "step": 3,
        "name": "R-17",
        "role": "maintenance",
        "location": "LineA.ControlRoom",
        "battery_level": 0.42,
        "emotions": {"stress": 0.7, "curiosity": 0.2},
        "traits": {"risk_aversion": 0.6, "obedience": 0.8},
        "world_summary": "Line A stable.",
        "personal_recent_summary": "Patched console firmware.",
        "local_events": ["Minor alarm cleared"],
        "recent_supervisor_text": "Remember Protocol 14.",
        "extra": {"debug_note": "test"},
    }

    perception = AgentPerception.from_dict(data)
    as_dict = perception.to_dict()

    # Basic invariants: we keep core fields & types
    assert as_dict["step"] == 3
    assert as_dict["name"] == "R-17"
    assert as_dict["role"] == "maintenance"
    assert as_dict["location"] == "LineA.ControlRoom"
    assert math.isclose(as_dict["battery_level"], 0.42)
    assert as_dict["emotions"]["stress"] == 0.7
    assert as_dict["traits"]["obedience"] == 0.8
    assert "Minor alarm cleared" in as_dict["local_events"]
    assert as_dict["recent_supervisor_text"] == "Remember Protocol 14."
    assert as_dict["extra"]["debug_note"] == "test"


def test_agent_action_plan_roundtrip_dict():
    data = {
        "intent": "inspect",
        "move_to": "LineA.SensorBank",
        "targets": ["Sensor-12"],
        "riskiness": 0.3,
        "narrative": "I go check the flaky sensor.",
        "meta": {"source": "test"},
    }

    plan = AgentActionPlan.from_dict(data)
    as_dict = plan.to_dict()

    assert as_dict["intent"] == "inspect"
    assert as_dict["move_to"] == "LineA.SensorBank"
    assert as_dict["targets"] == ["Sensor-12"]
    assert math.isclose(as_dict["riskiness"], 0.3)
    assert as_dict["narrative"] == "I go check the flaky sensor."
    assert as_dict["meta"]["source"] == "test"


def test_agent_reflection_roundtrip_dict():
    data = {
        "summary_of_day": "Lots of alarms, no major incidents.",
        "self_assessment": "I followed protocol too rigidly.",
        "intended_changes": "Ask more questions before escalating.",
        "tags": {
            "regretted_obedience": True,
            "resent_supervisor": False,
        },
    }

    reflection = AgentReflection.from_dict(data)
    as_dict = reflection.to_dict()

    assert as_dict["summary_of_day"].startswith("Lots of alarms")
    assert "protocol too rigidly" in as_dict["self_assessment"]
    assert "Ask more questions" in as_dict["intended_changes"]
    assert as_dict["tags"]["regretted_obedience"] is True
