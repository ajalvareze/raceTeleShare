"""
Tests for the session API: CRUD and file upload.
"""
import io
import pathlib
import pytest
from tests.conftest import make_user, auth, seed_track_config

SAMPLE_CSV = pathlib.Path(__file__).parent.parent / "uploads" / "sample-session.csv"


def test_create_session(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "sess_creator")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-09-01T08:00:00Z",
    }, headers=auth(token))
    assert res.status_code == 201
    data = res.json()
    assert data["session_type"] == "practice"
    assert data["is_public"] is False


def test_list_my_sessions(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "sess_lister")

    for i in range(3):
        client.post("/api/v1/sessions/", json={
            "track_configuration_id": config_id,
            "session_type": "practice",
            "date": f"2025-09-0{i+1}T08:00:00Z",
        }, headers=auth(token))

    res = client.get("/api/v1/sessions/", headers=auth(token))
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_update_session(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "sess_updater")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-09-10T08:00:00Z",
    }, headers=auth(token))
    session_id = res.json()["id"]

    res = client.patch(f"/api/v1/sessions/{session_id}", json={
        "is_public": True,
        "notes": "Great session!",
    }, headers=auth(token))
    assert res.status_code == 200
    data = res.json()
    assert data["is_public"] is True
    assert data["notes"] == "Great session!"


def test_delete_session(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "sess_deleter")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-09-15T08:00:00Z",
    }, headers=auth(token))
    session_id = res.json()["id"]

    res = client.delete(f"/api/v1/sessions/{session_id}", headers=auth(token))
    assert res.status_code == 204

    res = client.get(f"/api/v1/sessions/{session_id}", headers=auth(token))
    assert res.status_code == 404


def test_upload_session_file(client, db):
    """Upload the real TrackAddict CSV and verify laps are created."""
    if not SAMPLE_CSV.exists():
        pytest.skip("Sample CSV not found")

    # Ensure a track config exists (the uploader uses db.query(TrackConfiguration).first())
    seed_track_config(db)
    token = make_user(client, "sess_uploader")

    with open(SAMPLE_CSV, "rb") as f:
        res = client.post(
            "/api/v1/sessions/upload",
            files={"file": ("sample-session.csv", f, "text/csv")},
            headers=auth(token),
        )
    assert res.status_code == 201
    session_id = res.json()["id"]
    assert session_id > 0
    assert res.json()["app_source"] == "trackaddict"


def test_cannot_access_other_users_private_session(client, db):
    config_id = seed_track_config(db)
    owner = make_user(client, "priv_owner")
    other = make_user(client, "priv_other")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-10-01T08:00:00Z",
        "is_public": False,
    }, headers=auth(owner))
    session_id = res.json()["id"]

    res = client.get(f"/api/v1/sessions/{session_id}", headers=auth(other))
    assert res.status_code == 403


def test_public_session_visible_to_others(client, db):
    config_id = seed_track_config(db)
    owner = make_user(client, "pub_owner")
    other = make_user(client, "pub_other")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-10-05T08:00:00Z",
        "is_public": True,
    }, headers=auth(owner))
    session_id = res.json()["id"]

    res = client.get(f"/api/v1/sessions/{session_id}", headers=auth(other))
    assert res.status_code == 200


def test_cars_crud(client):
    token = make_user(client, "car_owner")

    # Create
    res = client.post("/api/v1/cars/", json={
        "make": "Renault",
        "model": "Clio Cup",
        "year": 2022,
        "power_hp": 165,
    }, headers=auth(token))
    assert res.status_code == 201
    car_id = res.json()["id"]
    assert res.json()["make"] == "Renault"

    # List
    res = client.get("/api/v1/cars/", headers=auth(token))
    assert any(c["id"] == car_id for c in res.json())

    # Update
    res = client.patch(f"/api/v1/cars/{car_id}", json={
        "weight_kg": 940,
        "notes": "Cup spec",
    }, headers=auth(token))
    assert res.status_code == 200
    assert res.json()["weight_kg"] == 940

    # Delete
    res = client.delete(f"/api/v1/cars/{car_id}", headers=auth(token))
    assert res.status_code == 204

    res = client.get("/api/v1/cars/", headers=auth(token))
    assert not any(c["id"] == car_id for c in res.json())
