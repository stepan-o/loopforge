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
