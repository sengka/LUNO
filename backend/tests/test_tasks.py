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


# ============================================================================
# US-011 (Issue #149) - Görev oluşturma ve listeleme API'si Testleri
# ============================================================================

def test_admin_creates_task_successfully(client: TestClient, db_session: Session):
    """FR-024, FR-025: Yönetici proje üyesiyse TODO durumunda görev oluşturabilir."""
    admin_data = create_user(client, "Yonetici US11", "admin_us11@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US11", "member_us11@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    token = get_token(client, "admin_us11@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Veritabanı Şeması",
        "description": "PostgreSQL tabloları oluşturulacak",
        "assignee_id": member_data["id"],
        "start_date": "2026-10-10",
        "due_date": "2026-10-20",
        "priority": "YUKSEK",
        "story_points": 5,
    }

    res = client.post(f"/api/v1/projects/{project.id}/tasks", json=payload, headers=headers)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Veritabanı Şeması"
    assert data["description"] == "PostgreSQL tabloları oluşturulacak"
    assert data["status"] == "TODO"
    assert data["priority"] == "YUKSEK"
    assert data["story_points"] == 5
    assert data["assignee"]["id"] == member_data["id"]
    assert data["created_by"]["id"] == admin_data["id"]
    assert data["subtask_count"] == 0


def test_member_cannot_create_task_forbidden(client: TestClient, db_session: Session):
    """US-011: Ekip üyesinin görev oluşturması/önermesi Sprint 8'e kadar 403 FORBIDDEN döner."""
    admin_data = create_user(client, "Admin US11-2", "admin_us11_2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US11-2", "member_us11_2@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    token = get_token(client, "member_us11_2@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"title": "Ekip üyesi görevi"}
    res = client.post(f"/api/v1/projects/{project.id}/tasks", json=payload, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"
    assert res.json()["error"]["message"] == "Bu işlem için yetkiniz yok."


def test_admin_not_member_cannot_create_task(client: TestClient, db_session: Session):
    """FR-013: Proje üyesi olmayan yönetici 403 PROJECT_ACCESS_DENIED alır."""
    owner_data = create_user(client, "Owner US11-3", "owner_us11_3@luno.com")
    promote_to_admin(db_session, owner_data["id"])
    project = create_project(db_session, owner_data["id"])

    other_admin = create_user(client, "Dış Admin US11-3", "dis_admin_us11_3@luno.com")
    promote_to_admin(db_session, other_admin["id"])

    token = get_token(client, "dis_admin_us11_3@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "Test"}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_create_task_nonexistent_project(client: TestClient, db_session: Session):
    admin_data = create_user(client, "Admin US11-4", "admin_us11_4@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    token = get_token(client, "admin_us11_4@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post("/api/v1/projects/99999/tasks", json={"title": "Test"}, headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_create_task_invalid_date_range(client: TestClient, db_session: Session):
    """FR-025: Teslim tarihi başlangıç tarihinden önce olamaz (400 INVALID_DATE_RANGE)."""
    admin_data = create_user(client, "Admin US11-5", "admin_us11_5@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    token = get_token(client, "admin_us11_5@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        f"/api/v1/projects/{project.id}/tasks",
        json={"title": "Tarih Hatası", "start_date": "2026-10-25", "due_date": "2026-10-20"},
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_DATE_RANGE"
    assert res.json()["error"]["message"] == "Teslim tarihi başlangıç tarihinden önce olamaz."


def test_create_task_assignee_not_member(client: TestClient, db_session: Session):
    """Sözleşme 6.2: Atanan kişi projenin üyesi değilse 400 ASSIGNEE_NOT_MEMBER."""
    admin_data = create_user(client, "Admin US11-6", "admin_us11_6@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    outsider = create_user(client, "Dış Kullanıcı", "disari_us11_6@luno.com")

    token = get_token(client, "admin_us11_6@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.post(
        f"/api/v1/projects/{project.id}/tasks",
        json={"title": "Görev", "assignee_id": outsider["id"]},
        headers=headers,
    )
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "ASSIGNEE_NOT_MEMBER"


def test_create_task_validation_errors(client: TestClient, db_session: Session):
    """FR-025: Görev başlığı zorunludur ve en az 2 karakter olmalıdır."""
    admin_data = create_user(client, "Admin US11-7", "admin_us11_7@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    token = get_token(client, "admin_us11_7@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Boş başlık
    res = client.post(f"/api/v1/projects/{project.id}/tasks", json={"title": "   "}, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_tasks_and_pagination(client: TestClient, db_session: Session):
    """FR-041: Proje görevlerini listeleme, sayfalama ve filtreleme."""
    admin_data = create_user(client, "Admin US11-8", "admin_us11_8@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US11-8", "member_us11_8@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    token = get_token(client, "member_us11_8@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 3 görev ekleyelim: 2 TODO, 1 DONE, 1 ONAY_BEKLIYOR (pending), 1 alt görev
    t1 = Task(project_id=project.id, title="Frontend Giriş", status=TaskStatus.TODO, priority=Priority.YUKSEK)
    t2 = Task(project_id=project.id, title="Backend API", status=TaskStatus.DONE, priority=Priority.ORTA)
    t3 = Task(project_id=project.id, title="DevOps Setup", status=TaskStatus.IN_PROGRESS, assignee_id=member_data["id"])
    t_pending = Task(project_id=project.id, title="Onay Bekleyen İş", status=TaskStatus.ONAY_BEKLIYOR)
    db_session.add_all([t1, t2, t3, t_pending])
    db_session.flush()

    sub = Task(project_id=project.id, title="Alt İş", status=TaskStatus.TODO, parent_id=t1.id)
    db_session.add(sub)
    db_session.commit()

    # 1. Varsayılan listeleme: sadece aktif ana görevler döner (sub ve pending hariç)
    res = client.get(f"/api/v1/projects/{project.id}/tasks", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    titles = [item["title"] for item in data["items"]]
    assert "Onay Bekleyen İş" not in titles
    assert "Alt İş" not in titles

    # 2. search filtresi
    res_search = client.get(f"/api/v1/projects/{project.id}/tasks?search=Backend", headers=headers)
    assert res_search.json()["total"] == 1
    assert res_search.json()["items"][0]["title"] == "Backend API"

    # 3. status filtresi
    res_status = client.get(f"/api/v1/projects/{project.id}/tasks?status=TODO,DONE", headers=headers)
    assert res_status.json()["total"] == 2

    # 4. assignee_id filtresi
    res_assignee = client.get(f"/api/v1/projects/{project.id}/tasks?assignee_id={member_data['id']}", headers=headers)
    assert res_assignee.json()["total"] == 1
    assert res_assignee.json()["items"][0]["title"] == "DevOps Setup"

    # 5. parent_id filtresi (alt görevleri getirme)
    res_sub = client.get(f"/api/v1/projects/{project.id}/tasks?parent_id={t1.id}", headers=headers)
    assert res_sub.json()["total"] == 1
    assert res_sub.json()["items"][0]["title"] == "Alt İş"

    # 6. include_pending=true
    res_pending = client.get(f"/api/v1/projects/{project.id}/tasks?include_pending=true", headers=headers)
    assert res_pending.json()["total"] == 4

    # 7. Sayfalama
    res_page = client.get(f"/api/v1/projects/{project.id}/tasks?limit=2&page=1", headers=headers)
    assert len(res_page.json()["items"]) == 2
    assert res_page.json()["page"] == 1
    assert res_page.json()["limit"] == 2


def test_list_tasks_non_member_forbidden(client: TestClient, db_session: Session):
    owner_data = create_user(client, "Owner US11-9", "owner_us11_9@luno.com")
    promote_to_admin(db_session, owner_data["id"])
    project = create_project(db_session, owner_data["id"])

    outsider = create_user(client, "Dış US11-9", "outsider_us11_9@luno.com")
    token = get_token(client, "outsider_us11_9@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/projects/{project.id}/tasks", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_get_task_detail(client: TestClient, db_session: Session):
    """Sözleşme 6.3: Görev detayı."""
    admin_data = create_user(client, "Admin US11-10", "admin_us11_10@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    task = Task(project_id=project.id, title="Detay Görevi", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    # Üye erişebilir
    headers = {"Authorization": f"Bearer {get_token(client, 'admin_us11_10@luno.com')}"}
    res = client.get(f"/api/v1/tasks/{task.id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Detay Görevi"

    # Olmayan görev 404
    res_404 = client.get("/api/v1/tasks/99999", headers=headers)
    assert res_404.status_code == 404
    assert res_404.json()["error"]["code"] == "TASK_NOT_FOUND"

    # Üye olmayan 403
    outsider = create_user(client, "Dış US11-10", "outsider_us11_10@luno.com")
    out_headers = {"Authorization": f"Bearer {get_token(client, 'outsider_us11_10@luno.com')}"}
    res_403 = client.get(f"/api/v1/tasks/{task.id}", headers=out_headers)
    assert res_403.status_code == 403
    assert res_403.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


# ============================================================================
# US-012 (Issue #152) - Görev atama API'si Testleri
# ============================================================================

def test_admin_assigns_task_to_member_successfully(client: TestClient, db_session: Session):
    """FR-030: Yönetici görevi proje üyesine atayabilir."""
    admin_data = create_user(client, "Admin US12-1", "admin_us12_1@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US12-1", "member_us12_1@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    task = Task(project_id=project.id, title="Atama Görevi", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_us12_1@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {"assignee_id": member_data["id"], "confirm_over_capacity": False}
    res = client.patch(f"/api/v1/tasks/{task.id}/assignee", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["assignee"]["id"] == member_data["id"]

    db_session.refresh(task)
    assert task.assignee_id == member_data["id"]


def test_admin_unassigns_task_successfully(client: TestClient, db_session: Session):
    """Sözleşme 6.6: assignee_id: null gönderilerek görev ataması kaldırılabilir."""
    admin_data = create_user(client, "Admin US12-2", "admin_us12_2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US12-2", "member_us12_2@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    task = Task(project_id=project.id, title="Atanmış Görev", status=TaskStatus.TODO, assignee_id=member_data["id"])
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_us12_2@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}/assignee", json={"assignee_id": None}, headers=headers)
    assert res.status_code == 200
    assert res.json()["assignee"] is None

    db_session.refresh(task)
    assert task.assignee_id is None


def test_assignee_not_member_returns_400(client: TestClient, db_session: Session):
    """Sözleşme 6.6: Atanan kişi projenin üyesi değilse 400 ASSIGNEE_NOT_MEMBER."""
    admin_data = create_user(client, "Admin US12-3", "admin_us12_3@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    outsider = create_user(client, "Dış Kişi US12", "disari_us12@luno.com")

    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_us12_3@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}/assignee", json={"assignee_id": outsider["id"]}, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "ASSIGNEE_NOT_MEMBER"


def test_member_cannot_assign_task_forbidden(client: TestClient, db_session: Session):
    """FR-012: Ekip üyesi görev atayamaz (403 FORBIDDEN)."""
    admin_data = create_user(client, "Admin US12-4", "admin_us12_4@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US12-4", "member_us12_4@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "member_us12_4@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}/assignee", json={"assignee_id": member_data["id"]}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_non_member_cannot_assign_task(client: TestClient, db_session: Session):
    """FR-013: Proje üyesi olmayan yönetici 403 PROJECT_ACCESS_DENIED alır."""
    owner_data = create_user(client, "Owner US12-5", "owner_us12_5@luno.com")
    promote_to_admin(db_session, owner_data["id"])
    project = create_project(db_session, owner_data["id"])

    other_admin = create_user(client, "Other Admin US12-5", "other_admin_us12_5@luno.com")
    promote_to_admin(db_session, other_admin["id"])

    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "other_admin_us12_5@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}/assignee", json={"assignee_id": owner_data["id"]}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_assign_task_not_found(client: TestClient, db_session: Session):
    admin_data = create_user(client, "Admin US12-6", "admin_us12_6@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    token = get_token(client, "admin_us12_6@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch("/api/v1/tasks/99999/assignee", json={"assignee_id": admin_data["id"]}, headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "TASK_NOT_FOUND"


# ============================================================================
# US-013 (Issue #155) - Görev düzenleme ve silme API'si Testleri
# ============================================================================

def test_admin_updates_task_fields_successfully(client: TestClient, db_session: Session):
    """FR-031: Yönetici görev bilgilerini düzenleyebilir."""
    admin_data = create_user(client, "Admin US13-1", "admin_us13_1@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    task = Task(
        project_id=project.id,
        title="Eski Başlık",
        description="Eski Açıklama",
        status=TaskStatus.TODO,
        priority=Priority.DUSUK,
        story_points=1,
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_us13_1@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "title": "Yeni Başlık",
        "description": "Yeni Açıklama",
        "priority": "YUKSEK",
        "story_points": 8,
        "start_date": "2026-10-15",
        "due_date": "2026-10-25",
    }
    res = client.patch(f"/api/v1/tasks/{task.id}", json=payload, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Yeni Başlık"
    assert data["description"] == "Yeni Açıklama"
    assert data["priority"] == "YUKSEK"
    assert data["story_points"] == 8
    assert data["start_date"] == "2026-10-15"
    assert data["due_date"] == "2026-10-25"


def test_update_task_invalid_date_range(client: TestClient, db_session: Session):
    """FR-025: Teslim tarihi başlangıç tarihinden önce olamaz (400 INVALID_DATE_RANGE)."""
    admin_data = create_user(client, "Admin US13-2", "admin_us13_2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO, start_date=date(2026, 10, 15))
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_us13_2@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}", json={"due_date": "2026-10-10"}, headers=headers)
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "INVALID_DATE_RANGE"


def test_update_task_foreign_label_422(client: TestClient, db_session: Session):
    """FR-037: Başka projeye ait etiket 422 VALIDATION_ERROR döndürür."""
    from app.models.label import Label
    admin_data = create_user(client, "Admin US13-3", "admin_us13_3@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])
    other_project = create_project(db_session, admin_data["id"])

    foreign_label = Label(project_id=other_project.id, name="backend", color="#123456")
    db_session.add(foreign_label)
    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(foreign_label)
    db_session.refresh(task)

    token = get_token(client, "admin_us13_3@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}", json={"label_ids": [foreign_label.id]}, headers=headers)
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


def test_member_cannot_update_task_forbidden(client: TestClient, db_session: Session):
    """FR-012: Ekip üyesi görevi düzenleyemez (403 FORBIDDEN)."""
    admin_data = create_user(client, "Admin US13-4", "admin_us13_4@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US13-4", "member_us13_4@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    task = Task(project_id=project.id, title="Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "member_us13_4@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.patch(f"/api/v1/tasks/{task.id}", json={"title": "Hacker Başlık"}, headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_admin_deletes_task_and_cascades_subtasks(client: TestClient, db_session: Session):
    """FR-032: Yönetici görevi silebilir; alt görevler de birlikte silinir (204)."""
    admin_data = create_user(client, "Admin US13-5", "admin_us13_5@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    parent_task = Task(project_id=project.id, title="Ana Görev Silinecek", status=TaskStatus.TODO)
    db_session.add(parent_task)
    db_session.flush()

    sub1 = Task(project_id=project.id, title="Alt Görev 1", status=TaskStatus.TODO, parent_id=parent_task.id)
    sub2 = Task(project_id=project.id, title="Alt Görev 2", status=TaskStatus.IN_PROGRESS, parent_id=parent_task.id)
    db_session.add_all([sub1, sub2])
    db_session.commit()

    token = get_token(client, "admin_us13_5@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.delete(f"/api/v1/tasks/{parent_task.id}", headers=headers)
    assert res.status_code == 204

    # Ana ve alt görevler silinmiş olmalı
    assert db_session.query(Task).filter(Task.id == parent_task.id).first() is None
    assert db_session.query(Task).filter(Task.id.in_([sub1.id, sub2.id])).count() == 0


def test_member_cannot_delete_task_forbidden(client: TestClient, db_session: Session):
    """FR-012: Ekip üyesi görevi silemez (403 FORBIDDEN)."""
    admin_data = create_user(client, "Admin US13-6", "admin_us13_6@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    member_data = create_user(client, "Uye US13-6", "member_us13_6@luno.com")
    add_member_to_project(db_session, project.id, member_data["id"])

    task = Task(project_id=project.id, title="Silinemez Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "member_us13_6@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.delete(f"/api/v1/tasks/{task.id}", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


# ============================================================================
# US-015 (Issue #161) - Kanban panosu API'si Testleri
# ============================================================================

def test_get_kanban_board_all_four_columns(client: TestClient, db_session: Session):
    """FR-042: Kanban panosu TODO, IN_PROGRESS, REVIEW_TESTING ve DONE sütunlarını döner."""
    admin_data = create_user(client, "Admin US15-1", "admin_us15_1@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    t_todo = Task(project_id=project.id, title="Pano TODO", status=TaskStatus.TODO)
    t_prog = Task(project_id=project.id, title="Pano Prog", status=TaskStatus.IN_PROGRESS)
    t_rev = Task(project_id=project.id, title="Pano Rev", status=TaskStatus.REVIEW_TESTING)
    t_done = Task(project_id=project.id, title="Pano Done", status=TaskStatus.DONE)
    db_session.add_all([t_todo, t_prog, t_rev, t_done])
    db_session.commit()

    token = get_token(client, "admin_us15_1@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/projects/{project.id}/board", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "columns" in data
    assert len(data["columns"]) == 4

    column_statuses = [col["status"] for col in data["columns"]]
    assert column_statuses == ["TODO", "IN_PROGRESS", "REVIEW_TESTING", "DONE"]

    # Her sütundaki görev sayısı 1 olmalı
    assert len(data["columns"][0]["tasks"]) == 1
    assert data["columns"][0]["tasks"][0]["title"] == "Pano TODO"
    assert len(data["columns"][1]["tasks"]) == 1
    assert data["columns"][1]["tasks"][0]["title"] == "Pano Prog"
    assert len(data["columns"][2]["tasks"]) == 1
    assert data["columns"][2]["tasks"][0]["title"] == "Pano Rev"
    assert len(data["columns"][3]["tasks"]) == 1
    assert data["columns"][3]["tasks"][0]["title"] == "Pano Done"


def test_kanban_board_excludes_subtasks_and_pending(client: TestClient, db_session: Session):
    """FR-042: Alt görevler ve onay bekleyen / reddedilen görevler panoda yer almaz."""
    admin_data = create_user(client, "Admin US15-2", "admin_us15_2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    main_task = Task(project_id=project.id, title="Ana Pano Görevi", status=TaskStatus.TODO)
    db_session.add(main_task)
    db_session.flush()

    sub = Task(project_id=project.id, title="Alt Görev Pano", status=TaskStatus.TODO, parent_id=main_task.id)
    pending = Task(project_id=project.id, title="Onay Bekleyen Pano", status=TaskStatus.ONAY_BEKLIYOR)
    rejected = Task(project_id=project.id, title="Reddedilen Pano", status=TaskStatus.REDDEDILDI)
    db_session.add_all([sub, pending, rejected])
    db_session.commit()

    token = get_token(client, "admin_us15_2@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/projects/{project.id}/board", headers=headers)
    assert res.status_code == 200
    todo_tasks = res.json()["columns"][0]["tasks"]
    assert len(todo_tasks) == 1
    assert todo_tasks[0]["title"] == "Ana Pano Görevi"


def test_kanban_board_sprint_filter(client: TestClient, db_session: Session):
    """Sözleşme 7.1: sprint_id filtresi ile panoda sadece o sprint'e ait görevler döner."""
    admin_data = create_user(client, "Admin US15-3", "admin_us15_3@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    t_sprint1 = Task(project_id=project.id, title="Sprint 1 İşi", status=TaskStatus.TODO, sprint_id=1)
    t_sprint2 = Task(project_id=project.id, title="Sprint 2 İşi", status=TaskStatus.TODO, sprint_id=2)
    db_session.add_all([t_sprint1, t_sprint2])
    db_session.commit()

    token = get_token(client, "admin_us15_3@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/projects/{project.id}/board?sprint_id=1", headers=headers)
    assert res.status_code == 200
    todo_tasks = res.json()["columns"][0]["tasks"]
    assert len(todo_tasks) == 1
    assert todo_tasks[0]["title"] == "Sprint 1 İşi"


def test_kanban_board_non_member_access_denied(client: TestClient, db_session: Session):
    """FR-013: Proje üyesi olmayan kullanıcı panoya erişemez (403 PROJECT_ACCESS_DENIED)."""
    admin_data = create_user(client, "Admin US15-4", "admin_us15_4@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    outsider = create_user(client, "Dış Kişi US15", "outsider_us15@luno.com")
    token = get_token(client, "outsider_us15@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get(f"/api/v1/projects/{project.id}/board", headers=headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_kanban_board_project_not_found(client: TestClient, db_session: Session):
    admin_data = create_user(client, "Admin US15-5", "admin_us15_5@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    token = get_token(client, "admin_us15_5@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/projects/99999/board", headers=headers)
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "PROJECT_NOT_FOUND"


# ============================================================================
# US-032 (Issue #164) - Öncelik ve efor puanı Testleri
# ============================================================================

def test_priority_and_story_points_on_create(client: TestClient, db_session: Session):
    """FR-035, FR-036: Görev oluştururken priority ve story_points kabul edilir."""
    admin_data = create_user(client, "Admin US32-1", "admin_us32_1@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    token = get_token(client, "admin_us32_1@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    for sp in [1, 2, 3, 5, 8, 13]:
        res = client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": f"Görev SP {sp}", "story_points": sp, "priority": "ORTA"},
            headers=headers,
        )
        assert res.status_code == 201
        assert res.json()["story_points"] == sp
        assert res.json()["priority"] == "ORTA"

    for prio in ["DUSUK", "ORTA", "YUKSEK"]:
        res = client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": f"Görev Prio {prio}", "priority": prio},
            headers=headers,
        )
        assert res.status_code == 201
        assert res.json()["priority"] == prio


def test_invalid_story_points_on_create_rejected(client: TestClient, db_session: Session):
    """FR-036: Fibonacci (1, 2, 3, 5, 8, 13) dışındaki efor puanları 422 ve Türkçe mesajla reddedilir."""
    admin_data = create_user(client, "Admin US32-2", "admin_us32_2@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    token = get_token(client, "admin_us32_2@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    for invalid_sp in [0, 4, 6, 7, 10, 21, -3]:
        res = client.post(
            f"/api/v1/projects/{project.id}/tasks",
            json={"title": "Geçersiz SP", "story_points": invalid_sp},
            headers=headers,
        )
        assert res.status_code == 422
        data = res.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "story_points" in data["error"]["fields"]
        assert "Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır." in data["error"]["fields"]["story_points"]


def test_priority_and_story_points_on_update(client: TestClient, db_session: Session):
    """FR-035, FR-036: Görev düzenlerken priority ve story_points güncellenebilir."""
    admin_data = create_user(client, "Admin US32-3", "admin_us32_3@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    task = Task(project_id=project.id, title="Düzenlenecek Görev", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_us32_3@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Geçerli güncelleme
    res = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"priority": "YUKSEK", "story_points": 13},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["priority"] == "YUKSEK"
    assert res.json()["story_points"] == 13

    # Geçersiz story_points güncellemesi 422
    res_invalid_sp = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"story_points": 9},
        headers=headers,
    )
    assert res_invalid_sp.status_code == 422
    assert res_invalid_sp.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "Efor puanı 1, 2, 3, 5, 8 veya 13 olmalıdır." in res_invalid_sp.json()["error"]["fields"]["story_points"]

    # Geçersiz priority güncellemesi 422
    res_invalid_prio = client.patch(
        f"/api/v1/tasks/{task.id}",
        json={"priority": "KRITIK"},
        headers=headers,
    )
    assert res_invalid_prio.status_code == 422
    assert res_invalid_prio.json()["error"]["code"] == "VALIDATION_ERROR"


# ============================================================================
# HATA #186 - Görev düzenlemede title null gönderildiğinde doğrulama
# ============================================================================

def test_update_task_null_or_blank_title_rejected(client: TestClient, db_session: Session):
    """HATA #186: PATCH /tasks/{id} title null veya boş gönderilirse 422 VALIDATION_ERROR dönmeli."""
    admin_data = create_user(client, "Admin BUG186", "admin_bug186@luno.com")
    promote_to_admin(db_session, admin_data["id"])
    project = create_project(db_session, admin_data["id"])

    task = Task(project_id=project.id, title="Orijinal Başlık", status=TaskStatus.TODO)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    token = get_token(client, "admin_bug186@luno.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. title: null gönderildiğinde 500 değil, 422 dönmeli
    res_null = client.patch(f"/api/v1/tasks/{task.id}", json={"title": None}, headers=headers)
    assert res_null.status_code == 422
    data_null = res_null.json()
    assert data_null["error"]["code"] == "VALIDATION_ERROR"
    assert data_null["error"]["message"] == "Lütfen hatalı alanları düzeltin."
    assert data_null["error"]["fields"]["title"] == "Görev başlığı zorunludur."

    # 2. title: "   " gönderildiğinde 422 dönmeli
    res_blank = client.patch(f"/api/v1/tasks/{task.id}", json={"title": "   "}, headers=headers)
    assert res_blank.status_code == 422
    assert res_blank.json()["error"]["code"] == "VALIDATION_ERROR"
    assert res_blank.json()["error"]["fields"]["title"] == "Görev başlığı zorunludur."

    # 3. Veritabanındaki başlık değişmemiş olmalı
    db_session.refresh(task)
    assert task.title == "Orijinal Başlık"
