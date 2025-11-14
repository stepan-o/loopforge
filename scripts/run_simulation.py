"""CLI entrypoint for Loopforge City simulation.

Usage (uv):
  uv run python -m scripts.run_simulation --steps 10

Or via installed script:
  loopforge-sim --steps 10
"""
from __future__ import annotations

import sys
import typer

from loopforge.simulation import run_simulation
from loopforge.config import get_settings

app = typer.Typer(add_completion=False, help="Run the Loopforge City simulation loop")


@app.command()
def main(
    steps: int = typer.Option(None, "--steps", "-n", help="Number of simulation steps to run"),
    no_db: bool = typer.Option(False, "--no-db", help="Run without database persistence (in-memory test)"),
) -> None:
    settings = get_settings()
    num_steps = steps if steps is not None else settings.simulate_steps
    persist = settings.persist_to_db and not no_db
    mode = "no-DB (in-memory)" if not persist else "DB-backed"
    typer.echo(f"Starting Loopforge City simulation for {num_steps} steps ({mode})...")
    run_simulation(num_steps=num_steps, persist_to_db=persist)


if __name__ == "__main__":
    app()
