"""Cross-cutting HTTP security: CSRF, response headers, request correlation.

The API authenticates with a session cookie, which browsers attach to
cross-site requests automatically — so cookie auth needs CSRF protection to be
safe. `SameSite=Lax` covers most of it, but it is a defence-in-depth measure,
not a guarantee (it does nothing for same-site subdomain takeover, and older
browsers ignore it), so a double-submit token backs it up.
"""
import logging
import secrets
import time
import uuid
from hmac import compare_digest

from flask import current_app, g, jsonify, request

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

CSP = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "   # the markup uses style="" attributes
    "img-src 'self' data:; "
    "font-src 'self'; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


def init_security(app):
    @app.before_request
    def _start_request():
        g.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        g.request_started = time.perf_counter()

    @app.before_request
    def _verify_csrf():
        if not app.config.get("CSRF_ENABLED") or request.method in SAFE_METHODS:
            return None
        if not request.path.startswith("/api/"):
            return None

        cookie_name = app.config["CSRF_COOKIE_NAME"]
        submitted_cookie = request.cookies.get(cookie_name)

        # Only authenticated requests can be abused by a cross-site forgery —
        # without a session cookie there is nothing to ride. Leaving unauth'd
        # calls alone keeps `curl`-ing the login endpoint workable.
        if not request.cookies.get(app.config["SESSION_COOKIE_NAME"]):
            return None

        header = request.headers.get("X-CSRF-Token", "")
        if not submitted_cookie or not compare_digest(str(header), str(submitted_cookie)):
            return jsonify({"error": "Invalid or missing CSRF token"}), 403
        return None

    @app.after_request
    def _apply_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        response.headers.setdefault("Content-Security-Policy", CSP)
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )

        request_id = g.get("request_id")
        if request_id:
            response.headers["X-Request-ID"] = request_id

        _ensure_csrf_cookie(response)
        return response

    @app.after_request
    def _log_request(response):
        started = g.get("request_started")
        duration_ms = round((time.perf_counter() - started) * 1000, 1) if started else None
        app.logger.info(
            "%s %s -> %s",
            request.method,
            request.full_path.rstrip("?"),
            response.status_code,
            extra={
                "request_id": g.get("request_id"),
                "duration_ms": duration_ms,
                "user_id": getattr(g.get("current_user"), "id", None),
            },
        )
        return response


def _ensure_csrf_cookie(response):
    """Issues the double-submit token. Deliberately NOT HttpOnly — the browser
    client has to read it back out and echo it in a header."""
    cookie_name = current_app.config["CSRF_COOKIE_NAME"]
    if request.cookies.get(cookie_name):
        return

    response.set_cookie(
        cookie_name,
        secrets.token_urlsafe(32),
        httponly=False,
        samesite=current_app.config["SESSION_COOKIE_SAMESITE"],
        secure=current_app.config["SESSION_COOKIE_SECURE"],
        max_age=current_app.config["PERMANENT_SESSION_LIFETIME"],
        path="/",
    )


class RequestFormatter(logging.Formatter):
    """Appends the correlation id so a single user action can be traced
    through the log even with several gunicorn workers interleaving output."""

    def format(self, record):
        base = super().format(record)
        request_id = getattr(record, "request_id", None)
        duration = getattr(record, "duration_ms", None)
        suffix = []
        if request_id:
            suffix.append(f"req={request_id}")
        if duration is not None:
            suffix.append(f"{duration}ms")
        return f"{base} [{' '.join(suffix)}]" if suffix else base


def init_logging(app):
    handler = logging.StreamHandler()
    handler.setFormatter(RequestFormatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s"))

    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    app.logger.handlers = [handler]
    app.logger.setLevel(level)
    app.logger.propagate = False
