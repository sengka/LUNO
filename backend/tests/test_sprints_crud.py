"""US-040 Sprint API'leri testleri (#242; sözleşme 11.1 – 11.3)."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import Project, ProjectMember, Sprint, Task, TaskStatus, User


def make_user(db: Session, email: str, role: str = "EKIP_UYESI") -> tuple[User, dict]:
    user = User(full_name=email.split("@")[0].title(), email=email, hashed_password="x", role=role)
    db.add(user)
    db.flush()
    token = create_access_token({"sub": str(user.id)})
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def case(db_session: Session):
    db = db_session
    admin, admin_h = make_user(db, "yonetici@ornek.com", "YONETICI")
    other_admin, other_admin_h = make_user(db, "baska-yonetici@ornek.com", "YONETICI")
    member, member_h = make_user(db, "uye@ornek.com", "EKIP_UYESI")
    outsider, outsider_h = make_user(db, "disari@ornek.com", "EKIP_UYESI")

    project = Project(
        name="LUNO",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
    )
    other_project = Project(
        name="Diğer",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 31),
        created_by_id=other_admin.id,
    )
    db.add_all([project, other_project])
    db.flush()

    db.add_all([
        ProjectMember(project_id=project.id, user_id=admin.id),
        ProjectMember(project_id=project.id, user_id=member.id),
        ProjectMember(project_id=other_project.id, user_id=other_admin.id),
    ])
    db.commit()
    return {
        "db": db,
        "project": project,
        "other_project": other_project,
        "admin": admin,
        "other_admin": other_admin,
        "member": member,
        "outsider": outsider,
        "h": {
            "admin": admin_h,
            "other_admin": other_admin_h,
            "member": member_h,
            "outsider": outsider_h,
        },
    }


def test_create_and_list_sprints(client, case):
    url = f"/api/v1/projects/{case['project'].id}/sprints"

    r1 = client.post(
        url,
        headers=case["h"]["admin"],
        json={
            "name": "Sprint 2",
            "goal": "Giriş sistemi çalışsın",
            "start_date": "2026-10-12",
            "end_date": "2026-10-18",
            "capacity_points": 40,
        },
    )
    assert r1.status_code == 201, r1.text
    assert r1.json()["name"] == "Sprint 2"
    assert r1.json()["capacity_points"] == 40

    r2 = client.post(
        url,
        headers=case["h"]["admin"],
        json={
            "name": "Sprint 1",
            "start_date": "2026-10-05",
            "end_date": "2026-10-11",
        },
    )
    assert r2.status_code == 201, r2.text

    listed = client.get(url, headers=case["h"]["member"])
    assert listed.status_code == 200
    assert [s["name"] for s in listed.json()] == ["Sprint 1", "Sprint 2"]


def test_create_sprint_date_validations(client, case):
    url = f"/api/v1/projects/{case['project'].id}/sprints"

    # Ters tarih -> 400 INVALID_DATE_RANGE
    bad_range = client.post(
        url,
        headers=case["h"]["admin"],
        json={
            "name": "Ters",
            "start_date": "2026-10-11",
            "end_date": "2026-10-05",
        },
    )
    assert bad_range.status_code == 400
    assert bad_range.json()["error"]["code"] == "INVALID_DATE_RANGE"

    # Geçerli sprint oluştur
    ok = client.post(
        url,
        headers=case["h"]["admin"],
        json={
            "name": "Sprint 1",
            "start_date": "2026-10-05",
            "end_date": "2026-10-11",
        },
    )
    assert ok.status_code == 201

    # Çakışan tarih (uç gün dahil) -> 400 SPRINT_OVERLAP
    overlap = client.post(
        url,
        headers=case["h"]["admin"],
        json={
            "name": "Çakışan",
            "start_date": "2026-10-11",
            "end_date": "2026-10-17",
        },
    )
    assert overlap.status_code == 400
    assert overlap.json()["error"]["code"] == "SPRINT_OVERLAP"

    # Başka projede aynı tarihler serbest
    other_url = f"/api/v1/projects/{case['other_project'].id}/sprints"
    other_ok = client.post(
        other_url,
        headers=case["h"]["other_admin"],
        json={
            "name": "Diğer Sprint 1",
            "start_date": "2026-10-05",
            "end_date": "2026-10-11",
        },
    )
    assert other_ok.status_code == 201


def test_sprint_permissions(client, case):
    url = f"/api/v1/projects/{case['project'].id}/sprints"
    payload = {"name": "S1", "start_date": "2026-10-05", "end_date": "2026-10-11"}

    # Ekip üyesi oluşturamaz -> 403 FORBIDDEN
    assert client.post(url, headers=case["h"]["member"], json=payload).status_code == 403
    # Başka projenin yöneticisi oluşturamaz -> 403 PROJECT_ACCESS_DENIED
    r_other = client.post(url, headers=case["h"]["other_admin"], json=payload)
    assert r_other.status_code == 403
    assert r_other.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"
    # Dışarıdaki listeleyemez -> 403
    assert client.get(url, headers=case["h"]["outsider"]).status_code == 403


def test_update_and_delete_sprint(client, case):
    db = case["db"]
    s1 = Sprint(
        project_id=case["project"].id,
        name="Sprint 1",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
        capacity_points=30,
    )
    s2 = Sprint(
        project_id=case["project"].id,
        name="Sprint 2",
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 18),
    )
    db.add_all([s1, s2])
    db.commit()

    # Güncelle + capacity_points: null ile kapasiteyi kaldır
    patch = client.patch(
        f"/api/v1/sprints/{s1.id}",
        headers=case["h"]["admin"],
        json={"name": "Sprint 1 (Güncel)", "capacity_points": None},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["name"] == "Sprint 1 (Güncel)"
    assert patch.json()["capacity_points"] is None

    # Çakışan tarihe güncelleme -> 400 SPRINT_OVERLAP
    bad_patch = client.patch(
        f"/api/v1/sprints/{s1.id}",
        headers=case["h"]["admin"],
        json={"end_date": "2026-10-13"},
    )
    assert bad_patch.status_code == 400
    assert bad_patch.json()["error"]["code"] == "SPRINT_OVERLAP"

    # Görev bağla ve sprinti sil -> görev kalır, sprint_id null olur
    task = Task(project_id=case["project"].id, title="Görev 1", sprint_id=s1.id)
    db.add(task)
    db.commit()
    task_id = task.id

    deleted = client.delete(f"/api/v1/sprints/{s1.id}", headers=case["h"]["admin"])
    assert deleted.status_code == 204
    db.expire_all()
    kept = db.get(Task, task_id)
    assert kept is not None
    assert kept.sprint_id is None


def test_add_and_remove_tasks_in_sprint_with_capacity_warning(client, case):
    db = case["db"]
    sprint = Sprint(
        project_id=case["project"].id,
        name="Sprint Kapasite",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
        capacity_points=10,
    )
    db.add(sprint)
    db.flush()

    t1 = Task(project_id=case["project"].id, title="T1", status=TaskStatus.DONE, story_points=5)
    t2 = Task(project_id=case["project"].id, title="T2", status=TaskStatus.TODO, story_points=8)
    other_task = Task(project_id=case["other_project"].id, title="Başka", story_points=3)
    db.add_all([t1, t2, other_task])
    db.commit()

    # İlk görev: kapasite (10) aşılmadı -> capacity_warning False
    add1 = client.post(
        f"/api/v1/sprints/{sprint.id}/tasks",
        headers=case["h"]["admin"],
        json={"task_ids": [t1.id]},
    )
    assert add1.status_code == 200, add1.text
    assert add1.json()["total_points"] == 5
    assert add1.json()["done_points"] == 5
    assert add1.json()["capacity_warning"] is False

    # İkinci görev: 5 + 8 = 13 > 10 -> eklenir ama capacity_warning True
    add2 = client.post(
        f"/api/v1/sprints/{sprint.id}/tasks",
        headers=case["h"]["admin"],
        json={"task_ids": [t2.id]},
    )
    assert add2.status_code == 200, add2.text
    assert add2.json()["total_points"] == 13
    assert add2.json()["capacity_warning"] is True

    # Başka projenin görevi eklenemez -> 404
    bad_add = client.post(
        f"/api/v1/sprints/{sprint.id}/tasks",
        headers=case["h"]["admin"],
        json={"task_ids": [other_task.id]},
    )
    assert bad_add.status_code == 404

    # Görev çıkarma -> 204
    rem = client.delete(
        f"/api/v1/sprints/{sprint.id}/tasks/{t2.id}",
        headers=case["h"]["admin"],
    )
    assert rem.status_code == 204
    db.expire_all()
    assert db.get(Task, t2.id).sprint_id is None
