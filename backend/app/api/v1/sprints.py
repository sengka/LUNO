"""Sprintler (US-040, US-041; sözleşme 11).

Şu an: sprint detayı ve ilerlemesi (11.2 GET, US-041, FR-068).
Sprint listeleme/oluşturma (11.1), düzenleme/silme (11.2 PATCH/DELETE) ve görev ekleme (11.3)
bu dosyaya eklenebilir; ilerleme hesabı için `app/services/sprints.build_sprint_response` kullanılmalı.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.exceptions import ProjectAccessDeniedException, SprintNotFoundException
from app.database import get_db
from app.models.project_member import ProjectMember
from app.models.sprint import Sprint
from app.models.user import User
from app.schemas.sprint import SprintResponse
from app.services.sprints import build_sprint_response

router = APIRouter(tags=["Sprintler"])


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
    """
    Sprint bilgisini ve ilerlemesini döner (US-041, FR-068). Erişim: proje üyesi.
    - total_points: Sprintteki aktif görevlerin efor puanı toplamı (puansız görev 0 sayılır)
    - done_points: DONE görevlerin efor puanı toplamı
    - progress_percent: done_points / total_points × 100; görev veya puan yoksa 0
    - is_active: Bugün (UTC) sprint tarihleri arasındaysa true
    - Sprint yoksa 404 SPRINT_NOT_FOUND, proje üyesi değilse 403 PROJECT_ACCESS_DENIED
    """
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if sprint is None:
        raise SprintNotFoundException()

    is_member = (
        db.query(ProjectMember)
        .filter(ProjectMember.project_id == sprint.project_id, ProjectMember.user_id == current_user.id)
        .first()
    )
    if is_member is None:
        raise ProjectAccessDeniedException()

    return build_sprint_response(db, sprint)
