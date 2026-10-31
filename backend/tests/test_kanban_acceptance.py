"""US-015 / #163 acceptance: real routes, isolated SQL fixtures, no fake board.

Board tests skip ONLY while its GET route is absent. Set LUNO_REQUIRE_KANBAN=1
on retest to turn that dependency into a failure. PATCH checks are API checks,
not proof of browser drag/drop or optimistic UI rollback.
"""
import os
from datetime import date

import pytest

from app.core.security import create_access_token
from app.main import app
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskResponse


STATUSES = ("TODO", "IN_PROGRESS", "REVIEW_TESTING", "DONE")
BOARD_PATH = "/api/v1/projects/{project_id}/board"


@pytest.fixture
def require_board():
    # Check routing, never skip because the actual endpoint returned an error.
    if "get" not in app.openapi()["paths"].get(BOARD_PATH, {}):
        message = "US-015 BLOCKED: GET board missing; implement #161, then retest #163 / #162"
        if os.getenv("LUNO_REQUIRE_KANBAN") == "1":
            pytest.fail(message)
        pytest.skip(message)


@pytest.fixture
def board_case(db_session):
    db = db_session
    users = {}
    for name, role in (("admin", "YONETICI"), ("owner", "EKIP_UYESI"),
                       ("colleague", "EKIP_UYESI"), ("outsider", "EKIP_UYESI"),
                       ("external_admin", "YONETICI")):
        user = User(full_name=name, email=f"kanban-{name}@example.com",
                    hashed_password="unused-synthetic-fixture", role=role)
        db.add(user)
        db.flush()
        users[name] = user
    projects = []
    for name in ("Kanban QA", "Other project", "Empty board"):
        project = Project(name=name, created_by_id=users["admin"].id,
                          start_date=date(2026, 10, 1), end_date=date(2026, 11, 30))
        db.add(project)
        db.flush()
        projects.append(project)
        for actor in ("admin", "owner", "colleague"):
            db.add(ProjectMember(project_id=project.id, user_id=users[actor].id,
                                 technical_role="QA"))
    tasks = []
    for index, status in enumerate(TaskStatus):
        task = Task(project_id=projects[0].id, title=f"Parent {status.value}",
                    status=status, assignee_id=users["owner"].id,
                    created_by_id=users["admin"].id, sprint_id=2 if index % 2 == 0 else 3)
        db.add(task)
        db.flush()
        tasks.append(task)
        db.add(Task(project_id=projects[0].id, parent_id=task.id,
                    title=f"Child {status.value}", status=TaskStatus.DONE,
                    assignee_id=users["owner"].id, created_by_id=users["admin"].id,
                    sprint_id=task.sprint_id))
    no_sprint = Task(project_id=projects[0].id, title="Unplanned task", status=TaskStatus.TODO,
                     created_by_id=users["admin"].id)
    db.add(no_sprint)
    db.add(Task(project_id=projects[1].id, title="Foreign project task", status=TaskStatus.TODO,
                assignee_id=users["owner"].id, created_by_id=users["admin"].id, sprint_id=2))
    db.commit()
    headers = {name: {"Authorization": "Bearer " + create_access_token({"sub": str(user.id)})}
               for name, user in users.items()}
    return {"users": users, "projects": projects, "tasks": tasks, "no_sprint": no_sprint,
            "headers": headers, "url": f"/api/v1/projects/{projects[0].id}/board"}


def row(db, task):
    db.refresh(task)
    return {column.name: getattr(task, column.name) for column in Task.__table__.columns}


def columns(response):
    assert response.status_code == 200, response.text
    body = response.json()
    assert [column["status"] for column in body["columns"]] == list(STATUSES)
    found = []
    for column in body["columns"]:
        assert isinstance(column["tasks"], list)
        for task in column["tasks"]:
            assert set(TaskResponse.model_fields) <= task.keys()
            TaskResponse.model_validate(task)
            assert task["status"] == column["status"]
            assert task["parent_id"] is None
            found.append(task["id"])
    assert len(found) == len(set(found)), "Duplicate cards"
    return body["columns"]


@pytest.mark.parametrize("actor", ["owner", "colleague", "admin"])
def test_board_groups_only_active_parents(require_board, client, board_case, actor):
    case = board_case
    result = columns(client.get(case["url"], headers=case["headers"][actor]))
    expected = [task for task in case["tasks"] if task.status.value in STATUSES] + [case["no_sprint"]]
    assert {task["id"] for col in result for task in col["tasks"]} == {task.id for task in expected}
    for col in result:
        assert {task["id"] for task in col["tasks"]} == {
            task.id for task in expected if task.status.value == col["status"]}
        assert all(task["project_id"] == case["projects"][0].id for task in col["tasks"])


def test_empty_project_still_has_four_columns(require_board, client, board_case):
    case = board_case
    result = columns(client.get(f'/api/v1/projects/{case["projects"][2].id}/board',
                                headers=case["headers"]["owner"]))
    assert all(col["tasks"] == [] for col in result)


@pytest.mark.parametrize("sprint_id", [2, 3, 999999])
def test_board_sprint_filter_excludes_other_and_unplanned_tasks(require_board, client, board_case, sprint_id):
    case = board_case
    result = columns(client.get(case["url"], params={"sprint_id": sprint_id},
                                headers=case["headers"]["owner"]))
    expected = {task.id for task in case["tasks"]
                if task.status.value in STATUSES and task.sprint_id == sprint_id}
    assert {task["id"] for col in result for task in col["tasks"]} == expected


@pytest.mark.parametrize("actor", ["outsider", "external_admin"])
def test_board_requires_project_membership(require_board, client, board_case, actor):
    result = client.get(board_case["url"], headers=board_case["headers"][actor])
    assert result.status_code == 403
    assert result.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert "columns" not in result.json()


def test_board_requires_authentication(require_board, client, board_case):
    assert client.get(board_case["url"]).status_code == 401


def test_missing_project_is_not_an_empty_board(require_board, client, board_case):
    result = client.get("/api/v1/projects/999999/board", headers=board_case["headers"]["owner"])
    assert result.status_code == 404
    assert result.json()["error"]["code"] == "PROJECT_NOT_FOUND"


@pytest.mark.parametrize("actor", ["owner", "admin"])
@pytest.mark.parametrize("target", STATUSES)
def test_card_move_patch_persists_status(client, db_session, board_case, actor, target):
    """API part of FR-043 only; this does not simulate browser dragging."""
    task = next(task for task in board_case["tasks"] if task.status == TaskStatus.TODO)
    # Ensure every parameter actually changes the state, including target TODO.
    task.status = TaskStatus.DONE if target == "TODO" else TaskStatus.TODO
    db_session.commit()
    before = row(db_session, task)
    response = client.patch(f"/api/v1/tasks/{task.id}/status",
                            headers=board_case["headers"][actor], json={"status": target})
    assert response.status_code == 200, response.text
    assert response.json()["status"] == target
    after = row(db_session, task)
    assert after["status"].value == target
    assert {k: v for k, v in after.items() if k not in ("status", "updated_at")} == {
        k: v for k, v in before.items() if k not in ("status", "updated_at")}


@pytest.mark.parametrize("actor", ["colleague", "outsider", "external_admin"])
def test_denied_card_move_preserves_database(client, db_session, board_case, actor):
    task = next(task for task in board_case["tasks"] if task.status == TaskStatus.TODO)
    before = row(db_session, task)
    response = client.patch(f"/api/v1/tasks/{task.id}/status",
                            headers=board_case["headers"][actor], json={"status": "DONE"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "NOT_TASK_ASSIGNEE"
    assert row(db_session, task) == before


@pytest.mark.parametrize("source", ["ONAY_BEKLIYOR", "REDDEDILDI"])
@pytest.mark.parametrize("actor", ["owner", "admin"])
def test_inactive_card_cannot_move(client, db_session, board_case, source, actor):
    task = next(task for task in board_case["tasks"] if task.status.value == source)
    before = row(db_session, task)
    response = client.patch(f"/api/v1/tasks/{task.id}/status",
                            headers=board_case["headers"][actor], json={"status": "TODO"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TASK_NOT_ACTIVE"
    assert row(db_session, task) == before


@pytest.mark.parametrize("target", STATUSES)
def test_board_reload_after_move_has_one_card_in_target_column(require_board, client, db_session, board_case, target):
    task = next(task for task in board_case["tasks"] if task.status == TaskStatus.TODO)
    task.status = TaskStatus.DONE if target == "TODO" else TaskStatus.TODO
    db_session.commit()
    headers = board_case["headers"]["owner"]
    assert client.patch(f"/api/v1/tasks/{task.id}/status", headers=headers,
                        json={"status": target}).status_code == 200
    result = columns(client.get(board_case["url"], headers=headers))
    locations = [col["status"] for col in result for card in col["tasks"] if card["id"] == task.id]
    assert locations == [target]


def test_board_unchanged_after_denied_move(require_board, client, board_case):
    headers = board_case["headers"]["colleague"]
    before = client.get(board_case["url"], headers=headers)
    columns(before)
    task = next(task for task in board_case["tasks"] if task.status == TaskStatus.TODO)
    assert client.patch(f"/api/v1/tasks/{task.id}/status", headers=headers,
                        json={"status": "DONE"}).status_code == 403
    after = client.get(board_case["url"], headers=headers)
    columns(after)
    assert after.json() == before.json()


def test_board_200_parent_cards_are_complete_without_duplicates(require_board, client, db_session, board_case):
    """Functional volume check; not the browser's NFR-011 performance measurement."""
    project = board_case["projects"][2]
    # Three fixture members plus 17 extra members reproduce the NFR-011 volume.
    member_ids = [board_case["users"][name].id for name in ("admin", "owner", "colleague")]
    for i in range(17):
        user = User(full_name=f"Volume member {i}", email=f"volume-{i}@example.com",
                    hashed_password="unused-synthetic-fixture", role="EKIP_UYESI")
        db_session.add(user)
        db_session.flush()
        member_ids.append(user.id)
        db_session.add(ProjectMember(project_id=project.id, user_id=user.id, technical_role="QA"))
    tasks = [Task(project_id=project.id, title=f"Volume card {i}",
                  status=TaskStatus(STATUSES[i % 4]), assignee_id=member_ids[i % 20],
                  created_by_id=board_case["users"]["admin"].id)
             for i in range(200)]
    db_session.add_all(tasks)
    db_session.commit()
    result = columns(client.get(f"/api/v1/projects/{project.id}/board",
                                headers=board_case["headers"]["owner"]))
    assert {card["id"] for col in result for card in col["tasks"]} == {task.id for task in tasks}
    assert [len(col["tasks"]) for col in result] == [50, 50, 50, 50]
