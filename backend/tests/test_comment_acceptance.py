"""US-020 / #204: real task and document comment routes, isolated SQLite data."""
from datetime import date, datetime, timezone

import pytest

from app.core.security import create_access_token
from app.models import Project, ProjectMember, Task, User
from app.models.comment import Comment
from app.models.file import ProjectFile


@pytest.fixture
def comments_case(db_session):
    users = {}
    for name, role in (("member", "EKIP_UYESI"), ("admin", "YONETICI"),
                       ("outsider", "EKIP_UYESI"), ("external_admin", "YONETICI")):
        user = User(full_name=name, email=f"comment-{name}@example.com",
                    hashed_password="unused-synthetic-fixture", role=role)
        db_session.add(user)
        db_session.flush()
        users[name] = user
    project = Project(name="Comments QA", start_date=date(2026, 11, 1),
                      end_date=date(2026, 12, 1))
    db_session.add(project)
    db_session.flush()
    for actor in ("member", "admin"):
        db_session.add(ProjectMember(project_id=project.id, user_id=users[actor].id))
    task = Task(project_id=project.id, title="Yorum kabul kontrolü")
    db_session.add(task)
    db_session.flush()
    file = ProjectFile(project_id=project.id, task_id=task.id, name="qa.txt",
                       storage_key="comments-qa.txt", size_bytes=1, mime_type="text/plain")
    db_session.add(file)
    db_session.commit()
    return {"users": users, "project": project, "task": task, "file": file,
            "headers": {name: {"Authorization": "Bearer " + create_access_token({"sub": str(u.id)})}
                        for name, u in users.items()}}


@pytest.fixture(params=["tasks", "files"])
def target(request, comments_case):
    kind = request.param
    obj = comments_case["task" if kind == "tasks" else "file"]
    return kind, obj.id, f"/api/v1/{kind}/{obj.id}/comments"


@pytest.mark.parametrize("actor", ["member", "admin"])
def test_create_list_author_target_and_persistence(client, db_session, comments_case, target, actor):
    kind, ident, url = target
    headers = comments_case["headers"][actor]
    assert client.get(url, headers=headers).json() == {"items": [], "total": 0, "page": 1, "limit": 50}
    text = "Türkçe çığöşü\n<script>alert('qa')</script>"
    response = client.post(url, headers=headers, json={"body": "  " + text + "  ",
        "author_id": comments_case["users"]["outsider"].id})
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["body"] == text
    assert data["author"]["id"] == comments_case["users"][actor].id
    assert data["author"]["full_name"] == actor
    assert data["task_id"] == (ident if kind == "tasks" else None)
    assert data["file_id"] == (ident if kind == "files" else None)
    datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    db_session.expire_all()
    assert db_session.get(Comment, data["id"]).body == text
    assert client.get(url, headers=headers).json()["items"] == [data]


@pytest.mark.parametrize("body", ["a", "ş" * 2000])
def test_inclusive_length_boundaries(client, comments_case, target, body):
    response = client.post(target[2], headers=comments_case["headers"]["member"], json={"body": body})
    assert response.status_code == 201, response.text
    assert response.json()["body"] == body


@pytest.mark.parametrize("payload", [{}, {"body": None}, {"body": 12}, {"body": ""},
    {"body": " \t\n\u00a0"}, {"body": "a" * 2001}])
def test_invalid_body_creates_no_comment(client, db_session, comments_case, target, payload):
    response = client.post(target[2], headers=comments_case["headers"]["member"], json=payload)
    assert response.status_code == 422, response.text
    assert db_session.query(Comment).count() == 0


@pytest.mark.parametrize("actor", [None, "outsider", "external_admin"])
@pytest.mark.parametrize("method", ["get", "post"])
def test_authentication_and_membership(client, db_session, comments_case, target, actor, method):
    headers = comments_case["headers"].get(actor, {})
    kwargs = {"json": {"body": "denied"}} if method == "post" else {}
    response = getattr(client, method)(target[2], headers=headers, **kwargs)
    assert response.status_code == (401 if actor is None else 403), response.text
    assert response.json()["error"]["code"] == ("UNAUTHORIZED" if actor is None else "PROJECT_ACCESS_DENIED")
    assert db_session.query(Comment).count() == 0


@pytest.mark.parametrize("method", ["get", "post"])
def test_missing_target(client, comments_case, target, method):
    kwargs = {"json": {"body": "missing"}} if method == "post" else {}
    response = getattr(client, method)(f"/api/v1/{target[0]}/999999/comments",
                                     headers=comments_case["headers"]["member"], **kwargs)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == ("TASK_NOT_FOUND" if target[0] == "tasks" else "FILE_NOT_FOUND")


@pytest.mark.parametrize("query", ["page=0", "page=-1", "limit=0", "limit=101", "page=x"])
def test_invalid_pagination(client, comments_case, target, query):
    assert client.get(target[2] + "?" + query,
                      headers=comments_case["headers"]["member"]).status_code == 422


def test_stable_order_pagination_and_target_isolation(client, db_session, comments_case, target):
    kind, ident, url = target
    timestamp = datetime(2026, 11, 1, tzinfo=timezone.utc)
    for text in ("one", "two", "three"):
        db_session.add(Comment(body=text, author_id=comments_case["users"]["member"].id,
            task_id=ident if kind == "tasks" else None,
            file_id=ident if kind == "files" else None, created_at=timestamp))
    # A comment on the other target must not leak into this list or its total.
    db_session.add(Comment(body="other", author_id=comments_case["users"]["member"].id,
        task_id=comments_case["task"].id if kind == "files" else None,
        file_id=comments_case["file"].id if kind == "tasks" else None))
    db_session.commit()
    headers = comments_case["headers"]["member"]
    pages = [client.get(url + f"?page={p}&limit=2", headers=headers).json() for p in (1, 2, 3)]
    assert all(p["total"] == 3 for p in pages)
    assert [[c["body"] for c in p["items"]] for p in pages] == [["one", "two"], ["three"], []]


def test_removed_member_immediately_loses_read_and_write(client, db_session, comments_case, target):
    user_id = comments_case["users"]["member"].id
    db_session.query(ProjectMember).filter_by(project_id=comments_case["project"].id,
                                             user_id=user_id).delete()
    db_session.commit()
    headers = comments_case["headers"]["member"]
    assert client.get(target[2], headers=headers).status_code == 403
    assert client.post(target[2], headers=headers, json={"body": "denied"}).status_code == 403
    assert db_session.query(Comment).count() == 0
