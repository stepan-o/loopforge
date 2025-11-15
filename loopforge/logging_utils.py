from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any, Optional, Iterable, List

from loopforge.types import (
    ActionLogEntry,
    AgentPerception,
    AgentActionPlan,
    ReflectionLogEntry,
    AgentReflection,
    SupervisorMessage,
)


class JsonlActionLogger:
    """
    Minimal JSONL logger for action steps.

    Writes one JSON object per line. This is deliberately simple so it
    can be swapped out later.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def write_entry(self, entry: ActionLogEntry) -> None:
        line = json.dumps(entry.to_dict(), separators=(",", ":"))
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line)
            f.write("\n")


def log_action_step(
    logger: JsonlActionLogger,
    perception: AgentPerception,
    plan: AgentActionPlan,
    action: Dict[str, Any],
    outcome: Optional[str] = None,
) -> None:
    entry = ActionLogEntry(
        step=perception.step,
        agent_name=perception.name,
        role=perception.role,
        mode=plan.mode,
        intent=plan.intent,
        move_to=plan.move_to,
        targets=list(plan.targets),
        riskiness=plan.riskiness,
        narrative=plan.narrative,
        outcome=outcome,
        raw_action=dict(action),
        perception=perception.to_dict(),
    )
    # Logging must not crash the sim; swallow exceptions.
    try:
        logger.write_entry(entry)
    except Exception:
        # Optional debug hook; for now, fail-soft.
        pass


def read_action_log_entries(path: Path) -> List[ActionLogEntry]:
    """Read a JSONL file of action entries.

    Fail-soft: if the file doesn't exist, return an empty list. Any
    malformed lines are skipped.
    """
    p = Path(path)
    if not p.exists():
        return []
    entries: List[ActionLogEntry] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(ActionLogEntry.from_dict(data))
                except Exception:
                    # skip malformed lines
                    continue
    except Exception:
        # If the file becomes unreadable, return what we have so far
        return entries
    return entries


class JsonlReflectionLogger:
    """Minimal JSONL logger for daily reflections."""

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_reflection(
        self,
        agent_name: str,
        role: str,
        day_index: int,
        reflection: AgentReflection,
        traits_after: Dict[str, float],
    ) -> None:
        entry = ReflectionLogEntry(
            agent_name=agent_name,
            role=role,
            day_index=day_index,
            reflection=reflection,
            traits_after=traits_after,
            perception_mode=getattr(reflection, "perception_mode", None),
        )
        with self.path.open("a", encoding="utf8") as f:
            f.write(json.dumps(entry.to_dict()) + "\n")


class JsonlSupervisorLogger:
    """
    Minimal JSONL logger for Supervisor messages.
    One JSON object per line, using SupervisorMessage.to_dict().
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write_message(self, message: SupervisorMessage) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(message.to_dict()))
            f.write("\n")
