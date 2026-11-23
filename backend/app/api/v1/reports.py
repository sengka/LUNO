"""Raporlar (US-023, FR-062, FR-063; sözleşme 10.2 – 10.3)."""

import calendar
from datetime import date, datetime, time, timedelta, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_project_member, require_admin
from app.core.exceptions import SprintNotFoundException
from app.database import get_db
from app.models.enums import ACTIVE_TASK_STATUSES, TaskStatus
from app.models.project_member import ProjectMember
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.user import User
from app.schemas.report import (
    MemberReportItem,
    MemberReportResponse,
    PeriodReportResponse,
    PeriodSeriesItem,
    ReportUserSummary,
)
from app.services.sprints import today_utc

router = APIRouter(tags=["Raporlar"])


@router.get(
    "/projects/{project_id}/reports/members",
    response_model=MemberReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Kişi bazlı rapor (US-023 / 10.2)",
)
def get_members_report(
    project_id: int,
    sprint_id: Optional[int] = Query(default=None),
    _admin: User = Depends(require_admin),
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    if sprint_id is not None:
        sprint_exists = (
            db.query(Sprint.id)
            .filter(Sprint.id == sprint_id, Sprint.project_id == project_id)
            .first()
        )
        if sprint_exists is None:
            raise SprintNotFoundException()

    members = (
        db.query(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .order_by(User.id.asc())
        .all()
    )

    task_query = db.query(
        Task.assignee_id,
        Task.status,
        func.count(Task.id),
        func.coalesce(func.sum(func.coalesce(Task.story_points, 0)), 0),
    ).filter(
        Task.project_id == project_id,
        Task.assignee_id.isnot(None),
        Task.status.in_(ACTIVE_TASK_STATUSES),
    )
    if sprint_id is not None:
        task_query = task_query.filter(Task.sprint_id == sprint_id)

    rows = task_query.group_by(Task.assignee_id, Task.status).all()

    counts_by_user: dict[int, dict[str, int]] = {
        u.id: {s.value: 0 for s in ACTIVE_TASK_STATUSES} for u in members
    }
    done_points_by_user: dict[int, int] = {u.id: 0 for u in members}

    for assignee_id, task_status, count, points_sum in rows:
        if assignee_id not in counts_by_user:
            continue
        status_key = (
            task_status.value if isinstance(task_status, TaskStatus) else str(task_status)
        )
        counts_by_user[assignee_id][status_key] = int(count)
        if status_key == TaskStatus.DONE.value:
            done_points_by_user[assignee_id] = int(points_sum or 0)

    items = [
        MemberReportItem(
            user=ReportUserSummary(
                id=u.id,
                full_name=u.full_name,
                avatar_url=getattr(u, "avatar_url", None),
            ),
            counts=counts_by_user[u.id],
            done_points=done_points_by_user[u.id],
        )
        for u in members
    ]
    return MemberReportResponse(members=items)


def _period_bounds(period: str, target_date: date) -> tuple[date, date]:
    if period == "DAILY":
        return target_date, target_date
    if period == "WEEKLY":
        monday = target_date - timedelta(days=target_date.weekday())
        return monday, monday + timedelta(days=6)
    # MONTHLY
    first_day = target_date.replace(day=1)
    last_day = target_date.replace(
        day=calendar.monthrange(target_date.year, target_date.month)[1]
    )
    return first_day, last_day


@router.get(
    "/projects/{project_id}/reports/period",
    response_model=PeriodReportResponse,
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    summary="Dönemsel rapor (US-023 / 10.3)",
)
def get_period_report(
    project_id: int,
    period: Literal["DAILY", "WEEKLY", "MONTHLY"] = Query(default="WEEKLY"),
    target_date: Optional[date] = Query(default=None, alias="date"),
    _admin: User = Depends(require_admin),
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    ref_date = target_date or today_utc()
    from_date, to_date = _period_bounds(period, ref_date)

    # Yalnızca gün/toplam sütunlarını getir; Task nesneleri ve ilişkilerini yükleme.
    start = datetime.combine(from_date, time.min, timezone.utc)
    end = datetime.combine(to_date, time.max, timezone.utc)

    def counts_by_day(timestamp, completed=False):
        day = func.date(timestamp)
        query = db.query(day, func.count(Task.id)).filter(
            Task.project_id == project_id,
            Task.status.in_(ACTIVE_TASK_STATUSES),
            timestamp >= start,
            timestamp <= end,
        )
        if completed:
            query = query.filter(Task.status == TaskStatus.DONE)
        return {
            date.fromisoformat(value) if isinstance(value, str) else value: count
            for value, count in query.group_by(day).all()
        }

    created_by_day = counts_by_day(Task.created_at)
    # Migration öncesi DONE kayıtlarının bitiş geçmişi bilinmediğinden eski tahmin korunur.
    completed_by_day = counts_by_day(func.coalesce(Task.completed_at, Task.updated_at), completed=True)

    series: list[PeriodSeriesItem] = []
    current = from_date
    while current <= to_date:
        series.append(
            PeriodSeriesItem(
                date=current,
                completed=completed_by_day.get(current, 0),
                created=created_by_day.get(current, 0),
            )
        )
        current += timedelta(days=1)

    return PeriodReportResponse(
        period=period,
        from_date=from_date,
        to=to_date,
        completed_count=sum(item.completed for item in series),
        created_count=sum(item.created for item in series),
        series=series,
    )
