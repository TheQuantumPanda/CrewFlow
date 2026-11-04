from flask import Blueprint, g, jsonify, request

from ..auth_decorators import (
    current_employee,
    in_scope,
    login_required,
    permission_required,
    scope_department,
)
from ..permissions import can
from ..services import employee_service
from ..services.errors import EmployeeError

employee_bp = Blueprint("employee", __name__)


@employee_bp.route("", methods=["POST"])
@permission_required("people.manage")
def create_employee():
    body = request.get_json(silent=True) or {}
    body.pop("user_id", None)  # linking to an existing login is internal-only
    body["role"] = body.get("role") or "employee"
    employee_service.authorize_people_change(
        g.current_user, department_id=body.get("department_id"), new_role=body["role"]
    )
    employee = employee_service.create_employee(body, g.current_user.id)
    return jsonify({"employee": employee.to_dict()}), 201


@employee_bp.route("", methods=["GET"])
@permission_required("people.view")
def list_employees():
    employees = employee_service.list_employees(scope_department())
    return jsonify({"employees": [e.to_dict() for e in employees]})


@employee_bp.route("/department/<int:department_id>", methods=["GET"])
@permission_required("people.view")
def list_by_department(department_id):
    if not in_scope(department_id):
        return jsonify({"error": "You can only view your own department"}), 403
    employees = employee_service.list_employees_by_department(department_id)
    return jsonify({"employees": [e.to_dict() for e in employees]})


@employee_bp.route("/<int:employee_id>", methods=["GET"])
@login_required
def get_employee(employee_id):
    mine = current_employee()
    employee = employee_service.get_employee(employee_id)
    is_self = mine is not None and mine.id == employee_id
    if not is_self and not (can(g.current_user.role, "people.view") and in_scope(employee.department_id)):
        return jsonify({"error": "You can only view your own profile"}), 403
    return jsonify({"employee": employee.to_dict()})


@employee_bp.route("/<int:employee_id>", methods=["PUT"])
@permission_required("people.manage")
def update_employee(employee_id):
    body = request.get_json(silent=True) or {}
    body.pop("role", None)  # role changes go through their own audited endpoint
    target = employee_service.get_employee(employee_id)
    employee_service.authorize_people_change(
        g.current_user, department_id=body.get("department_id"), target=target
    )
    employee = employee_service.update_employee(employee_id, body, g.current_user.id)
    return jsonify({"employee": employee.to_dict()})


@employee_bp.route("/<int:employee_id>/role", methods=["PUT"])
@permission_required("people.manage")
def change_role(employee_id):
    new_role = (request.get_json(silent=True) or {}).get("role")
    if not new_role:
        return jsonify({"error": "role is required"}), 400
    target = employee_service.get_employee(employee_id)
    employee_service.authorize_people_change(g.current_user, target=target, new_role=new_role)
    employee = employee_service.change_role(employee_id, new_role, g.current_user.id)
    return jsonify({"employee": employee.to_dict()})


@employee_bp.route("/<int:employee_id>/unlock", methods=["POST"])
@permission_required("people.manage")
def unlock(employee_id):
    target = employee_service.get_employee(employee_id)
    employee_service.authorize_people_change(g.current_user, target=target)
    return jsonify({"employee": employee_service.unlock(employee_id, g.current_user.id).to_dict()})


@employee_bp.route("/<int:employee_id>", methods=["DELETE"])
@permission_required("people.manage")
def delete_employee(employee_id):
    target = employee_service.get_employee(employee_id)
    employee_service.authorize_people_change(g.current_user, target=target)
    try:
        employee_service.delete_employee(employee_id, g.current_user.id)
        return jsonify({"ok": True})
    except EmployeeError as err:
        return jsonify({"error": err.message}), err.status
