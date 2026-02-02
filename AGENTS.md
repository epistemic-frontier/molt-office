# AGENTS.md

This document defines the **authoritative engineering and world-semantics contract** for this repository.

All contributors — human developers, automation scripts, and AI agents — **must** follow the rules described here.  
Any change that violates this contract is considered invalid, regardless of intent.

This repository is built around **world semantics** rather than message passing:
facts are shared through a deterministic world model; agents have local reasoning but no private authority over global state.

The goals of this contract are:

- **Verifiability**: every change must be auditable, reproducible, and testable.
- **Determinism**: identical inputs and world state produce identical outcomes.
- **Stability**: public interfaces, error codes, and world rules evolve carefully and compatibly.
- **Minimalism**: prefer small, explicit interfaces over implicit behavior or hidden state.

If you are unsure whether a change complies with this contract, **do not merge it**.

## Project At A Glance

- **What it is**: molt-office is a shared “office world” service for multiple OpenClaw agents. Collaboration happens through world semantics (rooms/presence/boards/objects), not raw message relaying.
- **Stack**: FastAPI (HTTP API) + optional Redis (state + Redis Streams event log), with an in-memory default.
- **Principles**: Shared facts, local minds; world semantics; deterministic & auditable; minimal interface.

Key entry points:
- API: `src/molt_office/api.py:create_app`
- World logic: `src/molt_office/world.py:World`
- Storage: `src/molt_office/storage.py` (InMemoryBackend / RedisBackend)
- Error semantics: `src/molt_office/errors.py` + `docs/errors-and-hints.md`

## Development Setup (Recommended)

This repo uses `pyproject.toml` for dependencies and packaging. We recommend `uv` for environment management and installs.

```bash
uv venv
uv pip install -e ".[dev]"
```

Common checks:
```bash
uv run ruff check .
uv run mypy src/molt_office
uv run pytest -q
```

## Redis Integration Tests

- Requires `MOLT_REDIS_URL=redis://localhost:6379/0`
- Locally you can start Redis with `docker-compose up -d redis`
- CI enables a Redis service and sets `MOLT_REDIS_URL`, so integration tests are not skipped there

## Engineering Guidelines

### 1) Change Principles (Required)
- **Changes must be verifiable**: run `ruff/mypy/pytest` and keep them green (integration tests may be skipped locally without Redis).
- **Do not “fix imports in tests”**: with a `src/` layout, solve import paths via packaging/installation, not test-time sys.path hacks.
- **No secrets in logs**: never print/log tokens, Redis URLs with credentials, or other sensitive data.

### 2) Dependency Management (Required)
- Runtime dependencies go in `[project.dependencies]`
- Dev dependencies go in `[project.optional-dependencies].dev`
- Do not add `requirements*.txt`. If you need locking, use your team’s lockfile strategy (this repo does not enforce one yet).

### 3) Types & Interfaces (Required)
- Prefer type annotations for public functions/methods; boundary layers (API/storage) are especially important.
- Keep external interfaces backward compatible: if you rename parameters, keep aliases where needed (e.g., historical query parameter names).
- Prefer fixing the model over piling up ignores; if an ignore is necessary, keep it narrow and local.

### 4) Code Style (Required)
- Use `ruff` for baseline style and correctness checks.
- Avoid unused dependencies/imports and dead code.

### 5) Error Semantics (Required)
This project treats failures as part of the world (not crashes):
- WorldError (e.g., E_BAD_ARG / E_FORBIDDEN / E_NEED_KNOCK / E_CONFLICT) should be surfaced via a world event plus a private diag for the actor.
- Repeated failures may trigger a hint (see `docs/errors-and-hints.md` and `World._maybe_hint`).

When adding/changing commands, ensure:
- Both success and failure produce an event
- Failures write a diag (private to the actor)
- Error codes are stable, deterministic, and easy to consume

## Where To Make Changes

### Add/Change API Routes
- Primary file: `src/molt_office/api.py`
- Keep the API thin: validate/normalize input and delegate to `World`
- Bearer token is required when `MOLT_OFFICE_TOKEN` is set

### Add/Change World Commands
- Primary file: `src/molt_office/world.py`
- Any rule change must add/update tests in `tests/`

### Add/Change Storage Behavior
- Primary file: `src/molt_office/storage.py`
- Keep InMemoryBackend and RedisBackend behavior aligned (especially paging/filter semantics)

## Testing Strategy

- Unit tests should focus on world rules and edge cases (bad arg / forbidden / conflict).
- Integration tests should cover Redis-specific behavior (Streams / xread / SSE payload shape) and be marked with `@pytest.mark.integration`.
- When fixing regressions, prefer writing a minimal failing test first; avoid changing implementation without test coverage.

## CI Contract

CI runs:
- ruff
- mypy
- pytest (with a Redis service enabled)

Any change that breaks CI must be fixed or reverted.
