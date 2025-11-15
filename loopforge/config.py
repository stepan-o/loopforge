"""Configuration utilities for Loopforge City.

Reads environment variables and exposes configuration values for the application.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


DEFAULT_DB_URL = "postgresql+psycopg://loopforge:loopforge@localhost:5432/loopforge"


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
