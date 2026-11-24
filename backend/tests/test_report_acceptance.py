"""US-023 / #241: known-data counts, calendar boundaries, access and query scaling."""
from datetime import date, datetime, time, timedelta, timezone
import json
from statistics import median
from time import perf_counter

import pytest
from sqlalchemy import event, insert

from app.core.security import create_access_token
from app.models import Project, ProjectMember, Sprint, Task, TaskStatus, User


@pytest.fixture
def report_case(db_session):
    users = {}
    for name, role in (("admin", "YONETICI"), ("member", "EKIP_UYESI"),
                       ("zero", "EKIP_UYESI"), ("outsider", "YONETICI")):
        user = User(full_name=f"QA {name}", email=f"report-{name}@example.com",
                    hashed_password="synthetic-no-login", role=role)
        db_session.add(user)
        db_session.flush()
        users[name] = user
    projects = [Project(name=n, start_date=date(2026, 1, 1), end_date=date(2028, 12, 31))
                for n in ("Report QA", "Other project")]
    db_session.add_all(projects)
    db_session.flush()
    for name in ("admin", "member", "zero"):
        db_session.add(ProjectMember(project_id=projects[0].id, user_id=users[name].id))
    sprints = [Sprint(project_id=p.id, name="QA sprint", start_date=date(2026, 11, 1),
                      end_date=date(2026, 11, 30)) for p in projects]
    db_session.add_all(sprints)
    db_session.commit()
    return {"db": db_session, "users": users, "project": projects[0], "other": projects[1],
            "sprints": sprints,
            "headers": {n: {"Authorization": "Bearer " + create_access_token({"sub": str(u.id)})}
                        for n, u in users.items()}}


def add_task(case, **overrides):
    values = dict(project_id=case["project"].id, title="Known QA task", status=TaskStatus.TODO,
                  assignee_id=case["users"]["member"].id,
                  created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                  updated_at=datetime(2026, 11, 1, tzinfo=timezone.utc))
    values.update(overrides)
    task = Task(**values)
    case["db"].add(task)
    case["db"].commit()
    return task


def read(client, case, kind, **params):
    r = client.get(f"/api/v1/projects/{case['project'].id}/reports/{kind}",
                   headers=case["headers"]["admin"], params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_known_members_sprint_and_project_isolation(client, report_case):
    c = report_case
    for status in (TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING,
                   TaskStatus.DONE, TaskStatus.DONE, TaskStatus.ONAY_BEKLIYOR, TaskStatus.REDDEDILDI):
        add_task(c, status=status, story_points=3 if status == TaskStatus.DONE else 13,
                 sprint_id=c["sprints"][0].id)
    add_task(c, status=TaskStatus.DONE, story_points=None)
    add_task(c, status=TaskStatus.DONE, assignee_id=None, story_points=8)
    add_task(c, project_id=c["other"].id, status=TaskStatus.DONE, story_points=13)
    rows = {r["user"]["id"]: r for r in read(client, c, "members")["members"]}
    assert len(rows) == 3
    assert rows[c["users"]["member"].id]["counts"] == {
        "TODO": 1, "IN_PROGRESS": 1, "REVIEW_TESTING": 1, "DONE": 3}
    assert rows[c["users"]["member"].id]["done_points"] == 6
    assert set(rows[c["users"]["zero"].id]["counts"].values()) == {0}
    filtered = read(client, c, "members", sprint_id=c["sprints"][0].id)["members"]
    assert next(r for r in filtered if r["user"]["id"] == c["users"]["member"].id)["counts"]["DONE"] == 2


@pytest.mark.parametrize("period,target,start,end", [
    ("DAILY", "2026-11-23", "2026-11-23", "2026-11-23"),
    ("WEEKLY", "2026-11-23", "2026-11-23", "2026-11-29"),
    ("WEEKLY", "2026-11-29", "2026-11-23", "2026-11-29"),
    ("WEEKLY", "2027-01-01", "2026-12-28", "2027-01-03"),
    ("MONTHLY", "2026-11-30", "2026-11-01", "2026-11-30"),
    ("MONTHLY", "2026-12-31", "2026-12-01", "2026-12-31"),
    ("MONTHLY", "2027-02-28", "2027-02-01", "2027-02-28"),
    ("MONTHLY", "2028-02-29", "2028-02-01", "2028-02-29"),
])
def test_period_edges_and_daily_series(client, report_case, period, target, start, end):
    c = report_case
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    stamps = [datetime.combine(a, time.min, timezone.utc) - timedelta(microseconds=1),
              datetime.combine(a, time.min, timezone.utc),
              datetime.combine(b, time.max, timezone.utc),
              datetime.combine(b + timedelta(days=1), time.min, timezone.utc)]
    for stamp in stamps:
        add_task(c, status=TaskStatus.DONE, created_at=stamp, updated_at=stamp)
    # Pending/rejected and other-project tasks must not inflate either total.
    for status in (TaskStatus.ONAY_BEKLIYOR, TaskStatus.REDDEDILDI):
        add_task(c, status=status, created_at=stamps[1], updated_at=stamps[1])
    add_task(c, project_id=c["other"].id, status=TaskStatus.DONE,
             created_at=stamps[1], updated_at=stamps[1])
    result = read(client, c, "period", period=period, date=target)
    assert (result["period"], result["from"], result["to"]) == (period, start, end)
    assert result["created_count"] == result["completed_count"] == 2
    expected_dates = [(a + timedelta(days=i)).isoformat() for i in range((b-a).days+1)]
    assert [r["date"] for r in result["series"]] == expected_dates
    assert sum(r["created"] for r in result["series"]) == 2
    assert sum(r["completed"] for r in result["series"]) == 2
    assert all(r["created"] == r["completed"] == (2 if a == b else 1)
               for r in (result["series"][0], result["series"][-1]))
    assert all(r["created"] == r["completed"] == 0 for r in result["series"][1:-1])


@pytest.mark.parametrize("period", ["DAILY", "WEEKLY", "MONTHLY"])
def test_zero_tasks(client, report_case, period):
    result = read(client, report_case, "period", period=period, date="2026-11-23")
    assert result["created_count"] == result["completed_count"] == 0
    assert all(r["created"] == r["completed"] == 0 for r in result["series"])
    members = read(client, report_case, "members")["members"]
    assert len(members) == 3
    assert all(not any(r["counts"].values()) and r["done_points"] == 0 for r in members)


@pytest.mark.parametrize("endpoint", ["members", "period"])
@pytest.mark.parametrize("actor,expected,code", [(None, 401, "UNAUTHORIZED"),
    ("member", 403, "FORBIDDEN"), ("outsider", 403, "PROJECT_ACCESS_DENIED")])
def test_permissions(client, report_case, endpoint, actor, expected, code):
    c = report_case
    r = client.get(f"/api/v1/projects/{c['project'].id}/reports/{endpoint}",
                   headers=c["headers"].get(actor, {}))
    assert r.status_code == expected
    assert r.json()["error"]["code"] == code


@pytest.mark.parametrize("endpoint", ["members", "period"])
def test_missing_project(client, report_case, endpoint):
    r = client.get(f"/api/v1/projects/999999/reports/{endpoint}", headers=report_case["headers"]["admin"])
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "PROJECT_NOT_FOUND"


@pytest.mark.parametrize("params", [{"period": "YEARLY"}, {"period": "daily"},
    {"date": "2026-02-29"}, {"date": "invalid"}])
def test_invalid_period_parameters(client, report_case, params):
    c = report_case
    r = client.get(f"/api/v1/projects/{c['project'].id}/reports/period",
                   params=params, headers=c["headers"]["admin"])
    assert r.status_code == 422


@pytest.mark.parametrize("value", [999999, "other-project", "text"])
def test_invalid_sprint(client, report_case, value):
    c = report_case
    value = c["sprints"][1].id if value == "other-project" else value
    r = client.get(f"/api/v1/projects/{c['project'].id}/reports/members",
                   params={"sprint_id": value}, headers=c["headers"]["admin"])
    assert r.status_code == (422 if value == "text" else 404)


def test_default_period_uses_server_today(client, report_case, monkeypatch):
    monkeypatch.setattr("app.api.v1.reports.today_utc", lambda: date(2026, 12, 31))
    data = read(client, report_case, "period")
    assert (data["period"], data["from"], data["to"]) == ("WEEKLY", "2026-12-28", "2027-01-03")


def test_completed_task_edit_does_not_move_completion_day(client, report_case, monkeypatch):
    c = report_case
    task = add_task(c, status=TaskStatus.IN_PROGRESS)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 20, 10, tzinfo=timezone.utc)
    monkeypatch.setattr("app.api.v1.tasks.datetime", Clock)
    assert client.patch(f"/api/v1/tasks/{task.id}/status", headers=c["headers"]["admin"],
                        json={"status": "DONE"}).status_code == 200
    Clock.now = classmethod(lambda cls, tz=None: cls(2026, 11, 23, 10, tzinfo=timezone.utc))
    assert client.patch(f"/api/v1/tasks/{task.id}", headers=c["headers"]["admin"],
                        json={"title": "Edited after completion"}).status_code == 200
    assert read(client, c, "period", period="DAILY", date="2026-11-20")["completed_count"] == 1
    assert read(client, c, "period", period="DAILY", date="2026-11-23")["completed_count"] == 0


@pytest.mark.parametrize("change", ["title", "assignee", "same-status"])
def test_legacy_completion_is_preserved_before_any_edit(client, report_case, change):
    c = report_case
    task = add_task(c, status=TaskStatus.DONE,
                    updated_at=datetime(2026, 11, 20, tzinfo=timezone.utc))
    suffix, payload = {
        "title": ("", {"title": "Legacy completion edit"}),
        "assignee": ("/assignee", {"assignee_id": c["users"]["zero"].id}),
        "same-status": ("/status", {"status": "DONE"}),
    }[change]
    response = client.patch(f"/api/v1/tasks/{task.id}{suffix}",
                            headers=c["headers"]["admin"], json=payload)
    assert response.status_code == 200, response.text
    c["db"].refresh(task)
    assert task.completed_at.date() == date(2026, 11, 20)
    assert read(client, c, "period", period="DAILY", date="2026-11-20")["completed_count"] == 1


def test_reopen_and_complete_again(client, report_case, monkeypatch):
    c = report_case
    task = add_task(c, status=TaskStatus.DONE,
                    updated_at=datetime(2026, 11, 20, tzinfo=timezone.utc))
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 23, 10, tzinfo=timezone.utc)
    monkeypatch.setattr("app.api.v1.tasks.datetime", Clock)
    url = f"/api/v1/tasks/{task.id}/status"
    assert client.patch(url, headers=c["headers"]["admin"], json={"status": "IN_PROGRESS"}).status_code == 200
    c["db"].refresh(task)
    assert task.completed_at is None
    assert read(client, c, "period", period="DAILY", date="2026-11-20")["completed_count"] == 0
    assert client.patch(url, headers=c["headers"]["admin"], json={"status": "DONE"}).status_code == 200
    assert read(client, c, "period", period="DAILY", date="2026-11-23")["completed_count"] == 1


def test_large_data_query_scaling(client, report_case):
    c, size = report_case, 10000
    rows = [dict(project_id=c["project"].id, title=f"Load {i}", assignee_id=c["users"]["member"].id,
                 status="DONE" if i % 2 == 0 else "TODO", story_points=3,
                 created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
                 updated_at=datetime(2026, 11, 23, tzinfo=timezone.utc)) for i in range(size)]
    c["db"].execute(insert(Task.__table__), rows)
    c["db"].commit()
    metrics = {}
    for endpoint in ("members", "period"):
        elapsed, queries = [], []
        for _ in range(5):
            statements = []
            def track(conn, cursor, statement, parameters, context, executemany):
                if statement.lstrip().upper().startswith("SELECT"):
                    statements.append(statement)
            engine = c["db"].get_bind()
            event.listen(engine, "before_cursor_execute", track)
            start = perf_counter()
            try:
                data = read(client, c, endpoint, **({"period": "MONTHLY", "date": "2026-11-23"} if endpoint == "period" else {}))
            finally:
                elapsed.append(round((perf_counter()-start)*1000, 3))
                event.remove(engine, "before_cursor_execute", track)
            queries.append(len(statements))
            if endpoint == "members":
                row = next(r for r in data["members"] if r["user"]["id"] == c["users"]["member"].id)
                assert row["counts"]["DONE"] == row["counts"]["TODO"] == 5000
                assert row["done_points"] == 15000
            else:
                assert data["created_count"] == 10000 and data["completed_count"] == 5000
        metrics[endpoint] = {"tasks": size, "elapsed_ms": elapsed, "median_ms": median(elapsed), "select_counts": queries}
    print("US023_PERFORMANCE=" + json.dumps(metrics))
    # A deterministic structural budget, not a machine-dependent latency SLA.
    assert max(metrics["members"]["select_counts"]) <= 8
    assert max(metrics["period"]["select_counts"]) <= 8
