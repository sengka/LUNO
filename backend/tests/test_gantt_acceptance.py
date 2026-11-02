"""US-017 / #195: real Gantt API acceptance, independent of unfinished UI #194.

SQL creates isolated synthetic fixtures; authentication and Gantt routes are real.
No skip or mocked Gantt response: regressions must fail.
"""
from datetime import date, timedelta

import pytest

from app.core.security import create_access_token
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User


ACTIVE = ("TODO", "IN_PROGRESS", "REVIEW_TESTING", "DONE")


@pytest.fixture
def gantt_case(db_session):
    users = {}
    for name, role in (("admin", "YONETICI"), ("member", "EKIP_UYESI"),
                       ("outsider", "EKIP_UYESI"), ("external_admin", "YONETICI")):
        user = User(full_name=name, email=f"gantt-{name}@example.com",
                    hashed_password="unused-synthetic-fixture", role=role)
        db_session.add(user)
        db_session.flush()
        users[name] = user
    project = Project(name="Gantt QA", start_date=date(2026, 10, 1),
                      end_date=date(2026, 12, 31), created_by_id=users["admin"].id)
    db_session.add(project)
    db_session.flush()
    for actor in ("admin", "member"):
        db_session.add(ProjectMember(project_id=project.id, user_id=users[actor].id))
    db_session.commit()
    headers = {name: {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
               for name, user in users.items()}
    return {"users": users, "project": project, "headers": headers,
            "url": f"/api/v1/projects/{project.id}/gantt"}


def add_task(db, case, **overrides):
    values = dict(project_id=case["project"].id, title="Türkçe görev — şema",
                  status=TaskStatus.TODO, start_date=date(2026, 11, 1),
                  due_date=date(2026, 11, 5), created_by_id=case["users"]["admin"].id)
    values.update(overrides)
    task = Task(**values)
    db.add(task)
    db.commit()
    return task


def read_gantt(client, case, actor="member"):
    response = client.get(case["url"], headers=case["headers"][actor])
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["project"] == {"start_date": "2026-10-01", "end_date": "2026-12-31"}
    ids = [item["task_id"] for item in data["items"]]
    assert len(ids) == len(set(ids)), "Duplicate Gantt items"
    for item in data["items"]:
        assert {"task_id", "title", "start_date", "due_date", "progress_percent",
                "status", "parent_id", "depends_on"} <= item.keys()
        assert type(item["task_id"]) is int
        assert date.fromisoformat(item["start_date"]) <= date.fromisoformat(item["due_date"])
        assert item["status"] in ACTIVE
        assert 0 <= item["progress_percent"] <= 100
        assert item["depends_on"] == []  # #193: dependency arrows are Sprint 9 work.
    return data["items"]


@pytest.mark.parametrize("status", ACTIVE)
@pytest.mark.parametrize("missing", ["start", "due", "both"])
def test_undated_active_tasks_are_omitted_without_mutation(client, db_session, gantt_case, status, missing):
    task = add_task(db_session, gantt_case, status=TaskStatus(status),
                    start_date=None if missing in ("start", "both") else date(2026, 11, 1),
                    due_date=None if missing in ("due", "both") else date(2026, 11, 5))
    before = (task.start_date, task.due_date, task.status, task.updated_at)
    assert read_gantt(client, gantt_case) == []
    db_session.refresh(task)
    assert (task.start_date, task.due_date, task.status, task.updated_at) == before


@pytest.mark.parametrize("status,progress", [("TODO", 0), ("IN_PROGRESS", 0),
                                           ("REVIEW_TESTING", 0), ("DONE", 100)])
def test_dated_leaf_preserves_dates_title_and_status(client, db_session, gantt_case, status, progress):
    task = add_task(db_session, gantt_case, status=TaskStatus(status))
    assert read_gantt(client, gantt_case) == [{
        "task_id": task.id, "title": task.title, "start_date": "2026-11-01",
        "due_date": "2026-11-05", "progress_percent": progress,
        "status": status, "parent_id": None, "depends_on": []}]


@pytest.mark.parametrize("start,end", [(date(2026, 11, 1), date(2026, 11, 1)),
    (date(2026, 10, 31), date(2026, 11, 1)), (date(2026, 12, 31), date(2027, 1, 1)),
    (date(2028, 2, 28), date(2028, 2, 29))])
def test_date_boundaries_are_returned_exactly_without_clipping(client, db_session, gantt_case, start, end):
    # 7.3 has no calendar-range filter and no project-date clipping rule.
    add_task(db_session, gantt_case, start_date=start, due_date=end)
    item, = read_gantt(client, gantt_case)
    assert (item["start_date"], item["due_date"]) == (start.isoformat(), end.isoformat())


def test_mixed_data_keeps_active_children_and_excludes_inactive_or_foreign_tasks(client, db_session, gantt_case):
    case = gantt_case
    parent = add_task(db_session, case, start_date=None, due_date=None)
    child = add_task(db_session, case, parent_id=parent.id)
    for status in ("ONAY_BEKLIYOR", "REDDEDILDI"):
        add_task(db_session, case, status=TaskStatus(status))
        add_task(db_session, case, parent_id=parent.id, status=TaskStatus(status))
    other = Project(name="Foreign", start_date=date(2026, 10, 1),
                    end_date=date(2026, 12, 31), created_by_id=case["users"]["admin"].id)
    db_session.add(other)
    db_session.commit()
    add_task(db_session, case, project_id=other.id)
    items = read_gantt(client, case)
    assert [item["task_id"] for item in items] == [child.id]
    assert items[0]["parent_id"] == parent.id


@pytest.mark.parametrize("parent_status,children,expected", [
    ("IN_PROGRESS", ["DONE", "TODO", "TODO"], 33.3),
    ("TODO", ["DONE", "DONE", "TODO"], 66.7),
    ("TODO", ["DONE", "DONE"], 100),
    ("DONE", ["TODO", "REVIEW_TESTING"], 0),
    ("DONE", ["DONE", "TODO"], 50),
    ("IN_PROGRESS", ["DONE", "ONAY_BEKLIYOR", "REDDEDILDI"], 33.3),
])
def test_parent_progress_uses_all_children_including_undated(client, db_session, gantt_case,
                                                          parent_status, children, expected):
    parent = add_task(db_session, gantt_case, status=TaskStatus(parent_status))
    for status in children:
        add_task(db_session, gantt_case, parent_id=parent.id, status=TaskStatus(status),
                 start_date=None, due_date=None)
    item, = read_gantt(client, gantt_case)
    assert item["task_id"] == parent.id
    assert item["progress_percent"] == expected


@pytest.mark.parametrize("actor", ["member", "admin"])
def test_empty_project_member_can_read_empty_timeline(client, gantt_case, actor):
    assert read_gantt(client, gantt_case, actor) == []


@pytest.mark.parametrize("actor", ["outsider", "external_admin"])
def test_nonmember_cannot_read_gantt_even_if_admin(client, db_session, gantt_case, actor):
    add_task(db_session, gantt_case)
    response = client.get(gantt_case["url"], headers=gantt_case["headers"][actor])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert "items" not in response.json()


@pytest.mark.parametrize("session", ["missing", "invalid", "expired", "logged_out"])
def test_unauthenticated_sessions_do_not_leak_timeline(client, gantt_case, session):
    headers = {}
    if session == "invalid":
        headers = {"Authorization": "Bearer invalid"}
    elif session == "expired":
        token = create_access_token({"sub": str(gantt_case["users"]["member"].id)},
                                    expires_delta=timedelta(seconds=-60))
        headers = {"Authorization": "Bearer " + token}
    elif session == "logged_out":
        headers = gantt_case["headers"]["member"]
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    response = client.get(gantt_case["url"], headers=headers)
    assert response.status_code == 401
    assert "items" not in response.json()


def test_removed_member_old_token_loses_timeline_access(client, gantt_case):
    case = gantt_case
    assert client.delete(f'/api/v1/projects/{case["project"].id}/members/{case["users"]["member"].id}',
                         headers=case["headers"]["admin"]).status_code == 204
    response = client.get(case["url"], headers=case["headers"]["member"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_missing_project_is_not_empty_success(client, gantt_case):
    response = client.get("/api/v1/projects/999999/gantt", headers=gantt_case["headers"]["member"])
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_status_update_is_reflected_on_next_gantt_read(client, db_session, gantt_case):
    task = add_task(db_session, gantt_case, assignee_id=gantt_case["users"]["member"].id)
    assert read_gantt(client, gantt_case)[0]["progress_percent"] == 0
    response = client.patch(f"/api/v1/tasks/{task.id}/status", headers=gantt_case["headers"]["member"],
                            json={"status": "DONE"})
    assert response.status_code == 200
    item, = read_gantt(client, gantt_case)
    assert item["status"] == "DONE"
    assert item["progress_percent"] == 100


def test_200_dated_tasks_with_20_members_are_complete(client, db_session, gantt_case):
    # Functional volume only, not browser rendering or an NFR-008 timing claim.
    case = gantt_case
    ids = [case["users"][name].id for name in ("admin", "member")]
    for i in range(18):
        user = User(full_name=f"Volume {i}", email=f"gantt-volume-{i}@example.com",
                    hashed_password="unused-synthetic-fixture", role="EKIP_UYESI")
        db_session.add(user)
        db_session.flush()
        ids.append(user.id)
        db_session.add(ProjectMember(project_id=case["project"].id, user_id=user.id))
    tasks = [Task(project_id=case["project"].id, title=f"Task {i}", status=TaskStatus(ACTIVE[i % 4]),
                  start_date=date(2026, 11, 1), due_date=date(2026, 11, 5), assignee_id=ids[i % 20])
             for i in range(200)]
    db_session.add_all(tasks)
    db_session.commit()
    assert {item["task_id"] for item in read_gantt(client, case)} == {task.id for task in tasks}
