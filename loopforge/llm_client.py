"""Minimal OpenAI chat client wrapper for Loopforge City.

This module is intentionally tiny and optional. If USE_LLM_POLICY is false or
no OPENAI_API_KEY is provided, all helpers return None and callers should fall
back to deterministic policies.
"""
from __future__ import annotations

from typing import List, Dict, Optional
import json
import logging
import os

from . import config as cfg
from .config import _bool_from_env as _bool_from_env

logger = logging.getLogger(__name__)

try:
    # Import is light; actual client created lazily only when needed
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - import errors simply disable LLM usage
    OpenAI = None  # type: ignore

_client: Optional["OpenAI"] = None


def get_client() -> Optional["OpenAI"]:
    """Return a cached OpenAI client if LLM usage is enabled and configured.

    Returns None when:
      - USE_LLM_POLICY is False, or
      - OPENAI_API_KEY is not set, or
      - openai package is not available.
    """
    global _client
    # Read flags dynamically from environment to make tests and runtime toggling reliable
    use_llm = _bool_from_env("USE_LLM_POLICY", default=False)
    api_key = os.getenv("OPENAI_API_KEY")
    if not use_llm:
        return None
    if not api_key:
        logger.debug("LLM policy enabled but OPENAI_API_KEY not set; falling back to stub")
        return None
    if OpenAI is None:
        logger.debug("openai package not available; falling back to stub")
        return None
    if _client is None:
        _client = OpenAI(api_key=api_key)
    return _client


def chat_json(system_prompt: str, messages: List[Dict[str, str]], schema_hint: str) -> Optional[dict]:
    """Call the LLM and parse a JSON object from the response content.

    Returns None if the client is unavailable or parsing fails.
    The `schema_hint` is included in the system instructions but not validated here.
    """
    client = get_client()
    if client is None:
        return None

    # Compact set of messages; keep temperature low for determinism.
    try:
        completion = client.chat.completions.create(
            model=cfg.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt + "\nSchema: " + schema_hint},
                *messages,
            ],
            temperature=0.2,
            max_tokens=256,
        )
    except Exception as e:  # network / auth / model errors
        logger.debug("LLM call failed: %s", e)
        return None

    content = (completion.choices[0].message.content or "").strip()
    try:
        return json.loads(content)
    except Exception:
        logger.debug("LLM content was not valid JSON; falling back. content=%r", content[:200])
        return None
