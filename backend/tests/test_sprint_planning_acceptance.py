"""US-040 / #244: FR-066, FR-067 acceptance and mutation isolation."""

from datetime import date

import pytest
from sqlalchemy import select

from app.core.security import create_access_token
from app.models import Project, ProjectMember, Sprint, Task, TaskStatus, User


@pytest.fixture
def planning(db_session):
    db = db_session
    users, headers = {}, {}
    for who, role in (("admin", "YONETICI"), ("member", "EKIP_UYESI"),
                      ("outside_admin", "YONETICI"), ("outsider", "EKIP_UYESI")):
        user = User(full_name=who, email=f"{who}@planning.example", role=role,
                    hashed_password="test-only")
        db.add(user)
        db.flush()
        users[who] = user
        headers[who] = {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}
    headers["anonymous"] = {}
    headers["invalid_token"] = {"Authorization": "Bearer invalid-token"}
    dates = dict(start_date=date(2026, 1, 1), end_date=date(2028, 12, 31))
    project = Project(name="Planning", created_by_id=users["admin"].id, **dates)
    other = Project(name="Other", created_by_id=users["outside_admin"].id, **dates)
    db.add_all([project, other])
    db.flush()
    db.add_all([ProjectMember(project_id=project.id, user_id=users[w].id)
                for w in ("admin", "member")])
    db.add(ProjectMember(project_id=other.id, user_id=users["outside_admin"].id))
    sprint = Sprint(project_id=project.id, name="Initial", goal="Keep goal",
                    start_date=date(2026, 11, 9), end_date=date(2026, 11, 15), capacity_points=8)
    later = Sprint(project_id=project.id, name="Later", start_date=date(2026, 11, 16),
                   end_date=date(2026, 11, 22))
    foreign = Sprint(project_id=other.id, name="Foreign", start_date=date(2026, 11, 9),
                     end_date=date(2026, 11, 15))
    db.add_all([sprint, later, foreign])
    db.flush()
    task = Task(project_id=project.id, title="Existing task", description="Keep description",
                assignee_id=users["member"].id, status=TaskStatus.IN_PROGRESS, story_points=5,
                sprint_id=sprint.id)
    unplanned = Task(project_id=project.id, title="Backlog", story_points=3)
    foreign_task = Task(project_id=other.id, title="Foreign task", sprint_id=foreign.id)
    db.add_all([task, unplanned, foreign_task])
    db.commit()
    return dict(db=db, headers=headers, project=project, other=other, sprint=sprint,
                later=later, foreign=foreign, task=task, unplanned=unplanned,
                foreign_task=foreign_task)


def payload(**kw):
    return {"name": "New sprint", "goal": "Release planning", "start_date": "2026-12-01",
            "end_date": "2026-12-07", "capacity_points": 13, **kw}


def snapshot(c):
    c["db"].expire_all()
    return {m.__tablename__: list(c["db"].execute(
                select(m.__table__).order_by(*m.__table__.primary_key.columns)))
            for m in (Sprint, Task, ProjectMember)}


def send(client, c, op, who="admin", missing=False):
    project_id = 999999 if missing else c["project"].id
    sprint_id = 999999 if missing else c["sprint"].id
    base = f"/api/v1/sprints/{sprint_id}"
    method, url, body = {
        "list": ("get", f"/api/v1/projects/{project_id}/sprints", None),
        "detail": ("get", base, None),
        "create": ("post", f"/api/v1/projects/{project_id}/sprints", payload()),
        "patch": ("patch", base, {"name": "Changed"}),
        "delete": ("delete", base, None),
        "add": ("post", base + "/tasks", {"task_ids": [c["unplanned"].id]}),
        "remove": ("delete", base + f"/tasks/{c['task'].id}", None),
    }[op]
    kwargs = {"headers": c["headers"][who]}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(url, **kwargs)


@pytest.mark.parametrize("op", ["list", "detail", "create", "patch", "delete", "add", "remove"])
@pytest.mark.parametrize("who", ["member", "outside_admin", "outsider", "anonymous", "invalid_token"])
def test_permission_matrix_preserves_rows(client, planning, op, who):
    c = planning
    before = snapshot(c)
    response = send(client, c, op, who)
    read = op in ("list", "detail")
    expected = 200 if who == "member" and read else 401 if who in (
        "anonymous", "invalid_token") else 403
    assert response.status_code == expected, response.text
    if expected != 200:
        code = "UNAUTHORIZED" if expected == 401 else "PROJECT_ACCESS_DENIED" if (
            read or who == "outside_admin") else "FORBIDDEN"
        assert response.json()["error"]["code"] == code
    assert snapshot(c) == before


@pytest.mark.parametrize("op", ["list", "detail", "create", "patch", "delete", "add", "remove"])
def test_missing_resources_are_404_and_atomic(client, planning, op):
    before = snapshot(planning)
    response = send(client, planning, op, missing=True)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == (
        "PROJECT_NOT_FOUND" if op in ("list", "create") else "SPRINT_NOT_FOUND")
    assert snapshot(planning) == before


@pytest.mark.parametrize("start,end", [
    ("2026-11-08", "2026-11-09"),  # shared first day
    ("2026-11-15", "2026-11-15"),  # shared last day
    ("2026-11-09", "2026-11-15"),  # identical
    ("2026-11-10", "2026-11-12"),  # contained
    ("2026-11-01", "2026-11-30"),  # enclosing
])
@pytest.mark.parametrize("method", ["post", "patch"])
def test_overlap_shapes_and_failed_edit_are_atomic(client, planning, start, end, method):
    c = planning
    before = snapshot(c)
    url = (f"/api/v1/projects/{c['project'].id}/sprints" if method == "post"
           else f"/api/v1/sprints/{c['later'].id}")
    response = getattr(client, method)(url, headers=c["headers"]["admin"],
                                      json=payload(start_date=start, end_date=end))
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SPRINT_OVERLAP"
    assert snapshot(c) == before


@pytest.mark.parametrize("method,body", [
    ("post", {"start_date": "2026-12-08", "end_date": "2026-12-07"}),
    ("patch", {"start_date": "2026-11-16"}),
    ("patch", {"end_date": "2026-11-08"}),
])
def test_reversed_dates_do_not_mutate(client, planning, method, body):
    c = planning
    before = snapshot(c)
    url = (f"/api/v1/projects/{c['project'].id}/sprints" if method == "post"
           else f"/api/v1/sprints/{c['sprint'].id}")
    response = getattr(client, method)(url, headers=c["headers"]["admin"],
                                      json=payload(**body) if method == "post" else body)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"
    assert snapshot(c) == before


@pytest.mark.parametrize("start,end", [("2026-11-08", "2026-11-08"),
    ("2026-11-23", "2026-11-23"), ("2028-02-29", "2028-03-01")])
def test_adjacent_one_day_and_leap_dates_persist(client, planning, start, end):
    c = planning
    response = client.post(f"/api/v1/projects/{c['project'].id}/sprints",
                           headers=c["headers"]["admin"],
                           json=payload(start_date=start, end_date=end))
    assert response.status_code == 201, response.text
    result = response.json()
    assert (result["start_date"], result["end_date"], result["goal"]) == (start, end, "Release planning")
    detail = client.get(f"/api/v1/sprints/{result['id']}", headers=c["headers"]["member"])
    assert detail.json() == result
    listed = client.get(f"/api/v1/projects/{c['project'].id}/sprints", headers=c["headers"]["member"]).json()
    assert result in listed
    assert [s["start_date"] for s in listed] == sorted(s["start_date"] for s in listed)
    assert all(s["project_id"] == c["project"].id for s in listed)


def test_patch_excludes_self_and_clears_only_nullable_fields(client, planning):
    c = planning
    response = client.patch(f"/api/v1/sprints/{c['sprint'].id}", headers=c["headers"]["admin"],
                            json={"name": "  Edited  ", "goal": None, "capacity_points": None,
                                  "start_date": "2026-11-09", "end_date": "2026-11-15"})
    assert response.status_code == 200
    assert response.json()["name"] == "Edited"
    assert response.json()["goal"] is None and response.json()["capacity_points"] is None
    c["db"].expire_all()
    assert c["db"].get(Task, c["task"].id).sprint_id == c["sprint"].id


@pytest.mark.parametrize("field", ["name", "start_date", "end_date"])
def test_null_required_patch_fields_are_validation_errors(client, planning, field):
    c = planning
    before = snapshot(c)
    response = client.patch(f"/api/v1/sprints/{c['sprint'].id}",
                            headers=c["headers"]["admin"], json={field: None})
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert field in response.json()["error"]["fields"]
    assert snapshot(c) == before


@pytest.mark.parametrize("bad", [{"name": ""}, {"name": "   "}, {"name": "x" * 101},
    {"goal": "x" * 2001}, {"capacity_points": 0}, {"capacity_points": -1},
    {"start_date": "2027-02-29"}, {"end_date": "not-a-date"}])
@pytest.mark.parametrize("method", ["post", "patch"])
def test_invalid_fields_are_422_and_atomic(client, planning, bad, method):
    c = planning
    before = snapshot(c)
    url = (f"/api/v1/projects/{c['project'].id}/sprints" if method == "post"
           else f"/api/v1/sprints/{c['sprint'].id}")
    response = getattr(client, method)(url, headers=c["headers"]["admin"],
                                      json=payload(**bad) if method == "post" else bad)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert snapshot(c) == before


@pytest.mark.parametrize("invalid", ["missing", "foreign"])
def test_mixed_task_batch_has_no_partial_assignment(client, planning, invalid):
    c = planning
    before = snapshot(c)
    task_id = 999999 if invalid == "missing" else c["foreign_task"].id
    response = client.post(f"/api/v1/sprints/{c['later'].id}/tasks", headers=c["headers"]["admin"],
                           json={"task_ids": [c["task"].id, c["unplanned"].id, task_id]})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"
    assert snapshot(c) == before


@pytest.mark.parametrize("ids", [[], ["invalid"], None])
def test_invalid_task_list_is_422(client, planning, ids):
    c = planning
    before = snapshot(c)
    response = client.post(f"/api/v1/sprints/{c['sprint'].id}/tasks", headers=c["headers"]["admin"],
                           json={"task_ids": ids})
    assert response.status_code == 422
    assert snapshot(c) == before


def task_content(c, task_id):
    c["db"].expire_all()
    task = c["db"].get(Task, task_id)
    return {col.name: getattr(task, col.name) for col in Task.__table__.columns
            if col.name not in ("sprint_id", "updated_at")}


def test_link_duplicate_move_unlink_preserves_task_content(client, planning):
    c = planning
    before = task_content(c, c["task"].id)
    url = f"/api/v1/sprints/{c['later'].id}/tasks"
    for _ in range(2):
        result = client.post(url, headers=c["headers"]["admin"], json={"task_ids": [c["task"].id] * 2})
        assert result.status_code == 200
        assert result.json()["total_points"] == 5
        assert task_content(c, c["task"].id) == before
        assert c["db"].get(Task, c["task"].id).sprint_id == c["later"].id
    assert client.get(f"/api/v1/sprints/{c['sprint'].id}", headers=c["headers"]["member"]).json()["total_points"] == 0
    removed = client.delete(url + f"/{c['task'].id}", headers=c["headers"]["admin"])
    assert removed.status_code == 204 and not removed.content
    assert task_content(c, c["task"].id) == before
    assert c["db"].get(Task, c["task"].id).sprint_id is None
    assert client.delete(url + f"/{c['task'].id}", headers=c["headers"]["admin"]).status_code == 404


@pytest.mark.parametrize("capacity,warning", [(8, False), (7, True), (None, False)])
def test_capacity_boundary_warns_without_rejecting_tasks(client, planning, capacity, warning):
    c = planning
    c["sprint"].capacity_points = capacity
    c["db"].commit()
    response = client.post(f"/api/v1/sprints/{c['sprint'].id}/tasks", headers=c["headers"]["admin"],
                           json={"task_ids": [c["task"].id, c["unplanned"].id]})
    assert response.status_code == 200
    assert response.json()["total_points"] == 8
    assert response.json()["capacity_warning"] is warning
    c["db"].expire_all()
    assert c["db"].get(Task, c["unplanned"].id).sprint_id == c["sprint"].id


@pytest.mark.parametrize("which", ["unplanned", "foreign_task"])
def test_wrong_task_removal_is_atomic(client, planning, which):
    c = planning
    before = snapshot(c)
    response = client.delete(f"/api/v1/sprints/{c['sprint'].id}/tasks/{c[which].id}",
                             headers=c["headers"]["admin"])
    assert response.status_code == 404
    assert snapshot(c) == before


def test_sprint_delete_keeps_task_and_other_project(client, planning):
    c = planning
    before = task_content(c, c["task"].id)
    foreign_before = task_content(c, c["foreign_task"].id)
    response = send(client, c, "delete")
    assert response.status_code == 204 and not response.content
    assert task_content(c, c["task"].id) == before
    assert c["db"].get(Task, c["task"].id).sprint_id is None
    assert task_content(c, c["foreign_task"].id) == foreign_before
    assert c["db"].get(Task, c["foreign_task"].id).sprint_id == c["foreign"].id
    assert c["db"].get(Sprint, c["sprint"].id) is None
    assert send(client, c, "detail").status_code == 404
