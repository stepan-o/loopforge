from __future__ import annotations

"""Supervisor Bias Field (Sprint 3)

Pure helper to infer an agent's subjective belief about a Supervisor message.
Deterministic, JSON-safe, and lives above the seam (no DB / I-O).
"""

from typing import Optional

from .types import SupervisorMessage, SupervisorIntentSnapshot

try:  # optional type import; avoid hard dependency at import time
    from .emotions import Traits  # type: ignore
except Exception:  # pragma: no cover - fallback for type hints only
    Traits = object  # type: ignore


def _val(obj: object, name: str, default: float = 0.5) -> float:
    """Best-effort attribute/dict accessor returning a float in [0,1]."""
    try:
        if isinstance(obj, dict):  # type: ignore[reportGeneralTypeIssues]
            v = float(obj.get(name, default))  # type: ignore[attr-defined]
        else:
            v = float(getattr(obj, name, default))
    except Exception:
        v = default
    # Clamp
    return max(0.0, min(1.0, v))


def infer_supervisor_intent(
    message: Optional[SupervisorMessage],
    traits: object,
    satisfaction: Optional[float] = None,
) -> Optional[SupervisorIntentSnapshot]:
    """Infer a subjective belief about Supervisor intent.

    Inputs (deterministic):
    - message.intent (true_intent): "tighten_guardrails" | "encourage_context" | "neutral_update"
    - traits signals: blame_external, obedience, risk_aversion
    - satisfaction (0..1) as morale proxy (optional). If None, treated as 0.5.

    Returns None if no message supplied.
    """
    if message is None:
        return None

    true_intent = message.intent

    blame_external = _val(traits, "blame_external", 0.5)
    obedience = _val(traits, "obedience", 0.5)
    risk_aversion = _val(traits, "risk_aversion", 0.5)
    sat = 0.5 if satisfaction is None else max(0.0, min(1.0, float(satisfaction)))

    perceived: str
    notes: str

    if true_intent == "tighten_guardrails":
        if blame_external >= 0.7:
            perceived = "punitive"
            notes = "Supervisor feels harsh and critical."
        elif obedience >= 0.7 and blame_external <= 0.4:
            perceived = "protective"
            notes = "Supervisor is trying to keep us safe and responsible."
        else:
            perceived = "strict"
            notes = "Supervisor stresses stricter protocol adherence."
        # Confidence: stronger extremity → higher confidence
        confidence = max(blame_external, obedience, 0.6)

    elif true_intent == "encourage_context":
        if risk_aversion >= 0.7:
            perceived = "reckless"
            notes = "Supervisor seems to push risky experimentation."
        elif obedience <= 0.4:
            perceived = "empowering"
            notes = "Supervisor is trying to empower us to use judgment."
        else:
            perceived = "supportive"
            notes = "Supervisor encourages contextual judgment within bounds."
        confidence = max(risk_aversion, 1 - obedience, 0.6)

    else:  # "neutral_update" (or any other future neutral-like intent)
        if sat <= 0.3:
            perceived = "apathetic"
            notes = "Supervisor seems disengaged."
        else:
            perceived = "steady"
            notes = "Supervisor maintains status quo without new pressure."
        confidence = max(1 - sat, 0.6)

    # Clamp confidence into [0,1]
    confidence = max(0.0, min(1.0, float(confidence)))

    return SupervisorIntentSnapshot(
        true_intent=true_intent,
        perceived_intent=perceived,
        confidence=confidence,
        notes=notes,
    )
