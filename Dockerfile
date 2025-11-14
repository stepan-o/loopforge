# Dockerfile for Loopforge City app using uv base image
FROM ghcr.io/astral-sh/uv:python3.14-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    VIRTUAL_ENV=/app/.venv \
    PATH="/app/.venv/bin:${PATH}"

WORKDIR /app

# Copy project metadata first for better caching (including lockfile)
COPY pyproject.toml README.md alembic.ini uv.lock /app/
# Copy source code and alembic scripts
COPY loopforge /app/loopforge
COPY scripts /app/scripts
COPY alembic /app/alembic

# Sync/install dependencies into a local venv managed by uv
RUN uv sync --frozen

ENV DATABASE_URL="postgresql+psycopg://loopforge:loopforge@db:5432/loopforge"

# Default command: run migrations then simulation
CMD ["sh", "-lc", "uv run alembic upgrade head && uv run loopforge-sim"]
