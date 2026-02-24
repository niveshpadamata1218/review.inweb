"""
Database initialization / seed script.

Usage:
    python init_db.py          — create tables
    python init_db.py --seed   — create tables + seed demo data
"""

import sys
from app import create_app
from extensions import db, bcrypt
from models import User, Class, Assignment


def init_database(seed=False):
    app = create_app()

    with app.app_context():
        db.create_all()
        print("✓ Database tables created.")

        if seed:
            _seed_data()
            print("✓ Demo data seeded.")


def _seed_data():
    """Insert demo teacher + student + class + assignment."""
    from models import User, Class, Assignment

    # Check if already seeded
    if User.query.first():
        print("  (database already has data — skipping seed)")
        return

    # Demo teacher
    teacher = User(
        name="Demo Teacher",
        email="teacher@reviewin.dev",
        password_hash=bcrypt.generate_password_hash("Teacher1").decode("utf-8"),
        role="teacher",
    )
    db.session.add(teacher)
    db.session.flush()

    # Demo student
    student = User(
        name="Demo Student",
        email="student@reviewin.dev",
        password_hash=bcrypt.generate_password_hash("Student1").decode("utf-8"),
        role="student",
    )
    db.session.add(student)
    db.session.flush()

    # Demo class
    demo_class = Class(
        name="Intro to Computer Science",
        subject="Computer Science",
        grade="10",
        description="A beginner-friendly CS class covering fundamentals.",
        owner_id=teacher.id,
    )
    db.session.add(demo_class)
    db.session.flush()

    # Enroll student
    demo_class.students.append(student)

    # Demo assignment
    assignment = Assignment(
        title="Hello World Program",
        description="Write a 'Hello World' program in Python.",
        class_id=demo_class.id,
    )
    db.session.add(assignment)

    db.session.commit()


if __name__ == "__main__":
    seed = "--seed" in sys.argv
    init_database(seed=seed)
