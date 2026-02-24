"""
Reusable decorators for route handlers.
"""

from functools import wraps
from flask import request, jsonify
from extensions import db


def paginated_response(default_per_page=20, max_per_page=100):
    """Handle pagination parameters from query string."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            page = request.args.get("page", 1, type=int)
            per_page = request.args.get("per_page", default_per_page, type=int)
            if page < 1:
                return jsonify({"error": "Page must be > 0"}), 400
            if per_page > max_per_page:
                per_page = max_per_page
            kwargs["page"] = page
            kwargs["per_page"] = per_page
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def validate_json(*required_fields):
    """Validate that the request has JSON body with required fields."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400
            data = request.get_json()
            if not data:
                return jsonify({"error": "Request body required"}), 400
            missing = [field for field in required_fields if field not in data]
            if missing:
                return jsonify({"error": "Missing required fields", "missing_fields": missing}), 400
            kwargs["data"] = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def handle_db_errors(f):
    """Handle common database errors gracefully."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": "Internal server error", "details": str(e)}), 500
    return decorated_function
