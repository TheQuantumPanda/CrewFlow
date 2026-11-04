"""CSRF enforcement, security headers, and health probes."""

CSP_DEFAULT_SRC = "default-src 'self'"


def test_mutating_request_without_csrf_header_is_rejected(client, users):
    client.post("/api/auth/login", json={"username": "manager.user", "password": "Password123"})
    # Authenticated, but deliberately not echoing the double-submit token.
    response = client.post("/api/tasks", json={"title": "Forged"})
    assert response.status_code == 403
    assert "CSRF" in response.get_json()["error"]


def test_mutating_request_with_a_wrong_csrf_token_is_rejected(client, users):
    client.post("/api/auth/login", json={"username": "manager.user", "password": "Password123"})
    client.environ_base["HTTP_X_CSRF_TOKEN"] = "not-the-real-token"
    assert client.post("/api/tasks", json={"title": "Forged"}).status_code == 403


def test_login_itself_works_without_a_prior_token(client, users):
    """An unauthenticated caller has no session to ride, so the login endpoint
    stays usable from curl and from a cold browser."""
    response = client.post(
        "/api/auth/login", json={"username": "manager.user", "password": "Password123"}
    )
    assert response.status_code == 200


def test_reads_are_never_blocked_by_csrf(as_admin):
    assert as_admin.get("/api/tasks").status_code == 200


def test_csrf_cookie_is_issued_and_readable_by_script(client):
    client.get("/api/healthz")
    cookie = client.get_cookie("taskforge_csrf")
    assert cookie is not None
    # The SPA has to read this value back out to echo it in the header.
    assert cookie.http_only is False


def test_security_headers_are_present(client):
    headers = client.get("/api/healthz").headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert CSP_DEFAULT_SRC in headers["Content-Security-Policy"]
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_every_response_carries_a_correlation_id(client):
    assert client.get("/api/healthz").headers.get("X-Request-ID")


def test_health_and_readiness_probes(client):
    assert client.get("/api/healthz").get_json()["status"] == "ok"
    assert client.get("/api/readyz").get_json()["database"] == "reachable"


def test_unknown_api_route_returns_json_not_html(client):
    response = client.get("/api/does-not-exist")
    assert response.status_code == 404
    assert response.is_json
