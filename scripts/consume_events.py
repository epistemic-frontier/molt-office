import os
import time

import redis


REDIS_URL = os.getenv("MOLT_REDIS_URL", "redis://localhost:6379/0")
STREAM_KEY = os.getenv("MOLT_EVENTS_STREAM", "molt:events")


def main() -> None:
    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    last_id = "0-0"
    print(f"Consuming {STREAM_KEY} from {last_id}...")
    while True:
        entries = client.xread({STREAM_KEY: last_id}, block=1000)
        if not entries:
            continue
        for _, items in entries:
            for entry_id, fields in items:
                print(entry_id, fields)
                last_id = entry_id
        time.sleep(0.1)


if __name__ == "__main__":
    main()
