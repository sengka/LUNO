"""Veritabanı modelleri ve seed verisi testleri (#80)."""

from datetime import date

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, StatementError

from app.core.security import get_password_hash
from app.models import Priority, Project, ProjectMember, Task, TaskStatus, User
from app.seed import LOAD_TASK_COUNT, SEED_PASSWORD, seed, seed_load_test


def make_user(db, email="ayse@ornek.com", role="EKIP_UYESI"):
    user = User(
        full_name="Ayşe Yılmaz",
        email=email,
        hashed_password=get_password_hash("Guclu1234"),
        role=role,
        theme="LIGHT",
    )
    db.add(user)
    db.flush()
    return user


def make_project(db, owner):
    project = Project(
        name="Mobil Uygulama",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 11, 30),
        created_by=owner,
    )
    db.add(project)
    db.flush()
    return project


def count(db, model, *where):
    return db.scalar(select(func.count()).select_from(model).where(*where))


def test_task_defaults_and_relations(db_session):
    user = make_user(db_session)
    project = make_project(db_session, user)
    db_session.add(ProjectMember(project=project, user=user, technical_role="Frontend Geliştirici"))
    parent = Task(project=project, title="Giriş ekranı", assignee=user, created_by=user)
    child = Task(project=project, title="Form tasarımı", parent=parent, priority=Priority.ORTA)
    db_session.add_all([parent, child])
    db_session.commit()

    assert parent.status == TaskStatus.TODO
    assert child.parent_id == parent.id
    assert [t.title for t in parent.subtasks] == ["Form tasarımı"]
    assert project.members[0].capacity_points is None  # kapasite tanımsız (FR-074)
    assert parent.created_at is not None and parent.updated_at is not None


@pytest.mark.parametrize("points", [1, 2, 3, 5, 8, 13])
def test_story_points_fibonacci_allowed(db_session, points):
    project = make_project(db_session, make_user(db_session))
    db_session.add(Task(project=project, title="Görev", story_points=points))
    db_session.commit()


@pytest.mark.parametrize("points", [0, 4, 21])
def test_story_points_other_values_rejected(db_session, points):
    """FR-036"""
    project = make_project(db_session, make_user(db_session))
    db_session.add(Task(project=project, title="Görev", story_points=points))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_task_due_date_before_start_rejected(db_session):
    """FR-025"""
    project = make_project(db_session, make_user(db_session))
    db_session.add(
        Task(
            project=project,
            title="Görev",
            start_date=date(2026, 10, 10),
            due_date=date(2026, 10, 9),
        )
    )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_project_end_date_before_start_rejected(db_session):
    """FR-016"""
    db_session.add(Project(name="Proje", start_date=date(2026, 10, 10), end_date=date(2026, 10, 1)))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_invalid_status_rejected(db_session):
    project = make_project(db_session, make_user(db_session))
    db_session.add(Task(project=project, title="Görev", status="BILINMIYOR"))
    with pytest.raises((StatementError, LookupError)):
        db_session.commit()


def test_member_added_twice_rejected(db_session):
    user = make_user(db_session)
    project = make_project(db_session, user)
    db_session.add(ProjectMember(project_id=project.id, user_id=user.id))
    db_session.commit()
    db_session.add(ProjectMember(project_id=project.id, user_id=user.id))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_capacity_must_be_positive(db_session):
    user = make_user(db_session)
    project = make_project(db_session, user)
    db_session.add(ProjectMember(project=project, user=user, capacity_points=0))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_deleting_project_deletes_tasks_and_members(db_session):
    """FR-020"""
    user = make_user(db_session)
    project = make_project(db_session, user)
    db_session.add(ProjectMember(project=project, user=user))
    parent = Task(project=project, title="Ana görev")
    db_session.add_all([parent, Task(project=project, title="Alt görev", parent=parent)])
    db_session.commit()

    db_session.delete(project)
    db_session.commit()
    assert count(db_session, Task) == 0
    assert count(db_session, ProjectMember) == 0
    assert count(db_session, User) == 1  # kullanıcı silinmez


def test_deleting_task_deletes_subtasks(db_session):
    """6.7: Alt görevler de silinir."""
    project = make_project(db_session, make_user(db_session))
    parent = Task(project=project, title="Ana görev")
    db_session.add_all([parent, Task(project=project, title="Alt görev", parent=parent)])
    db_session.commit()

    db_session.delete(parent)
    db_session.commit()
    assert count(db_session, Task) == 0


def test_seed_creates_data_and_is_idempotent(db_session):
    seed(db_session)
    seed(db_session)  # ikinci çalıştırma veri eklememeli
    assert count(db_session, User) == 10
    assert count(db_session, Project) == 2
    assert count(db_session, Task) == 19
    statuses = set(db_session.scalars(select(Task.status)).all())
    assert statuses == set(TaskStatus)  # her durumdan en az bir görev var


def test_seed_user_can_login(client, db_session):
    """Seed şifreleri giriş API'siyle aynı yöntemle (bcrypt) hash'lenir (NFR-001)."""
    seed(db_session)
    response = client.post(
        "/api/v1/auth/login", json={"email": "sena@ornek.com", "password": SEED_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "YONETICI"


def test_load_test_seed(db_session):
    """NFR-011: 200 görev ve 20 üyeli proje."""
    seed(db_session)
    seed_load_test(db_session)
    project = db_session.scalar(select(Project).where(Project.name == "Yük Testi Projesi"))
    assert count(db_session, Task, Task.project_id == project.id) == LOAD_TASK_COUNT
    assert count(db_session, ProjectMember, ProjectMember.project_id == project.id) == 20
