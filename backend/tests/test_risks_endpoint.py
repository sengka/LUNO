"""Risk seviyesi yanıtı ve riskli görevler uç noktası (US-024, US-043; sözleşme 12.1 – 12.2, #277, #280)."""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.security import create_access_token, get_password_hash
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User
from app.services.sprints import today_utc


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


def _project(db, admin: User, *members: User) -> Project:
    now = datetime.now(timezone.utc)
    project = Project(
        name="Risk Projesi",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
        created_at=now,
        updated_at=now,
    )
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=admin.id, joined_at=now))
    for member in members:
        db.add(ProjectMember(project_id=project.id, user_id=member.id, joined_at=now))
    db.commit()
    db.refresh(project)
    return project


def _task(
    db,
    project: Project,
    title: str,
    *,
    status=TaskStatus.TODO,
    days_left: int | None = 0,
    story_points=None,
    assignee_id=None,
    parent_id=None,
) -> Task:
    now = datetime.now(timezone.utc)
    due_date = None if days_left is None else today_utc() + timedelta(days=days_left)
    task = Task(
        project_id=project.id,
        parent_id=parent_id,
        title=title,
        status=status,
        story_points=story_points,
        due_date=due_date,
        assignee_id=assignee_id,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture()
def setup(db_session):
    admin, admin_headers = _user(db_session, "risk-admin@ornek.com", SystemRole.YONETICI, "Sena")
    member, member_headers = _user(db_session, "risk-uye@ornek.com", SystemRole.EKIP_UYESI, "Esra")
    outsider, outsider_headers = _user(db_session, "risk-yabanci@ornek.com", SystemRole.EKIP_UYESI)
    project = _project(db_session, admin, member)
    return {
        "db": db_session,
        "project": project,
        "admin": admin,
        "admin_headers": admin_headers,
        "member": member,
        "member_headers": member_headers,
        "outsider": outsider,
        "outsider_headers": outsider_headers,
    }


# --- Task nesnesinde risk_level (12.1) ----------------------------------------------


def test_task_detail_returns_risk_level(client, setup):
    """Görev detayında risk_level hesaplanarak döner (FR-070)."""
    task = _task(setup["db"], setup["project"], "Bugün teslim", status=TaskStatus.TODO, days_left=0)
    resp = client.get(f"/api/v1/tasks/{task.id}", headers=setup["admin_headers"])
    assert resp.status_code == 200
    assert resp.json()["risk_level"] == "YUKSEK"


def test_overdue_task_is_high_risk(client, setup):
    task = _task(
        setup["db"], setup["project"], "Gecikmiş", status=TaskStatus.REVIEW_TESTING, days_left=-3
    )
    resp = client.get(f"/api/v1/tasks/{task.id}", headers=setup["admin_headers"])
    assert resp.json()["risk_level"] == "YUKSEK"


def test_done_task_has_null_risk_level(client, setup):
    """Done görevde risk_level null döner (US-043, FR-072)."""
    task = _task(
        setup["db"], setup["project"], "Bitmiş gecikmiş", status=TaskStatus.DONE, days_left=-5
    )
    resp = client.get(f"/api/v1/tasks/{task.id}", headers=setup["admin_headers"])
    assert resp.status_code == 200
    assert resp.json()["risk_level"] is None


def test_status_change_to_done_clears_risk_level(client, setup):
    """Görev Done'a geçince aynı yanıtta risk_level null olur (US-043)."""
    task = _task(
        setup["db"],
        setup["project"],
        "Devam eden",
        status=TaskStatus.IN_PROGRESS,
        days_left=1,
    )
    before = client.get(f"/api/v1/tasks/{task.id}", headers=setup["admin_headers"])
    assert before.json()["risk_level"] == "ORTA"

    resp = client.patch(
        f"/api/v1/tasks/{task.id}/status",
        json={"status": "DONE"},
        headers=setup["admin_headers"],
    )
    assert resp.status_code == 200
    assert resp.json()["risk_level"] is None


def test_task_list_and_board_include_risk_level(client, setup):
    _task(setup["db"], setup["project"], "Listede", status=TaskStatus.TODO, days_left=1)
    project_id = setup["project"].id

    listed = client.get(
        f"/api/v1/projects/{project_id}/tasks", headers=setup["admin_headers"]
    ).json()
    assert [t["risk_level"] for t in listed["items"]] == ["YUKSEK"]

    board = client.get(
        f"/api/v1/projects/{project_id}/board", headers=setup["admin_headers"]
    ).json()
    todo_column = next(c for c in board["columns"] if c["status"] == "TODO")
    assert [t["risk_level"] for t in todo_column["tasks"]] == ["YUKSEK"]


# --- Riskli görevler uç noktası (12.2) ----------------------------------------------


def test_risks_default_returns_all_risky_tasks_sorted(client, setup):
    """level verilmezse DUSUK ve üstü döner; en riskliden aza sıralanır."""
    db, project = setup["db"], setup["project"]
    high = _task(db, project, "Gecikmiş", status=TaskStatus.TODO, days_left=-1)
    medium = _task(db, project, "İki gün", status=TaskStatus.IN_PROGRESS, days_left=2)
    low = _task(db, project, "Yedi gün", status=TaskStatus.IN_PROGRESS, days_left=7)
    _task(db, project, "Riski yok", status=TaskStatus.TODO, days_left=20)
    _task(db, project, "Tarihsiz", status=TaskStatus.TODO, days_left=None)

    resp = client.get(f"/api/v1/projects/{project.id}/risks", headers=setup["admin_headers"])
    assert resp.status_code == 200
    data = resp.json()
    assert [t["id"] for t in data] == [high.id, medium.id, low.id]
    assert [t["risk_level"] for t in data] == ["YUKSEK", "ORTA", "DUSUK"]


def test_risks_level_filter(client, setup):
    db, project = setup["db"], setup["project"]
    high = _task(db, project, "Gecikmiş", status=TaskStatus.TODO, days_left=-1)
    medium = _task(db, project, "İki gün", status=TaskStatus.IN_PROGRESS, days_left=2)
    _task(db, project, "Yedi gün", status=TaskStatus.IN_PROGRESS, days_left=7)

    orta = client.get(
        f"/api/v1/projects/{project.id}/risks?level=ORTA", headers=setup["admin_headers"]
    )
    assert [t["id"] for t in orta.json()] == [high.id, medium.id]

    yuksek = client.get(
        f"/api/v1/projects/{project.id}/risks?level=YUKSEK", headers=setup["admin_headers"]
    )
    assert [t["id"] for t in yuksek.json()] == [high.id]


def test_risks_same_level_sorted_by_due_date(client, setup):
    """Aynı seviyede teslim tarihi yakın olan önce gelir."""
    db, project = setup["db"], setup["project"]
    later = _task(db, project, "Sonra", status=TaskStatus.TODO, days_left=-1)
    earlier = _task(db, project, "Önce", status=TaskStatus.TODO, days_left=-9)

    resp = client.get(f"/api/v1/projects/{project.id}/risks", headers=setup["admin_headers"])
    assert [t["id"] for t in resp.json()] == [earlier.id, later.id]


def test_risks_excludes_done_and_inactive_tasks(client, setup):
    """Done (US-043) ile onay bekleyen ve reddedilen görevler listede yer almaz."""
    db, project = setup["db"], setup["project"]
    _task(db, project, "Bitmiş", status=TaskStatus.DONE, days_left=-2)
    _task(db, project, "Onay bekliyor", status=TaskStatus.ONAY_BEKLIYOR, days_left=-2)
    _task(db, project, "Reddedildi", status=TaskStatus.REDDEDILDI, days_left=-2)
    risky = _task(db, project, "Riskli", status=TaskStatus.TODO, days_left=-2)

    resp = client.get(f"/api/v1/projects/{project.id}/risks", headers=setup["admin_headers"])
    assert [t["id"] for t in resp.json()] == [risky.id]


def test_risks_includes_subtasks(client, setup):
    """Alt görevler de kendi riskleriyle listelenir."""
    db, project = setup["db"], setup["project"]
    parent = _task(db, project, "Ana görev", status=TaskStatus.TODO, days_left=20)
    subtask = _task(
        db, project, "Alt görev", status=TaskStatus.TODO, days_left=0, parent_id=parent.id
    )

    resp = client.get(f"/api/v1/projects/{project.id}/risks", headers=setup["admin_headers"])
    assert [t["id"] for t in resp.json()] == [subtask.id]


def test_risks_member_can_read_and_outsider_cannot(client, setup):
    """Erişim proje üyesiyle sınırlıdır (FR-013)."""
    db, project = setup["db"], setup["project"]
    _task(db, project, "Riskli", status=TaskStatus.TODO, days_left=0)

    member_resp = client.get(
        f"/api/v1/projects/{project.id}/risks", headers=setup["member_headers"]
    )
    assert member_resp.status_code == 200
    assert len(member_resp.json()) == 1

    outsider_resp = client.get(
        f"/api/v1/projects/{project.id}/risks", headers=setup["outsider_headers"]
    )
    assert outsider_resp.status_code == 403
    assert outsider_resp.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_risks_requires_login_and_existing_project(client, setup):
    assert client.get(f"/api/v1/projects/{setup['project'].id}/risks").status_code == 401

    missing = client.get("/api/v1/projects/9999/risks", headers=setup["admin_headers"])
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "PROJECT_NOT_FOUND"


def test_risks_invalid_level_returns_validation_error(client, setup):
    resp = client.get(
        f"/api/v1/projects/{setup['project'].id}/risks?level=COK_YUKSEK",
        headers=setup["admin_headers"],
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_risks_other_projects_tasks_are_not_listed(client, setup):
    """Riskli görevler yalnızca istenen projeden döner."""
    db = setup["db"]
    other_admin, other_headers = _user(db, "diger@ornek.com", SystemRole.YONETICI)
    other_project = _project(db, other_admin)
    _task(db, other_project, "Diğer projenin riski", status=TaskStatus.TODO, days_left=0)
    mine = _task(db, setup["project"], "Benim riskim", status=TaskStatus.TODO, days_left=0)

    resp = client.get(
        f"/api/v1/projects/{setup['project'].id}/risks", headers=setup["admin_headers"]
    )
    assert [t["id"] for t in resp.json()] == [mine.id]
