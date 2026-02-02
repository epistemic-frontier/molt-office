import json
import os
import time
from typing import Dict, Any

import redis


REDIS_URL = os.getenv("MOLT_REDIS_URL", "redis://localhost:6379/0")
STREAM_KEY = os.getenv("MOLT_EVENTS_STREAM", "molt:events")
OUT_PATH = os.getenv("MOLT_OPENCLAW_OUT", "./openclaw_events.jsonl")


def map_event(fields: Dict[str, Any]) -> Dict[str, Any]:
    data = json.loads(fields.get("data") or "{}")
    err_raw = fields.get("err") or ""
    err = json.loads(err_raw) if err_raw else None
    return {
        "cmd": fields.get("cmd"),
        "actor": fields.get("actor"),
        "room_id": fields.get("room_id"),
        "ok": fields.get("ok") == "1",
        "data": data,
        "err": err,
        "ts": float(fields.get("ts") or 0),
    }


def main() -> None:
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    last_id = "0-0"
    print(f"OpenClaw bridge: tail {STREAM_KEY} -> {OUT_PATH}")

    with open(OUT_PATH, "a", encoding="utf-8") as out:
        while True:
            entries = client.xread({STREAM_KEY: last_id}, block=1000)
            if not entries:
                continue
            for _, items in entries:
                for entry_id, fields in items:
                    payload = map_event(fields)
                    out.write(json.dumps(payload, ensure_ascii=False) + "\n")
                    out.flush()
                    last_id = entry_id
            time.sleep(0.1)


if __name__ == "__main__":
    main()
