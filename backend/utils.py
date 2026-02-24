"""
Utility functions for the ReviewIn backend.
"""

import re
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from extensions import db


# ──────────────────────────────────────────────
# Validators
# ──────────────────────────────────────────────

def validate_email(email):
    """Return True if email format is valid."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password):
    """
    Validate password strength.
    Requirements: ≥8 chars, 1 uppercase, 1 lowercase, 1 digit.
    Returns (is_valid: bool, message: str).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain an uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain a lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain a number"
    return True, "Valid"


# ──────────────────────────────────────────────
# Role decorators
# ──────────────────────────────────────────────

def teacher_required(fn):
    """Decorator: require authenticated user with role=teacher."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        from models import User

        current_user_id = int(get_jwt_identity())
        user = db.session.get(User, current_user_id)
        if not user or user.role != "teacher":
            return jsonify({"error": "Teacher access required"}), 403
        return fn(*args, **kwargs)

    return wrapper


def student_required(fn):
    """Decorator: require authenticated user with role=student."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        from models import User

        current_user_id = int(get_jwt_identity())
        user = db.session.get(User, current_user_id)
        if not user or user.role != "student":
            return jsonify({"error": "Student access required"}), 403
        return fn(*args, **kwargs)

    return wrapper
