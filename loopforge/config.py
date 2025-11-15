"""Configuration utilities for Loopforge City.

Reads environment variables and exposes configuration values for the application.

Notes on policy + logging flags:
- USE_LLM_POLICY:
  When False (default), the simulation uses the stub policy path that
  builds an AgentPerception and writes JSONL step entries.
  When True, the simulation uses RobotAgent.decide() (legacy path).
  The JSONL step logger is not currently wired into that legacy path.
- ACTION_LOG_PATH:
  If set in the environment before this module is imported, it changes
  DEFAULT_ACTION_LOG_PATH. Tests can either set ACTION_LOG_PATH before
  import, or pass an explicit `action_log_path` to `run_simulation`.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_DB_URL = "postgresql+psycopg://loopforge:loopforge@localhost:5432/loopforge"
# Default path for JSONL action logs (can be overridden via env ACTION_LOG_PATH)
DEFAULT_ACTION_LOG_PATH = Path(os.getenv("ACTION_LOG_PATH", "logs/loopforge_actions.jsonl"))


def _bool_from_env(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


# LLM policy flags (module-level constants for easy import by decision layer)
USE_LLM_POLICY: bool = _bool_from_env("USE_LLM_POLICY", default=False)
LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4.1-mini")
OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables.

    Attributes:
        database_url: SQLAlchemy connection URL for PostgreSQL.
        echo_sql: Whether to echo SQL statements to stdout.
        log_level: Application log level string.
        simulate_steps: Default number of steps to run when not provided via CLI.
        persist_to_db: Whether the simulation should persist state to the database.
    """

    database_url: str = os.getenv("DATABASE_URL", DEFAULT_DB_URL)
    echo_sql: bool = os.getenv("ECHO_SQL", "false").lower() in {"1", "true", "yes", "on"}
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    simulate_steps: int = int(os.getenv("SIM_STEPS", "10"))
    persist_to_db: bool = os.getenv("PERSIST_TO_DB", "true").lower() in {"1", "true", "yes", "on"}


def get_settings() -> Settings:
    """Return a Settings instance using current environment variables."""
    return Settings()


def get_action_log_path() -> Path:
    """Return the effective JSONL action log path from env or default.

    Tests can set ACTION_LOG_PATH (even after import) to redirect logs
    for a given run, or pass `action_log_path` directly to `run_simulation`.
    """
    return Path(os.getenv("ACTION_LOG_PATH", "logs/loopforge_actions.jsonl"))
