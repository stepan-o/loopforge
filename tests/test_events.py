from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from loopforge.environment import LoopforgeEnvironment, generate_environment_events
from loopforge import models as m


def _sqlite_engine(tmp_path):
    db_path = tmp_path / "events.db"
    return sa.create_engine(f"sqlite:///{db_path}", future=True)


def _bootstrap_db(engine):
    m.Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True)
    with Session() as s:
        # Create Sprocket with high stress at factory_floor
        sprocket = m.Robot(
            name="Sprocket",
            role="maintenance",
            personality_json={},
            traits_json={},
            location="factory_floor",
            battery_level=90,
            stress=0.8 + 0.05,  # > 0.7
            curiosity=0.5,
            social_need=0.3,
            satisfaction=0.5,
        )
        s.add(sprocket)
        s.flush()
        # Last action: work at factory_floor on previous step
        s.add(
            m.ActionLog(
                robot_id=sprocket.id,
                actor_type="robot",
                action_type="work",
                destination="factory_floor",
                content=None,
                timestamp_step=1,
            )
        )
        # Recent error at factory_floor within last 5 steps
        s.add(
            m.EnvironmentEvent(
                event_type="MinorError",
                location="factory_floor",
                description="Recent glitch",
                timestamp_step=1,
            )
        )
        s.commit()
    return Session


def test_generate_environment_events_incident_and_minor(tmp_path):
    engine = _sqlite_engine(tmp_path)
    Session = _bootstrap_db(engine)

    env = LoopforgeEnvironment()
    # Sweep steps to hit deterministic chance thresholds
    incidents = 0
    minor_errors = 0
    for step in range(1, 13):  # 1..12 includes a step%10 == 0 (step=10)
        env.step = step
        with Session() as s:
            events = generate_environment_events(env, s)
            for e in events:
                if e.event_type == "Incident":
                    incidents += 1
                if e.event_type == "MinorError":
                    minor_errors += 1
    # Expect at least one Incident across the sweep given 30% deterministic chance
    assert incidents >= 1
    # Expect at least one MinorError (chance ~10% fires on step%10==0 i.e., step=10)
    assert minor_errors >= 1
