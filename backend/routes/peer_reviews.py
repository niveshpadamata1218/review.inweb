"""
Peer Review routes.

Endpoints:
  POST /api/classes/<cid>/assignments/<aid>/submissions/<sid>/peer-reviews  — Submit peer review
  GET  /api/peer-reviews/pending                                            — List all pending review targets for student
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from extensions import db
from models import Class, Assignment, Submission, PeerReview, User
from utils import student_required
from decorators import validate_json, handle_db_errors

peer_reviews_bp = Blueprint("peer_reviews", __name__)


# ──────────────────────────────────────────────
# POST .../submissions/<sid>/peer-reviews
# ──────────────────────────────────────────────
@peer_reviews_bp.route("", methods=["POST"])
@student_required
@validate_json("content")
@handle_db_errors
def create_peer_review(class_id, assignment_id, submission_id, data):
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    cls = db.session.get(Class, class_id)

    if not cls:
        return jsonify({"error": "Class not found"}), 404
    if user not in cls.students:
        return jsonify({"error": "Not enrolled in this class"}), 403

    submission = db.session.get(Submission, submission_id)
    if (
        not submission
        or submission.assignment_id != assignment_id
        or submission.assignment.class_id != class_id
    ):
        return jsonify({"error": "Submission not found"}), 404

    # Cannot review own submission
    if submission.student_id == user_id:
        return jsonify({"error": "Cannot review your own submission"}), 400

    # Check for duplicate review
    existing = PeerReview.query.filter_by(
        reviewer_id=user_id, submission_id=submission_id
    ).first()
    if existing:
        return jsonify({"error": "You have already reviewed this submission"}), 409

    review = PeerReview(
        content=data["content"].strip(),
        reviewer_id=user_id,
        submission_id=submission_id,
    )
    db.session.add(review)
    db.session.commit()

    return jsonify({
        "message": "Peer review submitted",
        "peerReview": review.to_dict(),
    }), 201


# ──────────────────────────────────────────────
# Standalone blueprint for pending reviews across all classes
# ──────────────────────────────────────────────

pending_reviews_bp = Blueprint("pending_reviews", __name__)


@pending_reviews_bp.route("/pending", methods=["GET"])
@student_required
def get_pending_reviews():
    """
    Return all submissions from classmates (not own) across all joined classes
    that the current student has NOT yet reviewed.
    """
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    pending = []

    for cls in user.enrolled_classes:
        for assignment in cls.assignments:
            for submission in assignment.submissions:
                # Skip own submissions
                if submission.student_id == user_id:
                    continue
                # Skip if already reviewed
                already_reviewed = PeerReview.query.filter_by(
                    reviewer_id=user_id, submission_id=submission.id
                ).first()
                if already_reviewed:
                    continue

                pending.append({
                    "class": {"id": cls.id, "name": cls.name},
                    "assignment": {"id": assignment.id, "title": assignment.title},
                    "submission": submission.to_dict(),
                })

    return jsonify({"pending": pending}), 200
