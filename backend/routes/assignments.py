"""
Assignment management routes.

Endpoints:
  POST   /api/classes/<cid>/assignments              — Create assignment (teacher)
  PUT    /api/classes/<cid>/assignments/<aid>         — Edit assignment (teacher)
  DELETE /api/classes/<cid>/assignments/<aid>         — Delete assignment (teacher)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from extensions import db
from models import Class, Assignment
from utils import teacher_required
from decorators import validate_json, handle_db_errors
from datetime import datetime, timezone

assignments_bp = Blueprint("assignments", __name__)


def _parse_date(date_str):
    """Parse an ISO date string into a datetime object."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


# ──────────────────────────────────────────────
# POST /api/classes/<cid>/assignments
# ──────────────────────────────────────────────
@assignments_bp.route("", methods=["POST"])
@teacher_required
@validate_json("title")
@handle_db_errors
def create_assignment(class_id, data):
    user_id = int(get_jwt_identity())
    cls = db.session.get(Class, class_id)

    if not cls:
        return jsonify({"error": "Class not found"}), 404
    if cls.owner_id != user_id:
        return jsonify({"error": "Only the class owner can create assignments"}), 403

    assignment = Assignment(
        title=data["title"].strip(),
        description=data.get("description", "").strip() or None,
        due_date=_parse_date(data.get("dueDate")),
        class_id=class_id,
    )
    db.session.add(assignment)
    db.session.commit()

    return jsonify({
        "message": "Assignment created",
        "assignment": assignment.to_dict(),
    }), 201


# ──────────────────────────────────────────────
# PUT /api/classes/<cid>/assignments/<aid>
# ──────────────────────────────────────────────
@assignments_bp.route("/<int:assignment_id>", methods=["PUT"])
@teacher_required
@handle_db_errors
def update_assignment(class_id, assignment_id):
    user_id = int(get_jwt_identity())
    cls = db.session.get(Class, class_id)
    if not cls or cls.owner_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment or assignment.class_id != class_id:
        return jsonify({"error": "Assignment not found"}), 404

    data = request.get_json() or {}
    if "title" in data:
        assignment.title = data["title"].strip()
    if "description" in data:
        assignment.description = data["description"].strip() or None
    if "dueDate" in data:
        assignment.due_date = _parse_date(data["dueDate"])

    db.session.commit()
    return jsonify({
        "message": "Assignment updated",
        "assignment": assignment.to_dict(),
    }), 200


# ──────────────────────────────────────────────
# DELETE /api/classes/<cid>/assignments/<aid>
# ──────────────────────────────────────────────
@assignments_bp.route("/<int:assignment_id>", methods=["DELETE"])
@teacher_required
@handle_db_errors
def delete_assignment(class_id, assignment_id):
    user_id = int(get_jwt_identity())
    cls = db.session.get(Class, class_id)
    if not cls or cls.owner_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment or assignment.class_id != class_id:
        return jsonify({"error": "Assignment not found"}), 404

    db.session.delete(assignment)
    db.session.commit()
    return jsonify({"message": "Assignment deleted"}), 200
