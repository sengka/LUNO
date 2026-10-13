import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, SystemRole
from app.models.project import Project
from app.models.project_member import ProjectMember

def create_user(client: TestClient, full_name: str, email: str, password: str = "Password123") -> dict:
    res = client.post("/api/v1/auth/register", json={
        "full_name": full_name,
        "email": email,
        "password": password
    })
    return res.json()

def get_auth_token(client: TestClient, email: str, password: str = "Password123") -> str:
    res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    return res.json()["access_token"]

def promote_to_admin(db_session: Session, user_id: int):
    user = db_session.query(User).filter(User.id == user_id).first()
    if user:
        user.role = SystemRole.YONETICI.value
        db_session.commit()
        db_session.refresh(user)

# ==========================================
# US-006 (Issue #100) - POST /projects Testleri
# ==========================================

def test_create_project_as_admin_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Proje Yöneticisi", "pm@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "pm@luno.com")

    payload = {
        "name": "Mobil Uygulama",
        "description": "Müşteri için mobil uygulama geliştirme projesi",
        "start_date": "2026-10-05",
        "end_date": "2026-11-30"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Mobil Uygulama"
    assert data["description"] == "Müşteri için mobil uygulama geliştirme projesi"
    assert data["start_date"] == "2026-10-05"
    assert data["end_date"] == "2026-11-30"
    assert data["progress_percent"] == 0.0
    assert data["member_count"] == 1
    assert data["created_by"]["id"] == admin["id"]
    assert data["created_by"]["full_name"] == "Proje Yöneticisi"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Check creator is automatically a member in DB
    member = db_session.query(ProjectMember).filter(
        ProjectMember.project_id == data["id"],
        ProjectMember.user_id == admin["id"]
    ).first()
    assert member is not None

def test_create_project_invalid_date_range(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin User", "admin_date@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_date@luno.com")

    payload = {
        "name": "Geçersiz Tarihli Proje",
        "description": "Açıklama",
        "start_date": "2026-11-30",
        "end_date": "2026-10-05"  # end before start
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 400
    data = response.json()
    assert data["error"]["code"] == "INVALID_DATE_RANGE"
    assert data["error"]["message"] == "Bitiş tarihi başlangıç tarihinden önce olamaz."

def test_create_project_as_regular_user_forbidden(client: TestClient):
    user = create_user(client, "Normal Üye", "regular@luno.com")
    token = get_auth_token(client, "regular@luno.com")

    payload = {
        "name": "İzinsiz Proje",
        "start_date": "2026-10-05",
        "end_date": "2026-11-30"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"

def test_create_project_unauthorized(client: TestClient):
    payload = {
        "name": "Tokensiz Proje",
        "start_date": "2026-10-05",
        "end_date": "2026-11-30"
    }
    response = client.post("/api/v1/projects", json=payload)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"

def test_create_project_validation_error(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Val", "admin_val@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "admin_val@luno.com")

    # Name too short (<2 chars)
    payload = {
        "name": "X",
        "start_date": "2026-10-05",
        "end_date": "2026-11-30"
    }
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/api/v1/projects", json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
