"""Tests for the /rooms routes and the availability endpoints."""


def test_health(client):
    resp = client.get('/health')
    assert resp.status_code == 200
    assert resp.get_json()['status'] == 'ok'


def test_list_rooms(client):
    resp = client.get('/rooms')
    body = resp.get_json()
    assert resp.status_code == 200
    assert body['error'] is None
    assert len(body['data']) == 2
    assert {r['name'] for r in body['data']} == {'Test Room A', 'Test Room B'}


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


def test_available_excludes_booked_slot(client):
    # Room A has a booking 10:00-10:30 on 2025-07-01, so that slot is gone.
    resp = client.get('/rooms/1/available?date=2025-07-01')
    body = resp.get_json()
    assert resp.status_code == 200
    starts = {s['start_time'] for s in body['data']}
    assert '2025-07-01T10:00:00' not in starts
    # Business hours 09:00-18:00 in 30-min slots = 18 total, minus the 1 booked.
    assert len(body['data']) == 17


def test_available_full_day_when_no_bookings(client):
    # Room B (id 2) has no bookings, so the whole grid is free.
    resp = client.get('/rooms/2/available?date=2025-07-01')
    assert len(resp.get_json()['data']) == 18
