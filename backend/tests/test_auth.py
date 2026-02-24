"""
Tests for authentication endpoints.
"""

import json


def test_health_check(client):
    """Health endpoint should return 200."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "healthy"


def test_register_teacher(client):
    """Register a teacher account."""
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Test Teacher",
            "email": "teacher@test.com",
            "password": "Teacher1",
            "role": "teacher",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user"]["role"] == "teacher"
    assert "access_token" in data


def test_register_student(client):
    """Register a student account."""
    resp = client.post(
        "/api/auth/register",
        json={
            "name": "Test Student",
            "email": "student@test.com",
            "password": "Student1",
            "role": "student",
        },
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["user"]["role"] == "student"


def test_register_duplicate_email(client):
    """Registering with the same email twice should fail."""
    payload = {
        "name": "User",
        "email": "dup@test.com",
        "password": "Password1",
        "role": "student",
    }
    client.post("/api/auth/register", json=payload)
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409


def test_login_success(client):
    """Login with valid credentials."""
    client.post(
        "/api/auth/register",
        json={
            "name": "Login User",
            "email": "login@test.com",
            "password": "Password1",
            "role": "student",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "login@test.com", "password": "Password1"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.get_json()


def test_login_wrong_password(client):
    """Login with wrong password should fail."""
    client.post(
        "/api/auth/register",
        json={
            "name": "Bad Login",
            "email": "bad@test.com",
            "password": "Password1",
            "role": "student",
        },
    )
    resp = client.post(
        "/api/auth/login",
        json={"email": "bad@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_session_restore(client):
    """GET /api/auth/session should return current user."""
    reg = client.post(
        "/api/auth/register",
        json={
            "name": "Session User",
            "email": "session@test.com",
            "password": "Password1",
            "role": "student",
        },
    )
    token = reg.get_json()["access_token"]
    resp = client.get(
        "/api/auth/session",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.get_json()["user"]["email"] == "session@test.com"
