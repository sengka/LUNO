"""#253 (#219 madde 5 ve düşük önemli bulgular) için regresyon testleri.

1. subtask_count / subtask_done_count yalnızca aktif alt görevleri sayar (sözleşme 1.3).
2. Veritabanı benzersizlik hatası (IntegrityError) 500 yerine 409 döner.
3. page parametresinin üst sınırı var; çok büyük değer 500 yerine 422 döner.
4. Etiket tekrar kontrolü Türkçe karakterlerde de çalışır.
"""

from datetime import date

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.v1 import labels as labels_module
from app.api.v1.labels import label_key
from app.core.pagination import MAX_PAGE
from app.core.security import create_access_token
from app.main import app
from app.models import (
    Label,
    Project,
    ProjectFile,
    ProjectMember,
    Task,
    TaskStatus,
    User,
)


def make_user(db: Session, email: str, role: str = "EKIP_UYESI"):
    user = User(full_name=email.split("@")[0].title(), email=email, hashed_password="x", role=role)
    db.add(user)
    db.flush()
    return user, {"Authorization": f"Bearer {create_access_token({'sub': str(user.id)})}"}


@pytest.fixture
def case(db_session: Session):
    db = db_session
    admin, admin_h = make_user(db, "yonetici@ornek.com", "YONETICI")
    member, member_h = make_user(db, "uye@ornek.com")
    project = Project(name="Hata Projesi", start_date=date(2026, 11, 1), end_date=date(2026, 12, 31),
                      created_by_id=admin.id)
    db.add(project)
    db.flush()
    for user in (admin, member):
        db.add(ProjectMember(project_id=project.id, user_id=user.id))
    task = Task(project_id=project.id, title="Ana görev", status=TaskStatus.IN_PROGRESS,
                start_date=date(2026, 11, 2), due_date=date(2026, 11, 20))
    db.add(task)
    db.flush()
    file = ProjectFile(project_id=project.id, name="a.txt", storage_key="k/a.txt", size_bytes=1,
                       mime_type="text/plain")
    db.add(file)
    db.commit()
    return {"db": db, "admin": admin, "member": member, "project": project, "task": task,
            "file": file, "h": {"admin": admin_h, "member": member_h}}


def add_subtask(db: Session, parent: Task, status: TaskStatus) -> Task:
    sub = Task(project_id=parent.project_id, parent_id=parent.id, title=f"Alt {status.value}",
               status=status)
    db.add(sub)
    db.commit()
    return sub


# --- 1. Alt görev sayımı (#219 madde 5) ------------------------------------------------------


def task_counts(client: TestClient, case: dict) -> tuple[int, int]:
    body = client.get(f"/api/v1/tasks/{case['task'].id}", headers=case["h"]["member"]).json()
    return body["subtask_count"], body["subtask_done_count"]


def test_pending_subtask_does_not_lower_progress(client, case):
    """#219: İki alt görevi de bitmiş ana görev, alt görev önerisiyle %100'den %66'ya düşmemeli."""
    db, task = case["db"], case["task"]
    add_subtask(db, task, TaskStatus.DONE)
    add_subtask(db, task, TaskStatus.DONE)
    assert task_counts(client, case) == (2, 2)
    add_subtask(db, task, TaskStatus.ONAY_BEKLIYOR)
    assert task_counts(client, case) == (2, 2)


def test_rejected_subtask_is_not_counted(client, case):
    db, task = case["db"], case["task"]
    add_subtask(db, task, TaskStatus.DONE)
    add_subtask(db, task, TaskStatus.TODO)
    add_subtask(db, task, TaskStatus.REDDEDILDI)
    assert task_counts(client, case) == (2, 1)


def test_all_active_statuses_are_counted(client, case):
    db, task = case["db"], case["task"]
    for status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING, TaskStatus.DONE):
        add_subtask(db, task, status)
    assert task_counts(client, case) == (4, 1)


def test_only_inactive_subtasks_counts_zero(client, case):
    db, task = case["db"], case["task"]
    add_subtask(db, task, TaskStatus.ONAY_BEKLIYOR)
    add_subtask(db, task, TaskStatus.REDDEDILDI)
    assert task_counts(client, case) == (0, 0)


def test_approving_subtask_adds_it_to_count(client, case):
    db, task = case["db"], case["task"]
    add_subtask(db, task, TaskStatus.DONE)
    pending = add_subtask(db, task, TaskStatus.ONAY_BEKLIYOR)
    assert task_counts(client, case) == (1, 1)
    pending.status = TaskStatus.TODO
    db.commit()
    assert task_counts(client, case) == (2, 1)


def test_task_list_uses_same_counts(client, case):
    db, task = case["db"], case["task"]
    add_subtask(db, task, TaskStatus.DONE)
    add_subtask(db, task, TaskStatus.ONAY_BEKLIYOR)
    items = client.get(f"/api/v1/projects/{case['project'].id}/tasks", headers=case["h"]["member"]).json()["items"]
    parent = next(item for item in items if item["id"] == task.id)
    assert (parent["subtask_count"], parent["subtask_done_count"]) == (1, 1)


# --- 2. IntegrityError → 409 ---------------------------------------------------------------


def test_concurrent_duplicate_label_returns_409(client, case, monkeypatch):
    """Ön kontrolü geçen iki eşzamanlı istekten ikincisi veritabanında takılır: 500 değil 409."""
    url = f"/api/v1/projects/{case['project'].id}/labels"
    first = client.post(url, headers=case["h"]["member"], json={"name": "backend"})
    assert first.status_code == 201
    # Eşzamanlılığı taklit et: ön kontrol diğer isteğin eklediği etiketi henüz görmemiş olsun.
    keys = iter(range(1000))
    monkeypatch.setattr(labels_module, "label_key", lambda name: f"farkli-{next(keys)}")
    second = client.post(url, headers=case["h"]["member"], json={"name": "backend"})
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "LABEL_EXISTS"
    assert case["db"].query(Label).filter(Label.project_id == case["project"].id).count() == 1
    # Oturum geri alındı; sonraki istekler çalışmaya devam eder.
    monkeypatch.undo()
    third = client.post(url, headers=case["h"]["member"], json={"name": "frontend"})
    assert third.status_code == 201


@pytest.fixture
def conflict_route():
    router = APIRouter()

    @router.get("/__test__/conflict")
    def conflict():
        raise IntegrityError("INSERT ...", {}, Exception("UNIQUE constraint failed"))

    app.include_router(router)
    yield
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", "") != "/__test__/conflict"]


def test_unhandled_integrity_error_returns_409_in_contract_format(conflict_route):
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/__test__/conflict", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "CONFLICT",
            "message": "Bu işlem başka bir işlemle çakıştı. Lütfen sayfayı yenileyip tekrar deneyin.",
            "fields": None,
            "details": None,
        }
    }
    # Hata CORS katmanının içinde yakalanır; tarayıcı yanıtı okuyabilir.
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


# --- 3. page üst sınırı ---------------------------------------------------------------------


def list_urls(case: dict) -> list[tuple[str, str]]:
    project_id = case["project"].id
    return [
        ("admin", "/api/v1/users"),
        ("member", "/api/v1/projects"),
        ("member", f"/api/v1/projects/{project_id}/tasks"),
        ("member", f"/api/v1/projects/{project_id}/files"),
        ("member", f"/api/v1/tasks/{case['task'].id}/comments"),
        ("member", f"/api/v1/files/{case['file'].id}/comments"),
    ]


@pytest.mark.parametrize("page", ["9999999999999999999", str(MAX_PAGE + 1)])
def test_too_large_page_returns_422(client, case, page):
    for who, url in list_urls(case):
        response = client.get(url, params={"page": page}, headers=case["h"][who])
        assert response.status_code == 422, (url, response.status_code, response.text)
        error = response.json()["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "page" in error["fields"]


def test_max_page_returns_empty_list(client, case):
    for who, url in list_urls(case):
        response = client.get(url, params={"page": MAX_PAGE, "limit": 100}, headers=case["h"][who])
        assert response.status_code == 200, (url, response.text)
        body = response.json()
        assert body["items"] == []
        assert body["page"] == MAX_PAGE


def test_page_zero_still_rejected(client, case):
    response = client.get("/api/v1/projects", params={"page": 0}, headers=case["h"]["member"])
    assert response.status_code == 422


# --- 4. Türkçe karakterli etiket adları ---------------------------------------------------------


@pytest.mark.parametrize("existing,duplicate", [
    ("Ödeme", "ödeme"),
    ("ödeme", "ÖDEME"),
    ("Çalışma", "ÇALIŞMA"),
    ("Güvenlik", "GÜVENLİK"),
    ("İzin", "izin"),
    ("IŞIK", "ışık"),
    ("Şirket", "şİrket"),
    ("frontend", "Frontend"),
    ("API", "api"),
    ("Ödeme", "  ödeme  "),
])
def test_turkish_label_duplicates_rejected(client, case, existing, duplicate):
    url = f"/api/v1/projects/{case['project'].id}/labels"
    assert client.post(url, headers=case["h"]["member"], json={"name": existing}).status_code == 201
    response = client.post(url, headers=case["h"]["member"], json={"name": duplicate})
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "LABEL_EXISTS"


@pytest.mark.parametrize("first,second", [("Ödeme", "Odeme"), ("Çalışma", "Calisma"), ("test", "tests")])
def test_different_labels_still_allowed(client, case, first, second):
    url = f"/api/v1/projects/{case['project'].id}/labels"
    assert client.post(url, headers=case["h"]["member"], json={"name": first}).status_code == 201
    assert client.post(url, headers=case["h"]["member"], json={"name": second}).status_code == 201


def test_same_name_allowed_in_other_project(client, case, db_session):
    other = Project(name="Diğer", start_date=date(2026, 11, 1), end_date=date(2026, 12, 31))
    db_session.add(other)
    db_session.flush()
    db_session.add(ProjectMember(project_id=other.id, user_id=case["member"].id))
    db_session.commit()
    headers = case["h"]["member"]
    assert client.post(f"/api/v1/projects/{case['project'].id}/labels", headers=headers,
                       json={"name": "Ödeme"}).status_code == 201
    assert client.post(f"/api/v1/projects/{other.id}/labels", headers=headers,
                       json={"name": "ödeme"}).status_code == 201


def test_label_list_sorted_case_insensitively(client, case):
    url = f"/api/v1/projects/{case['project'].id}/labels"
    for name in ("backend", "API", "Ödeme", "frontend", "Çalışma"):
        assert client.post(url, headers=case["h"]["member"], json={"name": name}).status_code == 201
    names = [label["name"] for label in client.get(url, headers=case["h"]["member"]).json()]
    assert names[:3] == ["API", "backend", "frontend"]
    assert set(names) == {"backend", "API", "Ödeme", "frontend", "Çalışma"}


def test_label_key_examples():
    assert label_key("Ödeme") == label_key("ödeme")
    assert label_key("İSTANBUL") == label_key("istanbul") == label_key("ıstanbul")
    assert label_key("Ödeme") != label_key("Odeme")
