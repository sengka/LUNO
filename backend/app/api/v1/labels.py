"""Proje etiketleri (US-033, FR-037, sözleşme 6.11)."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_project_member
from app.core.exceptions import LabelExistsException
from app.database import get_db
from app.models.label import Label
from app.models.project_member import ProjectMember
from app.schemas.label import LabelCreateRequest, LabelResponse

router = APIRouter(tags=["Etiketler"])


@router.get(
    "/projects/{project_id}/labels",
    response_model=list[LabelResponse],
    status_code=status.HTTP_200_OK,
    summary="Etiketleri listele (US-033 / 6.11)",
)
def list_labels(
    project_id: int,
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    """
    Projenin etiketlerini ada göre sıralı döner.
    Erişim: proje üyesi. Proje yoksa 404 PROJECT_NOT_FOUND, üye değilse 403 PROJECT_ACCESS_DENIED.
    """
    return (
        db.query(Label)
        .filter(Label.project_id == project_id)
        .order_by(func.lower(Label.name))
        .all()
    )


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Etiket oluştur (US-033 / 6.11)",
)
def create_label(
    project_id: int,
    label_in: LabelCreateRequest,
    _membership: ProjectMember = Depends(get_project_member),
    db: Session = Depends(get_db),
):
    """
    Projeye yeni etiket ekler (FR-037).
    Erişim: proje üyesi. Aynı projede aynı adla (büyük/küçük harf farkı gözetmeden)
    etiket varsa 409 LABEL_EXISTS.
    """
    exists = (
        db.query(Label)
        .filter(Label.project_id == project_id, func.lower(Label.name) == label_in.name.lower())
        .first()
    )
    if exists:
        raise LabelExistsException()

    label = Label(project_id=project_id, name=label_in.name, color=label_in.color)
    db.add(label)
    db.commit()
    db.refresh(label)
    return label
