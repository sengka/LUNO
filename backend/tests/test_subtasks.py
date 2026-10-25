"""Alt görev ekleme testleri (US-033, FR-038, FR-039, sözleşme 6.10, #167)."""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Label, Project, ProjectMember, Task, TaskStatus, User

PASSWORD = "Password123"


def register(client: TestClient, email: str, db: Session, role: str = "EKIP_UYESI"):
    response = client.post(
        "/api/v1/auth/register",
        json={"full_name": email.split("@")[0].title(), "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    user_id = response.json()["id"]
    if role != "EKIP_UYESI":
        db.get(User, user_id).role = role
        db.commit()
    token = client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD}).json()[
        "access_token"
    ]
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def setup(client: TestClient, db_session: Session):
    admin_id, admin = register(client, "yonetici@ornek.com", db_session, "YONETICI")
    member_id, member = register(client, "uye@ornek.com", db_session)
    outsider_id, outsider = register(client, "disari@ornek.com", db_session)

    project = Project(
        name="Mobil Uygulama", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1)
    )
    other = Project(name="Web Sitesi", start_date=date(2026, 10, 1), end_date=date(2026, 12, 1))
    db_session.add_all([project, other])
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin_id),
            ProjectMember(project_id=project.id, user_id=member_id),
            ProjectMember(project_id=other.id, user_id=outsider_id),
        ]
    )
    parent = Task(project_id=project.id, title="Giriş ekranı", status=TaskStatus.IN_PROGRESS)
    db_session.add(parent)
    db_session.commit()
    return {
        "project": project,
        "other": other,
        "parent": parent,
        "admin": admin,
        "admin_id": admin_id,
        "member": member,
        "member_id": member_id,
        "outsider": outsider,
        "outsider_id": outsider_id,
    }


def url(task_id: int) -> str:
    return f"/api/v1/tasks/{task_id}/subtasks"


def test_admin_adds_subtask(client, setup, db_session):
    label = Label(project_id=setup["project"].id, name="frontend", color="#3A4CA0")
    db_session.add(label)
    db_session.commit()

    response = client.post(
        url(setup["parent"].id),
        headers=setup["admin"],
        json={
            "title": "Form tasarımı",
            "description": "Giriş formu",
            "assignee_id": setup["member_id"],
            "start_date": "2026-10-26",
            "due_date": "2026-10-28",
            "priority": "ORTA",
            "story_points": 2,
            "label_ids": [label.id],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["parent_id"] == setup["parent"].id
    assert body["project_id"] == setup["project"].id
    assert body["status"] == "TODO"
    assert body["priority"] == "ORTA"  # FR-039: alt göreve öncelik verilebilir
    assert body["story_points"] == 2
    assert body["assignee"]["id"] == setup["member_id"]
    assert body["created_by"]["id"] == setup["admin_id"]
    assert body["labels"] == [{"id": label.id, "name": "frontend", "color": "#3A4CA0"}]
    assert body["subtask_count"] == 0


def test_member_subtask_waits_for_approval(client, setup, db_session):
    """FR-026: ekip üyesinin eklediği görev ONAY_BEKLIYOR olur, atama yok sayılır."""
    response = client.post(
        url(setup["parent"].id),
        headers=setup["member"],
        json={"title": "Hata mesajları", "assignee_id": setup["member_id"]},
    )
    assert response.status_code == 201
    assert response.json()["status"] == "ONAY_BEKLIYOR"
    assert response.json()["assignee"] is None


def test_parent_counts_subtasks(client, setup, db_session):
    """Ana görevin subtask_count ve subtask_done_count alanları alt görevleri sayar."""
    parent = setup["parent"]
    first = client.post(url(parent.id), headers=setup["admin"], json={"title": "Birinci"}).json()
    client.post(url(parent.id), headers=setup["admin"], json={"title": "İkinci"})
    db_session.get(Task, first["id"]).status = TaskStatus.DONE
    db_session.commit()

    response = client.patch(
        f"/api/v1/tasks/{parent.id}/status", headers=setup["admin"], json={"status": "IN_PROGRESS"}
    )
    assert response.json()["subtask_count"] == 2
    assert response.json()["subtask_done_count"] == 1


def test_nested_subtask_rejected(client, setup, db_session):
    child = client.post(
        url(setup["parent"].id), headers=setup["admin"], json={"title": "Alt"}
    ).json()
    response = client.post(url(child["id"]), headers=setup["admin"], json={"title": "Alt-alt"})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "NESTED_SUBTASK_NOT_ALLOWED"
    assert response.json()["error"]["message"] == "Alt görevlere alt görev eklenemez."
    assert db_session.query(Task).count() == 2


def test_missing_parent(client, setup):
    response = client.post(url(9999), headers=setup["admin"], json={"title": "Görev"})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_non_member_cannot_add_subtask(client, setup, db_session):
    response = client.post(
        url(setup["parent"].id), headers=setup["outsider"], json={"title": "Görev"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    assert db_session.query(Task).count() == 1


def test_requires_login(client, setup):
    assert client.post(url(setup["parent"].id), json={"title": "Görev"}).status_code == 401


def test_due_date_before_start_rejected(client, setup):
    """FR-025"""
    response = client.post(
        url(setup["parent"].id),
        headers=setup["admin"],
        json={"title": "Görev", "start_date": "2026-10-28", "due_date": "2026-10-26"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_DATE_RANGE"
    assert response.json()["error"]["message"] == "Teslim tarihi başlangıç tarihinden önce olamaz."


def test_assignee_must_be_member(client, setup):
    response = client.post(
        url(setup["parent"].id),
        headers=setup["admin"],
        json={"title": "Görev", "assignee_id": setup["outsider_id"]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "ASSIGNEE_NOT_MEMBER"


def test_label_from_another_project_rejected(client, setup, db_session):
    foreign = Label(project_id=setup["other"].id, name="başka", color="#000000")
    db_session.add(foreign)
    db_session.commit()
    response = client.post(
        url(setup["parent"].id),
        headers=setup["admin"],
        json={"title": "Görev", "label_ids": [foreign.id]},
    )
    assert response.status_code == 422
    assert "label_ids" in response.json()["error"]["fields"]


@pytest.mark.parametrize(
    "body",
    [
        {"title": ""},
        {"title": "x"},
        {"title": "   "},
        {"title": "x" * 201},
        {"title": "Görev", "story_points": 4},
        {"title": "Görev", "story_points": 21},
        {"title": "Görev", "priority": "COK_YUKSEK"},
        {},
    ],
)
def test_invalid_body_rejected(client, setup, body):
    """FR-025 (başlık zorunlu), FR-036 (Fibonacci), FR-035 (öncelik değerleri)."""
    response = client.post(url(setup["parent"].id), headers=setup["admin"], json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_deleting_parent_deletes_subtasks(client, setup, db_session):
    client.post(url(setup["parent"].id), headers=setup["admin"], json={"title": "Alt"})
    db_session.delete(db_session.get(Task, setup["parent"].id))
    db_session.commit()
    assert db_session.query(Task).count() == 0
