from flask import Blueprint, request, jsonify
from app import db
from models import Booking, ConferenceRoom, Employee
from utils.conflict import check_overlap
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)

@bookings_bp.route('/bookings', methods=['GET'])
def get_bookings():
    """List bookings, optionally filtered by room and/or organizer.

    Route:
        GET /bookings?room_id=<int>&organizer_id=<int>

    Args:
        room_id (int, optional): Query parameter. When supplied, only
            bookings for this room are returned.
        organizer_id (int, optional): Query parameter. When supplied, only
            bookings created by this employee are returned. May be combined
            with ``room_id`` (both filters are ANDed together).

    Returns:
        flask.Response: JSON ``{"data": list[dict], "error": None, "status":
        200}`` where ``data`` is a list of booking dicts (see
        :meth:`models.Booking.to_dict`). The list is empty if nothing
        matches the filters.

    Examples:
        Example 1 — every booking for room 1:

        >>> import requests
        >>> requests.get("http://localhost:5000/bookings",
        ...              params={"room_id": 1}).json()["status"]
        200

        Example 2 — bookings for room 1 organized by employee 1:

        >>> import requests
        >>> requests.get("http://localhost:5000/bookings",
        ...              params={"room_id": 1, "organizer_id": 1}).json()["data"]
        [...]

    Browser:
        http://localhost:5000/bookings?room_id=1

    cURL:
        curl "http://localhost:5000/bookings?room_id=1&organizer_id=1"
    """
    room_id = request.args.get('room_id', type=int)
    organizer_id = request.args.get('organizer_id', type=int)
    query = Booking.query
    if room_id:
        query = query.filter_by(room_id=room_id)
    if organizer_id:
        query = query.filter_by(organizer_id=organizer_id)
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    """Fetch a single booking by its ID.

    Route:
        GET /bookings/<int:booking_id>

    Args:
        booking_id (int): Path parameter. The primary key of the booking.

    Returns:
        flask.Response: On success, JSON ``{"data": dict, "error": None,
        "status": 200}`` where ``data`` is the booking (see
        :meth:`models.Booking.to_dict`). If no booking matches, returns
        ``{"data": None, "error": "Booking not found", "status": 404}`` with
        HTTP status 404.

    Examples:
        Example 1 — fetch booking 1 in Python:

        >>> import requests
        >>> requests.get("http://localhost:5000/bookings/1").json()["data"]["room_id"]
        1

        Example 2 — detect a missing booking via the HTTP status code:

        >>> import requests
        >>> requests.get("http://localhost:5000/bookings/99999").status_code
        404

    Browser:
        http://localhost:5000/bookings/1

    cURL:
        curl http://localhost:5000/bookings/1
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings', methods=['POST'])
def create_booking():
    """Create a new booking after validating times and checking for conflicts.

    The request body must be JSON. ``start_time``/``end_time`` are parsed as
    ISO 8601, ``end_time`` must be strictly after ``start_time``, and the slot
    must not overlap an existing scheduled booking for the same room (the
    overlap check delegates to :func:`utils.conflict.check_overlap`). New
    bookings are always created with ``status="scheduled"``.

    Route:
        POST /bookings

    Args:
        JSON request body with the following keys:
            room_id (int): **Required.** Room to book.
            organizer_id (int): **Required.** Employee making the booking.
            start_time (str): **Required.** ISO 8601 datetime, e.g.
                ``"2025-08-01T10:00:00"``.
            end_time (str): **Required.** ISO 8601 datetime, must be after
                ``start_time``.
            meeting_title (str, optional): Defaults to ``""``.
            attendees (int, optional): Defaults to ``1``.

    Returns:
        flask.Response: On success, JSON ``{"data": dict, "error": None,
        "status": 201}`` (HTTP 201) with the created booking. Error
        envelopes: ``400`` for missing body, a missing required field, an
        unparseable datetime, or ``end_time <= start_time``; ``409``
        ``{"error": "Time slot conflicts with existing booking"}`` when the
        slot overlaps another scheduled booking.

    Examples:
        Example 1 — create a booking in Python:

        >>> import requests
        >>> body = {
        ...     "room_id": 1, "organizer_id": 1,
        ...     "start_time": "2025-08-01T10:00:00",
        ...     "end_time": "2025-08-01T10:30:00",
        ...     "meeting_title": "Design review", "attendees": 4,
        ... }
        >>> requests.post("http://localhost:5000/bookings", json=body).status_code
        201

        Example 2 — a conflicting slot is rejected with 409:

        >>> import requests
        >>> requests.post("http://localhost:5000/bookings", json=body).status_code
        409

    Browser:
        Not directly callable from the address bar (browsers only issue GET
        for typed URLs). Use the cURL command below, or an HTML form / fetch
        with ``method: "POST"``.

    cURL:
        curl -X POST http://localhost:5000/bookings \\
          -H "Content-Type: application/json" \\
          -d '{"room_id": 1, "organizer_id": 1, "start_time": "2025-08-01T10:00:00", "end_time": "2025-08-01T10:30:00", "meeting_title": "Design review", "attendees": 4}'
    """
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    required = ['room_id', 'organizer_id', 'start_time', 'end_time']
    for field in required:
        if field not in data:
            return jsonify({'data': None, 'error': f'Missing field: {field}', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(data['room_id'], start, end):
        return jsonify({'data': None, 'error': 'Time slot conflicts with existing booking', 'status': 409}), 409
    booking = Booking(
        room_id=data['room_id'],
        organizer_id=data['organizer_id'],
        start_time=start,
        end_time=end,
        meeting_title=data.get('meeting_title', ''),
        attendees=data.get('attendees', 1),
        status='scheduled'
    )
    db.session.add(booking)
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 201}), 201

@bookings_bp.route('/bookings/<int:booking_id>', methods=['PUT'])
def reschedule_booking(booking_id):
    """Reschedule an existing booking to a new start/end time.

    Only the times change; the room, organizer and other fields are left as
    they were. The new window is validated (ISO 8601, ``end_time`` after
    ``start_time``) and checked for overlaps against other scheduled bookings
    for the same room, excluding this booking itself.

    Route:
        PUT /bookings/<int:booking_id>

    Args:
        booking_id (int): Path parameter. The booking to reschedule.
        JSON request body with:
            start_time (str): **Required.** New ISO 8601 start datetime.
            end_time (str): **Required.** New ISO 8601 end datetime, must be
                after ``start_time``.

    Returns:
        flask.Response: On success, JSON ``{"data": dict, "error": None,
        "status": 200}`` with the updated booking. Error envelopes: ``404``
        when the booking does not exist; ``400`` for missing body, an
        unparseable datetime, or ``end_time <= start_time``; ``409``
        ``{"error": "New time slot conflicts with existing booking"}`` on
        overlap with another scheduled booking.

    Examples:
        Example 1 — move booking 1 to a new time in Python:

        >>> import requests
        >>> body = {"start_time": "2025-08-01T14:00:00",
        ...         "end_time": "2025-08-01T14:30:00"}
        >>> requests.put("http://localhost:5000/bookings/1", json=body).status_code
        200

        Example 2 — rescheduling a nonexistent booking returns 404:

        >>> import requests
        >>> requests.put("http://localhost:5000/bookings/99999", json=body).status_code
        404

    Browser:
        Not directly callable from the address bar (typed URLs issue GET, not
        PUT). Use the cURL command below or a ``fetch`` with ``method:
        "PUT"``.

    cURL:
        curl -X PUT http://localhost:5000/bookings/1 \\
          -H "Content-Type: application/json" \\
          -d '{"start_time": "2025-08-01T14:00:00", "end_time": "2025-08-01T14:30:00"}'
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    data = request.get_json()
    if not data:
        return jsonify({'data': None, 'error': 'No data provided', 'status': 400}), 400
    try:
        start = datetime.fromisoformat(data['start_time'])
        end = datetime.fromisoformat(data['end_time'])
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid datetime format. Use ISO 8601.', 'status': 400}), 400
    if end <= start:
        return jsonify({'data': None, 'error': 'end_time must be after start_time', 'status': 400}), 400
    if check_overlap(booking.room_id, start, end, exclude_id=booking_id):
        return jsonify({'data': None, 'error': 'New time slot conflicts with existing booking', 'status': 409}), 409
    booking.start_time = start
    booking.end_time = end
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})

@bookings_bp.route('/bookings/<int:booking_id>', methods=['DELETE'])
def cancel_booking(booking_id):
    """Cancel a booking (soft delete).

    The row is not removed; instead its ``status`` is set to ``"cancelled"``.
    Cancelled bookings no longer count toward availability or conflict checks
    (those only consider ``status="scheduled"``).

    Route:
        DELETE /bookings/<int:booking_id>

    Args:
        booking_id (int): Path parameter. The booking to cancel.

    Returns:
        flask.Response: On success, JSON ``{"data": dict, "error": None,
        "status": 200}`` where ``data`` is the updated booking with
        ``status="cancelled"``. If no booking matches, returns ``{"data":
        None, "error": "Booking not found", "status": 404}`` with HTTP
        status 404.

    Examples:
        Example 1 — cancel booking 1 in Python:

        >>> import requests
        >>> requests.delete("http://localhost:5000/bookings/1").json()["data"]["status"]
        'cancelled'

        Example 2 — cancelling a nonexistent booking returns 404:

        >>> import requests
        >>> requests.delete("http://localhost:5000/bookings/99999").status_code
        404

    Browser:
        Not directly callable from the address bar (typed URLs issue GET, not
        DELETE). Use the cURL command below or a ``fetch`` with ``method:
        "DELETE"``.

    cURL:
        curl -X DELETE http://localhost:5000/bookings/1
    """
    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({'data': None, 'error': 'Booking not found', 'status': 404}), 404
    booking.status = 'cancelled'
    db.session.commit()
    return jsonify({'data': booking.to_dict(), 'error': None, 'status': 200})
