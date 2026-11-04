from datetime import datetime

from ..extensions import db

PRIORITIES = ("Low", "Medium", "High", "Urgent")


class Task(db.Model):
    __tablename__ = "tasks"
    __table_args__ = (db.CheckConstraint("estimated_hours > 0", name="ck_task_estimated_hours_positive"),)

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    notes = db.Column(db.Text)
    priority = db.Column(db.Enum(*PRIORITIES, name="task_priority"), nullable=False, default="Medium")
    estimated_hours = db.Column(db.Numeric(6, 2))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    is_deleted = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignments = db.relationship("TaskAssignment", back_populates="task", cascade="all, delete-orphan")

    def to_dict(self, assignment_count=None):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "notes": self.notes,
            "priority": self.priority,
            "estimated_hours": float(self.estimated_hours) if self.estimated_hours is not None else None,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if assignment_count is not None:
            data["assignment_count"] = assignment_count
        return data
