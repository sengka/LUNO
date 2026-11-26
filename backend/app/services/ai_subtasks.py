"""Alt görev önerisi için yardımcılar (US-052, FR-079, sözleşme 13.3, #303).

Yalnızca okur; veritabanına yazmaz (13.1).
"""

from sqlalchemy.orm import Session

from app.core.exceptions import NestedSubtaskNotAllowedException
from app.models.task import Task
from app.schemas.ai import SubtaskSuggestion, SubtaskTitleLLM

_ASCII = str.maketrans("çğıöşü", "cgiosu")


def require_main_task(db: Session, task: Task) -> None:
    """Ortak korumanın ön kontrolü: alt görevin alt görevi olamaz (6.10) → 400, modele gidilmez."""
    if task.parent_id is not None:
        raise NestedSubtaskNotAllowedException()


def _key(title: str) -> str:
    """Tekrar kontrolü için: büyük-küçük harf, Türkçe karakter ve fazla boşluk farkı yok sayılır."""
    lowered = title.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(lowered.translate(_ASCII).split()).rstrip(".")


def task_with_subtasks_text(db: Session, task: Task) -> tuple[str, list[str]]:
    """Modele gidecek metni ve mevcut alt görev başlıklarını döndürür."""
    existing = [
        title
        for (title,) in db.query(Task.title).filter(Task.parent_id == task.id).order_by(Task.id).all()
    ]
    description = (task.description or "").strip() or "(yok)"
    lines = [f"Başlık: {task.title}", f"Açıklama: {description}"]
    if existing:
        lines.append("Mevcut alt görevler (bunları tekrar önerme):")
        lines += [f"- {title}" for title in existing]
    else:
        lines.append("Mevcut alt görevler: (yok)")
    return "\n".join(lines), existing


def subtask_suggestions(items: list[SubtaskTitleLLM], existing_titles: list[str]) -> list[SubtaskSuggestion]:
    """Tekrar eden ve mevcut alt görevlerle aynı olan önerileri atar; sırayı korur."""
    seen = {_key(title) for title in existing_titles}
    suggestions = []
    for item in items:
        key = _key(item.title)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(SubtaskSuggestion(title=item.title))
    return suggestions
