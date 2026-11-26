"""Kapasite tanımsız durumu (US-044, FR-074; sözleşme 6.6, #286).

Kapasite sınırı tanımlanmamış bir üyeye atama engellenmez ve uyarı verilmez. Kapasitesi
tanımlı üyede aşım kontrolü US-025 (#283) ile gelecek; buradaki testler yalnızca
kapasitenin tanımsız olduğu durumu ve kontrolün gerekip gerekmediğini doğrular.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User
from app.services.capacity import (
    capacity_check_required,
    ensure_assignment_capacity,
    member_capacity_points,
)


def _user(db, email: str, role: SystemRole, full_name: str = "Kullanıcı") -> tuple[User, dict]:
    user = User(
        full_name=full_name,
        email=email,
        hashed_password=get_password_hash("Luno1234"),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def setup(db_session):
    """Kapasitesi tanımsız bir üye, kapasitesi tanımlı bir üye ve dolu bir görev listesi."""
    admin, admin_headers = _user(db_session, "kapasite-admin@ornek.com", SystemRole.YONETICI)
    member, _ = _user(db_session, "kapasitesiz@ornek.com", SystemRole.EKIP_UYESI, "Ayşe")
    limited, _ = _user(db_session, "kapasiteli@ornek.com", SystemRole.EKIP_UYESI, "Can")

    now = datetime.now(timezone.utc)
    project = Project(
        name="Kapasite Projesi",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db_session.add(project)
    db_session.flush()
    db_session.add_all(
        [
            ProjectMember(project_id=project.id, user_id=admin.id, joined_at=now),
            # Kapasite tanımsız (FR-074)
            ProjectMember(
                project_id=project.id, user_id=member.id, capacity_points=None, joined_at=now
            ),
            ProjectMember(
                project_id=project.id, user_id=limited.id, capacity_points=13, joined_at=now
            ),
        ]
    )
    db_session.commit()
    db_session.refresh(project)

    # Kapasitesi tanımsız üyeye zaten yüklü iş atanmış olsun: 3 × 13 puan açık görev.
    for i in range(3):
        db_session.add(
            Task(
                project_id=project.id,
                title=f"Mevcut görev {i}",
                status=TaskStatus.IN_PROGRESS,
                story_points=13,
                due_date=date(2026, 12, 1),
                assignee_id=member.id,
                created_at=now,
                updated_at=now,
            )
        )
    db_session.commit()
    return {
        "db": db_session,
        "project": project,
        "admin_headers": admin_headers,
        "member": member,
        "limited": limited,
    }


def test_assign_to_member_without_capacity_is_not_blocked(client, setup):
    """Kapasitesi tanımsız üyeye atama engellenmez ve uyarı çıkmaz (US-044, FR-074)."""
    db, project = setup["db"], setup["project"]
    now = datetime.now(timezone.utc)
    task = Task(
        project_id=project.id,
        title="Yeni büyük görev",
        status=TaskStatus.TODO,
        story_points=13,
        due_date=date(2026, 12, 15),
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    resp = client.patch(
        f"/api/v1/tasks/{task.id}/assignee",
        json={"assignee_id": setup["member"].id, "confirm_over_capacity": False},
        headers=setup["admin_headers"],
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assignee"]["id"] == setup["member"].id
    # Yanıt sözleşmedeki Task nesnesidir; kapasite uyarısı alanı eklenmez.
    assert "capacity_warning" not in data
    assert "error" not in data


def test_create_task_with_uncapped_assignee_is_not_blocked(client, setup):
    """Görev oluştururken de kapasitesi tanımsız üyeye atama serbesttir (6.2, FR-074)."""
    resp = client.post(
        f"/api/v1/projects/{setup['project'].id}/tasks",
        json={
            "title": "Kapasitesiz üyeye görev",
            "assignee_id": setup["member"].id,
            "story_points": 13,
            "due_date": (date(2026, 12, 20)).isoformat(),
        },
        headers=setup["admin_headers"],
    )
    assert resp.status_code == 201
    assert resp.json()["assignee"]["id"] == setup["member"].id
    assert "capacity_warning" not in resp.json()


def test_many_assignments_to_member_without_capacity_all_succeed(client, setup):
    """Kapasitesi tanımsız üyede atama sayısı veya puan toplamı uyarı üretmez."""
    db, project = setup["db"], setup["project"]
    now = datetime.now(timezone.utc)
    for i in range(5):
        task = Task(
            project_id=project.id,
            title=f"Ek görev {i}",
            status=TaskStatus.TODO,
            story_points=13,
            due_date=date(2026, 12, 1) + timedelta(days=i),
            created_at=now,
            updated_at=now,
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        resp = client.patch(
            f"/api/v1/tasks/{task.id}/assignee",
            json={"assignee_id": setup["member"].id},
            headers=setup["admin_headers"],
        )
        assert resp.status_code == 200, resp.json()


def test_member_capacity_points_reads_undefined_as_none(setup):
    db, project = setup["db"], setup["project"]
    assert member_capacity_points(db, project.id, setup["member"].id) is None
    assert member_capacity_points(db, project.id, setup["limited"].id) == 13


def test_capacity_check_is_skipped_only_when_undefined(setup):
    db, project = setup["db"], setup["project"]
    assert capacity_check_required(db, project.id, setup["member"].id) is False
    assert capacity_check_required(db, project.id, setup["limited"].id) is True


def test_ensure_assignment_capacity_allows_undefined_and_unassign(setup):
    """Kapasite tanımsızken ve atama kaldırılırken kontrol hiçbir hata üretmez."""
    db, project = setup["db"], setup["project"]
    ensure_assignment_capacity(db, project.id, setup["member"].id, confirm_over_capacity=False)
    ensure_assignment_capacity(db, project.id, None, confirm_over_capacity=False)
