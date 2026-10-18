"""US-004 / FR-010, FR-011 (#76): role persistence and authorization regression."""
import pytest
from app.models.user import User


def register(client, email, **extra):
    response = client.post("/api/v1/auth/register", json={"full_name": "QA Role", "email": email, "password": "LunoTest123!", **extra})
    assert response.status_code == 201
    return response.json()


def login(client, email):
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "LunoTest123!"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


@pytest.fixture
def role_accounts(client, db_session):
    admin = register(client, "role.admin@example.com")
    db_session.get(User, admin["id"]).role = "YONETICI"
    db_session.commit()
    member = register(client, "role.member@example.com")
    return admin, member, login(client, admin["email"]), login(client, member["email"])


@pytest.mark.parametrize("injected_role", ["YONETICI", "SUPER_ADMIN"])
def test_registration_cannot_override_default_role(client, injected_role):
    account = register(client, "role.inject@example.com", role=injected_role)
    assert account["role"] == "EKIP_UYESI"
    headers = login(client, account["email"])
    assert client.get("/api/v1/auth/me", headers=headers).json()["role"] == "EKIP_UYESI"
    assert client.get("/api/v1/users", headers=headers).status_code == 403


def test_role_changes_persist_and_apply_to_existing_session(client, role_accounts):
    _, member, admin_headers, member_headers = role_accounts
    assert client.get("/api/v1/users", headers=member_headers).status_code == 403
    for role, expected_access in [("YONETICI", 200), ("EKIP_UYESI", 403)]:
        changed = client.patch(f"/api/v1/users/{member['id']}/role", json={"role": role}, headers=admin_headers)
        assert changed.status_code == 200
        assert changed.json()["role"] == role
        me = client.get("/api/v1/auth/me", headers=member_headers)
        assert me.status_code == 200
        assert me.json()["role"] == role
        assert client.get("/api/v1/users", headers=member_headers).status_code == expected_access
        listing = client.get("/api/v1/users", params={"search": member["email"]}, headers=admin_headers)
        assert listing.status_code == 200
        assert listing.json()["items"][0]["role"] == role


@pytest.mark.parametrize("actor", ["anonymous", "member"])
def test_denied_role_update_keeps_target_unchanged(client, role_accounts, actor):
    admin, member, _, member_headers = role_accounts
    headers = member_headers if actor == "member" else {}
    response = client.patch(f"/api/v1/users/{member['id']}/role", json={"role": "YONETICI"}, headers=headers)
    assert response.status_code == (403 if actor == "member" else 401)
    assert response.json()["error"]["code"] == ("FORBIDDEN" if actor == "member" else "UNAUTHORIZED")
    me = client.get("/api/v1/auth/me", headers=member_headers)
    assert me.status_code == 200
    assert me.json()["role"] == "EKIP_UYESI"


@pytest.mark.parametrize("payload", [{"role": "SUPER_ADMIN"}, {"role": None}, {}])
def test_invalid_admin_role_update_preserves_existing_role(client, role_accounts, payload):
    _, member, admin_headers, member_headers = role_accounts
    response = client.patch(f"/api/v1/users/{member['id']}/role", json=payload, headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.get("/api/v1/auth/me", headers=member_headers).json()["role"] == "EKIP_UYESI"
