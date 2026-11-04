import time

from flask import Blueprint, g, jsonify, request, session

from ..auth_decorators import login_required
from ..services import auth_service, employee_service
from ..services.errors import AuthError

auth_bp = Blueprint("auth", __name__)


def _start_session(user, console=False):
    """Drops anything left over from a previous visitor before establishing the
    new session, so no attacker-planted key survives the login boundary."""
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    if console:
        session["console"] = True
        session["seen"] = int(time.time())
    session.permanent = True


# Public — the signup form needs to populate its department picker before
# the visitor has an account.
@auth_bp.route("/departments", methods=["GET"])
def list_departments():
    departments = employee_service.list_departments()
    return jsonify({"departments": [{"id": d.id, "name": d.name} for d in departments]})


@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        user = auth_service.register_user(request.get_json(silent=True) or {})
        _start_session(user)
        return jsonify({"user": user.to_dict()}), 201
    except AuthError as err:
        return jsonify({"error": err.message}), err.status


def _login(console):
    body = request.get_json(silent=True) or {}
    username, password = body.get("username"), body.get("password")
    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400

    try:
        user = auth_service.authenticate_user(username, password, console=console)
        _start_session(user, console=console)
        return jsonify({"user": user.to_dict()})
    except AuthError as err:
        return jsonify({"error": err.message}), err.status


@auth_bp.route("/login", methods=["POST"])
def login():
    return _login(console=False)


@auth_bp.route("/admin/login", methods=["POST"])
def admin_login():
    return _login(console=True)


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"ok": True})


@auth_bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    body = request.get_json(silent=True) or {}
    old_password, new_password = body.get("oldPassword"), body.get("newPassword")
    if not old_password or not new_password:
        return jsonify({"error": "oldPassword and newPassword are required"}), 400

    try:
        auth_service.change_password(g.current_user.id, old_password, new_password)
        return jsonify({"ok": True})
    except AuthError as err:
        return jsonify({"error": err.message}), err.status


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    try:
        return jsonify({"user": auth_service.get_profile(g.current_user.id)})
    except AuthError as err:
        return jsonify({"error": err.message}), err.status
