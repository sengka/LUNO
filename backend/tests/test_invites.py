"""US-010 (FR-021): davet bağlantısı oluşturma ve kabul etme testleri (sözleşme 5.8 / 5.9)."""
from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_invite import ProjectInvite
from app.models.project_member import ProjectMember
from app.models.user import SystemRole, User

PASSWORD = "Password123"


def register_and_login(client: TestClient, db: Session, email: str, admin: bool = False) -> tuple[User, dict]:
    client.post("/api/v1/auth/register", json={
        "full_name": "Test " + email.split("@")[0], "email": email, "password": PASSWORD
    })
    user = db.query(User).filter(User.email == email).first()
    if admin:
        user.role = SystemRole.YONETICI.value
        db.commit()
    token = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


def make_project(db: Session, owner: User) -> Project:
    project = Project(
        name="Mobil Uygulama",
        description="Davet testi",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 11, 30),
        created_by_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.add(ProjectMember(project_id=project.id, user_id=owner.id))
    db.commit()
    db.refresh(project)
    return project


def token_from_url(url: str) -> str:
    return url.rsplit("/", 1)[-1]


# ==========================================
# 5.8 POST /projects/{project_id}/invites
# ==========================================

def test_create_invite_success(client: TestClient, db_session: Session):
    admin, headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    project = make_project(db_session, admin)

    res = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers)
    assert res.status_code == 201

    data = res.json()
    assert data["invite_url"].startswith("http://localhost:5173/davet/")
    assert len(token_from_url(data["invite_url"])) >= 32

    expires_at = datetime.strptime(data["expires_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    remaining = expires_at - datetime.now(timezone.utc)
    assert timedelta(days=6, hours=23) < remaining <= timedelta(days=7)

    assert db_session.query(ProjectInvite).filter(ProjectInvite.project_id == project.id).count() == 1


def test_create_invite_tokens_are_unique(client: TestClient, db_session: Session):
    admin, headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    project = make_project(db_session, admin)

    url1 = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers).json()["invite_url"]
    url2 = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers).json()["invite_url"]
    assert url1 != url2


def test_create_invite_forbidden_for_ekip_uyesi(client: TestClient, db_session: Session):
    admin, _ = register_and_login(client, db_session, "admin@luno.com", admin=True)
    member, member_headers = register_and_login(client, db_session, "uye@luno.com")
    project = make_project(db_session, admin)
    db_session.add(ProjectMember(project_id=project.id, user_id=member.id))
    db_session.commit()

    res = client.post(f"/api/v1/projects/{project.id}/invites", headers=member_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_create_invite_admin_not_member_denied(client: TestClient, db_session: Session):
    owner, _ = register_and_login(client, db_session, "sahip@luno.com", admin=True)
    _, other_headers = register_and_login(client, db_session, "admin2@luno.com", admin=True)
    project = make_project(db_session, owner)

    res = client.post(f"/api/v1/projects/{project.id}/invites", headers=other_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_create_invite_project_not_found(client: TestClient, db_session: Session):
    _, headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    res = client.post("/api/v1/projects/9999/invites", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_create_invite_requires_login(client: TestClient, db_session: Session):
    res = client.post("/api/v1/projects/1/invites")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


# ==========================================
# 5.9 POST /invites/{token}/accept
# ==========================================

def test_accept_invite_success(client: TestClient, db_session: Session):
    admin, admin_headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    user, user_headers = register_and_login(client, db_session, "yeni@luno.com")
    project = make_project(db_session, admin)

    url = client.post(f"/api/v1/projects/{project.id}/invites", headers=admin_headers).json()["invite_url"]
    res = client.post(f"/api/v1/invites/{token_from_url(url)}/accept", headers=user_headers)
    assert res.status_code == 200

    data = res.json()
    assert data["id"] == project.id
    assert data["name"] == "Mobil Uygulama"
    assert data["start_date"] == "2026-10-05"
    assert data["end_date"] == "2026-11-30"
    assert data["member_count"] == 2
    assert data["progress_percent"] == 0
    assert data["created_by"] == {"id": admin.id, "full_name": admin.full_name, "avatar_url": None}
    assert data["created_at"].endswith("Z")
    assert data["updated_at"].endswith("Z")

    membership = db_session.query(ProjectMember).filter(
        ProjectMember.project_id == project.id, ProjectMember.user_id == user.id
    ).first()
    assert membership is not None


def test_accept_invite_reusable_by_multiple_users(client: TestClient, db_session: Session):
    admin, admin_headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    _, h1 = register_and_login(client, db_session, "bir@luno.com")
    _, h2 = register_and_login(client, db_session, "iki@luno.com")
    project = make_project(db_session, admin)

    token = token_from_url(
        client.post(f"/api/v1/projects/{project.id}/invites", headers=admin_headers).json()["invite_url"]
    )
    assert client.post(f"/api/v1/invites/{token}/accept", headers=h1).status_code == 200
    res = client.post(f"/api/v1/invites/{token}/accept", headers=h2)
    assert res.status_code == 200
    assert res.json()["member_count"] == 3


def test_accept_invite_already_member(client: TestClient, db_session: Session):
    admin, admin_headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    project = make_project(db_session, admin)

    token = token_from_url(
        client.post(f"/api/v1/projects/{project.id}/invites", headers=admin_headers).json()["invite_url"]
    )
    res = client.post(f"/api/v1/invites/{token}/accept", headers=admin_headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ALREADY_MEMBER"
    assert res.json()["error"]["message"] == "Zaten bu projenin üyesisiniz."


def test_accept_invite_twice_returns_already_member(client: TestClient, db_session: Session):
    admin, admin_headers = register_and_login(client, db_session, "admin@luno.com", admin=True)
    _, user_headers = register_and_login(client, db_session, "yeni@luno.com")
    project = make_project(db_session, admin)

    token = token_from_url(
        client.post(f"/api/v1/projects/{project.id}/invites", headers=admin_headers).json()["invite_url"]
    )
    assert client.post(f"/api/v1/invites/{token}/accept", headers=user_headers).status_code == 200
    res = client.post(f"/api/v1/invites/{token}/accept", headers=user_headers)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "ALREADY_MEMBER"


def test_accept_invite_invalid_token(client: TestClient, db_session: Session):
    _, headers = register_and_login(client, db_session, "yeni@luno.com")
    res = client.post("/api/v1/invites/olmayan-token/accept", headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVITE_INVALID"
    assert res.json()["error"]["message"] == "Davet bağlantısı geçersiz veya süresi dolmuş."


def test_accept_invite_expired(client: TestClient, db_session: Session):
    admin, _ = register_and_login(client, db_session, "admin@luno.com", admin=True)
    user, user_headers = register_and_login(client, db_session, "yeni@luno.com")
    project = make_project(db_session, admin)

    db_session.add(ProjectInvite(
        token="suresi-dolmus-token",
        project_id=project.id,
        created_by_id=admin.id,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    ))
    db_session.commit()

    res = client.post("/api/v1/invites/suresi-dolmus-token/accept", headers=user_headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVITE_INVALID"
    assert db_session.query(ProjectMember).filter(ProjectMember.user_id == user.id).count() == 0


def test_accept_invite_requires_login(client: TestClient, db_session: Session):
    res = client.post("/api/v1/invites/herhangi-token/accept")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_project_delete_removes_invites(db_session: Session):
    owner = User(full_name="Sahip", email="sahip@luno.com", hashed_password="x", role="YONETICI")
    db_session.add(owner)
    db_session.commit()
    project = make_project(db_session, owner)
    db_session.add(ProjectInvite(
        token="silinecek", project_id=project.id, created_by_id=owner.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    ))
    db_session.commit()

    db_session.delete(project)
    db_session.commit()
    assert db_session.query(ProjectInvite).count() == 0
