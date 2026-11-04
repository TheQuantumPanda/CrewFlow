from datetime import datetime

from ..extensions import db

STATUSES = ("Pending", "In Progress", "Completed", "On Hold", "Cancelled")


class TaskAssignment(db.Model):
    __tablename__ = "task_assignments"
    __table_args__ = (
        db.CheckConstraint(
            "completion_percentage >= 0 AND completion_percentage <= 100",
            name="ck_assignment_completion_range",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    status = db.Column(db.Enum(*STATUSES, name="assignment_status"), nullable=False, default="Pending")
    completion_percentage = db.Column(db.Integer, nullable=False, default=0)
    remarks = db.Column(db.Text)
    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    task = db.relationship("Task", back_populates="assignments")
    employee = db.relationship("Employee", back_populates="assignments")

    def to_dict(self):
        return {
            "id": self.id,
            "task_id": self.task_id,
            "employee_id": self.employee_id,
            "status": self.status,
            "completion_percentage": self.completion_percentage,
            "remarks": self.remarks,
            "assigned_at": self.assigned_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_dict_with_task(self):
        data = self.to_dict()
        task = self.task
        data.update(
            {
                "task_title": task.title if task else None,
                "task_description": task.description if task else None,
                "task_priority": task.priority if task else None,
                "task_estimated_hours": float(task.estimated_hours)
                if task and task.estimated_hours is not None
                else None,
            }
        )
        return data

    def to_dict_with_employee(self):
        data = self.to_dict()
        employee = self.employee
        data.update(
            {
                "employee_name": f"{employee.first_name} {employee.last_name}" if employee else None,
                "employee_code": employee.employee_code if employee else None,
            }
        )
        return data
