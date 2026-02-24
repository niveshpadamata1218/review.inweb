"""
Submission management routes.

Endpoints:
  POST   /api/classes/<cid>/assignments/<aid>/submissions              — Submit work (student)
  PUT    /api/classes/<cid>/assignments/<aid>/submissions/<sid>         — Edit submission (student)
  DELETE /api/classes/<cid>/assignments/<aid>/submissions/<sid>         — Withdraw submission (student)
  PUT    /api/classes/<cid>/assignments/<aid>/submissions/<sid>/grade   — Grade submission (teacher)
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Class, Assignment, Submission, User
from utils import teacher_required, student_required
from decorators import validate_json, handle_db_errors
from datetime import datetime, timezone

submissions_bp = Blueprint("submissions", __name__)


# ──────────────────────────────────────────────
# POST .../submissions — student submits work
# ──────────────────────────────────────────────
@submissions_bp.route("", methods=["POST"])
@student_required
@handle_db_errors
def create_submission(class_id, assignment_id):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    cls = db.session.get(Class, class_id)

    if not cls:
        return jsonify({"error": "Class not found"}), 404
    if user not in cls.students:
        return jsonify({"error": "Not enrolled in this class"}), 403

    assignment = db.session.get(Assignment, assignment_id)
    if not assignment or assignment.class_id != class_id:
        return jsonify({"error": "Assignment not found"}), 404

    # Check for existing submission
    existing = Submission.query.filter_by(
        student_id=user_id, assignment_id=assignment_id
    ).first()
    if existing:
        return jsonify({"error": "Already submitted. Use PUT to edit."}), 409

    data = request.get_json() or {}

    submission = Submission(
        content=data.get("content", "").strip() or None,
        file_name=data.get("fileName"),
        file_size=data.get("fileSize"),
        student_id=user_id,
        assignment_id=assignment_id,
    )
    db.session.add(submission)
    db.session.commit()

    return jsonify({
        "message": "Submission created",
        "submission": submission.to_dict(),
    }), 201


# ──────────────────────────────────────────────
# PUT .../submissions/<sid> — edit own submission
# ──────────────────────────────────────────────
@submissions_bp.route("/<int:submission_id>", methods=["PUT"])
@student_required
@handle_db_errors
def update_submission(class_id, assignment_id, submission_id):
    user_id = int(get_jwt_identity())

    submission = db.session.get(Submission, submission_id)
    if (
        not submission
        or submission.assignment_id != assignment_id
        or submission.assignment.class_id != class_id
    ):
        return jsonify({"error": "Submission not found"}), 404
    if submission.student_id != user_id:
        return jsonify({"error": "Cannot edit another student's submission"}), 403

    data = request.get_json() or {}
    if "content" in data:
        submission.content = data["content"].strip() or None
    if "fileName" in data:
        submission.file_name = data["fileName"]
    if "fileSize" in data:
        submission.file_size = data["fileSize"]

    submission.submitted_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": "Submission updated",
        "submission": submission.to_dict(),
    }), 200


# ──────────────────────────────────────────────
# DELETE .../submissions/<sid> — withdraw submission
# ──────────────────────────────────────────────
@submissions_bp.route("/<int:submission_id>", methods=["DELETE"])
@student_required
@handle_db_errors
def delete_submission(class_id, assignment_id, submission_id):
    user_id = int(get_jwt_identity())

    submission = db.session.get(Submission, submission_id)
    if (
        not submission
        or submission.assignment_id != assignment_id
        or submission.assignment.class_id != class_id
    ):
        return jsonify({"error": "Submission not found"}), 404
    if submission.student_id != user_id:
        return jsonify({"error": "Cannot withdraw another student's submission"}), 403

    db.session.delete(submission)
    db.session.commit()
    return jsonify({"message": "Submission withdrawn"}), 200


# ──────────────────────────────────────────────
# PUT .../submissions/<sid>/grade — teacher grades submission
# ──────────────────────────────────────────────
@submissions_bp.route("/<int:submission_id>/grade", methods=["PUT"])
@teacher_required
@validate_json("grade")
@handle_db_errors
def grade_submission(class_id, assignment_id, submission_id, data):
    user_id = int(get_jwt_identity())
    cls = db.session.get(Class, class_id)
    if not cls or cls.owner_id != user_id:
        return jsonify({"error": "Access denied"}), 403

    submission = db.session.get(Submission, submission_id)
    if (
        not submission
        or submission.assignment_id != assignment_id
        or submission.assignment.class_id != class_id
    ):
        return jsonify({"error": "Submission not found"}), 404

    submission.grade = str(data["grade"]).strip()
    submission.feedback = data.get("feedback", "").strip() or None
    submission.graded_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({
        "message": "Submission graded",
        "submission": submission.to_dict(),
    }), 200
