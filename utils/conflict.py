from models import Booking

def check_overlap(room_id, start_time, end_time, exclude_id=None):
    """Check whether a proposed slot overlaps a room's scheduled bookings.

    Two bookings overlap when one starts before the other ends AND ends after
    the other starts. This uses strict less-than comparisons so that
    back-to-back bookings (e.g. 09:00-09:30 followed by 09:30-10:00) are
    correctly allowed. Only bookings with ``status="scheduled"`` are
    considered; cancelled bookings never conflict.

    Args:
        room_id (int): ID of the conference room whose schedule to check.
        start_time (datetime.datetime): Proposed booking start.
        end_time (datetime.datetime): Proposed booking end.
        exclude_id (int, optional): A booking ID to ignore during the check.
            Used when rescheduling so a booking does not conflict with
            itself. Defaults to ``None``.

    Returns:
        bool: ``True`` if an overlapping scheduled booking exists, ``False``
        if the slot is free.

    Examples:
        Example 1 — check a brand-new slot (must run inside an app context):

        >>> from datetime import datetime
        >>> check_overlap(1, datetime(2025, 8, 1, 10, 0),
        ...                   datetime(2025, 8, 1, 10, 30))
        False

        Example 2 — re-check a slot while rescheduling booking 5, ignoring it:

        >>> from datetime import datetime
        >>> check_overlap(1, datetime(2025, 8, 1, 10, 0),
        ...                   datetime(2025, 8, 1, 10, 30), exclude_id=5)
        False

    Browser:
        Not an HTTP endpoint. It runs server-side inside ``POST /bookings``
        and ``PUT /bookings/<id>``; a returned ``True`` is what surfaces as
        the ``409`` conflict response from those routes.

    cURL:
        # Exercised indirectly by attempting a conflicting booking:
        curl -X POST http://localhost:5000/bookings \\
          -H "Content-Type: application/json" \\
          -d '{"room_id": 1, "organizer_id": 1, "start_time": "2025-07-01T18:00:00", "end_time": "2025-07-01T18:30:00"}'
    """
    query = Booking.query.filter(
        Booking.room_id == room_id,
        Booking.status == 'scheduled',
        Booking.start_time < end_time,
        Booking.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Booking.id != exclude_id)
    return query.first() is not None
