.PHONY: help uv-sync uv sync run migrate downgrade-base downgrade-one revision docker-up docker-down docker-logs compose run-all hooks-install cz-check cz-bump cz-commit untrack-egg test

# Simple Makefile to streamline common tasks for Loopforge City
# Uses uv for environment and dependency management.
# You can override variables on the command line, e.g.:
#   make revision NAME="add_new_field"

# Export all Make variables to subprocess environments so overrides like
#   SIM_STEPS=25 make docker-up
# correctly reach docker-compose
.EXPORT_ALL_VARIABLES:

UV := $(shell command -v uv 2>/dev/null || echo uv)
PY := $(UV) run python
ALEMBIC := $(UV) run alembic
# Auto-detect Compose CLI: prefer Docker Compose v2 plugin, fallback to legacy binary
DC := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || (command -v docker-compose >/dev/null 2>&1 && echo docker-compose || echo docker-compose))
CZ := $(UV) run cz
PRECOMMIT := $(UV) run pre-commit

help:
	@echo "Loopforge City - common commands"
	@echo "-------------------------------------------------------------"
	@echo "make uv-sync           - Sync/install dependencies with uv"
	@echo "make uv / make sync    - Aliases for uv-sync"
	@echo "make migrate           - Run Alembic upgrade head (use inside container typically)"
	@echo "make downgrade-one     - Alembic downgrade by one revision"
	@echo "make downgrade-base    - Alembic downgrade to base"
	@echo "make revision NAME=msg - Create a new Alembic revision with message"
	@echo "make run               - Run the simulation locally (NO DB, in-memory)"
	@echo "make run-nodb          - Alias to run (no DB)"
	@echo "make run-all           - Migrate then run simulation (local DB only; not typical)"
	@echo "make hooks-install     - Install commit-msg hook via pre-commit"
	@echo "make cz-check          - Check commit message in HEAD using Commitizen"
	@echo "make cz-commit         - Interactive commit via Commitizen"
	@echo "make cz-bump           - Bump version and tag via Commitizen"
	@echo "make untrack-egg       - Stop tracking egg-info directory"
	@echo "make docker-up         - Build and start app + db via docker-compose"
	@echo "make docker-down       - Stop and remove compose services"
	@echo "make docker-logs       - Tail logs from compose services"

uv-sync:
	$(UV) sync --extra dev

# Aliases
uv: uv-sync
sync: uv-sync

# No-DB quick local run alias
run-nodb: run

migrate:
	$(ALEMBIC) upgrade head

downgrade-one:
	$(ALEMBIC) downgrade -1

downgrade-base:
	$(ALEMBIC) downgrade base

# Usage: make revision NAME="add robots table"
revision:
	@if [ -z "$(NAME)" ]; then \
		echo "ERROR: Please provide NAME=\"message\""; \
		exit 1; \
	fi
	$(ALEMBIC) revision -m "$(NAME)"

run:
	$(PY) -m scripts.run_simulation --no-db --steps 10

run-all: migrate run

# Commit tooling
hooks-install:
	$(PRECOMMIT) install --hook-type commit-msg

cz-check:
	$(CZ) check --rev-range HEAD~1..HEAD || true

cz-commit:
	$(CZ) commit

cz-bump:
	$(CZ) bump --yes

# Utility to untrack egg-info if already committed
untrack-egg:
	git rm -r --cached loopforge_city.egg-info || true

# Docker Compose helpers (match README which uses docker-compose)

docker-up:
	$(DC) up --build -d

compose: docker-up

docker-down:
	$(DC) down -v

docker-logs:
	$(DC) logs -f --tail=200

# Tests
 test:
	$(UV) run pytest

# Dev cockpit: summarize one day from logs
run-day:
	$(UV) run loopforge-sim view-day

# Dev cockpit: summarize an episode from logs
run-episode:
	$(UV) run loopforge-sim view-episode

# Coverage run
.PHONY: test-cov
test-cov:
	$(UV) run pytest --cov=loopforge --cov-report=term-missing
