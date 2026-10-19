"""US-010 / #115: invitation boundaries and real membership API acceptance."""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.api.v1 import invites
from app.core.security import create_access_token
from app.main import app
from app.models.project import Project
from app.models.project_invite import ProjectInvite
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User


@pytest.fixture
def membership_data(db_session):
    users = {}
    for name, role in (("owner", "YONETICI"), ("member", "EKIP_UYESI"),
                       ("new", "EKIP_UYESI"), ("admin", "YONETICI")):
        user = User(full_name=f"QA {name}", email=f"{name}@example.com",
                    hashed_password="not-used-in-token-tests", role=role)
        db_session.add(user)
        users[name] = user
    db_session.commit()
    projects = []
    for name in ("A", "B"):
        project = Project(name=f"QA Project {name}", start_date=date(2026,10,1),
                          end_date=date(2026,12,1), created_by_id=users["owner"].id)
        db_session.add(project)
        db_session.commit()
        projects.append(project)
    for project in projects:
        for name in ("owner", "member"):
            db_session.add(ProjectMember(project_id=project.id, user_id=users[name].id))
    db_session.commit()
    headers = {name: {"Authorization": "Bearer " + create_access_token({"sub": str(u.id)})}
               for name,u in users.items()}
    return users, projects, headers


def state(db):
    return (
        [(m.project_id,m.user_id,m.technical_role) for m in db.query(ProjectMember).order_by(ProjectMember.project_id,ProjectMember.user_id)],
        [(u.id,u.role) for u in db.query(User).order_by(User.id)],
        [(t.id,t.project_id,t.assignee_id) for t in db.query(Task).order_by(Task.id)],
        [(i.id,i.project_id,i.token) for i in db.query(ProjectInvite).order_by(ProjectInvite.id)],
    )


def invite_token(client, project, headers):
    response = client.post(f"/api/v1/projects/{project.id}/invites", headers=headers)
    assert response.status_code == 201
    return response.json()["invite_url"].rsplit("/",1)[-1]


def error(response, status, code):
    assert response.status_code == status
    assert response.json()["error"]["code"] == code


@pytest.mark.parametrize("delta,expected", [(-1,400),(0,400),(1,200)])
def test_invite_exact_expiry_boundary(client, db_session, membership_data, monkeypatch, delta, expected):
    users, (project,_), headers = membership_data
    now = datetime(2030,1,1,12,0,0,tzinfo=timezone.utc)
    class FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz else now.replace(tzinfo=None)
    monkeypatch.setattr(invites,"datetime",FrozenDatetime)
    db_session.add(ProjectInvite(token="boundary",project_id=project.id,
        created_by_id=users["owner"].id,expires_at=now+timedelta(seconds=delta)))
    db_session.commit()
    before = state(db_session)
    response = client.post("/api/v1/invites/boundary/accept",headers=headers["new"])
    assert response.status_code == expected
    if expected == 400:
        error(response,400,"INVITE_INVALID")
        assert response.json()["error"]["message"] == "Davet bağlantısı geçersiz veya süresi dolmuş."
        assert state(db_session) == before
    else:
        assert db_session.query(ProjectMember).filter_by(project_id=project.id,user_id=users["new"].id).count() == 1


@pytest.mark.parametrize("authorization", [None,"Bearer invalid-token"])
def test_valid_invite_requires_identity_without_consumption(client,db_session,membership_data,authorization):
    _,(project,_),headers = membership_data
    token = invite_token(client,project,headers["owner"])
    before = state(db_session)
    response = client.post(f"/api/v1/invites/{token}/accept",headers={} if authorization is None else {"Authorization":authorization})
    error(response,401,"UNAUTHORIZED")
    assert state(db_session) == before
    assert client.post(f"/api/v1/invites/{token}/accept",headers=headers["new"]).status_code == 200


def test_deleted_project_invite_cannot_join(client,db_session,membership_data):
    _,(project,_),headers = membership_data
    token = invite_token(client,project,headers["owner"])
    db_session.delete(project)
    db_session.commit()
    before = state(db_session)
    error(client.post(f"/api/v1/invites/{token}/accept",headers=headers["new"]),400,"INVITE_INVALID")
    assert state(db_session) == before


def test_invite_scope_and_role_cannot_be_overridden_by_request(client,db_session,membership_data):
    users,(a,b),headers = membership_data
    token = invite_token(client,a,headers["owner"])
    response = client.post(f"/api/v1/invites/{token}/accept",headers=headers["new"],
                           json={"project_id":b.id,"user_id":users["admin"].id,"role":"YONETICI"})
    assert response.status_code == 200
    assert response.json()["id"] == a.id
    db_session.expire_all()
    assert users["new"].role == "EKIP_UYESI"
    assert db_session.query(ProjectMember).filter_by(project_id=a.id,user_id=users["new"].id).count() == 1
    assert db_session.query(ProjectMember).filter_by(project_id=b.id,user_id=users["new"].id).count() == 0
    assert db_session.query(ProjectMember).filter_by(user_id=users["admin"].id).count() == 0


def test_member_admin_can_invite_without_owning_project(client,db_session,membership_data):
    users,(project,_),headers = membership_data
    db_session.add(ProjectMember(project_id=project.id,user_id=users["admin"].id))
    db_session.commit()
    token = invite_token(client,project,headers["admin"])
    assert db_session.query(ProjectInvite).filter_by(token=token).one().created_by_id == users["admin"].id


def test_invite_replay_preserves_membership_and_roles(client,db_session,membership_data):
    users,(project,_),headers = membership_data
    token = invite_token(client,project,headers["owner"])
    assert client.post(f"/api/v1/invites/{token}/accept",headers=headers["new"]).status_code == 200
    before = state(db_session)
    error(client.post(f"/api/v1/invites/{token}/accept",headers=headers["new"]),409,"ALREADY_MEMBER")
    assert state(db_session) == before
    assert users["new"].role == "EKIP_UYESI"


# These require the actual product routes. A 404 is never a passing membership test.
MEMBERS = "/api/v1/projects/{project_id}/members"
REMOVE = MEMBERS + "/{user_id}"
REQUIRED = {
    "list": [(MEMBERS,"get")], "email_add": [(MEMBERS,"post")],
    "unknown_email": [(MEMBERS,"post")], "invalid_email": [(MEMBERS,"post")],
    "remove": [(REMOVE,"delete")], "self_remove": [(REMOVE,"delete")],
    "unknown_member": [(REMOVE,"delete")], "member_add": [(MEMBERS,"post")],
    "member_remove": [(REMOVE,"delete")], "outsider_admin": [(MEMBERS,"post")],
    "removed_access": [(REMOVE,"delete"),("/api/v1/projects/{project_id}","get")],
    "anonymous": [(MEMBERS,"post")],
}


@pytest.mark.parametrize("case", [pytest.param(case,id=case,marks=pytest.mark.skipif(
    any(method not in app.openapi()["paths"].get(path,{}) for path,method in required),
    reason="US-010 blocked: real membership/project API missing (#112, #140); report #115",
)) for case,required in REQUIRED.items()])
def test_membership_real_route_acceptance(client,db_session,membership_data,case):
    users,(a,b),headers = membership_data
    member_id = users["member"].id
    db_session.add_all([Task(project_id=a.id,title="A task",assignee_id=member_id),
                       Task(project_id=b.id,title="B task",assignee_id=member_id)])
    db_session.commit()
    before = state(db_session)
    url = f"/api/v1/projects/{a.id}/members"
    owner = headers["owner"]
    if case == "list":
        response = client.get(url,headers=headers["member"])
        assert response.status_code == 200
        assert {row["user"]["id"] for row in response.json()} == {users["owner"].id,member_id}
    elif case == "email_add":
        body={"email":users["new"].email,"technical_role":"QA"}
        assert client.post(url,headers=owner,json=body).status_code == 201
        row=db_session.query(ProjectMember).filter_by(project_id=a.id,user_id=users["new"].id).one()
        assert row.technical_role == "QA"
        added=state(db_session)
        error(client.post(url,headers=owner,json=body),409,"ALREADY_MEMBER")
        assert state(db_session) == added
    elif case in ("remove","removed_access"):
        assert client.delete(url+f"/{member_id}",headers=owner).status_code == 204
        db_session.expire_all()
        assert db_session.query(ProjectMember).filter_by(project_id=a.id,user_id=member_id).count() == 0
        assert db_session.query(ProjectMember).filter_by(project_id=b.id,user_id=member_id).count() == 1
        assert db_session.query(Task).filter_by(project_id=a.id).one().assignee_id is None
        assert db_session.query(Task).filter_by(project_id=b.id).one().assignee_id == member_id
        if case == "removed_access":
            error(client.get(f"/api/v1/projects/{a.id}",headers=headers["member"]),403,"PROJECT_ACCESS_DENIED")
    elif case in ("self_remove","unknown_member","member_remove"):
        target=users["owner"].id if case == "self_remove" else users["new"].id if case == "unknown_member" else member_id
        actor=headers["member"] if case == "member_remove" else owner
        code={"self_remove":(400,"CANNOT_REMOVE_SELF"),"unknown_member":(404,"MEMBER_NOT_FOUND"),"member_remove":(403,"FORBIDDEN")}[case]
        error(client.delete(url+f"/{target}",headers=actor),*code)
        assert state(db_session) == before
    else:
        email="missing@example.com" if case == "unknown_email" else "invalid" if case == "invalid_email" else users["new"].email
        actor={} if case == "anonymous" else headers["member"] if case == "member_add" else headers["admin"] if case == "outsider_admin" else owner
        code={"unknown_email":(404,"USER_NOT_FOUND"),"invalid_email":(422,"VALIDATION_ERROR"),"member_add":(403,"FORBIDDEN"),"outsider_admin":(403,"PROJECT_ACCESS_DENIED"),"anonymous":(401,"UNAUTHORIZED")}[case]
        error(client.post(url,headers=actor,json={"email":email}),*code)
        assert state(db_session) == before
