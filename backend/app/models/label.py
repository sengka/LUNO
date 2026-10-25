from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Görev ↔ etiket ilişkisi (çoka çok). Görev veya etiket silinince bağlantı da silinir.
task_labels = Table(
    "task_labels",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("label_id", ForeignKey("labels.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Label(Base):
    """Sözleşme 2. bölüm: Label nesnesi (US-033, FR-037, sözleşme 6.11).

    Etiketler proje bazında tanımlanır; aynı projede aynı adla ikinci etiket olamaz.
    """

    __tablename__ = "labels"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_labels_project_id_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # #RRGGBB biçiminde renk kodu
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Proje silinince etiketleri de silinir (FR-020).
    project: Mapped["Project"] = relationship(
        backref=backref("labels", cascade="all, delete-orphan")
    )

    def __repr__(self) -> str:
        return f"<Label project_id={self.project_id} name={self.name!r}>"
