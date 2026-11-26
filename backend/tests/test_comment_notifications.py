"""Yorum bildirimi testleri (US-037, FR-054, sözleşme 8.5 & 9, #294)."""

from datetime import date, datetime, timezone

from app.core.security import create_access_token, get_password_hash
from app.models.enums import NotificationType, TaskStatus
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User


def _create_user(db, email: str, full_name: str, role: SystemRole = SystemRole.EKIP_UYESI) -> tuple[User, dict]:
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


def _setup_task(db):
    admin, admin_headers = _create_user(db, "admin@cmt.test", "Sena Yönetici", SystemRole.YONETICI)
    assignee, assignee_headers = _create_user(db, "assignee@cmt.test", "Ayşe Yılmaz")
    other, other_headers = _create_user(db, "other@cmt.test", "Can Demir")

    now = datetime.now(timezone.utc)
    project = Project(
        name="Bildirim Test Projesi",
        description="Test",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    db.flush()
    for u in (admin, assignee, other):
        db.add(ProjectMember(project_id=project.id, user_id=u.id, joined_at=now))

    task = Task(
        project_id=project.id,
        title="Giriş ekranı",
        status=TaskStatus.IN_PROGRESS,
        assignee_id=assignee.id,
        created_by_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return (admin, admin_headers), (assignee, assignee_headers), (other, other_headers), project, task


def test_comment_notifies_assignee_and_not_author(client, db_session):
    (admin, admin_headers), (assignee, assignee_headers), _, project, task = _setup_task(db_session)

    resp = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"body": "API hazır, ekranı bağlayabilirsin."},
        headers=admin_headers,
    )
    assert resp.status_code == 201

    # Atanan kişi COMMENT_ADDED bildirimi alır
    notif_resp = client.get("/api/v1/notifications", headers=assignee_headers)
    assert notif_resp.status_code == 200
    items = notif_resp.json()["items"]
    assert len(items) == 1
    assert items[0]["type"] == NotificationType.COMMENT_ADDED.value
    assert items[0]["project_id"] == project.id
    assert items[0]["task_id"] == task.id
    assert items[0]["is_read"] is False
    assert "Giriş ekranı" in items[0]["message"]

    # Yorumu yazan (admin) kendi yorumundan bildirim almaz
    admin_notifs = db_session.query(Notification).filter(Notification.user_id == admin.id).all()
    assert len(admin_notifs) == 0


def test_assignee_own_comment_does_not_notify_self(client, db_session):
    _, (assignee, assignee_headers), _, _, task = _setup_task(db_session)

    resp = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"body": "Kendi görevime not düşüyorum."},
        headers=assignee_headers,
    )
    assert resp.status_code == 201

    assignee_notifs = db_session.query(Notification).filter(Notification.user_id == assignee.id).all()
    assert len(assignee_notifs) == 0


def test_comment_also_notifies_previous_commenters_without_duplicates(client, db_session):
    (admin, admin_headers), (assignee, _), (other, other_headers), _, task = _setup_task(db_session)

    # 1. Yorum: admin yazar -> assignee bildirim alır
    client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"body": "İlk yorum"},
        headers=admin_headers,
    )

    # 2. Yorum: other yazar -> hem assignee hem önceki yorumcu admin bildirim alır, other almaz
    resp = client.post(
        f"/api/v1/tasks/{task.id}/comments",
        json={"body": "İkinci yorum"},
        headers=other_headers,
    )
    assert resp.status_code == 201

    admin_notifs = db_session.query(Notification).filter(Notification.user_id == admin.id).all()
    assignee_notifs = db_session.query(Notification).filter(Notification.user_id == assignee.id).all()
    other_notifs = db_session.query(Notification).filter(Notification.user_id == other.id).all()

    assert len(admin_notifs) == 1
    assert admin_notifs[0].type == NotificationType.COMMENT_ADDED
    assert len(assignee_notifs) == 2
    assert len(other_notifs) == 0
