"""Toplantı notundan çıkarılan görev önerilerini projeye bağlama (US-051, sözleşme 13.2, #302).

Model yalnızca metinde yazanı döndürür (başlık, kişi adı, tarih ifadesi). Bu modül:
- kişi adını projenin üyeleriyle eşleştirir,
- tarih ifadesini tarihe çevirir (turkish_dates).
Yalnızca okur; veritabanına yazmaz (13.1).
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.ai import ExtractedTaskLLM, TaskSuggestion
from app.services.turkish_dates import resolve_due_date

_ASCII = str.maketrans("çğıöşü", "cgiosu")


def _normalize(name: str) -> str:
    """Büyük-küçük harf ve Türkçe karakter farkını yok sayar: 'AYŞE  Kaya' → 'ayse kaya'."""
    lowered = name.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(lowered.translate(_ASCII).split())


def project_members(db: Session, project_id: int) -> list[User]:
    return (
        db.query(User)
        .join(ProjectMember, ProjectMember.user_id == User.id)
        .filter(ProjectMember.project_id == project_id)
        .all()
    )


def match_assignee(name: Optional[str], members: list[User]) -> tuple[Optional[int], Optional[str]]:
    """Modelin verdiği adı proje üyeleriyle eşleştirir.

    - Ad-soyad tam eşleşirse o kişi seçilir.
    - Yoksa yalnızca ad (ilk sözcük) karşılaştırılır.
    - Tam bir kişi bulunursa (id, kişinin tam adı) döner.
    - Hiç ya da birden fazla kişi eşleşirse (None, metindeki ad) döner; frontend kişiyi
      kullanıcıya seçtirir (13.2).
    """
    if not name:
        return None, None
    wanted = _normalize(name)

    full_matches = [m for m in members if _normalize(m.full_name) == wanted]
    if len(full_matches) == 1:
        return full_matches[0].id, full_matches[0].full_name
    if full_matches:
        return None, name

    first_matches = [m for m in members if _normalize(m.full_name).split(" ")[0] == wanted.split(" ")[0]]
    if len(first_matches) == 1 and " " not in wanted:
        return first_matches[0].id, first_matches[0].full_name
    return None, name


def build_suggestions(items: list[ExtractedTaskLLM], members: list[User], today: date) -> list[TaskSuggestion]:
    suggestions = []
    for item in items:
        assignee_id, assignee_name = match_assignee(item.assignee_name, members)
        suggestions.append(
            TaskSuggestion(
                title=item.title,
                assignee_id=assignee_id,
                assignee_name=assignee_name,
                due_date=resolve_due_date(item.due_expression, today),
            )
        )
    return suggestions
