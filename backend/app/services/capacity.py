"""Atamada kapasite kuralları (sözleşme 6.6, FR-073 – FR-074; US-025, US-044).

US-044 (bu modülün kapsamı): Bir üyenin kapasite sınırı tanımlı değilse
(`project_members.capacity_points` = `null`) kapasite kontrolü **yapılmaz**; atama
engellenmez ve uyarı verilmez (FR-074). Kapasite tanımsız üyeye atama, kapasite
özelliği hiç yokmuş gibi davranır.

US-025 (#283, ayrı iş): Kapasitesi tanımlı üyede açık görevlerin toplam efor puanı
kapasiteyi aşacaksa ve `confirm_over_capacity` `false` ise 409 `CAPACITY_EXCEEDED`.
O kural `ensure_assignment_capacity` içindeki işaretli yere eklenir; böylece kapasite
tanımsız üye için erken çıkış (FR-074) tek yerde kalır ve kuralı eklerken bozulmaz.
"""

from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember


def member_capacity_points(db: Session, project_id: int, user_id: int) -> int | None:
    """Üyenin kapasite sınırı. Üye değilse veya sınır tanımsızsa None (FR-074).

    Kapasite üyelikte tutulur (5.11); tanımsız kapasite `null` olarak döner.
    """
    return (
        db.query(ProjectMember.capacity_points)
        .filter(ProjectMember.project_id == project_id, ProjectMember.user_id == user_id)
        .scalar()
    )


def capacity_check_required(db: Session, project_id: int, user_id: int) -> bool:
    """Bu üye için kapasite kontrolü yapılmalı mı? (FR-074, US-044)

    Kapasite tanımsızsa False döner: atama engellenmez, uyarı verilmez.
    """
    return member_capacity_points(db, project_id, user_id) is not None


def ensure_assignment_capacity(
    db: Session,
    project_id: int,
    assignee_id: int | None,
    confirm_over_capacity: bool = False,
) -> None:
    """Atamayı kapasite açısından denetler (sözleşme 6.6).

    Atama kaldırılıyorsa (`assignee_id` None) veya üyenin kapasitesi tanımsızsa hiçbir
    kontrol yapılmaz ve hiçbir uyarı üretilmez (FR-074, US-044).
    """
    if assignee_id is None:
        return
    if not capacity_check_required(db, project_id, assignee_id):
        return
    # US-025 (#283): kapasitesi tanımlı üyede aşım kontrolü ve 409 CAPACITY_EXCEEDED
    # buraya eklenecek. Kapasite tanımsız üye yukarıda döndüğü için US-044 etkilenmez.
    return
