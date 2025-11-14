"""Core simulation loop for Loopforge City.

Implements `run_simulation` which initializes the DB, seeds robots, and
executes a simple step loop, persisting actions, memories, and events.
"""
from __future__ import annotations

from typing import List, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import RobotAgent, SupervisorAgent
from .config import get_settings
from .db import session_scope, get_engine
from .emotions import EmotionState
from .environment import LoopforgeEnvironment
from .models import ActionLog, EnvironmentEvent, Memory, Robot


INITIAL_ROBOTS: List[Tuple[str, str, dict]] = [
    ("Sprocket", "maintenance", {"curious": 0.7}),
    ("Delta", "optimizer", {"focused": 0.8}),
    ("Nova", "qa", {"social": 0.6, "introspective": 0.7}),
]


def _seed_robots(session: Session) -> None:
    """Ensure initial robots (and Supervisor) exist in DB."""
    existing = {r.name for r in session.scalars(select(Robot)).all()}
    for name, role, personality in INITIAL_ROBOTS:
        if name not in existing:
            session.add(
                Robot(
                    name=name,
                    role=role,
                    personality_json=personality,
                    location="factory_floor" if role != "qa" else "control_room",
                    battery_level=100,
                    stress=0.2,
                    curiosity=0.5,
                    social_need=0.5,
                    satisfaction=0.5,
                )
            )
    # Represent supervisor as a special robot row to link action logs if needed
    if "Supervisor" not in existing:
        session.add(
            Robot(
                name="Supervisor",
                role="supervisor",
                personality_json={"oversight": 1.0},
                location="control_room",
                battery_level=100,
                stress=0.1,
                curiosity=0.4,
                social_need=0.2,
                satisfaction=0.7,
            )
        )


def _agent_from_robot(r: Robot) -> RobotAgent:
    return RobotAgent(
        name=r.name,
        role=r.role,
        location=r.location,
        battery_level=r.battery_level,
        emotions=EmotionState(
            stress=r.stress,
            curiosity=r.curiosity,
            social_need=r.social_need,
            satisfaction=r.satisfaction,
        ),
    )


def run_simulation(num_steps: int = 10, persist_to_db: bool | None = None) -> None:
    """Run a simple multi-agent simulation for `num_steps` steps.

    If `persist_to_db` is True, connects to the DB, seeds robots, and persists
    actions, memories, and events. If False, runs a pure in-memory simulation
    suitable for quick local testing (no DB reads/writes).
    """
    settings = get_settings()
    if persist_to_db is None:
        persist_to_db = settings.persist_to_db

    env = LoopforgeEnvironment()
    supervisor = SupervisorAgent()

    if not persist_to_db:
        # Pure in-memory run: initialize agents from INITIAL_ROBOTS
        robots_agents: List[RobotAgent] = []
        for name, role, _personality in INITIAL_ROBOTS:
            start_loc = "factory_floor" if role != "qa" else "control_room"
            robots_agents.append(
                RobotAgent(
                    name=name,
                    role=role,
                    location=start_loc,
                    battery_level=100,
                    emotions=EmotionState(),
                )
            )
        for step in range(1, num_steps + 1):
            env.advance()
            step_summaries: List[str] = []
            for agent in robots_agents:
                decision = agent.decide(step)
                action = decision.get("action_type", "idle")
                dest = decision.get("destination") or agent.location
                agent.location = dest
                # Battery updates
                if action == "recharge":
                    agent.battery_level = min(100, agent.battery_level + 20)
                elif action == "move":
                    agent.battery_level = max(0, agent.battery_level - 5)
                elif action == "work":
                    agent.battery_level = max(0, agent.battery_level - 10)
                elif action == "talk":
                    agent.battery_level = max(0, agent.battery_level - 2)
                agent.emotions.apply_action_effects(action)
                # Environment events (not persisted in no-DB mode)
                if action == "work" and step % 7 == 0:
                    env.record_event("info", agent.location, f"(no-db) Minor fault noted by {agent.name}")
                step_summaries.append(
                    f"{agent.name} {action}s at {dest} (stress={agent.emotions.stress:.2f})"
                )
            # Drain any events (noop in no-DB mode)
            env.drain_events()
            summary_text = "; ".join(step_summaries)
            sup_action = supervisor.decide(step, summary_text).get("action_type", "inspect")
            print(f"t={step}: {summary_text}; Supervisor {sup_action}")
        return

    # DB-backed run
    # Ensure engine can connect early (will use DATABASE_URL)
    get_engine()

    with session_scope() as session:
        _seed_robots(session)

    for step in range(1, num_steps + 1):
        env.advance()
        with session_scope() as session:
            # Load latest robot rows
            robots = session.scalars(select(Robot).where(Robot.role != "supervisor").order_by(Robot.id)).all()
            sup_row = session.scalars(select(Robot).where(Robot.name == "Supervisor")).first()

            # Create agents from DB rows
            agents = [_agent_from_robot(r) for r in robots]

            step_summaries: List[str] = []
            # Each robot decides and acts
            for r, agent in zip(robots, agents):
                decision = agent.decide(step)
                action = decision.get("action_type", "idle")
                dest = decision.get("destination") or r.location
                content = decision.get("content")

                # Simple world update: location + battery + emotions
                r.location = dest
                if action == "recharge":
                    r.battery_level = min(100, r.battery_level + 20)
                elif action == "move":
                    r.battery_level = max(0, r.battery_level - 5)
                elif action == "work":
                    r.battery_level = max(0, r.battery_level - 10)
                elif action == "talk":
                    r.battery_level = max(0, r.battery_level - 2)

                agent.emotions.apply_action_effects(action)
                r.stress = agent.emotions.stress
                r.curiosity = agent.emotions.curiosity
                r.social_need = agent.emotions.social_need
                r.satisfaction = agent.emotions.satisfaction

                # Persist action + memory
                session.add(
                    ActionLog(
                        robot_id=r.id,
                        actor_type="robot",
                        action_type=action,
                        destination=dest,
                        content=content,
                        timestamp_step=step,
                    )
                )
                session.add(
                    Memory(
                        robot_id=r.id,
                        timestamp_step=step,
                        text=f"{r.name} did {action} at {dest}.",
                        importance=1,
                        tags={"action": action},
                    )
                )

                # Simple environment event
                if action == "work" and step % 7 == 0:
                    env.record_event("error", r.location, f"Minor fault detected by {r.name}")

                step_summaries.append(f"{r.name} {action}s at {dest} (stress={r.stress:.2f})")

            # Drain env events into DB
            for evt in env.drain_events():
                session.add(evt)

            # Supervisor overview and action
            summary_text = "; ".join(step_summaries)
            sup_decision = supervisor.decide(step, summary_text)
            sup_action = sup_decision.get("action_type", "inspect")
            sup_dest = sup_decision.get("destination")
            sup_target = sup_decision.get("target_robot_name")
            sup_content = sup_decision.get("content")

            session.add(
                ActionLog(
                    robot_id=sup_row.id if sup_row else None,
                    actor_type="supervisor",
                    action_type=sup_action,
                    target_robot_name=sup_target,
                    destination=sup_dest,
                    content=sup_content,
                    timestamp_step=step,
                )
            )

            # Print a concise summary
            print(f"t={step}: {summary_text}; Supervisor {sup_action}")
