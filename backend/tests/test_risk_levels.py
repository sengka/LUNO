"""Gecikme risk seviyesi kuralı ve sınır değerleri (US-024, US-043, sözleşme 12.1, #277, #280).

Kural, Sprint 7'de onaylanan haliyle sözleşme 12.1'de yazılıdır. Buradaki testler eşiklerin
tam değerinde, bir gün öncesinde ve bir gün sonrasında beklenen seviyeyi doğrular.
"""

from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.enums import RiskLevel, TaskStatus
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User
from app.services.risk import (
    HEAVY_OPEN_TASK_COUNT,
    NEAR_DAYS_LEFT,
    URGENT_DAYS_LEFT,
    calculate_risk_level,
    levels_at_or_above,
    load_open_task_counts,
)

TODAY = date(2026, 11, 20)


@pytest.fixture()
def project_fixture(db_session):
    """Bir yönetici, bir ekip üyesi ve ikisinin üye olduğu bir proje."""
    now = datetime.now(timezone.utc)
    admin = User(
        full_name="Yönetici",
        email="risk-admin@ornek.com",
        hashed_password="x",
        role=SystemRole.YONETICI,
    )
    member = User(
        full_name="Ekip Üyesi",
        email="risk-member@ornek.com",
        hashed_password="x",
        role=SystemRole.EKIP_UYESI,
    )
    db_session.add_all([admin, member])
    db_session.flush()

    project = Project(
        name="Risk Projesi",
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
            ProjectMember(project_id=project.id, user_id=member.id, joined_at=now),
        ]
    )
    db_session.commit()
    return project, admin, member


def _task(
    db,
    project,
    *,
    status=TaskStatus.TODO,
    due_date=TODAY,
    story_points=None,
    assignee_id=None,
    parent_id=None,
    title="Görev",
) -> Task:
    now = datetime.now(timezone.utc)
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


# --- 1. Risk olmayan durumlar -------------------------------------------------------


def test_done_task_has_no_risk(db_session, project_fixture):
    """Done görevde risk gösterilmez; teslim tarihi geçmiş olsa bile (FR-072, US-043)."""
    project, _, _ = project_fixture
    task = _task(db_session, project, status=TaskStatus.DONE, due_date=TODAY - timedelta(days=1))
    assert calculate_risk_level(task, today=TODAY) is None


def test_task_without_due_date_has_no_risk(db_session, project_fixture):
    project, _, _ = project_fixture
    task = _task(db_session, project, status=TaskStatus.TODO, due_date=None)
    assert calculate_risk_level(task, today=TODAY) is None


@pytest.mark.parametrize("status", [TaskStatus.ONAY_BEKLIYOR, TaskStatus.REDDEDILDI])
def test_inactive_tasks_have_no_risk(db_session, project_fixture, status):
    """Onay bekleyen ve reddedilen görevler aktif değildir; risk taşımaz (sözleşme 1.3)."""
    project, _, _ = project_fixture
    task = _task(db_session, project, status=status, due_date=TODAY - timedelta(days=1))
    assert calculate_risk_level(task, today=TODAY) is None


# --- 2. Teslim tarihi geçmiş --------------------------------------------------------


@pytest.mark.parametrize(
    "status", [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING]
)
def test_overdue_task_is_high_risk(db_session, project_fixture, status):
    """Teslim tarihi geçmiş ve Done olmayan görev YUKSEK (FR-071)."""
    project, _, _ = project_fixture
    task = _task(db_session, project, status=status, due_date=TODAY - timedelta(days=1))
    assert calculate_risk_level(task, today=TODAY) == RiskLevel.YUKSEK


# --- 3. Kalan güne ve duruma göre taban seviye --------------------------------------


@pytest.mark.parametrize("days_left", [0, 1, URGENT_DAYS_LEFT])
@pytest.mark.parametrize(
    "status,expected",
    [
        (TaskStatus.TODO, RiskLevel.YUKSEK),
        (TaskStatus.IN_PROGRESS, RiskLevel.ORTA),
        (TaskStatus.REVIEW_TESTING, RiskLevel.DUSUK),
    ],
)
def test_two_days_or_less_levels(db_session, project_fixture, days_left, status, expected):
    """2 gün veya az kaldıysa: To Do YUKSEK, In Progress ORTA, Review & Testing DUSUK."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=status,
        due_date=TODAY + timedelta(days=days_left),
    )
    assert calculate_risk_level(task, today=TODAY) == expected


@pytest.mark.parametrize("days_left", [URGENT_DAYS_LEFT + 1, 5, NEAR_DAYS_LEFT])
@pytest.mark.parametrize(
    "status,expected",
    [
        (TaskStatus.TODO, RiskLevel.ORTA),
        (TaskStatus.IN_PROGRESS, RiskLevel.DUSUK),
        (TaskStatus.REVIEW_TESTING, None),
    ],
)
def test_three_to_seven_days_levels(db_session, project_fixture, days_left, status, expected):
    """3-7 gün kaldıysa: To Do ORTA, In Progress DUSUK, Review & Testing risk yok."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=status,
        due_date=TODAY + timedelta(days=days_left),
    )
    assert calculate_risk_level(task, today=TODAY) == expected


@pytest.mark.parametrize(
    "status", [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING]
)
def test_more_than_seven_days_has_no_risk(db_session, project_fixture, status):
    """7 günden fazla kaldıysa risk yok; eşiğin bir gün sonrası sınır dışıdır."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=status,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT + 1),
    )
    assert calculate_risk_level(task, today=TODAY) is None


# --- 4. Seviye yükseltme etkenleri --------------------------------------------------


@pytest.mark.parametrize("story_points", [8, 13])
def test_two_factors_escalate_one_step(db_session, project_fixture, story_points):
    """Efor puanı 8/13 ve alt görevlerin yarısından azı bitmiş: DUSUK → ORTA."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=story_points,
    )
    for i in range(4):
        _task(
            db_session,
            project,
            status=TaskStatus.DONE if i == 0 else TaskStatus.TODO,
            due_date=None,
            parent_id=task.id,
            title=f"Alt görev {i}",
        )
    db_session.refresh(task)
    assert calculate_risk_level(task, today=TODAY) == RiskLevel.ORTA


def test_single_factor_does_not_escalate(db_session, project_fixture):
    """Tek etken yetmez: efor puanı 13 ama alt görev yok ve görev yükü düşük."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=13,
    )
    assert calculate_risk_level(task, today=TODAY) == RiskLevel.DUSUK


def test_escalation_stops_at_high(db_session, project_fixture):
    """YUKSEK en üst seviyedir; etkenler olsa da üstüne çıkılmaz."""
    project, _, member = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.TODO,
        due_date=TODAY,
        story_points=13,
        assignee_id=member.id,
    )
    for i in range(2):
        _task(
            db_session,
            project,
            status=TaskStatus.TODO,
            due_date=None,
            parent_id=task.id,
            title=f"Alt görev {i}",
        )
    db_session.refresh(task)
    assert calculate_risk_level(task, today=TODAY) == RiskLevel.YUKSEK


def test_no_base_level_is_not_escalated(db_session, project_fixture):
    """Taban seviye yoksa (8 gün kaldı) etkenler seviye üretmez."""
    project, _, member = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.TODO,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT + 1),
        story_points=13,
        assignee_id=member.id,
    )
    for i in range(3):
        _task(
            db_session,
            project,
            status=TaskStatus.TODO,
            due_date=None,
            parent_id=task.id,
            title=f"Alt görev {i}",
        )
    db_session.refresh(task)
    assert calculate_risk_level(task, today=TODAY) is None


def test_half_done_subtasks_is_not_a_factor(db_session, project_fixture):
    """Tam yarısı bitmiş alt görev etken değildir (yarısından azı aranır)."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=13,
    )
    for i, st in enumerate((TaskStatus.DONE, TaskStatus.TODO)):
        _task(
            db_session, project, status=st, due_date=None, parent_id=task.id, title=f"Alt {i}"
        )
    db_session.refresh(task)
    assert calculate_risk_level(task, today=TODAY) == RiskLevel.DUSUK


def test_pending_subtasks_are_ignored_in_factor(db_session, project_fixture):
    """Onay bekleyen alt görevler oranı düşürmez (sözleşme 1.3)."""
    project, _, _ = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=13,
    )
    _task(db_session, project, status=TaskStatus.DONE, due_date=None, parent_id=task.id, title="A")
    _task(
        db_session,
        project,
        status=TaskStatus.ONAY_BEKLIYOR,
        due_date=None,
        parent_id=task.id,
        title="B",
    )
    db_session.refresh(task)
    # Aktif alt görevlerin tamamı (1/1) bitmiş: etken yok, seviye taban seviyede kalır.
    assert calculate_risk_level(task, today=TODAY) == RiskLevel.DUSUK


def test_open_task_load_factor_boundary(db_session, project_fixture):
    """Atanan kişinin açık görev sayısı eşiği aşarsa etken sayılır; tam eşikte sayılmaz."""
    project, _, member = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=13,
        assignee_id=member.id,
    )
    # Görevin kendisi de kişinin açık görevlerinden biri; eşiğe kadar doldur.
    for i in range(HEAVY_OPEN_TASK_COUNT - 1):
        _task(
            db_session,
            project,
            status=TaskStatus.TODO,
            due_date=None,
            assignee_id=member.id,
            title=f"Diğer görev {i}",
        )
    counts = load_open_task_counts(db_session, [task])
    assert counts[(project.id, member.id)] == HEAVY_OPEN_TASK_COUNT
    assert calculate_risk_level(task, today=TODAY, open_task_counts=counts) == RiskLevel.DUSUK

    _task(
        db_session,
        project,
        status=TaskStatus.TODO,
        due_date=None,
        assignee_id=member.id,
        title="Eşiği aşan görev",
    )
    counts = load_open_task_counts(db_session, [task])
    assert counts[(project.id, member.id)] == HEAVY_OPEN_TASK_COUNT + 1
    assert calculate_risk_level(task, today=TODAY, open_task_counts=counts) == RiskLevel.ORTA


def test_done_tasks_are_not_counted_as_open_load(db_session, project_fixture):
    """Bitmiş görevler kişinin açık görev yüküne girmez."""
    project, _, member = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=13,
        assignee_id=member.id,
    )
    for i in range(HEAVY_OPEN_TASK_COUNT + 3):
        _task(
            db_session,
            project,
            status=TaskStatus.DONE,
            due_date=None,
            assignee_id=member.id,
            title=f"Bitmiş görev {i}",
        )
    counts = load_open_task_counts(db_session, [task])
    assert counts[(project.id, member.id)] == 1
    assert calculate_risk_level(task, today=TODAY, open_task_counts=counts) == RiskLevel.DUSUK


def test_batch_counts_match_lazy_calculation(db_session, project_fixture):
    """`open_task_counts` verilmediğinde sonuç, toplu sayımla aynı olmalı."""
    project, _, member = project_fixture
    task = _task(
        db_session,
        project,
        status=TaskStatus.IN_PROGRESS,
        due_date=TODAY + timedelta(days=NEAR_DAYS_LEFT),
        story_points=13,
        assignee_id=member.id,
    )
    for i in range(HEAVY_OPEN_TASK_COUNT):
        _task(
            db_session,
            project,
            status=TaskStatus.TODO,
            due_date=None,
            assignee_id=member.id,
            title=f"Yük {i}",
        )
    counts = load_open_task_counts(db_session, [task])
    assert calculate_risk_level(task, today=TODAY) == calculate_risk_level(
        task, today=TODAY, open_task_counts=counts
    )


def test_levels_at_or_above():
    assert levels_at_or_above(RiskLevel.DUSUK) == (
        RiskLevel.DUSUK,
        RiskLevel.ORTA,
        RiskLevel.YUKSEK,
    )
    assert levels_at_or_above(RiskLevel.ORTA) == (RiskLevel.ORTA, RiskLevel.YUKSEK)
    assert levels_at_or_above(RiskLevel.YUKSEK) == (RiskLevel.YUKSEK,)
