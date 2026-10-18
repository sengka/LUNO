"""US-005 / #99: real routed authorization and post-denial data integrity.

Missing project/task routes are tracked as blocked acceptance scenarios in the
report; a 404 is deliberately never asserted as successful authorization.
"""
from datetime import date

import pytest
from app.core.security import create_access_token
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_invite import ProjectInvite
from app.models.user import User


@pytest.fixture
def access_data(db_session):
    users = {}
    for name, role in (("owner", "YONETICI"), ("member", "EKIP_UYESI"),
                       ("outsider", "EKIP_UYESI"), ("other_admin", "YONETICI")):
        user = User(full_name=f"QA {name}", email=f"{name}@example.com",
                    hashed_password="not-used-in-token-tests", role=role)
        db_session.add(user)
        users[name] = user
    db_session.commit()
    project = Project(name="QA Private Project", description="Private sentinel",
                      start_date=date(2026, 10, 1), end_date=date(2026, 12, 1),
                      created_by_id=users["owner"].id)
    db_session.add(project)
    db_session.commit()
    for name in ("owner", "member"):
        db_session.add(ProjectMember(project_id=project.id, user_id=users[name].id))
    db_session.commit()
    headers = {name: {"Authorization": f"Bearer {create_access_token({'sub': str(u.id)})}"}
               for name, u in users.items()}
    return users, project, headers


def snapshot(db):
    return (
        [(u.id, u.role) for u in db.query(User).order_by(User.id)],
        [(p.id, p.name, p.description) for p in db.query(Project).order_by(Project.id)],
        [(m.project_id, m.user_id) for m in db.query(ProjectMember).order_by(ProjectMember.project_id, ProjectMember.user_id)],
        [(i.id, i.token) for i in db.query(ProjectInvite).order_by(ProjectInvite.id)],
    )


def denied(response, code, message):
    assert response.status_code == 403
    assert response.json() == {"error": {"code": code, "message": message,
                                        "fields": None, "details": None}}
    assert "Private sentinel" not in response.text
    assert "QA Private Project" not in response.text


@pytest.mark.parametrize("actor", ["member", "outsider"])
@pytest.mark.parametrize("operation", ["users", "own_role", "other_role", "invite"])
def test_member_admin_actions_denied_without_writes(client, db_session, access_data, actor, operation):
    users, project, headers = access_data
    before = snapshot(db_session)
    if operation == "users":
        response = client.get("/api/v1/users?search=QA", headers=headers[actor])
    elif operation == "invite":
        response = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers[actor])
    else:
        target = users[actor] if operation == "own_role" else users["owner"]
        response = client.patch(f"/api/v1/users/{target.id}/role", headers=headers[actor],
                                json={"role": "YONETICI"})
    denied(response, "FORBIDDEN", "Bu işlem için yetkiniz yok.")
    db_session.expire_all()
    assert snapshot(db_session) == before


def test_admin_without_project_membership_cannot_invite(client, db_session, access_data):
    _, project, headers = access_data
    before = snapshot(db_session)
    response = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers["other_admin"])
    denied(response, "PROJECT_ACCESS_DENIED", "Bu projeye erişim yetkiniz yok.")
    assert snapshot(db_session) == before


def test_admin_member_positive_control_and_different_project_id(client, db_session, access_data):
    users, project, headers = access_data
    assert client.get("/api/v1/users", headers=headers["owner"]).status_code == 200
    assert client.post(f"/api/v1/projects/{project.id}/invites", headers=headers["owner"]).status_code == 201
    other = Project(name="Other project", start_date=date(2026,10,1),
                    end_date=date(2026,12,1), created_by_id=users["other_admin"].id)
    db_session.add(other)
    db_session.commit()
    before = snapshot(db_session)
    response = client.post(f"/api/v1/projects/{other.id}/invites", headers=headers["owner"])
    denied(response, "PROJECT_ACCESS_DENIED", "Bu projeye erişim yetkiniz yok.")
    assert snapshot(db_session) == before


def test_membership_revocation_applies_to_existing_token(client, db_session, access_data):
    users, project, headers = access_data
    assert client.post(f"/api/v1/projects/{project.id}/invites", headers=headers["owner"]).status_code == 201
    membership = db_session.query(ProjectMember).filter_by(project_id=project.id, user_id=users["owner"].id).one()
    db_session.delete(membership)
    db_session.commit()
    before = snapshot(db_session)
    denied(client.post(f"/api/v1/projects/{project.id}/invites", headers=headers["owner"]),
           "PROJECT_ACCESS_DENIED", "Bu projeye erişim yetkiniz yok.")
    assert snapshot(db_session) == before


def test_role_demotion_applies_to_existing_token(client, db_session, access_data):
    users, project, headers = access_data
    assert client.post(f"/api/v1/projects/{project.id}/invites", headers=headers["owner"]).status_code == 201
    # Setup-only demotion: verifies request-time DB authorization, not the role update endpoint.
    users["owner"].role = "EKIP_UYESI"
    db_session.commit()
    before = snapshot(db_session)
    denied(client.post(f"/api/v1/projects/{project.id}/invites", headers=headers["owner"]),
           "FORBIDDEN", "Bu işlem için yetkiniz yok.")
    assert snapshot(db_session) == before


@pytest.mark.parametrize("operation", ["users", "role", "invite"])
@pytest.mark.parametrize("authorization", [None, "Bearer invalid-token"])
def test_protected_routes_require_identity(client, db_session, access_data, operation, authorization):
    users, project, _ = access_data
    headers = {} if authorization is None else {"Authorization": authorization}
    before = snapshot(db_session)
    if operation == "users":
        response = client.get("/api/v1/users", headers=headers)
    elif operation == "role":
        response = client.patch(f"/api/v1/users/{users['member'].id}/role", headers=headers,
                                json={"role": "YONETICI"})
    else:
        response = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert snapshot(db_session) == before



# Acceptance probes activate automatically when their real product routes exist.
# Skips are explicit blockers, never evidence of successful access control.
from app.main import app
from app.models.task import Task

MISSING_ROUTE_CASES = [
    ("create", "post", "/api/v1/projects"),
    ("delete", "delete", "/api/v1/projects/{project_id}"),
    ("add_member", "post", "/api/v1/projects/{project_id}/members"),
    ("remove_member", "delete", "/api/v1/projects/{project_id}/members/{user_id}"),
    ("assign", "patch", "/api/v1/tasks/{task_id}/assignee"),
    ("detail_member", "get", "/api/v1/projects/{project_id}"),
    ("detail_admin", "get", "/api/v1/projects/{project_id}"),
]


@pytest.mark.parametrize("case,method,path", [
    pytest.param(case, method, path, id=case, marks=pytest.mark.skipif(
        method not in app.openapi()["paths"].get(path, {}),
        reason="US-005 acceptance blocked: product route missing; report #99 / existing project API bug #140",
    )) for case, method, path in MISSING_ROUTE_CASES
])
def test_remaining_real_route_acceptance(client, db_session, access_data, case, method, path):
    users, project, headers = access_data
    task = Task(project_id=project.id, title="QA task", assignee_id=users["owner"].id)
    db_session.add(task)
    db_session.commit()
    url = path.format(project_id=project.id, user_id=users["owner"].id, task_id=task.id)
    actor = "other_admin" if case == "detail_admin" else "outsider" if case == "detail_member" else "member"
    bodies = {
        "create": {"name": "Forbidden new project", "start_date": "2026-10-01", "end_date": "2026-12-01"},
        "add_member": {"email": users["outsider"].email},
        "assign": {"assignee_id": users["member"].id, "confirm_over_capacity": False},
    }
    before = snapshot(db_session)
    assignments = [(t.id, t.assignee_id) for t in db_session.query(Task).order_by(Task.id)]
    kwargs = {"headers": headers[actor]}
    if case in bodies:
        kwargs["json"] = bodies[case]
    response = client.request(method.upper(), url, **kwargs)
    code = "PROJECT_ACCESS_DENIED" if case.startswith("detail") else "FORBIDDEN"
    message = "Bu projeye erişim yetkiniz yok." if case.startswith("detail") else "Bu işlem için yetkiniz yok."
    denied(response, code, message)
    db_session.expire_all()
    assert snapshot(db_session) == before
    assert [(t.id, t.assignee_id) for t in db_session.query(Task).order_by(Task.id)] == assignments
