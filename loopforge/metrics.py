from __future__ import annotations

"""Metrics harness (Phase 9 Lite).

Pure, deterministic, log-powered helpers for analyzing runs. This module does
not touch the DB and has no side effects other than reading JSONL files.

All readers are fail-soft: missing files yield empty lists; malformed lines are
skipped. All computations are pure.
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import json

from .types import ActionLogEntry, ReflectionLogEntry, AgentReflection
from .logging_utils import read_action_log_entries


# -----------------------------
# Log Readers (fail-soft, pure)
# -----------------------------

def _as_path(path: str | Path) -> Path:
    return Path(path) if not isinstance(path, Path) else path


def read_action_logs(path: str | Path) -> List[ActionLogEntry]:
    """Read action logs from a JSONL path into ActionLogEntry objects.

    Fail-soft: if the file is missing, return []. Malformed lines are skipped.
    """
    return read_action_log_entries(_as_path(path))


def read_reflection_logs(path: str | Path) -> List[ReflectionLogEntry]:
    """Read reflection logs (written by JsonlReflectionLogger) into objects.

    Each JSONL line is expected to have the shape produced by
    ReflectionLogEntry.to_dict():
      { agent_name, role, day_index, reflection: {...}, traits_after: {...},
        perception_mode, supervisor_perceived_intent, episode_index }

    Fail-soft: missing file → [], malformed lines are skipped.
    """
    p = _as_path(path)
    if not p.exists():
        return []
    out: List[ReflectionLogEntry] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    reflection_dict = data.get("reflection", {}) or {}
                    reflection = AgentReflection.from_dict(reflection_dict)
                    entry = ReflectionLogEntry(
                        agent_name=str(data.get("agent_name", "")),
                        role=str(data.get("role", "")),
                        day_index=data.get("day_index"),
                        reflection=reflection,
                        traits_after=dict(data.get("traits_after", {}) or {}),
                        perception_mode=data.get("perception_mode"),
                        supervisor_perceived_intent=data.get("supervisor_perceived_intent"),
                        episode_index=data.get("episode_index"),
                    )
                    out.append(entry)
                except Exception:
                    # skip malformed lines
                    continue
    except Exception:
        # return what we have
        return out
    return out


def read_supervisor_logs(path: str | Path) -> List[Dict[str, Any]]:
    """Read supervisor JSONL messages into plain dicts.

    Lines are written via SupervisorMessage.to_dict(); we return dictionaries
    to keep the reader loosely coupled.

    Fail-soft: missing file → [], malformed lines are skipped.
    """
    p = _as_path(path)
    if not p.exists():
        return []
    msgs: List[Dict[str, Any]] = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msgs.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return msgs
    return msgs


# ------------------
# Metrics (pure)
# ------------------

def _safe_div(n: float, d: float) -> float:
    return 0.0 if d == 0 else n / d


def compute_incident_rate(actions: Iterable[ActionLogEntry]) -> Dict[str, Any]:
    """Compute a simple incident rate from ActionLogEntry list.

    We count entries whose outcome (case-insensitive) equals "incident".
    If outcome is absent or different, it does not count as an incident.
    """
    total = 0
    incidents = 0
    for e in actions:
        total += 1
        outcome = (getattr(e, "outcome", None) or "").strip().lower()
        if outcome == "incident":
            incidents += 1
    return {
        "incident_rate": _safe_div(incidents, total),
        "total_steps": total,
        "incidents": incidents,
    }


def compute_mode_distribution(actions: Iterable[ActionLogEntry]) -> Dict[str, Any]:
    """Count action plan modes (guardrail/context) and return counts + distribution.
    """
    counts: Dict[str, int] = {}
    total = 0
    for e in actions:
        total += 1
        m = getattr(e, "mode", None) or "unknown"
        counts[m] = counts.get(m, 0) + 1
    dist = {k: _safe_div(v, total) for k, v in counts.items()}
    return {"counts": counts, "distribution": dist, "total": total}


def compute_perception_mode_distribution(reflections: Iterable[ReflectionLogEntry]) -> Dict[str, Any]:
    """Distribution over reflection.perception_mode (additive; None buckets allowed)."""
    counts: Dict[str, int] = {}
    total = 0
    for r in reflections:
        total += 1
        pm = getattr(r, "perception_mode", None) or "unknown"
        counts[pm] = counts.get(pm, 0) + 1
    dist = {k: _safe_div(v, total) for k, v in counts.items()}
    return {"counts": counts, "distribution": dist, "total": total}


def compute_supervisor_intent_distribution(reflections: Iterable[ReflectionLogEntry]) -> Dict[str, Any]:
    """Compute distributions of perceived vs. (if available) true intents.

    Current logs carry a compact perceived string on ReflectionLogEntry:
    - reflection.supervisor_perceived_intent: str | None

    True intent is not logged on reflections in v1; however, if nested
    reflection dict contains a tag like "supervisor_true_intent", we will
    count it under the "true" channel. Otherwise, true counts remain empty.
    """
    perceived_counts: Dict[str, int] = {}
    true_counts: Dict[str, int] = {}
    total = 0
    for r in reflections:
        total += 1
        perc = getattr(r, "supervisor_perceived_intent", None) or "unknown"
        perceived_counts[perc] = perceived_counts.get(perc, 0) + 1
        try:
            # Soft: look for a hint in nested reflection tags
            true_hint = None
            tags = getattr(r.reflection, "tags", {}) or {}
            # allowed keys we might upgrade to later
            for key in ("supervisor_true_intent", "supervisor_intent_true", "true_intent"):
                val = tags.get(key)
                if isinstance(val, str) and val:
                    true_hint = val
                    break
            if true_hint:
                true_counts[true_hint] = true_counts.get(true_hint, 0) + 1
        except Exception:
            pass
    perceived_dist = {k: _safe_div(v, total) for k, v in perceived_counts.items()}
    true_dist = {k: _safe_div(v, total) for k, v in true_counts.items()} if true_counts else {}
    return {
        "perceived": {"counts": perceived_counts, "distribution": perceived_dist, "total": total},
        "true": {"counts": true_counts, "distribution": true_dist, "total": total} if true_counts else {"counts": {}, "distribution": {}, "total": total},
    }


def compute_belief_vs_truth_drift(
    actions: Iterable[ActionLogEntry],
    reflections: Iterable[ReflectionLogEntry],
) -> Dict[str, Any]:
    """Estimate belief-vs-truth drift based on perception_mode only (v1).

    A "belief event" is counted when a reflection carries perception_mode != "accurate",
    or when an action's embedded perception dict has perception_mode != "accurate".
    This is not asserting ground-truth; it only marks non-accurate subjective regimes.
    """
    belief_events = 0
    total_events = 0

    # From reflections
    for r in reflections:
        total_events += 1
        pm = (getattr(r, "perception_mode", None) or "accurate").lower()
        if pm != "accurate":
            belief_events += 1

    # From actions (embedded perception dict)
    for a in actions:
        total_events += 1
        try:
            p = getattr(a, "perception", {}) or {}
            pm = (p.get("perception_mode") or "accurate").lower() if isinstance(p, dict) else "accurate"
            if pm != "accurate":
                belief_events += 1
        except Exception:
            # treat as accurate if unreadable
            pass

    return {
        "belief_events": belief_events,
        "total_events": total_events,
        "belief_rate": _safe_div(belief_events, total_events),
    }


# ------------------
# Episode/Day segmenters
# ------------------

def segment_by_episode(actions: Iterable[ActionLogEntry]) -> Dict[int, List[ActionLogEntry]]:
    """Partition actions by episode_index (None → -1)."""
    buckets: Dict[int, List[ActionLogEntry]] = {}
    for e in actions:
        key = getattr(e, "episode_index", None)
        key_i = -1 if key is None else int(key)
        buckets.setdefault(key_i, []).append(e)
    return buckets


def segment_by_day(actions: Iterable[ActionLogEntry]) -> Dict[int, List[ActionLogEntry]]:
    """Partition actions by day_index (None → -1)."""
    buckets: Dict[int, List[ActionLogEntry]] = {}
    for e in actions:
        key = getattr(e, "day_index", None)
        key_i = -1 if key is None else int(key)
        buckets.setdefault(key_i, []).append(e)
    return buckets
