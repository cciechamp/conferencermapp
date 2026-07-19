from flask import Blueprint, request, jsonify
from app import db
from models import ConferenceRoom, Booking
from datetime import datetime, timedelta, time

rooms_bp = Blueprint('rooms', __name__)

# Business hours and slot size used to build the available-slot grid.
BUSINESS_START = time(9, 0)
BUSINESS_END = time(18, 0)
SLOT_MINUTES = 30

@rooms_bp.route('/rooms', methods=['GET'])
def get_rooms():
    """List every conference room.

    Route:
        GET /rooms

    Args:
        None. This endpoint takes no path or query parameters.

    Returns:
        flask.Response: JSON envelope ``{"data": list[dict], "error": None,
        "status": 200}`` where ``data`` is a list of room dicts, each with
        keys ``id`` (int), ``name`` (str), ``capacity`` (int) and
        ``location`` (str). The list is empty if no rooms exist.

    Examples:
        Example 1 — fetch all rooms in Python:

        >>> import requests
        >>> resp = requests.get("http://localhost:5000/rooms")
        >>> resp.json()["data"][0]["name"]
        'Azure Hall'

        Example 2 — count how many rooms are configured:

        >>> import requests
        >>> len(requests.get("http://localhost:5000/rooms").json()["data"])
        5

    Browser:
        http://localhost:5000/rooms

    cURL:
        curl http://localhost:5000/rooms
    """
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    """Fetch a single conference room by its ID.

    Route:
        GET /rooms/<int:room_id>

    Args:
        room_id (int): Path parameter. The primary key of the room to fetch.

    Returns:
        flask.Response: On success, JSON ``{"data": dict, "error": None,
        "status": 200}`` where ``data`` holds the room's ``id`` (int),
        ``name`` (str), ``capacity`` (int) and ``location`` (str). If no room
        matches ``room_id``, returns ``{"data": None, "error": "Room not
        found", "status": 404}`` with HTTP status 404.

    Examples:
        Example 1 — fetch room 1 in Python:

        >>> import requests
        >>> requests.get("http://localhost:5000/rooms/1").json()["data"]["capacity"]
        30

        Example 2 — detect a missing room via the HTTP status code:

        >>> import requests
        >>> requests.get("http://localhost:5000/rooms/999").status_code
        404

    Browser:
        http://localhost:5000/rooms/1

    cURL:
        curl http://localhost:5000/rooms/1
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """List a room's booked (scheduled) time slots, optionally filtered by date.

    Note:
        This returns slots that are *taken*. For the free slots, use
        ``GET /rooms/<id>/available`` (see :func:`get_available_slots`).

    Route:
        GET /rooms/<int:room_id>/availability?date=YYYY-MM-DD

    Args:
        room_id (int): Path parameter. The room whose schedule to read.
        date (str, optional): Query parameter in ``YYYY-MM-DD`` (ISO 8601)
            format. When supplied, only bookings that start on that date are
            returned; when omitted, all scheduled bookings for the room are
            returned.

    Returns:
        flask.Response: On success, JSON ``{"data": list[dict], "error":
        None, "status": 200}`` where ``data`` is a list of booking dicts
        (see :meth:`models.Booking.to_dict`). If ``date`` is present but
        malformed, returns ``{"data": None, "error": "Invalid date format.
        Use YYYY-MM-DD.", "status": 400}`` with HTTP status 400.

    Examples:
        Example 1 — bookings for room 1 on a specific day:

        >>> import requests
        >>> url = "http://localhost:5000/rooms/1/availability"
        >>> requests.get(url, params={"date": "2025-07-01"}).json()["status"]
        200

        Example 2 — all scheduled bookings for room 1 (no date filter):

        >>> import requests
        >>> requests.get("http://localhost:5000/rooms/1/availability").json()["data"]
        [...]

    Browser:
        http://localhost:5000/rooms/1/availability?date=2025-07-01

    cURL:
        curl "http://localhost:5000/rooms/1/availability?date=2025-07-01"
    """
    date_str = request.args.get('date', type=str)
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled'
    )
    if date_str:
        try:
            target_date = datetime.fromisoformat(date_str).date()
            query = query.filter(db.func.date(Booking.start_time) == target_date)
        except ValueError:
            return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400
    bookings = query.all()
    return jsonify({'data': [b.to_dict() for b in bookings], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/available', methods=['GET'])
def get_available_slots(room_id):
    """List the free 30-minute slots for a room on a given date.

    Divides business hours (``BUSINESS_START``-``BUSINESS_END``, i.e.
    09:00-18:00) into fixed ``SLOT_MINUTES`` (30) minute slots and returns
    each slot that does not overlap any scheduled booking for that room.

    Route:
        GET /rooms/<int:room_id>/available?date=YYYY-MM-DD

    Args:
        room_id (int): Path parameter. The room to check availability for.
        date (str): **Required** query parameter in ``YYYY-MM-DD``
            (ISO 8601) format. The day whose grid of slots to evaluate.

    Returns:
        flask.Response: On success, JSON ``{"data": list[dict], "error":
        None, "status": 200}`` where each item is a free slot
        ``{"start_time": str, "end_time": str}`` with ISO 8601 datetimes.
        Error envelopes: ``404`` ``{"error": "Room not found"}`` when the
        room does not exist; ``400`` ``{"error": "Missing required query
        param: date (YYYY-MM-DD)"}`` when ``date`` is absent; ``400``
        ``{"error": "Invalid date format. Use YYYY-MM-DD."}`` when ``date``
        cannot be parsed.

    Examples:
        Example 1 — free slots for room 1 on a date with no daytime bookings:

        >>> import requests
        >>> url = "http://localhost:5000/rooms/1/available"
        >>> len(requests.get(url, params={"date": "2025-07-01"}).json()["data"])
        18

        Example 2 — a missing date parameter is rejected with 400:

        >>> import requests
        >>> requests.get("http://localhost:5000/rooms/1/available").status_code
        400

    Browser:
        http://localhost:5000/rooms/1/available?date=2025-07-01

    cURL:
        curl "http://localhost:5000/rooms/1/available?date=2025-07-01"
    """
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404

    date_str = request.args.get('date', type=str)
    if not date_str:
        return jsonify({'data': None, 'error': 'Missing required query param: date (YYYY-MM-DD)', 'status': 400}), 400
    try:
        target_date = datetime.fromisoformat(date_str).date()
    except ValueError:
        return jsonify({'data': None, 'error': 'Invalid date format. Use YYYY-MM-DD.', 'status': 400}), 400

    # Fetch that day's scheduled bookings once, then test each grid slot in memory.
    bookings = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        db.func.date(Booking.start_time) == target_date,
    ).all()

    slots = []
    slot_start = datetime.combine(target_date, BUSINESS_START)
    day_end = datetime.combine(target_date, BUSINESS_END)
    delta = timedelta(minutes=SLOT_MINUTES)
    while slot_start + delta <= day_end:
        slot_end = slot_start + delta
        # A slot is taken if any booking overlaps it (start < slot_end and end > slot_start).
        taken = any(b.start_time < slot_end and b.end_time > slot_start for b in bookings)
        if not taken:
            slots.append({'start_time': slot_start.isoformat(), 'end_time': slot_end.isoformat()})
        slot_start = slot_end

    return jsonify({'data': slots, 'error': None, 'status': 200})
