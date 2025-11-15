import importlib

import types

from loopforge.emotions import EmotionState


def test_robot_decision_stub_path(monkeypatch):
    import loopforge.llm_stub as stub
    importlib.reload(stub)

    # Force LLM off at the module level
    monkeypatch.setattr(stub, "USE_LLM_POLICY", False, raising=True)

    # If chat_json is ever called, raise to fail the test
    monkeypatch.setattr(stub, "chat_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("chat_json should not be called when LLM disabled")))

    out = stub.decide_robot_action(
        name="Sprocket",
        role="maintenance",
        step=1,
        location="factory_floor",
        battery_level=100,
        emotions=EmotionState(),
    )
    assert isinstance(out, dict)
    assert "action_type" in out


def test_robot_decision_llm_success(monkeypatch):
    import loopforge.llm_stub as stub
    importlib.reload(stub)

    # Enable LLM path
    monkeypatch.setattr(stub, "USE_LLM_POLICY", True, raising=True)

    # Return a valid JSON-like dict from the LLM helper
    monkeypatch.setattr(
        stub,
        "chat_json",
        lambda *a, **k: {"action_type": "move", "destination": "control_room", "content": "check equipment"},
    )

    # If deterministic fallback is called, error out
    def _bad(*a, **k):
        raise AssertionError("deterministic fallback should not be called on LLM success")

    monkeypatch.setattr(stub, "_deterministic_robot_policy", _bad)

    out = stub.decide_robot_action(
        name="Delta",
        role="optimizer",
        step=2,
        location="factory_floor",
        battery_level=80,
        emotions=EmotionState(),
    )
    assert out["action_type"] == "move"
    assert out["destination"] == "control_room"


def test_robot_decision_llm_fallback(monkeypatch):
    import loopforge.llm_stub as stub
    importlib.reload(stub)

    monkeypatch.setattr(stub, "USE_LLM_POLICY", True, raising=True)
    monkeypatch.setattr(stub, "chat_json", lambda *a, **k: None)

    sentinel = {"action_type": "idle", "destination": None, "content": "fallback"}
    monkeypatch.setattr(stub, "_deterministic_robot_policy", lambda *a, **k: sentinel)

    out = stub.decide_robot_action(
        name="Nova",
        role="qa",
        step=3,
        location="control_room",
        battery_level=70,
        emotions=EmotionState(),
    )
    assert out == sentinel


def test_supervisor_stub_path(monkeypatch):
    import loopforge.llm_stub as stub
    importlib.reload(stub)

    monkeypatch.setattr(stub, "USE_LLM_POLICY", False, raising=True)
    monkeypatch.setattr(stub, "chat_json", lambda *a, **k: (_ for _ in ()).throw(AssertionError("chat_json should not be called")))

    out = stub.decide_supervisor_action(1, "summary text")
    assert isinstance(out, dict)
    assert out.get("action_type") in {"broadcast", "inspect", "coach", "idle"}


def test_supervisor_llm_success(monkeypatch):
    import loopforge.llm_stub as stub
    importlib.reload(stub)

    monkeypatch.setattr(stub, "USE_LLM_POLICY", True, raising=True)
    monkeypatch.setattr(
        stub,
        "chat_json",
        lambda *a, **k: {
            "action_type": "broadcast",
            "target_robot_name": None,
            "destination": None,
            "content": "Hello workers",
        },
    )

    # Ensure deterministic fallback not used
    monkeypatch.setattr(stub, "_deterministic_supervisor_policy", lambda *a, **k: (_ for _ in ()).throw(AssertionError("fallback not expected")))

    out = stub.decide_supervisor_action(2, "world summary")
    assert out["action_type"] == "broadcast"
    assert out["content"] == "Hello workers"


def test_supervisor_llm_fallback(monkeypatch):
    import loopforge.llm_stub as stub
    importlib.reload(stub)

    monkeypatch.setattr(stub, "USE_LLM_POLICY", True, raising=True)
    monkeypatch.setattr(stub, "chat_json", lambda *a, **k: None)

    sentinel = {"actor_type": "supervisor", "action_type": "inspect", "destination": "control_room", "content": "fallback"}
    monkeypatch.setattr(stub, "_deterministic_supervisor_policy", lambda *a, **k: sentinel)

    out = stub.decide_supervisor_action(3, "summary")
    assert out == sentinel
