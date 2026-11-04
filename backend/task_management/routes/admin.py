from flask import Blueprint, jsonify

from ..auth_decorators import permission_required
from ..permissions import matrix

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/roles", methods=["GET"])
@permission_required("people.view")
def roles():
    return jsonify(matrix())
