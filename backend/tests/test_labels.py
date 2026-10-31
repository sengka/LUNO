"""Etiket API'si ve görev etiketleri testleri (US-033, FR-037, sözleşme 6.11, #167)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Label, Project, ProjectMember, Task, User, task_labels

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


def make_project(db: Session, name: str, member_ids: list[int]) -> Project:
    project = Project(name=name, start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db.add(project)
    db.flush()
    for user_id in member_ids:
        db.add(ProjectMember(project_id=project.id, user_id=user_id))
    db.commit()
    return project


@pytest.fixture
def setup(client: TestClient, db_session: Session):
    admin_id, admin = register(client, "yonetici@ornek.com", "YONETICI", db_session)
    member_id, member = register(client, "uye@ornek.com")
    outsider_id, outsider = register(client, "disari@ornek.com")
    project = make_project(db_session, "Mobil Uygulama", [admin_id, member_id])
    other = make_project(db_session, "Web Sitesi", [admin_id, outsider_id])
    return {
        "project": project,
        "other": other,
        "admin": admin,
        "member": member,
        "member_id": member_id,
        "outsider": outsider,
    }


def labels_url(project_id: int) -> str:
    return f"/api/v1/projects/{project_id}/labels"


# --- POST /projects/{id}/labels -----------------------------------------------


def test_member_creates_label(client, setup):
    """Ekip üyesi de etiket oluşturabilir (sözleşme 6.11: proje üyesi)."""
    response = client.post(
        labels_url(setup["project"].id),
        headers=setup["member"],
        json={"name": "frontend", "color": "#3A4CA0"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "frontend"
    assert body["color"] == "#3A4CA0"
    assert set(body) == {"id", "name", "color"}


def test_color_is_optional(client, setup):
    response = client.post(
        labels_url(setup["project"].id), headers=setup["admin"], json={"name": "acil"}
    )
    assert response.status_code == 201
    assert response.json()["color"] == "#6B7280"


def test_name_is_trimmed(client, setup):
    response = client.post(
        labels_url(setup["project"].id), headers=setup["admin"], json={"name": "  backend  "}
    )
    assert response.status_code == 201
    assert response.json()["name"] == "backend"


@pytest.mark.parametrize("name", ["frontend", "Frontend", " FRONTEND "])
def test_duplicate_label_rejected(client, setup, name):
    """409 LABEL_EXISTS; büyük/küçük harf ve boşluk farkı aynı etiket sayılır."""
    url = labels_url(setup["project"].id)
    assert client.post(url, headers=setup["admin"], json={"name": "frontend"}).status_code == 201

    response = client.post(url, headers=setup["member"], json={"name": name})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LABEL_EXISTS"
    assert response.json()["error"]["message"] == "Bu etiket zaten var."


def test_same_name_allowed_in_another_project(client, setup):
    """Etiketler proje bazında tanımlanır."""
    body = {"name": "frontend"}
    assert (
        client.post(labels_url(setup["project"].id), headers=setup["admin"], json=body).status_code
        == 201
    )
    assert (
        client.post(labels_url(setup["other"].id), headers=setup["admin"], json=body).status_code
        == 201
    )


@pytest.mark.parametrize(
    "body",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 51},
        {"name": "renk", "color": "mavi"},
        {"name": "renk", "color": "#12345"},
        {},
    ],
)
def test_invalid_label_rejected(client, setup, body):
    response = client.post(labels_url(setup["project"].id), headers=setup["admin"], json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_non_member_cannot_create_label(client, setup, db_session):
    response = client.post(
        labels_url(setup["project"].id), headers=setup["outsider"], json={"name": "x"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert db_session.scalar(select(func.count()).select_from(Label)) == 0


def test_label_on_missing_project(client, setup):
    response = client.post(labels_url(9999), headers=setup["admin"], json={"name": "x"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_label_requires_login(client, setup):
    assert client.post(labels_url(setup["project"].id), json={"name": "x"}).status_code == 401
    assert client.get(labels_url(setup["project"].id)).status_code == 401


# --- GET /projects/{id}/labels ------------------------------------------------


def test_list_labels_sorted_and_project_scoped(client, setup):
    url = labels_url(setup["project"].id)
    for name in ("tasarım", "Backend", "acil"):
        client.post(url, headers=setup["admin"], json={"name": name})
    client.post(labels_url(setup["other"].id), headers=setup["admin"], json={"name": "başka proje"})

    response = client.get(url, headers=setup["member"])
    assert response.status_code == 200
    assert [label["name"] for label in response.json()] == ["acil", "Backend", "tasarım"]


def test_list_labels_empty(client, setup):
    response = client.get(labels_url(setup["project"].id), headers=setup["member"])
    assert response.status_code == 200
    assert response.json() == []


def test_non_member_cannot_list_labels(client, setup):
    response = client.get(labels_url(setup["project"].id), headers=setup["outsider"])
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


# --- Task yanıtında etiketler ------------------------------------------------


def test_task_response_includes_labels(client, setup, db_session):
    """Task nesnesindeki labels alanı (sözleşme 2. bölüm) gerçek etiketleri döner."""
    project = setup["project"]
    backend = Label(project_id=project.id, name="backend", color="#00AA00")
    acil = Label(project_id=project.id, name="acil", color="#FF0000")
    task = Task(project_id=project.id, title="Giriş API'si", assignee_id=setup["member_id"])
    task.labels = [backend, acil]
    db_session.add(task)
    db_session.commit()

    response = client.patch(
        f"/api/v1/tasks/{task.id}/status", headers=setup["member"], json={"status": "IN_PROGRESS"}
    )
    assert response.status_code == 200
    assert response.json()["labels"] == [
        {"id": acil.id, "name": "acil", "color": "#FF0000"},
        {"id": backend.id, "name": "backend", "color": "#00AA00"},
    ]


def test_task_response_labels_empty_by_default(client, setup, db_session):
    task = Task(project_id=setup["project"].id, title="Etiketsiz", assignee_id=setup["member_id"])
    db_session.add(task)
    db_session.commit()
    response = client.patch(
        f"/api/v1/tasks/{task.id}/status", headers=setup["member"], json={"status": "DONE"}
    )
    assert response.json()["labels"] == []


# --- Silme davranışları --------------------------------------------------------


def count(db, table):
    return db.scalar(select(func.count()).select_from(table))


def test_deleting_label_detaches_it_from_tasks(db_session, setup):
    project = setup["project"]
    label = Label(project_id=project.id, name="silinecek", color="#000000")
    task = Task(project_id=project.id, title="Görev", labels=[label])
    db_session.add(task)
    db_session.commit()

    db_session.delete(label)
    db_session.commit()
    db_session.expire_all()
    assert count(db_session, task_labels) == 0
    assert db_session.get(Task, task.id).labels == []  # görev silinmez


def test_deleting_task_removes_its_label_links(db_session, setup):
    project = setup["project"]
    label = Label(project_id=project.id, name="kalacak", color="#000000")
    task = Task(project_id=project.id, title="Görev", labels=[label])
    db_session.add(task)
    db_session.commit()

    db_session.delete(task)
    db_session.commit()
    assert count(db_session, task_labels) == 0
    assert count(db_session, Label) == 1  # etiket silinmez


def test_deleting_project_deletes_labels(db_session, setup):
    """FR-020: proje silinince etiketleri ve görev-etiket bağlantıları da silinir."""
    project = setup["project"]
    db_session.add(
        Task(
            project_id=project.id,
            title="Görev",
            labels=[Label(project_id=project.id, name="a", color="#000000")],
        )
    )
    db_session.commit()

    db_session.delete(project)
    db_session.commit()
    assert count(db_session, Label) == 0
    assert count(db_session, task_labels) == 0
