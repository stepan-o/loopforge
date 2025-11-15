from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from loopforge.simulation import run_simulation
from loopforge import models as m


def _sqlite_engine(tmp_path):
    db_path = tmp_path / "memories.db"
    return sa.create_engine(f"sqlite:///{db_path}", future=True)


def _setup_sqlite_bind(monkeypatch, engine):
    import loopforge.db as db
    import loopforge.models as models

    # Replace get_engine to return our test engine
    monkeypatch.setattr(db, "get_engine", lambda echo=None: engine, raising=True)

    # Rebind SessionLocal
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    monkeypatch.setattr(db, "SessionLocal", TestSessionLocal, raising=True)

    # Create schema directly
    models.Base.metadata.create_all(engine)


def test_memory_contains_narrative_suffix(tmp_path, monkeypatch):
    engine = _sqlite_engine(tmp_path)
    _setup_sqlite_bind(monkeypatch, engine)

    # Ensure LLM disabled (deterministic path that adds narrative via plan)
    import loopforge.llm_stub as stub
    monkeypatch.setattr(stub, "USE_LLM_POLICY", False, raising=True)

    # Run a short DB-backed simulation
    run_simulation(num_steps=2, persist_to_db=True)

    # Verify at least one Memory has the narrative "Plan:" suffix
    from loopforge.db import SessionLocal

    with SessionLocal() as s:
        mems = s.query(m.Memory).all()
        assert mems, "Expected some Memory rows"
        assert any("Plan:" in (mem.text or "") for mem in mems)
