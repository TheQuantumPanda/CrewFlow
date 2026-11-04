"""Authentication: credentials, lockout, session handling, password policy."""
from datetime import datetime, timedelta

from conftest import PASSWORD, login

from task_management.extensions import db
from task_management.models import User


def test_login_succeeds_with_valid_credentials(client, users):
    response = login(client, "admin.user")
    assert response.status_code == 200
    assert response.get_json()["user"]["role"] == "admin"


def test_login_rejects_wrong_password(client, users):
    response = client.post("/api/auth/login", json={"username": "admin.user", "password": "nope"})
    assert response.status_code == 401


def test_login_error_does_not_reveal_whether_the_user_exists(client, users):
    real = client.post("/api/auth/login", json={"username": "admin.user", "password": "wrong1234"})
    fake = client.post("/api/auth/login", json={"username": "ghost.user", "password": "wrong1234"})
    assert real.get_json()["error"] == fake.get_json()["error"]


def test_account_locks_after_repeated_failures(client, users, app):
    for _ in range(app.config["MAX_FAILED_LOGINS"]):
        client.post("/api/auth/login", json={"username": "admin.user", "password": "wrong1234"})

    # Even the correct password is refused while the lock is in force.
    blocked = client.post("/api/auth/login", json={"username": "admin.user", "password": PASSWORD})
    assert blocked.status_code == 429


def test_lock_expires(client, users, app):
    user = User.query.filter_by(username="admin.user").first()
    user.locked_until = datetime.utcnow() - timedelta(minutes=1)
    db.session.commit()

    assert login(client, "admin.user").status_code == 200


def test_successful_login_clears_the_failure_counter(client, users):
    client.post("/api/auth/login", json={"username": "admin.user", "password": "wrong1234"})
    login(client, "admin.user")

    user = User.query.filter_by(username="admin.user").first()
    assert user.failed_login_count == 0
    assert user.last_login_at is not None


def test_me_requires_a_session(client, users):
    assert client.get("/api/auth/me").status_code == 401


def test_logout_ends_the_session(as_admin):
    assert as_admin.post("/api/auth/logout").status_code == 200
    assert as_admin.get("/api/auth/me").status_code == 401


def test_deactivated_user_is_rejected_mid_session(as_admin, users):
    users["admin"].is_active = False
    db.session.commit()
    assert as_admin.get("/api/auth/me").status_code == 401


def test_registration_creates_an_employee_never_an_admin(client, department):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "new.starter",
            "password": "Password123",
            "first_name": "New",
            "last_name": "Starter",
            "email": "new.starter@example.com",
            "phone": "9876500123",
            "department_id": department.id,
            "role": "admin",  # ignored on purpose
        },
    )
    assert response.status_code == 201
    assert response.get_json()["user"]["role"] == "employee"


def test_registration_rejects_a_weak_password(client, department):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "weak.user",
            "password": "abcdefgh",  # no digit
            "first_name": "Weak",
            "last_name": "User",
            "email": "weak@example.com",
            "phone": "9876500124",
            "department_id": department.id,
        },
    )
    assert response.status_code == 400
    assert "number" in response.get_json()["error"]


def test_registration_rejects_a_duplicate_username(client, users, department):
    response = client.post(
        "/api/auth/register",
        json={
            "username": "admin.user",
            "password": "Password123",
            "first_name": "Copy",
            "last_name": "Cat",
            "email": "copy@example.com",
            "phone": "9876500125",
            "department_id": department.id,
        },
    )
    assert response.status_code == 400


def test_change_password_requires_the_current_one(as_employee):
    response = as_employee.post(
        "/api/auth/change-password",
        json={"oldPassword": "wrong1234", "newPassword": "Brandnew123"},
    )
    assert response.status_code == 400


def test_change_password_then_login_with_it(as_employee, client):
    assert as_employee.post(
        "/api/auth/change-password",
        json={"oldPassword": PASSWORD, "newPassword": "Brandnew123"},
    ).status_code == 200

    as_employee.post("/api/auth/logout")
    assert login(as_employee, "employee.one", "Brandnew123").status_code == 200
