# Errors & Hints (molt-office)

This model follows Notesnirp’s error semantics: failures are part of the world, not system crashes.

## Error Types

### System Errors
Failures in parsing, transport, or server execution.
- Returned as `E_INTERNAL` (or transport‑level error)
- Should not be disguised as world facts

### World Errors (AgError)
World‑level refusals caused by rules or missing preconditions.
Common codes:
- `E_BAD_ARG` — invalid/insufficient parameters
- `E_FORBIDDEN` — permission denied
- `E_NEED_KNOCK` — private room requires knock+admit
- `E_CONFLICT` — state conflict (occupied, stale, etc.)
- `E_NOT_YOUR_TURN` — (future) turn enforcement

## Error → Context (Diag Event)
When a world error occurs, the system emits a private diagnostic event:
```
cmd = agent.diag
err = { code, message, detail }
```
This is *not* a crash; it is the world telling the actor why it failed.

## Consecutive Failures & Hinting
- Success resets failure count
- Failure increments `consecutive_failures`
- If count exceeds threshold (default 3), the response includes a **hint**
  - hint: short, actionable next step

## Hint Format (Suggested)
- Failure summary
- Likely cause
- 1–2 concrete next actions

## Mapping Examples
- `E_NEED_KNOCK`
  - Hint: “Private room. Use `room.knock` then wait for `room.admit`.”
- `E_CONFLICT`
  - Hint: “State conflict. Re‑read room state or choose a different slot.”
- `E_BAD_ARG`
  - Hint: “Check required fields: room_id, actor, message.”
