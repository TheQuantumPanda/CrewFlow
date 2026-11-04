from datetime import datetime

from sqlalchemy.orm import joinedload

from ..extensions import db
from ..models import Employee, Task, TaskAssignment
from .activity_service import log as log_activity
from .errors import AssignmentError

STATUSES = ("Pending", "In Progress", "Completed", "On Hold", "Cancelled")


def assign_task_to_employee(task_id, employee_id, actor_id):
    task = db.session.get(Task, task_id)
    if not task or task.is_deleted:
        raise AssignmentError("Task not found", 404)

    employee = db.session.get(Employee, employee_id)
    if not employee or not employee.is_active:
        raise AssignmentError("Employee not found", 404)

    if TaskAssignment.query.filter_by(task_id=task_id, employee_id=employee_id).first():
        raise AssignmentError("This task is already assigned to that employee")

    assignment = TaskAssignment(task_id=task_id, employee_id=employee_id)
    db.session.add(assignment)
    db.session.commit()

    log_activity(actor_id, "CREATE", "assignment", assignment.id, None, assignment.to_dict())
    return assignment


def get_assignment(assignment_id):
    assignment = db.session.get(TaskAssignment, assignment_id)
    if not assignment:
        raise AssignmentError("Assignment not found", 404)
    return assignment


def update_assignment_status(assignment_id, fields, actor_id):
    assignment = get_assignment(assignment_id)

    before = assignment.to_dict()

    if fields.get("status") is not None:
        if fields["status"] not in STATUSES:
            raise AssignmentError(f"Status must be one of: {', '.join(STATUSES)}")
        assignment.status = fields["status"]

    if fields.get("completion_percentage") is not None:
        try:
            pct = int(fields["completion_percentage"])
        except (TypeError, ValueError):
            raise AssignmentError("completion_percentage must be a whole number") from None
        if pct < 0 or pct > 100:
            raise AssignmentError("completion_percentage must be between 0 and 100")
        assignment.completion_percentage = pct

    if fields.get("remarks") is not None:
        assignment.remarks = fields["remarks"]

    if assignment.status == "Completed":
        assignment.completion_percentage = 100

    assignment.updated_at = datetime.utcnow()
    db.session.commit()

    log_activity(actor_id, "UPDATE", "assignment", assignment.id, before, assignment.to_dict())
    return assignment


def remove_assignment(assignment_id, actor_id):
    assignment = get_assignment(assignment_id)

    before = assignment.to_dict()
    db.session.delete(assignment)
    db.session.commit()

    log_activity(actor_id, "DELETE", "assignment", assignment_id, before, None)
    return True


def get_assignments_for_employee(employee_id):
    assignments = (
        TaskAssignment.query.options(joinedload(TaskAssignment.task))
        .filter_by(employee_id=employee_id)
        .order_by(TaskAssignment.assigned_at.desc())
        .all()
    )
    return [a.to_dict_with_task() for a in assignments]


def _in_department(query, department_id):
    if department_id is None:
        return query
    return query.join(Employee, TaskAssignment.employee_id == Employee.id).filter(
        Employee.department_id == department_id
    )


def get_assignments_for_task(task_id, department_id=None):
    query = TaskAssignment.query.options(joinedload(TaskAssignment.employee)).filter_by(task_id=task_id)
    assignments = _in_department(query, department_id).all()
    return [a.to_dict_with_employee() for a in assignments]


def list_all_assignments(department_id=None):
    query = TaskAssignment.query.options(
        joinedload(TaskAssignment.task), joinedload(TaskAssignment.employee)
    )
    assignments = _in_department(query, department_id).order_by(TaskAssignment.assigned_at.desc()).all()
    results = []
    for a in assignments:
        data = a.to_dict_with_employee()
        task = a.task
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
        results.append(data)
    return results
