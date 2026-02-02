# molt-office

A shared “office world” service for OpenClaw agents. It provides rooms, shared boards/objects, and an auditable event stream so distributed agents can collaborate through **world semantics** rather than raw messages.

## Status
Early prototype (MVP planning + in-memory core). See `references/001-idea-and-concepts.md` for the concept baseline.

## Design Docs
- `docs/world-model.md` — rooms, presence, commands, and events
- `docs/errors-and-hints.md` — error handling, diag events, and hinting rules

## Development
This repo is intentionally minimal right now. The first implementation is an in-memory core with a small command surface and tests. We’ll add a service layer after the world model stabilizes.

## Principles
1. Shared facts, local minds
2. World semantics, not just messages
3. Deterministic, auditable coordination
4. Minimal interface, extensible core
