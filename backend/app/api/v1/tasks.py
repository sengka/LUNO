from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, SystemRole
from app.models.task import Task
from app.models.project_member import ProjectMember
from app.models.enums import TaskStatus
from app.schemas.task import TaskStatusUpdateRequest, TaskResponse
from app.schemas.project import UserSummary
from app.core.exceptions import (
    TaskNotFoundException,
    TaskNotActiveException,
    NotTaskAssigneeException,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["Görevler"])


def _user_summary(user: User | None) -> UserSummary | None:
    if user is None:
        return None
    return UserSummary(id=user.id, full_name=user.full_name, avatar_url=user.avatar_url)


def build_task_response(task: Task) -> TaskResponse:
    """Task modelini sözleşme 2. bölümdeki Task nesnesine çevirir.

    Henüz tablosu olmayan alanlar (labels, depends_on, comment_count, file_count)
    boş/0 döner; risk_level Sprint 7'de (bölüm 12.1) hesaplanacağı için şimdilik null.
    """
    subtasks = task.subtasks or []
    return TaskResponse(
        id=task.id,
        project_id=task.project_id,
        parent_id=task.parent_id,
        title=task.title,
        description=task.description,
        status=task.status.value,
        priority=task.priority.value if task.priority else None,
        story_points=task.story_points,
        start_date=task.start_date,
        due_date=task.due_date,
        assignee=_user_summary(task.assignee),
        created_by=_user_summary(task.created_by),
        sprint_id=task.sprint_id,
        labels=[],
        subtask_count=len(subtasks),
        subtask_done_count=sum(1 for st in subtasks if st.status == TaskStatus.DONE),
        depends_on=[],
        risk_level=None,
        comment_count=0,
        file_count=0,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Görev durumunu değiştir (US-014 / 6.5)",
)
def update_task_status(
    task_id: int,
    status_in: TaskStatusUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Görev durumunu değiştirir (US-014, FR-033, FR-034, sözleşme 6.5).
    Erişim: görevin atandığı kişi veya Yönetici (YONETICI rolünde ve projenin üyesi, sözleşme 1.2).
    - Yetkisi yoksa 403 NOT_TASK_ASSIGNEE
    - Onay bekleyen veya reddedilen görevde 400 TASK_NOT_ACTIVE
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise TaskNotFoundException()

    is_assignee = task.assignee_id is not None and task.assignee_id == current_user.id
    is_project_admin = (
        current_user.role == SystemRole.YONETICI.value
        and db.query(ProjectMember)
        .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == current_user.id)
        .first()
        is not None
    )
    if not (is_assignee or is_project_admin):
        raise NotTaskAssigneeException()

    if task.status in (TaskStatus.ONAY_BEKLIYOR, TaskStatus.REDDEDILDI):
        raise TaskNotActiveException()

    task.status = TaskStatus(status_in.status.value)
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)

    return build_task_response(task)
