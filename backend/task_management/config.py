"""Environment-driven configuration.

One codebase runs against three engines without edits:

* **SQLite**   — zero-setup local development and the test suite.
* **MySQL 8**  — the original schema in `database/schema.sql`.
* **Postgres** — what every managed host (Render, Railway, Neon, Fly) hands you.

Selection is entirely by environment, so a deploy never needs a code change.
"""
import os
import secrets
from urllib.parse import quote_plus, urlsplit, urlunsplit

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Load backend/.env explicitly (by path, not cwd) so `flask` CLI commands and
# `python run.py` behave the same whether they're launched from the repo
# root or from inside backend/.
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _as_bool(value, default=False):
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def normalize_database_url(raw):
    """Maps the URL schemes hosts actually emit onto SQLAlchemy dialects.

    Render and Railway both still hand out `postgres://`, which SQLAlchemy 2
    refuses outright, and neither pins a driver — so the driver we installed
    has to be named explicitly.
    """
    if not raw:
        return None

    url = raw.strip()
    scheme = urlsplit(url).scheme.lower()

    replacements = {
        "postgres": "postgresql+psycopg",
        "postgresql": "postgresql+psycopg",
        "mysql": "mysql+pymysql",
    }
    if scheme in replacements:
        parts = urlsplit(url)
        url = urlunsplit(parts._replace(scheme=replacements[scheme]))

    return url


def _sqlite_url():
    instance_dir = os.path.join(BASE_DIR, "instance")
    os.makedirs(instance_dir, exist_ok=True)
    return "sqlite:///" + os.path.join(instance_dir, "taskforge.db").replace("\\", "/")


def _resolve_database_uri():
    explicit = normalize_database_url(os.environ.get("DATABASE_URL"))
    if explicit:
        return explicit

    # Only build a MySQL URL when the developer actually opted into MySQL by
    # setting credentials. Otherwise fall back to SQLite so a fresh clone runs
    # with `python run.py` and nothing else installed.
    if os.environ.get("DB_NAME") or os.environ.get("DB_USER"):
        user = os.environ.get("DB_USER", "root")
        password = os.environ.get("DB_PASSWORD", "")
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "3306")
        name = os.environ.get("DB_NAME", "taskforge")
        return (
            f"mysql+pymysql://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/{name}?charset=utf8mb4"
        )

    return _sqlite_url()


class Config:
    ENV_NAME = "development"
    DEBUG = False
    TESTING = False

    SECRET_KEY = os.environ.get("SECRET_KEY") or "taskforge-dev-secret-not-for-production"

    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,   # a managed Postgres drops idle connections
        "pool_recycle": 280,
    }

    # --- Session cookie -------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_NAME = "taskforge_session"
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_LIFETIME_SECONDS", 60 * 60 * 12))

    # --- Auth policy ----------------------------------------------------
    MIN_PASSWORD_LENGTH = int(os.environ.get("MIN_PASSWORD_LENGTH", 8))
    MAX_FAILED_LOGINS = int(os.environ.get("MAX_FAILED_LOGINS", 5))
    LOCKOUT_MINUTES = int(os.environ.get("LOCKOUT_MINUTES", 15))
    ADMIN_IDLE_MINUTES = int(os.environ.get("ADMIN_IDLE_MINUTES", 30))
    CSRF_ENABLED = True
    CSRF_COOKIE_NAME = "taskforge_csrf"

    # --- Bootstrap ------------------------------------------------------
    # Create tables and a starter admin + departments on first boot, so a
    # brand-new deploy is usable without shelling into the container.
    AUTO_BOOTSTRAP = _as_bool(os.environ.get("AUTO_BOOTSTRAP"), True)
    BOOTSTRAP_ADMIN_USERNAME = os.environ.get("BOOTSTRAP_ADMIN_USERNAME", "admin")
    BOOTSTRAP_ADMIN_PASSWORD = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")

    JSON_SORT_KEYS = False
    MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB — this API only ever takes JSON


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    ENV_NAME = "testing"
    TESTING = True
    SECRET_KEY = "testing-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"  # in-memory, per test
    SQLALCHEMY_ENGINE_OPTIONS = {}
    AUTO_BOOTSTRAP = False
    MIN_PASSWORD_LENGTH = 8


class ProductionConfig(Config):
    ENV_NAME = "production"
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        # Without a stable SECRET_KEY every restart silently invalidates all
        # sessions, and a shared default key would let anyone forge one.
        if not os.environ.get("SECRET_KEY"):
            raise RuntimeError(
                "SECRET_KEY must be set in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        self.SECRET_KEY = os.environ["SECRET_KEY"]


_CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    """Resolves the config object for APP_ENV / FLASK_ENV (default: development)."""
    name = (name or os.environ.get("APP_ENV") or os.environ.get("FLASK_ENV") or "development").lower()
    config_class = _CONFIGS.get(name, DevelopmentConfig)
    # ProductionConfig validates in __init__, so it has to be instantiated.
    return config_class() if config_class is ProductionConfig else config_class


def generate_secret_key():
    return secrets.token_hex(32)
