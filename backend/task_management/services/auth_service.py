import re

from flask import current_app

from ..extensions import db
from ..models import Department, Employee, User
from ..permissions import CONSOLE_ROLES
from . import employee_service
from .activity_service import log as log_activity
from .errors import AuthError
from .passwords import dummy_verify, hash_password, validate_password, verify_password

USERNAME_RE = re.compile(r"^[a-zA-Z0-9._-]{3,30}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^[0-9+()\-\s]{7,20}$")

REGISTER_FIELDS = ["username", "password", "first_name", "last_name", "email", "phone", "department_id"]

# A generic message for every credential failure, so the endpoint can't be
# used to enumerate which usernames exist.
INVALID_CREDENTIALS = "Invalid username or password"


def authenticate_user(username, password, console=False):
    """Checks credentials, then the door: admins sign in only through the
    console (`console=True`), everyone else only through the workspace login.
    The door is checked after the password so it reveals nothing to a guesser."""
    user = User.query.filter(db.func.lower(User.username) == str(username).strip().lower()).first()

    if not user or not user.is_active:
        # Verify against a throwaway hash anyway, so a missing user doesn't
        # return measurably faster than a wrong password — that timing gap is
        # itself a username oracle.
        dummy_verify(password)
        raise AuthError(INVALID_CREDENTIALS, 401)

    if user.is_locked:
        minutes = max(1, round(user.lock_seconds_remaining / 60))
        raise AuthError(
            f"Too many failed attempts. Try again in about {minutes} minute(s).", 429
        )

    if not verify_password(user.password_hash, password):
        user.register_failed_login(
            current_app.config["MAX_FAILED_LOGINS"],
            current_app.config["LOCKOUT_MINUTES"],
        )
        db.session.commit()
        raise AuthError(INVALID_CREDENTIALS, 401)

    if console and user.role not in CONSOLE_ROLES:
        log_activity(user.id, "CONSOLE_DENIED", "user", user.id)
        raise AuthError("This account does not have admin console access", 403)
    if not console and user.role in CONSOLE_ROLES:
        raise AuthError("Admin accounts sign in through the admin console", 403)

    user.register_successful_login()
    db.session.commit()

    log_activity(user.id, "ADMIN_LOGIN" if console else "LOGIN", "user", user.id)
    return user


def register_user(fields):
    """Public self-service signup. Always creates a plain `employee` account —
    manager and admin accounts can only be created by an existing admin
    through the employee management screen."""
    missing = [f for f in REGISTER_FIELDS if not fields.get(f)]
    if missing:
        verb = "are" if len(missing) > 1 else "is"
        raise AuthError(f"{', '.join(missing)} {verb} required")

    username = str(fields["username"]).strip()
    email = str(fields["email"]).strip()
    phone = str(fields["phone"]).strip()
    password = str(fields["password"])

    if not USERNAME_RE.match(username):
        raise AuthError("Username must be 3-30 characters, using letters, numbers, dot, dash or underscore")
    validate_password(password)
    if not EMAIL_RE.match(email):
        raise AuthError("Please enter a valid email address")
    if not PHONE_RE.match(phone):
        raise AuthError("Please enter a valid phone number")
    if User.query.filter(db.func.lower(User.username) == username.lower()).first():
        raise AuthError("That username is already taken")
    if Employee.query.filter(db.func.lower(Employee.email) == email.lower()).first():
        raise AuthError("An account with that email already exists")
    if not db.session.get(Department, _as_int(fields.get("department_id"))):
        raise AuthError("Please choose a valid department")

    user = User(username=username, password_hash=hash_password(password), role="employee")
    db.session.add(user)
    db.session.flush()

    try:
        employee_service.create_employee(
            {
                "user_id": user.id,
                "department_id": fields["department_id"],
                "employee_code": employee_service.generate_employee_code(fields["department_id"]),
                "first_name": str(fields["first_name"]).strip(),
                "last_name": str(fields["last_name"]).strip(),
                "email": email,
                "phone": phone,
                "position": (fields.get("position") or "").strip() or "Team Member",
            },
            user.id,
        )
    except Exception as err:
        # Don't leave an orphaned login behind if the profile couldn't be created.
        db.session.rollback()
        raise AuthError(getattr(err, "message", str(err))) from err

    log_activity(user.id, "REGISTER", "user", user.id)
    return user


def change_password(user_id, old_password, new_password):
    user = db.session.get(User, user_id)
    if not user:
        raise AuthError("User not found", 404)
    if not verify_password(user.password_hash, old_password):
        raise AuthError("Current password is incorrect")
    validate_password(new_password)
    if old_password == new_password:
        raise AuthError("New password must be different from the current one")

    user.password_hash = hash_password(new_password)
    db.session.commit()
    log_activity(user_id, "CHANGE_PASSWORD", "user", user_id)
    return True


def get_profile(user_id):
    user = db.session.get(User, user_id)
    if not user:
        raise AuthError("User not found", 404)

    profile = user.to_dict()
    if user.employee:
        profile["employee"] = user.employee.to_dict()
    return profile


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return -1
