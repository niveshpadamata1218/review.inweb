"""
Database models for ReviewIn application.

Models:
- User: teachers and students
- Class: classrooms owned by teachers
- ClassStudent: many-to-many link between classes and students
- Assignment: assignments within a class
- Submission: student submissions for an assignment
- PeerReview: peer reviews on submissions
"""

from datetime import datetime, timezone
from extensions import db
import uuid
import random
import string


def _utcnow():
    return datetime.now(timezone.utc)


def _generate_passcode():
    """Generate a 6-character alphanumeric passcode."""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ──────────────────────────────────────────────
# Association table: Class ↔ Student (many-to-many)
# ──────────────────────────────────────────────

class_students = db.Table(
    "class_students",
    db.Column("class_id", db.Integer, db.ForeignKey("classes.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("joined_at", db.DateTime, default=_utcnow),
)


# ──────────────────────────────────────────────
# User
# ──────────────────────────────────────────────

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'
    created_at = db.Column(db.DateTime, default=_utcnow)

    # Relationships
    owned_classes = db.relationship("Class", backref="owner", lazy="dynamic")
    enrolled_classes = db.relationship(
        "Class", secondary=class_students, backref="students", lazy="dynamic"
    )
    submissions = db.relationship("Submission", backref="student", lazy="dynamic")
    peer_reviews = db.relationship("PeerReview", backref="reviewer", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }


# ──────────────────────────────────────────────
# Class (Classroom)
# ──────────────────────────────────────────────

class Class(db.Model):
    __tablename__ = "classes"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    grade = db.Column(db.String(50), nullable=True)
    description = db.Column(db.Text, nullable=True)
    passcode = db.Column(db.String(10), nullable=False, default=_generate_passcode)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    # Relationships
    assignments = db.relationship(
        "Assignment", backref="class_", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self, include_passcode=False, include_students=False, include_assignments=False):
        data = {
            "id": self.id,
            "name": self.name,
            "subject": self.subject,
            "grade": self.grade,
            "description": self.description,
            "ownerId": self.owner_id,
            "ownerName": self.owner.name if self.owner else None,
            "studentCount": len(list(self.students)),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_passcode:
            data["passcode"] = self.passcode
        if include_students:
            data["students"] = [s.to_dict() for s in self.students]
        if include_assignments:
            data["assignments"] = [a.to_dict(include_submissions=True) for a in self.assignments]
        return data


# ──────────────────────────────────────────────
# Assignment
# ──────────────────────────────────────────────

class Assignment(db.Model):
    __tablename__ = "assignments"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    class_id = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    # Relationships
    submissions = db.relationship(
        "Submission", backref="assignment", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self, include_submissions=False):
        data = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "dueDate": self.due_date.isoformat() if self.due_date else None,
            "classId": self.class_id,
            "submissionCount": self.submissions.count(),
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
        if include_submissions:
            data["submissions"] = [s.to_dict(include_reviews=True) for s in self.submissions]
        return data


# ──────────────────────────────────────────────
# Submission
# ──────────────────────────────────────────────

class Submission(db.Model):
    __tablename__ = "submissions"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=True)
    file_name = db.Column(db.String(255), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False)
    submitted_at = db.Column(db.DateTime, default=_utcnow)

    # Grading fields
    grade = db.Column(db.String(10), nullable=True)
    feedback = db.Column(db.Text, nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)

    # Relationships
    peer_reviews = db.relationship(
        "PeerReview", backref="submission", lazy="dynamic", cascade="all, delete-orphan"
    )

    def to_dict(self, include_reviews=False):
        data = {
            "id": self.id,
            "content": self.content,
            "fileName": self.file_name,
            "fileSize": self.file_size,
            "studentId": self.student_id,
            "studentName": self.student.name if self.student else None,
            "assignmentId": self.assignment_id,
            "submittedAt": self.submitted_at.isoformat() if self.submitted_at else None,
            "grade": self.grade,
            "feedback": self.feedback,
            "gradedAt": self.graded_at.isoformat() if self.graded_at else None,
        }
        if include_reviews:
            data["peerReviews"] = [r.to_dict() for r in self.peer_reviews]
        return data


# ──────────────────────────────────────────────
# PeerReview
# ──────────────────────────────────────────────

class PeerReview(db.Model):
    __tablename__ = "peer_reviews"

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    submission_id = db.Column(db.Integer, db.ForeignKey("submissions.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "reviewerId": self.reviewer_id,
            "reviewerName": self.reviewer.name if self.reviewer else None,
            "submissionId": self.submission_id,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
