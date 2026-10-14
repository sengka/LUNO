"""US-005 (FR-012, FR-013): ortak yetki bağımlılıklarının birim testleri."""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_project_member, require_admin
from app.core.exceptions import (
    ForbiddenException,
    ProjectAccessDeniedException,
    ProjectNotFoundException,
)
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import SystemRole, User


def make_user(db: Session, email: str, role: str = SystemRole.EKIP_UYESI.value) -> User:
    user = User(full_name="Test Kullanıcı", email=email, hashed_password="x", role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_project(db: Session, owner: User) -> Project:
    project = Project(
        name="Test Projesi",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 1),
        created_by_id=owner.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def add_member(db: Session, project: Project, user: User) -> ProjectMember:
    member = ProjectMember(project_id=project.id, user_id=user.id)
    db.add(member)
    db.commit()
    return member


# ==========================================
# require_admin (FR-012)
# ==========================================

def test_require_admin_allows_yonetici(db_session: Session):
    admin = make_user(db_session, "admin@luno.com", SystemRole.YONETICI.value)
    assert require_admin(current_user=admin) is admin


def test_require_admin_rejects_ekip_uyesi(db_session: Session):
    member = make_user(db_session, "uye@luno.com")
    with pytest.raises(ForbiddenException) as exc:
        require_admin(current_user=member)
    assert exc.value.status_code == 403
    assert exc.value.code == "FORBIDDEN"
    assert exc.value.message == "Bu işlem için yetkiniz yok."


def test_require_admin_endpoint_returns_403_error_format(client: TestClient):
    """Bağımlılık bir uç noktada kullanıldığında sözleşmedeki hata formatı döner (1.5)."""
    client.post("/api/v1/auth/register", json={
        "full_name": "Ekip Üyesi", "email": "uye2@luno.com", "password": "Password123"
    })
    token = client.post("/api/v1/auth/login", json={
        "email": "uye2@luno.com", "password": "Password123"
    }).json()["access_token"]

    res = client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


# ==========================================
# get_project_member (FR-013)
# ==========================================

def test_get_project_member_returns_membership(db_session: Session):
    admin = make_user(db_session, "admin@luno.com", SystemRole.YONETICI.value)
    project = make_project(db_session, admin)
    add_member(db_session, project, admin)

    member = get_project_member(project_id=project.id, current_user=admin, db=db_session)
    assert member.project_id == project.id
    assert member.user_id == admin.id


def test_get_project_member_rejects_non_member(db_session: Session):
    admin = make_user(db_session, "admin@luno.com", SystemRole.YONETICI.value)
    outsider = make_user(db_session, "disari@luno.com")
    project = make_project(db_session, admin)
    add_member(db_session, project, admin)

    with pytest.raises(ProjectAccessDeniedException) as exc:
        get_project_member(project_id=project.id, current_user=outsider, db=db_session)
    assert exc.value.status_code == 403
    assert exc.value.code == "PROJECT_ACCESS_DENIED"
    assert exc.value.message == "Bu projeye erişim yetkiniz yok."


def test_get_project_member_rejects_non_member_admin(db_session: Session):
    """Yönetici rolü tek başına yetmez; projenin üyesi de olmalıdır (sözleşme 1.2)."""
    owner = make_user(db_session, "sahip@luno.com", SystemRole.YONETICI.value)
    other_admin = make_user(db_session, "admin2@luno.com", SystemRole.YONETICI.value)
    project = make_project(db_session, owner)
    add_member(db_session, project, owner)

    with pytest.raises(ProjectAccessDeniedException):
        get_project_member(project_id=project.id, current_user=other_admin, db=db_session)


def test_get_project_member_project_not_found(db_session: Session):
    user = make_user(db_session, "uye@luno.com")
    with pytest.raises(ProjectNotFoundException) as exc:
        get_project_member(project_id=9999, current_user=user, db=db_session)
    assert exc.value.status_code == 404
    assert exc.value.code == "PROJECT_NOT_FOUND"
