import os
import time
import requests


BASE_URL = os.getenv("MOLT_OFFICE_URL", "http://127.0.0.1:8099")
TOKEN = os.getenv("MOLT_OFFICE_TOKEN")
LAST_ID_FILE = os.getenv("MOLT_LAST_ID_FILE", "./.last_event_id")
HEARTBEAT = int(os.getenv("MOLT_SSE_HEARTBEAT", "15000"))


def load_last_id() -> str:
    try:
        with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or "0-0"
    except FileNotFoundError:
        return "0-0"


def save_last_id(last_id: str) -> None:
    with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
        f.write(last_id)


def stream_events() -> None:
    last_id = load_last_id()
    headers = {"Authorization": f"Bearer {TOKEN}"}
    params = {"last_id": last_id, "heartbeat": HEARTBEAT}

    while True:
        try:
            with requests.get(
                f"{BASE_URL}/events/sse",
                headers=headers,
                params=params,
                stream=True,
                timeout=60,
            ) as r:
                r.raise_for_status()
                for line in r.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if line.startswith("id:"):
                        last_id = line.replace("id:", "").strip()
                        save_last_id(last_id)
                    elif line.startswith("data:"):
                        payload = line.replace("data:", "").strip()
                        if payload and payload != "{}":
                            print(payload, flush=True)
                    elif line.startswith(":"):
                        # comment heartbeat; ignore
                        continue
        except Exception as e:
            print(f"SSE error: {e}. Reconnecting in 2s...", flush=True)
            time.sleep(2)
            params["last_id"] = last_id


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("MOLT_OFFICE_TOKEN is required")
    stream_events()
