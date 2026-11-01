from datetime import datetime, timezone
from typing import TYPE_CHECKING
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.user import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Comment(Base):
    """API sözleşmesi 2. bölüm & 8.5/8.6: Comment nesnesi (US-020, FR-050)."""

    __tablename__ = "comments"
    __table_args__ = (
        CheckConstraint(
            "task_id IS NOT NULL OR file_id IS NOT NULL",
            name="ck_comments_task_or_file",
        ),
        Index("ix_comments_task_id_created_at", "task_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True
    )
    # Dosya yorumu (8.6). Dosya silinince yorumları da silinir (8.4).
    file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="CASCADE"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    author: Mapped["User"] = relationship(lazy="joined")
    task: Mapped["Task | None"] = relationship(back_populates="comments")
