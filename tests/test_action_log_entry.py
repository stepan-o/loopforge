from loopforge.types import ActionLogEntry


def test_action_log_entry_to_dict_basic():
    entry = ActionLogEntry(
        step=3,
        agent_name="R-17",
        role="maintenance",
        mode="guardrail",
        intent="inspect",
        move_to="LineA.SensorBank",
        targets=["Sensor-12"],
        riskiness=0.3,
        narrative="I go inspect the flaky sensor.",
        outcome="no_incident",
        raw_action={"intent": "inspect"},
        perception={"name": "R-17"},
    )
    data = entry.to_dict()

    assert data["step"] == 3
    assert data["agent_name"] == "R-17"
    assert data["role"] == "maintenance"
    assert data["mode"] == "guardrail"
    assert data["intent"] == "inspect"
    assert data["move_to"] == "LineA.SensorBank"
    assert data["targets"] == ["Sensor-12"]
    assert data["narrative"].startswith("I go inspect")
    assert data["raw_action"]["intent"] == "inspect"
    assert data["perception"]["name"] == "R-17"