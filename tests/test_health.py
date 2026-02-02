from fastapi.testclient import TestClient

from molt_office.api import create_app


def test_health_endpoint_exists():
    app = create_app()
    routes = {route.path for route in app.router.routes}
    assert "/health" in routes


def test_health_endpoint_payload():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in {"ok", "degraded"}
    assert "backend" in data
    # If Redis is configured, redis_ok/latency should be present; otherwise None
    if data.get("backend") == "RedisBackend":
        assert data.get("redis_ok") in {True, False}
    else:
        assert data.get("redis_ok") is None
        assert data.get("redis_latency_ms") is None
