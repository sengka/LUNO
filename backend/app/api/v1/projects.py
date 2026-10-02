from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Proje Yönetimi"])

@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Yeni Proje Oluştur")
def create_project(project_in: ProjectCreate, db: Session = Depends(get_db)):
    """
    Yeni bir proje oluşturur (isim, açıklama, başlangıç-bitiş tarihi, durum).
    """
    return ProjectService.create_project(db, project_in)

@router.get("/", response_model=List[ProjectResponse], summary="Projeleri Listele")
def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: Optional[str] = Query(None, description="Proje durumuna göre filtrele (PLANNING, ACTIVE, ON_HOLD, COMPLETED, CANCELLED)"),
    db: Session = Depends(get_db)
):
    """
    Tüm projeleri listeler. Sayfalama ve durum bazlı filtreleme destekler.
    """
    return ProjectService.get_projects(db, skip=skip, limit=limit, status=status)

@router.get("/{project_id}", response_model=ProjectResponse, summary="Proje Detayı Getir")
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    ID'ye göre proje detayını getirir.
    """
    project = ProjectService.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{project_id} ID'li proje bulunamadı."
        )
    return project

@router.put("/{project_id}", response_model=ProjectResponse, summary="Proje Düzenle / Güncelle")
def update_project(project_id: int, project_in: ProjectUpdate, db: Session = Depends(get_db)):
    """
    Proje bilgilerini günceller (isim, açıklama, başlangıç-bitiş tarihi, durum).
    """
    updated_project = ProjectService.update_project(db, project_id, project_in)
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{project_id} ID'li proje bulunamadı."
        )
    return updated_project

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Proje Sil")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Projeyi ve projeye ait tüm görevleri siler.
    """
    success = ProjectService.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{project_id} ID'li proje bulunamadı."
        )
    return None
