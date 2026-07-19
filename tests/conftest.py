"""Shared pytest fixtures.

Provides a Flask test client backed by a throwaway in-memory SQLite database,
seeded with exactly one room and one employee and no bookings. Nothing here
touches the real ``db/bookings.db``.
"""
import os
import sys

import pytest

# Make the project root importable (app.py, models.py, ...) when pytest is run
# from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db  # noqa: E402
from models import ConferenceRoom, Employee  # noqa: E402


@pytest.fixture
def client():
    """A Flask test client on an in-memory DB seeded with 1 room, 1 employee.

    No bookings are created, so the schedule starts empty.

    Yields:
        flask.testing.FlaskClient: Client for issuing requests to the seeded
        app. The app context stays active for the duration of the test.
    """
    app = create_app({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True,
    })
    with app.app_context():
        # create_app already ran create_all() against the in-memory engine.
        db.session.add(ConferenceRoom(name='Test Room', capacity=10, location='Bldg X'))
        db.session.add(Employee(name='Alice', email='alice@test.com', department='Eng'))
        db.session.commit()

        yield app.test_client()
