"""US-002 (#70): expiration and protected API access regression tests."""
from datetime import timedelta

from app.core.security import create_access_token


def test_protected_endpoint_rejects_missing_session(client):
    endpoint = "/api/v1/auth/me"
    response = client.get(endpoint)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_token_rejected_but_valid_session_still_works(client):
    endpoint = "/api/v1/auth/me"
    account = {"full_name": "QA Login Test", "email": "qa.login@example.com", "password": "LunoTest123!"}
    registered = client.post("/api/v1/auth/register", json=account)
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": account["email"], "password": account["password"]})
    assert login.status_code == 200
    valid_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get(endpoint, headers=valid_headers).status_code == 200

    expired = create_access_token({"sub": str(registered.json()["id"])}, expires_delta=timedelta(minutes=-1))
    response = client.get(endpoint, headers={"Authorization": "Bearer " + expired})
    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "UNAUTHORIZED"
    assert error["message"] == "Oturumunuzun süresi doldu, lütfen tekrar giriş yapın."
    assert "email" not in response.json()
    assert client.get(endpoint, headers=valid_headers).status_code == 200
