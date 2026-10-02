from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.task import TaskStatus
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskAssign, TaskStatusUpdate, TaskDatesUpdate, TaskResponse
)
from app.services.task_service import TaskService
from app.services.project_service import ProjectService

router = APIRouter(prefix="/tasks", tags=["Görev Yönetimi"])

@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED, summary="Yeni Görev Oluştur")
def create_task(task_in: TaskCreate, db: Session = Depends(get_db)):
    """
    Yeni bir görev oluşturur ve projeye bağlar.
    """
    project = ProjectService.get_project(db, task_in.project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_in.project_id} ID'li proje bulunamadı. Görev oluşturulamadı."
        )
    return TaskService.create_task(db, task_in)

@router.get("/", response_model=List[TaskResponse], summary="Görevleri Listele & Filtrele")
def list_tasks(
    project_id: Optional[int] = Query(None, description="Proje ID'sine göre filtrele"),
    assigned_to_id: Optional[int] = Query(None, description="Atanan kullanıcıya göre filtrele"),
    status: Optional[TaskStatus] = Query(None, description="Duruma göre filtrele (TODO, IN_PROGRESS, DONE)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Görevleri listeler. Proje ID, atanan kullanıcı ve durum filtrelerini destekler.
    """
    return TaskService.get_tasks(
        db,
        project_id=project_id,
        assigned_to_id=assigned_to_id,
        status=status,
        skip=skip,
        limit=limit
    )

@router.get("/{task_id}", response_model=TaskResponse, summary="Görev Detayı Getir")
def get_task(task_id: int, db: Session = Depends(get_db)):
    """
    ID'ye göre görev detayını getirir.
    """
    task = TaskService.get_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_id} ID'li görev bulunamadı."
        )
    return task

@router.put("/{task_id}", response_model=TaskResponse, summary="Görev Güncelle")
def update_task(task_id: int, task_in: TaskUpdate, db: Session = Depends(get_db)):
    """
    Görev detaylarını günceller.
    """
    updated_task = TaskService.update_task(db, task_id, task_in)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_id} ID'li görev bulunamadı."
        )
    return updated_task

@router.patch("/{task_id}/assign", response_model=TaskResponse, summary="Görevi Kişiye Ata")
def assign_task(task_id: int, assign_in: TaskAssign, db: Session = Depends(get_db)):
    """
    Görevi belirli bir kullanıcıya atar (`assigned_to_id`).
    """
    updated_task = TaskService.assign_task(db, task_id, assign_in)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_id} ID'li görev bulunamadı."
        )
    return updated_task

@router.patch("/{task_id}/status", response_model=TaskResponse, summary="Görev Durumunu Güncelle")
def update_task_status(task_id: int, status_in: TaskStatusUpdate, db: Session = Depends(get_db)):
    """
    Görevin durumunu günceller (`TODO`, `IN_PROGRESS`, `DONE`).
    `DONE` yapıldığında `completed_at` tarihi otomatik atanır.
    """
    updated_task = TaskService.update_task_status(db, task_id, status_in)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_id} ID'li görev bulunamadı."
        )
    return updated_task

@router.patch("/{task_id}/dates", response_model=TaskResponse, summary="Görev Tarihlerini Güncelle")
def update_task_dates(task_id: int, dates_in: TaskDatesUpdate, db: Session = Depends(get_db)):
    """
    Görevin başlangıç (`start_date`) ve bitiş/teslim (`due_date`) tarihlerini günceller.
    Takvim ve Gantt görünümleri için kullanılır.
    """
    updated_task = TaskService.update_task_dates(db, task_id, dates_in)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_id} ID'li görev bulunamadı."
        )
    return updated_task

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Görev Sil")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """
    Görevi siler.
    """
    success = TaskService.delete_task(db, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{task_id} ID'li görev bulunamadı."
        )
    return None
