# ARCHITECTURE_EVOLUTION_PLAN

## 🎬 Context — The Producer North Star

For full creative intent, see the Producer Vision:
docs/PRODUCER_VISION.md

The architecture exists to support episode-level narrative and interpretable AI psychology. All phases should remain aligned with that North Star.

## LOOPFORGE — Unified Architecture Evolution Plan

This document describes the canonical roadmap for Loopforge’s architecture.
It merges all previous versions into one coherent plan based on the latest implementation and project philosophy.

Loopforge’s core pipeline:

```text
Environment (truth)
 → AgentPerception (subjective slice)
 → Policy (stub or LLM)
 → AgentActionPlan
 → Legacy action dict
 → Environment (truth updated)
```
Narrative, reflections, and Supervisor effects live above this seam.
World truth lives below it.

Baseline (Completed)
Phase 1 — Introduce Narrative Types
AgentPerception, AgentActionPlan, AgentReflection live in loopforge/types.py.

build_agent_perception introduced in loopforge/narrative.py.

Legacy behavior preserved.

Phase 2 — Route Decisions Through Seam (non-LLM path)
Non-LLM simulation path builds AgentPerception → calls decide_robot_action_plan(perception) → converts to legacy dict.

Legacy RobotAgent.decide(...) path remains for LLM mode and may bypass the seam (by design).

Note: This seam does not require a literal policy.py; adding one as an explicit seam is an implementation choice, not a hard requirement of this plan.

Phase 3 — Traits + Decision Mode
mode: "guardrail" | "context" added to AgentActionPlan.

Traits like guardrail_reliance, risk_aversion, obedience (and others) included in perception.

Traits live in loopforge/emotions.py (Traits dataclass) and round-trip via JSON on Robot rows.

Canonical Roadmap (Phase 4–13+)
Status Legend:

✅ Implemented

🌓 Implemented (opt-in / partial)

⏳ Planned

Phase 4 — Step-Level Narrative Logging (JSONL) — ✅ Implemented
Intent: Make every decision reconstructable as a story: perception → plan → raw action.

Introduced ActionLogEntry and JsonlActionLogger.

Non-LLM decision path logs one JSONL line per action via log_action_step(...).

Each entry includes:

- perception (serialized AgentPerception),
- plan-derived fields (intent, move_to, targets, riskiness, narrative),
- mode (guardrail vs context),
- narrative,
- raw_action (legacy dict),
- optional policy_name.

Simulation behavior unchanged; logging is fail-soft:

log I/O failures never crash the sim.

Log destination is injectable via:

- explicit run_simulation(..., action_log_path=...)
- ACTION_LOG_PATH env var
- default logs/loopforge_actions.jsonl.

Phase 5 — Daily Reflections & Trait Drift — 🌓 Implemented (opt-in)
Intent: Give agents a “day mind” that can evolve traits slowly.

loopforge/reflection.py provides:

- `summarize_agent_day(entries)`
- `build_agent_reflection(agent_name, role, summary) -> AgentReflection`
- `apply_reflection_to_traits(traits_or_agent, reflection)`
- helpers to run daily reflections for one or all agents.

Reflections can include tags like:

- `regretted_obedience`
- `regretted_risk`
- and others added over time.

Trait drift:

small, clamped nudges to traits such as guardrail_reliance, risk_aversion, obedience, etc.

Status:

Reflection logic and trait drift are implemented as a pure, opt-in layer.

Wiring into the day runner is available; use is controlled at the orchestrator level so behavior can be kept stable or turned on intentionally.

Phase 6 — Day Runner & Reflection Logs — ✅ Implemented
Intent: Turn steps into days, and days into logged reflections.

Added:

- ReflectionLogEntry and `JsonlReflectionLogger`.
- Day orchestration (`loopforge/day_runner.py`):
  - `run_one_day(...)`:
    - runs N steps via the simulation loop,
    - collects per-agent entries for that day,
    - runs reflections,
    - logs reflections via `JsonlReflectionLogger`,
    - applies trait drift (where enabled).
- Reflection logs:
  - JSONL stream containing `ReflectionLogEntry` (wraps `AgentReflection` plus metadata such as agent, role, day, episode, perception mode, supervisor-perceived intent, etc.).
  - Path injectable (e.g. via env/args, mirroring action logs).

Status:

Day runner + reflection logging is in place and used as the base for higher phases.

Phase 7 — Supervisor Messages & Bias Field — ✅ Implemented
Intent: Close the loop: reflections influence Supervisor behavior, which then shapes future perceptions and bias.

Core types:

SupervisorMessage in loopforge/types.py:

includes intent ("tighten_guardrails" | "encourage_context" | "neutral_update");
(perceived labels like "punitive"/"supportive" come from the Bias Snapshot, not from the message itself),

optional episode_index,

round-trips to/from dict.

JsonlSupervisorLogger for JSONL logging of Supervisor guidance.

Orchestration:

run_one_day_with_supervisor(...) in loopforge/day_runner.py:

wraps run_one_day(...),

reads reflections and/or aggregated state,

builds SupervisorMessage objects,

logs them via JsonlSupervisorLogger,

publishes messages onto the environment (e.g. env.supervisor_messages[agent.name]),

Supervisor text is surfaced in next day’s perceptions as recent_supervisor_text.

Bias field (Hinge addition):

SupervisorIntentSnapshot in loopforge/types.py.

loopforge/supervisor_bias.py:

infer_supervisor_intent(...) uses traits like blame_external, obedience, risk_aversion, and satisfaction to derive a per-agent perceived supervisor intent from SupervisorMessage.

AgentPerception.supervisor_intent:

snapshot attached after perception shaping.

Reflections:

record supervisor_perceived_intent at day end,

minimal tag (e.g. “punitive”) used for later analysis.

Reflection JSONL:

includes top-level supervisor_perceived_intent (additive field).

Status:

Supervisor messages, logging, and bias field are fully wired into the day runner and perceptions.

Phase 8 — Truth vs Belief Drift — ✅ Implemented (opt-in, configurable)
Intent: Explicitly model and tag the gap between world truth and agent belief at the perception level.

Perception modes:

AgentPerception.perception_mode: "accurate" | "partial" | "spin".

Config:

PERCEPTION_MODE added to loopforge/config.py with get_perception_mode():

validated,

safe fallback to "accurate".

Shaping layer:

loopforge/perception_shaping.py:

shape_perception(perception, env):

"accurate": no-op.

"partial": truncates/hides some details (e.g. fewer events, shorter summaries).

"spin": tone-shifts summaries based on Supervisor guidance / world context.

loopforge/narrative.py:

builds baseline AgentPerception,

then applies shape_perception(...) before returning.

Reflections:

Tag reflections with the perception_mode active that day.

ReflectionLogEntry and reflection JSONL include perception_mode at top level and inside nested reflection data.

Status:

Default is "accurate" → existing behavior unchanged.

"partial" / "spin" are opt-in modes that skew agent belief without touching world truth.

Phase 9 — Incident & Metrics Pipeline (Log-First) — 🌓 Partially Implemented
Original intent was twofold:

Incident logging tied to world truth (DB / environment events).

Metrics harness to compare truth vs belief vs mode.

Current state (log-first implementation):

9.1 Metrics Harness — ✅ Implemented
New module loopforge/metrics.py:

Fail-soft JSONL readers:

read_action_logs(path) -> list[ActionLogEntry]

read_reflection_logs(path) -> list[ReflectionLogEntry]

read_supervisor_logs(path) -> list[dict]

Pure metric helpers:

compute_incident_rate(actions)

compute_mode_distribution(actions)

compute_perception_mode_distribution(reflections)

compute_supervisor_intent_distribution(reflections)

compute_belief_vs_truth_drift(actions, reflections) (via perception_mode as a drift proxy)

Episode/day segmenters:

- segment_by_episode(actions)
- segment_by_day(actions)

CLI (optional) in scripts/metrics.py:

Tiny Typer app with commands like:

incidents

modes

pmods

drift

All functions are:

pure and deterministic,

log-only (no DB access),

safe to use offline.

9.2 Episode Weave & Tension Index — ✅ Implemented
Intent (Hinge bend): Turn raw metrics into a story spine per episode: how tense it felt, how much belief drift there was, and what the Supervisor “felt like” to the robots.

Core type (loopforge/types.py):

EpisodeTensionSnapshot with JSON round-trip:

episode_index: int

num_days: int

num_actions: int

num_reflections: int

incident_rate: float

belief_rate: float (drift proxy from perception modes)

guardrail_rate: float

context_rate: float

punitive_rate: float

supportive_rate: float

apathetic_rate: float

optional avg_stress: float | None

optional avg_satisfaction: float | None

tension_index: float in [0,1] — composite of the above

notes: str — short human-readable summary

Weave module (loopforge/weave.py):

compute_episode_tension_snapshot(episode_index, actions, reflections) -> EpisodeTensionSnapshot:

uses existing metrics helpers to derive rates,

clamps into [0,1],

constructs a brief natural-language notes string:

e.g. “High tension episode: frequent incidents and robots often perceived the Supervisor as punitive.”

compute_all_episode_snapshots(actions, reflections) -> list[EpisodeTensionSnapshot]:

9.3 Episode Indexing (Phase 10 Lite) — ✅ Implemented
Intent: add additive episode/day metadata for log analysis; keep simulation/DB unchanged.

- ActionLogEntry: episode_index: int | None, day_index: int | None (JSON numbers or null)
- ReflectionLogEntry: episode_index: int | None; day_index retained (Optional)
- SupervisorMessage: episode_index: int | None (optional)

Orchestrators (loopforge/day_runner.py):
- run_one_day(..., *, episode_index: int | None = None)
- run_one_day_with_supervisor(..., *, episode_index: int | None = None)
  - Threads indices into reflection and supervisor logs.
- run_episode(env, agents, num_days, steps_per_day, *, episode_index=0, action_log_path=None, reflection_log_path=None, supervisor_log_path=None)
  - Loops days and delegates to run_one_day_with_supervisor(...), tagging each day with (episode_index, day_index).

Behavior:
- Existing callers unchanged (indices default to None).
- JSONL formats remain append-only and deterministic; logging is fail-soft.

segments by episode using metrics segmenters,

computes snapshots per episode,

returns them sorted by episode_index.

Weave logger (loopforge/logging_utils.py):

JsonlWeaveLogger:

write_snapshot(snapshot: EpisodeTensionSnapshot) -> None:

appends one snapshot per line as JSONL,

fail-soft, matching logging philosophy.

Weave logs are separate from action/reflection/supervisor logs:

e.g. logs/loopforge_weave.jsonl.

Status:

Pure, deterministic, log-powered; no simulation or DB changes.

Episode-aware and perception-mode-aware via existing helpers.

Ready to be consumed by future viewers, notebooks, or scripts.

9.3 Incident DB & Truth Belts — ⏳ Planned
Still planned (not yet implemented):

Introduce explicit IncidentRecord model and DB-backed logging:

incidents table in DB,

link incidents to ActionLogEntry (via identifiers / timestamps).

Add metrics helpers to compare:

ground truth (incidents, environment events) vs agent beliefs (reflections, perception logs),

incident rates by mode, perception_mode, policy_name, etc.

Integrate with environment event engine for consistent, DB-backed truth.

Phase 10 — Multi-Day Episodes — 🌓 Implemented (Lite)
Intent: Make multi-day arcs a first-class, analyzable concept.

Log metadata:

ActionLogEntry:

optional episode_index: int | None

optional day_index: int | None

ReflectionLogEntry:

includes episode_index and optional day_index.

SupervisorMessage:

carries optional episode_index.

Orchestrators (loopforge/day_runner.py):

run_one_day(...):

accepts episode_index and forwards to reflection logging.

run_one_day_with_supervisor(...):

accepts episode_index,

threads it into reflection logging,

tags SupervisorMessage instances before logging.

run_episode(...):

orchestrates multi-day runs:

loops over day_index,

calls run_one_day_with_supervisor(...),

reuses loggers where provided,

keeps simulation semantics unchanged (no new world resets by default).

Status:

Episode/day indexing is fully wired into logs and orchestration.

Optional environment “scars” or partial resets between episodes are still planned (not yet implemented).

Phase 11 — Policy Variants & Experiment Harness — 🌓 Partially Implemented
Intent: Make policy experimentation first-class and comparable.

Plan:

Define a RobotPolicy base interface.

Implement multiple policies:

guardrail-heavy,

context-heavy,

experimental LLM-backed.

Tag each ActionLogEntry with policy_name.

Current state:

ActionLogEntry.policy_name exists and can carry policy identifiers.

The deterministic stub policy and optional LLM path exist, but a full experiment harness / explicit RobotPolicy implementations have not yet been formalized.

Next steps:

Introduce a small policy registry and explicit, typed policies.

Wire policy_name consistently through stub and LLM variants.

Add metrics helpers to compare policies via loopforge/metrics.py (and optionally cross-link with tension snapshots).

Phase 12 — Human-Facing Log Viewer — ⏳ Planned
Intent: Make logs readable as literature and dashboards.

Planned scripts:

view_actions.py

view_reflections.py

view_supervisor.py

optional: view_weave.py (episode tension & weave viewer).

Optional UI:

HTML or TUI viewer for:

step timelines,

per-agent arcs,

mode and perception overlays,

episodes and their tension_index from weave snapshots.

Current state:

No dedicated viewer yet.

Metrics CLI and weave snapshots are intended to be consumed here.

Phase 13 — DB-Backed World Truth + Scenarios — ⏳ Planned
Intent: Give world truth a durable, queryable spine and make scenarios reproducible.

Planned:

Add SQLite-backed (or Postgres-backed) storage for:

incidents,

scenario metadata,

seeds,

environment snapshots (optional).

Define scenario objects for reproducible runs:

scenario configs,

seeded initial conditions,

constraints for agents and Supervisor.

Connect DB truth with metrics and logs:

cross-check narratives against DB events,

analyze truth vs belief across runs and scenarios.

Historical Notes
Older design fragments and alternate roadmaps may remain in this repo.
If they are useful for lineage or inspiration, keep them — but clearly mark them as Historical (Superseded) to avoid confusion with this canonical plan.

Contradiction Notes (Current Implementation vs Plan)
These notes highlight gaps between the Unified Plan and the current codebase.
They are intentionally documented here rather than silently corrected, so future changes can be scoped and tracked.

Date: 2025-11-15 (Hinge revision 2 — post-weave)

Policy seam usage is partial (by design)

Plan baseline (Phase 2) prefers all decisions to flow via the Perception → Policy → Plan seam.

Current:

Main non-LLM path: simulation builds AgentPerception at the call site and calls decide_robot_action_plan(perception); actions go through AgentActionPlan and ActionLogEntry.

Legacy / LLM path: RobotAgent.decide(...) still exists and may bypass some logging/seam details. This is intentional to keep a stable escape hatch.

Reflections & trait drift are implemented but remain opt-in

reflection.py fully exists and day runner can invoke it.

Trait drift is small and clamped but can be disabled depending on orchestrator configuration.

The plan assumes eventual routine use; current code treats it as a controllable layer.

Phase 7: Supervisor orchestration & bias field slightly exceed the original text

Plan only required Supervisor messages and logging.

Current code also includes:

SupervisorIntentSnapshot,

supervisor bias inference based on traits,

perception and reflections annotated with perceived supervisor intent.

This is a strict extension of the original plan; nothing is removed, only enriched.

Phase 8: Perception modes now fully wired

Original plan treated perception modes as future additions.

Current implementation:

Provides PERCEPTION_MODE config,

shapes perceptions via shape_perception(...),

tags reflections with perception_mode.

This is now treated as Implemented (opt-in) rather than purely “future.”

Phase 9: Metrics harness & weave exist without DB incidents

Plan called for a combined Incident & Metrics pipeline.

Current:

Metrics harness (loopforge/metrics.py) and the episode weave (loopforge/weave.py + JsonlWeaveLogger) are implemented over logs only.

No dedicated IncidentRecord DB table or DB-level linking yet.

Status updated to:

Metrics & weave: ✅ Implemented (log-first).

DB-backed incident pipeline: ⏳ Planned.

Phase 10: Episodes implemented without “scars”

Plan suggested both episode indexing and optional partial resets (“scars”).

Current:

Episode and day indices are wired into logs and orchestrators (run_episode(...)).

No default environment resets or scar mechanics yet.

Plan text now reflects this as Phase 10 Lite; future work can add scars if desired.

Defaults

AgentActionPlan.mode defaults to "guardrail".

AgentPerception.perception_mode defaults to "accurate" via config.

EpisodeTensionSnapshot.tension_index is defined via a deterministic formula using incident, belief, guardrail, and punitive rates.

Metrics and weave-style consumers must remain aware of these defaults when interpreting logs.

Suggested non-breaking follow-ups:

Introduce explicit policy variants and a small experiment harness (Phase 11).

Add DB-backed incidents and scenario metadata (Phases 9.3 & 13).

Add a human-facing log viewer / weave viewer on top of metrics and tension snapshots (Phase 12).

If/when scars are implemented, update Phase 10 to describe how environment resets between episodes.

