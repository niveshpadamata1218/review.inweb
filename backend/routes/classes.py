"""
Class management routes.

Endpoints:
  POST   /api/classes              — Create class (teacher)
  GET    /api/classes              — List classes (filtered by role query param)
  GET    /api/classes/<id>         — Get class detail
  DELETE /api/classes/<id>         — Delete class (teacher/owner)
  POST   /api/classes/join         — Join class (student, body: classId + passcode)
  POST   /api/classes/<id>/leave   — Leave class (student)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Class, User, class_students
from utils import teacher_required, student_required
from decorators import validate_json, handle_db_errors

classes_bp = Blueprint("classes", __name__)


# ──────────────────────────────────────────────
# POST /api/classes  — create a new classroom
# ──────────────────────────────────────────────
@classes_bp.route("", methods=["POST"])
@teacher_required
@validate_json("name", "subject")
@handle_db_errors
def create_class(data):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    new_class = Class(
        name=data["name"].strip(),
        subject=data["subject"].strip(),
        grade=data.get("grade", "").strip() or None,
        description=data.get("description", "").strip() or None,
        owner_id=user_id,
    )
    db.session.add(new_class)
    db.session.commit()

    return jsonify({
        "message": "Class created successfully",
        "class": new_class.to_dict(include_passcode=True),
    }), 201


# ──────────────────────────────────────────────
# GET /api/classes  — list classes for current user
# Query params:
#   role=teacher  → classes the teacher owns
#   role=student  → classes the student has joined
# ──────────────────────────────────────────────
@classes_bp.route("", methods=["GET"])
@jwt_required()
def list_classes():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    role_filter = request.args.get("role", user.role)

    if role_filter == "teacher":
        classes = Class.query.filter_by(owner_id=user_id).order_by(Class.created_at.desc()).all()
        return jsonify({
            "classes": [c.to_dict(include_passcode=True, include_assignments=True, include_students=True) for c in classes]
        }), 200
    else:
        classes = user.enrolled_classes.order_by(Class.created_at.desc()).all()
        return jsonify({
            "classes": [c.to_dict(include_assignments=True) for c in classes]
        }), 200


# ──────────────────────────────────────────────
# GET /api/classes/<id>  — single class detail
# ──────────────────────────────────────────────
@classes_bp.route("/<int:class_id>", methods=["GET"])
@jwt_required()
def get_class(class_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    cls = db.session.get(Class, class_id)
    if not cls:
        return jsonify({"error": "Class not found"}), 404

    is_owner = cls.owner_id == user_id
    is_student = user in cls.students

    if not is_owner and not is_student:
        return jsonify({"error": "Access denied"}), 403

    return jsonify({
        "class": cls.to_dict(
            include_passcode=is_owner,
            include_students=is_owner,
            include_assignments=True,
        )
    }), 200


# ──────────────────────────────────────────────
# DELETE /api/classes/<id>  — delete class (owner only)
# ──────────────────────────────────────────────
@classes_bp.route("/<int:class_id>", methods=["DELETE"])
@teacher_required
@handle_db_errors
def delete_class(class_id):
    user_id = int(get_jwt_identity())
    cls = db.session.get(Class, class_id)
    if not cls:
        return jsonify({"error": "Class not found"}), 404
    if cls.owner_id != user_id:
        return jsonify({"error": "Only the class owner can delete it"}), 403

    db.session.delete(cls)
    db.session.commit()
    return jsonify({"message": "Class deleted successfully"}), 200


# ──────────────────────────────────────────────
# POST /api/classes/join  — student joins a class
# Body: { "classId": int, "passcode": str }
# ──────────────────────────────────────────────
@classes_bp.route("/join", methods=["POST"])
@student_required
@validate_json("classId", "passcode")
@handle_db_errors
def join_class(data):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)

    cls = db.session.get(Class, data["classId"])
    if not cls:
        return jsonify({"error": "Class not found"}), 404

    if cls.passcode != data["passcode"].strip():
        return jsonify({"error": "Invalid passcode"}), 401

    if user in cls.students:
        return jsonify({"error": "Already enrolled in this class"}), 409

    cls.students.append(user)
    db.session.commit()

    return jsonify({
        "message": "Joined class successfully",
        "class": cls.to_dict(),
    }), 200


# ──────────────────────────────────────────────
# POST /api/classes/<id>/leave  — student leaves a class
# ──────────────────────────────────────────────
@classes_bp.route("/<int:class_id>/leave", methods=["POST"])
@student_required
@handle_db_errors
def leave_class(class_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    cls = db.session.get(Class, class_id)
    if not cls:
        return jsonify({"error": "Class not found"}), 404
    if user not in cls.students:
        return jsonify({"error": "Not enrolled in this class"}), 400

    cls.students.remove(user)
    db.session.commit()

    return jsonify({"message": "Left class successfully"}), 200
