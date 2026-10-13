import pytest
from datetime import date
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.models.user import User, SystemRole
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.enums import TaskStatus


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

# ==========================================
# US-007 (Issue #103) - GET /projects & GET /projects/{id} Testleri
# ==========================================

def test_list_my_projects_only_shows_member_projects(client: TestClient, db_session: Session):
    admin = create_user(client, "Proje Lideri", "leader@luno.com")
    promote_to_admin(db_session, admin["id"])
    admin_token = get_auth_token(client, "leader@luno.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Admin creates Project A and Project B
    res_a = client.post("/api/v1/projects", json={
        "name": "Proje A",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=admin_headers)
    proj_a = res_a.json()

    client.post("/api/v1/projects", json={
        "name": "Proje B",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=admin_headers)

    # Member user
    member = create_user(client, "Ekip Üyesi Mert", "mert@luno.com")
    member_token = get_auth_token(client, "mert@luno.com")
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Initially Mert is in 0 projects
    res_empty = client.get("/api/v1/projects", headers=member_headers)
    assert res_empty.status_code == 200
    assert res_empty.json()["total"] == 0
    assert len(res_empty.json()["items"]) == 0

    # Add Mert to Proje A in DB
    new_mem = ProjectMember(project_id=proj_a["id"], user_id=member["id"])
    db_session.add(new_mem)
    db_session.commit()

    # Now Mert should see only Proje A
    res_one = client.get("/api/v1/projects", headers=member_headers)
    assert res_one.status_code == 200
    assert res_one.json()["total"] == 1
    assert res_one.json()["items"][0]["id"] == proj_a["id"]
    assert res_one.json()["items"][0]["name"] == "Proje A"

def test_list_my_projects_pagination(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Page", "page_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "page_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        client.post("/api/v1/projects", json={
            "name": f"Proje {i}",
            "start_date": "2026-10-01",
            "end_date": "2026-10-31"
        }, headers=headers)

    res = client.get("/api/v1/projects?page=2&limit=2", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["limit"] == 2
    assert len(data["items"]) == 2

def test_get_project_detail_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Detail", "detail_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "detail_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res_create = client.post("/api/v1/projects", json={
        "name": "Detay Projesi",
        "description": "Detay açıklama",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = res_create.json()["id"]

    res_get = client.get(f"/api/v1/projects/{proj_id}", headers=headers)
    assert res_get.status_code == 200
    d = res_get.json()
    assert d["id"] == proj_id
    assert d["name"] == "Detay Projesi"
    assert d["description"] == "Detay açıklama"
    assert d["member_count"] == 1
    assert d["progress_percent"] == 0.0

def test_get_project_detail_not_member_access_denied(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Boss", "boss_user@luno.com")
    promote_to_admin(db_session, admin["id"])
    admin_token = get_auth_token(client, "boss_user@luno.com")

    res_create = client.post("/api/v1/projects", json={
        "name": "Gizli Proje",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    proj_id = res_create.json()["id"]

    other_user = create_user(client, "Dışarıdaki Kullanıcı", "outsider@luno.com")
    other_token = get_auth_token(client, "outsider@luno.com")

    res = client.get(f"/api/v1/projects/{proj_id}", headers={"Authorization": f"Bearer {other_token}"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert res.json()["error"]["message"] == "Bu projeye erişim yetkiniz yok."

def test_get_project_detail_not_found(client: TestClient):
    user = create_user(client, "Test User", "test_404@luno.com")
    token = get_auth_token(client, "test_404@luno.com")

    res = client.get("/api/v1/projects/99999", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROJECT_NOT_FOUND"
    assert res.json()["error"]["message"] == "Proje bulunamadı."

# ==========================================
# US-008 (Issue #106) - PATCH /projects/{id} Testleri
# ==========================================

def test_update_project_as_admin_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Patch", "patch_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "patch_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Eski Proje Adı",
        "description": "Eski açıklama",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    patch_res = client.patch(f"/api/v1/projects/{proj_id}", json={
        "name": "Yeni Proje Adı",
        "description": "Güncellenmiş açıklama",
        "end_date": "2026-11-15"
    }, headers=headers)
    assert patch_res.status_code == 200
    data = patch_res.json()
    assert data["id"] == proj_id
    assert data["name"] == "Yeni Proje Adı"
    assert data["description"] == "Güncellenmiş açıklama"
    assert data["end_date"] == "2026-11-15"
    assert data["start_date"] == "2026-10-01"

def test_update_project_invalid_date_range(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin DatePatch", "patch_date@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "patch_date@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Tarih Projesi",
        "start_date": "2026-10-10",
        "end_date": "2026-10-20"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    # Try setting end_date before start_date
    patch_res = client.patch(f"/api/v1/projects/{proj_id}", json={
        "end_date": "2026-10-05"
    }, headers=headers)
    assert patch_res.status_code == 400
    assert patch_res.json()["error"]["code"] == "INVALID_DATE_RANGE"

def test_update_project_as_regular_user_forbidden(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin P", "admin_p@luno.com")
    promote_to_admin(db_session, admin["id"])
    admin_token = get_auth_token(client, "admin_p@luno.com")

    create_res = client.post("/api/v1/projects", json={
        "name": "Admin Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    proj_id = create_res.json()["id"]

    member = create_user(client, "Üye P", "member_p@luno.com")
    member_token = get_auth_token(client, "member_p@luno.com")

    patch_res = client.patch(f"/api/v1/projects/{proj_id}", json={
        "name": "Değiştirilmek İstenen Ad"
    }, headers={"Authorization": f"Bearer {member_token}"})
    assert patch_res.status_code == 403
    assert patch_res.json()["error"]["code"] == "FORBIDDEN"

def test_update_project_not_found(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin 404Patch", "patch_404@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "patch_404@luno.com")

    patch_res = client.patch("/api/v1/projects/99999", json={
        "name": "Olmayan Proje"
    }, headers={"Authorization": f"Bearer {token}"})
    assert patch_res.status_code == 404
    assert patch_res.json()["error"]["code"] == "PROJECT_NOT_FOUND"

# ==========================================
# US-009 (Issue #109) - DELETE /projects/{id} Testleri
# ==========================================

def test_delete_project_as_admin_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Del", "del_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "del_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Silinecek Proje",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    # Verify project and its member exist
    assert db_session.query(Project).filter(Project.id == proj_id).first() is not None
    assert db_session.query(ProjectMember).filter(ProjectMember.project_id == proj_id).count() == 1

    # Delete project
    del_res = client.delete(f"/api/v1/projects/{proj_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify project and its member are deleted (cascade FR-020)
    assert db_session.query(Project).filter(Project.id == proj_id).first() is None
    assert db_session.query(ProjectMember).filter(ProjectMember.project_id == proj_id).count() == 0

def test_delete_project_as_regular_user_forbidden(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin D", "admin_d@luno.com")
    promote_to_admin(db_session, admin["id"])
    admin_token = get_auth_token(client, "admin_d@luno.com")

    create_res = client.post("/api/v1/projects", json={
        "name": "Korumalı Proje",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    proj_id = create_res.json()["id"]

    member = create_user(client, "Üye D", "member_d@luno.com")
    member_token = get_auth_token(client, "member_d@luno.com")

    del_res = client.delete(f"/api/v1/projects/{proj_id}", headers={"Authorization": f"Bearer {member_token}"})
    assert del_res.status_code == 403
    assert del_res.json()["error"]["code"] == "FORBIDDEN"

def test_delete_project_not_found(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin 404Del", "del_404@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "del_404@luno.com")

    del_res = client.delete("/api/v1/projects/99999", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 404
    assert del_res.json()["error"]["code"] == "PROJECT_NOT_FOUND"

# ==========================================
# US-010 (Issue #112) - Proje Üyeleri Testleri
# ==========================================

def test_list_project_members_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Yönetici Canan", "canan@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "canan@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Üye Test Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    res = client.get(f"/api/v1/projects/{proj_id}/members", headers=headers)
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 1
    assert members[0]["user"]["id"] == admin["id"]
    assert members[0]["email"] == "canan@luno.com"
    assert members[0]["system_role"] == "YONETICI"
    assert members[0]["technical_role"] is None

def test_list_project_members_access_denied_for_non_member(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Mem", "mem_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    admin_token = get_auth_token(client, "mem_admin@luno.com")

    create_res = client.post("/api/v1/projects", json={
        "name": "Özel Proje",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    proj_id = create_res.json()["id"]

    non_member = create_user(client, "Dışarıdaki", "outsider_mem@luno.com")
    token = get_auth_token(client, "outsider_mem@luno.com")

    res = client.get(f"/api/v1/projects/{proj_id}/members", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"

def test_add_project_member_success(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Add", "add_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "add_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Ekip Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    new_user = create_user(client, "Geliştirici Tolga", "tolga@luno.com")

    add_res = client.post(f"/api/v1/projects/{proj_id}/members", json={
        "email": "tolga@luno.com",
        "technical_role": "Backend Geliştirici"
    }, headers=headers)
    assert add_res.status_code == 201
    data = add_res.json()
    assert data["user"]["id"] == new_user["id"]
    assert data["email"] == "tolga@luno.com"
    assert data["technical_role"] == "Backend Geliştirici"
    assert data["system_role"] == "EKIP_UYESI"

    # Verify members count increased in detail endpoint
    detail_res = client.get(f"/api/v1/projects/{proj_id}", headers=headers)
    assert detail_res.json()["member_count"] == 2

def test_add_project_member_user_not_found(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Add404", "add404_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "add404_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Proje 404",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    add_res = client.post(f"/api/v1/projects/{proj_id}/members", json={
        "email": "olmayan@luno.com"
    }, headers=headers)
    assert add_res.status_code == 404
    assert add_res.json()["error"]["code"] == "USER_NOT_FOUND"

def test_add_project_member_already_member(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Dup", "dup_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "dup_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Çift Üye Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    # Admin is already member; try adding admin again
    add_res = client.post(f"/api/v1/projects/{proj_id}/members", json={
        "email": "dup_admin@luno.com"
    }, headers=headers)
    assert add_res.status_code == 409
    assert add_res.json()["error"]["code"] == "ALREADY_MEMBER"

def test_add_project_member_as_regular_user_forbidden(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Forb", "forb_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    admin_token = get_auth_token(client, "forb_admin@luno.com")

    create_res = client.post("/api/v1/projects", json={
        "name": "İzin Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    proj_id = create_res.json()["id"]

    member = create_user(client, "Normal Üye", "regular_add@luno.com")
    member_token = get_auth_token(client, "regular_add@luno.com")

    target = create_user(client, "Hedef", "target@luno.com")

    add_res = client.post(f"/api/v1/projects/{proj_id}/members", json={
        "email": "target@luno.com"
    }, headers={"Authorization": f"Bearer {member_token}"})
    assert add_res.status_code == 403
    assert add_res.json()["error"]["code"] == "FORBIDDEN"

def test_remove_project_member_success_unassigns_tasks(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Rem", "rem_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "rem_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Çıkarma Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    member_to_remove = create_user(client, "Çıkarılacak Üye", "remove_me@luno.com")
    client.post(f"/api/v1/projects/{proj_id}/members", json={
        "email": "remove_me@luno.com"
    }, headers=headers)

    # Assign a task to this member in DB
    task = Task(
        project_id=proj_id,
        title="Üyenin Görevi",
        status=TaskStatus.TODO,
        assignee_id=member_to_remove["id"]
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    assert task.assignee_id == member_to_remove["id"]

    # Remove the member
    del_res = client.delete(f"/api/v1/projects/{proj_id}/members/{member_to_remove['id']}", headers=headers)
    assert del_res.status_code == 204

    # Verify task is now unassigned (assignee_id == None, FR-022)
    db_session.expire_all()
    refreshed_task = db_session.query(Task).filter(Task.id == task.id).first()
    assert refreshed_task.assignee_id is None

    # Verify member is gone from project_members
    mem_check = db_session.query(ProjectMember).filter(
        ProjectMember.project_id == proj_id,
        ProjectMember.user_id == member_to_remove["id"]
    ).first()
    assert mem_check is None

def test_remove_project_member_cannot_remove_self(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin Self", "self_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "self_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Kendini Çıkarma Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/projects/{proj_id}/members/{admin['id']}", headers=headers)
    assert del_res.status_code == 400
    assert del_res.json()["error"]["code"] == "CANNOT_REMOVE_SELF"
    assert del_res.json()["error"]["message"] == "Kendinizi projeden çıkaramazsınız."

def test_remove_project_member_not_found(client: TestClient, db_session: Session):
    admin = create_user(client, "Admin NotMem", "notmem_admin@luno.com")
    promote_to_admin(db_session, admin["id"])
    token = get_auth_token(client, "notmem_admin@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/projects", json={
        "name": "Bulunamayan Üye Projesi",
        "start_date": "2026-10-01",
        "end_date": "2026-10-31"
    }, headers=headers)
    proj_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/projects/{proj_id}/members/99999", headers=headers)
    assert del_res.status_code == 404
    assert del_res.json()["error"]["code"] == "MEMBER_NOT_FOUND"




