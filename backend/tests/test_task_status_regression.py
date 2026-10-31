"""US-014 / #160: persistence, transition and authorization regressions.

Fixtures seed isolated SQL rows because task creation is a separate story.
Requests exercise real authentication and PATCH routes; no auth override is used.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.security import create_access_token
from app.models.enums import Priority, TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User


ACTIVE = ("TODO", "IN_PROGRESS", "REVIEW_TESTING", "DONE")


@pytest.fixture
def status_case(db_session):
    db = db_session
    users = {}
    for name, role in (("admin", "YONETICI"), ("assignee", "EKIP_UYESI"),
                       ("colleague", "EKIP_UYESI"), ("outsider", "EKIP_UYESI"),
                       ("external_admin", "YONETICI")):
        user = User(full_name=name, email=f"{name}@example.com",
                    hashed_password="unused-fixture-password", role=role)
        db.add(user)
        db.flush()
        users[name] = user
    project = Project(name="US014 QA", created_by_id=users["admin"].id,
                      start_date=date(2026, 10, 1), end_date=date(2026, 11, 30))
    db.add(project)
    db.flush()
    for name in ("admin", "assignee", "colleague"):
        db.add(ProjectMember(project_id=project.id, user_id=users[name].id,
                             technical_role="QA"))
    task = Task(project_id=project.id, title="Status regression", description="Preserve me",
                assignee_id=users["assignee"].id, created_by_id=users["admin"].id,
                priority=Priority.YUKSEK, story_points=5, status=TaskStatus.TODO,
                start_date=date(2026, 10, 2), due_date=date(2026, 10, 30),
                created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
                updated_at=datetime(2026, 1, 2, tzinfo=timezone.utc))
    sibling = Task(project_id=project.id, title="Untouched sibling",
                   created_by_id=users["admin"].id, status=TaskStatus.TODO)
    db.add_all([task, sibling])
    db.commit()
    headers = {name: {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
               for name, user in users.items()}
    return {"users": users, "project": project, "task": task, "sibling": sibling,
            "headers": headers, "url": f"/api/v1/tasks/{task.id}/status"}


def snapshot(db, task):
    db.refresh(task)
    return {column.name: getattr(task, column.name) for column in Task.__table__.columns}


@pytest.mark.parametrize("actor", ["assignee", "admin"])
@pytest.mark.parametrize("source", ACTIVE)
@pytest.mark.parametrize("target", ACTIVE)
def test_all_active_transitions_persist_without_other_changes(client, db_session, status_case,
                                                            actor, source, target):
    """FR-033: 4x4 transitions, including reopen and repeat, for both allowed roles."""
    case = status_case
    task = case["task"]
    task.status = TaskStatus(source)
    db_session.commit()
    before = snapshot(db_session, task)
    sibling_before = snapshot(db_session, case["sibling"])
    result = client.patch(case["url"], headers=case["headers"][actor], json={"status": target})
    assert result.status_code == 200, result.text
    assert result.json()["status"] == target
    after = snapshot(db_session, task)
    assert after["status"] == TaskStatus(target)
    assert after["updated_at"] > before["updated_at"]
    for field in before.keys() - {"status", "updated_at"}:
        assert after[field] == before[field], field
    assert snapshot(db_session, case["sibling"]) == sibling_before


@pytest.mark.parametrize("actor", ["colleague", "outsider", "external_admin"])
@pytest.mark.parametrize("target", ACTIVE)
def test_denied_updates_preserve_entire_row(client, db_session, status_case, actor, target):
    """FR-034: same-project colleague, outside member and outside admin all denied."""
    before = snapshot(db_session, status_case["task"])
    result = client.patch(status_case["url"], headers=status_case["headers"][actor],
                          json={"status": target})
    assert result.status_code == 403
    assert result.json()["error"]["code"] == "NOT_TASK_ASSIGNEE"
    assert result.json()["error"]["message"] == "Size atanmamış bir görevin durumunu değiştiremezsiniz."
    assert snapshot(db_session, status_case["task"]) == before


@pytest.mark.parametrize("actor", ["assignee", "admin"])
@pytest.mark.parametrize("source", ["ONAY_BEKLIYOR", "REDDEDILDI"])
@pytest.mark.parametrize("target", ACTIVE)
def test_inactive_tasks_cannot_be_reactivated(client, db_session, status_case, actor, source, target):
    task = status_case["task"]
    task.status = TaskStatus(source)
    db_session.commit()
    before = snapshot(db_session, task)
    result = client.patch(status_case["url"], headers=status_case["headers"][actor],
                          json={"status": target})
    assert result.status_code == 400
    assert result.json()["error"]["code"] == "TASK_NOT_ACTIVE"
    assert snapshot(db_session, task) == before


@pytest.mark.parametrize("payload", [{}, {"status": None}, {"status": ""}, {"status": "done"},
    {"status": "UNKNOWN"}, {"status": "ONAY_BEKLIYOR"}, {"status": "REDDEDILDI"},
    {"status": 1}, {"status": True}, {"status": []}, {"status": {}}])
def test_invalid_payload_preserves_row(client, db_session, status_case, payload):
    before = snapshot(db_session, status_case["task"])
    result = client.patch(status_case["url"], headers=status_case["headers"]["assignee"], json=payload)
    assert result.status_code == 422
    assert snapshot(db_session, status_case["task"]) == before


@pytest.mark.parametrize("credential", ["missing", "malformed", "expired", "logged_out"])
def test_invalid_session_cannot_mutate_task(client, db_session, status_case, credential):
    headers = {}
    if credential == "malformed":
        headers = {"Authorization": "Bearer not-a-jwt"}
    elif credential == "expired":
        token = create_access_token({"sub": str(status_case["users"]["assignee"].id)},
                                    expires_delta=timedelta(seconds=-60))
        headers = {"Authorization": "Bearer " + token}
    elif credential == "logged_out":
        headers = status_case["headers"]["assignee"]
        assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    before = snapshot(db_session, status_case["task"])
    result = client.patch(status_case["url"], headers=headers, json={"status": "DONE"})
    assert result.status_code == 401
    assert snapshot(db_session, status_case["task"]) == before


def test_removed_member_old_token_cannot_update(client, db_session, status_case):
    case = status_case
    result = client.delete(f'/api/v1/projects/{case["project"].id}/members/{case["users"]["assignee"].id}',
                           headers=case["headers"]["admin"])
    assert result.status_code == 204, result.text
    before = snapshot(db_session, case["task"])
    assert before["assignee_id"] is None
    result = client.patch(case["url"], headers=case["headers"]["assignee"], json={"status": "DONE"})
    assert result.status_code == 403
    assert snapshot(db_session, case["task"]) == before


def test_demoted_admin_old_token_cannot_update_others_task(client, db_session, status_case):
    case = status_case
    case["users"]["admin"].role = "EKIP_UYESI"
    db_session.commit()
    before = snapshot(db_session, case["task"])
    result = client.patch(case["url"], headers=case["headers"]["admin"], json={"status": "DONE"})
    assert result.status_code == 403
    assert snapshot(db_session, case["task"]) == before
