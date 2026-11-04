from flask import Blueprint, g, jsonify, request

from ..auth_decorators import login_required, permission_required
from ..services import task_service
from ..services.errors import TaskError

task_bp = Blueprint("task", __name__)

@task_bp.route("", methods=["POST"])
@permission_required("tasks.manage")
def create_task():
    try:
        task = task_service.create_task(request.get_json(silent=True) or {}, g.current_user.id)
        return jsonify({"task": task.to_dict()}), 201
    except TaskError as err:
        return jsonify({"error": err.message}), err.status


@task_bp.route("", methods=["GET"])
@login_required
def list_tasks():
    filters = {
        "priority": request.args.get("priority"),
        "created_by": request.args.get("created_by", type=int),
        "status": request.args.get("status"),
        "search": request.args.get("search"),
    }
    page = request.args.get("page", default=1, type=int)
    per_page = min(request.args.get("per_page", default=100, type=int) or 100, 200)

    tasks, total = task_service.list_tasks(filters, page=page, per_page=per_page)
    return jsonify(
        {
            "tasks": tasks,
            "page": page,
            "per_page": per_page,
            "total": total,
        }
    )


@task_bp.route("/<int:task_id>", methods=["GET"])
@login_required
def get_task(task_id):
    try:
        return jsonify({"task": task_service.get_task(task_id).to_dict()})
    except TaskError as err:
        return jsonify({"error": err.message}), err.status


@task_bp.route("/<int:task_id>", methods=["PUT"])
@permission_required("tasks.manage")
def update_task(task_id):
    try:
        task = task_service.update_task(task_id, request.get_json(silent=True) or {}, g.current_user.id)
        return jsonify({"task": task.to_dict()})
    except TaskError as err:
        return jsonify({"error": err.message}), err.status


@task_bp.route("/<int:task_id>", methods=["DELETE"])
@permission_required("tasks.delete")
def delete_task(task_id):
    try:
        task_service.delete_task(task_id, g.current_user.id)
        return jsonify({"ok": True})
    except TaskError as err:
        return jsonify({"error": err.message}), err.status
