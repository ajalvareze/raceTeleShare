import pytest


def _register_login(client, username="lap_tester"):
    client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "pass123",
    })
    res = client.post("/api/v1/auth/login", data={"username": username, "password": "pass123"})
    return res.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_session_and_lap(client):
    from app.models.track import Track
    from tests.conftest import TestingSessionLocal

    # Seed a track
    db = TestingSessionLocal()
    track = Track(name="Monza", country="Italy")
    db.add(track)
    db.commit()
    track_id = track.id
    db.close()

    token = _register_login(client)

    res = client.post("/api/v1/sessions/", json={
        "track_id": track_id,
        "session_type": "practice",
        "date": "2025-06-15T10:00:00Z",
    }, headers=_auth(token))
    assert res.status_code == 201
    session_id = res.json()["id"]

    res = client.post("/api/v1/laps/", json={
        "session_id": session_id,
        "lap_number": 1,
        "lap_time_ms": 91500,
    }, headers=_auth(token))
    assert res.status_code == 201
    lap = res.json()
    assert lap["lap_time_display"] == "1:31.500"
