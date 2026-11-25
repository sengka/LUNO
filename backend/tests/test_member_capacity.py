"""Üye kapasite ve teknik rol güncelleme testleri (US-025, US-044, sözleşme 5.11, #282)."""

from datetime import date, datetime, timezone

from app.core.security import create_access_token, get_password_hash
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import SystemRole, User


def _create_user(db, email: str, role: SystemRole, full_name: str = "Test Kullanıcı") -> tuple[User, dict]:
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=get_password_hash("Test1234!"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return user, {"Authorization": f"Bearer {token}"}


def _create_project_with_members(db, admin: User, member: User) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(
        name="Kapasite Test Projesi",
        description="Test",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    db.flush()
    db.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin.id, joined_at=now),
            ProjectMember(
                project_id=project.id,
                user_id=member.id,
                technical_role="Backend Geliştirici",
                capacity_points=None,
                joined_at=now,
            ),
        ]
    )
    db.commit()
    db.refresh(project)
    return project


def test_update_member_capacity_success_and_clear_to_null(client, db_session):
    admin, admin_headers = _create_user(db_session, "admin@example.com", SystemRole.YONETICI, "Yönetici")
    member, _ = _create_user(db_session, "member@example.com", SystemRole.EKIP_UYESI, "Ekip Üyesi")
    project = _create_project_with_members(db_session, admin, member)

    # Kapasite puanı tanımla
    resp = client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"capacity_points": 13},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["capacity_points"] == 13
    assert data["technical_role"] == "Backend Geliştirici"
    assert data["user"]["id"] == member.id

    # Kapasite null gönderilirse tanımsız (None) olur (US-044)
    resp_clear = client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"capacity_points": None},
        headers=admin_headers,
    )
    assert resp_clear.status_code == 200
    assert resp_clear.json()["capacity_points"] is None
    assert resp_clear.json()["technical_role"] == "Backend Geliştirici"


def test_update_member_capacity_omitted_preserves_existing(client, db_session):
    admin, admin_headers = _create_user(db_session, "admin2@example.com", SystemRole.YONETICI)
    member, _ = _create_user(db_session, "member2@example.com", SystemRole.EKIP_UYESI)
    project = _create_project_with_members(db_session, admin, member)

    client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"capacity_points": 21},
        headers=admin_headers,
    )

    resp = client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"technical_role": "Frontend Geliştirici"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["capacity_points"] == 21
    assert resp.json()["technical_role"] == "Frontend Geliştirici"


def test_update_member_capacity_invalid_values(client, db_session):
    admin, admin_headers = _create_user(db_session, "admin3@example.com", SystemRole.YONETICI)
    member, _ = _create_user(db_session, "member3@example.com", SystemRole.EKIP_UYESI)
    project = _create_project_with_members(db_session, admin, member)

    for bad_value in (0, -5, "onuc"):
        resp = client.patch(
            f"/api/v1/projects/{project.id}/members/{member.id}",
            json={"capacity_points": bad_value},
            headers=admin_headers,
        )
        assert resp.status_code == 422
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_member_capacity_authorization_and_not_found(client, db_session):
    admin, admin_headers = _create_user(db_session, "admin4@example.com", SystemRole.YONETICI)
    other_admin, other_admin_headers = _create_user(db_session, "other@example.com", SystemRole.YONETICI)
    member, member_headers = _create_user(db_session, "member4@example.com", SystemRole.EKIP_UYESI)
    outsider, _ = _create_user(db_session, "outsider@example.com", SystemRole.EKIP_UYESI)
    project = _create_project_with_members(db_session, admin, member)

    # Giriş yapmadan -> 401
    resp_unauth = client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"capacity_points": 10},
    )
    assert resp_unauth.status_code == 401

    # Ekip üyesi -> 403 FORBIDDEN
    resp_member = client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"capacity_points": 10},
        headers=member_headers,
    )
    assert resp_member.status_code == 403
    assert resp_member.json()["error"]["code"] == "FORBIDDEN"

    # Proje üyesi olmayan yönetici -> 403 PROJECT_ACCESS_DENIED
    resp_other_admin = client.patch(
        f"/api/v1/projects/{project.id}/members/{member.id}",
        json={"capacity_points": 10},
        headers=other_admin_headers,
    )
    assert resp_other_admin.status_code == 403
    assert resp_other_admin.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"

    # Projede üye olmayan hedef kullanıcı -> 404 MEMBER_NOT_FOUND
    resp_not_found = client.patch(
        f"/api/v1/projects/{project.id}/members/{outsider.id}",
        json={"capacity_points": 10},
        headers=admin_headers,
    )
    assert resp_not_found.status_code == 404
    assert resp_not_found.json()["error"]["code"] == "MEMBER_NOT_FOUND"
