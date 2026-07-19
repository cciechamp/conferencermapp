"""Shared pytest fixtures.

Each test runs against a fresh in-memory SQLite database, seeded with a small,
predictable set of rooms, employees and bookings. Nothing here touches the real
``db/bookings.db``.
"""
import os
import sys
from datetime import datetime

import pytest

# Make the project root importable (app.py, models.py, ...) when pytest is run
# from anywhere.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db  # noqa: E402
from models import ConferenceRoom, Employee, Booking  # noqa: E402


@pytest.fixture
def app():
    """A Flask app bound to a throwaway in-memory database, pre-seeded."""
    application = create_app({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True,
    })
    with application.app_context():
        # create_app already ran create_all() against the in-memory engine.
        room_a = ConferenceRoom(name='Test Room A', capacity=10, location='Bldg X')
        room_b = ConferenceRoom(name='Test Room B', capacity=4, location='Bldg Y')
        db.session.add_all([room_a, room_b])

        alice = Employee(name='Alice', email='alice@test.com', department='Eng')
        bob = Employee(name='Bob', email='bob@test.com', department='Sales')
        db.session.add_all([alice, bob])
        db.session.commit()

        # One existing scheduled booking in room A: 2025-07-01 10:00-10:30.
        booking = Booking(
            room_id=room_a.id,
            organizer_id=alice.id,
            start_time=datetime(2025, 7, 1, 10, 0),
            end_time=datetime(2025, 7, 1, 10, 30),
            meeting_title='Existing',
            attendees=3,
            status='scheduled',
        )
        db.session.add(booking)
        db.session.commit()

        yield application


@pytest.fixture
def client(app):
    """A Flask test client for issuing requests to the seeded app."""
    return app.test_client()
