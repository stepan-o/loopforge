from __future__ import annotations

"""Episode Weave (Sprint 6: Memory Cross-Weave & Episode Tension)

Pure, deterministic, log-powered utilities to compress actions + reflections
into an episode-level EpisodeTensionSnapshot. No DB or sim changes.
"""

from dataclasses import dataclass
from typing import Dict, List, Iterable, Optional, Tuple

from .types import ActionLogEntry, ReflectionLogEntry, EpisodeTensionSnapshot
from . import metrics


def _clamp_0_1(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


def _distinct_days(actions: Iterable[ActionLogEntry], reflections: Iterable[ReflectionLogEntry]) -> int:
    days = set()
    for a in actions or []:
        di = getattr(a, "day_index", None)
        if di is not None:
            days.add(int(di))
    for r in reflections or []:
        di = getattr(r, "day_index", None)
        if di is not None:
            days.add(int(di))
    return max(1, len(days) or 0)


def compute_episode_tension_snapshot(
    episode_index: int,
    actions: List[ActionLogEntry],
    reflections: List[ReflectionLogEntry],
) -> EpisodeTensionSnapshot:
    """Compute a single EpisodeTensionSnapshot from lists already filtered to an episode.

    Pure/deterministic aggregation using helpers in loopforge.metrics.
    """
    num_actions = len(actions)
    num_reflections = len(reflections)
    num_days = _distinct_days(actions, reflections)

    # Incident rate
    inc = metrics.compute_incident_rate(actions)
    incident_rate = float(inc.get("incident_rate", 0.0))

    # Mode distribution
    mode = metrics.compute_mode_distribution(actions).get("distribution", {})
    guardrail_rate = float(mode.get("guardrail", 0.0))
    context_rate = float(mode.get("context", 0.0))

    # Belief vs truth drift
    drift = metrics.compute_belief_vs_truth_drift(actions, reflections)
    belief_rate = float(drift.get("belief_rate", 0.0))

    # Supervisor perceived intent distribution (per reflections)
    sup = metrics.compute_supervisor_intent_distribution(reflections)
    perceived_dist = sup.get("perceived", {}).get("distribution", {})
    punitive_rate = float(perceived_dist.get("punitive", 0.0))
    supportive_rate = float(perceived_dist.get("supportive", 0.0)) or float(perceived_dist.get("empowering", 0.0))
    apathetic_rate = float(perceived_dist.get("apathetic", 0.0))

    # Emotional climate (v1: leave None; future may average numeric hints)
    avg_stress: Optional[float] = None
    avg_satisfaction: Optional[float] = None

    # Composite tension index (deterministic)
    tension_index = _clamp_0_1(
        0.4 * incident_rate +
        0.2 * belief_rate +
        0.2 * punitive_rate +
        0.2 * guardrail_rate
    )

    # Notes (short, deterministic)
    if incident_rate >= 0.5 and punitive_rate >= 0.3:
        notes = (
            "High tension episode: frequent incidents and robots often perceived the Supervisor as punitive."
        )
    elif belief_rate >= 0.5 and incident_rate < 0.2:
        notes = (
            "Belief drift episode: perceptions were heavily distorted despite low incident frequency."
        )
    else:
        notes = (
            "Relatively stable episode with moderate tension and low incident and belief drift rates."
        )

    return EpisodeTensionSnapshot(
        episode_index=int(episode_index),
        num_days=int(num_days),
        num_actions=int(num_actions),
        num_reflections=int(num_reflections),
        incident_rate=incident_rate,
        belief_rate=belief_rate,
        guardrail_rate=guardrail_rate,
        context_rate=context_rate,
        punitive_rate=punitive_rate,
        supportive_rate=supportive_rate,
        apathetic_rate=apathetic_rate,
        avg_stress=avg_stress,
        avg_satisfaction=avg_satisfaction,
        tension_index=tension_index,
        notes=notes,
    )


def _episodes_present(actions: Iterable[ActionLogEntry], reflections: Iterable[ReflectionLogEntry]) -> List[int]:
    eps = set()
    for a in actions or []:
        ei = getattr(a, "episode_index", None)
        if ei is not None:
            eps.add(int(ei))
    for r in reflections or []:
        ei = getattr(r, "episode_index", None)
        if ei is not None:
            eps.add(int(ei))
    return sorted(eps)


def compute_all_episode_snapshots(
    actions: List[ActionLogEntry],
    reflections: List[ReflectionLogEntry],
) -> List[EpisodeTensionSnapshot]:
    """Compute snapshots for each episode present across actions/reflections."""
    # Segment actions by episode using metrics helper
    actions_by_ep = metrics.segment_by_episode(actions)
    # Build reflections by episode locally (ReflectionLogEntry carries episode_index)
    refs_by_ep: Dict[int, List[ReflectionLogEntry]] = {}
    for r in reflections:
        ei = getattr(r, "episode_index", None)
        if ei is None:
            continue
        refs_by_ep.setdefault(int(ei), []).append(r)

    episodes = _episodes_present(actions, reflections)
    snapshots: List[EpisodeTensionSnapshot] = []
    for ep in episodes:
        a_list = actions_by_ep.get(ep, [])
        r_list = refs_by_ep.get(ep, [])
        snapshots.append(
            compute_episode_tension_snapshot(ep, a_list, r_list)
        )
    return sorted(snapshots, key=lambda s: s.episode_index)
