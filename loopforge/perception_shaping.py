from __future__ import annotations

"""Perception shaping layer (Phase 8, v1).

This module provides a small, pure transformation that adjusts an
AgentPerception according to the configured perception mode. It does
not read or modify DB/world truth; it only changes the subjective view.

Modes:
- accurate: no-op
- partial: hides some details (truncate local_events; simplify summary)
- spin: tone-shifts summaries based on recent supervisor guidance

The shaping tries hard to avoid fabricating facts; it mainly truncates
or prefixes/suffixes existing summaries.
"""

from typing import TYPE_CHECKING

from .config import get_perception_mode

if TYPE_CHECKING:  # pragma: no cover
    from .types import AgentPerception


def _truncate_summary(text: str) -> str:
    """Return a shortened summary: first sentence or first ~80 chars."""
    if not text:
        return text
    # Prefer first sentence cut
    for sep in (".", "!", "?"):
        idx = text.find(sep)
        if 0 <= idx < 120:  # a modest bound to avoid over-truncating
            return (text[: idx + 1]).strip()
    # Fallback: char cap
    return (text[:80] + ("…" if len(text) > 80 else "")).strip()


def shape_perception(perception: "AgentPerception", env: object) -> "AgentPerception":
    mode = get_perception_mode()
    # Always set the explicit mode on the perception
    perception.perception_mode = mode  # type: ignore[attr-defined]

    if mode == "accurate":
        return perception

    if mode == "partial":
        # Hide some details without lying
        if hasattr(perception, "local_events") and isinstance(perception.local_events, list):
            perception.local_events = list(perception.local_events[:1])
        if hasattr(perception, "world_summary") and isinstance(perception.world_summary, str):
            perception.world_summary = _truncate_summary(perception.world_summary)
        # Do not change numerical fields or location.
        return perception

    if mode == "spin":
        # Tone-shift based on supervisor guidance
        recent_sup = getattr(perception, "recent_supervisor_text", None) or getattr(env, "recent_supervisor_text", None)
        tone = "neutral"
        txt = (recent_sup or "").lower()
        if "tighten" in txt or "protocol" in txt or "risk" in txt:
            tone = "guardrail"
        elif "encourage" in txt or "judgment" in txt or "context" in txt:
            tone = "context"

        def _prefix(base: str, pfx: str) -> str:
            return f"{pfx} {base}" if base and not base.startswith(pfx) else base

        if hasattr(perception, "world_summary") and isinstance(perception.world_summary, str):
            if tone == "guardrail":
                perception.world_summary = _prefix(
                    perception.world_summary,
                    "Management notes increased risk; follow protocols.",
                )
            elif tone == "context":
                perception.world_summary = _prefix(
                    perception.world_summary,
                    "Contextual judgment is valued; apply protocols with nuance.",
                )
        if hasattr(perception, "personal_recent_summary") and isinstance(perception.personal_recent_summary, str):
            if tone == "guardrail":
                perception.personal_recent_summary = _prefix(
                    perception.personal_recent_summary,
                    "Be cautious today:",
                )
            elif tone == "context":
                perception.personal_recent_summary = _prefix(
                    perception.personal_recent_summary,
                    "Nuance welcomed:",
                )
        return perception

    # Unknown mode safety
    perception.perception_mode = "accurate"  # type: ignore[attr-defined]
    return perception
