"""Liveness and readiness probes.

Every managed host wants an endpoint it can poll. `/healthz` answers without
touching anything, so it stays up even when the database is down; `/readyz`
actually round-trips a query, which is what a load balancer should gate on.
"""
from flask import Blueprint, current_app, jsonify
from sqlalchemy import text

from ..extensions import db

health_bp = Blueprint("health", __name__)


@health_bp.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok", "env": current_app.config.get("ENV_NAME")})


@health_bp.route("/readyz", methods=["GET"])
def readyz():
    try:
        db.session.execute(text("SELECT 1"))
    except Exception as err:  # noqa: BLE001 - the probe reports, it doesn't recover
        current_app.logger.error("Readiness check failed: %s", err)
        return jsonify({"status": "degraded", "database": "unreachable"}), 503

    return jsonify({"status": "ok", "database": "reachable"})
