"""Authentication and role guards.

`login_required` resolves the session user once per request and parks it on
`g`, so downstream guards and handlers never re-query it.
"""
import time
from functools import wraps

from flask import current_app, g, jsonify, session

from .extensions import db
from .models import User
from .permissions import CONSOLE_ROLES, can, is_department_scoped


def current_user():
    return g.get("current_user")


def current_employee():
    user = current_user()
    return user.employee if user else None


def scope_department():
    """The department a manager or team lead is confined to, or None for roles
    that see the whole organisation. A scoped user with no employee profile
    gets an id that matches nothing, never None."""
    user = current_user()
    if not is_department_scoped(user.role):
        return None
    employee = user.employee
    return employee.department_id if employee else -1


def in_scope(department_id):
    scope = scope_department()
    return scope is None or scope == department_id


def _resolve_session_user():
    user_id = session.get("user_id")
    if not user_id:
        return None, ("Authentication required", 401)

    user = db.session.get(User, user_id)
    if not user or not user.is_active:
        session.clear()
        return None, ("Your session is no longer valid, please sign in again", 401)

    # A role change (or a demotion) must take effect immediately rather than
    # waiting for the stale copy in the cookie to expire.
    if session.get("role") != user.role:
        session["role"] = user.role

    if user.role in CONSOLE_ROLES:
        # Admin power only travels on a session opened through the console
        # door, so promoting someone mid-session doesn't hand them admin rights
        # on a cookie that never passed the stricter sign-in.
        if not session.get("console"):
            session.clear()
            return None, ("Admins must sign in through the admin console", 401)
        now = int(time.time())
        idle_limit = current_app.config["ADMIN_IDLE_MINUTES"] * 60
        if now - session.get("seen", now) > idle_limit:
            session.clear()
            return None, ("Your admin session timed out, please sign in again", 401)
        session["seen"] = now

    return user, None


def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        user, failure = _resolve_session_user()
        if failure:
            message, status = failure
            return jsonify({"error": message}), status
        g.current_user = user
        return f(*args, **kwargs)

    return wrapped


def permission_required(permission):
    """Allows the request only for roles holding `permission` (see
    permissions.py). Implies `login_required`."""

    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if not can(g.current_user.role, permission):
                return jsonify({"error": "You do not have permission to do that"}), 403
            return f(*args, **kwargs)

        return wrapped

    return decorator
