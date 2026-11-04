"""Shared fixtures. Every test gets a fresh in-memory SQLite database, so the
suite needs no server, no MySQL, and no cleanup between tests."""
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from task_management import create_app  # noqa: E402
from task_management.config import TestingConfig  # noqa: E402
from task_management.extensions import db  # noqa: E402
from task_management.models import Department, Employee, User  # noqa: E402
from task_management.permissions import CONSOLE_ROLES  # noqa: E402
from task_management.services.passwords import hash_password  # noqa: E402

PASSWORD = "Password123"


@pytest.fixture
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def make_user(username, role, department=None, employee=True):
    user = User(username=username, password_hash=hash_password(PASSWORD), role=role)
    db.session.add(user)
    db.session.flush()

    if employee:
        db.session.add(
            Employee(
                user_id=user.id,
                department_id=department.id,
                employee_code=f"{role[:3].upper()}-{user.id:03d}",
                first_name=username.capitalize(),
                last_name="Test",
                email=f"{username}@example.com",
                phone="9876500000",
                position="Tester",
            )
        )
    db.session.commit()
    return user


@pytest.fixture
def department(app):
    dept = Department(name="Engineering", description="Builds things")
    db.session.add(dept)
    db.session.commit()
    return dept


@pytest.fixture
def users(app, department):
    return {
        "admin": make_user("admin.user", "admin", department),
        "manager": make_user("manager.user", "manager", department),
        "employee": make_user("employee.one", "employee", department),
        "other": make_user("employee.two", "employee", department),
    }


def login(client, username, password=PASSWORD):
    """Signs in through the right door for the account's role, and wires up the
    CSRF header the way the browser client does: read the double-submit cookie,
    echo it back on every mutating call."""
    user = User.query.filter_by(username=username).first()
    door = "/api/auth/admin/login" if user and user.role in CONSOLE_ROLES else "/api/auth/login"
    response = client.post(door, json={"username": username, "password": password})
    cookie = client.get_cookie("taskforge_csrf")
    if cookie is not None:
        client.environ_base["HTTP_X_CSRF_TOKEN"] = cookie.value
    return response


def _signed_in_client(app, username):
    """Each role gets its own client with its own cookie jar — sharing one
    would mean the last fixture to run silently owns the session, and a test
    that exercises two roles at once would quietly test the same role twice."""
    client = app.test_client()
    login(client, username)
    return client


@pytest.fixture
def as_admin(app, users):
    return _signed_in_client(app, "admin.user")


@pytest.fixture
def as_manager(app, users):
    return _signed_in_client(app, "manager.user")


@pytest.fixture
def as_employee(app, users):
    return _signed_in_client(app, "employee.one")
