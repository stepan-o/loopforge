import importlib
from contextlib import contextmanager

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker


def _make_sqlite_engine(tmp_path):
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    engine = sa.create_engine(url, future=True)
    return engine


def _setup_sqlite_bind(monkeypatch, engine):
    """Monkeypatch loopforge.db to use a provided engine and a fresh SessionLocal.
    Also create tables.
    """
    import loopforge.db as db
    import loopforge.models as models

    # Replace get_engine to return our test engine
    monkeypatch.setattr(db, "get_engine", lambda echo=None: engine, raising=True)

    # Rebind SessionLocal
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "SessionLocal", TestSessionLocal, raising=True)

    # Create schema directly
    models.Base.metadata.create_all(engine)


def test_run_simulation_nodb(monkeypatch):
    # Ensure LLM path is off for deterministic behavior
    import loopforge.llm_stub as stub
    monkeypatch.setattr(stub, "USE_LLM_POLICY", False, raising=True)

    from loopforge.simulation import run_simulation

    # Should complete without exceptions
    run_simulation(num_steps=3, persist_to_db=False)


def test_run_simulation_db_sqlite_llm_off(tmp_path, monkeypatch):
    engine = _make_sqlite_engine(tmp_path)
    _setup_sqlite_bind(monkeypatch, engine)

    # Ensure LLM is disabled
    import loopforge.llm_stub as stub
    monkeypatch.setattr(stub, "USE_LLM_POLICY", False, raising=True)

    from loopforge.simulation import run_simulation
    from loopforge.db import SessionLocal
    from loopforge import models as m

    run_simulation(num_steps=3, persist_to_db=True)

    # Assertions on DB contents
    with SessionLocal() as s:
        robots = s.query(m.Robot).all()
        assert any(r.role != "supervisor" for r in robots)
        actions = s.query(m.ActionLog).all()
        assert len(actions) > 0
        # At least one robot emotion changed from default
        any_changed = any(abs(r.stress - 0.2) > 1e-6 or abs(r.social_need - 0.3) > 1e-6 for r in robots if r.role != "supervisor")
        assert any_changed


def test_run_simulation_db_sqlite_llm_mocked(tmp_path, monkeypatch):
    engine = _make_sqlite_engine(tmp_path)
    _setup_sqlite_bind(monkeypatch, engine)

    # Enable LLM policy and mock decisions
    import loopforge.llm_stub as stub
    monkeypatch.setattr(stub, "USE_LLM_POLICY", True, raising=True)

    def robot_resp(*a, **k):
        return {"action_type": "move", "destination": "control_room", "content": "testing"}

    def sup_resp(*a, **k):
        return {
            "action_type": "broadcast",
            "target_robot_name": None,
            "destination": None,
            "content": "Test broadcast",
        }

    monkeypatch.setattr(stub, "chat_json", lambda *a, **k: robot_resp(*a, **k) if "Robot state:" in a[1][0]["content"] else sup_resp(*a, **k))

    from loopforge.simulation import run_simulation
    from loopforge.db import SessionLocal
    from loopforge import models as m

    run_simulation(num_steps=3, persist_to_db=True)

    with SessionLocal() as s:
        acts = s.query(m.ActionLog).filter(m.ActionLog.actor_type == "robot").all()
        assert acts, "Expected some robot actions"
        assert all(a.action_type == "move" for a in acts)
        assert all(a.destination == "control_room" for a in acts)
