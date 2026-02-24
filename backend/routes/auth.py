"""
Authentication routes: register, login, logout, session restore.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
)
from extensions import db, bcrypt, limiter
from models import User
from utils import validate_email, validate_password
from decorators import validate_json

auth_bp = Blueprint("auth", __name__)

# ─── Token blocklist (in-memory; use Redis in production) ───
BLOCKLIST = set()


# ──────────────────────────────────────────────
# POST /api/auth/register
# ──────────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
@limiter.limit("10 per minute")
@validate_json("name", "email", "password", "role")
def register(data):
    name = data["name"].strip()
    email = data["email"].strip().lower()
    password = data["password"]
    role = data["role"].strip().lower()

    # Validate role
    if role not in ("teacher", "student"):
        return jsonify({"error": "Role must be 'teacher' or 'student'"}), 400

    # Validate email format
    if not validate_email(email):
        return jsonify({"error": "Invalid email format"}), 400

    # Validate password strength
    is_valid, msg = validate_password(password)
    if not is_valid:
        return jsonify({"error": msg}), 400

    # Check duplicate
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Create user
    user = User(
        name=name,
        email=email,
        password_hash=bcrypt.generate_password_hash(password).decode("utf-8"),
        role=role,
    )
    db.session.add(user)
    db.session.commit()

    # Issue tokens
    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Registration successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }), 201


# ──────────────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")
@validate_json("email", "password")
def login(data):
    email = data["email"].strip().lower()
    password = data["password"]

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token = create_access_token(identity=str(user.id))
    refresh_token = create_refresh_token(identity=str(user.id))

    return jsonify({
        "message": "Login successful",
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": user.to_dict(),
    }), 200


# ──────────────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────────────
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]
    BLOCKLIST.add(jti)
    return jsonify({"message": "Logged out successfully"}), 200


# ──────────────────────────────────────────────
# GET /api/auth/session  — restore session from token
# ──────────────────────────────────────────────
@auth_bp.route("/session", methods=["GET"])
@jwt_required()
def get_session():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


# ──────────────────────────────────────────────
# POST /api/auth/refresh
# ──────────────────────────────────────────────
@auth_bp.route("/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    current_user_id = get_jwt_identity()
    access_token = create_access_token(identity=current_user_id)
    return jsonify({"access_token": access_token}), 200


def is_token_revoked(jwt_header, jwt_payload):
    """Check if a JWT has been revoked (logged out)."""
    return jwt_payload["jti"] in BLOCKLIST
