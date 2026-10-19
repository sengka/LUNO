from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.models.enums import ACTIVE_TASK_STATUSES, TaskStatus
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse,
    ProjectMemberAddRequest,
    ProjectMemberResponse,
    UserSummary
)
from app.core.exceptions import (
    InvalidDateRangeException,
    ProjectNotFoundException,
    ProjectAccessDeniedException,
    UserNotFoundException,
    AlreadyMemberException,
    MemberNotFoundException,
    CannotRemoveSelfException
)
from app.api.deps import get_current_user, require_admin, get_project_member


router = APIRouter(prefix="/projects", tags=["Projeler"])

def build_member_response(member: ProjectMember) -> ProjectMemberResponse:
    """Helper to convert ProjectMember to ProjectMemberResponse."""
    return ProjectMemberResponse(
        user=UserSummary(
            id=member.user.id,
            full_name=member.user.full_name,
            avatar_url=member.user.avatar_url
        ),
        email=member.user.email,
        system_role=member.user.role,
        technical_role=member.technical_role,
        capacity_points=member.capacity_points,
        joined_at=member.joined_at
    )

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

@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="Projelerimi Listele (US-007 / 5.1)"
)
def list_my_projects(
    page: int = Query(1, ge=1, description="Sayfa numarası (varsayılan: 1)"),
    limit: int = Query(10, ge=1, le=100, description="Sayfa başına öge sayısı (varsayılan: 10)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Oturum açmış kullanıcının üyesi olduğu projeleri listeler (FR-017).
    """
    query = (
        db.query(Project)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .filter(ProjectMember.user_id == current_user.id)
    )

    total = query.count()
    offset = (page - 1) * limit
    projects = query.order_by(Project.id.asc()).offset(offset).limit(limit).all()

    return ProjectListResponse(
        items=[build_project_response(p, db) for p in projects],
        total=total,
        page=page,
        limit=limit
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

@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Proje Detayı (US-007 / US-022 / 5.3)"
)
def get_project_detail(
    project_id: int,
    membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db)
):
    """
    Belirtilen projenin detayını getirir.
    Kullanıcı projenin üyesi olmalıdır (FR-013).
    """
    return build_project_response(membership.project, db)

@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Projeyi Düzenle (US-008 / 5.4)"
)
def update_project(
    project_id: int,
    project_in: ProjectUpdate,
    current_user: User = Depends(require_admin),
    membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db)
):
    """
    Mevcut bir projenin bilgilerini düzenler.
    Yalnızca YONETICI rolüne sahip ve projenin üyesi olan kullanıcılar düzenleyebilir (FR-013, FR-018).
    Bitiş tarihi başlangıç tarihinden önce olamaz (400 INVALID_DATE_RANGE).
    """
    project = membership.project

    new_start = project_in.start_date if project_in.start_date is not None else project.start_date
    new_end = project_in.end_date if project_in.end_date is not None else project.end_date

    if new_end < new_start:
        raise InvalidDateRangeException("Bitiş tarihi başlangıç tarihinden önce olamaz.")

    if project_in.name is not None:
        project.name = project_in.name
    if project_in.description is not None:
        project.description = project_in.description
    if project_in.start_date is not None:
        project.start_date = project_in.start_date
    if project_in.end_date is not None:
        project.end_date = project_in.end_date

    project.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)

    return build_project_response(project, db)

@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Projeyi Sil (US-009 / 5.5)"
)
def delete_project(
    project_id: int,
    current_user: User = Depends(require_admin),
    membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db)
):
    """
    Belirtilen projeyi siler.
    Yalnızca YONETICI rolüne sahip ve projenin üyesi olan kullanıcılar silebilir (FR-013, FR-019).
    Projeye bağlı görevler ve üyelikler de birlikte silinir (FR-020).
    """
    db.delete(membership.project)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get(
    "/{project_id}/members",
    response_model=List[ProjectMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="Proje Üyelerini Listele (US-010 / US-029 / 5.6)"
)
def list_project_members(
    project_id: int,
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db)
):
    """
    Belirtilen projenin üyelerini listeler (FR-014).
    Yalnızca projenin üyesi olan kullanıcılar erişebilir (FR-013).
    """
    members = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.joined_at.asc())
        .all()
    )
    return [build_member_response(m) for m in members]

@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Projeye Üye Ekle (US-010 / 5.7)"
)
def add_project_member(
    project_id: int,
    member_in: ProjectMemberAddRequest,
    current_user: User = Depends(require_admin),
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db)
):
    """
    E-posta adresi ile projeye yeni ekip üyesi ekler (FR-021).
    Yalnızca YONETICI rolüne sahip ve projenin üyesi olan kullanıcılar ekleyebilir.
    """
    target_user = db.query(User).filter(User.email == member_in.email).first()
    if not target_user:
        raise UserNotFoundException("Bu e-posta ile kayıtlı kullanıcı bulunamadı.")

    already_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == target_user.id)
        .first()
    )
    if already_member:
        raise AlreadyMemberException("Bu kullanıcı zaten projenin üyesi.")

    now = datetime.now(timezone.utc)
    new_member = ProjectMember(
        project_id=project_id,
        user_id=target_user.id,
        technical_role=member_in.technical_role,
        capacity_points=None,
        joined_at=now
    )
    db.add(new_member)
    db.commit()
    db.refresh(new_member)

    return build_member_response(new_member)

@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Üyeyi Projeden Çıkar (US-010 / 5.10)"
)
def remove_project_member(
    project_id: int,
    user_id: int,
    current_user: User = Depends(require_admin),
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db)
):
    """
    Belirtilen üyeyi projeden çıkarır (FR-022).
    Yalnızca YONETICI rolüne sahip ve projenin üyesi olan kullanıcılar çıkarabilir.
    Yöneticinin kendisini çıkarması engellenmiştir (400 CANNOT_REMOVE_SELF).
    Çıkarılan üyeye atanmış görevlerin sorumlusu boşaltılır (assignee = null).
    """
    if current_user.id == user_id:
        raise CannotRemoveSelfException("Kendinizi projeden çıkaramazsınız.")

    member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .first()
    )
    if not member:
        raise MemberNotFoundException("Bu kullanıcı projenin üyesi değil.")

    # Çıkarılan üyeye atanmış görevlerin assignee_id alanını null yap (FR-022)
    db.query(Task).filter(
        Task.project_id == project_id,
        Task.assignee_id == user_id
    ).update({Task.assignee_id: None}, synchronize_session=False)

    db.delete(member)
    db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)





