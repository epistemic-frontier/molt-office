import json
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from molt_office.api import create_app
from molt_office.storage import RedisBackend
from molt_office.world import World



def test_events_sse_endpoint_exists():
    app = create_app()
    routes = {route.path for route in app.router.routes}
    assert "/events/sse" in routes


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("MOLT_REDIS_URL") is None,
    reason="MOLT_REDIS_URL not set",
)
def test_events_sse_filters_actor_room_cmd():
    backend = RedisBackend(url=os.environ["MOLT_REDIS_URL"], prefix=f"molt-test-{uuid.uuid4().hex}")
    world = World(backend=backend)
    app = create_app(backend=backend)
    client = TestClient(app)

    world.room_enter("alice", "lobby")
    world.board_write("alice", "lobby", "hello")
    world.room_enter("bob", "coffee:public")
    world.board_write("bob", "coffee:public", "hi")

    with client.stream(
        "GET",
        "/events/sse",
        params={"actor": "alice", "last_id": "0-0", "heartbeat": 1},
        timeout=2,
    ) as resp:
        assert resp.status_code == 200
        payloads: list[dict] = []
        for line in resp.iter_lines():
            line_s = line.decode() if isinstance(line, (bytes, bytearray)) else line
            if line_s.startswith("data: "):
                payloads.append(json.loads(line_s[6:]))
                if len(payloads) >= 2:
                    break
        assert payloads
        assert all(p["fields"]["actor"] == "alice" for p in payloads)

    with client.stream(
        "GET",
        "/events/sse",
        params={"room_id": "coffee:public", "last_id": "0-0", "heartbeat": 1},
        timeout=2,
    ) as resp:
        assert resp.status_code == 200
        payloads = []
        for line in resp.iter_lines():
            line_s = line.decode() if isinstance(line, (bytes, bytearray)) else line
            if line_s.startswith("data: "):
                payloads.append(json.loads(line_s[6:]))
                if len(payloads) >= 1:
                    break
        assert payloads
        assert all(p["fields"]["room_id"] == "coffee:public" for p in payloads)

    with client.stream(
        "GET",
        "/events/sse",
        params={"cmd": "board.write", "last_id": "0-0", "heartbeat": 1},
        timeout=2,
    ) as resp:
        assert resp.status_code == 200
        payloads = []
        for line in resp.iter_lines():
            line_s = line.decode() if isinstance(line, (bytes, bytearray)) else line
            if line_s.startswith("data: "):
                payloads.append(json.loads(line_s[6:]))
                if len(payloads) >= 2:
                    break
        assert payloads
        assert all(p["fields"]["cmd"] == "board.write" for p in payloads)
