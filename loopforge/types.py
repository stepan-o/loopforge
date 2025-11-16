from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal, Union


# --- SupervisorIntentSnapshot (Phase 9: Supervisor Bias Field) -------------


@dataclass
class SupervisorIntentSnapshot:
    """
    Subjective belief about the Supervisor's intent.

    Lives above the seam; JSON-serializable; no DB coupling.
    """

    true_intent: str  # canonical: "encourage_context" | "tighten_guardrails" | "neutral"
    perceived_intent: str  # e.g., "punitive", "supportive", "apathetic", "protective", "reckless"
    confidence: float  # 0.0–1.0
    notes: str  # short natural-language summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            "true_intent": self.true_intent,
            "perceived_intent": self.perceived_intent,
            "confidence": float(self.confidence),
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SupervisorIntentSnapshot":
        return cls(
            true_intent=str(data.get("true_intent", "neutral")),
            perceived_intent=str(data.get("perceived_intent", "apathetic")),
            confidence=float(data.get("confidence", 0.5)),
            notes=str(data.get("notes", "")),
        )


# --- EpisodeTensionSnapshot (Phase 9 Lite: Weave) ----------------------------


@dataclass
class EpisodeTensionSnapshot:
    """Episode-level roll-up snapshot derived purely from logs.

    Pure, JSON-safe. No DB coupling. Intended to be written as JSONL lines
    by a dedicated weave logger.
    """

    episode_index: int
    num_days: int
    num_actions: int
    num_reflections: int

    # Aggregated metrics
    incident_rate: float
    belief_rate: float  # from perception_mode drift
    guardrail_rate: float
    context_rate: float

    # Supervisor perception rates from reflections
    punitive_rate: float
    supportive_rate: float
    apathetic_rate: float

    # Emotional climate (optional v1)
    avg_stress: Optional[float] = None
    avg_satisfaction: Optional[float] = None

    # High-level roll-up
    tension_index: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "episode_index": int(self.episode_index),
            "num_days": int(self.num_days),
            "num_actions": int(self.num_actions),
            "num_reflections": int(self.num_reflections),
            "incident_rate": float(self.incident_rate),
            "belief_rate": float(self.belief_rate),
            "guardrail_rate": float(self.guardrail_rate),
            "context_rate": float(self.context_rate),
            "punitive_rate": float(self.punitive_rate),
            "supportive_rate": float(self.supportive_rate),
            "apathetic_rate": float(self.apathetic_rate),
            "avg_stress": None if self.avg_stress is None else float(self.avg_stress),
            "avg_satisfaction": None if self.avg_satisfaction is None else float(self.avg_satisfaction),
            "tension_index": float(self.tension_index),
            "notes": str(self.notes or ""),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EpisodeTensionSnapshot":
        return cls(
            episode_index=int(data.get("episode_index", 0)),
            num_days=int(data.get("num_days", 0)),
            num_actions=int(data.get("num_actions", 0)),
            num_reflections=int(data.get("num_reflections", 0)),
            incident_rate=float(data.get("incident_rate", 0.0)),
            belief_rate=float(data.get("belief_rate", 0.0)),
            guardrail_rate=float(data.get("guardrail_rate", 0.0)),
            context_rate=float(data.get("context_rate", 0.0)),
            punitive_rate=float(data.get("punitive_rate", 0.0)),
            supportive_rate=float(data.get("supportive_rate", 0.0)),
            apathetic_rate=float(data.get("apathetic_rate", 0.0)),
            avg_stress=(None if data.get("avg_stress") is None else float(data.get("avg_stress"))),
            avg_satisfaction=(None if data.get("avg_satisfaction") is None else float(data.get("avg_satisfaction"))),
            tension_index=float(data.get("tension_index", 0.0)),
            notes=str(data.get("notes", "")),
        )


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

    # Phase 9: agent's biased belief about Supervisor intent for this day/period
    supervisor_intent: Optional[SupervisorIntentSnapshot] = None

    # Perception regime used when constructing this object. Phase 4b default: "accurate".
    perception_mode: Literal["accurate", "partial", "spin"] = "accurate"

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
            "supervisor_intent": self.supervisor_intent.to_dict() if self.supervisor_intent else None,
            "perception_mode": self.perception_mode,
            "extra": dict(self.extra),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentPerception":
        """
        Best-effort constructor from a dict.

        This exists mainly so legacy code/tests that produce dicts can be
        adapted later without massive refactors.
        """
        # Parse optional supervisor_intent sub-dict if present
        sup_intent_data = data.get("supervisor_intent")
        sup_intent_obj = None
        if isinstance(sup_intent_data, dict):
            try:
                sup_intent_obj = SupervisorIntentSnapshot.from_dict(sup_intent_data)
            except Exception:
                sup_intent_obj = None
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
            supervisor_intent=sup_intent_obj,
            perception_mode=data.get("perception_mode", "accurate"),
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
    tags: Dict[str, bool] = field(default_factory=dict)

    # Phase 8: which perception mode was active while acting this day
    perception_mode: Optional[str] = None

    # Phase 9: perceived supervisor intent keyword for the day (compact)
    supervisor_perceived_intent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary_of_day": self.summary_of_day,
            "self_assessment": self.self_assessment,
            "intended_changes": self.intended_changes,
            "tags": dict(self.tags),
            "perception_mode": self.perception_mode,
            "supervisor_perceived_intent": self.supervisor_perceived_intent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentReflection":
        return cls(
            summary_of_day=str(data.get("summary_of_day", "")),
            self_assessment=str(data.get("self_assessment", "")),
            intended_changes=str(data.get("intended_changes", "")),
            tags=dict(data.get("tags", {})),
            perception_mode=data.get("perception_mode"),
            supervisor_perceived_intent=data.get("supervisor_perceived_intent"),
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

    # Optional, used in later phases to tag which policy produced the action
    policy_name: Optional[str] = None

    # Phase 10 (episodes): optional episode/day labels for log analysis only
    episode_index: Optional[int] = None
    day_index: Optional[int] = None

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
            "policy_name": self.policy_name,
            "episode_index": self.episode_index,
            "day_index": self.day_index,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActionLogEntry":
        """Best-effort parse from a plain dict (JSONL line)."""
        return cls(
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
            policy_name=data.get("policy_name"),
            episode_index=data.get("episode_index"),
            day_index=data.get("day_index"),
        )



# --- ReflectionLogEntry ------------------------------------------------------


@dataclass
class ReflectionLogEntry:
    agent_name: str
    role: str
    day_index: Optional[int]
    reflection: AgentReflection
    traits_after: Dict[str, float]
    # Phase 8: include the perception mode under which the agent operated
    perception_mode: Optional[str] = None
    # Phase 9: include the perceived supervisor intent (compact string)
    supervisor_perceived_intent: Optional[str] = None
    # Phase 10: optional episode/day labels (day_index kept for backward compat)
    episode_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "day_index": self.day_index,
            "reflection": self.reflection.to_dict(),
            "traits_after": dict(self.traits_after),
            "perception_mode": self.perception_mode,
            "supervisor_perceived_intent": self.supervisor_perceived_intent,
            "episode_index": self.episode_index,
        }



# --- SupervisorMessage -------------------------------------------------------


@dataclass
class SupervisorMessage:
    """
    A single Supervisor message directed at one agent for a given day.
    This is what eventually shows up as `recent_supervisor_text` in
    AgentPerception.
    """

    agent_name: str
    role: str
    day_index: int

    # What kind of nudge this is
    intent: Literal["tighten_guardrails", "encourage_context", "neutral_update"]

    # Text the agent actually "sees"
    body: str

    # Optional episode label for log analysis (Phase 10)
    episode_index: Optional[int] = None

    # Extra flags for analysis
    tags: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "role": self.role,
            "day_index": self.day_index,
            "intent": self.intent,
            "body": self.body,
            "episode_index": self.episode_index,
            "tags": dict(self.tags),
        }
