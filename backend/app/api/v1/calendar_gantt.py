from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.calendar_gantt import CalendarEventResponse, GanttTimelineResponse
from app.services.report_service import ReportService

router = APIRouter(tags=["Takvim & Gantt Görünümü"])

@router.get("/calendar/events", response_model=List[CalendarEventResponse], summary="Takvim Etkinlik Verilerini Getir")
def get_calendar_events(
    start_date: Optional[date] = Query(None, description="Başlangıç tarihi (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Bitiş tarihi (YYYY-MM-DD)"),
    assigned_to_id: Optional[int] = Query(None, description="Belirli kullanıcıya ait görev takvimi"),
    db: Session = Depends(get_db)
):
    """
    Takvim bileşeni için tarih bilgisi olan proje ve görev etkinliklerini sunar.
    """
    return ReportService.get_calendar_events(
        db,
        start_date=start_date,
        end_date=end_date,
        assigned_to_id=assigned_to_id
    )

@router.get("/gantt/timeline", response_model=GanttTimelineResponse, summary="Gantt Şeması Zaman Çizelgesini Getir")
def get_gantt_timeline(
    project_id: Optional[int] = Query(None, description="Belirli bir projenin Gantt verisi için filtrele"),
    db: Session = Depends(get_db)
):
    """
    Gantt şeması ekranı için projelerin ve alt görevlerin zaman çizelgesi verilerini sunar.
    """
    return ReportService.get_gantt_timeline(db, project_id=project_id)
