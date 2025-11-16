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
from loopforge.logging_utils import read_action_log_entries
from loopforge.day_runner import run_one_day_with_supervisor, compute_day_summary
from loopforge.reporting import summarize_episode, EpisodeSummary, AgentEpisodeStats
from loopforge.types import ActionLogEntry
from pathlib import Path
from collections import Counter, defaultdict

app = typer.Typer(add_completion=False, help="Run the Loopforge City simulation loop")


# Allow invoking the module without an explicit subcommand, e.g.:
#   uv run python -m scripts.run_simulation --no-db --steps 10
# This preserves backward compatibility with the Makefile target `make run`.
@app.callback(invoke_without_command=True)
def _root(
    ctx: typer.Context,
    steps: int = typer.Option(None, "--steps", "-n", help="Number of simulation steps to run"),
    no_db: bool = typer.Option(False, "--no-db", help="Run without database persistence (in-memory test)"),
) -> None:
    if ctx.invoked_subcommand is None:
        # Defer to the main run command implementation
        main(steps=steps, no_db=no_db)


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


@app.command()
def view_day(
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    reflection_log_path: Path | None = typer.Option(None, help="Where to write reflections JSONL (optional)"),
    supervisor_log_path: Path | None = typer.Option(None, help="Where to write supervisor JSONL (optional)"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    day_index: int = typer.Option(0, help="Day index to summarize (0-based)"),
) -> None:
    """Summarize one day of Loopforge from JSONL logs.

    Reads action entries, builds a minimal env + agent stubs, runs the day runner
    with supervisor, and prints a compact report for devs.
    """
    entries: list[ActionLogEntry] = read_action_log_entries(action_log_path)
    if not entries:
        typer.echo(f"No action entries found at {action_log_path}")
        raise typer.Exit(code=0)

    # Build minimal env + agent stubs inferred from entries
    class _Env:
        def __init__(self) -> None:
            self.supervisor_messages = {}
    env = _Env()

    # Deduce agents (name, role)
    agent_roles: dict[str, str] = {}
    for e in entries:
        agent_roles.setdefault(e.agent_name, e.role)
    agents = [type("AgentStub", (), {"name": n, "role": r, "traits": {}})() for n, r in sorted(agent_roles.items())]

    # Run day orchestration (reads logs, not env)
    messages = run_one_day_with_supervisor(
        env=env,
        agents=agents,
        steps_per_day=steps_per_day,
        day_index=day_index,
        action_log_path=action_log_path,
        reflection_log_path=reflection_log_path,
        supervisor_log_path=supervisor_log_path,
    )

    # Slice entries for this day for stats
    start = day_index * steps_per_day
    end = (day_index + 1) * steps_per_day
    day_entries = [e for e in entries if start <= e.step < end]

    # Prepare aggregates
    by_agent: dict[str, list[ActionLogEntry]] = defaultdict(list)
    for e in day_entries:
        by_agent[e.agent_name].append(e)

    typer.echo(f"Day {day_index} — Summary")
    typer.echo("=" * 25)
    typer.echo("")

    for name in sorted(agent_roles.keys()):
        role = agent_roles[name]
        rows = by_agent.get(name, [])
        intents = Counter(e.intent for e in rows if e.intent)
        # Average emotions from perception snapshot if available
        stress_vals = []
        curiosity_vals = []
        satisfaction_vals = []
        for e in rows:
            emo = (e.perception or {}).get("emotions") or {}
            if isinstance(emo, dict):
                stress_vals.append(float(emo.get("stress", 0.0)))
                curiosity_vals.append(float(emo.get("curiosity", 0.0)))
                satisfaction_vals.append(float(emo.get("satisfaction", 0.0)))
        def _avg(vs: list[float]) -> float:
            return sum(vs) / len(vs) if vs else 0.0
        top3 = ", ".join(f"{k} ({v})" for k, v in intents.most_common(3)) or "(no intents)"
        typer.echo(f"{name} ({role})")
        typer.echo(f"- Intents: {top3}")
        typer.echo(
            f"- Emotions: stress={_avg(stress_vals):.2f}, curiosity={_avg(curiosity_vals):.2f}, satisfaction={_avg(satisfaction_vals):.2f}"
        )
        # Best-effort reflection summary: take the last narrative for the agent on that day
        summary_line = None
        for e in reversed(rows):
            if e.narrative:
                summary_line = e.narrative
                break
        typer.echo(f"- Reflection: \"{summary_line or '—'}\"")
        typer.echo("")

    typer.echo("Supervisor")
    sup_intents = ", ".join(f"\"{m.intent}\"" for m in messages) or "(none)"
    typer.echo(f"- Messages: {sup_intents}")


@app.command()
def view_episode(
    action_log_path: Path = typer.Option(Path("logs/loopforge_actions.jsonl"), help="Path to JSONL action log"),
    supervisor_log_path: Path | None = typer.Option(None, help="Path to supervisor JSONL (optional, unused for now)"),
    steps_per_day: int = typer.Option(50, help="Number of steps per simulated day"),
    days: int = typer.Option(3, help="Number of days to include in the episode"),
    narrative: bool = typer.Option(
        False,
        "--narrative",
        help="Print day-level narrative snippets in addition to numeric stats.",
    ),
) -> None:
    """Summarize a multi-day Loopforge episode from JSONL logs."""
    # Compute day summaries using the shared compute path
    day_summaries = []
    for day_index in range(days):
        ds = compute_day_summary(
            day_index=day_index,
            action_log_path=action_log_path,
            steps_per_day=steps_per_day,
        )
        day_summaries.append(ds)

    episode = summarize_episode(day_summaries)
    _print_episode_summary(episode)

    if narrative:
        from loopforge.narrative_viewer import build_day_narrative
        typer.echo("\nDAY NARRATIVES")
        typer.echo("==============================")
        for idx, day in enumerate(episode.days):
            prev = episode.days[idx - 1] if idx > 0 else None
            dn = build_day_narrative(day, idx, previous_day_summary=prev)
            _print_day_narrative(dn)


def _print_episode_summary(episode: EpisodeSummary) -> None:
    # Per-day blocks
    for d in episode.days:
        typer.echo(f"DAY {d.day_index} — perception={d.perception_mode}  tension={d.tension_score:.2f}")
        # Align agent names to improve readability
        if not d.agent_stats:
            typer.echo("  (no agent entries)")
            continue
        width = max(len(n) for n in d.agent_stats.keys())
        for name in sorted(d.agent_stats.keys()):
            s = d.agent_stats[name]
            typer.echo(
                f"  {name.ljust(width)}: guardrail={s.guardrail_count}, context={s.context_count}, avg_stress={s.avg_stress:.2f}"
            )
        typer.echo("")

    # Episode-level aggregates
    typer.echo("EPISODE SUMMARY")
    typer.echo("=" * 30)
    # Character sheets per agent
    typer.echo("\n=== CHARACTER SHEETS ===\n")
    # Determine width for agent names
    if episode.agents:
        width = max(len(n) for n in episode.agents.keys())
    else:
        width = 0
    for name in sorted(episode.agents.keys()):
        a = episode.agents[name]
        # Header
        typer.echo(f"{name}")
        typer.echo("-" * len(name))
        # Role + vibe
        if getattr(a, "vibe", ""):
            typer.echo(f"Role: {a.role} — {a.vibe}")
        else:
            typer.echo(f"Role: {a.role}")
        # Visual
        if getattr(a, "visual", ""):
            typer.echo(f"Visual: {a.visual}")
        # Tagline
        if getattr(a, "tagline", ""):
            typer.echo(f"Tagline: “{a.tagline}”")
        # Guardrail/context totals
        typer.echo(f"Guardrail vs context (episode): {a.guardrail_total} / {a.context_total}")
        # Stress arc
        if a.stress_start is not None and a.stress_end is not None:
            trend = "rising" if a.stress_end > a.stress_start else ("falling" if a.stress_end < a.stress_start else "flat")
            typer.echo(f"Stress arc: {a.stress_start:.2f} → {a.stress_end:.2f} ({trend})")
        else:
            typer.echo("Stress arc: n/a")
        # Traits placeholder/deltas
        if a.trait_deltas:
            deltas = ", ".join(f"{k}: {v:+.2f}" for k, v in a.trait_deltas.items())
            typer.echo(f"Traits: {deltas}")
        else:
            typer.echo("Traits: (deltas not tracked)")
        # Reflection quote snippet (first line)
        if a.representative_reflection and getattr(a.representative_reflection, "summary_of_day", ""):
            quote_full = a.representative_reflection.summary_of_day.strip()
            quote_one_line = quote_full.split("\n")[0]
            typer.echo(f"Reflection: “{quote_one_line}”")
        typer.echo("")

    # Tension trend and simple canaries
    trend_str = ", ".join(f"{v:.2f}" for v in episode.tension_trend)
    typer.echo(f"Tension trend: [{trend_str}]")

    # Oscillation detection: strictly increasing trend across days
    def _strictly_increasing(xs: list[float]) -> bool:
        return all(b > a for a, b in zip(xs, xs[1:])) if len(xs) >= 2 else False

    if _strictly_increasing(episode.tension_trend) and len(episode.tension_trend) >= 3:
        typer.echo("⚠ Tension increased every day this episode. Check for runaway feedback loops.")

    # Heavy guardrail skew warnings
    for name, a in episode.agents.items():
        total = a.guardrail_total + a.context_total
        if total >= 5 and a.guardrail_total >= 0.8 * total:
            typer.echo(f"⚠ {name} relied heavily on guardrails this episode ({a.guardrail_total} / {a.context_total}).")


if __name__ == "__main__":
    app()



def _print_day_narrative(dn):
    """Pretty-print a DayNarrative produced by narrative_viewer."""
    try:
        import typer as _ty
    except Exception:  # fail-soft; fallback to print
        _ty = None

    def _echo(s: str):
        if _ty is not None:
            _ty.echo(s)
        else:
            print(s)

    _echo(f"\nDay {dn.day_index} — {dn.day_intro}")
    for beat in dn.agent_beats:
        _echo(f"  [{beat.name} ({beat.role})]")
        _echo(f"    {beat.intro}")
        _echo(f"    {beat.perception_line}")
        _echo(f"    {beat.actions_line}")
        _echo(f"    {beat.closing_line}")
    if dn.supervisor_line:
        _echo(f"  Supervisor: {dn.supervisor_line}")
    if dn.day_outro:
        _echo(f"  {dn.day_outro}")
