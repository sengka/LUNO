"""Yorum API'si testleri (US-020, FR-050, sözleşme 8.5 ve 8.6, #202)."""

from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Project, ProjectMember, Task, User
from app.models.enums import Priority, TaskStatus

PASSWORD = "Password123"


def register(client: TestClient, email: str, role: str = "EKIP_UYESI", db: Session | None = None):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": email.split("@")[0].title(), "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    if role != "EKIP_UYESI":
        user = db.get(User, user_id)
        user.role = role
        db.commit()
    token = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return user_id, {"Authorization": f"Bearer {token}"}


def make_project_and_task(db: Session, member_ids: list[int]) -> tuple[Project, Task]:
    project = Project(name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db.add(project)
    db.flush()
    for user_id in member_ids:
        db.add(ProjectMember(project_id=project.id, user_id=user_id))

    task = Task(
        project_id=project.id,
        title="Giriş ekranı",
        status=TaskStatus.IN_PROGRESS,
        priority=Priority.ORTA,
        story_points=3,
        created_by_id=member_ids[0],
    )
    db.add(task)
    db.commit()
    db.refresh(project)
    db.refresh(task)
    return project, task


@pytest.fixture
def setup_comments(client: TestClient, db_session: Session):
    admin_id, admin_headers = register(client, "admin@ornek.com", "YONETICI", db_session)
    member_id, member_headers = register(client, "uye@ornek.com", "EKIP_UYESI", db_session)
    outsider_id, outsider_headers = register(client, "disari@ornek.com", "EKIP_UYESI", db_session)

    project, task = make_project_and_task(db_session, [admin_id, member_id])

    return {
        "project": project,
        "task": task,
        "admin_id": admin_id,
        "admin_headers": admin_headers,
        "member_id": member_id,
        "member_headers": member_headers,
        "outsider_id": outsider_id,
        "outsider_headers": outsider_headers,
    }


def test_create_task_comment_success(client: TestClient, setup_comments: dict):
    task = setup_comments["task"]
    headers = setup_comments["member_headers"]

    payload = {"body": "API hazır, ekranı bağlayabilirsin."}
    response = client.post(f"/api/v1/tasks/{task.id}/comments", json=payload, headers=headers)

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["id"] is not None
    assert data["body"] == "API hazır, ekranı bağlayabilirsin."
    assert data["task_id"] == task.id
    assert data["file_id"] is None
    assert data["author"]["id"] == setup_comments["member_id"]
    assert data["author"]["full_name"] == "Uye"
    assert "created_at" in data


def test_list_task_comments_order_and_pagination(client: TestClient, setup_comments: dict):
    task = setup_comments["task"]
    headers = setup_comments["member_headers"]

    # 3 yorum ekleyelim
    bodies = ["İlk yorum", "İkinci yorum", "Üçüncü yorum"]
    for b in bodies:
        res = client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": b}, headers=headers)
        assert res.status_code == 201

    # Tümünü listele (eskiden yeniye)
    response = client.get(f"/api/v1/tasks/{task.id}/comments?page=1&limit=50", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["limit"] == 50
    assert len(data["items"]) == 3
    assert [item["body"] for item in data["items"]] == bodies

    # Sayfalama: limit=2
    p1 = client.get(f"/api/v1/tasks/{task.id}/comments?page=1&limit=2", headers=headers).json()
    assert len(p1["items"]) == 2
    assert p1["total"] == 3
    assert p1["items"][0]["body"] == "İlk yorum"
    assert p1["items"][1]["body"] == "İkinci yorum"

    # Sayfalama: page=2, limit=2
    p2 = client.get(f"/api/v1/tasks/{task.id}/comments?page=2&limit=2", headers=headers).json()
    assert len(p2["items"]) == 1
    assert p2["items"][0]["body"] == "Üçüncü yorum"


def test_comment_task_not_found(client: TestClient, setup_comments: dict):
    headers = setup_comments["member_headers"]

    res_post = client.post("/api/v1/tasks/99999/comments", json={"body": "Test"}, headers=headers)
    assert res_post.status_code == 404
    assert res_post.json()["error"]["code"] == "TASK_NOT_FOUND"

    res_get = client.get("/api/v1/tasks/99999/comments", headers=headers)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_comment_project_access_denied(client: TestClient, setup_comments: dict):
    task = setup_comments["task"]
    outsider_headers = setup_comments["outsider_headers"]

    res_post = client.post(
        f"/api/v1/tasks/{task.id}/comments", json={"body": "Yetkisiz yorum"}, headers=outsider_headers
    )
    assert res_post.status_code == 403
    assert res_post.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"

    res_get = client.get(f"/api/v1/tasks/{task.id}/comments", headers=outsider_headers)
    assert res_get.status_code == 403
    assert res_get.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_comment_unauthenticated(client: TestClient, setup_comments: dict):
    task = setup_comments["task"]

    res_post = client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": "Giriş yapmadım"})
    assert res_post.status_code == 401
    assert res_post.json()["error"]["code"] == "UNAUTHORIZED"

    res_get = client.get(f"/api/v1/tasks/{task.id}/comments")
    assert res_get.status_code == 401
    assert res_get.json()["error"]["code"] == "UNAUTHORIZED"


def test_comment_validation_rules(client: TestClient, setup_comments: dict):
    task = setup_comments["task"]
    headers = setup_comments["member_headers"]

    # Boş gövde
    res1 = client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": ""}, headers=headers)
    assert res1.status_code == 422

    # Sadece boşluk
    res2 = client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": "   "}, headers=headers)
    assert res2.status_code == 422

    # 2000 karakterden uzun
    res3 = client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": "a" * 2001}, headers=headers)
    assert res3.status_code == 422


def test_comment_count_on_task_detail(client: TestClient, setup_comments: dict):
    task = setup_comments["task"]
    headers = setup_comments["member_headers"]

    # Başlangıçta 0
    t0 = client.get(f"/api/v1/tasks/{task.id}", headers=headers).json()
    assert t0["comment_count"] == 0

    # Yorum ekle
    client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": "Yorum 1"}, headers=headers)
    t1 = client.get(f"/api/v1/tasks/{task.id}", headers=headers).json()
    assert t1["comment_count"] == 1

    # İkinci yorum
    client.post(f"/api/v1/tasks/{task.id}/comments", json={"body": "Yorum 2"}, headers=headers)
    t2 = client.get(f"/api/v1/tasks/{task.id}", headers=headers).json()
    assert t2["comment_count"] == 2


def test_file_comments_missing_file(client: TestClient, setup_comments: dict):
    headers = setup_comments["member_headers"]

    res_get = client.get("/api/v1/files/42/comments", headers=headers)
    assert res_get.status_code == 404
    assert res_get.json()["error"]["code"] == "FILE_NOT_FOUND"

    res_post = client.post("/api/v1/files/42/comments", json={"body": "Dosya yorumu"}, headers=headers)
    assert res_post.status_code == 404
    assert res_post.json()["error"]["code"] == "FILE_NOT_FOUND"
