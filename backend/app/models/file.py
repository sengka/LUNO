from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.project import Project
    from app.models.task import Task
    from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProjectFile(Base):
    """Sözleşme 2. bölüm: File nesnesi (US-018, US-019, US-035; sözleşme 8.1 – 8.4).

    Dosyanın içeriği veritabanında değil depoda (yerel klasör veya Supabase Storage)
    durur; burada yalnızca bilgileri ve depodaki anahtarı (`storage_key`) tutulur.
    """

    __tablename__ = "files"
    __table_args__ = (Index("ix_files_project_id_created_at", "project_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    # Göreve yüklendiyse görev; doğrudan projeye yüklendiyse null.
    # Görev silinirse dosya kaybolmaz, projenin dosyası olarak kalır.
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Kullanıcının yüklediği dosya adı (indirmede bu adla iner)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Depodaki benzersiz anahtar, ör. "projects/3/2f1c...e9.pdf"
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Proje silinince dosya kayıtları da silinir (FR-020).
    project: Mapped["Project"] = relationship(
        backref=backref("files", cascade="all, delete-orphan", passive_deletes=True)
    )
    task: Mapped["Task | None"] = relationship(back_populates="files")
    uploaded_by: Mapped["User | None"] = relationship(foreign_keys=[uploaded_by_id])

    def __repr__(self) -> str:
        return f"<ProjectFile id={self.id} name={self.name!r} project_id={self.project_id}>"
