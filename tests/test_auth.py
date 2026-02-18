def test_register_and_login(client):
    res = client.post("/api/v1/auth/register", json={
        "username": "testdriver",
        "email": "driver@example.com",
        "password": "secret123",
    })
    assert res.status_code == 201
    data = res.json()
    assert data["username"] == "testdriver"

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
