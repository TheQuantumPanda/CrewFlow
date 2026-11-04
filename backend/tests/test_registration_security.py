"""Registration failures retain contracts without exposing internal exception text."""
import logging
import secrets

import pytest
from sqlalchemy.exc import IntegrityError

from task_management.extensions import db
from task_management.models import Employee, User
from task_management.services import auth_service, employee_service
from task_management.services.errors import EmployeeError


@pytest.fixture
def registration_payload(department):
    return {
        "username": "security.fixture",
        "password": secrets.token_urlsafe(24) + "A1",
        "first_name": "Security",
        "last_name": "Fixture",
        "email": "security.fixture@example.test",
        "phone": "5550101234",
        "department_id": department.id,
    }


@pytest.fixture
def registration_logs(app, caplog):
    # The application's logger deliberately does not propagate to the root logger.
    app.logger.addHandler(caplog.handler)
    caplog.set_level(logging.INFO, logger=app.logger.name)
    yield caplog
    app.logger.removeHandler(caplog.handler)


def assert_no_registered_account(client):
    assert User.query.count() == 0
    assert Employee.query.count() == 0
    assert client.get("/api/auth/me").status_code == 401


def assert_no_sensitive_text(text, needles):
    assert not any(needle in text for needle in needles), "Sensitive diagnostic content was disclosed"


def test_expected_registration_validation_is_unchanged(
    client, registration_payload, registration_logs
):
    registration_payload["email"] = "invalid-email"
    response = client.post("/api/auth/register", json=registration_payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": "Please enter a valid email address"}
    assert_no_registered_account(client)
    assert not any(record.levelno >= logging.ERROR for record in registration_logs.records)


def test_profile_validation_error_keeps_message_status_and_rolls_back(
    client, registration_payload, monkeypatch, registration_logs
):
    def reject_profile(*args, **kwargs):
        raise EmployeeError("employee_code already in use")

    monkeypatch.setattr(employee_service, "create_employee", reject_profile)
    response = client.post("/api/auth/register", json=registration_payload)
    assert response.status_code == 400
    assert response.get_json() == {"error": "employee_code already in use"}
    assert_no_registered_account(client)
    assert not any(record.levelno >= logging.ERROR for record in registration_logs.records)


@pytest.mark.parametrize("target", ["generate_employee_code", "create_employee"])
@pytest.mark.parametrize("kind", ["runtime", "database", "message_attribute"])
def test_unexpected_profile_error_is_sanitized_and_rolled_back(
    client, registration_payload, monkeypatch, registration_logs, capsys, target, kind
):
    secret = registration_payload["password"]
    connection = "postgresql://fixture:" + secret + "@private.invalid/fixture"
    statement = "INSERT INTO private_registration_details VALUES (:credential)"

    class InternalFailure(Exception):
        pass

    def fail_profile(*args, **kwargs):
        # The new login has been flushed but must not survive this failure.
        assert User.query.count() == 1
        detail = connection + " " + statement
        if kind == "database":
            raise IntegrityError(statement, {"credential": secret}, RuntimeError(detail))
        if kind == "message_attribute":
            error = InternalFailure(detail)
            error.message = detail
            raise error
        raise RuntimeError(detail)

    monkeypatch.setattr(employee_service, target, fail_profile)
    response = client.post("/api/auth/register", json=registration_payload)
    assert response.status_code == 400  # Preserve the existing profile-failure status.
    assert response.get_json() == {"error": "Could not create your account. Please try again."}
    assert_no_registered_account(client)
    records = [record for record in registration_logs.records if record.levelno >= logging.ERROR]
    assert len(records) == 1
    assert "Registration profile creation failed" in records[0].getMessage()
    assert records[0].request_id == response.headers["X-Request-ID"]
    assert records[0].exc_info is None
    assert records[0].stack_info is None
    captured = capsys.readouterr()
    public_and_logs = response.get_data(as_text=True) + registration_logs.text + captured.out + captured.err
    assert_no_sensitive_text(public_and_logs, [secret, connection, statement, "Traceback"])


def test_failure_before_profile_guard_retains_generic_500_without_secret_logging(
    client, registration_payload, monkeypatch, registration_logs, capsys
):
    secret = registration_payload["password"]

    def fail_hash(*args, **kwargs):
        raise RuntimeError("private hashing diagnostic " + secret)

    monkeypatch.setattr(auth_service, "hash_password", fail_hash)
    response = client.post("/api/auth/register", json=registration_payload)
    assert response.status_code == 500
    assert response.get_json() == {"error": "Something went wrong on the server"}
    assert_no_registered_account(client)
    records = [record for record in registration_logs.records if record.levelno >= logging.ERROR]
    assert len(records) == 1
    assert "Registration failed (RuntimeError)" in records[0].getMessage()
    assert records[0].request_id == response.headers["X-Request-ID"]
    assert records[0].exc_info is None
    captured = capsys.readouterr()
    assert_no_sensitive_text(
        response.get_data(as_text=True) + registration_logs.text + captured.out + captured.err,
        [secret, "private hashing diagnostic", "Traceback"],
    )


def test_failed_registration_does_not_leave_pending_changes(client, registration_payload, monkeypatch):
    def fail_profile(*args, **kwargs):
        raise RuntimeError("synthetic profile failure")

    monkeypatch.setattr(employee_service, "create_employee", fail_profile)
    assert client.post("/api/auth/register", json=registration_payload).status_code == 400
    assert not db.session.new
    assert not db.session.dirty
    assert_no_registered_account(client)
