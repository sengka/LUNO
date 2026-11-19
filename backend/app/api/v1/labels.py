"""Proje etiketleri (US-033, FR-037, sözleşme 6.11)."""

import unicodedata

from fastapi import APIRouter, Depends, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_project_member
from app.core.exceptions import LabelExistsException
from app.database import get_db
from app.models.label import Label
from app.models.project_member import ProjectMember
from app.schemas.label import LabelCreateRequest, LabelResponse

router = APIRouter(tags=["Etiketler"])


def label_key(name: str) -> str:
    """Etiket adını büyük/küçük harf farkı gözetmeden karşılaştırmak için anahtar (#219, #253).

    SQLite'ın lower() fonksiyonu yalnızca İngilizce harfleri küçülttüğü için karşılaştırma
    Python'da yapılır. Türkçe noktalı/noktasız i (İ, I, ı, i) aynı harf sayılır; böylece
    "Ödeme" = "ödeme", "IŞIK" = "ışık", "API" = "api" olur.
    """
    text = unicodedata.normalize("NFC", name.strip())
    text = text.replace("İ", "i").replace("ı", "i")
    return unicodedata.normalize("NFC", text.casefold()).replace("i̇", "i")


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
    Projenin etiketlerini ada göre sıralı döner (büyük/küçük harf farkı gözetmeden).
    Erişim: proje üyesi. Proje yoksa 404 PROJECT_NOT_FOUND, üye değilse 403 PROJECT_ACCESS_DENIED.
    """
    labels = db.query(Label).filter(Label.project_id == project_id).all()
    return sorted(labels, key=lambda label: (label_key(label.name), label.id))


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
    Erişim: proje üyesi. Aynı projede aynı adla (büyük/küçük harf ve Türkçe karakter farkı
    gözetmeden) etiket varsa 409 LABEL_EXISTS. Aynı etiket aynı anda iki kez gönderilirse
    ikincisi de 409 LABEL_EXISTS alır (veritabanı benzersizlik kuralı).
    """
    wanted = label_key(label_in.name)
    names = db.query(Label.name).filter(Label.project_id == project_id).all()
    if any(label_key(name) == wanted for (name,) in names):
        raise LabelExistsException()

    label = Label(project_id=project_id, name=label_in.name, color=label_in.color)
    db.add(label)
    try:
        db.commit()
    except IntegrityError:
        # Kontrolden sonra, kaydetmeden önce başka bir istek aynı etiketi eklemiş.
        db.rollback()
        raise LabelExistsException()
    db.refresh(label)
    return label
