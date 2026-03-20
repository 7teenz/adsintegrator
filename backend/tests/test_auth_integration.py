import pytest


@pytest.mark.smoke
def test_register_login_me_flow(client):
    register = client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "secret123", "full_name": "New User"},
    )
    assert register.status_code == 201
    assert "verify your account" in register.json()["message"].lower()

    login = client.post(
        "/api/auth/login",
        json={"email": "newuser@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "newuser@example.com"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"
