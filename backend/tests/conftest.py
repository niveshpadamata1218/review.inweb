"""
Pytest fixtures for the ReviewIn backend tests.
"""

import pytest
from app import create_app
from extensions import db as _db


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    """Test client."""
    with app.test_client() as client:
        with app.app_context():
            yield client


@pytest.fixture(scope="function", autouse=True)
def clean_db(app):
    """Roll back after each test."""
    with app.app_context():
        yield
        _db.session.rollback()
        for table in reversed(_db.metadata.sorted_tables):
            _db.session.execute(table.delete())
        _db.session.commit()
