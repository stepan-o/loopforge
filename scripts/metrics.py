from __future__ import annotations

"""Tiny CLI wrapper for the metrics harness (optional).

Usage examples:
  uv run python -m scripts.metrics incidents --actions logs/loopforge_actions.jsonl
  uv run python -m scripts.metrics modes --actions logs/loopforge_actions.jsonl
  uv run python -m scripts.metrics pmods --reflections logs/reflections.jsonl
  uv run python -m scripts.metrics drift --actions logs/loopforge_actions.jsonl --reflections logs/reflections.jsonl

This script prints compact JSON to stdout. It has no side effects beyond reading
files and writing to stdout.
"""

import json
from pathlib import Path
from typing import Optional

import typer

from loopforge import metrics as m

app = typer.Typer(add_completion=False, help="Loopforge Metrics Harness")


@app.command()
def incidents(actions: str = typer.Option("logs/loopforge_actions.jsonl", "--actions", help="Path to action JSONL")):
    entries = m.read_action_logs(actions)
    res = m.compute_incident_rate(entries)
    print(json.dumps(res))


@app.command()
def modes(actions: str = typer.Option("logs/loopforge_actions.jsonl", "--actions", help="Path to action JSONL")):
    entries = m.read_action_logs(actions)
    res = m.compute_mode_distribution(entries)
    print(json.dumps(res))


@app.command(name="pmods")
def perception_modes(reflections: str = typer.Option("logs/reflections.jsonl", "--reflections", help="Path to reflection JSONL")):
    entries = m.read_reflection_logs(reflections)
    res = m.compute_perception_mode_distribution(entries)
    print(json.dumps(res))


@app.command()
def drift(
    actions: str = typer.Option("logs/loopforge_actions.jsonl", "--actions", help="Path to action JSONL"),
    reflections: str = typer.Option("logs/reflections.jsonl", "--reflections", help="Path to reflection JSONL"),
):
    a = m.read_action_logs(actions)
    r = m.read_reflection_logs(reflections)
    res = m.compute_belief_vs_truth_drift(a, r)
    print(json.dumps(res))


if __name__ == "__main__":  # pragma: no cover
    app()