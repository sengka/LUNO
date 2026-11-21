"""US-023 Rapor API'leri testleri (#239; sözleşme 10.2 – 10.3)."""

from datetime import date, datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models import Project, ProjectMember, Sprint, Task, TaskStatus, User


def make_user(db: Session, email: str, full_name: str, role: str = "EKIP_UYESI") -> tuple[User, dict]:
    user = User(full_name=full_name, email=email, hashed_password="x", role=role)
    db.add(user)
    db.flush()
    token = create_access_token({"sub": str(user.id)})
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def case(db_session: Session):
    db = db_session
    admin, admin_h = make_user(db, "yonetici@ornek.com", "Yönetici Ali", "YONETICI")
    other_admin, other_admin_h = make_user(db, "baska@ornek.com", "Başka Yönetici", "YONETICI")
    ayse, ayse_h = make_user(db, "ayse@ornek.com", "Ayşe Yılmaz", "EKIP_UYESI")
    veli, veli_h = make_user(db, "veli@ornek.com", "Veli Demir", "EKIP_UYESI")

    project = Project(
        name="Rapor Projesi",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 12, 31),
        created_by_id=admin.id,
    )
    db.add(project)
    db.flush()

    for user in (admin, ayse, veli):
        db.add(ProjectMember(project_id=project.id, user_id=user.id))

    sprint = Sprint(
        project_id=project.id,
        name="Sprint 1",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 11),
    )
    db.add(sprint)
    db.commit()

    return {
        "db": db,
        "project": project,
        "sprint": sprint,
        "admin": admin,
        "other_admin": other_admin,
        "ayse": ayse,
        "veli": veli,
        "h": {
            "admin": admin_h,
            "other_admin": other_admin_h,
            "ayse": ayse_h,
        },
    }


def test_members_report_counts_and_done_points(client, case):
    db = case["db"]
    project, ayse, sprint = case["project"], case["ayse"], case["sprint"]

    db.add_all([
        Task(project_id=project.id, title="A1", status=TaskStatus.TODO, assignee_id=ayse.id, story_points=3, sprint_id=sprint.id),
        Task(project_id=project.id, title="A2", status=TaskStatus.IN_PROGRESS, assignee_id=ayse.id, story_points=5),
        Task(project_id=project.id, title="A3", status=TaskStatus.DONE, assignee_id=ayse.id, story_points=8, sprint_id=sprint.id),
        Task(project_id=project.id, title="A4", status=TaskStatus.DONE, assignee_id=ayse.id, story_points=5),
        # Aktif olmayan görevler sayılmaz
        Task(project_id=project.id, title="A5", status=TaskStatus.ONAY_BEKLIYOR, assignee_id=ayse.id, story_points=13),
        Task(project_id=project.id, title="A6", status=TaskStatus.REDDEDILDI, assignee_id=ayse.id, story_points=8),
    ])
    db.commit()

    url = f"/api/v1/projects/{project.id}/reports/members"
    res = client.get(url, headers=case["h"]["admin"])
    assert res.status_code == 200, res.text
    members = {m["user"]["id"]: m for m in res.json()["members"]}

    assert members[ayse.id]["counts"] == {
        "TODO": 1,
        "IN_PROGRESS": 1,
        "REVIEW_TESTING": 0,
        "DONE": 2,
    }
    assert members[ayse.id]["done_points"] == 13
    # Görevi olmayan üye de 0 sayılarla döner
    assert members[case["veli"].id]["counts"] == {
        "TODO": 0,
        "IN_PROGRESS": 0,
        "REVIEW_TESTING": 0,
        "DONE": 0,
    }
    assert members[case["veli"].id]["done_points"] == 0

    # sprint_id filtresi
    res_sprint = client.get(url, params={"sprint_id": sprint.id}, headers=case["h"]["admin"])
    assert res_sprint.status_code == 200
    s_members = {m["user"]["id"]: m for m in res_sprint.json()["members"]}
    assert s_members[ayse.id]["counts"] == {
        "TODO": 1,
        "IN_PROGRESS": 0,
        "REVIEW_TESTING": 0,
        "DONE": 1,
    }
    assert s_members[ayse.id]["done_points"] == 8


def test_reports_permissions(client, case):
    project_id = case["project"].id
    for endpoint in (
        f"/api/v1/projects/{project_id}/reports/members",
        f"/api/v1/projects/{project_id}/reports/period",
    ):
        # Ekip üyesi -> 403 FORBIDDEN
        assert client.get(endpoint, headers=case["h"]["ayse"]).status_code == 403
        # Üye olmayan yönetici -> 403 PROJECT_ACCESS_DENIED
        r_other = client.get(endpoint, headers=case["h"]["other_admin"])
        assert r_other.status_code == 403
        assert r_other.json()["error"]["code"] == "PROJECT_ACCESS_DENIED"


def test_period_report_weekly_daily_monthly(client, case):
    db = case["db"]
    project = case["project"]

    t1 = Task(
        project_id=project.id,
        title="Pazartesi açıldı ve bitti",
        status=TaskStatus.DONE,
        created_at=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 5, 15, 0, tzinfo=timezone.utc),
    )
    t2 = Task(
        project_id=project.id,
        title="Salı açıldı",
        status=TaskStatus.TODO,
        created_at=datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 6, 9, 0, tzinfo=timezone.utc),
    )
    t3 = Task(
        project_id=project.id,
        title="Önceki haftadan, Salı bitti",
        status=TaskStatus.DONE,
        created_at=datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 6, 18, 0, tzinfo=timezone.utc),
    )
    # Aktif olmayan görev sayılmaz
    t_pending = Task(
        project_id=project.id,
        title="Onay bekliyor",
        status=TaskStatus.ONAY_BEKLIYOR,
        created_at=datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 10, 5, 11, 0, tzinfo=timezone.utc),
    )
    db.add_all([t1, t2, t3, t_pending])
    db.commit()

    url = f"/api/v1/projects/{project.id}/reports/period"

    # WEEKLY (2026-10-07 Çarşamba -> 2026-10-05 Pazartesi .. 2026-10-11 Pazar)
    weekly = client.get(url, params={"period": "WEEKLY", "date": "2026-10-07"}, headers=case["h"]["admin"])
    assert weekly.status_code == 200, weekly.text
    body = weekly.json()
    assert body["period"] == "WEEKLY"
    assert body["from"] == "2026-10-05"
    assert body["to"] == "2026-10-11"
    assert body["created_count"] == 2
    assert body["completed_count"] == 2
    assert len(body["series"]) == 7
    by_day = {item["date"]: item for item in body["series"]}
    assert by_day["2026-10-05"] == {"date": "2026-10-05", "completed": 1, "created": 1}
    assert by_day["2026-10-06"] == {"date": "2026-10-06", "completed": 1, "created": 1}

    # DAILY
    daily = client.get(url, params={"period": "DAILY", "date": "2026-10-05"}, headers=case["h"]["admin"])
    assert daily.status_code == 200
    d_body = daily.json()
    assert d_body["from"] == "2026-10-05"
    assert d_body["to"] == "2026-10-05"
    assert len(d_body["series"]) == 1
    assert d_body["completed_count"] == 1
    assert d_body["created_count"] == 1

    # MONTHLY (Ekim 2026 -> 31 gün)
    monthly = client.get(url, params={"period": "MONTHLY", "date": "2026-10-07"}, headers=case["h"]["admin"])
    assert monthly.status_code == 200
    m_body = monthly.json()
    assert m_body["from"] == "2026-10-01"
    assert m_body["to"] == "2026-10-31"
    assert len(m_body["series"]) == 31
    assert m_body["created_count"] == 3
    assert m_body["completed_count"] == 2
