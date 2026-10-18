"""US-003 / FR-007 (#73): logout replay and session isolation."""
from datetime import timedelta

import pytest
from app.core.security import create_access_token


@pytest.fixture
def logout_session(client):
    account = {"full_name": "QA Logout", "email": "qa.logout@example.com", "password": "LunoTest123!"}
    registered = client.post("/api/v1/auth/register", json=account)
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": account["email"], "password": account["password"]})
    assert login.status_code == 200
    return registered.json()["id"], {"Authorization": "Bearer " + login.json()["access_token"]}


@pytest.mark.parametrize("endpoint, authenticated_status", [("/api/v1/auth/me", 200), ("/api/v1/users", 403)])
def test_logout_replay_denies_protected_routes_and_repeated_logout(client, logout_session, endpoint, authenticated_status):
    _, headers = logout_session
    assert client.get(endpoint, headers=headers).status_code == authenticated_status
    logout = client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert logout.content == b""
    denied = client.get(endpoint, headers=headers)
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "UNAUTHORIZED"
    repeated = client.post("/api/v1/auth/logout", headers=headers)
    assert repeated.status_code == 401
    assert repeated.json()["error"]["code"] == "UNAUTHORIZED"
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


@pytest.mark.parametrize("invalid_kind", ["missing", "malformed", "expired"])
def test_invalid_logout_does_not_end_a_valid_session(client, logout_session, invalid_kind):
    user_id, valid_headers = logout_session
    if invalid_kind == "missing":
        headers = {}
    elif invalid_kind == "malformed":
        headers = {"Authorization": "Bearer corrupted-token"}
    else:
        expired = create_access_token({"sub": str(user_id)}, expires_delta=timedelta(minutes=-1))
        headers = {"Authorization": "Bearer " + expired}
    response = client.post("/api/v1/auth/logout", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert client.get("/api/v1/auth/me", headers=valid_headers).status_code == 200


def test_logout_does_not_revoke_a_distinct_session_for_same_user(client, logout_session):
    user_id, current_headers = logout_session
    other_token = create_access_token({"sub": str(user_id)}, expires_delta=timedelta(minutes=30))
    other_headers = {"Authorization": "Bearer " + other_token}
    assert client.get("/api/v1/auth/me", headers=other_headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=current_headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=current_headers).status_code == 401
    other_response = client.get("/api/v1/auth/me", headers=other_headers)
    assert other_response.status_code == 200
    assert other_response.json()["id"] == user_id
