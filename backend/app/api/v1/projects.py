from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.enums import ACTIVE_TASK_STATUSES, TaskStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    UserSummary
)
from app.core.exceptions import InvalidDateRangeException
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/projects", tags=["Projeler"])

def build_project_response(project: Project, db: Session) -> ProjectResponse:
    """Helper to compute progress_percent and member_count for ProjectResponse."""
    # Active parent tasks progress percent (FR-061)
    active_tasks = db.query(Task).filter(
        Task.project_id == project.id,
        Task.parent_id.is_(None),
        Task.status.in_(ACTIVE_TASK_STATUSES)
    ).all()
    total_active = len(active_tasks)
    progress_percent = (
        round((sum(1 for t in active_tasks if t.status == TaskStatus.DONE) / total_active) * 100, 1)
        if total_active > 0 else 0.0
    )

    member_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()

    created_by_summary = None
    if project.created_by:
        created_by_summary = UserSummary(
            id=project.created_by.id,
            full_name=project.created_by.full_name,
            avatar_url=project.created_by.avatar_url
        )
    elif project.created_by_id:
        creator = db.query(User).filter(User.id == project.created_by_id).first()
        if creator:
            created_by_summary = UserSummary(
                id=creator.id,
                full_name=creator.full_name,
                avatar_url=creator.avatar_url
            )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        progress_percent=progress_percent,
        member_count=member_count,
        created_by=created_by_summary,
        created_at=project.created_at,
        updated_at=project.updated_at
    )

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Proje Oluştur (US-006 / 5.2)"
)
def create_project(
    project_in: ProjectCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Yeni bir proje oluşturur.
    Yalnızca YONETICI rolüne sahip kullanıcılar oluşturabilir.
    Oluşturan yönetici otomatik olarak projenin üyesi yapılır (FR-015).
    Bitiş tarihi başlangıç tarihinden önce olamaz (400 INVALID_DATE_RANGE, FR-016).
    """
    if project_in.end_date < project_in.start_date:
        raise InvalidDateRangeException("Bitiş tarihi başlangıç tarihinden önce olamaz.")

    now = datetime.now(timezone.utc)
    new_project = Project(
        name=project_in.name,
        description=project_in.description,
        start_date=project_in.start_date,
        end_date=project_in.end_date,
        created_by_id=current_user.id,
        created_at=now,
        updated_at=now
    )
    db.add(new_project)
    db.flush()  # to obtain new_project.id

    # Oluşturan yönetici otomatik olarak proje üyesi eklenir
    creator_member = ProjectMember(
        project_id=new_project.id,
        user_id=current_user.id,
        technical_role=None,
        capacity_points=None,
        joined_at=now
    )
    db.add(creator_member)
    db.commit()
    db.refresh(new_project)

    return build_project_response(new_project, db)
