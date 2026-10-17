from datetime import date, datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project_member import ProjectMember
    from app.models.task import Task
    from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    """API sözleşmesi 2. bölüm: Project nesnesi.

    progress_percent (FR-061) ve member_count tabloda tutulmaz; API katmanında
    görev ve üye kayıtlarından hesaplanır.
    """

    __tablename__ = "projects"
    __table_args__ = (
        # Bitiş tarihi başlangıçtan önce olamaz (FR-016).
        CheckConstraint("end_date >= start_date", name="ck_projects_end_after_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # En fazla 2000 karakter; uzunluk API'de doğrulanır.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    created_by: Mapped["User | None"] = relationship(foreign_keys=[created_by_id])
    # Proje silinince üyelikler ve görevler de silinir (FR-020).
    members: Mapped[list["ProjectMember"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"
