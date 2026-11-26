"""Gecikme risk seviyesi hesabı (sözleşme 12.1 – 12.2, FR-070 – FR-072, US-024, US-043).

Risk seviyesi veritabanında tutulmaz; her **Task** yanıtında anlık hesaplanır
(`build_task_response`). Kural, Sprint 7'de onaylanan haliyle:

1. Görev `DONE` ise risk yok (FR-072, US-043).
2. Teslim tarihi yoksa risk yok.
3. Görev aktif değilse (onay bekliyor / reddedildi) risk yok; bu görevler Kanban,
   takvim, Gantt ve raporlarda da gösterilmez (sözleşme 1.3).
4. Teslim tarihi geçmişse `YUKSEK` (FR-071).
5. Kalan güne ve duruma göre taban seviye (`_base_level`).
6. Üç etkenden en az ikisi varsa seviye bir basamak yükselir, en fazla `YUKSEK`
   (`_escalation_factor_count`). Taban seviye yoksa yükseltme uygulanmaz.

Eşiklerin tamamı bu modülün başındaki sabitlerde durur; kuralı değiştirmek için
yalnızca bu sabitleri düzenlemek yeterlidir.
"""

from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session, object_session

from app.models.enums import (
    ACTIVE_TASK_STATUSES,
    OPEN_TASK_STATUSES,
    RISK_LEVEL_ORDER,
    RiskLevel,
    TaskStatus,
)
from app.models.task import Task
from app.services.sprints import today_utc

# --- Eşikler (sözleşme 12.1) ---------------------------------------------------------

# "2 gün veya daha az kaldı" aralığının üst sınırı.
URGENT_DAYS_LEFT = 2
# "3 – 7 gün kaldı" aralığının üst sınırı. Bu günden sonrası için taban risk yok.
NEAR_DAYS_LEFT = 7
# Yükseltme etkeni: büyük efor puanı (FR-036 değerleri arasından).
HIGH_EFFORT_POINTS = (8, 13)
# Yükseltme etkeni: aktif alt görevlerin bu orandan azı bitmişse.
SUBTASK_DONE_RATIO = 0.5
# Yükseltme etkeni: atanan kişinin aynı projedeki açık görev sayısı bu değeri aşıyorsa.
HEAVY_OPEN_TASK_COUNT = 5
# Seviyeyi bir basamak yükseltmek için gereken en az etken sayısı.
ESCALATION_FACTOR_COUNT = 2

# Kalan gün `URGENT_DAYS_LEFT` veya daha azken duruma göre taban seviye.
URGENT_BASE_LEVELS = {
    TaskStatus.TODO: RiskLevel.YUKSEK,
    TaskStatus.IN_PROGRESS: RiskLevel.ORTA,
    TaskStatus.REVIEW_TESTING: RiskLevel.DUSUK,
}
# Kalan gün `URGENT_DAYS_LEFT`'ten fazla, `NEAR_DAYS_LEFT` veya daha azken taban seviye.
# Listede olmayan durum (REVIEW_TESTING) bu aralıkta risk taşımaz.
NEAR_BASE_LEVELS = {
    TaskStatus.TODO: RiskLevel.ORTA,
    TaskStatus.IN_PROGRESS: RiskLevel.DUSUK,
}

# Risk hesaplanan durumlar: aktif ve DONE olmayan görevler.
RISKABLE_STATUSES = OPEN_TASK_STATUSES


def load_open_task_counts(db: Session, tasks: list[Task]) -> dict[tuple[int, int], int]:
    """Verilen görevlerin atanan kişileri için (proje, kullanıcı) → açık görev sayısı.

    Liste uç noktaları (6.1, 7.1, 12.2) her görev için ayrı sorgu atmasın diye
    sayıları tek sorguda toplar; sonuç `calculate_risk_level`'a verilir.
    """
    pairs = {(t.project_id, t.assignee_id) for t in tasks if t.assignee_id is not None}
    if not pairs:
        return {}

    project_ids = {project_id for project_id, _ in pairs}
    user_ids = {user_id for _, user_id in pairs}
    rows = (
        db.query(Task.project_id, Task.assignee_id, func.count(Task.id))
        .filter(
            Task.project_id.in_(project_ids),
            Task.assignee_id.in_(user_ids),
            Task.status.in_(RISKABLE_STATUSES),
        )
        .group_by(Task.project_id, Task.assignee_id)
        .all()
    )
    return {(project_id, user_id): int(count) for project_id, user_id, count in rows}


def open_task_count(db: Session, project_id: int, user_id: int) -> int:
    """Kullanıcının bir projedeki açık (DONE olmayan aktif) görev sayısı; alt görevler dahil."""
    return (
        db.query(func.count(Task.id))
        .filter(
            Task.project_id == project_id,
            Task.assignee_id == user_id,
            Task.status.in_(RISKABLE_STATUSES),
        )
        .scalar()
        or 0
    )


def _base_level(status: TaskStatus, days_left: int) -> RiskLevel | None:
    """Kalan güne ve duruma göre taban seviye; risk yoksa None (sözleşme 12.1)."""
    if days_left <= URGENT_DAYS_LEFT:
        return URGENT_BASE_LEVELS.get(status)
    if days_left <= NEAR_DAYS_LEFT:
        return NEAR_BASE_LEVELS.get(status)
    return None


def _subtasks_behind(task: Task) -> bool:
    """Aktif alt görevlerin yarısından azı bitmiş mi?

    Alt görevi olmayan görevde bu etken sayılmaz. Onay bekleyen ve reddedilen alt
    görevler, `subtask_count` alanıyla aynı şekilde hesaba katılmaz (sözleşme 1.3).
    """
    subtasks = [st for st in (task.subtasks or []) if st.status in ACTIVE_TASK_STATUSES]
    if not subtasks:
        return False
    done = sum(1 for st in subtasks if st.status == TaskStatus.DONE)
    return done < len(subtasks) * SUBTASK_DONE_RATIO


def _escalation_factor_count(task: Task, assignee_open_tasks: int) -> int:
    """Seviyeyi yükselten etkenlerin sayısı (sözleşme 12.1, 6. kural)."""
    factors = (
        task.story_points in HIGH_EFFORT_POINTS,
        _subtasks_behind(task),
        assignee_open_tasks > HEAVY_OPEN_TASK_COUNT,
    )
    return sum(1 for factor in factors if factor)


def _escalate(level: RiskLevel) -> RiskLevel:
    """Seviyeyi bir basamak yükseltir; en fazla YUKSEK."""
    index = RISK_LEVEL_ORDER.index(level)
    return RISK_LEVEL_ORDER[min(index + 1, len(RISK_LEVEL_ORDER) - 1)]


def calculate_risk_level(
    task: Task,
    *,
    today: date | None = None,
    open_task_counts: dict[tuple[int, int], int] | None = None,
) -> RiskLevel | None:
    """Görevin gecikme risk seviyesi; risk yoksa None (sözleşme 12.1).

    `open_task_counts`: `load_open_task_counts` çıktısı. Verilmezse atanan kişinin açık
    görev sayısı yalnızca gerektiğinde (taban seviye varsa ve kişi atanmışsa) sorgulanır.
    """
    if task.status == TaskStatus.DONE:
        return None
    if task.status not in RISKABLE_STATUSES:
        return None
    if task.due_date is None:
        return None

    today = today or today_utc()
    days_left = (task.due_date - today).days
    if days_left < 0:
        return RiskLevel.YUKSEK

    level = _base_level(task.status, days_left)
    if level is None:
        return None

    assignee_open_tasks = 0
    if task.assignee_id is not None:
        if open_task_counts is not None:
            assignee_open_tasks = open_task_counts.get((task.project_id, task.assignee_id), 0)
        else:
            db = object_session(task)
            if db is not None:
                assignee_open_tasks = open_task_count(db, task.project_id, task.assignee_id)

    if _escalation_factor_count(task, assignee_open_tasks) >= ESCALATION_FACTOR_COUNT:
        level = _escalate(level)
    return level


def levels_at_or_above(level: RiskLevel) -> tuple[RiskLevel, ...]:
    """Verilen seviye ve ondan yüksek seviyeler (12.2 `level` filtresi)."""
    return RISK_LEVEL_ORDER[RISK_LEVEL_ORDER.index(level) :]


def risk_sort_key(task: Task, level: RiskLevel) -> tuple:
    """Riskli görev sıralaması: en riskliden aza, sonra teslim tarihi yakın olan önce (12.2)."""
    return (
        -RISK_LEVEL_ORDER.index(level),
        task.due_date or date.max,
        task.id,
    )
