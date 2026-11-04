from flask import Blueprint, g, jsonify, request

from ..auth_decorators import (
    current_employee,
    in_scope,
    login_required,
    permission_required,
    scope_department,
)
from ..permissions import can
from ..services import assignment_service, employee_service
from ..services.errors import AssignmentError

assignment_bp = Blueprint("assignment", __name__)


def _manages(employee_id):
    """Holds assignments.manage and the employee is inside the actor's scope."""
    if not can(g.current_user.role, "assignments.manage"):
        return False
    return in_scope(employee_service.get_employee(employee_id).department_id)


def _sees(employee_id):
    if not can(g.current_user.role, "assignments.view_all"):
        return False
    return in_scope(employee_service.get_employee(employee_id).department_id)


def _owns(employee_id):
    employee = current_employee()
    return employee is not None and employee.id == employee_id


@assignment_bp.route("", methods=["POST"])
@permission_required("assignments.manage")
def create_assignment():
    body = request.get_json(silent=True) or {}
    task_id, employee_id = body.get("task_id"), body.get("employee_id")
    if not task_id or not employee_id:
        return jsonify({"error": "task_id and employee_id are required"}), 400
    if not _manages(employee_id):
        return jsonify({"error": "You can only assign work inside your own department"}), 403

    try:
        assignment = assignment_service.assign_task_to_employee(task_id, employee_id, g.current_user.id)
        return jsonify({"assignment": assignment.to_dict()}), 201
    except AssignmentError as err:
        return jsonify({"error": err.message}), err.status


@assignment_bp.route("/<int:assignment_id>/status", methods=["PUT"])
@login_required
def update_status(assignment_id):
    try:
        assignment = assignment_service.get_assignment(assignment_id)
        # An employee may move their own work along, and nobody else's.
        if not _owns(assignment.employee_id) and not _manages(assignment.employee_id):
            return jsonify({"error": "You can only update tasks assigned to you"}), 403

        updated = assignment_service.update_assignment_status(
            assignment_id, request.get_json(silent=True) or {}, g.current_user.id
        )
        return jsonify({"assignment": updated.to_dict()})
    except AssignmentError as err:
        return jsonify({"error": err.message}), err.status


@assignment_bp.route("/<int:assignment_id>", methods=["DELETE"])
@permission_required("assignments.manage")
def delete_assignment(assignment_id):
    try:
        if not _manages(assignment_service.get_assignment(assignment_id).employee_id):
            return jsonify({"error": "You can only unassign work inside your own department"}), 403
        assignment_service.remove_assignment(assignment_id, g.current_user.id)
        return jsonify({"ok": True})
    except AssignmentError as err:
        return jsonify({"error": err.message}), err.status


@assignment_bp.route("/employee/<int:employee_id>", methods=["GET"])
@login_required
def by_employee(employee_id):
    if not _owns(employee_id) and not _sees(employee_id):
        return jsonify({"error": "You can only view your own assignments"}), 403
    return jsonify({"assignments": assignment_service.get_assignments_for_employee(employee_id)})


@assignment_bp.route("/task/<int:task_id>", methods=["GET"])
@permission_required("assignments.view_all")
def by_task(task_id):
    return jsonify({"assignments": assignment_service.get_assignments_for_task(task_id, scope_department())})


@assignment_bp.route("", methods=["GET"])
@permission_required("assignments.view_all")
def list_all():
    return jsonify({"assignments": assignment_service.list_all_assignments(scope_department())})


@assignment_bp.route("/mine", methods=["GET"])
@login_required
def mine():
    """The employee dashboard's own view — avoids the client having to know
    its own employee id before it can ask for anything."""
    employee = current_employee()
    if not employee:
        return jsonify({"assignments": []})
    return jsonify({"assignments": assignment_service.get_assignments_for_employee(employee.id)})
