from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    false,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import NotificationType

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Notification(Base):
    """API sözleşmesi 2. bölüm: Notification nesnesi (US-021, FR-051 – FR-057; sözleşme 9).

    Her kayıt tek bir kullanıcıya (`user_id`, bildirimi alan kişi) aittir.
    """

    __tablename__ = "notifications"
    __table_args__ = (
        # Bildirim listesi (yeniden eskiye) ve okunmamış sayısı (9.1, dashboard 10.1)
        Index("ix_notifications_user_id_created_at", "user_id", "created_at"),
        Index("ix_notifications_user_id_is_read", "user_id", "is_read"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Bildirimi alan kullanıcı; kullanıcı silinirse bildirimleri de silinir.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # Değerler metin olarak saklanır (tasks.status gibi); izin verilmeyen değer CHECK kısıtıyla reddedilir.
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="ck_notifications_type",
            native_enum=False,
            create_constraint=True,
            length=30,
        ),
        nullable=False,
    )
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    # Proje silinince projeye ait bildirimler de silinir (FR-020).
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Görev silinirse bildirim kalır, yalnızca görev bağlantısı kalkar.
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship(foreign_keys=[user_id])
    project: Mapped["Project | None"] = relationship(foreign_keys=[project_id])
    task: Mapped["Task | None"] = relationship(foreign_keys=[task_id])

    def __repr__(self) -> str:
        return f"<Notification id={self.id} type={self.type.value} user_id={self.user_id}>"
