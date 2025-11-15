from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal


# --- AgentPerception --------------------------------------------------------


@dataclass
class AgentPerception:
    """
    What the environment tells an agent at a single step.

    This is the agent's subjective view: it is derived from environment
    truth (DB / world state), but may be incomplete or biased in later phases.

    Environment code is responsible for constructing this from world truth.
    Agents and policies should rely on AgentPerception rather than reading
    raw environment state directly.
    """

    step: int
    name: str
    role: str  # e.g. "maintenance", "qa", "supervisor"
    location: str

    battery_level: Optional[float] = None  # 0.0–1.0 or None if N/A

    emotions: Dict[str, float] = field(default_factory=dict)
    # e.g. {"stress": 0.7, "curiosity": 0.2}

    traits: Dict[str, float] = field(default_factory=dict)
    # e.g. {"risk_aversion": 0.6, "obedience": 0.8, "guardrail_reliance": 0.9}

    world_summary: str = ""
    personal_recent_summary: str = ""

    local_events: List[str] = field(default_factory=list)
    # e.g. ["Line A: minor fault", "Console B locked for audit"]

    recent_supervisor_text: Optional[str] = None

    # Optional free-form field for anything we haven't modeled yet
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict for logging / DB if needed."""
        return {
            "step": self.step,
            "name": self.name,
            "role": self.role,
            "location": self.location,
            "battery_level": self.battery_level,
            "emotions": dict(self.emotions),
            "traits": dict(self.traits),
            "world_summary": self.world_summary,
            "personal_recent_summary": self.personal_recent_summary,
            "local_events": list(self.local_events),
            "recent_supervisor_text": self.recent_supervisor_text,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPerception":
        """
        Best-effort constructor from a dict.

        This exists mainly so legacy code/tests that produce dicts can be
        adapted later without massive refactors.
        """
        return cls(
            step=int(data.get("step", 0)),
            name=str(data.get("name", "")),
            role=str(data.get("role", "")),
            location=str(data.get("location", "")),
            battery_level=data.get("battery_level"),
            emotions=dict(data.get("emotions", {})),
            traits=dict(data.get("traits", {})),
            world_summary=str(data.get("world_summary", "")),
            personal_recent_summary=str(data.get("personal_recent_summary", "")),
            local_events=list(data.get("local_events", [])),
            recent_supervisor_text=data.get("recent_supervisor_text"),
            extra=dict(data.get("extra", {})),
        )


# --- AgentActionPlan --------------------------------------------------------


@dataclass
class AgentActionPlan:
    """
    What the agent intends to do next.

    Environment will later translate this into movement, incidents, etc.
    For now it is a structured replacement for ad-hoc action dicts.
    """

    intent: str  # e.g. "work", "inspect", "confront", "recharge", "idle"
    move_to: Optional[str] = None  # room / area id, or None to stay put
    targets: List[str] = field(default_factory=list)
    riskiness: float = 0.0  # agent's own sense of risk, 0.0–1.0

    # NEW: central axis for Loopforge behavior (guardrail vs context)
    mode: Literal["guardrail", "context"] = "guardrail"

    narrative: str = ""  # human-readable description of what & why

    # Optional metadata for migration from legacy action dicts
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to a plain dict compatible with existing code paths.

        This does *not* enforce a particular legacy schema; it's a thin
        wrapper so we can keep JSON logs / DB rows simple until Phase 2.
        """
        return {
            "intent": self.intent,
            "move_to": self.move_to,
            "targets": list(self.targets),
            "riskiness": float(self.riskiness),
            "mode": self.mode,
            "narrative": self.narrative,
            "meta": dict(self.meta),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentActionPlan":
        """
        Best-effort constructor from a legacy-style action dict.

        This is intentionally forgiving; missing fields fall back to defaults.
        """
        return cls(
            intent=str(data.get("intent", "")),
            move_to=data.get("move_to"),
            targets=list(data.get("targets", [])),
            riskiness=float(data.get("riskiness", 0.0)),
            mode=data.get("mode", "guardrail"),
            narrative=str(data.get("narrative", "")),
            meta=dict(data.get("meta", {})),
        )


# --- AgentReflection (stub for future phases) -------------------------------


@dataclass
class AgentReflection:
    """
    End-of-day/episode subjective reflection.

    Phase 1 only introduces the type so future phases can wire it in
    without broad signature churn.
    """

    summary_of_day: str
    self_assessment: str
    intended_changes: str

    # Optional tags for trait / relationship updates later.
    tags: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_of_day": self.summary_of_day,
            "self_assessment": self.self_assessment,
            "intended_changes": self.intended_changes,
            "tags": dict(self.tags),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentReflection":
        return cls(
            summary_of_day=str(data.get("summary_of_day", "")),
            self_assessment=str(data.get("self_assessment", "")),
            intended_changes=str(data.get("intended_changes", "")),
            tags=dict(data.get("tags", {})),
        )



# --- ActionLogEntry ----------------------------------------------------------


@dataclass
class ActionLogEntry:
    """
    Structured log for a single agent step.

    Captures what the agent knew (perception summary),
    how it decided (mode + intent), and what action dict we applied.
    """

    step: int
    agent_name: str
    role: str

    mode: Literal["guardrail", "context"]
    intent: str
    move_to: Optional[str]
    targets: List[str]
    riskiness: float
    narrative: str

    outcome: Optional[str] = None  # optional for now

    raw_action: Dict[str, Any] = field(default_factory=dict)
    perception: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "agent_name": self.agent_name,
            "role": self.role,
            "mode": self.mode,
            "intent": self.intent,
            "move_to": self.move_to,
            "targets": list(self.targets),
            "riskiness": float(self.riskiness),
            "narrative": self.narrative,
            "outcome": self.outcome,
            "raw_action": dict(self.raw_action),
            "perception": dict(self.perception),
        }
