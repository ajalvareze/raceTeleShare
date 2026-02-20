from tests.conftest import make_user, auth


def test_register_and_login(client):
    res = client.post("/api/v1/auth/register", json={
        "username": "testdriver",
        "email": "driver@example.com",
        "password": "secret123",
    })
    assert res.status_code == 201
    assert res.json()["username"] == "testdriver"

    res = client.post("/api/v1/auth/login", data={
        "username": "testdriver",
        "password": "secret123",
    })
    assert res.status_code == 200
    assert "access_token" in res.json()


def test_duplicate_registration(client):
    client.post("/api/v1/auth/register", json={
        "username": "dup_user",
        "email": "dup@example.com",
        "password": "pass",
    })
    res = client.post("/api/v1/auth/register", json={
        "username": "dup_user",
        "email": "dup@example.com",
        "password": "pass",
    })
    assert res.status_code == 400


def test_wrong_password(client):
    client.post("/api/v1/auth/register", json={
        "username": "wrongpass_user",
        "email": "wp@example.com",
        "password": "correct",
    })
    res = client.post("/api/v1/auth/login", data={
        "username": "wrongpass_user",
        "password": "wrong",
    })
    assert res.status_code == 401


def test_protected_route_without_token(client):
    res = client.get("/api/v1/sessions/")
    assert res.status_code == 401


def test_protected_route_with_token(client):
    token = make_user(client, "auth_test_user")
    res = client.get("/api/v1/sessions/", headers=auth(token))
    assert res.status_code == 200
