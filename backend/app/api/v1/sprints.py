"""Sprintler (US-040, US-041; sözleşme 11.1 – 11.3)."""

from datetime import date

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_member, require_admin
from app.core.exceptions import (
    InvalidDateRangeException,
    ProjectAccessDeniedException,
    SprintNotFoundException,
    SprintOverlapException,
    TaskNotFoundException,
)
from app.database import get_db
from app.models.project_member import ProjectMember
from app.models.sprint import Sprint
from app.models.task import Task
from app.models.user import User
from app.schemas.sprint import (
    SprintCreate,
    SprintResponse,
    SprintTasksAddRequest,
    SprintTasksAddResponse,
    SprintUpdate,
)
from app.services.sprints import build_sprint_response

router = APIRouter(tags=["Sprintler"])


def _get_sprint_and_check_member(db: Session, sprint_id: int, user_id: int) -> Sprint:
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if sprint is None:
        raise SprintNotFoundException()

    is_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == sprint.project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if is_member is None:
        raise ProjectAccessDeniedException()
    return sprint


def _check_sprint_dates(
    db: Session,
    project_id: int,
    start_date: date,
    end_date: date,
    exclude_sprint_id: int | None = None,
) -> None:
    if end_date < start_date:
        raise InvalidDateRangeException()

    overlap_query = db.query(Sprint.id).filter(
        Sprint.project_id == project_id,
        Sprint.start_date <= end_date,
        Sprint.end_date >= start_date,
    )
    if exclude_sprint_id is not None:
        overlap_query = overlap_query.filter(Sprint.id != exclude_sprint_id)

    if overlap_query.first() is not None:
        raise SprintOverlapException()


@router.get(
    "/projects/{project_id}/sprints",
    response_model=list[SprintResponse],
    status_code=status.HTTP_200_OK,
    summary="Sprintleri listele (US-040 / 11.1)",
)
def list_project_sprints(
    project_id: int,
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    sprints = (
        db.query(Sprint)
        .filter(Sprint.project_id == project_id)
        .order_by(Sprint.start_date.asc(), Sprint.id.asc())
        .all()
    )
    return [build_sprint_response(db, sprint) for sprint in sprints]


@router.post(
    "/projects/{project_id}/sprints",
    response_model=SprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sprint oluştur (US-040 / 11.1)",
)
def create_sprint(
    project_id: int,
    payload: SprintCreate,
    _admin: User = Depends(require_admin),
    _member: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    _check_sprint_dates(db, project_id, payload.start_date, payload.end_date)

    sprint = Sprint(
        project_id=project_id,
        name=payload.name,
        goal=payload.goal,
        start_date=payload.start_date,
        end_date=payload.end_date,
        capacity_points=payload.capacity_points,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)
    return build_sprint_response(db, sprint)


@router.get(
    "/sprints/{sprint_id}",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
    summary="Sprint detayı ve ilerlemesi (US-041 / 11.2)",
)
def get_sprint(
    sprint_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sprint = _get_sprint_and_check_member(db, sprint_id, current_user.id)
    return build_sprint_response(db, sprint)


@router.patch(
    "/sprints/{sprint_id}",
    response_model=SprintResponse,
    status_code=status.HTTP_200_OK,
    summary="Sprint düzenle (US-040, US-025 / 11.2)",
)
def update_sprint(
    sprint_id: int,
    payload: SprintUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sprint = _get_sprint_and_check_member(db, sprint_id, admin.id)
    data = payload.model_dump(exclude_unset=True)

    new_start = data.get("start_date", sprint.start_date)
    new_end = data.get("end_date", sprint.end_date)
    if "start_date" in data or "end_date" in data:
        _check_sprint_dates(
            db, sprint.project_id, new_start, new_end, exclude_sprint_id=sprint.id
        )

    for field, value in data.items():
        setattr(sprint, field, value)

    db.commit()
    db.refresh(sprint)
    return build_sprint_response(db, sprint)


@router.delete(
    "/sprints/{sprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sprint sil (US-040 / 11.2)",
)
def delete_sprint(
    sprint_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sprint = _get_sprint_and_check_member(db, sprint_id, admin.id)
    db.query(Task).filter(Task.sprint_id == sprint.id).update({Task.sprint_id: None})
    db.delete(sprint)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/sprints/{sprint_id}/tasks",
    response_model=SprintTasksAddResponse,
    status_code=status.HTTP_200_OK,
    summary="Görevleri sprinte ekle (US-040 / 11.3)",
)
def add_tasks_to_sprint(
    sprint_id: int,
    payload: SprintTasksAddRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sprint = _get_sprint_and_check_member(db, sprint_id, admin.id)
    unique_ids = list(dict.fromkeys(payload.task_ids))

    tasks = (
        db.query(Task)
        .filter(Task.id.in_(unique_ids), Task.project_id == sprint.project_id)
        .all()
    )
    if len(tasks) != len(unique_ids):
        raise TaskNotFoundException()

    for task in tasks:
        task.sprint_id = sprint.id
    db.commit()

    sprint_resp = build_sprint_response(db, sprint)
    capacity_warning = (
        sprint.capacity_points is not None
        and sprint_resp.total_points > sprint.capacity_points
    )
    return SprintTasksAddResponse(
        **sprint_resp.model_dump(),
        capacity_warning=capacity_warning,
    )


@router.delete(
    "/sprints/{sprint_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Görevi sprintten çıkar (US-040 / 11.3)",
)
def remove_task_from_sprint(
    sprint_id: int,
    task_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    sprint = _get_sprint_and_check_member(db, sprint_id, admin.id)
    task = (
        db.query(Task)
        .filter(
            Task.id == task_id,
            Task.project_id == sprint.project_id,
            Task.sprint_id == sprint.id,
        )
        .first()
    )
    if task is None:
        raise TaskNotFoundException()

    task.sprint_id = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
