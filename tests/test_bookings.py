"""Tests for the /bookings CRUD routes, including conflict handling."""


def test_list_bookings(client):
    resp = client.get('/bookings')
    body = resp.get_json()
    assert resp.status_code == 200
    assert len(body['data']) == 1


def test_list_bookings_filtered_by_room(client):
    assert len(client.get('/bookings?room_id=1').get_json()['data']) == 1
    assert len(client.get('/bookings?room_id=2').get_json()['data']) == 0


def test_get_booking_not_found(client):
    resp = client.get('/bookings/999')
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'Booking not found'


def test_create_booking_success(client):
    payload = {
        'room_id': 1,
        'organizer_id': 1,
        'start_time': '2025-07-01T11:00:00',
        'end_time': '2025-07-01T11:30:00',
        'meeting_title': 'New sync',
        'attendees': 2,
    }
    resp = client.post('/bookings', json=payload)
    body = resp.get_json()
    assert resp.status_code == 201
    assert body['data']['status'] == 'scheduled'
    assert body['data']['meeting_title'] == 'New sync'


def test_create_booking_missing_field(client):
    resp = client.post('/bookings', json={'room_id': 1})
    assert resp.status_code == 400
    assert 'Missing field' in resp.get_json()['error']


def test_create_booking_end_before_start(client):
    payload = {
        'room_id': 1,
        'organizer_id': 1,
        'start_time': '2025-07-01T12:00:00',
        'end_time': '2025-07-01T11:00:00',
    }
    resp = client.post('/bookings', json=payload)
    assert resp.status_code == 400
    assert 'after' in resp.get_json()['error']


def test_create_booking_conflict(client):
    # Overlaps the seeded 10:00-10:30 booking in room 1.
    payload = {
        'room_id': 1,
        'organizer_id': 2,
        'start_time': '2025-07-01T10:15:00',
        'end_time': '2025-07-01T10:45:00',
    }
    resp = client.post('/bookings', json=payload)
    assert resp.status_code == 409
    assert 'conflict' in resp.get_json()['error'].lower()


def test_create_booking_back_to_back_allowed(client):
    # Starts exactly when the seeded booking ends -> must be allowed (strict <>).
    payload = {
        'room_id': 1,
        'organizer_id': 2,
        'start_time': '2025-07-01T10:30:00',
        'end_time': '2025-07-01T11:00:00',
    }
    resp = client.post('/bookings', json=payload)
    assert resp.status_code == 201


def test_reschedule_booking(client):
    payload = {
        'start_time': '2025-07-01T15:00:00',
        'end_time': '2025-07-01T15:30:00',
    }
    resp = client.put('/bookings/1', json=payload)
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
    resp = client.delete('/bookings/1')
    assert resp.status_code == 200
    assert resp.get_json()['data']['status'] == 'cancelled'
    # Row still exists, just cancelled -> its slot is now free again.
    avail = client.get('/rooms/1/available?date=2025-07-01').get_json()['data']
    assert '2025-07-01T10:00:00' in {s['start_time'] for s in avail}


def test_cancel_not_found(client):
    resp = client.delete('/bookings/999')
    assert resp.status_code == 404
