"""US-011 / #151: creation acceptance against real product routes.

Missing POST is an explicit blocker, never a passing authorization/validation test.
The two storage tests are supplementary model coverage, not API acceptance.
"""
from datetime import date

import pytest

from app.core.security import create_access_token
from app.main import app
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User

CREATE_PATH = "/api/v1/projects/{project_id}/tasks"
CREATE_AVAILABLE = "post" in app.openapi()["paths"].get(CREATE_PATH, {})
requires_creation = pytest.mark.skipif(
    not CREATE_AVAILABLE,
    reason="US-011 blocked: real POST /projects/{project_id}/tasks missing (#149); report #151",
)


@pytest.fixture
def creation_data(db_session):
    users = {}
    for name, role in (("admin", "YONETICI"), ("member", "EKIP_UYESI"),
                       ("outsider", "EKIP_UYESI"), ("outside_admin", "YONETICI")):
        user = User(full_name=f"QA {name}", email=f"{name}@example.com",
                    hashed_password="not-used-in-token-tests", role=role)
        db_session.add(user)
        users[name] = user
    db_session.commit()
    project = Project(name="QA Task Creation", start_date=date(2026,10,1),
                      end_date=date(2026,12,1), created_by_id=users["admin"].id)
    db_session.add(project)
    db_session.commit()
    for name in ("admin", "member"):
        db_session.add(ProjectMember(project_id=project.id, user_id=users[name].id))
    db_session.commit()
    headers = {name: {"Authorization": "Bearer " + create_access_token({"sub":str(user.id)})}
               for name,user in users.items()}
    return users, project, headers


def payload(users):
    return {"title":"Türkçe görev oluşturma", "description":"Açıklama / QA",
            "assignee_id":users["member"].id,
            "start_date":"2026-10-24", "due_date":"2026-10-25"}


def task_state(db):
    return [(t.id,t.project_id,t.title,t.description,t.assignee_id,t.start_date,t.due_date,t.status)
            for t in db.query(Task).order_by(Task.id)]


def assert_error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@requires_creation
@pytest.mark.parametrize("title,day", [("Türkçe görev oluşturma","2026-10-25"),
                                      ("AB","2026-10-24"),("X"*200,"2026-10-25")])
def test_admin_creates_persisted_task(client,db_session,creation_data,title,day):
    users,project,headers=creation_data
    body=payload(users) | {"title":title,"due_date":day}
    before=db_session.query(Task).count()
    response=client.post(f"/api/v1/projects/{project.id}/tasks",headers=headers["admin"],json=body)
    assert response.status_code == 201
    data=response.json()
    assert data["project_id"] == project.id
    assert data["status"] == "TODO"
    assert data["assignee"]["id"] == users["member"].id
    assert data["created_by"]["id"] == users["admin"].id
    assert db_session.query(Task).count() == before+1
    task=db_session.get(Task,data["id"])
    assert (task.title,task.description,task.assignee_id,task.start_date.isoformat(),task.due_date.isoformat()) == (body["title"],body["description"],body["assignee_id"],body["start_date"],day)


@requires_creation
@pytest.mark.parametrize("title", [None,"","   ","A","X"*201])
def test_invalid_title_reports_field_without_insert(client,db_session,creation_data,title):
    users,project,headers=creation_data
    body=payload(users)
    if title is None:
        body.pop("title")
    else:
        body["title"]=title
    before=task_state(db_session)
    response=client.post(f"/api/v1/projects/{project.id}/tasks",headers=headers["admin"],json=body)
    assert_error(response,422,"VALIDATION_ERROR")
    assert "title" in response.json()["error"]["fields"]
    assert task_state(db_session) == before


@requires_creation
@pytest.mark.parametrize("case", ["reversed_dates","outside_assignee","missing_assignee"])
def test_invalid_creation_does_not_mutate_existing_tasks(client,db_session,creation_data,case):
    users,project,headers=creation_data
    db_session.add(Task(project_id=project.id,title="Existing sentinel",created_by_id=users["admin"].id))
    db_session.commit()
    body=payload(users)
    if case == "reversed_dates":
        body["due_date"]="2026-10-23"
        code="INVALID_DATE_RANGE"
    else:
        body["assignee_id"]=users["outsider"].id if case == "outside_assignee" else 999999
        code="ASSIGNEE_NOT_MEMBER"
    before=task_state(db_session)
    response=client.post(f"/api/v1/projects/{project.id}/tasks",headers=headers["admin"],json=body)
    assert_error(response,400,code)
    if case == "reversed_dates":
        assert "Teslim tarihi" in response.json()["error"]["message"]
    assert task_state(db_session) == before


@requires_creation
@pytest.mark.parametrize("actor", ["anonymous","invalid_token","outsider","outside_admin"])
def test_creation_requires_identity_and_project_membership(client,db_session,creation_data,actor):
    users,project,headers=creation_data
    auth={} if actor == "anonymous" else {"Authorization":"Bearer invalid-token"} if actor == "invalid_token" else headers[actor]
    before=task_state(db_session)
    response=client.post(f"/api/v1/projects/{project.id}/tasks",headers=auth,json=payload(users))
    assert_error(response,401 if actor in ("anonymous","invalid_token") else 403,
                 "UNAUTHORIZED" if actor in ("anonymous","invalid_token") else "PROJECT_ACCESS_DENIED")
    assert task_state(db_session) == before


@requires_creation
def test_nonexistent_project_does_not_create_task(client,db_session,creation_data):
    users,_,headers=creation_data
    before=task_state(db_session)
    response=client.post("/api/v1/projects/999999/tasks",headers=headers["admin"],json=payload(users))
    assert_error(response,404,"PROJECT_NOT_FOUND")
    assert task_state(db_session) == before


@requires_creation
def test_optional_fields_may_be_omitted(client,db_session,creation_data):
    _,project,headers=creation_data
    response=client.post(f"/api/v1/projects/{project.id}/tasks",headers=headers["admin"],json={"title":"Only title"})
    assert response.status_code == 201
    task=db_session.get(Task,response.json()["id"])
    assert task.project_id == project.id
    assert task.status == TaskStatus.TODO
    assert task.assignee_id is None


@requires_creation
def test_member_cannot_create_task_in_current_sprint(client,db_session,creation_data):
    # Owner's #149 explicitly defers pending suggestions to US-030 / Sprint 8.
    # Therefore this Sprint 4 acceptance requires 403, not the future 201 flow.
    users,project,headers=creation_data
    before=task_state(db_session)
    response=client.post(f"/api/v1/projects/{project.id}/tasks",headers=headers["member"],
                         json=payload(users) | {"assignee_id":users["admin"].id})
    assert_error(response,403,"FORBIDDEN")
    assert task_state(db_session) == before


@pytest.mark.parametrize("due", [date(2026,10,24),date(2026,10,25)])
def test_model_roundtrip_fields_and_non_reversed_date_boundary(db_session,creation_data,due):
    """Storage-only: never counted as successful task creation API acceptance."""
    users,project,_=creation_data
    task=Task(project_id=project.id,title="Türkçe alanlar",description="Ölçüm / QA",
              assignee_id=users["member"].id,created_by_id=users["admin"].id,
              start_date=date(2026,10,24),due_date=due)
    db_session.add(task)
    db_session.commit()
    task_id=task.id
    db_session.expire_all()
    loaded=db_session.get(Task,task_id)
    assert (loaded.title,loaded.description,loaded.assignee_id,loaded.start_date,loaded.due_date) == (
        "Türkçe alanlar","Ölçüm / QA",users["member"].id,date(2026,10,24),due)
    assert loaded.status == TaskStatus.TODO
