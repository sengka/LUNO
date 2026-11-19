"""Sprint ilerlemesi ve sprint bağlantısı kuralları (sözleşme 2. bölüm Sprint, 11.1 – 11.3).

`build_sprint_response` sprint ilerlemesini (FR-068) hesaplar. Sprint detayı (11.2),
sprint listesi/oluşturma (11.1) ve sprinte görev ekleme (11.3) aynı hesabı kullanmalıdır;
böylece hepsi aynı `total_points`, `done_points` ve `progress_percent` değerlerini döner.
"""

from datetime import date, datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import CustomAPIException
from app.models.enums import ACTIVE_TASK_STATUSES, TaskStatus
from app.models.sprint import Sprint
from app.models.task import Task
from app.schemas.sprint import SprintResponse


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def sprint_points(db: Session, sprint_id: int) -> tuple[int, int]:
    """Sprintteki aktif görevlerin (toplam efor puanı, DONE efor puanı).

    - Yalnızca aktif görevler sayılır (TODO, IN_PROGRESS, REVIEW_TESTING, DONE; sözleşme 1.3).
      Onay bekleyen ve reddedilen görevler sprint ilerlemesine girmez.
    - Efor puanı olmayan görev 0 puan sayılır; toplamı ve ilerlemeyi değiştirmez.
    - Sprinte eklenmiş her görev (ana görev veya alt görev) kendi puanıyla sayılır.
    """
    points = func.coalesce(func.sum(func.coalesce(Task.story_points, 0)), 0)
    total = (
        db.query(points)
        .filter(Task.sprint_id == sprint_id, Task.status.in_(ACTIVE_TASK_STATUSES))
        .scalar()
    )
    done = (
        db.query(points)
        .filter(Task.sprint_id == sprint_id, Task.status == TaskStatus.DONE)
        .scalar()
    )
    return int(total or 0), int(done or 0)


def progress_percent(done_points: int, total_points: int) -> float:
    """done_points / total_points × 100, bir ondalık (FR-068). Puan yoksa 0."""
    if total_points <= 0:
        return 0.0
    return round(done_points / total_points * 100, 1)


def build_sprint_response(db: Session, sprint: Sprint, today: date | None = None) -> SprintResponse:
    """Sprint modelini sözleşme 2. bölümdeki Sprint nesnesine çevirir."""
    total, done = sprint_points(db, sprint.id)
    today = today or today_utc()
    return SprintResponse(
        id=sprint.id,
        project_id=sprint.project_id,
        name=sprint.name,
        goal=sprint.goal,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        capacity_points=sprint.capacity_points,
        total_points=total,
        done_points=done,
        progress_percent=progress_percent(done, total),
        is_active=sprint.start_date <= today <= sprint.end_date,
    )


def validate_sprint_for_project(db: Session, project_id: int, sprint_id: int | None) -> None:
    """Göreve verilen sprint_id aynı projenin sprinti olmalı; değilse 422 VALIDATION_ERROR.

    Görev oluşturma (6.2, 6.10) ve görev düzenleme (6.4) bu kontrolü kullanır.
    """
    if sprint_id is None:
        return
    exists = (
        db.query(Sprint.id)
        .filter(Sprint.id == sprint_id, Sprint.project_id == project_id)
        .first()
    )
    if exists is None:
        raise CustomAPIException(
            status_code=422,
            code="VALIDATION_ERROR",
            message="Lütfen hatalı alanları düzeltin.",
            fields={"sprint_id": "Sprint bulunamadı veya bu projeye ait değil."},
        )
