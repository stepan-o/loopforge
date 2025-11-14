# Contributing to Loopforge City

Thanks for contributing! This project uses Conventional Commits and lightweight tooling to keep history clean and automatable.

## Commit messages

Follow the Conventional Commits spec:
- Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`
- Optional scope: `feat(simulation)`, `build(docker)`, `db(alembic)`, `chore(make)`
- Subject: imperative mood, lower case, no trailing period

Example:
```
feat(simulation): add basic error event on every 7th step

Include context in the body when helpful.
```

## Local environment

- Install dependencies (including dev tools):
  ```bash
  make uv-sync
  ```
- Use the commit template:
  ```bash
  git config commit.template .gitmessage
  ```
- Install the commit-msg hook (checks message format):
  ```bash
  make hooks-install
  ```
- Optional helper commands:
  ```bash
  make cz-commit   # interactive commit prompt (Commitizen)
  make cz-check    # check format for the last commit
  make cz-bump     # bump version and tag (uses Commitizen config)
  ```

## Running the app and migrations

- Local quick test (no DB):
  ```bash
  make uv-sync
  make run  # runs in-memory, prints step summaries
  ```
- Containerized app + db (recommended):
  ```bash
  make docker-up
  make docker-logs  # Ctrl+C to exit logs; containers keep running
  ```
  Migrations run automatically inside the app container before the simulation.
- If you intentionally manage a local Postgres for development, you can run Alembic manually:
  ```bash
  uv run alembic upgrade head
  ```
  But typical development should avoid a local Postgres; prefer the containerized flow above.

## Housekeeping

- Local virtual environments and caches are ignored via `.gitignore`.
- If `loopforge_city.egg-info/` was accidentally committed previously, run:
  ```bash
  make untrack-egg
  ```

## Code style

- Keep code idiomatic and consistent with the surrounding module.
- Prefer small, focused commits with clear messages.
