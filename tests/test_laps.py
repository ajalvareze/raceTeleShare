import pytest
from tests.conftest import make_user, auth, seed_track_config


def test_create_session_and_lap(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "lap_tester")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-06-15T10:00:00Z",
    }, headers=auth(token))
    assert res.status_code == 201
    session_id = res.json()["id"]

    res = client.post("/api/v1/laps/", json={
        "session_id": session_id,
        "lap_number": 1,
        "lap_time_ms": 91500,
    }, headers=auth(token))
    assert res.status_code == 201
    lap = res.json()
    assert lap["lap_time_display"] == "1:31.500"


def test_lap_time_display_formatting(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "fmt_tester")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "hotlap",
        "date": "2025-07-01T09:00:00Z",
    }, headers=auth(token))
    session_id = res.json()["id"]

    cases = [
        (60000,  "1:00.000"),
        (96971,  "1:36.971"),
        (121500, "2:01.500"),
    ]
    for ms, expected in cases:
        res = client.post("/api/v1/laps/", json={
            "session_id": session_id,
            "lap_number": cases.index((ms, expected)) + 1,
            "lap_time_ms": ms,
        }, headers=auth(token))
        assert res.status_code == 201
        assert res.json()["lap_time_display"] == expected, f"{ms} → expected {expected}"


def test_list_laps_in_session(client, db):
    config_id = seed_track_config(db)
    token = make_user(client, "list_tester")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-06-20T10:00:00Z",
    }, headers=auth(token))
    session_id = res.json()["id"]

    for i in range(1, 4):
        client.post("/api/v1/laps/", json={
            "session_id": session_id,
            "lap_number": i,
            "lap_time_ms": 90000 + i * 1000,
        }, headers=auth(token))

    res = client.get(f"/api/v1/laps/session/{session_id}", headers=auth(token))
    assert res.status_code == 200
    laps = res.json()
    assert len(laps) == 3
    assert [l["lap_number"] for l in laps] == [1, 2, 3]


def test_private_session_access_denied(client, db):
    config_id = seed_track_config(db)
    owner_token = make_user(client, "session_owner")
    other_token = make_user(client, "session_other")

    res = client.post("/api/v1/sessions/", json={
        "track_configuration_id": config_id,
        "session_type": "practice",
        "date": "2025-06-20T11:00:00Z",
        "is_public": False,
    }, headers=auth(owner_token))
    session_id = res.json()["id"]

    res = client.get(f"/api/v1/sessions/{session_id}", headers=auth(other_token))
    assert res.status_code == 403
