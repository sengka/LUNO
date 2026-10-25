"""Görev oluşturma kuralları (sözleşme 6.2 ve 6.10).

`POST /projects/{project_id}/tasks` (6.2, #149) ve `POST /tasks/{task_id}/subtasks`
(6.10, #167) aynı alanları ve kuralları kullandığı için ikisi de `create_task`
fonksiyonunu çağırır. Kurallar tek yerde durur, iki uç nokta farklı davranmaz.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AssigneeNotMemberException,
    CustomAPIException,
    InvalidDateRangeException,
    NestedSubtaskNotAllowedException,
)
from app.models.enums import TaskStatus
from app.models.label import Label
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import SystemRole, User
from app.schemas.task import TaskCreateRequest


def _is_member(db: Session, project_id: int, user_id: int) -> bool:
    return (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
        is not None
    )


def create_task(
    db: Session,
    project_id: int,
    data: TaskCreateRequest,
    current_user: User,
    parent: Task | None = None,
) -> Task:
    """Görev veya alt görev oluşturur ve kaydeder.

    Çağıran uç nokta, kullanıcının projenin üyesi olduğunu önceden doğrulamalıdır
    (proje yoksa 404 PROJECT_NOT_FOUND / TASK_NOT_FOUND, üye değilse 403 PROJECT_ACCESS_DENIED).

    Kurallar:
    - Alt görevin alt görevi olamaz: 400 NESTED_SUBTASK_NOT_ALLOWED (6.10).
    - Teslim tarihi başlangıçtan önce olamaz: 400 INVALID_DATE_RANGE (FR-025).
    - Yönetici oluşturursa durum TODO; ekip üyesi oluşturursa ONAY_BEKLIYOR ve
      assignee_id yok sayılır (FR-026).
    - Atanan kişi projenin üyesi olmalı: 400 ASSIGNEE_NOT_MEMBER.
    - Etiketler aynı projeye ait olmalı: 422 VALIDATION_ERROR (FR-037).

    Henüz yapılmayanlar (ilgili tablolar/özellikler gelince eklenecek):
    - Ekip üyesi önerisinde yöneticilere TASK_PENDING_APPROVAL bildirimi (bildirimler, Sprint 6).
    - Atamada kapasite kontrolü ve 409 CAPACITY_EXCEEDED (6.6, FR-073, Sprint 7).
    """
    if parent is not None and parent.parent_id is not None:
        raise NestedSubtaskNotAllowedException()

    if data.start_date and data.due_date and data.due_date < data.start_date:
        raise InvalidDateRangeException("Teslim tarihi başlangıç tarihinden önce olamaz.")

    is_admin = current_user.role == SystemRole.YONETICI.value
    assignee_id = data.assignee_id if is_admin else None
    if assignee_id is not None and not _is_member(db, project_id, assignee_id):
        raise AssigneeNotMemberException()

    labels: list[Label] = []
    if data.label_ids:
        wanted = set(data.label_ids)
        labels = db.query(Label).filter(Label.project_id == project_id, Label.id.in_(wanted)).all()
        if len(labels) != len(wanted):
            raise CustomAPIException(
                status_code=422,
                code="VALIDATION_ERROR",
                message="Lütfen hatalı alanları düzeltin.",
                fields={"label_ids": "Etiket bulunamadı veya bu projeye ait değil."},
            )

    now = datetime.now(timezone.utc)
    task = Task(
        project_id=project_id,
        parent_id=parent.id if parent is not None else None,
        title=data.title,
        description=data.description,
        status=TaskStatus.TODO if is_admin else TaskStatus.ONAY_BEKLIYOR,
        priority=data.priority,
        story_points=data.story_points,
        start_date=data.start_date,
        due_date=data.due_date,
        assignee_id=assignee_id,
        created_by_id=current_user.id,
        sprint_id=data.sprint_id,
        created_at=now,
        updated_at=now,
    )
    task.labels = labels
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
