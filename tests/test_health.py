from molt_office.api import create_app


def test_health_endpoint_exists():
    app = create_app()
    routes = {route.path for route in app.router.routes}
    assert "/health" in routes
