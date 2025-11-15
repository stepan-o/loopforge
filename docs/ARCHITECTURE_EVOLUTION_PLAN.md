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

#### Phase 2 — Route All Decisions Through Seam

- All policies receive `AgentPerception`.
- Legacy action dicts produced via plan conversion.

#### Phase 3 — Traits + Decision Mode

- `mode: guardrail | context` added to `AgentActionPlan`.
- Traits like `guardrail_reliance`, `risk_aversion`, `obedience` included in perception.

### Canonical Roadmap (Phase 4–13)
#### Phase 4 — Step-Level Narrative Logging (JSONL)

- Introduce `ActionLogEntry` and `JsonlActionLogger`.
- Log: perception, plan, mode, narrative, raw_action.
- Simulation behavior unchanged.

#### Phase 5 — Daily Reflections & Trait Drift

- In `loopforge/reflection.py`, add:
  - day summaries
  - reflection generation
  - reflection tags (regretted_obedience, regretted_risk, etc.)
  - `apply_reflection_to_traits`
- Slow evolution of `guardrail_reliance`, `risk_aversion`, etc.

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

- Add perception modes (`accurate`, `partial`, `spin`).
- Allow distorted summaries, hidden incidents, contradictory Supervisor tone.
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

These notes highlight gaps between the Unified Plan and the current codebase. They are intentionally documented here rather than silently corrected, so future changes can be scoped and tracked. Date: 2025-11-15 01:19

1) Policy seam not yet baseline-wide
- Plan baseline (Phase 2) says all decisions should flow via the Perception → Policy → Plan seam.
- Current: `RobotAgent.decide(...)` delegates to `llm_stub.decide_robot_action(...)`, which builds a minimal `AgentPerception` internally. There is no dedicated `policy.py`; simulation does not pass an explicit `AgentPerception` to a policy interface yet.

2) `guardrail_reliance` not present in `Traits` or default perception snapshot
- Plan baseline (Phase 3) calls out traits including `guardrail_reliance` in perception.
- Current: `emotions.Traits` lacks `guardrail_reliance`; `narrative.build_agent_perception` therefore omits it unless injected manually.

3) Step-level JSONL logging not wired at decision points
- Plan Phase 4 requires each robot decision to emit an action log line.
- Current: `ActionLogEntry` and `JsonlActionLogger` exist, and helpers like `log_action_step(...)` are defined, but `llm_stub.decide_robot_action(...)` does not call them yet.

4) `run_one_day_with_supervisor(...)` orchestrator not present
- Plan Phase 7 mentions a helper that runs a day, builds Supervisor messages, sets them on the env, and logs them.
- Current: `day_runner.run_one_day(...)` exists; Supervisor message building/logging exist in their own modules, but the combined helper is not implemented here.

5) Defaults and naming are close but not identical to examples
- `AgentActionPlan.mode` currently defaults to "guardrail". The plan does not mandate a specific default; examples sometimes show "context". This is non-breaking but worth noting for tests and docs.

If you want these gaps addressed next, suggested non-breaking tasks are:
- Introduce a thin `policy.py` with `decide_action_plan(perception)` and route `llm_stub` through it. Update `agents.py`/`simulation.py` callsites to use the seam without altering external behavior.
- Add `guardrail_reliance` to `Traits` and include it in `build_agent_perception(...)`.
- Call `log_action_step(...)` inside `llm_stub.decide_robot_action(...)` after building the plan and action dict.
- Add `run_one_day_with_supervisor(...)` to `day_runner.py` that composes existing helpers.

