from datetime import date, datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, SystemRole
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.enums import TaskStatus, Priority


def create_user(client: TestClient, full_name: str, email: str, password: str = "Password123") -> dict:
    res = client.post("/api/v1/auth/register", json={
        "full_name": full_name,
        "email": email,
        "password": password
    })
    return res.json()


def get_token(client: TestClient, email: str, password: str = "Password123") -> str:
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


def create_project(db_session: Session, owner_id: int) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(
        name="LUNO Test Projesi",
        description="Görev testleri için proje",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 11, 30),
        created_by_id=owner_id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(project)
    db_session.flush()

    member = ProjectMember(
        project_id=project.id,
        user_id=owner_id,
        technical_role="Yönetici",
        joined_at=now,
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(project)
    return project


def add_member_to_project(db_session: Session, project_id: int, user_id: int):
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        technical_role="Geliştirici",
        joined_at=datetime.now(timezone.utc),
    )
    db_session.add(member)
    db_session.commit()


# ============================================================================
# US-014 (Issue #24) - PATCH /tasks/{task_id}/status Testleri
# ============================================================================

def test_assignee_can_update_task_status_successfully(client: TestClient, db_session: Session):
    """FR-033: Ekip üyesi kendisine atanmış görevin durumunu güncelleyebilir."""
    admin_data = create_user(client, "Proje Yöneticisi", "admin@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Ahmet Geliştirici", "ahmet@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])
    token = get_token(client, "ahmet@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    task = Task(
        project_id=project.id,
        title="Giriş ekranı tasarımı",
        description="Arayüz çizimi",
        status=TaskStatus.TODO,
        priority=Priority.YUKSEK,
        story_points=5,
        assignee_id=member_data["id"],
        created_by_id=admin_data["id"],
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # 1. TODO -> IN_PROGRESS
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == task.id
    assert data["status"] == "IN_PROGRESS"
    assert data["title"] == "Giriş ekranı tasarımı"
    assert data["assignee"]["id"] == member_data["id"]
    assert data["created_by"]["id"] == admin_data["id"]
    assert "created_at" in data
    assert "updated_at" in data

    # 2. IN_PROGRESS -> REVIEW_TESTING
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "REVIEW_TESTING"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "REVIEW_TESTING"

    # 3. REVIEW_TESTING -> DONE
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "DONE"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "DONE"

    # 4. DONE -> TODO (Kanban'da geriye taşıma)
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "TODO"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "TODO"


def test_admin_can_update_task_status_of_any_task(client: TestClient, db_session: Session):
    """Yönetici kendisine atanmamış bir görevin de durumunu değiştirebilir."""
    admin_data = create_user(client, "Yönetici Kullanıcı", "admin2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    token = get_token(client, "admin2@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    project = create_project(db_session, admin_data["id"])
    member_data = create_user(client, "Mehmet Dev", "mehmet@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    task = Task(
        project_id=project.id,
        title="Veritabanı migration",
        status=TaskStatus.TODO,
        assignee_id=member_data["id"],
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"


def test_admin_can_update_unassigned_task(client: TestClient, db_session: Session):
    """Yönetici henüz kimseye atanmamış görevin durumunu değiştirebilir."""
    admin_data = create_user(client, "Admin Unassigned", "admin_unassigned@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    token = get_token(client, "admin_unassigned@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    project = create_project(db_session, admin_data["id"])
    task = Task(
        project_id=project.id,
        title="Atamasız görev",
        status=TaskStatus.TODO,
        assignee_id=None,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "IN_PROGRESS"


def test_non_assignee_cannot_update_task_status(client: TestClient, db_session: Session):
    """FR-034: Ekip üyesi kendisine atanmamış görevin durumunu değiştiremez (403 NOT_TASK_ASSIGNEE)."""
    admin_data = create_user(client, "Admin", "admin_sec@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    user_a = create_user(client, "Atanan Üye", "assignee@luno.com")
    user_b = create_user(client, "Başka Üye", "other@luno.com")
    add_member_to_project(db_session, project.id, user_a["id"])
    add_member_to_project(db_session, project.id, user_b["id"])

    task = Task(
        project_id=project.id,
        title="Kritik Görev",
        status=TaskStatus.TODO,
        assignee_id=user_a["id"],
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # user_b attempts to update user_a's task
    token_b = get_token(client, "other@luno.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}

    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers_b)
    assert res.status_code == 403
    data = res.json()
    assert data["error"]["code"] == "NOT_TASK_ASSIGNEE"
    assert data["error"]["message"] == "Size atanmamış bir görevin durumunu değiştiremezsiniz."

    # Verify task status was NOT changed in DB
    db_session.refresh(task)
    assert task.status == TaskStatus.TODO


def test_member_cannot_update_unassigned_task(client: TestClient, db_session: Session):
    """Ekip üyesi atamasız görevin durumunu değiştiremez (403 NOT_TASK_ASSIGNEE)."""
    admin_data = create_user(client, "Admin", "admin_unassigned2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member = create_user(client, "Üye", "member_unassigned@luno.com")
    add_member_to_project(db_session, project.id, member["id"])

    task = Task(
        project_id=project.id,
        title="Sahipsiz İş",
        status=TaskStatus.TODO,
        assignee_id=None,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "member_unassigned@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "NOT_TASK_ASSIGNEE"


def test_cannot_update_pending_approval_task(client: TestClient, db_session: Session):
    """Sözleşme 6.5: Onay bekleyen görevin durumu değiştirilemez (400 TASK_NOT_ACTIVE)."""
    admin_data = create_user(client, "Admin", "admin_pending@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member = create_user(client, "Üye", "member_pending@luno.com")
    add_member_to_project(db_session, project.id, member["id"])

    task = Task(
        project_id=project.id,
        title="Onay Bekleyen Görev",
        status=TaskStatus.ONAY_BEKLIYOR,
        assignee_id=member["id"],
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Test by assignee
    token = get_token(client, "member_pending@luno.com")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 400
    data = res.json()
    assert data["error"]["code"] == "TASK_NOT_ACTIVE"
    assert data["error"]["message"] == "Onay bekleyen veya reddedilen görevin durumu değiştirilemez."

    # Test by admin as well
    admin_token = get_token(client, "admin_pending@luno.com")
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    res_admin = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "IN_PROGRESS"}, headers=admin_headers)
    assert res_admin.status_code == 400
    assert res_admin.json()["error"]["code"] == "TASK_NOT_ACTIVE"

    # Status must remain unchanged
    db_session.refresh(task)
    assert task.status == TaskStatus.ONAY_BEKLIYOR


def test_cannot_update_rejected_task(client: TestClient, db_session: Session):
    """Sözleşme 6.5: Reddedilen görevin durumu değiştirilemez (400 TASK_NOT_ACTIVE)."""
    admin_data = create_user(client, "Admin", "admin_rejected@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member = create_user(client, "Üye", "member_rejected@luno.com")
    add_member_to_project(db_session, project.id, member["id"])

    task = Task(
        project_id=project.id,
        title="Reddedilen Görev",
        status=TaskStatus.REDDEDILDI,
        assignee_id=member["id"],
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "member_rejected@luno.com")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "TODO"}, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "TASK_NOT_ACTIVE"


def test_task_not_found(client: TestClient, db_session: Session):
    """Olmayan görev için 404 TASK_NOT_FOUND döner."""
    user = create_user(client, "User", "user_404@luno.com")
    token = get_token(client, "user_404@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch("/api/v1/tasks/99999/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "TASK_NOT_FOUND"
    assert data["error"]["message"] == "Görev bulunamadı."


def test_unauthenticated_request(client: TestClient):
    """Token olmadan istek atıldığında 401 döner."""
    res = client.patch("/api/v1/tasks/1/status", json={"status": "IN_PROGRESS"})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_status_value_rejected(client: TestClient, db_session: Session):
    """İzin verilenler dışındaki durum değerleri (422) reddedilir."""
    admin_data = create_user(client, "Admin", "admin_val@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    task = Task(
        project_id=project.id,
        title="Test Görevi",
        status=TaskStatus.TODO,
        assignee_id=admin_data["id"],
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_val@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Bilinmeyen string
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "UNKNOWN_STATUS"}, headers=headers)
    assert res.status_code == 422

    # 2. ONAY_BEKLIYOR bu uç nokta ile atanamaz (sözleşme 6.5 sadece TODO, IN_PROGRESS, REVIEW_TESTING, DONE)
    res2 = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "ONAY_BEKLIYOR"}, headers=headers)
    assert res2.status_code == 422

    # 3. Boş gövde
    res3 = client.patch(f"/api/v1/tasks/{task.id}/status", json={}, headers=headers)
    assert res3.status_code == 422


def test_admin_not_project_member_cannot_update(client: TestClient, db_session: Session):
    """Sözleşme 1.2: Yönetici = YONETICI rolünde VE projenin üyesi. Üye olmayan yönetici 403 alır."""
    owner = create_user(client, "Sahip", "owner_nm@luno.com")
    promote_to_admin(db_session, owner["id"])
    project = create_project(db_session, owner["id"])

    other_admin = create_user(client, "Diğer Yönetici", "other_admin@luno.com")
    promote_to_admin(db_session, other_admin["id"])

    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO, assignee_id=owner["id"])
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    headers = {"Authorization": f"Bearer {get_token(client, 'other_admin@luno.com')}"}
    res = client.patch(f"/api/v1/tasks/{task.id}/status", json={"status": "DONE"}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "NOT_TASK_ASSIGNEE"

    db_session.refresh(task)
    assert task.status == TaskStatus.TODO


def test_response_matches_task_object(client: TestClient, db_session: Session):
    """Yanıt sözleşme 2. bölümdeki Task nesnesinin tüm alanlarını içerir."""
    admin_data = create_user(client, "Admin", "admin_shape@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    token = get_token(client, "admin_shape@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    project = create_project(db_session, admin_data["id"])

    parent_task = Task(
        project_id=project.id,
        title="Ana Görev",
        status=TaskStatus.TODO,
        assignee_id=admin_data["id"],
    )
    db_session.add(parent_task)
    db_session.flush()

    sub1 = Task(project_id=project.id, title="Alt 1", status=TaskStatus.DONE, parent_id=parent_task.id)
    sub2 = Task(project_id=project.id, title="Alt 2", status=TaskStatus.IN_PROGRESS, parent_id=parent_task.id)
    db_session.add_all([sub1, sub2])
    db_session.commit()
    db_session.refresh(parent_task)

    res = client.patch(f"/api/v1/tasks/{parent_task.id}/status", json={"status": "IN_PROGRESS"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    expected_keys = {
        "id", "project_id", "parent_id", "title", "description", "status", "priority",
        "story_points", "start_date", "due_date", "assignee", "created_by", "sprint_id",
        "labels", "subtask_count", "subtask_done_count", "depends_on", "risk_level",
        "comment_count", "file_count", "created_at", "updated_at",
    }
    assert set(data.keys()) == expected_keys
    assert data["subtask_count"] == 2
    assert data["subtask_done_count"] == 1
    assert data["updated_at"].endswith("Z")
