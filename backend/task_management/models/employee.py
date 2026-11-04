from datetime import date, datetime

from ..extensions import db


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False)
    employee_code = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    position = db.Column(db.String(80))
    hire_date = db.Column(db.Date, default=date.today)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship("User", back_populates="employee")
    department = db.relationship("Department", back_populates="employees")
    assignments = db.relationship("TaskAssignment", back_populates="employee", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "department_id": self.department_id,
            "employee_code": self.employee_code,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone": self.phone,
            "position": self.position,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "department_name": self.department.name if self.department else None,
            "username": self.user.username if self.user else None,
            "role": self.user.role if self.user else None,
            "is_locked": self.user.is_locked if self.user else False,
            "last_login_at": (
                self.user.last_login_at.isoformat() if self.user and self.user.last_login_at else None
            ),
        }
