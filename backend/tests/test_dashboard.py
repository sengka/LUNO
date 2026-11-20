"""Dashboard API'si testleri (#236, US-022, FR-060, FR-061, sözleşme 10.1)."""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import (
    Notification,
    NotificationType,
    Project,
    ProjectMember,
    Task,
    TaskStatus,
    User,
)
from app.services.sprints import today_utc

URL = "/api/v1/dashboard"
TODAY = today_utc()


def make_user(db: Session, email: str, role: str = "EKIP_UYESI"):
    user = User(full_name=email.split("@")[0].title(), email=email, hashed_password="x", role=role)
    db.add(user)
    db.flush()
    return user, {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


def make_project(db: Session, name: str, *members: User) -> Project:
    project = Project(name=name, start_date=date(2026, 11, 1), end_date=date(2026, 12, 31))
    db.add(project)
    db.flush()
    for user in members:
        db.add(ProjectMember(project_id=project.id, user_id=user.id))
    db.flush()
    return project


def add_task(db: Session, project: Project, status=TaskStatus.TODO, assignee=None, due=None,
             parent=None, title=None) -> Task:
    task = Task(
        project_id=project.id, title=title or f"{status.value} görevi", status=status,
        assignee_id=assignee.id if assignee else None, due_date=due,
        parent_id=parent.id if parent else None,
    )
    db.add(task)
    db.flush()
    return task


@pytest.fixture
def case(db_session: Session):
    db = db_session
    me, me_h = make_user(db, "ben@ornek.com")
    other, other_h = make_user(db, "baskasi@ornek.com")
    admin, admin_h = make_user(db, "yonetici@ornek.com", "YONETICI")
    web = make_project(db, "Web Sitesi", me, other, admin)
    mobile = make_project(db, "Mobil Uygulama", me, admin)
    foreign = make_project(db, "Üye Olmadığım Proje", other)
    db.commit()
    return {"db": db, "me": me, "other": other, "admin": admin, "web": web, "mobile": mobile,
            "foreign": foreign, "h": {"me": me_h, "other": other_h, "admin": admin_h}}


def dashboard(client: TestClient, case: dict, who: str = "me") -> dict:
    response = client.get(URL, headers=case["h"][who])
    assert response.status_code == 200, response.text
    return response.json()


# --- Yanıt yapısı ve boş veri -----------------------------------------------------------


def test_requires_login(client):
    response = client.get(URL)
    assert response.status_code == 401


def test_response_has_contract_shape(client, case):
    body = dashboard(client, case)
    assert set(body) == {"projects", "my_task_counts", "upcoming_tasks", "unread_notification_count"}
    assert set(body["projects"][0]) == {"id", "name", "progress_percent", "my_open_tasks"}


def test_empty_user_without_projects(client, db_session):
    _, headers = make_user(db_session, "yeni@ornek.com")
    db_session.commit()
    response = client.get(URL, headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "projects": [],
        "my_task_counts": {"TODO": 0, "IN_PROGRESS": 0, "REVIEW_TESTING": 0, "DONE": 0},
        "upcoming_tasks": [],
        "unread_notification_count": 0,
    }


def test_projects_without_tasks(client, case):
    body = dashboard(client, case)
    assert body["projects"] == [
        {"id": case["web"].id, "name": "Web Sitesi", "progress_percent": 0.0, "my_open_tasks": 0},
        {"id": case["mobile"].id, "name": "Mobil Uygulama", "progress_percent": 0.0, "my_open_tasks": 0},
    ]
    assert body["my_task_counts"] == {"TODO": 0, "IN_PROGRESS": 0, "REVIEW_TESTING": 0, "DONE": 0}
    assert body["upcoming_tasks"] == []


# --- Projeler ve ilerleme yüzdesi -------------------------------------------------------------


def test_only_member_projects_are_listed(client, case):
    ids = [p["id"] for p in dashboard(client, case)["projects"]]
    assert ids == [case["web"].id, case["mobile"].id]
    assert case["foreign"].id not in ids


def test_progress_excludes_pending_and_rejected(client, case):
    """#236: Done görevlerin toplama oranı (onay bekleyen ve reddedilenler hariç)."""
    db, web = case["db"], case["web"]
    add_task(db, web, TaskStatus.DONE)
    add_task(db, web, TaskStatus.TODO)
    add_task(db, web, TaskStatus.IN_PROGRESS)
    add_task(db, web, TaskStatus.ONAY_BEKLIYOR)
    add_task(db, web, TaskStatus.REDDEDILDI)
    db.commit()
    project = next(p for p in dashboard(client, case)["projects"] if p["id"] == web.id)
    assert project["progress_percent"] == 33.3


def test_progress_counts_only_main_tasks(client, case):
    db, web = case["db"], case["web"]
    parent = add_task(db, web, TaskStatus.IN_PROGRESS)
    add_task(db, web, TaskStatus.DONE, parent=parent)
    add_task(db, web, TaskStatus.DONE, parent=parent)
    add_task(db, web, TaskStatus.DONE)
    db.commit()
    project = next(p for p in dashboard(client, case)["projects"] if p["id"] == web.id)
    assert project["progress_percent"] == 50.0


@pytest.mark.parametrize("statuses,expected", [
    ([TaskStatus.DONE], 100.0),
    ([TaskStatus.DONE, TaskStatus.DONE, TaskStatus.TODO], 66.7),
    ([TaskStatus.ONAY_BEKLIYOR, TaskStatus.REDDEDILDI], 0.0),
])
def test_progress_values(client, case, statuses, expected):
    db, web = case["db"], case["web"]
    for status in statuses:
        add_task(db, web, status)
    db.commit()
    project = next(p for p in dashboard(client, case)["projects"] if p["id"] == web.id)
    assert project["progress_percent"] == expected


def test_progress_matches_project_detail(client, case):
    """Dashboard ve proje sayfası aynı ilerleme yüzdesini göstermeli."""
    db, web = case["db"], case["web"]
    parent = add_task(db, web, TaskStatus.DONE)
    add_task(db, web, TaskStatus.TODO, parent=parent)
    for status in (TaskStatus.DONE, TaskStatus.REVIEW_TESTING, TaskStatus.ONAY_BEKLIYOR, TaskStatus.TODO):
        add_task(db, web, status)
    db.commit()
    detail = client.get(f"/api/v1/projects/{web.id}", headers=case["h"]["me"]).json()
    project = next(p for p in dashboard(client, case)["projects"] if p["id"] == web.id)
    assert project["progress_percent"] == detail["progress_percent"]


def test_my_open_tasks_per_project(client, case):
    db, me, other = case["db"], case["me"], case["other"]
    add_task(db, case["web"], TaskStatus.TODO, me)
    add_task(db, case["web"], TaskStatus.IN_PROGRESS, me)
    add_task(db, case["web"], TaskStatus.REVIEW_TESTING, me)
    add_task(db, case["web"], TaskStatus.DONE, me)          # bitti, açık değil
    add_task(db, case["web"], TaskStatus.ONAY_BEKLIYOR, me)  # aktif değil
    add_task(db, case["web"], TaskStatus.TODO, other)        # başkasının
    add_task(db, case["web"], TaskStatus.TODO)               # atanmamış
    add_task(db, case["mobile"], TaskStatus.TODO, me)
    db.commit()
    projects = {p["id"]: p["my_open_tasks"] for p in dashboard(client, case)["projects"]}
    assert projects == {case["web"].id: 3, case["mobile"].id: 1}


# --- Görev durum sayıları --------------------------------------------------------------------


def test_my_task_counts(client, case):
    db, me = case["db"], case["me"]
    for status in (TaskStatus.TODO, TaskStatus.TODO, TaskStatus.TODO, TaskStatus.IN_PROGRESS,
                   TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING, TaskStatus.DONE):
        add_task(db, case["web"], status, me)
    add_task(db, case["mobile"], TaskStatus.DONE, me)
    add_task(db, case["web"], TaskStatus.ONAY_BEKLIYOR, me)
    add_task(db, case["web"], TaskStatus.REDDEDILDI, me)
    add_task(db, case["web"], TaskStatus.TODO, case["other"])
    db.commit()
    assert dashboard(client, case)["my_task_counts"] == {
        "TODO": 3, "IN_PROGRESS": 2, "REVIEW_TESTING": 1, "DONE": 2,
    }


def test_counts_include_subtasks_assigned_to_me(client, case):
    db, me = case["db"], case["me"]
    parent = add_task(db, case["web"], TaskStatus.IN_PROGRESS, case["other"])
    add_task(db, case["web"], TaskStatus.TODO, me, parent=parent)
    db.commit()
    body = dashboard(client, case)
    assert body["my_task_counts"]["TODO"] == 1
    assert body["my_task_counts"]["IN_PROGRESS"] == 0


def test_other_users_dashboard_is_separate(client, case):
    db = case["db"]
    add_task(db, case["web"], TaskStatus.TODO, case["me"])
    add_task(db, case["foreign"], TaskStatus.DONE, case["other"])
    db.commit()
    body = dashboard(client, case, "other")
    assert [p["id"] for p in body["projects"]] == [case["web"].id, case["foreign"].id]
    assert body["my_task_counts"] == {"TODO": 0, "IN_PROGRESS": 0, "REVIEW_TESTING": 0, "DONE": 1}


# --- En yakın 5 teslim --------------------------------------------------------------------


def test_upcoming_tasks_are_nearest_five(client, case):
    db, me = case["db"], case["me"]
    for offset in (9, 1, 5, 3, 7, 2, 30):
        add_task(db, case["web"], TaskStatus.TODO, me, due=TODAY + timedelta(days=offset),
                 title=f"{offset} gün")
    db.commit()
    upcoming = dashboard(client, case)["upcoming_tasks"]
    assert [t["title"] for t in upcoming] == ["1 gün", "2 gün", "3 gün", "5 gün", "7 gün"]


def test_upcoming_tasks_are_full_task_objects(client, case):
    db = case["db"]
    task = add_task(db, case["mobile"], TaskStatus.IN_PROGRESS, case["me"], due=TODAY + timedelta(days=2))
    db.commit()
    upcoming = dashboard(client, case)["upcoming_tasks"]
    assert len(upcoming) == 1
    item = upcoming[0]
    assert item["id"] == task.id
    assert item["project_id"] == case["mobile"].id
    assert item["assignee"]["id"] == case["me"].id
    assert item["due_date"] == (TODAY + timedelta(days=2)).isoformat()
    for field in ("labels", "subtask_count", "risk_level", "comment_count", "file_count", "sprint_id"):
        assert field in item


def test_upcoming_excludes_done_inactive_undated_and_others(client, case):
    db, me = case["db"], case["me"]
    soon = TODAY + timedelta(days=1)
    add_task(db, case["web"], TaskStatus.DONE, me, due=soon, title="bitti")
    add_task(db, case["web"], TaskStatus.ONAY_BEKLIYOR, me, due=soon, title="onay bekliyor")
    add_task(db, case["web"], TaskStatus.REDDEDILDI, me, due=soon, title="reddedildi")
    add_task(db, case["web"], TaskStatus.TODO, me, due=None, title="tarihsiz")
    add_task(db, case["web"], TaskStatus.TODO, case["other"], due=soon, title="başkasının")
    add_task(db, case["web"], TaskStatus.REVIEW_TESTING, me, due=soon, title="benim")
    db.commit()
    assert [t["title"] for t in dashboard(client, case)["upcoming_tasks"]] == ["benim"]


def test_overdue_tasks_come_first(client, case):
    db, me = case["db"], case["me"]
    add_task(db, case["web"], TaskStatus.TODO, me, due=TODAY + timedelta(days=1), title="yarın")
    add_task(db, case["web"], TaskStatus.IN_PROGRESS, me, due=TODAY - timedelta(days=3), title="gecikmiş")
    add_task(db, case["web"], TaskStatus.TODO, me, due=TODAY, title="bugün")
    db.commit()
    titles = [t["title"] for t in dashboard(client, case)["upcoming_tasks"]]
    assert titles == ["gecikmiş", "bugün", "yarın"]


def test_upcoming_spans_projects(client, case):
    db, me = case["db"], case["me"]
    add_task(db, case["web"], TaskStatus.TODO, me, due=TODAY + timedelta(days=4), title="web")
    add_task(db, case["mobile"], TaskStatus.TODO, me, due=TODAY + timedelta(days=2), title="mobil")
    db.commit()
    assert [t["title"] for t in dashboard(client, case)["upcoming_tasks"]] == ["mobil", "web"]


def test_tasks_of_left_project_are_not_shown(client, case):
    """Üyesi olmadığı projedeki görevler (atama kalmış olsa bile) dashboard'a girmez."""
    db, me = case["db"], case["me"]
    add_task(db, case["foreign"], TaskStatus.TODO, me, due=TODAY + timedelta(days=1))
    db.commit()
    body = dashboard(client, case)
    assert body["upcoming_tasks"] == []
    assert body["my_task_counts"]["TODO"] == 0


# --- Okunmamış bildirimler ----------------------------------------------------------------


def test_unread_notification_count(client, case):
    db = case["db"]
    for is_read in (False, False, False, True):
        db.add(Notification(user_id=case["me"].id, type=NotificationType.TASK_ASSIGNED,
                            message="Görev atandı.", project_id=case["web"].id, is_read=is_read))
    db.add(Notification(user_id=case["other"].id, type=NotificationType.TASK_ASSIGNED, message="x"))
    db.commit()
    assert dashboard(client, case)["unread_notification_count"] == 3
    assert dashboard(client, case, "other")["unread_notification_count"] == 1


def test_unread_count_drops_after_read(client, case):
    db = case["db"]
    note = Notification(user_id=case["me"].id, type=NotificationType.DUE_DATE_SOON, message="x")
    db.add(note)
    db.commit()
    assert dashboard(client, case)["unread_notification_count"] == 1
    note.is_read = True
    db.commit()
    assert dashboard(client, case)["unread_notification_count"] == 0
