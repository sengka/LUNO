"""LLM özetleri için veritabanından metin hazırlama (US-053, FR-081, FR-082, sözleşme 13.5–13.6, #297).

Bu modül yalnızca okur; veritabanına yazmaz (13.1). Hazırlanan metin uç noktada ortak istem
şablonuyla (user_data) modele verilir. Tarih aralığını model değil backend belirler; model
yalnızca verilen veriyi özetler.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import NotEnoughCommentsException
from app.models.comment import Comment
from app.models.enums import TaskStatus
from app.models.project import Project
from app.models.sprint import Sprint
from app.models.task import Task

WEEK_DAYS = 7
MIN_COMMENTS = 5  # 13.6
LIST_LIMIT = 15  # bir listede modele gönderilen en fazla görev

OPEN_STATUSES = {TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.REVIEW_TESTING}

STATUS_LABELS = {
    TaskStatus.TODO: "Yapılacak",
    TaskStatus.IN_PROGRESS: "Devam ediyor",
    TaskStatus.REVIEW_TESTING: "İnceleme/Test",
    TaskStatus.DONE: "Tamamlandı",
    TaskStatus.ONAY_BEKLIYOR: "Onay bekliyor",
    TaskStatus.REDDEDILDI: "Reddedildi",
}


def _as_date(value: Optional[datetime]) -> Optional[date]:
    """Veritabanındaki zaman damgasını UTC tarihine çevirir (SQLite saat dilimini saklamaz)."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).date()


def _status(task: Task) -> TaskStatus:
    return TaskStatus(task.status)


def _task_line(task: Task, extra: str = "") -> str:
    assignee = task.assignee.full_name if task.assignee else "atanmamış"
    line = f"- {task.title} (sorumlu: {assignee}"
    if extra:
        line += f", {extra}"
    return line + ")"


def _task_list(title: str, tasks: list[Task], extra=lambda t: "") -> list[str]:
    lines = [f"{title}: {len(tasks)}"]
    lines += [_task_line(t, extra(t)) for t in tasks[:LIST_LIMIT]]
    if len(tasks) > LIST_LIMIT:
        lines.append(f"- ... ve {len(tasks) - LIST_LIMIT} görev daha")
    return lines


# --- 13.5 Haftalık proje özeti -----------------------------------------------------------------

@dataclass
class WeeklyData:
    from_date: date
    to_date: date
    text: str


def weekly_summary_data(db: Session, project: Project, today: date) -> WeeklyData:
    """Son 7 günün (bugün dahil) görev ve ilerleme verilerini düz metne çevirir (FR-081)."""
    from_date = today - timedelta(days=WEEK_DAYS - 1)
    in_week = lambda d: d is not None and from_date <= d <= today  # noqa: E731

    tasks = db.query(Task).filter(Task.project_id == project.id).order_by(Task.id).all()

    completed = [t for t in tasks if _status(t) == TaskStatus.DONE and in_week(_as_date(t.completed_at))]
    created = [t for t in tasks if in_week(_as_date(t.created_at))]
    open_tasks = [t for t in tasks if _status(t) in OPEN_STATUSES]
    overdue = [t for t in open_tasks if t.due_date and t.due_date < today]
    due_soon = [t for t in open_tasks if t.due_date and today <= t.due_date <= today + timedelta(days=WEEK_DAYS)]

    lines = [
        f"Proje: {project.name}",
        f"Dönem: {from_date.isoformat()} – {today.isoformat()} (son 7 gün)",
    ]

    sprint = (
        db.query(Sprint)
        .filter(Sprint.project_id == project.id, Sprint.start_date <= today, Sprint.end_date >= today)
        .order_by(Sprint.start_date.desc())
        .first()
    )
    if sprint:
        goal = f", hedef: {sprint.goal}" if sprint.goal else ""
        lines.append(f"Aktif sprint: {sprint.name} ({sprint.start_date} – {sprint.end_date}{goal})")

    counts = {status: 0 for status in STATUS_LABELS}
    for task in tasks:
        counts[_status(task)] += 1
    lines.append(f"Toplam görev: {len(tasks)}")
    lines.append(
        "Durumlara göre: " + ", ".join(f"{STATUS_LABELS[s]} {n}" for s, n in counts.items() if n)
        if tasks
        else "Durumlara göre: projede görev yok"
    )

    lines += _task_list("Bu hafta tamamlanan görevler", completed)
    lines += _task_list("Bu hafta oluşturulan görevler", created)
    lines += _task_list("Teslim tarihi geçmiş açık görevler", overdue, lambda t: f"teslim: {t.due_date}")
    lines += _task_list("Önümüzdeki 7 günde teslim edilecek açık görevler", due_soon, lambda t: f"teslim: {t.due_date}")

    return WeeklyData(from_date=from_date, to_date=today, text="\n".join(lines))


# --- 13.6 Yorum zinciri özeti ------------------------------------------------------------------

def require_enough_comments(db: Session, task: Task) -> None:
    """Ortak korumanın ön kontrolü: en az 5 yorum yoksa 400 NOT_ENOUGH_COMMENTS (13.6)."""
    count = db.query(func.count(Comment.id)).filter(Comment.task_id == task.id).scalar()
    if count < MIN_COMMENTS:
        raise NotEnoughCommentsException()


def comment_thread_text(db: Session, task: Task, max_chars: Optional[int] = None) -> str:
    """Yorumları eskiden yeniye "[tarih] Yazar: metin" biçiminde dizer.

    Metin uzunluk sınırını aşarsa en eski yorumlar çıkarılır; kararlar ve açık konular için
    en güncel yorumlar daha önemlidir.
    """
    budget = (settings.LLM_MAX_INPUT_CHARS if max_chars is None else max_chars) - 300
    comments = (
        db.query(Comment)
        .filter(Comment.task_id == task.id)
        .order_by(Comment.created_at, Comment.id)
        .all()
    )
    header = f"Görev: {task.title}\nYorumlar (eskiden yeniye):"

    kept: list[str] = []
    used = len(header)
    for comment in reversed(comments):
        line = f"[{_as_date(comment.created_at)}] {comment.author.full_name}: {comment.body.strip()}"
        if kept and used + len(line) + 1 > budget:
            break
        kept.append(line)
        used += len(line) + 1
    kept.reverse()

    lines = [header]
    omitted = len(comments) - len(kept)
    if omitted:
        lines.append(f"(Uzunluk sınırı nedeniyle en eski {omitted} yorum çıkarıldı.)")
    return "\n".join(lines + kept)
