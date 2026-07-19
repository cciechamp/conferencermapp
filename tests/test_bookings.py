"""Tests for the /bookings CRUD routes, including conflict handling.

The shared fixture seeds one room (id 1) and one employee (id 1) and no
bookings, so tests that need an existing booking create one via the API first.
"""


def _book(client, start, end, room_id=1, organizer_id=1, **extra):
    """Create a booking via the API and return the response."""
    payload = {
        'room_id': room_id,
        'organizer_id': organizer_id,
        'start_time': start,
        'end_time': end,
    }
    payload.update(extra)
    return client.post('/bookings', json=payload)


def test_list_bookings_starts_empty(client):
    resp = client.get('/bookings')
    assert resp.status_code == 200
    assert resp.get_json()['data'] == []


def test_list_bookings_filtered_by_room(client):
    _book(client, '2025-07-01T09:00:00', '2025-07-01T09:30:00')
    assert len(client.get('/bookings?room_id=1').get_json()['data']) == 1
    assert len(client.get('/bookings?room_id=999').get_json()['data']) == 0


def test_get_booking_not_found(client):
    resp = client.get('/bookings/999')
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'Booking not found'


def test_create_booking_success(client):
    resp = _book(client, '2025-07-01T11:00:00', '2025-07-01T11:30:00',
                 meeting_title='New sync', attendees=2)
    body = resp.get_json()
    assert resp.status_code == 201
    assert body['data']['status'] == 'scheduled'
    assert body['data']['meeting_title'] == 'New sync'


def test_create_booking_missing_field(client):
    resp = client.post('/bookings', json={'room_id': 1})
    assert resp.status_code == 400
    assert 'Missing field' in resp.get_json()['error']


def test_create_booking_end_before_start(client):
    resp = _book(client, '2025-07-01T12:00:00', '2025-07-01T11:00:00')
    assert resp.status_code == 400
    assert 'after' in resp.get_json()['error']


def test_create_booking_conflict(client):
    _book(client, '2025-07-01T10:00:00', '2025-07-01T10:30:00')
    # Overlaps the booking just created.
    resp = _book(client, '2025-07-01T10:15:00', '2025-07-01T10:45:00')
    assert resp.status_code == 409
    assert 'conflict' in resp.get_json()['error'].lower()


def test_create_booking_back_to_back_allowed(client):
    _book(client, '2025-07-01T10:00:00', '2025-07-01T10:30:00')
    # Starts exactly when the first ends -> allowed (strict < / > comparisons).
    resp = _book(client, '2025-07-01T10:30:00', '2025-07-01T11:00:00')
    assert resp.status_code == 201


def test_reschedule_booking(client):
    booking_id = _book(client, '2025-07-01T10:00:00',
                       '2025-07-01T10:30:00').get_json()['data']['id']
    resp = client.put(f'/bookings/{booking_id}', json={
        'start_time': '2025-07-01T15:00:00',
        'end_time': '2025-07-01T15:30:00',
    })
    body = resp.get_json()
    assert resp.status_code == 200
    assert body['data']['start_time'] == '2025-07-01T15:00:00'


def test_reschedule_not_found(client):
    resp = client.put('/bookings/999', json={
        'start_time': '2025-07-01T15:00:00',
        'end_time': '2025-07-01T15:30:00',
    })
    assert resp.status_code == 404


def test_cancel_booking_soft_deletes(client):
    booking_id = _book(client, '2025-07-01T10:00:00',
                       '2025-07-01T10:30:00').get_json()['data']['id']
    resp = client.delete(f'/bookings/{booking_id}')
    assert resp.status_code == 200
    assert resp.get_json()['data']['status'] == 'cancelled'
    # Row still exists, just cancelled -> its slot is free again.
    avail = client.get('/rooms/1/available?date=2025-07-01').get_json()['data']
    assert '2025-07-01T10:00:00' in {s['start_time'] for s in avail}


def test_cancel_not_found(client):
    resp = client.delete('/bookings/999')
    assert resp.status_code == 404
