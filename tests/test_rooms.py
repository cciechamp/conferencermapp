"""Tests for the /rooms routes and the availability endpoints.

The shared fixture seeds exactly one room (id 1) and one employee (id 1) and
no bookings, so tests that need a booking create one through the API first.
"""


def _book(client, start, end, room_id=1, organizer_id=1):
    """Create a booking via the API and return the response."""
    return client.post('/bookings', json={
        'room_id': room_id,
        'organizer_id': organizer_id,
        'start_time': start,
        'end_time': end,
    })


def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


def test_list_rooms(client):
    resp = client.get('/rooms')
    body = resp.get_json()
    assert resp.status_code == 200
    assert body['error'] is None
    assert len(body['data']) == 1
    assert body['data'][0]['name'] == 'Test Room'


def test_get_room_found(client):
    resp = client.get('/rooms/1')
    assert resp.status_code == 200
    assert resp.get_json()['data']['id'] == 1


def test_get_room_not_found(client):
    resp = client.get('/rooms/999')
    assert resp.status_code == 404
    assert resp.get_json()['error'] == 'Room not found'


def test_available_requires_date(client):
    resp = client.get('/rooms/1/available')
    assert resp.status_code == 400
    assert 'date' in resp.get_json()['error'].lower()


def test_available_rejects_bad_date(client):
    resp = client.get('/rooms/1/available?date=07-01-2025')
    assert resp.status_code == 400


def test_available_unknown_room(client):
    resp = client.get('/rooms/999/available?date=2025-07-01')
    assert resp.status_code == 404


def test_available_full_day_when_no_bookings(client):
    # Fresh fixture has no bookings, so the whole 09:00-18:00 grid is free.
    resp = client.get('/rooms/1/available?date=2025-07-01')
    assert resp.status_code == 200
    assert len(resp.get_json()['data']) == 18


def test_available_excludes_booked_slot(client):
    # Book 10:00-10:30, then that slot must disappear from availability.
    assert _book(client, '2025-07-01T10:00:00', '2025-07-01T10:30:00').status_code == 201
    body = client.get('/rooms/1/available?date=2025-07-01').get_json()
    starts = {s['start_time'] for s in body['data']}
    assert '2025-07-01T10:00:00' not in starts
    assert len(body['data']) == 17  # 18 slots minus the 1 booked
