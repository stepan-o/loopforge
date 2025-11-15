from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

from loopforge.logging_utils import JsonlReflectionLogger
from loopforge.reflection import (
    filter_entries_for_day,
    run_daily_reflections_for_all_agents,
)
from loopforge.types import ActionLogEntry, AgentReflection


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
    )
    return reflections
