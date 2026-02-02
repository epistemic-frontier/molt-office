from molt_office.api import create_app


def test_metrics_endpoint_exists():
    app = create_app()
    routes = {route.path for route in app.router.routes}
    assert "/metrics" in routes


def test_metrics_payload_shape():
    app = create_app()
    # Call endpoint via direct function
    metrics = None
    for route in app.router.routes:
        if getattr(route, "path", None) == "/metrics":
            metrics = route.endpoint()
            break
    assert metrics is not None
    assert "backend" in metrics
    assert "uptime_s" in metrics
