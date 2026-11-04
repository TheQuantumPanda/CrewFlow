from flask import Blueprint, g, jsonify, request

from ..auth_decorators import login_required, permission_required
from ..services import employee_service
from ..services.errors import EmployeeError

department_bp = Blueprint("department", __name__)


@department_bp.route("", methods=["GET"])
@login_required
def list_departments():
    departments = employee_service.list_departments()
    return jsonify({"departments": [d.to_dict() for d in departments]})


@department_bp.route("", methods=["POST"])
@permission_required("departments.manage")
def create_department():
    try:
        department = employee_service.create_department(request.get_json(silent=True) or {}, g.current_user.id)
        return jsonify({"department": department.to_dict()}), 201
    except EmployeeError as err:
        return jsonify({"error": err.message}), err.status
