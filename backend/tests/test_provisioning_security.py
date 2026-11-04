"""Provisioning tests use fake models/sessions, never a bootstrap database."""
import logging
import secrets
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

import task_management as factory
from task_management import seed
from task_management.services.passwords import verify_password


@pytest.fixture
def provisioning(monkeypatch, caplog):
    app = Flask("provisioning-security-fixture")
    password = secrets.token_urlsafe(24)
    app.config.update(
        BOOTSTRAP_ADMIN_USERNAME="bootstrap.fixture",
        BOOTSTRAP_ADMIN_PASSWORD=password,
    )
    user = Mock()
    user.query.filter.return_value.first.return_value = None
    department = Mock()
    department.query.first.return_value = None
    session = Mock()
    fake_db = SimpleNamespace(session=session)
    monkeypatch.setattr(seed, "User", user)
    monkeypatch.setattr(seed, "Department", department)
    monkeypatch.setattr(seed, "db", fake_db)
    monkeypatch.setattr(factory, "db", fake_db)
    caplog.set_level(logging.INFO, logger=app.name)
    return SimpleNamespace(
        app=app, password=password, user=user, department=department, session=session
    )


def assert_secret_absent(text, secret):
    assert secret not in text, "Private provisioning value was disclosed"


@pytest.mark.parametrize("missing", [None, ""])
def test_first_admin_requires_private_configuration_before_any_write(provisioning, missing):
    provisioning.app.config["BOOTSTRAP_ADMIN_PASSWORD"] = missing
    with pytest.raises(RuntimeError, match="BOOTSTRAP_ADMIN_PASSWORD"):
        seed.ensure_baseline(provisioning.app)
    provisioning.user.assert_not_called()
    provisioning.department.assert_not_called()
    provisioning.session.add.assert_not_called()
    provisioning.session.add_all.assert_not_called()
    provisioning.session.commit.assert_not_called()


def test_supplied_admin_password_is_hashed_and_absent_from_output(provisioning, caplog, capsys):
    note = seed.ensure_baseline(provisioning.app)
    values = provisioning.user.call_args.kwargs
    assert values["role"] == "super_admin"
    assert values["username"] == "bootstrap.fixture"
    assert verify_password(values["password_hash"], provisioning.password)
    assert values["password_hash"] != provisioning.password
    assert provisioning.session.commit.call_count == 2  # Existing department/admin commits.
    captured = capsys.readouterr()
    assert_secret_absent(note + caplog.text + captured.out + captured.err, provisioning.password)


@pytest.mark.parametrize("force", [False, True])
def test_existing_admin_does_not_require_or_change_a_password(provisioning, force):
    provisioning.app.config["BOOTSTRAP_ADMIN_PASSWORD"] = None
    provisioning.user.query.filter.return_value.first.return_value = SimpleNamespace(username="existing.fixture")
    provisioning.department.query.first.return_value = object()
    seed.ensure_baseline(provisioning.app, force=force)
    provisioning.user.assert_not_called()
    provisioning.session.add.assert_not_called()
    provisioning.session.commit.assert_not_called()


@pytest.mark.parametrize("force", [False, True])
def test_existing_admin_still_gets_missing_baseline_departments(provisioning, force):
    provisioning.app.config["BOOTSTRAP_ADMIN_PASSWORD"] = None
    provisioning.user.query.filter.return_value.first.return_value = SimpleNamespace(username="existing.fixture")
    seed.ensure_baseline(provisioning.app, force=force)
    provisioning.user.assert_not_called()
    provisioning.session.add.assert_not_called()
    provisioning.session.add_all.assert_called_once()
    provisioning.session.commit.assert_called_once()


def test_bootstrap_exception_logs_metadata_not_secret_details(provisioning, monkeypatch, caplog, capsys):
    import flask_migrate

    def fail_upgrade(*args, **kwargs):
        raise RuntimeError("private migration diagnostic " + provisioning.password)

    monkeypatch.setattr(flask_migrate, "upgrade", fail_upgrade)
    factory.bootstrap(provisioning.app)
    provisioning.session.rollback.assert_called_once()
    records = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(records) == 1
    assert "Bootstrap skipped" in records[0].getMessage()
    assert "RuntimeError" in records[0].getMessage()
    assert records[0].exc_info is None
    captured = capsys.readouterr()
    output = caplog.text + captured.out + captured.err
    assert_secret_absent(output, provisioning.password)
    assert "private migration diagnostic" not in output
    assert "Traceback" not in output


def test_cli_provisioning_success_never_prints_the_supplied_password(provisioning, caplog, capsys):
    factory.register_cli(provisioning.app)
    result = provisioning.app.test_cli_runner().invoke(args=["create-admin"])
    assert result.exit_code == 0
    assert "Created admin" in result.output
    captured = capsys.readouterr()
    assert_secret_absent(result.output + caplog.text + captured.out + captured.err, provisioning.password)


def test_cli_provisioning_failure_never_prints_exception_secrets(
    provisioning, monkeypatch, caplog, capsys
):
    def fail_hash(*args, **kwargs):
        raise RuntimeError("private hashing diagnostic " + provisioning.password)

    monkeypatch.setattr(seed, "_hash", fail_hash)
    factory.register_cli(provisioning.app)
    result = provisioning.app.test_cli_runner().invoke(args=["create-admin"])
    assert result.exit_code == 1
    assert "Could not provision administrator" in result.output
    provisioning.user.assert_not_called()
    records = [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert len(records) == 1
    assert records[0].exc_info is None
    captured = capsys.readouterr()
    output = result.output + caplog.text + captured.out + captured.err
    assert_secret_absent(output, provisioning.password)
    assert "private hashing diagnostic" not in output
    assert "Traceback" not in output
