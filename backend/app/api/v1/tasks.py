from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User, SystemRole
from app.models.project import Project
from app.models.task import Task
from app.models.label import Label
from app.models.project_member import ProjectMember
from app.models.enums import TaskStatus
from app.schemas.task import (
    TaskCreateRequest,
    TaskLabel,
    TaskStatusUpdateRequest,
    TaskAssigneeUpdateRequest,
    TaskResponse,
    TaskListResponse,
)
from app.services.tasks import create_task
from app.schemas.project import UserSummary
from app.core.exceptions import (
    ProjectAccessDeniedException,
    ProjectNotFoundException,
    TaskNotFoundException,
    TaskNotActiveException,
    NotTaskAssigneeException,
    AssigneeNotMemberException,
    ForbiddenException,
)
from app.api.deps import get_current_user

router = APIRouter(tags=["Görevler"])


def _user_summary(user: User | None) -> UserSummary | None:
    if user is None:
        return None
    return UserSummary(id=user.id, full_name=user.full_name, avatar_url=user.avatar_url)


def build_task_response(task: Task) -> TaskResponse:
    """Task modelini sözleşme 2. bölümdeki Task nesnesine çevirir.

    Henüz tablosu olmayan alanlar (depends_on, comment_count, file_count)
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
        labels=[TaskLabel.model_validate(label) for label in task.labels],
        subtask_count=len(subtasks),
        subtask_done_count=sum(1 for st in subtasks if st.status == TaskStatus.DONE),
        depends_on=[],
        risk_level=None,
        comment_count=0,
        file_count=0,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Görev oluştur (US-011 / 6.2)",
)
def create_project_task(
    project_id: int,
    task_in: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Projeye yeni görev ekler (US-011, FR-024, FR-025, sözleşme 6.2).
    Erişim: Yönetici ve proje üyesi (FR-012, FR-013).
    - Proje yoksa 404 PROJECT_NOT_FOUND
    - Proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    - Ekip üyesi eklemeye çalışırsa 403 FORBIDDEN (Sprint 8'de US-030 ile onay mekanizması gelecek)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundException()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise ProjectAccessDeniedException()

    if current_user.role != SystemRole.YONETICI.value:
        raise ForbiddenException("Bu işlem için yetkiniz yok.")

    task = create_task(db, project_id, task_in, current_user, parent=None)
    return build_task_response(task)


@router.get(
    "/projects/{project_id}/tasks",
    response_model=TaskListResponse,
    status_code=status.HTTP_200_OK,
    summary="Görevleri listele ve filtrele (US-011 / 6.1)",
)
def list_project_tasks(
    project_id: int,
    search: Optional[str] = Query(None, description="Görev adında arama"),
    assignee_id: Optional[int] = Query(None, description="Atanan kişi"),
    status: Optional[str] = Query(None, description="Durum (virgülle birden fazla: TODO,IN_PROGRESS)"),
    priority: Optional[str] = Query(None, description="Öncelik"),
    label_id: Optional[int] = Query(None, description="Etiket"),
    sprint_id: Optional[int] = Query(None, description="Sprint"),
    parent_id: Optional[int] = Query(None, description="Alt görevler için ana görev id'si"),
    include_pending: bool = Query(False, description="Onay bekleyen ve reddedilen görevleri de getir"),
    page: int = Query(1, ge=1, description="Sayfa numarası"),
    limit: int = Query(10, ge=1, le=100, description="Sayfa boyutu"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Projenin görevlerini listeler (US-011, US-034, FR-041, sözleşme 6.1).
    Erişim: Proje üyesi (FR-013).
    - Proje yoksa 404 PROJECT_NOT_FOUND
    - Proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    - parent_id verilmezse sadece ana görevler döner.
    - include_pending false ise ONAY_BEKLIYOR ve REDDEDILDI görevler filtrelenir.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ProjectNotFoundException()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise ProjectAccessDeniedException()

    query = db.query(Task).filter(Task.project_id == project_id)

    if parent_id is not None:
        query = query.filter(Task.parent_id == parent_id)
    else:
        query = query.filter(Task.parent_id.is_(None))

    if not include_pending:
        query = query.filter(
            Task.status.notin_([TaskStatus.ONAY_BEKLIYOR, TaskStatus.REDDEDILDI])
        )

    if search:
        query = query.filter(Task.title.ilike(f"%{search.strip()}%"))

    if assignee_id is not None:
        query = query.filter(Task.assignee_id == assignee_id)

    if status:
        status_list = [s.strip() for s in status.split(",") if s.strip()]
        if status_list:
            query = query.filter(Task.status.in_(status_list))

    if priority:
        query = query.filter(Task.priority == priority)

    if sprint_id is not None:
        query = query.filter(Task.sprint_id == sprint_id)

    if label_id is not None:
        query = query.filter(Task.labels.any(Label.id == label_id))

    total = query.count()
    tasks = query.order_by(Task.id.desc()).offset((page - 1) * limit).limit(limit).all()

    return TaskListResponse(
        items=[build_task_response(t) for t in tasks],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Görev detayı (US-011 / 6.3)",
)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Görev detayını döner (US-011, sözleşme 6.3).
    Erişim: Görevin ait olduğu projenin üyesi (FR-013).
    - Görev yoksa 404 TASK_NOT_FOUND
    - Proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise TaskNotFoundException()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise ProjectAccessDeniedException()

    return build_task_response(task)


@router.patch(
    "/tasks/{task_id}/assignee",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Görevi ata (US-012 / 6.6)",
)
def update_task_assignee(
    task_id: int,
    assignee_in: TaskAssigneeUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Görevi bir proje üyesine atar veya atamasını kaldırır (US-012, FR-030, sözleşme 6.6).
    Erişim: Yönetici (YONETICI rolünde ve projenin üyesi, sözleşme 1.2).
    - Görev yoksa 404 TASK_NOT_FOUND
    - Proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    - Yönetici değilse 403 FORBIDDEN
    - Atanan kişi projenin üyesi değilse 400 ASSIGNEE_NOT_MEMBER
    - Kapasite kontrolü Sprint 7'de eklenecektir; confirm_over_capacity kabul edilip yok sayılır.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise TaskNotFoundException()

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if not member:
        raise ProjectAccessDeniedException()

    if current_user.role != SystemRole.YONETICI.value:
        raise ForbiddenException("Bu işlem için yetkiniz yok.")

    if assignee_in.assignee_id is not None:
        target_member = (
            db.query(ProjectMember)
            .filter(ProjectMember.project_id == task.project_id, ProjectMember.user_id == assignee_in.assignee_id)
            .first()
        )
        if not target_member:
            raise AssigneeNotMemberException()

    task.assignee_id = assignee_in.assignee_id
    task.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)

    return build_task_response(task)


@router.patch(
    "/tasks/{task_id}/status",
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


@router.post(
    "/tasks/{task_id}/subtasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Alt görev ekle (US-033 / 6.10)",
)
def create_subtask(
    task_id: int,
    task_in: TaskCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ana göreve bağlı alt görev oluşturur (US-033, FR-038, FR-039, sözleşme 6.10).
    Alanlar ve kurallar görev oluşturmayla (6.2) aynıdır; proje ve `parent_id` ana görevden alınır.
    Erişim: ana görevin projesinin üyesi.
    - Ana görev yoksa 404 TASK_NOT_FOUND, proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    - Ana görev zaten bir alt görevse 400 NESTED_SUBTASK_NOT_ALLOWED
    - Ekip üyesi eklerse alt görev ONAY_BEKLIYOR durumunda kaydedilir (FR-026)
    """
    parent = db.query(Task).filter(Task.id == task_id).first()
    if not parent:
        raise TaskNotFoundException()

    is_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == parent.project_id, ProjectMember.user_id == current_user.id)
        .first()
        is not None
    )
    if not is_member:
        raise ProjectAccessDeniedException()

    subtask = create_task(db, parent.project_id, task_in, current_user, parent=parent)
    return build_task_response(subtask)
