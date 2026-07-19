from app import db
from datetime import datetime

class ConferenceRoom(db.Model):
    __tablename__ = 'conference_rooms'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='room', lazy=True)

    def to_dict(self):
        """Serialize this conference room to a JSON-safe dict.

        Used by the ``/rooms`` routes to build their responses.

        Args:
            self (ConferenceRoom): The room instance. Takes no other
                arguments.

        Returns:
            dict: ``{"id": int, "name": str, "capacity": int, "location":
            str}``. All values are already JSON-serializable.

        Examples:
            Example 1 — serialize a room looked up by ID:

            >>> room = ConferenceRoom.query.get(1)
            >>> room.to_dict()["name"]
            'Azure Hall'

            Example 2 — serialize every room for an API response:

            >>> [r.to_dict() for r in ConferenceRoom.query.all()]
            [{'id': 1, 'name': 'Azure Hall', ...}, ...]

        Browser:
            Not called directly over HTTP; its output is the ``data`` of
            ``GET /rooms/1`` — http://localhost:5000/rooms/1

        cURL:
            curl http://localhost:5000/rooms/1
        """
        return {'id': self.id, 'name': self.name, 'capacity': self.capacity, 'location': self.location}

class Employee(db.Model):
    __tablename__ = 'employees'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=False)
    bookings = db.relationship('Booking', backref='organizer', lazy=True)

    def to_dict(self):
        """Serialize this employee to a JSON-safe dict.

        Args:
            self (Employee): The employee instance. Takes no other arguments.

        Returns:
            dict: ``{"id": int, "name": str, "email": str, "department":
            str}``. All values are already JSON-serializable.

        Examples:
            Example 1 — serialize an employee looked up by ID:

            >>> emp = Employee.query.get(1)
            >>> emp.to_dict()["email"]
            'alice.thompson@corp.com'

            Example 2 — serialize every employee:

            >>> [e.to_dict() for e in Employee.query.all()]
            [{'id': 1, 'name': 'Alice Thompson', ...}, ...]

        Browser:
            There is no employee HTTP endpoint; employees surface only via
            the ``organizer_id`` field on bookings, e.g.
            http://localhost:5000/bookings/1

        cURL:
            curl http://localhost:5000/bookings/1
        """
        return {'id': self.id, 'name': self.name, 'email': self.email, 'department': self.department}

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('conference_rooms.id'), nullable=False)
    organizer_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    meeting_title = db.Column(db.String(200))
    attendees = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='scheduled')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        """Serialize this booking to a JSON-safe dict.

        Datetime columns are rendered with :meth:`datetime.isoformat`. Note
        that ``created_at`` is intentionally omitted from the output.

        Args:
            self (Booking): The booking instance. Takes no other arguments.

        Returns:
            dict: ``{"id": int, "room_id": int, "organizer_id": int,
            "start_time": str, "end_time": str, "meeting_title": str | None,
            "attendees": int | None, "status": str | None}`` where
            ``start_time`` and ``end_time`` are ISO 8601 strings.

        Examples:
            Example 1 — serialize a booking looked up by ID:

            >>> booking = Booking.query.get(1)
            >>> booking.to_dict()["start_time"]
            '2025-07-01T18:00:00'

            Example 2 — serialize a filtered set of bookings:

            >>> [b.to_dict() for b in Booking.query.filter_by(room_id=1).all()]
            [{'id': 1, 'room_id': 1, ...}, ...]

        Browser:
            Not called directly over HTTP; its output is the ``data`` of
            ``GET /bookings/1`` — http://localhost:5000/bookings/1

        cURL:
            curl http://localhost:5000/bookings/1
        """
        return {
            'id': self.id,
            'room_id': self.room_id,
            'organizer_id': self.organizer_id,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'meeting_title': self.meeting_title,
            'attendees': self.attendees,
            'status': self.status
        }
