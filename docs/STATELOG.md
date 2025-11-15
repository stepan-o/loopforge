# STATELOG

A snapshot of the repository state at the time of recording. Useful for future LLM/human architects to quickly reorient.

- Timestamp (local): 2025-11-15 00:59
- HEAD: fbccfe4e0be04748c5e78dbba5be77c9ef3160a5

## Recent commits (top 5)
```
fbccfe4 docs(readme): add roadmap/status links; point to extended evolution plan (Phases 4–13) and StateLog
360f40e docs(statelog): update timestamp, HEAD, and recent commits
c6c1d10 docs: append 'Architecture Evolution Plan — Next 10 Phases (Phase 4–13)' to ARCHITECTURE_EVOLUTION_PLAN.md
2af345e docs(prompt): add implementation snapshot; clarify core type locations, AgentActionPlan fields, and policy seam (Perception→Plan→dict)
e016217 feat(supervisor): add SupervisorMessage and JSONL supervisor logger; build/set messages from daily reflections; surface messages in perception; add run_one_day_with_supervisor helper; tests for supervisor policy, mailbox→perception, and logger
```

## Test status
- Command: `make test`
- Result: 23 passed (no failures)
- Last run duration: ~0.6s
- Note: no new test run for this entry

## Key docs pointers
- LLM builder prompt: `docs/LOOPFORGE_AGENT_PROMPT.md` (read first)
- Evolution plan: `docs/ARCHITECTURE_EVOLUTION_PLAN.md` (10-phase roadmap)
- README: top section links to both; contains architecture overview and testing instructions

## Environment & tooling
- Base image: `ghcr.io/astral-sh/uv:python3.14-bookworm`
- Orchestration: Docker Compose (services `app`, `db`)
- Database: PostgreSQL 16 (container)
- Migrations: Alembic (auto-applied in container)
- Dev/test: `uv` with dev extras, pytest

## Next suggested steps (from plan)
- Phase 1/2: introduce `policy.py` seam; ensure Perception→Plan path used everywhere (no behavior change)
- Phase 4/5: add `mode` to `AgentActionPlan`, log `mode` and `narrative`

