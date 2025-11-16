"""Core simulation loop for Loopforge City.

Implements `run_simulation` which initializes the DB, seeds robots, and
executes a simple step loop, persisting actions, memories, and events.
"""
from __future__ import annotations

from typing import List, Tuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import RobotAgent, SupervisorAgent, default_traits_for, default_triggers_for
from .config import get_settings, get_action_log_path
from .db import session_scope, get_engine
from .emotions import (
    EmotionState,
    update_emotions,
    emotion_from_robot,
    apply_emotion_to_robot,
    traits_from_robot,
    apply_traits_to_robot,
)
from .environment import LoopforgeEnvironment, generate_environment_events
from .models import ActionLog, EnvironmentEvent, Memory, Robot
from .narrative import build_agent_perception
from .llm_stub import decide_robot_action_plan, decide_robot_action_plan_and_dict
from pathlib import Path
from .logging_utils import JsonlActionLogger, log_action_step
from . import llm_stub


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
            # Seed with initial traits presets
            from .agents import default_traits_for  # local import to avoid cycles
            traits = default_traits_for(name)
            session.add(
                Robot(
                    name=name,
                    role=role,
                    personality_json=personality,
                    traits_json={
                        "risk_aversion": traits.risk_aversion,
                        "obedience": traits.obedience,
                        "ambition": traits.ambition,
                        "empathy": traits.empathy,
                        "blame_external": traits.blame_external,
                    },
                    location="factory_floor" if role != "qa" else "control_room",
                    battery_level=100,
                    stress=0.2,
                    curiosity=0.5,
                    social_need=0.3,
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
                traits_json={"risk_aversion": 0.6, "obedience": 0.8, "ambition": 0.5, "empathy": 0.6, "blame_external": 0.2},
                location="control_room",
                battery_level=100,
                stress=0.1,
                curiosity=0.4,
                social_need=0.2,
                satisfaction=0.7,
            )
        )


def _agent_from_robot(r: Robot) -> RobotAgent:
    # Build agent with emotions/traits from DB and attach default triggers by name
    agent = RobotAgent(
        name=r.name,
        role=r.role,
        location=r.location,
        battery_level=r.battery_level,
        emotions=emotion_from_robot(r),
        traits=traits_from_robot(r),
        triggers=default_triggers_for(r.name),
    )
    return agent


def run_simulation(
    num_steps: int = 10,
    persist_to_db: bool | None = None,
    action_logger: Optional[JsonlActionLogger] | None = None,
    action_log_path: Optional[Path] | None = None,
) -> None:
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

    # Resolve a single action logger for this run (fail-soft)
    if action_logger is None:
        try:
            effective_path = action_log_path or get_action_log_path()
        except Exception:
            effective_path = Path("logs/loopforge_actions.jsonl")
        action_logger = JsonlActionLogger(effective_path)

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
                    traits=default_traits_for(name),
                    triggers=default_triggers_for(name),
                )
            )
        for step in range(1, num_steps + 1):
            env.advance()
            step_summaries: List[str] = []
            for agent in robots_agents:
                # Build perception → plan via explicit seam (always), regardless of LLM flag.
                perception = build_agent_perception(agent, env, step)
                plan, decision = decide_robot_action_plan_and_dict(perception)
                # Log the action step exactly once (fail-soft)
                try:
                    log_action_step(
                        logger=action_logger,
                        perception=perception,
                        plan=plan,
                        action=decision,
                        outcome=None,
                    )
                except Exception:
                    pass
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

                # Build simple context flags
                near_error = any(e.location == agent.location for e in env.events_buffer)
                isolated = sum(1 for a in robots_agents if a.location == agent.location) <= 1
                ctx = {"near_error": near_error, "isolated": isolated}

                # Update emotions and run triggers
                update_emotions(agent, {"action_type": action}, ctx)
                agent.run_triggers(env)

                # Occasional environment events (in-memory only)
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
                # Build perception → plan via explicit seam (always), regardless of LLM flag.
                perception = build_agent_perception(agent, env, step)
                plan, decision = decide_robot_action_plan_and_dict(perception)
                try:
                    log_action_step(
                        logger=action_logger,
                        perception=perception,
                        plan=plan,
                        action=decision,
                        outcome=None,
                    )
                except Exception:
                    pass
                action = decision.get("action_type", "idle")
                dest = decision.get("destination") or r.location
                content = decision.get("content")

                # Simple world update: location + battery
                r.location = dest
                if action == "recharge":
                    r.battery_level = min(100, r.battery_level + 20)
                elif action == "move":
                    r.battery_level = max(0, r.battery_level - 5)
                elif action == "work":
                    r.battery_level = max(0, r.battery_level - 10)
                elif action == "talk":
                    r.battery_level = max(0, r.battery_level - 2)

                # Build a minimal context for emotion updates
                # near_error: any env event in last few steps at this location
                recent_err = session.scalars(
                    select(EnvironmentEvent)
                    .where(EnvironmentEvent.location == r.location)
                    .where(EnvironmentEvent.timestamp_step >= max(0, step - 3))
                    .limit(1)
                ).first()
                # isolated: naive heuristic (not talking and not in control room)
                isolated = (action != "talk" and r.location != "control_room")
                ctx = {"near_error": bool(recent_err), "isolated": isolated}

                # Update emotions and evaluate triggers, then persist back
                update_emotions(agent, {"action_type": action}, ctx)
                agent.run_triggers(env)
                apply_emotion_to_robot(r, agent.emotions)
                apply_traits_to_robot(r, agent.traits)

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
                # Include a short narrative from the decision plan if available
                narrative = decision.get("narrative")
                mem_text = f"{r.name} did {action} at {dest}."
                if narrative:
                    mem_text += f" Plan: {narrative}"
                session.add(
                    Memory(
                        robot_id=r.id,
                        timestamp_step=step,
                        text=mem_text,
                        importance=1,
                        tags={"action": action},
                    )
                )

                # Simple environment event buffered
                if action == "work" and step % 7 == 0:
                    env.record_event("error", r.location, f"Minor fault detected by {r.name}")

                step_summaries.append(f"{r.name} {action}s at {dest} (stress={r.stress:.2f})")

            # Drain env events into DB
            for evt in env.drain_events():
                session.add(evt)

            # Generate events from recent behavior/state
            new_events = generate_environment_events(env, session)
            for evt in new_events:
                session.add(evt)
                print(f"t={step}: {evt.event_type.upper()} at {evt.location} — {evt.description}")

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

            # Make the supervisor's content available to triggers next step
            env.recent_supervisor_text = sup_content or env.recent_supervisor_text

            # Print a concise summary
            print(f"t={step}: {summary_text}; Supervisor {sup_action}")
