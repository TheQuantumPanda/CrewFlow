from datetime import datetime

from ..extensions import db
from ..models import Task, TaskAssignment
from .activity_service import log as log_activity
from .errors import TaskError

PRIORITIES = ("Low", "Medium", "High", "Urgent")
UPDATABLE_FIELDS = ["title", "description", "notes", "priority", "estimated_hours"]


def create_task(fields, created_by):
    title = (fields.get("title") or "").strip()
    if not title:
        raise TaskError("Title is required")

    priority = fields.get("priority") or "Medium"
    if priority not in PRIORITIES:
        raise TaskError(f"Priority must be one of: {', '.join(PRIORITIES)}")

    estimated_hours = fields.get("estimated_hours")
    if estimated_hours not in (None, "") and float(estimated_hours) <= 0:
        raise TaskError("Estimated hours must be a positive number")

    task = Task(
        title=title,
        description=fields.get("description") or "",
        notes=fields.get("notes") or "",
        priority=priority,
        estimated_hours=estimated_hours or None,
        created_by=created_by,
    )
    db.session.add(task)
    db.session.commit()

    log_activity(created_by, "CREATE", "task", task.id, None, task.to_dict())
    return task


def get_task(task_id):
    task = db.session.get(Task, task_id)
    if not task or task.is_deleted:
        raise TaskError("Task not found", 404)
    return task


def update_task(task_id, fields, actor_id):
    task = get_task(task_id)
    before = task.to_dict()

    if "priority" in fields and fields["priority"] and fields["priority"] not in PRIORITIES:
        raise TaskError(f"Priority must be one of: {', '.join(PRIORITIES)}")
    if fields.get("estimated_hours") not in (None, "") and "estimated_hours" in fields:
        if float(fields["estimated_hours"]) <= 0:
            raise TaskError("Estimated hours must be a positive number")

    for key in UPDATABLE_FIELDS:
        if key in fields and fields[key] is not None:
            setattr(task, key, fields[key] if fields[key] != "" else None)
    task.updated_at = datetime.utcnow()

    db.session.commit()
    log_activity(actor_id, "UPDATE", "task", task.id, before, task.to_dict())
    return task


def delete_task(task_id, actor_id):
    task = get_task(task_id)
    before = task.to_dict()

    task.is_deleted = True
    task.updated_at = datetime.utcnow()
    TaskAssignment.query.filter_by(task_id=task_id).delete()
    db.session.commit()

    log_activity(actor_id, "DELETE", "task", task_id, before, None)
    return True


def list_tasks(filters=None, page=1, per_page=100):
    """Returns `(tasks, total)`, each task already carrying its assignment count.

    The counts come from a single GROUP BY rather than one COUNT per row —
    the previous per-task query made the backlog screen O(n) round trips.
    """
    filters = filters or {}
    query = Task.query.filter_by(is_deleted=False)

    if filters.get("priority"):
        query = query.filter(Task.priority == filters["priority"])
    if filters.get("created_by"):
        query = query.filter(Task.created_by == filters["created_by"])
    if filters.get("search"):
        needle = f"%{filters['search'].strip()}%"
        query = query.filter(db.or_(Task.title.ilike(needle), Task.description.ilike(needle)))
    if filters.get("status"):
        query = query.filter(
            Task.id.in_(
                db.session.query(TaskAssignment.task_id).filter(
                    TaskAssignment.status == filters["status"]
                )
            )
        )

    total = query.order_by(None).count()
    page = max(1, page)
    tasks = (
        query.order_by(Task.created_at.desc())
        .limit(per_page)
        .offset((page - 1) * per_page)
        .all()
    )

    counts = dict(
        db.session.query(TaskAssignment.task_id, db.func.count(TaskAssignment.id))
        .filter(TaskAssignment.task_id.in_([t.id for t in tasks] or [0]))
        .group_by(TaskAssignment.task_id)
        .all()
    )

    return [t.to_dict(assignment_count=counts.get(t.id, 0)) for t in tasks], total
