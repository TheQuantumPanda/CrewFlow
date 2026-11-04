"""Deployment configuration — the failure mode that actually took the site down.

Managed hosts hand out a `postgres://` URL, which SQLAlchemy 2 refuses, and
they never name a driver. Getting this mapping wrong is a boot-time crash on
the platform and cannot be reproduced locally against SQLite, so it is pinned
here instead.
"""
import pytest

from task_management.config import ProductionConfig, get_config, normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # Render and Railway still emit the legacy scheme.
        ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        # Neon and Supabase emit the modern one, still with no driver named.
        ("postgresql://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),
        ("mysql://u:p@host:3306/db", "mysql+pymysql://u:p@host:3306/db"),
        # Already-qualified URLs must pass through untouched.
        ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),
        ("mysql+pymysql://u:p@host/db", "mysql+pymysql://u:p@host/db"),
        ("sqlite:///local.db", "sqlite:///local.db"),
    ],
)
def test_database_urls_are_normalised_to_installed_drivers(raw, expected):
    assert normalize_database_url(raw) == expected


def test_query_parameters_survive_normalisation():
    """Managed Postgres usually requires `?sslmode=require`; dropping it turns
    into a connection refusal at boot."""
    normalised = normalize_database_url("postgres://u:p@host/db?sslmode=require")
    assert normalised.endswith("?sslmode=require")
    assert normalised.startswith("postgresql+psycopg://")


def test_no_url_is_passed_through_as_none():
    assert normalize_database_url(None) is None
    assert normalize_database_url("") is None


def test_production_refuses_to_start_without_a_secret_key(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        ProductionConfig()


def test_production_accepts_a_supplied_secret_key(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    assert ProductionConfig().SECRET_KEY == "a" * 64


def test_production_requires_secure_cookies(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "a" * 64)
    config = ProductionConfig()
    assert config.SESSION_COOKIE_SECURE is True
    assert config.SESSION_COOKIE_HTTPONLY is True


def test_env_name_selects_the_config(monkeypatch):
    monkeypatch.setenv("APP_ENV", "testing")
    assert get_config().ENV_NAME == "testing"
