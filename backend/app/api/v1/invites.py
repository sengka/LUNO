"""Proje davet bağlantıları (US-010, FR-021, sözleşme 5.8 / 5.9)."""
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_project_member, require_admin
from app.config import settings
from app.core.exceptions import AlreadyMemberException, InviteInvalidException
from app.database import get_db
from app.models.enums import ACTIVE_TASK_STATUSES, TaskStatus
from app.models.project import Project
from app.models.project_invite import ProjectInvite
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.user import User
from app.schemas.invite import (
    InviteCreateResponse,
    InviteProjectResponse,
    InviteUserSummary,
)

router = APIRouter(tags=["Proje Davetleri"])


def _as_utc(dt: datetime) -> datetime:
    """SQLite saat dilimi bilgisini saklamaz; okunan naive değerleri UTC kabul et."""
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _build_project_response(project: Project, db: Session) -> InviteProjectResponse:
    # progress_percent: aktif ana görevler içinde DONE olanların yüzdesi (FR-061)
    statuses = (
        db.query(Task.status)
        .filter(
            Task.project_id == project.id,
            Task.parent_id.is_(None),
            Task.status.in_(ACTIVE_TASK_STATUSES),
        )
        .all()
    )
    total = len(statuses)
    done = sum(1 for (s,) in statuses if s == TaskStatus.DONE)
    progress = round(done / total * 100, 1) if total else 0.0

    member_count = db.query(ProjectMember).filter(ProjectMember.project_id == project.id).count()
    creator = project.created_by

    return InviteProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        start_date=project.start_date,
        end_date=project.end_date,
        progress_percent=progress,
        member_count=member_count,
        created_by=InviteUserSummary.model_validate(creator) if creator else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.post(
    "/projects/{project_id}/invites",
    response_model=InviteCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Davet Bağlantısı Oluştur (US-010 / 5.8)",
)
def create_invite(
    project_id: int,
    current_user: User = Depends(require_admin),
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    """
    Proje için 7 gün geçerli bir davet bağlantısı oluşturur (FR-021).
    Erişim: YONETICI rolünde ve projenin üyesi olan kullanıcı (sözleşme 1.2).
    """
    now = datetime.now(timezone.utc)
    invite = ProjectInvite(
        token=secrets.token_urlsafe(32),
        project_id=project_id,
        created_by_id=current_user.id,
        expires_at=now + timedelta(days=settings.INVITE_EXPIRE_DAYS),
        created_at=now,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteCreateResponse(
        invite_url=f"{settings.FRONTEND_URL.rstrip('/')}/davet/{invite.token}",
        expires_at=_as_utc(invite.expires_at),
    )


@router.post(
    "/invites/{token}/accept",
    response_model=InviteProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Daveti Kabul Et (US-010 / 5.9)",
)
def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Giriş yapmış kullanıcıyı davet bağlantısının ait olduğu projeye ekler (FR-021).
    Bağlantı yoksa veya süresi dolmuşsa 400 INVITE_INVALID,
    kullanıcı zaten üyeyse 409 ALREADY_MEMBER döner.
    """
    invite = db.query(ProjectInvite).filter(ProjectInvite.token == token).first()
    if not invite or _as_utc(invite.expires_at) <= datetime.now(timezone.utc):
        raise InviteInvalidException()

    project = db.query(Project).filter(Project.id == invite.project_id).first()
    if not project:
        raise InviteInvalidException()

    already_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project.id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if already_member:
        raise AlreadyMemberException("Zaten bu projenin üyesisiniz.")

    db.add(ProjectMember(
        project_id=project.id,
        user_id=current_user.id,
        joined_at=datetime.now(timezone.utc),
    ))
    db.commit()
    db.refresh(project)

    return _build_project_response(project, db)
