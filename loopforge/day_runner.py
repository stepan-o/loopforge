from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, List, Optional

from loopforge.logging_utils import JsonlReflectionLogger, JsonlSupervisorLogger
from loopforge.reflection import (
    filter_entries_for_day,
    run_daily_reflections_for_all_agents,
)
from loopforge.supervisor import build_supervisor_messages_for_day, set_supervisor_messages_on_env
from loopforge.types import ActionLogEntry, AgentReflection, SupervisorMessage


def _read_action_log(path: Path) -> List[ActionLogEntry]:
    """Read JSONL action log into ActionLogEntry objects.

    If the file does not exist or is empty, return an empty list.
    """
    p = Path(path)
    if not p.exists():
        return []
    entries: List[ActionLogEntry] = []
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                # ActionLogEntry requires specific keys; tolerate missing with defaults
                e = ActionLogEntry(
                    step=int(data.get("step", 0)),
                    agent_name=str(data.get("agent_name", "")),
                    role=str(data.get("role", "")),
                    mode=data.get("mode", "guardrail"),
                    intent=str(data.get("intent", "")),
                    move_to=data.get("move_to"),
                    targets=list(data.get("targets", [])),
                    riskiness=float(data.get("riskiness", 0.0)),
                    narrative=str(data.get("narrative", "")),
                    outcome=data.get("outcome"),
                    raw_action=dict(data.get("raw_action", {})),
                    perception=dict(data.get("perception", {})),
                )
                entries.append(e)
            except Exception:
                # fail-soft; skip bad lines
                continue
    return entries


def run_one_day(
    env: Any,
    agents: List[Any],
    steps_per_day: int = 50,
    day_index: int = 0,
    reflection_logger: Optional[JsonlReflectionLogger] = None,
    action_log_path: Path = Path("logs/loopforge_actions.jsonl"),
    *,
    episode_index: Optional[int] = None,
) -> List[AgentReflection]:
    """
    - Run `steps_per_day` environment steps.
    - Collect ActionLogEntries from the JSONL action log.
    - Filter to this day's entries.
    - Run reflections for all agents.
    - Log reflections if logger provided.
    - Return list of AgentReflection.

    Notes:
    - This helper is opt-in scaffolding and does not alter environment behavior.
    - It assumes `env` has a `step()` method to advance one simulation step.
    """
    # Advance the environment for the requested number of steps
    if hasattr(env, "step") and callable(getattr(env, "step")):
        for _ in range(steps_per_day):
            env.step()
    else:
        # If there's no step method, treat this as a no-op; scaffolding remains optional
        pass

    # Read all action entries and slice the window for this day
    all_entries = _read_action_log(action_log_path)
    day_entries = filter_entries_for_day(all_entries, day_index, steps_per_day)

    # Run reflections per agent and optionally log
    reflections = run_daily_reflections_for_all_agents(
        agents=agents,
        entries=day_entries,
        logger=reflection_logger,
        day_index=day_index,
        episode_index=episode_index,
    )
    return reflections


def run_one_day_with_supervisor(
    env: Any,
    agents: List[Any],
    steps_per_day: int = 50,
    day_index: int = 0,
    action_log_path: Path = Path("logs/loopforge_actions.jsonl"),
    reflection_log_path: Optional[Path] = None,
    supervisor_log_path: Optional[Path] = None,
    reflection_logger: Optional[JsonlReflectionLogger] = None,
    *,
    episode_index: Optional[int] = None,
) -> List[SupervisorMessage]:
    """
    Orchestrate one simulated day and emit Supervisor messages.

    - Runs the base `run_one_day(...)` to produce reflections.
    - Builds Supervisor messages from reflections.
    - Logs each SupervisorMessage as a JSONL line (fail-soft).
    - Publishes messages onto the environment for the next day's perceptions
      via env.supervisor_messages (consumed by narrative.build_agent_perception).

    Notes on log path precedence (per Phase 7):
    - SUPERVISOR_LOG_PATH env var (if present) takes precedence over all.
    - Else, use the explicit `supervisor_log_path` parameter if provided.
    - Else, default to logs/loopforge_supervisor.jsonl.

    This helper does not change the behavior of the core simulation loop or
    `run_simulation(...)`. It composes existing functionality and remains
    fail-soft around logging.
    """
    # Prepare a reflection logger if a path was provided but no logger object
    if reflection_logger is None and reflection_log_path is not None:
        try:
            reflection_logger = JsonlReflectionLogger(reflection_log_path)
        except Exception:
            reflection_logger = None

    # Run the day and collect reflections
    reflections = run_one_day(
        env=env,
        agents=agents,
        steps_per_day=steps_per_day,
        day_index=day_index,
        reflection_logger=reflection_logger,
        action_log_path=action_log_path,
        episode_index=episode_index,
    )

    # Enrich reflections with agent metadata for downstream heuristics
    # Reflections are returned in the same order as `agents` in run_daily_reflections_for_all_agents.
    # To avoid fragile inference from text, attach explicit agent_name/role by position.
    for agent_obj, refl in zip(agents, reflections):
        try:
            setattr(refl, "agent_name", getattr(agent_obj, "name", ""))
        except Exception:
            pass
        try:
            setattr(refl, "role", getattr(agent_obj, "role", ""))
        except Exception:
            pass

    # Build supervisor messages using heuristic
    messages = build_supervisor_messages_for_day(reflections, day_index=day_index)

    # Tag messages with episode index for Phase 10 (log-level only)
    if episode_index is not None:
        for m in messages:
            try:
                setattr(m, "episode_index", episode_index)
            except Exception:
                pass

    # Resolve supervisor log path with precedence
    env_override = os.getenv("SUPERVISOR_LOG_PATH")
    if env_override:
        sup_path = Path(env_override)
    elif supervisor_log_path is not None:
        sup_path = Path(supervisor_log_path)
    else:
        sup_path = Path("logs/loopforge_supervisor.jsonl")

    # Log messages (fail-soft)
    try:
        sup_logger = JsonlSupervisorLogger(sup_path)
        for m in messages:
            try:
                sup_logger.write_message(m)
            except Exception:
                pass
    except Exception:
        pass

    # Publish messages onto the environment for next-day perceptions
    try:
        set_supervisor_messages_on_env(env, messages)
    except Exception:
        # Do not let this break the orchestrator
        pass

    return messages


def run_episode(
    env: Any,
    agents: List[Any],
    num_days: int,
    steps_per_day: int,
    *,
    persist_to_db: bool,
    episode_index: int = 0,
    action_log_path: Optional[Path] = None,
    reflection_log_path: Optional[Path] = None,
    supervisor_log_path: Optional[Path] = None,
) -> None:
    """Run a multi-day episode of Loopforge.

    Each day reuses the same DB (if persist_to_db=True) but is tagged with
    (episode_index, day_index) in logs for later analysis.

    This orchestrator composes the existing `run_one_day_with_supervisor(...)`
    helper across multiple day windows. It does not alter simulation semantics.
    """
    # Prepare an optional reflection logger once for reuse
    reflection_logger: Optional[JsonlReflectionLogger] = None
    if reflection_log_path is not None:
        try:
            reflection_logger = JsonlReflectionLogger(reflection_log_path)
        except Exception:
            reflection_logger = None

    for day_idx in range(num_days):
        # For each day, delegate to the day orchestrator with labels
        run_one_day_with_supervisor(
            env=env,
            agents=agents,
            steps_per_day=steps_per_day,
            day_index=day_idx,
            action_log_path=action_log_path or Path("logs/loopforge_actions.jsonl"),
            reflection_log_path=None if reflection_logger is not None else reflection_log_path,
            supervisor_log_path=supervisor_log_path,
            reflection_logger=reflection_logger,
            episode_index=episode_index,
        )
    # No return; side effects are logs and optional env mailbox for next-day perceptions
