# ARCHITECTURE_EVOLUTION_PLAN

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

### Baseline (Completed)
#### Phase 1 — Introduce Narrative Types

- `AgentPerception`, `AgentActionPlan`, `AgentReflection` live in `loopforge/types.py`.
- `build_agent_perception` introduced in `loopforge/narrative.py`.
- Legacy behavior preserved.

#### Phase 2 — Route Decisions Through Seam (non-LLM path)

- Non-LLM simulation path builds `AgentPerception` → calls `decide_robot_action_plan` → converts to legacy dict.
- Legacy `RobotAgent.decide(...)` path remains for LLM mode and may bypass the seam.
- Note: This seam does not require a literal `policy.py`; adding one as an explicit seam is an implementation choice, not a hard requirement of this plan.

#### Phase 3 — Traits + Decision Mode

- `mode: guardrail | context` added to `AgentActionPlan`.
- Traits like `guardrail_reliance`, `risk_aversion`, `obedience` included in perception.

### Canonical Roadmap (Phase 4–13)

Status Legend:
- Implemented
- Implemented (opt-in)
- Partially Implemented
- Planned
#### Phase 4 — Step-Level Narrative Logging (JSONL)

- Introduce `ActionLogEntry` and `JsonlActionLogger`.
- Log: perception, plan, mode, narrative, raw_action.
- Simulation behavior unchanged.
- Status: Implemented (2025-11-15): `ActionLogEntry` + `JsonlActionLogger` exist and the main non-LLM decision path logs one JSONL line per action via `log_action_step(...)`. Log destination is injectable via `ACTION_LOG_PATH` or `run_simulation(..., action_log_path=...)`. 

#### Phase 5 — Daily Reflections & Trait Drift

- In `loopforge/reflection.py`, add:
  - day summaries
  - reflection generation
  - reflection tags (regretted_obedience, regretted_risk, etc.)
  - `apply_reflection_to_traits`
- Slow evolution of `guardrail_reliance`, `risk_aversion`, etc.
- Status: Implemented (2025-11-15): Pure `reflection.py` module provides `summarize_agent_day`, `build_agent_reflection`, `apply_reflection_to_traits`, and `run_daily_reflection_for_agent`. This layer is opt-in and not yet wired to the main loop.

#### Phase 6 — Day Runner & Reflection Logs

- Add `ReflectionLogEntry` + `JsonlReflectionLogger`.
- Introduce `run_one_day(...)`:
  - runs N steps
  - collects entries
  - runs reflections
  - logs reflections
  - applies trait drift

#### Phase 7 — Supervisor Messages

- Add `SupervisorMessage` + `JsonlSupervisorLogger`.
- Supervisor reads reflections and sends messages (encourage context / tighten guardrails / neutral).
- Messages surface in next day’s perception (`recent_supervisor_text`).
- `run_one_day_with_supervisor(...)` orchestrates the loop.

#### Phase 8 — Truth vs Belief Drift

- Perception modes already exist (`perception_mode`: "accurate" | "partial" | "spin").
- Future phases will use these modes to distort perception, hide incidents, or alter summaries.
- Tag perceptions and reflections with `perception_mode`.

#### Phase 9 — Incident & Metrics Pipeline

- Introduce `IncidentRecord` and incident logging.
- Link incidents to `ActionLogEntry.outcome`.
- Add metrics helpers to compare:
  - ground truth vs agent beliefs
  - incident rates by mode

#### Phase 10 — Multi-Day Episodes

- Add `episode_index` to logs.
- `run_episode(...)` for multi-day runs.
- Optional “scars” or partial environment resets.

#### Phase 11 — Policy Variants & Experiment Harness

- Define `RobotPolicy` base interface.
- Implement multiple policies:
  - guardrail-heavy
  - context-heavy
  - experimental LLM-backed
- Tag each `ActionLogEntry` with `policy_name`.
- Status: Partially Implemented — `ActionLogEntry.policy_name` exists; multiple policy implementations and the experiment harness are not yet added.

#### Phase 12 — Human-Facing Log Viewer

- Add scripts:
  - `view_actions.py`
  - `view_reflections.py`
  - `view_supervisor.py`
- Optional HTML or TUI viewer.

#### Phase 13 — DB-Backed World Truth + Scenarios

- Add SQLite-backed:
  - incidents
  - scenario metadata
  - seeds
  - environment snapshots (optional)
- Define scenario objects for reproducible runs.

### Historical Notes

If older sections remain useful for lineage or inspiration, preserve them but mark them as Historical (Superseded) to avoid confusion with the canonical plan above.


## Contradiction Notes (current implementation vs plan)

These notes highlight gaps between the Unified Plan and the current codebase. They are intentionally documented here rather than silently corrected, so future changes can be scoped and tracked. Date: 2025-11-15 09:36

1) Policy seam usage is partial (by design)
- Plan baseline (Phase 2) prefers all decisions to flow via the Perception → Policy → Plan seam.
- Current: The main simulation path (when `USE_LLM_POLICY=False`) builds `AgentPerception` at the call site and calls `decide_robot_action_plan(perception)`; legacy `RobotAgent.decide(...)` remains for the LLM/legacy path. No dedicated `policy.py` is required by the plan.

2) Phase 3 and Phase 4 gaps resolved
- `guardrail_reliance` now exists on `Traits` and appears in `AgentPerception`.
- Step-level JSONL logging is wired in the simulation’s non‑LLM path via `log_action_step(...)` and is injectable via `ACTION_LOG_PATH`/`action_log_path`.

3) `run_one_day_with_supervisor(...)` orchestrator not present (Phase 7)
- `day_runner.run_one_day(...)` exists; Supervisor helpers exist; the combined orchestrator has not been added yet.

4) Perception modes added ahead of Phase 8
- `AgentPerception.perception_mode` exists and is currently always set to "accurate". Future phases may set it to "partial" or "spin".

5) Defaults
- `AgentActionPlan.mode` defaults to "guardrail". The plan doesn’t mandate a default; keep tests/docs aware of this.

Suggested non‑breaking follow‑ups:
- Add `run_one_day_with_supervisor(...)` to `day_runner.py`.
- Optionally, add an explicit `policy.py` seam for clarity (not required by the plan).

