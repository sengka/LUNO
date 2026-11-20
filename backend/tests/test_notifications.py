"""US-021 (#233) Bildirim API'si testleri (sözleşme 9.1 – 9.3)."""

from datetime import date, datetime, timezone

from app.core.security import create_access_token, get_password_hash
from app.models.enums import NotificationType
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import SystemRole, User


def _make_user(db, email: str, role: str = SystemRole.EKIP_UYESI.value, full_name: str = "Kullanıcı"):
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=get_password_hash("Guclu1234"),
        role=role,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _auth_headers(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def _make_project_with_members(db, admin: User, members: list[User]) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(
        name="Bildirim Projesi",
        description="Test",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=admin.id, joined_at=now))
    for m in members:
        db.add(ProjectMember(project_id=project.id, user_id=m.id, joined_at=now))
    db.commit()
    db.refresh(project)
    return project


def test_list_notifications_pagination_and_unread_only(client, db_session):
    user = _make_user(db_session, "ayse@ornek.com", full_name="Ayşe Yılmaz")
    other = _make_user(db_session, "can@ornek.com", full_name="Can Demir")
    now = datetime.now(timezone.utc)

    for i in range(3):
        db_session.add(
            Notification(
                user_id=user.id,
                type=NotificationType.TASK_ASSIGNED,
                message=f"Bildirim {i + 1}",
                is_read=(i == 0),
                created_at=now,
            )
        )
    db_session.add(
        Notification(
            user_id=other.id,
            type=NotificationType.TASK_ASSIGNED,
            message="Başkasının bildirimi",
            is_read=False,
            created_at=now,
        )
    )
    db_session.commit()

    # Tümü (sayfalama ile)
    res = client.get("/api/v1/notifications?page=1&limit=2", headers=_auth_headers(user))
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3
    assert data["unread_count"] == 2
    assert data["page"] == 1
    assert data["limit"] == 2
    assert len(data["items"]) == 2
    # Yeniden eskiye sıralı (en son eklenen 3. bildirim ilk sırada)
    assert data["items"][0]["message"] == "Bildirim 3"

    # unread_only=true
    res_unread = client.get("/api/v1/notifications?unread_only=true", headers=_auth_headers(user))
    assert res_unread.status_code == 200
    u_data = res_unread.json()
    assert u_data["total"] == 2
    assert u_data["unread_count"] == 2
    assert all(not item["is_read"] for item in u_data["items"])


def test_mark_single_and_all_read_and_forbid_other_user(client, db_session):
    user = _make_user(db_session, "ayse@ornek.com")
    other = _make_user(db_session, "can@ornek.com")
    now = datetime.now(timezone.utc)

    n1 = Notification(user_id=user.id, type=NotificationType.TASK_ASSIGNED, message="N1", is_read=False, created_at=now)
    n2 = Notification(user_id=user.id, type=NotificationType.TASK_ASSIGNED, message="N2", is_read=False, created_at=now)
    n_other = Notification(user_id=other.id, type=NotificationType.TASK_ASSIGNED, message="Other", is_read=False, created_at=now)
    db_session.add_all([n1, n2, n_other])
    db_session.commit()

    # Başkasının bildirimini okundu işaretleme -> 403 FORBIDDEN
    forbid = client.patch(f"/api/v1/notifications/{n_other.id}/read", headers=_auth_headers(user))
    assert forbid.status_code == 403
    assert forbid.json()["error"]["code"] == "FORBIDDEN"

    # Olmayan bildirim -> 404 NOTIFICATION_NOT_FOUND
    not_found = client.patch("/api/v1/notifications/99999/read", headers=_auth_headers(user))
    assert not_found.status_code == 404
    assert not_found.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

    # Kendi bildirimini okundu işaretle -> 200
    ok = client.patch(f"/api/v1/notifications/{n1.id}/read", headers=_auth_headers(user))
    assert ok.status_code == 200
    assert ok.json()["is_read"] is True

    # Tümünü okundu işaretle -> 204
    read_all = client.post("/api/v1/notifications/read-all", headers=_auth_headers(user))
    assert read_all.status_code == 204

    # user'ın okunmamışı 0, other'ın okunmamışı hâlâ 1
    assert client.get("/api/v1/notifications", headers=_auth_headers(user)).json()["unread_count"] == 0
    assert client.get("/api/v1/notifications", headers=_auth_headers(other)).json()["unread_count"] == 1


def test_task_assigned_and_pending_approval_notifications(client, db_session):
    admin = _make_user(db_session, "sena@ornek.com", role=SystemRole.YONETICI.value, full_name="Sena Gül Kara")
    member = _make_user(db_session, "ayse@ornek.com", role=SystemRole.EKIP_UYESI.value, full_name="Ayşe Yılmaz")
    project = _make_project_with_members(db_session, admin, [member])

    # 1. Yönetici görev oluştururken atama yapınca TASK_ASSIGNED bildirimi gider
    create_res = client.post(
        f"/api/v1/projects/{project.id}/tasks",
        json={"title": "Giriş ekranı", "assignee_id": member.id},
        headers=_auth_headers(admin),
    )
    assert create_res.status_code == 201
    task_id = create_res.json()["id"]

    member_notifs = client.get("/api/v1/notifications", headers=_auth_headers(member)).json()
    assert member_notifs["unread_count"] == 1
    assert member_notifs["items"][0]["type"] == "TASK_ASSIGNED"
    assert member_notifs["items"][0]["task_id"] == task_id
    assert member_notifs["items"][0]["project_id"] == project.id

    # 2. Atama kaldırılıp tekrar atanınca yeni TASK_ASSIGNED bildirimi gider
    client.patch(f"/api/v1/tasks/{task_id}/assignee", json={"assignee_id": None}, headers=_auth_headers(admin))
    client.patch(f"/api/v1/tasks/{task_id}/assignee", json={"assignee_id": member.id}, headers=_auth_headers(admin))
    member_notifs2 = client.get("/api/v1/notifications", headers=_auth_headers(member)).json()
    assert member_notifs2["unread_count"] == 2

    # 3. Ekip üyesi alt görev önerince yöneticiye TASK_PENDING_APPROVAL bildirimi gider
    sub_res = client.post(
        f"/api/v1/tasks/{task_id}/subtasks",
        json={"title": "Şifre alanı doğrulama"},
        headers=_auth_headers(member),
    )
    assert sub_res.status_code == 201
    subtask_id = sub_res.json()["id"]

    admin_notifs = client.get("/api/v1/notifications", headers=_auth_headers(admin)).json()
    assert admin_notifs["unread_count"] == 1
    assert admin_notifs["items"][0]["type"] == "TASK_PENDING_APPROVAL"
    assert admin_notifs["items"][0]["task_id"] == subtask_id
    assert admin_notifs["items"][0]["project_id"] == project.id
