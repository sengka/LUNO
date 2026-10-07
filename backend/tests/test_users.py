import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, SystemRole

def create_user(client: TestClient, full_name: str, email: str, password: str = "Password123", role: str = "EKIP_UYESI") -> dict:
    """Helper to create user and optionally update role."""
    res = client.post("/api/v1/auth/register", json={
        "full_name": full_name,
        "email": email,
        "password": password
    })
    user_data = res.json()
    return user_data

def get_auth_token(client: TestClient, email: str, password: str = "Password123") -> str:
    """Helper to login user and return JWT token."""
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    return res.json()["access_token"]

def promote_to_admin(db_session: Session, user_id: int):
    """Helper to directly update user role to YONETICI in DB for setup."""
    user = db_session.query(User).filter(User.id == user_id).first()
    if user:
        user.role = SystemRole.YONETICI.value
        db_session.commit()
        db_session.refresh(user)

# ==========================================
# US-004 (Issue #14) - GET /users Testleri
# ==========================================

def test_get_users_as_admin_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Yönetici Ali", "admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin@luno.com")

    # Create additional users
    create_user(client, "Ahmet Yılmaz", "ahmet@luno.com")
    create_user(client, "Ayşe Demir", "ayse@luno.com")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["limit"] == 10
    assert len(data["items"]) == 3

def test_get_users_search_filter(client: TestClient, db_session: Session):
    admin = create_user(client, "Yönetici Can", "admin_can@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_can@luno.com")

    create_user(client, "Mehmet Kaya", "mehmet@luno.com")
    create_user(client, "Selin Yıldız", "selin@test.com")

    headers = {"Authorization": f"Bearer {token}"}

    # Search by name "Selin"
    res1 = client.get("/api/v1/users?search=Selin", headers=headers)
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["total"] == 1
    assert d1["items"][0]["email"] == "selin@test.com"

    # Search by email "luno.com"
    res2 = client.get("/api/v1/users?search=luno.com", headers=headers)
    assert res2.status_code == 200
    d2 = res2.json()
    assert d2["total"] == 2  # admin_can and mehmet

def test_get_users_pagination(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin User", "admin_page@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_page@luno.com")

    for i in range(5):
        create_user(client, f"User {i}", f"user{i}@luno.com")

    headers = {"Authorization": f"Bearer {token}"}

    # Request page 2 with limit 2
    res = client.get("/api/v1/users?page=2&limit=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 6
    assert data["page"] == 2
    assert data["limit"] == 2
    assert len(data["items"]) == 2

def test_get_users_as_regular_user_forbidden(client: TestClient):
    user = create_user(client, "Normal Üye", "member@luno.com")
    token = get_auth_token(client, "member@luno.com")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/users", headers=headers)
    assert response.status_code == 403

    data = response.json()
    assert data["error"]["code"] == "FORBIDDEN"

def test_get_users_unauthorized(client: TestClient):
    response = client.get("/api/v1/users")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

# ==========================================
# US-004 (Issue #14) - PATCH /users/{id}/role Testleri
# ==========================================

def test_patch_user_role_as_admin_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Yönetici Zeynep", "admin_zeynep@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_zeynep@luno.com")

    target_user = create_user(client, "Bora Kaan", "bora@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Change EKIP_UYESI to YONETICI
    patch_res = client.patch(
        f"/api/v1/users/{target_user['id']}/role",
        json={"role": "YONETICI"},
        headers=headers
    )
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["id"] == target_user["id"]
    assert data["role"] == "YONETICI"

    # Change back to EKIP_UYESI
    patch_res2 = client.patch(
        f"/api/v1/users/{target_user['id']}/role",
        json={"role": "EKIP_UYESI"},
        headers=headers
    )
    assert patch_res2.status_code == 200
    assert patch_res2.json()["role"] == "EKIP_UYESI"

def test_patch_user_role_cannot_change_own_role(client: TestClient, db_session: Session):
    admin = create_user(client, "Yönetici Efe", "admin_efe@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_efe@luno.com")

    headers = {"Authorization": f"Bearer {token}"}

    # Admin tries to change own role
    response = client.patch(
        f"/api/v1/users/{admin['id']}/role",
        json={"role": "EKIP_UYESI"},
        headers=headers
    )
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "CANNOT_CHANGE_OWN_ROLE"
    assert data["error"]["message"] == "Kendi rolünüzü değiştiremezsiniz."

def test_patch_user_role_as_regular_user_forbidden(client: TestClient):
    member1 = create_user(client, "Üye One", "member1@luno.com")
    member2 = create_user(client, "Üye Two", "member2@luno.com")
    token = get_auth_token(client, "member1@luno.com")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        f"/api/v1/users/{member2['id']}/role",
        json={"role": "YONETICI"},
        headers=headers
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

def test_patch_user_role_user_not_found(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Boss", "boss@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "boss@luno.com")

    headers = {"Authorization": f"Bearer {token}"}
    response = client.patch(
        "/api/v1/users/99999/role",
        json={"role": "YONETICI"},
        headers=headers
    )
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["code"] == "USER_NOT_FOUND"
    assert data["error"]["message"] == "Kullanıcı bulunamadı."

def test_patch_user_role_invalid_role_value(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Invalid", "admin_invalid@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_invalid@luno.com")

    target = create_user(client, "Target User", "target@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.patch(
        f"/api/v1/users/{target['id']}/role",
        json={"role": "SUPER_ADMIN"},
        headers=headers
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
