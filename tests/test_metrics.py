from fastapi.testclient import TestClient

from molt_office.api import create_app
from molt_office.storage import RedisBackend


def test_metrics_endpoint_payload_inmemory():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backend"] in {"InMemoryBackend", "RedisBackend"}
    assert "uptime_s" in data
    # When Redis is not configured, these should be None
    if data.get("backend") != "RedisBackend":
        assert data.get("events") is None
        assert data.get("event_lag_ms") is None
        assert data.get("redis_ping_ms") is None


def test_metrics_endpoint_payload_redis():
    backend = RedisBackend()
    app = create_app(backend=backend)
    client = TestClient(app)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backend"] == "RedisBackend"
    assert isinstance(data.get("events"), int)
    assert data.get("event_lag_ms") is None or isinstance(data.get("event_lag_ms"), int)
    assert data.get("redis_ping_ms") is None or isinstance(data.get("redis_ping_ms"), (int, float))
