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
    rooms = ConferenceRoom.query.all()
    return jsonify({'data': [r.to_dict() for r in rooms], 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>', methods=['GET'])
def get_room(room_id):
    room = ConferenceRoom.query.get(room_id)
    if not room:
        return jsonify({'data': None, 'error': 'Room not found', 'status': 404}), 404
    return jsonify({'data': room.to_dict(), 'error': None, 'status': 200})

@rooms_bp.route('/rooms/<int:room_id>/availability', methods=['GET'])
def get_availability(room_id):
    """
    Returns a room's booked time slots, optionally filtered by date.
    Optional query param: ?date=YYYY-MM-DD
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
    """
    Returns the free 30-minute slots for a room on a given date.

    Divides business hours (09:00-18:00) into fixed 30-minute slots and
    returns each slot that does not overlap a scheduled booking.

    Required query param: ?date=YYYY-MM-DD
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
