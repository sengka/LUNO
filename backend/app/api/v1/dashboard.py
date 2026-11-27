"""Dashboard (US-022, FR-060, FR-061; sözleşme 10.1)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.v1.tasks import build_task_response
from app.database import get_db
from app.models.enums import ACTIVE_TASK_STATUSES, OPEN_TASK_STATUSES, TaskStatus
from app.models.notification import Notification
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.dashboard import DashboardProject, DashboardResponse

router = APIRouter(tags=["Dashboard"])

UPCOMING_LIMIT = 5


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Dashboard (US-022 / 10.1)",
)
def get_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Giriş yapan kullanıcının özet ekranı (US-022, FR-060). Erişim: giriş yapmış.

    - projects: Üyesi olunan projeler (proje id'sine göre). progress_percent, proje sayfasıyla
      aynı kural: aktif ana görevler içinde DONE olanların yüzdesi (FR-061); onay bekleyen ve
      reddedilen görevler sayılmaz, görev yoksa 0. my_open_tasks: o projede kullanıcıya atanmış,
      bitmemiş (TODO, IN_PROGRESS, REVIEW_TESTING) görev sayısı.
    - my_task_counts: Kullanıcıya atanmış aktif görevlerin durumlara göre sayısı; dört durum
      her zaman döner (görev yoksa 0).
    - upcoming_tasks: Kullanıcıya atanmış, bitmemiş ve teslim tarihi olan görevlerden teslim
      tarihi en yakın 5 tanesi (tarihi geçmiş olanlar en başta). Task nesnesi listesi.
    - unread_notification_count: Kullanıcının okunmamış bildirim sayısı.
    Alt görevler de kullanıcıya atanmışsa sayılara ve listeye dahildir.
    """
    project_ids = [
        pid
        for (pid,) in db.query(ProjectMember.project_id).filter(ProjectMember.user_id == current_user.id)
    ]

    projects: list[DashboardProject] = []
    my_task_counts = {s.value: 0 for s in ACTIVE_TASK_STATUSES}
    upcoming_tasks = []

    if project_ids:
        # Proje ilerlemesi (FR-061): aktif ana görevler içinde DONE oranı
        progress_rows = (
            db.query(
                Task.project_id,
                func.count(Task.id),
                func.sum(case((Task.status == TaskStatus.DONE, 1), else_=0)),
            )
            .filter(
                Task.project_id.in_(project_ids),
                Task.parent_id.is_(None),
                Task.status.in_(ACTIVE_TASK_STATUSES),
            )
            .group_by(Task.project_id)
            .all()
        )
        progress = {
            pid: round((done or 0) / total * 100, 1) if total else 0.0
            for pid, total, done in progress_rows
        }

        my_tasks = db.query(Task).filter(
            Task.project_id.in_(project_ids), Task.assignee_id == current_user.id
        )

        open_counts = dict(
            my_tasks.with_entities(Task.project_id, func.count(Task.id))
            .filter(Task.status.in_(OPEN_TASK_STATUSES))
            .group_by(Task.project_id)
            .all()
        )

        for status_value, count in (
            my_tasks.with_entities(Task.status, func.count(Task.id))
            .filter(Task.status.in_(ACTIVE_TASK_STATUSES))
            .group_by(Task.status)
            .all()
        ):
            key = status_value.value if isinstance(status_value, TaskStatus) else str(status_value)
            my_task_counts[key] = count

        for project in db.query(Project).filter(Project.id.in_(project_ids)).order_by(Project.id.asc()):
            projects.append(
                DashboardProject(
                    id=project.id,
                    name=project.name,
                    progress_percent=progress.get(project.id, 0.0),
                    my_open_tasks=open_counts.get(project.id, 0),
                )
            )

        upcoming = (
            my_tasks.filter(Task.status.in_(OPEN_TASK_STATUSES), Task.due_date.isnot(None))
            .order_by(Task.due_date.asc(), Task.id.asc())
            .limit(UPCOMING_LIMIT)
            .all()
        )
        upcoming_tasks = [build_task_response(task) for task in upcoming]

    unread = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .scalar()
    )

    return DashboardResponse(
        projects=projects,
        my_task_counts=my_task_counts,
        upcoming_tasks=upcoming_tasks,
        unread_notification_count=unread or 0,
    )
