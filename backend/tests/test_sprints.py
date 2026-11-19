"""Sprint ve bildirim modelleri (#248) ve sprint ilerlemesi API'si (#245, US-041, sözleşme 11.2)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Notification,
    NotificationType,
    Project,
    ProjectMember,
    Sprint,
    Task,
    TaskStatus,
    User,
)
from app.services.sprints import build_sprint_response, progress_percent, today_utc


def make_user(db: Session, email: str, role: str = "EKIP_UYESI") -> tuple[User, dict]:
    user = User(full_name=email.split("@")[0].title(), email=email, hashed_password="x", role=role)
    db.add(user)
    db.flush()
    token = create_access_token({"sub": str(user.id)})
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def case(db_session: Session):
    db = db_session
    admin, admin_h = make_user(db, "yonetici@ornek.com", "YONETICI")
    member, member_h = make_user(db, "uye@ornek.com")
    outsider, outsider_h = make_user(db, "disari@ornek.com")
    project = Project(
        name="Sprint Projesi", start_date=date(2026, 11, 1), end_date=date(2026, 12, 31),
        created_by_id=admin.id,
    )
    other = Project(
        name="Diğer Proje", start_date=date(2026, 11, 1), end_date=date(2026, 12, 31),
        created_by_id=admin.id,
    )
    db.add_all([project, other])
    db.flush()
    for user in (admin, member):
        db.add(ProjectMember(project_id=project.id, user_id=user.id))
    db.add(ProjectMember(project_id=other.id, user_id=admin.id))
    today = today_utc()
    sprint = Sprint(
        project_id=project.id, name="Sprint 6", goal="Bildirimler çalışsın",
        start_date=today - timedelta(days=2), end_date=today + timedelta(days=4),
        capacity_points=40,
    )
    other_sprint = Sprint(
        project_id=other.id, name="Başka sprint",
        start_date=today, end_date=today + timedelta(days=6),
    )
    db.add_all([sprint, other_sprint])
    db.commit()
    return {
        "db": db, "project": project, "other": other, "sprint": sprint, "other_sprint": other_sprint,
        "admin": admin, "member": member, "outsider": outsider,
        "h": {"admin": admin_h, "member": member_h, "outsider": outsider_h},
    }


def add_task(db: Session, case: dict, status: TaskStatus, points: int | None, sprint=None, **kw) -> Task:
    sprint = case["sprint"] if sprint is None else sprint
    task = Task(
        project_id=sprint.project_id, title=f"{status.value} {points}", status=status,
        story_points=points, sprint_id=sprint.id, **kw,
    )
    db.add(task)
    db.commit()
    return task


def get_sprint(client: TestClient, case: dict, who: str = "member", sprint=None):
    sprint = case["sprint"] if sprint is None else sprint
    return client.get(f"/api/v1/sprints/{sprint.id}", headers=case["h"][who])


# --- #248 Modeller -------------------------------------------------------------------


def test_sprint_model_fields_and_task_relationship(case):
    db = case["db"]
    task = add_task(db, case, TaskStatus.TODO, 5)
    db.expire_all()
    sprint = db.get(Sprint, case["sprint"].id)
    assert sprint.name == "Sprint 6"
    assert sprint.goal == "Bildirimler çalışsın"
    assert sprint.capacity_points == 40
    assert sprint.created_at is not None and sprint.updated_at is not None
    assert [t.id for t in sprint.tasks] == [task.id]
    assert db.get(Task, task.id).sprint.id == sprint.id
    assert sprint.project.sprints[0].id == sprint.id


def test_sprint_end_before_start_rejected(case):
    db = case["db"]
    db.add(Sprint(project_id=case["project"].id, name="Ters",
                  start_date=date(2026, 11, 10), end_date=date(2026, 11, 9)))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


@pytest.mark.parametrize("capacity", [0, -5])
def test_sprint_capacity_must_be_positive(case, capacity):
    db = case["db"]
    db.add(Sprint(project_id=case["project"].id, name="Kapasite",
                  start_date=date(2026, 11, 1), end_date=date(2026, 11, 7), capacity_points=capacity))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_sprint_capacity_can_be_empty(case):
    db = case["db"]
    sprint = Sprint(project_id=case["project"].id, name="Sınırsız",
                    start_date=date(2026, 11, 1), end_date=date(2026, 11, 7), capacity_points=None)
    db.add(sprint)
    db.commit()
    assert sprint.capacity_points is None


def test_task_sprint_id_must_reference_existing_sprint(case):
    db = case["db"]
    db.add(Task(project_id=case["project"].id, title="Boşta", sprint_id=999999))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_deleting_sprint_keeps_tasks_and_clears_sprint_id(case):
    """Sözleşme 11.2: Silinen sprintteki görevlerin sprint_id'si null yapılır."""
    db = case["db"]
    task = add_task(db, case, TaskStatus.IN_PROGRESS, 3)
    task_id = task.id
    db.delete(db.get(Sprint, case["sprint"].id))
    db.commit()
    db.expire_all()
    kept = db.get(Task, task_id)
    assert kept is not None
    assert kept.sprint_id is None


def test_deleting_sprint_with_raw_sql_also_clears_sprint_id(case):
    """ON DELETE SET NULL veritabanında da tanımlı (ORM'den bağımsız)."""
    db = case["db"]
    task = add_task(db, case, TaskStatus.TODO, 3)
    task_id, sprint_id = task.id, case["sprint"].id
    db.execute(Sprint.__table__.delete().where(Sprint.id == sprint_id))
    db.commit()
    db.expire_all()
    assert db.get(Task, task_id).sprint_id is None


def test_deleting_project_deletes_sprints_and_notifications(case):
    """FR-020: Proje silinince sprintleri ve projeye ait bildirimleri de silinir."""
    db = case["db"]
    db.add(Notification(user_id=case["member"].id, type=NotificationType.TASK_ASSIGNED,
                        message="Görev atandı.", project_id=case["project"].id))
    db.commit()
    project_id = case["project"].id
    db.delete(db.get(Project, project_id))
    db.commit()
    assert db.query(Sprint).filter(Sprint.project_id == project_id).count() == 0
    assert db.query(Notification).filter(Notification.project_id == project_id).count() == 0
    assert db.query(Sprint).filter(Sprint.project_id == case["other"].id).count() == 1


def test_notification_model_fields_and_defaults(case):
    db = case["db"]
    task = add_task(db, case, TaskStatus.TODO, 2)
    note = Notification(
        user_id=case["member"].id, type=NotificationType.TASK_ASSIGNED,
        message="Yönetici size 'Giriş ekranı' görevini atadı.",
        project_id=case["project"].id, task_id=task.id,
    )
    db.add(note)
    db.commit()
    db.expire_all()
    loaded = db.get(Notification, note.id)
    assert loaded.type == NotificationType.TASK_ASSIGNED
    assert loaded.is_read is False
    assert loaded.created_at is not None
    assert loaded.user.id == case["member"].id
    assert loaded.task.id == task.id
    assert loaded.project.id == case["project"].id


def test_notification_types_match_contract():
    assert {t.value for t in NotificationType} == {
        "TASK_ASSIGNED", "COMMENT_ADDED", "DUE_DATE_SOON", "TASK_STALE",
        "TASK_PENDING_APPROVAL", "TASK_APPROVED", "TASK_REJECTED",
    }


def test_notification_rejects_unknown_type(case):
    db = case["db"]
    with pytest.raises(IntegrityError):
        db.execute(
            Notification.__table__.insert().values(
                user_id=case["member"].id, type="BILINMEYEN", message="x", is_read=False,
                created_at=date(2026, 11, 1),
            )
        )
        db.commit()
    db.rollback()


def test_notification_without_project_or_task(case):
    """Proje veya göreve bağlı olmayan bildirim de tutulabilir (ör. haftalık özet, Sprint 8)."""
    db = case["db"]
    note = Notification(user_id=case["member"].id, type=NotificationType.TASK_STALE, message="x")
    db.add(note)
    db.commit()
    assert note.project_id is None and note.task_id is None


def test_deleting_task_keeps_notification(case):
    db = case["db"]
    task = add_task(db, case, TaskStatus.TODO, 1)
    note = Notification(user_id=case["member"].id, type=NotificationType.DUE_DATE_SOON,
                        message="Teslim yaklaşıyor.", project_id=case["project"].id, task_id=task.id)
    db.add(note)
    db.commit()
    note_id = note.id
    db.delete(task)
    db.commit()
    db.expire_all()
    kept = db.get(Notification, note_id)
    assert kept is not None and kept.task_id is None


def test_deleting_user_deletes_their_notifications(case):
    db = case["db"]
    db.add(Notification(user_id=case["member"].id, type=NotificationType.TASK_ASSIGNED, message="x"))
    db.add(Notification(user_id=case["admin"].id, type=NotificationType.TASK_PENDING_APPROVAL, message="y"))
    db.commit()
    member_id = case["member"].id
    db.delete(db.get(User, member_id))
    db.commit()
    assert db.query(Notification).filter(Notification.user_id == member_id).count() == 0
    assert db.query(Notification).count() == 1


# --- Görevde sprint_id kontrolü ------------------------------------------------------------


def test_create_task_with_sprint_of_same_project(client, case):
    response = client.post(
        f"/api/v1/projects/{case['project'].id}/tasks", headers=case["h"]["admin"],
        json={"title": "Sprintli görev", "sprint_id": case["sprint"].id},
    )
    assert response.status_code == 201, response.text
    assert response.json()["sprint_id"] == case["sprint"].id


@pytest.mark.parametrize("which", ["missing", "other_project"])
def test_create_task_with_invalid_sprint_returns_422(client, case, which):
    sprint_id = 999999 if which == "missing" else case["other_sprint"].id
    before = case["db"].query(Task).count()
    response = client.post(
        f"/api/v1/projects/{case['project'].id}/tasks", headers=case["h"]["admin"],
        json={"title": "Yanlış sprint", "sprint_id": sprint_id},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert "sprint_id" in error["fields"]
    assert case["db"].query(Task).count() == before


def test_create_subtask_with_invalid_sprint_returns_422(client, case):
    parent = add_task(case["db"], case, TaskStatus.TODO, 3)
    response = client.post(
        f"/api/v1/tasks/{parent.id}/subtasks", headers=case["h"]["admin"],
        json={"title": "Alt görev", "sprint_id": case["other_sprint"].id},
    )
    assert response.status_code == 422
    assert "sprint_id" in response.json()["error"]["fields"]


def test_update_task_sprint(client, case):
    task = add_task(case["db"], case, TaskStatus.TODO, 3)
    url = f"/api/v1/tasks/{task.id}"
    bad = client.patch(url, headers=case["h"]["admin"], json={"sprint_id": case["other_sprint"].id})
    assert bad.status_code == 422
    assert "sprint_id" in bad.json()["error"]["fields"]

    cleared = client.patch(url, headers=case["h"]["admin"], json={"sprint_id": None})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["sprint_id"] is None

    again = client.patch(url, headers=case["h"]["admin"], json={"sprint_id": case["sprint"].id})
    assert again.status_code == 200
    assert again.json()["sprint_id"] == case["sprint"].id


# --- #245 Sprint ilerlemesi (GET /sprints/{id}) ---------------------------------------------


def test_get_sprint_returns_contract_fields(client, case):
    add_task(case["db"], case, TaskStatus.DONE, 5)
    add_task(case["db"], case, TaskStatus.IN_PROGRESS, 3)
    add_task(case["db"], case, TaskStatus.TODO, 2)
    add_task(case["db"], case, TaskStatus.REVIEW_TESTING, 2)
    response = get_sprint(client, case)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "id", "project_id", "name", "goal", "start_date", "end_date", "capacity_points",
        "total_points", "done_points", "progress_percent", "is_active",
    }
    assert body["id"] == case["sprint"].id
    assert body["project_id"] == case["project"].id
    assert body["name"] == "Sprint 6"
    assert body["goal"] == "Bildirimler çalışsın"
    assert body["capacity_points"] == 40
    assert body["start_date"] == case["sprint"].start_date.isoformat()
    assert body["total_points"] == 12
    assert body["done_points"] == 5
    assert body["progress_percent"] == 41.7
    assert body["is_active"] is True


def test_empty_sprint_has_zero_progress(client, case):
    body = get_sprint(client, case).json()
    assert body["total_points"] == 0
    assert body["done_points"] == 0
    assert body["progress_percent"] == 0.0


def test_unpointed_tasks_count_as_zero(client, case):
    db = case["db"]
    add_task(db, case, TaskStatus.DONE, None)
    add_task(db, case, TaskStatus.TODO, None)
    body = get_sprint(client, case).json()
    assert (body["total_points"], body["done_points"], body["progress_percent"]) == (0, 0, 0.0)

    add_task(db, case, TaskStatus.DONE, 3)
    add_task(db, case, TaskStatus.TODO, 5)
    body = get_sprint(client, case).json()
    assert (body["total_points"], body["done_points"], body["progress_percent"]) == (8, 3, 37.5)


def test_all_done_is_100_percent(client, case):
    add_task(case["db"], case, TaskStatus.DONE, 8)
    add_task(case["db"], case, TaskStatus.DONE, 5)
    assert get_sprint(client, case).json()["progress_percent"] == 100.0


def test_pending_and_rejected_tasks_are_not_counted(client, case):
    """Sözleşme 1.3: Onay bekleyen ve reddedilen görevler ilerlemeye dahil edilmez."""
    db = case["db"]
    add_task(db, case, TaskStatus.DONE, 5)
    add_task(db, case, TaskStatus.TODO, 5)
    add_task(db, case, TaskStatus.ONAY_BEKLIYOR, 13)
    add_task(db, case, TaskStatus.REDDEDILDI, 8)
    body = get_sprint(client, case).json()
    assert (body["total_points"], body["done_points"], body["progress_percent"]) == (10, 5, 50.0)


def test_tasks_of_other_sprints_and_unplanned_tasks_are_not_counted(client, case):
    db = case["db"]
    add_task(db, case, TaskStatus.DONE, 3)
    later = Sprint(project_id=case["project"].id, name="Sonraki",
                   start_date=date(2027, 1, 1), end_date=date(2027, 1, 7))
    db.add(later)
    db.commit()
    add_task(db, case, TaskStatus.TODO, 13, sprint=later)
    db.add(Task(project_id=case["project"].id, title="Plansız", status=TaskStatus.TODO, story_points=8))
    db.commit()
    body = get_sprint(client, case).json()
    assert (body["total_points"], body["done_points"]) == (3, 3)


def test_subtasks_in_sprint_count_with_their_own_points(client, case):
    db = case["db"]
    parent = add_task(db, case, TaskStatus.IN_PROGRESS, 5)
    add_task(db, case, TaskStatus.DONE, 2, parent_id=parent.id)
    body = get_sprint(client, case).json()
    assert (body["total_points"], body["done_points"]) == (7, 2)


def test_progress_updates_when_task_status_changes(client, case):
    db = case["db"]
    task = add_task(db, case, TaskStatus.REVIEW_TESTING, 5)
    add_task(db, case, TaskStatus.TODO, 5)
    assert get_sprint(client, case).json()["progress_percent"] == 0.0
    task.status = TaskStatus.DONE
    db.commit()
    assert get_sprint(client, case).json()["progress_percent"] == 50.0


@pytest.mark.parametrize(
    "start_offset,end_offset,expected",
    [(-3, -1, False), (-3, 0, True), (0, 3, True), (1, 5, False)],
)
def test_is_active_depends_on_today(client, case, start_offset, end_offset, expected):
    db = case["db"]
    today = today_utc()
    sprint = case["sprint"]
    sprint.start_date = today + timedelta(days=start_offset)
    sprint.end_date = today + timedelta(days=end_offset)
    db.commit()
    assert get_sprint(client, case).json()["is_active"] is expected


def test_capacity_null_is_returned_as_null(client, case):
    case["sprint"].capacity_points = None
    case["db"].commit()
    assert get_sprint(client, case).json()["capacity_points"] is None


def test_admin_member_can_read_sprint(client, case):
    assert get_sprint(client, case, "admin").status_code == 200


def test_non_member_gets_403(client, case):
    response = get_sprint(client, case, "outsider")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_admin_of_other_project_only_gets_403(client, case, db_session):
    """Sistem rolü YONETICI olsa da projenin üyesi değilse erişemez (sözleşme 1.2)."""
    _, headers = make_user(db_session, "baska-yonetici@ornek.com", "YONETICI")
    db_session.commit()
    response = client.get(f"/api/v1/sprints/{case['sprint'].id}", headers=headers)
    assert response.status_code == 403


def test_missing_sprint_gets_404(client, case):
    response = client.get("/api/v1/sprints/999999", headers=case["h"]["member"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SPRINT_NOT_FOUND"


def test_requires_login(client, case):
    response = client.get(f"/api/v1/sprints/{case['sprint'].id}")
    assert response.status_code == 401


@pytest.mark.parametrize(
    "done,total,expected", [(0, 0, 0.0), (5, 12, 41.7), (1, 3, 33.3), (2, 3, 66.7), (13, 13, 100.0)]
)
def test_progress_percent_rounding(done, total, expected):
    assert progress_percent(done, total) == expected


def test_build_sprint_response_uses_given_day(case):
    sprint = case["sprint"]
    after = sprint.end_date + timedelta(days=1)
    assert build_sprint_response(case["db"], sprint, today=after).is_active is False
    assert build_sprint_response(case["db"], sprint, today=sprint.start_date).is_active is True
