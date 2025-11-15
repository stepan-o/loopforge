# Loopforge City

# LOOPFORGE LLM BUILDER PROMPT
(Read this before you touch anything, robot friend.)

For future LLM-based system architects and planners, start here:
- docs/LOOPFORGE_AGENT_PROMPT.md — the canonical system prompt/design brief that explains the philosophy, north star, and phased workflow expected in this repository. Read it before proposing changes.

A small, text-based multi-agent simulation scaffold. Three robots plus a Supervisor act over discrete steps; state persists to PostgreSQL via SQLAlchemy with Alembic migrations. The app is containerized and uses `uv` for Python env and dependency management.

---

## LLM-friendly project overview (what, where, why)

This repository is intentionally structured to be easy for both humans and LLMs to understand, extend, and test. The design separates concerns so you can safely modify one layer without breaking others.

Key ideas:
- Environment owns hard state and rules (facts, numbers, DB writes) — agents never mutate DB directly.
- Agents decide actions through a clear seam (Perception → ActionPlan). Today the plan is deterministic; later it can be LLM-driven without changing the simulation loop.
- Simulation orchestrates steps, applies rules, persists rows, and prints concise logs.

Primary modules and contracts:
- loopforge/simulation.py
  - run_simulation(num_steps=10, persist_to_db=None)
  - Drives each step: build agents from DB (or in-memory), call policies, update locations/battery, compute context, update emotions, evaluate triggers, persist ActionLog/Memory, derive EnvironmentEvent(s), invoke Supervisor.
  - Contract: Pure orchestrator; assumes policy functions follow a stable action dict schema.
- loopforge/agents.py
  - RobotAgent(name, role, location, battery_level, emotions, traits, triggers)
    - decide(step) -> dict  (delegates to llm_stub.decide_robot_action)
    - run_triggers(env) -> None
  - SupervisorAgent
    - decide(step, summary) -> dict (delegates to llm_stub.decide_supervisor_action)
  - Trigger(name, condition(agent, env), effect(agent, env))
  - Why: Encapsulates transient per-step agent state and behavioral hooks separate from persistence.
- loopforge/emotions.py
  - EmotionState + clamp; Traits + clamp
  - update_emotions(agent, last_action: dict, context: dict)
  - ORM sync helpers: emotion_from_robot, apply_emotion_to_robot, traits_from_robot, apply_traits_to_robot
  - Why: Keep affective/trait logic small, explicit, and testable; DB code stays elsewhere.
- loopforge/environment.py
  - LoopforgeEnvironment: rooms, step counter, events buffer, recent_supervisor_text; advance/drain/record methods
  - generate_environment_events(env, session) -> list[EnvironmentEvent]
  - Why: Derive world events from recent actions/stress deterministically; returns objects, simulation decides when to add/commit.
- loopforge/narrative.py
  - AgentPerception: what the agent “sees” (structured snapshot + short textual summaries)
  - AgentActionPlan: what the agent intends to do (intent/move_to/targets/riskiness + narrative)
  - build_agent_perception(agent, env, step)
  - Why: A clean seam for LLM prompts later without rewriting the loop; today used with deterministic planning.
- loopforge/llm_stub.py
  - decide_robot_action(...) and decide_supervisor_action(...): stable public API used by the simulation
  - Internally: builds Perception → creates an ActionPlan → adapts back to the legacy action dict schema; optional LLM path behind USE_LLM_POLICY with safe fallback
  - Why: Preserve old contracts while enabling narrative/LLM evolution.
- loopforge/models.py + loopforge/db.py
  - SQLAlchemy models (Robot, Memory, ActionLog, EnvironmentEvent) and DB utilities (Base, get_engine, session_scope)
  - Why: Single source of persistence truth; simulation orchestrates commit boundaries via session_scope.
- scripts/run_simulation.py (Typer CLI)
  - loopforge-sim entrypoint. Does not contain domain logic; resolves steps and persistence mode and calls run_simulation.

Data flow in a step (DB-backed):
1) Load Robot rows → build RobotAgent(s) using emotion/trait helpers.
2) For each agent: Perception → ActionPlan → action dict; simulation applies location/battery changes.
3) Compute context flags → update_emotions → run_triggers → persist updated emotions/traits to the same Robot row.
4) Write ActionLog + Memory (Memory.text embeds a short “Plan:” narrative for later analysis).
5) Drain buffered events; derive new events with generate_environment_events and add them.
6) Supervisor decides next action; action is logged; env.recent_supervisor_text is updated (used by triggers next step).

Testing philosophy:
- Unit tests cover config flags, LLM wrappers (mocked), perception/plan generation, emotion updates, triggers, and the deterministic event engine.
- Integration tests cover simulation in no‑DB mode and DB-backed mode using a temporary SQLite engine via monkeypatch (fast, offline, deterministic).

## Quickstart

Most local runs should be containerized (app + db). For a super-fast local smoke test without touching any database, use the no-DB mode.

### A) Local quick test (no DB)

This runs entirely in memory and prints step summaries to stdout; nothing is written to a database.

```bash
make uv-sync    # first time only, to install deps locally
make run        # runs 10 steps with --no-db
```

- You can change the number of steps with the CLI, e.g. `uv run loopforge-sim --no-db --steps 5` or by editing the Makefile target.
- This mode ignores any database settings and requires no Postgres running locally.

### B) Containers: app + db (recommended for normal runs)

Prereqs: Docker and docker-compose installed.

1) Build and start Postgres + app containers (detached):
```bash
make docker-up
```
This will:
- start a local PostgreSQL container (`db`)
- build the app image if needed
- run Alembic migrations automatically inside the app container
- start the simulation for `SIM_STEPS` (default: 10)

2) Stream logs from both services:
```bash
make docker-logs
```

3) Change the number of steps (override `SIM_STEPS` at launch):
```bash
SIM_STEPS=25 make docker-up
# re-run logs if needed:
make docker-logs
```

4) Stop and remove containers and volumes when done:
```bash
make docker-down
```

Notes:
- Base image: official uv image `ghcr.io/astral-sh/uv:python3.14-bookworm` (uv and Python preinstalled; smaller, faster, more reproducible builds).
- The container uses uv to create and manage a project-local virtual environment at `/app/.venv` during build (`uv sync --frozen`, honoring `uv.lock`).
- Migrations run automatically inside the app container before starting the simulation.
- No local `DATABASE_URL` needed for this flow; the compose file wires the app to the `db` service.
- The app inside the container uses `PERSIST_TO_DB=true` by default; local no-DB runs set `--no-db` automatically via the Makefile.
- You can adjust other env vars by prefixing the `make` call, e.g. `LOG_LEVEL=DEBUG make docker-up`.
- Compose command variants: if your system only has the v2 plugin (`docker compose`), either run those commands directly or override the Makefile variable once, e.g. `make DC="docker compose" docker-up`.

## Architecture overview

### Stack overview
- Runtime: Python 3.14 (container) using the official uv base image `ghcr.io/astral-sh/uv:python3.14-bookworm`.
- Dependency/env management: uv with a project-local virtualenv at `/app/.venv` inside the container; `uv.lock` ensures reproducible builds.
- Database: PostgreSQL 16 (container), accessed via SQLAlchemy 2.x ORM.
- Migrations: Alembic, auto-applied on container start (`alembic upgrade head`).
- CLI: Typer app exposed as `loopforge-sim`.
- Orchestration: Docker Compose (services `app` and `db`).

### Implementation layers and contracts

The project is intentionally layered and minimal. Most logic flows top→down:

1) CLI entrypoint (`scripts/run_simulation.py`)
   - Method: `main(steps: int | None, no_db: bool)` → parses CLI, resolves steps and persistence mode, calls `loopforge.simulation.run_simulation`.
   - Contract: Does not contain domain logic. It only selects mode and delegates.

2) Simulation loop (`loopforge/simulation.py`)
   - Method: `run_simulation(num_steps: int = 10, persist_to_db: bool | None = None)`
     - No-DB mode: builds in-memory `RobotAgent`s and runs a quick loop without touching the DB.
     - DB-backed mode: opens a SQLAlchemy session via `session_scope`, seeds robots if needed, and for each step:
       - Loads `Robot` rows, constructs `RobotAgent`s, runs decisions, updates world state (location, battery),
         computes context flags, updates emotions (`update_emotions`) and triggers (`agent.run_triggers`),
         persists state back to the corresponding `Robot` row, and writes `ActionLog` + `Memory` entries.
       - Buffers environment events (`env.record_event`), then calls `generate_environment_events` to derive
         events from recent actions/stress; adds them and commits.
     - Contracts:
       - Uses only public helpers from `agents.py`, `emotions.py`, `environment.py`.
       - ORM writes go through SQLAlchemy `Session` inside `session_scope()`.
       - Supervisor actions are logged to `ActionLog` with `actor_type="supervisor"` and also exposed to
         robot triggers via `env.recent_supervisor_text`.

3) Agents and triggers (`loopforge/agents.py`)
   - Classes:
     - `RobotAgent`: transient step-time representation with fields `name`, `role`, `location`, `battery_level`,
       `emotions: EmotionState`, `traits: Traits`, `triggers: list[Trigger]`.
       - Methods:
         - `decide(step) -> dict`: delegates to `llm_stub.decide_robot_action` (deterministic placeholder).
         - `run_triggers(env) -> None`: evaluates each `Trigger` after emotions update; guards against exceptions.
     - `SupervisorAgent`: minimal policy with `decide(step, summary) -> dict`, delegating to `llm_stub.decide_supervisor_action`.
     - `Trigger` (dataclass):
       - `name: str`
       - `condition(agent, env) -> bool`
       - `effect(agent, env) -> None`
   - Presets:
     - `default_traits_for(name) -> Traits`: initial trait profiles for Sprocket/Delta/Nova.
     - `default_triggers_for(name) -> list[Trigger]`:
       - Sprocket “Crash Mode”: fires when stress > 0.8 and recent supervisor message mentions "hurry"; lowers `risk_aversion` slightly and bumps stress.
       - Nova “Quiet Resentment”: fires when stress > 0.6 and satisfaction < 0.3; increases `blame_external`, reduces `obedience` slightly.
   - Contracts:
     - Trigger effects only mutate the agent’s emotions/traits; persistence is handled by the simulation layer via helpers.

4) Emotions and traits (`loopforge/emotions.py`)
   - Dataclasses:
     - `EmotionState`: `stress`, `curiosity`, `social_need`, `satisfaction`; `clamp()` keeps values within [0,1].
     - `Traits`: `risk_aversion`, `obedience`, `ambition`, `empathy`, `blame_external`; `clamp()` bounds values.
   - Functions:
     - `update_emotions(agent, last_action: dict, context: dict) -> None`:
       - Applies baseline drift each step (stress/social_need down slightly; curiosity up slightly).
       - Action-driven nudges: `work`, `recharge`, `talk`, `move`, `inspect`.
       - Context flags: `near_error` (stress+curiosity up), `isolated` (social_need up, satisfaction down slightly).
       - Clamps at the end.
     - ORM sync helpers:
       - `emotion_from_robot(robot) -> EmotionState`
       - `apply_emotion_to_robot(robot, emotions) -> None`
       - `traits_from_robot(robot) -> Traits`
       - `apply_traits_to_robot(robot, traits) -> None`
   - Contracts:
     - Stateless helpers; no direct DB access.
     - Update logic is small and deterministic, safe to call each step.

5) Environment and events (`loopforge/environment.py`)
   - Class: `LoopforgeEnvironment` with `rooms`, `step`, `events_buffer`, `recent_supervisor_text`.
     - Methods: `advance()`, `record_event(type, location, description)`, `drain_events()`.
   - Function: `generate_environment_events(env, session) -> list[EnvironmentEvent]`:
     - Heuristic: looks at Sprocket’s last action and stress, and recent errors at that location; with a small
       deterministic chance, emits an `Incident`. Also occasionally emits `MinorError` to keep the world lively.
   - Contracts:
     - Event derivation is side-effect free: returns new `EnvironmentEvent` objects without committing.
     - Simulation decides when to `session.add()` and commit.

6) Models and DB (`loopforge/models.py`, `loopforge/db.py`)
   - ORM models:
     - `Robot`: core state incl. `traits_json` and current emotions.
     - `Memory`: per-step text notes for robots.
     - `ActionLog`: actions for robots and supervisor (nullable `robot_id` for supervisor).
     - `EnvironmentEvent`: events derived from environment or heuristic engine.
   - DB utilities:
     - `Base` (DeclarativeBase), `get_engine()`, and `session_scope()` context manager.
   - Contracts:
     - All DB interactions in the simulation occur inside `session_scope()` to ensure commit/rollback safety.

7) Decision stubs (`loopforge/llm_stub.py`)
   - Functions:
     - `decide_robot_action(...) -> dict` : deterministic policy by role and step.
     - `decide_supervisor_action(step, summary) -> dict` : broadcasts every 4th step; coaches on “high stress”; otherwise inspects.
   - Contract: Pure function stubs suitable for replacement by real AI/LLM policy later.

### Data flow (DB-backed step)
1. Load `Robot` rows (excluding supervisor) → build `RobotAgent`s using `emotion_from_robot` / `traits_from_robot`.
2. Each agent decides an action → simulation updates location/battery.
3. Build context flags → `update_emotions(agent, last_action, context)` → `agent.run_triggers(env)`.
4. Persist back: `apply_emotion_to_robot` + `apply_traits_to_robot` on the same `Robot` row.
5. Append `ActionLog` and `Memory` rows for each agent.
6. Drain buffered env events; then call `generate_environment_events` and add those events.
7. Decide supervisor action; log it; expose text as `env.recent_supervisor_text` for next-step triggers.

---

## Configuration

Environment variables (container-first):
- `LOG_LEVEL` (default: `INFO`) – adjust verbosity (e.g., `LOG_LEVEL=DEBUG make docker-up`).
- `SIM_STEPS` (default: `10`) – number of simulation steps for the app container.
- `PERSIST_TO_DB` (default: `true` in containers) – controls DB persistence; local `make run` uses `--no-db` regardless.
- `ECHO_SQL` (default: `false`) – set to `true` to echo SQL statements from SQLAlchemy.
- `USE_LLM_POLICY` (default: `false`) – when `true` and an API key is provided, robot/supervisor decisions use an LLM instead of the deterministic stub.
- `LLM_MODEL_NAME` (default: `gpt-4.1-mini`) – model name passed to the OpenAI client.
- `OPENAI_API_KEY` (optional) – required only when `USE_LLM_POLICY=true`.

Notes:
- You do NOT need to set `DATABASE_URL` for container runs; compose wires the app to `db` internally.
- For local no-DB runs (`make run`), the database is not used at all.
- LLM usage is fully optional. By default, the simulation uses deterministic stub policies; set `USE_LLM_POLICY=true` and provide `OPENAI_API_KEY` to enable LLM-driven decisions.
- Advanced: if you intentionally run the app against a locally managed Postgres outside containers, see `CONTRIBUTING.md` for manual Alembic usage and supply `DATABASE_URL` yourself.

The app reads environment variables in `loopforge/config.py`.

## Testing & Coverage

- Run all tests locally:
  ```bash
  make uv-sync
  make test
  ```
- Run with coverage and see missing lines:
  ```bash
  make test-cov
  ```
- Run tests inside the container (optional):
  ```bash
  docker compose run --rm app uv run pytest -q
  ```

## Common tasks (Makefile)

```bash
make uv-sync       # uv sync --extra dev
make migrate       # alembic upgrade head
make run           # run the simulation locally (10 steps)
make run-all       # migrate then run
make revision NAME="message"   # create a new Alembic revision
make downgrade-one # alembic downgrade -1
make docker-up     # docker-compose up --build -d
make docker-logs   # tail logs
make docker-down   # docker-compose down -v
# commit tooling
git config commit.template .gitmessage
make hooks-install # install commit-msg hook (Commitizen check)
make cz-commit     # interactive commit
make cz-check      # check last commit message
make cz-bump       # bump version + tag
```

## Database & migrations

- Models live in `loopforge/models.py`.
- Alembic is configured in `alembic/` with an initial migration in `alembic/versions/0001_initial.py`.
- Typical workflow after changing models:
  ```bash
  # Using Makefile shortcuts
  make revision NAME="describe change"
  make migrate

  # Or raw uv commands (advanced/manual)
  uv run alembic revision --autogenerate -m "describe change"
  uv run alembic upgrade head
  ```

### Alembic versions

- `0001_initial`:
  - Creates base tables: `robots`, `memories`, `action_logs`, `environment_events`.
  - Sets initial server defaults for emotion columns (`stress=0.2`, `curiosity=0.5`, `social_need=0.5`, `satisfaction=0.5`).
- `0002_traits_and_defaults`:
  - Adds `robots.traits_json` to persist per-robot `Traits`.
  - Changes server default for `robots.social_need` from `0.5` → `0.3` (affects new inserts only; existing rows keep values).

Notes:
- Migrations are applied automatically inside the app container at startup (`alembic upgrade head`).
- If you add/modify ORM models, generate a new revision and apply it (see commands above). For deterministic container builds, commit the new migration into `alembic/versions/`.

## Development notes

- Decision stubs are in `loopforge/llm_stub.py`.
- Supervisor is represented as a `Robot` row for simpler logging.
- Emotions are simple placeholders in `loopforge/emotions.py`.
- Commit messages follow Conventional Commits; see `CONTRIBUTING.md` for details. A ready-to-use template is in `.gitmessage`, and commit hooks are configured via `.pre-commit-config.yaml`.

## Project layout

```
loopforge/
  config.py, db.py, models.py, emotions.py, memory_store.py,
  agents.py, environment.py, simulation.py, llm_stub.py
scripts/
  run_simulation.py
alembic/
  env.py, script.py.mako, versions/0001_initial.py
Dockerfile, docker-compose.yml, alembic.ini, pyproject.toml, README.md
```

## Troubleshooting

- uv not found in `make`: ensure `$HOME/.local/bin` is on PATH or run `PATH="$HOME/.local/bin:$PATH" make uv-sync`.
- Connection issues: verify `DATABASE_URL` and that Postgres is running (`docker ps` or `pg_isready`).
- psycopg URL scheme: use `postgresql+psycopg://...` (psycopg 3).


---

## Current capabilities (snapshot)
- Deterministic step-based simulation with three robots (Sprocket, Delta, Nova) and a Supervisor.
- Emotions and traits tracked per robot with simple update heuristics and clamped ranges.
- Triggers evaluated after emotions (e.g., Sprocket “Crash Mode”, Nova “Quiet Resentment”).
- Minimal event engine derives `Incident`/`MinorError` from recent actions and stress.
- Narrative layer (Phase 1): Environment builds `AgentPerception`; policy produces an `AgentActionPlan` with a short narrative; simulation persists the narrative into `Memory` ("Plan: ...").
- Optional LLM decision mode behind a feature flag with safe fallback to deterministic policies.
- Pytest suite covering config flags, LLM wrapper, narrative layer, emotions, triggers, event engine, and both simulation modes.

## LLM decision mode (optional)
The project runs deterministically by default. To let an LLM propose next actions (robots and supervisor) while keeping the same contracts and safe fallback:

Required env vars
- `USE_LLM_POLICY=true`
- `OPENAI_API_KEY=<your key>`
- optional: `LLM_MODEL_NAME` (default `gpt-4.1-mini`)

Local (no DB, just to see decisions change)
```bash
USE_LLM_POLICY=true OPENAI_API_KEY=sk-... uv run loopforge-sim --no-db --steps 5
```

Containers (DB-backed)
```bash
USE_LLM_POLICY=true OPENAI_API_KEY=sk-... make docker-up
make docker-logs
```
If the model response is invalid or the API is unavailable, the code automatically falls back to the deterministic stub for that decision.

## Where to add new behavior
- New triggers: `loopforge/agents.py` → extend `default_triggers_for(name)` or attach at runtime.
- New emotion/context rules: `loopforge/emotions.py` → adjust `update_emotions` or add helpers.
- New event heuristics: `loopforge/environment.py` → update `generate_environment_events` (keeps DB-agnostic behavior; return objects for the simulation to persist).
- Richer narrative prompts or parsing: `loopforge/narrative.py` and `loopforge/llm_stub.py` → expand `AgentPerception`/`AgentActionPlan` and the adapters without touching the loop.
- DB schema evolution: `loopforge/models.py` then create a migration via `make revision NAME="..."` and `make migrate`.

