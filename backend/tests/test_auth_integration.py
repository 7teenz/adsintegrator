from urllib.parse import parse_qs, urlparse

import pytest


@pytest.mark.smoke
def test_register_login_me_flow(client):
    register = client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "secret123", "full_name": "New User"},
    )
    assert register.status_code == 201
    payload = register.json()
    assert "verif" in payload["message"].lower()

    # If email delivery failed locally, the response includes a verification_url.
    # Use it to verify the account before attempting login.
    verification_url = payload.get("verification_url")
    if verification_url:
        parsed = urlparse(verification_url)
        token = parse_qs(parsed.query).get("token", [None])[0]
        assert token, "verification_url present but token missing"
        verify = client.get(f"/api/auth/verify-email?token={token}")
        assert verify.status_code == 200, verify.text

    login = client.post(
        "/api/auth/login",
        json={"email": "newuser@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "newuser@example.com"

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "newuser@example.com"
