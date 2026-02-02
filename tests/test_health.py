from fastapi.testclient import TestClient

from molt_office.api import create_app
from molt_office.storage import RedisBackend


def test_health_endpoint_exists():
    app = create_app()
    routes = {route.path for route in app.router.routes}
    assert "/health" in routes


def test_health_endpoint_payload_inmemory():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ok", "degraded"}
    assert data["backend"] in {"InMemoryBackend", "RedisBackend"}
    assert data.get("redis_ok") is None
    assert data.get("redis_latency_ms") is None


def test_health_endpoint_payload_redis():
    backend = RedisBackend()
    app = create_app(backend=backend)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["backend"] == "RedisBackend"
    assert data.get("redis_ok") in {True, False}
    if data.get("redis_ok"):
        assert isinstance(data.get("redis_latency_ms"), int)
