from datetime import datetime, timedelta

from ..extensions import db
from ..permissions import ROLES, grantable_roles, permissions_for


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum(*ROLES, name="user_role"), nullable=False, default="employee")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Brute-force protection. Kept on the row rather than in process memory so
    # the counter is shared across every gunicorn worker and survives restarts.
    failed_login_count = db.Column(db.Integer, nullable=False, default=0)
    locked_until = db.Column(db.DateTime)
    last_login_at = db.Column(db.DateTime)

    employee = db.relationship(
        "Employee", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > datetime.utcnow())

    @property
    def lock_seconds_remaining(self):
        if not self.is_locked:
            return 0
        return int((self.locked_until - datetime.utcnow()).total_seconds())

    def register_failed_login(self, max_attempts, lockout_minutes):
        self.failed_login_count = (self.failed_login_count or 0) + 1
        if self.failed_login_count >= max_attempts:
            self.locked_until = datetime.utcnow() + timedelta(minutes=lockout_minutes)
            self.failed_login_count = 0

    def register_successful_login(self):
        self.failed_login_count = 0
        self.locked_until = None
        self.last_login_at = datetime.utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "is_locked": self.is_locked,
            "permissions": permissions_for(self.role),
            "grantable_roles": grantable_roles(self.role),
        }
