# ARCHITECTURE_EVOLUTION_PLAN

This document guides future phases of Loopforge’s evolution. It starts with focused feedback on the current state, then outlines a 10‑phase plan. Treat this as a living roadmap: keep it updated as phases land.

---

## 1) Feedback for Junie (what’s missing right now)

Based on the manifesto and narrative layer intent:

### a) Narrative layer gaps
- AgentActionPlan.mode is missing (guardrail vs context)
  - The prompt treats guardrail vs context as central.
  - Add: `mode: Literal["guardrail", "context"] = "context"` to `AgentActionPlan`.
- Perception snapshot missing `guardrail_reliance`
  - Include a trait snapshot: `"guardrail_reliance": float(getattr(agent.traits, "guardrail_reliance", 0.5))` in `AgentPerception`.
- AgentReflection type should exist (even if unused yet)
  - Add now to `narrative.py` for future phases:
    ```text
    @dataclass
    class AgentReflection:
        summary_of_day: str
        self_assessment: str
        intended_changes: str
        tags: Dict[str, bool] = field(default_factory=dict)
    ```

### b) Architecture‑level gaps vs manifesto
- Missing a single policy seam
  - Introduce `loopforge/policy.py` that exposes the stable API:
    ```text
    def decide_robot_action_plan(perception: AgentPerception) -> AgentActionPlan
    def decide_supervisor_action_plan(perception: AgentPerception) -> AgentActionPlan
    ```
  - Have it delegate to `llm_stub` (or `llm_client` when enabled).
- Simulation likely not consistently using AgentPerception yet
  - The step should be:
    env + agent → AgentPerception → policy → AgentActionPlan → legacy action dict → env.
- Logging does not store `mode`/narrative yet
  - ActionLog should eventually include: `mode`, `narrative`, and optionally perceived risk.
- Emotions/traits don’t respond to `mode` and outcomes
  - Update logic should incorporate `mode` to shape trajectories (e.g., stress, obedience, risk_aversion, guardrail_reliance).

---

## 2) Ten‑phase evolution plan

### Phase 1 — Wire the narrative seam without changing behavior
Goal:
- Start using `AgentPerception`/`AgentActionPlan` in the live decision flow, keep external behavior/DB shape the same.

Changes:
- In `loopforge/narrative.py` ensure:
  - `AgentPerception`, `AgentActionPlan` (optionally with `mode`), `build_agent_perception(agent, env, step)` exist and are minimal.
- In `agents.py` or `simulation.py` (pick one owner):
  - For each decision step: build perception, call a stub plan from `llm_stub`, convert plan into the existing action dict, continue as before.
- In `llm_stub.py`:
  - Add `decide_robot_action_plan(perception)` and `decide_supervisor_action_plan(perception)` as thin wrappers around existing `decide_*` functions, returning an `AgentActionPlan` with `mode="context"` placeholder.

Tests:
- One short simulation step asserting that a perception is built and the action dict remains compatible.

---

### Phase 2 — Introduce policy.py as the single brain seam
Goal:
- Stop calling `llm_stub` directly from agents/simulation; use a single seam.

Changes:
- Create `loopforge/policy.py`:
  ```python
  from loopforge.narrative import AgentPerception, AgentActionPlan
  from loopforge import llm_stub

  def decide_robot_action_plan(perception: AgentPerception) -> AgentActionPlan:
      return llm_stub.decide_robot_action_plan(perception)

  def decide_supervisor_action_plan(perception: AgentPerception) -> AgentActionPlan:
      return llm_stub.decide_supervisor_action_plan(perception)
  ```
- Update call sites to import/use `policy.*` instead of `llm_stub.*`.

---

### Phase 3 — Make perception construction the single source of “what agents know”
Goal:
- Exactly one logic path turns env + agent → `AgentPerception`.

Changes:
- Centralize `build_agent_perception` usage in `simulation.py` (or a dedicated orchestrator).
- Ensure it uses: `env.rooms`, `env.events_buffer`, `env.recent_supervisor_text`, `agent.emotions`, `agent.traits`.

---

### Phase 4 — Add `mode` and `guardrail_reliance`
Goal:
- Tag every decision with `mode` and snapshot `guardrail_reliance` into perception.

Changes:
- `AgentActionPlan`: `mode: Literal["guardrail", "context"] = "context"`.
- `build_agent_perception`: include trait snapshot: `guardrail_reliance` (default .5 if missing).
- In `policy.decide_*`, set `mode` via a simple heuristic based on traits (temporary).

---

### Phase 5 — Log `mode` + `narrative` in DB
Goal:
- Action logs reflect how the agent decided, not just what it did.

Changes:
- `models.py`:
  - Extend `ActionLog` (or introduce a new table) with: `mode` (String), `narrative` (Text nullable), `perceived_risk` (Float nullable).
- `simulation.py`:
  - When logging, write `mode`, `narrative`, optional `perceived_risk` from the plan.
- Migration: add columns and indexes as needed.

---

### Phase 6 — Implement AgentReflection and basic day‑end reflections
Goal:
- At day end, agents produce narrative reflections; environment stores them.

Changes:
- `narrative.AgentReflection` (if not present yet).
- In `simulation.py`:
  - Define a "day" boundary.
  - At day end, call a deterministic helper to generate an `AgentReflection` per agent.
- `models.py`:
  - Either add a `Reflection` table or store reflections as `Memory` with `tags["type"] = "reflection"`.
- Migration: create a table or adjust `Memory` usage.

---

### Phase 7 — Add llm_client and config flag for LLM‑backed policy
Goal:
- Allow switching between stub and LLM via config.

Changes:
- `llm_client.py`: implement LLM‑backed `decide_*_action_plan` helpers.
- `config.py`: ensure `USE_LLM_POLICY`, `OPENAI_API_KEY`, `LLM_MODEL_NAME`.
- `policy.py`: if `USE_LLM_POLICY` true, use `llm_client`; else `llm_stub`.

Tests:
- Mocked LLM path; ensure deterministic fallback.

---

### Phase 8 — Make environment consequences depend on `mode`
Goal:
- Same action, different consequences depending on `mode`.

Changes:
- `environment.py`: use `plan.mode` in incident probability/severity and supervisor reactions.
- `emotions.py`: update emotions based on (outcome, mode): guardrail+failure vs context+failure vs context+success, etc.

---

### Phase 9 — Apply reflections to trait evolution
Goal:
- Close the loop from reflections → trait drift.

Changes:
- Helper:
  ```text
  def apply_reflection_to_traits(agent, reflection: AgentReflection) -> None:
      ...
  ```
- Use reflection tags to adjust: `guardrail_reliance`, `risk_aversion`, `obedience`, `blame_external`, etc.
- Call this at day end after generating reflections.

---

### Phase 10 — Introspection tools & scenarios
Goal:
- Make Loopforge usable as a lab: scenario knobs + simple analytics.

Changes:
- Add scenario config controlling: supervisor pressure style, base incident rates, initial traits.
- Add a script/notebook to:
  - query logs,
  - graph mode usage over time,
  - show trait evolution curves per agent.

---

## TL;DR Principles
From here on, every change should:
- Push decisions through: `AgentPerception → AgentActionPlan → env`.
- Make `mode` (guardrail vs context) explicit and analysable.
- Enrich logs and reflections so we can read real “stories” of failure modes.
- Leave clean seams (`policy`, `narrative`, `environment`) for future robots to evolve.


---

## Architecture Evolution Plan — Next 10 Phases (Phase 4–13)

This section describes the next 10 phases (Phase 4–Phase 13) of Loopforge’s architecture evolution. Phases 1–3 are considered baseline and already in place:

- Phase 1 (baseline) — Introduce AgentPerception, AgentActionPlan, AgentReflection in loopforge/types.py and re-export them from loopforge.
- Phase 2 (baseline) — Route all robot decisions through the seam: build_agent_perception(...) → AgentActionPlan → legacy action dict in loopforge/llm_stub.py, with tests asserting the dict shape is stable.
- Phase 3 (baseline) — Add mode: Literal["guardrail","context"] to AgentActionPlan, and traits like guardrail_reliance, risk_aversion, obedience on agents; have stub policy choose a mode based on traits.

The phases below assume this baseline and push the system toward richer narratives, reflections, and Supervisor dynamics.

### Phase 4 — Step-Level Narrative Logging (Perception + Plan + Mode)

Goal
Make every simulation step explainable after the fact by logging:

- what the agent saw (AgentPerception),
- what it intended (AgentActionPlan including mode),
- what actually got applied (legacy action dict).

Key Changes

- Define ActionLogEntry in loopforge/types.py with:
  - step, agent_name, role,
  - mode, intent, move_to, targets, riskiness, narrative,
  - optional outcome,
  - raw_action (legacy dict),
  - perception (dictified AgentPerception).
- Add JsonlActionLogger and log_action_step(...) in loopforge/logging_utils.py:
  - append one JSON object per step to logs/loopforge_actions.jsonl.
- In loopforge/llm_stub.py, after building perception, plan, and action_dict, call log_action_step(...) via a module-level logger.
  - The simulation still sees only the dict; behavior must not change.

Done Criteria

- ActionLogEntry round-trips to a dict with tests.
- JsonlActionLogger writes one well-formed JSON object per call.
- Every call to decide_robot_action(...) produces an action log line.
- No new keys appear in the public action dict; all tests still pass.

### Phase 5 — Daily Reflections & Tiny Trait Evolution

Goal
At the end of a “day” or episode, each agent produces a readable reflection and uses it to nudge their traits (especially guardrail_reliance and risk_aversion) in small, interpretable ways.

Key Changes

- In loopforge/reflection.py:
  - summarize_agent_day(agent_name, entries: list[ActionLogEntry]) -> dict
    - counts steps, guardrail vs context steps, incident count, etc.
  - build_agent_reflection(agent_name, role, summary) -> AgentReflection
    - generates:
      - summary_of_day
      - self_assessment (e.g. “I hid behind protocol and it still failed”)
      - intended_changes
      - tags such as:
        - regretted_obedience
        - regretted_risk
        - validated_context
  - apply_reflection_to_traits(agent, reflection)
    - nudges traits by small deltas (e.g. ±0.05) with clipping to [0,1]:
      - regretted_obedience → lower guardrail_reliance
      - regretted_risk → raise risk_aversion and guardrail_reliance
      - validated_context → slightly lower guardrail_reliance
  - run_daily_reflection_for_agent(agent, entries) -> AgentReflection
    - convenience wrapper that calls the three helpers above.

Done Criteria

- Unit tests cover:
  - summary counts,
  - reflection tags for different patterns,
  - trait updates and clipping,
  - end-to-end run_daily_reflection_for_agent.
- Simulation code is not yet calling reflections automatically; this remains opt-in.

### Phase 6 — Days, Reflection Logs & run_one_day Orchestrator

Goal
Introduce a minimal notion of a “day” as a range of steps, run reflections for that day, and log them separately from step logs.

Key Changes

- Add ReflectionLogEntry in loopforge/types.py:
  - agent_name, role, day_index,
  - reflection: AgentReflection,
  - traits_after: dict[str,float],
  - to_dict() for JSONL.
- Add JsonlReflectionLogger in loopforge/logging_utils.py, writing to logs/loopforge_reflections.jsonl.
- In loopforge/reflection.py:
  - filter_entries_for_day(entries, day_index, steps_per_day) -> list[ActionLogEntry].
  - run_daily_reflections_for_all_agents(agents, entries, logger, day_index) -> list[AgentReflection].
- New module loopforge/day_runner.py:
  - run_one_day(env, agents, steps_per_day=50, day_index=0, reflection_logger=None) -> list[AgentReflection]:
    - runs steps_per_day env steps,
    - reads ActionLogEntrys (from file or buffer),
    - filters to that day,
    - runs reflections for all agents,
    - logs them if reflection_logger provided.

Done Criteria

- A single CLI / test harness can:
  - run run_one_day(...),
  - produce both action logs and reflection logs,
  - confirm traits are updated for at least one agent.
- No change in step-by-step sim behavior; “days” are a thin orchestration layer.

### Phase 7 — Supervisor Messages & Perception Bias

Goal
Let a Supervisor read agents’ reflections, send per-agent messages, store them on the environment, log them, and have them appear as recent_supervisor_text in the next day’s AgentPerception.

Key Changes

- In loopforge/types.py:
  - Add SupervisorMessage dataclass with:
    - agent_name, role, day_index,
    - intent: Literal["tighten_guardrails","encourage_context","neutral_update"],
    - body: str,
    - tags: dict[str,bool],
    - to_dict().
- In loopforge/logging_utils.py:
  - Add JsonlSupervisorLogger writing SupervisorMessage to logs/loopforge_supervisor_messages.jsonl.
- New module loopforge/supervisor.py:
  - build_supervisor_messages_for_day(reflections, day_index) -> list[SupervisorMessage]
    - heuristics:
      - regretted_risk → guardrail-heavy warning.
      - regretted_obedience or validated_context → context-encouraging message.
      - otherwise → neutral or no message.
  - set_supervisor_messages_on_env(env, messages)
    - sets/updates env.supervisor_messages: dict[agent_name, SupervisorMessage].
- In loopforge/narrative.py:
  - build_agent_perception(...) reads from env.supervisor_messages and populates recent_supervisor_text with SupervisorMessage.body when available.
- In loopforge/day_runner.py:
  - Add run_one_day_with_supervisor(...):
    - calls run_one_day(...),
    - builds Supervisor messages,
    - sets them on env,
    - logs them with JsonlSupervisorLogger,
    - returns reflections.

Done Criteria

- Tests verify:
  - reflections with different tags lead to different Supervisor intents,
  - Supervisor messages show up in AgentPerception.recent_supervisor_text,
  - supervisor messages get logged correctly.
- Supervisor messages remain influence only; sim logic still doesn’t depend on them.

### Phase 8 — Truth vs Belief Drift (Biased Perceptions & Spin)

Goal
Make it possible to systematically diverge agent beliefs from world truth, and observe the effect on behavior and reflections.

Key Changes

- Introduce simple world-truth vs belief experiments:
  - Add configuration flags / experiment modes (e.g. "accurate", "incomplete", "misleading") that control how build_agent_perception(...) summarizes state.
  - Example manipulations:
    - Hide certain incidents from the agent.
    - Under- or over-state risk in world_summary.
    - Modify Supervisor messages to partially contradict the actual incidents.
- Tag log entries and reflections with which “perception regime” was used, so we can later slice:
  - "perception_mode": "accurate" | "partial" | "spin".
- Extend AgentReflection.tags with belief-related markers, e.g.:
  - felt_gaslit, blamed_self_for_system_failure, trusted_supervisor_despite_evidence.

Done Criteria

- At least one test or small scenario where:
  - world truth says: “systemic failure”,
  - Supervisor message blames an agent,
  - perception + reflection show the agent internalizing or rejecting the spin.
- No changes to DB yet; this is all at the perception + narrative level.

### Phase 9 — Incident & Metrics Pipeline (Ground Truth Tables)

Goal
Give Loopforge a ground-truth incident & metrics layer that is separate from agent narratives, so we can quantify:

- guardrail vs context outcomes,
- blame vs responsibility alignment,
- long-term effects of Supervisor styles.

Key Changes

- Introduce an incident/metrics module, e.g. loopforge/metrics.py or loopforge/incidents.py:
  - IncidentRecord dataclass:
    - who/what triggered it,
    - which mode they were in,
    - world-truth cause classification (e.g. operator_error, system_fault, bad_procedure, unknown),
    - severity, timestamp/step.
- As the environment detects incidents, it:
  - records an IncidentRecord (in memory and/or DB),
  - optionally tags the relevant ActionLogEntry via outcome="incident" and some incident_id.
- Add metrics helpers:
  - “Count incidents by (mode, severity)”,
  - “Compare incidents attributed to a given agent vs world-truth cause”.

Done Criteria

- You can run a short scenario and:
  - list incidents from the ground-truth incident table,
  - compare them to what agents think happened in their reflections.
- Tests cover basic incident recording and simple metric queries.

### Phase 10 — Episodes & Multi-Day Arcs

Goal
Structure simulations into episodes composed of multiple days, while preserving trait evolution and log continuity.

Key Changes

- Introduce a notion of episode index:
  - Add episode_index to ActionLogEntry, ReflectionLogEntry, and optionally SupervisorMessage.
- Add an episode-level runner:
  - e.g. run_episode(env, agents, num_days, steps_per_day, ...) in loopforge/day_runner.py:
    - loops over run_one_day_with_supervisor(...),
    - increments day_index,
    - preserves traits and relationships across days,
    - resets/adjusts environment state between days as necessary.
- Optionally add simple “episode reset policies”:
  - environment resets severe incidents,
  - but keeps some scars (e.g., persistent flags or degraded equipment).

Done Criteria

- A single CLI/test can:
  - run a multi-day episode,
  - show trait trajectories (e.g. guardrail_reliance over days),
  - show changes in Supervisor messaging style over the episode.
- Logs (actions, reflections, Supervisor) are clearly partitioned by episode_index and day_index.

### Phase 11 — Policy Variants & Experiment Harness

Goal
Support multiple policy implementations and an experiment harness so we can compare how different decision rules (stub, various LLM prompts, different risk profiles) behave under the same world conditions.

Key Changes

- Define a simple policy interface, even if thin wrappers:
  - e.g. RobotPolicy class with decide_action_plan(perception) -> AgentActionPlan.
- Implement at least 2–3 variants:
  - conservative guardrail-heavy stub,
  - risk-seeking context-heavy stub,
  - experimental LLM-backed policy (if/when you hook one in).
- Extend run_episode / day runner to accept a policy or a mapping from agent → policy.
- Tag logs with which policy was used for each action (e.g. policy_name in ActionLogEntry.meta).

Done Criteria

- You can run the same environment scenario with two different policies and later compare:
  - incident rates,
  - reflection patterns,
  - Supervisor messaging responses.
- Tests cover switching policies and tagging logs correctly.

### Phase 12 — Narrative & Metrics Viewer (Human-Facing Tooling)

Goal
Build a human-friendly viewing layer to explore logs as stories and metrics, so you can actually enjoy reading what these robots went through.

Key Changes

- Add a small analysis/visualization entrypoint, e.g. tools/ or scripts/:
  - view_actions.py: pretty-prints action logs for one agent (with mode).
  - view_reflections.py: shows reflection progression over days.
  - view_supervisor.py: shows how Supervisor tone/intents change over time.
- Optional lightweight HTML or TUI viewer:
  - Chronological view filtered by agent:
    - step → perception → plan (mode) → outcome → reflection → Supervisor message.
- Ensure these tools rely only on the JSONL logs and types, not on internal sim state.

Done Criteria

- Given a finished episode, a human can:
  - follow one agent’s arc through actions, reflections, and Supervisor messages,
  - see how traits changed,
  - see where guardrails helped or hurt.
- Tools are documented briefly in README or a docs/VIEWER.md.

### Phase 13 — DB-Backed World Truth & Reproducible Scenarios

Goal
Move world truth into a small DB-backed store so we can run reproducible experiments, replay scenarios, and do heavier offline analysis without bloating in-memory structures.

Key Changes

- Introduce a persistent store (probably SQLite) for:
  - world state snapshots (optional, light),
  - incident records,
  - high-level run metadata (episode ID, seeds, config).
- Add a minimal “scenario” concept:
  - scenario ID with:
    - initial world state configuration,
    - agent set and initial traits,
    - policy assignments,
    - key experiment flags (e.g. “spin supervisor messages”).
- Logging / runners store which scenario and seeds were used for each episode/day.

Done Criteria

- You can:
  - define a scenario,
  - run an episode,
  - persist incidents and metadata,
  - later regenerate the same run (or near-identical run) for comparison.
- DB layer remains simple and transparent; DB code does not bleed into agent policies (only environment & metrics).
