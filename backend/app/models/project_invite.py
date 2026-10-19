from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectInvite(Base):
    """Projeye davet bağlantısı (US-010, FR-021, sözleşme 5.8 / 5.9).

    Bağlantı oluşturulduktan sonra 7 gün geçerlidir; süre içinde birden fazla kişi
    aynı bağlantıyla projeye katılabilir.
    """

    __tablename__ = "project_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Proje silinince davetleri de silinir (FR-020).
    project: Mapped["Project"] = relationship(
        backref=backref("invites", cascade="all, delete-orphan")
    )

    def __repr__(self) -> str:
        return f"<ProjectInvite project_id={self.project_id} expires_at={self.expires_at}>"
