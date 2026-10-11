from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectMember(Base):
    """API sözleşmesi 2. bölüm: ProjectMember nesnesi.

    Bir kullanıcı bir projeye yalnızca bir kez üye olabilir (birleşik birincil anahtar).
    email ve system_role users tablosundan gelir, burada tekrar tutulmaz.
    """

    __tablename__ = "project_members"
    __table_args__ = (
        CheckConstraint(
            "capacity_points IS NULL OR capacity_points > 0",
            name="ck_project_members_capacity_positive",
        ),
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    # Ör. "Frontend Geliştirici" (FR-023)
    technical_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # null = kapasite sınırı yok, kapasite kontrolü yapılmaz (FR-074, FR-075)
    capacity_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()

    def __repr__(self) -> str:
        return f"<ProjectMember project_id={self.project_id} user_id={self.user_id}>"
