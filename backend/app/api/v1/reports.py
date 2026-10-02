from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.report import ProjectProgressReport, UserTaskSummaryReport, PeriodicStatsReport
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["Raporlama & Analiz"])

@router.get("/projects/{project_id}/progress", response_model=ProjectProgressReport, summary="Proje İlerleme Yüzdesi Raporu")
def get_project_progress_report(project_id: int, db: Session = Depends(get_db)):
    """
    Belirtilen projenin tamamlanan, devam eden ve yapılacak görev sayılarını ile ilerleme yüzdesini (% completed) hesaplar.
    """
    report = ReportService.get_project_progress(db, project_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{project_id} ID'li proje bulunamadı."
        )
    return report

@router.get("/users/{user_id}/tasks-summary", response_model=UserTaskSummaryReport, summary="Kişi Bazlı Görev İstatistikleri")
def get_user_task_summary_report(user_id: int, db: Session = Depends(get_db)):
    """
    Kullanıcıya atanmış görevlerin durum özetini (tamamlanan, devam eden, todo) ve başarı oranını (% completion rate) sunar.
    """
    return ReportService.get_user_task_summary(db, user_id)

@router.get("/stats", response_model=PeriodicStatsReport, summary="Günlük / Haftalık / Aylık İstatistikler")
def get_periodic_stats_report(
    timeframe: str = Query("daily", description="Zaman aralığı formatı: 'daily', 'weekly', 'monthly'"),
    start_date: Optional[date] = Query(None, description="Başlangıç tarihi (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Bitiş tarihi (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Projede belirli periyotlarda (günlük, haftalık, aylık) oluşturulan ve tamamlanan görevlerin istatistiklerini hesaplar.
    """
    if timeframe not in ["daily", "weekly", "monthly"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geçersiz timeframe parametresi. 'daily', 'weekly' veya 'monthly' kullanılmalıdır."
        )
    return ReportService.get_periodic_stats(db, timeframe=timeframe, start_date=start_date, end_date=end_date)
