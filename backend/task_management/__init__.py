"""TaskForge application factory.

The Flask app serves two things: a JSON API under `/api`, and the compiled
React single-page app. Keeping both behind one origin means the session cookie
is first-party, so there is no CORS surface and no token in local storage.
"""
import os

from click import ClickException
from flask import Flask, jsonify, request, send_from_directory
from werkzeug.exceptions import HTTPException

from .config import get_config
from .extensions import db, migrate
from .security import init_logging, init_security
from .services.errors import AppError

BACKEND_DIR = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
REPO_ROOT = os.path.normpath(os.path.join(BACKEND_DIR, ".."))

# Absolute, so `flask db` and the boot-time upgrade find the same scripts no
# matter which directory the process was started from.
MIGRATIONS_DIR = os.path.join(BACKEND_DIR, "migrations")

# Vite writes the production bundle here; `web/index.html` only exists in a
# dev checkout, where Vite serves it itself on :5173.
SPA_DIST = os.path.join(REPO_ROOT, "web", "dist")


def create_app(config_object=None):
    app = Flask(__name__, static_folder=None)
    app.config.from_object(config_object or get_config())

    init_logging(app)
    db.init_app(app)
    migrate.init_app(app, db, directory=MIGRATIONS_DIR)

    from . import models  # noqa: F401  (registers models with SQLAlchemy metadata)
    from .routes import register_routes

    init_security(app)
    register_routes(app)
    register_spa(app)
    register_error_handlers(app)
    register_cli(app)

    if app.config.get("AUTO_BOOTSTRAP"):
        with app.app_context():
            bootstrap(app)

    return app


def register_spa(app):
    """Serves the built SPA, falling back to index.html so client-side routes
    survive a hard refresh or a shared deep link."""

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        if path.startswith("api/"):
            return jsonify({"error": "Not found"}), 404

        if not os.path.isdir(SPA_DIST):
            return (
                jsonify(
                    {
                        "error": "Frontend is not built",
                        "hint": "Run `npm install && npm run build` in web/, "
                        "or `npm run dev` for the Vite dev server.",
                    }
                ),
                503,
            )

        candidate = os.path.join(SPA_DIST, path)
        if path and os.path.isfile(candidate):
            return send_from_directory(SPA_DIST, path)
        return send_from_directory(SPA_DIST, "index.html")


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        """Any service-layer error that escapes a route still returns the same
        JSON shape the client parses, instead of a 500."""
        return jsonify({"error": err.message}), err.status

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        if request.path.startswith("/api/"):
            return jsonify({"error": err.description}), err.code
        return err

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        db.session.rollback()
        app.logger.exception("Unhandled error on %s %s", request.method, request.path)
        # Never leak a traceback or an ORM message to the client.
        return jsonify({"error": "Something went wrong on the server"}), 500


def bootstrap(app):
    """Makes a brand-new deploy usable on its very first boot.

    Without this, a fresh database has no departments, so the signup form's
    department picker is empty and nobody can create the first account.
    Every step is idempotent, so it is safe on every restart.
    """
    from flask_migrate import upgrade

    from .seed import ensure_baseline

    try:
        if os.path.isdir(MIGRATIONS_DIR):
            # Alembic owns the schema wherever it is available, so a deploy
            # applies pending migrations instead of silently skipping columns
            # that create_all() would never add to an existing table.
            upgrade()
        else:
            db.create_all()
        ensure_baseline(app)
    except Exception as err:  # noqa: BLE001 - preserve the existing non-fatal bootstrap policy
        db.session.rollback()
        app.logger.error(
            "Bootstrap skipped; check database readiness and BOOTSTRAP_ADMIN_PASSWORD (%s)",
            type(err).__name__,
        )


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Creates every table from the SQLAlchemy models."""
        db.create_all()
        print("Database tables created.")

    @app.cli.command("seed")
    def seed():
        """Drops, recreates and repopulates the demo dataset."""
        from .seed import run

        run()

    @app.cli.command("create-admin")
    def create_admin():
        """Provisions the initial admin from private configuration without printing secrets."""
        from .seed import ensure_baseline

        try:
            result = ensure_baseline(app, force=True)
        except Exception as err:
            db.session.rollback()
            app.logger.error("Administrator provisioning failed (%s)", type(err).__name__)
            raise ClickException(
                "Could not provision administrator; check database readiness and BOOTSTRAP_ADMIN_PASSWORD."
            ) from None
        print(result or "Admin account already exists.")
