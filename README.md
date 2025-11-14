# Loopforge City

A small, text-based multi-agent simulation scaffold. Three robots plus a Supervisor act over discrete steps; state persists to PostgreSQL via SQLAlchemy with Alembic migrations. The app is containerized and uses `uv` for Python env and dependency management.

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

## Configuration

Environment variables (container-first):
- `LOG_LEVEL` (default: `INFO`) – adjust verbosity (e.g., `LOG_LEVEL=DEBUG make docker-up`).
- `SIM_STEPS` (default: `10`) – number of simulation steps for the app container.
- `PERSIST_TO_DB` (default: `true` in containers) – controls DB persistence; local `make run` uses `--no-db` regardless.
- `ECHO_SQL` (default: `false`) – set to `true` to echo SQL statements from SQLAlchemy.

Notes:
- You do NOT need to set `DATABASE_URL` for container runs; compose wires the app to `db` internally.
- For local no-DB runs (`make run`), the database is not used at all.
- Advanced: if you intentionally run the app against a locally managed Postgres outside containers, see `CONTRIBUTING.md` for manual Alembic usage and supply `DATABASE_URL` yourself.

The app reads environment variables in `loopforge/config.py`.

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
