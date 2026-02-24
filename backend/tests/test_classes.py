"""
Tests for class, assignment, submission, and peer review endpoints.
"""

import json


def _register(client, name, email, password, role):
    resp = client.post(
        "/api/auth/register",
        json={"name": name, "email": email, "password": password, "role": role},
    )
    return resp.get_json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Class tests ──────────────────────────────

def test_create_class(client):
    token = _register(client, "T", "t@t.com", "Teacher1", "teacher")
    resp = client.post(
        "/api/classes",
        json={"name": "Math 101", "subject": "Math", "grade": "9"},
        headers=_auth(token),
    )
    assert resp.status_code == 201
    data = resp.get_json()["class"]
    assert data["name"] == "Math 101"
    assert "passcode" in data


def test_student_cannot_create_class(client):
    token = _register(client, "S", "s@s.com", "Student1", "student")
    resp = client.post(
        "/api/classes",
        json={"name": "Nope", "subject": "Nah"},
        headers=_auth(token),
    )
    assert resp.status_code == 403


def test_join_class(client):
    t_token = _register(client, "T", "t2@t.com", "Teacher1", "teacher")
    s_token = _register(client, "S", "s2@s.com", "Student1", "student")

    # Create class
    create_resp = client.post(
        "/api/classes",
        json={"name": "Sci", "subject": "Science"},
        headers=_auth(t_token),
    )
    cls = create_resp.get_json()["class"]

    # Join
    resp = client.post(
        "/api/classes/join",
        json={"classId": cls["id"], "passcode": cls["passcode"]},
        headers=_auth(s_token),
    )
    assert resp.status_code == 200


def test_leave_class(client):
    t_token = _register(client, "T", "t3@t.com", "Teacher1", "teacher")
    s_token = _register(client, "S", "s3@s.com", "Student1", "student")

    create_resp = client.post(
        "/api/classes",
        json={"name": "Art", "subject": "Art"},
        headers=_auth(t_token),
    )
    cls = create_resp.get_json()["class"]

    client.post(
        "/api/classes/join",
        json={"classId": cls["id"], "passcode": cls["passcode"]},
        headers=_auth(s_token),
    )

    resp = client.post(
        f"/api/classes/{cls['id']}/leave",
        headers=_auth(s_token),
    )
    assert resp.status_code == 200


# ── Assignment tests ─────────────────────────

def test_create_assignment(client):
    t_token = _register(client, "T", "t4@t.com", "Teacher1", "teacher")
    cls = client.post(
        "/api/classes",
        json={"name": "Eng", "subject": "English"},
        headers=_auth(t_token),
    ).get_json()["class"]

    resp = client.post(
        f"/api/classes/{cls['id']}/assignments",
        json={"title": "Essay 1", "description": "Write something."},
        headers=_auth(t_token),
    )
    assert resp.status_code == 201


def test_delete_assignment(client):
    t_token = _register(client, "T", "t5@t.com", "Teacher1", "teacher")
    cls = client.post(
        "/api/classes",
        json={"name": "Hist", "subject": "History"},
        headers=_auth(t_token),
    ).get_json()["class"]

    a = client.post(
        f"/api/classes/{cls['id']}/assignments",
        json={"title": "Quiz"},
        headers=_auth(t_token),
    ).get_json()["assignment"]

    resp = client.delete(
        f"/api/classes/{cls['id']}/assignments/{a['id']}",
        headers=_auth(t_token),
    )
    assert resp.status_code == 200


# ── Submission tests ─────────────────────────

def test_submit_and_grade(client):
    t_token = _register(client, "T", "t6@t.com", "Teacher1", "teacher")
    s_token = _register(client, "S", "s6@s.com", "Student1", "student")

    cls = client.post(
        "/api/classes",
        json={"name": "Bio", "subject": "Biology"},
        headers=_auth(t_token),
    ).get_json()["class"]

    client.post(
        "/api/classes/join",
        json={"classId": cls["id"], "passcode": cls["passcode"]},
        headers=_auth(s_token),
    )

    a = client.post(
        f"/api/classes/{cls['id']}/assignments",
        json={"title": "Lab Report"},
        headers=_auth(t_token),
    ).get_json()["assignment"]

    # Submit
    sub = client.post(
        f"/api/classes/{cls['id']}/assignments/{a['id']}/submissions",
        json={"content": "My report content"},
        headers=_auth(s_token),
    )
    assert sub.status_code == 201
    sub_data = sub.get_json()["submission"]

    # Grade
    grade_resp = client.put(
        f"/api/classes/{cls['id']}/assignments/{a['id']}/submissions/{sub_data['id']}/grade",
        json={"grade": "A", "feedback": "Great work!"},
        headers=_auth(t_token),
    )
    assert grade_resp.status_code == 200
    assert grade_resp.get_json()["submission"]["grade"] == "A"
