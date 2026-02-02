from molt_office.api import create_app


def test_events_sse_endpoint_exists():
    app = create_app()
    routes = {route.path for route in app.router.routes}
    assert "/events/sse" in routes
