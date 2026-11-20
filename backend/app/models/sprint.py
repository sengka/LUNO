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
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Sprint(Base):
    """API sözleşmesi 2. bölüm: Sprint nesnesi (US-040, US-041; sözleşme 11).

    Tabloda tutulmayan, API katmanında hesaplanan alanlar (app/services/sprints.py):
      total_points, done_points, progress_percent (FR-068), is_active.
    """

    __tablename__ = "sprints"
    __table_args__ = (
        # Bitiş tarihi başlangıçtan önce olamaz (sözleşme 11.1, INVALID_DATE_RANGE).
        CheckConstraint("end_date >= start_date", name="ck_sprints_end_after_start"),
        # Kapasite boşsa sınır yok, doluysa > 0 (FR-074, FR-075).
        CheckConstraint(
            "capacity_points IS NULL OR capacity_points > 0",
            name="ck_sprints_capacity_positive",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    capacity_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Proje silinince sprintleri de silinir (FR-020).
    project: Mapped["Project"] = relationship(
        backref=backref("sprints", cascade="all, delete-orphan", passive_deletes=True)
    )
    # Sprint silinince görevler silinmez; sprint_id'leri null olur (sözleşme 11.2).
    tasks: Mapped[list["Task"]] = relationship(back_populates="sprint", passive_deletes=True)

    def __repr__(self) -> str:
        return f"<Sprint id={self.id} name={self.name!r} project_id={self.project_id}>"
