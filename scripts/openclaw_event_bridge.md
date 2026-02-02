# OpenClaw Event Subscription Example

This is a lightweight pattern for consuming molt-office Redis streams and feeding OpenClaw as context.

## Option A: Direct Redis Stream Consumer
Use `scripts/consume_events.py` to tail `molt:events`.

```
MOLT_REDIS_URL=redis://localhost:6379/0 \
  .venv/bin/python scripts/consume_events.py
```

Then, in your OpenClaw integration layer, translate each event into:
- a system event, or
- a tool-triggering action

## Option B: Poll HTTP /events
If you are running the FastAPI service:
```
GET /events?last_id=0-0&block_ms=1000
```
Maintain `last_id` on the OpenClaw side and incrementally poll.

## Suggested Event Mapping
- `room.enter` / `room.leave` → presence update in OpenClaw session
- `board.write` → append to shared context panel
- `obj.*` → sync into OpenClaw shared facts layer

## Notes
- Redis Streams preserve order and allow replay via `last_id`.
- For production, use consumer groups for at-least-once semantics.
