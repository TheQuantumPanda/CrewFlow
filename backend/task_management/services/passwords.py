"""Password hashing and policy, in one place so every creation path — signup,
admin-created accounts, and password changes — enforces the same rules."""
import re
import secrets

from flask import current_app
from werkzeug.security import check_password_hash, generate_password_hash

from .errors import AuthError

_DUMMY_HASH = None


def hash_password(password):
    return generate_password_hash(password, method="scrypt")


def verify_password(password_hash, password):
    return check_password_hash(password_hash, password)


def validate_password(password):
    """Raises AuthError when the value doesn't meet the configured policy."""
    minimum = current_app.config["MIN_PASSWORD_LENGTH"]
    if not password or len(password) < minimum:
        raise AuthError(f"Password must be at least {minimum} characters")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise AuthError("Password must contain at least one letter and one number")
    return password


def dummy_verify(password):
    """Burns the same work a real check costs, so a login attempt against a
    username that doesn't exist doesn't return measurably faster — that timing
    gap is itself a username oracle."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_hex(16))
    check_password_hash(_DUMMY_HASH, str(password))
